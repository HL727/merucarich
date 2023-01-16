#!/usr/bin/python 
# -*- coding: utf-8 -*-

import uuid

from time import sleep
from datetime import timedelta
from accounts.models import BatchExecution
from concurrent.futures import ThreadPoolExecutor

from django.test import TestCase
from django.utils import timezone

from richs_utils.BatchTransaction import BatchTransaction

class BatchTransactionTests(TestCase):
    
    def test_usage(self):
        ''' 使い方 '''
        with BatchTransaction('label') as transaction:
            # DBにバッチ実行状況を書き込む
            record = BatchExecution.objects.get(batch_id=transaction.batch_id)
            self.assertEquals('label', record.batch_type)
            batch_id = record.batch_id

            transaction.runnable()

            # runnable を実行するとDBを更新する
            # 結果が False の場合は Transaction を中断する
            new_record = BatchExecution.objects.get(batch_id=transaction.batch_id)
            self.assertTrue(record.updated_date < new_record.updated_date)

        # with 句を抜けた場合は DB情報は明示的に削除
        self.assertEquals(len(BatchExecution.objects.filter(batch_id=batch_id)), 0)


    def test_dualbooting(self):
        ''' 重複起動した場合の挙動が後勝ちとなる '''
        other = BatchTransaction('labelX') # 別ラベルの Transaction は気にしない

        def tran1():
            with BatchTransaction('label') as tran:
                while True:
                    if not tran.runnable():
                        break
                    sleep(1)

        def tran2():
            # 検証用に別に動き始めるまで待機
            while len(BatchExecution.objects.filter(batch_type='label')) <= 0:
                sleep(1)

            # 起動時にすでに起動している同一種別バッチがある場合、これが終了するまで待機
            with BatchTransaction('label') as tran:
                pass


        with ThreadPoolExecutor(max_workers=2) as executor:
            # バックグラウンドで起動
            executor.submit(tran1)
            executor.submit(tran2)
        
        # tran2 の起動によって tran1 が明示的に終了する
        pass 
            

    def test_transaction_close_by_outside(self):
        ''' 外部要因でバッチ実行状況が削除されると、バッチは終了する '''
        with BatchTransaction('label') as transaction:
            # DBにバッチ実行状況を書き込む
            record = BatchExecution.objects.get(batch_id=transaction.batch_id)
            transaction.runnable()

            # DBから削除された場合、runnable は Falseを返す
            BatchExecution.objects.filter(batch_id=transaction.batch_id).delete()
            self.assertFalse(transaction.runnable())


    def test_dualboot_on(self):
        ''' Dual Boot モードで起動した場合 '''
        with BatchTransaction('label', dual_boot=True) as tran1:
            with BatchTransaction('label', dual_boot=True) as tran2:
                # tran2 は tran1 の終了を待たないため起動できる
                # dual boot mode の場合、常に batch_id は同じ
                self.assertEquals(tran1.batch_id, tran2.batch_id)
           



