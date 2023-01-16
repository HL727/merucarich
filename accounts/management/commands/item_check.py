from django.core.management.base import BaseCommand
from accounts.models import User
from richs_utils import RichsUtils, InventoryYahoo
import threading
from time import sleep

# コマンドを実行
class Command(BaseCommand):
    help = "在庫チェックを実施します。"
    
    # 引数
    def add_arguments(self, parser):
        parser.add_argument('check_times', nargs='+', type=int)

    # ハンドラ
    def handle(self, *args, **options):
        # 対象となるユーザを抽出
        users = User.objects.filter(is_staff=False, is_active=True, check_times__in=options['check_times'])
        # 
        for user in users:
            thread = threading.Thread(target=self.check_items, args=([user]))
            thread.start()
            sleep(1)

    # 在庫チェック処理
    def check_items(self, user):
        InventoryYahoo.do_inventory_check(user)
