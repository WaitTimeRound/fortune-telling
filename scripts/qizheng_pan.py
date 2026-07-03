#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""qizheng_pan.py - 七政四余排盘

基于 ephem/pyswisseph 精密星历计算七政位置，pyswisseph 计算四余星
（罗睺、计都、紫炁、月孛），并提供真实二十八宿躔宿、命度主/身度主、
洞微大限等核心要素。

声明：七政四余流派众多，本实现综合现代天文星历与常见古籍算法，
仍属文化娱乐参考，建议用专业排盘软件复核。

Usage:
    python qizheng_pan.py <year> <month> <day> <hour> <minute> <gender> [city]

Example:
    python qizheng_pan.py 1990 5 15 14 30 男 北京
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
    import swisseph as swe
except ImportError:
    swe = None

try:
    from cnlunar import Lunar
except ImportError:
    Lunar = None


# ========== 二十八宿数据 ==========
# 采用传统宿度（总和约 365.25°），并按比例归一化到 360° 黄道。
# 同时记录每宿五行与度主星。
THE_28_XIU = [
    # 东方青龙
    {'name': '角', 'full': '角木蛟', 'degree': 12.0, 'wuxing': '木', 'ruler': '木星', 'animal': '蛟'},
    {'name': '亢', 'full': '亢金龙', 'degree': 9.0,  'wuxing': '金', 'ruler': '金星', 'animal': '龙'},
    {'name': '氐', 'full': '氐土貉', 'degree': 15.0, 'wuxing': '土', 'ruler': '土星', 'animal': '貉'},
    {'name': '房', 'full': '房日兔', 'degree': 5.0,  'wuxing': '日', 'ruler': '太阳', 'animal': '兔'},
    {'name': '心', 'full': '心月狐', 'degree': 5.0,  'wuxing': '月', 'ruler': '月亮', 'animal': '狐'},
    {'name': '尾', 'full': '尾火虎', 'degree': 18.0, 'wuxing': '火', 'ruler': '火星', 'animal': '虎'},
    {'name': '箕', 'full': '箕水豹', 'degree': 11.0, 'wuxing': '水', 'ruler': '水星', 'animal': '豹'},
    # 北方玄武
    {'name': '斗', 'full': '斗木獬', 'degree': 26.0, 'wuxing': '木', 'ruler': '木星', 'animal': '獬'},
    {'name': '牛', 'full': '牛金牛', 'degree': 8.0,  'wuxing': '金', 'ruler': '金星', 'animal': '牛'},
    {'name': '女', 'full': '女土蝠', 'degree': 12.0, 'wuxing': '土', 'ruler': '土星', 'animal': '蝠'},
    {'name': '虚', 'full': '虚日鼠', 'degree': 10.0, 'wuxing': '日', 'ruler': '太阳', 'animal': '鼠'},
    {'name': '危', 'full': '危月燕', 'degree': 17.0, 'wuxing': '月', 'ruler': '月亮', 'animal': '燕'},
    {'name': '室', 'full': '室火猪', 'degree': 16.0, 'wuxing': '火', 'ruler': '火星', 'animal': '猪'},
    {'name': '壁', 'full': '壁水貐', 'degree': 9.0,  'wuxing': '水', 'ruler': '水星', 'animal': '貐'},
    # 西方白虎
    {'name': '奎', 'full': '奎木狼', 'degree': 16.0, 'wuxing': '木', 'ruler': '木星', 'animal': '狼'},
    {'name': '娄', 'full': '娄金狗', 'degree': 12.0, 'wuxing': '金', 'ruler': '金星', 'animal': '狗'},
    {'name': '胃', 'full': '胃土雉', 'degree': 14.0, 'wuxing': '土', 'ruler': '土星', 'animal': '雉'},
    {'name': '昴', 'full': '昴日鸡', 'degree': 11.0, 'wuxing': '日', 'ruler': '太阳', 'animal': '鸡'},
    {'name': '毕', 'full': '毕月乌', 'degree': 16.0, 'wuxing': '月', 'ruler': '月亮', 'animal': '乌'},
    {'name': '觜', 'full': '觜火猴', 'degree': 2.0,  'wuxing': '火', 'ruler': '火星', 'animal': '猴'},
    {'name': '参', 'full': '参水猿', 'degree': 9.0,  'wuxing': '水', 'ruler': '水星', 'animal': '猿'},
    # 南方朱雀
    {'name': '井', 'full': '井木犴', 'degree': 32.0, 'wuxing': '木', 'ruler': '木星', 'animal': '犴'},
    {'name': '鬼', 'full': '鬼金羊', 'degree': 4.0,  'wuxing': '金', 'ruler': '金星', 'animal': '羊'},
    {'name': '柳', 'full': '柳土獐', 'degree': 15.0, 'wuxing': '土', 'ruler': '土星', 'animal': '獐'},
    {'name': '星', 'full': '星日马', 'degree': 7.0,  'wuxing': '日', 'ruler': '太阳', 'animal': '马'},
    {'name': '张', 'full': '张月鹿', 'degree': 18.0, 'wuxing': '月', 'ruler': '月亮', 'animal': '鹿'},
    {'name': '翼', 'full': '翼火蛇', 'degree': 18.0, 'wuxing': '火', 'ruler': '火星', 'animal': '蛇'},
    {'name': '轸', 'full': '轸水蚓', 'degree': 17.0, 'wuxing': '水', 'ruler': '水星', 'animal': '蚓'},
]

