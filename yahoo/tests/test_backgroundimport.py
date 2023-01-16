#!/usr/bin/python 
# -*- coding: utf-8 -*-

import datetime

from unittest.mock import mock_open, patch, MagicMock
from django.forms.models import model_to_dict

from django.test import TestCase
from django.utils import timezone
from django.http import QueryDict
from django.conf import settings

import yahoo.views 
from asyncworker import asynchelpers

from accounts.models import User, OfferReserchWatcher, StopRequest, BannedKeyword
from settings_amazon.models import AmazonAPI, ExcludeAsin, AmazonFeedPriceSettings, AmazonDefaultSettings
from yahoo.models import YahooImportCSVResult, YahooToAmazonItem, YahooExcludeSeller

@patch('yahoo.views.asynchelpers.wait')
@patch('yahoo.views.logger')
@patch('yahoo.views.asynchelpers.get_import_queue')
class BackgroundImportTaskTests(TestCase):
    ''' インポート処理の単体テスト '''

    def _init(self, username='ut01', status=0):
        user = User.objects.create_user(
            username='ut01', password='password', max_items=10)
        YahooImportCSVResult.objects.create(author=user, status=status)
        return user


    def test_entry_no_record(self, mqueue, mlogger, mwait):
        user = self._init(status=0)

        yahoo.views.import_report_entry('/path/to', user)

        (actuals, kwactuals) = mlogger.warn.call_args_list[0]
        self.assertEquals(actuals[0], 
            '事前に生成されているべきレコードが存在しません。 user=%s, status=1')


    def test_entry_fail_import_csv(self, mqueue, mlogger, mwait):
        user = self._init(status=1)
        for record_type in range(9, 15):
            YahooToAmazonItem.objects.create(author=user, record_type=record_type)

        with patch('yahoo.views.print'), \
                patch('yahoo.views.import_report_internal_csv_to_db', side_effect=Exception('mock')):
            yahoo.views.import_report_entry('/path/to', user)

        result = YahooImportCSVResult.objects.get(author=user)
        self.assertEquals(result.result_message,
            'CSVファイルのアップロードに失敗しました。\nもう一度アップロードしてください。')
        self.assertEquals(5, result.status)

        self.assertEquals(0, YahooToAmazonItem.objects.filter(
            author=user, record_type__in = [10, 11, 12, 13]).count())
        self.assertEquals(2, YahooToAmazonItem.objects.filter(
            author=user, record_type__in = [9, 10, 11, 12, 13, 14]).count())


    def test_entry_import_csv(self, mqueue, mlogger, mwait):
        user = self._init(status=1)
        YahooToAmazonItem.objects.create(author=user, 
            record_type=0, item_sku='SKU00001', current_purchase_item_id='ITEM00001')
        YahooToAmazonItem.objects.create(author=user, 
            feed_type=3, csv_flag=1, item_sku='SKU00002',
            external_product_id='ASIN', current_purchase_item_id='SKU00002')
        YahooToAmazonItem.objects.create(author=user, 
            feed_type=3, csv_flag=1, item_sku='SKU0000X', 
            external_product_id='ASIN', current_purchase_item_id='SKU00003')
        ExcludeAsin.objects.create(author=user, asin='X0001')
        
        csvmock = MagicMock(return_value=[
            ['SKU_OR_ITEM_ID', 'PRODUCt_ID', 'DUMMY', 'DUMMY'], 
            # OK - 2 liines 
            [],
            ['    '],
            # ERROR - 3 lines 
            ['AAA', 'BBB'],
            ['', 'BBB', 'CCC', 'DDD'],
            ['AAA', '', 'CCC', 'DDD'],
            # ERROR by exclude_asin
            ['SKU99999', 'X0001', 'DUMMY', 'DUMMY'],
            # IMPORT - 7 lines
            ['SKU90001', 'P0001', 'DUMMY', 'DUMMY'],
            ['SKU90002', 'P0002', 'DUMMY', 'DUMMY'],
            ['SKU90003', 'P0003', 'DUMMY', 'DUMMY'],
            ['SKU90004', 'P0004', 'DUMMY', 'DUMMY'],
            ['SKU90005', 'P0005', 'DUMMY', 'DUMMY'],
            ['SKU90006', 'P0006', 'DUMMY', 'DUMMY'],
            ['SKU90007', 'P0007', 'DUMMY', 'DUMMY'],
            # OVER - 4 lines
            ['SKU90010', 'P0010', 'DUMMY', 'DUMMY'],
            ['SKU90011', 'P0011', 'DUMMY', 'DUMMY'],
            ['SKU90012', 'P0012', 'DUMMY', 'DUMMY'],
            ['SKU90013', 'P0013', 'DUMMY', 'DUMMY'],
            # DUPLICATED but several updates - 4 lines (2 duplicated)
            ['SKU00001', 'BBB', 'CCC', 'DDD'], # 更新対象ではないので重複でスキップ (dup+1)
            ['SKU00002', 'BBB', 'CCC', 'DDD'], # external_product_id が一致しない場合でも上書きできる
            ['SKU00002', 'ASIN', 'DUMMY', 'DUMMY'], # 複数行ある場合、先が有効となりこの行が無視される (dup+1)
            ['SKU00003', 'ASIN2', 'DUMMY', 'DUMMY'], # current が該当する場合、そこを更新する
        ])

        dt = datetime.datetime(2001, 1, 1, 0, 0, 0)
        with patch('yahoo.views.print'), \
                    patch('yahoo.views.open', mock_open()), \
                    patch('yahoo.views.csv.reader', csvmock), \
                    patch('yahoo.views.timezone.datetime') as mdt:
            mdt.now = MagicMock(return_value=dt)
            yahoo.views.import_report_entry('/path/to', user)

        result = YahooImportCSVResult.objects.get(author=user)
        self.assertEquals(2, result.status)
        self.assertEquals(result.result_message,
            '[2001-01-01 00:00:00] CSVファイルのアップロード完了')

        self.assertEquals(4, result.error_record_numbers)
        self.assertEquals('4\n5\n6\n7 (除外ASIN<X0001>)', result.error_record_numbers_txt)
        self.assertEquals(2, result.duplicate_skus)
        self.assertEquals('SKU00001\nSKU00002', result.duplicate_skus_txt)
        self.assertEquals(4, result.over_skus)
        self.assertEquals('SKU90010\nSKU90011\nSKU90012\nSKU90013', result.over_skus_text)
        self.assertEquals(2, result.status)
 
        (actuals, kwactuals) = mqueue().enqueue.call_args_list[0]
        self.assertEquals(yahoo.views.import_report_internal_yahoo_task, actuals[0])
        self.assertEquals(kwactuals['user'], user)

        query = YahooToAmazonItem.objects.filter(author=user, feed_type=4, item_sku='SKU00002')
        self.assertEquals(1, len(query))
        self.assertEquals('BBB', query[0].external_product_id)
        self.assertEquals(4, query[0].feed_type)
        self.assertEquals(10, query[0].record_type)
        self.assertEquals(-1, query[0].csv_flag)
        self.assertEquals('SKU00002', query[0].current_purchase_item_id)
        self.assertEquals('SKU00002', query[0].purchase_item_id)

        query = YahooToAmazonItem.objects.filter(author=user, feed_type=4, item_sku='SKU0000X')
        self.assertEquals(1, len(query))
        self.assertEquals('ASIN2', query[0].external_product_id)


    def test_entry_raised_unknown_exception(self, mqueue, mlogger, mwait):
        user = self._init(status=1)
        result = YahooImportCSVResult.objects.get(author=user)
        err = Exception('unknown')
        with patch('yahoo.views.import_report_cancel_by_exception') as mcancel, \
                patch('yahoo.views.import_report_internal_delete_tmpdata', side_effect=err):
            yahoo.views.import_report_entry('/path/to', user)
            mcancel.assert_called_once_with(result, user, err)


    def test_import_report_internal_delete_tmpdata(self, mqueue, mlogger, mwait):
        ''' 失敗したデータが正常に削除・更新されるかのテスト '''
        user = self._init(status=1)
        # データ投入
        for record_type in range(9, 15):
            YahooToAmazonItem.objects.create(author=user, record_type=record_type)
        obj1 = YahooToAmazonItem.objects.create(author=user, 
            feed_type=4, item_sku='SKU00001', record_type=10)
        obj2 = YahooToAmazonItem.objects.create(author=user, 
            feed_type=4, item_sku='SKU00002', record_type=12)
        obj3 = YahooToAmazonItem.objects.create(author=user, 
            feed_type=3, item_sku='SKU00003', record_type=0)
 
        yahoo.views.import_report_internal_delete_tmpdata(user)

        # 失敗アイテムは在庫0に更新される
        item = YahooToAmazonItem.objects.get(id=obj1.id)
        self.assertEquals(3, item.feed_type)
        self.assertEquals(20, item.record_type)
        self.assertEquals(1, item.csv_flag)
        self.assertEquals(0, item.current_purchase_quantity)
        self.assertEquals(0, item.purchase_quantity)
        self.assertEquals(0, item.quantity)
        self.assertTrue(item.update_quantity_request)

        item = YahooToAmazonItem.objects.get(id=obj2.id)
        self.assertEquals(3, item.feed_type)
        self.assertEquals(20, item.record_type)
        self.assertEquals(1, item.csv_flag)
        self.assertEquals(0, item.current_purchase_quantity)
        self.assertEquals(0, item.purchase_quantity)
        self.assertEquals(0, item.quantity)
        self.assertTrue(item.update_quantity_request)
 
        # feed_type = 3 は更新されない
        item = YahooToAmazonItem.objects.get(id=obj3.id)
        self.assertEquals(3, item.feed_type)
        self.assertEquals(0, item.record_type)

        # record_status が 9, 14 と obj1, 2, 3 の計５個が残る
        query = YahooToAmazonItem.objects.all()
        self.assertEquals(5, len(query))

