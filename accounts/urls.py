#!/usr/bin/python 
# -*- coding: utf-8 -*-

from django.urls import path
from . import views

app_name='accounts'

urlpatterns = [
    path('api/fjcmember', views.fjc_member, name='api_fjcmember'),
]

