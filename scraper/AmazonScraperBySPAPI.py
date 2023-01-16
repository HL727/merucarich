# -*- coding: utf-8 -*-


import requests
from requests_html import HTMLSession
from urllib.parse import urljoin
from bs4 import BeautifulSoup
import time

import json
import os

try:
    from .AmazonOfferListScraper import AmazonOfferListScraper
except ImportError:
    import AmazonOfferListScraper

import io
from captchabuster import CaptchaBuster
from datetime import datetime

import traceback

import mws
import copy

from requests_toolbelt.adapters.source import SourceAddressAdapter
# sp api
from sp_api.api import Products
from accounts.models import User

from richs_utils import RichsUtils

_DEFAULT_BEAUTIFULSOUP_PARSER = "html5lib"

_CHROME_DESKTOP_USER_AGENT = 'Mozilla/5.0 (Macintosh; \
Intel Mac OS X 10_13_5) AppleWebKit/537.36 (KHTML, like Gecko) \
Chrome/67.0.3396.79 Safari/537.36'

_USER_AGENT_LIST = [
    _CHROME_DESKTOP_USER_AGENT,
]

_CSS_SELECTORS_DESKTOP = {
    "product": "div.s-result-item",
    "title": "h2.a-size-mini > a > span",
    "rating": "i.a-icon-star > span",
    "review_nb": "div.a-row.a-spacing-none > \
                a.a-size-small.a-link-normal.a-text-normal",
    "url": "span.rush-component > .a-link-normal",
    "next_page_url": "li.a-last > a",
    "prime-jp": "i.a-icon.a-icon-jp.a-icon-prime-jp.a-icon-small.s-align-text-bottom > span.a-icon-alt",
    "asin": "data-asin",
}

_CSS_SELECTOR_LIST = [
    _CSS_SELECTORS_DESKTOP
]

# ブロック対策
_MAX_TRIAL_REQUESTS = 10
_MAX_NORMAL_TRIAL_REQUESTS = 10
_WAIT_TIME_BETWEEN_REQUESTS = 1

_MY_USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36'

