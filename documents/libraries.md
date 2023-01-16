# 利用している主要ライブラリ

このプロジェクトで利用されている主なライブラリについて説明する。


## Django

https://www.djangoproject.com/

Python の中でも有名な MVT (Model-View-Template) Web フレームワーク。
利用しているのは Django 2.11 系。

※MVTは別の言語でのMVC(Model-View-Controller)と考え方は同じ。

- MVT Model = MVC Model (データ層)
- MVT View = MVC Controller (ロジック層)
- MVT Template = MVC View (画面表示や入出力層)


## Pillow + OpenCV

https://pillow.readthedocs.io/en/stable/
https://opencv.org/

両方共 Python の画像処理ライブラリ。

Pillow は PIL から fork されて作成された画像ライブラリ。
OpenCV はより高度な画像処理アルゴリズムを提供するライブラリ。


## rq 

https://python-rq.org/

Redis をメッセージキューとして利用するシンプルな分散処理ライブラリ。
事前に準備した Redis 上のキューにメッセージを投げることで、別のプロセスで関数を実行することが可能。

ただし、関数は pickle でシリアライズ化可能である必要がある点に注意。


## BeautifulSoup

https://pypi.org/project/beautifulsoup4/

Python のスクレイピングライブラリ。
システムでは BeautifulSoup 4 系を利用。


