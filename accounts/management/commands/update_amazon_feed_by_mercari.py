#!/usr/bin/python 
# -*- coding: utf-8 -*-

from django.core.management.base import BaseCommand
from richs_utils import UpdateAmazonFeed

# コマンドを実行
class Command(BaseCommand):
    help = "Mercari在庫チェックの結果をAmazon Feedに反映します。"
    
    # 引数
    def add_arguments(self, parser):
        # 有効なSKUの判定レート: 1秒 = 10アイテム
        # バッチ実行間隔: 10分 = 600秒 = 6000アイテム
        parser.add_argument('--max-workers', required=False, 
            help='parallel thread number', default=4, type=int)
        parser.add_argument('--usernames', required=False, nargs='+',
            help='search specific users only if set', default=None, type=str)
        parser.add_argument('--max-item-count', required=False, 
            help='update maximum item count at once', default=None, type=int)

    # ハンドラ
    def handle(self, *args, **options):
        UpdateAmazonFeed.do_update_feed_for_mercari(
            max_workers=options['max_workers'], 
            run_usernames=options['usernames'], 
            max_item_count=options['max_item_count'])
            

