#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bazi_pan.py - 八字排盘完整分析

基于 lunar_convert.py，添加格局判断、调候用神、喜用神等高级分析。

Usage:
    python bazi_pan.py <year> <month> <day> <hour> <minute> <gender> [city]

Example:
    python bazi_pan.py 1990 5 15 14 30 男 北京
    python bazi_pan.py 1990 5 15 14 30 男
"""
import argparse
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))
import lunar_convert


# ========== 八字高级分析 ==========

def analyze_pattern(pillars, wuxing_count, day_gan, month_zhi):
    """
    判断格局类型。
    返回: {'type': str, 'description': str, 'strength': str}
    """
    # 计算日主得令、得地、得势
    day_element = lunar_convert.ELEMENT_TG[lunar_convert.TIANGAN.index(day_gan)]
    month_element = lunar_convert.ELEMENT_DZ[lunar_convert.DIZHI.index(month_zhi)]
    
    # 得令：月令五行与日主相同或生助日主
    de_ling = False
    if month_element == day_element:
        de_ling = True
    elif (lunar_convert.WUXING_IDX[month_element] - lunar_convert.WUXING_IDX[day_element]) % 5 == 4:
        de_ling = True
    
    # 得地：地支中有根（同五行或生我者）
    de_di = False
    for name in ['year', 'month', 'day', 'hour']:
        zhi = pillars[name][1]
        zhi_element = lunar_convert.ELEMENT_DZ[lunar_convert.DIZHI.index(zhi)]
        if zhi_element == day_element:
            de_di = True
            break
        if (lunar_convert.WUXING_IDX[zhi_element] - lunar_convert.WUXING_IDX[day_element]) % 5 == 4:
            de_di = True
            break
    
    # 得势：天干中有比劫或印星
    de_shi = False
    for name in ['year', 'month', 'hour']:
        gan = pillars[name][0]
        gan_element = lunar_convert.ELEMENT_TG[lunar_convert.TIANGAN.index(gan)]
        if gan_element == day_element:
            de_shi = True
            break
        if (lunar_convert.WUXING_IDX[gan_element] - lunar_convert.WUXING_IDX[day_element]) % 5 == 4:
            de_shi = True
            break
    
    score = sum([de_ling, de_di, de_shi])
    
    if score >= 2:
        strength = '偏旺'
    elif score == 1:
        strength = '中和'
    else:
        strength = '偏弱'
    
    # 判断从格
    # 从格：日主极弱，无根气，月令亦为克/泄/耗，且天干不透印比。
    if score == 0 and not de_ling:
        # 月令须为克、泄、耗日主之五行（不能是比劫/印星）
        month_is_helper = (month_element == day_element) or \
            (lunar_convert.WUXING_IDX[month_element] - lunar_convert.WUXING_IDX[day_element]) % 5 == 4
        if not month_is_helper:
            # 检查地支藏干是否有日主根气（同五行或印星）
            has_root_in_canggan = False
            for name in ['year', 'month', 'day', 'hour']:
                zhi = pillars[name][1]
                for cg in lunar_convert.DIZHI_CANGGAN[zhi]:
                    cg_element = lunar_convert.ELEMENT_TG[lunar_convert.TIANGAN.index(cg)]
                    if cg == day_gan:
                        has_root_in_canggan = True
                        break
                    if (lunar_convert.WUXING_IDX[cg_element] - lunar_convert.WUXING_IDX[day_element]) % 5 in [0, 4]:
                        has_root_in_canggan = True
                        break
                if has_root_in_canggan:
                    break

            # 检查天干是否透出印比（日主柱除外）
            has_yinbi_in_tiangan = False
            for name in ['year', 'month', 'hour']:
                gan = pillars[name][0]
                # 因 score == 0，其它柱天干不可能再是日主；若未来阈值调整，
                # 此处将日主透干视为比劫根气，直接判定从格不成立。
                if gan == day_gan:
                    has_yinbi_in_tiangan = True
                    break
                gan_element = lunar_convert.ELEMENT_TG[lunar_convert.TIANGAN.index(gan)]
                if gan_element == day_element:
                    has_yinbi_in_tiangan = True
                    break
                if (lunar_convert.WUXING_IDX[gan_element] - lunar_convert.WUXING_IDX[day_element]) % 5 == 4:
                    has_yinbi_in_tiangan = True
                    break

            # 检查是否全盘克制/泄/耗日主（日主天干本身不计入克制/泄/耗）
            all_counter = True
            for name in ['year', 'month', 'day', 'hour']:
                gan = pillars[name][0]
                zhi = pillars[name][1]
                zhi_element = lunar_convert.ELEMENT_DZ[lunar_convert.DIZHI.index(zhi)]
                if (lunar_convert.WUXING_IDX[zhi_element] - lunar_convert.WUXING_IDX[day_element]) % 5 not in [1, 2, 3]:
                    all_counter = False
                    break
                # 日主天干本身为比劫，不视为克泄耗；其它柱天干若为印比则从格不成立
                if gan != day_gan:
                    gan_element = lunar_convert.ELEMENT_TG[lunar_convert.TIANGAN.index(gan)]
                    if (lunar_convert.WUXING_IDX[gan_element] - lunar_convert.WUXING_IDX[day_element]) % 5 not in [1, 2, 3]:
                        all_counter = False
                        break

            if all_counter and not has_root_in_canggan and not has_yinbi_in_tiangan:
                return {'type': '从格', 'description': '日主极弱，无根气，从格成立', 'strength': '极弱'}
    
    # 正格判断
    # 根据月令地支本气十神判断格局
    month_zhi = pillars['month'][1]
    month_main_qi = lunar_convert.DIZHI_CANGGAN[month_zhi][0]
    month_shishen = lunar_convert.get_shishen(day_gan, month_main_qi)
    
    pattern_map = {
        '正官': '正官格',
        '七杀': '七杀格',
        '正印': '正印格',
        '偏印': '偏印格',
        '食神': '食神格',
        '伤官': '伤官格',
        '正财': '正财格',
        '偏财': '偏财格',
        '比肩': '建禄格/月劫格',
        '劫财': '建禄格/月劫格'
    }
    
    pattern = pattern_map.get(month_shishen, '正格')
    
    return {
        'type': pattern,
        'description': f'月令为{month_shishen}，{pattern}。日主{strength}。',
        'strength': strength,
        'de_ling': de_ling,
        'de_di': de_di,
        'de_shi': de_shi
    }


def analyze_tiaohou(day_gan, month_zhi, wuxing_count):
    """
    调候用神分析。
    根据出生季节和日主五行，判断需要调候的五行。
    """
    # 月份对应季节
    month_num = lunar_convert.DIZHI.index(month_zhi) + 1
    season = ''
    if month_num in [11, 12, 1]:  # 子丑寅
        season = '冬'
    elif month_num in [2, 3, 4]:  # 卯辰巳
        season = '春'
    elif month_num in [5, 6, 7]:  # 午未申
        season = '夏'
    elif month_num in [8, 9, 10]:  # 酉戌亥
        season = '秋'
    
    day_element = lunar_convert.ELEMENT_TG[lunar_convert.TIANGAN.index(day_gan)]
    
    # 调候用神规则（简化）
    tiaohou_map = {
        ('冬', '木'): '丙火',
        ('冬', '火'): '甲木',
        ('冬', '土'): '丙火',
        ('冬', '金'): '丁火',
        ('冬', '水'): '丙火',
        ('春', '木'): '丙火',
        ('春', '火'): '壬水',
        ('春', '土'): '丙火',
        ('春', '金'): '壬水',
        ('春', '水'): '戊土',
        ('夏', '木'): '癸水',
        ('夏', '火'): '壬水',
        ('夏', '土'): '癸水',
        ('夏', '金'): '壬水',
        ('夏', '水'): '庚金',
        ('秋', '木'): '癸水',
        ('秋', '火'): '甲木',
        ('秋', '土'): '丙火',
        ('秋', '金'): '丁火',
        ('秋', '水'): '辛金',
    }
    
    tiaohou = tiaohou_map.get((season, day_element), '根据具体命局调整')
    
    return {
        'season': season,
        'tiaohou_yongshen': tiaohou,
        'description': f'出生于{season}季，日主属{day_element}，调候用神为{tiaohou}。'
    }


def analyze_xiyongshen(pattern, wuxing_count, day_gan):
    """
    喜用神分析（格局用神 + 扶抑用神）。
    """
    day_element = lunar_convert.ELEMENT_TG[lunar_convert.TIANGAN.index(day_gan)]
    strength = pattern['strength']
    
    # 扶抑用神：旺则泄/克，弱则生/助
    if pattern['type'] == '从格':
        # 从格：日主极弱无根，弃命从势，喜克泄耗
        xiyong = '官杀、食伤、财星'
    elif strength in ['偏旺', '极旺']:
        # 需要克、泄、耗
        # 克我者：官杀；我生者：食伤；我克者：财星
        xiyong = '官杀、食伤、财星'
    elif strength == '偏弱':
        # 需要生、助
        # 生我者：印星；同我者：比劫
        xiyong = '印星、比劫'
    else:
        xiyong = '根据大运流年调整'
    
    # 最喜的五行
    wuxing_sorted = sorted(wuxing_count.items(), key=lambda x: x[1])
    weakest = wuxing_sorted[0][0]
    strongest = wuxing_sorted[-1][0]
    
    return {
        'xiyong': xiyong,
        'weakest_wuxing': weakest,
        'strongest_wuxing': strongest,
        'description': f'格局用神：{pattern["type"]}。日主{strength}，喜{xiyong}。'
    }


def analyze_dayun_quality(dayun_list, day_gan, xiyongshen):
    """
    对大运进行质量评估。
    """
    day_element = lunar_convert.ELEMENT_TG[lunar_convert.TIANGAN.index(day_gan)]
    results = []

    # 喜用神类别集合
    yinbi_stars = {'正印', '偏印', '比肩', '劫财'}
    kexie_stars = {'正官', '七杀', '食神', '伤官', '正财', '偏财'}

    for dy in dayun_list:
        ganzhi = dy['ganzhi']
        gan = ganzhi[0]
        zhi = ganzhi[1]
        gan_element = lunar_convert.ELEMENT_TG[lunar_convert.TIANGAN.index(gan)]
        zhi_element = lunar_convert.ELEMENT_DZ[lunar_convert.DIZHI.index(zhi)]

        shishen = lunar_convert.get_shishen(day_gan, gan)

        # 简单评估：喜用神为吉，忌神为凶
        quality = '中平'
        # 将喜用神描述展开为具体十神集合
        xiyong_map = {
            '印星': {'正印', '偏印'},
            '比劫': {'比肩', '劫财'},
            '官杀': {'正官', '七杀'},
            '食伤': {'食神', '伤官'},
            '财星': {'正财', '偏财'}
        }
        xiyong_set = set()
        for item in xiyongshen['xiyong'].replace('、', ',').split(','):
            item = item.strip()
            xiyong_set.update(xiyong_map.get(item, {item}))
        if shishen in xiyong_set:
            quality = '吉'

        results.append({
            **dy,
            'shishen': shishen,
            'quality': quality
        })

    return results


def main():
    parser = argparse.ArgumentParser(description='八字排盘完整分析')
    parser.add_argument('year', type=int, help='出生年份')
    parser.add_argument('month', type=int, help='出生月份 (1-12)')
    parser.add_argument('day', type=int, help='出生日期 (1-31)')
    parser.add_argument('hour', type=int, help='出生小时 (0-23)')
    parser.add_argument('minute', type=int, help='出生分钟 (0-59)')
    parser.add_argument('gender', choices=['男', '女'], help='性别')
    parser.add_argument('city', nargs='?', default=None, help='出生城市（可选）')
    args = parser.parse_args()
    
    try:
        datetime(args.year, args.month, args.day, args.hour, args.minute)
    except ValueError as e:
        parser.error(f"无效日期时间: {e}")
    
    year, month, day, hour, minute, gender, city = \
        args.year, args.month, args.day, args.hour, args.minute, args.gender, args.city

    # 获取基础数据
    base = lunar_convert.get_bazi_pillars(year, month, day, hour, minute, gender, city)
    
    pillars = base['pillars']
    day_gan = pillars['day'][0]
    month_zhi = pillars['month'][1]
    wuxing_count = base['wuxing_count']
    
    # 高级分析
    pattern = analyze_pattern(pillars, wuxing_count, day_gan, month_zhi)
    tiaohou = analyze_tiaohou(day_gan, month_zhi, wuxing_count)
    xiyongshen = analyze_xiyongshen(pattern, wuxing_count, day_gan)
    dayun_quality = analyze_dayun_quality(base['dayun'], day_gan, xiyongshen)
    
    result = {
        **base,
        'advanced': {
            'pattern': pattern,
            'tiaohou': tiaohou,
            'xiyongshen': xiyongshen
        },
        'dayun': dayun_quality
    }
    
    return result


if __name__ == '__main__':
    result = main()
    output_file = os.environ.get('FORTUNE_OUTPUT_FILE', 'bazi_result.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"Result written to {output_file}")
