#!/usr/bin/python 
# -*- coding: utf-8 -*-

'''
関数的な汎用ロジックを定義します。
'''

import time


def exponential_backoff(func, else_value=None, raise_error=False, sleeps=[0.5, 1, 2, 4]):
    ''' 定期的なリトライを行う汎用Wrapperです '''
    last_error = None
    for sleep_seconds in sleeps + [0]:
        try:
            return func()
        except Exception as err:
            last_error = err
            time.sleep(sleep_seconds)
    if raise_error:
        raise last_error
    return else_value


