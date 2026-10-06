import pathlib

# ---------------- mixture card ----------------
p = pathlib.Path('evidence/mixture_evidence.md'); s = p.read_text(encoding='utf-8')
reps = [
 ("| 复核脚本 | `tmp/evidence_build/verify_mixture_metrics.py`、`tmp/evidence_build/verify_mixture_coef.py`（只读，不拟合） |",
  "| 复核脚本 | `tmp/evidence_build/verify_mixture_metrics.py`、`tmp/evidence_build/verify_mixture_coef.py`（只读，不拟合） |\n| 复核记录 | `evidence/verification_record.json`（本轮全部复算结果落盘；`meta.float_parse_policy` 记录 CSV 读取口径） |"),
 ("| 导出系数 → 预测 | 用 `normalized_mixtures × coefficients` 复算 12 组预测，最大偏差 **5.5e-14** |",
  "| 导出系数 → 预测 | 用 `normalized_mixtures × coefficients` 复算 12 组预测，最大偏差 **1.8e-14** |"),
]
for old, new in reps:
    assert old in s, old[:60]
    s = s.replace(old, new)
anchor = "**② 恢复轮已核验（`recovery/2026-09-24/verification.json`，本卡未复算）**"
assert anchor in s
s = s.replace(anchor, "数值解析口径：本轮统一以 `pandas.read_csv(..., float_precision='round_trip')` 读取 CSV。pandas 默认 `high` 解析会在末位产生偏差（例：`model_comparison.csv` 中 `0.00014649608992588822` 默认读成 `0.0001464960899258`），因此凡引用高精度数字都应使用 `round_trip`；该口径已记入 `evidence/verification_record.json` 的 `meta`。\n\n" + anchor)
p.write_text(s, encoding='utf-8'); print('mixture card patched')

# ---------------- scaling card ----------------
p = pathlib.Path('evidence/scaling_evidence.md'); s = p.read_text(encoding='utf-8')
reps = [
 ("| 复核脚本 | `tmp/evidence_build/verify_scaling.py`（只读，不拟合） |",
  "| 复核脚本 | `tmp/evidence_build/verify_scaling.py`（只读，不拟合） |\n| 复核记录 | `evidence/verification_record.json`（本轮全部复算结果落盘；`meta.float_parse_policy` 记录 CSV 读取口径） |"),
 ("| 80 条保存自助重采样 → 五个参数 2.5/50/97.5 分位 | 与 `scaling_params.json` 一致（最大差 5.6e-17） |",
  "| 80 条保存自助重采样 → 五个参数 2.5/50/97.5 分位 | 与 `scaling_params.json` **完全一致（diff = 0.0）** |"),
 ("| B1 四配置 × 三划分的 in-sample 指标 | 由 `B1_all_predictions.csv`（10336 行）复算，最大差 8.8e-16 |",
  "| B1 四配置 × 三划分的 in-sample 指标 | 由 `B1_all_predictions.csv`（10336 行）复算，**最大差 0.0** |"),
 ("复算 0.0001511797786 / 0.0001090974916，与 `model_comparison.csv` 一致",
  "复算 0.00015117977861670508 / 0.00010909749164734156，与 `model_comparison.csv` **完全一致**"),
 ("| 外部材料 B2/B3/B4/B5/B10 的 all 组指标 | 由各自 `*_predictions.csv` 复算，与 `external_validation.csv` 一致 |",
  "| 外部材料 B2/B3/B4/B5/B10 的 all 组指标 | 由各自 `*_predictions.csv` 复算，与 `external_validation.csv` **完全一致（diff = 0.0）** |"),
 ("| B6 情景预测（360 行） | 用保存的 B6 参数复算，最大差 4.4e-16 |",
  "| B6 情景预测（360 行） | 用保存的 B6 参数复算，**最大差 0.0** |"),
]
for old, new in reps:
    assert old in s, old[:60]
    s = s.replace(old, new)
anchor2 = "**② 恢复轮已核验（`recovery/2026-09-24/verification.json`）**"
assert anchor2 in s
s = s.replace(anchor2, "数值解析口径：本轮统一以 `pandas.read_csv(..., float_precision='round_trip')` 读取 CSV。pandas 默认 `high` 解析会在末位产生偏差（例：`model_comparison.csv` 中 `0.00014649608992588822` 默认读成 `0.0001464960899258`），故高精度数字一律按 `round_trip` 复核；口径见 `evidence/verification_record.json` 的 `meta`。\n\n" + anchor2)
p.write_text(s, encoding='utf-8'); print('scaling card patched')
