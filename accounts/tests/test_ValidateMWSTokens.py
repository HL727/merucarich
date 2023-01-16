#!/usr/bin/python 
# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
from unittest.mock import mock_open, patch, MagicMock
from django.forms.models import model_to_dict

from django.test import TestCase
from django.utils import timezone

from accounts.models import User
from settings_amazon.models import AmazonAPI
from richs_mws import MWSValidator

from accounts.management.commands.validate_mws_tokens import Command


class ValidateMWSTokensTests(TestCase):

    def test_updated_case(self):
        ''' バッチで validate_date が更新されるケースの検証 '''
        user = User.objects.create(username='testuser')
        auth = AmazonAPI.objects.create(account_id='XXX', auth_token='YYY', author=user)
        self.assertIsNone(auth.validated_date)
        now = datetime(2000, 1, 1, 1, 23, 45)
        with patch('richs_mws.MWSValidator.validate_tokens', return_value=(True, '')), \
                patch('django.utils.timezone.datetime') as mdt:
            mdt.now.return_value = now
            Command().handle(asin='XXXXXX')
        
        auth = AmazonAPI.objects.get(author=user)
        self.assertEquals(now, auth.validated_date)
