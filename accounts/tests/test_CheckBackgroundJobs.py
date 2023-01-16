#!/usr/bin/python 
# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
from unittest.mock import mock_open, patch, MagicMock
from django.forms.models import model_to_dict

from django.test import TestCase
from django.utils import timezone

from accounts.models import User, OfferReserchWatcher
from yahoo.models import YahooImportCSVResult
from mercari.models import MercariImportCSVResult

from accounts.management.commands.check_background_jobs import Command

class CheckBackgroundJobsTests(TestCase):

    def _create_watch(self, user, now, type=0, status=0):
        with patch('django.utils.timezone.datetime') as mtz:
            mtz.now = MagicMock(return_value=now)
            watch = OfferReserchWatcher.objects.create(
                author=user, research_type=type, status=status, total=0,
                exclude_asin=0, exclude_seller=0, prime=0, condition_different=0,
                not_found=0, feed_item=0)
        return watch.id

    def _create_yahoo_import(self, user, now, status=0, result_message=None):
        with patch('django.utils.timezone.datetime') as mtz:
            mtz.now = MagicMock(return_value=now)
            result = YahooImportCSVResult.objects.create(
                author=user, status=status, result_message=result_message)
        return result.id

    def _create_mercari_import(self, user, now, status=0, result_message=None):
        with patch('django.utils.timezone.datetime') as mtz:
            mtz.now = MagicMock(return_value=now)
            result = MercariImportCSVResult.objects.create(
                author=user, status=status, result_message=result_message)
        return result.id

    def test_background_search_c0(self):
        ''' 一括検索に対するC0コードカバレッジテスト '''
        user = User.objects.create(username='testuser')
        now = datetime(2020, 1, 23, 12, 0, 0)
        self._create_watch(user, now)
        conf = dict(RESTART_JOB_NEEDED=10, SHUTDOWN_JOB_NEEDED=20)
        cmd = Command()
        self.assertEqual(0, cmd.shutdown(conf, now))
        self.assertFalse(cmd.restart(conf, now))

        w1 = self._create_watch(user, now - timedelta(minutes=9, seconds=59), type=0, status=9)
        w2 = self._create_watch(user, now - timedelta(minutes=10, seconds=0), type=1, status=0)
        w3 = self._create_watch(user, now - timedelta(minutes=10, seconds=1), type=0, status=1)
        w4 = self._create_watch(user, now - timedelta(minutes=19, seconds=59), type=0, status=0)
        w5 = self._create_watch(user, now - timedelta(minutes=20, seconds=0), type=1, status=9)
        w6 = self._create_watch(user, now - timedelta(minutes=20, seconds=1), type=0, status=2)

        # w1 - w6 で強制停止対象は1つ
        self.assertEqual(1, cmd.shutdown(conf, now))
        # w5以外は入力ママ
        watch = OfferReserchWatcher.objects.get(id=w1)
        self.assertEqual(9, watch.status)
        self.assertIsNone(watch.end_date)
        watch = OfferReserchWatcher.objects.get(id=w2)
        self.assertEqual(0, watch.status)
        self.assertIsNone(watch.end_date)
        watch = OfferReserchWatcher.objects.get(id=w3)
        self.assertEqual(1, watch.status)
        self.assertIsNone(watch.end_date)
        watch = OfferReserchWatcher.objects.get(id=w4)
        self.assertEqual(0, watch.status)
        self.assertIsNone(watch.end_date)
        watch = OfferReserchWatcher.objects.get(id=w6)
        self.assertEqual(2, watch.status)
        self.assertIsNone(watch.end_date)
        # w5は停止状態に更新
        watch = OfferReserchWatcher.objects.get(id=w5)
        self.assertEqual(1, watch.status)
        self.assertEqual(now, watch.end_date)

        self.assertTrue(cmd.restart(conf, now))

    def test_c0test_handle(self):
        ''' handle関数のC0コードカバレッジテスト '''
        user = User.objects.create(username='testuser')
        now = datetime(2020, 1, 23, 12, 0, 0)

        w1 = self._create_watch(user, now - timedelta(minutes=9, seconds=59), type=0, status=9)
        w2 = self._create_watch(user, now - timedelta(minutes=10, seconds=0), type=1, status=0)
        w3 = self._create_watch(user, now - timedelta(minutes=10, seconds=1), type=0, status=1)
        w4 = self._create_watch(user, now - timedelta(minutes=19, seconds=59), type=0, status=0)
        w5 = self._create_watch(user, now - timedelta(minutes=20, seconds=0), type=1, status=9)
        w6 = self._create_watch(user, now - timedelta(minutes=20, seconds=1), type=0, status=2)

        conf = dict(RESTART_JOB_NEEDED=10, SHUTDOWN_JOB_NEEDED=20)
        with patch('accounts.management.commands.check_background_jobs.Command._background_jobs_config', return_value=conf), \
                patch('accounts.management.commands.check_background_jobs.print'), \
                patch('django.utils.timezone.datetime') as mtz:
            mtz.now = MagicMock(return_value=now)
            Command().handle()

        # w5以外は入力ママ
        watch = OfferReserchWatcher.objects.get(id=w1)
        self.assertEqual(9, watch.status)
        self.assertIsNone(watch.end_date)
        watch = OfferReserchWatcher.objects.get(id=w2)
        self.assertEqual(0, watch.status)
        self.assertIsNone(watch.end_date)
        watch = OfferReserchWatcher.objects.get(id=w3)
        self.assertEqual(1, watch.status)
        self.assertIsNone(watch.end_date)
        watch = OfferReserchWatcher.objects.get(id=w4)
        self.assertEqual(0, watch.status)
        self.assertIsNone(watch.end_date)
        watch = OfferReserchWatcher.objects.get(id=w6)
        self.assertEqual(2, watch.status)
        self.assertIsNone(watch.end_date)
        # w5は停止状態に更新
        watch = OfferReserchWatcher.objects.get(id=w5)
        self.assertEqual(1, watch.status)
        self.assertEqual(now, watch.end_date)

    def test_background_import_c0(self):
        ''' インポートに対するC0コードカバレッジテスト '''
        user = User.objects.create(username='testuser')
        now = datetime(2020, 1, 23, 12, 0, 0)
        conf = dict(RESTART_JOB_NEEDED=10, SHUTDOWN_JOB_NEEDED=20)

        # Status 0 と 5 の場合は何も処理しない
        y1 = self._create_yahoo_import(user, now, status=0)
        m1 = self._create_mercari_import(user, now, status=5)

        # restart / shutdown の両方が起動する時刻
        exec_dt = datetime(2020, 1, 23, 12, 30, 0)

        cmd = Command()
        self.assertEquals(0, cmd.shutdown(conf, exec_dt))
        self.assertFalse(cmd.restart(conf, exec_dt))

        # status 1, 2, 3, 4 の場合は起動する
        y2 = self._create_yahoo_import(user, now, status=1)
        m2 = self._create_mercari_import(user, now, status=4, result_message='HOGE')

        self.assertEquals(2, cmd.shutdown(conf, exec_dt))

        # DBデータが強制終了ステータスになっている
        y2item = YahooImportCSVResult.objects.get(id=y2)
        self.assertEquals(0, y2item.status)
        self.assertEquals(exec_dt, y2item.end_date)
        self.assertEquals(y2item.result_message, 
            '[予期せぬシステムエラーによって中断されました。 もう一度アップロードしてください]\n')
        m2item = MercariImportCSVResult.objects.get(id=m2)
        self.assertEquals(0, m2item.status)
        self.assertEquals(exec_dt, m2item.end_date)
        self.assertEquals(m2item.result_message, 
            '[予期せぬシステムエラーによって中断されました。 もう一度アップロードしてください]\nHOGE')

        # restart pattern
        exec_dt = datetime(2020, 1, 23, 12, 15, 0)
        y3 = self._create_yahoo_import(user, now, status=2)
        m3 = self._create_mercari_import(user, now, status=3)

        self.assertEquals(0, cmd.shutdown(conf, exec_dt))
        self.assertTrue(cmd.restart(conf, exec_dt))

        # DBデータのステータスは変わらない
        y3item = YahooImportCSVResult.objects.get(id=y3)
        self.assertEquals(2, y3item.status)
        self.assertIsNone(y3item.end_date)
        m3item = MercariImportCSVResult.objects.get(id=m3)
        self.assertEquals(3, m3item.status)
        self.assertIsNone(m3item.end_date)
