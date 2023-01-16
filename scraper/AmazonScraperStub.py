# -*- coding: utf-8 -*-


import sys

import requests
from urllib.parse import urljoin
from bs4 import BeautifulSoup
import time

import json
import os
import mws
import copy

try:
    from .AmazonOfferListScraperStub import AmazonOfferListScraperStub
except ImportError:
    import AmazonOfferListScraperStub

import traceback





_DEFAULT_BEAUTIFULSOUP_PARSER = "html5lib"

_CHROME_DESKTOP_USER_AGENT = 'Mozilla/5.0 (Macintosh; \
Intel Mac OS X 10_13_5) AppleWebKit/537.36 (KHTML, like Gecko) \
Chrome/67.0.3396.79 Safari/537.36'

_USER_AGENT_LIST = [
    _CHROME_DESKTOP_USER_AGENT,
]

_CSS_SELECTORS_DESKTOP = {
    "product": "ul > li.s-result-item > div.s-item-container",
    "title": "a.s-access-detail-page > h2",
    "rating": "i.a-icon-star > span",
    "review_nb": "div.a-row.a-spacing-none > \
                a.a-size-small.a-link-normal.a-text-normal",
    "url": "div.a-row.a-spacing-mini > div.a-row.a-spacing-none > a['href']",
    "next_page_url": "a#pagnNextLink",
    "prime-jp": "i.a-icon.a-icon-jp.a-icon-prime-jp.a-icon-small.s-align-text-bottom > span.a-icon-alt",    
}

_CSS_SELECTOR_LIST = [
    _CSS_SELECTORS_DESKTOP
]

# ブロック対策
_MAX_TRIAL_REQUESTS = 1
_WAIT_TIME_BETWEEN_REQUESTS = 1