# ------------------------------------------------------------------
# Unknown Exception
# ------------------------------------------------------------------

    def test_raised_unknown_exception(self, mqueue, mlogger, mwait):
        user = self._init(status=0)
        result = YahooImportCSVResult.objects.get(author=user)
        err = MagicMock()
        
        with patch('yahoo.views.timezone.datetime') as mtz:
            mtz.now = MagicMock(return_value=datetime.datetime(2001, 1, 1, 0, 0, 0))
            yahoo.views.import_report_cancel_by_exception(result, user, err)

        mlogger.exception.assert_called_once_with(err)
        mlogger.error.assert_called_once_with(
            'ユーザー %s の処理中にエラーが発生したため、強制中断しました', user)

        result = YahooImportCSVResult.objects.get(author=user)
        self.assertEquals(result.result_message, 
            'ヤフオクリサーチ出品レポート取り込みに失敗しました。\nもう一度アップロードしてください。')
        self.assertEquals(result.status, 5)
        self.assertEquals(result.end_date, datetime.datetime(2001, 1, 1, 0, 0, 0))

# ------------------------------------------------------------------
# Yahoo task
# ------------------------------------------------------------------

    def test_yahoo_task_no_record(self, mqueue, mlogger, mwait):
        user = self._init(status=1)

        yahoo.views.import_report_internal_yahoo_task(user)

        (actuals, kwactuals) = mlogger.warn.call_args_list[0]
        self.assertEquals(actuals[0], 
            '事前に生成されているべきレコードが存在しません。 user=%s, status=2')


    def _start(self, mqueue, row=10, status=None, record_type=None):
        ''' 必要なデータを投入する '''
        user = self._init(status=1)
        def _row(idx):
            return ['SKU9{:04}'.format(idx), 'P{:04}'.format(idx), 'DUMMY', 'DUMMY']
        csvmock = MagicMock(return_value=[
            ['SKU_OR_ITEM_ID', 'PRODUCt_ID', 'DUMMY', 'DUMMY']
        ] + [ _row(idx+1) for idx in range(row) ])

        with patch('yahoo.views.print'), \
                patch('yahoo.views.open', mock_open()), \
                patch('yahoo.views.csv.reader', csvmock):
            yahoo.views.import_report_entry('/path/to', user)
        
        mqueue.reset_mock()

        # 後のテスト用に更新
        if status is not None:
            YahooImportCSVResult.objects.filter(author=user).update(status=status)
        if record_type is not None:
            YahooToAmazonItem.objects.filter(
                record_type=10, author=user).update(record_type=record_type)

        return user


    def test_yahoo_task_error_case(self, mqueue, mlogger, mwait):
        user = self._start(mqueue)

        BannedKeyword.objects.create(banned_keyword='banned')
        YahooExcludeSeller.objects.create(author=user, seller_id='bad.seller')

        mdt = MagicMock()
        mdt.now = MagicMock(return_value=datetime.datetime(2001, 1, 1, 0, 0, 0))
        mscraper = MagicMock()
        mscraper().get_products = MagicMock(side_effect=[
            [], [], [], [], [], [], [], [], 
            [{
                'title': 'banned title', 'bid_or_buy': 1000, 'current_price': 1200,
                'condition': '良い', 'seller': 'bood.seller',
            }], [{
                'title': 'title', 'bid_or_buy': 1000, 'current_price': 1200,
                'condition': '良い', 'seller': 'bad.seller',
            }] 
        ])

        # 事前にアイテムは全てある
        self.assertEquals(10, YahooToAmazonItem.objects.filter(author=user).count())
        with patch('yahoo.views.datetime', mdt), \
                patch('yahoo.views.timezone.datetime') as mtz, \
                patch('yahoo.views.YahooAuctionIdScraper', mscraper):
            mtz.now = MagicMock(return_value=datetime.datetime(2002, 1, 1, 0, 0, 0))
            yahoo.views.import_report_internal_yahoo_task(user)

        # 正常成功
        result = YahooImportCSVResult.objects.get(author=user)
        self.assertEquals(3, result.status)
        self.assertEquals('[2002-01-01 00:00:00] Yahooオークション情報検索終了', result.result_message)
        self.assertEquals(10, result.error_yahoo_items)
        self.assertEquals('\n'.join([
            'アイテム取得失敗(終了済): SKU9{:04}'.format(idx+1) for idx in range(8)
        ] + [
            '禁止ワード <banned> を含む商品です: SKU90009',
            '除外セラーID <bad.seller>: SKU90010',
        ]), result.error_yahoo_items_txt)

        # 該当アイテムは削除されない (あとで削除される)
        self.assertEquals(10, YahooToAmazonItem.objects.filter(author=user).count())


    def test_yahoo_task_exception_case(self, mqueue, mlogger, mwait):
        user = self._start(mqueue)

        mdt = MagicMock()
        mdt.now = MagicMock(return_value=datetime.datetime(2001, 1, 1, 0, 0, 0))
        products = [
            {'title': 'title', 'bid_or_buy': 1000, 'current_price': 1200, 'condition': '良い', 'seller': 'seller01' },
        ]
        mget_products = MagicMock(return_value=products)
        mprint = MagicMock()
        with patch('yahoo.views.print', mprint), \
                patch('yahoo.views.datetime', mdt), \
                patch('yahoo.views.timezone.datetime') as mtz, \
                patch('yahoo.views.YahooToAmazonItem.objects.filter') as mfilter, \
                patch('yahoo.views.YahooAuctionIdScraper.get_products', mget_products):
            # 例外の発生するデータを作る
            mtz.now = MagicMock(return_value=datetime.datetime(2002, 1, 1, 0, 0, 0))
            erritem = MagicMock()
            erritem.purchase_item_id = 'FAKE'
            erritem.save = MagicMock(side_effect=Exception('mock'))
            mfilter().order_by = MagicMock(return_value=[erritem])
            yahoo.views.import_report_internal_yahoo_task(user)

        # 正常成功だがItemはエラーとしてカウント
        result = YahooImportCSVResult.objects.get(author=user)
        self.assertEquals(3, result.status)
        self.assertEquals('[2002-01-01 00:00:00] Yahooオークション情報検索終了', result.result_message)
        self.assertEquals(1, result.error_yahoo_items)
        self.assertEquals('オークション情報取得中にエラーが発生: FAKE', result.error_yahoo_items_txt)



    def test_yahoo_task_completed_case(self, mqueue, mlogger, mwait):
        user = self._start(mqueue)

        mdt = MagicMock()
        mdt.now = MagicMock(return_value=datetime.datetime(2001, 1, 1, 0, 0, 0))
        products = [
            {'title': 'title', 'bid_or_buy': 1000, 'current_price': 1200, 'condition': '良い', 'seller': 'seller01' },
        ]
        mget_products = MagicMock(return_value=products)

        with patch('yahoo.views.datetime', mdt), \
                patch('yahoo.views.timezone.datetime') as mtz, \
                patch('yahoo.views.YahooAuctionIdScraper.get_products', mget_products):
            mtz.now = MagicMock(return_value=datetime.datetime(2002, 1, 1, 0, 0, 0))
            yahoo.views.import_report_internal_yahoo_task(user)

        # 正常成功
        result = YahooImportCSVResult.objects.get(author=user)
        self.assertEquals(3, result.status)
        self.assertEquals('[2002-01-01 00:00:00] Yahooオークション情報検索終了', result.result_message)
        self.assertEquals(0, result.error_yahoo_items)
        self.assertEquals('', result.error_yahoo_items_txt)

        items = YahooToAmazonItem.objects.filter(record_type=11, author=user)
        self.assertEquals(10, len(items))

        # 次タスクの確認
        (actuals, kwactuals) = mqueue().enqueue.call_args_list[0]
        self.assertEquals(yahoo.views.import_report_internal_asin_download_task, actuals[0])
        self.assertEquals(kwactuals['user'], user)


    def test_yahoo_task_continues(self, mqueue, mlogger, mwait):
        user = self._start(mqueue)

        mdt = MagicMock()
        dt1 = datetime.datetime(2001, 1, 1, 0, 0, 0)
        dt2 = dt1 + datetime.timedelta(
            seconds=settings.ASYNC_WORKER['TASK_RECOMMENDED_MAXIMUM_IMPORT_SECONDS'])
        mdt.now = MagicMock(side_effect=[
            dt1, # 開始時
            dt1, dt1, dt1, dt2 - datetime.timedelta(seconds=1), # 1件目直前 - 4件目直前
            dt2, # 5件目処理前 
        ])
        products = [
            {'title': 'title', 'bid_or_buy': 1000, 'current_price': 1200, 'condition': '良い', 'seller': 'seller01' },
        ]
        mget_products = MagicMock(return_value=products)

        items = YahooToAmazonItem.objects.filter(
            author = user, record_type = 10).order_by('id')

        # 先頭4件のIDが対象になる
        expected_ids = sorted([ item.id for item in items ])[:4]

        # 1回目の呼び出し: 先頭4件目処理後に中断される
        with patch('yahoo.views.datetime', mdt), \
                patch('yahoo.views.timezone.datetime') as mtz, \
                patch('yahoo.views.YahooAuctionIdScraper.get_products', mget_products):
            mtz.now = MagicMock(return_value=datetime.datetime(2002, 1, 1, 0, 0, 0))
            yahoo.views.import_report_internal_yahoo_task(user, 0)

        # 正常成功(1回目)
        result = YahooImportCSVResult.objects.get(author=user)
        self.assertEquals(2, result.status)
        self.assertEquals('[2002-01-01 00:00:00] Yahooオークション情報検索中', result.result_message)
        items = YahooToAmazonItem.objects.filter(record_type=11, author=user)
        self.assertEquals(4, len(items))
        self.assertEquals(sorted([ item.id for item in items ]), expected_ids)

        # 次タスクの確認
        (actuals, kwactuals) = mqueue().enqueue.call_args_list[0]
        self.assertEquals(yahoo.views.import_report_internal_yahoo_task, actuals[0])
        self.assertEquals(kwactuals['user'], user)
        latest_id = kwactuals['latest_id']

        mqueue.reset_mock()

        # 2回目前の確認
        items = YahooToAmazonItem.objects.filter(
            author = user, record_type = 10, id__gte=latest_id).order_by('id')
        ids = [ item.id for item in items ]
        self.assertEquals(6, len(ids))
        # latest_id は最後に処理されたIDなので含まれない
        self.assertTrue(ids[0] > latest_id)
        mdt.now = MagicMock(return_value=dt1)

        # 2回目の呼び出し: 最後まで実施
        with patch('yahoo.views.datetime', mdt), \
                patch('yahoo.views.timezone.datetime') as mtz, \
                patch('yahoo.views.YahooAuctionIdScraper.get_products', mget_products):
            mtz.now = MagicMock(return_value=datetime.datetime(2002, 1, 1, 0, 0, 0))
            yahoo.views.import_report_internal_yahoo_task(user, 0)

        # 正常成功(2回目)
        result = YahooImportCSVResult.objects.get(author=user)
        self.assertEquals(3, result.status)
        self.assertEquals('[2002-01-01 00:00:00] Yahooオークション情報検索終了', result.result_message)
        items = YahooToAmazonItem.objects.filter(record_type=11, author=user)
        self.assertEquals(10, len(items))


    def test_yahoo_task_raised_unknown_exception(self, mqueue, mlogger, mwait):
        user = self._start(mqueue)
        result = YahooImportCSVResult.objects.get(author=user)
        err = Exception('unknown')
        with patch('yahoo.views.import_report_cancel_by_exception') as mcancel, \
                patch('yahoo.views.YahooToAmazonItem.objects.filter', side_effect=err):
            yahoo.views.import_report_internal_yahoo_task(user)
            mcancel.assert_called_once_with(result, user, err)


