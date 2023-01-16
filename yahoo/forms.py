from django import forms
from django.forms.widgets import NumberInput

from .models import *
#from .models import YahooExcludeSeller,YahooToAmazonItem,YahooToAmazonCSV,YahooImportCSVResult

class YahooExcludeSellerForm(forms.ModelForm):
    class Meta:
        model  = YahooExcludeSeller
        fields = ['seller_id', 'memo' ]


class AmazonSearchForm(forms.Form):
    keyword = forms.CharField(label='検索キーワード')
        
class YahooSearchForm(forms.Form):

    data1=[
        ('0','キーワードより商品検索'),             #
        ('1','セラーIDを指定して商品検索'),         # https://auctions.yahoo.co.jp/seller/life_partners_sapporo
        ('2','オークションIDを指定して商品検索'),   # 
    ]
    
    # 並び順の項目
    data2=[
        ('23','おすすめ順'),  #select=1
        ('1','価格の安い順'),
        ('2','価格の高い順'),
        ('3','入札の多い順'),        
        ('4','入札の少ない順'),
        ('5','残り時間の短い順'),
        ('6','残り時間の長い順'),
        ('7','即決価格の安い順'),
        ('8','即決価格の高い順'),
        ('22','新着順'),
    ]


    # 商品状態：
    data3=[
        ('0','指定なし'), #istatus=0
        ('1','新品'),     #istatus=1
        ('2','中古'),     #istatus=2
    ]

    # 出品者：
    data4=[
        ('0','すべての商品'), #abatch=0
        ('1','ストアの出品'), #abatch=1
        ('2','個人の出品'),   #abatch=1
    ]


    # 画像有無：
    data5=[
        ('0','指定なし'), #パラメータが付かない。。
        ('1','画像あり'), #thumb=1
    ]

    # 即決価格
    # tanaka
    data6=[
        ('0','指定あり'),
        ('1','指定なし'), 
    ]
    
    #
    search_type = forms.ChoiceField(label='検索方法', choices=data1)
    va = forms.CharField(label='検索キーワード')
    select = forms.ChoiceField(label='並び順の項目', choices=data2)
    istatus = forms.ChoiceField(label='商品状態', choices=data3)

    # 現在価格
    aucminprice = forms.CharField(label='現在価格', required=False)
    aucmaxprice = forms.CharField(label='現在価格', required=False)

    # 即決価格
    is_exist_bidorbuy_price = forms.ChoiceField(label='即決価格有無', choices=data6)   

    aucmin_bidorbuy_price = forms.CharField(label='即決価格', required=False)
    aucmax_bidorbuy_price = forms.CharField(label='即決価格', required=False)

    # 
    abatch = forms.ChoiceField(label='出品者', choices=data4)
    thumb  = forms.ChoiceField(label='画像有無', choices=data5)


# 新規画面
class FeedNewForm(forms.ModelForm):

    current_price  = forms.IntegerField( widget=forms.HiddenInput )
    bid_or_buy = forms.IntegerField( widget=forms.HiddenInput )

    class Meta:
        model=YahooToAmazonItem
        fields=['item_sku','item_name','external_product_id','external_product_id_type','brand_name','manufacturer','part_number','product_description', 'bullet_point'  ,\
                'quantity','fulfillment_latency','standard_price','standard_price_points','condition_type','condition_note', 'category', 'recommended_browse_nodes','generic_keywords','main_image_url','other_image_url1','other_image_url2','other_image_url3', 'purchaseo_seller_id']
        widgets = {'purchaseo_seller_id': forms.HiddenInput()}
 
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
        self.fields['bid_or_buy'].required = False
        # 以下、編集画面では、利用しないため。
        self.fields['purchaseo_seller_id'].required = False
        self.fields['current_price'].required = False
        
# 相乗り
class FeedOfferForm(forms.ModelForm):

    current_price  = forms.IntegerField( widget=forms.HiddenInput )
    bid_or_buy = forms.IntegerField( widget=forms.HiddenInput )
    amazon_price_new = forms.CharField( widget=forms.HiddenInput )
    amazon_price_used = forms.CharField( widget=forms.HiddenInput )

    class Meta:
        model=YahooToAmazonItem
        fields=['item_sku','external_product_id_type','external_product_id','condition_type','condition_note','standard_price','standard_price_points' ,'quantity','fulfillment_latency', 'main_image_url']
        widgets = {'purchaseo_seller_id': forms.HiddenInput(),'main_image_url':forms.HiddenInput()}
 
    def __init__(self, *args, **kwargs):
        super(FeedOfferForm, self).__init__(*args, **kwargs)
        self.fields['condition_note'].required = False
        self.fields['standard_price_points'].required = False
        # 以下、編集画面では、利用しないため。)
        #self.fields['purchaseo_seller_id'].required = False
        self.fields['main_image_url'].required = False
        self.fields['current_price'].required = False
        self.fields['amazon_price_new'].required = False
        self.fields['amazon_price_used'].required = False
        self.fields['bid_or_buy'].required = False


