#!/usr/bin/python 
# -*- coding: utf-8 -*-

import time
import requests
import logging
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.conf import settings as django_settings
from django.utils import timezone

from accounts.models import OfferReserchWatcher
from yahoo.models import YahooImportCSVResult
from mercari.models import MercariImportCSVResult

logger = logging.getLogger(__name__)

# コマンドを実行
class Command(BaseCommand):
    help = "バックグラウンドジョブ情報が正常に稼働していない場合の検知・修正を行います。"
    
    # 引数
    def add_arguments(self, parser):
        pass

    def _background_jobs_config(self):
        try:
            return django_settings.BACKGROUND_JOBS_CONFIG
        except:
            return {}
 
    def shutdown(self, conf, now):
        # 時間が経過しすぎているものは強制終了対象
        shutdown_expires = now - timedelta(minutes=conf.get('SHUTDOWN_JOB_NEEDED', 30))
        shutdowns = OfferReserchWatcher.objects.filter(
            status__in=[0, 9], updated_date__lte=shutdown_expires)
        logger.info('Background Jobs Shutdown (before %s): %s',
                    shutdown_expires, shutdowns.count())
        for watch in shutdowns:
            logger.info('Shutdown %s %s job forcely (status: %s -> 1, updated: %s, end_date: %s -> %s)', 
                watch.author.username, watch._get_research_type(), watch.status, watch.updated_date, watch.end_date, now)
            watch.status = 1
            watch.end_date = now
            watch.save()

        yahoo_csv_shutdowns = YahooImportCSVResult.objects.filter(
            status__in=[1, 2, 3, 4], updated_date__lte=shutdown_expires)
        for result in yahoo_csv_shutdowns:
            logger.info('Shutdown YahooImportCSV job forcely (status: %s -> 0, updated: %s, end_date: -> %s)',
                result.status, result.updated_date, now)
            result.status = 0
            result.end_date = now
            result.result_message = '\n'.join([
                '[予期せぬシステムエラーによって中断されました。 もう一度アップロードしてください]', 
                result.result_message or '',
            ])
            result.save()

        mercari_csv_shutdowns = MercariImportCSVResult.objects.filter(
            status__in=[1, 2, 3, 4], updated_date__lte=shutdown_expires)
        for result in mercari_csv_shutdowns:
            logger.info('Shutdown MercariImportCSV job forcely (status: %s -> 0, updated: %s, end_date: -> %s)',
                result.status, result.updated_date, now)
            result.status = 0
            result.end_date = now
            result.result_message = '\n'.join([
                '[予期せぬシステムエラーによって中断されました。 もう一度アップロードしてください]', 
                result.result_message or '',
            ])
            result.save()

        return shutdowns.count() + yahoo_csv_shutdowns.count() + mercari_csv_shutdowns.count()

    def restart(self, conf, now):
        # サービス再起動が必要か否かを返す
        restart_expires = now - timedelta(minutes=conf.get('RESTART_JOB_NEEDED', 15))
        restarts = OfferReserchWatcher.objects.filter(
            status__in=[0, 9], updated_date__lte=restart_expires)
        for watch in restarts:
            source = 'yahoo' if watch.research_type == 0 else 'mercari'
            logger.info('freeze candidate %s %s job found (status: %s, updated: %s, end_date: %s)', 
                watch.author.username, watch._get_research_type(), watch.status, watch.updated_date, watch.end_date)

        yahoo_csv_restarts = YahooImportCSVResult.objects.filter(
            status__in=[1, 2, 3, 4], updated_date__lte=restart_expires)
        for result in yahoo_csv_restarts:
            logger.info('freeze candidate YahooImportCSV job found (status: %s, updated: %s)',
                result.status, result.updated_date)

        mercari_csv_restarts = MercariImportCSVResult.objects.filter(
            status__in=[1, 2, 3, 4], updated_date__lte=restart_expires)
        for result in mercari_csv_restarts:
            logger.info('freeze candidate MercariImportCSV job found (status: %s, updated: %s)',
                result.status, result.updated_date)

        return any([
            restarts.count() > 0,
            yahoo_csv_restarts.count() > 0,
            mercari_csv_restarts.count() > 0,
        ])

    # ハンドラ
    def handle(self, *args, **options):
        logger.info('Background Jobs Check Start')
        conf = self._background_jobs_config()
        now = timezone.datetime.now()
        self.shutdown(conf, now)
        if self.restart(conf, now):
            logger.info('restart required')
            print('restart required')
        logger.info('Background Jobs Check End')
