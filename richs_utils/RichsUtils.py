from settings_amazon.models import AmazonAPI
from django.conf import settings
from datetime import datetime
from urllib.parse import urljoin

import cv2
import os
import traceback
from accounts.models import User, BannedKeyword

import jaconv
import random
import shutil
import importlib
from pydoc import locate


AUCTIONS_URL_KEY_SEARCH = 'https://auctions.yahoo.co.jp/search/search?n=50&select={select}&va={va}&vo=&ve=&ngrm=0&auccat=0&aucminprice={aucminprice}&aucmaxprice={aucmaxprice}&aucmin_bidorbuy_price={aucmin_bidorbuy_price}&aucmax_bidorbuy_price={aucmax_bidorbuy_price}&l0=0&abatch={abatch}&istatus={istatus}{thumb}&gift_icon=0&charity=&slider=0&ei=UTF-8&f_adv=1&fr=auc_adv&f=0x2&mode=2'

MERCARI_URL_KEY_SEARCH = "https://www.mercari.com/jp/search/?{_sort_order}keyword={_keyword}&category_root=&brand_name=&brand_id=&size_group=&price_min={_price_min}&price_max={_price_max}{_condition}{_shipping_payer}{_status}"


# Amazon API情報を取得
def get_mws_api(user):
    try:
        e = AmazonAPI.objects.get(author=user)
        e.access_key = settings.RICHS_AWS_ACCESS_KEY
        e.secret_key = settings.RICHS_AWS_SECRET_KEY
        e.region = settings.RICHS_AWS_REGION
        e.marketplace_id = settings.RICHS_AWS_MARKETPLACE_ID
        return e
    except AmazonAPI.DoesNotExist:
        return None

# ファイルを保存する。


def handle_uploaded_file_to_yahoo_foler(f, user):
    return handle_uploaded_file(f, 'yahoo', user)

# ファイルを保存する。


def handle_uploaded_file_to_mercari_foler(f, user):
    return handle_uploaded_file(f, 'mercari', user)

# ファイルを保存する。


def handle_uploaded_file(f, target_store, user):
    base_dir = settings.RICHS_FOLDER_IMAGE + \
        '/' + target_store + '/' + user.username
    if (os.path.isdir(base_dir) == False):
        os.makedirs(base_dir)
    file_name = get_timestamp_string() + '.jpg'
    path = os.path.join(base_dir, file_name)
    destination = open(path, 'wb+')
    for chunk in f.chunks():
        destination.write(chunk)
    return file_name


# ファイルを保存する。
def handle_uploaded_tmp_file(f, user):
    base_dir = settings.RICHS_FOLDER_TMP + '/' + user.username
    if (os.path.isdir(base_dir) == False):
        os.makedirs(base_dir)

    file_name = get_timestamp_string()
    path = os.path.join(base_dir, file_name)
    destination = open(path, 'wb+')

    for chunk in f.chunks():
        destination.write(chunk)
    return path

# タイムスタンプ文字列を取得する。


def get_timestamp_string():
    return str(datetime.now().timestamp()).replace('.', '')

# ファイル削除


def delete_file(base_dir, file_name):

    if (len(file_name) == 0 or len(base_dir) == 0):
        return

    path = os.path.join(base_dir, file_name)

    if (os.path.exists(path) and os.path.isfile(path)):
        os.remove(path)

# ファイル削除


def delete_file_if_exist(path):
    if (os.path.exists(path) and os.path.isfile(path)):
        os.remove(path)

# 画像比較


def diff(target_img_path, comparing_img_path):
    try:
        IMG_SIZE = (200, 200)

        if os.path.exists(target_img_path) == False:
            print('Not Found:' + target_img_path)
            return False

        target_img = cv2.imread(target_img_path)
        target_img = cv2.resize(target_img, IMG_SIZE)
        target_hist = cv2.calcHist([target_img], [0], None, [256], [0, 256])

        if os.path.exists(comparing_img_path) == False:
            print('Not Found:' + comparing_img_path)
            return False

        comparing_img = cv2.imread(comparing_img_path)
        comparing_img = cv2.resize(comparing_img, IMG_SIZE)
        comparing_hist = cv2.calcHist(
            [comparing_img], [0], None, [256], [0, 256])

        return cv2.compareHist(target_hist, comparing_hist, 0)
    except:
        print(traceback.format_exc())
        return 0.0

# メルカリ用画像URL


def get_mercari_image_url(user, file_name):
    if (len(file_name) == 0):
        return
    return get_mercari_image_base_url(user) + '/' + file_name

# メルカリ用画像URL


def get_mercari_image_base_url(user):
    return settings.RICHS_PROTOCOL + '://' + settings.RICHS_FQDN + settings.RICHS_URL_IMAGE + '/mercari/' + user.username

# Yahoo用画像URL


def get_yahoo_image_url(user, file_name):
    if (len(file_name) == 0):
        return
    return get_yahoo_image_base_url(user) + '/' + file_name

# Yahoo用画像URL


