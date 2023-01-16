import logging

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.conf import settings
import django_filters
from rest_framework import viewsets, filters
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import *
from .forms import *
from .serializer import *

from richs_utils import AmazonSearchUtils
from richs_mws import MWSValidator


logger = logging.getLogger(__name__)


# AmazonAPI設定
@login_required
def api_settings(request):
    params = {}
    if (request.method == 'POST'):
        form = AmazonAPIForm(request.POST, instance=AmazonAPI())
        form.instance.author = request.user
        params['form'] = form
        params['success'] = False
        if form.is_valid():
            try:
                # 現在保存されているレコードを取得する。
                obj = AmazonAPI.objects.get(author=request.user)
                # 上書登録
                obj.account_id = form['account_id'].value()
                obj.auth_token = form['auth_token'].value()
                obj.author = request.user
                obj.save()
                logger.info(
                    'updated Amazon API: user=%s, account_id=%s',
                    obj.author.username, obj.account_id)
            except AmazonAPI.DoesNotExist:
                # 新規登録
                form.save()
            # 登録成功メッセージ
            params['success'] = True
            params['message'] = settings.MY_MESSAGE_SUCCESS
            params['message_detail'] = settings.MY_MESSAGE_SAVE_SUCCESS
        else:
            # バリデーションエラー
            params['message'] = settings.MY_MESSAGE_FAILED
            params['message_detail'] = settings.MY_MESSAGE_FORM_INVALID
    else:
        try:
            # 保存されている値をFormに返却
            obj = AmazonAPI.objects.get(author=request.user)
            params['form'] = AmazonAPIForm(instance=obj)
        except AmazonAPI.DoesNotExist:
            # 空のFormを返却
            params['form'] = AmazonAPIForm()

    return render(request, 'settings_amazon/api.html', params)


@login_required
@require_POST
def token_validation(request):
    ''' 入力されているAmazonAPIトークンのバリデーションを実施 '''
    keyword = request.POST.get('keyword', 'フィギュア')
    amazon_url = AmazonSearchUtils.keyword_to_url('1', keyword)
    account_id = request.POST.get('account_id')
    auth_token = request.POST.get('auth_token')
    asin = MWSValidator.get_asin(amazon_url)
    (success, message) = MWSValidator.validate_tokens(
        account_id, auth_token, asin)
    return JsonResponse({
        'success': success, 'message': message
    })


# Amazonデフォルト設定
@login_required
def default_settings(request):
    params = {}
    if (request.method == 'POST'):
        form = AmazonDefaultSettingsForm(
            request.POST, instance=AmazonDefaultSettings())
        form.instance.author = request.user
        params['form'] = form
        params['success'] = False
        if form.is_valid():
            try:
                # 現在保存されているレコードを取得する。
                obj = AmazonDefaultSettings.objects.get(author=request.user)
                # 上書登録
                obj.condition_type = form['condition_type'].value()
                obj.condition_note = form['condition_note'].value()
                obj.part_number = form['part_number'].value()
                obj.fulfillment_latency = form['fulfillment_latency'].value()
                obj.standard_price_points = form['standard_price_points'].value(
                )
                obj.new_item_points = form['new_item_points'].value() or None
                obj.new_auto_item_points = form['new_auto_item_points'].value(
                ) or None
                obj.ride_item_points = form['ride_item_points'].value() or None
                obj.author = request.user
                obj.save()
            except AmazonDefaultSettings.DoesNotExist:
                # 新規登録
                form.save()
            # 登録成功メッセージ
            params['success'] = True
            params['message'] = settings.MY_MESSAGE_SUCCESS
            params['message_detail'] = settings.MY_MESSAGE_SAVE_SUCCESS
        else:
            # バリデーションエラー
            params['message'] = settings.MY_MESSAGE_FAILED
            params['message_detail'] = settings.MY_MESSAGE_FORM_INVALID
    else:
        try:
            # 保存されている値をFormに返却
            obj = AmazonDefaultSettings.objects.get(author=request.user)
            params['form'] = AmazonDefaultSettingsForm(instance=obj)
        except AmazonDefaultSettings.DoesNotExist:
            # 空のFormを返却
            params['form'] = AmazonDefaultSettingsForm()
    return render(request, 'settings_amazon/default.html', params)


