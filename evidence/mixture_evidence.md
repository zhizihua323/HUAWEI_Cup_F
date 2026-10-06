# 配比模型证据卡（RegMix 17 域配比 → 13 域验证 Loss）

| 字段 | 内容 |
|---|---|
| 卡片编号 | EV-MIX-01 |
| 生成时间 | 2026-09-24（Asia/Shanghai） |
| 覆盖范围 | `solution/outputs/mixture/`（27 文件）+ `solution/reports/mixture_baseline.md` + 原始表 A4–A15 |
| 本轮动作 | 只读整理与核验：原始 CSV 哈希比对、行数比对、逐行预测复算指标、导出系数复算预测、配方集合比对 |
| 本轮未做 | 未重新拟合、未重跑交叉验证/自助重采样、未修改任何原始数据与旧输出 |
| 证据分级 | ①本轮直接复算 ②恢复轮已核验 ③仅落盘记录（未复算） ④无逐行产物/需重拟合才可复算 |
| 登记表 | `evidence/baseline_result_registry.csv`（`result_id` 前缀 `MIX-`） |
| 复核脚本 | `tmp/evidence_build/verify_mixture_metrics.py`、`tmp/evidence_build/verify_mixture_coef.py`（只读，不拟合） |
| 复核记录 | `evidence/verification_record.json`（本轮全部复算结果落盘；`meta.float_parse_policy` 记录 CSV 读取口径） |

## 0. 一句话结论与四条必须照抄的边界

**一句话结论**：在 1M 尺度上，17 维配比的线性 Scheffé 模型相对“训练域均值”常数基线具有真实但有限的独立预测能力（RMSE 0.2270 对 0.2846，秩相关 0.625）；该能力在 60M/1B 尺度基本失效，10B/70B 只是估算材料，**不能**作为大尺度验证。模型系数是条件模型量，**不是因果效应**。

| 编号 | 必须照抄的边界 | 依据 |
|---|---|---|
| B1 | **1M 是真正独立检验**：`test_1m` 的 256 条配方与训练集配方重叠为 0，且未用于调参/选型。 | `audit.json`（`recipes_identical_to_training=0`）、本轮配方集合比对 ① |
| B2 | **60M/1B 迁移误差较大**：60M RMSE≈1.5173、1B RMSE≈3.1889，而 1M 为 0.2270；1B 甚至比常数基线（3.1195）更差，R² 为 −3768。 | `metrics.csv` 本轮复算 ① |
| B3 | **10B/70B 属估算相关材料**：Loss 为估算值（`estimated`），且 63 条配方 100% 来自训练集。它们不是真值，也不是样本外检验。 | `audit.json`、`dataset_registry` ②、本轮比对 ① |
| B4 | **不把线性系数解释为因果效应**：单纯形变量和为 1，系数是无截距条件关联，且经岭惩罚收缩；改变一个域配比必然挤压其他域。 | D03、`linear_coefficients.csv` 头部 ③ |

## 1. 数据来源

原始目录：`F题/real_attachments/A_data_value/regmix_tables/`（只读）。每套数据 = 一张配比表 + 一张损失表，按 `index` 一对一连接。

| 逻辑集 | 配比表（字节） | 损失表（字节） | 行数 | 说明文件性质 | 17 配比列 | 13 损失列 |
|---|---|---:|---:|---|---|---|
| `train_1m` | `train_mixture_1m.csv` (46412) | `train_pile_loss_1m.csv` (121898) | 512 | observed | `train_the_pile_*` | `metric/*` |
| `test_1m` | `test_mixture_1m.csv` (23537) | `test_pile_loss_1m.csv` (61175) | 256 | observed | 同左 | 同左 |
| `test_60m` | `test_mixture_60m.csv` (23537) | `test_pile_loss_60m.csv` (61827) | 256 | observed | 同左 | 同左 |
| `test_1B` | `test_mixture_1B.csv` (6393) | `test_pile_loss_1B.csv` (10639) | 64 | observed | 同左 | 同左 |
| `est_10b` | `est_mixture_10b.csv` (6113) | `est_pile_loss_10b.csv` (6467) | 63 | training_subset / estimated | 同左 | 同左 |
| `est_70b` | `est_mixture_70b.csv` (6113) | `est_pile_loss_70b.csv` (6467) | 63 | training_subset / estimated | 同左 | 同左 |