class AmazonScraperBySPAPI(object):

    def __init__(self, ipaddress=None):
        self.ipaddress = ipaddress
        self.session = requests.session()
        #self.session = HTMLSession() #requests.session()
        if (ipaddress):
            self.session.mount('http://', SourceAddressAdapter(ipaddress))
            self.session.mount('https://', SourceAddressAdapter(ipaddress))
        self.headers = {
            'Host': 'www.amazon.co.jp',
            # 'User-Agent': _USER_AGENT_LIST[0],
            'User-Agent': _MY_USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,\
                        application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        }
        self.product_dict_list = []
        self.page_index = 0
        self.base_url = 'https://www.amazon.co.jp'
        self.next_page_url = ''
        self.offer_list_scraper = None
        try:
            self.offer_list_scraper = AmazonOfferListScraper(self.ipaddress)
        except Exception:
            self.offer_list_scraper = AmazonOfferListScraper.AmazonOfferListScraper(self.ipaddress)
        # 変更禁止(MWS以降のため)
        self.low_price_detect = False
        self.proxies = {'http': 'socks5://127.0.0.1:9050','https': 'socks5://127.0.0.1:9050'}
        self.tor = False

        # MWS情報
        self.client_id = None
        self.client_secret = None
        self.access_key = None
        self.secret_key = None
        self.refresh_token = None
        self.region = None
        self.marketplace_id = None
        self.role_arn = None

    def get_cookies(self):
        return  json.dumps(self.session.cookies.get_dict())

    def set_cookies(self, cookies):
        self.session.cookies.update(json.loads(cookies))
            
    # データ取得
    def _get(self, url):
        print('from normal')
        headers = {
            'User-Agent': _MY_USER_AGENT,
            #'From': 'youremail@domain.com'  # This is another valid field
        }
        time.sleep(3)
        #res = requests.get(url)
        res = self.session.get(url, headers=self.headers, timeout=5) 
        '''
        number=str(datetime.now().timestamp()).replace('.','')
        path_w = '/tmp/amazon/' + number + '.html'
        with open(path_w, mode='w') as f:
            f.write(res.text)
            f.close()
        '''
        return res

    # データ取得
    def _get_tor(self, url):
        print('form tor')
        headers = {
            'User-Agent': _MY_USER_AGENT,
            #'From': 'youremail@domain.com'  # This is another valid field
        }
        time.sleep(3)
        return requests.get(url, headers=headers)
        # return self.session.get(url, proxies=self.proxies, timeout=15)


    # TOR利用有無を取得
    def get_tor(self, tor):        
        print('get form tor')
        return self.tor

    # TOR利用有無を設定
    def set_tor(self, tor):        
        print('get form local')
        self.tor = tor

    # 有効なページであるか判定する。TODO
    def _check_page(self, html_content):
        if "Amazon CAPTCHA" in html_content or "Sign in for the best experience" in html_content:
            print('ERROR')
            valid_page = False
        else:
            print('OK')
            valid_page = True
        return valid_page

    
    # ヘッダ更新 TODO;入力チェック   
    def _update_headers(self, search_url):
        self.base_url = "https://" + \
                        search_url.split("://")[1].split("/")[0] + "/"
        #self.headers['Host'] = self.base_url.split("://")[1].split("/")[0]
    
        
    # プライム
    def _get_prime(self, soup, css_selector_dict):
        prime = self._css_select(soup, css_selector_dict.get("prime-jp", ""))
        if (len(prime) > 0) :
            return 'True'
        else:
            return 'False'


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

    # 次のページ取得
    def get_next_page_url(self):
        return self.next_page_url

    # 認証
    def _do_captcha(self, org_url, res, timeout, proxies=None):
        base_dir='/tmp'
        #print('_do_captcha')

        # JavaScript実行
        #res.html.render()

        soup = BeautifulSoup(res.text, _DEFAULT_BEAUTIFULSOUP_PARSER)    
        tmp= soup.select('form')
        if (len(tmp) > 0):
            form = tmp[0]
            tmp = form.select('img')
            img_url=tmp[0].get('src')            
            #print(img_url)
            #number=str(datetime.now().timestamp()).replace('.','')
            #path = base_dir + '/' + self.save_image(img_url, base_dir, number)
            #print(path)
            #cb = CaptchaBuster(io.open(path, "rb", buffering = 0))
            #text=cb.guess
            #os.remove(path)
            #print(path)

            alias = img_url[48:].replace('/Captcha', '')
            aliasR = requests.get('http://160.16.133.101/amazon/captcha/' + alias)
            if (aliasR.status_code == 200):
                text = aliasR.json()['decode']
            else:
                number=str(datetime.now().timestamp()).replace('.','')
                path = base_dir + '/' + self.save_image(img_url, base_dir, number)
                #print(path)
                cb = CaptchaBuster(io.open(path, "rb", buffering = 0))
                text=cb.guess
                os.remove(path)
                print(path)

            print(text)
            inputs = form.select('input')
            payload={}
            url=form.get('action')
            method=form.get('method')
            for input in inputs:
                name=input.get('name')
                value=input.get('value')
                if (value == None):
                    value = text
                payload[name]=value

            # URLを再構築
            self._update_headers(org_url)
            url = urljoin(self.base_url, url)
            #print(url)
            #print(payload)
            if(method == 'post' or method == 'POST'):
                res = requests.post(url, headers=self.headers, data=payload, proxies=proxies, timeout=timeout, allow_redirects=True)
                #res = self.session.post(url, data=payload, proxies=proxies, timeout=timeout, allow_redirects=True)
            else:
                res = requests.get(url, headers=self.headers, params=payload, proxies=proxies, timeout=timeout, allow_redirects=True)
                #res = self.session.get(url, params=payload, proxies=proxies, timeout=timeout, allow_redirects=True)
        return res    
        



    # MWS情報設定
    def set_mws(self, client_id, client_secret, access_key, secret_key, refresh_token, region, marketplace_id, role_arn):
       self.client_id = client_id
       self.client_secret = client_secret
       self.access_key = access_key
       self.secret_key = secret_key
       self.refresh_token = refresh_token
       self.region = region
       self.marketplace_id = marketplace_id
       self.role_arn = role_arn

    # 最安値情報更新
    def _update_price_by_spapi_response(self, spapi_response):
        asin = spapi_response['ASIN']['value']
        status = spapi_response['status']['value']
        fba=False
        new_price=-1
        used_price=-1
        if (status == 'Success'):
            product=spapi_response['Product']
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
            
        print(asin + ',' + str(new_price) + ',' +  str(used_price) + ',' + str(fba))

    # 最安値情報更新
    def _update_price(self):    
        if (self.refresh_token == None or self.refresh_token == ''):
            return
        
        # API取得
        credentials = dict(
            refresh_token=self.refresh_token,
            lwa_app_id=self.client_id,
            lwa_client_secret=self.client_secret,
            aws_secret_key=self.secret_key,
            aws_access_key=self.access_key,
            role_arn=self.role_arn
        )
        products_api = Products(credentials=credentials, marketplace=self.marketplace_id)
        print('==========================================success======================================')
        # 最安値取得
        asins=[]
        data=copy.deepcopy(self.product_dict_list)
        last_idx = len(data) - 1
        
        for i,item in enumerate(data):
            is_last = True if i == last_idx else False
            tobe_called_api = True if ((i+1) % 20) == 0 else False #このAPIは、最大20ASIN
            asins.append(item['asin'])
            if (tobe_called_api or is_last):
                # 新品情報を取得
                # response = products_api.get_lowest_offer_listings_for_asin(marketplaceid=self.marketplace_id, asins=asins, condition='New')
                response = products_api.get_product_pricing_for_asins(asins, 'New', MarketPlaceId=self.marketplace_id)
                if type(response.payload) is list:
                    for response_item in response.payload:
                        try:
                            self._update_price_by_spapi_response(response_item)
                        except Exception:
                            print(traceback.format_exc())
                else:
                    try:
                        self._update_price_by_spapi_response(response.payload)
                    except Exception:
                        print(traceback.format_exc())

                #中古情報を取得
                response = products_api.get_product_pricing_for_asins(asins, 'Used', MarketPlaceId=self.marketplace_id)
                if type(response.payload) is list:
                    for response_item in response.payload:
                        try:
                            self._update_price_by_spapi_response(response_item)
                        except Exception:
                            print(traceback.format_exc())
                else:
                    try:
                        self._update_price_by_spapi_response(response.payload)
                    except Exception:
                        print(traceback.format_exc())

                # 更新済みのASIN情報をクリア
                asins.clear()

    # 商品情報取得
    def get_products(self, search_url=""):    

        self.next_page_url = ''
        self.product_dict_list.clear()
        self.tor = False

        # ヘッダ情報更新
        self._update_headers(search_url)
      
        trials = 0
        res=None
        valid_page = False
        while trials < _MAX_TRIAL_REQUESTS:
            trials += 1
            if (trials > _MAX_NORMAL_TRIAL_REQUESTS):
                self.tor = True
            try:
                if (self.tor):
                    res = self._get_tor(search_url)
                else:
                    res = self._get(search_url)
                
                valid_page = self._check_page(res.text)
            except Exception as e:
                print(traceback.format_exc())
                # To counter the "SSLError bad handshake" exception
                valid_page = False
                pass
            if valid_page:
                break
            else:
                time.sleep(_WAIT_TIME_BETWEEN_REQUESTS)
                if (self.tor):
                    res = self._do_captcha(search_url, res, timeout=15, proxies=self.proxies)
                else:
                    res = self._do_captcha(search_url, res, timeout=5, proxies=None)
                valid_page = self._check_page(res.text)
                if valid_page:
                    break
                time.sleep(_WAIT_TIME_BETWEEN_REQUESTS)

        self.page_index += 1                

        # ページチェック
        if (valid_page == False):
            return self.product_dict_list
        

        #print(res.text)
        soup = BeautifulSoup(res.text, _DEFAULT_BEAUTIFULSOUP_PARSER)    

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
                url = product.select_one(css_selector_dict.get("url", "")).attrs['href']
                if (url == None or url == ''):
                    continue
                
                url=url.strip()
                if (url.endswith('.html')):
                    continue

                asin = product[css_selector_dict.get("asin", "")]
                title = self._getTitle(product, css_selector_dict).strip()
                rating = self._getRating(product, css_selector_dict)
                revice_nb = self._getReviewNumber(product, css_selector_dict)
                image = product.select_one('img').get('src')		

                # 禁止キーワードの検索
                is_banned, _banned_item = RichsUtils.judge_banned_item(title)
                if is_banned:
                    continue

                price=''
                price_new=''
                price_old=''
                valid_price=True

                a_all=product.select('a')

                prime = self._get_prime(product, css_selector_dict)

                for a in a_all:
                    a_txt = a.text
                    n=a_txt.count('￥')
                    if (n==2 and a_txt.count('-')):
                        print(a_txt)
                        # 料金のレンジがある場合
                        price=a_txt.split('-')[-2].replace('￥','').replace(',','').strip()
                    elif(n==4):
                        # jay
                        price=a_txt.split('￥')[-4].replace('￥','').replace(',','').strip()
                        price_new=price
                        if(product.text.count('中古') == 1):
                            price_old=product.select_one('span.a-color-price').text.replace('￥','').replace(',','').strip()
                    elif(n==2):
                        # jay
                        price=a_txt.split('￥')[-2].replace('￥','').replace(',','').strip()
                        price_new=price
                        if(product.text.count('中古') == 1):
                            price_old=product.select_one('span.a-color-price').text.replace('￥','').replace(',','').strip()
                    elif(n==1):
                        if(a_txt.count('新品') == 1 and a_txt.count('中古') == 1 ):
                            '''
                            # 利用禁止:MWSに処理を変更(スクレイピングだとブロックがかかる)
                            if (self.low_price_detect == True):
                                # 最低価格を探索
                                self.offer_list_scraper.set_tor(self.tor)
                                self.offer_list_scraper.load_offers(a.get('href'))
                                price_new=str(self.offer_list_scraper.get_new_price())
                                price_old=str(self.offer_list_scraper.get_old_price())
                                time.sleep(_WAIT_TIME_BETWEEN_REQUESTS)
                                if (prime == False or prime == 'False'):
                                    prime = str(self.offer_list_scraper.get_prime())
                                #保持している値を初期化する。
                                self.offer_list_scraper.clear()
                            else:
                                valid_price=False
                            '''
                        elif(a_txt.count('新品') == 1):
                            price_new=a_txt.split('新品')[-2].replace('￥','').replace(',','').strip()
                            #print(price_new)
                        elif(a_txt.count('中古') == 1):
                            price_old=a_txt.split('中古')[-2].replace('￥','').replace(',','').strip()
                            #print(price_old)
                        else:
                            price=a_txt.replace('￥','').replace(',','').strip()
                            if (price_new == ''):
                                price_new = price
                            #print(price)

                #if (price == ''):
                #    continue

                '''
                # マーチャントを指定した検索(仕様禁止 MWSに以降のため。ブロックがかかる)
                if ('?me=' in search_url or '&me=' in search_url):
                    if (self.low_price_detect == True):
                        self.offer_list_scraper.set_tor(self.tor)
                        offer_url='https://www.amazon.co.jp/gp/offer-listing/' + asin  + '/ref=dp_olp_all_mbc?ie=UTF8&condition=all'
                        print(offer_url)
                        self.offer_list_scraper.load_offers(offer_url)
                        price_new=str(self.offer_list_scraper.get_new_price())
                        price_old=str(self.offer_list_scraper.get_old_price())
                        if (prime == False or prime == 'False'):
                            prime = str(self.offer_list_scraper.get_prime())
                        #保持している値を初期化する。
                        self.offer_list_scraper.clear()
                    else:
                        valid_price=False
                '''

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
                
                #print (asin + ',' + title  + ',' + str(price) + ',' + str(price_new) + ',' + str(price_old) + ',' + prime + ',' + str(valid_price))
                

            except Exception as e:
                print(traceback.format_exc())
                continue
            
        # 次のページが存在するか判定する
        self.next_page_url = self.getNextPageURL(soup, css_selector_dict)
        #time.sleep(_WAIT_TIME_BETWEEN_REQUESTS)

        # 価格更新
        try:
            self._update_price()
        except Exception as e:
            print(traceback.format_exc())
        
        return self.product_dict_list

    # 最低価格探索
    # 利用禁止:MWSに処理を変更(スクレイピングだとブロックがかかる)
    '''
    def set_low_price_detect(self,mode):
        self.low_price_detect = mode
    '''

    # 画像をダウンロードする
    def _download_image(self,url, timeout = 10):

        trials = 0
        while trials < _MAX_TRIAL_REQUESTS:
            trials += 1

            # ヘッダ情報更新
            self._update_headers(url)
            headers = {
                'User-Agent': _MY_USER_AGENT,
                'From': 'youremail@domain.com'  # This is another valid field
            }
            time.sleep(3)
            response = requests.get(url, headers=headers)
            #response = self.session.get(url, headers=self.headers, allow_redirects=False, timeout=timeout)
            # response = self.session.get(url, allow_redirects=False, timeout=timeout)
            if response.status_code != 200:
                print('-- 画像取得エラー1 --')
                print(response.status_code)
                time.sleep(_WAIT_TIME_BETWEEN_REQUESTS)
                continue
                
            content_type = response.headers["content-type"]
            if 'image' not in content_type:
                print('-- 画像取得エラー2 --')
                print(content_type)            
                time.sleep(_WAIT_TIME_BETWEEN_REQUESTS)
                continue
            
            # 取得結果チェック
            return response.content
        
        # TODO Exception
        print('画像取得エラー: AmazonScraper.py')
        return 'Error'.encode()


    # 画像のファイル名を決める
    def _make_filename(self, base_dir, number, url):
        ext = os.path.splitext(url)[1] # 拡張子を取得
        if '?' in ext:
            ext = ext.split('?')[-2]
        filename = number + ext        # 番号に拡張子をつけてファイル名にする
        return filename

    # 画像を保存する
    def _save_image(self, fullpath, image):
        with open(fullpath, "wb") as fout:
            fout.write(image)
    
    # 画像を保存する。
    def save_image(self, url, base_dir, number):
        image = self._download_image(url)
        filename =  self._make_filename(base_dir, number, url)
        fullpath = os.path.join(base_dir, filename)
        print('BBB save url=' + url)
        print('AAA save path=' + fullpath)

        self._save_image(fullpath, image)
        print('BBB save path=' + fullpath)
        return filename


'''
c = AmazonScraper('163.43.241.68')
x=c.get_products('https://www.amazon.co.jp/s?marketplaceID=A1VC38T7YXB528&me=A3IDNGUH5NBNB9&merchant=A3IDNGUH5NBNB9')
print(x)

cookies = c.get_cookies()
print(cookies)
c.set_cookies(cookies)
'''



