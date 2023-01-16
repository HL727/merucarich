#!/usr/bin/python 
# -*- coding: utf-8 -*-

from django.conf import settings

import mws
from richs_utils import Functional, AmazonSearchUtils
from scraper import AmazonScraper


def validate_tokens(account_id, auth_token, asin):
    ''' トークンバリデーションを実施して、メッセージを返します '''
    if None in [account_id, auth_token]:
        return (False, '有効な値が入力されていません。')
    if asin is None:
        return (False, 'Amazonの検索URLからアイテムを取得できませんでした。')

    # Amazon MWS にアクセス
    access_key = settings.RICHS_AWS_ACCESS_KEY
    secret_key = settings.RICHS_AWS_SECRET_KEY
    region = settings.RICHS_AWS_REGION
    marketplace_id = settings.RICHS_AWS_MARKETPLACE_ID
 
    try:
        client = mws.Products(
            access_key=access_key, secret_key=secret_key, 
            account_id=account_id, auth_token=auth_token, region=region)

        def call_api():
            return client.get_lowest_offer_listings_for_asin(
                marketplaceid=marketplace_id, asins=[asin], condition='New')

        response = Functional.exponential_backoff(call_api, raise_error=True, sleeps=[1, 2])

    except Exception as e:
        return (False, 'Amazon MWS APIの呼び出しに失敗しました。 トークン内容が正しくありません。')

    if response.parsed.get('status', {}).get('value') != 'Success':
        return (False, 'Amazon MWS APIの呼び出しに失敗しました。 トークン内容が正しくありません。')
    
    return (True, 'Amazon MWS APIの呼び出しに成功しました。 トークン内容が正しいことを確認しました。')


def get_asin(amazon_url):
    ''' AmazonのURLから有効なASINを何かひとつ取得 '''
    try:
        # API の対象とする ASIN を取得
        items = AmazonScraper().get_products(amazon_url)
        if len(items) <= 0:
            return None
        return items[0]['asin']
    except Exception as e:
        return None
