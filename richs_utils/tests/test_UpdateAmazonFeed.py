#!/usr/bin/python 
# -*- coding: utf-8 -*-

import datetime

from unittest.mock import mock_open, patch, MagicMock
from django.forms.models import model_to_dict

from django.test import TestCase
from django.utils import timezone

from accounts.models import User
from yahoo.models import YahooToAmazonItem
from mercari.models import MercariToAmazonItem

import richs_utils.UpdateAmazonFeed

@patch('richs_utils.UpdateAmazonFeed.psutil.pid_exists', return_value=True)
@patch('richs_utils.UpdateAmazonFeed.os.getpid', return_value=-1)
@patch('richs_utils.UpdateAmazonFeed.sleep')
@patch('richs_utils.UpdateAmazonFeed.logger')
@patch('richs_utils.UpdateAmazonFeed.connections')
class UpdateAmazonFeedTests(TestCase):

    def reset(self, *mocks):
        for m in mocks:
            m.reset_mock()


    def test_lock_user_for_yahoo(self, mconn, mlogger, msleep, mpid, mpid_exists):
        ''' userのロックに関する検証 '''
        user = User.objects.create_user(username='testuser', 
            password='1qaz2wsx3edc', max_items=20000, check_times=2)
        user.save()

        with patch('richs_utils.UpdateAmazonFeed.timezone') as mtz:
            mtz.datetime.now.return_value = datetime.datetime(2001, 1, 2, 1, 2, 3)

            # ユーザー削除済
            self.assertFalse(richs_utils.UpdateAmazonFeed._lock_user_for_yahoo(None))

            # 前提条件なし
            self.assertIsNone(user.update_yahoo_to_amazon_feed_pid)
            self.assertIsNone(user.update_yahoo_to_amazon_feed_start_date)
            richs_utils.UpdateAmazonFeed._lock_user_for_yahoo(user)
            self.assertEqual(user.update_yahoo_to_amazon_feed_pid, -1)
            self.assertEqual(user.update_yahoo_to_amazon_feed_start_date, 
                datetime.datetime(2001, 1, 2, 1, 2, 3))

            # 同一PID
            mtz.datetime.now.return_value = datetime.datetime(2001, 1, 2, 1, 2, 4)
            richs_utils.UpdateAmazonFeed._lock_user_for_yahoo(user)
            self.assertEqual(user.update_yahoo_to_amazon_feed_pid, -1)
            self.assertEqual(user.update_yahoo_to_amazon_feed_start_date, 
                datetime.datetime(2001, 1, 2, 1, 2, 4))

            # 異なるPIDで既存のプロセスがない場合
            mpid.return_value = -2
            mpid_exists.return_value = False
            mtz.datetime.now.return_value = datetime.datetime(2001, 1, 2, 1, 2, 5)
            richs_utils.UpdateAmazonFeed._lock_user_for_yahoo(user)
            self.assertEqual(user.update_yahoo_to_amazon_feed_pid, -2)
            self.assertEqual(user.update_yahoo_to_amazon_feed_start_date, 
                datetime.datetime(2001, 1, 2, 1, 2, 5))

            # 1800秒以下の場合
            user.update_yahoo_to_amazon_feed_pid = -1
            user.update_yahoo_to_amazon_feed_start_date = datetime.datetime(2001, 1, 2, 0, 0, 0)
            user.save()
            mpid.return_value = -2
            mpid_exists.return_value = True

            mtz.datetime.now.return_value = datetime.datetime(2001, 1, 2, 0, 29, 59)
            self.assertFalse(richs_utils.UpdateAmazonFeed._lock_user_for_yahoo(user))
 
            mtz.datetime.now.return_value = datetime.datetime(2001, 1, 2, 0, 30, 0)
            self.assertFalse(richs_utils.UpdateAmazonFeed._lock_user_for_yahoo(user))

            # 1800秒以上の場合、trueは返すが更新されない
            mtz.datetime.now.return_value = datetime.datetime(2001, 1, 2, 0, 30, 1)
            self.assertTrue(richs_utils.UpdateAmazonFeed._lock_user_for_yahoo(user))
            self.assertEqual(user.update_yahoo_to_amazon_feed_pid, -1)
            self.assertEqual(user.update_yahoo_to_amazon_feed_start_date, 
                datetime.datetime(2001, 1, 2, 0, 0, 0))


    def test_unlock_user_for_yahoo(self, mconn, mlogger, msleep, mpid, mpid_exists):
        ''' userのロックに関する検証 '''
        user = User.objects.create_user(username='testuser', 
            password='1qaz2wsx3edc', max_items=20000, check_times=2)
        user.save()

        with patch('richs_utils.UpdateAmazonFeed.timezone') as mtz:
            mtz.datetime.now.return_value = datetime.datetime(2001, 1, 2, 1, 2, 3)

            # ユーザー削除済
            self.assertFalse(richs_utils.UpdateAmazonFeed._lock_user_for_yahoo(None))

            # 前提条件なし
            richs_utils.UpdateAmazonFeed._lock_user_for_yahoo(user)
            self.assertEqual(user.update_yahoo_to_amazon_feed_pid, -1)
            self.assertEqual(user.update_yahoo_to_amazon_feed_start_date, 
                datetime.datetime(2001, 1, 2, 1, 2, 3))

            self.assertTrue(richs_utils.UpdateAmazonFeed._unlock_user_for_yahoo(user))
            self.assertIsNone(user.update_yahoo_to_amazon_feed_pid)
            self.assertIsNone(user.update_yahoo_to_amazon_feed_start_date)

            # 異なる PID 
            user.update_yahoo_to_amazon_feed_pid = -2
            user.update_yahoo_to_amazon_feed_start_date = datetime.datetime(2001, 1, 2, 0, 0, 0)
            user.save()
            self.assertTrue(richs_utils.UpdateAmazonFeed._unlock_user_for_yahoo(user))
            self.assertEqual(user.update_yahoo_to_amazon_feed_pid, -2)
            self.assertEqual(user.update_yahoo_to_amazon_feed_start_date, 
                datetime.datetime(2001, 1, 2, 0, 0, 0))


    def test_lock_user_for_mercari(self, mconn, mlogger, msleep, mpid, mpid_exists):
        ''' userのロックに関する検証 '''
        user = User.objects.create_user(username='testuser', 
            password='1qaz2wsx3edc', max_items=20000, check_times=2)
        user.save()

        with patch('richs_utils.UpdateAmazonFeed.timezone') as mtz:
            mtz.datetime.now.return_value = datetime.datetime(2001, 1, 2, 1, 2, 3)

            # ユーザー削除済
            self.assertFalse(richs_utils.UpdateAmazonFeed._lock_user_for_yahoo(None))

            # 前提条件なし
            self.assertIsNone(user.update_mercari_to_amazon_feed_pid)
            self.assertIsNone(user.update_mercari_to_amazon_feed_start_date)
            richs_utils.UpdateAmazonFeed._lock_user_for_mercari(user)
            self.assertEqual(user.update_mercari_to_amazon_feed_pid, -1)
            self.assertEqual(user.update_mercari_to_amazon_feed_start_date, 
                datetime.datetime(2001, 1, 2, 1, 2, 3))

            # 同一PID
            mtz.datetime.now.return_value = datetime.datetime(2001, 1, 2, 1, 2, 4)
            richs_utils.UpdateAmazonFeed._lock_user_for_mercari(user)
            self.assertEqual(user.update_mercari_to_amazon_feed_pid, -1)
            self.assertEqual(user.update_mercari_to_amazon_feed_start_date, 
                datetime.datetime(2001, 1, 2, 1, 2, 4))

            # 異なるPIDで既存のプロセスがない場合
            mpid.return_value = -2
            mpid_exists.return_value = False
            mtz.datetime.now.return_value = datetime.datetime(2001, 1, 2, 1, 2, 5)
            richs_utils.UpdateAmazonFeed._lock_user_for_mercari(user)
            self.assertEqual(user.update_mercari_to_amazon_feed_pid, -2)
            self.assertEqual(user.update_mercari_to_amazon_feed_start_date, 
                datetime.datetime(2001, 1, 2, 1, 2, 5))

            # 1800秒以下の場合
            user.update_mercari_to_amazon_feed_pid = -1
            user.update_mercari_to_amazon_feed_start_date = datetime.datetime(2001, 1, 2, 0, 0, 0)
            user.save()
            mpid.return_value = -2
            mpid_exists.return_value = True

            mtz.datetime.now.return_value = datetime.datetime(2001, 1, 2, 0, 29, 59)
            self.assertFalse(richs_utils.UpdateAmazonFeed._lock_user_for_mercari(user))
 
            mtz.datetime.now.return_value = datetime.datetime(2001, 1, 2, 0, 30, 0)
            self.assertFalse(richs_utils.UpdateAmazonFeed._lock_user_for_mercari(user))

            # 1800秒以上の場合、trueは返すが更新されない
            mtz.datetime.now.return_value = datetime.datetime(2001, 1, 2, 0, 30, 1)
            self.assertTrue(richs_utils.UpdateAmazonFeed._lock_user_for_mercari(user))
            self.assertEqual(user.update_mercari_to_amazon_feed_pid, -1)
            self.assertEqual(user.update_mercari_to_amazon_feed_start_date, 
                datetime.datetime(2001, 1, 2, 0, 0, 0))


    def test_unlock_user_for_mercari(self, mconn, mlogger, msleep, mpid, mpid_exists):
        ''' userのロックに関する検証 '''
        user = User.objects.create_user(username='testuser', 
            password='1qaz2wsx3edc', max_items=20000, check_times=2)
        user.save()

        with patch('richs_utils.UpdateAmazonFeed.timezone') as mtz:
            mtz.datetime.now.return_value = datetime.datetime(2001, 1, 2, 1, 2, 3)

            # ユーザー削除済
            self.assertFalse(richs_utils.UpdateAmazonFeed._lock_user_for_yahoo(None))

            # 前提条件なし
            richs_utils.UpdateAmazonFeed._lock_user_for_mercari(user)
            self.assertEqual(user.update_mercari_to_amazon_feed_pid, -1)
            self.assertEqual(user.update_mercari_to_amazon_feed_start_date, 
                datetime.datetime(2001, 1, 2, 1, 2, 3))

            self.assertTrue(richs_utils.UpdateAmazonFeed._unlock_user_for_mercari(user))
            self.assertIsNone(user.update_mercari_to_amazon_feed_pid)
            self.assertIsNone(user.update_mercari_to_amazon_feed_start_date)

            # 異なる PID 
            user.update_mercari_to_amazon_feed_pid = -2
            user.update_mercari_to_amazon_feed_start_date = datetime.datetime(2001, 1, 2, 0, 0, 0)
            user.save()
            self.assertTrue(richs_utils.UpdateAmazonFeed._unlock_user_for_mercari(user))
            self.assertEqual(user.update_mercari_to_amazon_feed_pid, -2)
            self.assertEqual(user.update_mercari_to_amazon_feed_start_date, 
                datetime.datetime(2001, 1, 2, 0, 0, 0))


    def test_get_valid_skus(self, mconn, mlogger, msleep, mpid, mpid_exists):
        ''' SKUS取得ロジックの確認 '''
        def valid(skus):
            return { sku: {'status': 'Success'} for sku in skus }
        mclient = MagicMock()
        mclient.get_my_price_for_sku.side_effect = valid

        # 通常時
        skus = richs_utils.UpdateAmazonFeed._get_valid_skus(mclient, [])
        self.assertEqual(skus, set([]))
        self.assertEqual(mclient.get_my_price_for_sku.call_count, 0)

        self.reset(mclient)
        skus = richs_utils.UpdateAmazonFeed._get_valid_skus(mclient, [
          'SKU{:04}'.format(idx) for idx in range(19)
        ])
        self.assertEqual(mclient.get_my_price_for_sku.call_count, 1)
        self.assertEqual(skus, set(['SKU{:04}'.format(idx) for idx in range(19)]))

        self.reset(mclient)
        skus = richs_utils.UpdateAmazonFeed._get_valid_skus(mclient, [
          'SKU{:04}'.format(idx) for idx in range(20)
        ])
        self.assertEqual(mclient.get_my_price_for_sku.call_count, 1)
        self.assertEqual(skus, set(['SKU{:04}'.format(idx) for idx in range(20)]))

        self.reset(mclient)
        skus = richs_utils.UpdateAmazonFeed._get_valid_skus(mclient, [
          'SKU{:04}'.format(idx) for idx in range(21)
        ])
        self.assertEqual(mclient.get_my_price_for_sku.call_count, 2)
        self.assertEqual(skus, set(['SKU{:04}'.format(idx) for idx in range(21)]))

        # エラーが交じるケース
        def half(skus):
            res = {}
            for sku in skus[:10]:
                res[sku] = {'status': 'Error'}
            for sku in skus[10:]:
                res[sku] = {'status': 'Success'}
            return res
        mclient = MagicMock()
        mclient.get_my_price_for_sku.side_effect = half
        skus = richs_utils.UpdateAmazonFeed._get_valid_skus(mclient, [
          'SKU{:04}'.format(idx) for idx in range(40)
        ])
        self.assertEqual(mclient.get_my_price_for_sku.call_count, 2)
        self.assertEqual(skus, set(
            ['SKU{:04}'.format(idx+10) for idx in range(10)] + ['SKU{:04}'.format(idx+30) for idx in range(10)]
        ))

        # リクエスト結果がエラーになるケース
        skus1 = valid([ 'SKU{:04}'.format(idx) for idx in range(20) ])
        skus2 = valid([ 'SKU{:04}'.format(idx) for idx in range(20, 21) ])
        mclient = MagicMock()
        mclient.get_my_price_for_sku.side_effect = [Exception('mock'), Exception('mock'), skus1, skus2]
        skus = richs_utils.UpdateAmazonFeed._get_valid_skus(mclient, [
          'SKU{:04}'.format(idx) for idx in range(21)
        ])
        # 規定回数(3回まで)に成功すれば結果は得られる
        self.assertEqual(mclient.get_my_price_for_sku.call_count, 4)
        self.assertEqual(skus, set(['SKU{:04}'.format(idx) for idx in range(21)]))

        mclient = MagicMock()
        mclient.get_my_price_for_sku.side_effect = [Exception('mock'), Exception('mock'), Exception('mock'), skus2]
        skus = richs_utils.UpdateAmazonFeed._get_valid_skus(mclient, [
          'SKU{:04}'.format(idx) for idx in range(21)
        ])
        # 規定回数でも成功しない場合、その範囲は全てスキップ
        self.assertEqual(mclient.get_my_price_for_sku.call_count, 4)
        self.assertEqual(skus, set(['SKU0020']))


    def _prepare_yahoo_testdata(self):
        ''' テストデータの作成 '''
        user = User.objects.create_user(username='testuser', 
            password='1qaz2wsx3edc', max_items=20000, check_times=2)

        def _sku(idx):
            return 'SKU{:04}'.format(idx)

        for idx in range(0, 300):
            YahooToAmazonItem.objects.create(
                author=user, csv_flag=1, current_purchase_quantity=0, update_quantity_request=True,
                item_sku=_sku(idx), current_purchase_fulfillment_latency=3)
        for idx in range(300, 600):
            YahooToAmazonItem.objects.create(
                author=user, csv_flag=1, current_purchase_quantity=0, update_fulfillment_latency_request=True, 
                item_sku=_sku(idx), current_purchase_fulfillment_latency=3)
        for idx in range(600, 700):
            YahooToAmazonItem.objects.create(
                author=user, csv_flag=1, current_purchase_quantity=1, update_quantity_request=True, 
                item_sku=_sku(idx), current_purchase_fulfillment_latency=3)
        for idx in range(700, 800):
            YahooToAmazonItem.objects.create(
                author=user, csv_flag=1, current_purchase_quantity=0, update_quantity_request=False,
                item_sku=_sku(idx), current_purchase_fulfillment_latency=3)

        return user


    def _prepare_mercari_testdata(self):
        ''' テストデータの作成 '''
        user = User.objects.create_user(username='testuser', 
            password='1qaz2wsx3edc', max_items=20000, check_times=2)

        def _sku(idx):
            return 'SKU{:04}'.format(idx)

        for idx in range(0, 300):
            MercariToAmazonItem.objects.create(
                author=user, csv_flag=1, current_purchase_quantity=0, update_quantity_request=True,
                item_sku=_sku(idx), current_purchase_fulfillment_latency=3)
        for idx in range(300, 600):
            MercariToAmazonItem.objects.create(
                author=user, csv_flag=1, current_purchase_quantity=0, update_fulfillment_latency_request=True, 
                item_sku=_sku(idx), current_purchase_fulfillment_latency=3)
        for idx in range(600, 700):
            MercariToAmazonItem.objects.create(
                author=user, csv_flag=1, current_purchase_quantity=1, update_quantity_request=True, 
                item_sku=_sku(idx), current_purchase_fulfillment_latency=3)
        for idx in range(700, 800):
            MercariToAmazonItem.objects.create(
                author=user, csv_flag=1, current_purchase_quantity=0, update_quantity_request=False,
                item_sku=_sku(idx), current_purchase_fulfillment_latency=3)

        return user



    def test_feed_update(self, mconn, mlogger, msleep, mpid, mpid_exists):
        ''' feed update 確認 '''
        def valid(skus):
            return { sku: {'status': 'Success'} for sku in skus }
        label = 'test'
        user = self._prepare_yahoo_testdata()
        conf = MagicMock()

        mclient = MagicMock()
        mclient.get_my_price_for_sku.side_effect = valid
        with patch('richs_utils.UpdateAmazonFeed._get_mws_client', return_value=mclient):
            # 0件の場合
            res = richs_utils.UpdateAmazonFeed._feed_update(label, user, conf, 
                lambda user: [], lambda user, skus: True, 
                max_item_count=None)
            mlogger.debug.assert_any_call('[%s] user %s has no items', label, user)
            self.assertTrue(res)
            self.reset(mlogger)

        mclient = MagicMock()
        mclient.get_my_price_for_sku.side_effect = valid
        mclient.update_quantity_and_fulfillment_latency.side_effect = Exception('mock')
        with patch('richs_utils.UpdateAmazonFeed._get_mws_client', return_value=mclient):
            # update時に例外
            res = richs_utils.UpdateAmazonFeed._feed_update('test', user, conf, 
                richs_utils.UpdateAmazonFeed._withdraw_candidates_for_yahoo, 
                richs_utils.UpdateAmazonFeed._item_update_for_yahoo, 
                max_item_count=None)
            mlogger.info.assert_any_call('[%s] user: %s feed update was cancelled because fail to call update API', label, user)
            self.assertFalse(res)
            self.reset(mlogger)

        mclient = MagicMock()
        mclient.get_my_price_for_sku.side_effect = valid
        mclient.update_quantity_and_fulfillment_latency.return_value = (True, 'mocked_feed_id')
        mclient.get_feed_submission_result.side_effect = Exception('mock')
        with patch('richs_utils.UpdateAmazonFeed._get_mws_client', return_value=mclient):
            # エラー取得時に例外 (DB更新がないので時間が経った後に再度updateが呼び出される)
            res = richs_utils.UpdateAmazonFeed._feed_update('test', user, conf, 
                richs_utils.UpdateAmazonFeed._withdraw_candidates_for_yahoo, 
                richs_utils.UpdateAmazonFeed._item_update_for_yahoo, 
                max_item_count=None)
            mlogger.info.assert_any_call('[%s] user: %s feed update was cancelled because fail to get error SKUs', label, user)
            self.assertFalse(res)
            self.reset(mlogger)

        mclient = MagicMock()
        mclient.get_my_price_for_sku.side_effect = valid
        mclient.update_quantity_and_fulfillment_latency.return_value = (True, 'mocked_feed_id')
        mclient.get_feed_submission_result.return_value = (True, [])
        with patch('richs_utils.UpdateAmazonFeed._get_mws_client', return_value=mclient):
            # 最後まで正常に流れた場合
            res = richs_utils.UpdateAmazonFeed._feed_update('test', user, conf, 
                richs_utils.UpdateAmazonFeed._withdraw_candidates_for_yahoo, 
                richs_utils.UpdateAmazonFeed._item_update_for_yahoo, 
                max_item_count=None)
            mlogger.info.assert_any_call('[%s] user %s feed update completed (count=%s)', label, user, 600)
            self.assertTrue(res)
            
            # リクエスト対象が全て更新されていること
            count = YahooToAmazonItem.objects.filter(
                author=user, current_purchase_quantity=0, update_fulfillment_latency_request=True).count()
            self.assertEqual(count, 0)
                
            count = YahooToAmazonItem.objects.filter(
                author=user, current_purchase_quantity=0, update_quantity_request=True).count()
            self.assertEqual(count, 0)

            # 対象外アイテムは更新されていないこと
            count = YahooToAmazonItem.objects.filter(
                author=user, current_purchase_quantity=1, update_quantity_request=True).count()
            self.assertEqual(count, 100)
                
            self.reset(mlogger)


    def test_feed_update_yahoo(self, mconn, mlogger, msleep, mpid, mpid_exists):
        ''' feed update yahoo のスレッド実行ロジック確認 '''
        def valid(skus):
            return { sku: {'status': 'Success'} for sku in skus }
        label = 'test'
        user = self._prepare_yahoo_testdata()
        conf = MagicMock()

        # ロックされている場合
        with patch('richs_utils.UpdateAmazonFeed.timezone') as mtz:
            mtz.datetime.now.return_value = datetime.datetime(2001, 1, 2, 1, 2, 3)
            mpid.return_value = -2
            richs_utils.UpdateAmazonFeed._lock_user_for_yahoo(user)
            mpid.return_value = -1
            label = 'yahoo withdraw'
            richs_utils.UpdateAmazonFeed._feed_update_withdraw_for_yahoo(user, conf)
            mlogger.info.assert_any_call('feed update %s for user:%s started', label, user)
            mlogger.info.assert_any_call('feed update %s for user:%s cancelled due to fail to get lock', label, user)
            mlogger.info.assert_any_call('feed update %s for user:%s finished (%s sec)', label, user, 0.0)
            dbuser = User.objects.get(username='testuser')
            self.assertEqual(dbuser.update_yahoo_to_amazon_feed_pid, -2)
            msleep.assert_called_once()
            mconn.close_all.assert_called_once()

            mpid.return_value = -2
            richs_utils.UpdateAmazonFeed._unlock_user_for_yahoo(user)
            user = User.objects.get(username='testuser')
            mpid.return_value = -1
            self.reset(mlogger)

        # 通常の場合
        mclient = MagicMock()
        mclient.get_my_price_for_sku.side_effect = valid
        mclient.update_quantity_and_fulfillment_latency.return_value = (True, 'mocked_feed_id')
        mclient.get_feed_submission_result.return_value = (True, [])
        with patch('richs_utils.UpdateAmazonFeed.timezone') as mtz, \
                patch('richs_utils.UpdateAmazonFeed._get_mws_client', return_value=mclient):
            # 最後まで正常に流れた場合
            mtz.datetime.now.return_value = datetime.datetime(2001, 1, 2, 1, 2, 3)
            richs_utils.UpdateAmazonFeed._feed_update_withdraw_for_yahoo(user, conf)
            richs_utils.UpdateAmazonFeed._feed_update_restore_for_yahoo(user, conf)
            mlogger.info.assert_any_call('feed update %s for user:%s started', label, user)
            mlogger.info.assert_any_call('[%s] user %s feed update completed (count=%s)', 'yahoo withdraw', user, 600)
            mlogger.info.assert_any_call('feed update %s for user:%s finished (%s sec)', label, user, 0.0)
            mlogger.info.assert_any_call('feed update %s for user:%s started', label, user)
            mlogger.info.assert_any_call('[%s] user %s feed update completed (count=%s)', 'yahoo restore', user, 100)
            mlogger.info.assert_any_call('feed update %s for user:%s finished (%s sec)', label, user, 0.0)
            
            # リクエスト対象が全て更新されていること
            count = YahooToAmazonItem.objects.filter(
                author=user, current_purchase_quantity=0, update_fulfillment_latency_request=True).count()
            self.assertEqual(count, 0)
                
            count = YahooToAmazonItem.objects.filter(
                author=user, current_purchase_quantity=0, update_quantity_request=True).count()
            self.assertEqual(count, 0)

            count = YahooToAmazonItem.objects.filter(
                author=user, current_purchase_quantity=1, update_quantity_request=True).count()
            self.assertEqual(count, 0)
                
            self.reset(mlogger)


    def test_feed_update_mercari(self, mconn, mlogger, msleep, mpid, mpid_exists):
        ''' feed update mercari のスレッド実行ロジック確認 '''
        def valid(skus):
            return { sku: {'status': 'Success'} for sku in skus }
        label = 'test'
        user = self._prepare_mercari_testdata()
        conf = MagicMock()

        # ロックされている場合
        with patch('richs_utils.UpdateAmazonFeed.timezone') as mtz:
            mtz.datetime.now.return_value = datetime.datetime(2001, 1, 2, 1, 2, 3)
            mpid.return_value = -2
            richs_utils.UpdateAmazonFeed._lock_user_for_mercari(user)
            mpid.return_value = -1
            label = 'mercari withdraw'
            richs_utils.UpdateAmazonFeed._feed_update_withdraw_for_mercari(user, conf)
            mlogger.info.assert_any_call('feed update %s for user:%s started', label, user)
            mlogger.info.assert_any_call('feed update %s for user:%s cancelled due to fail to get lock', label, user)
            mlogger.info.assert_any_call('feed update %s for user:%s finished (%s sec)', label, user, 0.0)
            dbuser = User.objects.get(username='testuser')
            self.assertEqual(dbuser.update_mercari_to_amazon_feed_pid, -2)
            msleep.assert_called_once()
            mconn.close_all.assert_called_once()

            mpid.return_value = -2
            richs_utils.UpdateAmazonFeed._unlock_user_for_mercari(user)
            user = User.objects.get(username='testuser')
            mpid.return_value = -1
            self.reset(mlogger)

        # 通常の場合
        mclient = MagicMock()
        mclient.get_my_price_for_sku.side_effect = valid
        mclient.update_quantity_and_fulfillment_latency.return_value = (True, 'mocked_feed_id')
        mclient.get_feed_submission_result.return_value = (True, [])
        with patch('richs_utils.UpdateAmazonFeed.timezone') as mtz, \
                patch('richs_utils.UpdateAmazonFeed._get_mws_client', return_value=mclient):
            # 最後まで正常に流れた場合
            mtz.datetime.now.return_value = datetime.datetime(2001, 1, 2, 1, 2, 3)
            richs_utils.UpdateAmazonFeed._feed_update_withdraw_for_mercari(user, conf)
            richs_utils.UpdateAmazonFeed._feed_update_restore_for_mercari(user, conf)
            mlogger.info.assert_any_call('feed update %s for user:%s started', label, user)
            mlogger.info.assert_any_call('[%s] user %s feed update completed (count=%s)', 'mercari withdraw', user, 600)
            mlogger.info.assert_any_call('feed update %s for user:%s finished (%s sec)', label, user, 0.0)
            mlogger.info.assert_any_call('feed update %s for user:%s started', label, user)
            mlogger.info.assert_any_call('[%s] user %s feed update completed (count=%s)', 'mercari restore', user, 100)
            mlogger.info.assert_any_call('feed update %s for user:%s finished (%s sec)', label, user, 0.0)
 
            # リクエスト対象が全て更新されていること
            count = MercariToAmazonItem.objects.filter(
                author=user, current_purchase_quantity=0, update_fulfillment_latency_request=True).count()
            self.assertEqual(count, 0)
                
            count = MercariToAmazonItem.objects.filter(
                author=user, current_purchase_quantity=0, update_quantity_request=True).count()
            self.assertEqual(count, 0)

            count = MercariToAmazonItem.objects.filter(
                author=user, current_purchase_quantity=1, update_quantity_request=True).count()
            self.assertEqual(count, 0)
                
            self.reset(mlogger)


    def test_feed_update_yahoo_when_update_userinfo(self, mconn, mlogger, msleep, mpid, mpid_exists):
        ''' 外部でユーザーの情報が更新された場合にその影響がないこと '''
        def valid(skus):
            return { sku: {'status': 'Success'} for sku in skus }
        label = 'test'
        user = self._prepare_yahoo_testdata()
        conf = MagicMock()
        
        # 通常の場合
        mclient = MagicMock()
        mclient.get_my_price_for_sku.side_effect = valid
        mclient.update_quantity_and_fulfillment_latency.return_value = (True, 'mocked_feed_id')
        mclient.get_feed_submission_result.return_value = (True, [])
        with patch('richs_utils.UpdateAmazonFeed.timezone') as mtz, \
                patch('richs_utils.UpdateAmazonFeed._get_mws_client', return_value=mclient):
            mtz.datetime.now.return_value = datetime.datetime(2001, 1, 2, 1, 2, 3)
            
            # 別スレッドでユーザー情報が更新
            external_thread_user = User.objects.get(uuid=user.uuid)
            external_thread_user.username = 'fixeduser'
            external_thread_user.save()

            richs_utils.UpdateAmazonFeed._feed_update_withdraw_for_yahoo(user, conf)
            # 引数は不変
            self.assertEqual(user.username, 'testuser')
            # DB側がロールバックしていない
            self.assertEqual(User.objects.get(uuid=user.uuid).username, 'fixeduser')

            richs_utils.UpdateAmazonFeed._feed_update_restore_for_yahoo(user, conf)
            # 引数は不変
            self.assertEqual(user.username, 'testuser')
            # DB側がロールバックしていない
            self.assertEqual(User.objects.get(uuid=user.uuid).username, 'fixeduser')

            # ユーザーが削除された場合
            User.objects.get(uuid=user.uuid).delete()

            richs_utils.UpdateAmazonFeed._feed_update_withdraw_for_yahoo(user, conf)
            # 引数は不変
            self.assertEqual(user.username, 'testuser')
            # DB側がロールバックしていない
            self.assertEqual(User.objects.filter(uuid=user.uuid).count(), 0)

            richs_utils.UpdateAmazonFeed._feed_update_restore_for_yahoo(user, conf)
            # 引数は不変
            self.assertEqual(user.username, 'testuser')
            # DB側がロールバックしていない
            self.assertEqual(User.objects.filter(uuid=user.uuid).count(), 0)


    def test_feed_update_mercari_when_update_userinfo(self, mconn, mlogger, msleep, mpid, mpid_exists):
        ''' 外部でユーザーの情報が更新された場合にその影響がないこと '''
        def valid(skus):
            return { sku: {'status': 'Success'} for sku in skus }
        label = 'test'
        user = self._prepare_mercari_testdata()
        conf = MagicMock()

        # 通常の場合
        mclient = MagicMock()
        mclient.get_my_price_for_sku.side_effect = valid
        mclient.update_quantity_and_fulfillment_latency.return_value = (True, 'mocked_feed_id')
        mclient.get_feed_submission_result.return_value = (True, [])
        with patch('richs_utils.UpdateAmazonFeed.timezone') as mtz, \
                patch('richs_utils.UpdateAmazonFeed._get_mws_client', return_value=mclient):
            # 最後まで正常に流れた場合
            mtz.datetime.now.return_value = datetime.datetime(2001, 1, 2, 1, 2, 3)

             # 別スレッドでユーザー情報が更新
            external_thread_user = User.objects.get(uuid=user.uuid)
            external_thread_user.username = 'fixeduser'
            external_thread_user.save()

            richs_utils.UpdateAmazonFeed._feed_update_withdraw_for_mercari(user, conf)
            # 引数は不変
            self.assertEqual(user.username, 'testuser')
            # DB側がロールバックしていない
            self.assertEqual(User.objects.get(uuid=user.uuid).username, 'fixeduser')

            richs_utils.UpdateAmazonFeed._feed_update_restore_for_mercari(user, conf)
             # 引数は不変
            self.assertEqual(user.username, 'testuser')
            # DB側がロールバックしていない
            self.assertEqual(User.objects.get(uuid=user.uuid).username, 'fixeduser')

            # ユーザーが削除された場合
            User.objects.get(uuid=user.uuid).delete()

            richs_utils.UpdateAmazonFeed._feed_update_withdraw_for_mercari(user, conf)
            # 引数は不変
            self.assertEqual(user.username, 'testuser')
            # DB側がロールバックしていない
            self.assertEqual(User.objects.filter(uuid=user.uuid).count(), 0)

            richs_utils.UpdateAmazonFeed._feed_update_restore_for_mercari(user, conf)
             # 引数は不変
            self.assertEqual(user.username, 'testuser')
            # DB側がロールバックしていない
            self.assertEqual(User.objects.filter(uuid=user.uuid).count(), 0)



