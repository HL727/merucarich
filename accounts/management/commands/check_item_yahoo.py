#!/usr/bin/python 
# -*- coding: utf-8 -*-

from django.core.management.base import BaseCommand
from richs_utils import InventoryYahoo

# コマンドを実行
class Command(BaseCommand):
    help = "Yahoo 在庫チェック(在庫取り下げ)を実施します。"
    
    # 引数
    def add_arguments(self, parser):
        parser.add_argument('check_times', nargs='+', type=int)
        parser.add_argument('--max-workers', required=False, 
            help='parallel thread number', default=4, type=int)
        parser.add_argument('--beginwith', required=False, 
            help='start item count (for operator)', default=0, type=int)
        parser.add_argument('--group-lower', required=False, 
            help='minimum group item count for each worker', default=100, type=int)
        parser.add_argument('--usernames', required=False, nargs='+',
            help='search specific users only if set', default=None, type=str)
        parser.add_argument('--skus', required=False, nargs='+',
            help='execute skus only if set', default=None, type=str)
        parser.add_argument('--without-update', required=False, action='store_true',
            help='set if you do not want update after checking (just check only)')

    # ハンドラ
    def handle(self, *args, **options):
        InventoryYahoo.do_inventory_check_v2(
            check_times=options['check_times'],
            beginwith=options['beginwith'], 
            max_workers=options['max_workers'],
            group_lower_size=options['group_lower'],
            run_usernames=options['usernames'],
            run_skus=options['skus'],
            update_required=not options['without_update'])

