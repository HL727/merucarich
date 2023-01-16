#!/bin/bash

SCRIPT_DIR=$(cd $(dirname $0); pwd)
cd $SCRIPT_DIR
cd ../..

PYTHON_CMD=/home/richs/.pyenv/versions/3.6.7/bin/python
# PYTHON_CMD=python

$PYTHON_CMD manage.py delete_old_items --expired-days 7


