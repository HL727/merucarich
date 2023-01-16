from django.contrib import admin
from django.urls import path, include
from rest_framework import routers
from django.conf.urls import url

from settings_amazon.urls import router as blog_router


admin.site.site_title = 'メルカリッチくん - 管理者画面' 
admin.site.site_header = 'メルカリッチくん - 管理者画面' 
admin.site.index_title = '管理メニュー'



urlpatterns = [
    path('admin/', admin.site.urls),
    path('admintools/', include('admintools.urls')),
    path('accounts/', include('django.contrib.auth.urls')),
    path('', include('top.urls')),
    path('home/', include('home.urls')),
    path('yahoo/', include('yahoo.urls')),
    path('mercari/', include('mercari.urls')),
    path('settings_amazon/', include('settings_amazon.urls')),
    url(r'^api/', include(blog_router.urls)),
    path('asyncworker/', include('asyncworker.urls')),
    path('system/', include('accounts.urls')),
]
