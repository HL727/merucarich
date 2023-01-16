#!/usr/bin/python 
# -*- coding: utf-8 -*-

from django.urls import path
from . import views

app_name='asyncworker'

urlpatterns = [
    path('api/worker', views.worker, name='worker'),
    path('api/workercount', views.workercount, name='workercount'),
]

