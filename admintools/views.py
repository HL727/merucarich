#!/usr/bin/python 
# -*- coding: utf-8 -*-

import sys
import csv 
import logging

from django.conf import settings
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.utils import timezone
from django.contrib.auth.decorators import login_required, user_passes_test

from accounts.models import User, ItemNameFormat, BannedKeyword
from yahoo.models import YahooExcludeSeller, YahooExcludeSellerMaster
from mercari.models import MercariExcludeSeller, MercariExcludeSellerMaster
from settings_amazon.models import ExcludeAsin, ExcludeAsinMaster
from scraper import AmazonScraper, YahooSearchScraper, MercariSearchScraper
from richs_utils import RichsUtils, ItemTitleConverter, ResponseUtils

logger = logging.getLogger(__name__)

def _adminuser(user):
    ''' Adminユーザーであれば true '''
    return user.is_staff


@login_required
@user_passes_test(_adminuser)
def index(request):
    return render(request, 'admintools/index.html')


@login_required
@user_passes_test(_adminuser)
def ipstatus(request):
    
    rows = []
    for user in sorted(User.objects.all(), key=lambda u: u.username):
        if user.ip_address in ['', None]:
            rows.append(dict(user=user, ipaddress='server'))
            continue
        for ipaddress in user.ip_address.split('\n'):
            rows.append(dict(user=user, ipaddress=ipaddress.strip()))
    
    return render(request, 'admintools/ipstatus.html', {
        'rows': rows, 
    })


def _check_access(params, scraper_class):
    url = params.get('checkurl')
    ipaddr = params.get('ipaddress')
    withsource = params.get('withsource', '0')
    if None in [url, ipaddr]:
        return JsonResponse({
          'success': False,  
        })

    url = url.strip()
    ipaddr = ipaddr.strip()
    if ipaddr == 'server':
        scraper = scraper_class()
    else:
        scraper = scraper_class(ipaddr)

    (success, html) = scraper.check_access(url);
    return JsonResponse({
        'success': success,
        'html': html if withsource != '0' else '',
    })


@login_required
@user_passes_test(_adminuser)
def api_ipstatus_amazon(request):
    return _check_access(request.GET, AmazonScraper)


@login_required
@user_passes_test(_adminuser)
def api_ipstatus_yahoo(request):
    return _check_access(request.GET, YahooSearchScraper)


@login_required
@user_passes_test(_adminuser)
def api_ipstatus_mercari(request):
    return _check_access(request.GET, MercariSearchScraper)


def _banned_keywords_register(params):
    keyword = params.get('keyword')
    if BannedKeyword.objects.filter(banned_keyword=keyword).count() > 0:
        return ('重複', '既に【{}】は禁止ワードとして登録されています'.format(keyword))
    BannedKeyword.objects.create(banned_keyword=keyword)
    return ('成功', '登録に成功しました')


def _banned_keywords_delete(params):
    itemid = int(params.get('id'))
    obj = BannedKeyword.objects.filter(id=itemid).first()
    if obj is None:
        return ('失敗', '削除アイテムが見つかりません')
    detail = 'キーワード:【{}】を削除しました'.format(obj.banned_keyword)
    obj.delete()
    return ('成功', detail)
 

def _banned_keywords_import(request):
    ''' csv のアップロードを実施 '''
    filepath = request.FILES.get('import_file')
    if filepath is None:
        return ('失敗', 'CSVファイルを選択してください')
    path = RichsUtils.handle_uploaded_tmp_file(filepath, request.user)
    clean = 'delete_all' in request.POST
    (succ, err) = (0, 0)
    if clean:
        BannedKeyword.objects.all().delete()
    with open(path, 'r', encoding='utf8') as fh:
        h2i = {}
        for (i, row) in enumerate(csv.reader(fh, delimiter='\t')):
            if i == 0:
                for (idx, item) in enumerate(row):
                    h2i[item] = idx
                for req in ['banned_keyword']:
                    if req not in h2i:
                        return ('失敗', 'CSVヘッダが不正です。 必須は banned_keyword です')
                continue
            try:
                BannedKeyword.objects.update_or_create(banned_keyword=row[h2i['banned_keyword']])
                succ += 1
            except:
                err += 1
    
    if err > 0:
        return ('成功', 'CSV取り込みをしましたが、{}件の取り込みに失敗しました'.format(err))
    return ('成功', '全てのCSV取り込みを実施しました')
 

