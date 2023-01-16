#!/usr/bin/python 
# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
from unittest.mock import mock_open, patch, MagicMock
from django.forms.models import model_to_dict

from django.test import TestCase
from django.utils import timezone

from accounts.models import User
from yahoo.models import YahooToAmazonItem
from mercari.models import MercariToAmazonItem

from accounts.management.commands.delete_old_items import Command


class DeleteOldItemBatchTests(TestCase):


    def _create_items(self, now):
        user = User.objects.create(username='testuser')
        with patch('django.utils.timezone.datetime') as mtz:
            udt1 = now - timedelta(days=7)
            mtz.now = MagicMock(return_value=udt1)
            # 消える
            YahooToAmazonItem.objects.create(
                author=user, item_sku='SKU0001Y', record_type=20, 
                current_purchase_quantity=0, update_quantity_request=False) 
            MercariToAmazonItem.objects.create(
                author=user, item_sku='SKU0001M', record_type=20, 
                current_purchase_quantity=0, update_quantity_request=False) 
            # 消えない
            YahooToAmazonItem.objects.create(
                author=user, item_sku='SKU0002Y', record_type=21, 
                current_purchase_quantity=0, update_quantity_request=False) 
            YahooToAmazonItem.objects.create(
                author=user, item_sku='SKU0003Y', record_type=20, 
                current_purchase_quantity=1, update_quantity_request=False) 
            YahooToAmazonItem.objects.create(
                author=user, item_sku='SKU0004Y', record_type=20, 
                current_purchase_quantity=0, update_quantity_request=True) 
            MercariToAmazonItem.objects.create(
                author=user, item_sku='SKU0002M', record_type=21, 
                current_purchase_quantity=0, update_quantity_request=False) 
            MercariToAmazonItem.objects.create(
                author=user, item_sku='SKU0003M', record_type=20, 
                current_purchase_quantity=1, update_quantity_request=False) 
            MercariToAmazonItem.objects.create(
                author=user, item_sku='SKU0004M', record_type=20, 
                current_purchase_quantity=0, update_quantity_request=True) 
            udt2 = now - timedelta(days=6, hours=23, minutes=59, seconds=59)
            mtz.now = MagicMock(return_value=udt2)
            YahooToAmazonItem.objects.create(
                author=user, item_sku='SKU0005Y', record_type=20, 
                current_purchase_quantity=0, update_quantity_request=False) 
            MercariToAmazonItem.objects.create(
                author=user, item_sku='SKU0005M', record_type=20, 
                current_purchase_quantity=0, update_quantity_request=False) 

    def test_c0_test(self):
        ''' C0 カバレッジ '''
        now = datetime(2020, 1, 23, 12, 0, 0)
        self._create_items(now)
        cmd = Command()
        cmd.handle(dict(expired_days=7))

    def test_delete_test(self):
        ''' アイテムの削除チェック '''
        now = datetime(2020, 1, 23, 12, 0, 0)
        self._create_items(now)
        cmd = Command()
        cmd.delete_items(now - timedelta(days=7))
        self.assertIsNone(YahooToAmazonItem.objects.filter(item_sku='SKU0001Y').first())
        self.assertIsNotNone(YahooToAmazonItem.objects.filter(item_sku='SKU0002Y').first())
        self.assertIsNotNone(YahooToAmazonItem.objects.filter(item_sku='SKU0003Y').first())
        self.assertIsNotNone(YahooToAmazonItem.objects.filter(item_sku='SKU0004Y').first())
        self.assertIsNotNone(YahooToAmazonItem.objects.filter(item_sku='SKU0005Y').first())
        self.assertIsNone(MercariToAmazonItem.objects.filter(item_sku='SKU0001M').first())
        self.assertIsNotNone(MercariToAmazonItem.objects.filter(item_sku='SKU0002M').first())
        self.assertIsNotNone(MercariToAmazonItem.objects.filter(item_sku='SKU0003M').first())
        self.assertIsNotNone(MercariToAmazonItem.objects.filter(item_sku='SKU0004M').first())
        self.assertIsNotNone(MercariToAmazonItem.objects.filter(item_sku='SKU0005M').first())