_XIU_TOTAL_DEGREE = sum(x['degree'] for x in THE_28_XIU)

# 二十八宿起度参数（示意性经验值）。
# 不同流派、不同历元的宿度起算差异较大，这里采用：
#   - J2000 年角宿起点约 204° 黄经（传统宿度与现代黄道的粗略对应）
#   - 岁差约每 71.6 年退行 1°
# 若需要更高精度，可使用 swisseph 的恒星黄道（ayanamsa）自行校准。
_XIU_J2000_START = 204.0
_PRECESSION_YEAR = 71.6

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

# 星座 -> 地支（七政四余十二宫分配）
_SIGN_TO_DIZHI = ['卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥', '子', '丑', '寅']


def _build_xiu_table(year):
    """
    根据年份构建岁差修正后的二十八宿黄经表。
    返回 [{name, full, start, width, degree, wuxing, ruler}, ...]
    """
    # 岁差修正：J2000 起每年约退行 1/_PRECESSION_YEAR 度
    offset = _XIU_J2000_START + (year - 2000) / _PRECESSION_YEAR
    offset = offset % 360
    
    table = []
    current = offset
    for x in THE_28_XIU:
        width = x['degree'] / _XIU_TOTAL_DEGREE * 360.0
        table.append({
            **x,
            'start': current % 360,
            'width': width
        })
        current += width
    
    return table


def get_xiu_from_longitude(longitude, year):
    """
    根据黄经和年份计算躔宿，返回宿信息和入宿度数。
    """
    lon = longitude % 360
    table = _build_xiu_table(year)
    
    # 找到包含该黄经的宿
    for i, x in enumerate(table):
        start = x['start']
        end = (start + x['width']) % 360
        
        if start <= end:
            in_xiu = start <= lon < end
        else:
            # 跨越 0°
            in_xiu = lon >= start or lon < end
        
        if in_xiu:
            entry_deg = (lon - start) % 360
            if entry_deg >= x['width']:
                entry_deg -= 360
            return {
                'xiu': x['full'],
                'xiu_char': x['name'],
                'xiu_element': x['wuxing'],
                'xiu_ruler': x['ruler'],
                'xiu_degree': round(entry_deg, 2),
                'xiu_width': round(x['width'], 2)
            }
    
    # 兜底（理论上不会到达）
    x = table[-1]
    return {
        'xiu': x['full'],
        'xiu_char': x['name'],
        'xiu_element': x['wuxing'],
        'xiu_ruler': x['ruler'],
        'xiu_degree': 0.0,
        'xiu_width': round(x['width'], 2)
    }


def _julian_day(dt):
    """datetime(UTC) -> Julian Day"""
    return swe.julday(dt.year, dt.month, dt.day, dt.hour + dt.minute / 60.0)


def _swe_longitude(dt, body):
    """使用 pyswisseph 计算某体的黄道经度"""
    if swe is None:
        return None
    utc = dt - timedelta(hours=8)
    jd = _julian_day(utc)
    result = swe.calc_ut(jd, body)
    return result[0][0] % 360


def get_planet_status(planet_name, xiu_element):
    """
    判断星曜在宿度的状态（庙旺/落陷/受克）。
    规则：星曜五行与宿度五行相生为庙，相克为落，同行为旺。
    """
    planet_wuxing = {
        '太阳': '火', '月亮': '水', '水星': '水', '金星': '金',
        '火星': '火', '木星': '木', '土星': '土',
        '罗睺': '火', '计都': '土', '紫炁': '木', '月孛': '水'
    }
    
    pw = planet_wuxing.get(planet_name, '土')
    xw = xiu_element
    if xw == '日':
        xw = '火'
    elif xw == '月':
        xw = '水'
    
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
        
        xiu_info = get_xiu_from_longitude(lon_deg, dt.year)
        status = get_planet_status(cn_name, xiu_info['xiu_element'])
        
        result[cn_name] = {
            'longitude': round(lon_deg, 2),
            **xiu_info,
            'status': status,
            'planet_en': en_name
        }
    
    return result