本轮哈希核验 ①：12 个原始文件的 SHA256 **全部**等于 `solution/outputs/mixture/audit.json` 中保存的 `p_sha256`/`loss_sha256`（6 套 × 配比/损失）。

本轮发现的结构性事实 ①（此前报告未写明，登记为 MIX-18/MIX-19）：

- `test_mixture_1m.csv` 与 `test_mixture_60m.csv` **字节完全相同**（SHA256 `197267b7d6f15367e2f46c881e564c35b0d34e51b1754bb09d07e650cf8e1ce8`，23537 字节）。即 60M 与 1M 使用同一批 256 条配方，只是换了模型规模。二者**不是两份独立配方样本**。
- `est_mixture_10b.csv` 与 `est_mixture_70b.csv` **字节完全相同**（`880c7ca1ebef470422e2b93d9bfcd0976db7db4e34ea57047518d95fe43327d1`），且这 63 条配方 100% 出现在训练集中。
- 与训练配方的重叠：`test_1m` 0/256、`test_60m` 0/256、`test_1B` 0/64、`est_10b` 63/63、`est_70b` 63/63。

数据性质提醒：「observed」是数据说明文件的标签，不是外部真实性认证（D01）；三张测试表的 13 个损失域都来自同一 Pythia 验证口径。

## 2. 训练/验证/外推划分

| 用途 | 数据 | 划分方式 | 规模 | 是否用于选择 | 证据 |
|---|---|---|---|---|---|
| 训练/选型 | `train_1m` | 训练集内嵌套 5 折 `KFold(shuffle, seed=20260924)`；内层对岭惩罚做网格搜索；外层生成 OOF | 512×13 | 是（唯一允许用于选择的集合） | `model.json`、`mixture_baseline.py` ③ |
| 独立检验 | `test_1m` | 未参与任何选择；配方与训练零重叠 | 256×13 | 否 | `model.json: test_usage=not_used_for_selection` ② |
| 跨规模迁移 | `test_60m` | 模型直接套用，**无重标定**；配方批次与 `test_1m` 相同 | 256×13 | 否 | 本轮哈希/集合比对 ① |
| 跨规模迁移 | `test_1B` | 模型直接套用，无重标定；配方与训练零重叠 | 64×13 | 否 | `audit.json` ① |
| 估算对照（外推材料） | `est_10b`、`est_70b` | 模型直接套用；Loss 为估算值；配方取自训练集子集 | 63×13 各 | 否 | `audit.json`、`dataset_registry` ①② |
| 平凡参照 | 全体 | 常数基线 = 训练响应域均值（仅用训练集拟合），逐套应用 | 同上 | 否 | `metrics.csv` 本轮复算 ① |

要点：真正“样本外且配方独立”的只有 `test_1m` 与 `test_1B`；`test_60m` 与 `test_1m` 共享配方，`est_*` 的配方在训练集内。这一划分层级是引用结果时的第一道限定。

## 3. 模型形式

- 输入：行归一化后的单纯形配比 `p`（17 维，行和 1，保留零值，不加伪计数、不取对数；原表行和 0.996–1.003，归一化最大修正 0.004）。
- 线性族（最终主族）：`f(p) = Σ_{j=1..17} θ_j p_j`，无截距，17 项。
- 二次族（对照）：`f(p) = Σ_j θ_j p_j + Σ_{i<j} θ_ij p_i p_j`，仅不同域交叉项，153 项。
- 输出：13 维（每个验证域一个），实现为多输出岭回归 `StandardScaler(with_mean=False) + Ridge(fit_intercept=False)`；惩罚网格 `logspace(-5,3,9)`。
- 选择准则：训练集内层 5 折 CV 选惩罚，外层 OOF 在两族间取 **各域 MSE 的平均**（因 13 列行数相同，等价于 pooled MSE）最小者 → 选中 `linear`；选出后在全训练集重拟合并冻结，测试集不做校准。族选择后的 OOF 可能乐观，`test_1m` 才是确认集。
- 边际/导数性质：因 `Σp=1`，系数是“其他域配比随单纯形约束变化”条件下的条件关联，不是可独立调节的因果效应（D03）。

## 4. 参数

