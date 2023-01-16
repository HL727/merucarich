import logging
logger = logging.getLogger(__name__)

from django import forms
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.db.models import Q
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.forms.models import model_to_dict
from django.views.decorators.http import require_GET
from datetime import datetime, timedelta
from django.utils.dateparse import parse_datetime

from settings_amazon.models import *
from settings_amazon import views as settings_amazon_views
from richs_utils import RichsUtils, InventoryYahoo, ItemImageComparator, \
    ResponseUtils, ItemTitleConverter, RecordLogger, Functional, AmazonSearchUtils

from .models import *
from .forms import *

from scraper import YahooSearchScraper, YahooSearchSellerScraper, YahooAuctionIdScraper, \
    YahooAuctionSellerRatingScraper, AmazonScraper, ImageDownloader, AmazonScraperBySPAPI
from richs_mws import MWSUtils

import base64
import urllib.parse
import threading

import io
import os
import re
import codecs
import csv

from accounts.models import (
    OfferReserchWatcher, StopRequest, URLSkipRequest,
    BackgroundSearchInfo, ItemCandidateToCsv,
    OverrideConstantValue, FJCMember
)
from time import sleep
from concurrent.futures import ThreadPoolExecutor

import inspect
import cv2
import traceback


from django.utils import timezone

from django.contrib import messages

from asyncworker import asynchelpers


# アイテム一覧に表示するデータを検索する。
def item_list_for_search(form, user, paging_ts, offset, limit):
    t = form['search_type'].value()
    keyword = form['keyword'].value().strip()
    search_condition = form['search_condition'].value()

    # キーワードが空の場合には、全件表示する。
    if keyword == '' or (t == '4' and keyword.isdecimal() == False ) :
        items = YahooToAmazonItem.objects.filter(author=user, csv_flag=1, updated_date__lte = paging_ts).order_by('-updated_date')[offset:limit]
        c = YahooToAmazonItem.objects.filter(author=user, csv_flag=1, updated_date__lte = paging_ts).count()
        return items, c

    # 完全一致
    if search_condition == '0':
        #商品タイトル
        if t == '0':
            items = YahooToAmazonItem.objects.filter(author=user, item_name=keyword, csv_flag=1, updated_date__lte = paging_ts).order_by('-updated_date')[offset:limit]
            c = YahooToAmazonItem.objects.filter(author=user, item_name=keyword, csv_flag=1, updated_date__lte = paging_ts).count()
            return items, c

        #Amazon SKU
        elif t == '1':
            items = YahooToAmazonItem.objects.filter(author=user, item_sku=keyword, csv_flag=1, updated_date__lte = paging_ts).order_by('-updated_date')[offset:limit]
            c = YahooToAmazonItem.objects.filter(author=user, item_sku=keyword, csv_flag=1, updated_date__lte = paging_ts).count()
            return items, c

        #仕入れ元オークションID
        elif t == '2':
            items = YahooToAmazonItem.objects.filter(author=user, current_purchase_item_id=keyword, csv_flag=1, updated_date__lte = paging_ts).order_by('-updated_date')[offset:limit]
            c = YahooToAmazonItem.objects.filter(author=user, current_purchase_item_id=keyword, csv_flag=1, updated_date__lte = paging_ts).count()
            return items, c
        #出品者ID
        elif t == '3':
            items = YahooToAmazonItem.objects.filter(author=user, current_purchase_seller_id=keyword, csv_flag=1, updated_date__lte = paging_ts).order_by('-updated_date')[offset:limit]
            c = YahooToAmazonItem.objects.filter(author=user, current_purchase_seller_id=keyword, csv_flag=1, updated_date__lte = paging_ts).count()
            return items, c
        #リードタイム
        elif t == '4':
            items = YahooToAmazonItem.objects.filter(author=user, fulfillment_latency=int(keyword), csv_flag=1, updated_date__lte = paging_ts).order_by('-updated_date')[offset:limit]
            c = YahooToAmazonItem.objects.filter(author=user, fulfillment_latency=int(keyword), csv_flag=1, updated_date__lte = paging_ts).count()
            return items, c
        print('検索条件がマッチしません。(A)')
    # 部分一致
    else:
        #商品タイトル
        if t == '0':
            items = YahooToAmazonItem.objects.filter(author=user, item_name__contains=keyword, csv_flag=1, updated_date__lte = paging_ts).order_by('-updated_date')[offset:limit]
            c = YahooToAmazonItem.objects.filter(author=user, item_name__contains=keyword, csv_flag=1, updated_date__lte = paging_ts).count()
            return items, c
        #Amazon SKU
        elif t == '1':
            items = YahooToAmazonItem.objects.filter(author=user, item_sku__contains=keyword, csv_flag=1, updated_date__lte = paging_ts).order_by('-updated_date')[offset:limit]
            c = YahooToAmazonItem.objects.filter(author=user, item_sku__contains=keyword, csv_flag=1, updated_date__lte = paging_ts).count()
            return items, c
        #仕入れ元オークションID
        elif t == '2':
            items = YahooToAmazonItem.objects.filter(author=user, current_purchase_item_id__contains=keyword, csv_flag=1, updated_date__lte = paging_ts).order_by('-updated_date')[offset:limit]
            c = YahooToAmazonItem.objects.filter(author=user, current_purchase_item_id__contains=keyword, csv_flag=1, updated_date__lte = paging_ts).count()
            return items, c
        #出品者ID
        elif t == '3':
            items = YahooToAmazonItem.objects.filter(author=user, current_purchase_seller_id__contains=keyword, csv_flag=1, updated_date__lte = paging_ts).order_by('-updated_date')[offset:limit]
            c = YahooToAmazonItem.objects.filter(author=user, current_purchase_seller_id__contains=keyword, csv_flag=1, updated_date__lte = paging_ts).count()
            return items, c
        #リードタイム
        elif t == '4':
            items = YahooToAmazonItem.objects.filter(author=user, fulfillment_latency=int(keyword), csv_flag=1, updated_date__lte = paging_ts).order_by('-updated_date')[offset:limit]
            c = YahooToAmazonItem.objects.filter(author=user, fulfillment_latency=int(keyword), csv_flag=1, updated_date__lte = paging_ts).count()
            return items, c
        print('検索条件がマッチしません。(B)')
    return None


def _item_list_status_message(item, br=False):
    brtag = '<br>' if br else ''
    substatus  = (brtag + '(適用待ち)') if item.update_quantity_request else ''
    if item.current_purchase_quantity == 0 and not item.update_quantity_request:
        return '取り下げ完了'
    if item.current_purchase_quantity == 0:
        return '取り下げ中' + substatus
    return '出品中' + substatus


def _item_list_inventory_message(item, br=False):
    if item.update_quantity_request and item.update_fulfillment_latency_request:
        if br:
            return '在庫数適用待ち<br>リードタイム適用待ち'
        return '在庫数適用待ち(リードタイム適用待ち)'
    if item.update_quantity_request:
        return '在庫数適用待ち'
    if item.record_type in [20,21]:
        if br:
            msg = RichsUtils.timestamp_to_display_string(item.updated_date)
            msg += '<br>在庫数を「{0}」に変更しました。'.format(item.current_purchase_quantity)
            if item.update_fulfillment_latency_request:
                msg += '<br>リードタイム適用待ち'
            return msg
        dt = RichsUtils.timestamp_to_display_string(item.updated_date)
        substatus = '(リードタイム適用待ち)' if item.update_fulfillment_latency_request else ''
        return '{}に在庫数を{}に変更しました。{}'.format(
            dt, item.current_purchase_quantity, substatus)
    if item.update_fulfillment_latency_request:
        return 'リードタイム適用待ち'
    return ''


def convert_item_list_to_csv_rows(items):
    ''' 出品一覧のアイテムをCSV出力用の形式に変換します '''
    rows = []
    # header
    rows.append([
        'No.', '商品名',
        'AMAZON SKU', 'AMAZON ASIN',
        '購入元オークションURL', '出品者 URL',
        '購入元価格', 'AMAZON販売価格',
        'リードタイム', '在庫',
        '出品状況', '自動在庫チェック結果',
        '商品登録日時', '最終更新日時',
    ])

    for (idx, item) in enumerate(items):
        rows.append([
            str(idx+1), item.item_name,
            item.item_sku, item.external_product_id,
            'https://page.auctions.yahoo.co.jp/jp/auction/{}'.format(item.current_purchase_item_id),
            'https://auctions.yahoo.co.jp/seller/{}'.format(item.current_purchase_seller_id),
            str(item.current_purchase_price),
            str(item.standard_price),
            str(item.current_purchase_fulfillment_latency),
            str(item.current_purchase_quantity),
            _item_list_status_message(item),
            _item_list_inventory_message(item),
            item.created_date.strftime('%Y年%m月%d日 %H時%M分%S秒'),
            item.updated_date.strftime('%Y年%m月%d日 %H時%M分%S秒'),
        ])

    return rows


# アイテム一覧
@login_required
def item_list(request):
    params={}
    form = None
    items = None
    items_count = 0
    page = 1
    offset = 0
    ts = None
    limit = settings.RICHS_PAGE_SIZE
    if (request.method == 'POST'):
        #元画面のフォーム
        form = YahooItemListSearchForm(request.POST)
        if form.is_valid():
            # 新規検索
            is_new_search = (True if 'search' in request.POST else False)
            keyword = form['keyword'].value().strip()
            tobe_search = False if keyword == '' else True
            page = int(form['page'].value())
            # 前へ
            is_prev = True if 'prev' in request.POST else False
            # 更新
            is_update = True if is_prev and page == 1 else False
            if is_prev and is_update == False:
                page -= 1
            # 次へ
            is_next = True if 'next' in request.POST else False
            if is_next:
                print('next')
                page += 1
            # オフセット/リミット算出
            offset = (page - 1) * settings.RICHS_PAGE_SIZE
            limit = offset + settings.RICHS_PAGE_SIZE
            # 削除
            is_delete = True if 'delete' in request.POST  else False
            if is_delete:
                ids = request.POST.getlist('ids')
                YahooToAmazonItem.objects.filter(id__in=ids,author=request.user).delete()
                params['message'] = "削除完了"
                params['message_detail'] = "削除が完了しました。"
            # SKUを指定して削除
            is_delete_skus = True if 'delete_skus' in request.POST  else False
            if is_delete_skus:
                skus_list = RichsUtils.keyslist_to_array(request.POST.get('delete_skus_text'))
                if (len(skus_list) > 0):
                    YahooToAmazonItem.objects.filter(author=request.user, item_sku__in=skus_list).delete()
                    params['message'] = "削除完了"
                    params['message_detail'] = "削除が完了しました。"
                else:
                    params['message'] = "失敗"
                    params['message_detail'] = "削除するSKUを指定してください。"

            # 全削除
            is_delete_all = True if 'delete_all' in request.POST  else False
            if is_delete_all:
                YahooToAmazonItem.objects.filter(author=request.user).delete()
                params['message'] = "削除完了"
                params['message_detail'] = "削除が完了しました。"

            # CSV出力
            export_csv = ('export_csv' in request.POST)
            if export_csv:
                # 検索に一致する全てを取得
                ts = timezone.datetime.now()
                (items, _count) = item_list_for_search(form, request.user, ts, 0, None)
                filename = 'itemlist_{}.csv'.format(ts.strftime('%Y%m%d%H%M%S'))
                return ResponseUtils.csv_response(filename, convert_item_list_to_csv_rows(items))

            # タイムスタンプ
            # 更新と新規検索を行った場合のみ現在時刻を利用する。
            if is_update or is_new_search:
                ts = timezone.datetime.now()
                params['top_timestamp']=RichsUtils.to_timestamp_string(ts)
            else:
                ts_string = form['top_timestamp'].value()
                params['top_timestamp']=ts_string
                ts=parse_datetime(ts_string)

            # 検索
            is_search = is_new_search or tobe_search
            if is_search:
                result = item_list_for_search(form, request.user, ts, offset, limit)
                items = result[0]
                items_count = result[1]

            # 検索/削除以外のページングの場合
            if (items == None and (is_prev or is_next)):
                items = YahooToAmazonItem.objects.filter(author=request.user, csv_flag=1, updated_date__lte = ts).order_by('-updated_date')[offset:limit]
                items_count = YahooToAmazonItem.objects.filter(author=request.user, csv_flag=1, updated_date__lte = ts).count()

        else:
            print(form.errors)

    # POST/GET共通処理
    # 値が無い場合
    if items == None:
        items = YahooToAmazonItem.objects.filter(author=request.user, csv_flag=1).order_by('-updated_date')[offset:limit]
        items_count = YahooToAmazonItem.objects.filter(author=request.user, csv_flag=1).count()
        if (len(items) > 0 and page == 1):
            ts_string=RichsUtils.to_timestamp_string(items[0].updated_date)
            params['top_timestamp'] = ts_string

    items_len = len(items)
    if (items_len > 0):
        remain = items_count - offset - items_len
        print(str(remain))
        if (remain > 0):
            params['has_next'] = True


    # 件数設定
    params['items_count'] = items_count
    params['max_items'] = request.user.max_items
    params['feed_items_count'] = YahooToAmazonItem.objects.filter(author=request.user).count()


    # 検索結果にID番号付加
    for i, item in enumerate(items):
        item.local_id = i + 1 + offset
        if (item.main_image_url.startswith('http') == False):
            item.main_image_url = RichsUtils.get_yahoo_image_url(request.user, item.main_image_url)
        item.status_message = _item_list_status_message(item, br=True)
        item.inventory_message = _item_list_inventory_message(item, br=True)

    if form == None:
        form = YahooItemListSearchForm()

    # タイムスタンプ情報を埋め込む
    params['page'] = page
    params['items'] = items
    params['form'] = form
    return render(request, 'yahoo/item_list.html', params)


# DBにCSV情報を取り込み
def import_report_internal_csv_to_db(path, user):

    # エラー行番号
    error_record_numbers = []
    # 重複SKU
    duplicate_skus = []
    # 登録件数越えSKU
    over_skus=[]

    remain = user.max_items - YahooToAmazonItem.objects.filter(author=user).count()
    exclude_asins = ExcludeAsin.objects.filter(author=user)

    with open(path, 'r', encoding='utf8') as f:
        for i, row in enumerate(csv.reader(f, delimiter = "\t")):
            try:
                # ヘッダ行のスキップ
                if (i < 1):
                    continue

                # 空行スキップ(エラーとしない)
                if (len(row) == 0):
                    continue
                if (len(row) == 1):
                    if (row[0].strip() == ''):
                        continue

                # print(len(row))
                # カラム数チェック
                if (len(row) < 4):
                    print('カラム数エラー')
                    error_record_numbers.append(str(i+1))
                    continue

                # データ設定有無チェック
                row[0] = row[0].strip()  # ItemSKU
                row[1] = row[1].strip()  # ASIN
                #row[2] = row[2].strip()
                #row[3] = row[2].strip()
                if (row[0] == '' or row[1] == ''):
                    print('未設定カラム有り')
                    error_record_numbers.append(i+1)
                    continue

                # 除外ASIN
                if RichsUtils.is_exclude_asins(exclude_asins, row[1]):
                    error_record_numbers.append('{} (除外ASIN<{}>)'.format(str(i+1), row[1]))
                    continue

                # 既存情報を上書き可能かをチェック
                items = YahooToAmazonItem.objects.filter(
                    Q(author=user) & Q(feed_type=3) & Q(csv_flag=1) & (Q(item_sku=row[0]) | Q(current_purchase_item_id=row[0])) )
                if len(items) > 0:
                    # 情報を更新して再度import処理を行う
                    # 既存データがあるため、ItemSKUは変更しない
                    updated = items[0]
                    # ASIN情報は更新してもメルカリッチ上でしか影響しない
                    # Amazon側のキーは SKU なので、不一致が置きても問題ない
                    updated.external_product_id = row[1]
                    updated.feed_type = 4 # 失敗時に復元するために一時的に設定
                    updated.current_purchase_item_id = updated.purchase_item_id = row[0]
                    updated.record_type = 10
                    updated.csv_flag = -1
                    updated.update_fulfillment_latency_request = False
                    updated.update_quantity_request = False
                    updated.research_request = False
                    updated.save()
                    continue

                # 上書き不可能な更新の重複チェック
                count = YahooToAmazonItem.objects.filter(
                    Q(author=user) & (Q(item_sku=row[0]) | Q(current_purchase_item_id=row[0])) ).count()

                if (count > 0):
                    print('重複レコード検出')
                    duplicate_skus.append(row[0])
                    continue

                # 登録件数オーバ
                if remain < 1:
                    over_skus.append(row[0])
                    continue


                # CSVデータをインポートフラグを立ててDBに取り込む
                e = YahooToAmazonItem()
                e.current_purchase_item_id  = e.purchase_item_id = row[0]
                e.item_sku = row[0]
                e.external_product_id = row[1]
                e.feed_type = 3
                e.external_product_id_type = 'ASIN'
                e.csv_flag = -1
                e.author = user
                e.record_type = 10
                e.update_fulfillment_latency_request = False
                e.update_quantity_request = False
                e.research_request = False
                e.save()
                remain -= 1
            except:
                print('CSVデータをDBにインポート中にエラーが発生')
                print(traceback.format_exc())

    return error_record_numbers, duplicate_skus, over_skus


# テンポラリーデータを削除
def import_report_internal_delete_tmpdata(user):
    # 更新中データに関しては更新失敗として0件で残す(取り下げがあるため、レコードは消せない)
    update_failed_items = YahooToAmazonItem.objects.filter(
        author=user, feed_type=4, record_type__in=[10, 11, 12, 13])
    for item in update_failed_items:
        item.feed_type = 3
        item.csv_flag = 1
        item.record_type = 20
        item.current_purchase_quantity = item.purchase_quantity = item.quantity = 0
        item.update_quantity_request = True
        item.save()

    # それ以外の中断データは消去する
    YahooToAmazonItem.objects.filter(author = user, record_type__in = [10, 11, 12, 13]).delete()


def import_report_cancel_by_exception(result, user, err):
    ''' CSV取り込みの中断処理 '''
    # 予期せぬ例外が起こった場合
    logger.exception(err)
    logger.error('ユーザー %s の処理中にエラーが発生したため、強制中断しました', user)

    result.result_message = '\n'.join([
        'ヤフオクリサーチ出品レポート取り込みに失敗しました。',
        'もう一度アップロードしてください。'
    ])
    result.status = 5
    result.end_date = timezone.datetime.now()
    result.save()


