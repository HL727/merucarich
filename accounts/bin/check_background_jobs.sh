#!/bin/bash
# バックグラウンドジョブの定期監視

PYTHON_CMD=/home/richs/.pyenv/versions/3.6.7/bin/python

# チェックして再起動が必要なら再起動させる
if $PYTHON_CMD manage.py check_background_jobs | grep 'restart required' >> /dev/null; then
    date
    /usr/bin/systemctl restart asyncworkers
fi