# ------------------------------------------------------------------
# ASIN Donwload
# ------------------------------------------------------------------

    def _set_redis(self, user, count):
        # redis へデータ投入
        # 0001: Error
        # 0002 - 0010: Success
        def asin(r):
            cache_keys = [
                'status', 'title', 'brand', 'small_image', 
                'manufacturer', 'model', 'product_group']
            data = {k: 'Success' if k == 'status' else k for k in cache_keys}
            err = data.copy()
            err['status'] = 'Error'
            rkey = asynchelpers.rkey('Y2A', 'ASIN', user.username, 'ASIN0001')
            r.hmset(rkey, err)
            for idx in range(1, 10):
                rkey = asynchelpers.rkey(
                    'Y2A', 'ASIN', user.username, 'ASIN{:04}'.format(idx+1))
                r.hmset(rkey, data)

        def sku(r):
            price_keys = ['status', 'amount']
            data = {k: 'Success' if k == 'status' else k for k in price_keys}
            data['amount'] = '1234'
            err = data.copy()
            err['status'] = 'Error'
            rkey = asynchelpers.rkey('Y2A', 'SKU', user.username, 'SKU0001')
            r.hmset(rkey, err)
            for idx in range(1, 10):
                rkey = asynchelpers.rkey(
                    'Y2A', 'SKU', user.username, 'SKU{:04}'.format(idx+1))
                r.hmset(rkey, data)

        r = asynchelpers.get_data_redis()
        asin(r)
        sku(r)


    def _item(self, id, product_id, sku=None, feed_type=3):
        m = MagicMock()
        m.id = id
        m.external_product_id = product_id
        m.feed_type = feed_type
        if sku is not None:
            m.item_sku = sku
        return m


    def test_asin_download_no_record(self, mqueue, mlogger, mwait):
        user = self._init(status=2)

        yahoo.views.import_report_internal_asin_download_task(user)

        (actuals, kwactuals) = mlogger.warn.call_args_list[0]
        self.assertEquals(actuals[0], 
            '事前に生成されているべきレコードが存在しません。 user=%s, status=3 (download)')

    def test_asin_download_concat_asins(self, mqueue, mlogger, mwait):
        user = self._start(mqueue, status=3, record_type=11)

        m_utils = MagicMock()
        m_utils.get_mws_api = MagicMock()
        m_product_for_id = MagicMock(return_value={})
        mdt = MagicMock()
        mdt.now = MagicMock(return_value=datetime.datetime(2001, 1, 1, 0, 0, 0))

        with patch('yahoo.views.RichsUtils.get_mws_api'), \
                patch('yahoo.views.YahooToAmazonItem.objects.filter') as m_items, \
                patch('yahoo.views.MWSUtils.get_matching_product_for_id', m_product_for_id):
            m_items().order_by = MagicMock(return_value=[])
            yahoo.views.import_report_internal_asin_download_task(user)
            m_product_for_id.assert_not_called()

        m_product_for_id.reset_mock()

        with patch('yahoo.views.RichsUtils.get_mws_api'), \
                patch('yahoo.views.YahooToAmazonItem.objects.filter') as m_items, \
                patch('yahoo.views.MWSUtils.get_matching_product_for_id', m_product_for_id):
            m_items().order_by = MagicMock(return_value=[
                self._item(idx+1, 'ITEM{:04}'.format(idx+1)) for idx in range(5)
            ])
            yahoo.views.import_report_internal_asin_download_task(user)
            m_product_for_id.assert_called_once_with(
                'ASIN', ['ITEM0001', 'ITEM0002', 'ITEM0003', 'ITEM0004', 'ITEM0005'])

        m_product_for_id.reset_mock()

        with patch('yahoo.views.RichsUtils.get_mws_api'), \
                patch('yahoo.views.YahooToAmazonItem.objects.filter') as m_items, \
                patch('yahoo.views.MWSUtils.get_matching_product_for_id', m_product_for_id):
            m_items().order_by = MagicMock(return_value=[
                self._item(idx+1, 'ITEM{:04}'.format(idx+1)) for idx in range(6)
            ])
            yahoo.views.import_report_internal_asin_download_task(user)
            m_product_for_id.assert_any_call(
                'ASIN', ['ITEM0001', 'ITEM0002', 'ITEM0003', 'ITEM0004', 'ITEM0005'])
            m_product_for_id.assert_any_call(
                'ASIN', ['ITEM0006'])


    def test_asin_download_timeout_continue(self, mqueue, mlogger, mwait):
        user = self._start(mqueue, status=3, record_type=11)

        m_utils = MagicMock()
        m_utils.get_mws_api = MagicMock()
        m_product_for_id = MagicMock(return_value={
            'ASIN0001': {
                'status': 'Success', 'status?': 'Error' 
            },
            'ASIN0002': {
                'status': 'Unknown', 'status?': 'Error' 
            }
        })
        mdt = MagicMock()
        dt1 = datetime.datetime(2001, 1, 1, 0, 0, 0)
        dt2 = dt1 + datetime.timedelta(
            seconds=settings.ASYNC_WORKER['TASK_RECOMMENDED_MAXIMUM_IMPORT_SECONDS'])
        mdt.now = MagicMock(side_effect=[
            dt1, dt2 - datetime.timedelta(seconds=1), dt2, 
        ])


        with patch('yahoo.views.RichsUtils.get_mws_api'), \
                patch('yahoo.views.datetime', mdt), \
                patch('yahoo.views.timezone.datetime') as mtz, \
                patch('yahoo.views.YahooToAmazonItem.objects.filter') as m_items, \
                patch('yahoo.views.MWSUtils.get_matching_product_for_id', m_product_for_id):
            mtz.now = MagicMock(return_value=datetime.datetime(2002, 1, 1, 0, 0, 0))
            m_items().order_by = MagicMock(return_value=[
                self._item(idx+1, 'ITEM{:04}'.format(idx+1)) for idx in range(11)
            ])
            yahoo.views.import_report_internal_asin_download_task(user)
            
            # 継続タスクが呼び出される
            self.assertEquals(m_product_for_id.call_count, 2)
            m_product_for_id.assert_any_call(
                'ASIN', ['ITEM0001', 'ITEM0002', 'ITEM0003', 'ITEM0004', 'ITEM0005'])
            m_product_for_id.assert_any_call(
                'ASIN', ['ITEM0006', 'ITEM0007', 'ITEM0008', 'ITEM0009', 'ITEM0010'])

            result = YahooImportCSVResult.objects.get(author=user)
            self.assertEquals(3, result.status)
            self.assertEquals('[2002-01-01 00:00:00] Amazon ASIN情報を取得中', result.result_message)
            mqueue().enqueue.assert_called_once_with(
                yahoo.views.import_report_internal_asin_download_task, user=user, latest_id=10)

        mqueue.reset_mock()
        m_product_for_id.reset_mock()

        mdt.now = MagicMock(side_effect=[
            dt1, dt1
        ])

        with patch('yahoo.views.RichsUtils.get_mws_api'), \
                patch('yahoo.views.datetime', mdt), \
                patch('yahoo.views.timezone.datetime') as mtz, \
                patch('yahoo.views.YahooToAmazonItem.objects.filter') as m_items, \
                patch('yahoo.views.MWSUtils.get_matching_product_for_id', m_product_for_id):
            mtz.now = MagicMock(return_value=datetime.datetime(2002, 2, 1, 0, 0, 0))
            m_items().order_by = MagicMock(return_value=[
                self._item(idx+1, 'ITEM{:04}'.format(idx+1)) for idx in range(10, 11)
            ])
            yahoo.views.import_report_internal_asin_download_task(user, 10)

            # 次のタスクが呼び出される
            result = YahooImportCSVResult.objects.get(author=user)
            self.assertEquals(3, result.status)
            self.assertEquals('[2002-02-01 00:00:00] Amazon ASIN情報を取得中', result.result_message)
            m_product_for_id.assert_called_once_with('ASIN', ['ITEM0011'])
            mqueue().enqueue.assert_called_once_with(
                yahoo.views.import_report_internal_asin_update_task, user=user)

        # redis へ最低限のデータが投入されている
        rkey = asynchelpers.rkey('Y2A', 'ASIN', user.username, 'ASIN0001')
        cache = asynchelpers.get_data_redis().hgetall(rkey)
        self.assertEquals(cache.get(b'status'), b'Success')
        rkey = asynchelpers.rkey('Y2A', 'ASIN', user.username, 'ASIN0002')
        cache = asynchelpers.get_data_redis().hgetall(rkey)
        self.assertEquals(cache.get(b'status'), b'Unknown')


    def test_asin_download_raised_unknown_exception(self, mqueue, mlogger, mwait):
        user = self._start(mqueue, status=3, record_type=11)
        result = YahooImportCSVResult.objects.get(author=user)
        err = Exception('unknown')
        with patch('yahoo.views.import_report_cancel_by_exception') as mcancel, \
                patch('yahoo.views.RichsUtils.get_mws_api', side_effect=err):
            yahoo.views.import_report_internal_asin_download_task(user)
            mcancel.assert_called_once_with(result, user, err)


