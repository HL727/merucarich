#!/bin/bash
# バックグラウンドワーカー用の定数ファイルを .env に書き出し

SCRIPT_DIR=$(cd $(dirname $0); pwd)
cd $SCRIPT_DIR
cd ../..

# PYTHON_CMD=/home/richs/.pyenv/versions/3.6.7/bin/python
PYTHON_CMD=python
BATCH="$PYTHON_CMD manage.py constant_manager"
OUTPUT=accounts/bin/.env

echo "# genarated at $(date)" > $OUTPUT
echo BACKGROUND_SEARCH_WORKER=$($BATCH BACKGROUND_SEARCH_WORKER --get-default 16) >> $OUTPUT
echo BACKGROUND_IMPORT_WORKER=$($BATCH BACKGROUND_IMPORT_WORKER --get-default 5) >> $OUTPUT
echo INVCHK_YAHOO_WORKER=$($BATCH INVCHK_YAHOO_WORKER --get-default 5) >> $OUTPUT
echo INVRES_YAHOO_WORKER=$($BATCH INVRES_YAHOO_WORKER --get-default 5) >> $OUTPUT
echo INVCHK_MERCARI_WORKER=$($BATCH INVCHK_MERCARI_WORKER --get-default 5) >> $OUTPUT
echo INVRES_MERCARI_WORKER=$($BATCH INVRES_MERCARI_WORKER --get-default 5) >> $OUTPUT

