from django.core.management.base import BaseCommand
from accounts.models import User
from richs_utils import RichsUtils, InventoryYahoo
import threading
from time import sleep
import traceback


from scraper import YahooAuctionIdScraper, AmazonScraper
from yahoo.models import YahooToAmazonItem

from mercari.models import MercariToAmazonItem


# コマンドを実行
class Command(BaseCommand):
    help = "アマゾン画像のダウンロードを実施します。"
    
    # 引数
    def add_arguments(self, parser):
        parser.add_argument('ip', nargs='+', type=str)       

    # ハンドラ
    def handle(self, *args, **options):
        self.update_yahoo(options['ip'][0])
        self.update_mercari(options['ip'][0])

    # Yahoo
    def update_yahoo(self,ip):
        try:
            client = AmazonScraper(ip)
            items = YahooToAmazonItem.objects.filter(csv_flag=1, main_image_url__startswith='http')
            for item in items:
                main_image_url = RichsUtils.download_to_yahoo_folder(client, item.main_image_url, item.author)
                item.main_image_url = main_image_url
                item.save()
        except:
            print(traceback.format_exc())
            pass


    # Mercari
    def update_mercari(self,ip):
        try:
            client = AmazonScraper(ip)
            items = MercariToAmazonItem.objects.filter(csv_flag=1, main_image_url__startswith='http')
            for item in items:
                main_image_url = RichsUtils.download_to_mercari_folder(client, item.main_image_url, item.author)
                item.main_image_url = main_image_url
                item.save()
        except:
            print(traceback.format_exc())
            pass






