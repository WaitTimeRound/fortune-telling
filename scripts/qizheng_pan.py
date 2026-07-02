#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""qizheng_pan.py - 七政四余示意排盘

基于 ephem 计算七政位置，cnlunar 获取二十八宿信息。
声明：本排盘为示意级，未接入实时精密星历，仅供文化娱乐参考。

Usage:
    python qizheng_pan.py <year> <month> <day> <hour> <minute> [city]

Example:
    python qizheng_pan.py 1990 5 15 14 30 北京
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

try:
    from cnlunar import Lunar
except ImportError:
    Lunar = None


# ========== 二十八宿数据 ==========
THE_28_XIU = [
    '角木蛟', '亢金龙', '氐土貉', '房日兔', '心月狐', '尾火虎', '箕水豹',  # 东方青龙
    '斗木獬', '牛金牛', '女土蝠', '虚日鼠', '危月燕', '室火猪', '壁水貐',  # 北方玄武
    '奎木狼', '娄金狗', '胃土雉', '昴日鸡', '毕月乌', '觜火猴', '参水猿',  # 西方白虎
    '井木犴', '鬼金羊', '柳土獐', '星日马', '张月鹿', '翼火蛇', '轸水蚓'   # 南方朱雀
]

XIU_ELEMENTS = {
    '角': '木', '亢': '金', '氐': '土', '房': '日', '心': '月', '尾': '火', '箕': '水',
    '斗': '木', '牛': '金', '女': '土', '虚': '日', '危': '月', '室': '火', '壁': '水',
    '奎': '木', '娄': '金', '胃': '土', '昴': '日', '毕': '月', '觜': '火', '参': '水',
    '井': '木', '鬼': '金', '柳': '土', '星': '日', '张': '月', '翼': '火', '轸': '水'
}

# 七政星与西方行星的对应
QIZHENG_PLANETS = {
    '太阳': 'Sun',
    '月亮': 'Moon',
    '水星': 'Mercury',
    '金星': 'Venus',
    '火星': 'Mars',
    '木星': 'Jupiter',
    '土星': 'Saturn'
}


def get_xiu_from_longitude(longitude):
    """根据黄经计算躔宿（简化：每个宿约13度）"""
    # 二十八宿总跨度约360度，每个宿约12.86度
    # 角宿起始于约0度（春分点）
    # 简化：每个宿13度
    xiu_idx = int(longitude / (360 / 28)) % 28
    return THE_28_XIU[xiu_idx]


def get_planet_status(planet_name, longitude, xiu_element):
    """
    判断星曜状态（庙旺/落陷/受克）。
    简化规则：星曜五行与宿度五行相生为庙，相克为落，同行为旺。
    """
    # 七政五行
    planet_wuxing = {
        '太阳': '火', '月亮': '水', '水星': '水', '金星': '金',
        '火星': '火', '木星': '木', '土星': '土'
    }
    
    pw = planet_wuxing.get(planet_name, '土')
    
    # 宿度五行转换：日视同火，月视同水
    xw = xiu_element
    if xw == '日':
        xw = '火'
    elif xw == '月':
        xw = '水'
    
    # 五行生克关系
    if pw == xw:
        return '旺（同气）'
    elif (lunar_convert.WUXING_IDX[xw] - lunar_convert.WUXING_IDX[pw]) % 5 == 4:
        return '庙（受生）'
    elif (lunar_convert.WUXING_IDX[xw] - lunar_convert.WUXING_IDX[pw]) % 5 == 3:
        return '落（受克）'
    elif (lunar_convert.WUXING_IDX[pw] - lunar_convert.WUXING_IDX[xw]) % 5 == 3:
        return '陷（克宿）'
    else:
        return '平'


def calculate_qizheng(dt, lat, lon):
    """计算七政位置"""
    if ephem is None:
        return {}
    
    observer = ephem.Observer()
    observer.lat = str(lat)
    observer.lon = str(lon)
    observer.elevation = 0
    
    utc = dt - timedelta(hours=8)
    observer.date = utc.strftime('%Y/%m/%d %H:%M:%S')
    
    result = {}
    for cn_name, en_name in QIZHENG_PLANETS.items():
        planet_class = getattr(ephem, en_name)
        planet = planet_class(observer)
        
        ecl = ephem.Ecliptic(planet, epoch=observer.date)
        lon_deg = math.degrees(float(ecl.lon)) % 360
        
        xiu = get_xiu_from_longitude(lon_deg)
        xiu_char = xiu[0]
        xiu_element = XIU_ELEMENTS.get(xiu_char, '土')
        status = get_planet_status(cn_name, lon_deg, xiu_element)
        
        result[cn_name] = {
            'longitude': round(lon_deg, 2),
            'xiu': xiu,
            'xiu_element': xiu_element,
            'status': status,
            'planet_en': en_name
        }
    
    return result


