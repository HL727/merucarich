from django import forms
from django.forms.widgets import NumberInput
from .models import MercariExcludeSeller, MercariToAmazonItem

#除外セラー
class MercariExcludeSellerForm(forms.ModelForm):
    class Meta:
        model  = MercariExcludeSeller
        fields = ['seller_id', 'memo' ]

# Amazon検索
class AmazonSearchForm(forms.Form):
    keyword = forms.CharField(label='検索キーワード')


SORT_ORDER_CHOICES = (
    ('standard','通常検索順'),
    ('price_asc','価格の安い順'),
    ('price_desc','価格の高い順'),
    ('created_asc','出品の古い順'),
    ('created_desc','出品の新しい順'),
    ('like_desc','いいねの多い順'),
)

# メルカリ検索
class MercariSearchForm(forms.Form):

    # Amazon相乗り商品検索条件指定
    data1=[
        ('0','キーワードより商品検索 '), 
        ('1','メルカリ商品IDを指定して検索'), 
    ]    
    search_type = forms.ChoiceField(label='検索方法', widget=forms.RadioSelect(), choices=data1)
    keyword = forms.CharField(label='検索キーワード')
    extra_keyword1 = forms.CharField(label='Amazon URL/検索キーワード', required=False)
    extra_keyword2 = forms.CharField(label='Amazon URL/検索キーワード', required=False)
    extra_keyword3 = forms.CharField(label='Amazon URL/検索キーワード', required=False)
    extra_keyword4 = forms.CharField(label='Amazon URL/検索キーワード', required=False)
    extra_keyword5 = forms.CharField(label='Amazon URL/検索キーワード', required=False)
    extra_keyword6 = forms.CharField(label='Amazon URL/検索キーワード', required=False)
    extra_keyword7 = forms.CharField(label='Amazon URL/検索キーワード', required=False)
    extra_keyword8 = forms.CharField(label='Amazon URL/検索キーワード', required=False)
    extra_keyword9 = forms.CharField(label='Amazon URL/検索キーワード', required=False)
 
    # 価格
    price_min= forms.IntegerField(label='最安値', required=False)
    price_max=forms.IntegerField(label='最高値', required=False)

    # 商品の状態
    condition_all = forms.BooleanField(label='すべて',required=False,widget=forms.CheckboxInput(attrs={'class': 'check'}))
    condition_id_1 = forms.BooleanField(label='新品未使用',required=False,widget=forms.CheckboxInput(attrs={'class': 'check'}))
    condition_id_2 = forms.BooleanField(label='未使用に近い',required=False,widget=forms.CheckboxInput(attrs={'class': 'check'}))
    condition_id_3 = forms.BooleanField(label='目立った傷や汚れなし',required=False,widget=forms.CheckboxInput(attrs={'class': 'check'}))
    condition_id_4 = forms.BooleanField(label='やや傷や汚れあり',required=False,widget=forms.CheckboxInput(attrs={'class': 'check'}))
    condition_id_5 = forms.BooleanField(label='傷や汚れあり',required=False,widget=forms.CheckboxInput(attrs={'class': 'check'}))
    condition_id_6 = forms.BooleanField(label='全体的に状態が悪い',required=False,widget=forms.CheckboxInput(attrs={'class': 'check'}))

    # 配送料の負担
    shipping_payer_all = forms.BooleanField(label='すべて',required=False,widget=forms.CheckboxInput(attrs={'class': 'check'}))
    shipping_payer_id_1 = forms.BooleanField(label='着払い(購入者負担) ',required=False,widget=forms.CheckboxInput(attrs={'class': 'check'}))
    shipping_payer_id_2 = forms.BooleanField(label=' 送料込み(出品者負担)',required=False,widget=forms.CheckboxInput(attrs={'class': 'check'}))

    # 販売状況
    status_all = forms.BooleanField(label='すべて',required=False,widget=forms.CheckboxInput(attrs={'class': 'check'}))
    status_id_on_sale = forms.BooleanField(label='販売中',required=False,widget=forms.CheckboxInput(attrs={'class': 'check'}))
    status_id_trading_sold_out  = forms.BooleanField(label='売り切れ',required=False,widget=forms.CheckboxInput(attrs={'class': 'check'}))                     

    #並び順新着順 
    sort_order = forms.ChoiceField(label='並び順', choices=SORT_ORDER_CHOICES, widget=forms.Select())