def _banned_keywords_export(params):
    csvrows = [['banned_keyword']] + [ [ k.banned_keyword ] for k in BannedKeyword.objects.all() ]
    filename = 'bannedkeyword_{}.csv'.format(timezone.datetime.now().strftime('%Y%m%d%H%M%S'))
    return ResponseUtils.csv_response(filename, csvrows, delimiter='\t', encoding='utf8')


@login_required
@user_passes_test(_adminuser)
def banned_keywords(request):
    ''' 禁止ワードの一括編集 '''
    params = {}
    if request.method == 'POST':
        try:
            if 'download_csv' in request.POST:
                return _banned_keywords_export(request.POST)
            elif 'delete' in request.POST:
                (msg, detail) = _banned_keywords_delete(request.POST)
            elif 'upload_csv' in request.POST:
                (msg, detail) = _banned_keywords_import(request) 
            else:
                (msg, detail) = _banned_keywords_register(request.POST)
            params['message'] = msg
            params['message_detail'] = detail
        except Exception as err:
            params['message'] = '失敗'
            params['message_detail'] = '例外が発生しました: ' + str(err)
    else:
        pass
    def _norm(k):
        k.banned_keyword = RichsUtils.normalize(k.banned_keyword)
        return k
    params['keywords'] = [ _norm(k) for k in BannedKeyword.objects.all() ] 
    return render(request, 'admintools/banned_keywords.html', params)


def _exclude_asins_add(params):
    ''' 禁止ASINの追加 '''
    username = params.get('author')
    asin = params.get('asin')
    memo = params.get('memo')
    
    if username == 'ALL':
        users = User.objects.all()
    else:
        users = User.objects.filter(username=username)

    (adds, updates) = (0, 0)
    for user in users:
        try:
            query = ExcludeAsin.objects.filter(author=user, asin=asin)
            if query.count() > 0:
                query.update(asin=asin, memo=memo)
                updates += 1
            else:
                ExcludeAsin.objects.create(author=user, asin=asin, memo=memo)
                adds += 1
        except Exception as err:
            pass

    addmsts = 0
    if username == 'ALL':
        try:
            # マスタに追加
            if ExcludeAsinMaster.objects.filter(asin=asin).count() <= 0:
                ExcludeAsinMaster.objects.create(asin=asin)
            addmsts += 1
        except:
            pass

    message = ''.join([
        '禁止ASINを追加しました (',
        '追加: {}件'.format(adds), 
        ', 更新: {}件'.format(updates),
        ', マスタ追加: {}件'.format(addmsts) if addmsts > 0 else '',
        ')',
    ])
    return ('成功', message)


def _exclude_asins_delete(params):
    ''' 禁止ASINの削除 '''
    itemid = params.get('id')
    target = params.get('target', 'simple')
    asin = ExcludeAsin.objects.filter(id=itemid).first()
    if asin is None:
        return ('失敗', '削除対象が見つかりません')

    if target == 'all':
        ExcludeAsin.objects.filter(asin=asin.asin).delete()
    else:
        asin.delete()

    return ('成功', '禁止ASINの削除に成功しました')


def _exclude_asins_export(params):
    header = ['author', 'asin', 'memo']
    asins = []
    for user in User.objects.all().order_by('username'):
        userasins = ExcludeAsin.objects.filter(author=user).order_by('id')
        asins = asins + [[e.author.username, e.asin, e.memo] for e in userasins ]
    csvrows = [header] + asins
    filename = 'excludeasin_{}.csv'.format(timezone.datetime.now().strftime('%Y%m%d%H%M%S'))
    return ResponseUtils.csv_response(filename, csvrows, delimiter='\t', encoding='utf8')


