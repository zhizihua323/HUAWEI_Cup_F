# FIG-FINAL V3 asset index

五张核心图均按 165 mm 正文宽度绘制；中文使用宋体，纯拉丁字符与数字使用 Times New Roman；所有图内文字最终物理尺寸不低于 12 pt。

| 顺序 | 图题 | 尺寸 | PNG | PDF | SVG | 图前建议 | 图后解释建议 |
|---|---|---|---|---|---|---|---|
| FIG-V3-01 | 总体技术路线与证据边界 | 165 × 84 mm | [fig01_v3_framework.png](fig01_v3_framework.png) | [fig01_v3_framework.pdf](fig01_v3_framework.pdf) | [fig01_v3_framework.svg](fig01_v3_framework.svg) | 置于数据与总体思路说明之后 | 随后说明四问共享冻结口径及资格标签。 |
| FIG-V3-02 | 质量代理的构造与验证 | 165 × 187 mm | [fig02_v3_q1_quality.png](fig02_v3_q1_quality.png) | [fig02_v3_q1_quality.pdf](fig02_v3_q1_quality.pdf) | [fig02_v3_q1_quality.svg](fig02_v3_q1_quality.svg) | 置于质量得分 Q 定义之后 | 随后解释部分稳定和人工核验局限。 |
| FIG-V3-03 | 配比模型检验与跨尺度运输 | 165 × 130 mm | [fig03_v3_regmix_transport.png](fig03_v3_regmix_transport.png) | [fig03_v3_regmix_transport.pdf](fig03_v3_regmix_transport.pdf) | [fig03_v3_regmix_transport.svg](fig03_v3_regmix_transport.svg) | 置于 RegMix 模型与验证口径之后 | 随后强调 n、散点单位及两种 RMSE 口径。 |
| FIG-V3-04 | 标度模型的支持覆盖与分来源验证 | 165 × 182 mm | [fig04_v3_q2_validation.png](fig04_v3_q2_validation.png) | [fig04_v3_q2_validation.pdf](fig04_v3_q2_validation.pdf) | [fig04_v3_q2_validation.svg](fig04_v3_q2_validation.svg) | 置于 B1 条件标度模型之后 | 随后逐来源陈述失败、同源插值、域外和估算资格。 |
| FIG-V3-05 | 六任务未来情景 | 165 × 161 mm | [fig05_v3_q4_scenarios.png](fig05_v3_q4_scenarios.png) | [fig05_v3_q4_scenarios.pdf](fig05_v3_q4_scenarios.pdf) | [fig05_v3_q4_scenarios.svg](fig05_v3_q4_scenarios.svg) | 置于情景定义与预测起点之后 | 随后强调三点并非置信区间且未经时间外验证。 |

## Supporting files

- `source_data/`: minimal frozen plotting inputs.
- `figure_source_map.csv`: source-to-panel mapping.
- `FIGURE_CONTRACTS.md`: claim and reviewer-risk contract.
- `checks.json`: machine-readable export and integrity checks.
- `VISUAL_QA.md`: final-size visual inspection record.
- `main_text_png_sha256.csv`: frozen PNG hashes.
- `build_submission_v3.py`: reproducible Python builder.
