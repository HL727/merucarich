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
from rq.registry import StartedJobRegistry, FailedJobRegistry

from django.conf import settings
from django.core.management.base import BaseCommand

import asynchelpers

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    
    help = 'Requeue failed and WIP jobs'

    def add_arguments(self, parser):
        ''' define command-line arguments '''
        parser.add_argument('--queue-name', required=False, 
            type=str, default=settings.ASYNC_WORKER['QUEUE_NAME'])


    def _requeue(self, registry):
        (succ, failed) = (0, 0)
        job_ids = registry.get_job_ids()
        for job_id in job_ids:
            try:
                registry.requeue(job_id)
                succ += 1
            except Exception:
                failed += 1      
        return (succ, failed)


    def handle(self, *args, **options):
        ''' entry point '''
        with rq.Connection(asynchelpers.get_queue_redis()) as conn:
            worker = rq.Worker([options['queue_name']])
            wip = StartedJobRegistry(name=options['queue_name'], 
                connection=conn, job_class=worker.job_class)
            job_ids = wip.cleanup('+inf')
            print('WIP jobs into FAILED: {}'.format(len(job_ids)))

            failed = FailedJobRegistry(name=options['queue_name'],
                connection=conn, job_class=worker.job_class)
            (succ, fail) = self._requeue(failed)
            print('requeue FAILED jobs: {} (succ={}, fail={})'.format(succ+fail, succ, fail))
 
