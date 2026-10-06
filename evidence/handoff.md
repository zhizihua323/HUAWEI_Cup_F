# 交回主控 GPT 的 handoff — TASK「配比 + Scaling 基线证据卡」

> 生成时间：2026-09-24（Asia/Shanghai）。本文件是本任务**唯一**的越界问题登记处。
> 本任务已按补充统一规则结束：完成后立即停止，不启动下一项任务，不修改 00–05，不修改其他 TASK 输出目录。

## 1. 任务状态

| 项 | 结果 |
|---|---|
| 任务 | 整理并核验**已保存**的配比基线与 Scaling Law 基线结果，产出两张证据卡 + 登记表 + 风险清单 |
| 状态 | **已完成并停止** |
| 是否重新拟合 | **否**（未拟合任何模型、未重跑 CV/自助/留一验证、未重算 B6/B7/B8） |
| 是否修改旧结果 | **否**（`solution/` 92 个文件与 7 份根目录项目文档 SHA256 全部未变；证据见 `evidence/verification_record.json` 的 `no_change_proof`） |
| 是否修改 00–05 | **否**（`01`–`05`、`00`、`恢复报告.md` 七个文件哈希不变） |
| 是否修改其他 TASK 目录 | **否**（`tasks/`、`diagnostics/`、`paper/`、`recovery/`、`F题/` 只读；本次写入仅限 `evidence/` 与 `tmp/evidence_build/`） |
| 结论可追溯性 | 登记表 46 行 × `value` 中每个数字均能在被引用的实际输出文件中逐字命中（审计结果：0 处未命中） |

## 2. 本任务交付物（绝对路径）

| 文件 | 字节 | 最后写入 | SHA256 前缀 |
|---|---:|---|---|
| `evidence/mixture_evidence.md` | 18788 | 2026-09-24 18:06:18 | `a38f51ccb14990aa…` |
| `evidence/scaling_evidence.md` | 20841 | 2026-09-24 18:06:18 | `edc0ba2c96effa99…` |
| `evidence/baseline_result_registry.csv` | 23346 | 2026-09-24 18:06:06 | `219f123bad6cb2ac…` |
| `evidence/open_risks.md` | 10326 | 2026-09-24 18:01:12 | `2fbc7b06554dcd7f…` |
| `evidence/verification_record.json` | 9951 | 2026-09-24 18:05:41 | `59a71e640b598262…` |

补充说明（需要主控知晓的产物边界）：

- `evidence/verification_record.json` 是本任务新增的**第 5 个**交付物。原因：统一规则要求“所有结论都必须指向实际输出文件”，而登记表 MIX-16 的数值是本轮复算得到的，必须落盘存放（另含 `no_change_proof`、`provenance_sha256`、`meta.float_parse_policy`）。若主控要求严格只保留施工单列出的 4 个文件，请裁决该文件应并入何处。
- 本任务临时脚本位于 `tmp/evidence_build/`（只读核验，不拟合）：
- `tmp/evidence_build/audit_registry_exactness.py`
- `tmp/evidence_build/build_handoff.py`
- `tmp/evidence_build/build_registry.py`
- `tmp/evidence_build/build_verification_record.py`
- `tmp/evidence_build/crosscheck_paper_registry.py`
- `tmp/evidence_build/patch_audit.py`
- `tmp/evidence_build/patch_card.py`
- `tmp/evidence_build/patch_card2.py`
- `tmp/evidence_build/patch_cards3.py`
- `tmp/evidence_build/patch_registry.py`
- `tmp/evidence_build/patch_registry2.py`
- `tmp/evidence_build/patch_registry3.py`
- `tmp/evidence_build/patch_registry4.py`
- `tmp/evidence_build/patch_registry5.py`
- `tmp/evidence_build/patch_registry6.py`
- `tmp/evidence_build/patch_registry7.py`
- `tmp/evidence_build/patch_registry8.py`
- `tmp/evidence_build/verify_mixture_coef.py`
- `tmp/evidence_build/verify_mixture_metrics.py`
- `tmp/evidence_build/verify_no_changes.py`
- `tmp/evidence_build/verify_readonly.py`
- `tmp/evidence_build/verify_scaling.py`
- `tmp/evidence_build/registry_v1_backup.csv` 是登记表修正前的快照，已被现行版本取代，仅作对照，请勿引用。

