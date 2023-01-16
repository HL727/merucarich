from django.db import models
from django.core.validators import MaxValueValidator
from django.dispatch import receiver
from django.conf import settings
from richs_utils import RichsUtils


import os


class YahooExcludeSeller(models.Model):
    class Meta:
        db_table = 'yahoo_exclude_seller'
        verbose_name = '禁止セラー個別設定'
        verbose_name_plural = '禁止セラー個別設定'

    seller_id = models.CharField(verbose_name="セラーID", max_length=128,db_index=True)
    memo = models.CharField(verbose_name="メモ", max_length=128, null=True, blank=True)
    author = models.ForeignKey('accounts.User', verbose_name="ユーザ名", on_delete=models.CASCADE,db_index=True) 
    created_date = models.DateTimeField(verbose_name="作成日", auto_now_add=True)
    updated_date = models.DateTimeField(verbose_name="更新日", auto_now=True)

    def __str__(self):
        return '[{}] {}'.format(self.author.username, self.seller_id)

# 禁止セラーのマスター
class YahooExcludeSellerMaster(models.Model):
    class Meta:
        db_table = 'yahoo_exclude_seller_master'
        verbose_name = '新規ユーザー禁止セラーマスタ'
        verbose_name_plural = '新規ユーザー禁止セラーマスタ'



    seller_id = models.CharField(verbose_name="セラーID", max_length=128,db_index=True)

    
    def __str__(self):
        return self.seller_id

# プルダウンの選択肢
CONDITION_CHOICES = (
    ('New', '新品'),
    ('Refurbished', '再生品'),
    ('UsedLikeNew', '中古-ほぼ新品'),
    ('UsedVeryGood', '中古-非常に良い'),
    ('UsedGood', '中古-良い'),
    ('UsedAcceptable', '中古-可'),
    ('CollectibleLikeNew', 'コレクター商品-ほぼ新品'),
    ('CollectibleVeryGood', 'コレクター商品-非常に良い'),    
    ('CollectibleGood', 'コレクター商品-良い'),
    ('CollectibleAcceptable', 'コレクター商品-可'),
)

# 商品コードのタイプ
EXTERNAL_PRODUCT_ID_TYPE_CHOICES = (
    ('EAN','EAN'),
    ('ISBN','ISBN'),
    ('UPC','UPC'),
    ('ASIN','ASIN'),
    ('GTIN','GTIN'),
)

