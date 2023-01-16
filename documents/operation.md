# 定例オペレーション

実際によくあった問題と対処方法。


## 既存の監視など

プロジェクトとしては行っていない。
調査の一環として Zabbix を利用していたため、 zabbix-agent はインストールされている。


## アクセスチェック

nginxのログは `/var/log/nginx` 以下にある。


## ログファイルをチェックする

ログファイルは `/var/www/richs/logs` 以下にある。
主に見るのは、

- django.log: 全般 (以下以外はだいたいここ)
- inventory-yahoo.log: 在庫チェック (Yahoo)
- inventory-mercari.log: 在庫チェック (Mercari)
- update-amazon-feed.log 在庫更新 (UpdateAmazonFeed)

あたり。

ログ出力は `richs_app/settings.py` 内でどのパッケージの出力をどのファイルに出すかを定義している。


## 外部向けファイル

`/var/www/richs_public/` においてある。 それぞれ以下の通り。

- `images` : Amazonの出品時に公開しておく必要のある画像が保存されている
- `output` : CSV出力されて、ダウンロード可能になったものの一覧
- `tmp` : 一時的にアップロードされたCSVや、プログラムで利用するために保存した画像ファイルなどがここの下に置かれる


## 即座に在庫チェックを走らせる

cron で 1日に2回しか動作しないので、悪いタイミングでPCが再起動した場合、手動で在庫チェックを起動しないとしばらく在庫チェックが止まってしまう。

```bash
# richs ユーザーで実行
su - richs 
# カレントディレクトリを変更
cd /var/www/richs

# 在庫チェック (取り下げ) 実行
python manage.py check_item_yahoo 2 4 --max-workers 14 &  >> /tmp/check_item_yahoo_12.log 2>&1
python manage.py check_item_mercari 2 4 --max-workers 14 &  >> /tmp/check_item_mercari_12.log 2>&1

# 在庫チェック (復活) 実行
python manage.py update_item_yahoo 2 4 --max-workers 14 &  >> /tmp/update_item_yahoo_12.log 2>&1
python manage.py update_item_mercari 2 4 --max-workers 14 &  >> /tmp/update_item_mercari_12.log 2>&1
```

## 在庫チェックを止める

特にメルカリ側で利用している index-linux の管理サーバーが落ちていることがある。
（これは内製サービス）。
この時に在庫チェックを走らせると、全てのメルカリ商品を取り下げてしまうので、
在庫チェックを一時的に止めたい場合がある。

1. `/etc/crontab` から `check_item_mercari` 部分をコメントアウトする
2. `systemctl reload crond` で設定を反映
3. 既存のプロセスを `ps aux` で探し出して `kill` する


### 在庫チェックの復活

1. `/etc/crontab` から `check_item_mercari` 部分をコメントアウトを元に戻す
2. `systemctl reload crond` で設定を反映

追加で即座に在庫チェックを走らせる場合は、該当の項目を参照。


## index-linux がうまく稼働しない

1. 再起動を試みる

※srv1の部分は適時変更する

```bash
SERVER=srv1 DEBUG=ibiz:* NODE_ENV=production pm2 stop /home/hai/index-linux
SERVER=srv1 DEBUG=ibiz:* NODE_ENV=production pm2 start /home/hai/index-linux
```

2. Redisを使っているので redis を再起動して再起動する

```bash
systemctl restart redis
SERVER=srv1 DEBUG=ibiz:* NODE_ENV=production pm2 stop /home/hai/index-linux
SERVER=srv1 DEBUG=ibiz:* NODE_ENV=production pm2 start /home/hai/index-linux
```

## DBのバックアップを取りたい

mysqldump を使って取る。
DBサーバーはボリュームが少ないので、AP上にとって gzip なり tar.gz なりに圧縮しておく。


## DBがいっぱいになった

アーカイブログがあるので、これを消して何とか開ける。

1. DBにログイン (以下は1号機DBの場合)

```bash
$ ssh root@163.43.241.69
```

2. ディスク容量の確認

```bash
$ df -h
ファイルシス   サイズ  使用  残り 使用% マウント位置
/dev/vda3         16G  7.2G  7.7G   49% /
devtmpfs         985M     0  985M    0% /dev
tmpfs           1000M     0 1000M    0% /dev/shm
tmpfs           1000M  105M  896M   11% /run
tmpfs           1000M     0 1000M    0% /sys/fs/cgroup
tmpfs            200M     0  200M    0% /run/user/0
```

3. 設定ファイル /etc/my.cnf の確認

中に書かれている `expire_logs_days=1` の数値が1より大きければ、これを1に。
その後、保存して閉じる

4. ディスクが100%の場合 `/var/lib/mysql/mysql-bin.xxxxxx` の中で一番小さい数字のやつを削除して手動で一時的なスペースを空ける

MySQLの再起動時にそれ以外の不要なものは消してくれるので、とりあえず１つで良い。
以下の例の場合は rm mysql-bin.000195 を実行。

```bash
# cd /var/lib/mysql/
[root@db1 mysql]# ll
合計 2033240
-rw-rw---- 1 mysql mysql      16384  3月 20 15:19 aria_log.00000001
-rw-rw---- 1 mysql mysql         52  3月 20 15:19 aria_log_control
-rw-rw---- 1 mysql mysql          6  3月 20 15:19 db1.pid
-rw-rw---- 1 mysql mysql   50331648  7月 17 12:51 ib_logfile0
-rw-rw---- 1 mysql mysql   50331648  7月 17 12:10 ib_logfile1
-rw-rw---- 1 mysql mysql  146800640  7月 17 12:51 ibdata1
-rw-rw---- 1 mysql mysql          0  1月 22  2019 multi-master.info
drwx--x--x 2 mysql mysql       4096  1月 22  2019 mysql
-rw-rw---- 1 mysql mysql 1073742237  7月 16 14:22 mysql-bin.000195
-rw-rw---- 1 mysql mysql  760778709  7月 17 12:51 mysql-bin.000196
-rw-rw---- 1 mysql mysql         38  7月 16 14:22 mysql-bin.index
srwxrwxrwx 1 mysql mysql          0  3月 20 15:19 mysql.sock
drwx------ 2 mysql mysql       4096  1月 22  2019 performance_schema
drwx------ 2 mysql mysql       4096  7月  1 10:10 richs
```

5. MySQL の再起動

以下のコマンドで再起動する。
時間がかかって失敗とみなされる場合は、もう一度同じコマンドを繰り返す。

```bash
systemctl restart mysqld
```

6. ディスク容量の再確認

```bash
$ df -h
```


## Amazon の Captcha について

Amazonに機械的にアクセスすると CAPTCHA によって認証を求められる。
これを解読するための仕組みが別のサーバー (`http://160.16.133.101/amazon/captcha/`) に用意されていて、これを使っている。
なお、このサービスは内製であり、本番環境のIPからのみアクセスが可能。


## Amazon にブロックされる

通信頻度が多い場合、 AmazonScraper からの通信 (https://www.amazon.co.jp/...) がブロックされることがある。

これはおそらく AWS WAF による「一定期間のアクセス頻度が一定以上の場合、一時的にブロック (503を返す) するもの」
に近いものであると推測される。

これまで同一の現象に当たったときは、通信を行わなければ 3 - 6 時間程度で再度アクセスが可能になったので、
一括検索を止めて対処する。

なお、IPアドレスは近いものが多いので、複数のIPアドレスで高頻度アクセスを行うとネットワークアクセス単位でブロックされる模様。


以上。 適時追加。
