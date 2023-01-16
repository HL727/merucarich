import os
import urllib.parse
import traceback
import logging

from concurrent.futures import ThreadPoolExecutor

from time import sleep
from datetime import timedelta
from richs_utils import RichsUtils, ItemImageComparator
from richs_utils.BatchTransaction import BatchTransaction
from scraper import YahooSearchScraper, YahooAuctionIdScraper, ImageDownloader
from yahoo.models import YahooToAmazonItem, YahooExcludeSeller
from richs_mws import MWSUtils
from django.db.models import Q
from django.db import connections
from django.conf import settings as django_settings

from accounts.models import User, StockCheckStatus
from django.utils import timezone

from asyncworker import asynchelpers

logger = logging.getLogger(__name__)

# スタブ
class Config(object):
    def __init__(self):
        self.is_exist_bidorbuy_price = False
        self.select = '5'
        self.abtch = '0'
        self.similarity_threshold = 0.8
        self.rateing_threshold = 80.0

# テーブルのモデルクラスを返却する
def get_item_class():
    return YahooToAmazonItem

# 禁止セラー情報
def get_exclude_sellers(user):
    return YahooExcludeSeller.objects.filter(author=user)

# 設定条件を取得する。
def get_config(user):
    return Config()

def create_item_scraper(index, ips):
    ''' 特定IDを持つItemScraperを生成します '''
    scraper_length = len(ips) + 1
    scraper_id = index % scraper_length
    if scraper_id == 0:
        # 0 indexの場合はIPを利用しない
        return YahooAuctionIdScraper()
    # それ以外のindexの場合はIPを利用
    ip = ips[scraper_id - 1]
    return YahooAuctionIdScraper(ip)


def create_search_scraper(index, ips):
    ''' 特定IDを持つSearchScraperを生成します '''
    scraper_length = len(ips) + 1
    scraper_id = index % scraper_length
    if scraper_id == 0:
        # 0 indexの場合はIPを利用しない
        return YahooSearchScraper()
    # それ以外のindexの場合はIPを利用
    ip = ips[scraper_id - 1]
    return YahooSearchScraper(ip)


# キーワード検索用URL
def make_url(e, config):

    urltml = RichsUtils.AUCTIONS_URL_KEY_SEARCH

    select = config.select
    istatus = '1' if e.condition_type == 'New' else '2'
    aucminprice = '0'
    aucmaxprice = str(e.purchase_price)
    aucmin_bidorbuy_price = ''
    aucmax_bidorbuy_price = ''
    if config.is_exist_bidorbuy_price:
        aucmin_bidorbuy_price = '0'
        aucmax_bidorbuy_price =  str(e.purchase_price)

    abatch = config.abtch
    thumb='1'

    tmp='&thumb=1'
    if thumb == '0':
        tmp = ''

    va = urllib.parse.quote(e.item_name)

    url=urltml.replace('{va}', va).replace('{select}',select).replace('{istatus}',istatus).replace('{aucminprice}',aucminprice).replace('{aucmaxprice}',aucmaxprice).replace('{aucmin_bidorbuy_price}',aucmin_bidorbuy_price).replace('{aucmax_bidorbuy_price}',aucmax_bidorbuy_price).replace('{abatch}',abatch).replace('{thumb}', tmp)
    #print(url)
    return url


def _update_status(user, sku):
    StockCheckStatus.objects.update_or_create(
        purchase_item_id=sku, item_type=0, owner=user)
            

def _update_stock(items, candidate, similarity):
    ''' items を candidate の内容に更新 '''
    for item in items:
        prev_item_id = item.current_purchase_item_id
        prev_price = item.current_purchase_price
        v1 = candidate['bid_or_buy']
        v2 = candidate['current_price']
        price = int(v1 if v1 != '' else v2)

        #  通常レコードもしくは、在庫復活中ではない場合
        if item.record_type != 0 and item.record_type != 21:
            item.update_quantity_request = True
        item.current_purchase_seller_id = candidate['seller']
        item.current_purchase_item_id = candidate['auction_id']
        item.current_purchase_quantity = item.quantity
        item.current_purchase_price = price
        item.current_similarity = similarity
        item.research_request = False # 検索要求を取り下げ
        item.record_type = 21 # 在庫復活
        item.save()
        logger.info('yahoo item %s stock re-found: "%s" -> "%s" (price: %s -> %s)', 
            item.id, prev_item_id, item.current_purchase_item_id, 
            prev_price, price)
 