def get_yahoo_image_base_url(user):
    return settings.RICHS_PROTOCOL + '://' + settings.RICHS_FQDN + settings.RICHS_URL_IMAGE + '/yahoo/' + user.username

# 画像をダウンロードしてYahooフォルダに保存


def download_to_yahoo_folder(client, url, user):
    return download(client, url, 'yahoo', user)

# 画像をダウンロードしてYahooフォルダに保存


def download_to_mercari_folder(client, url,  user):
    return download(client, url, 'mercari', user)

# 画像をダウンロードする。


def download(client, url, target_store, user):
    base_dir = settings.RICHS_FOLDER_IMAGE + \
        '/' + target_store + '/' + user.username
    if (os.path.isdir(base_dir) == False):
        os.makedirs(base_dir)
    number = get_timestamp_string()
    return client.save_image(url=url, base_dir=base_dir, number=number)

# ダウンロード済み画像をYahooフォルダに保存


def copy_image_to_yahoo_folder(src, user):
    return copy_image_to(src, 'yahoo', user)

# ダウンロード済み画像をYahooフォルダに保存


def copy_image_to_mercari_folder(src, user):
    return copy_image_to(src, 'mercari', user)

# ダウンロード済み画像をコピーして保存


def copy_image_to(src, target_store, user):
    base_dir = settings.RICHS_FOLDER_IMAGE + \
        '/' + target_store + '/' + user.username
    if (os.path.isdir(base_dir) == False):
        os.makedirs(base_dir)

    filename = src.split('/')[-1]
    basename = get_timestamp_string()
    ext = filename.split('.')[-1]

    filename = basename + '.' + ext
    dst = os.path.join(base_dir, filename)
    shutil.copyfile(src, dst)

    return filename

# Yahooの画像フォルダを取得


def get_yahoo_image_folder(user):
    return settings.RICHS_FOLDER_IMAGE + '/yahoo/' + user.username

# Yahooの画像フォルダを取得


def get_mercari_image_folder(user):
    return settings.RICHS_FOLDER_IMAGE + '/mercari/' + user.username


# テキストのKEY文字列を配列にする。
def keyslist_to_array(keyslist):
    result = []
    if keyslist == None or keyslist.strip() == '':
        return result

    rows = keyslist.split('\n')
    for col in rows:
        col = col.strip()
        if (len(col) > 0):
            result.append(col)
    return result

# 文字列が設定されているか判定する。


def is_valid_str(str):
    if (str == None):
        return False
    if (len(str) > 0):
        return True
    return False

# テンポラリ画像フォルダのパスを取得する。


def get_tmp_image_folder(user):
    path = os.path.join(settings.RICHS_FOLDER_IMAGE_TMP, user.username)
    if (os.path.isdir(path) == False):
        os.makedirs(path)
    return path

# ランダムにIPアドレスを返却する。


def get_ip_address(user):
    ip_address_list = get_ip_address_list(user)
    list_len = len(ip_address_list)
    if list_len == 0:
        return None
    idx = random.randint(0, list_len - 1)
    ip = ip_address_list[idx]
    return ip

# IPアドレスの一覧を返却する。


def get_ip_address_list(user):
    ip_address_list = []
    text = user.ip_address
    if (text == None):
        return ip_address_list
    ips = text.split('\n')
    for tmp in ips:
        ip_str = tmp.strip()
        if (len(ip_str) > 0):
            # TODO：validation
            ip_address_list.append(ip_str)

    return ip_address_list

# ランダムにバックグラウンドサーチ用のIPアドレスを変換する


def offer_research_ip_address():
    try:
        ipaddrs = [''] + settings.RIDE_SEARCH_EXTRA_IP_ADDRESSES
        idx = random.randint(0, len(ipaddrs))
        return ipaddrs[idx]
    except:
        # 設定がない場合はサーバー自身を指す空文字列
        return ''

# Yahooのコンディションをアマゾンのコンディションに変化する。


def yahoo_to_amazon_condition(key):
    if (key == None or key == ''):
        return 'ERR'

    try:
        dic = {'新品、未使用': 'New', '未使用': 'New', '未使用に近い': 'UsedLikeNew', '目立った傷や汚れなし': 'UsedVeryGood',
               'やや傷や汚れあり': 'UsedGood', '傷や汚れあり': 'UsedAcceptable', '中古': 'UsedAcceptable', 'その他': 'ERR', '全体的に状態が悪い': 'ERR'}
        return dic[key.strip()]
    except:
        return 'ERR'


# メルカリのコンディションをアマゾンのコンディションに変化する。
def mercari_to_amazon_condition(key):
    if (key == None or key == ''):
        return 'ERR'

    try:
        dic = {'新品、未使用': 'New', '未使用に近い': 'UsedLikeNew', '目立った傷や汚れなし': 'UsedVeryGood',
               'やや傷や汚れあり': 'UsedGood', '傷や汚れあり': 'UsedAcceptable', '全体的に状態が悪い': 'ERR'}
        return dic[key.strip()]
    except:
        return 'ERR'


# 禁止ASINであるか判定する。
def is_exclude_asins(asins, target):
    for asin in asins:
        if (asin.asin == target):
            return True
    return False


