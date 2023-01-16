from django.db import models
from django.core.validators import MaxValueValidator

# AmazonAPI設定


class AmazonAPI(models.Model):
    class Meta:
        db_table = 'amazon_api'
        verbose_name = 'API設定(各ユーザ)'
        verbose_name_plural = 'API設定(各ユーザ)'

    access_key = None
    secret_key = None
    region = None
    marketplace_id = None

    account_id = models.CharField(verbose_name="出品者ID", max_length=128)
    auth_token = models.CharField(
        verbose_name="認証トークン", max_length=128, null=True)
    author = models.ForeignKey(
        'accounts.User', on_delete=models.CASCADE, db_index=True)
    created_date = models.DateTimeField(verbose_name="作成日", auto_now_add=True)
    updated_date = models.DateTimeField(verbose_name="更新日", auto_now=True)
    validated_date = models.DateTimeField(verbose_name="検証日時", null=True)

    def __str__(self):
        return self.account_id


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

# Amazonデフォルト設定


class AmazonDefaultSettings(models.Model):
    class Meta:
        db_table = 'amazon_default_settings'

    condition_type = models.CharField(
        verbose_name="コンディション", max_length=32, choices=CONDITION_CHOICES, null=True, blank=True)
    condition_note = models.TextField(
        verbose_name="コンディション説明", null=True, blank=True)
    part_number = models.CharField(
        verbose_name="メーカー型番", max_length=128, null=True, blank=True)
    fulfillment_latency = models.IntegerField(
        verbose_name="リードタイム（日）", null=True, blank=True)
    standard_price_points = models.IntegerField(
        verbose_name="ポイント(デフォルト値)", null=True, blank=True, default=0, validators=[MaxValueValidator(50)])
    new_item_points = models.IntegerField(
        verbose_name="ポイント(新規出品)", null=True, blank=True)
    new_auto_item_points = models.IntegerField(
        verbose_name="ポイント(新規出品自動化)", null=True, blank=True)
    ride_item_points = models.IntegerField(
        verbose_name="ポイント(相乗り出品)", null=True, blank=True)
    author = models.ForeignKey('accounts.User', on_delete=models.CASCADE)
    created_date = models.DateTimeField(verbose_name="作成日", auto_now_add=True)
    updated_date = models.DateTimeField(verbose_name="更新日", auto_now=True)

    def __str__(self):
        return self.condition_type

# Amazonブランド設定


class AmazonBrand(models.Model):
    class Meta:
        db_table = 'amazon_brand'

    local_id = None
    brand_name = models.CharField(verbose_name="ブランド名", max_length=256)
    author = models.ForeignKey(
        'accounts.User', on_delete=models.CASCADE, db_index=True)
    created_date = models.DateTimeField(verbose_name="作成日", auto_now_add=True)
    updated_date = models.DateTimeField(verbose_name="更新日", auto_now=True)

    def __str__(self):
        return self.brand_name

# 禁止ASIN


class ExcludeAsin(models.Model):
    class Meta:
        db_table = 'amazon_exclude_asin'
        verbose_name = '禁止ASIN個別設定'
        verbose_name_plural = '禁止ASIN個別設定'

    local_id = None
    asin = models.CharField(verbose_name="禁止ASIN", max_length=16)
    memo = models.CharField(
        verbose_name="メモ", max_length=256, null=True, blank=True)
    author = models.ForeignKey(
        'accounts.User', on_delete=models.CASCADE, db_index=True)
    created_date = models.DateTimeField(verbose_name="作成日", auto_now_add=True)
    updated_date = models.DateTimeField(verbose_name="更新日", auto_now=True)

    def __str__(self):
        return '[{}] {}'.format(self.author.username, self.asin)


class ExcludeAsinMaster(models.Model):
    class Meta:
        db_table = 'amazon_exclude_asin_master'
        verbose_name = '新規ユーザー禁止ASINマスタ'
        verbose_name_plural = '新規ユーザー禁止ASINマスタ'

    local_id = None
    asin = models.CharField(verbose_name="禁止ASIN", max_length=16)

    def __str__(self):
        return self.asin