def _update_no_stock(items):
    ''' 該当のitemsを在庫なし状態に更新 '''
    for item in items:
        if item.record_type == 20:
            continue
        item.current_purchase_quantity = 0
        item.record_type = 20 # 在庫取り下げ
        item.update_quantity_request = True
        item.save()
        logger.info('yahoo item %s stock not-found', item.id)


def _search_new_stock(user, config, exclude_sellers, item_scraper, amazon_image, item, candidates):
    ''' 候補から新たな在庫を探す '''
    # TMPフォルダ
    tmp_image_folder = RichsUtils.get_tmp_image_folder(user)
    # 禁止セラーの場合は除外
    candidates = [ 
        c for c in candidates if not RichsUtils.is_exclude_sellers(exclude_sellers, c['seller'])
    ]
    # 禁止ワードを含む場合は除外
    candidates = [
        c for c in candidates if not RichsUtils.judge_banned_item(c['title'])[0]
    ]
    # 高速化のため、ある程度をまとめて処理する
    for chunk in RichsUtils.chunkof(candidates, 10):
        image_urls = [ c['images'][0] for c in chunk ]
        with ImageDownloader(tmp_image_folder, image_urls) as downloader:
            for candidate in chunk:
                try:
                    item_id = candidate['auction_id']
                    image_url = candidate['images'][0]
                    image_path = downloader.get(image_url)
                    if image_path is None:
                        # ダウンロード失敗
                        logger.debug('failed to download: %s', image_url)
                        continue

                    (similar, value) = ItemImageComparator.similar_fast(
                        amazon_image, image_path, config.similarity_threshold)
                    if not similar:
                        # 画像類似度が規定値以下なので何もしない
                        continue

                    # 出品情報判定
                    item_url = 'https://page.auctions.yahoo.co.jp/jp/auction/' + item_id
                    candidate_details = item_scraper.get_products(item_url, sleep_seconds=0.5)
                    if len(candidate_details) == 0:
                        continue

                    candidate_detail = candidate_details[0]
                    rateing = float(candidate_detail['rate_percent'])
                    if rateing < config.rateing_threshold:
                        # 出品者の評価が低い場合除外
                        continue

                    result = get_stock_update_info(item, candidate_detail, user)
                    # 処理結果判定
                    if result != 0:
                        continue

                    # 類似画像判定の最終チェック
                    (similar, _) = ItemImageComparator.similar(amazon_image, image_path)
                    if similar:
                        return (True, candidate_detail, value)

                except Exception as err: 
                    logger.exception(err)
    # 見つからない
    return (False, None, None)


def get_stock_update_info(item, candidate, user):
    ''' 在庫更新のための状態チェック '''
    try:
        sku = candidate['auction_id']
        if item.item_sku != sku and item.current_purchase_item_id != sku:
            c = get_item_class().objects.filter(
                (Q(current_purchase_item_id=sku)|Q(item_sku=sku))&Q(author=user)).count()
            if c > 0:
                # 重複アイテムがあるので更新しない
                return -9

        # オークションのコンディションを取得
        condition_type = RichsUtils.yahoo_to_amazon_condition(candidate['condition'])
        if (condition_type != item.condition_type):
            # コンディション不一致
            return -1

        # オークションの金額取得
        v1 = candidate['bid_or_buy']
        v2 = candidate['current_price']
        price = int(v1 if v1 != '' else v2)

        if (price > item.purchase_price):
            # 出品時の仕入れ価格よりも高いため除外
            return -1

        # ヤフオク特有の条件判断
        try:
            conf = django_settings.YAHOO_RIDE_SEARCH_CONFIG
        except:
            # 設定がない場合
            conf = {}

        # タイトルが短すぎる場合
        if len(candidate['title']) < conf.get('MINIMUM_TITLE_LENGTH', 0):
            return -4
        
        # 特定の発送元からは仕入れを行わない
        if candidate['delivery_from'] in conf.get('IGNORE_DELIVERY_FROM', []):
            return -4
        
        # 発送が指定日時以上かかる場合
        if RichsUtils.str2int(candidate['fulfillment_latency'], -1) > conf.get('MAXIMUM_FULFILLMENT'):
            return -4

        # 更新可能
        return 0
    except Exception as err:
        logger.exception(err)
        return -1


