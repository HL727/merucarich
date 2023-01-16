# -*- coding: utf-8 -*-

#GetMatchingProductForId

import mws
import mws
import time
from jinja2 import Environment, FileSystemLoader

import traceback

class MWSUtils(object):
    
    def __init__(self, account_id, access_key, secret_key, auth_token, region, marketplace_id):
        self.account_id = account_id
        self.access_key = access_key
        self.secret_key = secret_key
        self.auth_token = auth_token
        self.region = region
        self.marketplace_id = marketplace_id

    def __get_matching_product_parser(self, result, item):
        asin = item['ASIN']['value']
        status = item['status']['value']
        title = ''
        brand = ''
        small_image = ''
        manufacturer = ''
        model = ''
        product_group = ''
        product_type_name = ''
        data = {}
        if (status == 'Success'):
            product = item['Product']
            if ('AttributeSets' in product):
                attribute_sets = product['AttributeSets']
                if ('ItemAttributes' in attribute_sets):
                    item_attributes = attribute_sets['ItemAttributes']
                    title = item_attributes['Title']['value']
                    if ('Brand' in  item_attributes):
                        brand = item_attributes['Brand']['value']
                    if ('ProductGroup' in  item_attributes):
                        product_group = item_attributes['ProductGroup']['value']
                    if ('SmallImage' in  item_attributes):
                        small_image = item_attributes['SmallImage']['URL']['value']
                    if ('Manufacturer' in  item_attributes):
                        manufacturer = item_attributes['Manufacturer']['value']
                    if ('Model' in  item_attributes):
                        model = item_attributes['Model']['value']
                    if ('ProductGroup' in  item_attributes):
                        product_group = item_attributes['ProductGroup']['value']
                    if ('ProductTypeName' in  item_attributes):
                        product_type_name = item_attributes['ProductTypeName']['value']
                        
        data['asin'] = asin
        data['status'] = status
        data['title'] = title
        data['brand'] = brand
        data['small_image'] = small_image
        data['manufacturer'] = manufacturer
        data['model'] = model
        data['product_group'] = product_group
        data['product_type_name'] = product_type_name

        result[asin] = data
        #print(title + " " + brand + " " + manufacturer + " " + model + " " + product_group + " " + product_type_name + " " + small_image)



    def get_matching_product(self, asins):
        try:
            return self.__get_matching_product_internal(asins)
        except:
            print(traceback.format_exc())
            return {}

    def __get_matching_product_internal(self, asins):
        products_api = mws.Products(access_key=self.access_key, secret_key=self.secret_key, account_id=self.account_id, region=self.region, auth_token=self.auth_token)
        response = products_api.get_matching_product(marketplaceid=self.marketplace_id, asins=asins)
        result={}
        if (type(response.parsed) is list):
            # 各商品情報を取得
            for item in response.parsed:
                self.__get_matching_product_parser(result, item)
        else:
            self.__get_matching_product_parser(result, response.parsed)

        return result

    
    def __get_matching_product_for_id_parser(self, result, item):
        id_ = item['Id']['value']
        status = item['status']['value']
        title = ''
        brand = ''
        small_image = ''
        manufacturer = ''
        model = ''
        product_group = ''
        product_type_name = ''
        data = {}
        if (status == 'Success'):
            products = item['Products']
            product = products['Product']
            if ('AttributeSets' in product):
                attribute_sets = product['AttributeSets']
                if ('ItemAttributes' in attribute_sets):
                    item_attributes = attribute_sets['ItemAttributes']
                    title = item_attributes['Title']['value']
                    if ('Brand' in  item_attributes):
                        brand = item_attributes['Brand']['value']
                    if ('ProductGroup' in  item_attributes):
                        product_group = item_attributes['ProductGroup']['value']
                    if ('SmallImage' in  item_attributes):
                        small_image = item_attributes['SmallImage']['URL']['value']
                    if ('Manufacturer' in  item_attributes):
                        manufacturer = item_attributes['Manufacturer']['value']
                    if ('Model' in  item_attributes):
                        model = item_attributes['Model']['value']
                    if ('ProductGroup' in  item_attributes):
                        product_group = item_attributes['ProductGroup']['value']
                    if ('ProductTypeName' in  item_attributes):
                        product_type_name = item_attributes['ProductTypeName']['value']
                        
        data['id'] = id_
        data['status'] = status
        data['title'] = title
        data['brand'] = brand
        data['small_image'] = small_image
        data['manufacturer'] = manufacturer
        data['model'] = model
        data['product_group'] = product_group
        data['product_type_name'] = product_type_name

        result[id_] = data
        #print(title + " " + brand + " " + manufacturer + " " + model + " " + product_group + " " + product_type_name + " " + small_image)

    # GetMatchingProductForId
    def get_matching_product_for_id(self, type_, ids):
        try:
            return self.__get_matching_product_for_id_internal(type_, ids)
        except:
            print(traceback.format_exc())
            return {}

    # GetMatchingProductForId
    def __get_matching_product_for_id_internal(self, type_, ids):
        products_api = mws.Products(access_key=self.access_key, secret_key=self.secret_key, account_id=self.account_id, region=self.region, auth_token=self.auth_token)
        response = products_api.get_matching_product_for_id(marketplaceid=self.marketplace_id, type_=type_, ids=ids)
        result={}
        if (type(response.parsed) is list):
            # 各商品情報を取得
            for item in response.parsed:
                self.__get_matching_product_for_id_parser(result, item)
        else:
            self.__get_matching_product_for_id_parser(result, response.parsed)

        return result


    def __get_my_price_for_sku_parser(self, result, item):
        amount = ''
        code = ''
        
        sku = item['SellerSKU']['value']
        status = item['status']['value']
        if (status == 'Success'):
            products = item['Product']
            asin = products['Identifiers']['MarketplaceASIN']['ASIN']['value']
            offers = products['Offers']
            if ('Offer' in offers):
                try:
                    regular_price = offers['Offer']['RegularPrice']
                    amount = regular_price['Amount']['value']
                    code = regular_price['CurrencyCode']['value']
                except:
                    print(traceback.format_exc())
                    pass
        data={}
        data['sku'] = sku
        data['status'] = status
        data['amount'] = amount
        data['code'] = code
        result[sku]=data


    # SKUで指定された商品の価格を取得する。
    def get_my_price_for_sku(self, skus):
        products_api = mws.Products(access_key=self.access_key, secret_key=self.secret_key, account_id=self.account_id, region=self.region, auth_token=self.auth_token)
        response = products_api.get_my_price_for_sku(marketplaceid=self.marketplace_id, skus=skus)
        result={}
        if (type(response.parsed) is list):
            # 各商品情報を取得
            for item in response.parsed:
                self.__get_my_price_for_sku_parser(result, item)
        else:
            self.__get_my_price_for_sku_parser(result, response.parsed)

        return result


    # 商品情報の更新結果を種痘
    def get_feed_submission_result(self, feedid):
        # API
        feeds_api = mws.Feeds(access_key=self.access_key, secret_key=self.secret_key, account_id=self.account_id, region=self.region, auth_token=self.auth_token)
        # 変更要求
        response = feeds_api.get_feed_submission_result(feedid)
        parsed = response.parsed
        error_skus=[]
        valid_response = False
        #print(parsed)
        if ('ProcessingReport' in parsed):
            valid_response = True
            processing_report=parsed['ProcessingReport']
            if ('Result' in processing_report):
                result_list = processing_report['Result']
                if (type(result_list) is list):
                    for result in result_list:
                        info = result['AdditionalInfo']
                        if ('SKU' in info):
                            error_skus.append(info['SKU']['value'])
                else:
                    if ('AdditionalInfo' in result_list):
                        info = result_list['AdditionalInfo']
                        if ('SKU' in info):
                            error_skus.append(info['SKU']['value'])

        return valid_response, error_skus
        

    #  在庫数とリードタイムを更新
    def update_quantity_and_fulfillment_latency(self, feed_messages):
        feed_type='_POST_INVENTORY_AVAILABILITY_DATA_'

        env = Environment(loader=FileSystemLoader('/var/www/richs/richs_mws/templates', encoding='utf8') ,trim_blocks=True,lstrip_blocks=True)
        template = env.get_template('feed_update.xml')

        namespace = dict(MerchantId=self.account_id, FeedMessages=feed_messages)
        feed_xml = template.render(namespace)
        #print(feed_xml)
        feed_content = feed_xml.encode()
        # API
        feeds_api = mws.Feeds(access_key=self.access_key, secret_key=self.secret_key, account_id=self.account_id, region=self.region, auth_token=self.auth_token)
        # 変更要求
        feed_info = feeds_api.submit_feed(feed=feed_content, feed_type=feed_type, marketplaceids=[self.marketplace_id], content_type='text/xml', purge=False)
        # ID取得
        feed_id = feed_info.parsed['FeedSubmissionInfo']['FeedSubmissionId']['value']
        while True:
            submission_list = feeds_api.get_feed_submission_list(feedids=[feed_id])
            parsed = submission_list.parsed
            #print(parsed)
            status = parsed['FeedSubmissionInfo']['FeedProcessingStatus']['value']
            if (status in ('_SUBMITTED_', '_IN_PROGRESS_', '_UNCONFIRMED_')):
                #print('Sleeping and check again....')
                time.sleep(60)
            elif (status == '_DONE_'):
                #print('処理完了')
                return True, feed_id
            else:
                print("在庫数とリードタイム更新エラー発生:" + status)
                return False, feed_id 


# テスト用メッセージ
class Message(object):
    def __init__(self, sku, quantity, fulfillment_latency):
        self.item_sku = sku
        self.current_purchase_quantity = quantity
        self.current_purchase_fulfillment_latency = fulfillment_latency

'''
messages=[]

messages.append(Message('m42243138368', 0, 14))
messages.append(Message('m293904730', 0, 14))
messages.append(Message('aaaaaaaaaa', 0, 14))
messages.append(Message('bbbbbbbbbb', 0, 14))

api = MWSUtils('A24P4FJD3PR3A6', 'AKIAJEEEHMBTMBASK2FQ', 'L4Tp1Ux3bFz+jGImJVNVVp6sb0Y9Yi5bejfRPvI9', 'amzn.mws.42b3d459-00fd-a906-3d6a-1875e433f200', 'JP', 'A1VC38T7YXB528')
#result=api.update_quantity_and_fulfillment_latency(messages)

skus=[]
skus.append('m42243138368')
skus.append('m293904730')
skus.append('aaaaaaaaaa')
skus.append('bbbbbbbbbb')

result=api.get_my_price_for_sku(skus)
print(result)



result=api.get_feed_submission_result(result[1])
print(result[0])
print(result[1])

print('終了')
'''


