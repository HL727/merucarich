#!/usr/bin/python 
# -*- coding: utf-8 -*-

'''
Amazon Feed の更新を行うバッチのメインプログラムです。
'''

import os
import psutil
import logging

from time import sleep
from concurrent.futures import ThreadPoolExecutor

from django.utils import timezone
from accounts.models import User
from yahoo.models import YahooToAmazonItem
from mercari.models import MercariToAmazonItem
from django.db.models import Q
from django.db import connections

from richs_utils import RichsUtils
from richs_mws import MWSUtils

logger = logging.getLogger(__name__)


def _exponential_backoff(func, else_value=None, waits=[1, 2]):
    trial = len(waits) + 1
    for idx in range(trial):
        try:
            return func()
        except:
            if idx < len(waits):
                sleep(waits[idx])
    return else_value


def _get_user(user):
    try:
        # バッチ実行中にユーザー情報の変更があった場合に
        # 処理が巻き戻ってしまうので、最新の情報を取得
        return User.objects.get(uuid=user.uuid)
    except:
        return None


def _lock_user_for_yahoo(user):
    ''' Feed更新用にユーザー情報のロックを行う '''
    if user is None:
        # 削除済み
        return False

    pid = os.getpid()
    if user.update_yahoo_to_amazon_feed_pid is None:
        # 別プロセスが立っていない場合
        user.update_yahoo_to_amazon_feed_pid = pid
        user.update_yahoo_to_amazon_feed_start_date = timezone.datetime.now()
        user.save()
        return True

    if pid == user.update_yahoo_to_amazon_feed_pid:
        # 同一プロセス内で再度ロックを要求した場合は時刻のみ更新
        user.update_yahoo_to_amazon_feed_start_date = timezone.datetime.now()
        user.save()
        return True

    if not psutil.pid_exists(user.update_yahoo_to_amazon_feed_pid):
        # プロセスIDが記録されているが、該当プロセスが終了済の場合
        user.update_yahoo_to_amazon_feed_pid = pid
        user.update_yahoo_to_amazon_feed_start_date = timezone.datetime.now()
        user.save()
        return True

    delta = timezone.datetime.now() - user.update_yahoo_to_amazon_feed_start_date
    diff = int(delta.total_seconds())
    if diff <= 30 * 60:
        logger.debug('Yahoo Update Feed for user:%s another process (%s) has been alive', user, pid)
        return False

    logger.warn('Too long Yahoo process for user:%s was alive (pid=%s) so invoke new process',
        user, user.update_yahoo_to_amazon_feed_pid)
    return True


def _unlock_user_for_yahoo(user):
    ''' ユーザー情報のアンロックを行う '''
    if user is None:
        # 削除済み
        return False

    pid = os.getpid()
    old_pid = user.update_yahoo_to_amazon_feed_pid

    if pid == old_pid:
        # 起動処理が正常に終わった場合
        user.update_yahoo_to_amazon_feed_pid = None
        user.update_yahoo_to_amazon_feed_start_date = None
        user.save()
        return True

    # その他の場合は、プロセス起動時側の更新で
    # 同一プロセス上で lock -> unlock となるパターンを待つ
    return True


def _lock_user_for_mercari(user):
    ''' Feed更新用にユーザー情報のロックを行う '''
    if user is None:
        # 削除済み
        return False
        
    pid = os.getpid()

    if user.update_mercari_to_amazon_feed_pid is None:
        # 別プロセスが立っていない場合
        user.update_mercari_to_amazon_feed_pid = pid
        user.update_mercari_to_amazon_feed_start_date = timezone.datetime.now()
        user.save()
        return True

    if pid == user.update_mercari_to_amazon_feed_pid:
        # 同一プロセス内で再度ロックを要求した場合は時刻のみ更新
        user.update_mercari_to_amazon_feed_start_date = timezone.datetime.now()
        user.save()
        return True

    if not psutil.pid_exists(user.update_mercari_to_amazon_feed_pid):
        # プロセスIDが記録されているが、該当プロセスが終了済の場合
        user.update_mercari_to_amazon_feed_pid = pid
        user.update_mercari_to_amazon_feed_start_date = timezone.datetime.now()
        user.save()
        return True

    delta = timezone.datetime.now() - user.update_mercari_to_amazon_feed_start_date
    diff = int(delta.total_seconds())
    if diff <= 30 * 60:
        logger.debug('Yahoo Update Feed for user:%s another process (%s) has been alive', user, pid)
        return False

    logger.warn('Too long Yahoo process for user:%s was alive (pid=%s) so invoke new process',
        user, user.update_mercari_to_amazon_feed_pid)
    return True


