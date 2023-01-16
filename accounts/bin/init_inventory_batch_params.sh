#!/bin/bash
# バックグラウンドワーカーの初期化数を設定

SCRIPT_DIR=$(cd $(dirname $0); pwd)
cd $SCRIPT_DIR
cd ../..

PYTHON_CMD=/home/richs/.pyenv/versions/3.6.7/bin/python
BATCH="$PYTHON_CMD manage.py constant_manager --operation set"

$BATCH BACKGROUND_SEARCH_WORKER 16 --description "一括検索のワーカー数"
$BATCH BACKGROUND_IMPORT_WORKER 5 --description "CSVインポートのワーカー数"
$BATCH INVCHK_YAHOO_WORKER 5 --description "Yahoo在庫取り下げのワーカー数"
$BATCH INVRES_YAHOO_WORKER 2 --description "Yahoo在庫復活のワーカー数"
$BATCH INVCHK_MERCARI_WORKER 2 --description "Mercari在庫取り下げのワーカー数"
$BATCH INVRES_MERCARI_WORKER 2 --description "Mercari在庫復活のワーカー数"
