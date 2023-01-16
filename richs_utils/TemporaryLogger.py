#!/usr/bin/python 
# -*- coding: utf-8 -*-

'''
本番環境で一時的にのみファイル出力したい処理を実現します。
そのためのネームスペースを提供します。
'''

import logging

logger = logging.getLogger(__name__)

def get():
    ''' Debug用 Logger を取得します '''
    return logger


class Context:
    ''' 特定 Context をログ出力に付与したい場合の簡易 Wrapper です '''
    def __init__(self, context):
        self.context = context

    def _fmt(self, msg):
        return msg if self.context is None else '[{}] {}'.format(self.context, msg)

    def debug(self, msg, *args):
        logger.debug(self._fmt(msg), *args)

    def info(self, msg, *args):
        logger.info(self._fmt(msg), *args)

    def warn(self, msg, *args):
        logger.warn(self._fmt(msg), *args)

    def error(self, msg, *args):
        logger.error(self._fmt(msg), *args)

    def exception(self, ex):
        logger.exception(ex)


