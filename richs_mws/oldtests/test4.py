# -*- coding: utf-8 -*-

#GetMatchingProductForId

import mws

def parse(item):
    print(item)
    asin = item['ASIN']['value']
    status = item['status']['value']
    print(asin)
    print(status)
    if (status == 'Success'):
        attributes = item['Product']['AttributeSets']['ItemAttributes']
        title = attributes['Title']['value']
        image = attributes['SmallImage']['URL']['value']
        print(title)
        print(image)

# Amazon US MWS ID
account_id = 'A24P4FJD3PR3A6' #顧客情報
access_key = 'AKIAJEEEHMBTMBASK2FQ'
secret_key = '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'
auth_token = 'amzn.mws.42b3d459-00fd-a906-3d6a-1875e433f200' #顧客情報
region = 'JP'
marketplace_id='A1VC38T7YXB528'

# 5 
asins = ['B073WRNNZ2', 'B00JVEPJYI']
#asins = ['B00JVEPJYI']

# API
products_api = mws.Products(access_key=access_key,secret_key=secret_key,account_id=account_id,region=region,auth_token=auth_token)

# 情報の取得
response = products_api.get_matching_product(marketplaceid=marketplace_id, asins=asins)

if (type(response.parsed) is list):
    # 各商品情報を取得
    for item in response.parsed:
        parse(item)
else:
    parse(item)



