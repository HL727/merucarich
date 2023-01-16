#!/usr/bin/python 
# -*- coding: utf-8 -*-

import datetime

from unittest.mock import mock_open, patch, MagicMock
from django.forms.models import model_to_dict

from django.test import TestCase
from django.utils import timezone
from django.http import QueryDict
from django.conf import settings

import mercari.views 
from asyncworker import asynchelpers

from accounts.models import User, OfferReserchWatcher, StopRequest, BannedKeyword
from settings_amazon.models import AmazonAPI, ExcludeAsin, AmazonFeedPriceSettings, AmazonDefaultSettings
from mercari.models import MercariImportCSVResult, MercariToAmazonItem, MercariExcludeSeller

@patch('mercari.views.asynchelpers.wait')
@patch('mercari.views.logger')
@patch('mercari.views.asynchelpers.get_import_queue')
class BackgroundImportTaskTests(TestCase):
    ''' インポート処理の単体テスト '''

    def _init(self, username='ut01', status=0):
        user = User.objects.create_user(
            username='ut01', password='password', max_items=10)
        MercariImportCSVResult.objects.create(author=user, status=status)
        return user

# ------------------------------------------------------------------
# Entry
# ------------------------------------------------------------------

    def test_entry_no_record(self, mqueue, mlogger, mwait):
        user = self._init(status=0)

        mercari.views.import_item_entry('/path/to', user)

        (actuals, kwactuals) = mlogger.warn.call_args_list[0]
        self.assertEquals(actuals[0], 
            '事前に生成されているべきレコードが存在しません。 user=%s, status=1')


    def test_entry_fail_import_csv(self, mqueue, mlogger, mwait):
        user = self._init(status=1)
        for record_type in range(9, 15):
            MercariToAmazonItem.objects.create(author=user, record_type=record_type)

        with patch('mercari.views.print'), \
                patch('mercari.views.import_item_internal_csv_to_db', side_effect=Exception('mock')):
            mercari.views.import_item_entry('/path/to', user)

        result = MercariImportCSVResult.objects.get(author=user)
        self.assertEquals(5, result.status)

        self.assertEquals(0, MercariToAmazonItem.objects.filter(
            author=user, record_type__in = [10, 11, 12, 13]).count())
        self.assertEquals(2, MercariToAmazonItem.objects.filter(
            author=user, record_type__in = [9, 10, 11, 12, 13, 14]).count())

    def test_entry_import_csv(self, mqueue, mlogger, mwait):
        user = self._init(status=1)
        MercariToAmazonItem.objects.create(author=user, 
            record_type=0, item_sku='SKU00001', current_purchase_item_id='ITEM00001')
        MercariToAmazonItem.objects.create(author=user, 
            feed_type=3, csv_flag=1, item_sku='SKU00002',
            external_product_id='ASIN', current_purchase_item_id='SKU00002')
        MercariToAmazonItem.objects.create(author=user, 
            feed_type=3, csv_flag=1, item_sku='SKU00003', 
            external_product_id='ASIN', current_purchase_item_id='SKU00003')
        ExcludeAsin.objects.create(author=user, asin='X0001')

        csvmock = MagicMock(return_value=[
            # spec: first 2 lines are header. 
            ['ITEM_ID', 'SKU', 'EXTERNAL_PRODUCT_ID'], 
            ['ITEM_ID', 'SKU', 'EXTERNAL_PRODUCT_ID'], 
            # OK (skip) - 2 liines 
            [],
            ['    '],
            # ERROR - 5 lines 
            ['AAA'],
            ['AAA', 'BBB'],
            ['', 'BBB', 'CCC'],
            ['AAA', '', 'CCC'],
            ['AAA', 'BBB', ''],
            # ERROR by exclude_asin
            ['SKU99999', 'DUMMY', 'X0001'],
            # DUP - 5 lines
            ['SKU00001', 'DUP001',  'CCC'],
            ['ITEM00001', 'DUP002', 'CCC'],
            ['AAA', 'SKU00001', 'CCC'],
            ['AAA', 'ITEM00001', 'CCC'],
            ['SKU00002', 'DUMMY', 'ASIN'],
            # IMPORT - 7 lines
            ['SKU90001', 'P0001', 'EX001'],
            ['SKU90002', 'P0002', 'EX002'],
            ['SKU90003', 'P0003', 'EX003'],
            ['SKU90004', 'P0004', 'EX004'],
            ['SKU90005', 'P0005', 'EX005'],
            ['SKU90006', 'P0006', 'EX006'],
            ['SKU90007', 'P0007', 'EX007'],
            # OVER - 3 lines
            ['SKU90010', 'P0010', 'DUMMY'],
            ['SKU90011', 'P0011', 'DUMMY'],
            ['SKU90012', 'P0012', 'DUMMY'],
            # DUPLICATED but update - 2 lines
            ['SKU00002', 'SKU00002', 'ASIN'],
            ['SKU00003', 'SKU00003', 'ASIN'],
        ])

        with patch('mercari.views.print'), \
                patch('mercari.views.open', mock_open()), \
                patch('mercari.views.csv.reader', csvmock):
            mercari.views.import_item_entry('/path/to', user)

        result = MercariImportCSVResult.objects.get(author=user)
        self.assertEquals(2, result.status)

        self.assertEquals(6, result.error_record_numbers)
        self.assertEquals('5\n6\n7\n8\n9\n10 (除外ASIN<X0001>)', result.error_record_numbers_txt)
        self.assertEquals(5, result.duplicate_skus)
        self.assertEquals('DUP001\nDUP002\nSKU00001\nITEM00001\nDUMMY', result.duplicate_skus_txt)
        self.assertEquals(3, result.over_skus)
        self.assertEquals('P0010\nP0011\nP0012', result.over_skus_text)
        self.assertEquals(2, result.status)

        query = MercariToAmazonItem.objects.filter(author=user, feed_type=4, item_sku='SKU00002')
        self.assertEquals(1, len(query))
        self.assertEquals('SKU00002', query[0].current_purchase_item_id)
        self.assertEquals('SKU00002', query[0].purchase_item_id)
        query = MercariToAmazonItem.objects.filter(author=user, feed_type=4, item_sku='SKU00003')
        self.assertEquals(1, len(query))
        self.assertEquals('SKU00003', query[0].current_purchase_item_id)
        self.assertEquals('SKU00003', query[0].purchase_item_id)

        mqueue().enqueue.assert_called_once_with(
            mercari.views.import_item_internal_mercari_task, user=user)


    def test_entry_raised_unknown_exception(self, mqueue, mlogger, mwait):
        user = self._init(status=1)
        result = MercariImportCSVResult.objects.get(author=user)
        err = Exception('unknown')
        with patch('mercari.views.import_item_cancel_by_exception') as mcancel, \
                patch('mercari.views.import_item_internal_delete_tmpdata', side_effect=err):
            mercari.views.import_item_entry('/path/to', user)
            mcancel.assert_called_once_with(result, user, err)


    def test_import_report_internal_delete_tmpdata(self, mqueue, mlogger, mwait):
        ''' 失敗したデータが正常に削除・更新されるかのテスト '''
        user = self._init(status=1)
        # データ投入
        for record_type in range(9, 15):
            MercariToAmazonItem.objects.create(author=user, record_type=record_type)
        obj1 = MercariToAmazonItem.objects.create(author=user, 
            feed_type=4, item_sku='SKU00001', record_type=10)
        obj2 = MercariToAmazonItem.objects.create(author=user, 
            feed_type=4, item_sku='SKU00002', record_type=12)
        obj3 = MercariToAmazonItem.objects.create(author=user, 
            feed_type=3, item_sku='SKU00003', record_type=0)
 
        mercari.views.import_item_internal_delete_tmpdata(user)

        # 失敗アイテムは在庫0に更新される
        item = MercariToAmazonItem.objects.get(id=obj1.id)
        self.assertEquals(3, item.feed_type)
        self.assertEquals(20, item.record_type)
        self.assertEquals(1, item.csv_flag)
        self.assertEquals(0, item.current_purchase_quantity)
        self.assertEquals(0, item.purchase_quantity)
        self.assertEquals(0, item.quantity)
        self.assertTrue(item.update_quantity_request)

        item = MercariToAmazonItem.objects.get(id=obj2.id)
        self.assertEquals(3, item.feed_type)
        self.assertEquals(20, item.record_type)
        self.assertEquals(1, item.csv_flag)
        self.assertEquals(0, item.current_purchase_quantity)
        self.assertEquals(0, item.purchase_quantity)
        self.assertEquals(0, item.quantity)
        self.assertTrue(item.update_quantity_request)
 
        # feed_type = 3 は更新されない
        item = MercariToAmazonItem.objects.get(id=obj3.id)
        self.assertEquals(3, item.feed_type)
        self.assertEquals(0, item.record_type)

        # record_status が 9, 14 と obj1, 2, 3 の計５個が残る
        query = MercariToAmazonItem.objects.all()
        self.assertEquals(5, len(query))


