#!/usr/bin/python 
# -*- coding: utf-8 -*-

from datetime import timedelta

from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone

from settings_amazon.models import AmazonAPI

def _has_validate_token(user):
    auth = AmazonAPI.objects.filter(author=user).first()
    if auth is None or auth.validated_date is None:
        return False
    now = timezone.datetime.now()
    return (now - auth.validated_date) <= timedelta(days=1)


@login_required
def index(request):

    if request.user.is_staff == True:
        return HttpResponseRedirect("/admintools/index")

    params={}
    params['full_name']= request.user.full_name
    params['token_validated'] = _has_validate_token(request.user)
    
    return render(request, 'home/index.html', params)
