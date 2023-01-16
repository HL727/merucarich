#!/usr/bin/python 
# -*- coding: utf-8 -*-

import datetime

from unittest.mock import mock_open, patch, MagicMock
from django.forms.models import model_to_dict

from django.test import TestCase
from django.utils import timezone

from accounts.models import User, BannedKeyword

from richs_utils import RichsUtils

class RichsUtilsTests(TestCase):
    ''' 新規追加/修正したメソッドのテスト '''

    def test_chunkof(self):
        self.assertEquals([], RichsUtils.chunkof([], 3))
        self.assertEquals([[1]], RichsUtils.chunkof([1], 3))
        self.assertEquals([[1, 2]], RichsUtils.chunkof([1, 2], 3))
        self.assertEquals([[1, 2, 3]], RichsUtils.chunkof([1, 2, 3], 3))
        self.assertEquals([[1, 2, 3], [4]], RichsUtils.chunkof([1, 2, 3, 4], 3))


    def test_to_amazon_csv_column(self):
        self.assertEquals('', RichsUtils.to_amazon_csv_column(''))
        self.assertEquals('1234', RichsUtils.to_amazon_csv_column(1234))
        self.assertEquals('新品・未使用。', 
            RichsUtils.to_amazon_csv_column('新品・未使用。'))
        self.assertEquals('新品・未使用。 送料無料です。', 
            RichsUtils.to_amazon_csv_column('新品・未使用。\n送料無料です。'))
        self.assertEquals('新品・未使用。 送料無料です。', 
            RichsUtils.to_amazon_csv_column('新品・未使用。\r\n送料無料です。'))
        self.assertEquals('新品・未使用。<br>送料無料です。', 
            RichsUtils.to_amazon_csv_column('新品・未使用。\r\n送料無料です。', br='<br>'))
        self.assertEquals('新品・未使用。 送料無料です。', 
            RichsUtils.to_amazon_csv_column('新品・未使用。\t送料無料です。'))


    def test_judge_banned_item(self):
        BannedKeyword.objects.create(banned_keyword='Banned')
        BannedKeyword.objects.create(banned_keyword='転売')
        self.assertFalse(RichsUtils.judge_banned_item('')[0])
        self.assertFalse(RichsUtils.judge_banned_item('Successful Title')[0])
        self.assertTrue(RichsUtils.judge_banned_item('Banned Title')[0])
        self.assertTrue(RichsUtils.judge_banned_item('Title Banned')[0])
        self.assertTrue(RichsUtils.judge_banned_item('Title Banned Title')[0])
        self.assertFalse(RichsUtils.judge_banned_item('ワンピース 限定フィギュア【送料無料】')[0])
        self.assertFalse(RichsUtils.judge_banned_item('OnePeace 限定フィギュア【送料無料】')[0])
        self.assertTrue(RichsUtils.judge_banned_item('OnePeace 限定フィギュア【転売禁止】')[0])

        bans = RichsUtils.get_banned_list()

        self.assertFalse(RichsUtils.judge_banned_item('', bans)[0])
        self.assertFalse(RichsUtils.judge_banned_item('Successful Title', bans)[0])
        self.assertTrue(RichsUtils.judge_banned_item('Banned Title', bans)[0])
        self.assertTrue(RichsUtils.judge_banned_item('Title Banned', bans)[0])
        self.assertTrue(RichsUtils.judge_banned_item('Title Banned Title', bans)[0])
        self.assertFalse(RichsUtils.judge_banned_item('ワンピース 限定フィギュア【送料無料】', bans)[0])
        self.assertFalse(RichsUtils.judge_banned_item('OnePeace 限定フィギュア【送料無料】', bans)[0])
        self.assertTrue(RichsUtils.judge_banned_item('OnePeace 限定フィギュア【転売禁止】', bans)[0])

        bans = [ RichsUtils.normalize(s) for s in ['Banned', '転売', 'OnePeace'] ]
        self.assertFalse(RichsUtils.judge_banned_item('', bans)[0])
        self.assertFalse(RichsUtils.judge_banned_item('Successful Title', bans)[0])
        self.assertTrue(RichsUtils.judge_banned_item('Banned Title', bans)[0])
        self.assertTrue(RichsUtils.judge_banned_item('Title Banned', bans)[0])
        self.assertTrue(RichsUtils.judge_banned_item('Title Banned Title', bans)[0])
        self.assertFalse(RichsUtils.judge_banned_item('ワンピース 限定フィギュア【送料無料】', bans)[0])
        self.assertTrue(RichsUtils.judge_banned_item('OnePeace 限定フィギュア【送料無料】', bans)[0])
        self.assertEquals((True, '転売'), RichsUtils.judge_banned_item('OnePeace 限定フィギュア【転売禁止】', bans))


    def test_banned_keyword(self):
        ''' 大小文字混合禁止ワード判定チェック '''
        # Trimされるので "it banned2" が比較用文字列
        BannedKeyword.objects.create(banned_keyword=' It Banned2 ')
        BannedKeyword.objects.create(banned_keyword='ＳＵＮ')
        
        # 英数字＋スペースは全て半角小文字に変換して比較する
        self.assertTrue(RichsUtils.judge_banned_item('**It Banned2**')[0])
        self.assertTrue(RichsUtils.judge_banned_item('it banned2')[0])
        self.assertTrue(RichsUtils.judge_banned_item('IT BANNED2')[0])
        self.assertTrue(RichsUtils.judge_banned_item('ＩＴ　ＢＡＮＮＥＤ２')[0])
        self.assertTrue(RichsUtils.judge_banned_item('ｉｔ ｂａｎｎｅｄ２')[0])
        
        # 登録側が全角でもOK
        self.assertTrue(RichsUtils.judge_banned_item('pokemon sun and moon')[0])

        # キーワードが直接含まれていない場合は対象外
        self.assertFalse(RichsUtils.judge_banned_item('It not banned2')[0])


    def test_offer_research_ip_address(self):
        ''' バックグラウンドサーチ用のIP取得ロジック '''
        with patch('richs_utils.RichsUtils.settings.RIDE_SEARCH_EXTRA_IP_ADDRESSES', None):
            # 宣言なしの場合
            self.assertEquals('', RichsUtils.offer_research_ip_address())

        with patch('richs_utils.RichsUtils.settings.RIDE_SEARCH_EXTRA_IP_ADDRESSES', ['AAA.BBB.CCC.DDD']):
            # 設定した場合は数値によってその値が取得できる
            with patch('richs_utils.RichsUtils.random.randint', return_value=0):
                self.assertEquals('', RichsUtils.offer_research_ip_address())
            with patch('richs_utils.RichsUtils.random.randint', return_value=1):
                self.assertEquals('AAA.BBB.CCC.DDD', RichsUtils.offer_research_ip_address())

        ipaddrs = ['A', 'B', 'C']
        results = {}
        with patch('richs_utils.RichsUtils.settings.RIDE_SEARCH_EXTRA_IP_ADDRESSES', ipaddrs):
            for _ in range(10000):
                key = RichsUtils.offer_research_ip_address()
                if key not in results:
                    results[key] = 1
                else:
                    results[key] += 1
            # ランダムがちゃんと1度以上選択されているかをチェック
            self.assertTrue(results[''] > 0)
            self.assertTrue(results['A'] > 0)
            self.assertTrue(results['B'] > 0)
            self.assertTrue(results['C'] > 0)

