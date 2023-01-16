# -*- coding: utf-8 -*-

import requests
from requests_html import HTMLSession
from urllib.parse import urljoin
from bs4 import BeautifulSoup
import time
import json
import os
import urllib.request
from urllib.parse import urlparse, parse_qs, urlencode
import traceback

from requests_toolbelt.adapters.source import SourceAddressAdapter

import logging
logging.basicConfig(filename='/var/www/richs/scraper/mercari.log', format='%(asctime)s %(levelname)s:%(message)s', level=logging.DEBUG)

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
_MAX_TRIAL_REQUESTS = 3
_WAIT_TIME_BETWEEN_REQUESTS = 1

class Response(object):
    def __init__(self):
        self.text = ''

class MercariSearchScraper(object):


    def __init__(self, ipaddress=None):
#         logging.debug('IP %s', ipaddress)
        self.session = requests.session()
        #self.session = HTMLSession() #requests.session()
        if (ipaddress):
            self.session.mount('http://', SourceAddressAdapter(ipaddress))
            self.session.mount('https://', SourceAddressAdapter(ipaddress))
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
        self.page_index = 0
        self.base_url = 'https://www.mercari.com'
        self.product_size = 0
        self.url_next_page = ''
        self.url_prev_page = ''
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
        # return requests.get(url, headers=headers)
        # return self.session.get(url, timeout=5)
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
        # return self.session.get(url, proxies=self.proxies, timeout=15)

    # TOR利用有無を取得
    def get_tor(self, tor):        
        return self.tor

    # TOR利用有無を設定
    def set_tor(self, tor):        
        self.tor = tor

    # 有効なページであるか判定する。TODO
    def _check_page(self, html_content):
        if "g-recaptcha login-captcha" in html_content:
            #print('validation err')
            # Tor無効
            #self.tor = True
            valid_page = False
        else:
            #print('validaton ok')
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


   # アクセスチェックを実施
    def check_access(self, search_url, max_trial=3):
        # ヘッダ情報更新
        qs = urlparse(search_url).query
        last_raised = None
        completed = False
        for idx in range(max_trial):
            try:
                res = requests.get('http://localhost:1234/mercari/search?' + qs)
                completed = True
                break
            except Exception as e:
                last_raised = e

        if not completed and last_raised is not None:
            return (False, 'ページのアクセス時に例外が発生しました。 {}'.format(last_raised))
        return (True, res.text)
 

    # 商品情報取得
    def get_products(self, search_url):
        self.result.clear()
        self.url_prev_page = ''
        self.url_next_page = ''
        qs = urlparse(search_url).query
        res = requests.get('http://localhost:1234/mercari/search?' + qs)
        if (res.status_code != 200):
            return self.result
        res = res.json()
        if (not res['status']):
            return self.result
        qs = parse_qs(qs)
        cur_page = qs.setdefault('page', ['0'])
        cur_page = int(cur_page[0])
        
        if res['items'].get('next', None):
            qs['page'] = cur_page + 1
            self.url_next_page = 'https://www.mercari.com/jp/search/?' + urlencode(qs, doseq=True)
        if cur_page > 0:
            qs['page'] = cur_page - 1
            self.url_prev_page = 'https://www.mercari.com/jp/search/?' + urlencode(qs, doseq=True)
        for item in res['items']['data']:
            images = []
            for img in item['thumbnails']:
                images.append(img.replace('/c!/w=240,f=webp/thumb/', '/item/detail/orig/'))
            product_dict = {}
            product_dict['item_id'] = item['id']
            product_dict['url'] = 'https://item.mercari.com/jp/' + item['id']
            product_dict['seller'] = str(item.get('seller', {}).get('id'))
            product_dict['title'] = item['name']
            product_dict['images'] = images
            product_dict['price'] = item['price']   
            product_dict['like'] = item['num_likes']
            
            self.result.append(product_dict)

        return self.result

    def _get_products(self, search_url):    
        
        # ヘッダ情報更新
        self._update_headers(search_url)
        self.result.clear()
        self.url_prev_page = ''
        self.url_next_page = ''

        trials = 0
        res = None
        valid_page = False
        while trials < _MAX_TRIAL_REQUESTS:
            trials += 1
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
                # TODO:UA変更
                time.sleep(_WAIT_TIME_BETWEEN_REQUESTS)

        # ページチェック
        if (valid_page == False):
            return self.result

        self.page_index += 1                

        soup = BeautifulSoup(res.text, _DEFAULT_BEAUTIFULSOUP_PARSER)    

        result_number = soup.select_one('.search-result-number')
        print('result_number', result_number)
        if result_number is None:
          return self.result

        # 対応するCSSを探す
        for css_selector_dict in _CSS_SELECTOR_LIST:
            css_selector = css_selector_dict.get("product", "")
            products = soup.select(css_selector)
            if len(products) >= 1:
                break


        # 検索結果チェック
        tmp=soup.select('h2.search-result-head')
        if (len(tmp) > 0):
            result=tmp[0].text.replace('検索結果','').replace('件','').replace(' ','').replace('\n','')
            if (result == '0'):
                return self.result

        for product in products: 
            url=product.select('a')[0].get('href')

            tmp=product.select('img')[0]
            title=tmp.get('alt')
            image=tmp.get('data-src')
            images = []
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
            # response = self.session.get(url, allow_redirects=False, timeout=timeout)
            if response.status_code != 200:
                print(response.status_code)
                time.sleep(_WAIT_TIME_BETWEEN_REQUESTS)
                continue
                
            content_type = response.headers["content-type"]
            if 'image' not in content_type:
                print(content_type)            
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
c = MercariSearchScraper('163.43.104.91')
x=c.get_products(search_url="https://www.mercari.com/jp/search/?keyword=%E6%99%82%E8%A8%88")
print(x)
print(c.getNextPageURL())
print(c.getPrevPageURL())



item=x[0]
images=item['images']
for i, image in enumerate(images):
    c.save_image(image, '/tmp', str(i))
'''