def calculate_siyu(dt, lat, lon):
    """
    计算四余星位置。
    使用 pyswisseph 精密星历：
      - 罗睺 = 白道升交点 (True Node)
      - 计都 = 降交点（罗睺对宫）
      - 月孛 = 月亮远地点 (Interpolated Apogee)
      - 紫炁 = 月亮近地点 (Interpolated Perigee)
    若 pyswisseph 不可用，回退到简化近似。
    """
    result = {}
    
    if swe is not None:
        rahu = _swe_longitude(dt, swe.TRUE_NODE)
        ketu = (rahu + 180) % 360 if rahu is not None else None
        lilith = _swe_longitude(dt, swe.INTP_APOG)
        perigee = _swe_longitude(dt, swe.INTP_PERG)
        
        siyu_data = {
            '罗睺': {'lon': rahu, 'desc': '白道升交点，前世业力'},
            '计都': {'lon': ketu, 'desc': '白道降交点，今生成长方向'},
            '月孛': {'lon': lilith, 'desc': '月亮远地点，暗月、情欲与潜藏业力'},
            '紫炁': {'lon': perigee, 'desc': '月亮近地点，清高、精神追求'}
        }
        
        for name, data in siyu_data.items():
            lon_deg = data['lon']
            if lon_deg is None:
                continue
            xiu_info = get_xiu_from_longitude(lon_deg, dt.year)
            status = get_planet_status(name, xiu_info['xiu_element'])
            result[name] = {
                'longitude': round(lon_deg, 2),
                **xiu_info,
                'status': status,
                'description': data['desc']
            }
    
    else:
        # 回退：使用 ephem/近似
        qizheng = calculate_qizheng(dt, lat, lon)
        if '月亮' in qizheng:
            moon_lon = qizheng['月亮']['longitude']
            result['罗睺'] = {
                'longitude': round((moon_lon + 180) % 360, 2),
                **get_xiu_from_longitude((moon_lon + 180) % 360, dt.year),
                'status': '示意（未接入精密星历）',
                'description': '南交点，前世业力'
            }
            result['计都'] = {
                'longitude': round(moon_lon, 2),
                **get_xiu_from_longitude(moon_lon, dt.year),
                'status': '示意（未接入精密星历）',
                'description': '北交点，今生成长方向'
            }
        if '木星' in qizheng:
            jupiter_lon = qizheng['木星']['longitude']
            result['紫炁'] = {
                'longitude': round((jupiter_lon + 30) % 360, 2),
                **get_xiu_from_longitude((jupiter_lon + 30) % 360, dt.year),
                'status': '示意（简化计算）',
                'description': '清高、精神追求'
            }
        if '水星' in qizheng:
            mercury_lon = qizheng['水星']['longitude']
            result['月孛'] = {
                'longitude': round((mercury_lon + 30) % 360, 2),
                **get_xiu_from_longitude((mercury_lon + 30) % 360, dt.year),
                'status': '示意（简化计算）',
                'description': '情欲、桃花、暗昧'
            }
    
    return result


def _get_gong_zhi(longitude):
    """根据黄经返回七政四余十二宫地支"""
    sign_idx = int(longitude / 30) % 12
    return _SIGN_TO_DIZHI[sign_idx]


def get_ming_shen_info(dt, lat, lon, qizheng):
    """
    计算命宫、身宫、命度主、身度主。
    - 命宫：上升点所在宫位
    - 命度主：命宫所在宿的度主星
    - 身宫：月亮所在宫位（简化）
    - 身度主：月亮所躔宿的度主星
    """
    asc = lunar_convert.get_ascendant(dt, lat, lon)
    ming_zhi = _get_gong_zhi(asc) if asc is not None else '卯'
    ming_xiu = get_xiu_from_longitude(asc, dt.year) if asc is not None else get_xiu_from_longitude(0, dt.year)
    mingdu_zhu = ming_xiu['xiu_ruler']
    
    moon = qizheng.get('月亮', {})
    moon_lon = moon.get('longitude', 0)
    shen_zhi = _get_gong_zhi(moon_lon)
    shen_xiu = get_xiu_from_longitude(moon_lon, dt.year)
    shenzhu = shen_xiu['xiu_ruler']
    
    return {
        'ming_gong': {
            'zhi': ming_zhi,
            'ascendant': round(asc, 2) if asc is not None else None,
            'xiu': ming_xiu,
            'mingdu_zhu': mingdu_zhu
        },
        'shen_gong': {
            'zhi': shen_zhi,
            'longitude': round(moon_lon, 2),
            'xiu': shen_xiu,
            'shenzhu': shenzhu
        }
    }


