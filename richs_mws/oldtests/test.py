# -*- coding: utf-8 -*-

from boto.mws import connection
import time
from jinja2 import Environment, FileSystemLoader


# Amazon US MWS ID
MarketPlaceID = 'A1VC38T7YXB528'
MerchantID = 'A24P4FJD3PR3A6'
AccessKeyID = 'AKIAJEEEHMBTMBASK2FQ'
SecretKey = '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'

env = Environment(loader=FileSystemLoader('/var/www/richs/richs_mws/templates', encoding='utf8') ,trim_blocks=True,lstrip_blocks=True)
template = env.get_template('feed_update.xml')

class Message(object):
    def __init__(self, sku, quantity, fulfillment_latency):
        self.sku = sku
        self.quantity = quantity
        self.fulfillment_latency = fulfillment_latency

feed_messages = [
    Message('00000003', 1, 14),
    Message('00000004', 1, 14),
]
namespace = dict(MerchantId=MerchantID, FeedMessages=feed_messages)
feed_content = template.render(namespace).encode('utf-8')


conn = connection.MWSConnection(
    aws_access_key_id=AccessKeyID,
    aws_secret_access_key=SecretKey,
    Merchant=MerchantID)

conn.host='mws.amazonservices.jp'

feed = conn.submit_feed(
    FeedType='_POST_INVENTORY_AVAILABILITY_DATA_',
    PurgeAndReplace=False,
    MarketplaceIdList=[MarketPlaceID],
    content_type='text/xml',
    FeedContent=feed_content
)

feed_info = feed.SubmitFeedResult.FeedSubmissionInfo
print('Submitted product feed: ' + str(feed_info))

while True:
    submission_list = conn.get_feed_submission_list(
        FeedSubmissionIdList=[feed_info.FeedSubmissionId]
    )
    info =  submission_list.GetFeedSubmissionListResult.FeedSubmissionInfo[0]
    id = info.FeedSubmissionId
    status = info.FeedProcessingStatus
    print( 'Submission Id: {}. Current status: {}'.format(id, status))

    if (status in ('_SUBMITTED_', '_IN_PROGRESS_', '_UNCONFIRMED_')):
        print('Sleeping and check again....')
        time.sleep(60)
    elif (status == '_DONE_'):
        feedResult = conn.get_feed_submission_result(FeedSubmissionId=id)
        print(feedResult)
        break
    else:
        print("Submission processing error. Quit.")
        break

