# Q4 GAP 闭合候选冻结

日期：2026-09-25。状态：CANDIDATE_VERIFIED_PENDING_MAIN_CONTROL。run：20260925T195716+0800。

本文件是TASK-G4候选接口，不自行宣布Q4关闭，不修改T05/T08、Loss桥接或旧论文正文。

## 冻结口径

- forecast origin：2025-01-28；12月：2026-01-28；24月：2027-01-28。
- 时间切点：2024-06-19；状态：EVALUABLE。
- 主样本：25个pretrained、开放权重、明确许可且C3/C4/C8身份唯一的模型；任务分数在seal后读取。
- compute优先使用C4直接观测；只有N和D均为观测值时才使用6ND，逐模型保留compute_origin。
- C1只用于C2等价/原字段审计，不把C1/C2作为两批独立观测。
- Family-out与group split可评价；primary scale子集的时间外测试少于10个模型，因此该协议标NOT_EVALUABLE。

## 候选选择

| benchmark | 选择模型 | 扩展门 | 0.90前沿情景模型 | 情景资格 |
|---|---|---|---|---|
| IFEval | M0_CONSTANT | FAIL | M2_SCALE_TIME | SCENARIO_ONLY_UNVALIDATED |
| BBH | M1_SCALE | FAIL | M2_SCALE_TIME | SCENARIO_ONLY_UNVALIDATED |
| MATH Lvl 5 | M1_SCALE | FAIL | M2_SCALE_TIME | SCENARIO_ONLY_UNVALIDATED |
| GPQA | M1_SCALE | FAIL | M2_SCALE_TIME | SCENARIO_ONLY_UNVALIDATED |
| MUSR | M0_CONSTANT | FAIL | M2_SCALE_TIME | SCENARIO_ONLY_UNVALIDATED |
| MMLU-PRO | M1_SCALE | FAIL | M2_SCALE_TIME | SCENARIO_ONLY_UNVALIDATED |
| six_task_mean_complete_only | M1_SCALE | FAIL | M2_SCALE_TIME | SCENARIO_ONLY_UNVALIDATED |

M0/M1/M2均为预注册嵌套规格。M2在六个任务和辅助均值上均未通过冻结升级门槛，因此12/24月结果不是验证预测。

## 规模与非规模关联贡献

| benchmark | 选择模型 | Delta_scale | Delta_non_scale | Delta_fitted | scale share | non-scale share |
|---|---:|---:|---:|---:|---:|---:|
| IFEval | M0_CONSTANT | 0 | 0 | 0 | NOT_DEFINED | NOT_DEFINED |
| BBH | M1_SCALE | 0 | 0 | 0 | NOT_DEFINED | NOT_DEFINED |
| MATH Lvl 5 | M1_SCALE | 0 | 0 | 0 | NOT_DEFINED | NOT_DEFINED |
| GPQA | M1_SCALE | 0 | 0 | 0 | NOT_DEFINED | NOT_DEFINED |
| MUSR | M0_CONSTANT | 0 | 0 | 0 | NOT_DEFINED | NOT_DEFINED |
| MMLU-PRO | M1_SCALE | 0 | 0 | 0 | NOT_DEFINED | NOT_DEFINED |
| six_task_mean_complete_only | M1_SCALE | 0 | 0 | 0 | NOT_DEFINED | NOT_DEFINED |

预注册的+/-365天端点窗口在当前7个月主时间跨度内相互重叠，因此端点scale中心相同，主分解严格为0；比例分母为0时写NOT_DEFINED。该0值是冻结规则下的结果，不解释为规模对能力无作用。

## 12/24个月任务前沿情景