# ------------------------------------------------------------------
# Unknown Exception
# ------------------------------------------------------------------

    def test_raised_unknown_exception(self, mqueue, mlogger, mwait):
        user = self._init(status=0)
        result = MercariImportCSVResult.objects.get(author=user)
        err = MagicMock()
        
        with patch('mercari.views.timezone.datetime') as mtz:
            mtz.now = MagicMock(return_value=datetime.datetime(2001, 1, 1, 0, 0, 0))
            mercari.views.import_item_cancel_by_exception(result, user, err)

        mlogger.exception.assert_called_once_with(err)
        mlogger.error.assert_called_once_with(
            'ユーザー %s の処理中にエラーが発生したため、強制中断しました', user)

        result = MercariImportCSVResult.objects.get(author=user)
        self.assertEquals(result.result_message, 
            'メルカリリサーチ商品取り込みに失敗しました。\nもう一度アップロードしてください。')
        self.assertEquals(result.status, 5)
        self.assertEquals(result.end_date, datetime.datetime(2001, 1, 1, 0, 0, 0))



# ------------------------------------------------------------------
# Mercari task
# ------------------------------------------------------------------

    def test_mercari_task_no_record(self, mqueue, mlogger, mwait):
        user = self._init(status=1)

        mercari.views.import_item_internal_mercari_task(user)

        mlogger.warn.assert_called_once_with(
            '事前に生成されているべきレコードが存在しません。 user=%s, status=2', user)

    def _start(self, mqueue, row=10, status=None, record_type=None):
        ''' 必要なデータを投入する '''
        user = self._init(status=1)
        def _row(idx):
            return ['ITEM9{:04}'.format(idx), 'P{:04}'.format(idx), 'EX{:03}'.format(idx)]
        # ITEM90001, ITEM90002, ...
        csvmock = MagicMock(return_value=[
            ['ITEM_ID', 'SKU', 'PRODUCt_ID'],
            ['ITEM_ID', 'SKU', 'PRODUCt_ID'],
        ] + [ _row(idx+1) for idx in range(row) ])

        with patch('mercari.views.print'), \
                patch('mercari.views.open', mock_open()), \
                patch('mercari.views.csv.reader', csvmock):
            mercari.views.import_item_entry('/path/to', user)
        
        mqueue.reset_mock()

        # 後のテスト用に更新
        if status is not None:
            MercariImportCSVResult.objects.filter(author=user).update(status=status)
        if record_type is not None:
            MercariToAmazonItem.objects.filter(
                record_type=10, author=user).update(record_type=record_type)

        return user


    def test_mercari_task_empty_case(self, mqueue, mlogger, mwait):
        user = self._start(mqueue)

        mdt = MagicMock()
        mdt.now = MagicMock(return_value=datetime.datetime(2001, 1, 1, 0, 0, 0))

        with patch('mercari.views.datetime', mdt), \
                patch('mercari.views.MercariItemScraper.get_products', return_value=[]):
            mercari.views.import_item_internal_mercari_task(user)

        # 正常成功
        result = MercariImportCSVResult.objects.get(author=user)
        self.assertEquals(3, result.status)
        self.assertEquals(10, result.error_mercari_items)
        self.assertEquals('\n'.join([
            'アイテム取得失敗(終了済): ITEM9{:04}'.format(idx+1) for idx in range(10)
        ]), result.error_mercari_items_txt)


    def test_mercari_task_error_case(self, mqueue, mlogger, mwait):
        user = self._start(mqueue)

        BannedKeyword.objects.create(banned_keyword='banned')
        MercariExcludeSeller.objects.create(author=user, seller_id='bad.seller')

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
        self.assertEquals(10, MercariToAmazonItem.objects.filter(author=user).count())
        with patch('mercari.views.print'), \
                patch('mercari.views.datetime', mdt), \
                patch('mercari.views.MercariItemScraper', mscraper):
            mercari.views.import_item_internal_mercari_task(user)

        # 正常成功
        result = MercariImportCSVResult.objects.get(author=user)
        self.assertEquals(3, result.status)
        self.assertEquals(10, result.error_mercari_items)
        self.assertEquals('\n'.join([
            'アイテム取得失敗(終了済): ITEM9{:04}'.format(idx+1) for idx in range(8)
        ] +[
            '禁止ワード <banned> を含む商品です: ITEM90009',
            '除外セラーID <bad.seller>: ITEM90010',
        ]), result.error_mercari_items_txt)

        # 該当アイテムは削除されない (あとで削除される)
        self.assertEquals(10, MercariToAmazonItem.objects.filter(author=user).count())


    def test_mercari_task_exception_case(self, mqueue, mlogger, mwait):
        user = self._start(mqueue)

        mdt = MagicMock()
        mdt.now = MagicMock(return_value=datetime.datetime(2001, 1, 1, 0, 0, 0))
        mprint = MagicMock()
        with patch('mercari.views.print', mprint), \
                patch('mercari.views.datetime', mdt), \
                patch('mercari.views.MercariToAmazonItem.objects.filter') as mfilter, \
                patch('mercari.views.MercariItemScraper.get_products', return_value=[{}]):
            # 例外の発生するデータを作る
            erritem = MagicMock()
            erritem.purchase_item_id = 'FAKE'
            erritem.save = MagicMock(side_effect=Exception('mock'))
            mfilter().order_by = MagicMock(return_value=[erritem])
            mercari.views.import_item_internal_mercari_task(user)

        # 正常成功だがItemはエラーとしてカウント
        result = MercariImportCSVResult.objects.get(author=user)
        self.assertEquals(3, result.status)
        self.assertEquals(1, result.error_mercari_items)
        self.assertEquals('メルカリ情報取得中にエラーが発生: FAKE', result.error_mercari_items_txt)


    def test_mercari_task_completed_case(self, mqueue, mlogger, mwait):
        user = self._start(mqueue)

        mdt = MagicMock()
        mdt.now = MagicMock(return_value=datetime.datetime(2001, 1, 1, 0, 0, 0))
        products = [
            {
                'title': 'title', 'price': 1000, 'sold': '', 'condition': '良い', 
                'seller': 'seller01', 'seller_name': 'セラー',
            }
        ]
        mget_products = MagicMock(return_value=products)

        with patch('mercari.views.datetime', mdt), \
                patch('mercari.views.MercariItemScraper.get_products', mget_products):
            mercari.views.import_item_internal_mercari_task(user)

        # 正常成功
        result = MercariImportCSVResult.objects.get(author=user)
        self.assertEquals(3, result.status)
        self.assertEquals(0, result.error_mercari_items)
        self.assertEquals('', result.error_mercari_items_txt)

        items = MercariToAmazonItem.objects.filter(record_type=11, author=user)
        self.assertEquals(10, len(items))

        # 次タスクの確認
        mqueue().enqueue.assert_called_once_with(
            mercari.views.import_item_internal_asin_download_task, user=user)


    def test_mercari_task_continues(self, mqueue, mlogger, mwait):
        user = self._start(mqueue)

        mdt = MagicMock()
        dt1 = datetime.datetime(2001, 1, 1, 0, 0, 0)
        dt2 = dt1 + datetime.timedelta(
            seconds=settings.ASYNC_WORKER['TASK_RECOMMENDED_MAXIMUM_IMPORT_SECONDS'])
        mdt.now = MagicMock(side_effect=[
            dt1, # 関数開始時
            dt1, dt1, dt1, dt2 - datetime.timedelta(seconds=1),  dt2, # 1 - 5回目呼び出し直前の判定 
        ])
        products = [
            {
                'title': 'title', 'price': 1000, 'sold': '', 'condition': '良い', 
                'seller': 'seller01', 'seller_name': 'セラー',
            }
        ]
        mget_products = MagicMock(return_value=products)

        items = MercariToAmazonItem.objects.filter(
            author = user, record_type = 10).order_by('id')

        # 先頭4件のIDが対象になる
        expected_ids = sorted([ item.id for item in items ])[:4]

        # 1回目の呼び出し: 先頭4件目処理後に中断される
        with patch('mercari.views.datetime', mdt), \
                patch('mercari.views.MercariItemScraper.get_products', mget_products):
            mercari.views.import_item_internal_mercari_task(user)

        # 正常成功(1回目)
        result = MercariImportCSVResult.objects.get(author=user)
        self.assertEquals(2, result.status)
        items = MercariToAmazonItem.objects.filter(record_type=11, author=user)
        self.assertEquals(4, len(items))
        self.assertEquals(sorted([ item.id for item in items ]), expected_ids)

        # 次タスクの確認
        (actuals, kwactuals) = mqueue().enqueue.call_args_list[0]
        self.assertEquals(mercari.views.import_item_internal_mercari_task, actuals[0])
        self.assertEquals(kwactuals['user'], user)
        latest_id = kwactuals['latest_id']

        mqueue.reset_mock()

        # 2回目前の確認
        items = MercariToAmazonItem.objects.filter(
            author = user, record_type = 10, id__gte=latest_id).order_by('id')
        ids = [ item.id for item in items ]
        self.assertEquals(6, len(ids))
        # latest_id は最後に処理されたIDなので含まれない
        self.assertTrue(ids[0] > latest_id)
        mdt.now = MagicMock(return_value=dt1)

        # 2回目の呼び出し: 最後まで実施
        with patch('mercari.views.datetime', mdt), \
                patch('mercari.views.MercariItemScraper.get_products', mget_products):
            mercari.views.import_item_internal_mercari_task(user)

        # 正常成功(2回目)
        result = MercariImportCSVResult.objects.get(author=user)
        self.assertEquals(3, result.status)
        items = MercariToAmazonItem.objects.filter(record_type=11, author=user)
        self.assertEquals(10, len(items))


    def test_mercari_task_raised_unknown_exception(self, mqueue, mlogger, mwait):
        user = self._start(mqueue)
        result = MercariImportCSVResult.objects.get(author=user)
        err = Exception('unknown')
        with patch('mercari.views.import_item_cancel_by_exception') as mcancel, \
                patch('mercari.views.MercariToAmazonItem.objects.filter', side_effect=err):
            mercari.views.import_item_internal_mercari_task(user)
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
            rkey = asynchelpers.rkey('M2A', 'ASIN', user.username, 'ASIN0001')
            r.hmset(rkey, err)
            for idx in range(1, 10):
                rkey = asynchelpers.rkey(
                    'M2A', 'ASIN', user.username, 'ASIN{:04}'.format(idx+1))
                r.hmset(rkey, data)

        def sku(r):
            price_keys = ['status', 'amount']
            data = {k: 'Success' if k == 'status' else k for k in price_keys}
            data['amount'] = '1234'
            err = data.copy()
            err['status'] = 'Error'
            rkey = asynchelpers.rkey('M2A', 'SKU', user.username, 'SKU0001')
            r.hmset(rkey, err)
            for idx in range(1, 10):
                rkey = asynchelpers.rkey(
                    'M2A', 'SKU', user.username, 'SKU{:04}'.format(idx+1))
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

        mercari.views.import_item_internal_asin_download_task(user)

        mlogger.warn.assert_called_once_with(
            '事前に生成されているべきレコードが存在しません。 user=%s, status=3 (download)', user)


    def test_asin_download_concat_asins(self, mqueue, mlogger, mwait):
        user = self._start(mqueue, status=3, record_type=11)

        m_product_for_id = MagicMock(return_value={})
        mdt = MagicMock()
        mdt.now = MagicMock(return_value=datetime.datetime(2001, 1, 1, 0, 0, 0))

        with patch('mercari.views.RichsUtils.get_mws_api'), \
                patch('mercari.views.MercariToAmazonItem.objects.filter') as m_items, \
                patch('mercari.views.MWSUtils.get_matching_product_for_id', m_product_for_id):
            m_items().order_by = MagicMock(return_value=[])
            mercari.views.import_item_internal_asin_download_task(user)
            m_product_for_id.assert_not_called()

        m_product_for_id.reset_mock()

        with patch('mercari.views.RichsUtils.get_mws_api'), \
                patch('mercari.views.MercariToAmazonItem.objects.filter') as m_items, \
                patch('mercari.views.MWSUtils.get_matching_product_for_id', m_product_for_id):
            m_items().order_by = MagicMock(return_value=[
                self._item(idx+1, 'ITEM{:04}'.format(idx+1)) for idx in range(5)
            ])
            mercari.views.import_item_internal_asin_download_task(user)
            m_product_for_id.assert_called_once_with(
                'ASIN', ['ITEM0001', 'ITEM0002', 'ITEM0003', 'ITEM0004', 'ITEM0005'])

        m_product_for_id.reset_mock()

        with patch('mercari.views.RichsUtils.get_mws_api'), \
                patch('mercari.views.MercariToAmazonItem.objects.filter') as m_items, \
                patch('mercari.views.MWSUtils.get_matching_product_for_id', m_product_for_id):
            m_items().order_by = MagicMock(return_value=[
                self._item(idx+1, 'ITEM{:04}'.format(idx+1)) for idx in range(6)
            ])
            mercari.views.import_item_internal_asin_download_task(user)
            m_product_for_id.assert_any_call(
                'ASIN', ['ITEM0001', 'ITEM0002', 'ITEM0003', 'ITEM0004', 'ITEM0005'])
            m_product_for_id.assert_any_call(
                'ASIN', ['ITEM0006'])


    def test_asin_download_timeout_continue(self, mqueue, mlogger, mwait):
        user = self._start(mqueue, status=3, record_type=11)

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

        with patch('mercari.views.RichsUtils.get_mws_api'), \
                patch('mercari.views.datetime', mdt), \
                patch('mercari.views.MercariToAmazonItem.objects.filter') as m_items, \
                patch('mercari.views.MWSUtils.get_matching_product_for_id', m_product_for_id):
            m_items().order_by = MagicMock(return_value=[
                self._item(idx+1, 'ITEM{:04}'.format(idx+1)) for idx in range(11)
            ])
            mercari.views.import_item_internal_asin_download_task(user)
            
            # 継続タスクが呼び出される
            self.assertEquals(m_product_for_id.call_count, 2)
            m_product_for_id.assert_any_call(
                'ASIN', ['ITEM0001', 'ITEM0002', 'ITEM0003', 'ITEM0004', 'ITEM0005'])
            m_product_for_id.assert_any_call(
                'ASIN', ['ITEM0006', 'ITEM0007', 'ITEM0008', 'ITEM0009', 'ITEM0010'])
            mqueue().enqueue.assert_called_once_with(
                mercari.views.import_item_internal_asin_download_task, user=user, latest_id=10)

        mqueue.reset_mock()
        m_product_for_id.reset_mock()

        mdt.now = MagicMock(side_effect=[
            dt1, dt1
        ])

        with patch('mercari.views.RichsUtils.get_mws_api'), \
                patch('mercari.views.datetime', mdt), \
                patch('mercari.views.MercariToAmazonItem.objects.filter') as m_items, \
                patch('mercari.views.MWSUtils.get_matching_product_for_id', m_product_for_id):
            m_items().order_by = MagicMock(return_value=[
                self._item(idx+1, 'ITEM{:04}'.format(idx+1)) for idx in range(10, 11)
            ])
            mercari.views.import_item_internal_asin_download_task(user, 10)

            # 次のタスクが呼び出される
            m_product_for_id.assert_called_once_with('ASIN', ['ITEM0011'])
            mqueue().enqueue.assert_called_once_with(
                mercari.views.import_item_internal_asin_update_task, user=user)

        # redis へ最低限のデータが投入されている
        rkey = asynchelpers.rkey('M2A', 'ASIN', user.username, 'ASIN0001')
        cache = asynchelpers.get_data_redis().hgetall(rkey)
        self.assertEquals(cache.get(b'status'), b'Success')
        rkey = asynchelpers.rkey('M2A', 'ASIN', user.username, 'ASIN0002')
        cache = asynchelpers.get_data_redis().hgetall(rkey)
        self.assertEquals(cache.get(b'status'), b'Unknown')



    def test_asin_download_raised_unknown_exception(self, mqueue, mlogger, mwait):
        user = self._start(mqueue, status=3, record_type=11)
        result = MercariImportCSVResult.objects.get(author=user)
        err = Exception('unknown')
        with patch('mercari.views.import_item_cancel_by_exception') as mcancel, \
                patch('mercari.views.RichsUtils.get_mws_api', side_effect=err):
            mercari.views.import_item_internal_asin_download_task(user)
            mcancel.assert_called_once_with(result, user, err)


