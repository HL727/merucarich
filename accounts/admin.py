from .models import User, OfferReserchWatcher, StopRequest, BannedKeyword, \
    ItemCandidateToCsv, OverrideConstantValue, URLSkipRequest 
from django.contrib.auth.admin import UserAdmin
from django.contrib import admin
from django.utils.translation import gettext, gettext_lazy as _

# Register your models here
class ItemCandidateToCsvInline(admin.StackedInline):
    model = ItemCandidateToCsv


@admin.register(User)
class AdminUserAdmin(UserAdmin):

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Personal info'), {'fields': ('full_name', 'email')}),
        (_('システム設定'), {'fields': ('check_times', 'max_items', 'ip_address')}),
        #(_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        #(_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )
    list_display = ('username', 'email', 'full_name', 'is_staff', 'date_joined', 'check_times', 'max_items', 'ip_address')
    search_fields = ('username', 'full_name', 'email', 'ip_address')
    filter_horizontal = ('groups', 'user_permissions')
    inlines = [ ItemCandidateToCsvInline ]

# IPアドレス
#admin.site.register(IPAddress)
admin.site.register(OfferReserchWatcher)
admin.site.register(StopRequest)
admin.site.register(URLSkipRequest)
# 禁止ワード
admin.site.register(BannedKeyword)
# 候補のCSV出力
admin.site.register(ItemCandidateToCsv)
admin.site.register(OverrideConstantValue)

