# Generated by Django 2.1.4 on 2020-03-26 14:11

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0011_fjcmember'),
    ]

    operations = [
        migrations.CreateModel(
            name='BackgroundSearchInfo',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('url', models.TextField(verbose_name='検索URL')),
                ('next_url', models.TextField(blank=True, null=True, verbose_name='次の検索URL')),
                ('order', models.IntegerField(default=0, verbose_name='URLの順序')),
                ('search_completed', models.BooleanField(default=False, verbose_name='更新が完了しているか否か')),
                ('output_csv', models.BooleanField(default=False, verbose_name='CSV出力を行ったか否か')),
                ('total_feed_count', models.IntegerField(default=0, verbose_name='該当検索までの相乗り出品発見件数')),
                ('total_new_feed_count', models.IntegerField(default=0, verbose_name='該当検索までの新規出品総見件数')),
                ('total_count', models.IntegerField(default=0, verbose_name='該当検索までの合計検索件数')),
                ('feed_count', models.IntegerField(default=0, verbose_name='該当URLでの相乗り出品発見件数')),
                ('new_feed_count', models.IntegerField(default=0, verbose_name='該当URLでの新規出品総見件数')),
                ('total_url_count', models.IntegerField(default=0, verbose_name='該当URLの検索件数')),
            ],
            options={
                'verbose_name': '一括相乗り検索情報',
                'verbose_name_plural': '一括相乗り検索情報',
            },
        ),
        migrations.AddField(
            model_name='offerreserchwatcher',
            name='current_url',
            field=models.TextField(blank=True, null=True, verbose_name='検索中のURL'),
        ),
        migrations.AddField(
            model_name='offerreserchwatcher',
            name='error_message',
            field=models.TextField(blank=True, null=True, verbose_name='エラー状況'),
        ),
        migrations.AddField(
            model_name='backgroundsearchinfo',
            name='watcher',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='accounts.OfferReserchWatcher', verbose_name='一括相乗り検索モニター'),
        ),
    ]
