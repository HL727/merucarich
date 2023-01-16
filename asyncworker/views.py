#!/usr/bin/python 
# -*- coding: utf-8 -*-

import rq
import redis

from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse

from . import asynchelpers

@csrf_exempt
def worker(request):
    ws = asynchelpers.get_workers()
    return JsonResponse(dict(workers=ws))

@csrf_exempt
def workercount(requrest):
    ws = asynchelpers.get_workers()
    return JsonResponse(dict(count=len(ws)))

