# めるかりっちくん

どのようなアプリケーションかはユーザー向けのマニュアルをご覧ください。

http://yuukiiida.xsrv.jp/merucarich/user_manual.pdf


## How to run for local

最初にセットアップを行う。

- [ローカル環境での開発環境構築](documents/local.md)

セットアップ後、ローカル環境では以下のコマンドで起動する。 

```bash
# サーバー起動
pipenv run python manage.py runserver
```

デフォルトではポートは8000となっているので、サービス起動後  http://localhost:8000/ にアクセスすれば良い。


### How to run local worker

バックグラウンドジョブ用のワーカーの起動方法は以下の通り。

それぞれ、各機能をローカルで検証する場合に利用する。
なお、多重起動（並列実行）が可能なので、速度を出す場合などは利用すること。

```bash
# 一括検索用バックグラウンド用ワーカー起動
pipenv run python manage.py runasyncworker

# CSV取り込み用バックグラウンドワーカー起動
pipenv run python manage.py runasyncworker --queue-name import_queue

# Yahoo 在庫チェック用バックグラウンドワーカー起動
pipenv run python manage.py runasyncworker --queue-name invchk_yahoo
# Yahoo 在庫復活用バックグラウンドワーカー起動
pipenv run python manage.py runasyncworker --queue-name invres_yahoo

# Mercari 在庫チェック用バックグラウンドワーカー起動
pipenv run python manage.py runasyncworker --queue-name invchk_mercari
# Mercari 在庫復活用バックグラウンドワーカー起動
pipenv run python manage.py runasyncworker --queue-name invres_mercari
```

## Documentation

それぞれ以下のリンク先を参照。

- [ローカル環境での開発環境構築](documents/local.md)
- [各機能の概要の説明](documents/features.md)
- [利用している主要なライブラリ](documents/libraries.md)
- [本番サーバーの構成](documents/environment.md)
- [本番サーバーへのデプロイ](documents/deploy.md)
- [定例オペレーション](documents/operation.md)


## TIPS

以下、本番・開発を触る上でのTIPS


### ローカル環境でメルカリAPIを利用する場合

メルカリは本番で稼働している内部サービス localhost:1234 経由で必要データを取得するので、メルカリの検索などはこのプロジェクト単独では実現不可能。
これを実現する場合、本番環境を一時的に利用する方法がもっとも簡単。
具体的には、以下のようにローカルの1234ポートを本番の1234ポートまでsshトンネリングでつなげれば良い。

踏み台を使わない場合はローカルから直接本番へ流してもOK

```
# 自分 -> 踏み台サーバー (ある場合)
ssh -i [踏み台の鍵] -L 1234:localhost:1234 -N [踏み台ユーザー]@[踏み台IP]

# 踏み台 -> 本番
ssh -L 1234:localhost:1234 -N root@srv1.merucarich.com
```


### 単体テスト

`python manage.py test yahoo` や `python manage.py test mercari` などでプロダクトごとの検証が可能。
それぞれ `yahoo/tests/test*.py` や `mercari/tests/test.*.py` に反応する。

テストの都度、DBテーブルを作り直す・消去するので `-k` オプション付きでの実行を推奨。

なお、 `manage.py` が接続DBを前提としていることから、 これらのテストも利用するミドルウェア (DB, Redis) が必要なので注意する。 
`docker-compose` を利用してテスト用のミドルウェアは準備できるので活用すること。


### DB増設

号機を増やし、DBを増設する場合は下記のテーブルをコピーする必要がある。

- 禁止ワード(accounts_bannedkeyword)
- 除外セラー（メルカリ）(mercari_exclude_seller_master)
- 禁止ASIN(amazon_exclude_asin_master)
- 除外セラー（ヤフオク）(yahoo_exclude_seller_master)
- AMAZON新規出品用CSV出力(amazon_csv_format)
- Settings_Amazon › 大カテゴリー設定（amazon_parent_category)
- Settings_Amazon › 詳細カテゴリー設定(ホビー)（amazon_hobbies_category)
- 新規出品用CSVフォーマット(amazon_csv_format)

