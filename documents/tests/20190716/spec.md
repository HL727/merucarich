# 20190716 非同期処理検証報告

ここでは、2019年7月16日に実施された新規非同期処理に関する検証結果をまとめる。


## 環境環境

### インフラ構成

全てローカル上で実施。 サーバーは ubuntu 18.04 LST.

* 環境: pyenv および virtualenv で構築された環境
* サーバー: `python manage.py runserver` - 1台 (1プロセス)
* ワーカー: `python manage.py runasyncworker` - 4台 (4プロセス)
* DB: ローカル上 (Docker) の Maria DB
* Redis: ローカル上 (Docker) の Redis


### richs_app/settings.py の設定

* PRODUCTION: `False` (MWSキーを所有していないため)
* ASYNC_WORKER['WAIT_DEFAULT_SECONDS']: `1`
* ASYNC_WORKER['TASK_RECOMMENDED_MAXIMUM_SECONDS'']: `5` (順次処理で5秒以上経った場合は処理を明け渡す)
* ASYNC_WORKER['MAXIMUM_SEQUENCE']: `-1` (ジョブ打ち切りはなし)


## 検証シナリオ

Goal: 同時実行最大ユーザー数想定が80人であるため、80人が同時に検索を行い、画面が固まらず処理が終わる事を確かめる。


### 検証データ作成

以下のコマンドで作成。 細かい処理は `devtools/testdata_20190716.py` に記載。

```bash
python manage.py shell

from devtools import testdata_20190716 as td

# loadtest01 - loadtest80 までのユーザーを作成
td.setup()

# for文などでコマンドを発行
for idx in range(80):
    username = 'loadtest{:02}'.format(idx+1)
    td.start_yahoo(username)
    # merucari の場合
    td.start_mercari(username)

# 停止したい場合
td.stop_yahoo('loadtest02')

# 全ユーザーの削除
td.close()

# shellの終了
quit()
```

## 検証方法

- Workerは12時間経過した状態でスタートさせた
  - 長期タスクを実施しないことによるコネクション切れなどの問題がないかを確認
  - 正常にタスクの再実施は可能
- `loadtest01` から `loadtest80` までのユーザーでYahooサーチをスタート
- `loadtest01` から `loadtest40` までのユーザーでメルカリサーチをスタート
- ブラウザで `loadtest01` にログインしてヤフオク・メルカリのAmazon検索画面を開く
  - 画面は検索中である表示を確認
  - ヤフオク版の方は開きっぱなしにしておき、ajaxにて情報が逐次更新されることを確認
  - 5分後にそれぞれの画面を開き、経過時間や検索件数などのパラメータが更新されていることを確認
  - それぞれの検索を「停止」させて、これらが動作することを確認
- ブラウザで `loadtest02` にログインしてヤフオク・メルカリのAmazon検索画面を開く
  - メルカリ版を再度画面から検索を実施し、正常に検索が行われることを確認
  - 経過時間が1時間以上の場合でも問題が起きないことを確認
- １時間以上経過したところで、再度メルカリ検索を40件投入
- 開始から4時間ほどそのままにして、タスクが終了するかを確かめる


## 結果

上記の場合でも画面側、ジョブ側ともに固まること無く正常に終了した。
ただし、非常に多くのログが出力される (rqのloggerがジョブの開始時、終了時に引数を出力する）ため、場合によってはロガーの再設定が必要。