def import_report_entry(path, user):
    ''' CSV取り込みを実行する遅延タスクのエントリーポイント '''
    # データの事前準備
    result = YahooImportCSVResult.objects.filter(author=user, status=1).first()
    if result is None:
        logger.warn('事前に生成されているべきレコードが存在しません。 user=%s, status=1', user)
        return

    try:
        # 不要ファイルの削除
        import_report_internal_delete_tmpdata(user)

        # CSVファイルの取り込み
        try:
            (error_record_numbers, duplicate_skus, over_skus) = import_report_internal_csv_to_db(path, user)
            result.error_record_numbers = len(error_record_numbers)
            result.error_record_numbers_txt = '\n'.join(map(str, error_record_numbers))
            result.duplicate_skus = len(duplicate_skus)
            result.duplicate_skus_txt = '\n'.join(duplicate_skus)
            result.over_skus = len(over_skus)
            result.over_skus_text  = '\n'.join(over_skus)
            result.status = 2
            result.result_message = '[{}] CSVファイルのアップロード完了'.format(
                timezone.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            result.save()
        except Exception:
            print('CSVファイルのアップロードに失敗しました。')
            print(traceback.format_exc())
            result.result_message = 'CSVファイルのアップロードに失敗しました。\nもう一度アップロードしてください。'
            result.status = 5
            result.end_date = timezone.datetime.now()
            result.save()
            # 取り込み途中のデータを削除
            import_report_internal_delete_tmpdata(user)
            return

        # next status へと引き継ぐ
        q = asynchelpers.get_import_queue()
        q.enqueue(import_report_internal_yahoo_task, user=user)

    except Exception as err:
        # 想定しない例外の発生時は強制キャンセル
        import_report_cancel_by_exception(result, user, err)


def _import_maximum_seconds():
    ''' インポート時のワーカー稼働時間を返す '''
    conf = settings.ASYNC_WORKER
    candidate = conf.get('TASK_RECOMMENDED_MAXIMUM_IMPORT_SECONDS')
    if candidate is not None:
        return timedelta(seconds=candidate)
    candidate = conf.get('TASK_RECOMMENDED_MAXIMUM_SECONDS', 30)
    return timedelta(seconds=candidate)


def import_report_internal_yahoo_task(user, latest_id=-1):
    ''' yahooオークションの情報を取得してDBに登録する継続タスク。
    latest_id は再開時の YahooToAmazonItem の id となる。 '''
    started = datetime.now()
    worktime = _import_maximum_seconds()

    result = YahooImportCSVResult.objects.filter(author=user, status=2).first()
    if result is None:
        logger.warn('事前に生成されているべきレコードが存在しません。 user=%s, status=2', user)
        return

    exclude_sellers = YahooExcludeSeller.objects.filter(author=user)

    try:
        # アイテムを一意にソートし、まだ未処理のアイテムのみをピックアップ
        items = YahooToAmazonItem.objects.filter(
            author = user, record_type = 10, id__gt=latest_id).order_by('id')
        scraper = YahooAuctionIdScraper(RichsUtils.get_ip_address(user))
        banned_list = RichsUtils.get_banned_list()
        error_items = []
        completed = True
        for item in items:
            # 与えられた時間を使い切った場合は打ち切り
            if datetime.now() - started >= worktime:
                completed = False
                break

            latest_id = item.id
            try:
                url = 'https://page.auctions.yahoo.co.jp/jp/auction/' + item.purchase_item_id
                item_infos = scraper.get_products(url)
                # 必須: リクエストが連続しないようにする
                asynchelpers.wait(2)

                # 該当 item_id の情報が取得できない
                if len(item_infos) == 0:
                    error_items.append('アイテム取得失敗(終了済): {}'.format(item.purchase_item_id))
                    continue

                # 除外セラーID
                if RichsUtils.is_exclude_sellers(exclude_sellers, item_infos[0]['seller']):
                    error_items.append('除外セラーID <{}>: {}'.format(
                        item_infos[0]['seller'], item.purchase_item_id))
                    continue

                # 禁止ワード判定
                (is_banned, banned_keyword) = RichsUtils.judge_banned_item(
                    item_infos[0]['title'], banned_list)
                if is_banned:
                    error_items.append('禁止ワード <{}> を含む商品です: {}'.format(
                        banned_keyword, item.purchase_item_id))
                    continue

                v1 = item_infos[0]['bid_or_buy']
                v2 = item_infos[0]['current_price']
                price_str = int(v1 if v1 != '' else v2)
                item.current_purchase_price = item.purchase_price = int(price_str)
                item.condition_type = RichsUtils.yahoo_to_amazon_condition(item_infos[0]['condition'])
                item.condition_note = item_infos[0]['condition']
                item.current_purchase_seller_id = item.purchaseo_seller_id = item_infos[0]['seller']
                # 後続の処理で、現在在庫数は、SKUで価格を価格が取得できない場合は、0に上書きする。(やめる)
                item.current_purchase_quantity = item.purchase_quantity = item.quantity = 1
                item.record_type = 11
                item.save()
            except:
                print(traceback.format_exc())
                error_items.append('オークション情報取得中にエラーが発生: {}'.format(item.purchase_item_id))

        # 途中経過を更新
        def _or(a, b):
            return a if a is not None else b

        result.error_yahoo_items = _or(result.error_yahoo_items, 0) + len(error_items)
        if result.error_yahoo_items_txt in [None, '']:
            result.error_yahoo_items_txt = '\n'.join(error_items)
        else:
            result.error_yahoo_items_txt = '\n'.join([result.error_yahoo_items_txt] +  error_items)

        if completed:
            # 全てが終わっている場合はステータスを更新して次のタスクへ移る
            result.status = 3
            result.result_message = '[{}] Yahooオークション情報検索終了'.format(
                timezone.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            result.save()
            q = asynchelpers.get_import_queue()
            q.enqueue(import_report_internal_asin_download_task, user=user)
        else:
            # まだ処理がある場合は継続実行
            result.result_message = '[{}] Yahooオークション情報検索中'.format(
                timezone.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            result.save()
            q = asynchelpers.get_import_queue()
            q.enqueue(import_report_internal_yahoo_task, user=user, latest_id=latest_id)

    except Exception as err:
        # 想定しない例外の発生時は強制キャンセル
        import_report_cancel_by_exception(result, user, err)


def import_report_internal_asin_download_task(user, latest_id=-1):
    ''' ASIN情報を取得する継続タスク。
    複数のASINをまとめてAPIアクセスとredisへの保存を行う。
    latest_id は再開時の YahooToAmazonItem の id となる。 '''
    started = datetime.now()
    worktime = _import_maximum_seconds()

    result = YahooImportCSVResult.objects.filter(author=user, status=3).first()
    if result is None:
        logger.warn('事前に生成されているべきレコードが存在しません。 user=%s, status=3 (download)', user)
        return

    try:
        e = RichsUtils.get_mws_api(user)
        mws_api = MWSUtils(e.account_id,
            e.access_key, e.secret_key, e.auth_token, e.region, e.marketplace_id)

        errors=[]

        # ASIN情報を取得してredisに積む。　
        # XXX: ここはDBに作り変えても良い。
        items = YahooToAmazonItem.objects.filter(
            author=user, record_type=11, id__gt=latest_id).order_by('id')

        r = asynchelpers.get_data_redis()
        def save_into_redis(matching):
            # redisに保存 (TTLは1日)
            # 保存量を小さくするため、一時的に移し替える
            matching_keys = [
                'status', 'title', 'brand', 'small_image',
                'manufacturer', 'model', 'product_group']
            for key, value in matching.items():
                data = {}
                for matching_key in matching_keys:
                    data[matching_key] = value.get(matching_key, '')
                rkey = asynchelpers.rkey('Y2A', 'ASIN', user.username, key)
                r.hmset(rkey, data)
                r.expire(rkey, timedelta(days=1))

        complated = True
        asins = []
        for item in items:
            latest_id = item.id

            asins.append(item.external_product_id)
            if len(asins) < 5:
                continue
            # 与えられた時間を使い切った場合は打ち切り
            if datetime.now() - started >= worktime:
                complated = False
                break
            # APIでの問い合わせを行ってデータを積み込む
            matching = Functional.exponential_backoff(
                lambda: mws_api.get_matching_product_for_id('ASIN', asins),
                else_value={}, sleeps=[2, 4, 8, 16])
            save_into_redis(matching)
            asynchelpers.wait(2)
            asins = []

        if len(asins) > 0:
            # 末尾を処理
            matching = Functional.exponential_backoff(
                lambda: mws_api.get_matching_product_for_id('ASIN', asins),
                else_value={}, sleeps=[2, 4, 8, 16])
            save_into_redis(matching)
            asynchelpers.wait(2)

        result.result_message = '[{}] Amazon ASIN情報を取得中'.format(
            timezone.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        result.save()

        if complated:
            # 全てが終わっている場合はステータスを更新して次のタスクへ移る
            q = asynchelpers.get_import_queue()
            q.enqueue(import_report_internal_asin_update_task, user=user)
        else:
            # まだ処理がある場合は継続実行
            q = asynchelpers.get_import_queue()
            q.enqueue(import_report_internal_asin_download_task, user=user, latest_id=latest_id)

    except Exception as err:
        # 想定しない例外の発生時は強制キャンセル
        import_report_cancel_by_exception(result, user, err)


def import_report_internal_asin_update_task(user, latest_id=-1):
    ''' ASIN情報を取得する継続タスク。
    事前に取得したASIN情報からDBの値を更新する。
    latest_id は再開時の YahooToAmazonItem の id となる。 '''
    started = datetime.now()
    worktime = _import_maximum_seconds()

    result = YahooImportCSVResult.objects.filter(author=user, status=3).first()
    if result is None:
        logger.warn('事前に生成されているべきレコードが存在しません。 user=%s, status=3 (update)', user)
        return

    exclude_asins = ExcludeAsin.objects.filter(author=user)

    try:
        items = YahooToAmazonItem.objects.filter(
            author=user, record_type=11, id__gt=latest_id).order_by('id')

        r = asynchelpers.get_data_redis()
        client = AmazonScraper(RichsUtils.get_ip_address(user))
        errors = []
        completed = True
        for item in items:
            # 与えられた時間を使い切った場合は打ち切り
            if datetime.now() - started >= worktime:
                completed = False
                break

            latest_id = item.id
            # 除外ASIN
            if RichsUtils.is_exclude_asins(exclude_asins, item.external_product_id):
                errors.append('除外ASIN : {}'.format(item.external_product_id))
                continue

            rkey = asynchelpers.rkey(
                'Y2A', 'ASIN', user.username, item.external_product_id)
            raw_cache = r.hgetall(rkey)
            if raw_cache is None or len(raw_cache) == 0:
                errors.append(item.external_product_id)
                continue
            # convert byte into str
            info = { k.decode('utf8'): v.decode('utf8') for (k, v) in raw_cache.items() }
            if (info['status'] != 'Success'):
                errors.append(item.external_product_id)
                continue
            try:
                # update item
                item.item_name = info['title']
                item.brand_name = info['brand']
                #item.main_image_url = info['small_image']
                item.manufacturer = info['manufacturer']
                item.model = info['model']
                item.category = info['product_group']
                item.record_type = 12
                item.main_image_url  = RichsUtils.download_to_yahoo_folder(
                    client, info['small_image'], user)
                item.save()
            except:
                logger.debug('更新に失敗しました。 user=%s, external_product_id=%s',
                    user, item.external_product_id)
                errors.append(item.external_product_id)

            asynchelpers.wait()

        left = 0 if result.error_asins is None else result.error_asins
        result.error_asins = left + len(errors)
        if result.error_asins_text in [None, '']:
            result.error_asins_text = '\n'.join(errors)
        else:
            result.error_asins_text = '\n'.join([result.error_asins_text] +  errors)

        if completed:
            # 全てが終わっている場合はステータスを更新して次のタスクへ移る
            result.status = 4
            result.result_message = '[{}] Amazon ASIN情報を更新終了'.format(
                timezone.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            result.save()
            q = asynchelpers.get_import_queue()
            q.enqueue(import_report_internal_sku_download_task, user=user)
        else:
            # まだ処理がある場合は継続実行
            result.result_message = '[{}] Amazon ASIN情報を更新中'.format(
                timezone.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            result.save()
            q = asynchelpers.get_import_queue()
            q.enqueue(import_report_internal_asin_update_task, user=user, latest_id=latest_id)

    except Exception as err:
        # 想定しない例外の発生時は強制キャンセル
        import_report_cancel_by_exception(result, user, err)


def import_report_internal_sku_download_task(user, latest_id=-1):
    ''' SKU情報を取得する継続タスク。
    複数のSKUをまとめてAPIアクセスとredisへの保存を行う。
    latest_id は再開時の YahooToAmazonItem の id となる。 '''
    started = datetime.now()
    worktime = _import_maximum_seconds()

    result = YahooImportCSVResult.objects.filter(author=user, status=4).first()
    if result is None:
        logger.warn('事前に生成されているべきレコードが存在しません。 user=%s, status=4 (download)', user)
        return

    try:
        e = RichsUtils.get_mws_api(user)
        mws_api = MWSUtils(e.account_id,
            e.access_key, e.secret_key, e.auth_token, e.region, e.marketplace_id)

        errors=[]

        # ASIN情報を取得してredisに積む。　
        # XXX: ここはDBに作り変えても良い。
        items = YahooToAmazonItem.objects.filter(
            author=user, record_type=12, id__gt=latest_id).order_by('id')

        r = asynchelpers.get_data_redis()
        def save_into_redis(prices):
            # redisに保存 (TTLは1日)
            # 保存量を小さくするため、一時的に移し替える
            price_keys = ['status', 'amount']
            for sku, value in prices.items():
                data = {}
                for key in price_keys:
                    data[key] = value.get(key, '')
                rkey = asynchelpers.rkey('Y2A', 'SKU', user.username, sku)
                r.hmset(rkey, data)
                r.expire(rkey, timedelta(days=1))

        completed = True
        skus = []

        for item in items:
            latest_id = item.id
            skus.append(item.item_sku)
            if len(skus) < 20:
                continue
            # 与えられた時間を使い切った場合は打ち切り
            if datetime.now() - started >= worktime:
                completed = False
                break
            # APIでの問い合わせを行ってデータを積み込む
            prices = Functional.exponential_backoff(
                lambda: mws_api.get_my_price_for_sku(skus),
                else_value=None, sleeps=[2, 4, 8, 16])
            if prices is not None:
                save_into_redis(prices)
            else:
                # API呼び出しで最後までエラー
                api_err_msg = 'AmazonのAPI呼び出しが全て失敗: {}'.format(
                    ','.join(skus))
                logger.info(api_err_msg)
                if result.error_skus_text:
                    result.error_skus_text = '\n'.join([
                      result.error_skus_text, api_err_msg
                    ])
                else:
                    result.error_skus_text = api_err_msg

            # 回復レート 10商品/sec
            asynchelpers.wait(2)
            skus = []

        if len(skus) > 0:
            # 末尾を処理
            prices = Functional.exponential_backoff(
                lambda: mws_api.get_my_price_for_sku(skus),
                else_value=None, sleeps=[2, 4, 8, 16])
            if prices is not None:
                save_into_redis(prices)
            else:
                # API呼び出しで最後までエラー
                api_err_msg = 'AmazonのAPI呼び出しが全て失敗: {}'.format(
                    ','.join(skus))
                logger.info(api_err_msg)
                if result.error_skus_text:
                    result.error_skus_text = '\n'.join([
                      result.error_skus_text, api_err_msg
                    ])
                else:
                    result.error_skus_text = api_err_msg
            # 回復レート 10商品/sec
            asynchelpers.wait(2)

        result.result_message = '[{}] Amazon SKU情報を取得中'.format(
            timezone.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        result.save()

        if completed:
            # 全てが終わっている場合はステータスを更新して次のタスクへ移る
            q = asynchelpers.get_import_queue()
            q.enqueue(import_report_internal_sku_update_task, user=user)
        else:
            # まだ処理がある場合は継続実行
            q = asynchelpers.get_import_queue()
            q.enqueue(import_report_internal_sku_download_task, user=user, latest_id=latest_id)

    except Exception as err:
        # 想定しない例外の発生時は強制キャンセル
        import_report_cancel_by_exception(result, user, err)


def import_report_internal_sku_update_task(user, latest_id=-1):
    ''' SKU情報を取得する継続タスク。
    事前に取得したSKU情報からDBの値を更新する。
    latest_id は再開時の YahooToAmazonItem の id となる。 '''
    started = datetime.now()
    worktime = _import_maximum_seconds()

    result = YahooImportCSVResult.objects.filter(author=user, status=4).first()
    if result is None:
        logger.warn('事前に生成されているべきレコードが存在しません。 user=%s, status=4 (update)', user)
        return

    try:
        items = YahooToAmazonItem.objects.filter(
            author=user, record_type=12, id__gt=latest_id).order_by('id')

        amazon_default_setting = AmazonDefaultSettings.objects.get(author=user)
        fulfillment_latency = amazon_default_setting.fulfillment_latency
        # インポートの時は、相乗り出品相当となる
        if amazon_default_setting.ride_item_points is not None:
            standard_price_points = amazon_default_setting.ride_item_points
        else:
            standard_price_points = amazon_default_setting.standard_price_points

        r = asynchelpers.get_data_redis()
        errors = []
        completed = True
        for item in items:
            # 与えられた時間を使い切った場合は打ち切り
            if datetime.now() - started >= worktime:
                completed = False
                break

            latest_id = item.id
            rkey = asynchelpers.rkey(
                'Y2A', 'SKU', user.username, item.item_sku)
            raw_cache = r.hgetall(rkey)
            if raw_cache is None or len(raw_cache) == 0:
                errors.append(item.item_sku)
                continue
            # convert byte into str
            info = { k.decode('utf8'): v.decode('utf8') for (k, v) in raw_cache.items() }
            if (info['status'] != 'Success'):
                errors.append(item.item_sku)
                continue
            try:
                item.feed_type = 3
                item.record_type = 13
                item.csv_flag = 1
                item.purchase_fulfillment_latency = fulfillment_latency
                item.current_purchase_fulfillment_latency = fulfillment_latency
                item.fulfillment_latency = fulfillment_latency
                item.standard_price_points = standard_price_points
                if info.get('amount', '') != '':
                    item.standard_price = int(float(info['amount']))
                else:
                    item.standard_price = -1
                item.save()
            except Exception as e:
                logger.debug('更新に失敗しました。 user=%s, sku=%s',
                    user, item.item_sku)
                errors.append(item.item_sku)

            asynchelpers.wait()

        left = 0 if result.error_skus is None else result.error_skus
        result.error_skus = left + len(errors)
        if result.error_skus_text in [None, '']:
            result.error_skus_text = '\n'.join(errors)
        else:
            result.error_skus_text = '\n'.join([result.error_skus_text] +  errors)

        if completed:
            # 全てが終わっている場合はステータスを更新して次のタスクへ移る
            result.status = 5
            result.result_message = '[{}] Amazon SKU情報を更新完了'.format(
                timezone.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            result.save()
            q = asynchelpers.get_import_queue()
            q.enqueue(import_report_internal_finalize, user=user)
        else:
            # まだ処理がある場合は継続実行
            result.result_message = '[{}] Amazon SKU情報を更新中'.format(
                timezone.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            result.save()
            q = asynchelpers.get_import_queue()
            q.enqueue(import_report_internal_sku_update_task, user=user, latest_id=latest_id)

    except Exception as err:
        # 想定しない例外の発生時は強制キャンセル
        import_report_cancel_by_exception(result, user, err)


def import_report_internal_finalize(user):
    ''' CSV取り込み処理の最終処理 '''

    result = YahooImportCSVResult.objects.filter(author=user, status=5).first()
    if result is None:
        logger.warn('事前に生成されているべきレコードが存在しません。 user=%s, status=5', user)
        return

    # 正常処理結果数 (保存が成功した後に消す）
    result.success = YahooToAmazonItem.objects.filter(author = user, record_type = 13).count()
    result.save()

    # 登録商品を登録完了状態にする。
    YahooToAmazonItem.objects.filter(author = user, record_type = 13).update(record_type = 0)

    # 不要なレコード削除する。
    import_report_internal_delete_tmpdata(user)


    result_messages=[]
    result_messages.append('正常商品取り込み:{0}件'.format(result.success))

    result_messages.append('CSVフォーマットエラーの為削除:{0}件'.format(result.error_record_numbers))
    if (result.error_record_numbers > 0):
        result_messages.append('-- フォーマットエラー行数 --')
        result_messages.append(result.error_record_numbers_txt)
        result_messages.append('')

    result_messages.append('登録件数オーバの為削除:{0}件'.format(result.over_skus))
    if (result.over_skus > 0):
        result_messages.append('-- 登録件数オーバの為削除したSKU一覧 --')
        result_messages.append(result.over_skus_text)
        result_messages.append('')

    result_messages.append('登録済みのSKUである為削除:{0}件'.format(result.duplicate_skus))
    if (result.duplicate_skus > 0):
        result_messages.append('-- 既に登録済みのSKU一覧 --')
        result_messages.append(result.duplicate_skus_txt)
        result_messages.append('')

    result_messages.append('出品できない商品である為削除:{0}件'.format(result.error_yahoo_items))
    if (result.error_yahoo_items > 0):
        # 削除事由は件数を集約して表示
        lines = result.error_yahoo_items_txt.replace('\r', '').split('\n')
        matches = [ re.search('^(.+): ([a-zA-Z0-9]+)$', line) for line in lines ]
        contents = [ (m.group(1), m.group(2)) for m in matches if m is not None ]
        error_items = {}
        for (reason, _) in contents:
            if reason not in error_items:
                error_items[reason] = 1
            else:
                error_items[reason] += 1
        for reason in sorted(error_items.keys()):
            result_messages.append('- {}: {}件'.format(reason, error_items[reason]))
        result_messages.append('')

        # ユーザーがコピペして利用できるように作業が必要なSKUのみを表示
        result_messages.append('-- 削除が必要なSKU --')
        for (_, sku) in contents:
            result_messages.append(sku)
        result_messages.append('')

    result_messages.append('Amazonに登録されていないASINの為削除:{0}件'.format(result.error_asins))
    if (result.error_asins > 0):
        result_messages.append('-- 出品できないASIN一覧  --')
        result_messages.append(result.error_asins_text)
        result_messages.append('')

    result_messages.append('Amazonに登録されていないSKUの為削除:{0}件'.format(result.error_skus))
    if (result.error_skus > 0):
        result_messages.append('-- 出品できないSKU一覧 --')
        result_messages.append(result.error_skus_text)
        result_messages.append('')

    result.result_message = '\n'.join(result_messages)
    result.end_date = timezone.datetime.now()
    result.save()


def _get_importing_status(request):
    ''' アイテム取り込みの途中経過を返す '''
    params = { 'exists': True, 'done': False }
    try:
        result = YahooImportCSVResult.objects.get(Q(author=request.user), ~Q(status=0))
        params['status'] = result.status
        # プログレスメッセージ構築
        if result.status == 5:
            params['done'] = True
            params['progress_messages'] = result.result_message
        else:
            params['runging'] = True
            progress_messages = [
              '最新状況: {}'.format(result.result_message),
              '-------------------------------------------',
            ]
            if result.status > 0:
                progress_messages.append('CSVをロード中・・・')
            if result.status > 1:
                progress_messages.append('ヤフオク商品情報を取得中・・・')
            if result.status > 2:
                progress_messages.append('Amazon ASIN情報を取得中・・・')
            if result.status > 3:
                progress_messages.append('Amazon SKU情報を取得中・・・')
            params['progress_messages'] = '\n'.join(progress_messages)

    except YahooImportCSVResult.DoesNotExist:
        return {'exists': False}

    return params


# アイテム取り込み
@login_required
def import_report(request):
    encoding='utf-8'
    if (request.method == 'POST'):

        my_api = RichsUtils.get_mws_api(request.user)
        if my_api == None:
            return HttpResponseRedirect("/settings_amazon/api_settings")

        if ('import_file' in request.FILES):

            # 書き込みが行われていない場合のみ
            progress_count = YahooImportCSVResult.objects.filter(
                Q(author=request.user), ~Q(status=0)).count()
            if progress_count > 0:
                return HttpResponseRedirect("/yahoo/import_report")

            # 処理開始をDBに書き込む
            result = YahooImportCSVResult()
            result.user_check = False
            result.author = request.user
            result.status = 1
            result.result_message = '[{}] CSVファイルの取り込み開始'.format(
                timezone.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            result.save()

            path = RichsUtils.handle_uploaded_tmp_file(request.FILES['import_file'], request.user)
            #io.TextIOWrapper(request.FILES['import_file'], encoding=encoding)
            print(path)

            # 商品取り込み処理
            q = asynchelpers.get_import_queue()
            q.enqueue(import_report_entry, path=path, user=request.user)

        elif ('clear' in request.POST):
            # データがある場合のみ削除
            progress_count = YahooImportCSVResult.objects.filter(
                Q(author=request.user), ~Q(status=0)).count()
            if progress_count == 1:
                result = YahooImportCSVResult.objects.get(Q(author=request.user), ~Q(status=0))
                result.clear = True
                result.status = 0
                result.save()
    # POST/GET共通
    # 処理中のレコードを取得する。
    params = _get_importing_status(request)
    # 過去の物、および完了した物のみを表示させる
    result_list = YahooImportCSVResult.objects.filter(
        author=request.user, status__in=[0, 5]).order_by('-start_date')
    for i,e in enumerate(result_list):
        e.local_id = i + 1

    params['result_list'] = result_list

    return render(request, 'yahoo/import_report.html', params)


@login_required
@require_GET
def import_report_progress(request):
    ''' 相乗り検索のページを更新するための情報を取得 '''
    return JsonResponse(_get_importing_status(request))


# 除外セーラ
@login_required
def exclude_seller(request):
    params = {}
    if (request.method == 'POST'):
        form = YahooExcludeSellerForm(request.POST, instance=YahooExcludeSeller())
        form.instance.author = request.user
        params['success'] = False
        if form.is_valid():
            if YahooExcludeSeller.objects.filter(author=request.user, seller_id=form.instance.seller_id).count() == 0:
                form.save()
                # 登録成功メッセージ
                params['success'] = True
                params['message'] = settings.MY_MESSAGE_SUCCESS
                params['message_detail'] = settings.MY_MESSAGE_SAVE_SUCCESS
            else:
                params['message'] = settings.MY_MESSAGE_FAILED
                params['message_detail'] = '既に登録済みのセラーです。'
        else:
            # バリデーションエラー
            params['message'] = settings.MY_MESSAGE_FAILED
            params['message_detail'] = settings.MY_MESSAGE_FORM_INVALID

    params['form'] = YahooExcludeSellerForm()
    params['sellers'] = YahooExcludeSeller.objects.filter(author=request.user)
    return render(request, 'yahoo/exclude_seller.html', params)

# 除外セーラ削除
@login_required
def delete_exclude_seller(request):
    params = {}
    if (request.method == 'POST'):
        delete_ids = request.POST.getlist('delete_ids')
        if delete_ids:
            YahooExcludeSeller.objects.filter(id__in=delete_ids).delete()

    params['form'] = YahooExcludeSellerForm()
    params['sellers'] = YahooExcludeSeller.objects.filter(author=request.user)
    return render(request, 'yahoo/exclude_seller.html', params)


# キーワード検索用URL
def get_keyword_search_url(form, type):

    va = urllib.parse.quote(form['va'].value().strip(), safe='?')
    if (type == '1'):
        select = form['select'].value().strip()
        return 'https://auctions.yahoo.co.jp/seller/{0}?select={1}&sid={0}&n=50&mode=2'.format(va, select)

    urltml = RichsUtils.AUCTIONS_URL_KEY_SEARCH

    select = form['select'].value().strip()
    istatus = form['istatus'].value().strip()
    aucminprice = form['aucminprice'].value().strip()
    aucmaxprice = form['aucmaxprice'].value().strip()
    aucmin_bidorbuy_price = form['aucmin_bidorbuy_price'].value().strip()
    aucmax_bidorbuy_price = form['aucmax_bidorbuy_price'].value().strip()
    if aucmin_bidorbuy_price == '' and aucmax_bidorbuy_price == '':
        is_exist_bidorbuy_price = form['is_exist_bidorbuy_price'].value()
        # 即決価格有り
        if is_exist_bidorbuy_price == '0':
            aucmin_bidorbuy_price = '0'
            aucmax_bidorbuy_price = '10000000'
    abatch = form['abatch'].value()
    thumb=form['thumb'].value()

    tmp='&thumb=1'
    if thumb == '0':
        tmp = ''

    url=urltml.replace('{va}',va).replace('{select}',select).replace('{istatus}',istatus).replace('{aucminprice}',aucminprice).replace('{aucmaxprice}',aucmaxprice).replace('{aucmin_bidorbuy_price}',aucmin_bidorbuy_price).replace('{aucmax_bidorbuy_price}',aucmax_bidorbuy_price).replace('{abatch}',abatch).replace('{thumb}', tmp)
    #print(url)
    return url


# 検索結果のレスポンスパラメータを生成
def set_items_for_params(params, items, page, user, next_page_url='', prev_page_url=''):

    ok_items = []
    exclude_sellers = YahooExcludeSeller.objects.filter(author=user)
    banned_list = RichsUtils.get_banned_list()

    for item in items:
        seller = item.get('seller')
        if (seller is not None) and RichsUtils.is_exclude_sellers(exclude_sellers, seller):
            continue
        is_banned, banned_item = RichsUtils.judge_banned_item(
            item.get('title', ''), banned_list)
        if is_banned:
            continue
        ok_items.append(item)

    params['items'] = ok_items
    params['page'] = page

    if next_page_url != '':
        params['next_page_url'] = next_page_url

    if prev_page_url != '' and page > 1:
        params['prev_page_url'] = prev_page_url


# 検索
@login_required
def research(request):
    params = {}
    if (request.method == 'POST'):

        my_api = RichsUtils.get_mws_api(request.user)
        if my_api == None:
            return HttpResponseRedirect("/settings_amazon/api_settings")

        form = YahooSearchForm(request.POST)
        params['form'] = form

        va = form['va'].value()
        is_banned, banned_item = RichsUtils.judge_banned_item(va)
        if is_banned:
            messages.info(request, '<{}>が含まれる商品の出品は禁止されています'.format(banned_item))
            return redirect('/yahoo/research')

        # 検索
        is_search = True if 'search' in request.POST  else False
        if is_search:
            search_type = form['search_type'].value()
            if search_type == '0':
                url = get_keyword_search_url(form, search_type)
                c=YahooSearchScraper(RichsUtils.get_ip_address(request.user))
                items = c.get_products(search_url=url)
                set_items_for_params(params, items, 1, request.user, c.getNextPageURL(), c.getPrevPageURL())
            elif search_type == '1':
                url = get_keyword_search_url(form, search_type)
                c=YahooSearchSellerScraper(RichsUtils.get_ip_address(request.user))
                items = c.get_products(search_url=url)
                set_items_for_params(params, items, 1, request.user, c.getNextPageURL(), c.getPrevPageURL())
            elif search_type == '2':
                url = 'https://page.auctions.yahoo.co.jp/jp/auction/' + request.POST.get('va')
                c = YahooAuctionIdScraper(RichsUtils.get_ip_address(request.user))
                items = c.get_products(search_url=url)
                set_items_for_params(params, items, 1, request.user)
        else:
            # ページング
            is_next = True if 'next' in request.POST  else False
            is_prev = True if 'prev' in request.POST  else False
            if is_next or is_prev:
                page = int(request.POST.get('page'))
                url = ''
                if is_next:
                    page+=1
                    url = request.POST.get('next_page_url')
                elif is_prev:
                    page-=1
                    url = request.POST.get('prev_page_url')

                search_type = form['search_type'].value()
                if search_type == '1':
                    c = YahooSearchSellerScraper(RichsUtils.get_ip_address(request.user))
                else:
                    # search type は 0 or 1 のみ
                    c = YahooSearchScraper(RichsUtils.get_ip_address(request.user))

                items = c.get_products(search_url=url)
                set_items_for_params(params, items, page, request.user, c.getNextPageURL(), c.getPrevPageURL())

        # END POST
    else:
        # GET
        params['form'] = YahooSearchForm(initial = {'select': 5, 'istatus': 1})

    return render(request, 'yahoo/research.html', params)




# 検索
@login_required
def research_amazon_by_yahoo(request):

    def _get_items_from_yahoo(request, auction_id):
        c = YahooAuctionIdScraper(RichsUtils.get_ip_address(request.user))
        url='https://page.auctions.yahoo.co.jp/jp/auction/' + auction_id
        return c.get_products(search_url=url, sleep_seconds=0)

    def _get_seller_from_yahoo(request, seller_id):
        # Scraper has wrong argument name auction_id (seller_id is correct)
        c1 = YahooAuctionSellerRatingScraper(RichsUtils.get_ip_address(request.user))
        return c1.get_ratings(auction_id=seller_id, sleep_seconds=0)

    def _get_amazon_items(request, keyword):
        log_context = 'research_yahoo_by_amazon - {}'.format(request.user.username)
        amazon = AmazonScraper(RichsUtils.get_ip_address(request.user), context=log_context)
        # url = 'https://www.amazon.co.jp/s/field-keywords=' + urllib.parse.quote(keyword, safe='?')
        url = 'https://www.amazon.co.jp/s?k=' + urllib.parse.quote(keyword)
        items = amazon.get_products(url, sleep_seconds=0)
        return items
    def _get_amazon_items_by_spapi(request, keyword):
        log_context = 'research_yahoo_by_amazon - {}'.format(request.user.username)
        amazon = AmazonScraperBySPAPI(RichsUtils.get_ip_address(request.user), context=log_context)
        # url = 'https://www.amazon.co.jp/s/field-keywords=' + urllib.parse.quote(keyword, safe='?')
        url = 'https://www.amazon.co.jp/s?k=' + urllib.parse.quote(keyword)
        items = amazon.get_products(url, sleep_seconds=0)
        return items

    params = {}
    keyword = ''
    if (request.method == 'POST'):
        keyword = request.POST.get('keyword')
        params['item'] = request.session['new_feed_item_info']
        amazon_items = _get_amazon_items(request, keyword)
    else:
        auction_id = request.GET.get('auction_id')
        seller_id = request.GET.get('seller_id')
        keyword = request.GET.get('keyword')

        if (seller_id is None) or (keyword is None):
            # キーワードが足りないので順次実施する(遅い)
            items = _get_items_from_yahoo(request, auction_id)
            if (len(items) == 0):
                params['error_message'] = 'このオークションは、既に終了しています。'
                return render(request, 'yahoo/close.html', params)

            seller_id = items[0]['seller']
            rate = _get_seller_from_yahoo(request, seller_id)
            items[0]['rate'] = rate_string = str(rate['rate_all']) + ':'  + str(rate['rate_good']) + ':' + str(rate['rate_bad'])
            params['item'] = items[0]
            keyword = items[0]['title']
            request.session['new_feed_item_info'] = items[0]
            amazon_items = _get_amazon_items(request, keyword)
        else:
            # 必要なパラメータが全てあるので並列実行する(速い)
            with ThreadPoolExecutor(max_workers=3) as executor:
                f1 = executor.submit(_get_items_from_yahoo, request, auction_id)
                f2 = executor.submit(_get_seller_from_yahoo, request, seller_id)
                f3 = executor.submit(_get_amazon_items, request, keyword)
            items = f1.result()
            if (len(items) == 0):
                params['error_message'] = 'このオークションは、既に終了しています。'
                return render(request, 'yahoo/close.html', params)
            rate = f2.result()
            items[0]['rate'] = rate_string = str(rate['rate_all']) + ':'  + str(rate['rate_good']) + ':' + str(rate['rate_bad'])
            params['item'] = items[0]
            request.session['new_feed_item_info'] = items[0]
            amazon_items = f3.result()

    ok_items=[]

    if (len(amazon_items) > 0):
        asin_list = RichsUtils.amazon_items_to_asin_list(amazon_items)
        exclude_asins = ExcludeAsin.objects.filter(author=request.user, asin__in=asin_list)
        for item in amazon_items:
            if (RichsUtils.is_exclude_asins(exclude_asins, item['asin']) == False):
                ok_items.append(item)

    params['amazon_items'] = ok_items

    # Form
    initial_param={}
    initial_param['keyword'] = keyword
    form = AmazonSearchForm(initial=initial_param)
    params['form']= form
    return render(request, 'yahoo/research_amazon_by_yahoo.html', params)


# 検証用メソッド
@login_required
def test(request):
    pass


# 新規登録
@login_required
def feed_amazon_new(request):

    params={}

    def is_register():
        if request.method != 'POST':
            return False
        item_name = request.POST.get('item_name', '')
        is_banned, banned_item = RichsUtils.judge_banned_item(item_name)
        if is_banned:
            params['success'] = False
            params['message'] = '入力項目エラー'
            params['message_detail'] = '商品名に禁止ワード【{}】が含まれています'.format(banned_item)
            return False
        return True
    
    if is_register():

        if YahooToAmazonItem.objects.filter(author=request.user).count() >= request.user.max_items:
            params['error_message'] = '商品登録件数を超えているため、登録することができません。'
            return render(request, 'yahoo/close.html', params)

        form = FeedNewForm(request.POST, instance=YahooToAmazonItem())

        if form.is_valid():

            count=YahooToAmazonItem.objects.filter(Q(author=request.user) & (Q(item_sku=form.instance.item_sku) | Q(current_purchase_item_id=form.instance.item_sku)) ).count()
            print(form.instance.item_sku)
            print(count)
            if (count > 0):
                params['message'] = '既に登録済みの商品であるため登録できません。'
                return render(request, 'yahoo/close.html', params)

            form.instance.feed_type = 0
            form.instance.author = request.user
            form.instance.record_type = 0
            form.instance.current_purchase_seller_id = form.instance.purchaseo_seller_id
            form.instance.purchase_item_id = form.instance.current_purchase_item_id = form.instance.item_sku
            form.instance.purchase_quantity = form.instance.current_purchase_quantity = form.instance.quantity
            form.instance.purchase_fulfillment_latency = form.instance.current_purchase_fulfillment_latency = form.instance.fulfillment_latency


            form.instance.csv_flag=0

            #とりあえず、セッションで逃げる。
            #v1 = request.POST.get('bid_or_buy')
            #v2 = request.POST.get('current_price')
            if 'new_feed_item_info' in request.session:
                item_info = request.session['new_feed_item_info']
                v1 = item_info['bid_or_buy']
                v2 = item_info['current_price']
                form.instance.purchase_price = form.instance.current_purchase_price = int(v1 if v1 != '' else v2)

            if (form.instance.external_product_id == None or form.instance.external_product_id == ''):
                form.instance.external_product_id_type= ''
            for e in settings_amazon_views.get_child_user_model_class(form.instance.category).objects.filter(author=request.user, value=form.instance.recommended_browse_nodes):
                form.instance.format = e.format
                form.instance.feed_product_type = e.feed_product_type

            # 画像の保存
            client = YahooAuctionIdScraper(RichsUtils.get_ip_address(request.user))

            # 画像の保存
            if (form.instance.main_image_url != None and form.instance.main_image_url != ''):
                if (form.instance.main_image_url.startswith('http')):
                    form.instance.main_image_url = RichsUtils.download_to_yahoo_folder(client, form.instance.main_image_url, request.user)
                else:
                    if ('main_image_file' in request.FILES):
                        f = request.FILES['main_image_file']
                        form.instance.main_image_url = RichsUtils.handle_uploaded_file_to_yahoo_foler(f, request.user)

            if (form.instance.other_image_url1 != None and form.instance.other_image_url1 != ''):
                if (form.instance.other_image_url1.startswith('http')):
                    form.instance.other_image_url1 = RichsUtils.download_to_yahoo_folder(client, form.instance.other_image_url1, request.user)
                else:
                    if ('other_image_file1' in request.FILES):
                        f = request.FILES['other_image_file1']
                        form.instance.other_image_url1 = RichsUtils.handle_uploaded_file_to_yahoo_foler(f, request.user)

            if (form.instance.other_image_url2 != None and form.instance.other_image_url2 != ''):
                if (form.instance.other_image_url2.startswith('http')):
                    form.instance.other_image_url2 = RichsUtils.download_to_yahoo_folder(client, form.instance.other_image_url2, request.user)
                else:
                    if ('other_image_file2' in request.FILES):
                        f = request.FILES['other_image_file2']
                        form.instance.other_image_url2 = RichsUtils.handle_uploaded_file_to_yahoo_foler(f, request.user)


            if (form.instance.other_image_url3 != None and form.instance.other_image_url3 != ''):
                if (form.instance.other_image_url3.startswith('http')):
                    form.instance.other_image_url3 = RichsUtils.download_to_yahoo_folder(client, form.instance.other_image_url3, request.user)
                else:
                    if ('other_image_file3' in request.FILES):
                        f = request.FILES['other_image_file3']
                        form.instance.other_image_url3 = RichsUtils.handle_uploaded_file_to_yahoo_foler(f, request.user)

            form.instance.update_fulfillment_latency_request = False
            form.instance.update_quantity_request = False
            form.instance.research_request = False
            form.instance.record_type = 0
            form.save()
        else:
            print(form.errors)
            params['error_message'] = 'データにエラーがあります。'
            return render(request, 'yahoo/close.html', params)

        params['message'] = "登録が完了しました。"
        return render(request, 'yahoo/close.html', params)

    else:

        if request.POST:
            # 再入力の場合
            form = FeedNewForm(request.POST, instance=YahooToAmazonItem())
            params['images'] = request.session.get('new_feed_item_info', {}).get('images', [])
        elif 'new_feed_item_info' in request.session:
            item_info = request.session['new_feed_item_info']

            count=YahooToAmazonItem.objects.filter(Q(author=request.user) & (Q(item_sku=item_info['auction_id']) | Q(current_purchase_item_id=item_info['auction_id']))   ).count()
            if (count > 0):
                params['error_message'] = '既に登録済みの商品であるため登録できません。'
                return render(request, 'yahoo/close.html', params)

            # Form引き渡し情報構築
            initial_param = {}
            initial_param['external_product_id_type'] = 'EAN'

            # スクレイピングからForm
            initial_param['item_sku'] = item_info['auction_id']
            initial_item_name = ItemTitleConverter.convert(item_info['title'])
            initial_param['item_name'] = initial_item_name
            initial_param['product_description'] = initial_item_name
            initial_param['generic_keywords'] = initial_item_name
            initial_param['bullet_point'] = initial_item_name
            initial_param['purchaseo_seller_id'] = item_info['seller']
            initial_param['quantity'] = 1

            price_setting = AmazonFeedPriceSettings.objects.get(author=request.user)

            v1 = item_info['bid_or_buy']
            v2 = item_info['current_price']
            value = v1 if v1 != '' else v2

            try:
                initial_param['current_price'] = 0
                initial_param['current_price'] = int(value)
                standard_price = max(
                    price_setting.default_minimum_item_price,
                    int(int(value) * price_setting.margin_new + 0.5))
                initial_param['standard_price'] = standard_price
            except Exception as e:
                pass

            try:
                initial_param['bid_or_buy'] = 0
                initial_param['bid_or_buy'] = int(item_info['bid_or_buy'])
            except Exception as e:
                pass

            # スクレイピングからパラメータ
            params['images'] = item_info['images']
            if (item_info['condition'] !=''):
                initial_param['condition_type'] = RichsUtils.yahoo_to_amazon_condition(item_info['condition'])
                initial_param['condition_note'] = item_info['condition']
            # デフォルト情報
            try:
                obj=AmazonDefaultSettings.objects.get(author=request.user)
                initial_param['part_number'] = obj.part_number
                initial_param['fulfillment_latency'] = obj.fulfillment_latency
                if (item_info['condition'] == ''):
                    initial_param['condition_type'] = obj.condition_type
                    initial_param['condition_note'] = obj.condition_note
                # ポイントの設定 (新規出品)
                if obj.new_item_points is not None:
                    initial_param['standard_price_points'] = obj.new_item_points
                else:
                    initial_param['standard_price_points'] = obj.standard_price_points
            except AmazonDefaultSettings.DoesNotExist:
                pass

            form = FeedNewForm(initial=initial_param)
        else:
            # 例外ケース
            form = FeedNewForm()

        # プルダウンの生成
        form.fields['manufacturer'].widget = forms.Select(choices =  ((e.brand_name, e.brand_name) for e in AmazonBrand.objects.filter(author=request.user)) )
        form.fields['category'].widget = forms.Select(choices = ((f.value, f.name) for f in AmazonParentCategoryUser.objects.filter(author=request.user)) )
        category = AmazonParentCategoryUser.objects.filter(author=request.user).first()
        if category != None:
            form.fields['recommended_browse_nodes'].widget = forms.Select(choices = ((g.value, g.name) for g in   settings_amazon_views.get_child_user_model_class(category.value).objects.filter(author=request.user)) )

        params['form'] = form

        return render(request, 'yahoo/feed_amazon_new.html', params)


@login_required
def feed_amazon_offer(request):

    params ={}
    if (request.method == 'POST'):

        if YahooToAmazonItem.objects.filter(author=request.user).count() >= request.user.max_items:
            params['error_message'] = '商品登録件数を超えているため、登録することができません。'
            return render(request, 'yahoo/close.html', params)

        form = FeedOfferForm(request.POST, instance=YahooToAmazonItem())
        if form.is_valid():

            count=YahooToAmazonItem.objects.filter(Q(author=request.user) &  (Q(item_sku=form.instance.item_sku) | Q(current_purchase_item_id=form.instance.item_sku))  ).count()
            if (count > 0):
                params['error_message'] = '既に登録済みの商品であるため登録できません。'
                return render(request, 'yahoo/close.html', params)

            item_info = request.session['new_feed_item_info']
            # 画像の保存処理
            client = AmazonScraper(RichsUtils.get_ip_address(request.user))
            form.instance.main_image_url = RichsUtils.download_to_yahoo_folder(client, form.instance.main_image_url, request.user)
            form.instance.feed_type = 1
            form.instance.author = request.user
            form.instance.record_type = 0
            form.instance.item_name = item_info['title'] # 引き継ぐべきか？
            form.instance.current_purchase_seller_id = form.instance.purchaseo_seller_id = item_info['seller'] #引き継ぐべきか？
            form.instance.purchase_item_id = form.instance.current_purchase_item_id = form.instance.item_sku
            form.instance.purchase_quantity = form.instance.current_purchase_quantity = form.instance.quantity
            form.instance.purchase_fulfillment_latency = form.instance.current_purchase_fulfillment_latency = form.instance.fulfillment_latency
            form.instance.csv_flag=0
            #v1 = request.POST.get('bid_or_buy')
            #v2 = request.POST.get('current_price')
            v1 = item_info['bid_or_buy']
            v2 = item_info['current_price']
            form.instance.purchase_price = form.instance.current_purchase_price = int(v1 if v1 != '' else v2)
            amazon_price = -1
            if (form.instance.condition_type == 'New'):
                tmp = request.POST.get('amazon_price_new')
                if (RichsUtils.is_valid_str(tmp)):
                    amazon_price=int(tmp)
            else:
                tmp = request.POST.get('amazon_price_old')
                if (RichsUtils.is_valid_str(tmp)):
                    amazon_price=int(tmp)
                else:
                    tmp = request.POST.get('amazon_price_new')
                    if (RichsUtils.is_valid_str(tmp)):
                        amazon_price=int(tmp)
            form.instance.amazon_price = amazon_price
            form.instance.update_fulfillment_latency_request = False
            form.instance.update_quantity_request = False
            form.instance.research_request = False
            form.instance.record_type = 0
            form.save()
        else:
            print(form.errors)
            params['error_message'] = 'データにエラーがあります。'
            return render(request, 'yahoo/close.html', params)

        params['message'] = "登録が完了しました。"
        return render(request, 'yahoo/close.html', params)

    else:

        initial_param = {}
        if 'new_feed_item_info' in request.session:
            item_info = request.session['new_feed_item_info']
            initial_param['item_sku'] = item_info['auction_id']
            initial_param['purchaseo_seller_id'] = item_info['seller']

            count=YahooToAmazonItem.objects.filter(Q(author=request.user) & (Q(item_sku=item_info['auction_id']) | Q(current_purchase_item_id=item_info['auction_id']))   ).count()
            if (count > 0):
                params['error_message'] = '既に登録済みの商品であるため登録できません。'
                return render(request, 'yahoo/close.html', params)

            price_setting = AmazonFeedPriceSettings.objects.get(author=request.user)

            v1 = item_info['bid_or_buy']
            v2 = item_info['current_price']
            value = v1 if v1 != '' else v2

            try:
                initial_param['current_price'] = 0
                initial_param['current_price'] = int(value)
                initial_param['standard_price'] = int(int(value) * price_setting.margin_offer + 0.5)
            except Exception as e:
                print(e)
                pass
            try:
                initial_param['bid_or_buy'] = 0
                initial_param['bid_or_buy'] = int(item_info['bid_or_buy'])
            except Exception as e:
                pass

        initial_param['external_product_id'] = request.GET.get('asin')
        initial_param['main_image_url'] = request.GET.get('image')
        initial_param['quantity'] = 1


        if (item_info['condition'] !=''):
            initial_param['condition_type'] = RichsUtils.yahoo_to_amazon_condition(item_info['condition'])
            initial_param['condition_note'] = item_info['condition']
            #initial_param['fulfillment_latency'] = int(item_info['fulfillment_latency'])
        # アマゾンの価格
        initial_param['amazon_price_new'] = request.GET.get('price_new')
        initial_param['amazon_price_used'] = request.GET.get('price_old')
        try:
            obj=AmazonDefaultSettings.objects.get(author=request.user)
            if (item_info['condition'] ==''):
                initial_param['condition_type'] = obj.condition_type
                initial_param['condition_note'] = obj.condition_note
            initial_param['part_number'] = obj.part_number
            initial_param['fulfillment_latency'] = obj.fulfillment_latency
            # ポイントの設定 (相乗り出品)
            if obj.ride_item_points is not None:
                initial_param['standard_price_points'] = obj.ride_item_points
            else:
                initial_param['standard_price_points'] = obj.standard_price_points
        except AmazonDefaultSettings.DoesNotExist:
            pass

        form = FeedOfferForm(initial=initial_param)
        form.fields['external_product_id_type'].widget = forms.Select(choices = (('ASIN','ASIN'),))
        params['form']=form

        return render(request, 'yahoo/feed_amazon_offer.html', params)


# 新規CSVファイルを出力のメイン処理部分
def _export_amazon_new_csv(csv_format, y2a_items, user):
    format = csv_format
    list = y2a_items
    if len(list) <= 0:
        return

    url_base = settings.RICHS_PROTOCOL + '://' + settings.RICHS_FQDN + settings.RICHS_URL_IMAGE + '/yahoo/' + user.username + '/'
    # テンプレートのCSVを読み込みヘッダ部分を書き出し
    out_folder=settings.RICHS_FOLDER_CSV_OUTPUT + '/' + user.username
    if (os.path.isdir(out_folder) == False):
        os.makedirs(out_folder)

    csv_file_name = format.format + str(datetime.now().timestamp()).replace('.','') + '.csv'
    csv_file_path = out_folder + '/' + csv_file_name

    csv_tpl = settings.RICHS_FOLDER_CSV_TEMPLATE + '/' + format.format + '.csv'

    # ファイル読み込み
    with codecs.open(csv_tpl, 'r', 'cp932') as fin, \
            codecs.open(csv_file_path, 'w', 'cp932', 'ignore') as fout:

        for line in fin:
            fout.write(line)
        size=len(list)
        print(size)
        for i, e in enumerate(list):
            cols = [''] * format.fields
            if (format.feed_product_type > -1 and RichsUtils.is_valid_str(e.feed_product_type)):
                cols[format.feed_product_type] =  '"' + e.feed_product_type + '"'
            if (format.item_sku > -1 and RichsUtils.is_valid_str(e.item_sku)):
                cols[format.item_sku] =  '"' + e.item_sku + '"'
            if (format.brand_name > -1 and RichsUtils.is_valid_str(e.brand_name)):
                cols[format.brand_name] =  '"' + e.brand_name + '"'
            if (format.item_name > -1  and RichsUtils.is_valid_str(e.item_name)):
                cols[format.item_name] =  '"' + e.item_name + '"'
            if (format.external_product_id > -1  and RichsUtils.is_valid_str(e.external_product_id)):
                cols[format.external_product_id] =  '"' + e.external_product_id + '"'
            if (format.external_product_id_type > -1  and RichsUtils.is_valid_str(e.external_product_id_type)):
                cols[format.external_product_id_type] =  '"' + e.external_product_id_type + '"'
            if (format.manufacturer > -1  and RichsUtils.is_valid_str(e.manufacturer)):
                cols[format.manufacturer] =  '"' + e.manufacturer  + '"'

            print('----')
            print(format.feed_product_type)
            print(format.feed_product_type > -1)
            print(RichsUtils.is_valid_str(e.feed_product_type))
            print(e.feed_product_type)

            if (format.recommended_browse_nodes > -1  and RichsUtils.is_valid_str(e.recommended_browse_nodes)):
                cols[format.recommended_browse_nodes] =  '"' + e.recommended_browse_nodes + '"'
            if (format.quantity > -1  and e.quantity != None):
                cols[format.quantity] =  str(e.quantity)
            if (format.standard_price > -1  and e.standard_price != None):
                cols[format.standard_price] =  str(e.standard_price)
            if (format.main_image_url > -1  and RichsUtils.is_valid_str(e.main_image_url)):
                cols[format.main_image_url] =  '"' + url_base + e.main_image_url + '"'
            if (format.part_number > -1  and RichsUtils.is_valid_str(e.part_number)):
                cols[format.part_number] =  '"' + e.part_number + '"'

            if (format.condition_type > -1  and RichsUtils.is_valid_str(e.condition_type)):
                cols[format.condition_type] =  '"' + e.condition_type + '"'

            if (format.condition_note > -1  and RichsUtils.is_valid_str(e.condition_note)):
                cols[format.condition_note] =  '"' + e.condition_note + '"'
            if (format.product_description > -1  and RichsUtils.is_valid_str(e.product_description)):
                cols[format.product_description] =  '"' + e.product_description + '"'
            if (format.bullet_point > -1  and RichsUtils.is_valid_str(e.bullet_point)):
                cols[format.bullet_point] =  '"' + e.bullet_point + '"'
            if (format.generic_keywords > -1  and RichsUtils.is_valid_str(e.generic_keywords)):
                cols[format.generic_keywords] =  '"' + e.generic_keywords + '"'
            if (format.other_image_url1 > -1  and RichsUtils.is_valid_str(e.other_image_url1)):
                cols[format.other_image_url1] =  '"' + url_base + e.other_image_url1 + '"'
            if (format.other_image_url2 > -1  and RichsUtils.is_valid_str(e.other_image_url2)):
                cols[format.other_image_url2] =  '"' + url_base + e.other_image_url2 + '"'
            if (format.other_image_url3 > -1  and RichsUtils.is_valid_str(e.other_image_url3)):
                cols[format.other_image_url3] =  '"' + url_base + e.other_image_url3 + '"'
            if (format.fulfillment_latency > -1  and e.fulfillment_latency != None):
                cols[format.fulfillment_latency] =  str(e.fulfillment_latency)
            if (format.standard_price_points > -1  and e.standard_price_points != None):
                cols[format.standard_price_points] =  str(e.standard_price_points)
            if (format.is_adult_product > -1):
                # 固定埋め込み
                cols[format.is_adult_product] = '"false"'

            cols_str = ''
            tab_write_flag = False
            for col in cols:
                if tab_write_flag:
                    cols_str = cols_str + "\t"
                else:
                    tab_write_flag = True
                cols_str  = cols_str  + col
            try:
                fout.write(cols_str)
                fout.write("\n")
                e.csv_flag =1
                e.save()
            except:
                print('CSV出力処理中にエラーが発生したため、該当レコードをスキップします。')
                print(traceback.format_exc())

    # DB書き込み
    YahooToAmazonCSV.objects.create(file_name=csv_file_name, feed_type=0, author=user)



# 新規CSVファイルを出力
@login_required
def export_amazon_new_csv(request):
    params = {}
    if (request.method == 'POST'):
        do_post = False
        ids = request.POST.getlist('ids')
        is_delete = True if 'delete' in request.POST  else False
        if is_delete:
            do_post = True
            if ids:
                YahooToAmazonItem.objects.filter(id__in=ids, author=request.user).delete()
                params['message'] = "削除完了"
                params['message_detail'] = "削除が完了しました。"

        if not do_post:
            do_post = True
            for format in CSVFormat.objects.all():
                output_all = 'output_all' in request.POST
                if output_all:
                    list = YahooToAmazonItem.objects.filter(format=format.format,
                        author=request.user, feed_type=0, csv_flag=0)
                else:
                    ids = ids if ids else []
                    list = YahooToAmazonItem.objects.filter(id__in=ids, format=format.format,
                        author=request.user, feed_type=0, csv_flag=0)
                if len(list) > 0:
                    _export_amazon_new_csv(format, list, request.user)
                    params['success'] = True
                    params['message'] = "出力完了"
                    params['message_detail'] = "CSV出力が完了しました。"

    # GET/POST共通
    items = YahooToAmazonItem.objects.filter(author=request.user, csv_flag =0, feed_type=0)
    for i, item in enumerate(items):
        item.local_id = i + 1
    params['items'] = items
    params['url_item'] =  settings.RICHS_PROTOCOL + '://' + settings.RICHS_FQDN + settings.RICHS_URL_IMAGE + '/yahoo/' + request.user.username
    return render(request, 'yahoo/export_amazon_new_csv.html', params)




# CSVを出力する
def export_amazon_offer_csv_internal(list, user):

    if len(list) <= 0:
        return

    url_base = settings.RICHS_PROTOCOL + '://' + settings.RICHS_FQDN + settings.RICHS_URL_IMAGE + '/yahoo/' + user.username + '/'

    # テンプレートのCSVを読み込みヘッダ部分を書き出し
    out_folder=settings.RICHS_FOLDER_CSV_OUTPUT + '/' + user.username
    if (os.path.isdir(out_folder) == False):
        os.makedirs(out_folder)

    csv_file_name = str(datetime.now().timestamp()).replace('.','') + '.csv'
    csv_file_path = out_folder + '/' + csv_file_name

    csv_tpl = settings.RICHS_FOLDER_CSV_TEMPLATE + '/' + 'offer.csv'

    # ファイル読み込み
    fin  = codecs.open(csv_tpl, 'r', 'cp932')
    fout = codecs.open(csv_file_path, 'w', 'cp932', 'ignore')

    for line in fin:
        fout.write(line)
    fin.close()
    size=len(list)
    print(size)
    for i, e in enumerate(list):
        try:
            cols = [''] * 27
            cols[0] =  e.item_sku
            cols[1] =  str(e.standard_price)
            cols[2] =  str(e.standard_price_points)  if e.standard_price_points != None else ''
            cols[3] =  str(e.quantity)
            cols[4] =  e.external_product_id
            cols[5] =  e.external_product_id_type
            cols[6] =  e.condition_type
            cols[7] =  RichsUtils.to_amazon_csv_column(e.condition_note)
            cols[15] = str(e.fulfillment_latency)
            cols_str = ''
            tab_write_flag = False
            for col in cols:
                if tab_write_flag:
                    cols_str = cols_str + "\t"
                else:
                    tab_write_flag = True
                cols_str  = cols_str  + col

            fout.write(cols_str)
            fout.write("\n")
            e.csv_flag =1
            e.save()
        except:
            print('CSV出力処理中にエラーが発生したため、該当レコードをスキップします。')
            print(traceback.format_exc())

    fout.close()

    # DB書き込み
    YahooToAmazonCSV.objects.create(file_name=csv_file_name, feed_type=1, author=user)

@login_required
def export_amazon_offer_csv(request):
    params = {}
    if (request.method == 'POST'):
        do_post = False
        ids = request.POST.getlist('ids')
        is_delete = True if 'delete' in request.POST  else False
        if is_delete:
            do_post = True
            if ids:
                YahooToAmazonItem.objects.filter(id__in=ids, author=request.user).delete()
                params['message'] = "削除完了"
                params['message_detail'] = "削除が完了しました。"

        if not do_post:
            do_post = True
            output_all = 'output_all' in request.POST
            if output_all:
                list = YahooToAmazonItem.objects.filter(
                    author=request.user, feed_type=1, csv_flag=0)
            else:
                ids = ids if ids else []
                list = YahooToAmazonItem.objects.filter(id__in=ids,
                    author=request.user, feed_type=1, csv_flag=0)
            if len(list) > 0:
                export_amazon_offer_csv_internal(list, request.user)
                # DB書き込み
                params['success'] = True
                params['message'] = "出力完了"
                params['message_detail'] = "CSV出力が完了しました。"

    # GET/POST共通
    items = YahooToAmazonItem.objects.filter(author=request.user, csv_flag =0, feed_type=1)
    for i, item in enumerate(items):
        item.local_id = i + 1
    params['items'] = items
    params['url_item'] =  settings.RICHS_PROTOCOL + '://' + settings.RICHS_FQDN + settings.RICHS_URL_IMAGE + '/yahoo/' + request.user.username
    return render(request, 'yahoo/export_amazon_offer_csv.html', params)


def _get_latest_item2csv(user):
    # この画面にアクセスした時点で更新
    try:
        item2csv = ItemCandidateToCsv.objects.get(owner=user)
    except:
        max_item_per_day = OverrideConstantValue.get_value('EXPORT_CANDIDATE_ITEM_PER_DAY', 0, int)
        item2csv = ItemCandidateToCsv.objects.create(owner=user, max_output=max_item_per_day)
    item2csv.daily_update(now=timezone.datetime.now())
    return item2csv


def _convert_candidate_to_formal_item(candidates):
    ''' 候補アイテムを正式アイテムへと変換します '''
    items = []
    for candidate in candidates:
        # 既存アイテムがある場合はそのアイテムはインポートしない
        sku = candidate.item_sku
        c = YahooToAmazonItem.objects.filter(
            (Q(item_sku=sku)|Q(current_purchase_item_id=sku)) & Q(author=candidate.author)).count()
        if c > 0:
            candidate.delete_file()
            continue
        item = YahooToAmazonItem.objects.create(
            feed_type=candidate.feed_type,
            item_sku=candidate.item_sku,
            item_name=candidate.item_name,
            external_product_id=candidate.external_product_id,
            external_product_id_type=candidate.external_product_id_type,
            brand_name=candidate.brand_name,
            manufacturer=candidate.manufacturer,
            feed_product_type=candidate.feed_product_type,
            part_number=candidate.part_number,
            product_description=candidate.product_description,
            bullet_point=candidate.bullet_point,
            model=candidate.model,
            quantity=candidate.quantity,
            fulfillment_latency=candidate.fulfillment_latency,
            condition_type=candidate.condition_type,
            standard_price=candidate.standard_price,
            standard_price_points=candidate.standard_price_points,
            condition_note=candidate.condition_note,
            item_weight=candidate.item_weight,
            item_weight_unit_of_measure=candidate.item_weight_unit_of_measure,
            item_height=candidate.item_height,
            item_length=candidate.item_length,
            item_width=candidate.item_width,
            item_length_unit_of_measure=candidate.item_length_unit_of_measure,
            recommended_browse_nodes=candidate.recommended_browse_nodes,
            generic_keywords=candidate.generic_keywords,
            main_image_url=candidate.main_image_url,
            other_image_url1=candidate.other_image_url1,
            other_image_url2=candidate.other_image_url2,
            other_image_url3=candidate.other_image_url3,
            csv_flag=candidate.csv_flag,
            format=candidate.format,
            category=candidate.category,
            purchaseo_seller_id=candidate.purchaseo_seller_id,
            purchase_item_id=candidate.purchase_item_id,
            purchase_quantity=candidate.purchase_quantity,
            purchase_fulfillment_latency=candidate.purchase_fulfillment_latency,
            purchase_price=candidate.purchase_price,
            purchase_similarity=candidate.purchase_similarity,
            current_purchase_seller_id=candidate.current_purchase_seller_id,
            current_purchase_item_id=candidate.current_purchase_item_id,
            current_purchase_quantity=candidate.current_purchase_quantity,
            current_purchase_fulfillment_latency=candidate.current_purchase_fulfillment_latency,
            current_purchase_price=candidate.current_purchase_price,
            current_similarity=candidate.current_similarity,
            amazon_price=candidate.amazon_price,
            update_fulfillment_latency_request=candidate.update_fulfillment_latency_request,
            research_request=candidate.research_request,
            update_quantity_request=candidate.update_quantity_request,
            record_type=candidate.record_type,
            author=candidate.author)
        items.append(item)

    # 候補は全削除
    for candidate in candidates:
        candidate.delete()
    return items


# 候補を出力
def _export_amazon_new_csv_from_candidate(user, ids=None, item2csv=None):
    if item2csv is None:
        item2csv = _get_latest_item2csv(user)

    # 実際には1つのみ
    fmts = CSVFormat.objects.all()
    if len(fmts) <= 0:
        return (False, "出力失敗", "CSV出力のためのフォーマットが見つかりません")

    fmt = fmts[0]
    # 残数0
    available_export_item = item2csv.max_output - item2csv.today_output
    if available_export_item <= 0:
        return (False, "出力失敗", "本日の出品可能上限に達しています")

    importable = user.max_items - YahooToAmazonItem.objects.filter(author=user).count()
    if importable <= 0:
        return (False, "出力失敗", '商品登録件数を超えているため、登録することができません。')

    if available_export_item > importable:
        available_export_item = importable

    if ids is not None:
        candidates = YahooToAmazonItemCandidate.objects.filter(
            id__in=ids, author=user).order_by('updated_date').reverse()[:available_export_item]
    else:
        candidates = YahooToAmazonItemCandidate.objects.filter(
            author=user).order_by('updated_date').reverse()[:available_export_item]

    if len(candidates) <= 0:
        return (False, "出力失敗", '出品候補がありません。')

    items = _convert_candidate_to_formal_item(candidates)
    if len(items) <= 0:
        return (False, "出力失敗", '全ての出力候補はすでに出品されています。')

    _export_amazon_new_csv(fmt, items, user)
    item2csv.today_output += len(items)
    item2csv.save()
    if item2csv.today_output >= item2csv.max_output:
        return (True, '出力完了', "CSV出力が完了しました。 出品上限に達しました。")
    else:
        return (True, '出力完了', "CSV出力が完了しました。")


def _export_amazon_new_csv_from_candidate_post(request, params):
    item2csv = params['item2csv']
    ids = request.POST.getlist('ids')
    is_delete = True if 'delete' in request.POST  else False
    if is_delete:
        if not ids:
            return
        targets = YahooToAmazonItemCandidate.objects.filter(id__in=ids)
        for target in targets:
            target.delete_file()
        targets.delete()
        params['message'] = "削除完了"
        params['message_detail'] = "削除が完了しました。"
        return

    if 'output_all' in request.POST:
        # 全て出力
        ids = None
    else:
        # 一部出力の場合はidがないと出力しない
        if not ids:
            return

    (succ, msg, detail) = _export_amazon_new_csv_from_candidate(request.user, ids, item2csv)
    params['success'] = succ
    params['message'] = msg
    params['message_detail'] = detail


# 新規CSVファイルを相乗り検索のアイテムをベースに出力
@login_required
def export_amazon_new_csv_from_candidate(request):
    item2csv = _get_latest_item2csv(request.user)
    params = {}
    params['item2csv'] = item2csv
    if (request.method == 'POST'):
        _export_amazon_new_csv_from_candidate_post(request, params)

    # GET/POST共通
    # items = YahooToAmazonItemCandidate.objects.filter(
    #     author=request.user, csv_flag=0, feed_type=0).order_by('updated_date').reverse()[:1000]tanaka
    items = YahooToAmazonItemCandidate.objects.filter(
        author=request.user, csv_flag=0, feed_type=0).reverse()[:1000]
    for i, item in enumerate(items):
        item.local_id = i + 1
    params['items'] = items
    params['url_item'] =  settings.RICHS_PROTOCOL + '://' + settings.RICHS_FQDN + settings.RICHS_URL_IMAGE + '/yahoo/' + request.user.username
    return render(request, 'yahoo/export_amazon_new_csv_from_candidate.html', params)



# ダウンロード
@login_required
def download_amazon_csv(request):

    params = {}

    new_feed_csv = YahooToAmazonCSV.objects.filter(author=request.user, feed_type=0).order_by('-created_date')
    for i, csv in enumerate(new_feed_csv):
        csv.local_id = i + 1

    offer_feed_csv = YahooToAmazonCSV.objects.filter(author=request.user, feed_type=1).order_by('-created_date')
    for i, csv in enumerate(offer_feed_csv):
        csv.local_id = i + 1

    params['image_base'] = settings.RICHS_PROTOCOL + '://' + settings.RICHS_FQDN + '/output/' + request.user.username
    params['new_feed_csv'] = new_feed_csv
    params['offer_feed_csv'] = offer_feed_csv

    return render(request, 'yahoo/download_amazon_csv.html', params)

# 新規登録の編集
@login_required
def edit_amazon_new(request):
    params={}
    if (request.method == 'POST'):
        form = FeedNewForm(request.POST, instance=YahooToAmazonItem())
        if form.is_valid():
            try:
                e = YahooToAmazonItem.objects.get(author=request.user, item_sku=form.instance.item_sku)

                current_image_urls = set([
                    e.main_image_url, e.other_image_url1,
                    e.other_image_url2, e.other_image_url3
                ])

                e.author = request.user
                e.external_product_id_type = form.instance.external_product_id_type
                e.external_product_id = form.instance.external_product_id
                e.item_name = form.instance.item_name
                e.manufacturer = form.instance.manufacturer
                e.brand_name = form.instance.brand_name
                e.part_number = form.instance.part_number
                e.condition_type = form.instance.condition_type
                e.condition_note = form.instance.condition_note
                e.product_description = form.instance.product_description
                e.bullet_point = form.instance.bullet_point
                e.generic_keywords = form.instance.generic_keywords
                e.category = form.instance.category
                e.recommended_browse_nodes = form.instance.recommended_browse_nodes
                e.purchase_quantity = e.current_purchase_quantity = form.instance.quantity
                e.purchase_fulfillment_latency = e.current_purchase_fulfillment_latency = e.fulfillment_latency = form.instance.fulfillment_latency
                e.standard_price = form.instance.standard_price
                e.standard_price_points = form.instance.standard_price_points
                e.quantity = form.instance.quantity
                e.update_fulfillment_latency_request = False
                e.update_quantity_request = False
                e.research_request = False
                e.record_type = 0

                if (form.instance.external_product_id == None or form.instance.external_product_id == ''):
                    e.external_product_id_type= ''

                for e2 in settings_amazon_views.get_child_user_model_class(form.instance.category).objects.filter(author=request.user, value=form.instance.recommended_browse_nodes):
                    e.format = e2.format
                    e.feed_product_type = e2.feed_product_type

                # 画像の保存
                client = YahooAuctionIdScraper(RichsUtils.get_ip_address(request.user))

                # 画像の保存
                if (form.instance.main_image_url != None and form.instance.main_image_url != ''):
                    if (form.instance.main_image_url.startswith('http')):
                        e.main_image_url = RichsUtils.download_to_yahoo_folder(client, form.instance.main_image_url, request.user)
                    else:
                        if ('main_image_file' in request.FILES):
                            f = request.FILES['main_image_file']
                            e.main_image_url = RichsUtils.handle_uploaded_file_to_yahoo_foler(f, request.user)
                        elif form.instance.main_image_url in current_image_urls:
                            e.main_image_url = form.instance.main_image_url

                if (form.instance.other_image_url1 != None and form.instance.other_image_url1 != ''):
                    if (form.instance.other_image_url1.startswith('http')):
                        e.other_image_url1 = RichsUtils.download_to_yahoo_folder(client, form.instance.other_image_url1, request.user)
                    else:
                        if ('other_image_file1' in request.FILES):
                            f = request.FILES['other_image_file1']
                            e.other_image_url1 = RichsUtils.handle_uploaded_file_to_yahoo_foler(f, request.user)
                        elif form.instance.other_image_url1 in current_image_urls:
                            e.other_image_url1 = form.instance.other_image_url1
                else:
                    e.other_image_url1 = None
                    # tanaka

                if (form.instance.other_image_url2 != None and form.instance.other_image_url2 != ''):
                    if (form.instance.other_image_url2.startswith('http')):
                        e.other_image_url2 = RichsUtils.download_to_yahoo_folder(client, form.instance.other_image_url2, request.user)
                    else:
                        if ('other_image_file2' in request.FILES):
                            f = request.FILES['other_image_file2']
                            e.other_image_url2 = RichsUtils.handle_uploaded_file_to_yahoo_foler(f, request.user)
                        elif form.instance.other_image_url2 in current_image_urls:
                            e.other_image_url2 = form.instance.other_image_url2
                else:
                    e.other_image_url2 = None

                if (form.instance.other_image_url3 != None and form.instance.other_image_url3 != ''):
                    if (form.instance.other_image_url3.startswith('http')):
                        e.other_image_url3 = RichsUtils.download_to_yahoo_folder(client, form.instance.other_image_url3, request.user)
                    else:
                        if ('other_image_file3' in request.FILES):
                            f = request.FILES['other_image_file3']
                            e.other_image_url3 = RichsUtils.handle_uploaded_file_to_yahoo_foler(f, request.user)
                        elif form.instance.other_image_url3 in current_image_urls:
                            e.other_image_url3 = form.instance.other_image_url3
                else:
                    e.other_image_url3 = None

                e.save()

            except YahooToAmazonItem.DoesNotExist:
                params['error_message'] = '該当データは、存在しません。'
                return render(request, 'yahoo/close.html', params)

        else:
            print(form.errors)
            params['error_message'] = 'データにエラーがあります。'
            return render(request, 'yahoo/close.html', params)

        params['message'] = "登録が完了しました。"
        return render(request, 'yahoo/close.html', params)

    else:
        # データ検索
        item_sku=request.GET.get('item_sku')
        try:
            e = YahooToAmazonItem.objects.get(author=request.user, item_sku=item_sku)
            form  = FeedNewForm(instance=e)

            images = [''] * 4
            images[0] = e.main_image_url
            images[1] = e.other_image_url1
            images[2] = e.other_image_url2
            images[3] = e.other_image_url3
            params['base_url'] = RichsUtils.get_yahoo_image_base_url(request.user)
            params['images'] = images

            # プルダウンの生成
            form.fields['manufacturer'].widget = forms.Select(choices =  ((e.brand_name, e.brand_name) for e in AmazonBrand.objects.filter(author=request.user)) )
            form.fields['category'].widget = forms.Select(choices = ((f.value, f.name) for f in AmazonParentCategoryUser.objects.filter(author=request.user)) )
            category = AmazonParentCategoryUser.objects.filter(author=request.user).first()
            if category != None:
                form.fields['recommended_browse_nodes'].widget = forms.Select(choices = ((g.value, g.name) for g in settings_amazon_views.get_child_user_model_class(category.value).objects.filter(author=request.user)))
            params['form'] = form
        except YahooToAmazonItem.DoesNotExist:
            params['error_message'] = '該当データは、存在しません。'
            return render(request, 'yahoo/close.html', params)

        return render(request, 'yahoo/edit_amazon_new.html', params)


# 相乗りからの新規登録の編集
@login_required
def edit_amazon_new_candidate(request):
    params={}
    if (request.method == 'POST'):
        form = FeedNewForm(request.POST, instance=YahooToAmazonItemCandidate())
        if form.is_valid():
            try:
                e = YahooToAmazonItemCandidate.objects.get(author=request.user, item_sku=form.instance.item_sku)

                current_image_urls = set([
                    e.main_image_url, e.other_image_url1,
                    e.other_image_url2, e.other_image_url3
                ])

                e.author = request.user
                e.external_product_id_type = form.instance.external_product_id_type
                e.external_product_id = form.instance.external_product_id
                e.item_name = form.instance.item_name
                e.manufacturer = form.instance.manufacturer
                e.brand_name = form.instance.brand_name
                e.part_number = form.instance.part_number
                e.condition_type = form.instance.condition_type
                e.condition_note = form.instance.condition_note
                e.product_description = form.instance.product_description
                e.bullet_point = form.instance.bullet_point
                e.generic_keywords = form.instance.generic_keywords
                e.category = form.instance.category
                e.recommended_browse_nodes = form.instance.recommended_browse_nodes
                e.purchase_quantity = e.current_purchase_quantity = form.instance.quantity
                e.purchase_fulfillment_latency = e.current_purchase_fulfillment_latency = e.fulfillment_latency = form.instance.fulfillment_latency
                e.standard_price = form.instance.standard_price
                e.standard_price_points = form.instance.standard_price_points
                e.quantity = form.instance.quantity
                e.update_fulfillment_latency_request = False
                e.update_quantity_request = False
                e.research_request = False
                e.record_type = 0

                if (form.instance.external_product_id == None or form.instance.external_product_id == ''):
                    e.external_product_id_type= ''

                for e2 in settings_amazon_views.get_child_user_model_class(form.instance.category).objects.filter(author=request.user, value=form.instance.recommended_browse_nodes):
                    e.format = e2.format
                    e.feed_product_type = e2.feed_product_type

                # 画像の保存
                client = YahooAuctionIdScraper(RichsUtils.get_ip_address(request.user))

                # 画像の保存
                if (form.instance.main_image_url != None and form.instance.main_image_url != ''):
                    if (form.instance.main_image_url.startswith('http')):
                        e.main_image_url = RichsUtils.download_to_yahoo_folder(client, form.instance.main_image_url, request.user)
                    else:
                        if ('main_image_file' in request.FILES):
                            f = request.FILES['main_image_file']
                            e.main_image_url = RichsUtils.handle_uploaded_file_to_yahoo_foler(f, request.user)
                        elif form.instance.main_image_url in current_image_urls:
                            e.main_image_url = form.instance.main_image_url

                if (form.instance.other_image_url1 != None and form.instance.other_image_url1 != ''):
                    if (form.instance.other_image_url1.startswith('http')):
                        e.other_image_url1 = RichsUtils.download_to_yahoo_folder(client, form.instance.other_image_url1, request.user)
                    else:
                        if ('other_image_file1' in request.FILES):
                            f = request.FILES['other_image_file1']
                            e.other_image_url1 = RichsUtils.handle_uploaded_file_to_yahoo_foler(f, request.user)
                        elif form.instance.other_image_url1 in current_image_urls:
                            e.other_image_url1 = form.instance.other_image_url1
                else:
                    e.other_image_url1 = None

                if (form.instance.other_image_url2 != None and form.instance.other_image_url2 != ''):
                    if (form.instance.other_image_url2.startswith('http')):
                        e.other_image_url2 = RichsUtils.download_to_yahoo_folder(client, form.instance.other_image_url2, request.user)
                    else:
                        if ('other_image_file2' in request.FILES):
                            f = request.FILES['other_image_file2']
                            e.other_image_url2 = RichsUtils.handle_uploaded_file_to_yahoo_foler(f, request.user)
                        elif form.instance.other_image_url2 in current_image_urls:
                            e.other_image_url2 = form.instance.other_image_url2
                else:
                    e.other_image_url2 = None

                if (form.instance.other_image_url3 != None and form.instance.other_image_url3 != ''):
                    if (form.instance.other_image_url3.startswith('http')):
                        e.other_image_url3 = RichsUtils.download_to_yahoo_folder(client, form.instance.other_image_url3, request.user)
                    else:
                        if ('other_image_file3' in request.FILES):
                            f = request.FILES['other_image_file3']
                            e.other_image_url3 = RichsUtils.handle_uploaded_file_to_yahoo_foler(f, request.user)
                        elif form.instance.other_image_url3 in current_image_urls:
                            e.other_image_url3 = form.instance.other_image_url3
                else:
                    e.other_image_url3 = None

                e.save()
                
            except YahooToAmazonItemCandidate.DoesNotExist:
                params['error_message'] = '該当データは、存在しません。'
                return render(request, 'yahoo/close.html', params)

        else:
            print(form.errors)
            params['error_message'] = 'データにエラーがあります。'
            return render(request, 'yahoo/close.html', params)

        params['message'] = "登録が完了しました。"
        return render(request, 'yahoo/close.html', params)

    else:
        # データ検索
        item_sku=request.GET.get('item_sku')
        try:
            e = YahooToAmazonItemCandidate.objects.get(author=request.user, item_sku=item_sku)
            form  = FeedNewForm(instance=e)

            images = [''] * 4
            images[0] = e.main_image_url
            images[1] = e.other_image_url1
            images[2] = e.other_image_url2
            images[3] = e.other_image_url3
            params['base_url'] = RichsUtils.get_yahoo_image_base_url(request.user)
            params['images'] = images

            # プルダウンの生成
            form.fields['manufacturer'].widget = forms.Select(choices =  ((e.brand_name, e.brand_name) for e in AmazonBrand.objects.filter(author=request.user)) )
            form.fields['category'].widget = forms.Select(choices = ((f.value, f.name) for f in AmazonParentCategoryUser.objects.filter(author=request.user)) )
            category = AmazonParentCategoryUser.objects.filter(author=request.user).first()
            if category != None:
                form.fields['recommended_browse_nodes'].widget = forms.Select(choices = ((g.value, g.name) for g in settings_amazon_views.get_child_user_model_class(category.value).objects.filter(author=request.user)))
            params['form'] = form
        except YahooToAmazonItemCandidate.DoesNotExist:
            params['error_message'] = '該当データは、存在しません。'
            return render(request, 'yahoo/close.html', params)

        return render(request, 'yahoo/edit_amazon_new_candidate.html', params)


@login_required
def edit_amazon_offer(request):
    params={}
    if (request.method == 'POST'):
        form = FeedOfferForm(request.POST, instance=YahooToAmazonItem())
        if form.is_valid():
            try:
                e = YahooToAmazonItem.objects.get(author=request.user, item_sku=form.instance.item_sku)
                e.external_product_id_type = form.instance.external_product_id_type
                e.external_product_id = form.instance.external_product_id
                e.condition_type = form.instance.condition_type
                e.condition_note = form.instance.condition_note
                e.standard_price = form.instance.standard_price
                e.standard_price_points = form.instance.standard_price_points
                e.quantity = form.instance.quantity
                e.fulfillment_latency = e.purchase_fulfillment_latency = e.current_purchase_fulfillment_latency = form.instance.fulfillment_latency
                e.save()
            except YahooToAmazonItem.DoesNotExist:
                params['error_message'] = '該当データは、存在しません。'
                return render(request, 'yahoo/close.html', params)
        else:
            print(form.errors)
            params['error_message'] = 'データにエラーがあります。'
            return render(request, 'yahoo/close.html', params)

        params['message'] = "登録が完了しました。"
        return render(request, 'yahoo/close.html', params)

    else:
        item_sku=request.GET.get('item_sku')
        form = FeedOfferForm(instance=YahooToAmazonItem.objects.get(author=request.user, item_sku=item_sku))
        form.fields['external_product_id_type'].widget = forms.Select(choices = (('ASIN','ASIN'),))
        params['form'] = form
        return render(request, 'yahoo/edit_amazon_offer.html', params)


# 内部処理(検索フォーム)
def amazon_offer_research_search_view(request):
    params = {}
    params['form'] = AmazonOfferYahooSearchForm(initial = {
        'amazon_search_type': 0, 'rateing': 90.0 , 'similarity': 0.80, 'search_type': 0, 'istatus': 1, 'is_export_csv': 1
    })
    return render(request, 'yahoo/amazon_offer_research.html', params)


# 内部処理(処理計画)
def amazon_offer_research_loading_view(request, e, user, params=None):
    params = params if params else {}

    if URLSkipRequest.objects.filter(view=11, author=request.user).count() > 0:
        # スキップ要求中
        e.status = 8

    entityList = StopRequest.objects.filter(view = 11,  author = user)
    if (len(entityList) > 0):
        # 停止要求中
        e.status = 9

    now = datetime.now()
    e.now = RichsUtils.timestamp_to_display_string(now)
    e.start_time = RichsUtils.timestamp_to_display_string(e.created_date)
    e.end_time = RichsUtils.timestamp_to_display_string(e.end_date)
    e.duration = RichsUtils.timestamp_duration_to_display_string(e.created_date, e.updated_date)

    params['data'] = e;
    return render(request, 'yahoo/watch_offer_reserch_transaction.html', params)


def _form_to_dict(form):
    ''' convert form to dict '''
    return { k: form[k].value() for k in form.fields.keys() }


def _add_amazon_search_url(request):
    ''' Amazon 検索の URL を後から追加 '''
    watch = OfferReserchWatcher.objects.get(author=request.user, research_type=0)
    if watch.status != 0:
        params = {}
        params['success'] = False
        params['message'] = 'ステータスエラー'
        params['message_detail'] = '現在の状態ではURLを追加できません。'
        return amazon_offer_research_loading_view(request, watch, request.user, params)

    url = AmazonSearchUtils.keyword_to_url(
        request.POST.get('search_type', '0'), request.POST.get('url'))
    (succ, msg) = AmazonSearchUtils.validate(url)
    if not succ:
        params = {}
        params['success'] = False
        params['message'] = 'パラメターエラー'
        params['message_detail'] = msg
        return amazon_offer_research_loading_view(request, watch, request.user, params)

    searches = BackgroundSearchInfo.objects.filter(
        watcher=watch, search_completed=False).order_by('order')
    uncompleted_count = len(searches)
    if uncompleted_count >= 10:
        params = {}
        params['success'] = False
        params['message'] = 'パラメターエラー'
        params['message_detail'] = '未完了のURLは10個以上にはできません。'
        return amazon_offer_research_loading_view(request, watch, request.user, params)

    # 末尾に追加する
    last_info = searches[uncompleted_count - 1]
    last_info.next_url = url
    last_info.save()
    BackgroundSearchInfo.objects.create(
        watcher=watch, url=url, order=last_info.order + 1)
    params = {}
    params['success'] = True
    return amazon_offer_research_loading_view(request, watch, request.user, params)

def _interrupt_amazon_search_url(request):
    ''' Amazon 検索の URL を割り込み '''
    watch = OfferReserchWatcher.objects.get(author=request.user, research_type=0)
    if watch.status != 0:
        params = {}
        params['success'] = False
        params['message'] = 'ステータスエラー'
        params['message_detail'] = '現在の状態ではURLを追加できません。'
        return amazon_offer_research_loading_view(request, watch, request.user, params)

    url = AmazonSearchUtils.keyword_to_url(
        request.POST.get('search_type', '0'), request.POST.get('url'))
    (succ, msg) = AmazonSearchUtils.validate(url)
    if not succ:
        params = {}
        params['success'] = False
        params['message'] = 'パラメターエラー'
        params['message_detail'] = msg
        return amazon_offer_research_loading_view(request, watch, request.user, params)

    searches = BackgroundSearchInfo.objects.filter(
        watcher=watch, search_completed=False).order_by('order')
    uncompleted_count = len(searches)
    if uncompleted_count >= 10:
        params = {}
        params['success'] = False
        params['message'] = 'パラメターエラー'
        params['message_detail'] = '未完了のURLは10個以上にはできません。'
        return amazon_offer_research_loading_view(request, watch, request.user, params)

    URLSkipRequest.objects.create(view = 11,  author = request.user)
    e = OfferReserchWatcher.objects.get(author=request.user, research_type=0)

    # 次に実行予定の情報の実行順と次のURLを取得、退避する
    if searches.count() == 1:
        next_info_order = searches[0].order + 1
        next_info_url = None
    else:
        next_info_order = searches[1].order
        next_info_url = searches[1].url

    # 各情報の順序を1つ後にする
    for current_info in searches:
        if not current_info.order == searches[0].order:
            current_info.order += 1
            current_info.save()

    # 割り込み
    BackgroundSearchInfo.objects.create(
        watcher=watch, url=url, next_url=next_info_url, order=next_info_order)

    params = {}
    params['success'] = True
    return amazon_offer_research_loading_view(request, e, request.user, params)

def amazon_offer_research_post(request):
    ''' amazon offer research with post request. '''

    # check mws api was set
    my_api = RichsUtils.get_mws_api(request.user)
    if my_api == None:
        return HttpResponseRedirect("/settings_amazon/api_settings")

    # 閉じる要求時はDB上の進捗ステータスを削除
    if ('close' in request.POST):
        # 行き違いでStopRequestがある場合残ったままになってしまうので削除する
        StopRequest.objects.filter(view=11, author=request.user).delete()
        URLSkipRequest.objects.filter(view=11, author=request.user).delete()
        OfferReserchWatcher.objects.filter(author=request.user, research_type=0).delete()
        return amazon_offer_research_search_view(request)

    # URLスキップ要求時はDB上にスキップ依頼を発行
    if ('skip' in request.POST):
        URLSkipRequest.objects.create(view = 11,  author = request.user)
        e = OfferReserchWatcher.objects.get(author=request.user, research_type=0)
        return amazon_offer_research_loading_view(request, e, request.user)

    # 停止要求時はDB上に停止依頼を発行
    if ('stop' in request.POST):
        print('停止ボタン')
        stop = StopRequest(view = 11,  author = request.user)
        stop.save();
        e = OfferReserchWatcher.objects.get(author=request.user, research_type=0)
        return amazon_offer_research_loading_view(request, e, request.user)

    # URL追加時はその処理を追加
    if ('addurl' in request.POST):
        return _add_amazon_search_url(request)

    # URL割り込み時はその処理を追加 
    if ('Interrupturl' in request.POST):
        return _interrupt_amazon_search_url(request)

    try:
        # 該当ユーザーの検索情報がすでに存在する場合は以降のオペレーションを実施しない
        # (Redirectで再度GETを要求する)
        e = OfferReserchWatcher.objects.get(author=request.user, research_type=0)
        return HttpResponseRedirect("/yahoo/amazon_offer_research")
    except OfferReserchWatcher.DoesNotExist:
        pass

    # 最大登録数超過
    if YahooToAmazonItem.objects.filter(author=request.user).count() >= request.user.max_items:
        # 超過時は空の完了リクエストを登録することで強制的に完了状態にする
        e = OfferReserchWatcher(research_type = 0, status = 1, total = 0, exclude_asin = 0,
            prime = 0, condition_different = 0, exclude_seller = 0, not_found = 0,
            feed_item = 0, is_over_items=True, end_date=datetime.now(), author = request.user)
        e.save()
        return amazon_offer_research_loading_view(request, e, request.user)


    # 通常の相乗り検索処理
    form = AmazonOfferYahooSearchForm(request.POST)
    search_type = form['amazon_search_type'].value()
    keyword = form['keyword'].value()
    target_urls = [
        AmazonSearchUtils.keyword_to_url(search_type, keyword),
        AmazonSearchUtils.keyword_to_url(search_type, form['extra_keyword1'].value()),
        AmazonSearchUtils.keyword_to_url(search_type, form['extra_keyword2'].value()),
        AmazonSearchUtils.keyword_to_url(search_type, form['extra_keyword3'].value()),
        AmazonSearchUtils.keyword_to_url(search_type, form['extra_keyword4'].value()),
        AmazonSearchUtils.keyword_to_url(search_type, form['extra_keyword5'].value()),
        AmazonSearchUtils.keyword_to_url(search_type, form['extra_keyword6'].value()),
        AmazonSearchUtils.keyword_to_url(search_type, form['extra_keyword7'].value()),
        AmazonSearchUtils.keyword_to_url(search_type, form['extra_keyword8'].value()),
        AmazonSearchUtils.keyword_to_url(search_type, form['extra_keyword9'].value()),
    ]
    if all([ url is None for url in target_urls ]):
        params={}
        params['form'] = form
        params['success'] = False
        params['message'] = 'パラメターエラー'
        params['message_detail'] = '有効なURLが入力されていません。'
        return render(request, 'yahoo/amazon_offer_research.html', params)

    # URLバリデーション
    for (idx, url) in enumerate(target_urls):
        if url is None:
            continue
        (succ, msg) = AmazonSearchUtils.validate(url)
        if not succ:
            params={}
            params['form'] = form
            params['success'] = False
            params['message'] = 'パラメターエラー'
            params['message_detail'] = '{}番目の{}'.format(idx+1, msg)
            return render(request, 'yahoo/amazon_offer_research.html', params)

    # None を削除。 入力順序が欲しいのでバリデーションの後に削除
    target_urls = [ url for url in target_urls if url is not None ]

    # 既にDBに登録されている場合には、削除する。
    entityList = OfferReserchWatcher.objects.filter(author=request.user, research_type=0)
    for entity in entityList:
        entity.delete()

    # 未完了状態のオブジェクトを登録する
    url = target_urls[0]
    e = OfferReserchWatcher.objects.create(
        research_type = 0, status = 0, total = 0, exclude_asin = 0,
        prime = 0, condition_different = 0, exclude_seller = 0, not_found = 0,
        feed_item = 0, is_over_items=False, author = request.user, current_url=url)

    # 複数URL検索用の入力を実施
    url_pairs = zip(target_urls, target_urls[1:] + [None])
    for (order, (current_url, next_url)) in enumerate(url_pairs):
        BackgroundSearchInfo.objects.create(
            watcher=e, url=current_url, next_url=next_url, order=order)

    # 以降の処理では AmazonOfferYahooSearchForm のキーが必要
    # rq ではシリアライザに pickle を利用しており、formはシリアライズできない
    params = _form_to_dict(form)
    # 非同期処理情報をキューに積む
    queue = asynchelpers.get_queue()
    queue.enqueue(amazon_offer_research_entry,
        params=params, url=url, user=request.user)

    return amazon_offer_research_loading_view(request, e, request.user)


# Amazon相乗り商品リサーチ
@login_required
def amazon_offer_research(request):
    if (request.method == 'POST'):
        # POST時はユーザーからの操作要求が発生している
        return amazon_offer_research_post(request)
    else:
        # GETと処理開始後共通
        try:
            e = OfferReserchWatcher.objects.get(author=request.user, research_type=0)
            return amazon_offer_research_loading_view(request, e, request.user)
        except OfferReserchWatcher.DoesNotExist:
            return amazon_offer_research_search_view(request)


@login_required
@require_GET
def amazon_offer_research_progress(request):
    ''' 相乗り検索のページを更新するための情報を取得 '''
    # status code
    # 0:進行中 1:完了 2:完了(CSV出力済み)
    # -1:異常終了 8:スキップ要求中  9:停止要求中
    try:
        watch = OfferReserchWatcher.objects.get(author=request.user, research_type=0)
    except OfferReserchWatcher.DoesNotExist:
        return JsonResponse({ 'exists': False })

    res = model_to_dict(watch)
    if res['status'] == 0:
        # 進行中の場合、割り込みがないかを確認
        if URLSkipRequest.objects.filter(view=11, author=request.user).count() > 0:
            # スキップ要求中
            res['status'] = 8

        if StopRequest.objects.filter(view=11, author=request.user).count() > 0:
            # 停止要求中
            res['status'] = 9

    now = datetime.now()
    res['exists'] = True
    res['now'] = RichsUtils.timestamp_to_display_string(now)
    res['start_time'] = RichsUtils.timestamp_to_display_string(watch.created_date)
    res['end_time'] = RichsUtils.timestamp_to_display_string(watch.end_date)
    res['duration'] = RichsUtils.timestamp_duration_to_display_string(watch.created_date, watch.updated_date)
    res['max_items'] = request.user.max_items
    res['error_info'] = watch.error_message or ''
    res['search_urls'] = []

    # NOTE: feed_count と new_feed_count は確定タイミングでのみ計算
    # 画面に表示する分は画面側で計算している
    searches = BackgroundSearchInfo.objects.filter(watcher=watch).order_by('order')
    for search in searches:
        from_dt = search.start_date
        to_dt = search.end_date if search.end_date else search.updated_date
        if None not in [from_dt, to_dt]:
            # 経過時間を hh:mm:dd の形式に変換
            sec = int((to_dt - from_dt).total_seconds())
            exectime = '{:02}:{:02}:{:02}'.format(
                int(sec/3600), int((sec/60)%60), int(sec%60))
            completeDatetime = search.updated_date.strftime("%Y年%m月%d日\n%H:%M")
            # tanaka
        else:
            # 経過時間は未定義
            exectime = '00:00:00'
            completeDatetime = ""
        res['search_urls'].append({
            'order': search.order,
            'url': search.url,
            'completed': search.search_completed,
            'total_count': search.total_url_count,
            'feed_count': search.feed_count,
            'new_feed_count': search.new_feed_count,
            'exectime': exectime,
            'completeDatetime': completeDatetime,
        })

    return JsonResponse(res)


def _ride_search_config():
    try:
        # ヤフオク特有の条件判断
        return settings.YAHOO_RIDE_SEARCH_CONFIG
    except:
        # 設定がない場合
        return {}


def available_for_purchase(amazon_item, yahoo_item, value, user, price_setting, amazon_image):
    # 購入可能なアイテムと判断された場合は 0 を返す
    try:
        # 商品数超過
        if YahooToAmazonItem.objects.filter(author=user).count() >= user.max_items:
            return -3

        sku = yahoo_item['auction_id']
        c = YahooToAmazonItem.objects.filter(
            (Q(item_sku=sku)|Q(current_purchase_item_id=sku)) & Q( author=user)).count()
        if c > 0:
            # 重複
            return -2

        # オークションのコンディションを取得
        condition_type = RichsUtils.yahoo_to_amazon_condition( yahoo_item['condition'])
        if condition_type == 'ERR':
            # コンディション不一致
            return -1

        # オークションの金額取得
        v1 = yahoo_item['bid_or_buy']
        v2 = yahoo_item['current_price']
        m_price = int(v1 if v1 != '' else v2)

        # コンディションに応じたアマゾンの価格を取得
        a_price = 0
        if condition_type == 'New':
            if (amazon_item['price_new'] != '' and amazon_item['price_new'] != '-1'):
                a_price = int(amazon_item['price_new'])
            elif (amazon_item['price_old'] != '' and amazon_item['price_old'] != '-1'): # 新品がなければ、中古の最低価格
                a_price = int(amazon_item['price_old'])
        else:
            if (amazon_item['price_old'] != '' and amazon_item['price_old'] != '-1'):
                a_price = int(amazon_item['price_old'])
            elif (amazon_item['price_new'] != '' and amazon_item['price_new'] != '-1'): # 中古がなければ、新品の最低価格
                a_price = int(amazon_item['price_new'])

        if a_price == 0:
           # アマゾン金額取得エラー
            return -1

        standard_price = a_price + price_setting.offset_offer_price_url
        diff = standard_price - m_price
        if (diff < price_setting.margin_offer_url):
            # 最低利益を下回っている
            return -1

        conf = _ride_search_config()

        # タイトルが短すぎる場合
        if len(yahoo_item['title']) < conf.get('MINIMUM_TITLE_LENGTH', 0):
            return -4

        # 利益率算出 ::= (Amazon販売額 - Yahoo販売額) / Amazon販売額
        profit_rate = float(standard_price - m_price) / float(standard_price)
        if profit_rate < conf.get('MINIMUM_PROFIT', 0.0):
            return -5

        # 特定の発送元からは仕入れを行わない
        if yahoo_item['delivery_from'] in conf.get('IGNORE_DELIVERY_FROM', []):
            return -6

        # 発送が指定日時以上かかる場合
        if RichsUtils.str2int(yahoo_item['fulfillment_latency'], -1) > conf.get('MAXIMUM_FULFILLMENT'):
            return -7

        # 正常
        return 0
    except Exception as e:
        # 予期せぬ異常が発生
        return -9


# データを保存
def store(amazon_item, yahoo_item, value, user, price_setting, amazon_default_setting, amazon_image):

    try:
        # 商品数超過
        if YahooToAmazonItem.objects.filter(author=user).count() >= user.max_items:
            return -3

        sku = yahoo_item['auction_id']
        print(yahoo_item)
        print('sku' + sku)
        c=YahooToAmazonItem.objects.filter((Q(item_sku=sku)|Q(current_purchase_item_id=sku)) & Q( author=user)).count()
        if (c > 0):
            print('重複')
            return -2

        # オークションのコンディションを取得
        condition_type = RichsUtils.yahoo_to_amazon_condition( yahoo_item['condition'])
        if (condition_type == 'ERR'):
            print('コンディションエラー')
            return -1

        # オークションの金額取得
        v1 = yahoo_item['bid_or_buy']
        v2 = yahoo_item['current_price']
        m_price =int(v1 if v1 != '' else v2)

        print('-- オークション------' +str( m_price))

        # コンディションに応じたアマゾンの価格を取得
        a_price = 0
        if(condition_type == 'New'):
            if (amazon_item['price_new'] != '' and amazon_item['price_new'] != '-1'):
                a_price = int(amazon_item['price_new'])
            elif (amazon_item['price_old'] != '' and amazon_item['price_old'] != '-1'): # 新品がなければ、中古の最低価格
                a_price = int(amazon_item['price_old'])
        else:
            if (amazon_item['price_old'] != '' and amazon_item['price_old'] != '-1'):
                a_price = int(amazon_item['price_old'])
            elif (amazon_item['price_new'] != '' and amazon_item['price_new'] != '-1'): # 中古がなければ、新品の最低価格
                a_price = int(amazon_item['price_new'])

        print('-- アマゾン------' + str(a_price))

        if (a_price == 0):
            print('アマゾン金額取得エラー')
            return -1

        print(''+ str(price_setting.margin_offer_url))

        #standard_price= m_price + price_setting.margin_offer_url

        standard_price = a_price + price_setting.offset_offer_price_url
        print('販売価格:' + str(standard_price))
        diff = standard_price - m_price
        print('利益:' + str(diff))
        if (diff < price_setting.margin_offer_url):
            print('最低利益を下回っているため:' + str(diff))
            return -1

        e = YahooToAmazonItem()
        #画面から入れる情報
        e.feed_type = 1
        e.external_product_id = amazon_item['asin']
        e.external_product_id_type = 'ASIN'
        e.condition_type = condition_type
        e.standard_price = standard_price
        if condition_type == 'New':
            # 新品の場合はデフォルト設定のコンディション説明を利用
            e.condition_note = amazon_default_setting.condition_note
        else:
            # 中古の場合はヤフオクのコンディションを記載
            e.condition_note = yahoo_item['condition']
        e.purchase_fulfillment_latency = amazon_default_setting.fulfillment_latency
        e.current_purchase_fulfillment_latency = amazon_default_setting.fulfillment_latency
        e.fulfillment_latency = amazon_default_setting.fulfillment_latency

        # ポイントの設定 (相乗り出品)
        if amazon_default_setting.ride_item_points is not None:
            e.standard_price_points = amazon_default_setting.ride_item_points
        else:
            e.standard_price_points = amazon_default_setting.standard_price_points

        e.item_sku=sku
        e.item_name = amazon_item['title']
        e.current_purchase_seller_id = e.purchaseo_seller_id = yahoo_item['seller']
        #e.current_purchase_seller_id_name = e.purchaseo_seller_id_name = yahoo_item['item_id']
        e.purchase_item_id = e.current_purchase_item_id = yahoo_item['auction_id']
        e.purchase_quantity = e.current_purchase_quantity =e.quantity = 1
        e.csv_flag = 0
        e.purchase_price = e.current_purchase_price = m_price
        e.main_image_url = RichsUtils.copy_image_to_yahoo_folder(amazon_image, user)
        e.author = user
        e.purchase_similarity = e.current_similarity = value
        e.amazon_price = a_price
        e.update_fulfillment_latency_request = False
        e.update_quantity_request = False
        e.research_request = False
        e.record_type = 0
        e.save()
        return 0
    except Exception:
        print(traceback.format_exc())
        return -1


# 新規出品用アイテムの候補 Model を取得
# この関数を呼び出しただけでは DB に保存はされない
def create_item_candidate_in_ride_search(amazon_item, yahoo_item,
        value, user, price_setting, amazon_default_setting, image_base, amazon_image):
    try:
        # 機能はオプションなので、数値的に不可能な場合
        permission = ItemCandidateToCsv.objects.filter(owner=user).first()
        if permission is None or permission.max_output <= 0:
            return None

        sku = yahoo_item['auction_id']

        # 同様の オークションID での出品/出品候補がある場合は出力しない
        c=YahooToAmazonItemCandidate.objects.filter(
            (Q(item_sku=sku)|Q(current_purchase_item_id=sku)) & Q( author=user)).count()
        if (c > 0):
            return None
        c=YahooToAmazonItem.objects.filter(
            (Q(item_sku=sku)|Q(current_purchase_item_id=sku)) & Q( author=user)).count()
        if (c > 0):
            return None

        # 同様の ASIN で出品がある場合は出品しない
        c=YahooToAmazonItemCandidate.objects.filter(author=user,
            external_product_id_type='ASIN', external_product_id=amazon_item['asin']).count()
        if (c > 0):
            return None
        c=YahooToAmazonItem.objects.filter(author=user,
            external_product_id_type='ASIN', external_product_id=amazon_item['asin']).count()
        if (c > 0):
            return None

        # オークションのコンディションを取得
        condition_type = RichsUtils.yahoo_to_amazon_condition( yahoo_item['condition'])
        if (condition_type == 'ERR'):
            return None

        # オークションの金額取得
        v1 = yahoo_item['bid_or_buy']
        v2 = yahoo_item['current_price']
        m_price =int(v1 if v1 != '' else v2)

        # コンディションに応じたアマゾンの価格を取得
        a_price = 0
        if(condition_type == 'New'):
            if (amazon_item['price_new'] != '' and amazon_item['price_new'] != '-1'):
                a_price = int(amazon_item['price_new'])
            elif (amazon_item['price_old'] != '' and amazon_item['price_old'] != '-1'): # 新品がなければ、中古の最低価格
                a_price = int(amazon_item['price_old'])
        else:
            if (amazon_item['price_old'] != '' and amazon_item['price_old'] != '-1'):
                a_price = int(amazon_item['price_old'])
            elif (amazon_item['price_new'] != '' and amazon_item['price_new'] != '-1'): # 中古がなければ、新品の最低価格
                a_price = int(amazon_item['price_new'])


        if (a_price == 0):
            return None

        # 新規出品時の価格
        price_settings = AmazonFeedPriceSettings.objects.filter(author=user).first()
        minimum = price_settings.default_minimum_item_price if price_settings is not None else 3000
        standard_price = max(int(m_price * price_settings.margin_new + 0.5), minimum)

        # 情報を自動入力
        e = YahooToAmazonItemCandidate()
        # 新規出品時は product_id が自動的に割り振られるためここでは入力しない
        e.feed_type = 0
        e.external_product_id = None
        e.external_product_id_type = ''
        e.condition_type = condition_type
        e.standard_price = standard_price
        if condition_type == 'New':
            # 新品の場合はデフォルト設定のコンディション説明を利用
            e.condition_note = amazon_default_setting.condition_note
        else:
            # 中古の場合はヤフオクのコンディションを記載
            e.condition_note = yahoo_item['condition']

        e.purchase_fulfillment_latency = amazon_default_setting.fulfillment_latency
        e.current_purchase_fulfillment_latency = amazon_default_setting.fulfillment_latency
        e.fulfillment_latency = amazon_default_setting.fulfillment_latency

        # ポイントの設定 (新規自動出品)
        if amazon_default_setting.new_auto_item_points is not None:
            e.standard_price_points = amazon_default_setting.new_auto_item_points
        else:
            e.standard_price_points = amazon_default_setting.standard_price_points

        e.item_sku=sku
        initial_item_name = ItemTitleConverter.convert(yahoo_item['title'])
        e.item_name = initial_item_name
        e.product_description = initial_item_name    # 商品の説明
        e.bullet_point = initial_item_name           # 商品の仕様
        e.generic_keywords = initial_item_name       # 検索キーワード1

        # メーカ名/ブランド名の設定
        brandinfo = AmazonBrand.objects.filter(author=user).first()
        if brandinfo is not None:
            e.manufacturer = e.brand_name = brandinfo.brand_name
        else:
            e.manufacturer = e.brand_name = 'ノーブランド品'
        e.part_number = amazon_default_setting.part_number # メーカ型番

        # カテゴリのデフォルト設定
        ## カテゴリ(大分類)
        category = AmazonParentCategoryUser.objects.filter(author=user).first()
        if category is not None:
            e.category = category.value
        else:
            e.category = 'Hobbies'

        ## カテゴリ(詳細)
        nodesmodel = settings_amazon_views.get_child_user_model_class(e.category)
        browse_nodes = nodesmodel.objects.filter(author=user).first()
        if browse_nodes is not None:
            e.recommended_browse_nodes = browse_nodes.value
        else:
            e.recommended_browse_nodes = '2277722051'

        # カテゴリ用フォーマットの指定
        fmtmodel = settings_amazon_views.get_child_user_model_class(e.category)
        fmt = fmtmodel.objects.filter(author=user, value=e.recommended_browse_nodes).first()
        if fmt is not None:
            e.format = fmt.format
            e.feed_product_type = fmt.feed_product_type
        else:
            # デフォルト値を利用
            e.format = 'Toys'
            e.feed_product_type = 'Hobbies'

        e.current_purchase_seller_id = e.purchaseo_seller_id = yahoo_item['seller']
        #e.current_purchase_seller_id_name = e.purchaseo_seller_id_name = yahoo_item['item_id']
        e.purchase_item_id = e.current_purchase_item_id = yahoo_item['auction_id']
        e.purchase_quantity = e.current_purchase_quantity =e.quantity = 1
        e.csv_flag = 0
        e.purchase_price = e.current_purchase_price = m_price

        image_urls = [ url for url in yahoo_item['images'] ]
        with ImageDownloader(image_base, image_urls) as downloader:
            if len(image_urls) > 0:
                # 画像の保存(あるだけ)
                e.main_image_url = RichsUtils.copy_image_to_yahoo_folder(downloader.get(image_urls[0]), user)
                if len(image_urls) > 1:
                    e.other_image_url1 = RichsUtils.copy_image_to_yahoo_folder(downloader.get(image_urls[1]), user)
                if len(image_urls) > 2:
                    e.other_image_url2 = RichsUtils.copy_image_to_yahoo_folder(downloader.get(image_urls[2]), user)
                if len(image_urls) > 3:
                    e.other_image_url3 = RichsUtils.copy_image_to_yahoo_folder(downloader.get(image_urls[3]), user)
            else:
                # 万が一存在しない場合は Amazon のものを流用
                e.main_image_url = RichsUtils.copy_image_to_yahoo_folder(amazon_image, user)

        e.author = user
        e.purchase_similarity = e.current_similarity = value
        # e.amazon_price = a_price # 未使用
        e.update_fulfillment_latency_request = False
        e.update_quantity_request = False
        e.research_request = False
        e.record_type = 0
        return e
    except Exception:
        print(traceback.format_exc())
        return None


def yahoo_url_foramazon_offer_research(params, keyword, price_min, price_max):
    ''' 一気通貫用のオークションリサーチ用URL生成 '''

    urltml = RichsUtils.AUCTIONS_URL_KEY_SEARCH

    select = params.get('select')
    istatus = params.get('istatus')
    aucminprice = '' #str(price_min)
    aucmaxprice = '' #str(price_max)
    aucmin_bidorbuy_price = '' # str(price_min)
    aucmax_bidorbuy_price = '' #str(price_max)
    is_exist_bidorbuy_price = params.get('is_exist_bidorbuy_price')
    # 即決価格有り
    if is_exist_bidorbuy_price == '0':
        aucmin_bidorbuy_price = '0'
        aucmax_bidorbuy_price = '10000000'

    abatch = params.get('abatch')
    thumb='1'

    tmp='&thumb=1'
    if thumb == '0':
        tmp = ''

    va = urllib.parse.quote(keyword, safe='?')

    url=urltml.replace('{va}', va).replace('{select}',select).replace('{istatus}',istatus).replace('{aucminprice}',aucminprice).replace('{aucmaxprice}',aucmaxprice).replace('{aucmin_bidorbuy_price}',aucmin_bidorbuy_price).replace('{aucmax_bidorbuy_price}',aucmax_bidorbuy_price).replace('{abatch}',abatch).replace('{thumb}', tmp)
    return url



#
# 進捗情報を保持
#
def save_amazon_offer_progress(obj,total,exclude_asin,prime,condition_different,exclude_seller,not_found,feed_item, is_over_items):
    obj.total = total
    obj.exclude_asin = exclude_asin
    obj.prime = prime
    obj.condition_different = condition_different
    obj.exclude_seller = exclude_seller
    obj.not_found = not_found
    obj.feed_item = feed_item
    obj.is_over_items = is_over_items
    obj.save()

# 最大金額取得
def get_max_price_from_amazon_item(amazon_item):

    price = 0

    try:
        if (amazon_item['price_new'] != ''):
            tmp = int(amazon_item['price_new'])
            if (tmp > price):
                price = tmp
    except:
        pass

    try:
        if (amazon_item['price_old'] != ''):
            tmp = int(amazon_item['price_old'])
            if (tmp > price):
                price = tmp
    except:
        pass

    try:
        if (price == 0 and amazon_item['price'] != ''):
            tmp = int(amazon_item['price'])
            if (tmp > price):
                price = tmp
    except:
        pass

    return price


def _get_offer_research_scrapers(user):
    ''' 利用する Scraper オブジェクトを生成する '''
    # API情報の登録がない場合は処理を中断
    e = RichsUtils.get_mws_api(user)
    if e is None:
        return (None, None, None)

    # 1回の検索ではバックグラウンド検索用に割り当てられたIPを利用
    ipaddr = RichsUtils.offer_research_ip_address()
    context = 'YahooBGSearch:{}'.format(user.username)
    amazon_scraper = AmazonScraper(ipaddr, context=context)
    yahoo_scraper = YahooSearchScraper(ipaddr)
    yahoo_auction_id_scraper = YahooAuctionIdScraper(ipaddr)

    if settings.PRODUCTION:
        # 開発環境化ではAmazon MWS API を利用しない
        amazon_scraper.set_mws(
            e.account_id, e.access_key, e.secret_key, e.auth_token, e.region, e.marketplace_id)

    return (amazon_scraper, yahoo_scraper, yahoo_auction_id_scraper)


def _amazon_retry_settings():
    try:
        return settings.AMAZON_ERROR_RETRY_SETTINGS
    except:
        return {}


def _save_background_search_progress(watch, current_search):
    ''' 一括検索の状態を保存する関数 '''
    watch.save()
    if current_search:
        # それ以外のデータを上書きしないように最新情報を取得して移し替える
        e = BackgroundSearchInfo.objects.get(id=current_search.id)
        e.start_date = current_search.start_date
        e.save()


def amazon_offer_research_entry(params, url, user, trial=0, rest_wait_count=0):
    ''' 相乗り商品抽出内部処理のエントリーポイント '''
    try:
        try:
            watch = OfferReserchWatcher.objects.get(research_type=0, author=user)
        except OfferReserchWatcher.DoesNotExist:
            logger.warn('相乗り商品抽出レコードが未登録です。 research_type=0, author=%s', user)
            return

        # 現在検索中のURL情報
        current_search = BackgroundSearchInfo.objects.filter(
            watcher=watch, search_completed=False).order_by('order').first()

        # 外部からの中断リクエストを処理する
        entityList = StopRequest.objects.filter(view=11, author=user)
        if len(entityList) > 0:
            entityList.delete()
            OfferReserchWatcher.objects.get(research_type=0, author=user).delete()
            logger.info('ユーザー %s からの停止リクエストを処理しました', user)
            return

        if rest_wait_count > 0:
            # rest_wait_count > 0 の場合は指定時間のウェイトを入れて再実行
            retry_settings = _amazon_retry_settings()
            wait_sec = retry_settings.get('TRIAL_WAIT_SECONDS', 5)
            asynchelpers.wait(wait_sec)

            # 一定時間後に再実行を登録して終了
            queue = asynchelpers.get_queue()
            queue.enqueue(amazon_offer_research_entry,
                kwargs=dict(params=params, url=url, user=user, trial=trial, rest_wait_count=rest_wait_count-1))
            return

        # API情報の登録がない場合は処理を中断
        (amazon_scraper, _y, _yid) =  _get_offer_research_scrapers(user)
        if amazon_scraper is None:
            logger.info('MWS APIの情報登録がありません。 research_type=0, author=%s', user)
            watch.delete()
            return

        # 検索をトランザクションと見立てて、そこで利用できる共用プールを作成
        pools = dict(
            # テンポラリ画像の出力フォルダ
            image_base = RichsUtils.get_tmp_image_folder(user),
            # 価格設定情報
            price_setting = AmazonFeedPriceSettings.objects.get(author=user),
            # 禁止セラー
            exclude_sellers = YahooExcludeSeller.objects.filter(author=user),
            # Amazon出品デフォルト設定
            amazon_default_setting = AmazonDefaultSettings.objects.get(author=user),
            # シーケンス番号 (具体的に何度workerで処理されたか)
            sequence = 0,
            # 検索個数
            item_search_count = 0,
            # アイテム発見個数
            item_search_found = 0,
            # 現在のURLで取得できるAmazon Item一覧
            amazon_items = [],
            # 検索途中のAmazon Item一覧
            rest_amazon_items = [],
            # 次のURL
            next_url = '',
        )

        try:
            # Amazon の情報を取得
            amazon_items = amazon_scraper.get_products(url, raise_when_5xx=True)
        except Exception:
            # 5xxで取得できない場合, あるいはAmazonへの通信で不明なエラーが発生した場合はリトライをかける
            retry_settings = _amazon_retry_settings()

            # 最大試行回数を超えていた場合は中断
            if trial >= retry_settings.get('MAX_TRIAL', 60):
                raise ValueError('Amazon Scraping reached maximum trial')

            # 一定時間後に再実行を登録して終了
            queue = asynchelpers.get_queue()
            rest_wait_count = retry_settings.get('TRIAL_WAIT_COUNT', 12)
            watch.error_message = '[{}] Amazonとの通信に失敗したため、再試行待機中です。'.format(
                datetime.now().strftime('%H:%M:%S'))
            _save_background_search_progress(watch, current_search)
            queue.enqueue(amazon_offer_research_entry,
                kwargs=dict(params=params, url=url, user=user, trial=trial+1, rest_wait_count=rest_wait_count))
            logger.info('scraping failed and enqueue retry: {} user for {} trial(s)'.format(user, trial+1))
            return

        pools['amazon_items'] = pools['rest_amazon_items'] = amazon_items
        pools['next_url'] = amazon_scraper.get_next_page_url()

        try:
            # 相乗り検索で発見された新規出品候補は7日以上経ったタイミングで自動削除
            expired = timezone.datetime.now() - timedelta(days=7)
            deletes = YahooToAmazonItemCandidate.objects.filter(author=user, created_date__lte=expired)
            for candidate in deletes:
                # 画像を手動で削除
                candidate.delete_file()
            deletes.delete()
        except Exception as ex:
            logger.exception(ex)

        # 正常開始なのでエラーメッセージを消去
        watch.error_message = ''
        # URL単位経過時間の計測開始
        if current_search:
            current_search.start_date = timezone.datetime.now()
        _save_background_search_progress(watch, current_search)

        # 遅延処理を登録
        queue = asynchelpers.get_queue()
        queue.enqueue(amazon_offer_research_task,
            params=params, url=url, user=user, pools=pools)

    except Exception as err:
        # 予期せぬ例外が起こった場合
        logger.exception(err)
        logger.info('ユーザー %s の処理中にエラーが発生したため、強制中断しました', user)

        # 遅延処理を登録
        queue = asynchelpers.get_queue()
        queue.enqueue(amazon_offer_research_finalize,
            params=params, user=user)


def amazon_offer_research_task(params, url, user, pools, trial=0, rest_wait_count=0):
    ''' 相乗り商品抽出内部処理のエントリーポイント '''
    try:
        # 外部からのURLスキップリクエストを処理する
        skipRequests = URLSkipRequest.objects.filter(view=11, author=user)
        if len(skipRequests) > 0:
            skipRequests.delete()
            logger.info('ユーザー %s からのURL: %s のスキップリクエストを処理しました。', url, user)
            queue = asynchelpers.get_queue()
            queue.enqueue(amazon_offer_research_finalize, params=params, user=user)
            return

        # 外部からの中断リクエストを処理する
        entityList = StopRequest.objects.filter(view=11, author=user)
        if len(entityList) > 0:
            entityList.delete()
            OfferReserchWatcher.objects.get(research_type=0, author=user).delete()
            logger.info('ユーザー %s からの停止リクエストを処理しました', user)
            return

        logger.debug('[seq=%s] started amazon_offer_research_task', pools['sequence'])

        amazon_items = pools['rest_amazon_items']

        watch = OfferReserchWatcher.objects.get(research_type=0, author=user)
        if watch.status not in [0, 9]:
            # その他ステータスの場合は二重更新にならないように打ち切る
            logger.info('Cancel to avoid duplicate: %s', watch)
            return

        current_search = BackgroundSearchInfo.objects.filter(
            watcher=watch, search_completed=False).order_by('order').first()

        if rest_wait_count > 0:
            # rest_wait_count > 0 の場合は指定時間のウェイトを入れて再実行
            retry_settings = _amazon_retry_settings()
            wait_sec = retry_settings.get('TRIAL_WAIT_SECONDS', 5)
            asynchelpers.wait(wait_sec)

            # 一定時間後に再実行を登録して終了
            queue = asynchelpers.get_queue()
            kwargs = dict(
                params=params, url=url, user=user,
                pools=pools, trial=trial,
                rest_wait_count=rest_wait_count-1)
            queue.enqueue(amazon_offer_research_task, kwargs=kwargs)
            return

        def _cancel_current_url(pools):
            ''' 1000件検索して、found数が10件未満で検索をキャンセル '''
            # 旧版対応(キャンセルしない)
            if 'item_search_count' not in pools or 'item_search_found' not in pools:
                return False
            conf = _ride_search_config()
            if pools['item_search_count'] < conf.get('SKIP_JUDGE_ITEM', 1000):
                return False
            return pools['item_search_found'] < conf.get('SKIP_JUDGE_LOWER_ITEM', 10)

        # メインループ処理： Amazon Itemを１つずつ処理
        exec_count = 0
        work_start = datetime.now()
        cancel = False
        for amazon_item in amazon_items:

            if watch.is_over_items:
                # アイテムが上限に達している場合は中断
                break

            cancel = _cancel_current_url(pools)
            if cancel:
                # URLにアイテムが少なすぎるため打ち切り
                break

            try:
                prev_feed = watch.feed_item
                prev_candidate = watch.new_feed_item_candidate

                # 1Amazon Itemの検索を実施
                amazon_offer_research_for_item(params, user, pools, watch, amazon_item)

                # 検索結果の更新
                if watch.feed_item > prev_feed or watch.new_feed_item_candidate > prev_candidate:
                    pools['item_search_found'] = pools.get('item_search_found', 0) + 1
            except Exception as e:
                research_code = 'Yahoo Research: {:08d}#{}##{}'.format(watch.id, user.username, amazon_item['asin'])
                rlogger = RecordLogger.Context(research_code)
                rlogger.info('#EOS# #DIFF# unknown exception')
                rlogger.exception(e)
                logger.exception(e)
                watch.condition_different += 1

            # 検索終了後の情報を保存
            _save_background_search_progress(watch, current_search)
            exec_count += 1
            pools['item_search_count'] = pools.get('item_search_count', 0) + 1

            # 指定時間が経過している場合、作業を中断
            delta = timedelta(seconds=settings.ASYNC_WORKER['TASK_RECOMMENDED_MAXIMUM_SECONDS'])
            if datetime.now() - work_start >= delta:
                break
            asynchelpers.wait()

        if watch.is_over_items:
            # アイテムが上限に達している場合は強制終了
            logger.debug('検索可能アイテム数の上限を超えました。user=%s', user)
            queue = asynchelpers.get_queue()
            queue.enqueue(amazon_offer_research_finalize,
                params=params, user=user)
            return

        if cancel:
            # 一定個数検索を行ったが、得られた数が想定以下
            conf = _ride_search_config()
            logger.info(
                'URL: %s - %s件検索しましたが、見つかったアイテムが%s個 (< %s)のため打ち切ります。',
                watch.current_url, conf.get('SKIP_JUDGE_ITEM', 1000),
                pools.get('item_search_found', 0), conf.get('SKIP_JUDGE_LOWER_ITEM', 10))
            queue = asynchelpers.get_queue()
            queue.enqueue(amazon_offer_research_finalize,
                params=params, user=user)
            return

        # itemの更新
        rest_amazon_items = amazon_items[exec_count:]
        if len(rest_amazon_items) <= 0:
            (amazon_scraper, _y, _yid) =  _get_offer_research_scrapers(user)
            if 'next_url' in pools:
                next_url = pools.get('next_url', '')
            else:
                # next page を探すために一度ロードする
                amazon_scraper.get_products(url)
                asynchelpers.wait()
                next_url = amazon_scraper.get_next_page_url()

            if next_url == '':
                # 次の検索URLなし
                logger.debug('全てのAmazon商品の検索を終了しました。seq=%s', pools['sequence'])
                # finalize request を積んで終了
                queue = asynchelpers.get_queue()
                queue.enqueue(amazon_offer_research_finalize,
                    params=params, user=user)
                return

            watch.error_message = ''
            _save_background_search_progress(watch, current_search)

            try:
                next_amazon_items = amazon_scraper.get_products(next_url, raise_when_5xx=True)
            except Exception as err:
                # 5xxで取得できない場合, あるいはAmazonへの通信で不明なエラーが発生した場合はリトライをかける
                retry_settings = _amazon_retry_settings()

                # 最大試行回数を超えていた場合は中断
                if trial >= retry_settings.get('MAX_TRIAL', 60):
                    raise ValueError('Amazon Scraping reached maximum trial')

                # この2つのパラメータは更新する
                pools['sequence'] = pools['sequence'] + 1
                pools['rest_amazon_items'] = rest_amazon_items

                # 一定時間後に再実行を登録して終了
                queue = asynchelpers.get_queue()
                rest_wait_count = retry_settings.get('TRIAL_WAIT_COUNT', 12)
                watch.error_message = '[{}] Amazonとの通信に失敗したため、再試行待機中です。'.format(
                    datetime.now().strftime('%H:%M:%S'))
                _save_background_search_progress(watch, current_search)
                kwargs=dict(
                    params=params, url=url, user=user,
                    pools=pools, trial=trial+1,
                    rest_wait_count=rest_wait_count)
                queue.enqueue(amazon_offer_research_task, kwargs=kwargs)
                logger.info('search scraping failed and enqueue retry: {} user for {} trial(s)'.format(user, trial+1))
                return

            url = next_url
            pools['amazon_items'] = next_amazon_items
            pools['next_url'] = amazon_scraper.get_next_page_url()
            rest_amazon_items = pools['amazon_items']

        # pools情報の更新
        pools['sequence'] = pools['sequence'] + 1
        pools['rest_amazon_items'] = rest_amazon_items

        if asynchelpers.reached_maximum_sequence(pools['sequence']):
            # 最大試行回数に届いている場合は finalize request を積んで終了
            queue = asynchelpers.get_queue()
            queue.enqueue(amazon_offer_research_finalize,
                params=params, user=user)
            return

        # 継続リクエストを積んで終了
        queue = asynchelpers.get_queue()
        queue.enqueue(amazon_offer_research_task,
            params=params, url=url, user=user, pools=pools)

    except Exception as err:
        # 予期せぬ例外が起こった場合
        logger.exception(err)
        logger.info('ユーザー %s の処理中にエラーが発生したため、強制中断しました', user)

        # 遅延処理を登録
        queue = asynchelpers.get_queue()
        queue.enqueue(amazon_offer_research_finalize,
            params=params, user=user)


def amazon_offer_research_for_item(params, user, pools, watch, amazon_item):
    ''' 商品抽出処理の1アイテム分の処理。
    続行不可能となった場合は何らかのErrorをraiseする。 '''

    (amazon_scraper, yahoo_scraper, yahoo_auction_id_scraper) =  _get_offer_research_scrapers(user)
    research_code = 'Yahoo Research: {:08d}#{}##{}'.format(watch.id, user.username, amazon_item['asin'])
    rlogger = RecordLogger.Context(research_code)

    # 禁止ASIN
    asin_list = RichsUtils.amazon_items_to_asin_list(pools['amazon_items'])
    exclude_asins = ExcludeAsin.objects.filter(author=user, asin__in=asin_list)

    watch.total += 1
    watch.asin = amazon_item['asin']
    rlogger.info('AMAZON: %s', amazon_item.get('title'))

    # 禁止ASIN判定
    if (RichsUtils.is_exclude_asins(exclude_asins, watch.asin)):
        watch.exclude_asin += 1
        rlogger.info('#EOS# prohibited: %s', amazon_item['asin'])
        return

    # プライム判定
    if (amazon_item['prime'] == 'True'):
        watch.prime += 1
        rlogger.info('#EOS# prime: %s', amazon_item['asin'])
        return

    # 予約商品判定
    if amazon_item.get('reserved') == 'True':
        watch.condition_different += 1
        rlogger.info('#EOS# #DIFF# reserved: %s', amazon_item['asin'])
        return

    # 仕入れ元検索
    price_min = 0
    price_max = get_max_price_from_amazon_item(amazon_item)
    rlogger.info('price: %s, min: %s, max: %s',
        amazon_item.get('price'), amazon_item.get('price_min'), amazon_item.get('price_max'))

    if (price_max < pools['price_setting'].lowest_offer_price_url):
        #print('最低販売価格以下であるため除外')
        watch.condition_different += 1
        rlogger.info('#EOS# #DIFF# less than minimum price: %s < %s', price_max, pools['price_setting'].lowest_offer_price_url)
        return

    # 検索条件に利益額を入れる。
    margin = pools['price_setting'].margin_offer_url + pools['price_setting'].offset_offer_price_url
    price_max = price_max - margin
    if (price_max <= 0):
        # print('最低利益を確保できない商品であるため、仕入れ検索を中止')
        watch.condition_different += 1
        rlogger.info('#EOS# #DIFF# no margin: %s', margin)
        return

    asynchelpers.wait()

    #print("仕入れ検索条件の高い方" + str(price_max))
    # Yahoo検索
    keyword = amazon_item['title']
    yahoo_url = yahoo_url_foramazon_offer_research(params, keyword, price_min, price_max)
    yahoo_items = yahoo_scraper.get_products(yahoo_url)
    if (len(yahoo_items) == 0):
        watch.not_found += 1
        rlogger.info('#EOS# no yahoo item: %s', yahoo_url)
        return
    rlogger.info('found yahoo item: %s from %s', len(yahoo_items), yahoo_url)

    # アマゾンの画像を保存
    asin = amazon_item['asin']
    amazon_image_url = amazon_item['image']
    rlogger.info('amazon image: %s', amazon_image_url)
    amazon_image = os.path.join(
        pools['image_base'],
        amazon_scraper.save_image(
            amazon_image_url, pools['image_base'], asin))

    # アマゾンの画像とYahooで得られた画像の類似度を比較
    detected_similar_item = False
    detected_similar_item_candidates = []
    banned_list = RichsUtils.get_banned_list()
    for chunk in RichsUtils.chunkof(yahoo_items, 10):
        if detected_similar_item:
            break

        valid_items = []
        for yahoo_item in chunk:
            # 禁止ワード判定
            (is_banned, banned_keyword) = RichsUtils.judge_banned_item(
                yahoo_item['title'], banned_list)
            if not is_banned:
                valid_items.append(yahoo_item)
            else:
                rlogger.info('contains banned keyword: %s in %s', banned_keyword, yahoo_item['title'])

        image_urls = [ c['images'][0] for c in valid_items ]
        with ImageDownloader(pools['image_base'], image_urls) as downloader:
            for yahoo_item in valid_items:

                # 比較のためにローカルに保存
                yahoo_item_id = yahoo_item['auction_id']
                yahoo_image_url = yahoo_item['images'][0]
                yahoo_image = downloader.get(yahoo_image_url)
                rlogger.info('yahoo item %s (%s)', yahoo_item['title'], yahoo_item_id)
                rlogger.info('yahoo image: %s', yahoo_image_url)
                if yahoo_image is None:
                    # ダウンロード失敗
                    logger.debug('failed to download: %s', yahoo_image_url)
                    rlogger.info('#SKIP# failed to download: %s from %s', yahoo_item_id, yahoo_image_url)
                    continue

                # 類似度の簡易判定 (similar_fast) を行ってふるいをかける。
                # 最終的な画像比較は非常に重たいため、分割して行う (similar)
                (detected_similar_item, value) = ItemImageComparator.similar_fast(
                    amazon_image, yahoo_image, float(params.get('similarity')))
                if not detected_similar_item:
                    rlogger.info('#SKIP# failed to compare similar_fast: %s', value)
                    continue

                # 禁止セラー判定
                seller_id = yahoo_item['seller']
                if (RichsUtils.is_exclude_sellers(pools['exclude_sellers'], seller_id)):
                    # detected_similar_item は true のまま
                    watch.exclude_seller += 1
                    rlogger.info('exclude seller: %s', seller_id)
                    continue

                # レーティング判定
                yahoo_aution_url = 'https://page.auctions.yahoo.co.jp/jp/auction/' + yahoo_item_id
                feed_item = yahoo_auction_id_scraper.get_products(yahoo_aution_url)
                rateing = float(feed_item[0]['rate_percent'])
                rateing_thres = float(params.get('rateing'))
                if rateing < rateing_thres:
                    # 評判の良くないユーザー判定 (detected_similar_item は true のまま)
                    watch.condition_different += 1
                    rlogger.info('#DIFF# non-good rating: %s < %s from %s', rateing, rateing_thres, yahoo_aution_url)
                    continue

                # 情報の総合比較を実施
                result = available_for_purchase(amazon_item, feed_item[0], value, user,
                    pools['price_setting'], amazon_image)

                if result == -3:
                    # 登録件数オーバー
                    watch.is_over_items = True
                    rlogger.info('#EOS# over items')
                    break
                elif result != 0:
                    # その他の購入不可理由が発見されたため無視して次のアイテムを検索
                    detected_similar_item = False
                    rlogger.info('#SKIP# unavailable purchage: %s', result)
                    continue

                # 最終的な画像判定を行う
                (final_image_matched, compare_details) = ItemImageComparator.similar(amazon_image, yahoo_image)
                rlogger.info('final image compare: %s and %s', final_image_matched, compare_details)
                if not final_image_matched:
                    # 最終画像判定は失敗した場合は新規出品候補に追加
                    item_candidate = create_item_candidate_in_ride_search(
                        amazon_item, feed_item[0], value, user,
                        pools['price_setting'], pools['amazon_default_setting'],
                        pools['image_base'], amazon_image)

                    # 候補のmodelオブジェクトを登録
                    if item_candidate is not None:
                        detected_similar_item_candidates.append(item_candidate)

                    # 相乗り可能なアイテムが見つかる可能性はあるので検索は続ける
                    detected_similar_item = False
                    continue

                # アイテムを登録
                result = store(amazon_item, feed_item[0], value, user,
                    pools['price_setting'], pools['amazon_default_setting'], amazon_image)

                if result == 0:
                    # 対象商品がヒット
                    watch.feed_item += 1
                    rlogger.info('#EOS# feed found: %s', yahoo_item_id)
                    break
                else:
                    # その他例外が発生したため無視する
                    detected_similar_item = False
                    rlogger.info('#SKIP# store returns non-zero: %s', result)
                    continue

    if not detected_similar_item and len(detected_similar_item_candidates) > 0:
        # 相乗り検索対象は見つからなかったが、新規出品可能商品は見つかったので
        # もっとも利益が高いものをDBに保存する
        detected_similar_item_candidates = sorted(
            detected_similar_item_candidates, reverse=True,
            key=lambda e: e.standard_price - e.purchase_price)
        head = detected_similar_item_candidates[0]
        detected_similar_item_candidates = detected_similar_item_candidates[1:]
        head.save()
        print('新規出品可能商品: {} ({})'.format(head.item_name, head.item_sku))
        print('販売価格: {}'.format(head.standard_price))
        watch.new_feed_item_candidate += 1
        rlogger.info('#EOS# add new_feed_candidate: %s %s', head.item_name, head.item_sku)

        # 利用しない保存している画像を削除
        for never_used_candidate in detected_similar_item_candidates:
            RichsUtils.delete_file_if_exist(never_used_candidate.main_image_url)

    elif not detected_similar_item:
        # yahooアイテム全てが不一致である場合
        watch.condition_different += 1
        rlogger.info('#EOS# #DIFF# all yahoo item mismatched')

    RichsUtils.delete_file_if_exist(amazon_image)


def _amazon_offer_research_finalize_for_single(params, user, watch):
    # 単一URLのみの場合(修正前の検索データ対応)
    watch.status = 1
    # CSVフラグが立っていて、出品がある場合
    if params.get('is_export_csv') == '1':
        try:
            if watch.feed_item > 0:
                watch.status = 2
                y2a_items = YahooToAmazonItem.objects.filter(feed_type=1, csv_flag=0, author=user)
                if len(y2a_items) > 0:
                    export_amazon_offer_csv_internal(y2a_items, user)
            if watch.new_feed_item_candidate > 0:
                watch.status = 2
                _export_amazon_new_csv_from_candidate(user)
        except:
            # Exportに失敗したのでステータスはCSVフラグなしとして扱う
            logger.warn('CSV Exportに失敗しました。')
            logger.warn(traceback.format_exc())
            watch.status = 1

    # 終了処理
    watch.end_date = datetime.now()
    watch.save()

    # 停止要求ファイルを全て削除する。
    StopRequest.objects.filter(view=11, author=user).delete()


def _amazon_offer_research_finalize_for_multiurls(params, user, watch, current_search):
    # 前の検索結果を取得
    # (同一URLが入力された場合に対応するため、ソートして最後を取る)
    prev_search = BackgroundSearchInfo.objects.filter(
        watcher=watch, search_completed=True).order_by('order')
    if len(prev_search) > 0:
        prev_index = len(prev_search) - 1
        prev = prev_search[prev_index]
        prev_feed = prev.total_feed_count
        prev_new_feed = prev.total_new_feed_count
        prev_total = prev.total_count
    else:
        prev_feed = 0
        prev_new_feed = 0
        prev_total = 0

    # NOTE: feed_count と new_feed_count は確定タイミングでのみ計算
    # 画面に表示する分は画面側で計算している
    current_url_feed = watch.feed_item - prev_feed
    current_url_new_feed = watch.new_feed_item_candidate - prev_new_feed
    current_url_count = watch.total - prev_total

    current_search.output_csv = False
    current_search.search_completed = True
    current_search.total_feed_count = watch.feed_item
    current_search.total_new_feed_count = watch.new_feed_item_candidate
    current_search.total_count = watch.total
    current_search.feed_count = current_url_feed
    current_search.new_feed_count = current_url_new_feed
    current_search.total_url_count = current_url_count
    current_search.end_date = timezone.datetime.now()

    # URL個別にCSV出力を実施
    if params.get('is_export_csv') == '1':
        try:
            if current_url_feed > 0:
                current_search.output_csv = True
                y2a_items = YahooToAmazonItem.objects.filter(feed_type=1, csv_flag=0, author=user)
                if len(y2a_items) > 0:
                    export_amazon_offer_csv_internal(y2a_items, user)
            if current_url_new_feed > 0:
                current_search.output_csv = True
                _export_amazon_new_csv_from_candidate(user)
        except:
            # Exportに失敗したのでステータスはCSVフラグなしとして扱う
            current_search.output_csv = False
            logger.warn('CSV Exportに失敗しました。')
            logger.warn(traceback.format_exc())
    current_search.save()

    logger.info('search completed - URL: %s', current_search.url)

    next_url = current_search.next_url
    if next_url is None:
        # next_url が存在しない場合、他に検索未完了のものがないかをチェック
        candidate = BackgroundSearchInfo.objects.filter(
            watcher=watch, search_completed=False).order_by('order').first()
        if candidate is not None:
            # 未完了のものがある場合は情報を書き換える
            current_search.next_url = candidate.url
            current_search.save()
            next_url = candidate.url

    if next_url is not None:
        # URL情報を保持し、次のURL検索を開始
        watch.current_url = next_url
        watch.save()
        queue = asynchelpers.get_queue()
        queue.enqueue(amazon_offer_research_entry,
            params=params, url=next_url, user=user)
        return

    # 終了処理
    count = BackgroundSearchInfo.objects.filter(
        watcher=watch, output_csv=True).count()
    watch.status = 2 if (count > 0) else 1
    watch.end_date = datetime.now()
    watch.save()

    # 停止要求ファイルを全て削除する。
    StopRequest.objects.filter(view=11, author=user).delete()


def amazon_offer_research_finalize(params, user):
    ''' 遅延検索の終了処理 '''
    try:
        watch = OfferReserchWatcher.objects.get(research_type=0, author=user)

        # 追加のURLがあるか否かをチェック
        allurls = BackgroundSearchInfo.objects.filter(
            watcher=watch, search_completed=False).order_by('order')
        if len(allurls) > 0:
            # 複数URL対応の処理
            _amazon_offer_research_finalize_for_multiurls(
                params, user, watch, allurls[0])
        else:
            # URL複数対応前の処理
            _amazon_offer_research_finalize_for_single(params, user, watch)

    except Exception:
        logger.error('終了処理中にエラーが発生しました。')
        logger.error(traceback.format_exc())


@login_required
def download_item_list(request):
    return render(request, 'yahoo/todo.html')


@login_required
def import_csv(request):
    return render(request, 'yahoo/todo.html')