# 除外ASIN
@login_required
def exclude_asin(request):
    params = {}
    if (request.method == 'POST'):
        form = ExcludeAsinForm(request.POST, instance=ExcludeAsin())
        form.instance.author = request.user
        params['success'] = False
        if form.is_valid():
            if ExcludeAsin.objects.filter(author=request.user, asin=form.instance.asin).count() == 0:
                form.save()
                # 登録成功メッセージ
                params['success'] = True
                params['message'] = settings.MY_MESSAGE_SUCCESS
                params['message_detail'] = settings.MY_MESSAGE_SAVE_SUCCESS
            else:
                params['message'] = settings.MY_MESSAGE_FAILED
                params['message_detail'] = '既に登録済みの禁止ASINです。'
        else:
            # バリデーションエラー
            params['message'] = settings.MY_MESSAGE_FAILED
            params['message_detail'] = settings.MY_MESSAGE_FORM_INVALID

    params['form'] = ExcludeAsinForm()
    asins = ExcludeAsin.objects.filter(author=request.user)
    for i, asin in enumerate(asins):
        asin.local_id = i + 1

    params['asins'] = asins
    return render(request, 'settings_amazon/exclude_asin.html', params)

# 除外ASIN


@login_required
def delete_exclude_asin(request):
    params = {}
    if (request.method == 'POST'):
        delete_ids = request.POST.getlist('delete_ids')
        if delete_ids:
            ExcludeAsin.objects.filter(id__in=delete_ids).delete()

    params['form'] = ExcludeAsinForm()
    params['asins'] = ExcludeAsin.objects.filter(author=request.user)
    return render(request, 'settings_amazon/exclude_asin.html', params)


# Amazonブランド設定
@login_required
def brand_settings(request):
    params = {}
    if (request.method == 'POST'):
        form = AmazonBrandForm(request.POST, instance=AmazonBrand())
        form.instance.author = request.user
        params['success'] = False
        if form.is_valid():
            if AmazonBrand.objects.filter(author=request.user, brand_name=form.instance.brand_name).count() == 0:
                form.save()
                # 登録成功メッセージ
                params['success'] = True
                params['message'] = settings.MY_MESSAGE_SUCCESS
                params['message_detail'] = settings.MY_MESSAGE_SAVE_SUCCESS
            else:
                params['message'] = settings.MY_MESSAGE_FAILED
                params['message_detail'] = '既に登録済みのブランド名です。'
        else:
            # バリデーションエラー
            params['message'] = settings.MY_MESSAGE_FAILED
            params['message_detail'] = settings.MY_MESSAGE_FORM_INVALID

    params['form'] = AmazonBrandForm()
    params['brands'] = AmazonBrand.objects.filter(author=request.user)
    return render(request, 'settings_amazon/brand.html', params)

# Amazonブランド設定削除


@login_required
def delete_brands(request):
    params = {}
    if (request.method == 'POST'):
        delete_ids = request.POST.getlist('delete_ids')
        if delete_ids:
            AmazonBrand.objects.filter(id__in=delete_ids).delete()

    params['form'] = AmazonBrandForm()
    params['brands'] = AmazonBrand.objects.filter(author=request.user)
    return render(request, 'settings_amazon/brand.html', params)


@login_required
def feed_price_settings(request):
    params = {}
    if (request.method == 'POST'):
        form = AmazonFeedPriceSettingsForm(
            request.POST, instance=AmazonFeedPriceSettings())
        form.instance.author = request.user
        params['form'] = form
        params['success'] = False
        if form.is_valid():
            try:
                # 現在保存されているレコードを取得する。
                obj = AmazonFeedPriceSettings.objects.get(author=request.user)
                # 上書登録
                obj.margin_new = form['margin_new'].value()
                obj.margin_offer = form['margin_offer'].value()
                obj.margin_offer_url = form['margin_offer_url'].value()
                obj.margin_offer_percent_url = form['margin_offer_percent_url'].value(
                )
                obj.offset_offer_price_url = form['offset_offer_price_url'].value(
                )
                obj.lowest_offer_price_url = form['lowest_offer_price_url'].value(
                )
                obj.default_minimum_item_price = form['default_minimum_item_price'].value(
                )
                obj.author = request.user
                obj.save()
            except AmazonFeedPriceSettings.DoesNotExist:
                # 新規登録
                form.save()
            # 登録成功メッセージ
            params['success'] = True
            params['message'] = settings.MY_MESSAGE_SUCCESS
            params['message_detail'] = settings.MY_MESSAGE_SAVE_SUCCESS
        else:
            # バリデーションエラー
            params['message'] = settings.MY_MESSAGE_FAILED
            params['message_detail'] = settings.MY_MESSAGE_FORM_INVALID
    else:
        try:
            # 保存されている値をFormに返却
            obj = AmazonFeedPriceSettings.objects.get(author=request.user)
            params['form'] = AmazonFeedPriceSettingsForm(instance=obj)
        except AmazonFeedPriceSettings.DoesNotExist:
            # 空のFormを返却
            params['form'] = AmazonFeedPriceSettingsForm()

    return render(request, 'settings_amazon/feed_price_settings.html', params)

# カテゴリー


@login_required
def category(request):
    return render(request, 'settings_amazon/category.html')

# カテゴリー親


