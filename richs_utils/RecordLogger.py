#!/usr/bin/python 
# -*- coding: utf-8 -*-

'''
本番環境での記録をするためのLoggerロジックを提供します。
'''

import logging

from django.utils import timezone

class Context:
    ''' 特定 Context をログ出力に付与したい場合の簡易 Wrapper です '''
    def __init__(self, context, namespace=None):
        self.context = context
        self.namespace = namespace if namespace is not None else __name__
        self.logger = logging.getLogger(self.namespace)
        self.debug('Initialized %s', timezone.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

    def _fmt(self, msg):
        return msg if self.context is None else '[{}] {}'.format(self.context, msg)

    def debug(self, msg, *args):
        self.logger.debug(self._fmt(msg), *args)

    def info(self, msg, *args):
        self.logger.info(self._fmt(msg), *args)

    def warn(self, msg, *args):
        self.logger.warn(self._fmt(msg), *args)

    def error(self, msg, *args):
        self.logger.error(self._fmt(msg), *args)

    def exception(self, ex):
        self.logger.error(self._fmt('raised'))
        self.logger.exception(ex)


