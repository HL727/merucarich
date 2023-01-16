#!/usr/bin/python 
# -*- coding: utf-8 -*-

import datetime

from unittest.mock import patch, MagicMock

from django.test import TestCase
from django.utils import timezone
from django.http import QueryDict
from django.conf import settings

import yahoo.views 

from accounts.models import (
    User, OfferReserchWatcher, StopRequest, URLSkipRequest, 
    BannedKeyword, ItemCandidateToCsv, BackgroundSearchInfo
)
from settings_amazon.models import AmazonAPI, ExcludeAsin, AmazonFeedPriceSettings
from yahoo.models import YahooToAmazonItem, YahooToAmazonCSV, YahooExcludeSeller

@patch('yahoo.views.asynchelpers.wait')
@patch('yahoo.views.logger')
@patch('yahoo.views.asynchelpers.get_queue')
class BackgroundSearchTaskTests(TestCase):
    ''' 相乗り検索の単体テスト '''
    def test_entry_if_no_watcher(self, mqueue, mlogger, mwait):
        user = User.objects.create(username='hoge')

        yahoo.views.amazon_offer_research_entry(MagicMock(), '', user)
        
        self.assertEquals(mlogger.warn.call_count, 1)
        self.assertEquals(mlogger.warn.call_args[0][0], 
            '相乗り商品抽出レコードが未登録です。 research_type=0, author=%s')

    def test_entry_if_mws_is_none(self, mqueue, mlogger, mwait):
        user = User.objects.create(username='hoge')
        watch = OfferReserchWatcher.objects.create(
            research_type = 0, status = 0, total = 0, exclude_asin = 0, 
            prime = 0, condition_different = 0, exclude_seller = 0, not_found = 0, 
            feed_item = 0, is_over_items=False, author = user)

  
        with patch('yahoo.views.RichsUtils.get_mws_api', return_value=None):
            yahoo.views.amazon_offer_research_entry(MagicMock(), '', user)

        self.assertEquals(mlogger.info.call_count, 1)
        self.assertEquals(mlogger.info.call_args[0][0], 
            'MWS APIの情報登録がありません。 research_type=0, author=%s')


    def _entry(self):
        user = User.objects.create(username='hoge')
        watch = OfferReserchWatcher.objects.create(
            research_type = 0, status = 0, total = 0, exclude_asin = 0, 
            prime = 0, condition_different = 0, exclude_seller = 0, not_found = 0, 
            feed_item = 0, is_over_items=False, author = user)
        apikey = AmazonAPI.objects.create(
            author=user, account_id='xxx', auth_token='yyy')
        YahooExcludeSeller.objects.create(author=user, seller_id='bad.seller')
        BackgroundSearchInfo.objects.create(
            watcher=watch, url='dummy url', next_url=None, order=0)
        self.assertEquals(AmazonFeedPriceSettings.objects.filter(author=user).count(), 1)
        params = QueryDict('&'.join([
            'select=hoge&istatus=piyo&is_exist_bidorbuy_price=1', 
            'similarity=0.8&abatch=&rateing=80.0&is_export_csv=1'
        ]))
        with patch('yahoo.views.RichsUtils.get_tmp_image_folder', return_value='/tmp'), \
                patch('yahoo.views.RichsUtils.get_mws_api', return_value=MagicMock()), \
                patch('yahoo.views.AmazonScraper.get_products', return_value=['mock!']), \
                patch('yahoo.views.timezone.datetime') as mdt:
            mdt.now.return_value = datetime.datetime(2002, 1, 2, 1, 2, 3)
            yahoo.views.amazon_offer_research_entry(params, '', user)


    def test_entry_success_develop(self, mqueue, mlogger, mwait):
        with patch('yahoo.views.settings') as msettings, \
                patch('yahoo.views.AmazonScraper.set_mws') as mmws:
            msettings.PRODUCTION = False
            self._entry()
            self.assertEquals(mmws.call_count, 0)

        target = mqueue().enqueue
        self.assertEquals(target.call_count, 1)
        (nameless, actuals) = target.call_args
        self.assertEquals(nameless[0], yahoo.views.amazon_offer_research_task)
        pools = actuals['pools']
        self.assertEquals(pools['amazon_items'], ['mock!'])
        self.assertEquals(pools['image_base'], '/tmp')


    def test_entry_success_production(self, mqueue, mlogger, mwait):
        with patch('yahoo.views.settings') as msettings, \
                patch('yahoo.views.AmazonScraper.set_mws') as mmws:
            msettings.PRODUCTION = True
            self._entry()
            self.assertEquals(mmws.call_count, 1)

        target = mqueue().enqueue
        self.assertEquals(target.call_count, 1)
        (nameless, actuals) = target.call_args
        self.assertEquals(nameless[0], yahoo.views.amazon_offer_research_task)
        pools = actuals['pools']
        self.assertEquals(pools['amazon_items'], ['mock!'])
        self.assertEquals(pools['image_base'], '/tmp')
        # URL単位の開始日時が出力されている
        watch = OfferReserchWatcher.objects.filter(author=actuals['user']).first()
        bginfo = BackgroundSearchInfo.objects.filter(watcher=watch)
        self.assertEquals(1, len(bginfo))
        self.assertEquals(datetime.datetime(2002, 1, 2, 1, 2, 3), bginfo[0].start_date)


    def test_entry_raise_unknown_exception(self, mqueue, mlogger, mwait):
        e = Exception('unknown!')
        with patch('yahoo.views._get_offer_research_scrapers', side_effect=e):
            self._entry()

        user = User.objects.get(username='hoge')
        mlogger.info.assert_called_once_with(
            'ユーザー %s の処理中にエラーが発生したため、強制中断しました', user)
        mlogger.exception.assert_called_once_with(e)
        (actuals, _) = mqueue().enqueue.call_args_list[0]
        self.assertEquals(actuals[0], yahoo.views.amazon_offer_research_finalize)


    def test_entry_retry_when_amazon_response_5xx(self, mqueue, mlogger, mwait):
        ''' get_products で 503 が返ってきた場合の処理 '''
        user = User.objects.create(username='hoge')
        watch = OfferReserchWatcher.objects.create(
            research_type = 0, status = 0, total = 0, exclude_asin = 0, 
            prime = 0, condition_different = 0, exclude_seller = 0, not_found = 0, 
            feed_item = 0, is_over_items=False, author = user)
        apikey = AmazonAPI.objects.create(
            author=user, account_id='xxx', auth_token='yyy')
        params = QueryDict('&'.join([
            'select=hoge&istatus=piyo&is_exist_bidorbuy_price=1', 
            'similarity=0.8&abatch=&rateing=80.0&is_export_csv=1'
        ]))

        retry_settings = { 'MAX_TRIAL': 120, 'TRIAL_WAIT_SECONDS': 10, 'TRIAL_WAIT_COUNT': 8 }

        with patch('yahoo.views.RichsUtils.get_tmp_image_folder', return_value='/tmp'), \
                patch('yahoo.views.RichsUtils.get_mws_api', return_value=MagicMock()), \
                patch('yahoo.views._amazon_retry_settings', return_value=retry_settings), \
                patch('yahoo.views.AmazonScraper.get_products', side_effect=ValueError('503')):
            yahoo.views.amazon_offer_research_entry(params, '', user)

        user = User.objects.get(username='hoge')
        (actuals, kwactuals) = mqueue().enqueue.call_args_list[0]
        kwargs = kwactuals['kwargs']
        self.assertEquals(actuals[0], yahoo.views.amazon_offer_research_entry)
        self.assertEquals(kwargs['params'], params)
        self.assertEquals(kwargs['url'], '')
        self.assertEquals(kwargs['user'], user)
        self.assertEquals(kwargs['trial'], 1)
        self.assertEquals(kwargs['rest_wait_count'], 8)

        # rest_wait_count > 0 の場合の処理
        mqueue.reset_mock()
        mlogger.reset_mock()
        mwait.rest_mock()
        with patch('yahoo.views.RichsUtils.get_tmp_image_folder', return_value='/tmp'), \
                patch('yahoo.views.RichsUtils.get_mws_api', return_value=MagicMock()), \
                patch('yahoo.views._amazon_retry_settings', return_value=retry_settings), \
                patch('yahoo.views.AmazonScraper.get_products', side_effect=ValueError('503')):
            yahoo.views.amazon_offer_research_entry(params, '', user, trial=10, rest_wait_count=1)
        # 指定秒数ウェイトする
        mwait.assert_called_once_with(10)
        user = User.objects.get(username='hoge')
        (actuals, kwactuals) = mqueue().enqueue.call_args_list[0]
        kwargs = kwactuals['kwargs']
        self.assertEquals(actuals[0], yahoo.views.amazon_offer_research_entry)
        self.assertEquals(kwargs['params'], params)
        self.assertEquals(kwargs['url'], '')
        self.assertEquals(kwargs['user'], user)
        # trial は変わらず、rest count が1減る
        self.assertEquals(kwargs['trial'], 10)
        self.assertEquals(kwargs['rest_wait_count'], 0)

        # max_trial に達した場合の処理
        mqueue.reset_mock()
        mlogger.reset_mock()
        with patch('yahoo.views.RichsUtils.get_tmp_image_folder', return_value='/tmp'), \
                patch('yahoo.views.RichsUtils.get_mws_api', return_value=MagicMock()), \
                patch('yahoo.views._amazon_retry_settings', return_value=retry_settings), \
                patch('yahoo.views.AmazonScraper.get_products', side_effect=ValueError('503')):
            yahoo.views.amazon_offer_research_entry(params, '', user, trial=120)
        user = User.objects.get(username='hoge')
        mlogger.info.assert_called_once_with(
            'ユーザー %s の処理中にエラーが発生したため、強制中断しました', user)
        (actuals, _) = mqueue().enqueue.call_args_list[0]
        self.assertEquals(actuals[0], yahoo.views.amazon_offer_research_finalize)

    def _entry_for_maintask(self, mqueue):
        self._entry()
        target = mqueue().enqueue
        (_, kwargs) = target.call_args
        mqueue.reset_mock()
        return kwargs

    def test_maintask_for_urlskip_requests(self, mqueue, mlogger, mwait):
        ''' URLスキップの検証 '''
        args = self._entry_for_maintask(mqueue)
        user = User.objects.get(username='hoge')
        URLSkipRequest.objects.create(author=user, view=11)

        # メルカリ検索のOfferReserchWatcher を追加
        OfferReserchWatcher.objects.create(
            research_type = 1, status = 0, total = 0, exclude_asin = 0, 
            prime = 0, condition_different = 0, exclude_seller = 0, not_found = 0, 
            feed_item = 0, is_over_items=False, author = user)

        # ヤフオク検索の Watcher は存在する
        self.assertEquals(
            OfferReserchWatcher.objects.filter(author=user, research_type=0).count(), 1)
        
        # テスト対象呼び出し
        yahoo.views.amazon_offer_research_task(args['params'], '', user, args['pools'])

        # モックの呼び出しを確認
        self.assertEquals(mlogger.info.call_count, 1)
        self.assertEquals(mlogger.info.call_args[0][0], 
            'ユーザー %s からのURL: %s のスキップリクエストを処理しました。')

        # 現在のURL検索の打ち切りが呼ばれていることを確認
        (actuals, _) = mqueue().enqueue.call_args_list[0]
        self.assertEquals(actuals[0], yahoo.views.amazon_offer_research_finalize)

        # 関連するスキップリクエストに基づくデータのみ消えていることを確認
        self.assertEquals(URLSkipRequest.objects.filter(view=11, author=user).count(), 0)
        self.assertEquals(
            OfferReserchWatcher.objects.filter(author=user, research_type=0).count(), 1)
        self.assertEquals(
            OfferReserchWatcher.objects.filter(author=user, research_type=1).count(), 1)


    def test_maintask_for_stop_requests(self, mqueue, mlogger, mwait):
        args = self._entry_for_maintask(mqueue)
        user = User.objects.get(username='hoge')
        StopRequest.objects.create(author=user, view=11)
        # 別の種類のOfferReserchWatcher がある場合
        OfferReserchWatcher.objects.create(
            research_type = 1, status = 0, total = 0, exclude_asin = 0, 
            prime = 0, condition_different = 0, exclude_seller = 0, not_found = 0, 
            feed_item = 0, is_over_items=False, author = user)

        self.assertEquals(
            OfferReserchWatcher.objects.filter(author=user, research_type=0).count(), 1)
        
        yahoo.views.amazon_offer_research_task(args['params'], '', user, args['pools'])

        self.assertEquals(mlogger.info.call_count, 1)
        self.assertEquals(mlogger.info.call_args[0][0], 
            'ユーザー %s からの停止リクエストを処理しました')
        
        # 関連する停止リクエストに基づくデータのみ消えていることを確認
        self.assertEquals(StopRequest.objects.filter(view=11, author=user).count(), 0)
        self.assertEquals(
            OfferReserchWatcher.objects.filter(author=user, research_type=0).count(), 0)
        self.assertEquals(
            OfferReserchWatcher.objects.filter(author=user, research_type=1).count(), 1)


    def test_maintask_for_empty_input(self, mqueue, mlogger, mwait):
        args = self._entry_for_maintask(mqueue)
        user = User.objects.get(username='hoge')
        pools = args['pools']
        pools['amazon_items'] = pools['rest_amazon_items'] = []
        pools.pop('next_url') # 旧式バージョンでこれまで通りの動きになるか否かのチェック
        amazon_scraper = MagicMock()
        amazon_scraper().get_next_page_url = MagicMock(return_value='')

        with patch('yahoo.views.AmazonScraper', amazon_scraper):
            yahoo.views.amazon_offer_research_task(
                args['params'], '', user, args['pools'])

        self.assertEquals(mlogger.debug.call_count, 2)
        (actuals, _) = mlogger.debug.call_args_list[1]
        self.assertEquals(actuals[0], '全てのAmazon商品の検索を終了しました。seq=%s')

        amazon_scraper().get_products.assert_called_once_with('')
        amazon_scraper().get_next_page_url.assert_called_once()

        # finalize用のメッセージが積まれている
        target = mqueue().enqueue
        self.assertEquals(target.call_count, 1)
        (actuals, kwactuals) = target.call_args_list[0]
        self.assertEquals(actuals[0], yahoo.views.amazon_offer_research_finalize)
        self.assertEquals(set(kwactuals.keys()), set(['params', 'user']))


    def test_maintask_raised_exception_in_item_research(self, mqueue, mlogger, mwait):
        args = self._entry_for_maintask(mqueue)
        user = User.objects.get(username='hoge')
        ExcludeAsin.objects.create(author=user, asin='X123456789')
        amazon_item = {
            'asin': 'A123456789', 'prime': 'False', 
            'image': 'mockimage.jpg', 'title': 'mock',
            'price': '1000', 'price_new': '', 'price_old': '',
        }
        pools = args['pools']
        pools['rest_amazon_items'] = pools['amazon_items'] = [amazon_item]

        amazon_scraper = MagicMock()
        amazon_scraper().get_next_page_url = MagicMock(return_value='')

        with patch('yahoo.views.AmazonScraper', amazon_scraper), \
                patch('yahoo.views.amazon_offer_research_for_item', side_effect=Exception('Mock Exception')):
            yahoo.views.amazon_offer_research_task(
                args['params'], 'url', user, pools)

        self.assertEquals(mlogger.exception.call_count, 1)
        self.assertEquals(mlogger.debug.call_count, 2)
        (actuals, _) = mlogger.debug.call_args_list[1]
        self.assertEquals(actuals[0], '全てのAmazon商品の検索を終了しました。seq=%s')

        watch = OfferReserchWatcher.objects.get(author=user) # load saved watch object
        self.assertEquals(watch.condition_different, 1)


    def test_maintask_over_item(self, mqueue, mlogger, mwait):
        args = self._entry_for_maintask(mqueue)
        user = User.objects.get(username='hoge')
        ExcludeAsin.objects.create(author=user, asin='X123456789')
        amazon_item = {
            'asin': 'A123456789', 'prime': 'False', 
            'image': 'mockimage.jpg', 'title': 'mock',
            'price': '1000', 'price_new': '', 'price_old': '',
        }
        pools = args['pools']
        pools['rest_amazon_items'] = pools['amazon_items'] = [amazon_item]

        amazon_scraper = MagicMock()
        amazon_scraper().get_next_page_url = MagicMock(return_value='')

        def fake(params, user, pools, watch, amazon_item):
            watch.is_over_items = True

        with patch('yahoo.views.AmazonScraper', amazon_scraper), \
                patch('yahoo.views.amazon_offer_research_for_item', side_effect=fake):
            yahoo.views.amazon_offer_research_task(
                args['params'], 'url', user, pools)

        self.assertEquals(mlogger.debug.call_count, 2)
        (actuals, _) = mlogger.debug.call_args_list[1]
        self.assertEquals(actuals[0], '検索可能アイテム数の上限を超えました。user=%s')

        watch = OfferReserchWatcher.objects.get(author=user) # load saved watch object
        self.assertTrue(watch.is_over_items)


    def test_maintask_can_break_when_time_over(self, mqueue, mlogger, mwait):
        args = self._entry_for_maintask(mqueue)
        user = User.objects.get(username='hoge')
        ExcludeAsin.objects.create(author=user, asin='X123456789')
        amazon_item = {
            'asin': 'A123456789', 'prime': 'False', 
            'image': 'mockimage.jpg', 'title': 'mock',
            'price': '1000', 'price_new': '', 'price_old': '',
        }
        pools = args['pools']
        pools['rest_amazon_items'] = pools['amazon_items'] = [
            amazon_item, amazon_item, amazon_item
        ]

        amazon_scraper = MagicMock()
        amazon_scraper().get_products = MagicMock(return_value=['dummy1'])
        amazon_scraper().get_next_page_url = MagicMock(return_value='dummyurl')

        dt1 = datetime.datetime(2000, 1, 1, 0, 0, 0)
        dt2 = datetime.datetime(2000, 1, 1, 0, 0, 0) + \
            datetime.timedelta(seconds=settings.ASYNC_WORKER['TASK_RECOMMENDED_MAXIMUM_SECONDS'])

        def fake(params, user, pools, watch, amazon_item):
            watch.feed_item += 1

        with patch('yahoo.views.datetime') as mdt, \
                patch('yahoo.views.AmazonScraper', amazon_scraper), \
                patch('yahoo.views.amazon_offer_research_for_item', side_effect=fake):
            # Itemを2個検索する
            mdt.now.side_effect = [dt1, dt1, dt2]
            yahoo.views.amazon_offer_research_task(
                args['params'], 'url', user, pools)

        watch = OfferReserchWatcher.objects.get(author=user) # load saved watch object
        self.assertEquals(watch.feed_item, 2)
        self.assertEquals(pools['sequence'], 1)
        self.assertEquals(pools['rest_amazon_items'], [amazon_item])


    def test_maintask_has_next_url(self, mqueue, mlogger, mwait):
        args = self._entry_for_maintask(mqueue)
        user = User.objects.get(username='hoge')
        ExcludeAsin.objects.create(author=user, asin='X123456789')
        amazon_item = {
            'asin': 'A123456789', 'prime': 'False', 
            'image': 'mockimage.jpg', 'title': 'mock',
            'price': '1000', 'price_new': '', 'price_old': '',
        }
        pools = args['pools']
        pools['rest_amazon_items'] = pools['amazon_items'] = []
        pools['next_url'] = 'initial_next_url'

        amazon_scraper = MagicMock()
        amazon_scraper().get_products = MagicMock(return_value=['dummy1'])
        amazon_scraper().get_next_page_url = MagicMock(return_value='next_url')

        with patch('yahoo.views.AmazonScraper', amazon_scraper), \
                patch('yahoo.views.amazon_offer_research_for_item'):
            yahoo.views.amazon_offer_research_task(
                args['params'], 'url', user, pools)

        target = mqueue().enqueue
        self.assertEquals(target.call_count, 1)
        (nameless, actuals) = target.call_args
        self.assertEquals(nameless[0], yahoo.views.amazon_offer_research_task)
        self.assertEquals(actuals['url'], 'initial_next_url')
        self.assertEquals(actuals['pools']['sequence'], 1)
        self.assertEquals(actuals['pools']['next_url'], 'next_url')
        self.assertEquals(actuals['pools']['amazon_items'], ['dummy1'])
        self.assertEquals(actuals['pools']['rest_amazon_items'], ['dummy1'])


    def test_maintask_raise_amazon_response_5xx(self, mqueue, mlogger, mwait):
        ''' Amazon から 5xx レスポンスが返ってきた場合 '''
        args = self._entry_for_maintask(mqueue)
        user = User.objects.get(username='hoge')
        pools = args['pools']
        pools['rest_amazon_items'] = pools['amazon_items'] = [MagicMock()]
        pools['next_url'] = 'initial_next_url'

        amazon_scraper = MagicMock()
        amazon_scraper().get_products = MagicMock(side_effect=ValueError('503'))
        amazon_scraper().get_next_page_url = MagicMock(return_value='')
        retry_settings = { 'MAX_TRIAL': 120, 'TRIAL_WAIT_SECONDS': 10, 'TRIAL_WAIT_COUNT': 8 }

        with patch('yahoo.views.AmazonScraper', amazon_scraper), \
                patch('yahoo.views._amazon_retry_settings', return_value=retry_settings), \
                patch('yahoo.views.amazon_offer_research_for_item'):
            yahoo.views.amazon_offer_research_task(
                args['params'], 'url', user, pools)

        target = mqueue().enqueue
        self.assertEquals(target.call_count, 1)
        (nameless, actuals) = target.call_args
        kwargs = actuals['kwargs']
        self.assertEquals(nameless[0], yahoo.views.amazon_offer_research_task)
        # 同じことを繰り返すので同じ引数での呼び出しになる
        self.assertEquals(kwargs['params'], args['params'])
        self.assertEquals(kwargs['url'], 'url')
        self.assertEquals(kwargs['user'], user)
        self.assertEquals(kwargs['pools'], pools)
        # pools の一部情報は更新されている
        self.assertEquals(kwargs['pools']['sequence'], 1)
        self.assertEquals(kwargs['pools']['rest_amazon_items'], [])
        # trial / rest_wait_count は規定値へ
        self.assertEquals(kwargs['trial'], 1)
        self.assertEquals(kwargs['rest_wait_count'], 8)

        # rest_wait_count > 0 の場合の処理
        mqueue().reset_mock()
        mwait.reset_mock()
        with patch('yahoo.views.AmazonScraper', amazon_scraper), \
                patch('yahoo.views._amazon_retry_settings', return_value=retry_settings), \
                patch('yahoo.views.amazon_offer_research_for_item'):
            yahoo.views.amazon_offer_research_task(
                args['params'], 'url', user, pools, trial=12, rest_wait_count=1)
        target = mqueue().enqueue
        self.assertEquals(target.call_count, 1)
        (nameless, actuals) = target.call_args
        kwargs = actuals['kwargs']
        self.assertEquals(nameless[0], yahoo.views.amazon_offer_research_task)
        # 同じことを繰り返すので同じ引数での呼び出しになる
        self.assertEquals(kwargs['params'], args['params'])
        self.assertEquals(kwargs['url'], 'url')
        self.assertEquals(kwargs['user'], user)
        self.assertEquals(kwargs['pools'], pools)
        # trial / rest_wait_count は規定値へ
        self.assertEquals(kwargs['trial'], 12)
        self.assertEquals(kwargs['rest_wait_count'], 0)

        # 規定回数を超えた場合は強制終了処理へと移動
        mqueue().reset_mock()
        mwait.rest_mock()
        with patch('yahoo.views.AmazonScraper', amazon_scraper), \
                patch('yahoo.views._amazon_retry_settings', return_value=retry_settings), \
                patch('yahoo.views.amazon_offer_research_for_item'):
            yahoo.views.amazon_offer_research_task(
                args['params'], 'url', user, pools, trial=120)

        target = mqueue().enqueue
        self.assertEquals(target.call_count, 1)
        (actuals, kwactuals) = target.call_args
        self.assertEquals(actuals[0], yahoo.views.amazon_offer_research_finalize)
        self.assertEquals(set(kwactuals.keys()), set(['params', 'user']))


    def test_maintask_has_next_url_and_reaches_maximum(self, mqueue, mlogger, mwait):
        args = self._entry_for_maintask(mqueue)
        user = User.objects.get(username='hoge')
        ExcludeAsin.objects.create(author=user, asin='X123456789')
        amazon_item = {
            'asin': 'A123456789', 'prime': 'False', 
            'image': 'mockimage.jpg', 'title': 'mock',
            'price': '1000', 'price_new': '', 'price_old': '',
        }
        pools = args['pools']
        pools['rest_amazon_items'] = pools['amazon_items'] = []

        amazon_scraper = MagicMock()
        amazon_scraper().get_products = MagicMock(return_value=['dummy1'])
        amazon_scraper().get_next_page_url = MagicMock(return_value='dummyurl')

        with patch('yahoo.views.asynchelpers.reached_maximum_sequence', return_value=True), \
                patch('yahoo.views.AmazonScraper', amazon_scraper), \
                patch('yahoo.views.amazon_offer_research_for_item'):
            yahoo.views.amazon_offer_research_task(
                args['params'], 'url', user, pools)

        target = mqueue().enqueue
        self.assertEquals(target.call_count, 1)
        (actuals, kwactuals) = target.call_args
        self.assertEquals(actuals[0], yahoo.views.amazon_offer_research_finalize)
        self.assertEquals(set(kwactuals.keys()), set(['params', 'user']))


    def test_maintask_raise_unknown_exception(self, mqueue, mlogger, mwait):
        args = self._entry_for_maintask(mqueue)
        user = User.objects.get(username='hoge')
        err = Exception('unknown!')

        with patch('yahoo.views.datetime', MagicMock()) as mdt:
            mdt.now = MagicMock(side_effect=err)
            yahoo.views.amazon_offer_research_task(
                args['params'], 'url', user, MagicMock())

        mlogger.info.assert_called_once_with(
            'ユーザー %s の処理中にエラーが発生したため、強制中断しました', user)
        mlogger.exception.assert_called_once_with(err)
        (actuals, _) = mqueue().enqueue.call_args_list[0]
        self.assertEquals(actuals[0], yahoo.views.amazon_offer_research_finalize)


    def test_itemtask_for_exclude_asin(self, mqueue, mlogger, mwait):
        args = self._entry_for_maintask(mqueue)
        user = User.objects.get(username='hoge')
        watch = OfferReserchWatcher.objects.get(author=user)
        ExcludeAsin.objects.create(author=user, asin='A123456789')
        amazon_item = {
            'asin': 'A123456789'
        }
        pools = args['pools']
        pools['amazon_items'] = [{'asin': 'X12345'}, amazon_item]

        self.assertEquals(watch.exclude_asin, 0)
        yahoo.views.amazon_offer_research_for_item(
            args['params'], user, pools, watch, amazon_item)

        self.assertEquals(watch.asin, 'A123456789')
        self.assertEquals(watch.exclude_asin, 1)


    def test_itemtask_for_prime_item(self, mqueue, mlogger, mwait):
        args = self._entry_for_maintask(mqueue)
        user = User.objects.get(username='hoge')
        watch = OfferReserchWatcher.objects.get(author=user)
        ExcludeAsin.objects.create(author=user, asin='X123456789')
        amazon_item = {
            'asin': 'A123456789', 'prime': 'True',
        }
        pools = args['pools']
        pools['amazon_items'] = [amazon_item]

        self.assertEquals(watch.prime, 0)
        yahoo.views.amazon_offer_research_for_item(
            args['params'], user, pools, watch, amazon_item)

        self.assertEquals(watch.asin, 'A123456789')
        self.assertEquals(watch.prime, 1)


    def test_itemtask_for_reserved_item(self, mqueue, mlogger, mwait):
        args = self._entry_for_maintask(mqueue)
        user = User.objects.get(username='hoge')
        watch = OfferReserchWatcher.objects.get(author=user)
        ExcludeAsin.objects.create(author=user, asin='X123456789')
        amazon_item = {
            'asin': 'A123456789', 'prime': 'False', 'reserved': 'True',
        }
        pools = args['pools']
        pools['amazon_items'] = [amazon_item]

        self.assertEquals(watch.prime, 0)
        yahoo.views.amazon_offer_research_for_item(
            args['params'], user, pools, watch, amazon_item)

        self.assertEquals(watch.asin, 'A123456789')
        self.assertEquals(watch.condition_different, 1)


    def test_itemtask_for_price_condition_mismatch(self, mqueue, mlogger, mwait):
        args = self._entry_for_maintask(mqueue)
        user = User.objects.get(username='hoge')
        watch = OfferReserchWatcher.objects.get(author=user)
        ExcludeAsin.objects.create(author=user, asin='X123456789')
        amazon_item = {
            'asin': 'A123456789', 'prime': 'False', 'reserved': 'False',
            'price': '1000', 'price_new': '', 'price_old': '',
        }
        pools = args['pools']
        pools['amazon_items'] = [amazon_item]
        pools['price_setting'].lowest_offer_price_url = 99999999 

        self.assertEquals(watch.condition_different, 0)
        yahoo.views.amazon_offer_research_for_item(
            args['params'], user, pools, watch, amazon_item)

        self.assertEquals(watch.asin, 'A123456789')
        self.assertEquals(watch.condition_different, 1)


    def test_itemtask_for_price_condition_no_margin(self, mqueue, mlogger, mwait):
        args = self._entry_for_maintask(mqueue)
        user = User.objects.get(username='hoge')
        watch = OfferReserchWatcher.objects.get(author=user)
        ExcludeAsin.objects.create(author=user, asin='X123456789')
        amazon_item = {
            'asin': 'A123456789', 'prime': 'False', 'reserved': 'False',
            'price': '1000', 'price_new': '', 'price_old': '',
        }
        pools = args['pools']
        pools['amazon_items'] = [amazon_item]
        pools['price_setting'].lowest_offer_price_url = 100
        pools['price_setting'].margin_offer_url = 500
        pools['price_setting'].offset_offer_price_url = 501

        self.assertEquals(watch.condition_different, 0)
        yahoo.views.amazon_offer_research_for_item(
            args['params'], user, pools, watch, amazon_item)

        self.assertEquals(watch.asin, 'A123456789')
        self.assertEquals(watch.condition_different, 1)

        pools['price_setting'].margin_offer_url = 500
        pools['price_setting'].offset_offer_price_url = 500
        yahoo.views.amazon_offer_research_for_item(
            args['params'], user, pools, watch, amazon_item)

        self.assertEquals(watch.condition_different, 2)

    def test_itemtask_for_price_yahoo_item_not_found(self, mqueue, mlogger, mwait):
        args = self._entry_for_maintask(mqueue)
        user = User.objects.get(username='hoge')
        watch = OfferReserchWatcher.objects.get(author=user)
        ExcludeAsin.objects.create(author=user, asin='X123456789')
        amazon_item = {
            'asin': 'A123456789', 'prime': 'False', 'reserved': 'False',
            'title': 'mock', 'price': '1000', 'price_new': '', 'price_old': '',
        }
        pools = args['pools']
        pools['amazon_items'] = [amazon_item]
        pools['price_setting'].lowest_offer_price_url = 100
        pools['price_setting'].margin_offer_url = 500
        pools['price_setting'].offset_offer_price_url = 499

        yahoo_scraper = MagicMock()
        yahoo_scraper().get_products = MagicMock(return_value=[])

        self.assertEquals(watch.not_found, 0)
        with patch('yahoo.views.YahooSearchScraper', yahoo_scraper):
            yahoo.views.amazon_offer_research_for_item(
                args['params'], user, pools, watch, amazon_item)

        self.assertEquals(watch.asin, 'A123456789')
        self.assertEquals(watch.not_found, 1)


    def test_itemtask_for_price_yahoo_item_all_invalid(self, mqueue, mlogger, mwait):
        args = self._entry_for_maintask(mqueue)
        user = User.objects.get(username='hoge')
        watch = OfferReserchWatcher.objects.get(author=user)
        ExcludeAsin.objects.create(author=user, asin='X123456789')
        amazon_item = {
            'asin': 'A123456789', 'prime': 'False', 'reserved': 'False',
            'image': 'mockimage.jpg', 'title': 'mock',
            'price': '1000', 'price_new': '', 'price_old': '',
        }
        pools = args['pools']
        pools['amazon_items'] = [amazon_item]
        pools['price_setting'].lowest_offer_price_url = 100
        pools['price_setting'].margin_offer_url = 500
        pools['price_setting'].offset_offer_price_url = 499

        amazon_scraper = MagicMock()
        amazon_scraper().save_image = MagicMock(return_value='mock/amazon')
        yahoo_items = [
            { 'title': 'title', 'auction_id': 'Y123456789', 'images': ['image/yahoo'], },
            { 'title': 'title', 'auction_id': 'Z123456789', 'images': ['image/yahoo2'], },
        ]
        yahoo_scraper= MagicMock()
        yahoo_scraper().get_products = MagicMock(return_value=yahoo_items)

        mdownloader = MagicMock()
        mdownloader().__enter__().get = MagicMock(side_effect=[None, '/tmp/mock/yahoo']) 
        self.assertEquals(watch.condition_different, 0)
        with patch('yahoo.views.ItemImageComparator.similar_fast', return_value=(False, 0.0)) as mdiff, \
                patch('yahoo.views.AmazonScraper', amazon_scraper), \
                patch('yahoo.views.YahooSearchScraper', yahoo_scraper), \
                patch('yahoo.views.ImageDownloader', mdownloader), \
                patch('yahoo.views.RichsUtils.delete_file_if_exist'):
            yahoo.views.amazon_offer_research_for_item(
                args['params'], user, pools, watch, amazon_item)
            
            self.assertEquals(mdiff.call_count, 1)
            (args, _) = mdiff.call_args_list[0]
            self.assertEquals(args[0], '/tmp/mock/amazon')
            self.assertEquals(args[1], '/tmp/mock/yahoo')

        self.assertEquals(watch.asin, 'A123456789')
        self.assertEquals(watch.condition_different, 1)


    def test_itemtask_for_price_yahoo_item_skipped(self, mqueue, mlogger, mwait):
        args = self._entry_for_maintask(mqueue)
        user = User.objects.get(username='hoge')
        watch = OfferReserchWatcher.objects.get(author=user)
        ExcludeAsin.objects.create(author=user, asin='X123456789')
        BannedKeyword.objects.create(banned_keyword='banned')
        
        amazon_item = {
            'asin': 'A123456789', 'prime': 'False', 'reserved': 'False',
            'image': 'mockimage.jpg', 'title': 'mock',
            'price': '1000', 'price_new': '', 'price_old': '',
        }
        pools = args['pools']
        pools['amazon_items'] = [amazon_item]
        pools['price_setting'].lowest_offer_price_url = 100
        pools['price_setting'].margin_offer_url = 500
        pools['price_setting'].offset_offer_price_url = 499

        amazon_scraper = MagicMock()
        amazon_scraper().save_image = MagicMock(return_value='mock/amazon')
        yahoo_items = [
            { 'title': 'banned', 'auction_id': 'X123456789', 'images': ['image/yahoo'], 'seller': 'good.seller' },
            { 'title': 'title', 'auction_id': 'Y123456789', 'images': ['image/yahoo'], 'seller': 'bad.seller' },
            { 'title': 'title', 'auction_id': 'Z123456789', 'images': ['image/yahoo2'],'seller': 'no.good.seller' },
        ]
        yahoo_scraper = MagicMock()
        yahoo_scraper().get_products = MagicMock(return_value=yahoo_items)

        yahoo_auction_id_scraper = MagicMock()
        yahoo_auction_id_scraper().get_products = MagicMock(return_value=[
            {'rate_percent': '79.0' }
        ])

        mdownloader = MagicMock()
        mdownloader().__enter__().get = MagicMock(return_value='/tmp/mock/yahoo')

        with patch('yahoo.views.ItemImageComparator.similar_fast', return_value=(True, 1.0)) as mdiff, \
                patch('yahoo.views.AmazonScraper', amazon_scraper), \
                patch('yahoo.views.YahooSearchScraper', yahoo_scraper), \
                patch('yahoo.views.YahooAuctionIdScraper', yahoo_auction_id_scraper), \
                patch('yahoo.views.ImageDownloader', mdownloader), \
                patch('yahoo.views.RichsUtils.delete_file_if_exist'):
            self.assertEquals(watch.exclude_seller, 0)
            self.assertEquals(watch.condition_different, 0)

            yahoo.views.amazon_offer_research_for_item(
                args['params'], user, pools, watch, amazon_item)

            self.assertEquals(watch.asin, 'A123456789')
            self.assertEquals(watch.exclude_seller, 1)
            self.assertEquals(watch.condition_different, 1)


    def test_itemtask_for_price_yahoo_item_comparas(self, mqueue, mlogger, mwait):
        args = self._entry_for_maintask(mqueue)
        user = User.objects.get(username='hoge')
        watch = OfferReserchWatcher.objects.get(author=user)
        ExcludeAsin.objects.create(author=user, asin='X123456789')
        amazon_item = {
            'asin': 'A123456789', 'prime': 'False', 'reserved': 'False',
            'image': 'mockimage.jpg', 'title': 'mock',
            'price': '1000', 'price_new': '', 'price_old': '',
        }
        pools = args['pools']
        pools['amazon_items'] = [amazon_item]
        pools['price_setting'].lowest_offer_price_url = 100
        pools['price_setting'].margin_offer_url = 500
        pools['price_setting'].offset_offer_price_url = 499
 
        amazon_scraper = MagicMock()
        amazon_scraper().save_image = MagicMock(return_value='mock/amazon')
        yahoo_items = [
            { 'title': 'title', 'auction_id': 'Y123456789', 'images': ['image/yahoo'], 'seller': 'S1' },
            { 'title': 'title', 'auction_id': 'Z123456789', 'images': ['image/yahoo2'],'seller': 'S2' },
        ]
        yahoo_scraper = MagicMock()
        yahoo_scraper().get_products = MagicMock(return_value=yahoo_items)

        yahoo_auction_id_scraper = MagicMock()
        yahoo_auction_id_scraper().get_products = MagicMock(return_value=[
            {'rate_percent': '100.0', 'auction_id': 'Z123456789', 
              'bid_or_buy': '3000', 'current_price': '2000', 'seller': 'Y1',
              'condition': '新品', 'images': ['image/yahoo1', 'image/yahoo2'] }, 
        ])

        mdownloader = MagicMock()
        mdownloader().__enter__().get = MagicMock(return_value='/tmp/mock/yahoo')

        with patch('yahoo.views.ItemImageComparator.similar_fast', return_value=(True, 1.0)), \
                patch('yahoo.views.AmazonScraper', amazon_scraper), \
                patch('yahoo.views.YahooSearchScraper', yahoo_scraper), \
                patch('yahoo.views.YahooAuctionIdScraper', yahoo_auction_id_scraper), \
                patch('yahoo.views.ImageDownloader', mdownloader), \
                patch('yahoo.views.RichsUtils.delete_file_if_exist'), \
                patch('yahoo.views.RichsUtils.is_exclude_sellers', return_value=False):
            
            # available_for_purchase が超過判定を行った場合
            with patch('yahoo.views.available_for_purchase', return_value=-3):
                self.assertEquals(watch.feed_item, 0)
                self.assertFalse(watch.is_over_items)
                self.assertEquals(watch.exclude_seller, 0)
                self.assertEquals(watch.condition_different, 0)

                yahoo.views.amazon_offer_research_for_item(
                    args['params'], user, pools, watch, amazon_item)

                self.assertEquals(watch.feed_item, 0)
                self.assertTrue(watch.is_over_items)
                self.assertEquals(watch.exclude_seller, 0)
                self.assertEquals(watch.condition_different, 0)

            watch.is_over_items = False

            # available_for_purchase がその他異常判定を行った場合、全て不一致と判定
            with patch('yahoo.views.available_for_purchase', return_value=-1):
                self.assertEquals(watch.feed_item, 0)
                self.assertFalse(watch.is_over_items)
                self.assertEquals(watch.exclude_seller, 0)
                self.assertEquals(watch.condition_different, 0)

                yahoo.views.amazon_offer_research_for_item(
                    args['params'], user, pools, watch, amazon_item)

                self.assertEquals(watch.feed_item, 0)
                self.assertFalse(watch.is_over_items)
                self.assertEquals(watch.exclude_seller, 0)
                self.assertEquals(watch.condition_different, 1)

            watch.condition_different = 0

            # availabel_for_purchase が正常判定を行った場合
            with patch('yahoo.views.available_for_purchase', return_value=0):
                # 最終画像判定が NG
                dummy1 = MagicMock()
                dummy1.standard_price = 3000
                dummy1.purchase_price = 2000
                dummy2 = MagicMock()
                dummy2.standard_price = 4000
                dummy2.purchase_price = 2000
                with patch('yahoo.views.ItemImageComparator.similar', return_value=(False, [])), \
                        patch('yahoo.views.print'), \
                        patch('yahoo.views.create_item_candidate_in_ride_search', side_effect=[dummy1, dummy2]):
                    self.assertEquals(watch.feed_item, 0)
                    self.assertFalse(watch.is_over_items)
                    self.assertEquals(watch.exclude_seller, 0)
                    self.assertEquals(watch.condition_different, 0)

                    # 該当ユーザーでデータが存在すること
                    ItemCandidateToCsv.objects.create(owner=user, max_output=100)
                    yahoo.views.amazon_offer_research_for_item(
                        args['params'], user, pools, watch, amazon_item)

                    self.assertEquals(watch.feed_item, 0)
                    self.assertFalse(watch.is_over_items)
                    self.assertEquals(watch.exclude_seller, 0)
                    self.assertEquals(watch.condition_different, 0)
                    self.assertEquals(watch.new_feed_item_candidate, 1)
                    dummy1.save.assert_not_called()
                    dummy2.save.assert_called_once()

                watch.new_feed_item_candidate = 0

                # 最終画像判定が OK, store で意図せぬエラー
                with patch('yahoo.views.ItemImageComparator.similar', return_value=(True, [])), \
                        patch('yahoo.views.store', return_value=-1):
                    self.assertEquals(watch.feed_item, 0)
                    self.assertFalse(watch.is_over_items)
                    self.assertEquals(watch.exclude_seller, 0)
                    self.assertEquals(watch.condition_different, 0)
                    self.assertEquals(watch.new_feed_item_candidate, 0)

                    yahoo.views.amazon_offer_research_for_item(
                        args['params'], user, pools, watch, amazon_item)

                    self.assertEquals(watch.feed_item, 0)
                    self.assertFalse(watch.is_over_items)
                    self.assertEquals(watch.exclude_seller, 0)
                    self.assertEquals(watch.condition_different, 1)
                    self.assertEquals(watch.new_feed_item_candidate, 0)

                watch.condition_different = 0

                # 全てOK
                with patch('yahoo.views.ItemImageComparator.similar', return_value=(True, [])), \
                        patch('yahoo.views.store', return_value=0):
                    self.assertEquals(watch.feed_item, 0)
                    self.assertFalse(watch.is_over_items)
                    self.assertEquals(watch.exclude_seller, 0)
                    self.assertEquals(watch.condition_different, 0)
                    self.assertEquals(watch.new_feed_item_candidate, 0)

                    yahoo.views.amazon_offer_research_for_item(
                        args['params'], user, pools, watch, amazon_item)

                    self.assertEquals(watch.feed_item, 1)
                    self.assertFalse(watch.is_over_items)
                    self.assertEquals(watch.exclude_seller, 0)
                    self.assertEquals(watch.condition_different, 0)
                    self.assertEquals(watch.new_feed_item_candidate, 0)

                watch.feed_item = 0


    def test_finalizetask_raise_exception(self, mqueue, mlogger, mwait):
        args = self._entry_for_maintask(mqueue)
        user = User.objects.get(username='hoge')

        watch = OfferReserchWatcher.objects.get(author=user)
        watch.delete() 

        # raise NotFound Exception
        yahoo.views.amazon_offer_research_finalize(args['params'], user)

        (actuals, _) = mlogger.error.call_args_list[0]
        self.assertEquals(actuals[0], '終了処理中にエラーが発生しました。')


    def test_finalizetask_without_csv_download(self, mqueue, mlogger, mwait):
        args = self._entry_for_maintask(mqueue)
        user = User.objects.get(username='hoge')
        watch = OfferReserchWatcher.objects.get(author=user)
        watch.feed_item = 1
        watch.save()

        StopRequest.objects.create(view=11, author=user)
        self.assertEquals(StopRequest.objects.filter(view=11, author=user).count(), 1)

        with patch('yahoo.views.datetime') as mdt:
            mdt.now = MagicMock(return_value=datetime.datetime(2000, 1, 1, 0, 0, 0))
            params = QueryDict('is_export_csv=0')
            yahoo.views.amazon_offer_research_finalize(params, user)

        watch = OfferReserchWatcher.objects.get(author=user)
        self.assertEquals(watch.status, 1)
        self.assertEquals(watch.end_date, datetime.datetime(2000, 1, 1, 0, 0, 0))

        self.assertEquals(StopRequest.objects.filter(view=11, author=user).count(), 0)


    def test_finalizetask_with_csv_download_and_no_item(self, mqueue, mlogger, mwait):
        args = self._entry_for_maintask(mqueue)
        user = User.objects.get(username='hoge')
        watch = OfferReserchWatcher.objects.get(author=user)
        watch.feed_item = 1
        watch.save()

        YahooToAmazonItem.objects.filter(feed_type=1, csv_flag=0, author=user).delete()
        self.assertEquals(YahooToAmazonItem.objects.filter(feed_type=1, csv_flag=0, author=user).count(), 0)

        with patch('yahoo.views.datetime') as mdt, \
                patch('yahoo.views.export_amazon_offer_csv_internal') as minternal:
            mdt.now = MagicMock(return_value=datetime.datetime(2000, 1, 1, 0, 0, 0))
            params = QueryDict('is_export_csv=1')
            yahoo.views.amazon_offer_research_finalize(params, user)
            # YahooToAmazonItem がない場合は呼び出しが発生しない
            self.assertEquals(minternal.call_count, 0)

        watch = OfferReserchWatcher.objects.get(author=user)
        self.assertEquals(watch.status, 2)
        self.assertEquals(watch.end_date, datetime.datetime(2000, 1, 1, 0, 0, 0))

        self.assertEquals(StopRequest.objects.filter(view=11, author=user).count(), 0)


    def test_finalizetask_with_csv_download_and_item(self, mqueue, mlogger, mwait):
        args = self._entry_for_maintask(mqueue)
        user = User.objects.get(username='hoge')
        watch = OfferReserchWatcher.objects.get(author=user)
        watch.feed_item = 1
        watch.save()

        YahooToAmazonItem.objects.create(
            item_sku='item sku', standard_price=1000, standard_price_points=100,
            quantity=10, external_product_id='xxx', 
            external_product_id_type='yyy',
            condition_type='', condition_note='', 
            fulfillment_latency=24, 
            feed_type=1, csv_flag=0, author=user)
        self.assertEquals(
            YahooToAmazonItem.objects.filter(feed_type=1, csv_flag=0, author=user).count(), 1)
        self.assertEquals(
            YahooToAmazonItem.objects.filter(feed_type=1, csv_flag=1, author=user).count(), 0)
        self.assertEquals(
            YahooToAmazonCSV.objects.filter(feed_type=1, author=user).count(), 0)

        with patch('yahoo.views.print'), \
                patch('yahoo.views.datetime') as mdt, \
                patch('yahoo.views.os.path.isdir', return_value=True), \
                patch('yahoo.views.codecs'), \
                patch('yahoo.views.settings') as msettings:
            msettings.RICHS_FOLDER_CSV_OUTPUT = '.'
            mdt.now = MagicMock(return_value=datetime.datetime(2000, 1, 1, 0, 0, 0))
            params = QueryDict('is_export_csv=1')
            yahoo.views.amazon_offer_research_finalize(params, user)

        watch = OfferReserchWatcher.objects.get(author=user)
        self.assertEquals(watch.status, 2)
        self.assertEquals(watch.end_date, datetime.datetime(2000, 1, 1, 0, 0, 0))

        self.assertEquals(StopRequest.objects.filter(view=11, author=user).count(), 0)

        # updated
        self.assertEquals(
            YahooToAmazonItem.objects.filter(feed_type=1, csv_flag=0, author=user).count(), 0)
        self.assertEquals(
            YahooToAmazonItem.objects.filter(feed_type=1, csv_flag=1, author=user).count(), 1)
        # added
        self.assertEquals(
            YahooToAmazonCSV.objects.filter(feed_type=1, author=user).count(), 1)


    def test_finalizetask_with_csv_download_exception(self, mqueue, mlogger, mwait):
        args = self._entry_for_maintask(mqueue)
        user = User.objects.get(username='hoge')
        watch = OfferReserchWatcher.objects.get(author=user)
        watch.feed_item = 1
        watch.save()

        YahooToAmazonItem.objects.create(
            item_sku='item sku', standard_price=1000, standard_price_points=100,
            quantity=10, external_product_id='xxx', 
            external_product_id_type='yyy',
            condition_type='', condition_note='', 
            fulfillment_latency=24, 
            feed_type=1, csv_flag=0, author=user)
        self.assertEquals(
            YahooToAmazonItem.objects.filter(feed_type=1, csv_flag=0, author=user).count(), 1)
        self.assertEquals(
            YahooToAmazonCSV.objects.filter(feed_type=1, author=user).count(), 0)

        with patch('yahoo.views.print'), \
                patch('yahoo.views.datetime') as mdt, \
                patch('yahoo.views.export_amazon_offer_csv_internal', side_effect=Exception('csv error')):
            mdt.now = MagicMock(return_value=datetime.datetime(2000, 1, 1, 0, 0, 0))
            params = QueryDict('is_export_csv=1')
            yahoo.views.amazon_offer_research_finalize(params, user)

        (actuals, _) = mlogger.warn.call_args_list[0]
        self.assertEquals(actuals[0], 'CSV Exportに失敗しました。')

        watch = OfferReserchWatcher.objects.get(author=user)
        self.assertEquals(watch.status, 1)
        self.assertEquals(watch.end_date, datetime.datetime(2000, 1, 1, 0, 0, 0))

        self.assertEquals(StopRequest.objects.filter(view=11, author=user).count(), 0)


    def test_finalizetask_with_csv_download_invalid_export(self, mqueue, mlogger, mwait):
        args = self._entry_for_maintask(mqueue)
        user = User.objects.get(username='hoge')
        watch = OfferReserchWatcher.objects.get(author=user)
        watch.feed_item = 1
        watch.save()

        YahooToAmazonItem.objects.create(
            item_sku='item sku', standard_price=1000, standard_price_points=100,
            quantity=10, external_product_id='xxx', 
            external_product_id_type='yyy',
            condition_type=None, condition_note='', 
            fulfillment_latency=24, 
            feed_type=1, csv_flag=0, author=user)
        self.assertEquals(
            YahooToAmazonItem.objects.filter(feed_type=1, csv_flag=0, author=user).count(), 1)
        self.assertEquals(
            YahooToAmazonItem.objects.filter(feed_type=1, csv_flag=1, author=user).count(), 0)
        self.assertEquals(
            YahooToAmazonCSV.objects.filter(feed_type=1, author=user).count(), 0)

        with patch('yahoo.views.print'), \
                patch('yahoo.views.datetime') as mdt, \
                patch('yahoo.views.os.path.isdir', return_value=True), \
                patch('yahoo.views.codecs'), \
                patch('yahoo.views.settings') as msettings:
            msettings.RICHS_FOLDER_CSV_OUTPUT = '.'
            mdt.now = MagicMock(return_value=datetime.datetime(2000, 1, 1, 0, 0, 0))
            params = QueryDict('is_export_csv=1')
            yahoo.views.amazon_offer_research_finalize(params, user)

        watch = OfferReserchWatcher.objects.get(author=user)
        self.assertEquals(watch.status, 2)
        self.assertEquals(watch.end_date, datetime.datetime(2000, 1, 1, 0, 0, 0))

        self.assertEquals(StopRequest.objects.filter(view=11, author=user).count(), 0)

        # non updated (error line skipped)
        self.assertEquals(
            YahooToAmazonItem.objects.filter(feed_type=1, csv_flag=0, author=user).count(), 1)
        self.assertEquals(
            YahooToAmazonItem.objects.filter(feed_type=1, csv_flag=1, author=user).count(), 0)
        # added
        self.assertEquals(
            YahooToAmazonCSV.objects.filter(feed_type=1, author=user).count(), 1)


    def test_available_for_purchase(self, mqueue, mlogger, mwait):
        ''' yahoo.views.available_for_purchase の C0 カバレッジ '''
        # デフォルト設定の場合
        # Amazon販売額 ::= 6000 (10000 - 4000)
        # Yahoo購入額  ::= 4200
        # 利益率       ::= (6000 - 4200) / 6000 = 0.3
        amazon_item = {
            'price_new': '10000',
            'price_old': '999',
        }
        yahoo_item = {
            'title': '【送料無料・激レア】ヤフオクの有効なアイテムは30文字以上。', 
            'auction_id': 'SKU', 'condition': 'DUMMY', 
            'bid_or_buy': '4200', 'current_price': '1000', 
            'fulfillment_latency': '6', 'delivery_from': '東京都',
        }
        # テストで利用する設定値
        ridesearch_conf = {
            'MINIMUM_TITLE_LENGTH': 30, 
            'MINIMUM_PROFIT': 0.3,
            'MAXIMUM_FULFILLMENT': 6,
            'IGNORE_DELIVERY_FROM': ['海外'],
        }
        value = 1.0
        user = MagicMock()
        user.max_items = 10
        price_setting = MagicMock()
        price_setting.offset_offer_price_url = -4000
        price_setting.margin_offer_url = 1
        amazon_image = '/tmp/mock/amazon'

        with patch('yahoo.views.settings') as msettings:
            # 設定は推奨の値を利用 (ローカルはUIテスト用に書き換わっていることがある)
            msettings.YAHOO_RIDE_SEARCH_CONFIG = ridesearch_conf

            with patch('yahoo.views.YahooToAmazonItem.objects.filter') as mf:
                mf().count.return_value = 11
                code = yahoo.views.available_for_purchase(
                    amazon_item, yahoo_item, value, user, price_setting,
                    amazon_image)
                self.assertEqual(code, -3)

            with patch('yahoo.views.YahooToAmazonItem.objects.filter') as mf:
                mf().count.side_effect = [0, 1] 
                code = yahoo.views.available_for_purchase(
                    amazon_item, yahoo_item, value, user, price_setting,
                    amazon_image)
                self.assertEqual(code, -2)

            with patch('yahoo.views.YahooToAmazonItem.objects.filter') as mf, \
                    patch('yahoo.views.RichsUtils.yahoo_to_amazon_condition', return_value='ERR'):
                mf().count.return_value = 0
                code = yahoo.views.available_for_purchase(
                    amazon_item, yahoo_item, value, user, price_setting,
                    amazon_image)
                self.assertEqual(code, -1)

            with patch('yahoo.views.YahooToAmazonItem.objects.filter') as mf, \
                    patch('yahoo.views.RichsUtils.yahoo_to_amazon_condition', return_value='New'):
                mf().count.return_value = 0
                dummy_item = {'price_new': '-1', 'price_old': '-1'}
                code = yahoo.views.available_for_purchase(
                    dummy_item, yahoo_item, value, user, price_setting,
                    amazon_image)
                self.assertEqual(code, -1)

            with patch('yahoo.views.YahooToAmazonItem.objects.filter') as mf, \
                    patch('yahoo.views.RichsUtils.yahoo_to_amazon_condition', return_value='Old'):
                mf().count.return_value = 0
                dummy_item = {'price_new': '-1', 'price_old': '-1'}
                code = yahoo.views.available_for_purchase(
                    dummy_item, yahoo_item, value, user, price_setting,
                    amazon_image)
                self.assertEqual(code, -1)

            with patch('yahoo.views.YahooToAmazonItem.objects.filter') as mf, \
                    patch('yahoo.views.RichsUtils.yahoo_to_amazon_condition', return_value='New'):
                mf().count.return_value = 0
                dummy = MagicMock()
                dummy.offset_offer_price_url = 200
                dummy.margin_offer_url = 100000
                code = yahoo.views.available_for_purchase(
                    amazon_item, yahoo_item, value, user, dummy,
                    amazon_image)
                self.assertEqual(code, -1)

            with patch('yahoo.views.YahooToAmazonItem.objects.filter') as mf, \
                    patch('yahoo.views.RichsUtils.yahoo_to_amazon_condition', return_value='New'):
                mf().count.return_value = 0
                dummy_item = yahoo_item.copy()
                # 29文字
                dummy_item['title'] = '【送料無料・激レア】ヤフオクの有効なアイテムは30文字以上'
                code = yahoo.views.available_for_purchase(
                    amazon_item, dummy_item, value, user, price_setting,
                    amazon_image)
                self.assertEqual(code, -4)

            with patch('yahoo.views.YahooToAmazonItem.objects.filter') as mf, \
                    patch('yahoo.views.RichsUtils.yahoo_to_amazon_condition', return_value='New'):
                mf().count.return_value = 0
                dummy_item = yahoo_item.copy()
                dummy_item['bid_or_buy'] = '4201'  # 利益率が30%を切る
                code = yahoo.views.available_for_purchase(
                    amazon_item, dummy_item, value, user, price_setting,
                    amazon_image)
                self.assertEqual(code, -5)

            with patch('yahoo.views.YahooToAmazonItem.objects.filter') as mf, \
                    patch('yahoo.views.RichsUtils.yahoo_to_amazon_condition', return_value='New'):
                mf().count.return_value = 0
                dummy_item = yahoo_item.copy()
                dummy_item['delivery_from'] = '海外'
                code = yahoo.views.available_for_purchase(
                    amazon_item, dummy_item, value, user, price_setting,
                    amazon_image)
                self.assertEqual(code, -6)

            with patch('yahoo.views.YahooToAmazonItem.objects.filter') as mf, \
                    patch('yahoo.views.RichsUtils.yahoo_to_amazon_condition', return_value='New'):
                mf().count.return_value = 0
                dummy_item = yahoo_item.copy()
                dummy_item['fulfillment_latency'] = '7'
                code = yahoo.views.available_for_purchase(
                    amazon_item, dummy_item, value, user, price_setting,
                    amazon_image)
                self.assertEqual(code, -7)


            with patch('yahoo.views.YahooToAmazonItem.objects.filter') as mf, \
                    patch('yahoo.views.RichsUtils.yahoo_to_amazon_condition', return_value='New'):
                mf().count.return_value = 0
                code = yahoo.views.available_for_purchase(
                    amazon_item, yahoo_item, value, user, price_setting,
                    amazon_image)
                self.assertEqual(code, 0)

            with patch('yahoo.views.YahooToAmazonItem.objects.filter') as mf, \
                    patch('yahoo.views.RichsUtils.yahoo_to_amazon_condition', return_value='New'):
                mf().count.side_effect = ValueError('mocked!')
                code = yahoo.views.available_for_purchase(
                    amazon_item, yahoo_item, value, user, price_setting,
                    amazon_image)
                self.assertEqual(code, -9)


    def test_item_list_status_message(self, mqueue, mlogger, mwait):
        ''' _item_list_status_message の C0 カバレッジ '''
        item = YahooToAmazonItem()
        item.update_quantity_request = 0
        item.current_purchase_quantity = 0
        self.assertEqual('取り下げ完了', yahoo.views._item_list_status_message(item)) 
        item.update_quantity_request = 1
        item.current_purchase_quantity = 0
        self.assertEqual('取り下げ中(適用待ち)', yahoo.views._item_list_status_message(item)) 
        self.assertEqual('取り下げ中<br>(適用待ち)', yahoo.views._item_list_status_message(item, br=True)) 
        item.update_quantity_request = 0
        item.current_purchase_quantity = 1
        self.assertEqual('出品中', yahoo.views._item_list_status_message(item)) 
        item.update_quantity_request = 1
        item.current_purchase_quantity = 1
        self.assertEqual('出品中(適用待ち)', yahoo.views._item_list_status_message(item)) 
        self.assertEqual('出品中<br>(適用待ち)', yahoo.views._item_list_status_message(item, br=True)) 


    def test_item_list_inventory_message(self, mqueue, mlogger, mwait):
        ''' _item_list_inventory_message の C0 カバレッジ '''
        item = YahooToAmazonItem()
        item.update_quantity_request = 1
        item.update_fulfillment_latency_request = 1
        self.assertEqual('在庫数適用待ち(リードタイム適用待ち)', 
            yahoo.views._item_list_inventory_message(item)) 
        self.assertEqual('在庫数適用待ち<br>リードタイム適用待ち', 
            yahoo.views._item_list_inventory_message(item, br=True)) 
        item.update_quantity_request = 1
        item.update_fulfillment_latency_request = 0
        self.assertEqual('在庫数適用待ち', yahoo.views._item_list_inventory_message(item)) 

        item.update_quantity_request = 0
        item.update_fulfillment_latency_request = 0
        item.record_type = 20
        item.updated_date = datetime.datetime(2001, 1, 1, 1, 2, 3)
        item.current_purchase_quantity = 1
        self.assertEqual('2001年01月01日 01時02分03秒に在庫数を1に変更しました。',
            yahoo.views._item_list_inventory_message(item)) 
        self.assertEqual('2001年01月01日 01時02分03秒<br>在庫数を「1」に変更しました。',
            yahoo.views._item_list_inventory_message(item, br=True)) 

        item.record_type = 21
        item.update_fulfillment_latency_request = 1
        item.updated_date = datetime.datetime(2001, 1, 1, 1, 2, 3)
        self.assertEqual('2001年01月01日 01時02分03秒に在庫数を1に変更しました。(リードタイム適用待ち)',
            yahoo.views._item_list_inventory_message(item)) 
        self.assertEqual('2001年01月01日 01時02分03秒<br>在庫数を「1」に変更しました。<br>リードタイム適用待ち',
            yahoo.views._item_list_inventory_message(item, br=True)) 

        item.update_quantity_request = 0
        item.update_fulfillment_latency_request = 1
        item.record_type = 0
        self.assertEqual('リードタイム適用待ち', yahoo.views._item_list_inventory_message(item)) 

        item.update_quantity_request = 0
        item.update_fulfillment_latency_request = 0
        item.record_type = 0
        self.assertEqual('', yahoo.views._item_list_inventory_message(item)) 


    def test_url_search_cancel(self, mqueue, mlogger, mwait):
        ''' 検索の結果が芳しくない場合、URL検索をキャンセルできるか否か '''
        args = self._entry_for_maintask(mqueue)
        user = User.objects.get(username='hoge')
        watch = OfferReserchWatcher.objects.get(research_type=0, author=user)
        watch.current_url = 'current_url'
        watch.save()

        amazon_item = {
            'asin': 'A123456789', 'prime': 'False', 
            'image': 'mockimage.jpg', 'title': 'mock',
            'price': '1000', 'price_new': '', 'price_old': '',
        }
        pools = args['pools']
        pools['rest_amazon_items'] = pools['amazon_items'] = [ amazon_item for _ in range(1001) ]
        pools['next_url'] = 'initial_next_url'

        now = datetime.datetime(2001, 1, 1, 1, 2, 3)
        def not_found(*args, **kwargs):
            return

        ride_search_config = {
            'SKIP_JUDGE_ITEM': 256,           # URLの打ち切りのために調べるアイテム数
            'SKIP_JUDGE_LOWER_ITEM': 10,      # URLの打ち切り判定時にこのアイテム数よりも小さい場合は打ち切る
        }

        with patch('yahoo.views.datetime') as mdt, \
                patch('yahoo.views._ride_search_config', return_value=ride_search_config), \
                patch('yahoo.views.amazon_offer_research_for_item', side_effect=not_found):
            mdt.now = MagicMock(return_value=now)
            yahoo.views.amazon_offer_research_task(args['params'], 'url', user, pools)

        target = mqueue().enqueue
        self.assertEquals(target.call_count, 1)
        (nameless, actuals) = target.call_args
        self.assertEquals(pools['item_search_count'], 256)
        self.assertEquals(pools['item_search_found'], 0)
        self.assertEquals(nameless[0], yahoo.views.amazon_offer_research_finalize)
        self.assertEquals(mlogger.info.call_count, 1)
        self.assertEquals(mlogger.info.call_args[0][0], 
            'URL: %s - %s件検索しましたが、見つかったアイテムが%s個 (< %s)のため打ち切ります。')
        self.assertEquals(mlogger.info.call_args[0][1], 'current_url')
        self.assertEquals(mlogger.info.call_args[0][2], 256)
        self.assertEquals(mlogger.info.call_args[0][3], 0)
        self.assertEquals(mlogger.info.call_args[0][4], 10)


    def test_url_search_found_but_cancel(self, mqueue, mlogger, mwait):
        ''' 検索の結果が芳しくない場合、URL検索をキャンセルできるか否か '''
        args = self._entry_for_maintask(mqueue)
        user = User.objects.get(username='hoge')
        watch = OfferReserchWatcher.objects.get(research_type=0, author=user)
        watch.current_url = 'current_url'
        watch.save()

        amazon_item = {
            'asin': 'A123456789', 'prime': 'False', 
            'image': 'mockimage.jpg', 'title': 'mock',
            'price': '1000', 'price_new': '', 'price_old': '',
        }
        pools = args['pools']
        pools['rest_amazon_items'] = pools['amazon_items'] = [ amazon_item for _ in range(1001) ]
        pools['next_url'] = 'initial_next_url'

        now = datetime.datetime(2001, 1, 1, 1, 2, 3)
        def lower_found(*args, **kwargs):
            watch = args[3]
            if watch.feed_item < 5:
                watch.feed_item += 1
                return
            if watch.new_feed_item_candidate < 3:
                watch.new_feed_item_candidate += 1
                return
            return

        ride_search_config = {
            'SKIP_JUDGE_ITEM': 256,           # URLの打ち切りのために調べるアイテム数
            'SKIP_JUDGE_LOWER_ITEM': 9,       # URLの打ち切り判定時にこのアイテム数よりも小さい場合は打ち切る
        }

        with patch('yahoo.views.datetime') as mdt, \
                patch('yahoo.views._ride_search_config', return_value=ride_search_config), \
                patch('yahoo.views.amazon_offer_research_for_item', side_effect=lower_found):
            mdt.now = MagicMock(return_value=now)
            yahoo.views.amazon_offer_research_task(args['params'], 'url', user, pools)

        target = mqueue().enqueue
        self.assertEquals(target.call_count, 1)
        (nameless, actuals) = target.call_args
        self.assertEquals(pools['item_search_count'], 256)
        self.assertEquals(pools['item_search_found'], 8)
        self.assertEquals(nameless[0], yahoo.views.amazon_offer_research_finalize)
        self.assertEquals(mlogger.info.call_count, 1)
        self.assertEquals(mlogger.info.call_args[0][0], 
            'URL: %s - %s件検索しましたが、見つかったアイテムが%s個 (< %s)のため打ち切ります。')
        self.assertEquals(mlogger.info.call_args[0][1], 'current_url')
        self.assertEquals(mlogger.info.call_args[0][2], 256)
        self.assertEquals(mlogger.info.call_args[0][3], 8)
        self.assertEquals(mlogger.info.call_args[0][4], 9)


    def test_url_search_found_and_next_search(self, mqueue, mlogger, mwait):
        ''' 検索の結果が芳しい場合、URL検索を継続できるか否か '''
        args = self._entry_for_maintask(mqueue)
        user = User.objects.get(username='hoge')
        watch = OfferReserchWatcher.objects.get(research_type=0, author=user)
        watch.current_url = 'current_url'
        watch.save()

        amazon_item = {
            'asin': 'A123456789', 'prime': 'False', 
            'image': 'mockimage.jpg', 'title': 'mock',
            'price': '1000', 'price_new': '', 'price_old': '',
        }
        pools = args['pools']
        pools['rest_amazon_items'] = pools['amazon_items'] = [ amazon_item for _ in range(1001) ]
        pools['next_url'] = 'initial_next_url'

        now = datetime.datetime(2001, 1, 1, 1, 2, 3)
        def found(*args, **kwargs):
            watch = args[3]
            if watch.feed_item < 8:
                watch.feed_item += 1
                return
            if watch.new_feed_item_candidate < 2:
                watch.new_feed_item_candidate += 1
                return
            return

        ride_search_config = {
            'SKIP_JUDGE_ITEM': 256,           # URLの打ち切りのために調べるアイテム数
            'SKIP_JUDGE_LOWER_ITEM': 10,       # URLの打ち切り判定時にこのアイテム数よりも小さい場合は打ち切る
        }

        with patch('yahoo.views.datetime') as mdt, \
                patch('yahoo.views._ride_search_config', return_value=ride_search_config), \
                patch('yahoo.views.AmazonScraper.get_products', return_value=['mock!']), \
                patch('yahoo.views.AmazonScraper.get_next_page_url', return_value='mock_next_url'), \
                patch('yahoo.views.amazon_offer_research_for_item', side_effect=found):
            mdt.now = MagicMock(return_value=now)
            yahoo.views.amazon_offer_research_task(args['params'], 'url', user, pools)

        target = mqueue().enqueue
        self.assertEquals(target.call_count, 1)
        (nameless, actuals) = target.call_args
        
        self.assertEquals(nameless[0], yahoo.views.amazon_offer_research_task)
        self.assertEquals(actuals['pools']['item_search_count'], 1001)
        self.assertEquals(actuals['pools']['item_search_found'], 10)
        self.assertEquals(actuals['pools']['rest_amazon_items'], ['mock!'])
        self.assertEquals(actuals['pools']['next_url'], 'mock_next_url')

    def test_url_search_for_prev_version(self, mqueue, mlogger, mwait):
        ''' 検索の結果が芳しくない場合でも古いバージョンの場合は打ち切らない '''
        args = self._entry_for_maintask(mqueue)
        user = User.objects.get(username='hoge')
        watch = OfferReserchWatcher.objects.get(research_type=0, author=user)
        watch.current_url = 'current_url'
        watch.save()

        amazon_item = {
            'asin': 'A123456789', 'prime': 'False', 
            'image': 'mockimage.jpg', 'title': 'mock',
            'price': '1000', 'price_new': '', 'price_old': '',
        }
        pools = args['pools']
        pools['rest_amazon_items'] = pools['amazon_items'] = [ amazon_item for _ in range(1001) ]
        pools['next_url'] = 'initial_next_url'
        pools.pop('item_search_count')
        pools.pop('item_search_found')

        now = datetime.datetime(2001, 1, 1, 1, 2, 3)
        def not_found(*args, **kwargs):
            return

        ride_search_config = {
            'SKIP_JUDGE_ITEM': 256,            # URLの打ち切りのために調べるアイテム数
            'SKIP_JUDGE_LOWER_ITEM': 10,       # URLの打ち切り判定時にこのアイテム数よりも小さい場合は打ち切る
        }

        with patch('yahoo.views.datetime') as mdt, \
                patch('yahoo.views._ride_search_config', return_value=ride_search_config), \
                patch('yahoo.views.AmazonScraper.get_products', return_value=['mock!']), \
                patch('yahoo.views.AmazonScraper.get_next_page_url', return_value='mock_next_url'), \
                patch('yahoo.views.amazon_offer_research_for_item', side_effect=not_found):
            mdt.now = MagicMock(return_value=now)
            yahoo.views.amazon_offer_research_task(args['params'], 'url', user, pools)

        target = mqueue().enqueue
        self.assertEquals(target.call_count, 1)
        (nameless, actuals) = target.call_args
        
        # item_search_found が生成されないので、スキップしない
        self.assertEquals(nameless[0], yahoo.views.amazon_offer_research_task)
        self.assertEquals(actuals['pools']['item_search_count'], 1001)
        self.assertFalse('item_search_found' in actuals['pools'])
        self.assertEquals(actuals['pools']['rest_amazon_items'], ['mock!'])
        self.assertEquals(actuals['pools']['next_url'], 'mock_next_url')

