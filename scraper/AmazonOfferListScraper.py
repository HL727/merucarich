# -*- coding: utf-8 -*-

import requests
from urllib.parse import urljoin
from bs4 import BeautifulSoup
import time

import json
import os

from datetime import datetime

import io
from captchabuster import CaptchaBuster
from datetime import datetime


from requests_toolbelt.adapters.source import SourceAddressAdapter

import traceback

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
_MAX_TRIAL_REQUESTS = 5
_MAX_NORMAL_TRIAL_REQUESTS = 3
_WAIT_TIME_BETWEEN_REQUESTS = 1

_MY_USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36'


class AmazonOfferListScraper(object):

    def __init__(self, ipaddress=None):
        self.session = requests.session()
        if (ipaddress):
            self.session.mount('http://', SourceAddressAdapter(ipaddress))
            self.session.mount('https://', SourceAddressAdapter(ipaddress))
        self.headers = {
            'Host': 'www.amazon.co.jp',
            'User-Agent': _MY_USER_AGENT,
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
        self.proxies = {'http': 'socks5://127.0.0.1:9050','https': 'socks5://127.0.0.1:9050'}
        self.tor = False


    def get_cookies(self):
        return  json.dumps(self.session.cookies.get_dict())

    def set_cookies(self, cookies):
        self.session.cookies.update(json.loads(cookies))
            
    # データ取得
    def _get(self, url):
        print('normal get')
        headers = {
            'User-Agent': _MY_USER_AGENT,
            #'From': 'youremail@domain.com'  # This is another valid field
        }
        time.sleep(3)
        return requests.get(url, headers=headers)
        # return self.session.get(url, headers=self.headers, timeout=5)

    # データ取得
    def _get_tor(self, url):
        print('use tor')
        headers = {
            'User-Agent': _MY_USER_AGENT,
            #'From': 'youremail@domain.com'  # This is another valid field
        }
        time.sleep(3)
        return requests.get(url, headers=headers)
        # return self.session.get(url, headers=self.headers, proxies=self.proxies, timeout=15)


    # TOR利用有無を取得
    def get_tor(self, tor):        
        return self.tor

    # TOR利用有無を設定
    def set_tor(self, tor):        
        self.tor = tor

    # 有効なページであるか判定する。TODO
    def _check_page(self, html_content):
        if  "Amazon CAPTCHA" in html_content or "Sign in for the best experience" in html_content: 
            self.tor = True
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

    # 認証
    def _do_captcha(self, org_url, res, timeout, proxies=None):
        base_dir='/tmp'
        # print('_do_captcha')
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
            else:
                res = requests.get(url, headers=self.headers, params=payload, proxies=proxies, timeout=timeout, allow_redirects=True)
        return res    
        

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
            self.prime=True
            prime=True

        print(str(price) + ',' + condition + ',' +  seller + ',' + str(fba) + ',' + str(prime))

    
    # 商品情報取得
    def load_offers(self, search_url):

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
                time.sleep(_WAIT_TIME_BETWEEN_REQUESTS)
                continue
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
                    return self.load_offers(search_url)
                    #break
                time.sleep(_WAIT_TIME_BETWEEN_REQUESTS)

        # ページチェック
        if (valid_page == False):
            print('バリデーションエラー(Offer)')
            print(res.text)
            return

        print(res.text)
        soup = BeautifulSoup(res.text, _DEFAULT_BEAUTIFULSOUP_PARSER)    

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
            self.load_offers(urljoin(self.base_url, next_page))    

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
c = AmazonOfferListScraper()
x=c.load_offers('https://www.amazon.co.jp/gp/offer-listing/B07HM5FWZT/ref=sr_1_3_olp?ie=UTF8&qid=1544468251&sr=8-3&keywords=NO+WAY+MAN+%E5%88%9D%E5%9B%9E%E9%99%90%E5%AE%9A%E7%9B%A4')
'''
