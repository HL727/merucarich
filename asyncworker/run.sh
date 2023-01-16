#!/bin/bash
# 非同期ワーカーを実行する

WORKER_NUM=${1:-12}
IMPORT_NUM=${2:-4}
PYTHON_CMD=/home/richs/.pyenv/versions/3.6.7/bin/python
# PYTHON_CMD=python

# ディレクトリをプロジェクトルートに
SCRIPT_DIR=$(cd $(dirname $0); pwd)
cd $SCRIPT_DIR
cd ../


# WIP状態で止まってしまっているものとFailed状態を全て積み直す
$PYTHON_CMD manage.py requeue_jobs
$PYTHON_CMD manage.py requeue_jobs --queue-name import_queue

# ワーカー実行数がDBにあれば、上書きする
ENVFILE=accounts/bin/.env
if [ -e $ENVFILE ]; then
  source $ENVFILE
fi
WORKER_NUM=${BACKGROUND_SEARCH_WORKER:-$WORKER_NUM}
IMPORT_NUM=${BACKGROUND_IMPORT_WORKER:-$IMPORT_NUM}

# ワーカーを指定数実行
for i in `seq 1 $WORKER_NUM`; do
  $PYTHON_CMD manage.py runasyncworker &
done

# ワーカーを指定数実行
for i in `seq 1 $IMPORT_NUM`; do
  $PYTHON_CMD manage.py runasyncworker --queue-name import_queue &
done

