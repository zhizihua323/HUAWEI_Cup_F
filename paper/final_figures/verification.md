# 最终图表验证说明

总状态：`PASS`。科学阶段保持 `SCIENCE_CLOSED`，本次只执行字段选择、排版和可视化。

- 交付规模：7 幅核心图、9 张核心表。每幅图含 600 dpi PNG、SVG、PDF、脚本入口、最小源数据、caption 与 source map；每张表含 CSV、DOCX、caption 与 source map。
- 强制补丁：Q1 图 2/表 3、Q2 图 4/表 6、Q4 图 7/表 9 的科学内容已按最终补丁合同更新；本资产包内部编号分别为 FIG-02/TAB-03、FIG-04/TAB-06、FIG-06/TAB-09。
- Q4：42 条任务情景与 6 条辅助均值全部保留 `SCENARIO_ONLY_UNVALIDATED`；MATH Lvl 5 的 24 月三项负值未 clip；两类文件中的日期均使用 2025-01-28 原点与 2026/2027 同日目标。
- 图像 QA：逐幅检查最终 PNG；SVG 保留 `<text>` 节点，PDF 使用 TrueType 字体。黑白区分同时依靠网纹、线型、标记和直接标签。
- DOCX QA：打包运行时未包含 LibreOffice，故使用本机 Microsoft Word 隐式导出 9 个临时 PDF，并对每页 PNG 进行视觉检查；所有表均为单页，无裁切、重叠、缺字或跨页断裂。临时 QA 文件不纳入交付。
- 静态绘图审查：12 PASS、2 个已解释 WARN、0 FAIL。PNG 已满足用户要求的 600 dpi；未额外交付 TIFF。图 5 的对数轴只用于严格为正的冻结 N_B/D_B，不执行对数变换或数值替换。

## 机器检查

| 检查 | 状态 |
|---|---|
| `asset_count` | `PASS` |
| `figure_bundle_complete` | `PASS` |
| `table_bundle_complete` | `PASS` |
| `png_600_dpi` | `PASS` |
| `svg_editable_text` | `PASS` |
| `q4_negative_values_preserved` | `PASS` |
| `q4_all_unvalidated` | `PASS` |
| `q3_upper_boundary_retained` | `PASS` |
| `q2_source_qualifications` | `PASS` |
| `q1_manual_denominators` | `PASS` |
| `docx_visual_qa` | `PASS` |
| `black_white_redundancy` | `PASS` |
| `figure_validator` | `PASS` |
