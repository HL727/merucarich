#!/usr/bin/python 
# -*- coding: utf-8 -*-

# resolve top level import by using absolute path
import sys
import pathlib

current_dir = pathlib.Path(__file__).resolve().parent
project_root = current_dir.joinpath('..').joinpath('..').resolve()
sys.path.append(str(project_root)) 

import os
import logging
import datetime
import rq
import rq.scheduler

from django.conf import settings
from django.core.management.base import BaseCommand

import asynchelpers

logger = logging.getLogger(__name__)
scheduler_logger = logging.getLogger('rq.scheduler')

def info(*argv, **kwargs):
    scheduler_logger.info(*argv, **kwargs)

def debug(*argv, **kwargs):
    scheduler_logger.debug(*argv, **kwargs)

class Command(BaseCommand):
    
    help = 'Run Asyncworker process'

    def add_arguments(self, parser):
        ''' define command-line arguments '''
        parser.add_argument('--queue-name', required=False, 
            type=str, default=settings.ASYNC_WORKER['QUEUE_NAME'])

    def override_scheduler_logger(self):
        ''' scheduler の log 実装がまずいので、ここで上書きする '''
        try:
            rq.scheduler.logging.info = info
            rq.scheduler.logging.debug = debug
            print('override logger was successful')
        except:
            print('override logger was failed')

    def handle(self, *args, **options):
        ''' entry point '''
        self.override_scheduler_logger()
        with rq.Connection(asynchelpers.get_queue_redis()):
            worker = rq.Worker([options['queue_name']])
            worker.work()