# 出品商品
class YahooToAmazonItem(models.Model):
    class Meta:
        db_table = 'yahoo_to_amazon_item'

    local_id = None
    status_message = None
    inventory_message= None
    feed_type= models.IntegerField(verbose_name="出品種別",null=True) # 0:新規, 1:相乗り, 3:取り込み, 4:取り込み更新中
    item_sku= models.CharField(verbose_name="出品者SKU",max_length=64,null=True, db_index=True)
    item_name= models.CharField(verbose_name="商品名",max_length=256,null=True, db_index=True) 
    external_product_id= models.CharField(verbose_name="商品コード(JANコード等)",max_length=64,null=True, blank=True)
    external_product_id_type= models.CharField(verbose_name="商品コードのタイプ",max_length=16,null=True, blank=True,choices=EXTERNAL_PRODUCT_ID_TYPE_CHOICES)
    brand_name= models.CharField(verbose_name="ブランド名",max_length=256,null=True, blank=True)
    manufacturer= models.CharField(verbose_name="メーカー名",max_length=256,null=True, blank=True)
    feed_product_type= models.CharField(verbose_name="商品タイプ",max_length=64,null=True, blank=True)
    part_number= models.CharField(verbose_name="メーカー型番",max_length=256,null=True, blank=True)
    product_description= models.TextField(verbose_name="商品説明文",null=True, blank=True)
    bullet_point = models.TextField(verbose_name="商品の仕様",null=True, blank=True)
    model= models.CharField(verbose_name="型番",max_length=256,null=True, blank=True)
    quantity = models.IntegerField(verbose_name="在庫数(登録時)",null=True, blank=True)
    fulfillment_latency= models.IntegerField(verbose_name="リードタイム(登録時)",null=True, blank=True,db_index=True) 
    condition_type= models.CharField(verbose_name="商品のコンディション",max_length=32,choices=CONDITION_CHOICES,null=True, blank=True)
    standard_price= models.IntegerField(verbose_name="商品の販売価格",null=True)
    standard_price_points= models.IntegerField(verbose_name="ポイント",null=True, blank=True, validators=[MaxValueValidator(50)])
    condition_note= models.TextField(verbose_name="商品のコンディション説明",null=True)
    item_weight= models.IntegerField(verbose_name="商品の重量",null=True, blank=True)
    item_weight_unit_of_measure= models.CharField(verbose_name="商品の重量の単位",max_length=16,null=True, blank=True)
    item_height= models.IntegerField(verbose_name="商品の高さ",null=True, blank=True)
    item_length= models.IntegerField(verbose_name="商品の長さ",null=True, blank=True)
    item_width= models.IntegerField(verbose_name="商品の幅",null=True, blank=True)
    item_length_unit_of_measure= models.CharField(verbose_name="商品寸法の単位",max_length=16,null=True, blank=True)
    recommended_browse_nodes= models.CharField(verbose_name="推奨ブラウズノード",max_length=64,null=True, blank=True)
    generic_keywords= models.CharField(verbose_name="検索キーワード",max_length=256,null=True, blank=True)
    main_image_url= models.CharField(verbose_name="商品メイン画像URL",max_length=256,null=True)
    other_image_url1= models.CharField(verbose_name="商品サブ画像URL1",max_length=256,null=True, blank=True)
    other_image_url2= models.CharField(verbose_name="商品サブ画像URL2",max_length=256,null=True, blank=True)
    other_image_url3= models.CharField(verbose_name="商品サブ画像URL3",max_length=256,null=True, blank=True)    
    csv_flag= models.IntegerField(verbose_name="CSV出力状態",null=True,db_index=True) 
    format= models.CharField(verbose_name="フォーマット",max_length=32,null=True, blank=True,db_index=True) 
    category= models.CharField(verbose_name="カテゴリー",max_length=32,null=True, blank=True)
    purchaseo_seller_id= models.CharField(verbose_name="セーラーID(初回仕入れ時)",max_length=64,null=True, blank=True)
    purchase_item_id= models.CharField(verbose_name="商品ID(登録時)",max_length=64,null=True, blank=True)
    purchase_quantity= models.IntegerField(verbose_name="仕入数(初回仕入れ時)",null=True, blank=True)
    purchase_fulfillment_latency= models.IntegerField(verbose_name="リードタイム(初回仕入れ時)",null=True, blank=True,db_index=True) 
    purchase_price= models.IntegerField(verbose_name="仕入れ価格(初回仕入れ時)",null=True, blank=True)
    purchase_similarity= models.FloatField(verbose_name="類似度(初回仕入れ時)",null=True, blank=True)
    current_purchase_seller_id= models.CharField(verbose_name="セーラーID(現在)",max_length=32,null=True, blank=True,db_index=True)
    current_purchase_item_id= models.CharField(verbose_name="商品ID(現在)",max_length=32,null=True, blank=True,db_index=True) 
    current_purchase_quantity= models.IntegerField(verbose_name="仕入数(現在)",null=True, blank=True)
    current_purchase_fulfillment_latency= models.IntegerField(verbose_name="リードタイム(現在)",null=True, blank=True,db_index=True) 
    current_purchase_price= models.IntegerField(verbose_name="仕入れ価格(現在)",null=True, blank=True)
    current_similarity= models.FloatField(verbose_name="類似度(現在)",null=True, blank=True)
    amazon_price= models.IntegerField(verbose_name="アマゾン最安値",null=True, blank=True)

    update_fulfillment_latency_request = models.BooleanField(verbose_name="リードタイム更新要求",null=True, blank=True, db_index=True)
    research_request = models.BooleanField(verbose_name="在庫検索要求", null=True, blank=True, db_index=True)
    update_quantity_request = models.BooleanField(verbose_name="在庫更新要求", null=True, blank=True, db_index=True)

    # 0:確定レコード
    # 1X: インポート中, 10:CSVロード直後, 12:メルカリで商品収集完了, 13:アマゾンで商品情報収集完了,     
    # 2X:               20:取り下げ   21:復活中


    record_type = models.IntegerField(verbose_name="レコードタイプ",null=True, blank=True, db_index=True)
    
    author = models.ForeignKey('accounts.User', verbose_name="ユーザ名", on_delete=models.CASCADE,db_index=True) 
    created_date = models.DateTimeField(verbose_name="作成日", auto_now_add=True)
    updated_date = models.DateTimeField(verbose_name="更新日", auto_now=True)

    def __str__(self):
        return self.item_sku

# ファイルを削除する。
@receiver(models.signals.post_delete, sender=YahooToAmazonItem)
def delete_file(sender, instance, **kwargs):    
    base_dir = os.path.join(settings.RICHS_FOLDER_IMAGE, 'yahoo', instance.author.username)
    try:
        RichsUtils.delete_file(base_dir, instance.main_image_url)
        RichsUtils.delete_file(base_dir, instance.other_image_url1)
        RichsUtils.delete_file(base_dir, instance.other_image_url2)
        RichsUtils.delete_file(base_dir, instance.other_image_url3)
    except:
        pass


