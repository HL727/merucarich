from django import forms
from .models import AmazonAPI, AmazonDefaultSettings, AmazonBrand, AmazonFeedPriceSettings, ExcludeAsin

# API設定


class AmazonAPIForm(forms.ModelForm):
    class Meta:
        model = AmazonAPI
        fields = ['account_id', 'auth_token']

# デフォルト設定


class AmazonDefaultSettingsForm(forms.ModelForm):
    class Meta:
        model = AmazonDefaultSettings
        fields = [
            'condition_type', 'condition_note', 'part_number',
            'fulfillment_latency', 'standard_price_points',
            'new_item_points', 'new_auto_item_points', 'ride_item_points',
        ]

    def __init__(self, *args, **kwargs):
        super(AmazonDefaultSettingsForm, self).__init__(*args, **kwargs)
        self.fields['condition_type'].required = False
        self.fields['condition_note'].required = False
        self.fields['part_number'].required = False
        self.fields['fulfillment_latency'].required = False
        self.fields['standard_price_points'].required = False
        self.fields['new_item_points'].required = False
        self.fields['new_auto_item_points'].required = False
        self.fields['ride_item_points'].required = False


# ブランド設定
class AmazonBrandForm(forms.ModelForm):
    class Meta:
        model = AmazonBrand
        fields = ['brand_name']


# 禁止ASIN
class ExcludeAsinForm(forms.ModelForm):
    class Meta:
        model = ExcludeAsin
        fields = ['asin', 'memo']


# 上乗せ金額設定
class AmazonFeedPriceSettingsForm(forms.ModelForm):
    class Meta:
        model = AmazonFeedPriceSettings
        fields = ['margin_new', 'margin_offer', 'default_minimum_item_price', 'margin_offer_url',
                  'margin_offer_percent_url', 'offset_offer_price_url', 'lowest_offer_price_url']