# ------------------------------------------------------------------
# ASIN Update
# ------------------------------------------------------------------

    def test_asin_update_no_record(self, mqueue, mlogger, mwait):
        user = self._init(status=2)

        yahoo.views.import_report_internal_asin_update_task(user)

        (actuals, kwactuals) = mlogger.warn.call_args_list[0]
        self.assertEquals(actuals[0], 
            '事前に生成されているべきレコードが存在しません。 user=%s, status=3 (update)')


    def test_asin_update_error_cases(self, mqueue, mlogger, mwait):
        user = self._start(mqueue, status=3, record_type=11)
        self._set_redis(user, 10)

        m_product_for_id = MagicMock(return_value={})
        mdt = MagicMock()
        mdt.now = MagicMock(return_value=datetime.datetime(2001, 1, 1, 0, 0, 0))

        with patch('yahoo.views.datetime', mdt), \
                patch('yahoo.views.timezone.datetime') as mtz, \
                patch('yahoo.views.YahooToAmazonItem.objects.filter') as m_items, \
                patch('yahoo.views.RichsUtils.download_to_yahoo_folder', side_effect=Exception('mock')):
            mtz.now = MagicMock(return_value=datetime.datetime(2002, 1, 1, 0, 0, 0))
            m_items().order_by = MagicMock(return_value=[
                # 0: cacheなし, 1: Error Statsu, 2: 例外発生
                self._item(idx, 'ASIN{:04}'.format(idx)) for idx in range(3)
            ])
            yahoo.views.import_report_internal_asin_update_task(user)

        result = YahooImportCSVResult.objects.get(author=user)
        self.assertEquals(result.status, 4)
        self.assertEquals('[2002-01-01 00:00:00] Amazon ASIN情報を更新終了', result.result_message)
        self.assertEquals(result.error_asins, 3)
        self.assertEquals(result.error_asins_text, 'ASIN0000\nASIN0001\nASIN0002')
        mlogger.debug.assert_called_once_with(
            '更新に失敗しました。 user=%s, external_product_id=%s', user, 'ASIN0002')


    def test_asin_update_success_cases(self, mqueue, mlogger, mwait):
        user = self._start(mqueue, status=3, record_type=11)
        self._set_redis(user, 10)

        m_product_for_id = MagicMock(return_value={})
        mdt = MagicMock()
        dt1 = datetime.datetime(2001, 1, 1, 0, 0, 0)
        dt2 = dt1 + datetime.timedelta(
            seconds=settings.ASYNC_WORKER['TASK_RECOMMENDED_MAXIMUM_IMPORT_SECONDS'])
        mdt.now = MagicMock(side_effect=[
            dt1, # 開始時
            dt1, dt2 - datetime.timedelta(seconds=1), # 1-2件目直前
            dt2, # 3件目直前
        ])

        with patch('yahoo.views.datetime', mdt), \
                patch('yahoo.views.timezone.datetime') as mtz, \
                patch('yahoo.views.YahooToAmazonItem.objects.filter') as m_items, \
                patch('yahoo.views.RichsUtils.download_to_yahoo_folder', return_value='image/url'):
            mtz.now = MagicMock(return_value=datetime.datetime(2002, 1, 1, 0, 0, 0))
            items = [
                self._item(idx, 'ASIN{:04}'.format(idx)) for idx in range(2, 5)
            ]
            m_items().order_by = MagicMock(return_value=items)
            yahoo.views.import_report_internal_asin_update_task(user)
            # 2件のみ処理が行われる
            items[0].save.assert_called_once()
            items[1].save.assert_called_once()
            items[2].save.assert_not_called()

        # ステータスを確認
        result = YahooImportCSVResult.objects.get(author=user)
        self.assertEquals(result.status, 3)
        self.assertEquals('[2002-01-01 00:00:00] Amazon ASIN情報を更新中', result.result_message)
        self.assertEquals(result.error_asins, 0)
        self.assertEquals(result.error_asins_text, '')
        mqueue().enqueue.assert_called_once_with(
            yahoo.views.import_report_internal_asin_update_task, user=user, latest_id=3)

        mdt.reset_mock()
        mqueue.reset_mock()

        # 継続時のケース
        mdt.now = MagicMock(return_value=dt1)
        with patch('yahoo.views.datetime', mdt), \
                patch('yahoo.views.YahooToAmazonItem.objects.filter') as m_items, \
                patch('yahoo.views.RichsUtils.download_to_yahoo_folder', return_value='image/url'):
            items = [
                self._item(idx, 'ASIN{:04}'.format(idx)) for idx in range(4, 5)
            ]
            m_items().order_by = MagicMock(return_value=items)
            yahoo.views.import_report_internal_asin_update_task(user, latest_id=3)
            # 1件のみ処理が行われる
            items[0].save.assert_called_once()

        # ステータスを確認
        result = YahooImportCSVResult.objects.get(author=user)
        self.assertEquals(result.status, 4)
        self.assertEquals(result.error_asins, 0)
        self.assertEquals(result.error_asins_text, '')
        mqueue().enqueue.assert_called_once_with(
            yahoo.views.import_report_internal_sku_download_task, user=user)


    def test_asin_update_raised_unknown_exception(self, mqueue, mlogger, mwait):
        user = self._start(mqueue, status=3, record_type=11)
        result = YahooImportCSVResult.objects.get(author=user)
        err = Exception('unknown')
        with patch('yahoo.views.import_report_cancel_by_exception') as mcancel, \
                patch('yahoo.views.YahooToAmazonItem.objects.filter', side_effect=err):
            yahoo.views.import_report_internal_asin_update_task(user)
            mcancel.assert_called_once_with(result, user, err)


