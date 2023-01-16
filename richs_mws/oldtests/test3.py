# -*- coding: utf-8 -*-

import mws

# Amazon US MWS ID
account_id = 'A24P4FJD3PR3A6' #顧客情報
access_key = 'AKIAJEEEHMBTMBASK2FQ'
secret_key = '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'
auth_token = 'amzn.mws.42b3d459-00fd-a906-3d6a-1875e433f200' #顧客情報
region = 'JP'
marketplace_id='A1VC38T7YXB528'


# 最大20
skus = ['00000001', '00000005']

# API
products_api = mws.Products(access_key=access_key,secret_key=secret_key,account_id=account_id,region=region,auth_token=auth_token)

# 情報の取得
items = products_api.get_my_price_for_sku(marketplaceid=marketplace_id, skus=skus)

print(items.original)


# 各商品情報を取得
for item in items.parsed:
    sku = item['SellerSKU']['value']
    status = item['status']['value']
    print(sku)
    print(status)
    if (status == 'Success'):
        products = item['Product']
        asin = products['Identifiers']['MarketplaceASIN']['ASIN']['value']
        offers = products['Offers']
        if ('Offer' in offers):
            regular_price = offers['Offer']['RegularPrice']
            code = regular_price['CurrencyCode']['value']
            amount = regular_price['Amount']['value']
            print(amount)
            print(code)
            



