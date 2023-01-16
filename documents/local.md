# 開発環境セットアップ

ここでは以下の環境にセットアップを行う。
Windows などで開発する場合でも、Virtual Box などを使って Linux をインストールすれば、その上で開発は可能。

- Windows 10 + VirtualBox 上の Linux (Ubuntu 18.04 LTS)
  - Git
  - Docker

また、著者は Vim によって開発を行っていたが、必要に応じて好みのエディタを入れる事。
以下、コマンドラインは `bash` で検証したものになる。


## Git Clone

ソースコードは git でクローンすること。
以下は https でクローンした場合の例。

```bash
cd [clone するディレクトリ]
git clone https://github.com/Merucarich/merucarich.git
# ユーザー名・パスワードを入力
cd merucarich
```

## Python

開発環境として pipenv + pyenv を採用している。
ただし、本番環境は仮想環境を採用していないため、別途 requirements.txt が本番用にコミットされている。


### pyenv + pipenv のインストール

例えば以下を参考にして pyenv + pipenv を利用可能にする。

https://qiita.com/fury00812/items/08036e78a449d1cbeb48

以下、必要に応じて参照のこと。

- https://github.com/pyenv/pyenv/wiki/Common-build-problems
- https://github.com/pyenv/pyenv-installer
- ubuntuでsudo pyenvに問題がある場合: https://qiita.com/shigechioyo/items/198211e84f8e0e9a5c18


### pipenv の 設置

本番で使われているバージョンは `python3.6.7` で、これは `Pipfile` に記載してある。

```bash
cd [cloneしたディレクトリ]
pipenv install
pipenv install -r requrements.txt
```

### settings.py の設置

Djangoの基本設定 `settings.py` を `richs_app/settings.py` に置くことでアプリケーションは起動する。
ここにはDjangoのアプリケーション固有のシークレットキーやDBのパスワードなどを記載するため
`richs_app/settings.py` はコミットされていない。

ローカルの開発環境では、以下の処理を行う。

```bash
# 自分の環境用の settings.py を作成する
cp richs_app/base_settings.py richs_app/settings.py

# ローカル用設定を自動生成
pipenv run python local_dev_setting.py > richs_app/local_settings.py
```

なお、本番適用時のやり方は [デプロイ用ドキュメント](./deploy.md) を参照の事。


## Database (MariaDB + Redis)

※Django のツールを利用するため、先に Python の設定を済ませて置くこと。

本番環境は MariaDB 10.1.37。 設定は以下の通り。

```
Server version: 10.1.37-MariaDB MariaDB Server

MariaDB [(none)]> show variables like 'chara%';
+--------------------------+----------------------------+
| Variable_name            | Value                      |
+--------------------------+----------------------------+
| character_set_client     | utf8                       |
| character_set_connection | utf8                       |
| character_set_database   | utf8mb4                    |
| character_set_filesystem | binary                     |
| character_set_results    | utf8                       |
| character_set_server     | utf8mb4                    |
| character_set_system     | utf8                       |
| character_sets_dir       | /usr/share/mysql/charsets/ |
+--------------------------+----------------------------+
```

Django で utf8mb4 を取り扱う場合、`(1071, 'Specified key was too long; max key length is 767 bytes')` などが発生するので事前にサーバー側の設定でこれを回避する必要がある。
ここでは `mariadb/conf.d/my.cnf` と `manage.py` にそのための記載がある。 詳しくは以下を参照。

- https://qiita.com/shirakiya/items/71861325b2c8988979a2

MariaDBは `docker` と `docker-compose` を利用して既存環境を汚すこと無くローカルに導入する。 
また、docker-compose によって `redis` も合わせて導入する。
本番環境ではこの２つのミドルウェアを利用している。

以下、これらは sudo なしでdockerコマンドが利用可能な前提で記載する。

```bash
cd [cloneしたディレクトリ]
docker-compose up -d
```

ただし、これによって立ち上げた場合は Docker コンテナを終了させるとボリュームが迷子になってしまい、
これまでに書き込んだデータが消えてしまう。
そのため、データをローカルに保存して永続化したい場合は以下の通り `docker-compose.yml` のコメントを外す。

( `./mariadb/mount` 以下にマウントされるので、自分の好みがあればマウント場所は変更すること)

```yaml
# enable it if you want permanent database
- ./mariadb/mount:/var/lib/mysql
```

その後、以下のコマンドでこのプロジェクトで作成するデータベースの作成、および、テーブルの作成を行う。
なお、DBの初期化にしばらくかかるので、その場合は少し待ってリトライすること。

```bash
pipenv run python manage.py migrate
```

その後、`python manage.py createsuperuser` を実行してテストで利用できるユーザーを作成する。

```bash
 pipenv run python manage.py createsuperuser
ユーザー名: admin
メールアドレス: admin@localhost
Password: 
Password (again): 
Superuser created successfully.
```

### マスタデータの追加

開発用に、以下のテーブルにデータを入れる。
開発で用いていたものを dump して `documents/initdata.sql` に配置済。

- 禁止ワード(accounts_bannedkeyword)
- 除外セラー（メルカリ）(mercari_exclude_seller_master)
- 禁止ASIN(amazon_exclude_asin_master)
- 除外セラー（ヤフオク）(yahoo_exclude_seller_master)
- AMAZON新規出品用CSV出力(amazon_csv_format)
- Settings_Amazon › 大カテゴリー設定（amazon_parent_category)
- Settings_Amazon › 詳細カテゴリー設定(ホビー)（amazon_hobbies_category)
- 新規出品用CSVフォーマット(amazon_csv_format)

```bash
mysql -u root -p -h 127.0.0.1 richs < documents/initdata.sql
```

## ローカルサーバー実行

以下のコマンドでサーバーを実行する。

```bash
pipenv run python manage.py runserver
```

その後、ブラウザで `http://localhost:8000/admin` にアクセスする。
ここでは先程 `createsuperuser` で作成したユーザーでログインする。

その後、`ACCOUNTS` > `ユーザー` を選び、一般ユーザーを作成する。
ユーザーには２種類あり、

- 特権ユーザー: ログインすると管理機能が利用できる
- 一般ユーザー: 通常の機能が利用できる

と分離されている。


ユーザーを作成した後、 `http://localhost:8000/` にアクセスすれば一般ユーザー用のログイン画面が表示されるので、
ここに作成したユーザー・パスワードを入力してログインし、サーバーにサクセスできるかを確かめる。


以上が開発環境のセットアップとなる。


