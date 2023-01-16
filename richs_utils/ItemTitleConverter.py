#!/usr/bin/python 
# -*- coding: utf-8 -*-

'''
商品タイトルの編集用関数を提供します。
'''

import re
import csv
import jaconv

from django.forms.models import model_to_dict
from accounts.models import ItemNameFormat

def apply_format(text, rule):
    ''' 文字列置換を行う '''
    try:
        from_text = rule.from_text
        to_text = '' if rule.to_text is None else rule.to_text
        if rule.strategy == 'replace':
            # 単純置換
            res = text.replace(from_text, to_text)
        elif rule.strategy == 'regex':
            # 正規表現置換
            res = re.sub(from_text, to_text, text)
        else:
            # 戦略なし
            return (False, text)
        return (True, res)
    except:
        # 失敗時はそのままを返す
        return (False, text)


def put_rule(strategy, from_text, to_text, priority, comment):
    ''' 新規ルールを登録 or 更新します '''
    strategy = ItemNameFormat.choose_strategy(strategy.strip())
    from_text = jaconv.z2h(from_text, kana=False, ascii=True, digit=True)
    to_text = jaconv.z2h(to_text, kana=False, ascii=True, digit=True)
    priority = int(priority)

    (obj, created) = ItemNameFormat.objects.update_or_create(
        strategy=strategy, from_text=from_text, priority=priority,
        defaults=dict(to_text=to_text, comment=comment, valid=True))
    # 正常に適用できない場合は無効化する
    (success, _) = apply_format('', obj)
    if not success:
        obj.valid = False
        obj.save()
    return obj.valid
 

def import_csv(path, clean=False, delimiter='\t'):
    ''' CSVファイルをシステムに取り込む '''
    # path = RichsUtils.handle_uploaded_tmp_file(request.FILES['import_file'], request.user)
    results = dict(success=0, error=0, messages=[])
    if clean:
        ItemNameFormat.objects.all().delete()
    with open(path, 'r', encoding='utf8') as fh:
        h2i = {}
        for (i, row) in enumerate(csv.reader(fh, delimiter=delimiter)):
            if i == 0:
                for (idx, item) in enumerate(row):
                    h2i[item] = idx
                continue
            try:
                success = put_rule(row[h2i['strategy']], 
                    row[h2i['from_text']], row[h2i['to_text']], 
                    int(row[h2i['priority']]), row[h2i['comment']])
                if success:
                    results['success'] += 1
                else:
                    results['error'] += 1
                    results['messages'].append('L{:04d}: 登録エラー'.format(i+1))
            except:
                results['error'] += 1
                results['messages'].append('L{:04d}: フォーマットエラー'.format(i+1))
    return results


def export_csv_rows():
    ''' CSV出力用のデータを返す '''
    header = ['strategy', 'from_text', 'to_text', 'priority', 'comment']
    rows = [ model_to_dict(fmt) for fmt in ItemNameFormat.get_ordered() ]
    csvrows = [ header ] + [ 
        [ r['strategy'], r['from_text'], r['to_text'], r['priority'], r['comment'] ] for r in rows
    ]
    return csvrows


def convert(title, rules=None, details=False):
    ''' 商品タイトルを登録ルールに従って置換する '''
    if rules is None:
        rules = ItemNameFormat.get_ordered()
    # 数値・英数字は半角に、カタカナは全角に統一
    title = jaconv.h2z(title, kana=True, ascii=False, digit=False)
    title = jaconv.z2h(title, kana=False, ascii=True, digit=True)
    logs = []
    for rule in rules:
        (success, title) = apply_format(title, rule)
        logs.append(success)

    # 最終的に trim は実施
    res = title.strip()
    if details:
        return (logs, res)
    return res


def test(title, rule):
    ''' rule が有効か否かをテストする '''
    (logs, res) = convert(title, rules=[rule], details=True)
    return (all(logs), res)


def alltest(title, rule):
    ''' rule が有効か否かをテストする '''
    rules = ItemNameFormat.get_ordered(rule)
    (logs, res) = convert(title, rules=rules, details=True)
    return (all(logs), res)

