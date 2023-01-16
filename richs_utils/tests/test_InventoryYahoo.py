#!/usr/bin/python 
# -*- coding: utf-8 -*-

import datetime 

from unittest.mock import mock_open, patch, MagicMock
from django.forms.models import model_to_dict

from django.test import TestCase
from django.utils import timezone

from accounts.models import User, OfferReserchWatcher, StopRequest, StockCheckStatus
from yahoo.models import YahooToAmazonItem

import richs_utils.InventoryYahoo

class InventoryYahooTests(TestCase):

    def test_item_scraper_result(self):
        ''' ItemScraper 生成関数のチェック '''
        ips = []
        with patch('richs_utils.InventoryYahoo.YahooAuctionIdScraper') as m:
            richs_utils.InventoryYahoo.create_item_scraper(0, ips)
            richs_utils.InventoryYahoo.create_item_scraper(1, ips)
            richs_utils.InventoryYahoo.create_item_scraper(2, ips)
            (actuals, kwactuals) = m.call_args_list[0]
            self.assertEquals(len(actuals), 0)
            (actuals, kwactuals) = m.call_args_list[1]
            self.assertEquals(len(actuals), 0)
            (actuals, kwactuals) = m.call_args_list[2]
            self.assertEquals(len(actuals), 0)

        ips = ['127.0.0.1', '127.0.0.2']
        with patch('richs_utils.InventoryYahoo.YahooAuctionIdScraper') as m:
            richs_utils.InventoryYahoo.create_item_scraper(0, ips)
            richs_utils.InventoryYahoo.create_item_scraper(1, ips)
            richs_utils.InventoryYahoo.create_item_scraper(2, ips)
            richs_utils.InventoryYahoo.create_item_scraper(3, ips)
            richs_utils.InventoryYahoo.create_item_scraper(4, ips)
            richs_utils.InventoryYahoo.create_item_scraper(5, ips)
            richs_utils.InventoryYahoo.create_item_scraper(6, ips)
            richs_utils.InventoryYahoo.create_item_scraper(7, ips)
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


    def test_search_scraper_result(self):
        ''' ItemScraper 生成関数のチェック '''
        ips = []
        with patch('richs_utils.InventoryYahoo.YahooSearchScraper') as m:
            richs_utils.InventoryYahoo.create_search_scraper(0, ips)
            richs_utils.InventoryYahoo.create_search_scraper(1, ips)
            richs_utils.InventoryYahoo.create_search_scraper(2, ips)
            (actuals, kwactuals) = m.call_args_list[0]
            self.assertEquals(len(actuals), 0)
            (actuals, kwactuals) = m.call_args_list[1]
            self.assertEquals(len(actuals), 0)
            (actuals, kwactuals) = m.call_args_list[2]
            self.assertEquals(len(actuals), 0)

        ips = ['127.0.0.1', '127.0.0.2']
        with patch('richs_utils.InventoryYahoo.YahooSearchScraper') as m:
            richs_utils.InventoryYahoo.create_search_scraper(0, ips)
            richs_utils.InventoryYahoo.create_search_scraper(1, ips)
            richs_utils.InventoryYahoo.create_search_scraper(2, ips)
            richs_utils.InventoryYahoo.create_search_scraper(3, ips)
            richs_utils.InventoryYahoo.create_search_scraper(4, ips)
            richs_utils.InventoryYahoo.create_search_scraper(5, ips)
            richs_utils.InventoryYahoo.create_search_scraper(6, ips)
            richs_utils.InventoryYahoo.create_search_scraper(7, ips)
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


    def test_executable_run_user_inventory_check(self):
        ''' 関数が最後まで流れるかをチェック '''
        sku = 'dummy'
        scraper = MagicMock()
        scraper.get_products = MagicMock(return_value=[])
        user = MagicMock()
        config = MagicMock()
        exclude_sellers = []

        with patch('richs_utils.InventoryYahoo.sleep'), \
                patch('richs_utils.InventoryYahoo.logger') as mlogger, \
                patch('richs_utils.InventoryYahoo.create_item_scraper', side_effect=Exception('ERR')), \
                patch('richs_utils.InventoryYahoo.connections') as mconn:
            richs_utils.InventoryYahoo._run_user_inventory_check(user, sku, 0, [], config, exclude_sellers)
            mlogger.warn.assert_called_once()
            mconn.close_all.assert_called_once()

        scraper = MagicMock()
        scraper.get_products = MagicMock(return_value=['content is living'])
        with patch('richs_utils.InventoryYahoo.sleep'), \
                patch('richs_utils.InventoryYahoo.logger') as mlogger, \
                patch('richs_utils.InventoryYahoo.create_item_scraper', return_value=scraper), \
                patch('richs_utils.InventoryYahoo.YahooToAmazonItem.objects.filter') as mf, \
                patch('richs_utils.InventoryYahoo.connections') as mconn:
            richs_utils.InventoryYahoo._run_user_inventory_check(user, sku, 0, [], config, exclude_sellers)
            mf().update.assert_not_called()
            mconn.close_all.assert_called_once()

        scraper = MagicMock()
        scraper.get_products = MagicMock(return_value=[])
        with patch('richs_utils.InventoryYahoo.sleep'), \
                patch('richs_utils.InventoryYahoo.logger') as mlogger, \
                patch('richs_utils.InventoryYahoo.create_item_scraper', return_value=scraper), \
                patch('richs_utils.InventoryYahoo.YahooToAmazonItem.objects.filter') as mf, \
                patch('richs_utils.InventoryYahoo.connections') as mconn:
            # content is none so require update again.
            richs_utils.InventoryYahoo._run_user_inventory_check(user, sku, 0, [], config, exclude_sellers)
            mf().update.assert_called_once()
            mconn.close_all.assert_called_once()


    def test_executable_run_user_inventory_check_adjust_sleep(self):
        ''' 補正スリープが正常に行われるかをチェック '''
        sku = 'dummy'
        scraper = MagicMock()
        scraper.get_products = MagicMock(return_value=[])
        user = MagicMock()
        mdt = MagicMock()
        scraper = MagicMock()
        scraper.get_products = MagicMock(return_value=['content is living'])
        config = MagicMock()
        exclude_sellers = []

        mdt.now = MagicMock(side_effect=[
            datetime.datetime(2001, 1, 1,  1, 23, 45), 
            datetime.datetime(2001, 1, 1,  1, 23, 45, 500000),
            datetime.datetime(2001, 1, 1,  1, 23, 45, 500000),
        ])
        with patch('richs_utils.InventoryYahoo.sleep') as msleep, \
                patch('richs_utils.InventoryYahoo.logger') as mlogger, \
                patch('richs_utils.InventoryYahoo.create_item_scraper', return_value=scraper), \
                patch('richs_utils.InventoryYahoo.timezone.datetime', mdt), \
                patch('richs_utils.InventoryYahoo.connections') as mconn:
            richs_utils.InventoryYahoo._run_user_inventory_check(user, sku, 0, [], config, exclude_sellers)
            (actuals, kwactuals) = msleep.call_args_list[0]
            self.assertTrue(abs(actuals[0] - 1.5) < 0.00001)

        mdt.now = MagicMock(side_effect=[
            datetime.datetime(2001, 1, 1,  1, 23, 45), 
            datetime.datetime(2001, 1, 1,  1, 23, 47),
            datetime.datetime(2001, 1, 1,  1, 23, 47),
        ])
        with patch('richs_utils.InventoryYahoo.sleep') as msleep, \
                patch('richs_utils.InventoryYahoo.logger') as mlogger, \
                patch('richs_utils.InventoryYahoo.create_item_scraper', return_value=scraper), \
                patch('richs_utils.InventoryYahoo.timezone.datetime', mdt), \
                patch('richs_utils.InventoryYahoo.connections') as mconn:
            richs_utils.InventoryYahoo._run_user_inventory_check(user, sku, 0, [], config, exclude_sellers)
            msleep.assert_called_once_with(1)

        mdt.now = MagicMock(side_effect=[
            datetime.datetime(2001, 1, 1,  1, 23, 45), 
            datetime.datetime(2001, 1, 1,  1, 23, 47, 500),
            datetime.datetime(2001, 1, 1,  1, 23, 47, 500),
        ])
        with patch('richs_utils.InventoryYahoo.sleep') as msleep, \
                patch('richs_utils.InventoryYahoo.logger') as mlogger, \
                patch('richs_utils.InventoryYahoo.create_item_scraper', return_value=scraper), \
                patch('richs_utils.InventoryYahoo.timezone.datetime', mdt), \
                patch('richs_utils.InventoryYahoo.connections') as mconn:
            richs_utils.InventoryYahoo._run_user_inventory_check(user, sku, 0, [], config, exclude_sellers)
            msleep.assert_called_once_with(1)


    def test_executable_run_stock_update(self):
        ''' 関数が最後まで流れるかをチェック '''
        sku = 'dummy'
        config = MagicMock()
        exclude_seller = [MagicMock()]
        scraper = MagicMock()
        scraper.get_products = MagicMock(return_value=[])
        user = MagicMock()

        with patch('richs_utils.InventoryYahoo.sleep'), \
                patch('richs_utils.InventoryYahoo.logger') as mlogger, \
                patch('richs_utils.InventoryYahoo.YahooToAmazonItem.objects.filter') as mf, \
                patch('richs_utils.InventoryYahoo.connections') as mconn:
            mf().order_by = MagicMock(return_value=[])
            richs_utils.InventoryYahoo._run_stock_update(user, sku, 0, [], config, exclude_seller)
            mlogger.debug.assert_any_call('SKU: %s was updated or deleted', sku)

        with patch('richs_utils.InventoryYahoo.sleep'), \
                patch('richs_utils.InventoryYahoo.logger') as mlogger, \
                patch('richs_utils.InventoryYahoo.YahooToAmazonItem.objects.filter') as mf, \
                patch('richs_utils.InventoryYahoo.make_url', return_value='dummyurl'), \
                patch('richs_utils.InventoryYahoo.create_search_scraper', side_effect=Exception('ERR')), \
                patch('richs_utils.InventoryYahoo.connections') as mconn:
            mf().order_by = MagicMock(return_value=[MagicMock()])
            richs_utils.InventoryYahoo._run_stock_update(user, sku, 0, [], config, exclude_seller)
            mlogger.warn.assert_any_call('Yahooオークションへの問い合わせに失敗: %s:%s', user, sku)

        scraper = MagicMock()
        scraper.get_products = MagicMock(return_value=[])
        with patch('richs_utils.InventoryYahoo.sleep'), \
                patch('richs_utils.InventoryYahoo.logger') as mlogger, \
                patch('richs_utils.InventoryYahoo.YahooToAmazonItem.objects.filter') as mf, \
                patch('richs_utils.InventoryYahoo.make_url', return_value='dummyurl'), \
                patch('richs_utils.InventoryYahoo.create_search_scraper', return_value=scraper), \
                patch('richs_utils.InventoryYahoo.connections') as mconn:
            mf().order_by = MagicMock(return_value=[MagicMock()])
            richs_utils.InventoryYahoo._run_stock_update(user, sku, 0, [], config, exclude_seller)
            mlogger.info.assert_any_call('Not found candidates: %s:%s', user, sku)

        scraper = MagicMock()
        scraper.get_products = MagicMock(return_value=[MagicMock()])
        with patch('richs_utils.InventoryYahoo.sleep'), \
                patch('richs_utils.InventoryYahoo.logger') as mlogger, \
                patch('richs_utils.InventoryYahoo.YahooToAmazonItem.objects.filter') as mf, \
                patch('richs_utils.InventoryYahoo.make_url', return_value='dummyurl'), \
                patch('richs_utils.InventoryYahoo.create_search_scraper', return_value=scraper), \
                patch('richs_utils.InventoryYahoo.RichsUtils.get_yahoo_image_folder', return_value='/tmp'), \
                patch('richs_utils.InventoryYahoo.os.path.join', return_value='/tmp/hoge.jpg'), \
                patch('richs_utils.InventoryYahoo.connections') as mconn:
            mf().order_by = MagicMock(return_value=[MagicMock()])

            stock_results = (False, None, None)
            with patch('richs_utils.InventoryYahoo._search_new_stock', return_value=stock_results), \
                    patch('richs_utils.InventoryYahoo._update_no_stock') as m_update:
                richs_utils.InventoryYahoo._run_stock_update(user, sku, 0, [], config, exclude_seller)
                m_update.assert_called_once()

            stock_results = (True, None, None)
            with patch('richs_utils.InventoryYahoo._search_new_stock', return_value=stock_results), \
                    patch('richs_utils.InventoryYahoo._update_stock') as m_update:
                richs_utils.InventoryYahoo._run_stock_update(user, sku, 0, [], config, exclude_seller)
                m_update.assert_called_once()


    def test_executable_update_no_stock(self):
        ''' 関数が最後まで流れるかをチェック '''
        item1 = MagicMock()
        item1.record_type = 20
        item2 = MagicMock()
        item2.record_type = 0

        with patch('richs_utils.InventoryYahoo.logger') as mlogger:
            richs_utils.InventoryYahoo._update_no_stock([item1, item2])

        item1.save.assert_not_called()
        item2.save.assert_called_once()


    def test_executable_update_stock(self):
        ''' 関数が最後まで流れるかをチェック '''
        candidate = {
            'seller': 'seller', 'auction_id': 'auction', 
            'bid_or_buy': '100', 'current_price': '200',
        }
        item1 = MagicMock()
        item1.record_type = 20
        item1.update_quantity_request = False
        item2 = MagicMock()
        item2.record_type = 21
        item2.update_quantity_request = False

        with patch('richs_utils.InventoryYahoo.logger') as mlogger:
            richs_utils.InventoryYahoo._update_stock([item1, item2], candidate, 0.99)

        item1.save.assert_called_once()
        self.assertTrue(item1.update_quantity_request)
        item2.save.assert_called_once()
        self.assertFalse(item2.update_quantity_request)


    def test_active_item_order(self):
        ''' 検索対象が想定どおりに取得できるかをチェック '''
        # データ作成
        user1 = User.objects.create_user(
            username='ut01', password='password', max_items=10)
        user2 = User.objects.create_user(
            username='ut02', password='password', max_items=10)

        for x in range(100):
            sku = 'Y2A_SKU{:04d}'.format(x)
            YahooToAmazonItem.objects.create(author=user1, csv_flag=1,
                current_purchase_item_id=sku, research_request=False)
            YahooToAmazonItem.objects.create(author=user2, csv_flag=1,
                current_purchase_item_id=sku, research_request=False)
            sku = 'DUMMY1_SKU{:04d}'.format(x)
            YahooToAmazonItem.objects.create(author=user1, csv_flag=0,
                current_purchase_item_id=sku, research_request=False)
            sku = 'DUMMY2_SKU{:04d}'.format(x)
            YahooToAmazonItem.objects.create(author=user1, csv_flag=1,
                current_purchase_item_id=sku, research_request=True)

        with patch('richs_utils.InventoryYahoo.logger') as mlogger:
            # 別ユーザーのチェックを実施
            updated_sku = [ 'Y2A_SKU{:04d}'.format(x) for x in range(20) ]
            for sku in updated_sku:
                richs_utils.InventoryYahoo._update_status(user2, sku)
                
            # この時点ではuser1のチェック情報がないので作成順に実行される
            skus = richs_utils.InventoryYahoo.get_sorted_active_item_skus(user1)
            self.assertEquals(skus, [ 'Y2A_SKU{:04d}'.format(x) for x in range(100) ])

            # チェックを実施
            updated_sku = [ 'Y2A_SKU{:04d}'.format(x) for x in range(20) ]
            for sku in updated_sku:
                richs_utils.InventoryYahoo._update_status(user1, sku)
                richs_utils.InventoryYahoo._update_status(user2, sku)
          
            # チェックしたものが後回しになる
            skus = richs_utils.InventoryYahoo.get_sorted_active_item_skus(user1)
            expected = [ 'Y2A_SKU{:04d}'.format(x) for x in list(range(20, 100)) + list(range(20)) ]
            self.assertEquals(skus, expected)

            # 逆順チェックを実施
            updated_sku = [ 'Y2A_SKU{:04d}'.format(x) for x in sorted(list(range(100)), reverse=True) ]
            for sku in updated_sku:
                richs_utils.InventoryYahoo._update_status(user1, sku)
                richs_utils.InventoryYahoo._update_status(user2, sku)

            # チェックしたものが後回しになる
            skus = richs_utils.InventoryYahoo.get_sorted_active_item_skus(user1)
            expected = [ 'Y2A_SKU{:04d}'.format(x) for x in sorted(list(range(100)), reverse=True) ]
            self.assertEquals(skus, expected)


    def test_restore_item_order(self):
        ''' 検索対象が想定どおりに取得できるかをチェック '''
        # データ作成
        user1 = User.objects.create_user(
            username='ut01', password='password', max_items=10)
        user2 = User.objects.create_user(
            username='ut02', password='password', max_items=10)

        for x in range(100):
            sku = 'Y2A_SKU{:04d}'.format(x)
            YahooToAmazonItem.objects.create(author=user1, csv_flag=1,
                current_purchase_item_id=sku, research_request=True)
            YahooToAmazonItem.objects.create(author=user2, csv_flag=1,
                current_purchase_item_id=sku, research_request=True)
            sku = 'DUMMY1_SKU{:04d}'.format(x)
            YahooToAmazonItem.objects.create(author=user1, csv_flag=0,
                current_purchase_item_id=sku, research_request=True)
            sku = 'DUMMY2_SKU{:04d}'.format(x)
            YahooToAmazonItem.objects.create(author=user1, csv_flag=1,
                current_purchase_item_id=sku, research_request=False)

        with patch('richs_utils.InventoryYahoo.logger') as mlogger, \
                patch('richs_utils.InventoryYahoo.django_settings') as msettings:
            msettings.ITEM_RESTORE_DAYS = 3
            # 別ユーザーのチェックを実施
            updated_sku = [ 'Y2A_SKU{:04d}'.format(x) for x in range(20) ]
            for sku in updated_sku:
                richs_utils.InventoryYahoo._update_status(user2, sku)
                
            # この時点ではuser1のチェック情報がないので作成順に実行される
            skus = richs_utils.InventoryYahoo.get_sorted_restorable_item_skus(user1)
            self.assertEquals(skus, [ 'Y2A_SKU{:04d}'.format(x) for x in range(100) ])

            # チェックを実施
            updated_sku = [ 'Y2A_SKU{:04d}'.format(x) for x in range(20) ]
            for sku in updated_sku:
                richs_utils.InventoryYahoo._update_status(user1, sku)
                richs_utils.InventoryYahoo._update_status(user2, sku)
          
            # チェックしたものが後回しになる
            skus = richs_utils.InventoryYahoo.get_sorted_restorable_item_skus(user1)
            expected = [ 'Y2A_SKU{:04d}'.format(x) for x in list(range(20, 100)) + list(range(20)) ]
            self.assertEquals(skus, expected)

            # 逆順チェックを実施
            updated_sku = [ 'Y2A_SKU{:04d}'.format(x) for x in sorted(list(range(100)), reverse=True) ]
            for sku in updated_sku:
                richs_utils.InventoryYahoo._update_status(user1, sku)
                richs_utils.InventoryYahoo._update_status(user2, sku)

            # チェックしたものが後回しになる
            skus = richs_utils.InventoryYahoo.get_sorted_restorable_item_skus(user1)
            expected = [ 'Y2A_SKU{:04d}'.format(x) for x in sorted(list(range(100)), reverse=True) ]
            self.assertEquals(skus, expected)

            # 日付を未来にすることで、一定以上前に登録した対象をフェッチしないことを確認
            dt = datetime.datetime.now() + datetime.timedelta(days=3)
            with patch('richs_utils.InventoryYahoo.timezone') as mtz:
                mtz.datetime.now = MagicMock(return_value=dt)
                skus = richs_utils.InventoryYahoo.get_sorted_restorable_item_skus(user1)
                self.assertEquals(skus, [])

            dt = datetime.datetime.now() + datetime.timedelta(days=2)
            with patch('richs_utils.InventoryYahoo.timezone') as mtz:
                mtz.datetime.now = MagicMock(return_value=dt)
                skus = richs_utils.InventoryYahoo.get_sorted_restorable_item_skus(user1)
                self.assertEquals(skus, expected)


