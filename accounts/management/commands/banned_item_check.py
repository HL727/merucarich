from django.core.management.base import BaseCommand
from richs_utils import RichsUtils
from yahoo.models import YahooToAmazonItem
from mercari.models import MercariToAmazonItem

# コマンドを実行
class Command(BaseCommand):
    help = "禁止ワードを含むアイテムとユーザーを出力します"
    
    # 引数
    def add_arguments(self, parser):
        pass

    def _output_row(self, idx, shop, user, item, keyword):
        print('"{}","{}","{}","{}","{}","{}","{}"'.format(
            idx, shop, user.username, 
            item.id, item.item_name, item.current_purchase_quantity, keyword))

    # ハンドラ
    def handle(self, *args, **options):
        idx = 1
        banned_list = RichsUtils.get_banned_list()
        print('"#","Shop","User","ItemId","Item","Quantity","Keyword"')
        base = [
            ('Yahoo', lambda: YahooToAmazonItem.objects.all()),
            ('Mercari', lambda: MercariToAmazonItem.objects.all()),
        ]
        for (shop, item_generator) in base:
            for item in item_generator():
                (banned, keyword) = RichsUtils.judge_banned_item(item.item_name, banned_list)
                if banned:
                    self._output_row(idx, 'Yahoo', item.author, item, keyword)
                    idx += 1


