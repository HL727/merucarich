#!/usr/bin/python 
# -*- coding: utf-8 -*-

'''
Django の Response のヘルパーです。
'''

import io
import csv
import urllib
import unicodedata

from django.http import HttpResponse

def csv_response(filename, rows, delimiter=',', encoding='cp932'):
    ''' django が csv ファイルを直接返すレスポンスを返します '''
    charset = 'Shift_JIS' if encoding == 'cp932' else encoding
    res = HttpResponse(content_type='text/csv; charset={}'.format(charset))
    filename = urllib.parse.quote(filename)
    res['Content-Disposition'] = 'attachment; filename*=UTF-8\'\'{}'.format(filename)
    
    sio = io.StringIO()
    writer = csv.writer(sio, delimiter=delimiter)
    for row in rows:
        writer.writerow(row)
    res.write(unicodedata.normalize('NFKC', sio.getvalue()).encode(encoding, 'ignore'))
    return res