def _internal_run_user_inventory_check(user, sku, index, ips, expected_required_seconds=2):
    ''' 1アイテムの在庫チェックを実施
    return (更新必要の可否, 予定wait秒数) '''
    try:
        scraper = create_item_scraper(index, ips)
        url = 'https://page.auctions.yahoo.co.jp/jp/auction/' + sku
        item = scraper.get_products(url, sleep_seconds=0)
    except:
        logger.warn('在庫確認のスクレイピングに失敗しました: %s:%s', user, sku)
        return (False, expected_required_seconds)

    def _can_buy(item):
        # オークションのアイテムが購入可能かをかえす
        return len(item) > 0

    if _can_buy(item):
        # 購入可能なら何もしない
        return (False, expected_required_seconds)

    logger.info('Yahoo auction closed so update required: %s:%s', user, sku)
    get_item_class().objects.filter(
        author=user, current_purchase_item_id=sku).update(research_request=True)
    return (True, expected_required_seconds)


def _internal_run_stock_update(user, sku, index, ips, config, exclude_sellers, expected_required_seconds):
    ''' 1アイテムの在庫更新を実施
    return (新規在庫発見, 新アイテム候補数, 予定wait秒数) '''
    item_class = get_item_class()
    items = item_class.objects.filter(
        author=user, current_purchase_item_id=sku, 
        research_request=True).order_by('updated_date')
    if len(items) <= 0:
        # 削除されている場合は処理の必要なし
        logger.debug('SKU: %s was updated or deleted', sku)
        return (False, -1, expected_required_seconds)

    candidates = []
    try:
        # Yahooオークションへと問い合わせ
        item = items[0]
        search_url = make_url(item, config)
        scraper = create_search_scraper(index, ips)
        candidates = scraper.get_products(search_url, sleep_seconds=0)
    except:
        # 問い合わせに失敗した場合は打ち切り
        logger.warn('Yahooオークションへの問い合わせに失敗: %s:%s', user, sku)
        return (False, -1, expected_required_seconds)

    candidate_size = len(candidates)
    if candidate_size == 0:
        # アイテムは全て更新する
        _update_no_stock(items)
        logger.info('Not found candidates: %s:%s', user, sku)
        return (False, candidate_size, expected_required_seconds)

    # 関数の予期時間を動的に更新
    expected_required_seconds += 1

    # 検索を実施
    base_store_image_folder = RichsUtils.get_yahoo_image_folder(user)
    amazon_image = os.path.join(base_store_image_folder, item.main_image_url)

    # 在庫復活検索
    item_scraper = create_item_scraper(index, ips)
    (detect, details, diff) = _search_new_stock(
        user, config, exclude_sellers, item_scraper, amazon_image, item, candidates)
    if detect:
        _update_stock(items, details, diff)
    else:
        _update_no_stock(items)

    return (detect, candidate_size, expected_required_seconds)
   

def _run_user_inventory_check(user, sku, index, ips, config, exclude_sellers, with_update=False, expected_required_seconds=2):
    ''' 1アイテムの在庫チェックを行う '''
    logger.debug('start - Yahoo Item check: %s:%s', user, sku)
    started = timezone.datetime.now()
    (update_required, detect) = (False, False)
    try:
        # update_required: 在庫取り下げを行うか否か
        (update_required, expected_required_seconds) = _internal_run_user_inventory_check(
            user, sku, index, ips, expected_required_seconds)
        update_required = (with_update and update_required)
        if update_required:
            # 代替アイテムを探して、その結果に応じてアイテムの個数・仕入元を更新
            (detect, candidate_size, expected_required_seconds) = _internal_run_stock_update(
                user, sku, index, ips, config, exclude_sellers, expected_required_seconds)
        # アイテムを検索したログを残す
        _update_status(user, sku)
    except Exception as err:
        logger.exception(err)

    finally:
        # 関数の実行時間を算出し、短く終わった場合はスリープで負荷対策
        delta = timezone.datetime.now() - started
        seconds = expected_required_seconds - delta.total_seconds()
        sleep(max(1, seconds))
        logger.debug('completed - Yahoo Item check: %s:%s (%s sec, update=%s, detect=%s)', 
            user, sku, (timezone.datetime.now() - started).total_seconds(), update_required, detect)
        connections.close_all()


