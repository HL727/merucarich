#!/usr/bin/python 
# -*- coding: utf-8 -*-

import random
from unittest.mock import patch, MagicMock

from django.http import QueryDict

from accounts.models import User, OfferReserchWatcher
from settings_amazon.models import AmazonAPI

import yahoo.views
import mercari.views

# テストに利用する検索用URLの候補
url_candidates = [
    'https://www.amazon.co.jp/s?k=Haskell&__mk_ja_JP=%E3%82%AB%E3%82%BF%E3%82%AB%E3%83%8A&ref=nb_sb_noss_2',
    'https://www.amazon.co.jp/s?k=Scala&__mk_ja_JP=%E3%82%AB%E3%82%BF%E3%82%AB%E3%83%8A&ref=nb_sb_noss_2,',
    'https://www.amazon.co.jp/s?k=C%E8%A8%80%E8%AA%9E&__mk_ja_JP=%E3%82%AB%E3%82%BF%E3%82%AB%E3%83%8A&ref=nb_sb_noss_2',
    'https://www.amazon.co.jp/s?k=Web2.0&__mk_ja_JP=%E3%82%AB%E3%82%BF%E3%82%AB%E3%83%8A&ref=nb_sb_noss',
    # マウス
    'https://www.amazon.co.jp/s?k=%E3%83%9E%E3%82%A6%E3%82%B9&__mk_ja_JP=%E3%82%AB%E3%82%BF%E3%82%AB%E3%83%8A&ref=nb_sb_noss_1',
    # スマホケース iPhone8
    'https://www.amazon.co.jp/s?k=%E3%82%B9%E3%83%9E%E3%83%9B%E3%82%B1%E3%83%BC%E3%82%B9+iPhone8&__mk_ja_JP=%E3%82%AB%E3%82%BF%E3%82%AB%E3%83%8A&ref=nb_sb_noss_2',
    # ワンピース
    'https://www.amazon.co.jp/s?k=%E3%83%AF%E3%83%B3%E3%83%94%E3%83%BC%E3%82%B9&__mk_ja_JP=%E3%82%AB%E3%82%BF%E3%82%AB%E3%83%8A&ref=nb_sb_noss_20',
]

def _url():
    return url_candidates[random.randrange(0, len(url_candidates))]


def setup():
    ''' 負荷試験に必要なデータを作成 '''
    for index in range(80):
        username = 'loadtest{:02}'.format(index + 1)
        if User.objects.filter(username=username).count() > 0:
            print('user {} skipped: already exists'.format(username))
            continue
        user = User.objects.create_user(username=username, 
            password='1qaz2wsx3edc', max_items=20000, check_times=2)
        AmazonAPI.objects.create(
            author=user, account_id='xxx', auth_token='yyy')
        print('created user={}, password=1qaz2wsx3edc'.format(username))


def start_yahoo(user):
    ''' Yahoo 負荷検証開始 '''
    if isinstance(user, str):
        user = User.objects.get(username=user)

    if OfferReserchWatcher.objects.filter(research_type=0, author=user).count() > 0:
        print('Yahoo task by {} was started already.'.format(user.username))
        return

    # ダミー引数の作成
    req =  MagicMock()
    req.POST = QueryDict('&'.join([
        'amazon_search_type=0',
        'keyword=' + _url(),
        'similarity=0.8',
        'rateing=80.0',
        'search_type=0'
        'select=23'
        'is_exist_bidorbuy_price=0',
        'istatus=1'
        'abatch=0'
        'is_export_csv=1'
    ]))
    req.user = user

    # リクエスト時の内部処理をコール
    yahoo.views.amazon_offer_research_post(req)
    print('start Yahoo AmazonOfferResearch by {}'.format(user.username))


def stop_yahoo(user):
    ''' Yahoo 処理キャンセル '''
    if isinstance(user, str):
        user = User.objects.get(username=user)

    if OfferReserchWatcher.objects.filter(research_type=0, author=user).count() <= 0:
        print('Yahoo task by {} is not started.'.format(user.username))
        return
    req =  MagicMock()
    req.POST = QueryDict('close=close')
    req.user = user
    yahoo.views.amazon_offer_research_post(req)
    print('stop Yahoo AmazonOfferResearch by {}'.format(user.username))

 
def start_mercari(user):
    ''' Mercari 負荷検証開始 '''
    if isinstance(user, str):
        user = User.objects.get(username=user)

    if OfferReserchWatcher.objects.filter(research_type=1, author=user).count() > 0:
        print('Mercari task by {} was started already.'.format(user.username))
        return

    # ダミー引数の作成
    req =  MagicMock()
    req.POST = QueryDict('&'.join([
        'amazon_search_type=0',
        'keyword=' + _url(),
        'similarity=0.8',
        'rateing=80.0',
        'condition_id_1=on',
        'shipping_payer_id_2=on',
        'status_id_on_sale=on',
        'sort_order=standard',
        'is_export_csv=1'
    ]))
    req.user = user

    # リクエスト時の内部処理をコール
    mercari.views.amazon_offer_research_post(req)
    print('start Mercari AmazonOfferResearch by {}'.format(user.username))


def stop_mercari(user):
    ''' Mercari 処理キャンセル '''
    if isinstance(user, str):
        user = User.objects.get(username=user)

    if OfferReserchWatcher.objects.filter(research_type=1, author=user).count() <= 0:
        print('Mercari task by {} is not started.'.format(user.username))
        return
    req =  MagicMock()
    req.POST = QueryDict('close=close')
    req.user = user
    mercari.views.amazon_offer_research_post(req)
    print('stop Mercari AmazonOfferResearch by {}'.format(user.username))


def close():
    ''' 不要なデータを全削除 '''
    for index in range(80):
        username = 'loadtest{:02}'.format(index + 1)
        try:
            user = User.objects.get(username=username)
        except:
            continue
        AmazonAPI.objects.filter(author=user).delete()
        user.delete()
        print('deleted user={}'.format(username))

