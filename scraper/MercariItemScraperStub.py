# -*- coding: utf-8 -*-

import requests
from urllib.parse import urljoin
from bs4 import BeautifulSoup
import time
import json
import re


_DEFAULT_BEAUTIFULSOUP_PARSER = "html5lib"

_CHROME_DESKTOP_USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.94 Safari/537.36'

_USER_AGENT_LIST = [
    _CHROME_DESKTOP_USER_AGENT,
]

# ブロック対策
_MAX_TRIAL_REQUESTS = 1
_WAIT_TIME_BETWEEN_REQUESTS = 1

class MercariItemScraperStub(object):

    
    def __init__(self):
        self.session = requests.session()
        self.headers = {
                    'Host': 'www.mercari.com',
                    'Upgrade-Insecure-Requests': '1',
                    'Connection': 'keep-alive', 
                    'DNT': '1',
                    'User-Agent': _USER_AGENT_LIST[0],
                    'Accept': 'text/html,application/',
                    'Accept-Encoding': 'deflate',
                    'Accept-Language': 'ja,en-US;q=0.9,en;q=0.8',
                    }
        self.product_dict_list = []
        self.page_index = 0
        self.base_url = 'https://www.mercari.com'
        self.product_size = 0
        self.url_next_page = ''
        self.url_prev_page = ''
        self.result = []

    
    def get_cookies(self):
        return  json.dumps(self.session.cookies.get_dict())

    def set_cookies(self, cookies):
        self.session.cookies.update(json.loads(cookies))
        
    # データ取得
    def _get(self, url):
        #return self.session.get(url, headers=self.headers)
        with open("/var/www/richs/scraper/data/mercari/item_2.htm") as f:
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
        #self.headers['Host'] = self.base_url.split("://")[1].split("/")[0]

    
    # 商品情報取得
    def get_products(self, url):    
        
        # ヘッダ情報更新
        self._update_headers(url)

        self.result.clear()

        trials = 0
        text=""
        while trials < _MAX_TRIAL_REQUESTS:
            trials += 1
            try:
                text = self._get(url)
                valid_page = self._check_page(text)
            except Exception as e:
                print(e)
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
        #print(text)
        soup = BeautifulSoup(text, _DEFAULT_BEAUTIFULSOUP_PARSER)    

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

        tmp = soup.select('h1.item-name')
        if (len(tmp) > 0):
            title = tmp[0].text
            
        table = soup.select('table.item-detail-table > tbody > tr')
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
                    
        
        tmp = soup.select('div.item-price-box > span.item-price')
        if (len(tmp) > 0):
            price = tmp[0].text.replace('¥','').replace(',','').strip()
        
        tmp = soup.select('div.item-button-container')
        if (len(tmp) > 0):
            like = tmp[0].select('span')[1].text


        tmp = soup.select('div.owl-item-inner > img')
        if (len(tmp) > 0):
            for img in tmp:
                image = img.get('data-src')
                images.append(image)
        
        item_id = url.split('/')[-2]

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

        self.result.append(product_dict)            
    
        return self.result



'''   
c = MercariItemScraperStub()
x=c.get_products(url="https://www.mercari.com/jp/search/?keyword=%E6%99%82%E8%A8%88")
print(x)
'''