# ------------------------------------------------------------------
# ASIN Update
# ------------------------------------------------------------------

    def test_asin_update_no_record(self, mqueue, mlogger, mwait):
        user = self._init(status=2)

        mercari.views.import_item_internal_asin_update_task(user)

        mlogger.warn.assert_called_once_with(
            '事前に生成されているべきレコードが存在しません。 user=%s, status=3 (update)', user)


    def test_asin_update_error_cases(self, mqueue, mlogger, mwait):
        user = self._start(mqueue, status=3, record_type=11)
        self._set_redis(user, 10)

        m_product_for_id = MagicMock(return_value={})
        mdt = MagicMock()
        mdt.now = MagicMock(return_value=datetime.datetime(2001, 1, 1, 0, 0, 0))

        with patch('mercari.views.datetime', mdt), \
                patch('mercari.views.MercariToAmazonItem.objects.filter') as m_items, \
                patch('mercari.views.RichsUtils.download_to_mercari_folder', side_effect=Exception('mock')):
            m_items().order_by = MagicMock(return_value=[
                # 0: cacheなし, 1: Error Status, 2: 例外発生
                self._item(idx, 'ASIN{:04}'.format(idx)) for idx in range(3)
            ])
            mercari.views.import_item_internal_asin_update_task(user)

        result = MercariImportCSVResult.objects.get(author=user)
        self.assertEquals(result.status, 4)
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
            dt1, # 関数呼び出し時
            dt1, dt2 - datetime.timedelta(seconds=1), dt2, # 1-3回目の直前に呼び出し
        ])

        with patch('mercari.views.datetime', mdt), \
                patch('mercari.views.MercariToAmazonItem.objects.filter') as m_items, \
                patch('mercari.views.RichsUtils.download_to_mercari_folder', return_value='image/url'):
            items = [
                self._item(idx, 'ASIN{:04}'.format(idx)) for idx in range(2, 5)
            ]
            m_items().order_by = MagicMock(return_value=items)
            mercari.views.import_item_internal_asin_update_task(user)
            # 2件のみ処理が行われる
            items[0].save.assert_called_once()
            items[1].save.assert_called_once()
            items[2].save.assert_not_called()

        # ステータスを確認
        result = MercariImportCSVResult.objects.get(author=user)
        self.assertEquals(result.status, 3)
        self.assertEquals(result.error_asins, 0)
        self.assertEquals(result.error_asins_text, '')
        mqueue().enqueue.assert_called_once_with(
            mercari.views.import_item_internal_asin_update_task, user=user, latest_id=3)

        mdt.reset_mock()
        mqueue.reset_mock()

        # 継続時のケース
        mdt.now = MagicMock(return_value=dt1)
        with patch('mercari.views.datetime', mdt), \
                patch('mercari.views.MercariToAmazonItem.objects.filter') as m_items, \
                patch('mercari.views.RichsUtils.download_to_mercari_folder', return_value='image/url'):
            items = [
                self._item(idx, 'ASIN{:04}'.format(idx), feed_type=4) for idx in range(4, 5)
            ]
            m_items().order_by = MagicMock(return_value=items)
            mercari.views.import_item_internal_asin_update_task(user, latest_id=3)
            # feed_type は 更新されない
            self.assertEquals(4, items[0].feed_type)
            # 1件のみ処理が行われる
            items[0].save.assert_called_once()

        # ステータスを確認
        result = MercariImportCSVResult.objects.get(author=user)
        self.assertEquals(result.status, 4)
        self.assertEquals(result.error_asins, 0)
        self.assertEquals(result.error_asins_text, '')
        mqueue().enqueue.assert_called_once_with(
            mercari.views.import_item_internal_sku_download_task, user=user)


    def test_asin_update_raised_unknown_exception(self, mqueue, mlogger, mwait):
        user = self._start(mqueue, status=3, record_type=11)
        result = MercariImportCSVResult.objects.get(author=user)
        err = Exception('unknown')
        with patch('mercari.views.import_item_cancel_by_exception') as mcancel, \
                patch('mercari.views.MercariToAmazonItem.objects.filter', side_effect=err):
            mercari.views.import_item_internal_asin_update_task(user)
            mcancel.assert_called_once_with(result, user, err)


