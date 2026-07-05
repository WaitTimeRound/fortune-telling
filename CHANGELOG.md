# 更新日志

## 2026-07-05

### 文档审查与修正

- 修正 `references/qizheng-guide.md` 中罗睺/计都南北交点定义，与 `scripts/qizheng_pan.py` 脚本保持一致（罗睺 = 升交点/北交点，计都 = 降交点/南交点）
- 扩充 `references/ziwei-guide.md` 与 `references/qizheng-guide.md` 的三维度策略建议，确保每个维度至少 6 条具体行为指南
- 统一 `SKILL.md` 与 `README.md` 的真太阳时公式，补充均时差（EOT）说明
- 在 `SKILL.md` 各体系结构要求中明确“精度声明/前置声明”章节，并扩展占位符替换说明
- 在 `README.md` 项目结构中补充 `docs/superpowers/` 目录
- 在 `references/cross-summary-guide.md` 开运建议表格中增加“七政四余建议”列
- 优化 `references/bazi-guide.md` 调候用神示例表述
- 重新编号 `docs/superpowers/specs/2026-07-03-code-review-fixes-design.md` 中的问题列表为连续 1-11

## 2026-07-03

### 修复

- 修复八字大运喜忌判断漏判食伤、财星的问题
- 修复七政四余 `qizheng_pan.py` 与西方占星 `western_pan.py` 性别硬编码问题，CLI 统一增加 `<gender>` 参数
- 修复紫微斗数文昌/文曲安星写死子时的问题，改为按实际出生时辰计算
- 将 `lunar_convert.py` 中的 `print()` 警告替换为 `logging.warning()`，避免污染 stdout
- 七政四余 `today_xiu` 改用真太阳时日期计算，七政/四余/命宫/十二宫统一使用真太阳时排盘
- 细化八字从格判断逻辑（月令、地支藏干、天干印比综合判断）
- 紫微斗数 `ZIWEI_TABLE` 增加边界处理与闰月说明
- 二十八宿起度参数补充来源说明
- 修正 `references/western-guide.md` 章节编号重复

### 改进

- 西方占星宫位接入 `pyswisseph` 真实 Placidus 分宫算法，未安装时回退到近似插值并标记 `approximate: true`
- 所有脚本 `main()` 增加 `gender` 合法性校验
- 新增 `scripts/verify_fixes.py` 验证脚本
- 同步更新 `README.md`、`SKILL.md` 的 CLI 示例、依赖说明与精度描述
- 为所有 `references/` 指南增加「快速检查清单」摘要

## 更早更新

- 七政四余升级：接入 `pyswisseph` 精密星历计算四余星（罗睺=升交点、计都=降交点、月孛=远地点、紫炁=近地点）
- 七政四余升级：采用传统二十八宿宿度表（岁差修正），输出真实躔宿与入宿度数
- 七政四余升级：新增命宫/身宫、命度主/身度主、十二宫布局
- 七政四余升级：改进洞微大限（顺逆区分）
- 修复紫微斗数五虎遁月法公式
- 修复八字从格喜用神判断
- 修复回退时柱天干计算
- 修正西方占星上升点公式（原公式实际计算的是下降点）
- 实现简化 Placidus 宫位系统
- 使用 `ephem` 精确计算真太阳时时差
- 新增 150° 梅花相与 Yod 格局识别
- 添加 `geopy` 缺失时的降级保护
- 细化异常处理
