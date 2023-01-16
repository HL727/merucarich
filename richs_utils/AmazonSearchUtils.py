#!/usr/bin/python 
# -*- coding: utf-8 -*-

'''
Amazon検索のための共通関数を提供します。
'''

import urllib.parse
from accounts.models import FJCMember


def keyword_to_url(search_type, keyword):
    ''' 入力から有効な Amazon の検索URLを生成します '''
    if keyword in ['', None]:
        return None
    if search_type == '0':
        return keyword
    else:
        return 'https://www.amazon.co.jp/s?k=' + urllib.parse.quote(keyword, safe='?')


def validate(url):
    ''' URLのバリデーションを行います '''
    if not url:
        return (False, 'URLが入力されていません。')
    if not url.startswith('https://'):
        return (False, 'URLが不正です。')
    if FJCMember.contains(url):
        return (False, 'URLはFJCメンバーのストアURLのため実行不可です。')
    return (True, '')