# ------------------------------------------------------------------
# SKU Donwload
# ------------------------------------------------------------------

    def test_sku_download_no_record(self, mqueue, mlogger, mwait):
        user = self._init(status=2)

        yahoo.views.import_report_internal_sku_download_task(user)

        (actuals, kwactuals) = mlogger.warn.call_args_list[0]
        self.assertEquals(actuals[0], 
            '事前に生成されているべきレコードが存在しません。 user=%s, status=4 (download)')

    def test_asin_download_concat_sku(self, mqueue, mlogger, mwait):
        user = self._start(mqueue, status=4, record_type=12)

        m_utils = MagicMock()
        m_utils.get_mws_api = MagicMock()
        mdt = MagicMock()
        mdt.now = MagicMock(return_value=datetime.datetime(2001, 1, 1, 0, 0, 0))

        with patch('yahoo.views.RichsUtils', m_utils), \
                patch('yahoo.views.YahooToAmazonItem.objects.filter') as m_items, \
                patch('yahoo.views.MWSUtils.get_my_price_for_sku', return_value={}) as m_price_for_sku:
            m_items().order_by = MagicMock(return_value=[])
            yahoo.views.import_report_internal_sku_download_task(user)
            m_price_for_sku.assert_not_called()


        with patch('yahoo.views.RichsUtils', m_utils), \
                patch('yahoo.views.YahooToAmazonItem.objects.filter') as m_items, \
                patch('yahoo.views.MWSUtils.get_my_price_for_sku', return_value={}) as m_price_for_sku:
            m_items().order_by = MagicMock(return_value=[
                self._item(idx+1, 'ITEM{:04}'.format(idx+1), 
                    sku='SKU{:04}'.format(idx+1)) for idx in range(20)
            ])
            yahoo.views.import_report_internal_sku_download_task(user)
            m_price_for_sku.assert_called_once_with(
                ['SKU{:04}'.format(idx+1) for idx in range(20)] )


        with patch('yahoo.views.RichsUtils', m_utils), \
                patch('yahoo.views.YahooToAmazonItem.objects.filter') as m_items, \
                patch('yahoo.views.MWSUtils.get_my_price_for_sku', return_value={}) as m_price_for_sku:
            m_items().order_by = MagicMock(return_value=[
                self._item(idx+1, 'ITEM{:04}'.format(idx+1), 
                    sku='SKU{:04}'.format(idx+1)) for idx in range(21)
            ])
            yahoo.views.import_report_internal_sku_download_task(user)
            m_price_for_sku.assert_any_call(
                ['SKU{:04}'.format(idx+1) for idx in range(20)] )
            m_price_for_sku.assert_any_call(
                ['SKU0021'])


    def test_sku_download_timeout_continue(self, mqueue, mlogger, mwait):
        user = self._start(mqueue, status=4, record_type=12)

        m_utils = MagicMock()
        m_utils.get_mws_api = MagicMock()
        mdt = MagicMock()
        dt1 = datetime.datetime(2001, 1, 1, 0, 0, 0)
        dt2 = dt1 + datetime.timedelta(
            seconds=settings.ASYNC_WORKER['TASK_RECOMMENDED_MAXIMUM_IMPORT_SECONDS'])
        mdt.now = MagicMock(side_effect=[
            dt1, dt2 - datetime.timedelta(seconds=1), dt2, 
        ])
        m_price_for_sku = MagicMock(return_value={
            'SKU0001': {'status': 'Success'}, 
            'SKU0002': {'status': 'Unknown'},
        })


        with patch('yahoo.views.RichsUtils', m_utils), \
                patch('yahoo.views.datetime', mdt), \
                patch('yahoo.views.timezone.datetime') as mtz, \
                patch('yahoo.views.YahooToAmazonItem.objects.filter') as m_items, \
                patch('yahoo.views.MWSUtils.get_my_price_for_sku', m_price_for_sku):
            # data: SKU0001 - SKU0041
            mtz.now = MagicMock(return_value=datetime.datetime(2002, 1, 1, 0, 0, 0))
            m_items().order_by = MagicMock(return_value=[
                self._item(idx+1, 'ITEM{:04}'.format(idx+1),
                    sku='SKU{:04}'.format(idx+1)) for idx in range(41)
            ])
            yahoo.views.import_report_internal_sku_download_task(user)
            
            result = YahooImportCSVResult.objects.get(author=user)
            self.assertEquals(result.status, 4)
            self.assertEquals('[2002-01-01 00:00:00] Amazon SKU情報を取得中', result.result_message)

            # 継続タスクが呼び出される
            self.assertEquals(m_price_for_sku.call_count, 2)
            m_price_for_sku.assert_any_call(
                ['SKU{:04}'.format(idx+1) for idx in range(20)] )
            m_price_for_sku.assert_any_call(
                ['SKU{:04}'.format(idx+1) for idx in range(20, 40)] )
            mqueue().enqueue.assert_called_once_with(
                yahoo.views.import_report_internal_sku_download_task, user=user, latest_id=40)

        m_price_for_sku.reset_mock()
        mqueue.reset_mock()
        mdt.now = MagicMock(side_effect=[
            dt1, dt1
        ])

        with patch('yahoo.views.RichsUtils', m_utils), \
                patch('yahoo.views.datetime', mdt), \
                patch('yahoo.views.timezone.datetime') as mtz, \
                patch('yahoo.views.YahooToAmazonItem.objects.filter') as m_items, \
                patch('yahoo.views.MWSUtils.get_my_price_for_sku', m_price_for_sku):
            # data: SKU0041 - SKU0041
            mtz.now = MagicMock(return_value=datetime.datetime(2003, 1, 1, 0, 0, 0))
            m_items().order_by = MagicMock(return_value=[
                self._item(idx+1, 'ITEM{:04}'.format(idx+1),
                    sku='SKU{:04}'.format(idx+1)) for idx in range(40, 41)
            ])
            yahoo.views.import_report_internal_sku_download_task(user, 40)

            result = YahooImportCSVResult.objects.get(author=user)
            self.assertEquals(result.status, 4)
            self.assertEquals('[2003-01-01 00:00:00] Amazon SKU情報を取得中', result.result_message)

            # 次のタスクが呼び出される
            m_price_for_sku.assert_called_once_with(['SKU0041'])
            mqueue().enqueue.assert_called_once_with(
                yahoo.views.import_report_internal_sku_update_task, user=user)

        # redis へ最低限のデータが投入されている
        rkey = asynchelpers.rkey('Y2A', 'SKU', user.username, 'SKU0001')
        cache = asynchelpers.get_data_redis().hgetall(rkey)
        self.assertEquals(cache.get(b'status'), b'Success')
        rkey = asynchelpers.rkey('Y2A', 'SKU', user.username, 'SKU0002')
        cache = asynchelpers.get_data_redis().hgetall(rkey)
        self.assertEquals(cache.get(b'status'), b'Unknown')


    def test_sku_download_api_call_error(self, mqueue, mlogger, mwait):
        ''' AmazonのAPIコールリミットによってデータが取得できなかった場合 '''
        user = self._start(mqueue, status=4, record_type=12)

        m_utils = MagicMock()
        m_utils.get_mws_api = MagicMock()
        mdt = MagicMock()
        dt1 = datetime.datetime(2001, 1, 1, 0, 0, 0)
        mdt.now = MagicMock(return_value=dt1)

        with patch('yahoo.views.RichsUtils', m_utils), \
                patch('yahoo.views.datetime', mdt), \
                patch('yahoo.views.timezone.datetime') as mtz, \
                patch('yahoo.views.Functional.time.sleep'), \
                patch('yahoo.views.YahooToAmazonItem.objects.filter') as m_items, \
                patch('yahoo.views.MWSUtils.get_my_price_for_sku', side_effect=ValueError()):
            # data: SKU0001 - SKU0041
            mtz.now = MagicMock(return_value=datetime.datetime(2002, 1, 1, 0, 0, 0))
            m_items().order_by = MagicMock(return_value=[
                self._item(idx+1, 'ITEM{:04}'.format(idx+1),
                    sku='SKU{:04}'.format(idx+1)) for idx in range(41)
            ])
            yahoo.views.import_report_internal_sku_download_task(user)
            
            result = YahooImportCSVResult.objects.get(author=user)
            self.assertEquals(result.status, 4)
            self.assertEquals(
                '\n'.join([
                    'AmazonのAPI呼び出しが全て失敗: {}'.format(
                        ','.join([ 'SKU{:04}'.format(idx+1) for idx in range(0, 20) ])
                    ),
                    'AmazonのAPI呼び出しが全て失敗: {}'.format(
                        ','.join([ 'SKU{:04}'.format(idx+1) for idx in range(20, 40) ])
                    ),
                    'AmazonのAPI呼び出しが全て失敗: {}'.format(
                        ','.join([ 'SKU{:04}'.format(idx+1) for idx in range(40, 41) ])
                    ),
                ]),
                result.error_skus_text
            )

            # 次のタスクが呼び出される
            mqueue().enqueue.assert_called_once_with(
                yahoo.views.import_report_internal_sku_update_task, user=user)

        mqueue.reset_mock()
        def apicall(skus):
            # 個数によって例外になる
            if len(skus) >= 20:
                return {}
            raise ValueError()


        with patch('yahoo.views.RichsUtils', m_utils), \
                patch('yahoo.views.datetime', mdt), \
                patch('yahoo.views.timezone.datetime') as mtz, \
                patch('yahoo.views.Functional.time.sleep'), \
                patch('yahoo.views.YahooToAmazonItem.objects.filter') as m_items, \
                patch('yahoo.views.MWSUtils.get_my_price_for_sku', side_effect=apicall):
            # あまりの SKUS のみ失敗したケース
            # data: SKU0001 - SKU0039
            mtz.now = MagicMock(return_value=datetime.datetime(2002, 1, 1, 0, 0, 0))
            m_items().order_by = MagicMock(return_value=[
                self._item(idx+1, 'ITEM{:04}'.format(idx+1),
                    sku='SKU{:04}'.format(idx+1)) for idx in range(39)
            ])

            # エラーメッセージ部分を初期化
            result = YahooImportCSVResult.objects.get(author=user)
            result.error_skus_text = None
            result.save()

            yahoo.views.import_report_internal_sku_download_task(user)
            
            result = YahooImportCSVResult.objects.get(author=user)
            self.assertEquals(result.status, 4)
            self.assertEquals(
                '\n'.join([
                    'AmazonのAPI呼び出しが全て失敗: {}'.format(
                        ','.join([ 'SKU{:04}'.format(idx+1) for idx in range(20, 39) ])
                    ),
                ]),
                result.error_skus_text
            )

            # 次のタスクが呼び出される
            mqueue().enqueue.assert_called_once_with(
                yahoo.views.import_report_internal_sku_update_task, user=user)


    def test_sku_download_raised_unknown_exception(self, mqueue, mlogger, mwait):
        user = self._start(mqueue, status=4, record_type=12)
        result = YahooImportCSVResult.objects.get(author=user)
        err = Exception('unknown')
        with patch('yahoo.views.import_report_cancel_by_exception') as mcancel, \
                patch('yahoo.views.RichsUtils.get_mws_api', side_effect=err):
            yahoo.views.import_report_internal_sku_download_task(user)
            mcancel.assert_called_once_with(result, user, err)


