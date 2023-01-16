import os
import urllib.parse
import traceback
import logging

from concurrent.futures import ThreadPoolExecutor

from time import sleep
from datetime import timedelta
from richs_utils import RichsUtils, ItemImageComparator
from richs_utils.BatchTransaction import BatchTransaction
from scraper import MercariSearchScraper, MercariItemScraper, ImageDownloader
from mercari.models import MercariToAmazonItem, MercariExcludeSeller
from mercari.forms import MercariSearchForm

from richs_mws import MWSUtils
from django.db.models import Q
from django.db import connections
from django.conf import settings as django_settings

from mercari import views as mercari_views

from accounts.models import User, StockCheckStatus
from django.utils import timezone

from asyncworker import asynchelpers

logger = logging.getLogger(__name__)

# スタブ
class Config(object):
    def __init__(self):
        self.similarity_threshold = 0.80
        self.rateing_threshold = 80.0


# テーブルのモデルクラスを返却する
def get_item_class():
    return MercariToAmazonItem

# 禁止セラー情報
def get_exclude_sellers(user):
    return MercariExcludeSeller.objects.filter(author=user)

# 設定条件を取得する。
def get_config(user):
    return Config()

def create_item_scraper(index, ips):
    ''' 特定IDを持つItemScraperを生成します '''
    scraper_length = len(ips) + 1
    scraper_id = index % scraper_length
    if scraper_id == 0:
        # 0 indexの場合はIPを利用しない
        return MercariItemScraper()
    # それ以外のindexの場合はIPを利用
    ip = ips[scraper_id - 1]
    return MercariItemScraper(ip)


def create_search_scraper(index, ips):
    ''' 特定IDを持つSearchScraperを生成します '''
    scraper_length = len(ips) + 1
    scraper_id = index % scraper_length
    if scraper_id == 0:
        # 0 indexの場合はIPを利用しない
        return MercariSearchScraper()
    # それ以外のindexの場合はIPを利用
    ip = ips[scraper_id - 1]
    return MercariSearchScraper(ip)


# キーワード検索用URL
def make_url(e, config):

    initial_param={}
    initial_param['search_type'] = '0'

    c = e.condition_type

    initial_param['sort_order'] = 'standard'
    initial_param['search_type'] = '0'
    initial_param['shipping_payer_id_2'] = True
    initial_param['status_id_on_sale'] = True

    initial_param['keyword'] = e.item_name
    initial_param['price_min'] = ''
    initial_param['price_max'] = ''    #   str(e.purchase_price)  # 理由は不明だが商品が見当たらなくなるので。

    if (c == 'New'):
        initial_param['condition_id_1'] = True
    elif (c == 'UsedLikeNew'):
        initial_param['condition_id_2'] = True
    elif (c == 'UsedVeryGood'):
        initial_param['condition_id_2'] = True
        initial_param['condition_id_3'] = True
    elif (c == 'UsedGood'):
        initial_param['condition_id_2'] = True
        initial_param['condition_id_3'] = True
        initial_param['condition_id_4'] = True
    elif (c == 'UsedAcceptable'):
        initial_param['condition_id_2'] = True
        initial_param['condition_id_3'] = True
        initial_param['condition_id_4'] = True
        initial_param['condition_id_5'] = True
    else :
        initial_param['condition_id_2'] = True
        initial_param['condition_id_3'] = True
        initial_param['condition_id_4'] = True
        initial_param['condition_id_5'] = True

    form = MercariSearchForm(initial = initial_param)
    url = mercari_views.to_search_url(form)

    if not form.is_valid():
        # valid で無くても URL の生成は可能
        logger.info('form err in make_url: item_id=%s (%s), errs=%s',
            e.id, e.item_name, form.errors)
        logger.debug('url (item_id: %s): %s', e.id, url)

    return url


def _update_status(user, sku):
    StockCheckStatus.objects.update_or_create(
        purchase_item_id=sku, item_type=1, owner=user)


