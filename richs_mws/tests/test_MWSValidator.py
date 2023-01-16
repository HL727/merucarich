#!/usr/bin/python 
# -*- coding: utf-8 -*-

import datetime

from unittest.mock import mock_open, patch, MagicMock

from django.test import TestCase

from scraper import AmazonScraper
from richs_mws import MWSValidator

class MWSValidatorTests(TestCase):
    ''' MWSValidatorのテスト '''

    def test_get_asin(self):
        ''' get_asin の C0 テスト '''
        self.assertIsNone(MWSValidator.get_asin(''))
        with patch('scraper.AmazonScraper.get_products', return_value=[]):
            self.assertIsNone(MWSValidator.get_asin(''))
        with patch('scraper.AmazonScraper.get_products', return_value=[{'asin': 'ABCDEFG'}]):
            self.assertEquals('ABCDEFG', MWSValidator.get_asin(''))

    @patch('time.sleep')
    def test_token_validation(self, msleep):
        ''' Validation の C0 テスト '''
        self.assertEquals(
            (False, '有効な値が入力されていません。'),
            MWSValidator.validate_tokens(None, None, ''))

        self.assertEquals(
            (False, 'Amazonの検索URLからアイテムを取得できませんでした。'),
            MWSValidator.validate_tokens('xxx', 'yyy', None))

        # ASIN取得 + MWS例外
        self.assertEquals(
            (False, 'Amazon MWS APIの呼び出しに失敗しました。 トークン内容が正しくありません。'),
            MWSValidator.validate_tokens('xxx', 'yyy', 'ABCDEFG'))

        # ASIN取得 + MWSレスポンス異常
        with patch('mws.Products.get_lowest_offer_listings_for_asin') as mresponse:
            mresponse().parsed = {'status': {'value': 'Failed'}}
            self.assertEquals(
                (False, 'Amazon MWS APIの呼び出しに失敗しました。 トークン内容が正しくありません。'),
                MWSValidator.validate_tokens('xxx', 'yyy', 'ABCDEFG'))

        # ASIN取得 + MWSレスポンス正常
        with patch('mws.Products.get_lowest_offer_listings_for_asin') as mresponse:
            mresponse().parsed = {'status': {'value': 'Success'}}
            self.assertEquals(
                (True, 'Amazon MWS APIの呼び出しに成功しました。 トークン内容が正しいことを確認しました。'),
                MWSValidator.validate_tokens('xxx', 'yyy', 'ABCDEFG'))