## 3. 本轮实际执行的范围（只读）

1. 12 个原始配比/损失 CSV 的 SHA256 与 `solution/outputs/mixture/audit.json` 逐一比对。
2. 由 `*_predictions.csv` 复算 `metrics.csv` 全部 12 组（2 族 × 6 套）指标；由 `normalized_mixtures × coefficients` 复算 12 组预测。
3. 配方集合比对：`test_1m`/`test_60m`/`test_1B` 与训练重叠、`est_10b`/`est_70b` 与训练重叠、两两文件级字节同一性。
4. 由 `B1_all_predictions.csv`（10336 行）复算 4 配置 × 3 划分的 in-sample/留模型/时间外指标。
5. 由 `cluster_bootstrap_parameters.csv` 的 80 条保存重采样复算五个参数的 2.5/50/97.5 分位。
6. 由 `B2/B3/B4/B5/B10_predictions.csv` 复算 `external_validation.csv` 的 all 组指标。
7. 由 `quality_within_ND_slopes.csv` 复核 B6/B7/B8 方向计数；用保存的 B6 参数复算 360 行情景预测与 B7 新增 90 点 RMSE。
8. 结果全部落盘于 `evidence/verification_record.json`。

**未执行**：任何拟合/重采样/交叉验证、质量流水线、C 演化模块、问三优化、论文写作、对 00–05 的任何编辑。

## 4. 需要主控裁决的事项（超出本任务范围）

| ID | 事项 | 证据 | 影响 | 建议选项（供裁决） |
|---|---|---|---|---|
| H-01 | **存在两张并行登记表**：本任务 `evidence/baseline_result_registry.csv`（ID 空间 `MIX-/SCL-/GAP-`，状态词表 `V1–V4`、`A–D`）与另一任务的 `paper/result_registry.md`（ID `RES-*`，状态 `PASS/PARTIAL/FAIL/PENDING`、`APPROVED_*`）。 | 两文件均存在；本任务只读交叉检查：`paper/result_registry.md` 中 35 条含数字的 Q1/Q2 结果，其 `value` 文本**全部**能在其引用的 `solution/` 产物中逐字命中（0 处冲突）。 | 论文数字若来自两处，可能出现 ID/状态不一致或重复引用。 | (a) 以 `paper/result_registry.md` 为唯一入口，本表降级为证据索引，由主控补 `evidence_ref` 映射；(b) 双向映射表；(c) 保持并行但声明分工。**本任务未做任何改动，等裁决。** |
| H-02 | **pandas 默认浮点解析会在末位改变数字**（默认 `float_precision='high'`，非正确舍入）。例：`model_comparison.csv` 的 `0.00014649608992588822` 被默认读成 `0.0001464960899258`。 | `evidence/verification_record.json` 的 `meta.float_parse_policy`；可复现命令见本文件 §5。 | 任何用 pandas 默认解析做**数字核验或登记**的脚本（含其他 TASK、含恢复轮）都可能登记到与文件文本不同的末位数字。 | 建议全项目核验/登记脚本统一 `float_precision='round_trip'`；已登记的高精度数字是否需要复核由主控决定。**本任务未改其他脚本。** |
| H-03 | 本轮新发现的结构性事实（`open_risks.md` 的 N-01…N-06）可能与其他文档的既有表述冲突：如“1M 与 60M 是两次独立检验”“估算集可作外推证据”“大尺度仍有效”等。 | `evidence/open_risks.md` §4；`evidence/verification_record.json` 的 `mixture_structural_facts`、`mixture_recipe_overlap`。 | 若其他任务文档沿用旧表述，会与本卡边界冲突。 | 请主控在其他任务的任务单中转发两卡 §0 的“必须照抄边界”，并指定需要修订的文档（本任务不修改）。 |
| H-04 | **配比 OOF 逐行预测未落盘**，训练内族选择链无法在“不重拟合”前提下复现（登记表唯一 `V4` 条目）。 | `evidence/baseline_result_registry.csv` MIX-12/MIX-13。 | 论文若要主张“按训练 OOF 选中线性族”，目前只有落盘记录支撑。 | 需要主控授权后续任务重跑并落盘 OOF；或明确降级为该结论的表述方式。 |
| H-05 | **B8 与 B6/B7 的 Q 方向冲突未处置**（B8 的 E、k 触界，条件数 1.08e7；共同键 Loss 最大差 2.5769）。 | `evidence/open_risks.md` O-06；`solution/outputs/scaling/quality_audit.json`。 | 直接影响问三能否使用 Q 参数、以及论文中质量方向的写法。 | 需主控裁决冲突处置规则（分层参数 / 排除 B8 / 仅情景披露）。 |
| H-06 | 本任务复核脚本位于 `tmp/evidence_build/`，卡片与登记表按该路径引用。 | 两卡“复核脚本/复核记录”行。 | 若 `tmp/` 被清理或另作约定，引用会失效。 | 请裁决是否迁入 `evidence/`（或任务的正式脚本目录）。本任务未迁移，以免与其他任务的目录约定冲突。 |
| H-07 | **00–05 与 `03_DATA_CATALOG.md` 未包含 `evidence/`**（按规则本任务不得修改）。 | `03_DATA_CATALOG.md` 的产物清单；`evidence/` 现存 6 文件。 | 项目文档与文件系统暂时不一致。 | 由主控或获授权任务补登 `evidence/`；本任务不执行。 |
| H-08 | `paper/result_registry.md` 对 B2/B4/B5/B10、`est_*`、`quality_scenario` 使用“另建验证/不得作真值/未验证情景”的限定，与本卡 `claim_level`（C/D）**方向一致但粒度不同**。 | 两文件对应条目。 | 下游写作可能按其中一种粒度执行。 | 建议由主控确认以本卡 `claim_level` 作为更细的依据补充登记。**本任务未改 paper 文件。** |
| H-09 | 本卡登记但 `paper/result_registry.md` 尚未覆盖的结果：常数基线对照、配方字节同一性、B2 恒定偏差、B9 FLOPs 比分布、自助分位数值等。 | `evidence/baseline_result_registry.csv`（MIX-07…11、MIX-18/19、SCL-30、SCL-42、SCL-29 等）。 | 若论文数字必须“先登记后使用”，这些值目前不能直接进入正文。 | 请裁决是否补登记到 `paper/result_registry.md`（本任务不修改该文件）。 |
| H-10 | 本任务未对**原始 XZ / C8 JSON / Parquet** 做任何解码或重哈希（超出范围）。 | `evidence/verification_record.json` 的读取范围。 | 与质量、C 模块相关的结论不在本卡覆盖内。 | 如需该层证据，另行分派任务。 |