| 项 | 值 | 位置 |
|---|---|---|
| 主族 | `linear`（`selected_by_training_only`） | `model.json`（登记 MIX-13） |
| 线性族最终惩罚 | `alpha = 1.0` | `model.json.models.linear.alpha` |
| 二次族最终惩罚 | `alpha = 0.1` | `model.json.models.quadratic.alpha` |
| 外层选择记录 | linear：1.0, 1.0, 0.01, 1.0, 1.0；quadratic：0.1 ×5 | `model.json.outer_selections` |
| 系数矩阵 | linear 17×13；quadratic 153×13（项名×域） | `linear_coefficients.csv`、`quadratic_coefficients.csv` |
| 训练配比基准 | `reference_p` = 训练集 17 列均值（单纯形质心） | `model.json.reference_p` |
| 截距 | 无（`fit_intercept=False`，单纯形约束下避免共线冗余） | 源码 D03 ③ |

系数矩阵的读法：列是 13 个验证域（`metric/*_val_loss`），行是配比项；导出前已用 `StandardScaler.scale_` 还原到原始配比尺度，因此 `预测 = 配比特征 @ 系数` 可直接复现（本轮验证见 §6）。系数本身数值较大（个别可达 ±6），因为它们同时承担了无截距时的水平项，**不能**按“每单位配比变化带来多少 Loss”的因果口径解读。

## 5. 评价指标

`metrics.csv` 的字段定义（易误读，必须按定义引用）：

| 字段 | 定义 | 备注 |
|---|---|---|
| `rmse_all_domains` / `mae_all_domains` | 对 13×n 全部单元格计算 | 因各域行数相同，等价于“各域 MSE 先算再平均”后的 RMSE |
| `r2_domain_mean` | 对全部单元格做 pooled R² | **名字有歧义**：不是各域 R² 的平均 |
| `rmse_equal_domain_mean` | 先对每行 13 域取平均 Loss，再算 RMSE | 报告 `mixture_baseline.md` 表格用的是这一列 |
| `r2_equal_domain_mean` | 对行均值 Loss 序列算 R² | 同上 |
| `spearman_equal_domain_mean` | 行均值实际 vs 行均值预测的秩相关 | 排序能力 |

主模型（linear）六套结果（`metrics.csv`，本轮全部复算 ①）：

| 集 | role | rmse_all_domains | r2_domain_mean(pooled) | rmse_equal_domain_mean | r2_equal_domain_mean | spearman |
|---|---|---:|---:|---:|---:|---:|
| train_nested_oof | （训练内） | 0.5719770155 | 0.5996965543 | 0.2821840537 | 0.2436868732 | 0.4997154165 |
| train_1m | training_fit | 0.5511714870 | 0.6288523911 | 0.2722748326 | 0.2958718586 | 0.5457052842 |
| test_1m | independent_1m_test | 0.5229481985 | 0.6193057996 | **0.2269777773** | **0.3319216143** | **0.6250743877** |
| test_60m | zero_shot_cross_scale | 1.6185760456 | −7.9136579386 | 1.5173310792 | −47.0562130 | 0.5591496910 |
| test_1B | zero_shot_cross_scale | 3.2522400649 | −808.2272720 | 3.1889453478 | −3768.5169804 | 0.3722985348 |
| est_10b | external_estimate_comparison | 3.6209899136 | −236.8013134 | 3.5804573970 | −1386.7031834 | −0.4536290323 |
| est_70b | external_estimate_comparison | 4.0063353366 | −385.3239899 | 3.9633176997 | −1446.9189632 | −0.5164650538 |

对照：二次族（非主族，事后观察）`test_1m` 0.5189230 / 0.6692304 / **0.1864214666** / **0.5493362933** / **0.7798860**；训练 OOF 为 0.5986579 / 0.5958813 / 0.2608100 / 0.3539218 / 0.6687094。

平凡常数基线 `training_domain_means`（rmse_equal_domain_mean）：test_1m 0.2846150、test_60m 1.5374063、test_1B 3.1195189、est_10b 3.5484997、est_70b 3.9314908。

→ 关键判断：线性模型仅在 **1M** 明显优于常数基线；**60M 仅好 0.02**；**1B、10B、70B 均不如常数基线**。

