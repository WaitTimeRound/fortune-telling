#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""western_pan.py - 西方占星排盘（优化版）

基于 ephem 计算行星位置、宫位、相位，输出完整的本命星盘数据。
优化结构：Big Three 置顶、行星按层级分组、宫位按性质分组、相位按容许度分级、
元素与模式统计、星盘格局识别。

Usage:
    python western_pan.py <year> <month> <day> <hour> <minute> <city>

Example:
    python western_pan.py 1990 5 15 14 30 北京
"""
import json
import math
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(__file__))
import lunar_convert

try:
    import ephem
except ImportError:
    ephem = None


# ========== 星座元数据 ==========
SIGN_METADATA = {
    '白羊座':   {'element': 'fire',    'modality': 'cardinal', 'ruler_classical': '火星',   'ruler_modern': '火星'},
    '金牛座':   {'element': 'earth',   'modality': 'fixed',    'ruler_classical': '金星',   'ruler_modern': '金星'},
    '双子座':   {'element': 'air',     'modality': 'mutable',  'ruler_classical': '水星',   'ruler_modern': '水星'},
    '巨蟹座':   {'element': 'water',   'modality': 'cardinal', 'ruler_classical': '月亮',   'ruler_modern': '月亮'},
    '狮子座':   {'element': 'fire',    'modality': 'fixed',    'ruler_classical': '太阳',   'ruler_modern': '太阳'},
    '处女座':   {'element': 'earth',   'modality': 'mutable',  'ruler_classical': '水星',   'ruler_modern': '水星'},
    '天秤座':   {'element': 'air',     'modality': 'cardinal', 'ruler_classical': '金星',   'ruler_modern': '金星'},
    '天蝎座':   {'element': 'water',   'modality': 'fixed',    'ruler_classical': '火星',   'ruler_modern': '冥王星'},
    '射手座':   {'element': 'fire',    'modality': 'mutable',  'ruler_classical': '木星',   'ruler_modern': '木星'},
    '摩羯座':   {'element': 'earth',   'modality': 'cardinal', 'ruler_classical': '土星',   'ruler_modern': '土星'},
    '水瓶座':   {'element': 'air',     'modality': 'fixed',    'ruler_classical': '土星',   'ruler_modern': '天王星'},
    '双鱼座':   {'element': 'water',   'modality': 'mutable',  'ruler_classical': '木星',   'ruler_modern': '海王星'}
}

# 行星层级分类
PLANET_TIERS = {
    'inner': ['太阳', '月亮', '水星', '金星', '火星'],
    'outer': ['木星', '土星'],
    'transpersonal': ['天王星', '海王星', '冥王星']
}

# 宫位性质分类
HOUSE_QUALITIES = {
    'angular': [1, 4, 7, 10],
    'succedent': [2, 5, 8, 11],
    'cadent': [3, 6, 9, 12]
}


def _get_sign_from_longitude(lon_deg):
    """根据黄经获取星座"""
    idx = int(lon_deg / 30) % 12
    return lunar_convert.WESTERN_SIGNS[idx]


def _format_degree(deg):
    """将度数格式化为 XX°XX' 格式"""
    d = int(deg)
    m = int((deg - d) * 60)
    return f"{d}°{m:02d}'"


def get_planet_in_house(planet_longitude, houses):
    """判断行星落在哪个宫位"""
    for i in range(1, 13):
        cusp_current = houses[i]['cusp']
        cusp_next = houses[(i % 12) + 1]['cusp']
        if cusp_current < cusp_next:
            if cusp_current <= planet_longitude < cusp_next:
                return i
        else:
            if planet_longitude >= cusp_current or planet_longitude < cusp_next:
                return i
    return 1


def get_retrograde_status(dt, lat, lon, planet_en):
    """检测行星是否逆行"""
    if ephem is None:
        return False
    
    observer = ephem.Observer()
    observer.lat = str(lat)
    observer.lon = str(lon)
    observer.elevation = 0
    utc = dt - timedelta(hours=8)
    observer.date = utc.strftime('%Y/%m/%d %H:%M:%S')
    
    # 获取行星和前一天的位置比较
    planet_class = getattr(ephem, planet_en)
    p1 = planet_class(observer)
    lon1 = math.degrees(float(ephem.Ecliptic(p1, epoch=observer.date).lon))
    
    observer.date = (utc - timedelta(days=1)).strftime('%Y/%m/%d %H:%M:%S')
    p2 = planet_class(observer)
    lon2 = math.degrees(float(ephem.Ecliptic(p2, epoch=observer.date).lon))
    
    # 逆行：黄经减小（注意 360° 边界）
    diff = lon1 - lon2
    if diff < -180:
        diff += 360
    elif diff > 180:
        diff -= 360
    
    return diff < -0.01


