# -*- coding: utf-8 -*-

import requests
from urllib.parse import urljoin
from bs4 import BeautifulSoup
import time

import json
import os

_DEFAULT_BEAUTIFULSOUP_PARSER = "html5lib"

_CHROME_DESKTOP_USER_AGENT = 'Mozilla/5.0 (Macintosh; \
Intel Mac OS X 10_13_5) AppleWebKit/537.36 (KHTML, like Gecko) \
Chrome/67.0.3396.79 Safari/537.36'

_USER_AGENT_LIST = [
    _CHROME_DESKTOP_USER_AGENT,
]

_CSS_SELECTORS_DESKTOP = {
    "seller": "div#olpOfferListColumn > div > div > div > div.a-row.a-spacing-mini.olpOffer",
    "next_page_url": "ul.a-pagination > li.a-last > a",
}

_CSS_SELECTOR_LIST = [
    _CSS_SELECTORS_DESKTOP
]

# ブロック対策
_MAX_TRIAL_REQUESTS = 1
_WAIT_TIME_BETWEEN_REQUESTS = 1

class AmazonOfferListScraperStub(object):

    def __init__(self):
        self.session = requests.session()
        self.headers = {
            'Host': 'www.amazon.co.jp',
            'User-Agent': _USER_AGENT_LIST[0],
            'Accept': 'text/html,application/xhtml+xml,\
                        application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        }
        self.price_new=-1
        self.price_old=-1
        self.new_count=0
        self.old_count=0
        self.fba=False
        self.prime=False
        self.base_url = 'https://www.amazon.co.jp'

    def get_cookies(self):
        return  json.dumps(self.session.cookies.get_dict())

    def set_cookies(self, cookies):
        self.session.cookies.update(json.loads(cookies))
            
        
    # データ取得
    def _get(self, url):
        #return self.session.get(url, headers=self.headers)
        with open("/var/www/richs/scraper/data/amazon/seller-list.htm") as f:
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


    def getNextPageURL(self, soup, css_selector_dict):
        css_selector = css_selector_dict.get("next_page_url", "")
        url_next_page_soup = soup.select(css_selector)
        if url_next_page_soup:
            return urljoin(self.base_url,url_next_page_soup[0].get('href'))
        return ""


    # アイテム詳細情報取得
    def _get_item(self, soup):
        price = int(soup.select('span.olpOfferPrice')[0].text.replace('￥','').replace(',','').strip())
        condition = soup.select('span.olpCondition')[0].text.replace('￥','').replace(',','').replace(' ','').replace('\n','').strip()
        if (condition.startswith('新品')):
            if (self.price_new == -1 or self.price_new > price):
                self.price_new = price
                self.new_count = self.new_count + 1
        elif (condition.startswith('中古')):
            if (self.price_old == -1 or self.price_old > price):
                self.price_old = price
                self.old_count = self.old_count + 1
        elif (condition.startswith('コレクター商品')):
            if (self.price_old == -1 or self.price_old > price):
                self.price_old = price
                self.old_count = self.old_count + 1




        tmp = soup.select('h3.olpSellerName')[0]
        tmp2 = tmp.select('span > a')
        seller=''
        fba=False
        #FBA
        if(len(tmp2) > 0):
            seller=tmp2[0].get('href').split('seller=')[-1]
            tmp3=soup.select('div.olpBadgeContainer')
            if(len(tmp3) > 0):
                fba=True
                self.fba=True
        else:
            tmp2 = tmp.select('img')
            if (len(tmp2) >0):
                seller=tmp2[0].get('alt')
                if(seller.startswith('Amazon')):
                    fba=True
                    self.fba=True
       
        #プライム
        tmp = soup.select('i.a-icon-prime-jp')
        prime=False
        if (len(tmp) > 0):
            prime=True

        print(str(price) + ',' + condition + ',' +  seller + ',' + str(fba) + ',' + str(prime))

    
    # 商品情報取得
    def load_offers(self, search_url):

        # ヘッダ情報更新
        self._update_headers(search_url)
      
        trials = 0
        text=''
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

        soup = BeautifulSoup(text, _DEFAULT_BEAUTIFULSOUP_PARSER)    

        # 対応するCSSを探す
        for css_selector_dict in _CSS_SELECTOR_LIST:
            css_selector = css_selector_dict.get("seller", "")
            sellers = soup.select(css_selector)
            if len(sellers) >= 1:
                break
       
        # 各セラーの商品情報を取得
        for seller in sellers:
            self._get_item(seller)
        
        # 次のページが存在するか判定する
        next_page= self.getNextPageURL(soup, css_selector_dict)
        if (next_page != None and next_page != ''):
            time.sleep(_WAIT_TIME_BETWEEN_REQUESTS)
            #self.load_offers(next_page)    

    def get_new_count(self):
        self.new_count

    def get_old_count(self):
        self.old_count

    def get_new_price(self):
        return self.price_new

    def get_old_price(self):
        return self.price_old

    def get_fba_price(self):
        return self.fba

    def get_prime(self):
        return self.prime



    # クリア
    def clear(self):
        self.price_new=-1
        self.price_old=-1
        self.new_count=0
        self.old_count=0
        self.fba=False
        self.prime=False





'''
c = AmazonOfferListScraperStub()
x=c.load_offerss('https://dumy?aaa=bbbb')
'''

#print(x)
# 3x3
#c.get_products(search_url="https://www.amazon.co.jp/s?marketplaceID=A1VC38T7YXB528&redirect=true&me=A2VPSJWJUCARY0&merchant=A2VPSJWJUCARY0", max_product_nb=100000)

# 2x2
#c.get_products(search_url="https://www.amazon.co.jp/s/ref=sr_il_ti_merchant-items?me=A2VPSJWJUCARY0&rh=i%3Amerchant-items&ie=UTF8&qid=1536731837&lo=merchant-items", max_product_nb=100000)    