@login_required
def category_parent(request):
    if (request.method == 'POST'):
        selected_values = request.POST.getlist('selected')
        AmazonParentCategoryUser.objects.filter(author=request.user).delete()
        datas = AmazonParentCategory.objects.filter(value__in=selected_values)
        i = 0
        for data in datas:
            i = i+1
            model = AmazonParentCategoryUser()
            model.display_order = i
            model.name = data.name
            model.value = data.value
            model.author = request.user
            model.save()

    return render(request, 'settings_amazon/category_parent.html')

# カテゴリー子供


@login_required
def category_child(request):
    if (request.method == 'POST'):
        selected_values = request.POST.getlist('selected')
        category = request.POST.get('category')
        sys_model = get_child_model_class(category)
        user_model = get_child_user_model_class(category)
        user_model.objects.filter(author=request.user).delete()
        datas = sys_model.objects.filter(value__in=selected_values)
        i = 0
        for data in datas:
            i = i+1
            model = user_model()
            model.display_order = i
            model.name = data.name
            model.format = data.format
            model.feed_product_type = data.feed_product_type
            model.value = data.value
            model.author = request.user
            model.save()

    return render(request, 'settings_amazon/category_child.html')

# 選択可能な大カテゴリー


class AmazonParentCategorySerializerViewSet(LoginRequiredMixin, viewsets.ModelViewSet):
    login_url = '/'
    redirect_field_name = 'redirect_to'
    queryset = AmazonParentCategory.objects.none()
    serializer_class = AmazonParentCategorySerializer

    def get_queryset(self):
        user = self.request.user
        names = AmazonParentCategoryUser.objects.filter(
            author=user).values_list('name')
        return AmazonParentCategory.objects.exclude(name__in=names)

# 選択済み大カテゴリー


class AmazonParentCategoryUserSerializerViewSet(LoginRequiredMixin, viewsets.ModelViewSet):
    login_url = '/'
    redirect_field_name = 'redirect_to'
    queryset = AmazonParentCategoryUser.objects.none()
    serializer_class = AmazonParentCategoryUserSerializer

    def get_queryset(self):
        user = self.request.user
        return AmazonParentCategoryUser.objects.filter(author=user)

# 選択可能な 詳細カテゴリー


class AmazonChildCategorySerializerViewSet(LoginRequiredMixin, viewsets.ModelViewSet):
    login_url = '/'
    redirect_field_name = 'redirect_to'
    queryset = AmazonHobbiesCategory.objects.none()

    def get_queryset(self):
        category = self.request.GET.get('category')
        user = self.request.user
        names = get_child_user_model_class(category).objects.filter(
            author=user).values_list('name')
        return get_child_model_class(category).objects.exclude(name__in=names)

    def get_serializer_class(self):
        category = self.request.GET.get('category')
        return get_child_serializer_class(category)

# 選択済み詳細カテゴリー


class AmazonChildCategoryUserSerializerViewSet(LoginRequiredMixin, viewsets.ModelViewSet):
    login_url = '/'
    redirect_field_name = 'redirect_to'
    queryset = AmazonHobbiesCategoryUser.objects.none()

    def get_queryset(self):
        category = self.request.GET.get('category')
        user = self.request.user
        return get_child_user_model_class(category).objects.filter(author=user)

    def get_serializer_class(self):
        category = self.request.GET.get('category')
        return get_child_user_serializer_class(category)


# メーカ名
class AmazonBrandSerializerViewSet(LoginRequiredMixin, viewsets.ModelViewSet):
    login_url = '/'
    redirect_field_name = 'redirect_to'
    queryset = AmazonBrand.objects.none()
    serializer_class = AmazonBrandSerializer
    def get_queryset(self):
        return AmazonBrand.objects.filter(author=self.request.user)


# ------ 以下モデルを追加 ------

# 子カテゴリー(システム用)
def get_child_model_class(category):
    if category == 'Hobbies':
        return AmazonHobbiesCategory
    elif category == 'PetSupplies':
        return AmazonPetSuppliesCategory
    else:
        return None

# 子カテゴリー(ユーザ用)


def get_child_user_model_class(category):
    if category == 'Hobbies':
        return AmazonHobbiesCategoryUser
    elif category == 'PetSupplies':
        return AmazonPetSuppliesCategoryUser
    else:
        print('Not Found get_child_user_model_class ' + category)
        return None

# シリアライザー(システム用)


def get_child_serializer_class(category):
    if category == 'Hobbies':
        return AmazonHobbiesCategorySerializer
    elif category == 'PetSupplies':
        return AmazonPetSuppliesCategorySerializer
    else:
        print('Not Found get_child_serializer_class ' + category)
        return None

# シリアライザー(ユーザ用)


def get_child_user_serializer_class(category):
    if category == 'Hobbies':
        return AmazonHobbiesCategoryUserSerializer
    elif category == 'PetSupplies':
        return AmazonPetSuppliesCategoryUserSerializer
    else:
        print('Not Found get_child_user_serializer_class ' + category)
        return None
