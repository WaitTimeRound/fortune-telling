#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ziwei_pan.py - 紫微斗数排盘（简化版）

基于 cnlunar 农历数据，实现紫微斗数核心排盘算法。
支持：命宫、身宫、主星、辅星、四化、大限。

Usage:
    python ziwei_pan.py <year> <month> <day> <hour> <minute> <gender> [city]

Example:
    python ziwei_pan.py 1990 5 15 14 30 男 北京
"""
import json
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(__file__))
import lunar_convert

try:
    from cnlunar import Lunar
except ImportError:
    Lunar = None


# ========== 紫微斗数基础数据 ==========
ZHIWEI_GONGS = ['命宫', '兄弟', '夫妻', '子女', '财帛', '疾厄',
                '迁移', '仆役', '官禄', '田宅', '福德', '父母']
ZHIWEI_GONG_ORDER = ['命宫', '兄弟', '夫妻', '子女', '财帛', '疾厄',
                     '迁移', '仆役', '官禄', '田宅', '福德', '父母']

# 五行局：根据命宫干支确定
WUXING_JU = {
    ('甲', '子'): '水二局', ('甲', '寅'): '水二局', ('甲', '辰'): '火六局',
    ('甲', '午'): '火六局', ('甲', '申'): '土五局', ('甲', '戌'): '土五局',
    ('乙', '丑'): '火六局', ('乙', '卯'): '火六局', ('乙', '巳'): '水二局',
    ('乙', '未'): '水二局', ('乙', '酉'): '土五局', ('乙', '亥'): '土五局',
    ('丙', '子'): '火六局', ('丙', '寅'): '火六局', ('丙', '辰'): '木三局',
    ('丙', '午'): '木三局', ('丙', '申'): '金四局', ('丙', '戌'): '金四局',
    ('丁', '丑'): '木三局', ('丁', '卯'): '木三局', ('丁', '巳'): '金四局',
    ('丁', '未'): '金四局', ('丁', '酉'): '火六局', ('丁', '亥'): '火六局',
    ('戊', '子'): '火六局', ('戊', '寅'): '火六局', ('戊', '辰'): '木三局',
    ('戊', '午'): '木三局', ('戊', '申'): '土五局', ('戊', '戌'): '土五局',
    ('己', '丑'): '木三局', ('己', '卯'): '木三局', ('己', '巳'): '金四局',
    ('己', '未'): '金四局', ('己', '酉'): '火六局', ('己', '亥'): '火六局',
    ('庚', '子'): '土五局', ('庚', '寅'): '土五局', ('庚', '辰'): '金四局',
    ('庚', '午'): '金四局', ('庚', '申'): '木三局', ('庚', '戌'): '木三局',
    ('辛', '丑'): '金四局', ('辛', '卯'): '金四局', ('辛', '巳'): '土五局',
    ('辛', '未'): '土五局', ('辛', '酉'): '水二局', ('辛', '亥'): '水二局',
    ('壬', '子'): '木三局', ('壬', '寅'): '木三局', ('壬', '辰'): '金四局',
    ('壬', '午'): '金四局', ('壬', '申'): '水二局', ('壬', '戌'): '水二局',
    ('癸', '丑'): '金四局', ('癸', '卯'): '金四局', ('癸', '巳'): '土五局',
    ('癸', '未'): '土五局', ('癸', '酉'): '火六局', ('癸', '亥'): '火六局',
}

# 安紫微星表：五行局数 -> 生日 -> 紫微星位置（地支索引）
ZIWEI_TABLE = {
    '水二局': {1: 0, 2: 1, 3: 2, 4: 3, 5: 4, 6: 5, 7: 6, 8: 7, 9: 8, 10: 9, 11: 10, 12: 11,
              13: 0, 14: 1, 15: 2, 16: 3, 17: 4, 18: 5, 19: 6, 20: 7, 21: 8, 22: 9, 23: 10, 24: 11,
              25: 0, 26: 1, 27: 2, 28: 3, 29: 4, 30: 5},
    '木三局': {1: 11, 2: 0, 3: 1, 4: 2, 5: 3, 6: 4, 7: 5, 8: 6, 9: 7, 10: 8, 11: 9, 12: 10,
              13: 11, 14: 0, 15: 1, 16: 2, 17: 3, 18: 4, 19: 5, 20: 6, 21: 7, 22: 8, 23: 9, 24: 10,
              25: 11, 26: 0, 27: 1, 28: 2, 29: 3, 30: 4},
    '金四局': {1: 11, 2: 0, 3: 1, 4: 2, 5: 3, 6: 4, 7: 5, 8: 6, 9: 7, 10: 8, 11: 9, 12: 10,
              13: 11, 14: 0, 15: 1, 16: 2, 17: 3, 18: 4, 19: 5, 20: 6, 21: 7, 22: 8, 23: 9, 24: 10,
              25: 11, 26: 0, 27: 1, 28: 2, 29: 3, 30: 4},
    '土五局': {1: 10, 2: 11, 3: 0, 4: 1, 5: 2, 6: 3, 7: 4, 8: 5, 9: 6, 10: 7, 11: 8, 12: 9,
              13: 10, 14: 11, 15: 0, 16: 1, 17: 2, 18: 3, 19: 4, 20: 5, 21: 6, 22: 7, 23: 8, 24: 9,
              25: 10, 26: 11, 27: 0, 28: 1, 29: 2, 30: 3},
    '火六局': {1: 10, 2: 11, 3: 0, 4: 1, 5: 2, 6: 3, 7: 4, 8: 5, 9: 6, 10: 7, 11: 8, 12: 9,
              13: 10, 14: 11, 15: 0, 16: 1, 17: 2, 18: 3, 19: 4, 20: 5, 21: 6, 22: 7, 23: 8, 24: 9,
              25: 10, 26: 11, 27: 0, 28: 1, 29: 2, 30: 3}
}

# 主星排列：紫微、天机、太阳、武曲、天同、廉贞、天府、太阴、贪狼、巨门、天相、天梁、七杀、破军
# 安星规则：紫微定后，天机在紫微前一宫，太阳在紫微前两宫，武曲在紫微前三宫，天同在紫微前四宫，廉贞在紫微前五宫
# 天府与紫微相对（或按公式），太阴在天府前一宫，贪狼在天府前两宫，巨门在天府前三宫，天相在天府前四宫，天梁在天府前五宫，七杀在天府前六宫，破军在天府前七宫

# 四化表：根据年干
SIHUA_TABLE = {
    '甲': {'禄': '廉贞', '权': '破军', '科': '武曲', '忌': '太阳'},
    '乙': {'禄': '天机', '权': '天梁', '科': '紫微', '忌': '太阴'},
    '丙': {'禄': '天同', '权': '天机', '科': '文昌', '忌': '廉贞'},
    '丁': {'禄': '太阴', '权': '天同', '科': '天机', '忌': '巨门'},
    '戊': {'禄': '贪狼', '权': '太阴', '科': '右弼', '忌': '天机'},
    '己': {'禄': '武曲', '权': '贪狼', '科': '天梁', '忌': '文曲'},
    '庚': {'禄': '太阳', '权': '武曲', '科': '太阴', '忌': '天同'},
    '辛': {'禄': '巨门', '权': '太阳', '科': '文曲', '忌': '文昌'},
    '壬': {'禄': '天梁', '权': '紫微', '科': '左辅', '忌': '武曲'},
    '癸': {'禄': '破军', '权': '巨门', '科': '太阴', '忌': '贪狼'}
}

# 十四主星庙旺利陷表（简化）
ZHUXING_MIAOWANG = {
    '紫微': {'亥': '庙', '子': '旺', '丑': '庙', '寅': '旺', '卯': '利', '辰': '庙', '巳': '旺',
            '午': '庙', '未': '利', '申': '旺', '酉': '庙', '戌': '利'},
    '天机': {'子': '庙', '丑': '陷', '寅': '旺', '卯': '利', '辰': '庙', '巳': '旺', '午': '陷',
            '未': '庙', '申': '旺', '酉': '陷', '戌': '庙', '亥': '旺'},
    '太阳': {'子': '陷', '丑': '不', '寅': '旺', '卯': '庙', '辰': '庙', '巳': '旺', '午': '庙',
            '未': '利', '申': '不', '酉': '陷', '戌': '庙', '亥': '旺'},
    '武曲': {'子': '庙', '丑': '旺', '寅': '庙', '卯': '利', '辰': '庙', '巳': '旺', '午': '庙',
            '未': '陷', '申': '旺', '酉': '庙', '戌': '旺', '亥': '陷'},
    '天同': {'子': '旺', '丑': '陷', '寅': '庙', '卯': '旺', '辰': '陷', '巳': '庙', '午': '陷',
            '未': '庙', '申': '旺', '酉': '陷', '戌': '庙', '亥': '旺'},
    '廉贞': {'子': '陷', '丑': '庙', '寅': '旺', '卯': '庙', '辰': '陷', '巳': '庙', '午': '旺',
            '未': '陷', '申': '庙', '酉': '陷', '戌': '庙', '亥': '陷'},
    '天府': {'子': '庙', '丑': '庙', '寅': '庙', '卯': '庙', '辰': '庙', '巳': '庙', '午': '庙',
            '未': '庙', '申': '庙', '酉': '庙', '戌': '庙', '亥': '庙'},
    '太阴': {'子': '庙', '丑': '庙', '寅': '陷', '卯': '陷', '辰': '陷', '巳': '陷', '午': '陷',
            '未': '不', '申': '旺', '酉': '庙', '戌': '庙', '亥': '庙'},
    '贪狼': {'子': '旺', '丑': '庙', '寅': '旺', '卯': '庙', '辰': '陷', '巳': '庙', '午': '陷',
            '未': '陷', '申': '旺', '酉': '庙', '戌': '庙', '亥': '陷'},
    '巨门': {'子': '旺', '丑': '庙', '寅': '陷', '卯': '庙', '辰': '庙', '巳': '旺', '午': '庙',
            '未': '陷', '申': '旺', '酉': '庙', '戌': '旺', '亥': '陷'},
    '天相': {'子': '庙', '丑': '庙', '寅': '庙', '卯': '庙', '辰': '庙', '巳': '庙', '午': '庙',
            '未': '庙', '申': '庙', '酉': '庙', '戌': '庙', '亥': '庙'},
    '天梁': {'子': '庙', '丑': '庙', '寅': '庙', '卯': '庙', '辰': '庙', '巳': '庙', '午': '庙',
            '未': '庙', '申': '庙', '酉': '庙', '戌': '庙', '亥': '庙'},
    '七杀': {'子': '陷', '丑': '庙', '寅': '庙', '卯': '庙', '辰': '庙', '巳': '庙', '午': '庙',
            '未': '庙', '申': '庙', '酉': '庙', '戌': '庙', '亥': '陷'},
    '破军': {'子': '庙', '丑': '陷', '寅': '旺', '卯': '庙', '辰': '陷', '巳': '庙', '午': '旺',
            '未': '陷', '申': '旺', '酉': '庙', '戌': '陷', '亥': '庙'}
}

# 辅星（简化）
FUXING = ['左辅', '右弼', '文昌', '文曲', '天魁', '天钺', '禄存', '天马', '擎羊', '陀罗', '火星', '铃星', '地空', '地劫']


def get_ming_shen_gong(lunar_month, lunar_day, hour_zhi_idx):
    """
    安命宫和身宫。
    lunar_month: 农历月份（1-12）
    hour_zhi_idx: 时辰地支索引（子=0, ..., 亥=11）
    
    返回: (ming_gong_zhi_idx, shen_gong_zhi_idx)
    """
    # 命宫：从寅宫（索引2）起正月，顺数到生月，再从该宫起子时，逆数到生时
    # 寅 = 2, 卯 = 3, ..., 亥 = 11, 子 = 0, 丑 = 1
    start = 2  # 寅宫
    month_pos = (start + lunar_month - 1) % 12
    ming_gong = (month_pos - hour_zhi_idx) % 12
    
    # 身宫：从寅宫起正月，顺数到生月，再从该宫起子时，顺数到生时
    shen_gong = (month_pos + hour_zhi_idx) % 12
    
    return ming_gong, shen_gong


def get_wuxing_ju(ming_gong_ganzhi):
    """根据命宫干支定五行局"""
    gan = ming_gong_ganzhi[0]
    zhi = ming_gong_ganzhi[1]
    return WUXING_JU.get((gan, zhi), '土五局')


def get_wuxing_ju_number(ju_name):
    """提取五行局数（汉字数字转阿拉伯数字）"""
    num_map = {'二': 2, '三': 3, '四': 4, '五': 5, '六': 6}
    return num_map.get(ju_name[1], 5)


def set_zhu_stars(ming_gong_zhi, lunar_day, wuxing_ju):
    """安十四主星"""
    ju_name = wuxing_ju
    ju_num = get_wuxing_ju_number(ju_name)
    day = lunar_day
    
    # 安紫微星
    ziwei_pos = ZIWEI_TABLE.get(ju_name, {}).get(day, 0)
    
    # 安天机（紫微前一宫）
    tianji_pos = (ziwei_pos + 1) % 12
    
    # 安太阳（紫微前两宫）
    taiyang_pos = (ziwei_pos + 2) % 12
    
    # 安武曲（紫微前三宫）
    wuqu_pos = (ziwei_pos + 3) % 12
    
    # 安天同（紫微前四宫）
    tiantong_pos = (ziwei_pos + 4) % 12
    
    # 安廉贞（紫微前五宫）
    lianzhen_pos = (ziwei_pos + 5) % 12
    
    # 安天府（紫微对宫，即+6）
    tianfu_pos = (ziwei_pos + 6) % 12
    
    # 安太阴（天府前一宫）
    taiyin_pos = (tianfu_pos + 1) % 12
    
    # 安贪狼（天府前两宫）
    tanlang_pos = (tianfu_pos + 2) % 12
    
    # 安巨门（天府前三宫）
    jumen_pos = (tianfu_pos + 3) % 12
    
    # 安天相（天府前四宫）
    tianxiang_pos = (tianfu_pos + 4) % 12
    
    # 安天梁（天府前五宫）
    tianliang_pos = (tianfu_pos + 5) % 12
    
    # 安七杀（天府前六宫）
    qisha_pos = (tianfu_pos + 6) % 12
    
    # 安破军（天府前七宫）
    pojun_pos = (tianfu_pos + 7) % 12
    
    stars = {}
    for zhi_idx in range(12):
        zhi = lunar_convert.DIZHI[zhi_idx]
        stars[zhi] = []
    
    # 放入主星
    star_map = {
        '紫微': ziwei_pos, '天机': tianji_pos, '太阳': taiyang_pos, '武曲': wuqu_pos,
        '天同': tiantong_pos, '廉贞': lianzhen_pos, '天府': tianfu_pos, '太阴': taiyin_pos,
        '贪狼': tanlang_pos, '巨门': jumen_pos, '天相': tianxiang_pos, '天梁': tianliang_pos,
        '七杀': qisha_pos, '破军': pojun_pos
    }
    
    for star, pos in star_map.items():
        zhi = lunar_convert.DIZHI[pos]
        stars[zhi].append(star)
    
    return stars


def set_sihua(year_gan, stars):
    """安四化"""
    sihua = SIHUA_TABLE.get(year_gan, {})
    result = {}
    
    for zhi_idx in range(12):
        zhi = lunar_convert.DIZHI[zhi_idx]
        zhi_stars = stars.get(zhi, [])
        result[zhi] = []
        for star in zhi_stars:
            if star == sihua.get('禄'):
                result[zhi].append({'star': star, 'sihua': '化禄'})
            elif star == sihua.get('权'):
                result[zhi].append({'star': star, 'sihua': '化权'})
            elif star == sihua.get('科'):
                result[zhi].append({'star': star, 'sihua': '化科'})
            elif star == sihua.get('忌'):
                result[zhi].append({'star': star, 'sihua': '化忌'})
            else:
                result[zhi].append({'star': star, 'sihua': None})
    
    return result


def set_fuxing(ming_gong_zhi, lunar_month, lunar_day, year_gan):
    """安辅星（简化）"""
    # 左辅：从辰宫起正月，顺数到生月
    zuofu_pos = (4 + lunar_month - 1) % 12
    # 右弼：从戌宫起正月，逆数到生月
    youbi_pos = (10 - lunar_month + 1 + 12) % 12
    # 文昌：从戌宫起子时，顺数到生时
    wenchang_pos = (10 + 0) % 12  # 简化
    # 文曲：从辰宫起子时，逆数到生时
    wenqu_pos = (4 - 0 + 12) % 12  # 简化
    # 天魁：根据年干
    tiankui_map = {'甲': 11, '乙': 10, '丙': 9, '丁': 8, '戊': 7, '己': 6, '庚': 5, '辛': 4, '壬': 3, '癸': 2}
    tiankui_pos = tiankui_map.get(year_gan, 0)
    # 天钺
    tianyue_map = {'甲': 5, '乙': 6, '丙': 7, '丁': 8, '戊': 9, '己': 10, '庚': 11, '辛': 0, '壬': 1, '癸': 2}
    tianyue_pos = tianyue_map.get(year_gan, 0)
    
    fuxing = {}
    for zhi_idx in range(12):
        zhi = lunar_convert.DIZHI[zhi_idx]
        fuxing[zhi] = []
    
    fuxing[lunar_convert.DIZHI[zuofu_pos]].append('左辅')
    fuxing[lunar_convert.DIZHI[youbi_pos]].append('右弼')
    fuxing[lunar_convert.DIZHI[wenchang_pos]].append('文昌')
    fuxing[lunar_convert.DIZHI[wenqu_pos]].append('文曲')
    fuxing[lunar_convert.DIZHI[tiankui_pos]].append('天魁')
    fuxing[lunar_convert.DIZHI[tianyue_pos]].append('天钺')
    
    return fuxing


def get_miaowang(star, zhi):
    """获取主星庙旺利陷状态"""
    if star not in ZHUXING_MIAOWANG:
        return '平'
    return ZHUXING_MIAOWANG[star].get(zhi, '平')


def get_daxian(ming_gong_zhi, wuxing_ju, gender, year_gan_idx):
    """排大限"""
    ju_num = get_wuxing_ju_number(wuxing_ju)
    
    # 阳男阴女：顺行；阴男阳女：逆行
    is_yang = year_gan_idx % 2 == 0
    forward = (is_yang and gender == '男') or (not is_yang and gender == '女')
    
    daxian = []
    for i in range(12):
        if forward:
            start_age = ju_num + i * 10
            zhi_pos = (ming_gong_zhi + i) % 12
        else:
            start_age = ju_num + i * 10
            zhi_pos = (ming_gong_zhi - i + 12) % 12
        
        daxian.append({
            'index': i + 1,
            'zhi': lunar_convert.DIZHI[zhi_pos],
            'age_start': start_age,
            'age_end': start_age + 9
        })
    
    return daxian


def get_gong_layout(ming_gong_zhi):
    """生成十二宫布局（以命宫为起点）"""
    layout = {}
    for i, gong_name in enumerate(ZHIWEI_GONG_ORDER):
        zhi_pos = (ming_gong_zhi + i) % 12
        zhi = lunar_convert.DIZHI[zhi_pos]
        layout[gong_name] = zhi
    return layout


def get_gong_ganzhi(ming_gong_zhi, year_gan):
    """计算各宫的天干地支"""
    # 根据五虎遁月法确定命宫天干
    year_gan_idx = lunar_convert.TIANGAN.index(year_gan)
    # 五虎遁月：甲己之年丙作首，乙庚之岁戊为头，丙辛之年寻庚起，
    # 丁壬壬位顺行流，戊癸之年甲上求。
    ming_gan_idx = (year_gan_idx * 2 + 2) % 10
    
    ganzhi = {}
    for i, gong_name in enumerate(ZHIWEI_GONG_ORDER):
        zhi_pos = (ming_gong_zhi + i) % 12
        zhi = lunar_convert.DIZHI[zhi_pos]
        gan = lunar_convert.TIANGAN[(ming_gan_idx + i) % 10]
        ganzhi[gong_name] = f"{gan}{zhi}"
    
    return ganzhi


def main():
    if len(sys.argv) < 7:
        print("Usage: python ziwei_pan.py <year> <month> <day> <hour> <minute> <gender> [city]")
        sys.exit(1)
    
    year = int(sys.argv[1])
    month = int(sys.argv[2])
    day = int(sys.argv[3])
    hour = int(sys.argv[4])
    minute = int(sys.argv[5])
    gender = sys.argv[6]
    city = sys.argv[7] if len(sys.argv) > 7 else None
    
    # 使用 lunar_convert 获取真太阳时和农历数据
    base = lunar_convert.get_bazi_pillars(year, month, day, hour, minute, gender, city)
    
    # 获取农历信息
    if Lunar is not None:
        dt = datetime(year, month, day, hour, minute)
        lunar = Lunar(dt)
        lunar_info = lunar.get_lunarDateNum()
        lunar_month = lunar_info[1]
        lunar_day = lunar_info[2]
    else:
        lunar_month = month
        lunar_day = day
    
    # 时辰地支索引
    if hour % 2 == 1:
        hour_zhi_idx = (hour + 1) // 2 % 12
    else:
        hour_zhi_idx = hour // 2 % 12
    
    # 安命宫、身宫
    ming_gong_zhi, shen_gong_zhi = get_ming_shen_gong(lunar_month, lunar_day, hour_zhi_idx)
    
    # 十二宫布局
    gong_layout = get_gong_layout(ming_gong_zhi)
    
    # 各宫干支
    year_gan = base['pillars']['year'][0]
    gong_ganzhi = get_gong_ganzhi(ming_gong_zhi, year_gan)
    
    # 命宫干支
    ming_ganzhi = gong_ganzhi['命宫']
    
    # 定五行局
    wuxing_ju = get_wuxing_ju(ming_ganzhi)
    
    # 安主星
    stars = set_zhu_stars(ming_gong_zhi, lunar_day, wuxing_ju)
    
    # 安四化
    sihua = set_sihua(year_gan, stars)
    
    # 安辅星
    fuxing = set_fuxing(ming_gong_zhi, lunar_month, lunar_day, year_gan)
    
    # 获取各宫主星和状态
    gong_stars = {}
    for gong_name, zhi in gong_layout.items():
        zhi_stars = sihua.get(zhi, [])
        zhi_fuxing = fuxing.get(zhi, [])
        gong_stars[gong_name] = {
            'zhi': zhi,
            'ganzhi': gong_ganzhi[gong_name],
            'zhu_stars': [s for s in zhi_stars if s['star'] in ['紫微', '天机', '太阳', '武曲', '天同', '廉贞', '天府', '太阴', '贪狼', '巨门', '天相', '天梁', '七杀', '破军']],
            'fu_stars': zhi_fuxing,
            'miaowang': {s['star']: get_miaowang(s['star'], zhi) for s in zhi_stars if s['star'] in ZHUXING_MIAOWANG}
        }
    
    # 大限
    year_gan_idx = lunar_convert.TIANGAN.index(year_gan)
    daxian = get_daxian(ming_gong_zhi, wuxing_ju, gender, year_gan_idx)
    
    result = {
        'input': {
            'year': year, 'month': month, 'day': day,
            'hour': hour, 'minute': minute,
            'gender': gender, 'city': city
        },
        'time_conversion': base.get('time_conversion', {}),
        'ming_gong': {
            'zhi': lunar_convert.DIZHI[ming_gong_zhi],
            'ganzhi': ming_ganzhi,
            'position': '命宫'
        },
        'shen_gong': {
            'zhi': lunar_convert.DIZHI[shen_gong_zhi],
            'position': '身宫'
        },
        'wuxing_ju': wuxing_ju,
        'gong_layout': gong_layout,
        'gong_stars': gong_stars,
        'daxian': daxian,
        'sihua': SIHUA_TABLE.get(year_gan, {})
    }
    
    return result


if __name__ == '__main__':
    result = main()
    output_file = os.environ.get('FORTUNE_OUTPUT_FILE', 'ziwei_result.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"Result written to {output_file}")
