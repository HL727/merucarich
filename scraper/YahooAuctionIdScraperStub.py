# -*- coding: utf-8 -*-

import requests
from urllib.parse import urljoin
from bs4 import BeautifulSoup
import time

import json
import unittest
from unittest import mock

_DEFAULT_BEAUTIFULSOUP_PARSER = "html5lib"

_CHROME_DESKTOP_USER_AGENT = 'Mozilla/5.0 (Macintosh; \
Intel Mac OS X 10_13_5) AppleWebKit/537.36 (KHTML, like Gecko) \
Chrome/67.0.3396.79 Safari/537.36'

_USER_AGENT_LIST = [
    _CHROME_DESKTOP_USER_AGENT,
]

# ブロック対策
_MAX_TRIAL_REQUESTS = 1
_WAIT_TIME_BETWEEN_REQUESTS = 1

class YahooAuctionIdScraperStub(object):

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
        with open("/root/richs/scraper/data/auciton_id.htm") as f:
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

         

    # 価格情報から余分な情報を除く
    def _priceTrim1(self, price):
        return price.replace('送料無料', '').replace('1円開始', '').replace('Ｔポイント', '').replace('最低落札', '').replace('最低落札', '').replace('かんたん決済', '').replace('コンビニ受取', '').replace('円', '').replace(',', '').strip()

    def _priceTrim2(self, price):
        return price.replace('値下げ交渉あり', '').replace('かんたん決済', '').replace('コンビニ受取', '').replace('円', '').replace(',', '').replace('－', '').strip()

    
    # タイトル
    def _get_title(self, soup):
        tmp = soup.find('div', class_='ProductTitle')
        if tmp == None:
            return ''
        else:
            return tmp.select('div > h1')[0].text.strip()
    
    # 価格情報取得共通メソッド
    def _get_price_base(self, soup):
        tmp  = soup.select('dl > dd.Price__value')[0]
        v1 = tmp.contents[0]
        v2 = tmp.select('span')[0].text.strip()
        
        v1 = v1.replace(',', '').replace('円','').strip()
        v2 = v2.replace(',', '').replace('円','').replace('（','').replace('）','').replace('税込','').replace('税','').strip()
        #print(v1)
        #print(v2)
        if int(v1) > int(v2):
            return v1
        else:
            return v2

    # 現在価格取得
    def _get_current_price(self, soup):
        tmp  = soup.find('div', class_='Price Price--current')
        if tmp == None:
            return ''
        else:
            return self._get_price_base(tmp)
        
    # 即決価格
    def _get_bid_or_buy(self, soup):
        tmp  = soup.find('div', class_='Price Price--buynow')
        if tmp == None:
            return ''
        else:
            return self._get_price_base(tmp)

    # 画像情報取得
    def _get_images(self, soup):
        images = []
        lis =soup.select('div.ProductImage > div > ul > li')
        for li in lis:
            img = li.select('div > img')[0].get('src')
            images.append(img)
        return images
        
    def _get_seller(self,soup):
        return soup.select('span.Seller__name > a')[0].text.strip()


    def _get_rate_all(self,soup):
        try:
            return str(float(soup.select('span.Seller__ratingGood > a')[0].text.strip().replace('%', '')))
        except Exception:
            return '0.0'
            pass        
        

    def _get_rate_percent(self,soup):
        try:
            return str(int(soup.select('span.Seller__ratingSum > a')[0].text.strip()))
        except Exception:
            return '0'
            pass
        

        
    # 商品情報取得
    def get_products(self, search_url):    
        
        # ヘッダ情報更新
        self._update_headers(search_url)

        trials = 0
        text=""
        while trials < _MAX_TRIAL_REQUESTS:
            trials += 1
            try:
                text = self._get(search_url)
                valid_page = self._check_page(text)
            except Exception as e:
                print(e)
                valid_page = False
                pass
            if valid_page:
                break
            else:
                time.sleep(_WAIT_TIME_BETWEEN_REQUESTS)

        self.page_index += 1                
        self.last_html_page = text
        
        soup = BeautifulSoup(text, _DEFAULT_BEAUTIFULSOUP_PARSER)    

        result = {}
    
        # タイトル取得
        title = self._get_title(soup)

        if title == '':
            return self.result

        # 現在価格
        current_price = self._get_current_price(soup)
        # 即決価格
        bid_or_buy  = self._get_bid_or_buy(soup)
        # 画像
        images = self._get_images(soup)
        # セーラ
        seller = self._get_seller(soup)
        # 総合評価
        rate_all=self._get_rate_all(soup)
        # 良い評価パーセント
        rate_percent=self._get_rate_percent(soup)

        
        product_dict = {}
        product_dict['auction_id'] = search_url.split('/')[-1] # TODO
        product_dict['title'] = title
        product_dict['seller'] = seller
        product_dict['current_price'] = current_price
        product_dict['bid_or_buy'] = bid_or_buy
        product_dict['url'] = search_url
        product_dict['images'] = images
        #product_dict['bids'] = bids
        product_dict['rate_all'] = rate_all
        product_dict['rate_percent'] = rate_percent
        self.result.append(product_dict)            

        print(title)                
        print(current_price)
        print(bid_or_buy)
        for img in images:
            print(img)
        print(seller)
        print(rate_all)
        print(rate_percent)
        return self.result

'''
c = YahooAuctionIdScraperStub()
x=c.get_products(search_url="https://www.amazon.co.jp/s/ref=nb_sb_noss?__mk_ja_JP=%E3%82%AB%E3%82%BF%E3%82%AB%E3%83%8A&url=search-alias%3Dstripbooks&field-keywords=%E3%81%9B%E3%81%A9%E3%82%8A")
print(x)
'''