# ------------------------------------------------------------------
# SKU Donwload
# ------------------------------------------------------------------

    def test_sku_download_no_record(self, mqueue, mlogger, mwait):
        user = self._init(status=2)

        mercari.views.import_item_internal_sku_download_task(user)

        mlogger.warn.assert_called_once_with(
            '事前に生成されているべきレコードが存在しません。 user=%s, status=4 (download)', user)


    def test_asin_download_concat_sku(self, mqueue, mlogger, mwait):
        user = self._start(mqueue, status=4, record_type=12)

        m_utils = MagicMock()
        m_utils.get_mws_api = MagicMock()
        mdt = MagicMock()
        mdt.now = MagicMock(return_value=datetime.datetime(2001, 1, 1, 0, 0, 0))

        # 長さが0の場合はそもそもコールされない
        with patch('mercari.views.RichsUtils', m_utils), \
                patch('mercari.views.MercariToAmazonItem.objects.filter') as m_items, \
                patch('mercari.views.MWSUtils.get_my_price_for_sku', return_value={}) as m_price_for_sku:
            m_items().order_by = MagicMock(return_value=[])
            mercari.views.import_item_internal_sku_download_task(user)
            m_price_for_sku.assert_not_called()


        # 長さが20の場合、1度だけAPI呼び出しが発生
        with patch('mercari.views.RichsUtils', m_utils), \
                patch('mercari.views.MercariToAmazonItem.objects.filter') as m_items, \
                patch('mercari.views.MWSUtils.get_my_price_for_sku', return_value={}) as m_price_for_sku:
            m_items().order_by = MagicMock(return_value=[
                self._item(idx+1, 'ITEM{:04}'.format(idx+1), 
                    sku='SKU{:04}'.format(idx+1)) for idx in range(20)
            ])
            mercari.views.import_item_internal_sku_download_task(user)
            m_price_for_sku.assert_called_once_with(
                ['SKU{:04}'.format(idx+1) for idx in range(20)] )

        # 長さが21の場合、2度に分けてAPI呼び出しが発生
        with patch('mercari.views.RichsUtils', m_utils), \
                patch('mercari.views.MercariToAmazonItem.objects.filter') as m_items, \
                patch('mercari.views.MWSUtils.get_my_price_for_sku', return_value={}) as m_price_for_sku:
            m_items().order_by = MagicMock(return_value=[
                self._item(idx+1, 'ITEM{:04}'.format(idx+1), 
                    sku='SKU{:04}'.format(idx+1)) for idx in range(21)
            ])
            mercari.views.import_item_internal_sku_download_task(user)
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


        with patch('mercari.views.RichsUtils', m_utils), \
                patch('mercari.views.datetime', mdt), \
                patch('mercari.views.MercariToAmazonItem.objects.filter') as m_items, \
                patch('mercari.views.MWSUtils.get_my_price_for_sku', m_price_for_sku):
            # data: SKU0001 - SKU0041
            m_items().order_by = MagicMock(return_value=[
                self._item(idx+1, 'ITEM{:04}'.format(idx+1),
                    sku='SKU{:04}'.format(idx+1)) for idx in range(41)
            ])
            mercari.views.import_item_internal_sku_download_task(user)
            
            # 継続タスクが呼び出される
            self.assertEquals(m_price_for_sku.call_count, 2)
            m_price_for_sku.assert_any_call(
                ['SKU{:04}'.format(idx+1) for idx in range(20)] )
            m_price_for_sku.assert_any_call(
                ['SKU{:04}'.format(idx+1) for idx in range(20, 40)] )
            mqueue().enqueue.assert_called_once_with(
                mercari.views.import_item_internal_sku_download_task, user=user, latest_id=40)

        m_price_for_sku.reset_mock()
        mqueue.reset_mock()
        mdt.now = MagicMock(side_effect=[
            dt1, dt1
        ])

        with patch('mercari.views.RichsUtils', m_utils), \
                patch('mercari.views.datetime', mdt), \
                patch('mercari.views.MercariToAmazonItem.objects.filter') as m_items, \
                patch('mercari.views.MWSUtils.get_my_price_for_sku', m_price_for_sku):
            # data: SKU0041 - SKU0041
            m_items().order_by = MagicMock(return_value=[
                self._item(idx+1, 'ITEM{:04}'.format(idx+1),
                    sku='SKU{:04}'.format(idx+1)) for idx in range(40, 41)
            ])
            mercari.views.import_item_internal_sku_download_task(user, 40)

            # 次のタスクが呼び出される
            m_price_for_sku.assert_called_once_with(['SKU0041'])
            mqueue().enqueue.assert_called_once_with(
                mercari.views.import_item_internal_sku_update_task, user=user)

        # redis へ最低限のデータが投入されている
        rkey = asynchelpers.rkey('M2A', 'SKU', user.username, 'SKU0001')
        cache = asynchelpers.get_data_redis().hgetall(rkey)
        self.assertEquals(cache.get(b'status'), b'Success')
        rkey = asynchelpers.rkey('M2A', 'SKU', user.username, 'SKU0002')
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

        with patch('mercari.views.RichsUtils', m_utils), \
                patch('mercari.views.datetime', mdt), \
                patch('mercari.views.timezone.datetime') as mtz, \
                patch('mercari.views.Functional.time.sleep'), \
                patch('mercari.views.MercariToAmazonItem.objects.filter') as m_items, \
                patch('mercari.views.MWSUtils.get_my_price_for_sku', side_effect=ValueError()):
            # data: SKU0001 - SKU0041
            mtz.now = MagicMock(return_value=datetime.datetime(2002, 1, 1, 0, 0, 0))
            m_items().order_by = MagicMock(return_value=[
                self._item(idx+1, 'ITEM{:04}'.format(idx+1),
                    sku='SKU{:04}'.format(idx+1)) for idx in range(41)
            ])

            mercari.views.import_item_internal_sku_download_task(user)

            result = MercariImportCSVResult.objects.get(author=user)
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
                mercari.views.import_item_internal_sku_update_task, user=user)

        mqueue.reset_mock()
        def apicall(skus):
            # 個数によって例外になる
            if len(skus) >= 20:
                return {}
            raise ValueError()


        with patch('mercari.views.RichsUtils', m_utils), \
                patch('mercari.views.datetime', mdt), \
                patch('mercari.views.timezone.datetime') as mtz, \
                patch('mercari.views.Functional.time.sleep'), \
                patch('mercari.views.MercariToAmazonItem.objects.filter') as m_items, \
                patch('mercari.views.MWSUtils.get_my_price_for_sku', side_effect=apicall):
            # あまりの SKUS のみ失敗したケース
            # data: SKU0001 - SKU0039
            mtz.now = MagicMock(return_value=datetime.datetime(2002, 1, 1, 0, 0, 0))
            m_items().order_by = MagicMock(return_value=[
                self._item(idx+1, 'ITEM{:04}'.format(idx+1),
                    sku='SKU{:04}'.format(idx+1)) for idx in range(39)
            ])

            # エラーメッセージ部分を初期化
            result = MercariImportCSVResult.objects.get(author=user)
            result.error_skus_text = None
            result.save()

            mercari.views.import_item_internal_sku_download_task(user)
            
            result = MercariImportCSVResult.objects.get(author=user)
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
                mercari.views.import_item_internal_sku_update_task, user=user)


    def test_sku_download_raised_unknown_exception(self, mqueue, mlogger, mwait):
        user = self._start(mqueue, status=4, record_type=12)
        result = MercariImportCSVResult.objects.get(author=user)
        err = Exception('unknown')
        with patch('mercari.views.import_item_cancel_by_exception') as mcancel, \
                patch('mercari.views.RichsUtils.get_mws_api', side_effect=err):
            mercari.views.import_item_internal_sku_download_task(user)
            mcancel.assert_called_once_with(result, user, err)


