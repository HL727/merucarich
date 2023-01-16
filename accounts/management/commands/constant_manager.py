#!/usr/bin/python 
# -*- coding: utf-8 -*-

from django.core.management.base import BaseCommand

from accounts.models import OverrideConstantValue

# コマンドを実行
class Command(BaseCommand):
    help = "システム定数テーブルの操作を行います"
    
    # 引数
    def add_arguments(self, parser):
        parser.add_argument('key_value', nargs='+', type=str)
        parser.add_argument('--operation', required=False,
            choices=['get', 'set'], default='get')
        parser.add_argument('--get-default', required=False, default='')
        parser.add_argument('--description', required=False)

    # ハンドラ
    def handle(self, *args, **options):
        ts = options['key_value']
        if len(ts) <= 0:
            return
        if options['operation'] == 'get':
            key = ts[0]
            obj = OverrideConstantValue.objects.filter(key=key).first()
            if obj is None:
                print(options['get_default'])
            else:
                print(obj.value)
        elif options['operation'] == 'set':
            if len(ts) != 2:
                print('ERR: you must set [key] and [value]')
                return
            (key, value) = (ts[0], ts[1])
            (obj, _) = OverrideConstantValue.objects.get_or_create(key=key)
            obj.value = value
            if options['description']:
                obj.description = options['description']
            obj.save()
            print(f'{obj.key} was updated as {obj.value}')