def _exclude_asins_apply_master(params):
    ''' マスタに登録されている全ての情報を既存ユーザー全てに反映する '''
    exclude_asin_ids = [ m.asin for m in ExcludeAsinMaster.objects.all() ]
    (added, exists, failed) = (0, 0, 0)
    for user in User.objects.all().order_by('username'):
        for asin in exclude_asin_ids:
            try:
                if ExcludeAsin.objects.filter(author=user, asin=asin).count() <= 0:
                    ExcludeAsin.objects.create(
                        author=user, asin=asin, memo='')
                    added += 1
                else:
                    exists += 1
            except Exception as err:
                failed += 1

    msg = ''.join([
        '禁止ASINマスタ情報を全ユーザーに反映しました ',
        '(追加: {}件, 既に設定済: {}件, 失敗: {}件)'.format(added, exists, failed),
    ])

    return ('成功', msg)


def _exclude_asins_import(request):
    ''' csv のアップロードを実施 '''
    filepath = request.FILES.get('import_file')
    if filepath is None:
        return ('失敗', 'CSVファイルを選択してください')
    path = RichsUtils.handle_uploaded_tmp_file(filepath, request.user)
    # clean = 'delete_all' in request.POST
    # if clean:
    #     ExcludeAsin.objects.all().delete()
    (succ, err) = (0, 0)
    with open(path, 'r', encoding='utf8') as fh:
        h2i = {}
        for (i, row) in enumerate(csv.reader(fh, delimiter='\t')):
            if i == 0:
                for (idx, item) in enumerate(row):
                    h2i[item] = idx
                for req in ['author', 'asin', 'memo']:
                    if req not in h2i:
                        return ('失敗', 'CSVヘッダが不正です。 必須は author, asin, memo です')
                continue
            if len(row) < 3:
                continue
            try:
                username = row[h2i['author']]
                asin = row[h2i['asin']]
                memo = row[h2i['memo']]
                if username.lower() == 'all':
                    for author in User.objects.all():
                        if ExcludeAsin.objects.filter(author=author, asin=asin).count() > 0:
                            ExcludeAsin.objects.filter(author=author, asin=asin).update(memo=memo)
                        else:
                            ExcludeAsin.objects.create(author=author, asin=asin, memo=memo)
                        succ += 1
                    if ExcludeAsinMaster.objects.filter(asin=asin).count() <= 0:
                        ExcludeAsinMaster.objects.create(asin=asin)
                else:
                    author = User.objects.filter(username=username).first()
                    if author is None:
                        err += 1
                        logger.warn('[exclude asin import] username %s is not found', username)
                        continue
                    if ExcludeAsin.objects.filter(author=author, asin=asin).count() > 0:
                        ExcludeAsin.objects.filter(author=author, asin=asin).update(memo=memo)
                    else:
                        ExcludeAsin.objects.create(author=author, asin=asin, memo=memo)
                    succ += 1
            except Exception as e:
                logger.exception(e)
                err += 1
    
    if err > 0:
        return ('成功', 'CSV取り込みをしましたが、{}件の取り込みに失敗しました'.format(err))
    return ('成功', '全てのCSV取り込みを実施しました')


@login_required
@user_passes_test(_adminuser)
def exclude_asins(request):
    ''' 禁止ASINの管理者編集 '''
    params = {}
    params['users'] = User.objects.all().order_by('username')
    if request.method == 'POST':
        username = request.POST.get('user')
        try:
            if 'download_csv' in request.POST:
                return _exclude_asins_export(params)
            elif 'upload_csv' in request.POST:
                (msg, detail) = _exclude_asins_import(request)
            elif 'delete' in request.POST:
                (msg, detail) = _exclude_asins_delete(request.POST)
            elif 'apply_master' in request.POST:
                (msg, detail) = _exclude_asins_apply_master(request.POST)
            else:
                (msg, detail) = _exclude_asins_add(request.POST)
            params['message'] = msg
            params['message_detail'] = detail
        except Exception as err:
            logger.exception(err)
            params['message'] = '失敗'
            params['message_detail'] = '例外が発生しました: ' + str(err)
    else:
        username = request.GET.get('user')

    user = User.objects.filter(username=username).first()
    if user is None:
        user = params['users'].first()

    if user is not None:
        params['asins'] = ExcludeAsin.objects.filter(author=user)
        params['selected_username'] = user.username
    else:
        params['asins'] = []
        params['selected_username'] = ''

    return render(request, 'admintools/exclude_asins.html', params)