# ------------------------------------------------------------------
# SKU Update
# ------------------------------------------------------------------

    def test_sku_update_no_record(self, mqueue, mlogger, mwait):
        user = self._init(status=2)

        mercari.views.import_item_internal_sku_update_task(user)

        mlogger.warn.assert_called_once_with(
            '事前に生成されているべきレコードが存在しません。 user=%s, status=4 (update)', user)


    def test_sku_update_error_cases(self, mqueue, mlogger, mwait):
        user = self._start(mqueue, status=4, record_type=12)
        self._set_redis(user, 10)

        m_product_for_id = MagicMock(return_value={})
        mdt = MagicMock()
        mdt.now = MagicMock(return_value=datetime.datetime(2001, 1, 1, 0, 0, 0))

        AmazonDefaultSettings.objects.update_or_create(author=user, 
            defaults=dict(standard_price_points=100, new_item_points=11,
            new_auto_item_points=22, ride_item_points=33))

        with patch('mercari.views.datetime', mdt), \
                patch('mercari.views.MercariToAmazonItem.objects.filter') as m_items:
            # save のタイミングで例外が発生するように設定
            ms = [
                # 0: cacheなし, 1: Error Statsu, 2: 例外発生
                self._item(idx, 'ASIN{:04}'.format(idx), 'SKU{:04}'.format(idx)) for idx in range(3)
            ]
            for m in ms:
                m.save.side_effect = Exception('mock')
            m_items().order_by = MagicMock(return_value=ms)

            mercari.views.import_item_internal_sku_update_task(user)
            self.assertEquals(33, ms[2].standard_price_points)

        result = MercariImportCSVResult.objects.get(author=user)
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
            dt1, # 関数呼び出し直後
            dt1, dt2 - datetime.timedelta(seconds=1), dt2, # 1-3回目呼び出し直前
        ])

        AmazonDefaultSettings.objects.update_or_create(author=user, 
            defaults=dict(standard_price_points=100, new_item_points=11,
            new_auto_item_points=22, ride_item_points=None))

        with patch('mercari.views.datetime', mdt), \
                patch('mercari.views.MercariToAmazonItem.objects.filter') as m_items:
            items = [
                 # SKU0002 - SKU0004
                self._item(idx, 'ASIN{:04}'.format(idx), 'SKU{:04}'.format(idx)) for idx in range(2, 5)
            ]
            m_items().order_by = MagicMock(return_value=items)
            mercari.views.import_item_internal_sku_update_task(user)
            # デフォルトポイントが設定
            self.assertEquals(100, items[0].standard_price_points)
            # 2件のみ処理が行われる (時刻)
            items[0].save.assert_called_once()
            items[1].save.assert_called_once()
            items[2].save.assert_not_called()

        # ステータスを確認
        result = MercariImportCSVResult.objects.get(author=user)
        self.assertEquals(result.status, 4)
        self.assertEquals(result.error_skus, 0)
        self.assertEquals(result.error_skus_text, '')
        mqueue().enqueue.assert_called_once_with(
            mercari.views.import_item_internal_sku_update_task, user=user, latest_id=3)

        mdt.reset_mock()
        mqueue.reset_mock()

        # 継続時のケース
        mdt.now = MagicMock(return_value=dt1)
        with patch('mercari.views.datetime', mdt), \
                patch('mercari.views.MercariToAmazonItem.objects.filter') as m_items:
            items = [
                # SKU0004
                self._item(idx, 'ASIN{:04}'.format(idx), 'SKU{:04}'.format(idx), feed_type=4) for idx in range(4, 5)
            ]
            m_items().order_by = MagicMock(return_value=items)
            mercari.views.import_item_internal_sku_update_task(user, latest_id=3)
            # feed_type は 3 に更新される
            self.assertEquals(3, items[0].feed_type)
            # 1件のみ処理が行われる
            items[0].save.assert_called_once()

        # ステータスを確認
        result = MercariImportCSVResult.objects.get(author=user)
        self.assertEquals(result.status, 5)
        self.assertEquals(result.error_skus, 0)
        self.assertEquals(result.error_skus_text, '')
        mqueue().enqueue.assert_called_once_with(
            mercari.views.import_item_internal_finalize, user=user)


    def test_sku_update_raised_unknown_exception(self, mqueue, mlogger, mwait):
        user = self._start(mqueue, status=4, record_type=12)
        result = MercariImportCSVResult.objects.get(author=user)
        err = Exception('unknown')
        with patch('mercari.views.import_item_cancel_by_exception') as mcancel, \
                patch('mercari.views.MercariToAmazonItem.objects.filter', side_effect=err):
            mercari.views.import_item_internal_sku_update_task(user)
            mcancel.assert_called_once_with(result, user, err)