def _run_stock_update(user, sku, index, ips, config, exclude_sellers, expected_required_seconds=2):
    ''' 商品の在庫復活処理 '''
    logger.debug('start - Yahoo Item update: %s:%s', user, sku)
    started = timezone.datetime.now()
    (detect, candidate_size) = (False, -1)
    try:
        # 代替アイテムを探して、その結果に応じてアイテムの個数・仕入元を更新
        (detect, candidate_size, expected_required_seconds) = _internal_run_stock_update(
            user, sku, index, ips, config, exclude_sellers, expected_required_seconds)

        # アイテムを検索したログを残す
        _update_status(user, sku)

    except Exception as ex:
        logger.exception(ex)

    finally:
        # 関数の実行時間を算出し、短く終わった場合はスリープで負荷対策
        delta = timezone.datetime.now() - started
        seconds = expected_required_seconds - delta.total_seconds()
        sleep(max(1, seconds))
        logger.debug('completed - Yahoo Item update: %s:%s, (%s sec, updated=%s, candidate=%s)',
            user, sku, (timezone.datetime.now() - started).total_seconds(), detect, candidate_size)
        connections.close_all()


def _can_run_for_user(user, run_usernames):
    if run_usernames is None:
        return True
    return user.username in run_usernames


def _can_run_for_sku(sku, run_skus):
    if run_skus is None:
        return True
    return sku in run_skus


def _get_sorted_item_skus(items, statuses):
    last_checked = { s.purchase_item_id: s.updated_date for s in statuses }
    
    latest_skus = []
    skus_and_updated = []

    for item in items:
        if item.current_purchase_item_id in last_checked:
            # 一度チェックしている
            skus_and_updated.append((item.current_purchase_item_id, last_checked[item.current_purchase_item_id]))
        else:
            # 一度もチェックしていない
            latest_skus.append(item.current_purchase_item_id)

    # SKUSを時刻順ソートして取得
    skus = [ x[0] for x in sorted(skus_and_updated, key=lambda x: x[1]) ]
    return latest_skus + skus


def get_sorted_active_item_skus(user):
    ''' ユーザーの有効な取り下げ可能性のあるアイテムSKUS一覧を返す '''
    items = get_item_class().objects.filter(
        author=user, csv_flag=1, research_request=False).order_by('updated_date')
    statuses = StockCheckStatus.objects.filter(owner=user, item_type=0)
    return _get_sorted_item_skus(items, statuses)


def get_sorted_restorable_item_skus(user):
    ''' ユーザーの復帰可能性のあるアイテムSKUS一覧を返す '''
    try:
        # 復帰基準の日付
        days = django_settings.ITEM_RESTORE_DAYS
    except:
        days = 3
    restore_dt = timezone.datetime.now() - timedelta(days=days)
    items = get_item_class().objects.filter(author=user, csv_flag=1,
        research_request=True, updated_date__gte=restore_dt).order_by('updated_date')
    statuses = StockCheckStatus.objects.filter(owner=user, item_type=0)
    return _get_sorted_item_skus(items, statuses)        
        

# -----------------------------------------------------------------------
# Entry Points v1 
# -----------------------------------------------------------------------


