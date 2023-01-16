#!/usr/bin/python 
# -*- coding: utf-8 -*-

import datetime

from unittest.mock import mock_open, patch, MagicMock

from django.test import TestCase

from richs_utils import Functional

class FunctionalTests(TestCase):
    ''' 新規追加/修正したメソッドのテスト '''

    def test_exponential_backoff(self):
        ''' Exponential Backoff のテスト '''
        with patch('time.sleep') as msleep:
            (a, b) = (0, 0)
            # 正常時
            self.assertEquals(1, Functional.exponential_backoff(lambda: 1, else_value=0))
            self.assertEquals(0, Functional.exponential_backoff(lambda: a/b, else_value=0))
            try:
                # 例外を投げる場合
                self.assertEquals(0, Functional.exponential_backoff(lambda: a/b, raise_error=True, else_value=0))
                self.fail()
            except:
                pass

        # timeの呼び出し回数
        with patch('time.sleep') as msleep:
            m = MagicMock(side_effect=[ValueError(), ValueError(), 1])
            self.assertEquals(1, Functional.exponential_backoff(lambda: m()))
            self.assertEquals(2, msleep.call_count)
            msleep.assert_any_call(0.5)
            msleep.assert_any_call(1)

        # timeの呼び出し回数
        with patch('time.sleep') as msleep:
            m = MagicMock(side_effect=ValueError())
            self.assertEquals(9, Functional.exponential_backoff(lambda: m(), else_value=9, sleeps=[2, 4, 6, 8, 16]))
            self.assertEquals(6, msleep.call_count)
            msleep.assert_any_call(2)
            msleep.assert_any_call(4)
            msleep.assert_any_call(6)
            msleep.assert_any_call(8)
            msleep.assert_any_call(16)
            msleep.assert_any_call(0)



