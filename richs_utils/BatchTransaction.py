#!/usr/bin/python 
# -*- coding: utf-8 -*-

'''
Batch実行のトランザクション制御を行うモジュールです。
'''

import uuid
import logging

from time import sleep
from datetime import timedelta
from accounts.models import BatchExecution

from django.utils import timezone

logger = logging.getLogger(__name__)

class BatchTransaction:

    def __init__(self, batch_type, dual_boot=False):
        self.batch_type = batch_type
        self.dual_boot = dual_boot
        self.batch_id = self.init(batch_type, dual_boot)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()


    def init(self, batch_type, dual_boot):
        ''' トランザクションを開始する '''
        if dual_boot:
            # dual boot モードの場合は制御を実施しない
            return 'dual boot mode'
    
        while True:
            records = BatchExecution.objects.filter(batch_type=batch_type)
            if len(records) <= 0:
                # 起動可能
                break
    
            old_date = timezone.datetime.now() - timedelta(minutes=5)
            for record in records:
                if record.status == 0:
                    # 新しい情報には破棄希望通達
                    record.status = 9
                    record.save()
                elif record.status != 0 and record.updated_date <= old_date:
                    # 古い情報は削除
                    record.delete()
            sleep(3)
    
        # 起動
        batch_id = str(uuid.uuid4())
        BatchExecution.objects.create(batch_id=batch_id, batch_type=batch_type, status=0)
        return batch_id
    
    
    def runnable(self):
        ''' バッチ実行中にトランザクションの状況を更新する '''
        if self.dual_boot:
            # dual boot モードの場合は制御を実施しない
            return True
    
        records = BatchExecution.objects.filter(batch_id=self.batch_id)
        if len(records) <= 0:
            # 何らかの理由で削除されてしまった場合は終了
            return False
    
        cancel = False
        for record in records:
            if record.status == 0:
                # update timestamp
                record.save()
            else:
                # delete and close batch execution 
                record.delete()
                cancel = True
        return not cancel
    
    
    def close(self):
        ''' トランザクションを閉じる '''
        if self.dual_boot:
            return
        BatchExecution.objects.filter(batch_id=self.batch_id).delete()