def calculate_siyu(dt, lat, lon):
    """
    计算四余星位置（简化示意）。
    罗睺=南交点，计都=北交点，紫炁=木星+30°，月孛=水星+30°（简化）
    """
    if ephem is None:
        return {}
    
    # 四余星简化计算
    # 实际四余星需要精密星历，这里做示意级简化
    
    result = {}
    qizheng = calculate_qizheng(dt, lat, lon)
    
    # 罗睺（南交点）：简化 = 月球交点的对宫
    # 计都（北交点）：简化 = 月球交点
    # 这里用占位符，因为 ephem 不直接提供月球交点
    if '月亮' in qizheng:
        moon_lon = qizheng['月亮']['longitude']
        # 简化：罗睺与月亮对宫，计都与月亮同宫（示意）
        result['罗睺'] = {
            'longitude': round((moon_lon + 180) % 360, 2),
            'xiu': get_xiu_from_longitude((moon_lon + 180) % 360),
            'status': '示意（未接入精密星历）',
            'description': '南交点，前世业力'
        }
        result['计都'] = {
            'longitude': round(moon_lon, 2),
            'xiu': get_xiu_from_longitude(moon_lon),
            'status': '示意（未接入精密星历）',
            'description': '北交点，今生成长方向'
        }
    
    # 紫炁：简化 = 木星 + 30°
    if '木星' in qizheng:
        jupiter_lon = qizheng['木星']['longitude']
        result['紫炁'] = {
            'longitude': round((jupiter_lon + 30) % 360, 2),
            'xiu': get_xiu_from_longitude((jupiter_lon + 30) % 360),
            'status': '示意（简化计算）',
            'description': '清高、精神追求'
        }
    
    # 月孛：简化 = 水星 + 30°
    if '水星' in qizheng:
        mercury_lon = qizheng['水星']['longitude']
        result['月孛'] = {
            'longitude': round((mercury_lon + 30) % 360, 2),
            'xiu': get_xiu_from_longitude((mercury_lon + 30) % 360),
            'status': '示意（简化计算）',
            'description': '情欲、桃花、暗昧'
        }
    
    return result


def get_dongwei_daxian(year, gender, mingdu_zhi):
    """
    洞微大限（简化）。
    七政四余大限以命宫为起点，每宫10年（或按五行局数）。
    """
    mingdu_idx = lunar_convert.DIZHI.index(mingdu_zhi)
    daxian = []
    for i in range(12):
        start_age = 10 + i * 10
        zhi_pos = (mingdu_idx + i) % 12
        daxian.append({
            'index': i + 1,
            'zhi': lunar_convert.DIZHI[zhi_pos],
            'age_start': start_age,
            'age_end': start_age + 9
        })
    return daxian


def main():
    if len(sys.argv) < 6:
        print("Usage: python qizheng_pan.py <year> <month> <day> <hour> <minute> [city]")
        sys.exit(1)
    
    year = int(sys.argv[1])
    month = int(sys.argv[2])
    day = int(sys.argv[3])
    hour = int(sys.argv[4])
    minute = int(sys.argv[5])
    city = sys.argv[6] if len(sys.argv) > 6 else None
    
    # 获取基础数据（真太阳时 + 农历）
    base = lunar_convert.get_bazi_pillars(year, month, day, hour, minute, '男', city)
    
    dt = datetime(year, month, day, hour, minute)
    lon = base.get('time_conversion', {}).get('longitude', 120.0)
    lat = base.get('time_conversion', {}).get('latitude', 39.9)
    
    # 计算七政
    qizheng = calculate_qizheng(dt, lat, lon)
    
    # 计算四余
    siyu = calculate_siyu(dt, lat, lon)
    
    # 二十八宿（当日值宿）
    today_xiu = '未知'
    if Lunar is not None:
        lunar_dt = Lunar(dt)
        today_xiu = lunar_dt.get_the28Stars()
    
    # 命度主（简化：以太阳为命度主示意）
    mingdu = qizheng.get('太阳', {})
    
    # 洞微大限
    # 命度主所在的地支（简化）
    if mingdu:
        mingdu_lon = mingdu['longitude']
        mingdu_zhi = lunar_convert.DIZHI[int(mingdu_lon / 30) % 12]
    else:
        mingdu_zhi = '子'
    
    daxian = get_dongwei_daxian(year, '男', mingdu_zhi)
    
    result = {
        'input': {
            'year': year, 'month': month, 'day': day,
            'hour': hour, 'minute': minute,
            'city': city
        },
        'time_conversion': base.get('time_conversion', {}),
        'disclaimer': '本排盘为示意级简化版本，未接入实时精密星历。七政四余极度依赖精密星历，所有星曜躔宿、庙旺喜乐、受克情况的标注可能存在偏差。强烈建议使用专业七政四余排盘软件获取精确命盘后复核。以下内容仅供文化娱乐参考。',
        'today_xiu': today_xiu,
        'mingdu': mingdu,
        'qizheng': qizheng,
        'siyu': siyu,
        'daxian': daxian
    }
    
    return result


if __name__ == '__main__':
    result = main()
    output_file = os.environ.get('FORTUNE_OUTPUT_FILE', 'qizheng_result.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"Result written to {output_file}")