# Amazon出品プライス設定
class AmazonFeedPriceSettings(models.Model):
    class Meta:
        db_table = 'amazon_feed_price_settings'

    margin_new = models.FloatField(verbose_name="新規出品時の利益設定倍率（仕入れ元価格に対する倍率）")
    margin_offer = models.FloatField(
        verbose_name="相乗り出品時の利益設定倍率（仕入れ元価格に対する倍率）")
    margin_new_url = models.IntegerField(verbose_name="金額（円）", null=True)

    margin_offer_url = models.IntegerField(verbose_name="最低利益額（円）", null=True)
    margin_offer_percent_url = models.FloatField(
        verbose_name="最低利益率（％）　※0: チェックしない", null=True, default=0)
    offset_offer_price_url = models.IntegerField(
        verbose_name="相乗り販売価格（円）", null=True)
    lowest_offer_price_url = models.IntegerField(
        verbose_name="最低販売価格（円）", null=True)
    default_minimum_item_price = models.IntegerField(
        verbose_name='新規出品時の最低販売価格(円)', null=True, default=3000)

    author = models.ForeignKey(
        'accounts.User', on_delete=models.CASCADE, db_index=True)
    created_date = models.DateTimeField(verbose_name="作成日", auto_now_add=True)
    updated_date = models.DateTimeField(verbose_name="更新日", auto_now=True)

    def __str__(self):
        return self.author.username


# Amazon大カテゴリー(システム用)
class AmazonParentCategory(models.Model):
    class Meta:
        db_table = 'amazon_parent_category'
        verbose_name = '大カテゴリー設定'
        verbose_name_plural = '大カテゴリー設定'

    display_order = models.IntegerField(verbose_name="表示順序", db_index=True)
    name = models.CharField(verbose_name="名称", max_length=256)
    value = models.CharField(verbose_name="値", max_length=256)
    created_date = models.DateTimeField(verbose_name="作成日", auto_now_add=True)
    updated_date = models.DateTimeField(verbose_name="更新日", auto_now=True)

    def __str__(self):
        return self.name

# Amazon大カテゴリー(ユーザ用)


class AmazonParentCategoryUser(models.Model):
    class Meta:
        db_table = 'amazon_parent_category_user'

    display_order = models.IntegerField(verbose_name="表示順序", db_index=True)
    name = models.CharField(verbose_name="名称", max_length=256)
    value = models.CharField(verbose_name="値", max_length=256, db_index=True)
    author = models.ForeignKey('accounts.User', on_delete=models.CASCADE)
    created_date = models.DateTimeField(verbose_name="作成日", auto_now_add=True)
    updated_date = models.DateTimeField(verbose_name="更新日", auto_now=True)

    def __str__(self):
        return self.name


# CSV
class CSVFormat(models.Model):
    ''' 新規出品フォーマットの Index を指し示す '''
    class Meta:
        db_table = 'amazon_csv_format'
        verbose_name = '新規出品用CSVフォーマット'
        verbose_name_plural = '新規出品用CSVフォーマット'

    format = models.CharField(verbose_name="フォーマット",
                              max_length=64, db_index=True)
    fields = models.IntegerField(verbose_name="フィールド数")
    feed_product_type = models.IntegerField(verbose_name="商品タイプ")
    item_sku = models.IntegerField(verbose_name="出品者SKU")
    brand_name = models.IntegerField(verbose_name="ブランド名")
    item_name = models.IntegerField(verbose_name="商品名")
    external_product_id = models.IntegerField(verbose_name="商品コード(JANコード等)")
    external_product_id_type = models.IntegerField(verbose_name="商品コードのタイプ")
    manufacturer = models.IntegerField(verbose_name="メーカー名")
    recommended_browse_nodes = models.IntegerField(verbose_name="推奨ブラウズノード")
    quantity = models.IntegerField(verbose_name="在庫数")
    standard_price = models.IntegerField(verbose_name="商品の販売価格")
    main_image_url = models.IntegerField(verbose_name="商品メイン画像URL")
    part_number = models.IntegerField(verbose_name="メーカー型番")
    condition_type = models.IntegerField(verbose_name="商品のコンディション")
    condition_note = models.IntegerField(verbose_name="商品のコンディション説明")
    product_description = models.IntegerField(verbose_name="商品説明文")
    bullet_point = models.IntegerField(verbose_name="商品の仕様")
    generic_keywords = models.IntegerField(verbose_name="検索キーワード")
    other_image_url1 = models.IntegerField(verbose_name="商品サブ画像URL1")
    other_image_url2 = models.IntegerField(verbose_name="商品サブ画像URL2")
    other_image_url3 = models.IntegerField(verbose_name="商品サブ画像URL3")
    fulfillment_latency = models.IntegerField(
        verbose_name="リードタイム(出荷までにかかる作業日数)")
    standard_price_points = models.IntegerField(verbose_name="ポイント", validators=[MaxValueValidator(50)])
    is_adult_product = models.IntegerField(default=85, verbose_name="アダルト商品")
    created_date = models.DateTimeField(verbose_name="作成日", auto_now_add=True)
    updated_date = models.DateTimeField(verbose_name="更新日", auto_now=True)

    def __str__(self):
        return self.format

