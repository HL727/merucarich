#!/usr/bin/python 
# -*- coding: utf-8 -*-

import time
import datetime
import requests
import logging

from django.core.management.base import BaseCommand
from django.conf import settings as django_settings
from django.utils import timezone

from accounts.models import FJCMember

logger = logging.getLogger(__name__)

# コマンドを実行
class Command(BaseCommand):
    help = "他サーバーで動いているFJCメンバー情報を更新します"
    
    # 引数
    def add_arguments(self, parser):
        pass

    # ハンドラ
    def handle(self, *args, **options):
        try:
            config = django_settings.FJC_MEMBER_CONFIG 
        except:
            config = {}
        for url in config.get('URLS', []):
            try:
                r = requests.post(url, data={'token': config.get('TOKEN', '')})
                for member in r.json().get('fjc_members', []):
                    print('append: {}.{} from {}'.format(member['username'], member['account'], url))
                    FJCMember.objects.update_or_create(
                        account_id=member['account'], username=member['username'], url=url)
                time.sleep(1)
            except Exception as e:
                logger.exception(e)

        dt = timezone.datetime.now() - datetime.timedelta(days=config.get('EXPIRE_DAYS', 3))
        FJCMember.objects.filter(updated_date__lte=dt).delete()
        print('completed')

 

