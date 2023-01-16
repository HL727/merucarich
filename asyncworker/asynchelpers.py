#!/usr/bin/python 
# -*- coding: utf-8 -*-

'''
Utility Functions for AsyncWorkers. 
'''
import time

import rq
import redis

from django.conf import settings


def _b2s(bs, default_value='', encoding='utf-8'):
    try:
        return bs.decode(encoding)
    except:
        return default_value


def get_queue_redis():
    ''' create redis.StrictRedis instance from settings configuration. '''
    rconf = settings.ASYNC_WORKER['REDIS']
    return redis.StrictRedis(host=rconf['HOST'], port=rconf['PORT'], db=rconf['DB_FOR_QUEUE'])


def get_data_redis():
    ''' create redis.StrictRedis instance from settings configuration. '''
    rconf = settings.ASYNC_WORKER['REDIS']
    return redis.StrictRedis(host=rconf['HOST'], port=rconf['PORT'], db=rconf['DB_FOR_DATA'])


def get_queue(queuename=None):
    conn = get_queue_redis()
    timeout = settings.ASYNC_WORKER.get('JOB_DEFAULT_TIMEOUT', 3600)
    queuename = queuename or settings.ASYNC_WORKER['QUEUE_NAME']
    return rq.Queue(queuename, connection=conn, default_timeout=timeout)


def get_import_queue():
    ''' インポートに使うキューを取得します '''
    queuename = settings.ASYNC_WORKER.get('IMPORT_QUEUE_NAME')
    return get_queue(queuename)


def get_workers():
    ''' get current worker information '''
    def to_dict(w):
        return dict(
            name=w.name, hostname=_b2s(w.hostname), 
            pid=w.pid, last_heartbeat=w.last_heartbeat)
    queue = get_queue()
    return [to_dict(w) for w in rq.Worker.all(queue=queue)]


def reached_maximum_sequence(sequence_number):
    if settings.ASYNC_WORKER['MAXIMUM_SEQUENCE'] <= 0:
        return False
    return sequence_number >= settings.ASYNC_WORKER['MAXIMUM_SEQUENCE'] 


def wait(seconds=None):
    ''' to be clear to wait '''
    s = seconds if seconds is not None else settings.ASYNC_WORKER['WAIT_DEFAULT_SECONDS']
    time.sleep(s)


def rkey(*args):
    ''' return redis key with asyncworker prefix '''
    return 'merucarich:asyncworker:{}'.format(':'.join(args))

    
