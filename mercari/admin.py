from django.contrib import admin
from .models import MercariToAmazonItem, MercariToAmazonCSV, MercariImportCSVResult,\
    MercariExcludeSeller, MercariExcludeSellerMaster


# Register your models here.
#admin.site.register(MercariToAmazonItem)
#admin.site.register(MercariToAmazonCSV)
admin.site.register(MercariImportCSVResult)
admin.site.register(MercariExcludeSellerMaster)
admin.site.register(MercariExcludeSeller)