def get_dongwei_daxian(year, gender, mingdu_zhi, start_age=1):
    """
    洞微大限。
    以命宫为起点，每宫 10 年。
    阳男阴女顺行，阴男阳女逆行。
    """
    year_gan_idx = (year - 4) % 10
    is_yang = year_gan_idx % 2 == 0
    forward = (is_yang and gender == '男') or (not is_yang and gender == '女')
    
    mingdu_idx = lunar_convert.DIZHI.index(mingdu_zhi)
    daxian = []
    for i in range(12):
        age_start = start_age + i * 10
        if forward:
            zhi_pos = (mingdu_idx + i) % 12
        else:
            zhi_pos = (mingdu_idx - i + 12) % 12
        daxian.append({
            'index': i + 1,
            'zhi': lunar_convert.DIZHI[zhi_pos],
            'age_start': age_start,
            'age_end': age_start + 9
        })
    return daxian


def calculate_houses(asc_longitude, year):
    """计算七政四余十二宫（基于黄道十二宫）"""
    if asc_longitude is None:
        return {}
    
    # 七政四余十二宫名称
    gong_names = [
        '命宫', '财帛', '兄弟', '田宅', '男女', '奴仆',
        '夫妻', '疾厄', '迁移', '官禄', '福德', '相貌'
    ]
    
    houses = {}
    for i, name in enumerate(gong_names):
        cusp = (asc_longitude + i * 30) % 360
        zhi = _get_gong_zhi(cusp)
        xiu = get_xiu_from_longitude(cusp, year)
        houses[name] = {
            'number': i + 1,
            'cusp': round(cusp, 2),
            'zhi': zhi,
            'xiu': xiu
        }
    return houses


def main():
    if len(sys.argv) < 7:
        print("Usage: python qizheng_pan.py <year> <month> <day> <hour> <minute> <gender> [city]")
        sys.exit(1)

    year = int(sys.argv[1])
    month = int(sys.argv[2])
    day = int(sys.argv[3])
    hour = int(sys.argv[4])
    minute = int(sys.argv[5])
    gender = sys.argv[6]
    if gender not in ('男', '女'):
        print("Error: gender must be 男 or 女")
        sys.exit(1)
    city = sys.argv[7] if len(sys.argv) > 7 else None

    # 获取基础数据（真太阳时 + 农历）
    base = lunar_convert.get_bazi_pillars(year, month, day, hour, minute, gender, city)

    dt = datetime(year, month, day, hour, minute)
    lon = base.get('time_conversion', {}).get('longitude', 120.0)
    lat = base.get('time_conversion', {}).get('latitude', 39.9)

    # 七政四余排盘统一使用真太阳时
    ts_str = base.get('time_conversion', {}).get('true_solar_time')
    if ts_str:
        calc_dt = datetime.strptime(ts_str, '%Y-%m-%d %H:%M')
    else:
        calc_dt = dt

    # 计算七政
    qizheng = calculate_qizheng(calc_dt, lat, lon)

    # 计算四余
    siyu = calculate_siyu(calc_dt, lat, lon)

    # 二十八宿（当日值宿）
    today_xiu = '未知'
    if Lunar is not None:
        lunar_dt = Lunar(calc_dt)
        today_xiu = lunar_dt.get_the28Stars()

    # 命宫/身宫/命度主/身度主
    ming_shen = get_ming_shen_info(calc_dt, lat, lon, qizheng)

    # 十二宫
    asc = lunar_convert.get_ascendant(calc_dt, lat, lon)
    houses = calculate_houses(asc, calc_dt.year)

    # 洞微大限
    mingdu_zhi = ming_shen['ming_gong']['zhi']
    daxian = get_dongwei_daxian(year, gender, mingdu_zhi)

    result = {
        'input': {
            'year': year, 'month': month, 'day': day,
            'hour': hour, 'minute': minute,
            'gender': gender, 'city': city
        },
        'time_conversion': base.get('time_conversion', {}),
        'disclaimer': '本排盘综合现代天文星历与常见古籍算法，七政四余流派众多、精度要求极高，不同软件结果可能存在差异。四余星、二十八宿躔度、命度主等仅供文化娱乐参考，强烈建议使用专业七政四余排盘软件复核。',
        'today_xiu': today_xiu,
        'ming_shen': ming_shen,
        'houses': houses,
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
