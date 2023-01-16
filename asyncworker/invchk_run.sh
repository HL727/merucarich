#!/bin/bash
# 在庫チェック用非同期ワーカーを実行する

INVCHK_YAHOO_WORKER_NUM=${1:-2}
INVRES_YAHOO_WORKER_NUM=${2:-2}
INVCHK_MERCARI_WORKER_NUM=${3:-2}
INVRES_MERCARI_WORKER_NUM=${4:-2}
PYTHON_CMD=/home/richs/.pyenv/versions/3.6.7/bin/python
# PYTHON_CMD=python

# ディレクトリをプロジェクトルートに
SCRIPT_DIR=$(cd $(dirname $0); pwd)
cd $SCRIPT_DIR
cd ../

# WIP状態で止まってしまっているものとFailed状態を全て積み直す
$PYTHON_CMD manage.py requeue_jobs --queue-name invchk_yahoo
$PYTHON_CMD manage.py requeue_jobs --queue-name invres_yahoo
$PYTHON_CMD manage.py requeue_jobs --queue-name invchk_mercari
$PYTHON_CMD manage.py requeue_jobs --queue-name invres_mercari

# ワーカー実行数が環境変数にあれば、上書きする
ENVFILE=accounts/bin/.env
if [ -e $ENVFILE ]; then
  source $ENVFILE
fi
INVCHK_YAHOO_WORKER_NUM=${INVCHK_YAHOO_WORKER:-$INVCHK_YAHOO_WORKER_NUM}
INVRES_YAHOO_WORKER_NUM=${INVRES_YAHOO_WORKER:-$INVRES_YAHOO_WORKER_NUM}
INVCHK_MERCARI_WORKER_NUM=${INVCHK_MERCARI_WORKER:-$INVCHK_MERCARI_WORKER_NUM}
INVRES_MERCARI_WORKER_NUM=${INVRES_MERCARI_WORKER:-$INVRES_MERCARI_WORKER_NUM}

echo $INVCHK_YAHOO_WORKER_NUM
echo $INVRES_YAHOO_WORKER_NUM
echo $INVCHK_MERCARI_WORKER_NUM
echo $INVRES_MERCARI_WORKER_NUM

# ワーカーを指定数実行
for i in `seq 1 $INVCHK_YAHOO_WORKER_NUM`; do
  $PYTHON_CMD manage.py runasyncworker --queue-name invchk_yahoo &
done

for i in `seq 1 $INVRES_YAHOO_WORKER_NUM`; do
  $PYTHON_CMD manage.py runasyncworker --queue-name invres_yahoo &
done

for i in `seq 1 $INVCHK_MERCARI_WORKER_NUM`; do
  $PYTHON_CMD manage.py runasyncworker --queue-name invchk_mercari &
done

for i in `seq 1 $INVRES_MERCARI_WORKER_NUM`; do
  $PYTHON_CMD manage.py runasyncworker --queue-name invres_mercari &
done
