#!/usr/bin/python
# -*- coding: utf-8 -*-

import datetime

from unittest.mock import mock_open, patch, MagicMock
from django.forms.models import model_to_dict

from django.test import TestCase
from django.utils import timezone

from accounts.models import User, OfferReserchWatcher, StopRequest, BannedKeyword, StockCheckStatus
from mercari.models import MercariToAmazonItem

import richs_utils.InventoryMercari

@patch('richs_utils.InventoryMercari.sleep')
@patch('richs_utils.InventoryMercari.logger')
@patch('richs_utils.InventoryMercari.connections')
class InventoryMercariTests(TestCase):

    def _reset(self, *mocks):
        for m in mocks:
            m.reset_mock()


    def test_item_scraper_result(self, mconn, mlogger, msleep):
        ''' Scraper 生成関数のチェック '''
        ips = []
        with patch('richs_utils.InventoryMercari.MercariItemScraper') as m:
            richs_utils.InventoryMercari.create_item_scraper(0, ips)
            richs_utils.InventoryMercari.create_item_scraper(1, ips)
            richs_utils.InventoryMercari.create_item_scraper(2, ips)
            (actuals, kwactuals) = m.call_args_list[0]
            self.assertEquals(len(actuals), 0)
            (actuals, kwactuals) = m.call_args_list[1]
            self.assertEquals(len(actuals), 0)
            (actuals, kwactuals) = m.call_args_list[2]
            self.assertEquals(len(actuals), 0)

        ips = ['127.0.0.1', '127.0.0.2']
        with patch('richs_utils.InventoryMercari.MercariItemScraper') as m:
            richs_utils.InventoryMercari.create_item_scraper(0, ips)
            richs_utils.InventoryMercari.create_item_scraper(1, ips)
            richs_utils.InventoryMercari.create_item_scraper(2, ips)
            richs_utils.InventoryMercari.create_item_scraper(3, ips)
            richs_utils.InventoryMercari.create_item_scraper(4, ips)
            richs_utils.InventoryMercari.create_item_scraper(5, ips)
            richs_utils.InventoryMercari.create_item_scraper(6, ips)
            richs_utils.InventoryMercari.create_item_scraper(7, ips)
            (actuals, kwactuals) = m.call_args_list[0]
            self.assertEquals(len(actuals), 0)
            (actuals, kwactuals) = m.call_args_list[1]
            self.assertEquals(actuals[0], '127.0.0.1')
            (actuals, kwactuals) = m.call_args_list[2]
            self.assertEquals(actuals[0], '127.0.0.2')
            (actuals, kwactuals) = m.call_args_list[3]
            self.assertEquals(len(actuals), 0)
            (actuals, kwactuals) = m.call_args_list[4]
            self.assertEquals(actuals[0], '127.0.0.1')
            (actuals, kwactuals) = m.call_args_list[5]
            self.assertEquals(actuals[0], '127.0.0.2')
            (actuals, kwactuals) = m.call_args_list[6]
            self.assertEquals(len(actuals), 0)


    def test_search_scraper_result(self, mconn, mlogger, msleep):
        ''' Scraper 生成関数のチェック '''
        ips = []
        with patch('richs_utils.InventoryMercari.MercariSearchScraper') as m:
            richs_utils.InventoryMercari.create_search_scraper(0, ips)
            richs_utils.InventoryMercari.create_search_scraper(1, ips)
            richs_utils.InventoryMercari.create_search_scraper(2, ips)
            (actuals, kwactuals) = m.call_args_list[0]
            self.assertEquals(len(actuals), 0)
            (actuals, kwactuals) = m.call_args_list[1]
            self.assertEquals(len(actuals), 0)
            (actuals, kwactuals) = m.call_args_list[2]
            self.assertEquals(len(actuals), 0)

        ips = ['127.0.0.1', '127.0.0.2']
        with patch('richs_utils.InventoryMercari.MercariSearchScraper') as m:
            richs_utils.InventoryMercari.create_search_scraper(0, ips)
            richs_utils.InventoryMercari.create_search_scraper(1, ips)
            richs_utils.InventoryMercari.create_search_scraper(2, ips)
            richs_utils.InventoryMercari.create_search_scraper(3, ips)
            richs_utils.InventoryMercari.create_search_scraper(4, ips)
            richs_utils.InventoryMercari.create_search_scraper(5, ips)
            richs_utils.InventoryMercari.create_search_scraper(6, ips)
            richs_utils.InventoryMercari.create_search_scraper(7, ips)
            (actuals, kwactuals) = m.call_args_list[0]
            self.assertEquals(len(actuals), 0)
            (actuals, kwactuals) = m.call_args_list[1]
            self.assertEquals(actuals[0], '127.0.0.1')
            (actuals, kwactuals) = m.call_args_list[2]
            self.assertEquals(actuals[0], '127.0.0.2')
            (actuals, kwactuals) = m.call_args_list[3]
            self.assertEquals(len(actuals), 0)
            (actuals, kwactuals) = m.call_args_list[4]
            self.assertEquals(actuals[0], '127.0.0.1')
            (actuals, kwactuals) = m.call_args_list[5]
            self.assertEquals(actuals[0], '127.0.0.2')
            (actuals, kwactuals) = m.call_args_list[6]
            self.assertEquals(len(actuals), 0)


    def test_executable_run_user_inventory_check(self, mconn, mlogger, msleep):
        ''' 関数が最後まで流れるかをチェック '''
        sku = 'dummy'
        scraper = MagicMock()
        scraper.get_products = MagicMock(return_value=[])
        user = MagicMock()
        config = MagicMock()
        exclude_sellers = []

        with patch('richs_utils.InventoryMercari.create_item_scraper', side_effect=Exception('ERR')):
            richs_utils.InventoryMercari._run_user_inventory_check(user, sku, 0, [], config, exclude_sellers)
            mlogger.warn.assert_called_once_with(
                '在庫確認のスクレイピングに失敗しました: %s:%s', user, sku)
            mconn.close_all.assert_called_once()
            self._reset(mconn, mlogger, msleep)

        scraper = MagicMock()
        scraper.get_products = MagicMock(return_value=[{'sold': 'False', 'item_status': 'on_sale'}])
        with patch('richs_utils.InventoryMercari.create_item_scraper', return_value=scraper), \
                patch('richs_utils.InventoryMercari.MercariToAmazonItem.objects.filter') as mf:
            richs_utils.InventoryMercari._run_user_inventory_check(user, sku, 0, [], config, exclude_sellers)
            mf().update.assert_not_called()
            mconn.close_all.assert_called_once()
            self._reset(mconn, mlogger, msleep)

        scraper = MagicMock()
        scraper.get_products = MagicMock(return_value=[{'sold': 'True', 'item_status': 'sold_out'}])
        with patch('richs_utils.InventoryMercari.create_item_scraper', return_value=scraper), \
                patch('richs_utils.InventoryMercari.MercariToAmazonItem.objects.filter') as mf:
            richs_utils.InventoryMercari._run_user_inventory_check(user, sku, 0, [], config, exclude_sellers)
            mf().update.assert_called_once_with(research_request=True)
            mconn.close_all.assert_called_once()
            self._reset(mconn, mlogger, msleep)

        scraper = MagicMock()
        scraper.get_products = MagicMock(return_value=[{'sold': 'False', 'item_status': 'trading'}])
        with patch('richs_utils.InventoryMercari.create_item_scraper', return_value=scraper), \
                patch('richs_utils.InventoryMercari.MercariToAmazonItem.objects.filter') as mf:
            richs_utils.InventoryMercari._run_user_inventory_check(user, sku, 0, [], config, exclude_sellers)
            mf().update.assert_called_once_with(research_request=True)
            mconn.close_all.assert_called_once()
            self._reset(mconn, mlogger, msleep)

        scraper = MagicMock()
        scraper.get_products = MagicMock(return_value=[{'sold': 'False', 'item_status': 'trading'}])
        with patch('richs_utils.InventoryMercari.create_item_scraper', return_value=scraper), \
                patch('richs_utils.InventoryMercari._internal_run_stock_update') as mupdate, \
                patch('richs_utils.InventoryMercari.MercariToAmazonItem.objects.filter') as mf:
            richs_utils.InventoryMercari._run_user_inventory_check(user, sku, 0, [], config, exclude_sellers, with_update=True)
            mf().update.assert_called_once_with(research_request=True)
            mupdate.assert_called_once()
            mconn.close_all.assert_called_once()
            self._reset(mconn, mlogger, msleep)

        scraper = MagicMock()
        scraper.get_products = MagicMock(return_value=[{'sold': 'False', 'item_status': 'trading'}])
        with patch('richs_utils.InventoryMercari.create_item_scraper', return_value=scraper), \
                patch('richs_utils.InventoryMercari._internal_run_stock_update') as mupdate, \
                patch('richs_utils.InventoryMercari.MercariToAmazonItem.objects.filter') as mf:
            richs_utils.InventoryMercari._run_user_inventory_check(user, sku, 0, [], config, exclude_sellers, with_update=False)
            mf().update.assert_called_once_with(research_request=True)
            mupdate.assert_not_called()
            mconn.close_all.assert_called_once()
            self._reset(mconn, mlogger, msleep)


    def test_can_buy_item(self, mconn, mlogger, msleep):
        ''' メルカリアイテムの購入可否をチェック '''
        self.assertFalse(richs_utils.InventoryMercari._can_buy_item([]))

        item = { 'sold': 'True' }
        self.assertFalse(richs_utils.InventoryMercari._can_buy_item([item]))
        item = { 'sold': 'False', 'item_status': 'sold_out' }
        self.assertFalse(richs_utils.InventoryMercari._can_buy_item([item]))
        item = { 'sold': 'False', 'item_status': 'trading' }
        self.assertFalse(richs_utils.InventoryMercari._can_buy_item([item]))
        item = { 'sold': 'False', 'item_status': 'stop' }
        self.assertFalse(richs_utils.InventoryMercari._can_buy_item([item]))
        item = { 'sold': 'False', 'item_status': 'cancel' }
        self.assertFalse(richs_utils.InventoryMercari._can_buy_item([item]))

        item = { 'sold': 'False', 'item_status': 'on_sale' }
        self.assertTrue(richs_utils.InventoryMercari._can_buy_item([item]))
        item = { 'sold': 'False', 'item_status': 'unknown' }
        self.assertTrue(richs_utils.InventoryMercari._can_buy_item([item]))


    def test_executable_run_stock_update(self, mconn, mlogger, msleep):
        ''' 関数が最後まで流れるかをチェック '''
        sku = 'dummy'
        scraper = MagicMock()
        scraper.get_products = MagicMock(return_value=[])
        user = MagicMock()
        config = MagicMock()
        exclude_seller = MagicMock()

        with patch('richs_utils.InventoryMercari.MercariToAmazonItem.objects.filter') as mf:
            mf().order_by = MagicMock(return_value=[])
            richs_utils.InventoryMercari._run_stock_update(user, sku, 0, [], config, exclude_seller)
            mlogger.debug.assert_any_call('SKU: %s was updated or deleted', sku)
            self._reset(mconn, mlogger, msleep)

        scraper = MagicMock()
        scraper.get_products = MagicMock(side_effect=Exception('err'))
        with patch('richs_utils.InventoryMercari.create_search_scraper', return_value=scraper), \
                patch('richs_utils.InventoryMercari.make_url', return_value='dummyurl'), \
                patch('richs_utils.InventoryMercari.MercariToAmazonItem.objects.filter') as mf:
            mf().order_by = MagicMock(return_value=[MagicMock()])
            richs_utils.InventoryMercari._run_stock_update(user, sku, 0, [], config, exclude_seller)
            mlogger.warn.assert_any_call('Mercariへの問い合わせに失敗: %s:%s', user, sku)
            self._reset(mconn, mlogger, msleep)

        scraper = MagicMock()
        scraper.get_products = MagicMock(return_value=[])
        with patch('richs_utils.InventoryMercari.create_search_scraper', return_value=scraper), \
                patch('richs_utils.InventoryMercari.make_url', return_value='dummyurl'), \
                patch('richs_utils.InventoryMercari.MercariToAmazonItem.objects.filter') as mf:
            mf().order_by = MagicMock(return_value=[MagicMock()])
            richs_utils.InventoryMercari._run_stock_update(user, sku, 0, [], config, exclude_seller)
            mlogger.info.assert_any_call('Not found candidates: %s:%s', user, sku)
            self._reset(mconn, mlogger, msleep)

        scraper = MagicMock()
        scraper.get_products = MagicMock(return_value=['dummy'])
        mitem = MagicMock()
        mitem.main_image_url = 'dummy.png'
        with patch('richs_utils.InventoryMercari.create_search_scraper', return_value=scraper), \
                patch('richs_utils.InventoryMercari.make_url', return_value='dummyurl'), \
                patch('richs_utils.InventoryMercari._search_new_stock', return_value=(False, None, None)), \
                patch('richs_utils.InventoryMercari._update_no_stock') as mupdate, \
                patch('richs_utils.InventoryMercari.RichsUtils.get_mercari_image_folder', return_value='/tmp'), \
                patch('richs_utils.InventoryMercari.MercariToAmazonItem.objects.filter') as mf:
            mf().order_by = MagicMock(return_value=[mitem])
            richs_utils.InventoryMercari._run_stock_update(user, sku, 0, [], config, exclude_seller)
            mupdate.assert_called_once_with([mitem])
            self._reset(mconn, mlogger, msleep)

        scraper = MagicMock()
        scraper.get_products = MagicMock(return_value=['dummy'])
        mitem = MagicMock()
        mitem.main_image_url = 'dummy.png'
        with patch('richs_utils.InventoryMercari.create_search_scraper', return_value=scraper), \
                patch('richs_utils.InventoryMercari.make_url', return_value='dummyurl'), \
                patch('richs_utils.InventoryMercari._search_new_stock', return_value=(True, None, None)), \
                patch('richs_utils.InventoryMercari._update_stock') as mupdate, \
                patch('richs_utils.InventoryMercari.RichsUtils.get_mercari_image_folder', return_value='/tmp'), \
                patch('richs_utils.InventoryMercari.MercariToAmazonItem.objects.filter') as mf:
            mf().order_by = MagicMock(return_value=[mitem])
            richs_utils.InventoryMercari._run_stock_update(user, sku, 0, [], config, exclude_seller)
            mupdate.assert_called_once_with([mitem], None, None)
            self._reset(mconn, mlogger, msleep)


    def test_executable_search_new_stock(self, mconn, mlogger, msleep):
        ''' 関数が最後まで流れるかをチェック '''
        sku = 'dummy'
        item_scraper = MagicMock()
        user = MagicMock()
        config = MagicMock()
        config.similarity_threshold = 0.8
        config.rateing_threshold = 95

        exclude_seller = MagicMock()
        exclude_seller.seller_id = 'bad.seller'
        exclude_sellers = [ exclude_seller ]

        BannedKeyword.objects.create(banned_keyword='banned')
        amazon_image = '/tmp/dummy.png'
        item = MagicMock()
        candidates = []

        mdownloader = MagicMock()
        mdownloader.get = MagicMock(return_value='/tmp/dummy2.png')

        # 空の場合
        with patch('richs_utils.InventoryMercari.RichsUtils.get_tmp_image_folder', return_value='/tmp'), \
                patch('richs_utils.InventoryMercari.ImageDownloader') as ignore_downloader:
            (detect, detail, value) = richs_utils.InventoryMercari._search_new_stock(
                user, config, exclude_sellers, item_scraper, amazon_image, item, candidates)
            self.assertFalse(detect)
            ignore_downloader().__enter__.assert_not_called()
            self._reset(mconn, mlogger, msleep)

        # 全て除外される場合
        candidates = [
            {'title': 'banned title', 'item_id': 'ITEM', 'images': ['path/to/0'], 'seller': 'good.seller'},
            {'title': 'title', 'item_id': 'ITEM', 'images': ['path/to/1'], 'seller': 'bad.seller'},
        ]
        with patch('richs_utils.InventoryMercari.RichsUtils.get_tmp_image_folder', return_value='/tmp'), \
                patch('richs_utils.InventoryMercari.ImageDownloader') as ignore_downloader:
            (detect, detail, value) = richs_utils.InventoryMercari._search_new_stock(
                user, config, exclude_sellers, item_scraper, amazon_image, item, candidates)
            self.assertFalse(detect)
            ignore_downloader().__enter__.assert_not_called()
            self._reset(mconn, mlogger, msleep)

        candidates = [
            {'title': 'title', 'item_id': 'ITEM', 'images': ['path/to/0'], 'seller': 'good.seller'},
            {'title': 'title', 'item_id': 'ITEM', 'images': ['path/to/1'], 'seller': 'good.seller'},
            {'title': 'title', 'item_id': 'ITEM', 'images': ['path/to/2'], 'seller': 'good.seller'},
            {'title': 'title', 'item_id': 'ITEM', 'images': ['path/to/3'], 'seller': 'good.seller'},
            {'title': 'title', 'item_id': 'ITEM', 'images': ['path/to/4'], 'seller': 'good.seller'},
            {'title': 'title', 'item_id': 'ITEM', 'images': ['path/to/5'], 'seller': 'good.seller'},
            {'title': 'title', 'item_id': 'ITEM', 'images': ['path/to/6'], 'seller': 'good.seller'},
            {'title': 'title', 'item_id': 'ITEM', 'images': ['path/to/7'], 'seller': 'good.seller'},
            {'title': 'title', 'item_id': 'ITEM', 'images': ['path/to/8'], 'seller': 'good.seller'},
            {'title': 'title', 'item_id': 'ITEM', 'images': ['path/to/9'], 'seller': 'good.seller'},
            {'title': 'title', 'item_id': 'ITEM', 'images': ['path/to/A'], 'seller': 'good.seller'},
            {'title': 'title', 'item_id': 'ITEM', 'images': ['path/to/B'], 'seller': 'good.seller'},
        ]
        with patch('richs_utils.InventoryMercari.RichsUtils.get_tmp_image_folder', return_value='/tmp'), \
                patch('richs_utils.InventoryMercari.ItemImageComparator.similar_fast', return_value=(False, 0.0)), \
                patch('richs_utils.InventoryMercari.ImageDownloader', mdownloader):
            (detect, detail, value) = richs_utils.InventoryMercari._search_new_stock(
                user, config, exclude_sellers, item_scraper, amazon_image, item, candidates)
            self.assertFalse(detect)
            self._reset(mconn, mlogger, msleep)

        item_scraper.get_products = MagicMock(return_value=[])
        with patch('richs_utils.InventoryMercari.RichsUtils.get_tmp_image_folder', return_value='/tmp'), \
                patch('richs_utils.InventoryMercari.ItemImageComparator.similar_fast', return_value=(True, 0.9)), \
                patch('richs_utils.InventoryMercari.ImageDownloader', mdownloader):
            (detect, detail, value) = richs_utils.InventoryMercari._search_new_stock(
                user, config, exclude_sellers, item_scraper, amazon_image, item, candidates)
            self.assertFalse(detect)
            self._reset(mconn, mlogger, msleep)

        item_scraper.get_products = MagicMock(return_value=[
            {'seller': 'xxxxxxxx', 'rate_percent': '99', 'sold': 'False', 'item_status': 'trading'},
        ])
        with patch('richs_utils.InventoryMercari.RichsUtils.get_tmp_image_folder', return_value='/tmp'), \
                patch('richs_utils.InventoryMercari.ItemImageComparator.similar_fast', return_value=(True, 0.9)), \
                patch('richs_utils.InventoryMercari.ImageDownloader', mdownloader):
            (detect, detail, value) = richs_utils.InventoryMercari._search_new_stock(
                user, config, exclude_sellers, item_scraper, amazon_image, item, candidates)
            self.assertFalse(detect)
            self._reset(mconn, mlogger, msleep)

        item_scraper.get_products = MagicMock(return_value=[
            {'seller': 'xxxxxxxx', 'rate_percent': '90', 'sold': 'False', 'item_status': 'on_sale'},
        ])
        with patch('richs_utils.InventoryMercari.RichsUtils.get_tmp_image_folder', return_value='/tmp'), \
                patch('richs_utils.InventoryMercari.ItemImageComparator.similar_fast', return_value=(True, 0.9)), \
                patch('richs_utils.InventoryMercari.ImageDownloader', mdownloader):
            (detect, detail, value) = richs_utils.InventoryMercari._search_new_stock(
                user, config, exclude_sellers, item_scraper, amazon_image, item, candidates)
            self.assertFalse(detect)
            self._reset(mconn, mlogger, msleep)

        item_scraper.get_products = MagicMock(return_value=[
            {'seller': 'xxxxxxxx', 'rate_percent': '99', 'sold': 'False', 'item_status': 'on_sale'},
        ])
        with patch('richs_utils.InventoryMercari.RichsUtils.get_tmp_image_folder', return_value='/tmp'), \
                patch('richs_utils.InventoryMercari.ItemImageComparator.similar_fast', return_value=(True, 0.9)), \
                patch('richs_utils.InventoryMercari.ItemImageComparator.similar', return_value=(False, [])), \
                patch('richs_utils.InventoryMercari.get_stock_update_info', return_value=0), \
                patch('richs_utils.InventoryMercari.ImageDownloader', mdownloader):
            (detect, detail, value) = richs_utils.InventoryMercari._search_new_stock(
                user, config, exclude_sellers, item_scraper, amazon_image, item, candidates)
            self.assertFalse(detect)
            self._reset(mconn, mlogger, msleep)

        expected_detail = {
            'seller': 'xxxxxxxx', 'rate_percent': '99', 'sold': 'False', 'item_status': 'on_sale'
        }
        item_scraper.get_products = MagicMock(return_value=[expected_detail])
        with patch('richs_utils.InventoryMercari.RichsUtils.get_tmp_image_folder', return_value='/tmp'), \
                patch('richs_utils.InventoryMercari.ItemImageComparator.similar_fast', return_value=(True, 0.9)), \
                patch('richs_utils.InventoryMercari.ItemImageComparator.similar', return_value=(True, [])), \
                patch('richs_utils.InventoryMercari.get_stock_update_info', return_value=0), \
                patch('richs_utils.InventoryMercari.ImageDownloader', mdownloader):
            (detect, detail, value) = richs_utils.InventoryMercari._search_new_stock(
                user, config, exclude_sellers, item_scraper, amazon_image, item, candidates)
            self.assertTrue(detect)
            self.assertEqual(expected_detail, detail)
            self.assertEqual(value, 0.9)
            self._reset(mconn, mlogger, msleep)


    def test_executable_get_stock_update_info(self, mconn, mlogger, msleep):
        ''' 関数が最後まで流れるかをチェック '''
        item = MagicMock()
        item.item_sku = 'XYZ'
        item.current_purchase_item_id = 'ABC'
        item.purchase_price = 12344
        candidate = {
            'item_id': 'xyz', 'price': '12345',
            'delivery_from': '東京都', 'fulfillment_latency': '6',
            'title': 'Mercari Item Title Length must be more than 30 characters'}
        user = MagicMock()

        with patch('richs_utils.InventoryMercari.MercariToAmazonItem.objects.filter') as mf:
            mf().count = MagicMock(return_value = 1)
            code = richs_utils.InventoryMercari.get_stock_update_info(item, candidate, user)
            self.assertEquals(code, -9)
            self._reset(mconn, mlogger, msleep)

        item.item_sku = 'xyz'
        code = richs_utils.InventoryMercari.get_stock_update_info(item, candidate, user)
        self.assertEquals(code, -1)
        self._reset(mconn, mlogger, msleep)

        item.purchase_price = 12345

        with patch('richs_utils.InventoryMercari.django_settings') as msettings:
            msettings.MERCARI_RIDE_SEARCH_CONFIG = {
                'MINIMUM_TITLE_LENGTH': 30,
                'MINIMUM_PROFIT': 0.3,
                'MAXIMUM_FULFILLMENT': 6,
                'IGNORE_DELIVERY_FROM': ['海外'],
            }

            dummy = candidate.copy()
            dummy['title'] = 'Too short title text'
            code = richs_utils.InventoryMercari.get_stock_update_info(item, dummy, user)
            self.assertEquals(code, -4)
            self._reset(mconn, mlogger, msleep)

            dummy = candidate.copy()
            dummy['delivery_from'] = '海外'
            code = richs_utils.InventoryMercari.get_stock_update_info(item, dummy, user)
            self.assertEquals(code, -4)
            self._reset(mconn, mlogger, msleep)

            dummy = candidate.copy()
            dummy['fulfillment_latency'] = '7'
            code = richs_utils.InventoryMercari.get_stock_update_info(item, dummy, user)
            self.assertEquals(code, -4)
            self._reset(mconn, mlogger, msleep)

            code = richs_utils.InventoryMercari.get_stock_update_info(item, candidate, user)
            self.assertEquals(code, 0)
            self._reset(mconn, mlogger, msleep)

            candidate = {}
            code = richs_utils.InventoryMercari.get_stock_update_info(item, candidate, user)
            self.assertEquals(code, -1)
            self._reset(mconn, mlogger, msleep)


    def test_executable_update_no_stock(self, mconn, mlogger, msleep):
        ''' 関数が最後まで流れるかをチェック '''
        item1 = MagicMock()
        item1.record_type = 20
        item2 = MagicMock()
        item2.record_type = 0

        richs_utils.InventoryMercari._update_no_stock([item1, item2])

        item1.save.assert_not_called()
        item2.save.assert_called_once()


    def test_executable_update_stock(self, mconn, mlogger, msleep):
        ''' 関数が最後まで流れるかをチェック '''
        candidate = {
            'seller': 'seller', 'seller_name': 'seller_name',
            'price': '100', 'item_id': 'item_id',
        }
        item1 = MagicMock()
        item1.record_type = 20
        item1.update_quantity_request = False
        item2 = MagicMock()
        item2.record_type = 21
        item2.update_quantity_request = False

        richs_utils.InventoryMercari._update_stock([item1, item2], candidate, 0.99)

        item1.save.assert_called_once()
        self.assertTrue(item1.update_quantity_request)
        item2.save.assert_called_once()
        self.assertFalse(item2.update_quantity_request)


    def test_active_item_order(self, mconn, mlogger, msleep):
        ''' 検索対象が想定どおりに取得できるかをチェック '''
        # データ作成
        user1 = User.objects.create_user(
            username='ut01', password='password', max_items=10)
        user2 = User.objects.create_user(
            username='ut02', password='password', max_items=10)

        for x in range(100):
            sku = 'M2A_SKU{:04d}'.format(x)
            MercariToAmazonItem.objects.create(author=user1, csv_flag=1,
                current_purchase_item_id=sku, research_request=False)
            MercariToAmazonItem.objects.create(author=user2, csv_flag=1,
                current_purchase_item_id=sku, research_request=False)
            sku = 'DUMMY1_SKU{:04d}'.format(x)
            MercariToAmazonItem.objects.create(author=user1, csv_flag=0,
                current_purchase_item_id=sku, research_request=False)
            sku = 'DUMMY2_SKU{:04d}'.format(x)
            MercariToAmazonItem.objects.create(author=user1, csv_flag=1,
                current_purchase_item_id=sku, research_request=True)

        # 別ユーザーのチェックを実施
        updated_sku = [ 'M2A_SKU{:04d}'.format(x) for x in range(20) ]
        for sku in updated_sku:
            richs_utils.InventoryMercari._update_status(user2, sku)

        # この時点ではuser1のチェック情報がないので作成順に実行される
        skus = richs_utils.InventoryMercari.get_sorted_active_item_skus(user1)
        self.assertEquals(skus, [ 'M2A_SKU{:04d}'.format(x) for x in range(100) ])

        # チェックを実施
        updated_sku = [ 'M2A_SKU{:04d}'.format(x) for x in range(20) ]
        for sku in updated_sku:
            richs_utils.InventoryMercari._update_status(user1, sku)
            richs_utils.InventoryMercari._update_status(user2, sku)

        # チェックしたものが後回しになる
        skus = richs_utils.InventoryMercari.get_sorted_active_item_skus(user1)
        expected = [ 'M2A_SKU{:04d}'.format(x) for x in list(range(20, 100)) + list(range(20)) ]
        self.assertEquals(skus, expected)

        # 逆順チェックを実施
        updated_sku = [ 'M2A_SKU{:04d}'.format(x) for x in sorted(list(range(100)), reverse=True) ]
        for sku in updated_sku:
            richs_utils.InventoryMercari._update_status(user1, sku)
            richs_utils.InventoryMercari._update_status(user2, sku)

        # チェックしたものが後回しになる
        skus = richs_utils.InventoryMercari.get_sorted_active_item_skus(user1)
        expected = [ 'M2A_SKU{:04d}'.format(x) for x in sorted(list(range(100)), reverse=True) ]
        self.assertEquals(skus, expected)


    def test_restore_item_order(self, mconn, mlogger, msleep):
        ''' 検索対象が想定どおりに取得できるかをチェック '''
        # データ作成
        user1 = User.objects.create_user(
            username='ut01', password='password', max_items=10)
        user2 = User.objects.create_user(
            username='ut02', password='password', max_items=10)

        for x in range(100):
            sku = 'M2A_SKU{:04d}'.format(x)
            MercariToAmazonItem.objects.create(author=user1, csv_flag=1,
                current_purchase_item_id=sku, research_request=True)
            MercariToAmazonItem.objects.create(author=user2, csv_flag=1,
                current_purchase_item_id=sku, research_request=True)
            sku = 'DUMMY1_SKU{:04d}'.format(x)
            MercariToAmazonItem.objects.create(author=user1, csv_flag=0,
                current_purchase_item_id=sku, research_request=True)
            sku = 'DUMMY2_SKU{:04d}'.format(x)
            MercariToAmazonItem.objects.create(author=user1, csv_flag=1,
                current_purchase_item_id=sku, research_request=False)

        with patch('richs_utils.InventoryMercari.django_settings') as msettings:
            msettings.ITEM_RESTORE_DAYS = 3
            # 別ユーザーのチェックを実施
            updated_sku = [ 'M2A_SKU{:04d}'.format(x) for x in range(20) ]
            for sku in updated_sku:
                richs_utils.InventoryMercari._update_status(user2, sku)

            # この時点ではuser1のチェック情報がないので作成順に実行される
            skus = richs_utils.InventoryMercari.get_sorted_restorable_item_skus(user1)
            self.assertEquals(skus, [ 'M2A_SKU{:04d}'.format(x) for x in range(100) ])

            # チェックを実施
            updated_sku = [ 'M2A_SKU{:04d}'.format(x) for x in range(20) ]
            for sku in updated_sku:
                richs_utils.InventoryMercari._update_status(user1, sku)
                richs_utils.InventoryMercari._update_status(user2, sku)

            # チェックしたものが後回しになる
            skus = richs_utils.InventoryMercari.get_sorted_restorable_item_skus(user1)
            expected = [ 'M2A_SKU{:04d}'.format(x) for x in list(range(20, 100)) + list(range(20)) ]
            self.assertEquals(skus, expected)

            # 逆順チェックを実施
            updated_sku = [ 'M2A_SKU{:04d}'.format(x) for x in sorted(list(range(100)), reverse=True) ]
            for sku in updated_sku:
                richs_utils.InventoryMercari._update_status(user1, sku)
                richs_utils.InventoryMercari._update_status(user2, sku)

            # チェックしたものが後回しになる
            skus = richs_utils.InventoryMercari.get_sorted_restorable_item_skus(user1)
            expected = [ 'M2A_SKU{:04d}'.format(x) for x in sorted(list(range(100)), reverse=True) ]
            self.assertEquals(skus, expected)

            # 日付を未来にすることで、一定以上前に登録した対象をフェッチしないことを確認
            dt = datetime.datetime.now() + datetime.timedelta(days=3)
            with patch('richs_utils.InventoryMercari.timezone') as mtz:
                mtz.datetime.now = MagicMock(return_value=dt)
                skus = richs_utils.InventoryMercari.get_sorted_restorable_item_skus(user1)
                self.assertEquals(skus, [])

            dt = datetime.datetime.now() + datetime.timedelta(days=2)
            with patch('richs_utils.InventoryMercari.timezone') as mtz:
                mtz.datetime.now = MagicMock(return_value=dt)
                skus = richs_utils.InventoryMercari.get_sorted_restorable_item_skus(user1)
                self.assertEquals(skus, expected)


