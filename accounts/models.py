from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, UserManager
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.mail import send_mail
from django.dispatch import receiver

import re
import uuid as uuid_lib
import importlib


# Create your models here.                                                                                                                                                                                                                                                                                                                                                  

'''
class IPAddress(models.Model):

    address = models.GenericIPAddressField(_('IPアドレス'), primary_key=True, protocol='IPv4')
    author = models.ForeignKey('accounts.User', on_delete=models.DO_NOTHING, related_name='missions_assigned', blank = True, null=True)

    def __str__(self):
        return self.address
    class Meta:
        db_table = 'accounts_ip_address'
        verbose_name = _('IPアドレス')
        verbose_name_plural = _('IPアドレス')
'''

# プルダウンの選択肢
MAX_FEED_ITEM = (
    (20000, '2万件'),
    (40000, '4万件'),
    (50000, '5万件'),
    (10,    '10件(試験用)'),
)

# プルダウンの選択肢
CHECK_TIMES = (
    (2, '2回/日'),
    (4, '4回/日'),
)


class User(AbstractBaseUser, PermissionsMixin):

    """ユーザー AbstractUserをコピペし編集"""

    uuid = models.UUIDField(default=uuid_lib.uuid4,
                            primary_key=True, editable=False)
    username_validator = UnicodeUsernameValidator()

    username = models.CharField(
        _('username'),
        max_length=150,
        unique=True,
        help_text=_(
            'Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.'),
        validators=[username_validator],
        error_messages={
            'unique': _("A user with that username already exists."),
        },
    )
    full_name = models.CharField(_('氏名'), max_length=150, blank=True)
    email = models.EmailField(_('email address'), blank=True)
    max_items = models.IntegerField(_('最大登録商品数'), null=True, blank=True, choices=MAX_FEED_ITEM)
    check_times = models.IntegerField(_('在庫チェック回数'), null=True, blank=True, choices=CHECK_TIMES)
    ip_address = models.TextField(_('IPアドレス'), help_text=_('2回/日の場合:<br>2万件:1IP/4万件:2IP/5万件:3IP<br>4回/日の場合:<br>2万件:2IP/4万件:4IP/5万件:5IP'), null=True, blank=True)
    is_staff = models.BooleanField(
        _('staff status'),
        default=False,
        help_text=_(
            'Designates whether the user can log into this admin site.'),
    )

    is_active = models.BooleanField(
        _('active'),
        default=True,
        help_text=_(
            'Designates whether this user should be treated as active. '
            'Unselect this instead of deleting accounts.'
        ),
    )

    update_mercari_to_amazon_feed_pid = models.IntegerField(_('出品情報更新プロセスPID(メルカリ)'), null=True, blank=True)
    update_mercari_to_amazon_feed_start_date = models.DateTimeField(_('出品情報更新プロセス開始時間(メルカリ)'),  null=True, blank=True)
    update_yahoo_to_amazon_feed_pid = models.IntegerField(_('出品情報更新プロセスPID(ヤフー)'), null=True, blank=True)
    update_yahoo_to_amazon_feed_start_date = models.DateTimeField(_('出品情報更新プロセス開始時間(ヤフー)'),  null=True, blank=True)

    date_joined = models.DateTimeField(_('date joined'), default=timezone.now)

    objects = UserManager()

    EMAIL_FIELD = 'email'
    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email', ]

    class Meta:
        db_table = 'accounts_user'
        verbose_name = _('user')
        verbose_name_plural = _('users')

    def clean(self):
        super().clean()
        self.email = self.__class__.objects.normalize_email(self.email)

    def email_user(self, subject, message, from_email=None, **kwargs):
        """Send an email to this user."""
        send_mail(subject, message, from_email, [self.email], **kwargs)

    # 既存メソッドの変更                                                                                                                                                                                                                                                                                                                                                    
    def get_full_name(self):
        return self.full_name

    def get_short_name(self):
        return self.full_name


@receiver(models.signals.post_save, sender=User)
def execute_after_save(sender, instance, created, *args, **kwargs):
    if created:
        utils = importlib.import_module('richs_utils.RichsUtils')
        utils.init_richs_user(instance)