## 5. 复现入口（只读；按顺序执行）

```powershell
python -X utf8 tmp/evidence_build/verify_mixture_metrics.py
python -X utf8 tmp/evidence_build/verify_mixture_coef.py
python -X utf8 tmp/evidence_build/verify_scaling.py
python -X utf8 tmp/evidence_build/verify_no_changes.py
python -X utf8 tmp/evidence_build/build_verification_record.py   # 生成 evidence/verification_record.json
python -X utf8 tmp/evidence_build/build_registry.py              # 生成 evidence/baseline_result_registry.csv（依赖上一行）
python -X utf8 tmp/evidence_build/audit_registry_exactness.py    # 校验登记表每个数字都能在产物中命中
python -X utf8 tmp/evidence_build/crosscheck_paper_registry.py   # 只读对照 paper/result_registry.md
```

pandas 浮点解析的最小复现：

```powershell
python -X utf8 -c "import pandas as pd; a=pd.read_csv('solution/outputs/scaling/model_comparison.csv'); b=pd.read_csv('solution/outputs/scaling/model_comparison.csv', float_precision='round_trip'); print(repr(float(a[a.configuration=='point__linear'].fit_RMSE.iloc[0])), repr(float(b[b.configuration=='point__linear'].fit_RMSE.iloc[0])))"
```

预期输出：`0.0001464960899258 0.00014649608992588822`，后者才是文件文本。

## 6. 本任务产物的自身限制（不需裁决，供引用时注意）

1. 登记表 `claim_level=C/D` 的条目可被引用，但**不可**进入论文强结论；具体禁用表述见两张证据卡 §8。
2. 两卡数值以 10 位或文件原精度两种口径混排：表格内已注明口径，登记表 `value` 一律为文件原精度（`round_trip` 解析）。
3. 本轮所有核验均为“由已保存产物复算”，**不构成**对原脚本端到端重跑的验收。
4. 本任务未判定任何模型“可用”；两张卡的结论仅描述现有保存结果的证据强度。