class AmazonScraperStub(object):

    def __init__(self):
        self.session = requests.session()
        self.headers = {
            'Host': 'www.amazon.co.jp',
            'User-Agent': _USER_AGENT_LIST[0],
            'Accept': 'text/html,application/xhtml+xml,\
                        application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        }
        self.product_dict_list = []
        self.page_index = 0
        self.base_url = 'https://www.amazon.co.jp'
        self.next_page_url = ''

        # MWS情報
        self.account_id = None
        self.access_key = None
        self.secret_key = None
        self.auth_token = None
        self.region = None
        self.marketplace_id = None
        
        try:
            self.offer_list_scraper = AmazonOfferListScraperStub()
        except Exception:
            self.offer_list_scraper = AmazonOfferListScraperStub.AmazonOfferListScraperStub()

        # 変更禁止(MWS以降のため)
        self.low_price_detect = False


    def get_cookies(self):
        return  json.dumps(self.session.cookies.get_dict())

    def set_cookies(self, cookies):
        self.session.cookies.update(json.loads(cookies))
            
        
    # データ取得
    def _get(self, url):
        #return self.session.get(url, headers=self.headers)
        with open("/var/www/richs/scraper/data/amazon/amazon.htm") as f:
            text = f.read()
            f.close()
            return text

    # 有効なページであるか判定する。TODO
    def _check_page(self, html_content):
        """ Check if the page is a valid result page
        (even if there is no result) """
        if "Sign in for the best experience" in html_content:
            valid_page = False
        else:
            valid_page = True
        return valid_page

    # ヘッダ更新 TODO;入力チェック   
    def _update_headers(self, search_url):
        self.base_url = "https://" + \
                        search_url.split("://")[1].split("/")[0] + "/"
        self.headers['Host'] = self.base_url.split("://")[1].split("/")[0]

        
    # CSS選択
    def _css_select(self, soup, css_selector):
        selection = soup.select(css_selector)
        if len(selection) > 0:
            if hasattr(selection[0], 'text'):
                retour = selection[0].text.strip()
            else:
                retour = ""
        else:
            retour = ""
        return retour

    # プライム
    def _get_prime(self, soup, css_selector_dict):
        prime = self._css_select(soup, css_selector_dict.get("prime-jp", ""))
        if (len(prime) > 0) :
            return 'True'
        else:
            return 'False'

    # 商品名を取得
    def _getTitle(self, soup, css_selector_dict):
        return self._css_select(soup, css_selector_dict.get("title", ""))
    
    # レビュー数を取得
    def _getReviewNumber(self, soup, css_selector_dict):
        selections = soup.select(css_selector_dict.get("review_nb", ""))
        if len(selections) > 0:
            # TODO:最後の要素から見る
            for selection in selections:
                if selection.get('href').endswith('Reviews') :
                    return selection.text.strip()
        return ""

    # URL取得
    def _getURL(self, soup, css_selector_dict):
        selections = soup.select(css_selector_dict.get("url", ""))
        if len(selections) > 0:
            for selection in selections:
                return selection.get('href').split("/ref=")[0]
            return ""

    # 星の数 TODO , -> .
    def _getRating(self, soup, css_selector_dict):
        rating = self._css_select(soup, css_selector_dict.get("rating", ""))
        if rating:
            tmp = rating.split(' ')
            if len(tmp) == 2:
                return tmp[1]
        return ""

    # 次のページを取得
    def getNextPageURL(self, soup, css_selector_dict):
        css_selector = css_selector_dict.get("next_page_url", "")
        url_next_page_soup = soup.select(css_selector)
        if url_next_page_soup:
            return urljoin(self.base_url,url_next_page_soup[0].get('href'))
        return ""


    def get_next_page_url(self):
        return self.next_page_url



    # MWS情報設定
    def set_mws(self, account_id, access_key, secret_key, auth_token, region, marketplace_id):
       self.account_id = account_id
       self.access_key = access_key
       self.secret_key = secret_key
       self.auth_token = auth_token
       self.region = region
       self.marketplace_id = marketplace_id
       
    # 最安値情報更新
    def _update_price_by_mws_response(self, mws_response):    
        asin = mws_response['ASIN']['value']
        status = mws_response['status']['value']
        fba=False
        new_price=-1
        used_price=-1
        if (status == 'Success'):
            product=mws_response['Product']
            asin=product['Identifiers']['MarketplaceASIN']['ASIN']['value']
            lowest_offer_listings = product['LowestOfferListings']
            if ('LowestOfferListing' not in lowest_offer_listings):
                return
            lowest_offer_listing = lowest_offer_listings['LowestOfferListing']
            if (type(lowest_offer_listing) is not list):
                lowest_offer_listing = [lowest_offer_listing]
            for lowest_offer in lowest_offer_listing:
                if ('Qualifiers' not in lowest_offer):
                    continue
                channel=lowest_offer['Qualifiers']['FulfillmentChannel']['value']
                if (channel == 'Amazon'):
                    fba=True
                condition=lowest_offer['Qualifiers']['ItemCondition']['value']
                if ('Price' not in lowest_offer):
                    continue

                # 通常料金
                price = lowest_offer['Price']
                if('LandedPrice' in price):
                    value=int(float(price['LandedPrice']['Amount']['value'])+ 0.5)
                    if (condition == 'New'):
                        if (new_price == -1 or new_price > value):
                            new_price = value
                    elif (condition == 'Used'):
                        if (used_price == -1 or used_price > value):
                            used_price = value

                # プロモーション料金
                if('ListingPrice' in price):
                    value=int(float(price['ListingPrice']['Amount']['value'])+ 0.5)
                    if (condition == 'New'):
                        if (new_price == -1 or new_price > value):
                            new_price = value
                    elif (condition == 'Used'):
                        if (used_price == -1 or used_price > value):
                            used_price = value

        # リスト更新処理
        for item in self.product_dict_list:
            if (item['asin'] != asin):
                continue
            if (fba):
                item['prime'] = 'True'
            if (new_price > -1):
                item['price_new'] = str(new_price)
            if (used_price > -1):
                item['price_old'] = str(used_price)
            item['valid_price'] = 'True'
            
        #print(asin + ',' + str(new_price) + ',' +  str(used_price) + ',' + str(fba))

    # 最安値情報更新
    def _update_price(self):    
        if (self.auth_token == None or self.auth_token == ''):
            return
        
        # API取得
        products_api = mws.Products(access_key=self.access_key, secret_key=self.secret_key, account_id=self.account_id, region=self.region, auth_token=self.auth_token)

        # 最安値取得
        asins=[]
        data=copy.deepcopy(self.product_dict_list)
        for i,item in enumerate(data):
            tobe_called_api = True if ((i+1) % 20) == 0 else False #このAPIは、最大20ASIN
            asins.append(item['asin'])
            if (tobe_called_api):
                # 新品情報を取得
                response = products_api.get_lowest_offer_listings_for_asin(marketplaceid=self.marketplace_id, asins=asins, condition='New')
                if (type(response.parsed) is list):
                    for item in response.parsed:
                        try:
                            self._update_price_by_mws_response(item)
                        except Exception:
                            print(traceback.format_exc())
                else:
                    try:
                        self._update_price_by_mws_response(response.parsed)
                    except Exception:
                        print(traceback.format_exc())

                #中古情報を取得
                response = products_api.get_lowest_offer_listings_for_asin(marketplaceid=self.marketplace_id, asins=asins, condition='Used')
                if (type(response.parsed) is list):
                    for item in response.parsed:
                        try:
                            self._update_price_by_mws_response(item)
                        except Exception:
                            print(traceback.format_exc())
                else:
                    try:
                        self._update_price_by_mws_response(response.parsed)
                    except Exception:
                        print(traceback.format_exc())

                # 更新済みのASIN情報をクリア
                asins.clear()

    # 商品情報取得
    def get_products(self, search_url=""):    

        self.next_page_url = ''
        self.product_dict_list.clear()

        # ヘッダ情報更新
        self._update_headers(search_url)
      
        trials = 0
        text=''
        while trials < _MAX_TRIAL_REQUESTS:
            trials += 1
            try:
                text = self._get(search_url)
                valid_page = self._check_page(res.text)
                path_w = '/tmp/html_' + str(self.page_index + 1) + '.' + str(trials) + '.html'
                #with open(path_w, mode='w') as f:
                #    f.write(res.text)
                #    f.close()
            except Exception as e:
                # To counter the "SSLError bad handshake" exception
                valid_page = False
                pass
            if valid_page:
                break
            else:
                # TODO:UA変更
                time.sleep(_WAIT_TIME_BETWEEN_REQUESTS)

        self.page_index += 1                
        self.last_html_page = text
        #print(res.text)
        
        soup = BeautifulSoup(text, _DEFAULT_BEAUTIFULSOUP_PARSER)    

        # 対応するCSSを探す
        for css_selector_dict in _CSS_SELECTOR_LIST:
            css_selector = css_selector_dict.get("product", "")
            products = soup.select(css_selector)
            if len(products) >= 1:
                break

        # 検索結果から個々の製品情報を取得する。
        for product in products:
            try:
                
                # 現在のページから取得できる情報を取得する。
                url = self._getURL(product, css_selector_dict)
                if (url == None or url == ''):
                    continue
                
                url=url.strip()
                if (url.endswith('.html')):
                    continue

                asin = url.split('/')[-1]
                title = self._getTitle(product, css_selector_dict).strip()
                rating = self._getRating(product, css_selector_dict)
                revice_nb = self._getReviewNumber(product, css_selector_dict)
                image = product.select('img.s-access-image.cfMarker')[0].get('src')


                price=''
                price_new=''
                price_old=''
                valid_price=True

                a_all=product.select('a')

                prime = self._get_prime(product, css_selector_dict)

                for a in a_all:
                    a_txt = a.text
                    n=a_txt.count('￥')
                    if (n==2):
                        #print(a_txt)
                        # 料金のレンジがある場合
                        price=a_txt.split('-')[-2].replace('￥','').replace(',','').strip()
                    elif(n==1):
                        if(a_txt.count('新品') == 1 and a_txt.count('中古') == 1 ):
                            if (self.low_price_detect == True):
                                # スクレイピングによる最低価格を探索(旧処理で、現状は呼び出し禁止。現状は、MWSに移行)
                                self.offer_list_scraper.load_offers(a.get('href'))
                                price_new=str(self.offer_list_scraper.get_new_price())
                                price_old=str(self.offer_list_scraper.get_old_price())
                                time.sleep(_WAIT_TIME_BETWEEN_REQUESTS)
                                if (prime == False):
                                    prime = str(self.offer_list_scraper.get_prime())
                                #保持している値を初期化する。
                                self.offer_list_scraper.clear()
                            else:
                                valid_price=False
                        elif(a_txt.count('新品') == 1):
                            price_new=a_txt.split('新品')[-2].replace('￥','').replace(',','').strip()
                            #print(price_new)
                        elif(a_txt.count('中古') == 1):
                            price_old=a_txt.split('中古')[-2].replace('￥','').replace(',','').strip()
                            #print(price_old)
                        else:
                            price=a_txt.replace('￥','').replace(',','').strip()
                            if (price_new == -1):
                                price_new = price

                            #print(price)

                if (price == ''):
                    continue

                product_dict = {}
                product_dict['asin'] = asin
                product_dict['title'] = title
                product_dict['rating'] = rating
                product_dict['revice_nb'] = revice_nb
                product_dict['url'] = url
                product_dict['image'] =image
                product_dict['prime'] = prime
                product_dict['price'] = price
                product_dict['price_new'] = price_new
                product_dict['price_old'] = price_old
                product_dict['valid_price'] = str(valid_price)
                                
                self.product_dict_list.append(product_dict)
                
                print (asin + ',' + title  + ',' + str(price) + ',' + str(price_new) + ',' + str(price_old))

            except Exception as e:
                print(traceback.format_exc())
                continue
            
        # 次のページが存在するか判定する
        nextPageURL= self.getNextPageURL(soup, css_selector_dict)
        #time.sleep(_WAIT_TIME_BETWEEN_REQUESTS)

        # 価格更新
        self._update_price()

        return self.product_dict_list

    
    # 最低価格探索 * 利用禁止(MWS以降のため)
    def set_low_price_detect(self,mode):
        self.low_price_detect = mode

    # 画像をダウンロードする
    def _download_image(self,url, timeout = 10):

        # ヘッダ情報更新
        self._update_headers(url)
        headers = {
            'User-Agent': 'My User Agent 1.0',
            'From': 'youremail@domain.com'  # This is another valid field
        }
        time.sleep(3)
        response = requests.get(url, headers=headers)
        # response = self.session.get(url, headers=self.headers, allow_redirects=False, timeout=timeout)
        if response.status_code != 200:
            e = Exception("HTTP status: " + response.status_code)
            raise e

        content_type = response.headers["content-type"]
        if 'image' not in content_type:
            e = Exception("Content-Type: " + content_type)
            raise e

        return response.content

    # 画像のファイル名を決める
    def _make_filename(self, base_dir, number, url):
        ext = os.path.splitext(url)[1] # 拡張子を取得
        if '?' in ext:
            ext = ext.split('?')[-2]
        filename = number + ext        # 番号に拡張子をつけてファイル名にする
        return filename

    # 画像を保存する
    def _save_image(self, fullpath, image):
        print('fullpath=' +fullpath)
        with open(fullpath, "wb") as fout:
            fout.write(image)

    #
    def save_image(self, url, base_dir, number):
        print('base_dir=' + base_dir)
        image = self._download_image(url)
        filename =  self._make_filename(base_dir, number, url)
        fullpath = os.path.join(base_dir, filename)
        self._save_image(fullpath, image)
        return filename


'''
c = AmazonScraperStub()
#c.set_low_price_detect(True)
#c.set_mws('A3UHE9VQJJHJ98', 'AKIAJEEEHMBTMBASK2FQ', 'L4Tp1Ux3bFz+jGImJVNVVp6sb0Y9Yi5bejfRPvI9', 'amzn.mws.e6b3de8d-cc3f-25fa-9813-aef1aaa98259', 'JP', 'A1VC38T7YXB528')
x=c.get_products('https://www.amazon.co.jp/s/ref=nb_sb_ss_i_7_3?__mk_ja_JP=%E3%82%AB%E3%82%BF%E3%82%AB%E3%83%8A&url=search-alias%3Daps&field-keywords=akb48+%E3%82%AB%E3%83%AC%E3%83%B3%E3%83%80%E3%83%BC+2019&rh=i%3Aaps%2Ck%3Aakb48+%E3%82%AB%E3%83%AC%E3%83%B3%E3%83%80%E3%83%BC+2019')
print(x)
'''

# 3x3
#c.get_products(search_url="https://www.amazon.co.jp/s?marketplaceID=A1VC38T7YXB528&redirect=true&me=A2VPSJWJUCARY0&merchant=A2VPSJWJUCARY0", max_product_nb=100000)

# 2x2
#c.get_products(search_url="https://www.amazon.co.jp/s/ref=sr_il_ti_merchant-items?me=A2VPSJWJUCARY0&rh=i%3Amerchant-items&ie=UTF8&qid=1536731837&lo=merchant-items", max_product_nb=100000)    