def build_planet_details(planets, houses, dt, lat, lon):
    """构建行星详细信息，包含宫位、逆行状态"""
    details = {}
    for name, data in planets.items():
        if name == '上升点':
            continue
        
        house = get_planet_in_house(data['longitude'], houses)
        sign = data['sign']
        meta = SIGN_METADATA.get(sign, {})
        
        retrograde = get_retrograde_status(dt, lat, lon, data['planet_en'])
        
        details[name] = {
            'name': name,
            'longitude': data['longitude'],
            'degree': _format_degree(data['longitude'] % 30),
            'sign': sign,
            'sign_en': data['sign_en'],
            'element': meta.get('element'),
            'modality': meta.get('modality'),
            'house': house,
            'retrograde': retrograde,
            'planet_en': data['planet_en']
        }
    return details


def group_planets_by_tier(planet_details):
    """按层级分组行星"""
    result = {'inner': [], 'outer': [], 'transpersonal': []}
    for name, data in planet_details.items():
        for tier, names in PLANET_TIERS.items():
            if name in names:
                result[tier].append(data)
                break
    # 每组内按宫位排序
    for tier in result:
        result[tier].sort(key=lambda x: x['house'])
    return result


def build_house_details(houses, planet_details):
    """构建宫位详细信息，包含宫内行星"""
    result = {}
    for quality, house_numbers in HOUSE_QUALITIES.items():
        result[quality] = []
        for num in house_numbers:
            sign = houses[num]['sign']
            meta = SIGN_METADATA.get(sign, {})
            
            # 找出该宫内的行星
            planets_in_house = [
                {'name': p['name'], 'longitude': p['longitude'], 'degree': p['degree']}
                for p in planet_details.values()
                if p['house'] == num
            ]
            planets_in_house.sort(key=lambda x: x['longitude'])
            
            result[quality].append({
                'number': num,
                'cusp': houses[num]['cusp'],
                'sign': sign,
                'sign_en': lunar_convert.WESTERN_SIGNS_EN[lunar_convert.WESTERN_SIGNS.index(sign)],
                'element': meta.get('element'),
                'modality': meta.get('modality'),
                'ruler_classical': meta.get('ruler_classical'),
                'ruler_modern': meta.get('ruler_modern'),
                'planets': planets_in_house,
                'planet_count': len(planets_in_house),
                'empty': len(planets_in_house) == 0
            })
    return result


def classify_aspects(aspects):
    """按容许度分级相位"""
    result = {'tight': [], 'moderate': [], 'loose': []}
    for asp in aspects:
        orb = asp['orb']
        if orb <= 2:
            result['tight'].append(asp)
        elif orb <= 5:
            result['moderate'].append(asp)
        else:
            result['loose'].append(asp)
    
    # 每组内按 orb 排序
    for tier in result:
        result[tier].sort(key=lambda x: x['orb'])
    return result


def calculate_elements(planet_details):
    """统计元素分布"""
    counts = {'fire': 0, 'earth': 0, 'air': 0, 'water': 0}
    for p in planet_details.values():
        elem = p.get('element')
        if elem and elem in counts:
            counts[elem] += 1
    return counts


def calculate_modalities(planet_details):
    """统计模式分布"""
    counts = {'cardinal': 0, 'fixed': 0, 'mutable': 0}
    for p in planet_details.values():
        mod = p.get('modality')
        if mod and mod in counts:
            counts[mod] += 1
    return counts