| benchmark | horizon | scenario | prediction points | range-constrained sensitivity | range OOS |
|---|---:|---|---:|---:|---|
| IFEval | 12 | SLOW | 27.002799 | 27.002799 | False |
| IFEval | 24 | SLOW | 26.676006 | 26.676006 | False |
| IFEval | 12 | BASELINE | 27.647843 | 27.647843 | False |
| IFEval | 24 | BASELINE | 27.966093 | 27.966093 | False |
| IFEval | 12 | UPPER_SENSITIVITY | 28.105508 | 28.105508 | False |
| IFEval | 24 | UPPER_SENSITIVITY | 28.881424 | 28.881424 | False |
| BBH | 12 | SLOW | 34.107388 | 34.107388 | False |
| BBH | 24 | SLOW | 23.122995 | 23.122995 | False |
| BBH | 12 | BASELINE | 35.451789 | 35.451789 | False |
| BBH | 24 | BASELINE | 25.811797 | 25.811797 | False |
| BBH | 12 | UPPER_SENSITIVITY | 36.405656 | 36.405656 | False |
| BBH | 24 | UPPER_SENSITIVITY | 27.719532 | 27.719532 | False |
| MATH Lvl 5 | 12 | SLOW | 3.894673 | 3.894673 | False |
| MATH Lvl 5 | 24 | SLOW | -3.971072 | 0.000000 | True |
| MATH Lvl 5 | 12 | BASELINE | 4.913355 | 4.913355 | False |
| MATH Lvl 5 | 24 | BASELINE | -1.933709 | 0.000000 | True |
| MATH Lvl 5 | 12 | UPPER_SENSITIVITY | 5.636120 | 5.636120 | False |
| MATH Lvl 5 | 24 | UPPER_SENSITIVITY | -0.488178 | 0.000000 | True |
| GPQA | 12 | SLOW | 27.124326 | 27.124326 | False |
| GPQA | 24 | SLOW | 22.076170 | 22.076170 | False |
| GPQA | 12 | BASELINE | 27.668664 | 27.668664 | False |
| GPQA | 24 | BASELINE | 23.164847 | 23.164847 | False |
| GPQA | 12 | UPPER_SENSITIVITY | 28.054879 | 28.054879 | False |
| GPQA | 24 | UPPER_SENSITIVITY | 23.937275 | 23.937275 | False |
| MUSR | 12 | SLOW | 32.876304 | 32.876304 | False |
| MUSR | 24 | SLOW | 22.580095 | 22.580095 | False |
| MUSR | 12 | BASELINE | 33.105237 | 33.105237 | False |
| MUSR | 24 | BASELINE | 23.037961 | 23.037961 | False |
| MUSR | 12 | UPPER_SENSITIVITY | 33.267667 | 33.267667 | False |
| MUSR | 24 | UPPER_SENSITIVITY | 23.362822 | 23.362822 | False |
| MMLU-PRO | 12 | SLOW | 17.353537 | 17.353537 | False |
| MMLU-PRO | 24 | SLOW | 4.422898 | 4.422898 | False |
| MMLU-PRO | 12 | BASELINE | 19.145090 | 19.145090 | False |
| MMLU-PRO | 24 | BASELINE | 8.006002 | 8.006002 | False |
| MMLU-PRO | 12 | UPPER_SENSITIVITY | 20.416216 | 20.416216 | False |
| MMLU-PRO | 24 | UPPER_SENSITIVITY | 10.548255 | 10.548255 | False |

辅助综合能力仅用于汇总：

| horizon | scenario | prediction points | range-constrained sensitivity | range OOS |
|---:|---|---:|---:|---|
| 12 | SLOW | 23.511163 | 23.511163 | False |
| 24 | SLOW | 16.214986 | 16.214986 | False |
| 12 | BASELINE | 24.414168 | 24.414168 | False |
| 24 | BASELINE | 18.020997 | 18.020997 | False |
| 12 | UPPER_SENSITIVITY | 25.054860 | 25.054860 | False |
| 24 | UPPER_SENSITIVITY | 19.302381 | 19.302381 | False |

负值或超过100分的原始q90预测未截断；范围约束列只作敏感性。compute未来值均落在训练compute范围内；时间12/24月均为训练时间范围外。不确定性按参数/重采样、模型选择、scenario structure和time extrapolation分列，不合成伪精确CI。

## Loss桥接隔离

T05资格保持CONDITIONAL_ASSOCIATION_ONLY。桥接文件仅作只读敏感性，Loss-to-Benchmark换算次数为0，未参与任何直接Benchmark候选、门槛或情景。

## 限制

- 主样本25个模型、10个族；BBH、MATH Lvl 5、GPQA、MMLU-PRO及辅助均值通过M1 group/family升级门，IFEval与MUSR保持M0。
- Time-out阈值协议在primary scale子集上不可评价，不能称三协议完整验证。
- M2时间项方向不稳定，因此所有数值前沿标SCENARIO_ONLY_UNVALIDATED。
- 量化、Hugging Face镜像共享C4身份和open-weight冲突样本保留在身份审计中，不进入主样本。
- 历史compute增长支持不足，情景来自冻结的1.0/1.5/2.0数学网格而非历史估计。

独立验证文件：verification.json。执行检查：PASS。