def _update_stock(items, candidate, similarity):
    ''' items を candidate の内容に更新 '''
    for item in items:
        prev_item_id = item.current_purchase_item_id
        prev_price = item.current_purchase_price
        price = int(candidate['price'])

        #  通常レコードもしくは、在庫復活中ではない場合
        if item.record_type != 0 and item.record_type != 21:
            item.update_quantity_request = True
        item.current_purchase_seller_id = candidate['seller']
        item.current_purchase_seller_id_name = candidate['seller_name']
        item.current_purchase_item_id = candidate['item_id']
        item.current_purchase_quantity = item.quantity
        item.current_purchase_price = price
        item.current_similarity = similarity
        item.research_request = False # 検索要求を取り下げ
        item.record_type = 21 # 在庫復活
        item.save()
        logger.info('mercari item %s stock re-found: "%s" -> "%s" (price: %s -> %s)',
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
        logger.info('mercari item %s stock not-found', item.id)


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
                    item_id = candidate['item_id']
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
                    item_url = 'https://item.mercari.com/jp/' + item_id + '/'
                    candidate_details = item_scraper.get_products(item_url)
                    if not _can_buy_item(candidate_details):
                        # 購入不可能なアイテムは除外
                        continue

                    candidate_detail = candidate_details[0]

                    seller_id = candidate_detail['seller']
                    if RichsUtils.is_exclude_sellers(exclude_sellers, seller_id):
                        # 禁止出品者は除外
                        continue

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
        sku = candidate['item_id']
        if item.item_sku != sku and item.current_purchase_item_id != sku:
            c = get_item_class().objects.filter(
                (Q(current_purchase_item_id=sku)|Q(item_sku=sku))&Q(author=user)).count()
            if c > 0:
                # 重複アイテムがあるので更新しない
                return -9

        # コンディションの調査 (現在は実施しない)
        # 上位のコンディションも見ているので。
        # condition_type = RichsUtils.mercari_to_amazon_condition(candidate['condition'])
        # if (condition_type != item.condition_type):
        #     print('コンディションエラー')
        #     return -1

        # 金額取得
        price = int(candidate['price'])
        if (price > item.purchase_price):
            # 出品時の仕入れ価格よりも高いため除外
            return -1

        # メルカリ特有の条件判断
        try:
            conf = django_settings.MERCARI_RIDE_SEARCH_CONFIG
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


def _can_buy_item(item):
    ''' 該当のメルカリItemが購入可能な状態であるかを判断 '''
    if len(item) == 0:
        return False
    if item[0]['sold'] == 'True':
        return False
    if item[0]['item_status'] in ['sold_out', 'trading', 'stop', 'cancel']:
        # それぞれ、売り切れ、取引中(sold表示済)、販売停止、cancel済の場合
        return False
    return True


def _internal_run_user_inventory_check(user, sku, index, ips, expected_required_seconds):
    ''' 1アイテムの在庫チェックを実施
    return (更新必要の可否, 予定wait秒数) '''
    try:
        scraper = create_item_scraper(index, ips)
        url = 'https://item.mercari.com/jp/' + sku + '/'
        item = scraper.get_products(url)
    except:
        logger.warn('在庫確認のスクレイピングに失敗しました: %s:%s', user, sku)
        return (False, expected_required_seconds)

    if _can_buy_item(item):
        return (False, expected_required_seconds)

    logger.info('Mercari Item closed so update required: %s:%s', user, sku)
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
        # メルカリにキーワードで問い合わせ
        item = items[0]
        search_url = make_url(item, config)
        scraper = create_search_scraper(index, ips)
        candidates = scraper.get_products(search_url)
    except:
        # 問い合わせに失敗した場合は打ち切り
        logger.warn('Mercariへの問い合わせに失敗: %s:%s', user, sku)
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
    base_store_image_folder = RichsUtils.get_mercari_image_folder(user)
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
    logger.debug('start - Mercari Item Check: %s:%s', user, sku)
    started = timezone.datetime.now()
    (update_required, detect) = (False, False)
    try:
        (update_required, expected_required_seconds) = _internal_run_user_inventory_check(
            user, sku, index, ips, expected_required_seconds)
        update_required = (with_update and update_required)
        if update_required:
            (detect, candidate_size, expected_required_seconds) = _internal_run_stock_update(
                user, sku, index, ips, config, exclude_sellers, expected_required_seconds)

        _update_status(user, sku)
    except Exception as err:
        logger.exception(err)

    finally:
        # 関数の実行時間を算出し、短く終わった場合はスリープで負荷対策
        delta = timezone.datetime.now() - started
        seconds = expected_required_seconds - delta.total_seconds()
        sleep(max(1, seconds))
        logger.debug('completed - Mercari Item Check: %s:%s (%s sec, update=%s, detect=%s)',
            user, sku, (timezone.datetime.now() - started).total_seconds(), update_required, detect)
        connections.close_all()


def _run_stock_update(user, sku, index, ips, config, exclude_sellers, expected_required_seconds=2):
    ''' 商品の在庫復活処理 '''
    logger.debug('start - Mercari Item update: %s:%s', user, sku)
    started = timezone.datetime.now()
    (detect, candidate_size) = (False, -1)
    try:
        (detect, candidate_size, expected_required_seconds) = _internal_run_stock_update(
            user, sku, index, ips, config, exclude_sellers, expected_required_seconds)
        _update_status(user, sku)

    except Exception as ex:
        logger.exception(ex)

    finally:
        # 関数の実行時間を算出し、短く終わった場合はスリープで負荷対策
        delta = timezone.datetime.now() - started
        seconds = expected_required_seconds - delta.total_seconds()
        sleep(max(1, seconds))
        logger.debug('completed - Mercari Item Update: %s:%s, (%s sec, updated=%s, candidate=%s)',
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
    statuses = StockCheckStatus.objects.filter(owner=user, item_type=1)
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
    statuses = StockCheckStatus.objects.filter(owner=user, item_type=1)
    return _get_sorted_item_skus(items, statuses)


# -----------------------------------------------------------------------
# Entry Points v1
# -----------------------------------------------------------------------


def do_inventory_check(check_times=[2, 4],
        beginwith=0, max_workers=4, run_usernames=None, run_skus=None, update_required=True, dual_boot=False):
    ''' 在庫チェックの必要アイテムのカウント '''
    with BatchTransaction('mercari-withdraw', dual_boot) as transaction:
        logger.info('[%s] start inventory check for Mercari', transaction.batch_id)

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

        logger.info('[%s] complete inventory check for Mercari (total executed: %s)',
            transaction.batch_id, exec_count)


def update_inventory_check(check_times=[2, 4],
        beginwith=0, max_workers=4, run_usernames=None, run_skus=None, dual_boot=False):
    ''' 在庫チェックが必要と判断されたアイテムを順次処理する '''
    with BatchTransaction('mercari-restore', dual_boot) as transaction:
        logger.info('[%s] start inventory update for Mercari', transaction.batch_id)

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

        logger.info('[%s] complete inventory update for Mercari (total executed: %s)',
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
    with BatchTransaction('mercari-withdraw', dual_boot) as transaction:
        logger.info('[%s] start inventory check for Mercari', transaction.batch_id)

        run_usernames = set(run_usernames) if run_usernames is not None else None
        run_skus = set(run_skus) if run_skus is not None else None

        qname = django_settings.ASYNC_WORKER.get(
            'INVCHK_MERCARI_QUEUE_NAME', 'invchk_mercari')
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
            execid = 'invchk-mercari-from-{}-to-{}'.format(prev_count, exec_count)
            queue.enqueue(inventory_check_entry,
                execid, group_buffer, 
                max_workers=max_workers, 
                update_required=update_required)
            prev_count = exec_count
            group_buffer = []

        logger.info('[%s] complete inventory check distribution for Mercari (total executed: %s/%s)', 
            transaction.batch_id, exec_count, total_count)


def do_inventory_restore_v2(check_times=[2, 4],
        beginwith=0, max_workers=4, run_usernames=None, run_skus=None,
        group_lower_size=200, dual_boot=False):
    ''' 在庫チェック(復活)処理 '''
    with BatchTransaction('mercari-restore', dual_boot) as transaction:
        logger.info('[%s] start inventory update for Mercari', transaction.batch_id)

        run_usernames = set(run_usernames) if run_usernames is not None else None
        run_skus = set(run_skus) if run_skus is not None else None

        qname = django_settings.ASYNC_WORKER.get(
            'INVRES_MERCARI_QUEUE_NAME', 'invres_mercari')
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
            execid = 'invres-mercari-from-{}-to-{}'.format(prev_count, exec_count)
            queue.enqueue(inventory_restore_entry,
                execid, group_buffer, 
                max_workers=max_workers)
            prev_count = exec_count
            group_buffer = []

        logger.info('[%s] complete inventory restore distribution for Mercari (total executed: %s/%s)', 
            transaction.batch_id, exec_count, total_count)