# 一括検索一時停止要求
# class BackgroundSearchTemporaryStop(models.Model):
# 
#     class Meta:
#         verbose_name = '一括相乗り検索一時停止'
#         verbose_name_plural = '一括相乗り検索一時停止'
# 
#     VIEW_CHOICES = [
#       (11, '一括Yahoo検索一時停止'),
#       (21, '一括メルカリ検索一時停止'),
#     ]
#     view = models.IntegerField(verbose_name='一時停止対象機能',choices=VIEW_CHOICES)    


# 停止要求
class StopRequest(models.Model):

    class Meta:
        db_table = 'stop_request'
        verbose_name = '一括相乗り検索停止要求'
        verbose_name_plural = '一括相乗り検索停止要求'


    view = models.IntegerField(verbose_name="停止対象画面") # 1X:yahoo, 2X:メルカリ(20:相乗り画面)  
    author = models.ForeignKey('accounts.User', verbose_name="ユーザ", on_delete=models.CASCADE)     
    created_date = models.DateTimeField(verbose_name="作成日", auto_now_add=True)
    updated_date = models.DateTimeField(verbose_name="更新日", auto_now=True)


# URLスキップ要求
class URLSkipRequest(models.Model):

    class Meta:
        verbose_name = '一括相乗り検索URLスキップ要求'
        verbose_name_plural = '一括相乗り検索URLスキップ要求'


    view = models.IntegerField(verbose_name="スキップ対象画面") # 1X:yahoo, 2X:メルカリ(20:相乗り画面)  
    author = models.ForeignKey('accounts.User', verbose_name="ユーザ", on_delete=models.CASCADE)     
    created_date = models.DateTimeField(verbose_name="作成日", auto_now_add=True)
    updated_date = models.DateTimeField(verbose_name="更新日", auto_now=True)


# 相乗り処理状況
class OfferReserchWatcher(models.Model):

    class Meta:
        db_table = 'offer_reserch_watcher'
        verbose_name = '一括相乗り検索モニター'
        verbose_name_plural = '一括相乗り検索モニター'

    # こちらは、未使用になる予定
    now = None
    start_time = None
    duration = None
    end_time = None
    
    research_type = models.IntegerField(verbose_name="検索種別")         # 0:yahoo, 1:メルカリ
    status = models.IntegerField(verbose_name="ステータス")              # 0:進行中 1:完了 2:完了(CSV出力済み) -1:異常終了 9:停止要求中(こちらは、View側で上書き)
    total = models.IntegerField(verbose_name="総検索数")                 #
    exclude_asin = models.IntegerField(verbose_name="出品禁止商品")      #
    exclude_seller = models.IntegerField(verbose_name="禁止セラー")      #
    prime = models.IntegerField(verbose_name="PRIME除外件数")            #
    condition_different = models.IntegerField(verbose_name="検索条件不一致") #
    not_found = models.IntegerField(verbose_name="検索結果未該当")       #
    feed_item = models.IntegerField(verbose_name="相乗り出品商品")       #
    new_feed_item_candidate = models.IntegerField(verbose_name="新規出品候補商品", default=0)     #
    is_over_items = models.BooleanField(verbose_name="登録商品超過", null=True, blank=True)
    end_date = models.DateTimeField(verbose_name="終了日時", null=True, blank=True)
    author = models.ForeignKey('accounts.User', verbose_name="ユーザ", on_delete=models.CASCADE)
    created_date = models.DateTimeField(verbose_name="開始日時", auto_now_add=True)
    updated_date = models.DateTimeField(verbose_name="更新日時", auto_now=True)
    current_url = models.TextField(verbose_name='検索中のURL', null=True, blank=True)
    error_message = models.TextField(verbose_name='エラー状況', null=True, blank=True)

    def _get_research_type(self):
        if self.research_type == 0:
            return 'Yahoo'
        if self.research_type == 1:
            return 'Mercari'
        return str(self.research_type)

    def __str__(self):
        return 'OfferReserchWatcher[user={}, search={}, status={}]'.format(
            self.author.username, self._get_research_type(), self.status)