def do_inventory_check(check_times=[2, 4], 
        beginwith=0, max_workers=4, run_usernames=None, run_skus=None, update_required=True, dual_boot=False):
    ''' 在庫チェック(取り下げ)の実施 '''
    with BatchTransaction('yahoo-withdraw', dual_boot) as transaction:
        logger.info('[%s] start inventory check for Yahoo', transaction.batch_id)

        run_usernames = set(run_usernames) if run_usernames is not None else None
        run_skus = set(run_skus) if run_skus is not None else None

        # 全ユーザーの検索条件を事前に作成して保持
        users = User.objects.filter(is_staff=False, is_active=True, check_times__in=check_times)
        search_settings = []
        max_item_count = 0
        for user in users:
            if RichsUtils.get_mws_api(user) is None:
                logger.info('skip user %s because no mws found', user)
                continue

            skus = get_sorted_active_item_skus(user)
            skus_length = len(skus)
            max_item_count = max(max_item_count, skus_length)

            logger.debug('user: %s, target_skus count: %s', user, skus_length)

            # 検索用ユーザー設定作成
            ips = RichsUtils.get_ip_address_list(user)
            search_settings.append(dict(user=user, 
                skus=skus, skulen=skus_length, 
                config=get_config(user), ips=ips,
                exclude_sellers=get_exclude_sellers(user)))

        logger.info('maximum item check: %s', max_item_count)
        item_index = beginwith
        exec_count = 0
        while item_index < max_item_count:
            begin_index = item_index
            # 数万件単位に成り得るので、Executorの負荷を減らす
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                for idx in range(10):
                    for settings in search_settings:
                        if settings['skulen'] <= item_index:
                            continue
                        user = settings['user']
                        sku = settings['skus'][item_index]
                        ips = settings['ips']
                        config = settings['config']
                        exclude_sellers = settings['exclude_sellers']
                        
                        if not _can_run_for_user(user, run_usernames):
                            continue
                        if not _can_run_for_sku(sku, run_skus):
                            continue
                        
                        executor.submit(_run_user_inventory_check, 
                            user, sku, item_index, ips, config, exclude_sellers, update_required)
                        exec_count += 1
                    item_index += 1

            logger.info('[%s] completed item check: %s - %s (total executed: %s)', 
                transaction.batch_id, begin_index, item_index - 1, exec_count)

            if not transaction.runnable():
                logger.info('[%s] stop itself by request from another process', transaction.batch_id)
                break

        logger.info('[%s] complete inventory check for Yahoo (total executed: %s)', 
            transaction.batch_id, exec_count)


def update_inventory_check(check_times=[2, 4],
        beginwith=0, max_workers=4, run_usernames=None, run_skus=None, dual_boot=False):
    ''' 在庫チェック(復活)処理 '''
    with BatchTransaction('yahoo-restore', dual_boot) as transaction:
        logger.info('[%s] start inventory update for Yahoo', transaction.batch_id)

        run_usernames = set(run_usernames) if run_usernames is not None else None
        run_skus = set(run_skus) if run_skus is not None else None

        # 全ユーザーの検索条件を事前に作成して保持
        users = User.objects.filter(is_staff=False, is_active=True, check_times__in=check_times)
        search_settings = []
        max_item_count = 0
        for user in users:
            if RichsUtils.get_mws_api(user) is None:
                logger.info('skip user %s because no mws found', user)
                continue

            skus = get_sorted_restorable_item_skus(user)
            skus_length = len(skus)
            max_item_count = max(max_item_count, skus_length)
            if skus_length > 0:
                logger.debug('user: %s, target_skus: %s', user, skus_length)

            # 検索用ユーザー設定作成
            ips = RichsUtils.get_ip_address_list(user)
            search_settings.append(dict(user=user, 
                skus=skus, skulen=len(skus), 
                config=get_config(user), ips=ips,
                exclude_sellers=get_exclude_sellers(user)))

        logger.info('maximum item check: %s', max_item_count)
        item_index = beginwith
        exec_count = 0
        while item_index < max_item_count:
            begin_index = item_index
            # 数万件単位に成り得るので、Executorの負荷を減らす
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                for idx in range(10):
                    for settings in search_settings:
                        if settings['skulen'] <= item_index:
                            continue
                        user = settings['user']
                        sku = settings['skus'][item_index]
                        config = settings['config']
                        exclude_sellers = settings['exclude_sellers']

                        if not _can_run_for_user(user, run_usernames):
                            continue
                        if not _can_run_for_sku(sku, run_skus):
                            continue
                        
                        executor.submit(_run_stock_update, user, sku, item_index, ips, config, exclude_sellers)
                        exec_count += 1
                    item_index += 1

            logger.info('[%s] completed item update: %s - %s (total executed: %s)', 
                transaction.batch_id, begin_index, item_index - 1, exec_count)

            if not transaction.runnable():
                logger.info('[%s] stop itself by request from another process', transaction.batch_id)
                break

        logger.info('[%s] complete inventory update for Yahoo (total executed: %s)', 
            transaction.batch_id, exec_count)


# ----------------------------------------------------------------------
# Entry Points v2
# ----------------------------------------------------------------------

