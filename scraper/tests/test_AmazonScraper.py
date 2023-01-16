#!/usr/bin/python 
# -*- coding: utf-8 -*-

from time import sleep
from datetime import timedelta

from unittest.mock import mock_open, patch, MagicMock
from django.forms.models import model_to_dict

from django.test import TestCase
from django.utils import timezone

import scraper
from scraper import AmazonScraper

def item(asin):
    return dict(asin=asin)


@patch('builtins.print')
class AmazonScraperTests(TestCase):
    ''' AmazonScraper の動作検証 '''

    def test_get_products(self, mprint):
        s = scraper.AmazonScraper('')
        res = s.get_products('https://www.amazon.co.jp/s?k=%E3%83%89%E3%83%A9%E3%82%B4%E3%83%B3%E3%83%9C%E3%83%BC%E3%83%AB+%E3%83%95%E3%82%A3%E3%82%AE%E3%83%A5%E3%82%A2&__mk_ja_JP=%E3%82%AB%E3%82%BF%E3%82%AB%E3%83%8A&ref=nb_sb_noss_1')


    def test_update_price(self, mprint):
        s = scraper.AmazonScraper('')
        s.auth_token = 'dummy'
        s._update_price_by_mws_response = MagicMock()

        with patch('mws.Products') as m:
            s.product_dict_list = []
            s._update_price()
            self.assertEquals(m().get_lowest_offer_listings_for_asin.call_count, 0)

        with patch('mws.Products') as m:
            s.product_dict_list = [ item('ITEM{:04d}'.format(idx)) for idx in range(20) ]
            s._update_price()
            self.assertEquals(m().get_lowest_offer_listings_for_asin.call_count, 2)

        with patch('mws.Products') as m:
            s.product_dict_list = [ item('ITEM{:04d}'.format(idx)) for idx in range(21) ]
            s._update_price()
            self.assertEquals(m().get_lowest_offer_listings_for_asin.call_count, 4)

        with patch('mws.Products') as m:
            s.product_dict_list = [ item('ITEM{:04d}'.format(idx)) for idx in range(40) ]
            s._update_price()
            self.assertEquals(m().get_lowest_offer_listings_for_asin.call_count, 4)


    def test_when_503(self, mprint):
        ''' 503 が返ってきた場合の動作チェック '''
        m1 = MagicMock()
        m1.text = 'ERR'
        m1.status_code = 503
        with patch('time.sleep'), \
                patch('scraper.AmazonScraper._get', return_value=m1):
            s = scraper.AmazonScraper()
            # 通常呼び出しの場合は 503 でも単に [] が返る
            res = s.get_products('https://example.com/?s=ABC', raise_when_5xx=False)
            self.assertEquals(res, [])
            try:
                # raise_when_5xx が True なら同様の条件で例外_
                res = s.get_products('https://example.com/?s=ABC', raise_when_5xx=True)
                self.fail()
            except ValueError as err:
                pass


    def test_get_products_when_captcha_responsed(self, mprint):
        ''' CAPTCHA が返ってきた場合の挙動のチェック '''
        m1 = MagicMock()
        m1.text = 'Amazon CAPTCHA'
        m2 = MagicMock()
        m2.text = 'OK'
      
        with patch('time.sleep'), \
                patch('scraper.AmazonScraper._get', side_effect=[m1, m2]), \
                patch('scraper.AmazonScraper._do_captcha', return_value=m2):
            # CAPTCHA がうまく返ってきた場合の挙動の確認
            s = scraper.AmazonScraper()
            res = s.get_products('https://example.com/?s=ABC')
            self.assertEquals(res, [])

        error_count = 10
        with patch('time.sleep'), \
                patch('scraper.AmazonScraper._get', side_effect=[ m1 for _ in range(error_count) ]), \
                patch('scraper.AmazonScraper._do_captcha', return_value=m2):
            # 最後までCAPTCHA が成功しない場合の挙動の確認(ちゃんと規定回数で終わる)
            s = scraper.AmazonScraper()
            res = s.get_products('https://example.com/?s=ABC')
            self.assertEquals(res, [])