# ------------------------------------------------------------------
# SKU Update
# ------------------------------------------------------------------

    def test_sku_update_no_record(self, mqueue, mlogger, mwait):
        user = self._init(status=2)

        yahoo.views.import_report_internal_sku_update_task(user)

        (actuals, kwactuals) = mlogger.warn.call_args_list[0]
        self.assertEquals(actuals[0], 
            '事前に生成されているべきレコードが存在しません。 user=%s, status=4 (update)')


    def test_sku_update_error_cases(self, mqueue, mlogger, mwait):
        user = self._start(mqueue, status=4, record_type=12)
        self._set_redis(user, 10)

        m_product_for_id = MagicMock(return_value={})
        mdt = MagicMock()
        mdt.now = MagicMock(return_value=datetime.datetime(2001, 1, 1, 0, 0, 0))

        AmazonDefaultSettings.objects.update_or_create(author=user, 
            defaults=dict(standard_price_points=100, new_item_points=11,
            new_auto_item_points=22, ride_item_points=33))

        with patch('yahoo.views.datetime', mdt), \
                patch('yahoo.views.YahooToAmazonItem.objects.filter') as m_items:
            # save のタイミングで例外が発生するように設定
            ms = [
                # 0: cacheなし, 1: Error Statsu, 2: 例外発生
                self._item(idx, 'ASIN{:04}'.format(idx), 'SKU{:04}'.format(idx)) for idx in range(3)
            ]
            for m in ms:
                m.save.side_effect = Exception('mock')
            m_items().order_by = MagicMock(return_value=ms)

            yahoo.views.import_report_internal_sku_update_task(user)
            self.assertEquals(33, ms[2].standard_price_points)

        result = YahooImportCSVResult.objects.get(author=user)
        self.assertEquals(result.status, 5)
        self.assertEquals(result.error_skus, 3)
        self.assertEquals(result.error_skus_text, 'SKU0000\nSKU0001\nSKU0002')
        mlogger.debug.assert_called_once_with(
            '更新に失敗しました。 user=%s, sku=%s', user, 'SKU0002')


    def test_sku_update_success_cases(self, mqueue, mlogger, mwait):
        user = self._start(mqueue, status=4, record_type=12)
        self._set_redis(user, 10)

        m_product_for_id = MagicMock(return_value={})
        mdt = MagicMock()
        dt1 = datetime.datetime(2001, 1, 1, 0, 0, 0)
        dt2 = dt1 + datetime.timedelta(
            seconds=settings.ASYNC_WORKER['TASK_RECOMMENDED_MAXIMUM_IMPORT_SECONDS'])
        mdt.now = MagicMock(side_effect=[
            dt1, # 関数開始時
            dt1, dt2 - datetime.timedelta(seconds=1), dt2, # 1 - 3回目の呼び出し直前
        ])

        AmazonDefaultSettings.objects.update_or_create(author=user, 
            defaults=dict(standard_price_points=100, new_item_points=11,
            new_auto_item_points=22, ride_item_points=None))

        with patch('yahoo.views.datetime', mdt), \
                patch('yahoo.views.timezone.datetime') as mtz, \
                patch('yahoo.views.YahooToAmazonItem.objects.filter') as m_items:
            mtz.now = MagicMock(return_value=datetime.datetime(2002, 1, 1, 0, 0, 0))
            items = [
                 # SKU0002 - SKU0004
                self._item(idx, 'ASIN{:04}'.format(idx), 'SKU{:04}'.format(idx)) for idx in range(2, 5)
            ]
            m_items().order_by = MagicMock(return_value=items)
            yahoo.views.import_report_internal_sku_update_task(user)
            # デフォルトポイントが設定
            self.assertEquals(100, items[0].standard_price_points)
            # 2件のみ処理が行われる
            items[0].save.assert_called_once()
            items[1].save.assert_called_once()
            items[2].save.assert_not_called()

        # ステータスを確認
        result = YahooImportCSVResult.objects.get(author=user)
        self.assertEquals(result.status, 4)
        self.assertEquals(result.result_message, '[2002-01-01 00:00:00] Amazon SKU情報を更新中')
        self.assertEquals(result.error_skus, 0)
        self.assertEquals(result.error_skus_text, '')
        mqueue().enqueue.assert_called_once_with(
            yahoo.views.import_report_internal_sku_update_task, user=user, latest_id=3)

        mdt.reset_mock()
        mqueue.reset_mock()

        # 継続時のケース
        mdt.now = MagicMock(return_value=dt1)
        with patch('yahoo.views.datetime', mdt), \
                patch('yahoo.views.timezone.datetime') as mtz, \
                patch('yahoo.views.YahooToAmazonItem.objects.filter') as m_items:
            mtz.now = MagicMock(return_value=datetime.datetime(2002, 1, 1, 0, 0, 0))
            items = [
                # SKU0004
                self._item(idx, 'ASIN{:04}'.format(idx), 'SKU{:04}'.format(idx), feed_type=4) for idx in range(4, 5)
            ]
            m_items().order_by = MagicMock(return_value=items)
            yahoo.views.import_report_internal_sku_update_task(user, latest_id=3)
            # 更新中から更新済にステータスを更新
            self.assertEquals(3, items[0].feed_type)
            # 1件のみ処理が行われる
            items[0].save.assert_called_once()

        # ステータスを確認
        result = YahooImportCSVResult.objects.get(author=user)
        self.assertEquals(result.status, 5)
        self.assertEquals(result.result_message, '[2002-01-01 00:00:00] Amazon SKU情報を更新完了')
        self.assertEquals(result.error_skus, 0)
        self.assertEquals(result.error_skus_text, '')
        mqueue().enqueue.assert_called_once_with(
            yahoo.views.import_report_internal_finalize, user=user)


    def test_sku_update_raised_unknown_exception(self, mqueue, mlogger, mwait):
        user = self._start(mqueue, status=4, record_type=12)
        result = YahooImportCSVResult.objects.get(author=user)
        err = Exception('unknown')
        with patch('yahoo.views.import_report_cancel_by_exception') as mcancel, \
                patch('yahoo.views.YahooToAmazonItem.objects.filter', side_effect=err):
            yahoo.views.import_report_internal_sku_update_task(user)
            mcancel.assert_called_once_with(result, user, err)


