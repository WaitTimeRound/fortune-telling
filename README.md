# 命理占星综合分析工具

> **郑重声明：本项目所有内容仅供文化娱乐与自我探索，不可作为人生决策依据。**

一套基于 Python 的命理占星排盘工具，支持八字、紫微斗数、七政四余、西方占星四大体系，并提供多体系交叉分析所需的基础数据输出。

## 功能特性

- **八字排盘**：四柱干支、藏干十神、五行统计、神煞、大运、格局判断、调候用神、喜用神
- **紫微斗数**：命宫身宫、五行局、十四主星、辅星、四化、庙旺利陷、十二宫布局、大限
- **七政四余**：七政星躔宿、四余星、二十八宿、洞微大限
- **西方占星**：行星位置、上升点、十二宫位、相位、格局识别（T三角、大三角、星群、Yod）
- **真太阳时换算**：根据出生地点经度自动换算，严格遵循"23时规则"
- **多体系输出**：每个体系生成独立 JSON 文件，便于后续 AI 解读或报告生成

## 项目结构

```
.
├── references/          # 各体系深度解读写作指南
│   ├── bazi-guide.md
│   ├── cross-summary-guide.md
│   ├── qizheng-guide.md
│   ├── western-guide.md
│   └── ziwei-guide.md
├── scripts/             # 排盘脚本
│   ├── lunar_convert.py # 公共基础：农历转换、干支、真太阳时、西方占星基础计算
│   ├── bazi_pan.py      # 八字排盘（含格局、用神）
│   ├── ziwei_pan.py     # 紫微斗数排盘
│   ├── qizheng_pan.py   # 七政四余排盘
│   └── western_pan.py   # 西方占星排盘
├── SKILL.md             # Kimi 技能说明（解读工作流）
├── CHANGELOG.md         # 更新日志
└── README.md            # 本文件
```

## 安装依赖

```bash
pip install cnlunar ephem geopy pyswisseph
```

- `cnlunar`：农历、八字、节气、神煞计算
- `ephem`：天文计算、行星位置、真太阳时
- `geopy`：城市经纬度查询
- `pyswisseph`：精密星历，用于七政四余四余星（罗睺、计都、紫炁、月孛）计算

若某个库未安装，脚本会降级到简化计算并输出警告。

## 使用方法

### 八字排盘

```bash
python scripts/bazi_pan.py <年> <月> <日> <时> <分> <性别> [城市]

# 示例
python scripts/bazi_pan.py 1990 5 15 14 30 男 北京
```

### 紫微斗数排盘

```bash
python scripts/ziwei_pan.py <年> <月> <日> <时> <分> <性别> [城市]

# 示例
python scripts/ziwei_pan.py 1990 5 15 14 30 男 北京
```

### 西方占星排盘

```bash
python scripts/western_pan.py <年> <月> <日> <时> <分> <性别> <城市>

# 示例
python scripts/western_pan.py 1990 5 15 14 30 男 北京
```

### 七政四余排盘

```bash
python scripts/qizheng_pan.py <年> <月> <日> <时> <分> <性别> [城市]

# 示例
python scripts/qizheng_pan.py 1990 5 15 14 30 男 北京
```

### 指定输出文件

```bash
# Windows
set FORTUNE_OUTPUT_FILE=D:\result.json
python scripts/bazi_pan.py 1990 5 15 14 30 男 北京

# Linux/macOS
export FORTUNE_OUTPUT_FILE=/tmp/result.json
python scripts/bazi_pan.py 1990 5 15 14 30 男 北京
```

### 默认输出文件

| 脚本 | 默认输出 |
|------|----------|
| `bazi_pan.py` | `bazi_result.json` |
| `ziwei_pan.py` | `ziwei_result.json` |
| `western_pan.py` | `western_result.json` |
| `qizheng_pan.py` | `qizheng_result.json` |
| `lunar_convert.py` | `lunar_convert_result.json` |

## 真太阳时说明

所有脚本均支持通过 `city` 参数自动查询城市经纬度并换算真太阳时。

换算公式：

```
真太阳时 = 北京时间 + (经度 - 120) × 4 分钟 + 时差(EOT)
```

当出生地点经度与北京时间（120°E）差异超过 15 分钟时，会自动换算。八字排盘以真太阳时为准。

## 精度说明

| 体系 | 精度 | 说明 |
|------|------|------|
| 八字 | 1901–2100 年精确 | 基于 `cnlunar`，严格遵循节气与 23 时规则 |
| 紫微斗数 | 基于 cnlunar 农历数据 | 安星步骤繁复，建议用专业软件复核 |
| 西方占星 | 基于 ephem 地心黄道坐标 | 默认使用 Placidus 分宫；安装 `pyswisseph` 时调用真实 Placidus 算法，未安装时回退到近似插值 |
| 七政四余 | 七政用 `ephem`，四余星用 `pyswisseph` 精密星历 | 四余星接入真实月交点与远近地点；二十八宿采用传统宿度并岁差修正；建议用专业软件复核 |

## 解读指南

项目内置 `references/` 目录，提供各体系的 AI 解读写作规范：

- `bazi-guide.md`：八字命理报告结构
- `ziwei-guide.md`：紫微斗数报告结构
- `qizheng-guide.md`：七政四余报告结构
- `western-guide.md`：西方占星报告结构
- `cross-summary-guide.md`：多体系交叉综合报告结构

`SKILL.md` 定义了 Kimi 调用这些脚本的工作流程与输出规范。

## 最近更新

- 修复八字大运喜忌、七政/西方性别透传、紫微文昌文曲时辰等代码审查问题
- 西方占星接入 `pyswisseph` 真实 Placidus 分宫算法
- 新增 `scripts/verify_fixes.py` 验证脚本与 `CHANGELOG.md`

完整更新历史见 [CHANGELOG.md](./CHANGELOG.md)。

## 许可证

详见 `LICENSE` 文件。

---

**再次声明：本项目仅供文化娱乐参考，不可作为医疗、投资、婚姻等重大决策依据。**