class BackgroundSearchInfo(models.Model):
    ''' 一括検索を複数URL対応する場合の情報処理スペース '''
    class Meta:
        verbose_name = '一括相乗り検索情報'
        verbose_name_plural = '一括相乗り検索情報'

    watcher = models.ForeignKey('accounts.OfferReserchWatcher', 
        verbose_name="一括相乗り検索モニター", on_delete=models.CASCADE)
    url = models.TextField(verbose_name='検索URL')
    next_url = models.TextField(verbose_name='次の検索URL', null=True, blank=True)
    order = models.IntegerField(verbose_name="URLの順序", default=0)
    search_completed = models.BooleanField(verbose_name="更新が完了しているか否か", default=False)
    output_csv = models.BooleanField(verbose_name="CSV出力を行ったか否か", default=False)
    total_feed_count = models.IntegerField(verbose_name='該当検索までの相乗り出品発見件数', default=0)
    total_new_feed_count = models.IntegerField(verbose_name='該当検索までの新規出品総見件数', default=0)
    total_count = models.IntegerField(verbose_name='該当検索までの合計検索件数', default=0)
    feed_count = models.IntegerField(verbose_name='該当URLでの相乗り出品発見件数', default=0)
    new_feed_count = models.IntegerField(verbose_name='該当URLでの新規出品総見件数', default=0)
    total_url_count = models.IntegerField(verbose_name='該当URLの検索件数', default=0)
    start_date = models.DateTimeField(verbose_name="検索開始日時", null=True, blank=True)
    end_date = models.DateTimeField(verbose_name="検索終了日時", null=True, blank=True)
    updated_date = models.DateTimeField(verbose_name="更新日時", null=True, blank=True, auto_now=True)

class BannedKeyword(models.Model):
    class Meta:
        verbose_name = '禁止ワード'
        verbose_name_plural = '禁止ワード'

    banned_keyword = models.CharField(max_length=100)

    def __str__(self):
        return self.banned_keyword


class BatchExecution(models.Model):
    ''' バッチ実行制御のデータを保持する '''
    batch_id = models.CharField(verbose_name="バッチID", max_length=64, unique=True)
    batch_type = models.CharField(verbose_name="バッチ種別", max_length=256)
    status = models.IntegerField(verbose_name='バッチステータス') # 0: 稼働中, 9: 終了要請中
    created_date = models.DateTimeField(verbose_name="開始日時", auto_now_add=True)
    updated_date = models.DateTimeField(verbose_name="更新日時", auto_now=True)


class StockCheckStatus(models.Model):
    ''' 在庫チェックに利用するアイテムの状況を管理 '''
    class Meta:
        unique_together=(('purchase_item_id', 'item_type', 'owner'))

    purchase_item_id = models.CharField(verbose_name='アイテム固有ID', max_length=32)    
    item_type = models.IntegerField(verbose_name="アイテム種別")   # 0: Yahoo, 1: Mercari
    owner = models.ForeignKey('accounts.User', verbose_name="所有ユーザ", on_delete=models.CASCADE)
    created_date = models.DateTimeField(verbose_name="開始日時", auto_now_add=True)
    updated_date = models.DateTimeField(verbose_name="更新日時", auto_now=True)


class ItemCandidateToCsv(models.Model):
    ''' 相乗り検索で見つけた候補を新規出品できる数をコントロールするデータテーブル '''
    class Meta:
        verbose_name = '相乗り/新規出品制御'
        verbose_name_plural = '相乗り/新規出品制御'

    owner = models.OneToOneField(User, verbose_name="所有ユーザ", on_delete=models.CASCADE)
    today_output = models.IntegerField(verbose_name='今日出力したアイテム数', default=0) 
    max_output = models.IntegerField(verbose_name='1日に出力可能な最大アイテム数', default=0) 
    today_output_yahoo = models.IntegerField(verbose_name='今日出力したYahooアイテム数(未使用)', default=0) 
    today_output_mercari = models.IntegerField(verbose_name='今日出力したMercariアイテム数(未使用)', default=0) 
    max_output_yahoo = models.IntegerField(verbose_name='1日に出力可能な最大Yahooアイテム数(未使用)', default=0) 
    max_output_mercari = models.IntegerField(verbose_name='1日に出力可能な最大Mercariアイテム数(未使用)', default=0) 
    created_date = models.DateTimeField(verbose_name="開始日時", auto_now_add=True)
    updated_date = models.DateTimeField(verbose_name="更新日時", auto_now=True)

    def daily_update(self, now):
        ''' 日付に従って更新を行う '''
        ymd1 = (self.updated_date.year, self.updated_date.month, self.updated_date.day)
        ymd2 = (now.year, now.month, now.day)
        if ymd1 == ymd2:
            # 更新日時が同じ場合は更新しない
            return
        # 日が変わっているとリセット
        self.today_output = 0
        self.today_output_yahoo = 0
        self.today_output_mercari = 0
        self.save()

    def __str__(self):
        return '{} [Daily Output: {}/{}]'.format(
            self.owner.username, self.today_output, self.max_output)