def find_stelliums(planet_details, houses):
    """
    识别星群（Stellium）：3颗或以上行星落在同一星座或同一宫位。
    返回列表。
    """
    stelliums = []
    
    # 按星座分组
    sign_groups = {}
    for p in planet_details.values():
        sign = p['sign']
        sign_groups.setdefault(sign, []).append(p['name'])
    
    for sign, names in sign_groups.items():
        if len(names) >= 3:
            meta = SIGN_METADATA.get(sign, {})
            stelliums.append({
                'type': 'stellium_sign',
                'description': f"{'、'.join(names)} 聚集在 {sign}",
                'location': sign,
                'planets': names,
                'count': len(names),
                'element': meta.get('element'),
                'modality': meta.get('modality')
            })
    
    # 按宫位分组
    house_groups = {}
    for p in planet_details.values():
        house = p['house']
        house_groups.setdefault(house, []).append(p['name'])
    
    for house, names in house_groups.items():
        if len(names) >= 3:
            stelliums.append({
                'type': 'stellium_house',
                'description': f"{'、'.join(names)} 聚集在 第{house}宫",
                'location': f"第{house}宫",
                'planets': names,
                'count': len(names)
            })
    
    return stelliums


def find_t_squares(aspects, planet_details):
    """
    识别 T-Square（T三角）：
    两颗行星冲相（180°），第三颗行星与两者都刑相（90°）。
    """
    t_squares = []
    
    # 找出所有冲相
    oppositions = [a for a in aspects if a['aspect'] == '冲相']
    # 找出所有刑相
    squares = [a for a in aspects if a['aspect'] == '刑相']
    
    for opp in oppositions:
        p1, p2 = opp['planet1'], opp['planet2']
        # 找同时与 p1 和 p2 刑相的行星
        for sq in squares:
            if sq['planet1'] == p1 and sq['planet2'] not in (p1, p2):
                apex = sq['planet2']
                # 检查 apex 是否也与 p2 刑相
                for sq2 in squares:
                    if (sq2['planet1'] == apex and sq2['planet2'] == p2) or \
                       (sq2['planet2'] == apex and sq2['planet1'] == p2):
                        t_squares.append({
                            'type': 't_square',
                            'description': f"{p1} 冲 {p2}，{apex} 刑两者",
                            'opposition': [p1, p2],
                            'apex': apex,
                            'planets': [p1, p2, apex]
                        })
                        break
    
    return t_squares


def find_grand_trines(aspects, planet_details):
    """
    识别 Grand Trine（大三角）：
    三颗行星互成120°拱相。
    """
    grand_trines = []
    trines = [a for a in aspects if a['aspect'] == '拱相']
    
    # 构建图
    from collections import defaultdict
    graph = defaultdict(set)
    for t in trines:
        graph[t['planet1']].add(t['planet2'])
        graph[t['planet2']].add(t['planet1'])
    
    # 找三角形
    planets = list(graph.keys())
    for i in range(len(planets)):
        for j in range(i + 1, len(planets)):
            for k in range(j + 1, len(planets)):
                p1, p2, p3 = planets[i], planets[j], planets[k]
                if p2 in graph[p1] and p3 in graph[p1] and p3 in graph[p2]:
                    # 检查是否同一元素（更严格的大三角）
                    elems = [planet_details.get(p, {}).get('element') for p in (p1, p2, p3)]
                    same_element = len(set(elems)) == 1 and elems[0] is not None
                    grand_trines.append({
                        'type': 'grand_trine',
                        'description': f"{'、'.join([p1, p2, p3])} 形成大三角{'（同元素）' if same_element else ''}",
                        'planets': [p1, p2, p3],
                        'same_element': same_element,
                        'element': elems[0] if same_element else None
                    })
    
    return grand_trines


def find_yods(aspects, planet_details):
    """
    识别 Yod（上帝之指）：
    两颗行星60°六分，且都与第三颗行星150°梅花。
    """
    yods = []
    sextiles = [a for a in aspects if a['aspect'] == '六分相']
    quincunxes = [a for a in aspects if a['aspect'] == '梅花相']
    
    # 为每个六分相找共同的梅花相顶点
    for sextile in sextiles:
        p1, p2 = sextile['planet1'], sextile['planet2']
        
        # 找出所有与 p1 梅花相且不是 p2 的行星
        apex_from_p1 = set()
        for q in quincunxes:
            if q['planet1'] == p1 and q['planet2'] != p2:
                apex_from_p1.add(q['planet2'])
            elif q['planet2'] == p1 and q['planet1'] != p2:
                apex_from_p1.add(q['planet1'])
        
        # 检查这些候选顶点是否也与 p2 梅花相
        for apex in apex_from_p1:
            found = False
            for q in quincunxes:
                if (q['planet1'] == apex and q['planet2'] == p2) or \
                   (q['planet2'] == apex and q['planet1'] == p2):
                    found = True
                    break
            if found:
                yods.append({
                    'type': 'yod',
                    'description': f"{p1} 六分 {p2}，且均与 {apex} 梅花",
                    'base': [p1, p2],
                    'apex': apex,
                    'planets': [p1, p2, apex]
                })
    
    return yods