# ------------------------------------------------------------------
# Finalize 
# ------------------------------------------------------------------

    def test_finalize_no_record(self, mqueue, mlogger, mwait):
        user = self._init(status=4)

        mercari.views.import_item_internal_finalize(user)

        mlogger.warn.assert_called_once_with(
            '事前に生成されているべきレコードが存在しません。 user=%s, status=5', user)

    def test_finalize_success(self, mqueue, mlogger, mwait):
        # データ準備
        user = self._start(mqueue, status=5, record_type=13)
        result = MercariImportCSVResult.objects.filter(author=user, status=5).first()
        result.success = 0
        result.error_record_numbers = 1
        result.error_record_numbers_txt = 'error number'
        result.over_skus = 2
        result.over_skus_text = 'over skus'
        result.duplicate_skus = 3
        result.duplicate_skus_txt = 'skus text'
        result.error_mercari_items = 4
        result.error_mercari_items_txt = 'Mercari item'
        result.error_asins = 5
        result.error_asins_text  = 'asin text'
        result.error_skus = 6
        result.error_skus_text = 'skus text'
        result.save()

        self.assertEquals(10,
            MercariToAmazonItem.objects.filter(author=user, record_type=13).count())

        mercari.views.import_item_internal_finalize(user)

        result = MercariImportCSVResult.objects.filter(author=user, status=5).first()
        self.assertEquals(0, 
            MercariToAmazonItem.objects.filter(author=user, record_type=13).count())
        self.assertIsNotNone(result.end_date)
        self.assertTrue(len(result.result_message) > 0)


    def test_finalize_output_sku_messages(self, mqueue, mlogger, mwait):
        # データ準備
        user = self._start(mqueue, status=5, record_type=13)
        result = MercariImportCSVResult.objects.filter(author=user, status=5).first()
        result.success = 0
        result.error_record_numbers = 1
        result.error_record_numbers_txt = 'error number'
        result.over_skus = 2
        result.over_skus_text = 'over skus'
        result.duplicate_skus = 3
        result.duplicate_skus_txt = 'skus text'
        result.error_mercari_items = 5
        result.error_mercari_items_txt = '\r\n'.join([
            'アイテム取得失敗(終了済): m432775279',
            '除外セラーID <aria_est2004>: m366541663',
            'アイテム取得失敗(終了済): m781673524',
            '関係ないテキストは対象外',
            '禁止ワード <抱き枕> を含む商品です: m746478781',
            '禁止ワード <抱き枕> を含む商品です: m405444906',
        ])
        result.error_asins = 5
        result.error_asins_text  = 'asin text'
        result.error_skus = 6
        result.error_skus_text = 'skus text'
        result.save()

        self.assertEquals(10,
            MercariToAmazonItem.objects.filter(author=user, record_type=13).count())

        mercari.views.import_item_internal_finalize(user)

        result = MercariImportCSVResult.objects.filter(author=user, status=5).first()
        self.assertEquals(0, 
            MercariToAmazonItem.objects.filter(author=user, record_type=13).count())
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
            '出品できない商品である為削除:5件',
            '- アイテム取得失敗(終了済): 2件',
            '- 禁止ワード <抱き枕> を含む商品です: 2件',
            '- 除外セラーID <aria_est2004>: 1件',
            '',
            '-- 削除が必要なSKU --',
            'm432775279',
            'm366541663',
            'm781673524',
            'm746478781',
            'm405444906',
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


        self.assertTrue(len(result.result_message) > 0)


