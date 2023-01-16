#!/usr/bin/python 
# -*- coding: utf-8 -*-

import logging
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from yahoo.models import YahooToAmazonItem
from mercari.models import MercariToAmazonItem

logger = logging.getLogger(__name__)

# コマンドを実行
class Command(BaseCommand):
    help = "在庫が0で更新が行われていないアイテムを削除します。"
    
    # 引数
    def add_arguments(self, parser):
        parser.add_argument('--expired-days', required=False, 
            help='delete target item updated date', default=7, type=int)

    def delete_items(self, dt):
        items = YahooToAmazonItem.objects.filter(
                record_type=20, current_purchase_quantity=0,
                update_quantity_request=False, updated_date__lte=dt) 
        logger.info('delete target yahoo items: %s', len(items))
        items.delete()
        items = MercariToAmazonItem.objects.filter(
                record_type=20, current_purchase_quantity=0,
                update_quantity_request=False, updated_date__lte=dt) 
        logger.info('delete target mercari items: %s', len(items))
        items.delete()
 
    # ハンドラ
    def handle(self, *args, **options):
        logger.info('start: delete expired item batch')
        days = max(options.get('expired_days', 7), 7)
        dt = timezone.datetime.now() - timedelta(days=days)
        logger.info('delete before %s, expired days: %s (minimum days is 7)', dt, days)
        self.delete_items(dt)
        logger.info('completed: delete expired item batch')
