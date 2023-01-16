#!/usr/bin/python 
# -*- coding: utf-8 -*-

from django.urls import path
from . import views

app_name='admintools'

urlpatterns = [
    path('index', views.index, name='index'),
    path('ipstatus', views.ipstatus, name='ipstatus'),
    path('api/ipstatus/amazon', views.api_ipstatus_amazon, name='api.ipstatus.amazon'),
    path('api/ipstatus/yahoo', views.api_ipstatus_yahoo, name='api.ipstatus.yahoo'),
    path('api/ipstatus/mercari', views.api_ipstatus_mercari, name='api.ipstatus.mercari'),
    path('banned_keywords', views.banned_keywords, name='banned_keywords'),
    path('exclude_asins', views.exclude_asins, name='exclude_asins'),
    path('exclude_sellers', views.exclude_sellers, name='exclude_sellers'),
    path('itemname_rules', views.itemname_rules, name='itemname_rules'),
    path('api/itemname_rules/test', views.test_rule, name='api.itemname_rules.test'),
]

