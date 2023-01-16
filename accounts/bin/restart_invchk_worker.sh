#!/bin/bash
# 在庫管理バッチ用バックグラウンドジョブのリフレッシュ
# 基本は1日に1度, 各処理が終了している PM 11:45 に再起動を行う
/usr/bin/systemctl restart invchkworker

