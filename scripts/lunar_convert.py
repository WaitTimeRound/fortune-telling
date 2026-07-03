#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""lunar_convert.py - 农历转换、八字四柱、真太阳时、西方占星基础计算
基于 cnlunar + ephem + geopy，覆盖1901-2100年。
"""
import json
import logging
import math
import os
import sys
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

try:
    from geopy.geocoders import Nominatim
    from geopy.exc import GeocoderTimedOut
except ImportError:
    Nominatim = None
    GeocoderTimedOut = Exception
    logger.warning("geopy not installed. City geocoding will be limited to built-in coords.")

try:
    from cnlunar import Lunar
except ImportError:
    Lunar = None
    logger.warning("cnlunar not installed. Some features will be limited.")

try:
    import ephem
except ImportError:
    ephem = None
    logger.warning("ephem not installed. Western astrology features will be limited.")

try:
    import swisseph as swe
except ImportError:
    swe = None
    logger.warning("swisseph not installed. Placidus house calculation will fall back to approximation.")

# ========== 基础数据 ==========
TIANGAN = ['甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸']
DIZHI = ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥']
GANZHI_60 = [
    '甲子', '乙丑', '丙寅', '丁卯', '戊辰', '己巳', '庚午', '辛未', '壬申', '癸酉',
    '甲戌', '乙亥', '丙子', '丁丑', '戊寅', '己卯', '庚辰', '辛巳', '壬午', '癸未',
    '甲申', '乙酉', '丙戌', '丁亥', '戊子', '己丑', '庚寅', '辛卯', '壬辰', '癸巳',
    '甲午', '乙未', '丙申', '丁酉', '戊戌', '己亥', '庚子', '辛丑', '壬寅', '癸卯',
    '甲辰', '乙巳', '丙午', '丁未', '戊申', '己酉', '庚戌', '辛亥', '壬子', '癸丑',
    '甲寅', '乙卯', '丙辰', '丁巳', '戊午', '己未', '庚申', '辛酉', '壬戌', '癸亥'
]
NAYIN = [
    '海中金', '炉中火', '大林木', '路旁土', '剑锋金', '山头火',
    '涧下水', '城头土', '白蜡金', '杨柳木', '泉中水', '屋上土',
    '霹雳火', '松柏木', '长流水', '砂中金', '山下火', '平地木',
    '壁上土', '金箔金', '覆灯火', '天河水', '大驿土', '钗钏金',
    '桑柘木', '大溪水', '沙中土', '天上火', '石榴木', '大海水'
]
NAYIN_WUXING = {
    '海中金': '金', '炉中火': '火', '大林木': '木', '路旁土': '土', '剑锋金': '金',
    '山头火': '火', '涧下水': '水', '城头土': '土', '白蜡金': '金', '杨柳木': '木',
    '泉中水': '水', '屋上土': '土', '霹雳火': '火', '松柏木': '木', '长流水': '水',
    '砂中金': '金', '山下火': '火', '平地木': '木', '壁上土': '土', '金箔金': '金',
    '覆灯火': '火', '天河水': '水', '大驿土': '土', '钗钏金': '金', '桑柘木': '木',
    '大溪水': '水', '沙中土': '土', '天上火': '火', '石榴木': '木', '大海水': '水'
}
ELEMENT_TG = ['木', '木', '火', '火', '土', '土', '金', '金', '水', '水']
ELEMENT_DZ = ['水', '土', '木', '木', '土', '火', '火', '土', '金', '金', '土', '水']
DIZHI_CANGGAN = {
    '子': ['癸'], '丑': ['己', '癸', '辛'], '寅': ['甲', '丙', '戊'],
    '卯': ['乙'], '辰': ['戊', '乙', '癸'], '巳': ['丙', '庚', '戊'],
    '午': ['丁', '己'], '未': ['己', '丁', '乙'], '申': ['庚', '壬', '戊'],
    '酉': ['辛'], '戌': ['戊', '辛', '丁'], '亥': ['壬', '甲']
}

WESTERN_SIGNS = ['白羊座', '金牛座', '双子座', '巨蟹座', '狮子座', '处女座',
                 '天秤座', '天蝎座', '射手座', '摩羯座', '水瓶座', '双鱼座']
WESTERN_SIGNS_EN = ['Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo',
                    'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces']
PLANETS = ['Sun', 'Moon', 'Mercury', 'Venus', 'Mars', 'Jupiter', 'Saturn', 'Uranus', 'Neptune', 'Pluto']
PLANETS_CN = {'Sun': '太阳', 'Moon': '月亮', 'Mercury': '水星', 'Venus': '金星',
              'Mars': '火星', 'Jupiter': '木星', 'Saturn': '土星', 'Uranus': '天王星',
              'Neptune': '海王星', 'Pluto': '冥王星'}


# ========== 地理位置查询 ==========
_geolocator = None

CITY_COORDS = {
    '北京': {'lat': 39.9042, 'lon': 116.4074},
    '北京市': {'lat': 39.9042, 'lon': 116.4074},
    '上海': {'lat': 31.2304, 'lon': 121.4737},
    '上海市': {'lat': 31.2304, 'lon': 121.4737},
    '广州': {'lat': 23.1291, 'lon': 113.2644},
    '广州市': {'lat': 23.1291, 'lon': 113.2644},
    '深圳': {'lat': 22.5431, 'lon': 114.0579},
    '深圳市': {'lat': 22.5431, 'lon': 114.0579},
    '杭州': {'lat': 30.2741, 'lon': 120.1551},
    '杭州市': {'lat': 30.2741, 'lon': 120.1551},
    '南京': {'lat': 32.0603, 'lon': 118.7969},
    '南京市': {'lat': 32.0603, 'lon': 118.7969},
    '武汉': {'lat': 30.5928, 'lon': 114.3055},
    '武汉市': {'lat': 30.5928, 'lon': 114.3055},
    '成都': {'lat': 30.5728, 'lon': 104.0668},
    '成都市': {'lat': 30.5728, 'lon': 104.0668},
    '重庆': {'lat': 29.5630, 'lon': 106.5516},
    '重庆市': {'lat': 29.5630, 'lon': 106.5516},
    '西安': {'lat': 34.3416, 'lon': 108.9398},
    '西安市': {'lat': 34.3416, 'lon': 108.9398},
    '天津': {'lat': 39.0842, 'lon': 117.2009},
    '天津市': {'lat': 39.0842, 'lon': 117.2009},
    '香港': {'lat': 22.3193, 'lon': 114.1694},
    '澳门': {'lat': 22.1987, 'lon': 113.5431},
    '台北': {'lat': 25.0330, 'lon': 121.5654},
    '台北市': {'lat': 25.0330, 'lon': 121.5654},
}

def _get_geolocator():
    global _geolocator
    if _geolocator is None and Nominatim is not None:
        _geolocator = Nominatim(user_agent='fortune_telling_app/1.0')
    return _geolocator

def get_location(city_name):
    """通过城市名称获取经纬度。返回 dict 或 None。"""
    # 优先使用本地缓存，避免网络请求
    key = city_name.strip()
    if key in CITY_COORDS:
        coords = CITY_COORDS[key]
        return {
            'name': city_name,
            'lat': coords['lat'],
            'lon': coords['lon'],
            'display_name': city_name
        }
    if Nominatim is None:
        return None
    try:
        geolocator = _get_geolocator()
        location = geolocator.geocode(city_name, language='zh', timeout=10)
        if location:
            return {
                'name': city_name,
                'lat': location.latitude,
                'lon': location.longitude,
                'display_name': location.address
            }
    except Exception as e:
        # 网络或 geopy 异常时不应中断主流程
        logger.warning("geocoding failed for '%s': %s", city_name, e)
    return None


# ========== 真太阳时计算 ==========
def get_true_solar_time(dt, lon):
    """
    计算真太阳时。
    dt: 本地标准时间（北京时间）
    lon: 经度
    返回: datetime（真太阳时）
    """
    # 1. 经度修正：平太阳时
    offset_minutes = (lon - 120.0) * 4.0
    mean_solar = dt + timedelta(minutes=offset_minutes)
    
    if ephem is None:
        # 无 ephem 时仅做经度修正
        return mean_solar
    
    # 2. 精确时差修正（Equation of Time）
    # 真太阳时 = 平太阳时 + 时差(EOT)
    # EOT ≈ 4 * (RA_apparent - RA_mean) 分钟
    try:
        utc = mean_solar - timedelta(hours=8)
        observer = ephem.Observer()
        observer.date = utc.strftime('%Y/%m/%d %H:%M:%S')
        observer.lon = '0'
        observer.lat = '0'
        
        sun = ephem.Sun(observer)
        ra_apparent = math.degrees(float(sun.ra))
        
        # 平太阳黄经：假设太阳沿黄道均匀运动
        jd = ephem.Date(observer.date)
        j2000 = ephem.Date('2000/01/01 12:00:00')
        n = jd - j2000  # 从 J2000.0 起算的天数
        eps = math.radians(23.4367)
        l_mean = math.radians((280.46061837 + 0.985626283 * n) % 360)
        # 平太阳赤经
        ra_mean = math.degrees(math.atan2(
            math.sin(l_mean) * math.cos(eps),
            math.cos(l_mean)
        ))
        
        # 时差（分钟），归一化到 [-720, 720] 避免环绕
        eot_deg = (ra_apparent - ra_mean + 180) % 360 - 180
        eot_minutes = eot_deg * 4.0  # 1° = 4 分钟
        
        return mean_solar + timedelta(minutes=eot_minutes)
    except Exception as e:
        logger.warning("precise equation of time failed: %s, falling back to longitude-only correction.", e)
        return mean_solar


# ========== 上升星座与宫位计算 ==========
def get_ascendant(dt, lat, lon):
    """
    计算上升点黄道经度。
    dt: 本地时间（北京时间）
    lat, lon: 纬度、经度
    返回: 上升点黄经（度，0-360）
    """
    if ephem is None:
        return None
    
    observer = ephem.Observer()
    observer.lat = str(lat)
    observer.lon = str(lon)
    observer.elevation = 0
    
    utc = dt - timedelta(hours=8)
    observer.date = utc.strftime('%Y/%m/%d %H:%M:%S')
    
    lst = observer.sidereal_time()
    lst_rad = float(lst)
    lat_rad = math.radians(lat)
    eps = math.radians(23.4367)
    
    # 标准上升点黄经公式：
    # lambda = atan2(cos(LST), -sin(eps)*tan(lat) - cos(eps)*sin(LST))
    lambda_rad = math.atan2(
        math.cos(lst_rad),
        -math.sin(eps) * math.tan(lat_rad) - math.cos(eps) * math.sin(lst_rad)
    )
    lambda_deg = math.degrees(lambda_rad)
    if lambda_deg < 0:
        lambda_deg += 360
    return lambda_deg


def get_planet_positions(dt, lat, lon):
    """
    计算所有行星的地心黄道经度。
    返回: {planet_name: {'longitude': deg, 'sign': str, 'sign_en': str}}
    """
    if ephem is None:
        return {}
    
    observer = ephem.Observer()
    observer.lat = str(lat)
    observer.lon = str(lon)
    observer.elevation = 0
    
    utc = dt - timedelta(hours=8)
    observer.date = utc.strftime('%Y/%m/%d %H:%M:%S')
    
    result = {}
    for planet_name in PLANETS:
        planet_class = getattr(ephem, planet_name)
        planet = planet_class(observer)
        
        # 转换为地心黄道坐标
        ecl = ephem.Ecliptic(planet, epoch=observer.date)
        lon_deg = math.degrees(float(ecl.lon)) % 360
        sign_idx = int(lon_deg / 30) % 12
        
        result[PLANETS_CN[planet_name]] = {
            'longitude': round(lon_deg, 2),
            'sign': WESTERN_SIGNS[sign_idx],
            'sign_en': WESTERN_SIGNS_EN[sign_idx],
            'planet_en': planet_name
        }
    
    # 上升点
    asc = get_ascendant(dt, lat, lon)
    if asc is not None:
        sign_idx = int(asc / 30) % 12
        result['上升点'] = {
            'longitude': round(asc, 2),
            'sign': WESTERN_SIGNS[sign_idx],
            'sign_en': WESTERN_SIGNS_EN[sign_idx],
            'planet_en': 'Ascendant'
        }
    
    return result


def _get_mc_longitude(dt, lat, lon):
    """计算中天（MC）黄经"""
    if ephem is None:
        return None
    observer = ephem.Observer()
    observer.lat = str(lat)
    observer.lon = str(lon)
    observer.elevation = 0
    utc = dt - timedelta(hours=8)
    observer.date = utc.strftime('%Y/%m/%d %H:%M:%S')
    lst = observer.sidereal_time()
    lst_deg = math.degrees(float(lst))
    eps = math.radians(23.4367)
    # MC：本地子午圈与黄道的上交点
    mc = math.degrees(math.atan2(
        math.sin(math.radians(lst_deg)) / math.cos(eps),
        math.cos(math.radians(lst_deg))
    ))
    return mc % 360


def get_houses(dt, lat, lon, house_system='placidus'):
    """
    计算宫位。支持等宫制（Equal House）和 Placidus。
    若已安装 swisseph，Placidus 使用真正的 Placidus 算法；否则回退到近似插值。
    返回: {house_number: {'cusp': deg, 'sign': str}}
    """
    if ephem is None:
        return {}

    asc = get_ascendant(dt, lat, lon)
    if asc is None:
        return {}

    houses = {}
    if house_system == 'equal':
        # 等宫制：每个宫位 30°，从上升点开始
        for i in range(1, 13):
            cusp = (asc + (i - 1) * 30) % 360
            sign_idx = int(cusp / 30) % 12
            houses[i] = {'cusp': round(cusp, 2), 'sign': WESTERN_SIGNS[sign_idx]}
    elif house_system == 'placidus':
        # 优先使用 swisseph 实现真正的 Placidus 分宫
        if swe is not None:
            try:
                # 使用 UTC 时间计算 Julian Day
                utc = dt - timedelta(hours=8)
                jd = swe.julday(utc.year, utc.month, utc.day,
                                utc.hour + utc.minute / 60.0)
                cusps, ascmc = swe.houses_ex(jd, lat, lon, b'P')
                for i in range(1, 13):
                    cusp = cusps[i - 1] % 360
                    sign_idx = int(cusp / 30) % 12
                    houses[i] = {'cusp': round(cusp, 2), 'sign': WESTERN_SIGNS[sign_idx]}
                return houses
            except Exception as e:
                logger.warning("swisseph Placidus calculation failed: %s, falling back to approximation.", e)

        # 回退：基于 ASC 与 MC 的球面插值近似
        logger.warning("Falling back to approximate Placidus interpolation.")
        mc = _get_mc_longitude(dt, lat, lon)
        if mc is None:
            mc = (asc + 90) % 360
        dsc = (asc + 180) % 360
        ic = (mc + 180) % 360

        def _interpolate_cusp(start, end, ratio):
            """沿黄道从 start 到 end 按比例插值，处理 360° 环绕"""
            if start <= end:
                return start + (end - start) * ratio
            return (start + (end + 360 - start) * ratio) % 360

        def _add_house(num, lon):
            sign_idx = int(lon / 30) % 12
            houses[num] = {
                'cusp': round(lon, 2),
                'sign': WESTERN_SIGNS[sign_idx],
                'approximate': True
            }

        _add_house(1, asc)
        _add_house(10, mc)
        _add_house(7, dsc)
        _add_house(4, ic)
        _add_house(12, _interpolate_cusp(asc, mc, 1/3))
        _add_house(11, _interpolate_cusp(asc, mc, 2/3))
        _add_house(9, _interpolate_cusp(mc, dsc, 1/3))
        _add_house(8, _interpolate_cusp(mc, dsc, 2/3))
        _add_house(6, _interpolate_cusp(dsc, ic, 1/3))
        _add_house(5, _interpolate_cusp(dsc, ic, 2/3))
        _add_house(3, _interpolate_cusp(ic, asc, 1/3))
        _add_house(2, _interpolate_cusp(ic, asc, 2/3))
    else:
        # 未知分宫制：回退到等宫制
        for i in range(1, 13):
            cusp = (asc + (i - 1) * 30) % 360
            sign_idx = int(cusp / 30) % 12
            houses[i] = {'cusp': round(cusp, 2), 'sign': WESTERN_SIGNS[sign_idx]}

    return houses


def get_aspects(planet_positions, orb=8):
    """
    计算行星相位。
    planet_positions: get_planet_positions 的返回值
    orb: 容许度（度）
    返回: [(planet1, planet2, aspect_type, angle, orb)]
    """
    aspects = []
    planet_names = list(planet_positions.keys())
    
    ASPECTS = {
        '合相': 0,
        '六分相': 60,
        '刑相': 90,
        '拱相': 120,
        '冲相': 180,
        '梅花相': 150
    }
    
    for i in range(len(planet_names)):
        for j in range(i + 1, len(planet_names)):
            p1 = planet_names[i]
            p2 = planet_names[j]
            if p1 == '上升点' or p2 == '上升点':
                continue
            
            lon1 = planet_positions[p1]['longitude']
            lon2 = planet_positions[p2]['longitude']
            diff = abs(lon1 - lon2)
            if diff > 180:
                diff = 360 - diff
            
            for aspect_name, target_angle in ASPECTS.items():
                aspect_diff = abs(diff - target_angle)
                if aspect_diff <= orb:
                    aspects.append({
                        'planet1': p1,
                        'planet2': p2,
                        'aspect': aspect_name,
                        'angle': round(diff, 2),
                        'target': target_angle,
                        'orb': round(aspect_diff, 2)
                    })
    
    return aspects


# ========== 八字相关函数 ==========
def get_nayin(ganzhi):
    """根据干支获取纳音五行"""
    idx = GANZHI_60.index(ganzhi)
    return NAYIN[idx // 2]

def get_liunian_ganzhi(year):
    """获取某年的流年干支"""
    return GANZHI_60[(year - 4) % 60]

# 五行索引映射（用于生克计算）
WUXING_IDX = {'木': 0, '火': 1, '土': 2, '金': 3, '水': 4}

def get_shishen(day_gan, target_gan):
    """计算十神关系
    
    五行生克关系（索引差）：
    - 我生者: (target - day) % 5 == 1
    - 生我者: (target - day) % 5 == 4
    - 我克者: (target - day) % 5 == 2
    - 克我者: (target - day) % 5 == 3
    """
    day_idx = TIANGAN.index(day_gan)
    target_idx = TIANGAN.index(target_gan)
    day_element = ELEMENT_TG[day_idx]
    target_element = ELEMENT_TG[target_idx]
    
    same = (day_idx % 2) == (target_idx % 2)
    
    diff = (WUXING_IDX[target_element] - WUXING_IDX[day_element]) % 5
    
    if diff == 0:  # 同五行（比肩/劫财）
        return '比肩' if same else '劫财'
    elif diff == 4:  # 生我者
        return '偏印' if same else '正印'
    elif diff == 1:  # 我生者
        return '食神' if same else '伤官'
    elif diff == 3:  # 克我者
        return '七杀' if same else '正官'
    elif diff == 2:  # 我克者
        return '偏财' if same else '正财'
    
    return '未知'

def calculate_wuxing_count(pillars):
    """统计五行数量"""
    count = {'金': 0, '木': 0, '水': 0, '火': 0, '土': 0}
    for pillar in [pillars['year'], pillars['month'], pillars['day'], pillars['hour']]:
        gan = pillar[0]
        zhi = pillar[1]
        count[ELEMENT_TG[TIANGAN.index(gan)]] += 1
        count[ELEMENT_DZ[DIZHI.index(zhi)]] += 1
        for cg in DIZHI_CANGGAN[zhi]:
            count[ELEMENT_TG[TIANGAN.index(cg)]] += 0.5
    return count

def calculate_shensha(year_gan, year_zhi, month_gan, month_zhi, day_gan, day_zhi, hour_gan, hour_zhi, gender):
    """计算神煞（简化版）"""
    shensha = {}
    
    # 天乙贵人
    tianyi_map = {
        '甲': '丑', '戊': '丑', '庚': '丑',
        '乙': '子', '己': '子',
        '丙': '亥', '丁': '亥',
        '壬': '卯', '癸': '卯',
        '辛': '午'
    }
    tianyi = tianyi_map.get(day_gan, '')
    if tianyi in [year_zhi, month_zhi, day_zhi, hour_zhi]:
        shensha['天乙贵人'] = '有'
    
    # 文昌贵人
    wenchang_map = {
        '甲': '巳', '乙': '午', '丙': '申', '丁': '酉',
        '戊': '申', '己': '酉', '庚': '亥', '辛': '子', '壬': '寅', '癸': '卯'
    }
    wenchang = wenchang_map.get(day_gan, '')
    if wenchang in [year_zhi, month_zhi, day_zhi, hour_zhi]:
        shensha['文昌贵人'] = '有'
    
    # 驿马
    yima_map = {'申': '寅', '子': '寅', '辰': '寅',
                '寅': '申', '午': '申', '戌': '申',
                '亥': '巳', '卯': '巳', '未': '巳',
                '巳': '亥', '酉': '亥', '丑': '亥'}
    yima = yima_map.get(year_zhi, '')
    if yima in [year_zhi, month_zhi, day_zhi, hour_zhi]:
        shensha['驿马'] = '有'
    
    # 桃花
    taohua_map = {'申': '酉', '子': '酉', '辰': '酉',
                  '寅': '卯', '午': '卯', '戌': '卯',
                  '亥': '子', '卯': '子', '未': '子',
                  '巳': '午', '酉': '午', '丑': '午'}
    taohua = taohua_map.get(year_zhi, '')
    if taohua in [year_zhi, month_zhi, day_zhi, hour_zhi]:
        shensha['桃花'] = '有'
    
    # 华盖
    huagai_map = {'申': '辰', '子': '辰', '辰': '辰',
                  '寅': '戌', '午': '戌', '戌': '戌',
                  '亥': '未', '卯': '未', '未': '未',
                  '巳': '丑', '酉': '丑', '丑': '丑'}
    huagai = huagai_map.get(year_zhi, '')
    if huagai in [year_zhi, month_zhi, day_zhi, hour_zhi]:
        shensha['华盖'] = '有'
    
    # 将星
    jiangxing_map = {'申': '子', '子': '子', '辰': '子',
                     '寅': '午', '午': '午', '戌': '午',
                     '亥': '卯', '卯': '卯', '未': '卯',
                     '巳': '酉', '酉': '酉', '丑': '酉'}
    jiangxing = jiangxing_map.get(year_zhi, '')
    if jiangxing in [year_zhi, month_zhi, day_zhi, hour_zhi]:
        shensha['将星'] = '有'
    
    # 天德贵人、月德贵人（简化）
    
    return shensha

def calculate_dayun(year_gan, gender, month_pillar, birth_dt, solar_terms=None):
    """计算大运"""
    # 阳年男/阴年女：顺排；阴年男/阳年女：逆排
    year_gan_idx = TIANGAN.index(year_gan[0])
    is_yang = year_gan_idx % 2 == 0
    
    forward = (is_yang and gender == '男') or (not is_yang and gender == '女')
    
    # 从月柱开始排大运
    month_gan_idx = TIANGAN.index(month_pillar[0])
    month_zhi_idx = DIZHI.index(month_pillar[1])
    
    dayun = []
    for i in range(12):
        if forward:
            g_idx = (month_gan_idx + i + 1) % 10
            z_idx = (month_zhi_idx + i + 1) % 12
        else:
            g_idx = (month_gan_idx - i - 1 + 10) % 10
            z_idx = (month_zhi_idx - i - 1 + 12) % 12
        dayun.append(f"{TIANGAN[g_idx]}{DIZHI[z_idx]}")
    
    # 起运年龄计算（简化）
    if solar_terms is None:
        start_age = 3
    else:
        # 计算距离下一个/上一个节气的天数
        try:
            if forward:
                next_term = None
                for term in solar_terms:
                    if term > birth_dt:
                        next_term = term
                        break
                if next_term:
                    days_diff = (next_term - birth_dt).days
                else:
                    days_diff = 30
            else:
                prev_term = None
                for term in reversed(solar_terms):
                    if term < birth_dt:
                        prev_term = term
                        break
                if prev_term:
                    days_diff = (birth_dt - prev_term).days
                else:
                    days_diff = 30
            start_age = max(1, days_diff / 3)
        except (TypeError, ValueError, AttributeError) as e:
            logger.warning("dayun start_age calculation failed: %s, using default 3.", e)
            start_age = 3
    
    dayun_result = []
    for i, dy in enumerate(dayun):
        age_start = start_age + i * 10
        age_end = age_start + 9
        dayun_result.append({
            'index': i + 1,
            'ganzhi': dy,
            'age_start': round(age_start, 1),
            'age_end': round(age_end, 1)
        })
    
    return dayun_result


# ========== 主函数：八字排盘 ==========
def get_bazi_pillars(year, month, day, hour, minute, gender, city=None):
    """
    计算完整八字信息。
    year, month, day, hour, minute: 公历时间（北京时间）
    gender: '男' 或 '女'
    city: 城市名称（可选，用于真太阳时计算）
    返回: dict
    """
    dt = datetime(year, month, day, hour, minute)
    
    # 真太阳时计算
    true_solar_dt = dt
    lon = 120.0
    lat = 39.9
    location_info = None
    
    if city:
        location_info = get_location(city)
        if location_info:
            lon = location_info['lon']
            lat = location_info['lat']
            true_solar_dt = get_true_solar_time(dt, lon)
    
    # 使用真太阳时的年月日时
    ts = true_solar_dt
    ts_hour = ts.hour
    ts_minute = ts.minute
    
    # 23:00后算第二天（用于日柱）
    if ts_hour >= 23:
        day_dt = ts + timedelta(days=1)
    else:
        day_dt = ts
    
    # 使用 cnlunar 获取八字
    if Lunar is not None:
        # 时柱以真太阳时计算
        lunar_dt = datetime(ts.year, ts.month, ts.day, ts.hour, ts.minute)
        lunar = Lunar(lunar_dt)
        
        year_pillar = lunar.get_year8Char()
        month_pillar = lunar.get_month8Char()
        day_pillar = lunar.get_day8Char()
        hour_pillar = lunar.get_twohour8Char()
        
        nayin = lunar.get_nayin()
        the28 = lunar.get_the28Stars()
        solar_term = lunar.get_todaySolarTerms()
        lunar_cn = lunar.get_lunarCn()
        zodiac = lunar.get_chineseYearZodiac()
        
        # 神煞（使用 cnlunar 的完整数据）
        angel_demon = lunar.get_AngelDemon()
        
        # 获取全年节气列表
        solar_terms_list = lunar.getSolarTermsDateList(ts.year)
        # 转换为 datetime 列表
        solar_terms_dt = []
        for term in solar_terms_list:
            if isinstance(term, (list, tuple)) and len(term) >= 3:
                solar_terms_dt.append(datetime(term[0], term[1], term[2]))
        
        # 获取月相
        phase = lunar.getPhaseOfMoon()
    else:
        # 回退到手工计算（保留原有逻辑）
        year_pillar = _calc_year_pillar(ts.year)
        month_pillar = _calc_month_pillar(ts.year, ts.month, ts.day, ts.hour, ts.minute)
        day_pillar = _calc_day_pillar(ts.year, ts.month, ts.day, ts.hour, ts.minute)
        hour_pillar = _calc_hour_pillar(ts.year, ts.month, ts.day, ts.hour, ts.minute)
        nayin = get_nayin(year_pillar)
        the28 = '未知'
        solar_term = '未知'
        lunar_cn = '未知'
        zodiac = '未知'
        angel_demon = {}
        solar_terms_dt = []
        phase = '未知'
    
    pillars = {
        'year': year_pillar,
        'month': month_pillar,
        'day': day_pillar,
        'hour': hour_pillar
    }
    
    # 藏干
    canggan = {}
    for name, pillar in [('year', year_pillar), ('month', month_pillar), ('day', day_pillar), ('hour', hour_pillar)]:
        zhi = pillar[1]
        canggan[name] = DIZHI_CANGGAN[zhi]
    
    # 十神
    day_gan = day_pillar[0]
    shishen = {}
    for name in ['year', 'month', 'day', 'hour']:
        gan = pillars[name][0]
        shishen[name] = get_shishen(day_gan, gan)
    
    canggan_shishen = {}
    for name in ['year', 'month', 'day', 'hour']:
        zhi = pillars[name][1]
        canggan_list = DIZHI_CANGGAN[zhi]
        canggan_shishen[name] = [(cg, get_shishen(day_gan, cg)) for cg in canggan_list]
    
    # 五行统计
    wuxing_count = calculate_wuxing_count(pillars)
    
    # 神煞
    year_gan = year_pillar[0]
    year_zhi = year_pillar[1]
    month_gan = month_pillar[0]
    month_zhi = month_pillar[1]
    day_gan = day_pillar[0]
    day_zhi = day_pillar[1]
    hour_gan = hour_pillar[0]
    hour_zhi = hour_pillar[1]
    
    shensha = calculate_shensha(year_gan, year_zhi, month_gan, month_zhi,
                                 day_gan, day_zhi, hour_gan, hour_zhi, gender)
    
    # 大运
    dayun_result = calculate_dayun(year_pillar, gender, month_pillar, dt, solar_terms_dt)
    
    # 西方占星基础数据
    western = {}
    if ephem is not None:
        western['planets'] = get_planet_positions(dt, lat, lon)
        western['houses'] = get_houses(dt, lat, lon)
        western['aspects'] = get_aspects(western['planets'])
        western['ascendant'] = western['planets'].get('上升点', {})
    
    result = {
        'input': {
            'year': year, 'month': month, 'day': day,
            'hour': hour, 'minute': minute,
            'gender': gender, 'city': city
        },
        'time_conversion': {
            'beijing_time': dt.strftime('%Y-%m-%d %H:%M'),
            'true_solar_time': true_solar_dt.strftime('%Y-%m-%d %H:%M') if city else None,
            'longitude': lon if city else 120.0,
            'latitude': lat if city else 39.9,
            'location': location_info
        },
        'pillars': pillars,
        'nayin': {
            'year': get_nayin(year_pillar),
            'month': get_nayin(month_pillar),
            'day': get_nayin(day_pillar),
            'hour': get_nayin(hour_pillar)
        },
        'canggan': canggan,
        'shishen': shishen,
        'canggan_shishen': canggan_shishen,
        'wuxing_count': wuxing_count,
        'shensha': shensha,
        'dayun': dayun_result,
        'lunar': {
            'lunar_date': lunar_cn if Lunar else 'unknown',
            'zodiac': zodiac if Lunar else 'unknown',
            'solar_term': solar_term if Lunar else 'unknown',
            'the28': the28 if Lunar else 'unknown',
            'phase': phase if Lunar else 'unknown'
        },
        'western': western
    }
    
    return result


# ========== 回退函数（cnlunar 不可用时） ==========
def _calc_year_pillar(year):
    """手工计算年柱"""
    gan_idx = (year - 4) % 10
    zhi_idx = (year - 4) % 12
    return f"{TIANGAN[gan_idx]}{DIZHI[zhi_idx]}"

def _calc_month_pillar(year, month, day, hour, minute):
    """手工计算月柱（简化）"""
    year_gan_idx = (year - 4) % 10
    month_gan_start = (year_gan_idx * 2 + 1) % 10
    # 简化：按农历月计算
    month_zhi_idx = (month + 1) % 12
    month_gan_idx = (month_gan_start + month_zhi_idx - 2) % 10
    return f"{TIANGAN[month_gan_idx]}{DIZHI[month_zhi_idx]}"

def _calc_day_pillar(year, month, day, hour, minute):
    """手工计算日柱"""
    base_dt = datetime(2019, 1, 29)
    dt = datetime(year, month, day, hour, minute)
    if hour >= 23:
        days_diff = (dt - base_dt).days + 1
    else:
        days_diff = (dt - base_dt).days
    base_index = GANZHI_60.index('丙寅')
    day_index = (days_diff + base_index) % 60
    return GANZHI_60[day_index]

def _calc_hour_pillar(year, month, day, hour, minute):
    """手工计算时柱"""
    day_gan = _calc_day_pillar(year, month, day, hour, minute)[0]
    day_gan_idx = TIANGAN.index(day_gan)
    if hour % 2 == 1:
        zhi_idx = (hour + 1) // 2 % 12
    else:
        zhi_idx = hour // 2 % 12
    # 时干起法：甲己还加甲，乙庚丙作初，丙辛从戊起，
    # 丁壬庚子居，戊癸何方发，壬子是真途。
    hour_gan_start = (day_gan_idx % 5) * 2
    hour_gan_idx = (hour_gan_start + zhi_idx) % 10
    return f"{TIANGAN[hour_gan_idx]}{DIZHI[zhi_idx]}"


if __name__ == '__main__':
    # 测试
    result = get_bazi_pillars(1990, 1, 1, 12, 0, '男', '北京')
    output_file = os.environ.get('FORTUNE_OUTPUT_FILE', 'lunar_convert_result.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"Result written to {output_file}")