# Amazon相乗り検索フォーム        
class AmazonOfferYahooSearchForm(forms.Form):

    # Amazon相乗り商品検索条件指定
    data1=[
        ('0','Amazon URL'), 
        ('1','キーワード検索'), 
    ]
    
    amazon_search_type = forms.ChoiceField(label='検索方法', widget=forms.RadioSelect(), choices=data1)
    keyword = forms.CharField(label='Amazon URL/検索キーワード')
    extra_keyword1 = forms.CharField(label='Amazon URL/検索キーワード', required=False)
    extra_keyword2 = forms.CharField(label='Amazon URL/検索キーワード', required=False)
    extra_keyword3 = forms.CharField(label='Amazon URL/検索キーワード', required=False)
    extra_keyword4 = forms.CharField(label='Amazon URL/検索キーワード', required=False)
    extra_keyword5 = forms.CharField(label='Amazon URL/検索キーワード', required=False)
    extra_keyword6 = forms.CharField(label='Amazon URL/検索キーワード', required=False)
    extra_keyword7 = forms.CharField(label='Amazon URL/検索キーワード', required=False)
    extra_keyword8 = forms.CharField(label='Amazon URL/検索キーワード', required=False)
    extra_keyword9 = forms.CharField(label='Amazon URL/検索キーワード', required=False)
            
    data2=[
        ('0','タイトル'),             #
        ('1','タイトルと商品説明'),   # https://auctions.yahoo.co.jp/seller/life_partners_sapporo
        ('2','あいまい検索'),         # 
    ]
    
    # 並び順の項目
    data3=[
        ('23','おすすめ順'),  #select=1
        ('1','価格の安い順'),
        ('2','価格の高い順'),
        ('3','入札の多い順'),        
        ('4','入札の少ない順'),
        ('5','残り時間の短い順'),
        ('6','残り時間の長い順'),
        ('7','即決価格の安い順'),
        ('8','即決価格の高い順'),
        ('22','新着順'),
    ]

    # 商品状態：
    data4=[
        ('0','指定なし'), #istatus=0
        ('1','新品'),     #istatus=1
        ('2','中古'),     #istatus=2
    ]

    # 出品者：
    data5=[
        ('0','すべての商品'), #abatch=0
        ('1','ストアの出品'), #abatch=1
        ('2','個人の出品'),   #abatch=1
    ]

    # 即決価格
    # tanaka
    data6=[
        ('0','指定あり'),
        ('1','指定なし'), 
    ]

    # CSV出力
    data7=[
        ('0','しない'),
        ('1','する'), 
    ]

    similarity = forms.FloatField(label='画像類似度', max_value=1, min_value=0, widget=NumberInput(attrs={'step': "0.1"}))
    rateing = forms.FloatField(label='良評価', max_value=100, min_value=0, widget=NumberInput(attrs={'step': "0.1"}))
    search_type = forms.ChoiceField(label='検索方法', choices=data2)
    select = forms.ChoiceField(label='検索優先順位', choices=data3)
    istatus = forms.ChoiceField(label='商品状態', choices=data4)
    abatch = forms.ChoiceField(label='出品者', choices=data5)
    is_exist_bidorbuy_price = forms.ChoiceField(label='即決価格有無', choices=data6)
    is_export_csv  = forms.ChoiceField(label='ファイルダウンロード出力', choices=data7)
    


#商品一覧
class YahooItemListSearchForm(forms.Form):
    data1=[
        ('0','商品タイトル'), 
        ('1','Amazon SKU'), 
        ('2','仕入れ元オークションID'), 
        ('3','出品者ID'), 
        ('4','リードタイム'), 
    ]    
        
    data2=[
        ('0','完全一致'), 
        ('1','部分一致'), 
    ]    

    search_type = forms.ChoiceField(label='検索方法', choices=data1)
    search_condition = forms.ChoiceField(label='検索条件', choices=data2)
    keyword = forms.CharField(label='検索キーワード')
    top_timestamp = forms.CharField(label='先頭商品更新時間', widget=forms.HiddenInput)
    page = forms.IntegerField(label='ページ番号', widget=forms.HiddenInput)
    def __init__(self, *args, **kwargs):
        super(YahooItemListSearchForm, self).__init__(*args, **kwargs)
        self.fields['keyword'].required = False
        self.fields['top_timestamp'].required = False