def _unlock_user_for_mercari(user):
    ''' ユーザー情報のアンロックを行う '''
    if user is None:
        # 削除済み
        return False

    pid = os.getpid()
    old_pid = user.update_mercari_to_amazon_feed_pid

    if pid == old_pid:
        # 起動処理が正常に終わった場合
        user.update_mercari_to_amazon_feed_pid = None
        user.update_mercari_to_amazon_feed_start_date = None
        user.save()
        return True

    # その他の場合は、プロセス起動時側の更新で
    # 同一プロセス上で lock -> unlock となるパターンを待つ
    return True


def _get_mws_client(conf):
    return MWSUtils(conf.account_id, conf.access_key, conf.secret_key,
        conf.auth_token, conf.region, conf.marketplace_id)


def _get_valid_skus(mws_client, skus_candidates):
    ''' 有効なSKUSの集合を取得する '''
    valid_skus = []
    for chunk_skus in RichsUtils.chunkof(skus_candidates, 20):
        # 最大20アイテム, 1秒に10アイテム回復
        # 失敗時のリトライは3回。 リトライの結果取得できなかったものは有効とはみなさない
        result = _exponential_backoff(
            lambda: mws_client.get_my_price_for_sku(chunk_skus), 
            else_value={}, waits=[2, 2])
        for (key, value) in result.items():
            if (value['status'] == 'Success'):
                valid_skus.append(key)
        # 1秒に10アイテム回復なのでレートを元に戻す
        sleep(2)

    return set(valid_skus)
 

def _withdraw_candidates_for_yahoo(user):
    ''' ヤフオク出品のアイテム取り下げを行う候補を取得 '''
    return YahooToAmazonItem.objects.filter(
        Q(author=user) & Q(csv_flag=1) & Q(current_purchase_quantity=0) & (
            Q(update_fulfillment_latency_request=True) | Q(update_quantity_request=True) 
        )).order_by('updated_date').only(
            'item_sku', 'current_purchase_quantity', 'current_purchase_fulfillment_latency')


def _restore_candidates_for_yahoo(user):
    ''' ヤフオク出品のアイテム復活を行う候補を取得 '''
    return YahooToAmazonItem.objects.filter(
        Q(author=user) & Q(csv_flag=1) & Q(current_purchase_quantity__gte=1) & ( 
            Q(update_fulfillment_latency_request=True) | Q(update_quantity_request=True)
        )).order_by('updated_date').only(
            'item_sku', 'current_purchase_quantity', 'current_purchase_fulfillment_latency')


def _item_update_for_yahoo(user, updated_skus):
    ''' ヤフオク出品アイテムの更新を行う '''
    # IN句要素が多くなりすぎるとパフォーマンス劣化を招き、
    # Oracleでは1000を超えるとエラーになるので、その中間を1クエリの更新の値として用いる
    for chunk_skus in RichsUtils.chunkof(updated_skus, 500):
        YahooToAmazonItem.objects.filter(
            author=user, csv_flag=1, item_sku__in=chunk_skus).update(
            update_fulfillment_latency_request=False, update_quantity_request=False)


def _withdraw_candidates_for_mercari(user):
    ''' メルカリ出品のアイテム取り下げを行う候補を取得 '''
    return MercariToAmazonItem.objects.filter(
        Q(author=user) & Q(csv_flag=1) & Q(current_purchase_quantity=0) & (
            Q(update_fulfillment_latency_request=True) | Q(update_quantity_request=True)
        )).order_by('updated_date').only(
            'item_sku', 'current_purchase_quantity', 'current_purchase_fulfillment_latency')


def _restore_candidates_for_mercari(user):
    ''' メルカリ出品のアイテム復活を行う候補を取得 '''
    return MercariToAmazonItem.objects.filter(
        Q(author=user) & Q(csv_flag=1) & Q(current_purchase_quantity__gte=1) & ( 
            Q(update_fulfillment_latency_request=True) | Q(update_quantity_request=True)
        )).order_by('updated_date').only(
            'item_sku', 'current_purchase_quantity', 'current_purchase_fulfillment_latency')