def to_userdict(entry_tuples):
    ''' [(username, sku, item_index), ...] から User Object を抽出 '''
    usernames = set([ username for (username, _1, _2) in entry_tuples ])
    userdict = {}
    for username in usernames:
        try:
            user = User.objects.get(username=username)
            ips = RichsUtils.get_ip_address_list(user)
            userdict[username] = dict(
                user=user, config=get_config(user), ips=ips,
                exclude_sellers=get_exclude_sellers(user))
        except Exception as e:
            logger.exception(e)
    return userdict


def inventory_check_entry(execid, entry_tuples, **kwargs):
    ''' 在庫取り下げ非同期処理のエントリポイント '''
    logger.info('[%s] start async inventory group check', execid)
    # 可変引数からオプションを取得
    max_workers = kwargs.get('max_workers', 10)
    update_required = kwargs.get('update_required', True)
    # 処理に必要な情報を取得
    started = timezone.datetime.now()
    userdict = to_userdict(entry_tuples)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for (username, sku, item_index) in entry_tuples:
            user = userdict[username]['user']
            executor.submit(_run_user_inventory_check, 
                user, sku, item_index, 
                userdict[username]['ips'],
                userdict[username]['config'], 
                userdict[username]['exclude_sellers'],
                update_required)
    delta = timezone.datetime.now() - started
    seconds = delta.total_seconds()
    logger.info('[%s] completed async inventory group check (%s items, %s sec)',
        execid, len(entry_tuples), seconds)


def inventory_restore_entry(execid, entry_tuples, **kwargs):
    ''' 在庫復活非同期処理のエントリポイント '''
    logger.info('[%s] start async inventory group restore', execid)
    # 可変引数からオプションを取得
    max_workers = kwargs.get('max_workers', 10)
    # 処理に必要な情報を取得
    started = timezone.datetime.now()
    userdict = to_userdict(entry_tuples)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for (username, sku, item_index) in entry_tuples:
            user = userdict[username]['user']
            executor.submit(_run_stock_update,
                user, sku, item_index, 
                userdict[username]['ips'],
                userdict[username]['config'], 
                userdict[username]['exclude_sellers'])
    delta = timezone.datetime.now() - started
    seconds = delta.total_seconds()
    logger.info('[%s] completed async inventory group restore (%s items, %s sec)',
        execid, len(entry_tuples), seconds)


def do_inventory_check_v2(check_times=[2, 4], 
        beginwith=0, max_workers=4, run_usernames=None, run_skus=None,
        group_lower_size=200, update_required=True, dual_boot=False):
    ''' 在庫チェック(取り下げ) version 2 のエントリーポイント '''
    with BatchTransaction('yahoo-withdraw', dual_boot) as transaction:
        logger.info('[%s] start inventory check for Yahoo', transaction.batch_id)

        run_usernames = set(run_usernames) if run_usernames is not None else None
        run_skus = set(run_skus) if run_skus is not None else None

        qname = django_settings.ASYNC_WORKER.get(
            'INVCHK_YAHOO_QUEUE_NAME', 'invchk_yahoo')
        queue = asynchelpers.get_queue(qname)
        enough_jobs = django_settings.ASYNC_WORKER.get(
            'INV_QUEUE_ENOUGH_JOB_COUNT', 20)

        # 更新対象のユーザーとSKUと追加情報の組を事前に作成して保持
        users = User.objects.filter(is_staff=False, is_active=True, check_times__in=check_times)
        user_skus = {}
        max_item_count = 0
        total_count = 0
        for user in users:
            if RichsUtils.get_mws_api(user) is None:
                logger.info('skip user %s because no mws found', user)
                continue
            if not _can_run_for_user(user, run_usernames):
                logger.info('skip user %s because target user set and non-target', user)
                continue
            skus = get_sorted_active_item_skus(user)
            user_skus[user.username] = skus
            skus_length = len(skus)
            max_item_count = max(max_item_count, skus_length)
            total_count += skus_length
            logger.debug('user: %s, target_skus count: %s', user, skus_length)
        logger.info('maximum item check: %s (total: %s)', max_item_count, total_count)
        item_index = beginwith
        prev_count = 0
        exec_count = 0
        group_buffer = []
        while item_index < max_item_count:
            if not transaction.runnable():
                logger.info('[%s] stop itself by request from another process', transaction.batch_id)
                break
            qcount = queue.count
            if qcount > enough_jobs:
                # ジョブ数が一定数以上ある場合は消化されるまで待機
                logger.debug('[%s] waiting with item_index = %s because queue has enough (%s) entries',
                        transaction.batch_id, item_index, qcount)
                asynchelpers.wait(10)
                continue

            while (item_index < max_item_count) and (len(group_buffer) < group_lower_size):
                for (username, skus) in user_skus.items():
                    skulen = len(skus)
                    if skulen <= item_index:
                        continue
                    sku = skus[item_index]
                    group_buffer.append((username, sku, item_index))
                    exec_count += 1
                item_index += 1

            # 一定数以上溜まった場合、ジョブに追加
            execid = 'invchk-yahoo-from-{}-to-{}'.format(prev_count, exec_count)
            queue.enqueue(inventory_check_entry,
                execid, group_buffer, 
                max_workers=max_workers, 
                update_required=update_required)
            prev_count = exec_count
            group_buffer = []

        logger.info('[%s] complete inventory check distribution for Yahoo (total executed: %s/%s)', 
            transaction.batch_id, exec_count, total_count)


