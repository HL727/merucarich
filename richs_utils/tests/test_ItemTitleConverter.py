#!/usr/bin/python 
# -*- coding: utf-8 -*-

import os
import datetime 

from unittest.mock import mock_open, patch, MagicMock
from django.forms.models import model_to_dict

from django.test import TestCase
from django.utils import timezone

from richs_utils import ItemTitleConverter
from accounts.models import ItemNameFormat

class ItemTitleConverterTests(TestCase):
    
    def _put(self, strategy, from_text, to_text='', priority=100, valid=True):
        return ItemNameFormat.objects.create(strategy=strategy, 
            from_text=from_text, to_text=to_text,
            priority=priority, valid=valid)

    def _init(self):
        ''' テストデータの投入 '''
        # オークション開始文言
        self._put('regex', '[0-9,]+円(スタート)?', '', 1000)

        # タイトル全体の飾り記号の排除
        symbols = '☆★※＊▲▼◆♡♥❤'
        regex = '^\\s*[' + symbols + ']{1,4}(.*[^' + symbols + '])[' + symbols + ']{1,4}\\s*$'
        self._put('regex', regex, '\\1', 1000)

        # 単純置換
        dictionary = [
            '新品', '未使用品', '未開封', '送料', '無料', '輸送箱', '出品', '代理出品', 
            '稀少品', '稀少', '希少品', '希少', '送料込み', '送料込', 
            '人気', '大幅値下げ', '大幅値下', '値下', 
        ]
        for keyword in dictionary:
            self._put('replace', keyword)

        # 空括弧対応
        for priority in [90, 89]:
            self._put('regex', '『\\s*』', ' ', priority)
            self._put('regex', '\\[\\s*\\]', ' ', priority)
            self._put('regex', '「\\s*」', ' ', priority)
            self._put('regex', '｛\\s*｝', ' ', priority)
            self._put('regex', '【\\s*】', ' ', priority)
            self._put('regex', '＜\\s*＞', ' ', priority)
            self._put('regex', '〈\\s*〉', ' ', priority)
            self._put('regex', '★\\s*★', ' ', priority)
            self._put('regex', '☆\\s*☆', ' ', priority)
 
        # 重複排除
        self._put('regex', '☆+', '☆', 80)
        self._put('regex', '★+', '★', 80)
        self._put('regex', '・+', '・', 80)
        self._put('regex', '\\s+', ' ', 80)
 

    def test_convert(self):
        ''' 単純機能 '''
        self.assertEquals('あいうえお', ItemTitleConverter.convert('あいうえお'))
        self._put('replace', 'うえ')
        rules = ItemNameFormat.get_ordered()
        self.assertEquals('あいお', ItemTitleConverter.convert(' あいうえお ', rules))

    def test_convert_dict(self):
        ''' 実際にあるそれっぽいタイトルが正常置換できるかをチェック '''
        self._init()
        self.assertEquals('アミエ・グラン 1/6 セーラープルート', 
            ItemTitleConverter.convert('稀少品 新品 未開封 アミエ・グラン 1/6 セーラープルート'))
        self.assertEquals('未組み立て プラモデル MPC ALIEN エイリアン', 
            ItemTitleConverter.convert('★☆500円スタート　未開封 未組み立て　希少　プラモデル MPC ALIEN エイリアン☆★'))
        self.assertEquals('METAL BUILD クロスボーン・ガンダムX1 メタルビルド ガンダム バンダイ', 
            ItemTitleConverter.convert('【新品未開封】METAL BUILD クロスボーン・ガンダムX1【送料無料】メタルビルド　ガンダム　バンダイ'))
        self.assertEquals('★ S.H.フィギュアーツ 仮面ライダー ジオウ II・プレバン・真骨彫', 
            ItemTitleConverter.convert('★ 1円 S.H.フィギュアーツ 仮面ライダー ジオウ II・新品・未開封・プレバン・真骨彫'))
        self.assertEquals('フィギュア 一番くじ ドラゴンボール THE GREATEST SAIYAN ラストワン賞 黄金大猿悟空ソフビフィギュア バンダイ', 
            ItemTitleConverter.convert('☆未使用品☆【未開封】フィギュア 一番くじ ドラゴンボール THE GREATEST SAIYAN ラストワン賞 黄金大猿悟空ソフビフィギュア バンダイ'))
        self.assertEquals('ドラゴンクエスト AM はぐれメタルのローラークリーナー', 
            ItemTitleConverter.convert('【〈送料無料〉】ドラゴンクエスト　AM　★★はぐれメタルのローラークリーナー'))

    def _test_output(self):
        self._init()
        def s2r(s):
            if s is None:
                return ''
            return str(s)
        for row in ItemTitleConverter.export_csv_rows():
            print('\t'.join([ s2r(e) for e in row]))


