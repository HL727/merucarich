# -*- coding: utf-8 -*-

import requests
from requests_html import HTMLSession
from urllib.parse import urljoin
from bs4 import BeautifulSoup
import time
import json
import os
import re

#from selenium import webdriver
#from selenium.webdriver.chrome.options import Options


from requests_toolbelt.adapters.source import SourceAddressAdapter

import traceback


_DEFAULT_BEAUTIFULSOUP_PARSER = "html5lib"

_CHROME_DESKTOP_USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.94 Safari/537.36'

_USER_AGENT_LIST = [
    _CHROME_DESKTOP_USER_AGENT,
]

# ブロック対策
_MAX_TRIAL_REQUESTS = 3
_WAIT_TIME_BETWEEN_REQUESTS = 1

class Response(object):
    def __init__(self):
        self.text = ''
    
class MercariItemScraper(object):

    
    def __init__(self, ipaddress=None):
        self.session = requests.session()
        #self.session = HTMLSession() #requests.session()
        if (ipaddress):
            self.session.mount('http://', SourceAddressAdapter(ipaddress))
            self.session.mount('https://', SourceAddressAdapter(ipaddress))
        self.headers = {
                    'Host': 'item.mercari.com',
                    'User-Agent': _USER_AGENT_LIST[0],
                    'Accept': 'text/html,application/',
                    'Accept-Encoding': 'deflate',
                    'Accept-Language': 'ja,en-US;q=0.9,en;q=0.8',
                    }
        self.base_url = 'https://item.mercari.com',
        self.result = []
        self.proxies = {'http': 'socks5://127.0.0.1:9050','https': 'socks5://127.0.0.1:9050'}
        self.tor = False
    
    def get_cookies(self):
        return  json.dumps(self.session.cookies.get_dict())

    def set_cookies(self, cookies):
        self.session.cookies.update(json.loads(cookies))

    # データ取得
    def _get(self, url):
        headers = {
            'User-Agent': 'My User Agent 1.0',
            'From': 'youremail@domain.com'  # This is another valid field
        }
        time.sleep(3)
        #return requests.get(url, headers=headers)
        #return self.session.get(url, headers=self.headers, timeout=5)
        return self.session.get(url, headers=self.headers)
        '''
        with open("/var/www/richs/scraper/data/mercari/robot.chk.htm") as f:
            text = f.read()
            f.close()
            res = Response()
            res.text = text
            return res
        '''
        
    # データ取得
    def _get_tor(self, url):
        headers = {
            'User-Agent': 'My User Agent 1.0',
            'From': 'youremail@domain.com'  # This is another valid field
        }
        time.sleep(3)
        return requests.get(url, headers=headers)
        # return self.session.get(url,  proxies=self.proxies, timeout=15)
    
    # 有効なページであるか判定する。TODO
    def _check_page(self, html_content):
        if "g-recaptcha login-captcha" in html_content:
            #print('validation err')
            # Torを無効にする
            #self.tor = True
            valid_page = False
        else:
            #print('validaton ok')
            valid_page = True
        return valid_page

    # ヘッダ更新 TODO;入力チェック   
    def _update_headers(self, search_url):
        self.base_url = "https://" + \
            search_url.split("://")[1].split("/")[0] + "/"
        #self.headers['Host'] = self.base_url.split("://")[1].split("/")[0]


    # TOR利用有無を取得
    def get_tor(self, tor):        
        return self.tor

    # TOR利用有無を設定
    def set_tor(self, tor):        
        self.tor = tor

    # 商品情報取得
    def get_products(self, url):
        item_id = url.split('/')[-2]
        self.result.clear()
        res = requests.get('http://localhost:1234/mercari/item/' + item_id)
        if (res.status_code != 200):
            return self.result
        res = res.json()
        if (not res['status']):
            return self.result
        item = res['item']
        # images
        images = []
        for photo in item['photos']:
            images.append(photo['url'].replace('/webp/', '/orig/'))
        # rating
        rate_good = item['seller']['ratings']['good']
        rate_unknown = item['seller']['ratings']['normal']
        rate_bad = item['seller']['ratings']['bad']
        rate_all = rate_good - rate_bad
        try:
            rate_percent = round(float(rate_good * 100) / float(rate_good + rate_bad), 1)
        except Exception:
            rate_percent=0.0

        product_dict = {}
        product_dict['url'] = url
        product_dict['item_id'] = item_id
        product_dict['title'] = item['name']
        product_dict['images'] = images
        product_dict['price'] = item['price']
        product_dict['like'] = item['num_likes']
        product_dict['rate'] =  str(rate_all) + ":" + str(rate_good) + ":" + str(rate_bad)
        product_dict['rate_all'] = rate_all
        product_dict['rate_good'] = rate_good
        product_dict['rate_unknown'] = rate_unknown
        product_dict['rate_bad'] = rate_bad
        product_dict['rate_percent'] = rate_percent
        product_dict['seller'] = str(item['seller']['id'])
        product_dict['seller_name'] = item['seller']['name']
        product_dict['condition'] = item['item_condition']['name']
        product_dict['fulfillment_latency'] = item['shipping_duration']['max_days']
        product_dict['sold'] = 'True' if item['status'] == 'sold_out'  else 'False'
        product_dict['item_status'] = item['status']
        product_dict['delivery_from'] = item.get('shipping_from_area', {}).get('name', '')

        self.result.append(product_dict)            
    
        return self.result

    def _get_products(self, url):    
        
        # ヘッダ情報更新
        self._update_headers(url)
        self.result.clear()

        trials = 0
        res = None
        valid_page = False
        while trials < _MAX_TRIAL_REQUESTS:
            trials += 1
            try:
                if (self.tor):
                    res = self._get_tor(url)
                else:
                    res = self._get(url)
                valid_page = self._check_page(res.text)
            except Exception as e:
                print(traceback.format_exc())
                # To counter the "SSLError bad handshake" exception
                valid_page = False
                pass
            if valid_page:
                break
            else:
                # TODO:UA変更
                time.sleep(_WAIT_TIME_BETWEEN_REQUESTS)

        # ページ
        if (valid_page == False):
            return self.result

        soup = BeautifulSoup(res.text, _DEFAULT_BEAUTIFULSOUP_PARSER) 

        # 製品情報抽出
        
        title=''
        seller_id=''
        seller_id_name=''
        rate_all = 0
        rate_good = 0
        rate_unknown = 0
        rate_bad = 0
        rate_percent=0.0
        price = 0
        like = 0
        condition=''
        fulfillment_latency=''
        images = []
        sold='False'

        item_id = url.split('/')[-2]
        
        tmp = soup.select('section.item-box-container')
        
        if (len(tmp) == 0):
            # 商品ページが存在しない場合
            return self.result

        if (len(tmp) > 0):
            item_box = tmp[0]

            tmp = item_box.select('h1.item-name')
            if (len(tmp) == 0):
                # 商品ページが存在しない場合
                return self.result

            if (len(tmp) > 0):
                title = tmp[0].text
        
            tmp = item_box.select('div.item-sold-out-badge')
            if (len(tmp) > 0):
                sold = 'True'

            table = item_box.select('table.item-detail-table > tbody > tr')
            if (len(table) > 0):
                a = table[0].find('a')
                seller_id = a.get('href').split('/')[-2]
                seller_id_name =  a.text
                # 評価の取得
                ratings = table[0].select('div.item-user-ratings')
                if (len(ratings) > 0):
                    rate_good = int(ratings[0].find('span').text)
                    rate_unknown = int(ratings[1].find('span').text)
                    rate_bad = int(ratings[2].find('span').text)
                    rate_all = rate_good - rate_bad
                    try:
                        rate_percent = round(float(rate_good * 100) / float(rate_good + rate_bad) ,1)
                    except Exception:
                        pass

                # コンディション
                for i, tr in enumerate(table):
                    name = tr.find('th').text
                    if (name == '商品の状態'):
                        condition=tr.find('td').text
                    elif (name == '発送日の目安'):
                        fulfillment_latency=tr.find('td').text
                        lists=re.findall(r'([0-9]+)', fulfillment_latency)
                        fulfillment_latency=lists[-1]
                    
        
            tmp = item_box.select('div.item-price-box > span.item-price')
            if (len(tmp) > 0):
                price = tmp[0].text.replace('¥','').replace(',','').strip()
        
            tmp = item_box.select('div.item-button-container')
            if (len(tmp) > 0):
                like = tmp[0].select('span')[1].text


            tmp = item_box.select('div.owl-item-inner > img')
            if (len(tmp) > 0):
                for img in tmp:
                    image = img.get('data-src')
                    images.append(image)
        
        product_dict = {}
        product_dict['url'] = url
        product_dict['item_id'] = item_id
        product_dict['title'] = title
        product_dict['images'] = images
        product_dict['price'] = price            
        product_dict['like'] = like
        product_dict['rate'] =  str(rate_all) + ":" + str(rate_good) + ":" + str(rate_bad)
        product_dict['rate_all'] = rate_all
        product_dict['rate_good'] = rate_good
        product_dict['rate_unknown'] = rate_unknown
        product_dict['rate_bad'] = rate_bad
        product_dict['rate_percent'] = rate_percent
        product_dict['seller'] = seller_id
        product_dict['seller_name'] = seller_id_name
        product_dict['condition'] = condition
        product_dict['fulfillment_latency'] = fulfillment_latency
        product_dict['sold'] = sold

        self.result.append(product_dict)            
    
        return self.result

    # 画像をダウンロードする
    def _download_image(self,url, timeout = 10):

        trials = 0
        while trials < _MAX_TRIAL_REQUESTS:
            trials += 1

            # ヘッダ情報更新
            self._update_headers(url)
            headers = {
                'User-Agent': 'My User Agent 1.0',
                'From': 'youremail@domain.com'  # This is another valid field
            }
            time.sleep(3)
            response = requests.get(url, headers=headers)
            # response = self.session.get(url,  allow_redirects=False, timeout=timeout)
            if response.status_code != 200:
                #print(response.status_code)
                time.sleep(_WAIT_TIME_BETWEEN_REQUESTS)
                continue
                
            content_type = response.headers["content-type"]
            if 'image' not in content_type:
                #print(content_type)            
                time.sleep(_WAIT_TIME_BETWEEN_REQUESTS)
                continue
            
            # 取得結果チェック
            return response.content
        
        # TODO Exception
        print('画像取得エラー: MercariItemScraper.py')
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
        self._save_image(fullpath, image)
        return filename

'''
c = MercariItemScraper('163.43.104.91')
x=c.get_products("https://item.mercari.com/jp/m81733053181/")
print(x)
item=x[0]
images=item['images']
for i, image in enumerate(images):
    c.save_image(image, '/tmp', str(i))
'''


