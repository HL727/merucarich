# AsyncWorker

merucarich の非同期処理を行うモジュールです。

メッセージキューには rq を利用しています。

## Requirements 

- `pip install rq` にて `rq` がインストールされていること
- キューとして利用可能な redis が立っていること


## Configuration

`richs_app/settings.py` 内で以下を設定。

1. `INSTALLED_APPS` に 'asyncworker' を追加
2. 変数 `ASYNC_WORKER` に設定を定義する

```python
ASYNC_WORKER = {
    'WAIT_DEFAULT_SECONDS': 1,                    # 単にwaitした場合のスリープ時間
    'TASK_RECOMMENDED_MAXIMUM_SECONDS': 30,       # Workerが1ジョブ辺りを専有する推奨時間
    'MAXIMUM_SEQUENCE': -1 if PRODUCTION else 2,  # jobの打ち切り最大シーケンス数 (負数時は無限大)
    'REDIS': {
        'HOST': 'localhost',
        'PORT': 6379,
        'DB_FOR_DATA': 0,
        'DB_FOR_QUEUE': 0,
    },
    'QUEUE_NAME': 'default',
}
```

## How to run

1プロセスは以下の方法で立ち上がる。

```bash
python manage.py runasyncworker
```

もちろん、１台の中に複数台のプロセスを立ち上げてもよい。


## 確認

```bash
rq info
```

## ワーカー停止時の挙動について

rq.Worker は Redis をキューとして遅延ジョブ実行を行う。
ワーカーが実行中のジョブは "rq:wip:[キュー名]" に格納されている。

ワーカープロセスに対してプロセス停止シグナルが送られた場合、１度目であればジョブの終了を待つが、２度目の場合はジョブの終了を待たずにWIP状態のままでジョブが中断されてしまう。

これを復帰させるために `python manage.py requeue_jobs` を実装したので、サービス再起動前には実行すると良い。
(systemdから呼ばれる想定の `run.sh` では対処済)


