# -*- coding: utf-8 -*-

import requests
from urllib.parse import urljoin
from bs4 import BeautifulSoup
import time
import re
import json
import unittest
from unittest import mock

from requests_toolbelt.adapters.source import SourceAddressAdapter


_DEFAULT_BEAUTIFULSOUP_PARSER = "html5lib"

_CHROME_DESKTOP_USER_AGENT = 'Mozilla/5.0 (Macintosh; \
Intel Mac OS X 10_13_5) AppleWebKit/537.36 (KHTML, like Gecko) \
Chrome/67.0.3396.79 Safari/537.36'

_USER_AGENT_LIST = [
    _CHROME_DESKTOP_USER_AGENT,
]

# ブロック対策
_MAX_TRIAL_REQUESTS = 3
_WAIT_TIME_BETWEEN_REQUESTS = 1

class YahooAuctionSellerRatingScraper(object):

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
        self.result = {}

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

    # レーティング情報
    def get_ratings(self, auction_id, sleep_seconds=3):    

        self.result.clear()

        search_url = 'https://auctions.yahoo.co.jp/jp/show/rating?userID=' + auction_id

        print(search_url)
        
        # ヘッダ情報更新
        self._update_headers(search_url)

        trials = 0
        text = ""
        while trials < _MAX_TRIAL_REQUESTS:
            trials += 1
            try:
                res = self._get(search_url, sleep_seconds=sleep_seconds)
                valid_page = self._check_page(text)
            except Exception as e:
                valid_page = False
                pass
            if valid_page:
                break
            else:
                time.sleep(_WAIT_TIME_BETWEEN_REQUESTS)

        self.page_index += 1                
        self.last_html_page = res.text

        #print(res.text)
        
        soup = BeautifulSoup(res.text, _DEFAULT_BEAUTIFULSOUP_PARSER)    
        
        rate_all=0
        rate_good=0
        rate_unknown=0
        rate_bad=0
        rate_percent=0.0
        tmp = soup.find('table', 'RateDetail')

        try:
            if tmp != None:
                ditail = tmp.select('tbody > tr')[1].text.strip()
                print(ditail)
                #リストに保存
                lists=re.findall(r'([0-9]+)人', ditail)
                rate_good=int(lists[0])
                rate_unknown=int(lists[1])
                rate_bad=int(lists[2])
                rate_all=rate_good - rate_bad
                rate_percent= round(float(rate_good) * 100.0 / float(rate_good + rate_bad),1)
        except Exception as e:
            print(e)
            pass

        self.result['rate_all'] = rate_all
        self.result['rate_good'] = rate_good
        self.result['rate_unknown'] = rate_unknown
        self.result['rate_bad']  = rate_bad
        self.result['rate_percent']  = str(rate_percent)
        


        return self.result

'''
c = YahooAuctionSellerRatingScraper()
x=c.get_ratings(auction_id="dmmyu748")
print(x)
'''
