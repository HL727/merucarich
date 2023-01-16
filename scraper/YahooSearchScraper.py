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

_CSS_SELECTORS_DESKTOP = {
    "product": "ul.Products__items > li.Product",
    # "product": "div.AS1m > div > table > tbody > tr",
    "title": "a.s-access-detail-page > h2",
    "rating": "i.a-icon-star > span",
    "review_nb": "div.a-row.a-spacing-none > \
                a.a-size-small.a-link-normal.a-text-normal",
    "url": "div.a-row.a-spacing-mini > div.a-row.a-spacing-none > a['href']",
    "next_page_url": "a#pagnNextLink",
}

_CSS_SELECTOR_LIST = [
                        _CSS_SELECTORS_DESKTOP
]

# ブロック対策
_MAX_TRIAL_REQUESTS = 1
_WAIT_TIME_BETWEEN_REQUESTS = 1

class YahooSearchScraper(object):

    
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
    def get_products(self, search_url, seller_='', sleep_seconds=3):    
        

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

        '''
        with open('load.htm', mode='w') as f:
            f.write(res.text)
        '''
        
        soup = BeautifulSoup(res.text, _DEFAULT_BEAUTIFULSOUP_PARSER)    

        # 対応するCSSを探す
        for css_selector_dict in _CSS_SELECTOR_LIST:
            css_selector = css_selector_dict.get("product", "")
            products = soup.select(css_selector)
            if len(products) >= 1:
                break
            
        for i in range(len(products)):
            # print(i)
            # print(len(products))
            # if products[i].find('td', class_='i') == None:
            #     continue

            # td_i_a = products[i].select('td.i')[0].select('a')[0]
            td_i_a = products[i].select('.Product__titleLink')[0]
            # 商品の詳細URL
            url = td_i_a.get('href')
            # 商品名を取得する。
            title = td_i_a.text.strip()
            # 商品画像のURL
            img = products[i].select('.Product__imageData')[0].get('src')

            # tmp1=products[i].select('td.a1 > div.a1wrp')[0]
            # # 商品名を取得する。
            # title  = tmp1.select('a')[0].text.strip()


            seller = ''
            # if seller_ == '':
            #
            #     # セーラ(TODO:公売の場合は、取得できない。)
            #     if tmp1.find('li', class_="sic3") == None: #公官庁ではない
            #         seller = tmp1.select("a[href*=auctions.yahoo.co.jp/seller]")[0].text.strip()
            #     else:
            #         continue
            #         #seller = ''
            # else:
            #     seller = seller_

            # 販売者の取得
            seller = products[i].select('.Product__seller')[0].text.strip()

                
            # 現在価格
            # currentPrice  = products[i].select('td.pr1')[0].text.strip()
            currentPrice  = products[i].select('span.Product__price > span.u-textRed')[0].text.strip()
            currentPrice = self._priceTrim1(currentPrice)

            # 即決価格
            # bidOrBuy  = products[i].select('td.pr2')[0].text.strip()
            bidOrBuy = products[i].select('span.Product__price')[1].select('span')[1].text.strip()
            bidOrBuy  = self._priceTrim2(bidOrBuy)

            # 入札(TODO: - の時は、SPANで、ある時は、a )
            # tmp  = products[i].select('td.bi')[0]
            bids = products[i].select('.Product__bid')[0].text.strip()
            # bids = "0"
            # if tmp.find('span') == None:
            #     bids = tmp.select('a')[0].text.strip()
                
            # 残り時間
            # endTime  = products[i].select('td.ti')[0].text.strip()

            '''
            print('"' + title + '","' + seller + '","'  + currentPrice  + '","'  + bidOrBuy + '","' + bids)
            print(url)
            print(img)
            print('----')
            '''

            images = []

            images.append(img)
            
            product_dict = {}
            product_dict['auction_id'] = url.split('/')[-1]
            product_dict['title'] = title
            product_dict['seller'] = seller
            product_dict['current_price'] = currentPrice
            product_dict['bid_or_buy'] = bidOrBuy
            product_dict['url'] = url
            product_dict['images'] = images
            product_dict['bids'] = bids
            self.result.append(product_dict)            

            
        # 次のページ
        tmp = soup.find('li', class_='Pager__list--next')
        if tmp != None:
            tmp = tmp.find('a')
            if tmp != None:
                self.url_next_page = tmp.get('href')

        tmp = soup.find('li', class_='Pager__list--prev')
        if tmp != None:
            tmp = tmp.find('a')
            if tmp != None:
                self.url_prev_page = tmp.get('href')

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


'''    
c = YahooSearchScraper()
x=c.get_products(search_url="https://auctions.yahoo.co.jp/seller/rcs_3067650010")

print(c._getNextPageURL())
print(c._getPrevPageURL())
'''