# 出品商品
class YahooToAmazonItemCandidate(models.Model):
    class Meta:
        db_table = 'yahoo_to_amazon_item_candidate'

    local_id = None
    status_message = None
    inventory_message= None
    feed_type= models.IntegerField(verbose_name="出品種別",null=True) # 0:新規, 1:相乗り, 3:取り込み
    item_sku= models.CharField(verbose_name="出品者SKU",max_length=64,null=True, db_index=True)
    item_name= models.CharField(verbose_name="商品名",max_length=256,null=True, db_index=True) 
    external_product_id= models.CharField(verbose_name="商品コード(JANコード等)",max_length=64,null=True, blank=True)
    external_product_id_type= models.CharField(verbose_name="商品コードのタイプ",max_length=16,null=True, blank=True,choices=EXTERNAL_PRODUCT_ID_TYPE_CHOICES)
    brand_name= models.CharField(verbose_name="ブランド名",max_length=256,null=True, blank=True)
    manufacturer= models.CharField(verbose_name="メーカー名",max_length=256,null=True, blank=True)
    feed_product_type= models.CharField(verbose_name="商品タイプ",max_length=64,null=True, blank=True)
    part_number= models.CharField(verbose_name="メーカー型番",max_length=256,null=True, blank=True)
    product_description= models.TextField(verbose_name="商品説明文",null=True, blank=True)
    bullet_point = models.TextField(verbose_name="商品の仕様",null=True, blank=True)
    model= models.CharField(verbose_name="型番",max_length=256,null=True, blank=True)
    quantity = models.IntegerField(verbose_name="在庫数(登録時)",null=True, blank=True)
    fulfillment_latency= models.IntegerField(verbose_name="リードタイム(登録時)",null=True, blank=True,db_index=True) 
    condition_type= models.CharField(verbose_name="商品のコンディション",max_length=32,choices=CONDITION_CHOICES,null=True, blank=True)
    standard_price= models.IntegerField(verbose_name="商品の販売価格",null=True)
    standard_price_points= models.IntegerField(verbose_name="ポイント",null=True, blank=True, validators=[MaxValueValidator(50)])
    condition_note= models.TextField(verbose_name="商品のコンディション説明",null=True)
    item_weight= models.IntegerField(verbose_name="商品の重量",null=True, blank=True)
    item_weight_unit_of_measure= models.CharField(verbose_name="商品の重量の単位",max_length=16,null=True, blank=True)
    item_height= models.IntegerField(verbose_name="商品の高さ",null=True, blank=True)
    item_length= models.IntegerField(verbose_name="商品の長さ",null=True, blank=True)
    item_width= models.IntegerField(verbose_name="商品の幅",null=True, blank=True)
    item_length_unit_of_measure= models.CharField(verbose_name="商品寸法の単位",max_length=16,null=True, blank=True)
    recommended_browse_nodes= models.CharField(verbose_name="推奨ブラウズノード",max_length=64,null=True, blank=True)
    generic_keywords= models.CharField(verbose_name="検索キーワード",max_length=256,null=True, blank=True)
    main_image_url= models.CharField(verbose_name="商品メイン画像URL",max_length=256,null=True)
    other_image_url1= models.CharField(verbose_name="商品サブ画像URL1",max_length=256,null=True, blank=True)
    other_image_url2= models.CharField(verbose_name="商品サブ画像URL2",max_length=256,null=True, blank=True)
    other_image_url3= models.CharField(verbose_name="商品サブ画像URL3",max_length=256,null=True, blank=True)    
    csv_flag= models.IntegerField(verbose_name="CSV出力状態",null=True,db_index=True) 
    format= models.CharField(verbose_name="フォーマット",max_length=32,null=True, blank=True,db_index=True) 
    category= models.CharField(verbose_name="カテゴリー",max_length=32,null=True, blank=True)
    purchaseo_seller_id= models.CharField(verbose_name="セーラーID(初回仕入れ時)",max_length=64,null=True, blank=True)
    purchase_item_id= models.CharField(verbose_name="商品ID(登録時)",max_length=64,null=True, blank=True)
    purchase_quantity= models.IntegerField(verbose_name="仕入数(初回仕入れ時)",null=True, blank=True)
    purchase_fulfillment_latency= models.IntegerField(verbose_name="リードタイム(初回仕入れ時)",null=True, blank=True,db_index=True) 
    purchase_price= models.IntegerField(verbose_name="仕入れ価格(初回仕入れ時)",null=True, blank=True)
    purchase_similarity= models.FloatField(verbose_name="類似度(初回仕入れ時)",null=True, blank=True)
    current_purchase_seller_id= models.CharField(verbose_name="セーラーID(現在)",max_length=32,null=True, blank=True,db_index=True)
    current_purchase_item_id= models.CharField(verbose_name="商品ID(現在)",max_length=32,null=True, blank=True,db_index=True) 
    current_purchase_quantity= models.IntegerField(verbose_name="仕入数(現在)",null=True, blank=True)
    current_purchase_fulfillment_latency= models.IntegerField(verbose_name="リードタイム(現在)",null=True, blank=True,db_index=True) 
    current_purchase_price= models.IntegerField(verbose_name="仕入れ価格(現在)",null=True, blank=True)
    current_similarity= models.FloatField(verbose_name="類似度(現在)",null=True, blank=True)
    amazon_price= models.IntegerField(verbose_name="アマゾン最安値",null=True, blank=True)

    update_fulfillment_latency_request = models.BooleanField(verbose_name="リードタイム更新要求",null=True, blank=True, db_index=True)
    research_request = models.BooleanField(verbose_name="在庫検索要求", null=True, blank=True, db_index=True)
    update_quantity_request = models.BooleanField(verbose_name="在庫更新要求", null=True, blank=True, db_index=True)

    # 0:確定レコード
    # 1X: インポート中, 10:CSVロード直後, 12:メルカリで商品収集完了, 13:アマゾンで商品情報収集完了,     
    # 2X:               20:取り下げ   21:復活中


    record_type = models.IntegerField(verbose_name="レコードタイプ",null=True, blank=True, db_index=True)
    
    author = models.ForeignKey('accounts.User', verbose_name="ユーザ名", on_delete=models.CASCADE,db_index=True) 
    created_date = models.DateTimeField(verbose_name="作成日", auto_now_add=True)
    updated_date = models.DateTimeField(verbose_name="更新日", auto_now=True)

    def __str__(self):
        return self.item_sku

    def delete_file(self):
        ''' ファイルの削除 '''
        base_dir = os.path.join(settings.RICHS_FOLDER_IMAGE, 'yahoo', self.author.username)
        try:
            RichsUtils.delete_file(base_dir, self.main_image_url)
            RichsUtils.delete_file(base_dir, self.other_image_url1)
            RichsUtils.delete_file(base_dir, self.other_image_url2)
            RichsUtils.delete_file(base_dir, self.other_image_url3)
        except:
            pass