def _exclude_seller_model(source):
    source = source.lower()
    if source == 'yahoo':
        return YahooExcludeSeller
    if source == 'mercari':
        return MercariExcludeSeller
    return None


def _exclude_seller_master_model(source):
    source = source.lower()
    if source == 'yahoo':
        return YahooExcludeSellerMaster
    if source == 'mercari':
        return MercariExcludeSellerMaster
    return None


def _exclude_sellers_add(params):
    ''' 禁止セラーの追加 '''
    username = params.get('author')
    source = params.get('source')
    seller_id = params.get('seller_id')
    memo = params.get('memo')
    
    if username == 'ALL':
        users = User.objects.all()
    else:
        users = User.objects.filter(username=username)

    model = _exclude_seller_model(source)
    master_model = _exclude_seller_master_model(source)
    if model is None or master_model is None:
        return ('失敗', '対象外の種別です')

    (adds, updates) = (0, 0)
    for user in users:
        try:
            query = model.objects.filter(author=user, seller_id=seller_id)
            if query.count() > 0:
                query.update(memo=memo)
                updates += 1
            else:
                model.objects.create(author=user, seller_id=seller_id, memo=memo)
                adds += 1
        except:
            pass

    if username == 'ALL':
        if master_model.objects.filter(seller_id=seller_id).count() <= 0:
            master_model.objects.create(seller_id=seller_id)

    return ('成功', '禁止セラーを追加しました(追加: {}件, 更新: {}件'.format(adds, updates))


def _exclude_sellers_delete(params):
    ''' 禁止セラーの削除 '''
    itemid = params.get('id')
    source = params.get('source')
    target = params.get('target', 'simple')
 
    model = _exclude_seller_model(source)
    if model is None:
        return ('失敗', '対象外の種別です')

    seller = model.objects.filter(id=itemid).first()
    if seller is None:
        return ('失敗', '削除対象が見つかりません')
    
    if target == 'all':
        model.objects.filter(seller_id=seller.seller_id).delete()
    else:
        seller.delete()

    return ('成功', '禁止セラーの削除に成功しました')


def _exclude_sellers_export(params):
    header = ['source', 'author', 'seller_id', 'memo']
    (ysellers, msellers) = ([], [])
    for user in User.objects.all().order_by('username'):
        ys = YahooExcludeSeller.objects.filter(author=user).order_by('id')
        ysellers = ysellers + [['yahoo', s.author.username, s.seller_id, s.memo] for s in ys ]
        ms = MercariExcludeSeller.objects.filter(author=user).order_by('id')
        msellers = msellers + [['mercari', s.author.username, s.seller_id, s.memo] for s in ms ]
    csvrows = [header] + ysellers + msellers
    filename = 'excludeseller_{}.csv'.format(timezone.datetime.now().strftime('%Y%m%d%H%M%S'))
    return ResponseUtils.csv_response(filename, csvrows, delimiter='\t', encoding='utf8')


def _exclude_sellers_apply_master(params):
    ''' マスタに登録されている全ての情報を既存ユーザー全てに反映する '''
    yahoo_mst_exclude_seller_ids = [ m.seller_id for m in YahooExcludeSellerMaster.objects.all() ]
    mercari_mst_exclude_seller_ids = [ m.seller_id for m in MercariExcludeSellerMaster.objects.all() ]
    (added, exists, failed) = (0, 0, 0)
    for user in User.objects.all().order_by('username'):
        for seller_id in yahoo_mst_exclude_seller_ids:
            try:
                query = YahooExcludeSeller.objects.filter(author=user, seller_id=seller_id)
                if query.count() > 0:
                    # 特になにもしない
                    exists += 1
                else:
                    YahooExcludeSeller.objects.create(
                        author=user, seller_id=seller_id, memo='')
                    added += 1
            except:
                failed += 1

        for seller_id in mercari_mst_exclude_seller_ids:
            try:
                query = MercariExcludeSeller.objects.filter(author=user, seller_id=seller_id)
                if query.count() > 0:
                    # 特になにもしない
                    exists += 1
                else:
                    MercariExcludeSeller.objects.create(
                        author=user, seller_id=seller_id, memo='')
                    added += 1
            except:
                failed += 1

    msg = ''.join([
        'マスタ情報をユーザーに反映しました ',
        '(追加: {}件, 既に設定済: {}件, 失敗: {}件'.format(added, exists, failed),
    ])

    return ('成功', msg)


