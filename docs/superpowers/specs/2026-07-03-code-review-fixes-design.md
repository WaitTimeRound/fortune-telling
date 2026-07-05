# 命理占星工具代码审查修复设计

## 背景

对 `fortune-telling` 项目进行全量代码与文档审查后，发现 11 项问题。本设计按「分批交付」策略（方案 C）实施修复，便于逐批验证与回滚。

## 目标

修复以下 11 项问题，保持 CLI 接口在合理范围内向后兼容，并确保每次批次都能独立验证。

## 分批计划

### 第一批：明确功能 bug

| # | 问题 | 文件 | 修复方式 |
|---|------|------|----------|
| 1 | 大运吉凶判断只检查「官杀」，漏判「食伤」「财星」 | `scripts/bazi_pan.py` | 将条件拆分为对「官杀」「食伤」「财星」三组十神的完整匹配 |
| 2 | 七政洞微大限性别硬编码为男 | `scripts/qizheng_pan.py` | `main()` 增加 `gender` 参数，透传给 `get_dongwei_daxian` |
| 3 | 紫微文昌/文曲安星写死子时 | `scripts/ziwei_pan.py` | `set_fuxing()` 增加 `hour_zhi_idx` 参数，按实际出生时辰计算 |
| 4 | 文档编号错误 | `references/western-guide.md`、`references/bazi-guide.md` | 修正 western-guide 中重复的「七、」；检查 bazi-guide 章节口径 |

#### CLI 兼容性说明

- `qizheng_pan.py` 当前用法：`python qizheng_pan.py <year> <month> <day> <hour> <minute> [city]`
- 修复后用法：`python qizheng_pan.py <year> <month> <day> <hour> <minute> <gender> [city]`
- 这是破坏性变更，但性别是命理计算的必要输入，与 `bazi_pan.py`、`ziwei_pan.py` 保持一致。

### 第二批：代码质量与一致性

| # | 问题 | 文件 | 修复方式 |
|---|------|------|----------|
| 5 | 多处 gender='男' 硬编码 | `scripts/western_pan.py`、`scripts/qizheng_pan.py` | `western_pan.py` 增加 `gender` 参数并透传；`qizheng_pan.py` 中第一批已处理 |
| 6 | `print()` 警告污染 stdout | `scripts/lunar_convert.py` 等 | 引入 `logging` 模块，将 `print("Warning: ...")` 替换为 `logging.warning(...)` |
| 7 | 七政 today_xiu 用未换算真太阳时的 dt | `scripts/qizheng_pan.py` | 使用 `base['time_conversion']['true_solar_time']` 构造 `datetime` 后再取二十八宿 |

#### CLI 兼容性说明

- `western_pan.py` 当前用法：`python western_pan.py <year> <month> <day> <hour> <minute> <city>`
- 修复后用法：`python western_pan.py <year> <month> <day> <hour> <minute> <gender> <city>`
- 同样破坏性变更，但与项目其它脚本保持一致。

### 第三批：算法精度改进

| # | 问题 | 文件 | 修复方式 |
|---|------|------|----------|
| 8 | 紫微安星表覆盖不全 | `scripts/ziwei_pan.py` | 扩展 `ZIWEI_TABLE` 或增加闰月/顺逆局处理；至少补全常见边界 |
| 9 | 西方占星宫位是近似 Placidus | `scripts/lunar_convert.py` | 实现真正的 Placidus 分宫算法，或显式降级为等宫制并更名 |
| 10 | 七政二十八宿起度是经验值 | `scripts/qizheng_pan.py` | 引入更精确的岁差与宿度起算；至少说明参数来源 |
| 11 | 八字从格判断过于粗糙 | `scripts/bazi_pan.py` | 细化从格判断，增加地支藏干、月令强度等综合判断 |

#### 风险说明

第三批改动会改变输出结果，与 README 中「娱乐级」「建议专业软件复核」的声明并不冲突，但需要在输出中保留免责声明。实施前应单独评估每项改动的可行性与测试方法。

## 验证方法

每批修复后执行：

1. 运行对应脚本示例命令，检查输出 JSON 是否符合预期。
2. 对修改的函数编写/运行最小断言测试（可在 `scripts/` 下新增临时验证脚本，或直接在命令行对比输出）。
3. 检查文档渲染（MD 章节编号）。

## 设计决策

- 不引入新依赖：第三批若需天文精度提升，优先使用现有 `ephem`/`cnlunar`，不新增外部库。
- 不改动 README 核心定位：修复后仍保留「娱乐参考」声明。
- 破坏性 CLI 变更：由于性别是命理计算必要输入，统一 CLI 是合理代价。