def build_patterns(planet_details, houses, aspects):
    """识别所有星盘格局"""
    patterns = {
        'stelliums': find_stelliums(planet_details, houses),
        't_squares': find_t_squares(aspects, planet_details),
        'grand_trines': find_grand_trines(aspects, planet_details),
        'yods': find_yods(aspects, planet_details)
    }
    return patterns


def main():
    if len(sys.argv) < 7:
        print("Usage: python western_pan.py <year> <month> <day> <hour> <minute> <city>")
        sys.exit(1)
    
    year = int(sys.argv[1])
    month = int(sys.argv[2])
    day = int(sys.argv[3])
    hour = int(sys.argv[4])
    minute = int(sys.argv[5])
    city = sys.argv[6]
    
    # 获取基础数据
    base = lunar_convert.get_bazi_pillars(year, month, day, hour, minute, '男', city)
    western = base.get('western', {})
    
    planets = western.get('planets', {})
    houses = western.get('houses', {})
    aspects = western.get('aspects', {})
    
    dt = datetime(year, month, day, hour, minute)
    lon = base.get('time_conversion', {}).get('longitude', 120.0)
    lat = base.get('time_conversion', {}).get('latitude', 39.9)
    
    # 1. Big Three
    asc = western.get('ascendant', {})
    big_three = {
        'sun': {
            'name': '太阳',
            'sign': planets.get('太阳', {}).get('sign', '未知'),
            'sign_en': planets.get('太阳', {}).get('sign_en', 'Unknown'),
            'degree': _format_degree(planets.get('太阳', {}).get('longitude', 0) % 30),
            'longitude': planets.get('太阳', {}).get('longitude', 0),
            'house': get_planet_in_house(planets.get('太阳', {}).get('longitude', 0), houses),
            'description': '核心身份、生命力、显意识的自我'
        },
        'moon': {
            'name': '月亮',
            'sign': planets.get('月亮', {}).get('sign', '未知'),
            'sign_en': planets.get('月亮', {}).get('sign_en', 'Unknown'),
            'degree': _format_degree(planets.get('月亮', {}).get('longitude', 0) % 30),
            'longitude': planets.get('月亮', {}).get('longitude', 0),
            'house': get_planet_in_house(planets.get('月亮', {}).get('longitude', 0), houses),
            'description': '情感景观、潜意识习惯、安全感来源'
        },
        'ascendant': {
            'name': '上升点',
            'sign': asc.get('sign', '未知'),
            'sign_en': asc.get('sign_en', 'Unknown'),
            'degree': _format_degree(asc.get('longitude', 0) % 30),
            'longitude': asc.get('longitude', 0),
            'house': 1,
            'description': '外在行为、社会面具、人生路径'
        }
    }
    
    # 2. 行星详细信息
    planet_details = build_planet_details(planets, houses, dt, lat, lon)
    
    # 3. 按层级分组
    planets_grouped = group_planets_by_tier(planet_details)
    
    # 4. 宫位详细信息
    house_details = build_house_details(houses, planet_details)
    
    # 5. 相位分级
    aspects_classified = classify_aspects(aspects)
    
    # 6. 元素与模式统计
    elements = calculate_elements(planet_details)
    modalities = calculate_modalities(planet_details)
    
    # 7. 星盘格局
    patterns = build_patterns(planet_details, houses, aspects)
    
    # 8. 整理输出
    result = {
        'input': {
            'year': year, 'month': month, 'day': day,
            'hour': hour, 'minute': minute,
            'city': city
        },
        'time_conversion': base.get('time_conversion', {}),
        'big_three': big_three,
        'planets': planets_grouped,
        'houses': house_details,
        'aspects': aspects_classified,
        'elements': elements,
        'modalities': modalities,
        'patterns': patterns,
        'raw': {
            'planets': planets,
            'houses': houses,
            'aspects': aspects
        }
    }
    
    return result


if __name__ == '__main__':
    result = main()
    output_file = os.environ.get('FORTUNE_OUTPUT_FILE', 'western_result.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"Result written to {output_file}")
