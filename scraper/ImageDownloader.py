#!/usr/bin/python 
# -*- coding: utf-8 -*-

import os
import time
import logging
import requests
import uuid

from concurrent.futures import ThreadPoolExecutor

from richs_utils import RichsUtils

logger = logging.getLogger(__name__)

class ImageDownloader:
    ''' 
    高速に画像をダウンロードするためのヘルパクラスです。
    一般に画面表示後の画像取得はブラウザで並列して行われるため、
    画像ファイルを並列でダウンロードし、ローカルに保存する仕組みを提供します。
    '''

    VALID_SUFFIXES = ['jpg', 'jpeg', 'png', 'gif']

    def __init__(self, directory, urllist, download_block=10, max_workers=2, headers=None):
        '''
        directory 内に画像ファイルをダウンロードして保存します。
        ファイル名は全て uuid.uuid4() を利用してランダムなものが作成されます。
        downloaded_block で指定したブロック数だけ画像をダウンロードした後、明示的なウェイトを挟みます。
        max_workers はダウンロードに利用するスレッド数です。
        '''
        self.directory = directory
        self.urllist = [ self._to_url_dict(url) for url in urllist ]
        self.download_block = download_block
        self.max_workers = max_workers
        if headers is not None:
            self.headers = headers
        else:
            self.headers = {
                'User-Agent': 'My User Agent 1.0',
                'From': 'youremail@domain.com'
            }
        self.downloaded = {}


    def _to_url_dict(self, url):
        res = { 'url': url, 'suffix': '', 'valid': False, 'filename': ''}
        for suffix in ImageDownloader.VALID_SUFFIXES:
            if suffix in url or suffix.upper() in url:
                res['valid'] = True
                res['suffix'] = suffix
                res['filename'] = '{}.{}'.format(str(uuid.uuid4()), suffix)
                break
        return res


    def _exponential_backoff(self, func, else_value=None, sleeps=[1, 2]):
        sleep_size = len(sleeps)
        for idx in range(sleep_size + 1):
            try:
                res = func()
                return res
            except:
                # 例外時
                pass
            if idx < sleep_size:
                self._wait(sleeps[idx])
        return else_value


    def _download_image(self, url):
        logger.debug('download %s', url)
        response = requests.get(url, headers=self.headers)
        if response.status_code != 200:
            return None

        content_type = response.headers["content-type"]
        if 'image' not in content_type:
            return None

        return response.content


    def _save_image(self, fullpath, content):
        try:
            with open(fullpath, "wb") as fh:
                fh.write(content)
            logger.debug('save image: %s', fullpath)
            return True
        except:
            logger.debug('failed to save image: %s', fullpath)
            return False


    def _wait(self, seconds=1):
        time.sleep(seconds)


    def get(self, url, else_value=None):
        ''' return local image file absolute path '''
        return self.downloaded.get(url, else_value)


    def _download_and_save(self, urlinfo):
        content = self._exponential_backoff(
            lambda: self._download_image(urlinfo['url']))
        if content is None:
            logger.debug('Image download failed: %s', urlinfo['url'])
            return (urlinfo['url'], None)
        fullpath = os.path.join(self.directory, urlinfo['filename'])
        if not self._save_image(fullpath, content):
            return (urlinfo['url'], None)
        return (urlinfo['url'], fullpath)
        

    def downloads(self):
        ''' download and save all url images '''
        self.downloaded = {}
        validurls = [ urlinfo for urlinfo in self.urllist if urlinfo['valid'] ]
        chunks = RichsUtils.chunkof(validurls, self.download_block)
        for chunk in chunks:
            futures = []
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                for urlinfo in chunk:
                    futures.append(executor.submit(self._download_and_save, urlinfo))
            for (url, path) in [ f.result() for f in futures ]:
                if path is None:
                    continue
                self.downloaded[url] = path
            self._wait()


    def removes(self):
        ''' remove all images from local disk '''
        for fullpath in self.downloaded.values():
            try:
                RichsUtils.delete_file_if_exist(fullpath)
            except Exception as e:
                logger.exception(e)


    def __enter__(self):
        '''
        with ImageDownloader('/tmp', ['https://path.to/hoge.png']) as downloader:
            # downloads and saves are completed when run with scope codes
            path = downloader.get('https://path.to/hoge.png')
            ...
        # remove all local images when break with scope automatically
        '''
        self.downloads()
        return self


    def __exit__(self, exception_type, exception_value, traceback):
        self.removes()