逐域细节：`domain_metrics.csv`（157 行含表头，即 13 域 × 12 组 = 156 行），逐行预测：`{model}_{set}_predictions.csv`。
不确定性：`test_1m_conditional_intervals.json`（500 次行重采样，linear，95%）：RMSE [0.2049, 0.2466]、R² [0.2155, 0.4329]、Spearman [0.5443, 0.6935]。其 `scope` 字段自述为“固定模型下测试行抽样”，不含族选择、质量映射与跨规模偏差。

## 6. 哪些结果已核验

**① 本轮直接复算（未拟合）**

| 核验项 | 结果 |
|---|---|
| 12 个原始配比/损失文件 SHA256 | 全部与 `audit.json` 一致 |
| 六套行数 512/256/256/64/63/63 | 与 `audit.json`、`metrics.csv` 一致 |
| `metrics.csv` 全部 12 组（2 族 × 6 套）指标 | 由对应 `*_predictions.csv` 复算，最大偏差 **4.5e-13**（六字段 + n 全对） |
| 导出系数 → 预测 | 用 `normalized_mixtures × coefficients` 复算 12 组预测，最大偏差 **1.8e-14** |
| 配方集合关系 | `test_1m`/`test_60m`/`test_1B` 与训练重叠 0；`est_*` 重叠 63/63；`test_1m≡test_60m`、`est_10b≡est_70b` |

数值解析口径：本轮统一以 `pandas.read_csv(..., float_precision='round_trip')` 读取 CSV。pandas 默认 `high` 解析会在末位产生偏差（例：`model_comparison.csv` 中 `0.00014649608992588822` 默认读成 `0.0001464960899258`），因此凡引用高精度数字都应使用 `round_trip`；该口径已记入 `evidence/verification_record.json` 的 `meta`。

**② 恢复轮已核验（`recovery/2026-09-24/verification.json`，本卡未复算）**

- 配比标准化、实际 y、系数预测与指标 6 套 × 2 族 PASS；
- `aggregate_predictions.csv` 与逐行预测一致；
- 64 份既有 JSON/CSV 可读性 PASS。

**③ 仅落盘记录（本卡未复算，可引用但需注明）**

- `model.json` 的族选择结果与外层 alpha 记录；
- `observed_training_reference.json` 的描述性最优行（index=170，mean_loss 4.7534）；
- 条件自助区间的具体数值。

**④ 不可复算（需重新拟合，本卡禁止）**

- `train_nested_oof` 两族的指标：**没有落盘逐行 OOF 预测**，因此“训练 OOF 上线性优于二次、故选中线性”这一决策链无法在不重拟合的前提下独立复现。这是本模块最大的可复现性缺口（登记 MIX-12、MIX-13）。

## 7. 哪些只是探索结果

- 整个配比模块是“首轮探索性基线”，不是定稿模型：等权 13 域目标、岭惩罚网格、单纯形参数化都是分析选择，不是题目给定。
- 族选择（linear）是在训练内完成并可能乐观的探索过程；无独立最终测试集之外的复现记录。
- 二次族在 `test_1m`/`test_60m`/`test_1B` 上更优（如 1M R² 0.5493、Spearman 0.7799）属**事后观察**；D04 明确禁止因此改称“训练选了二次”。若论文要改用二次族，必须重走训练内选择流程。
- `est_10b`/`est_70b` 的全部数字属估算材料对照，只能与同性质材料比较。
- B7/条件自助区间等不确定性刻画是条件性描述，不是全流程不确定性。
- `observed_training_reference.json` 是描述统计：训练集中观测均值最小的一行，不是全局最优配方，也不是独立检验结论。

## 8. 哪些不能用于论文强结论

| 禁止表述 | 原因 |
|---|---|
| “线性系数反映某域占比的因果效应 / 提升某域占比可降低 Loss X” | 单纯形共线 + 无截距条件模型 + 岭收缩；D03。系数只描述该数据集内的条件关联。 |
| “模型可迁移到 60M/1B 尺度” | 1B 的 RMSE 比常数基线更差，R² −3768；60M R² −47。只能表述为“绝对损失迁移失败、排序能力部分保留（60M 0.559、1B 0.372）”。 |
| “模型在 10B/70B 上得到验证” | Loss 为估算值且配方在训练集内（in-sample）。 |
| “已找到全局最优配比” | 未在单纯形上做受约束优化，未引入 Q、p；训练集观测最优行只是描述统计。 |
| “13 域等权平均 Loss 就是题目目标” | 等权是分析选择（报告已声明），非题目事实。 |
| “1M 与 60M 是两次独立检验” | 两者配方字节相同，只是规模不同，不能计为两个独立证据。 |
| “条件自助区间是全流程置信区间” | 区间只覆盖测试行抽样。 |
| “二次族优于线性族” | 事后观察，未经过训练内选择；且训练 OOF 上二次族 pooled MSE 更大。 |

