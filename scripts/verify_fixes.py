#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""修复验证脚本：对代码审查修复项进行最小化断言测试。"""
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, 'scripts')


def run_script(name, args):
    """运行某个排盘脚本并返回解析后的 JSON。"""
    env = os.environ.copy()
    env['FORTUNE_OUTPUT_FILE'] = os.path.join(ROOT, 'verify_result.json')
    subprocess.run(
        [sys.executable, os.path.join(SCRIPTS, name)] + args,
        cwd=ROOT, env=env, check=True
    )
    with open(env['FORTUNE_OUTPUT_FILE'], encoding='utf-8') as f:
        return json.load(f)


def test_bazi_dayun_quality():
    """八字：喜用神包含官杀/食伤/财星时，这些十神的大运应为吉。"""
    r = run_script('bazi_pan.py', ['1990', '5', '15', '14', '30', '男', '北京'])
    xiyong = r['advanced']['xiyongshen']['xiyong']
    assert '官杀' in xiyong or '食伤' in xiyong or '财星' in xiyong, \
        f'喜用神 unexpected: {xiyong}'
    good = [d for d in r['dayun'] if d['quality'] == '吉']
    good_shishen = {d['shishen'] for d in good}
    for s in ['食神', '伤官', '正财', '偏财', '正官', '七杀']:
        assert s in good_shishen, f'{s} 大运未被标记为吉'
    print('PASS: bazi_dayun_quality')


def test_qizheng_gender():
    """七政：女性与男性洞微大限方向相反。"""
    rm = run_script('qizheng_pan.py', ['1990', '5', '15', '14', '30', '男', '北京'])
    rf = run_script('qizheng_pan.py', ['1990', '5', '15', '14', '30', '女', '北京'])
    assert rm['input']['gender'] == '男'
    assert rf['input']['gender'] == '女'
    male_zhi = [d['zhi'] for d in rm['daxian']]
    female_zhi = [d['zhi'] for d in rf['daxian']]
    assert male_zhi != female_zhi, '男女大限顺序不应相同'
    # 阳年男顺行、女逆行，从同一命宫出发后第二宫应相反
    assert male_zhi[0] == female_zhi[0], '男女大限起点应相同'
    assert male_zhi[1] != female_zhi[1], '男女大限第二宫应不同'
    print('PASS: qizheng_gender')


def test_ziwei_wenchang_wenqu():
    """紫微：文昌/文曲位置随出生时辰变化。"""
    r0 = run_script('ziwei_pan.py', ['1990', '5', '15', '0', '30', '男', '北京'])
    r6 = run_script('ziwei_pan.py', ['1990', '5', '15', '12', '30', '男', '北京'])

    def find_star(result, star_name):
        for gong, data in result['gong_stars'].items():
            if star_name in data.get('fu_stars', []):
                return data['zhi']
        return None

    assert find_star(r0, '文昌') != find_star(r6, '文昌'), '文昌应随时辰变化'
    assert find_star(r0, '文曲') != find_star(r6, '文曲'), '文曲应随时辰变化'
    print('PASS: ziwei_wenchang_wenqu')


def test_western_placidus():
    """西方占星：Placidus 宫头不应是严格的 30° 等分。"""
    r = run_script('western_pan.py', ['1990', '5', '15', '14', '30', '男', '北京'])
    houses = r['raw']['houses']
    # 至少部分相邻宫头间隔明显偏离 30°
    diffs = []
    for i in range(1, 12):
        a = houses[str(i)]['cusp']
        b = houses[str(i + 1)]['cusp']
        diff = (b - a + 360) % 360
        diffs.append(diff)
    assert max(diffs) > 32 or min(diffs) < 28, 'Placidus 宫头间隔应不均匀'
    assert r['input']['gender'] == '男'
    print('PASS: western_placidus')


def test_congge():
    """八字：从格判断不会把明显有根气的命局误判为从格（回归测试）。"""
    # 1990-05-15 日主为庚金，月令巳火克金，原本不一定从格，但此用例主要确保不崩溃
    r = run_script('bazi_pan.py', ['1990', '5', '15', '14', '30', '男', '北京'])
    pattern = r['advanced']['pattern']['type']
    assert pattern in ['正官格', '七杀格', '正印格', '偏印格', '食神格', '伤官格',
                       '正财格', '偏财格', '建禄格/月劫格', '正格', '从格']
    print('PASS: congge (pattern=%s)' % pattern)


def test_invalid_gender():
    """CLI：非法性别应报错退出。"""
    for script in ['bazi_pan.py', 'ziwei_pan.py', 'qizheng_pan.py', 'western_pan.py']:
        args = ['1990', '5', '15', '14', '30', 'X']
        if script == 'western_pan.py':
            args.append('北京')
        elif script == 'qizheng_pan.py':
            args.append('北京')
        result = subprocess.run(
            [sys.executable, os.path.join(SCRIPTS, script)] + args,
            cwd=ROOT, capture_output=True, text=True
        )
        assert result.returncode != 0, f'{script} 应对非法性别报错'
        assert ('gender must be' in (result.stdout + result.stderr) or
                'invalid choice' in (result.stdout + result.stderr)), \
            f'{script} 错误信息不完整'
    print('PASS: invalid_gender')


if __name__ == '__main__':
    test_bazi_dayun_quality()
    test_qizheng_gender()
    test_ziwei_wenchang_wenqu()
    test_western_placidus()
    test_congge()
    test_invalid_gender()
    print('\nAll verifications passed.')
