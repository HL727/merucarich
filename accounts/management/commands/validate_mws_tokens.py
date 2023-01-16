#!/usr/bin/python 
# -*- coding: utf-8 -*-

import logging

from accounts.models import User
from settings_amazon.models import AmazonAPI
from richs_mws import MWSValidator
from richs_utils import AmazonSearchUtils

from django.utils import timezone
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)

# コマンドを実行
class Command(BaseCommand):
    help = "ユーザーが登録している AmazonAPI のトークンが利用可能か否かを検証します。 "
    
    # 引数
    def add_arguments(self, parser):
        parser.add_argument('--keyword', required=False, 
            help='Amazon Search Keyword', default='フィギュア', type=str)
        parser.add_argument('--asin', required=False, 
            help='Target ASIN', default=None, type=str)

    # ハンドラ
    def handle(self, *args, **options):
        execdt = timezone.datetime.now()
        logger.info('Start: AmazonAPI Validation (at %s)', execdt)
        asin = options.get('asin')
        if asin is None:
            keyword = options.get('keyword', 'フィギュア')
            amazon_url = AmazonSearchUtils.keyword_to_url('1', keyword)
            asin = MWSValidator.get_asin(amazon_url)
        logger.info('Test ASIN: %s', asin)
        for user in User.objects.all():
            auth = AmazonAPI.objects.filter(author=user).first()
            if auth is None:
                logger.info('Checked: username=%s, AmazonAPI is not registered', user.username)
                continue
            (success, message) = MWSValidator.validate_tokens(auth.account_id, auth.auth_token, asin)
            logger.info('Checked: username=%s, results=%s, message=%s', user.username, success, message)
            if success:
                auth.validated_date = execdt
                auth.save()
        logger.info('Completed: AmazonAPI Validation')