def _item_update_for_mercari(user, updated_skus):
    ''' メルカリ出品アイテムの更新を行う '''
    # IN句要素が多くなりすぎるとパフォーマンス劣化を招き、
    # Oracleでは1000を超えるとエラーになるので、その中間を1クエリの更新の値として用いる
    for chunk_skus in RichsUtils.chunkof(updated_skus, 500):
        MercariToAmazonItem.objects.filter(
            author=user, csv_flag=1, item_sku__in=chunk_skus).update(
            update_fulfillment_latency_request=False, update_quantity_request=False)


def _feed_update(label, user, conf, f_candidate, f_update, max_item_count=None):
    ''' Amazonアイテムの更新を行う共通ロジック
    f_candidate: 更新対象アイテムを取得する関数 (userを引数に取り、item modelを返す)
    f_update: 更新を通知する関数 (user, 更新済SKUのリストを引数に取る)
    '''
    candidate_items = f_candidate(user)
    if len(candidate_items) <= 0:
        logger.debug('[%s] user %s has no items', label, user)
        return True
    
    if max_item_count is not None:
        candidate_items = candidate_items[:max_item_count]

    logger.debug('[%s] user %s item count = %s', label, user, len(candidate_items))
    mws_client = _get_mws_client(conf)
    skus_candidates = [ item.item_sku for item in candidate_items ]
    valid_skus = _get_valid_skus(mws_client, skus_candidates)

    update_target_items = [ item for item in candidate_items if item.item_sku in valid_skus ]

    # 商品情報の更新
    (success, feed_id) = (False, None)
    try:
        logger.info('[%s] start to update quantity and fulfillment - user: %s, item: %s',
            label, user, len(update_target_items))
        (success, feed_id) = mws_client.update_quantity_and_fulfillment_latency(update_target_items)
    except Exception as err:
        logger.exception(err)

    if not success:
        logger.info('[%s] user: %s feed update was cancelled because fail to call update API', label, user)
        return False

    # 処理に失敗したアイテム一覧を取得
    (success, error_skus) = (False, [])
    try:
        logger.info('[%s] start to get update results - user: %s, feed_id: %s', label, user, feed_id)
        (success, error_skus) = mws_client.get_feed_submission_result(feed_id)

    except Exception as err:
        logger.exception(err)

    if not success:
        logger.info('[%s] user: %s feed update was cancelled because fail to get error SKUs', label, user)
        return False

    # DBにデータを反映する
    error_skus = set(error_skus)
    update_skus = [ item.item_sku for item in update_target_items if item.item_sku not in error_skus ]
    update_count = len(update_skus)
    f_update(user, update_skus)
    
    logger.info('[%s] user %s feed update completed (count=%s)', label, user, update_count)
    return True


def _feed_update_for_yahoo(label, user, conf, f_picker, f_updater, max_item_count=None):
    ''' ヤフオクアイテムのフィード更新を行う '''
    started = timezone.datetime.now()
    try:
        logger.info('feed update %s for user:%s started', label, user)
        user = _get_user(user)
        if not _lock_user_for_yahoo(user):
            logger.info('feed update %s for user:%s cancelled due to fail to get lock', label, user)
            return
        _feed_update(label, user, conf, f_picker, f_updater, max_item_count)

    except Exception as err:
        logger.error('[%s, user=%s, Yahoo] 予期せぬエラーが発生したため、処理を中断しました', label, user)
        logger.exception(err)

    finally:
        user = _get_user(user)
        _unlock_user_for_yahoo(user)
        sleep(1)
        connections.close_all()
        logger.info('feed update %s for user:%s finished (%s sec)',
            label, user, (timezone.datetime.now() - started).total_seconds())


def _feed_update_withdraw_for_yahoo(user, conf, max_item_count=None):
    ''' ヤフオクアイテムの取り下げ反映を行う '''
    _feed_update_for_yahoo('yahoo withdraw', user, conf, 
            _withdraw_candidates_for_yahoo, _item_update_for_yahoo, max_item_count)


