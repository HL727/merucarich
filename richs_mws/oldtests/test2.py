# -*- coding: utf-8 -*-

import mws
import time
from jinja2 import Environment, FileSystemLoader

# Amazon US MWS ID
account_id = 'A3UHE9VQJJHJ98' #顧客情報
access_key = 'AKIAJEEEHMBTMBASK2FQ'
secret_key = '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'
auth_token = 'amzn.mws.e6b3de8d-cc3f-25fa-9813-aef1aaa98259' #顧客情報
region = 'JP'
env = Environment(loader=FileSystemLoader('/var/www/richs/richs_mws/templates', encoding='utf8') ,trim_blocks=True,lstrip_blocks=True)
template = env.get_template('feed_update.xml')


feed_type='_POST_INVENTORY_AVAILABILITY_DATA_'
class Message(object):
    def __init__(self, sku, quantity, fulfillment_latency):
        self.sku = sku
        self.quantity = quantity
        self.fulfillment_latency = fulfillment_latency

# 30,000
feed_messages = [
    Message('m21104783438', 0, 14),
]

namespace = dict(MerchantId=account_id, FeedMessages=feed_messages)
feed_xml = template.render(namespace)
feed_content = feed_xml.encode()

# API
feeds_api = mws.Feeds(access_key=access_key,secret_key=secret_key,account_id=account_id,region=region,auth_token=auth_token)

# 変更要求
feed_info = feeds_api.submit_feed(feed=feed_content,
                              feed_type=feed_type,
                              #marketplaceids=[marketplace_id],
                              content_type='text/xml', purge=False)
# ID取得
feed_id = feed_info.parsed['FeedSubmissionInfo']['FeedSubmissionId']['value']


while True:
    submission_list = feeds_api.get_feed_submission_list(feedids=[feed_id])
    status = submission_list.parsed['FeedSubmissionInfo']['FeedProcessingStatus']['value']
    
    if (status in ('_SUBMITTED_', '_IN_PROGRESS_', '_UNCONFIRMED_')):
        print('Sleeping and check again....')
        time.sleep(60)
    elif (status == '_DONE_'):
        print('処理完了')
        break
    else:
        print("エラー発生")
        break
    