# CSV管理テーブル
class YahooToAmazonCSV(models.Model):
    class Meta:
        db_table = 'yahoo_to_amazon_csv'

    local_id = None
    feed_type= models.IntegerField(verbose_name="出品種別")
    file_name = models.CharField(verbose_name="ファイル名",max_length=64)
    author = models.ForeignKey('accounts.User', verbose_name="ユーザ名", on_delete=models.CASCADE,db_index=True) 
    created_date = models.DateTimeField(verbose_name="作成日", auto_now_add=True)
    updated_date = models.DateTimeField(verbose_name="更新日", auto_now=True)


# 商品取り込み履歴
class YahooImportCSVResult(models.Model):
    class Meta:
        db_table = 'yahoo_import_csv_result'
        verbose_name = '商品取り込み履歴'
        verbose_name_plural = '商品取り込み履歴'

    local_id = None

    success = models.IntegerField(verbose_name="正常処理件数", null=True, blank=True)
    error_record_numbers = models.IntegerField(verbose_name="フォーマットエラー件数", null=True, blank=True)
    error_record_numbers_txt= models.TextField(verbose_name="フォーマットエラー一覧", null=True, blank=True)
    duplicate_skus =  models.IntegerField(verbose_name="重複件数", null=True, blank=True)
    duplicate_skus_txt= models.TextField(verbose_name="重複一覧", null=True, blank=True)
    over_skus = models.IntegerField(verbose_name="登録オーバ件数", null=True, blank=True)
    over_skus_text = models.TextField(verbose_name="登録オーバ一覧", null=True, blank=True)
    error_yahoo_items = models.IntegerField(verbose_name="オークション該当商品無し", null=True, blank=True)
    error_yahoo_items_txt = models.TextField(verbose_name="オークション該当商品無し", null=True, blank=True)
    error_asins = models.IntegerField(verbose_name="ASINエラー", null=True, blank=True)
    error_asins_text = models.TextField(verbose_name="ASINエラー一覧", null=True, blank=True)
    error_skus = models.IntegerField(verbose_name="SKUエラー", null=True, blank=True)
    error_skus_text = models.TextField(verbose_name="SKUエラー一覧", null=True, blank=True)
    status = models.IntegerField(verbose_name="ステータス", null=True, blank=True)
    user_check =  models.BooleanField(verbose_name="ユーザ確認", null=True, blank=True)
    author = models.ForeignKey('accounts.User', verbose_name="ユーザ名", on_delete=models.CASCADE, db_index=True) 
    start_date = models.DateTimeField(verbose_name="登録日", auto_now_add=True)
    end_date = models.DateTimeField(verbose_name="完了日", null=True, blank=True)
    updated_date = models.DateTimeField(verbose_name="更新日", auto_now=True)
    result_message = models.TextField(verbose_name="処理結果", null=True, blank=True)

    def __str__(self):
        return self.author.username