def do_inventory_restore_v2(check_times=[2, 4],
        beginwith=0, max_workers=4, run_usernames=None, run_skus=None,
        group_lower_size=200, dual_boot=False):
    ''' 在庫チェック(復活)処理 '''
    with BatchTransaction('yahoo-restore', dual_boot) as transaction:
        logger.info('[%s] start inventory update for Yahoo', transaction.batch_id)

        run_usernames = set(run_usernames) if run_usernames is not None else None
        run_skus = set(run_skus) if run_skus is not None else None

        qname = django_settings.ASYNC_WORKER.get(
            'INVRES_YAHOO_QUEUE_NAME', 'invres_yahoo')
        queue = asynchelpers.get_queue(qname)
        enough_jobs = django_settings.ASYNC_WORKER.get(
            'INV_QUEUE_ENOUGH_JOB_COUNT', 20)

        # 全ユーザーの検索条件を事前に作成して保持
        users = User.objects.filter(is_staff=False, is_active=True, check_times__in=check_times)
        user_skus = {}
        max_item_count = 0
        total_count = 0
        for user in users:
            if RichsUtils.get_mws_api(user) is None:
                logger.info('skip user %s because no mws found', user)
                continue
            if not _can_run_for_user(user, run_usernames):
                logger.info('skip user %s because target user set and non-target', user)
                continue
            skus = get_sorted_restorable_item_skus(user)
            user_skus[user.username] = skus
            skus_length = len(skus)
            max_item_count = max(max_item_count, skus_length)
            total_count += skus_length
            logger.debug('user: %s, target_skus count: %s', user, skus_length)
        logger.info('maximum item check: %s (total: %s)', max_item_count, total_count)
        item_index = beginwith
        prev_count = 0
        exec_count = 0
        group_buffer = []
        while item_index < max_item_count:
            if not transaction.runnable():
                logger.info('[%s] stop itself by request from another process', transaction.batch_id)
                break
            qcount = queue.count
            if qcount > enough_jobs:
                # ジョブ数が一定数以上ある場合は消化されるまで待機
                logger.debug('[%s] waiting with item_index = %s because queue has enough (%s) entries',
                        transaction.batch_id, item_index, qcount)
                asynchelpers.wait(10)
                continue

            while (item_index < max_item_count) and (len(group_buffer) < group_lower_size):
                for (username, skus) in user_skus.items():
                    skulen = len(skus)
                    if skulen <= item_index:
                        continue
                    sku = skus[item_index]
                    group_buffer.append((username, sku, item_index))
                    exec_count += 1
                item_index += 1

            # 一定数以上溜まった場合、ジョブに追加
            execid = 'invres-yahoo-from-{}-to-{}'.format(prev_count, exec_count)
            queue.enqueue(inventory_restore_entry,
                execid, group_buffer, 
                max_workers=max_workers)
            prev_count = exec_count
            group_buffer = []

        logger.info('[%s] complete inventory restore distribution for Yahoo (total executed: %s/%s)', 
            transaction.batch_id, exec_count, total_count)