## 9. 已发现的风险

| 风险 | 说明 | 处置建议 |
|---|---|---|
| R1 指标命名歧义（P06） | `r2_domain_mean` 实为 pooled R²；报告表用的是行均值口径。两种运算顺序会给出不同排序。 | 引用时写明“先平均 13 域 Loss，再算 RMSE/R²”，或直接引用 `rmse_equal_domain_mean` 字段名。 |
| R2 OOF 未落盘 | 族选择链不可复现（§6④）。 | 后续重跑时落盘逐行 OOF 与选择轨迹；本文引用时标注“训练内选择、未独立复现”。 |
| R3 证据重复计数 | `test_1m` 与 `test_60m` 同配方；`est_10b`/`est_70b` 同配方。 | 明确“1 个独立检验 + 3 个迁移/估算对照”，不做样本量累加。 |
| R4 估算集自证 | 估算集配方全部在训练集内，Loss 又是估算。 | 只作量级对照，禁止作为验证。 |
| R5 大尺度不如常数 | 1B/10B/70B 上线性模型劣于训练域均值基线。 | 任何跨规模结论必须同时给出该基线。 |
| R6 数据精度 | 原始配比行和 0.996–1.003（最大修正 0.004），损失表小数位有限。 | 归一化已做且不改原表；报告中保留精度说明。 |
| R7 域口径单一 | 13 个域都来自同一 Pythia 验证口径，域等权与题目关心的目标可能不一致。 | 引入域权重向量作为显式参数，做敏感性分析。 |
| R8 Q 通道缺失 | 质量域与配方域缺少可验证映射，域级固定 Q 可能与 p 共线。 | 在进入广义模型前先建立 Q 映射与共线性检验（见 `open_risks.md`）。 |

## 10. 后续进入广义模型 L(N,D,Q,p) 时可复用的接口

**可直接复用的对象**

1. **配比规范化函数**：`raw → 行归一化（和=1，保留零）`，附原始行和修正上限 0.004 的记录（`audit.json`）。
2. **特征映射**：17 维线性项 + 136 个两两交互项（共 153）；`p` 向量即广义模型中 “p 方向” 的自然坐标。
3. **配比→损失块**：`f(p) → 13 维 Loss`，以及 `→ 行均值 Loss` 两种归约；后者是与 N/D/Q 标量律对接的桥。
4. **证据角色标签**：`metrics.csv.role ∈ {training_fit, independent_1m_test, zero_shot_cross_scale, external_estimate_comparison}`，可直接作为广义模型数据分层键。
5. **参照基线**：`training_domain_means` 与 `observed_training_reference`（描述性）作为任何新模型的必报对照。
6. **系数矩阵格式**：`term × domain` CSV，便于与缩放律的 `E/A/B/α/β` 一起组成联合参数对象。

**接入广义模型前必须补齐**

- (i) 一个**域权重向量**：把 13 维输出归约为题目所需的标量目标，并做权重敏感性；
- (ii) **跨规模标定层**：必须在每个目标尺度上有配方不重叠的样本（现有 60M/1B 均失败或共享配方）；
- (iii) **Q 映射**：A 域质量评分 → B 的 `Q_score` 的可检验标定（当前仅有未验证情景）；
- (iv) **p 与 Q 的共线性检验**：域级固定 Q 会与 p 混淆，需先做识别性检查；
- (v) **受限优化接口**：单纯形约束 + 外推可行性标记，供问三调用。

**登记表口径**：`evidence/baseline_result_registry.csv` 每行一条可引用事实，字段为 `result_id, module, item, config_or_model, dataset, data_nature, split_role, n, metric, value, unit, artifact, source_table, verification, verification_method, claim_level, caveat, interface`；`verification` 取 `V1_本轮复算 / V2_恢复轮核验 / V3_仅落盘记录 / V4_不可复算_需重拟合`，`claim_level` 取 `A_可用_附边界 / B_探索性 / C_仅内部参考 / D_禁止用于论文结论`。
