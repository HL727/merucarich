# -*- coding: utf-8 -*-

#GetMatchingProductForId

import mws

def parse2(item):
    print(item)
    asin = item['ASIN']['value']
    status = item['status']['value']
    if (status == 'Success'):
        all_offer_listings_considered=item['AllOfferListingsConsidered']['value']    
        product=item['Product']
        asin=product['Identifiers']['MarketplaceASIN']['ASIN']['value']
        marketplace_id=product['Identifiers']['MarketplaceASIN']['MarketplaceId']['value']
        for lowest_offer in product['LowestOfferListings']['LowestOfferListing']:
            print('----')
            print(lowest_offer['Qualifiers']['ItemCondition']['value'])
            print(lowest_offer['Qualifiers']['ItemSubcondition']['value'])
            print(lowest_offer['Qualifiers']['FulfillmentChannel']['value'])
            print(lowest_offer['Qualifiers']['ShipsDomestically']['value'])
            print(lowest_offer['Qualifiers']['ShippingTime']['Max']['value'])
            print(lowest_offer['Qualifiers']['SellerPositiveFeedbackRating']['value'])
            print(lowest_offer['NumberOfOfferListingsConsidered']['value'])
            print(lowest_offer['SellerFeedbackCount']['value'])
            print(lowest_offer['Price']['LandedPrice']['CurrencyCode']['value'])
            print(lowest_offer['Price']['LandedPrice']['Amount']['value'])
            print(lowest_offer['Price']['ListingPrice']['CurrencyCode']['value'])
            print(lowest_offer['Price']['ListingPrice']['Amount']['value'])
            print(lowest_offer['Price']['Shipping']['CurrencyCode']['value'])
            print(lowest_offer['Price']['Shipping']['Amount']['value'])
            print(lowest_offer['MultipleOffersAtLowestPrice']['value'])




def parse(item):
    asin = item['ASIN']['value']
    status = item['status']['value']
    fba=False
    new_price=-1
    used_price=-1
    if (status == 'Success'):
        product=item['Product']
        asin=product['Identifiers']['MarketplaceASIN']['ASIN']['value']
        for lowest_offer in product['LowestOfferListings']['LowestOfferListing']:
            channel=lowest_offer['Qualifiers']['FulfillmentChannel']['value']
            if (channel == 'Amazon'):
                fba=True

            condition=lowest_offer['Qualifiers']['ItemCondition']['value']
            value=int(float(lowest_offer['Price']['LandedPrice']['Amount']['value'])+ 0.5)
            if (condition == 'New'):
                if (new_price == -1 or new_price > value):
                    new_price = value
            elif (condition == 'Used'):
                if (used_price == -1 or used_price > value):
                    used_price = value

    print(asin + ',' + str(new_price) + ',' +  str(used_price) + ',' + str(fba))



# Amazon US MWS ID
account_id = 'A24P4FJD3PR3A6' #顧客情報
access_key = 'AKIAJEEEHMBTMBASK2FQ'
secret_key = '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'
auth_token = 'amzn.mws.42b3d459-00fd-a906-3d6a-1875e433f200' #顧客情報
region = 'JP'
marketplace_id='A1VC38T7YXB528'

# 5 
#asins = ['B073WRNNZ2', 'B00JVEPJYI']
asins = ['B07DRC2G4F']

# API
products_api = mws.Products(access_key=access_key,secret_key=secret_key,account_id=account_id,region=region,auth_token=auth_token)

# 情報の取得
response = products_api.get_lowest_offer_listings_for_asin(marketplaceid=marketplace_id, asins=asins)

if (type(response.parsed) is list):
    # 各商品情報を取得
    for item in response.parsed:
        parse(item)
else:
    parse(response.parsed)



