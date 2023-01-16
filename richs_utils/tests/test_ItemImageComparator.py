#!/usr/bin/python 
# -*- coding: utf-8 -*-

import os
import datetime 

import cv2

from unittest.mock import mock_open, patch, MagicMock
from django.forms.models import model_to_dict

from django.test import TestCase
from django.utils import timezone

from accounts.models import User, OfferReserchWatcher, StopRequest
from yahoo.models import YahooToAmazonItem

import richs_utils.ItemImageComparator

class ItemImageComparatorTests(TestCase):

    def abspath(self, name):
        dirname = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(dirname, name)

    def test_similar_fast(self):
        ''' 高速比較のチェック '''
        path1 = self.abspath('a1.jpg')
        (similar, value) = richs_utils.ItemImageComparator.similar_fast(path1, path1)
        self.assertTrue(similar)
        self.assertTrue(abs(1.0 - value) < 0.00001)

        path2 = self.abspath('y1.jpg')
        (similar, value) = richs_utils.ItemImageComparator.similar_fast(path1, path2)
        self.assertTrue(similar)
        
        (similar, _) = richs_utils.ItemImageComparator.similar_fast(path1, path2, value+0.1)
        self.assertFalse(similar)


    def test_similar_debug(self):
        # debugモードで書き出しをする場合のテスト
        # 通常時は利用しないで良い
        return
        path1 = cv2.imread(self.abspath('a1.jpg'))
        path2 = cv2.imread(self.abspath('y1.jpg'))
        output = self.abspath('t1.jpg')
        richs_utils.ItemImageComparator._is_similar_matching(path1, path2, debug=True, debug_output=output)

        path1 = cv2.imread(self.abspath('a2.jpg'))
        path2 = cv2.imread(self.abspath('y2.jpg'))
        output = self.abspath('t2.jpg')
        richs_utils.ItemImageComparator._is_similar_matching(path1, path2, debug=True, debug_output=output)


    def test_similar(self):
        ''' 重い比較のチェック '''
        path1 = self.abspath('a1.jpg')
        path2 = self.abspath('y1.jpg')
        path3 = self.abspath('a2.jpg')
        (similar, details) = richs_utils.ItemImageComparator.similar(path1, path2)
        self.assertTrue(all([similar, details[0][0], details[1][0]]))
        (similar, details) = richs_utils.ItemImageComparator.similar(path1, path3)
        self.assertFalse(similar)

        # 片方のみマッチするケースもある
        path1 = self.abspath('a3.jpg')
        path2 = self.abspath('y3.jpg')
        (similar, details) = richs_utils.ItemImageComparator.similar(path1, path2)
        self.assertFalse(similar)
        self.assertFalse(details[0][0])
        self.assertTrue(details[0][1])


    def test_non_similar(self):
        ''' 類似しないと判断された場合のテスト '''
        path1 = self.abspath('a1.jpg')
        path2 = self.abspath('y1.jpg')
        
        with patch('cv2.BFMatcher') as matcher:
            matcher().knnMatch.return_value = []
            (_, details) = richs_utils.ItemImageComparator.similar(path1, path2, dual_check=False)
            self.assertEqual(details[0][1]['message'], '画像の類似特徴点が一定数以下')

            dummy = MagicMock()
            dummy.distance = 10000
            matcher().knnMatch.return_value = [ [dummy] for _ in range(100) ]
            (_, details) = richs_utils.ItemImageComparator.similar(path1, path2, dual_check=False)
            self.assertEqual(details[0][1]['message'], '画像の類似特徴点の性質が悪い')
            

        with patch('cv2.perspectiveTransform') as mtrans:
            mtrans.return_value = [
                [(0, 0)], [(10, 10)], [(20, 20)], [(30, 30)]
            ]
            (_, details) = richs_utils.ItemImageComparator.similar(path1, path2, dual_check=False)
            self.assertEqual(details[0][1]['message'], '対応領域が歪な四角形')

        with patch('richs_utils.ItemImageComparator._dst_hash', return_value=9999):
            (_, details) = richs_utils.ItemImageComparator.similar(path1, path2, dual_check=False)
            self.assertEqual(details[0][1]['message'], '対応領域の面積が２つの画像で大きく異なる')