def _exclude_sellers_import(request):
    ''' csv のアップロードを実施 '''
    filepath = request.FILES.get('import_file')
    if filepath is None:
        return ('失敗', 'CSVファイルを選択してください')
    path = RichsUtils.handle_uploaded_tmp_file(filepath, request.user)
    # clean = 'delete_all' in request.POST
    # if clean:
    #     YahooExcludeSeller.objects.all().delete()
    #     MercariExcludeSeller.objects.all().delete()
    (succ, err) = (0, 0)
    with open(path, 'r', encoding='utf8') as fh:
        h2i = {}
        for (i, row) in enumerate(csv.reader(fh, delimiter='\t')):
            if i == 0:
                for (idx, item) in enumerate(row):
                    h2i[item] = idx
                for req in ['source', 'author', 'seller_id', 'memo']:
                    if req not in h2i:
                        return ('失敗', 'CSVヘッダが不正です。 必須は source, author, seller_id, memo です')
                continue
            if len(row) < 4:
                continue
            try:
                model = _exclude_seller_model(row[h2i['source']])
                master_model = _exclude_seller_master_model(row[h2i['source']])
                username = row[h2i['author']]
                seller_id = row[h2i['seller_id']]
                memo = row[h2i['memo']]
                if username.lower() == 'all':
                    for author in User.objects.all():
                        query = model.objects.filter(author=author, seller_id=seller_id)
                        if query.count() > 0:
                            query.update(memo=memo)
                        else:
                            model.objects.create(author=author, seller_id=seller_id, memo=memo)
                        succ += 1
                    query = master_model.objects.filter(seller_id=seller_id)
                    if query.count() <= 0:
                        master_model.objects.create(seller_id=seller_id)
                else:
                    author = User.objects.filter(username=username).first()
                    if author is None:
                        err += 1
                        logger.warn('[exclude seller import] username %s is not found', username)
                        continue
                    model.objects.update_or_create(
                        author=author, seller_id=seller_id, defaults={'memo': memo})
                    succ += 1
            except Exception as e:
                logger.exception(e)
                err += 1
    
    if err > 0:
        return ('成功', 'CSV取り込みをしましたが、{}件の取り込みに失敗しました'.format(err))
    return ('成功', '全てのCSV取り込みを実施しました')
 

@login_required
@user_passes_test(_adminuser)
def exclude_sellers(request):
    ''' 禁止セラーの管理者編集 '''
    params = {}
    params['users'] = User.objects.all().order_by('username')
    if request.method == 'POST':
        username = request.POST.get('user')
        try:
            if 'download_csv' in request.POST:
                return _exclude_sellers_export(params)
            elif 'upload_csv' in request.POST:
                (msg, detail) = _exclude_sellers_import(request)
            elif 'delete' in request.POST:
                (msg, detail) = _exclude_sellers_delete(request.POST)
            elif 'apply_master' in request.POST:
                (msg, detail) = _exclude_sellers_apply_master(request.POST)
            else:
                (msg, detail) = _exclude_sellers_add(request.POST)
            params['message'] = msg
            params['message_detail'] = detail
        except Exception as err:
            logger.exception(err)
            params['message'] = '失敗'
            params['message_detail'] = '例外が発生しました: ' + str(err)
    else:
        username = request.GET.get('user')

    user = User.objects.filter(username=username).first()
    if user is None:
        user = params['users'].first()

    if user is not None:
        params['yahoo_sellers'] = YahooExcludeSeller.objects.filter(author=user)
        params['mercari_sellers'] = MercariExcludeSeller.objects.filter(author=user)
        params['selected_username'] = user.username
    else:
        params['yahoo_sellers'] = []
        params['mercari_sellers'] = []
        params['selected_username'] = ''

    return render(request, 'admintools/exclude_sellers.html', params)


