#!/usr/bin/python 
# -*- coding: utf-8 -*-

'''
商品画像の比較を行う関数を提供します。
'''
import codecs
import math

import cv2
import numpy as np
import imagehash
from PIL import Image

from richs_utils import RichsUtils

def similar_fast(path1, path2, similarity=0.8):
    '''
    img1 と img2 が規定の類似度を超えるかを判定します。

    :return: Tuple of (similar_or_not, calculated similarity value)
    '''
    value = RichsUtils.diff(path1, path2)
    return (value > similarity, value)


def _resize(img1, height=200):
    (w1, h1) = (img1.shape[1], img1.shape[0])
    width = int(float(w1 * height) / float(h1))
    return cv2.resize(img1, (width, height))


def _load_image(img1, img2):
    ''' load images into array and resize them '''
    if isinstance(img1, str):
        img1 = cv2.imread(img1)

    if isinstance(img2, str):
        img2 = cv2.imread(img2)

    (w1, h1) = (img1.shape[1], img1.shape[0])
    (w2, h2) = (img2.shape[1], img2.shape[0])
    
    img1 = _resize(img1, height=min(h1, h2))
    img2 = _resize(img2, height=min(h1, h2))

    # 面積が小さい方が左手に来る
    return (img1, img2) if w1*h1 <= w2*h2 else (img2, img1)
 

def _deg(p1, p2, p3):
    ''' 3点の角度計算 (度数法) '''
    v1 = (p2[0] - p1[0], p2[1] - p1[1])
    v2 = (p3[0] - p1[0], p3[1] - p1[1])
    d1 = math.sqrt(v1[0]*v1[0] + v1[1]*v1[1])
    d2 = math.sqrt(v2[0]*v2[0] + v2[1]*v2[1])
    if d1 < 0.00001 or d2 < 0.00001:
        return None
    cos = (v1[0] * v2[0] + v1[1] * v2[1]) / (d1 * d2)
    if -1.0 <= cos <= 1.0:
        return math.degrees(math.acos(cos))
    else:
        return None


def opencv2pil(cv2img):
    cv2_img_rgb = cv2img[:, :, ::-1].copy()
    return Image.fromarray(cv2_img_rgb)


def _dst_hash(img):
    img_pil = opencv2pil(img)
    h2 = imagehash.dhash(img_pil, hash_size=32)
    dist = 0
    for (p, n) in zip(h2.hash, h2.hash[1:]):
        dist += np.count_nonzero(p.flatten() != n.flatten())
    return dist
 

def _is_similar_matching(img1, img2, 
        debug=False, debug_output='/tmp/similar_matching.jpg', 
        th_dist=350.0, th_hash=60, th_deg=20.0, min_points=10):
    '''
    類似度計算を行う
    :param cv2.Image img1: left image 
    :param cv2.Image img2: right image
    :param bool debug: needs debug output 
    :param str debug_output: debug output image file path
    :param float th_dist: threshold distance (algorithm parameter)
    :param int th_hash: threshold imagehash bit on 32x32 (algorithm parameter)
    :param float th_deg: threshold degrees (algorithm parameter)
    :param int min_points: threshold match point count (algorithm parameter)
    :return bool: similar matched or not
    '''
    gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)

    # AKAZE アルゴリズムにより特徴点を抽出
    detector = cv2.AKAZE_create()
    (kp1, desc1) = detector.detectAndCompute(gray1, None)
    (kp2, desc2) = detector.detectAndCompute(gray2, None)

    matcher = cv2.BFMatcher(crossCheck=True)
    matches = matcher.knnMatch(desc1, desc2, k=1)
    matches = filter(lambda m: len(m) > 0, matches)
    matches = sorted(matches, key=lambda ms: ms[0].distance)

    params = {}
    params['points'] = len(matches)
    if len(matches) < min_points:
        params['message'] = '画像の類似特徴点が一定数以下'
        return (False, params)

    params['distance'] = matches[0][0].distance
    if matches[0][0].distance > th_dist:
        params['message'] = '画像の類似特徴点の性質が悪い'
        return (False, params)

    # 得られた特徴点から img2 画像の対応領域を判定
    goods = matches[:min_points]
    src_pts = np.float32([ kp1[m[0].queryIdx].pt for m in goods ]).reshape(-1, 1, 2)
    dst_pts = np.float32([ kp2[m[0].trainIdx].pt for m in goods ]).reshape(-1, 1, 2)
    
    (M, mask) = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
    matchesMask = mask.ravel().tolist()

    (h, w) = (img1.shape[0], img1.shape[1])
    pts = np.float32([ [0, 0], [0, h-1], [w-1, h-1], [w-1, 0] ]).reshape(-1,1,2)
    dst = cv2.perspectiveTransform(pts, M)

    if debug and debug_output is not None:
        linedimg2 = cv2.polylines(img2.copy() ,[np.int32(dst)], True, 255, 3, cv2.LINE_AA)
        img3 = cv2.drawMatchesKnn(
            img1, kp1, linedimg2, kp2, list(goods), None, flags=2)
        cv2.imwrite(debug_output, img3)


    # 対応領域の角度の計算
    # 今回は同じような画像を探すので、極端な回転などがある場合は
    # 画像を一致させないようにしたい
    # 長方形に近い四角形を検出できていればOK
    lt = (dst[0][0][0], dst[0][0][1])
    lb = (dst[1][0][0], dst[1][0][1])
    rb = (dst[2][0][0], dst[2][0][1])
    rt = (dst[3][0][0], dst[3][0][1])
    ds = [ _deg(lt, lb, rt), _deg(lb, lt, rb), _deg(rb, lb, rt), _deg(rt, lt, rb)]
    params['degrees'] = ds
    for d in ds:
        if not ( (90.0 - th_deg) <= d <= (90 + th_deg) ):
            params['message'] = '対応領域が歪な四角形'
            return (False, params)

    # 対応領域を塗りつぶした場合の全体の濃淡をチェック
    filled2 = cv2.fillPoly(img2.copy(), [np.int32(dst)], (255, 255, 255))
    dhash = _dst_hash(filled2)
    params['dst_hash'] = dhash
    if dhash > th_hash:
        params['message'] = '対応領域の面積が２つの画像で大きく異なる'
        return (False, params)

    params['message'] = '成功'
    return (True, params)



def similar(path1, path2, dual_check=True):
    '''
    img1 と img2 の類似度を時間のかかるアルゴリズムによって判断します。
    :param str path1: image path 1
    :param str path2: image path 2
    :param bool dual_check: run dual check if True (of cource slow)
    :return: tuple (bool, list):  (similar both images or not, check details list). 
    '''
    (img1, img2) = _load_image(path1, path2)
    if dual_check:
        (f1, p1) = _is_similar_matching(img1, img2)
        (f2, p2) = _is_similar_matching(img2, img1)
        return (f1 and f2, [(f1, p1), (f2, p2)])
    else:
        (found, param) = _is_similar_matching(img1, img2)
        return (found, [(found, param)])


