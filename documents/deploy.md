# 本番環境へのデプロイ手順書

ここでは本番環境へのデプロイ方法について記載する。
この手順は 2019 年 7 月 22 日に当時の開発者で協議の後、制定されたものである。

## 0. Github へのコミット

Github へ変更を commit/push した後、master ブランチに反映する。
開発者がほぼ 1 人の為、特にルールはないが、

- 自身の変更を `fix-YYYYMMDD-N` (例: fix-20200701-1) のようなブランチに push する
- PullRequest を master に出す。 この時、変更内容を PullRequest に記載する
- Github 上で確認し、マージを実施

のようにすると良い。

### settings.py の更新について

主にシステム定数などを追加する場合にこのファイルを更新する必要がある。
しかし、Amazon のキーなどの重要情報が入っているため、これは Git にはコミットしない。
このファイルを変更したい場合は以下の方法で更新を行う。

- ローカル環境の `richs_app/settings.py` で検証する
- 変更を `richs_app/base_settings.py` に書き加えてコミットする
- 本番のサービス稼働前に `richs_app/settings.py` に 変更を手動で適用する

### DB の変更(マイグレーション)について

DB に新しいテーブル・カラムを追加する場合は Django の migrate 機能を利用する。
方法は以下の通り。

- ローカル環境の models.py に新しいテーブル・カラムの変更を加える
- `pipenv run python manage.py makemigrations` を行い、マイグレーション用のプログラムを作成する
  - 例えば `yahoo/models.py` を編集した場合は、 `yahoo/migrations` 以下に `0004_aaaaaa.py` のようなマイグレーションファイルができる
- ローカル環境に適用する
  - `pipenv run python manage.py migrate` を実施する
  - 打ち消したい場合などは `pipenv run python manage migrate yahoo 0003` のように実行アプリとマイグレーション番号を指定することで対処できる
  - 一度ロールバックした後、コミット前のファイルを消して `makemigrations` をすれば新しいマイグレーションファイルができる。
  - より詳しくは Django の migrate 機能について調べること
- このファイルに問題がなければコミット・push する
  - `git add -f yahoo/migrations` などのように `-f` をつける必要がある

なお、後述する通り、本番では migrate がうまく行かない場合があるので注意すること。

### requiements.txt について

ローカルは pipenv で行うことにしているが、本番適用したい追加ライブラリがある場合は `requirements.txt` にも記載しておくこと。

## 1. 本番サーバーへの ssh ログイン

まずはデプロイ先サーバーへとログインを行う。

## 2. リソースの最新化

本番サーバーでは `/var/www/richs` 以下に Github の情報を SSH で clone してある。
そのため、該当ディレクトリに移動後 git コマンドでリソースを最新化する。

```bash
# ユーザー権限を持つ richs で作業する
sudo su - richs

# OPTIONAL: ライブラリを追加
/home/richs/.pyenv/versions/3.6.7/bin/pip install ....

# リソースを最新化
cd /var/www/richs
git remote update -p && git stash && git rebase origin/master && git stash pop

# OPTIONAL: richs_app/base_settings.py を参考に更新がある場合は適用
vi richs_app/settings.py

# OPTIONAL: Database の変更がある場合は適用
python manage.py migrate

# richs ユーザーでの処理終了
exit

# パーミッションが変わってしまうので root ユーザーで実行
# これがないと asyncworker/run.sh などが働かない
# よりよい構成にしたい場合はパーミッションをきちんと管理するべきだが
# 既存の設定に従って 777 を指定
chmod -R 777 /var/www/richs
```

### 注意: 外部キー制約を追加する場合、マイグレートできない場合がある

`python manage.py migrate` を実施した際に、エラーになることがある。

具体的には、本番環境で accounts_user テーブルを外部キーに指定した新たなテーブルを作成しようとした場合。
自身の検証環境ではうまくいったが、本番では失敗した。

外部キー制約周りのエラーが出ていることは分かるが、詳細は表示されない。
この原因は「外部キーとしての型が異なる」ため。 `desc accounts_user` で見ると `char(32)` となっているが、 `show create table accounts_user` で見ると以下の通り COLLATE が指定されている。

```bash
 CREATE TABLE `accounts_user` (
  `password` varchar(128) COLLATE utf8mb4_unicode_ci NOT NULL,
  `last_login` datetime(6) DEFAULT NULL,
  `is_superuser` tinyint(1) NOT NULL,
  `uuid` char(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `username` varchar(150) COLLATE utf8mb4_unicode_ci NOT NULL,
  `full_name` varchar(150) COLLATE utf8mb4_unicode_ci NOT NULL,
  `email` varchar(254) COLLATE utf8mb4_unicode_ci NOT NULL,
  `max_items` int(11) DEFAULT NULL,
  `check_times` int(11) DEFAULT NULL,
  `ip_address` longtext COLLATE utf8mb4_unicode_ci,
  `is_staff` tinyint(1) NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  `date_joined` datetime(6) NOT NULL,
  `update_mercari_to_amazon_feed_pid` int(11) DEFAULT NULL,
  `update_mercari_to_amazon_feed_start_date` datetime(6) DEFAULT NULL,
  `update_yahoo_to_amazon_feed_pid` int(11) DEFAULT NULL,
  `update_yahoo_to_amazon_feed_start_date` datetime(6) DEFAULT NULL,
  PRIMARY KEY (`uuid`),
  UNIQUE KEY `username` (`username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci ROW_FORMAT=DYNAMIC |
```

そのため、このテーブルに外部キー制約を貼る場合は手動で SQL を実施して型あわせと外部キー制約を作成する。
その後、Django のマイグレートが正常に終了したことを認識させる必要がある。

```bash
python manage.py migrate accounts  # マイグレートするがエラーが発生する。
mysql -u richs -p -h [DB hostname] richs
# migrate が中断した場合、テーブルはできているので、カラムと外部キーを手動で設定
# -----
# 具体例: Django が作ったテーブルのカラムに対して属性を変更して外部キーを作成
> ALTER TABLE accounts_stockcheckstatus MODIFY COLUMN owner_id char(32) COLLATE 'utf8mb4_unicode_ci';
> ALTER TABLE accounts_stockcheckstatus ADD FOREIGN KEY(owner_id) REFERENCES accounts_user(uuid);
> exit;

# 最新状況まで当てたことをシステムに認識させる
python manage.py migrate accounts 0004 --fake
```

## 3. 各種サービスの更新

```bash
systemctl restart asyncworkers
systemctl restart invchkworkers
systemctl restart uwsgi

# if needed
systemctl restart nginx
```

以上。