# 禁止セラーであるか判定する。
def is_exclude_sellers(sellers, target):
    for seller in sellers:
        if (seller.seller_id == target):
            return True
    return False

# 日付型を文字列型に変換する。


def to_timestamp_string(ts):
    return ts.strftime('%Y-%m-%d %H:%M:%S.%f')


# 日付型を文字列型に変換する。
def timestamp_to_display_string(ts):
    if ts == None:
        return ''
    return ts.strftime('%Y年%m月%d日 %H時%M分%S秒')


# 経過時間を表示
def timestamp_duration_to_display_string(start_ts, now_ts):
    diff = now_ts - start_ts
    s = int(diff.total_seconds())
    h = int(s / 3600)
    s %= 3600
    m = int(s / 60)
    s %= 60

    duration = ''
    if h > 0:
        duration = '{0}時間{1}分{2}秒'.format(h, m, s)
    elif m > 0:
        duration = '{0}分{1}秒'.format(m, s)
    else:
        duration = '{0}秒'.format(s)

    return duration


def amazon_items_to_asin_list(items):
    asins = []
    for item in items:
        asin = item['asin']
        if asin != '':
            asins.append(asin)
    return asins


def init_richs_user(user):
    init_yahoo_exclude_seller(user)
    init_mercari_exclude_seller(user)
    init_asin(user)
    init_amazon_settings(user)


def init_yahoo_exclude_seller(user):
    master = locate('yahoo.models.YahooExcludeSellerMaster')
    seller = locate('yahoo.models.YahooExcludeSeller')
    entity_list = master.objects.all()
    for e in entity_list:
        seller.objects.create(author=user, seller_id=e.seller_id)

def init_mercari_exclude_seller(user):
    master = locate('mercari.models.MercariExcludeSellerMaster')
    seller = locate('mercari.models.MercariExcludeSeller')
    entity_list = master.objects.all()
    for e in entity_list:
        seller.objects.create(author=user, seller_id=e.seller_id)

def init_asin(user):
    master = locate('settings_amazon.models.ExcludeAsinMaster')
    asin = locate('settings_amazon.models.ExcludeAsin')
    entity_list = master.objects.all()
    for e in entity_list:
        asin.objects.create(author=user, asin=e.asin)


def init_amazon_settings(user):
    m1 = locate('settings_amazon.models.AmazonFeedPriceSettings')
    m1.objects.create(author=user, margin_new=1.5, margin_offer=1.5, margin_new_url=3000, margin_offer_url=3000,
                      margin_offer_percent_url=0, offset_offer_price_url=-200, lowest_offer_price_url=6000)

    m2 = locate('settings_amazon.models.AmazonDefaultSettings')
    m2.objects.create(author=user, condition_type='New',
                      condition_note='新品・未使用です。', part_number='', fulfillment_latency=3)

    m3 = locate('settings_amazon.models.AmazonBrand')
    m3.objects.create(author=user, brand_name='ASK')

    m4 = locate('settings_amazon.models.AmazonParentCategoryUser')
    m4.objects.create(author=user, display_order=1,
                      name='ホビー', value='Hobbies')

    m5 = locate('settings_amazon.models.AmazonHobbiesCategoryUser')
    m5.objects.create(author=user, display_order=1, name='ホビー（その他）',
                      format='Toys', feed_product_type='Hobbies', value='2277722051')


# 禁止ワード用共通変換
def normalize(s):
    # アルファベットの大小全半角を問わず比較 + 前後のtrim付き
    return jaconv.z2h(s, kana=False, ascii=True, digit=True).lower().strip()


# 禁止キーワード
def judge_banned_item(keyword, banned_list=None):
    keyword = normalize(keyword)
    if banned_list is None:
        # 指定しない場合は DB から読み出し
        # ループ中に都度チェックする場合はIOコストが大きい
        banned_list = get_banned_list()
    for banned_keyword in banned_list:
        if banned_keyword in keyword:
            return (True, banned_keyword)
    return (False, '')


# 禁止キーワードリストの取得
# judge_banned_item の第二引数に使う
def get_banned_list():
    return [
        normalize(obj.banned_keyword) for obj in BannedKeyword.objects.all()
    ]


# listをchunk化する
# ([1,2,3,4,5], 3) -> [[1,2,3], [4,5]]
def chunkof(xs, maxlen):
    chunks = []
    ys = []
    count = 0
    for x in xs:
        ys.append(x)
        count += 1
        if count >= maxlen:
            chunks.append(ys)
            ys = []
            count = 0
    if len(ys) > 0:
        chunks.append(ys)
    return chunks


# str を int へと変換する
# 失敗時は else_value で渡した値を返す
def str2int(s, else_value=-1):
    try:
        return int(s)
    except:
        return else_value


# Amazon CSV で利用する文字列へと変換する
def to_amazon_csv_column(s, br=' '):
    if s is None:
        return ''
    if not isinstance(s, str):
        s = str(s)
    # Tab, 改行を破棄
    return s.replace('\t', ' ').replace('\r', '').replace('\n', br)
