from django.urls import path
from . import views

app_name='yahoo'

urlpatterns = [
    path('test', views.test, name='test'),
    path('exclude_seller', views.exclude_seller, name='exclude_seller'),
    path('delete_exclude_seller', views.delete_exclude_seller, name='delete_exclude_seller'),
    path('amazon_offer_research', views.amazon_offer_research, name='amazon_offer_research'),
    path('research', views.research, name='research'),
    path('research_amazon_by_yahoo', views.research_amazon_by_yahoo, name='research_amazon_by_yahoo'),
    path('feed_amazon_new', views.feed_amazon_new, name='feed_amazon_new'),
    path('feed_amazon_offer', views.feed_amazon_offer, name='feed_amazon_offer'),
    path('export_amazon_new_csv', views.export_amazon_new_csv, name='export_amazon_new_csv'),
    path('export_amazon_offer_csv', views.export_amazon_offer_csv, name='export_amazon_offer_csv'),
    path('export_amazon_new_csv_from_candidate', views.export_amazon_new_csv_from_candidate, name='export_amazon_new_csv_from_candidate'),
    path('download_amazon_csv', views.download_amazon_csv, name='download_amazon_csv'),
    path('edit_amazon_offer', views.edit_amazon_offer, name='edit_amazon_offer'),
    path('edit_amazon_new', views.edit_amazon_new, name='edit_amazon_new'),
    path('edit_amazon_new_candidate', views.edit_amazon_new_candidate, name='edit_amazon_new_candidate'),
    path('item_list', views.item_list, name='item_list'),
    path('import_report', views.import_report, name='import_report'),
    path('download_item_list', views.download_item_list, name='download_item_list'),
    path('import_csv', views.import_csv, name='import_csv'),

    path('api/progress/import_report', views.import_report_progress, 
        name='api.progress.import_report'),
    path('api/progress/amazon_offer_research', views.amazon_offer_research_progress, 
        name='api.progress.amazon_offer_research'),
    


]
