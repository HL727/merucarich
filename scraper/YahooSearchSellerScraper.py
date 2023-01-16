#!/usr/bin/python 
# -*- coding: utf-8 -*-

import requests
from urllib.parse import urljoin
from bs4 import BeautifulSoup
import time
#import pickle
import os
import json
import re

from requests_toolbelt.adapters.source import SourceAddressAdapter



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

class YahooSearchSellerScraper(object):
    ''' Sellerの出展物を検索する Scraper です '''

    
    def __init__(self, ipaddress=None):
        self.session = requests.session()
        if (ipaddress):
            self.session.mount('http://', SourceAddressAdapter(ipaddress))
            self.session.mount('https://', SourceAddressAdapter(ipaddress))
        self.headers = {
                    'Host': 'auctions.yahoo.co.jp',
                    'User-Agent': _USER_AGENT_LIST[0],
                    'Accept': 'text/html,application/xhtml+xml,\
                        application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                    }
        self.product_dict_list = []
        self.page_index = 0
        self.base_url = 'https://auctions.yahoo.co.jp'
        self.product_size = 0
        self.url_next_page = ''
        self.url_prev_page = ''
        self.result = []

    
    def get_cookies(self):
        return  json.dumps(self.session.cookies.get_dict())

    def set_cookies(self, cookies):
        self.session.cookies.update(json.loads(cookies))
    
    # データ取得
    def _get(self, url, sleep_seconds=3):
        headers = {
            'User-Agent': 'My User Agent 1.0',
            'From': 'youremail@domain.com'  # This is another valid field
        }
        time.sleep(sleep_seconds)
        return requests.get(url, headers=headers)
        # return self.session.get(url, headers=self.headers)

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
    def getNextPageURL(self):
        return self.url_next_page

    # 前のページを取得
    def getPrevPageURL(self):
        return self.url_prev_page


    # 価格情報から余分な情報を除く
    def _priceTrim1(self, price):
        return price.replace('送料無料', '').replace('1円開始', '').replace('Ｔポイント', '').replace('最低落札', '').replace('最低落札', '').replace('かんたん決済', '').replace('コンビニ受取', '').replace('円', '').replace(',', '').strip()

    def _priceTrim2(self, price):
        return price.replace('値下げ交渉あり', '').replace('かんたん決済', '').replace('コンビニ受取', '').replace('円', '').replace(',', '').replace('－', '').strip()
    
    def _priceTrim(self, text, else_value='0'):
        m = re.search('([0-9,]+)円', text)
        if m is None:
            return else_value
        return m.group(1).replace(',', '')

    # アクセスチェックを実施
    def check_access(self, search_url, max_trial=3):
        # ヘッダ情報更新
        self._update_headers(search_url)
        last_raised = None
        completed = False
        for idx in range(max_trial):
            try:
                res = self._get(search_url, sleep_seconds=1)
                valid_page = self._check_page(res.text)
                completed = True
                break
            except Exception as e:
                last_raised = e

        if not completed and last_raised is not None:
            return (False, 'ページのアクセス時に例外が発生しました。 {}'.format(last_raised))
        return (valid_page, res.text)
 

    # 商品情報取得
    def get_products(self, search_url, sleep_seconds=3):    
        

        self.result.clear()


        # ヘッダ情報更新
        self._update_headers(search_url)
        res = None
        trials = 0
        while trials < _MAX_TRIAL_REQUESTS:
            trials += 1
            try:
                res = self._get(search_url, sleep_seconds=sleep_seconds)
                #self.saveCookies()
                valid_page = self._check_page(res.text)
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
        self.last_html_page = res.text

        soup = BeautifulSoup(res.text, _DEFAULT_BEAUTIFULSOUP_PARSER)    
        all_rows = soup.select("table > tbody > tr")
        if len(all_rows) <= 0:
            return self.result

        # 不要なものを省く
        products = []
        for row in all_rows:
            # 子要素に td としてアイテムの各行を持つ
            if len(row.select('td.i')) != 1:
                continue
            products.append(row)

        # 共通項目を取得
        seller = search_url.split('?')[0].split('/')[-1]

        for product in products:
            try:
                title_atag = product.select('td.a1 a')[0]
                url = title_atag.get('href')
                title = title_atag.text.strip()

                img_tag = product.select('td.i img')[0]
                img = img_tag.get('src')

                # 現在価格、即決価格
                currentPrice = self._priceTrim(product.select('td.pr1')[0].text, '')
                bidOrBuy  = self._priceTrim(product.select('td.pr2')[0].text, '')

                # 入札数
                atag_for_bids = product.select('td.bi a')
                if len(atag_for_bids) > 0:
                    bids = atag_for_bids[0].text.strip()
                else:
                    # 入札なし
                    bids = ''

                product_dict = {}
                product_dict['auction_id'] = url.split('/')[-1]
                product_dict['title'] = title
                product_dict['seller'] = seller
                product_dict['current_price'] = currentPrice
                product_dict['bid_or_buy'] = bidOrBuy
                product_dict['url'] = url
                product_dict['images'] = [ img ]
                product_dict['bids'] = bids
                self.result.append(product_dict)            
 
            except Exception as e:
                pass

        # 次のページ
        tmp = soup.find('p', class_='next')
        if tmp != None:
            tmp = tmp.find('a')
            if tmp != None:
                self.url_next_page = soup.select('p.next > a')[0].get('href')

        tmp = soup.find('p', class_='prev')
        if tmp != None:
            tmp = tmp.find('a')
            if tmp != None:
                self.url_prev_page = soup.select('p.prev > a')[0].get('href')

        return self.result                


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

    # 画像のファイル名を決める(暫定実装)
    def _make_filename(self, base_dir, number, url):
        ext = '.jpg'  #os.path.splitext(url)[1] # 拡張子を取得
        #if '?' in ext:
        #    ext = ext.split('?')[-2]
        filename = number + ext        # 番号に拡張子をつけてファイル名にする
        return filename

    # 画像を保存する
    def _save_image(self, fullpath, image):
        #print('fullpath=' +fullpath)
        with open(fullpath, "wb") as fout:
            fout.write(image)

    def save_image(self, url, base_dir, number):
        #print('base_dir=' + base_dir)
        image = self._download_image(url)
        filename =  self._make_filename(base_dir, number, url)
        fullpath = os.path.join(base_dir, filename)
        self._save_image(fullpath, image)
        return filename