def _feed_update_restore_for_yahoo(user, conf, max_item_count=None):
    ''' ヤフオクアイテムの在庫復活反映を行う '''
    _feed_update_for_yahoo('yahoo restore', user, conf, 
            _restore_candidates_for_yahoo, _item_update_for_yahoo, max_item_count)


def _feed_update_for_mercari(label, user, conf, f_picker, f_updater, max_item_count=None):
    ''' メルカリアイテムのフィード更新を行う '''
    started = timezone.datetime.now()
    try:
        logger.info('feed update %s for user:%s started', label, user)
        user = _get_user(user)
        if not _lock_user_for_mercari(user):
            logger.info('feed update %s for user:%s cancelled due to fail to get lock', label, user)
            return
        _feed_update(label, user, conf, f_picker, f_updater, max_item_count)

    except Exception as err:
        logger.error('[user=%s, Mercari] 予期せぬエラーが発生したため、処理を中断しました', user)
        logger.exception(err)

    finally:
        user = _get_user(user)
        _unlock_user_for_mercari(user)
        sleep(1)
        connections.close_all()
        logger.info('feed update %s for user:%s finished (%s sec)',
            label, user, (timezone.datetime.now() - started).total_seconds())


def _feed_update_withdraw_for_mercari(user, conf, max_item_count=None):
    ''' ヤフオクアイテムの取り下げ反映を行う '''
    _feed_update_for_mercari('mercari withdraw', user, conf, 
            _withdraw_candidates_for_mercari, _item_update_for_mercari, max_item_count)


def _feed_update_restore_for_mercari(user, conf, max_item_count=None):
    ''' ヤフオクアイテムの在庫復活反映を行う '''
    _feed_update_for_mercari('mercari restore', user, conf, 
            _restore_candidates_for_mercari, _item_update_for_mercari, max_item_count)


def _can_run_for_user(user, run_usernames):
    if run_usernames is None:
        return True
    return user.username in run_usernames


def _get_update_settings():
    update_settings = []
    users = User.objects.filter(is_staff=False, is_active=True)
    for user in users:
        conf = RichsUtils.get_mws_api(user)
        if conf is None:
            logger.info('skip user %s because no mws found', user)
            continue
        update_settings.append(dict(user=user, conf=conf))
    return update_settings
    

def do_update_feed_for_yahoo(max_workers=4, run_usernames=None, max_item_count=None): 
    ''' Yahooアイテム更新処理のエントリーポイント '''
    pid = os.getpid()
    logger.info('update feed for yahoo start (pid=%s)', pid)
    update_settings = _get_update_settings()
    exec_count = 0
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 全ユーザーの取り下げを優先的に行う
        for setting in update_settings:
            if not _can_run_for_user(setting['user'], run_usernames):
                continue
            executor.submit(_feed_update_withdraw_for_yahoo, 
                setting['user'], setting['conf'], max_item_count)
            exec_count += 1

        # 取り下げが全て終わった後に更新処理
        for setting in update_settings:
            if not _can_run_for_user(setting['user'], run_usernames):
                continue
            executor.submit(_feed_update_restore_for_yahoo, 
                setting['user'], setting['conf'], max_item_count)
            exec_count += 1

    logger.info('update feed for yahoo completed (pid=%s, count=%s)', pid, exec_count)


def do_update_feed_for_mercari(max_workers=4, run_usernames=None, max_item_count=None): 
    ''' Mercariアイテム更新処理のエントリーポイント '''
    pid = os.getpid()
    logger.info('update feed for mercari start: pid=%s', pid)
    update_settings = _get_update_settings()
    exec_count = 0
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 全ユーザーの取り下げを優先的に行う
        for setting in update_settings:
            if not _can_run_for_user(setting['user'], run_usernames):
                continue
            executor.submit(_feed_update_withdraw_for_mercari, 
                setting['user'], setting['conf'], max_item_count)
            exec_count += 1

        # 取り下げが全て終わった後に更新処理
        for setting in update_settings:
            if not _can_run_for_user(setting['user'], run_usernames):
                continue
            executor.submit(_feed_update_restore_for_mercari, 
                setting['user'], setting['conf'], max_item_count)
            exec_count += 1

    logger.info('update feed for mercari completed (pid=%s, count=%s)', pid, exec_count)