# Amazonシステムカテゴリー（ホビー）
class AmazonHobbiesCategory(models.Model):
    class Meta:
        db_table = 'amazon_hobbies_category'
        verbose_name = '詳細カテゴリー設定(ホビー)'
        verbose_name_plural = '詳細カテゴリー設定(ホビー)'

    display_order = models.IntegerField(verbose_name="表示順序", db_index=True)
    name = models.CharField(verbose_name="名称", max_length=256)
    format = models.CharField(verbose_name="フォーマット", max_length=64)
    feed_product_type = models.CharField(verbose_name="商品タイプ", max_length=64)
    value = models.CharField(verbose_name="推奨ブラウズノード",
                             max_length=64, db_index=True)
    created_date = models.DateTimeField(verbose_name="作成日", auto_now_add=True)
    updated_date = models.DateTimeField(verbose_name="更新日", auto_now=True)

    def __str__(self):
        return self.name


# Amazonユーザカテゴリー（ホビー）
class AmazonHobbiesCategoryUser(models.Model):
    class Meta:
        db_table = 'amazon_hobbies_category_user'

    display_order = models.IntegerField(verbose_name="表示順序", db_index=True)
    name = models.CharField(verbose_name="名称", max_length=256)
    format = models.CharField(verbose_name="フォーマット", max_length=64)
    feed_product_type = models.CharField(verbose_name="商品タイプ", max_length=64)
    value = models.CharField(verbose_name="推奨ブラウズノード", max_length=64)
    author = models.ForeignKey(
        'accounts.User', on_delete=models.CASCADE, db_index=True)
    created_date = models.DateTimeField(verbose_name="作成日", auto_now_add=True)
    updated_date = models.DateTimeField(verbose_name="更新日", auto_now=True)

    def __str__(self):
        return self.name


# Amazonシステムカテゴリー（ペット）
class AmazonPetSuppliesCategory(models.Model):
    class Meta:
        db_table = 'amazon_pet_supplies_category'

    display_order = models.IntegerField(verbose_name="表示順序", db_index=True)
    name = models.CharField(verbose_name="名称", max_length=256)
    format = models.CharField(verbose_name="フォーマット", max_length=64)
    feed_product_type = models.CharField(verbose_name="商品タイプ", max_length=64)
    value = models.CharField(verbose_name="推奨ブラウズノード", max_length=64)
    created_date = models.DateTimeField(verbose_name="作成日", auto_now_add=True)
    updated_date = models.DateTimeField(verbose_name="更新日", auto_now=True)

    def __str__(self):
        return self.name

# Amazonユーザカテゴリー（ペット）
class AmazonPetSuppliesCategoryUser(models.Model):
    class Meta:
        db_table = 'amazon_pet_supplies_category_user'

    display_order = models.IntegerField(verbose_name="表示順序", db_index=True)
    name = models.CharField(verbose_name="名称", max_length=256)
    format = models.CharField(verbose_name="フォーマット", max_length=64)
    feed_product_type = models.CharField(verbose_name="商品タイプ", max_length=64)
    value = models.CharField(verbose_name="推奨ブラウズノード", max_length=64)
    author = models.ForeignKey(
        'accounts.User', on_delete=models.CASCADE, db_index=True)
    created_date = models.DateTimeField(verbose_name="作成日", auto_now_add=True)
    updated_date = models.DateTimeField(verbose_name="更新日", auto_now=True)

    def __str__(self):
        return self.name
