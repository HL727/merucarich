from django.urls import path
from rest_framework import routers
from . import views
#from .views import UserViewSet, EntryViewSet

from django.conf.urls import url, include

app_name = 'settings_amazon'

urlpatterns = [
    path('api_settings/', views.api_settings, name='api_settings'),
    path('default/', views.default_settings, name='default'),
    path('exclude_asin', views.exclude_asin, name='exclude_asin'),
    path('delete_exclude_asin', views.delete_exclude_asin, name='delete_exclude_asin'),
    path('brand/', views.brand_settings, name='brand'),
    path('delete_brands/', views.delete_brands, name='delete_brands'),
    path('category/', views.category, name='category'),
    path('category_parent', views.category_parent, name='category_parent'),
    path('category_child', views.category_child, name='category_child'),
    path('feed_price_settings', views.feed_price_settings, name='feed_price_settings'),
    path('api/token_validation', views.token_validation, name='api_token_validation'),
]

router = routers.DefaultRouter()
router.register(r'amazon_category', views.AmazonParentCategorySerializerViewSet)
router.register(r'amazon_brand', views.AmazonBrandSerializerViewSet)
router.register(r'amazon_category_user', views.AmazonParentCategoryUserSerializerViewSet)
router.register(r'amazon_child_category', views.AmazonChildCategorySerializerViewSet)
router.register(r'amazon_child_category_user', views.AmazonChildCategoryUserSerializerViewSet)