class OverrideConstantValue(models.Model):
    ''' システムの固定値を外部から上書きするために利用されるテーブル '''
    class Meta:
        verbose_name = 'システム変数変更'
        verbose_name_plural = 'システム変数変更'

    key = models.CharField(verbose_name='システム変数名', max_length=256)    
    value = models.CharField(verbose_name="アイテム変数の値", max_length=256)
    description = models.CharField(verbose_name="説明", max_length=1024, null=True, default='')
    created_date = models.DateTimeField(verbose_name="開始日時", auto_now_add=True)
    updated_date = models.DateTimeField(verbose_name="更新日時", auto_now=True)

    @staticmethod
    def get_value(key, default_value, converter=None):
        vals = OverrideConstantValue.objects.filter(key=key)
        if len(vals) <= 0:
            return default_value
        if converter is None:
            return vals[0].value
        try:
            return converter(vals[0].value)
        except:
            return default_value

    def __str__(self):
        return '{}={} ({})'.format(self.key, self.value, self.description)


class ItemNameFormat(models.Model):
    ''' 商品名の修正に利用するテーブル '''
    class Meta:
        unique_together=(('strategy', 'from_text', 'priority'))

    STRATEGY_CHOICES = [
      ('replace', '単純置換'),
      ('regex', '正規表現置換'),
    ]
    strategy = models.CharField(verbose_name='修正手段', max_length=32, choices=STRATEGY_CHOICES)    
    from_text = models.CharField(verbose_name='検索文', max_length=256)
    to_text = models.CharField(verbose_name='置換文', max_length=256, null=True, blank=True)
    comment = models.CharField(verbose_name='コメント', max_length=256, null=True, blank=True)
    priority = models.IntegerField(verbose_name="適用優先順位(大きい方が先)")
    valid = models.IntegerField(verbose_name="有効無効")
    created_date = models.DateTimeField(verbose_name="開始日時", auto_now_add=True)
    updated_date = models.DateTimeField(verbose_name="更新日時", auto_now=True)

    def __str__(self):
        return '[{}:{}] {} => {}'.format(
            self.strategy, self.priority, self.from_text, self.to_text)

    @staticmethod
    def choose_strategy(strategy):
        ''' 戦略キーを取得 '''
        for ch in ItemNameFormat.STRATEGY_CHOICES:
            if strategy == ch[0]:
                return strategy
        return ItemNameFormat.STRATEGY_CHOICES[0][0]

    @staticmethod
    def get_ordered(extra=None):
        ''' ソート済置換ルールを取得 '''
        # -- 適用優先順序
        # 1. 優先順序数値が大きい、2. 置換元テキストが長い、3. 先に登録された
        rules = ItemNameFormat.objects.filter(valid=True)
        if extra is not None:
            if isinstance(extra, list):
                rules = [ r for r in rules ] + extra
            else:
                rules = [ r for r in rules ] + [ extra ]
        return sorted(rules, key=lambda r: (-r.priority, -len(r.from_text), r.id))


class FJCMember(models.Model):
    ''' FJCMemberを管理するテーブルです '''
    class Meta:
        verbose_name = 'FJCメンバー管理'
        verbose_name_plural = 'FCJメンバー管理'

    account_id = models.CharField(verbose_name="出品者ID", max_length=128)
    username = models.CharField(verbose_name="ユーザー名", max_length=128)
    url = models.CharField(verbose_name='取得元URL', max_length=512) 
    created_date = models.DateTimeField(verbose_name="開始日時", auto_now_add=True)
    updated_date = models.DateTimeField(verbose_name="更新日時", auto_now=True)

    def __str__(self):
        return '{}.{}'.format(self.username, self.account_id)

    @staticmethod
    def contains(url):
        ''' URLにメンバーのIDが含まれるか否かをチェックします  '''
        for m in FJCMember.objects.all():
            # 登録されたアカウントは最低8文字以上
            if not re.match('^[A-Z0-9]{8}[A-Z0-9]*$', m.account_id):
                continue
            if m.account_id in url:
                return True
        return False
 
