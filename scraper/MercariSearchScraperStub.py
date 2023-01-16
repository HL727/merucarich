# -*- coding: utf-8 -*-

import requests
from urllib.parse import urljoin
from bs4 import BeautifulSoup
import time
import json

import unittest
from unittest import mock

_DEFAULT_BEAUTIFULSOUP_PARSER = "html5lib"

_CHROME_DESKTOP_USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.94 Safari/537.36'

_USER_AGENT_LIST = [
    _CHROME_DESKTOP_USER_AGENT,
]

_CSS_SELECTORS_DESKTOP = {
    "product": "div.items-box-content.clearfix > section.items-box",
}




_CSS_SELECTOR_LIST = [
                        _CSS_SELECTORS_DESKTOP
]

# ブロック対策
_MAX_TRIAL_REQUESTS = 1
_WAIT_TIME_BETWEEN_REQUESTS = 1

class MercariSearchScraperStub(object):

    
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
        with open("/var/www/richs/scraper/data/mercari/list.htm") as f:
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
            search_url.split("://")[1].split("/")[0] 
        #self.headers['Host'] = self.base_url.split("://")[1].split("/")[0]

        
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


    # 次のページを取得
    def getNextPageURL(self):
        return self.url_next_page

    # 前のページを取得
    def getPrevPageURL(self):
        return self.url_prev_page


    
    # 商品情報取得
    def get_products(self, search_url):    
        
        # ヘッダ情報更新
        self._update_headers(search_url)

        self.result.clear()
        self.url_prev_page = ''
        self.url_next_page = ''

        trials = 0
        text=""
        while trials < _MAX_TRIAL_REQUESTS:
            trials += 1
            try:
                text = self._get(search_url)
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

        # 対応するCSSを探す
        for css_selector_dict in _CSS_SELECTOR_LIST:
            css_selector = css_selector_dict.get("product", "")
            products = soup.select(css_selector)
            if len(products) >= 1:
                break

        # 検索結果チェック
        tmp=soup.select('h2.search-result-head')
        if (len(tmp) >0 ):
            result=tmp[0].text.replace('検索結果','').replace('件','').replace(' ','').replace('\n','')
            if (result == '0'):
                return self.result

        for product in products: 
            url=product.select('a')[0].get('href')

            tmp=product.select('img')[0]
            title=tmp.get('alt')
            image=tmp.get('data-src')
            images=[]
            images.append(image)

            tmp=product.select('div.items-box-body')[0] 
            price = tmp.select('div.items-box-price')[0].text.replace('¥','').replace(',','').strip()
            tmp =  tmp.select('div.items-box-likes')
            like = 0
            if(len(tmp) > 0):
                like=tmp[0].select('span')[0].text

            item_id=url.split('/')[-2]
            
            '''
            print(item_id)
            print(url)
            print(title)
            print(image)
            print(price)
            print(like)
            '''

            product_dict = {}
            product_dict['item_id'] = item_id
            product_dict['url'] = url
            product_dict['title'] = title
            product_dict['images'] = images
            product_dict['price'] = price            
            product_dict['like'] = like
            
            self.result.append(product_dict)            
                
        # 次のページ
        tmp = soup.select('li.pager-next.visible-pc > ul > li.pager-cell > a')
        if tmp != None and len(tmp) > 0:
            self.url_next_page = self.base_url + tmp[0].get('href')

        tmp = soup.select('li.pager-prev.visible-pc > ul > li.pager-cell > a')    
        if tmp != None and len(tmp) > 0:
            self.url_prev_page = self.base_url + tmp[0].get('href')

        return self.result



   
#c = MercariSearchScraperStub()
#x=c.get_products(search_url="https://www.mercari.com/jp/search/?keyword=%E6%99%82%E8%A8%88")
#print(x)
#print(c.getNextPageURL())
#print(c.getPrevPageURL())