# 新規出品フォーム
class FeedNewForm(forms.ModelForm):

    current_price  = forms.IntegerField( widget=forms.HiddenInput)

    class Meta:
        model=MercariToAmazonItem
        fields=['item_sku','item_name','external_product_id','external_product_id_type','brand_name','manufacturer','part_number','product_description', 'bullet_point'  ,\
                'quantity','fulfillment_latency','standard_price','standard_price_points','condition_type','condition_note', 'category', 'recommended_browse_nodes','generic_keywords','main_image_url','other_image_url1','other_image_url2','other_image_url3', 'purchaseo_seller_id', 'purchaseo_seller_id_name']
        widgets = {'purchaseo_seller_id': forms.HiddenInput(), 'purchaseo_seller_id_name': forms.HiddenInput()}
 
    def __init__(self, *args, **kwargs):
        super(FeedNewForm, self).__init__(*args, **kwargs)
        self.fields['external_product_id'].required = False
        self.fields['external_product_id_type'].required = False
        self.fields['condition_note'].required = False
        self.fields['generic_keywords'].required = False
        self.fields['standard_price_points'].required = False
        self.fields['other_image_url1'].required = False
        self.fields['other_image_url2'].required = False
        self.fields['other_image_url3'].required = False
        # 以下、編集画面では、利用しないため。
        self.fields['purchaseo_seller_id'].required = False
        self.fields['purchaseo_seller_id_name'].required = False
        self.fields['current_price'].required = False


# 相乗り出品フォーム
class FeedOfferForm(forms.ModelForm):

    current_price  = forms.IntegerField( widget=forms.HiddenInput )
    amazon_price_new = forms.CharField( widget=forms.HiddenInput )
    amazon_price_used = forms.CharField( widget=forms.HiddenInput )

    class Meta:
        model=MercariToAmazonItem
        fields=['item_sku','external_product_id_type','external_product_id','condition_type','condition_note','standard_price','standard_price_points' ,'quantity','fulfillment_latency','main_image_url','purchaseo_seller_id','main_image_url']
        widgets = {'purchaseo_seller_id': forms.HiddenInput(), 'main_image_url': forms.HiddenInput()}
 
    def __init__(self, *args, **kwargs):
        super(FeedOfferForm, self).__init__(*args, **kwargs)
        self.fields['condition_note'].required = False
        self.fields['standard_price_points'].required = False
        # 以下、編集画面では、利用しないため。)
        self.fields['purchaseo_seller_id'].required = False
        self.fields['main_image_url'].required = False
        self.fields['current_price'].required = False
        self.fields['amazon_price_new'].required = False
        self.fields['amazon_price_used'].required = False
        
# Amazon URL検索
class AmazonOfferMercariSearchForm(MercariSearchForm):

    # Amazon相乗り商品検索条件指定
    data1=[
        ('0','Amazon URL'), 
        ('1','キーワード検索'), 
    ]    
    search_type = forms.ChoiceField(label='検索方法', widget=forms.RadioSelect(), choices=data1)
    
    # メルカリ仕入れ商品条件指定
    rateing = forms.FloatField(label='セラー良評価率', max_value=100, min_value=0, widget=NumberInput(attrs={'step': "0.1"}))
    # CSV出力
    data7=[
        ('0','しない'),
        ('1','する'), 
    ]
    similarity = forms.FloatField(label='画像類似度', max_value=1, min_value=0, widget=NumberInput(attrs={'step': "0.1"}))
    sort_order = forms.ChoiceField(label='検索順序', choices=SORT_ORDER_CHOICES)
    is_export_csv  = forms.ChoiceField(label='ファイルダウンロード出力', choices=data7)


#商品一覧
class MercariItemListSearchForm(forms.Form):
    data1=[
        (0,'商品タイトル'), 
        (1,'Amazon SKU'), 
        (2,'メルカリ商品ID'), 
        (3,'出品者ID'), 
        (4,'リードタイム'), 
    ]    
        
    data2=[
        (0,'完全一致'), 
        (1,'部分一致'), 
    ]    

    search_type = forms.ChoiceField(label='検索方法', choices=data1)
    search_condition = forms.ChoiceField(label='検索条件', choices=data2)
    keyword = forms.CharField(label='検索キーワード')
    top_timestamp = forms.CharField(label='先頭商品更新時間', widget=forms.HiddenInput)
    page = forms.IntegerField(label='ページ番号', widget=forms.HiddenInput)
    def __init__(self, *args, **kwargs):
        super(MercariItemListSearchForm, self).__init__(*args, **kwargs)
        self.fields['keyword'].required = False
        self.fields['top_timestamp'].required = False
