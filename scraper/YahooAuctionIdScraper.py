# -*- coding: utf-8 -*-

import requests
import os
from urllib.parse import urljoin
from bs4 import BeautifulSoup
import time
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

class YahooAuctionIdScraper(object):

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

         

    # 価格情報から余分な情報を除く
    def _priceTrim1(self, price):
        return price.replace('送料無料', '').replace('1円開始', '').replace('Ｔポイント', '').replace('最低落札', '').replace('最低落札', '').replace('かんたん決済', '').replace('コンビニ受取', '').replace('円', '').replace(',', '').strip()

    def _priceTrim2(self, price):
        return price.replace('値下げ交渉あり', '').replace('かんたん決済', '').replace('コンビニ受取', '').replace('円', '').replace(',', '').replace('－', '').strip()

    
    def _is_closed(self, soup):
        ''' オークションが終了しているか否か '''
        closed = soup.select('div.ClosedHeader')
        return len(closed) > 0
        

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
        v1 = v1.replace(',', '').replace('円','').strip()

        v2 = '0'
        span = tmp.select('span')
        if (len(span) >0 ):
            v2 = tmp.select('span')[0].text.strip()
            v2 = v2.replace(',', '').replace('円','').replace('（','').replace('）','').replace('税込','').replace('税','').strip()

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
        lis =soup.select('div.ProductImage > div.ProductImage__body > ul.ProductImage__images > li')
        for li in lis:
            img = li.select('div > img')[0].get('src')
            images.append(img)
        return images
        
    def _get_seller(self,soup):
        return soup.select('span.Seller__name > a')[0].text.strip()
    

    def _get_rate_all(self,soup):
        try:
            return str(int(soup.select('span.Seller__ratingSum > a')[0].text.strip()))
        except Exception:
            return '0'
            pass

    def _get_rate_percent(self,soup):
        try:
            return str(int(float(soup.select('span.Seller__ratingGood > a')[0].text.strip().replace('%', ''))))
        except Exception:
            return '0'
            pass        
            

    def _get_condition(self,soup):
        #tmp = soup.select('dd.ProductDetail__description') changed on 2019/04/20
        tmp = soup.find_all("th", class_="ProductTable__th", string=re.compile('状態'))[0].parent.select('td.ProductTable__td')
        if (len(tmp) > 0):
            text = tmp[0].text.replace('：', '').strip()
            if text.find('（') > -1:
                lists=re.findall(r'（.+）', text)
                if (len(lists) > 0):
                    text = text.replace(lists[0], '').replace('（', '').replace('）', '')
                    return text
            else:
                return text
        return 'その他'

    def _get_delivery_from(self, soup):
        ''' 発送元を取得 '''
        shippings = soup.select('div.ProductProcedure--shipping')
        for shipping in shippings:
            for tag in shipping.select('li.ProductProcedure__item'):
                m = re.search('発送元：(.+)$', tag.text)
                if m is None:
                    continue
                return m.group(1)
        return ''

    def _get_fulfillment_latency(self,soup):
        tmp = soup.select('#ProductProcedures')
        if (len(tmp)):
            for tmp in  tmp[0].select('li.ProductProcedure__item'):
                text = tmp.text
                if (text.count('発送日までの日数') > 0):
                    lists = re.findall(r'([0-9]+)', text)
                    if (len(lists) > 0):
                        return lists[-1]
        return ''
    
    # 商品情報取得
    def get_products(self, search_url, sleep_seconds=3):    
        
        self.result.clear()


        # ヘッダ情報更新
        self._update_headers(search_url)

        trials = 0
        text=""
        while trials < _MAX_TRIAL_REQUESTS:
            trials += 1
            try:
                res = self._get(search_url, sleep_seconds=sleep_seconds)
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
        self.last_html_page = res.text
        
        soup = BeautifulSoup(res.text, _DEFAULT_BEAUTIFULSOUP_PARSER)    

        result = {}
    
        # タイトル取得
        title = self._get_title(soup)

        if title == '':
            # タイトルが取れない場合は終了しているか無効なアイテム
            return self.result

        is_closed = self._is_closed(soup)
        if is_closed:
            # オークションが終了している場合は空の結果を返す (仕様)
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
        # コンディション
        condition=self._get_condition(soup)
        # 配送元
        delivery_from = self._get_delivery_from(soup)
        # リードタイム
        fulfillment_latency=self._get_fulfillment_latency(soup)
        

        product_dict = {}
        product_dict['auction_id'] = search_url.split('/')[-1] # TODO
        product_dict['title'] = title
        product_dict['seller'] = seller
        product_dict['current_price'] = current_price
        product_dict['bid_or_buy'] = bid_or_buy
        product_dict['url'] = search_url
        product_dict['images'] = images
        #product_dict['bids'] = bids
        product_dict['condition'] = condition
        product_dict['delivery_from'] = delivery_from
        product_dict['fulfillment_latency'] = fulfillment_latency
        product_dict['rate_percent'] = rate_percent

        self.result.append(product_dict)            

        '''
        print(title)                
        print(current_price)
        print(bid_or_buy)
        for img in images:
            print(img)
        print(seller)
        print(rate_all)
        print(rate_percent)
        '''
        
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

    # 画像のファイル名を決める
    def _make_filename(self, base_dir, number, url):
        tmp = url
        while tmp.find('&') > -1:
            # 後ろからURLパラメータを消していく。(現在のYahooのURL仕様に合わせて作成)
            remove_string = '&' +tmp.split('&')[-1]
            tmp = tmp.replace(remove_string, '')

        ext = os.path.splitext(tmp)[1] # 拡張子を取得
        if '?' in ext:
            ext = ext.split('?')[-2]
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
c = YahooAuctionIdScraper()
x=c.get_products('https://page.auctions.yahoo.co.jp/jp/auction/j538204181')
print(x)
'''