def _itemname_rules_register(params):
    ''' 新規ルールの登録 '''
    success = ItemTitleConverter.put_rule(params.get('strategy'), 
        params.get('from_text'), params.get('to_text', ''), 
        int(params.get('priority')), params.get('comment', ''))
    if not success:
        return ('失敗', '登録に失敗しました。 登録前にテストを実施してください')
    return ('成功', '登録に成功しました')


def _itemname_rules_delete(params):
    ''' 新規ルールの登録 '''
    itemid = params.get('id')
    if itemid is None:
        return ('失敗', '削除アイテムが指定されていません')
    
    item = ItemNameFormat.objects.filter(id=itemid).first()
    if item is None:
        return ('失敗', 'アイテムが存在しません')
    item.delete()

    return ('成功', 'アイテムを削除しました')


def _itemname_rules_export(params):
    ''' csv のエクスポートを実施 '''
    csvrows = ItemTitleConverter.export_csv_rows()
    filename = 'itemrules_{}.csv'.format(timezone.datetime.now().strftime('%Y%m%d%H%M%S'))
    return ResponseUtils.csv_response(filename, csvrows, delimiter='\t', encoding='utf8')


def _itemname_rules_uploads(request):
    ''' csv のアップロードを実施 '''
    filepath = request.FILES.get('import_file')
    if filepath is None:
        return ('失敗', 'CSVファイルを選択してください')
    path = RichsUtils.handle_uploaded_tmp_file(filepath, request.user)
    # clean = 'delete_all' in request.POST
    results = ItemTitleConverter.import_csv(path)
    if results['error'] > 0:
        return ('成功', 'CSV取り込みをしましたが、{}件の取り込みに失敗しました'.format(results['error']))
    return ('成功', '全てのCSV取り込みを実施しました')


@login_required
@user_passes_test(_adminuser)
def itemname_rules(request):
    ''' 新規出品商品名のルール編集 '''
    params = {}
    if request.method == 'POST':
        try:
            if 'download_csv' in request.POST:
                return _itemname_rules_export(request.POST)
            elif 'upload_csv' in request.POST:
                (msg, detail) = _itemname_rules_uploads(request) 
            elif 'delete' in request.POST:
                (msg, detail) = _itemname_rules_delete(request.POST)
            else:
                (msg, detail) = _itemname_rules_register(request.POST)
            params['message'] = msg
            params['message_detail'] = detail
        except Exception as err:
            logger.exception(err)
            params['message'] = '失敗'
            params['message_detail'] = '例外が発生しました: ' + str(err)

    params['rules'] = ItemNameFormat.get_ordered()
    return render(request, 'admintools/itemname_rules.html', params)


def _test_rule(params):
    strategy = params.get('strategy')
    from_text = params.get('from_text')
    to_text = params.get('to_text')
    priority = int(params.get('priority'))
    input_text = params.get('input', '')
    testtype = params.get('testtype', 'simple')
    tmp = ItemNameFormat(id=sys.maxsize, strategy=strategy, 
        from_text=from_text, to_text=to_text,
        priority=priority, valid=True)
    # Simple テスト (入力ルールがうまくいくかのチェック)
    (success, output) = ItemTitleConverter.test(input_text, tmp)
    if testtype == 'all':
        # 総合テスト
        (_, output) = ItemTitleConverter.alltest(input_text, tmp)

    return (success, output)


@login_required
@user_passes_test(_adminuser)
def test_rule(request):
    ''' 入力されたルールのテスト '''
    try:
        (success, output) = _test_rule(request.GET)
        return JsonResponse({
            'success': success,
            'output': output,
        })
    except Exception as e:
        logger.exception(e)
        return JsonResponse({
            'success': False,
            'output': str(e),
        })