# ------------------------------------------------------------------
# Finalize 
# ------------------------------------------------------------------

    def test_finalize_no_record(self, mqueue, mlogger, mwait):
        user = self._init(status=4)

        yahoo.views.import_report_internal_finalize(user)

        (actuals, kwactuals) = mlogger.warn.call_args_list[0]
        self.assertEquals(actuals[0], 
            '事前に生成されているべきレコードが存在しません。 user=%s, status=5')

    def test_finalize_success(self, mqueue, mlogger, mwait):
        # データ準備
        user = self._start(mqueue, status=5, record_type=13)
        result = YahooImportCSVResult.objects.filter(author=user, status=5).first()
        result.success = 0
        result.error_record_numbers = 1
        result.error_record_numbers_txt = 'error number'
        result.over_skus = 2
        result.over_skus_text = 'over skus'
        result.duplicate_skus = 3
        result.duplicate_skus_txt = 'skus text'
        result.error_yahoo_items = 4
        result.error_yahoo_items_txt = 'Yahoo item'
        result.error_asins = 5
        result.error_asins_text  = 'asin text'
        result.error_skus = 6
        result.error_skus_text = 'skus text'
        result.save()

        self.assertEquals(10,
            YahooToAmazonItem.objects.filter(author=user, record_type=13).count())

        yahoo.views.import_report_internal_finalize(user)

        result = YahooImportCSVResult.objects.filter(author=user, status=5).first()
        self.assertEquals(0, 
            YahooToAmazonItem.objects.filter(author=user, record_type=13).count())
        self.assertIsNotNone(result.end_date)
        self.assertTrue(len(result.result_message) > 0)

    def test_finalize_output_sku_messages(self, mqueue, mlogger, mwait):
        # データ準備
        user = self._start(mqueue, status=5, record_type=13)
        result = YahooImportCSVResult.objects.filter(author=user, status=5).first()
        result.success = 0
        result.error_record_numbers = 1
        result.error_record_numbers_txt = 'error number'
        result.over_skus = 2
        result.over_skus_text = 'over skus'
        result.duplicate_skus = 3
        result.duplicate_skus_txt = 'skus text'
        result.error_yahoo_items = 4
        result.error_yahoo_items_txt = '\n'.join([
            '禁止ワード <サマンサタバサ> を含む商品です: v506998253',
            'アイテム取得失敗(終了済): w342364958',
            'アイテム取得失敗(終了済): h441695644',
            'アイテム取得失敗(終了済): 432775279',
            '除外セラーID <aria_est2004>: 366541663',
            'アイテム取得失敗(終了済): c781673524',
            '禁止ワード <抱き枕> を含む商品です: p746478781',
            '禁止ワード <抱き枕> を含む商品です: e405444906',
            '禁止ワード <disney> を含む商品です: b139955258',
            'アイテム取得失敗(終了済): p746242148',
            'アイテム取得失敗(終了済): d310047555',
            'アイテム取得失敗(終了済): h393770626',
            '禁止ワード <dvd> を含む商品です: m374839451',
            '禁止ワード <抱き枕> を含む商品です: 452978398',
            'アイテム取得失敗(終了済): q283450501',
            'アイテム取得失敗(終了済): p745087330',
            'アイテム取得失敗(終了済): m382284313',
            '禁止ワード <抱き枕> を含む商品です: w220649025',
            'アイテム取得失敗(終了済): d414155384',
            'アイテム取得失敗(終了済): u332524173',
            'アイテム取得失敗(終了済): o371971914',
            'アイテム取得失敗(終了済): u305431469',
            '禁止ワード <抱き枕> を含む商品です: p745956791',
            'アイテム取得失敗(終了済): c804421800',
            '禁止ワード <抱き枕> を含む商品です: n402457568',
            'アイテム取得失敗(終了済): t597503075',
            'アイテム取得失敗(終了済): c777977170',
            'アイテム取得失敗(終了済): g403666888',
            'アイテム取得失敗(終了済): f406634371',
            'アイテム取得失敗(終了済): g406472778',
            'アイテム取得失敗(終了済): q350725536',
            'アイテム取得失敗(終了済): w372789500',
            'アイテム取得失敗(終了済): d421069709',
            'アイテム取得失敗(終了済): q350360977',
            'アイテム取得失敗(終了済): w363449034',
            'アイテム取得失敗(終了済): p727363571',
            'アイテム取得失敗(終了済): b440123051',
            'アイテム取得失敗(終了済): f406382236',
            '禁止ワード <抱き枕> を含む商品です: w368852679',
            '禁止ワード <抱き枕> を含む商品です: x670927406',
            'アイテム取得失敗(終了済): o306582782',
            'アイテム取得失敗(終了済): n401430629',
            '禁止ワード <cd> を含む商品です: m377711554',
            'アイテム取得失敗(終了済): s706416086',
            'アイテム取得失敗(終了済): t702161432',
            'アイテム取得失敗(終了済): l578595502',
            'アイテム取得失敗(終了済): r378402542',
            'アイテム取得失敗(終了済): r381401613',
            'アイテム取得失敗(終了済): c791501178',
            'アイテム取得失敗(終了済): w372271835',
            'アイテム取得失敗(終了済): k421367889',
            '禁止ワード <cd> を含む商品です: x679565108',
            'アイテム取得失敗(終了済): v689094226',
            'アイテム取得失敗(終了済): o313888285',
            'アイテム取得失敗(終了済): e409606428',
            'アイテム取得失敗(終了済): n403221243',
            'アイテム取得失敗(終了済): c786217144',
            'アイテム取得失敗(終了済): u324242792',
            'アイテム取得失敗(終了済): u330562804',
            '禁止ワード <seiko> を含む商品です: s616516773',
            'アイテム取得失敗(終了済): j395012688',
            '禁止ワード <同人> を含む商品です: t531845626',
            '禁止ワード <同人> を含む商品です: o218819479',
            'アイテム取得失敗(終了済): c803486469',
            '禁止ワード <blu-ray> を含む商品です: m356024562',
            '禁止ワード <cd> を含む商品です: k228398749',
            '禁止ワード <バンダイ> を含む商品です: w90504060',
            'アイテム取得失敗(終了済): b195331125',
            'アイテム取得失敗(終了済): b285425385',
            '禁止ワード <dvd> を含む商品です: l466121472',
            '禁止ワード <seiko> を含む商品です: s506280551',
            '禁止ワード <抱き枕> を含む商品です: r200364029',
            '禁止ワード <cd> を含む商品です: g400422316',
            '禁止ワード <cd> を含む商品です: f403907710',
        ])
        result.error_asins = 5
        result.error_asins_text  = 'asin text'
        result.error_skus = 6
        result.error_skus_text = 'skus text'
        result.save()

        self.assertEquals(10,
            YahooToAmazonItem.objects.filter(author=user, record_type=13).count())

        yahoo.views.import_report_internal_finalize(user)

        result = YahooImportCSVResult.objects.filter(author=user, status=5).first()
        self.assertEquals(0, 
            YahooToAmazonItem.objects.filter(author=user, record_type=13).count())
        self.assertIsNotNone(result.end_date)
        assumed_result_message = '\n'.join([
            '正常商品取り込み:10件',
            'CSVフォーマットエラーの為削除:1件',
            '-- フォーマットエラー行数 --',
            'error number',
            '',
            '登録件数オーバの為削除:2件',
            '-- 登録件数オーバの為削除したSKU一覧 --',
            'over skus',
            '',
            '登録済みのSKUである為削除:3件',
            '-- 既に登録済みのSKU一覧 --',
            'skus text',
            '',
            '出品できない商品である為削除:4件',
            '- アイテム取得失敗(終了済): 49件',
            '- 禁止ワード <blu-ray> を含む商品です: 1件',
            '- 禁止ワード <cd> を含む商品です: 5件',
            '- 禁止ワード <disney> を含む商品です: 1件',
            '- 禁止ワード <dvd> を含む商品です: 2件',
            '- 禁止ワード <seiko> を含む商品です: 2件',
            '- 禁止ワード <サマンサタバサ> を含む商品です: 1件',
            '- 禁止ワード <バンダイ> を含む商品です: 1件',
            '- 禁止ワード <同人> を含む商品です: 2件',
            '- 禁止ワード <抱き枕> を含む商品です: 9件',
            '- 除外セラーID <aria_est2004>: 1件',
            '',
            '-- 削除が必要なSKU --',
            'v506998253',
            'w342364958',
            'h441695644',
            '432775279',
            '366541663',
            'c781673524',
            'p746478781',
            'e405444906',
            'b139955258',
            'p746242148',
            'd310047555',
            'h393770626',
            'm374839451',
            '452978398',
            'q283450501',
            'p745087330',
            'm382284313',
            'w220649025',
            'd414155384',
            'u332524173',
            'o371971914',
            'u305431469',
            'p745956791',
            'c804421800',
            'n402457568',
            't597503075',
            'c777977170',
            'g403666888',
            'f406634371',
            'g406472778',
            'q350725536',
            'w372789500',
            'd421069709',
            'q350360977',
            'w363449034',
            'p727363571',
            'b440123051',
            'f406382236',
            'w368852679',
            'x670927406',
            'o306582782',
            'n401430629',
            'm377711554',
            's706416086',
            't702161432',
            'l578595502',
            'r378402542',
            'r381401613',
            'c791501178',
            'w372271835',
            'k421367889',
            'x679565108',
            'v689094226',
            'o313888285',
            'e409606428',
            'n403221243',
            'c786217144',
            'u324242792',
            'u330562804',
            's616516773',
            'j395012688',
            't531845626',
            'o218819479',
            'c803486469',
            'm356024562',
            'k228398749',
            'w90504060',
            'b195331125',
            'b285425385',
            'l466121472',
            's506280551',
            'r200364029',
            'g400422316',
            'f403907710',
            '',
            'Amazonに登録されていないASINの為削除:5件',
            '-- 出品できないASIN一覧  --',
            'asin text',
            '',
            'Amazonに登録されていないSKUの為削除:6件',
            '-- 出品できないSKU一覧 --',
            'skus text',
            '',
        ])

        self.assertEquals(assumed_result_message, result.result_message)



