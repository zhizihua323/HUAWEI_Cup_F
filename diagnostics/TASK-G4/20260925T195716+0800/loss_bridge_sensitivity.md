# G4 Loss-Benchmark桥接只读敏感性

生成时间：2026-09-25T20:30:14.391562+08:00

## 资格边界

- 资格：CONDITIONAL_ASSOCIATION_ONLY。
- 本文件不重新运行T05桥接，不重新解析C8 JSON，不重跑Loss模型。
- 桥接只描述前三问Loss与Benchmark的条件联系及误差。
- Loss变化不得换算为Benchmark点数；桥接误差、残差或显著性不得控制G4直接Benchmark候选、门槛或情景。
- 本次Loss-Benchmark数值换算次数为0。

## 冻结来源

- T05 run：diagnostics/TASK-T05/20260925T113355+0800
- 桥接表行数：812
- 主层行数：126；主层模型数：7；模型族数：1
- T05合同资格：CONDITIONAL_ASSOCIATION_ONLY

## 冻结桥接误差（仅条件描述）

| benchmark | n | MAE | RMSE | residual median | eligibility |
|---|---:|---:|---:|---:|---|
| BBH_pct | 18 | 4.18082 | 6.39812 | -1.25673 | CONDITIONAL_ASSOCIATION_ONLY |
| GPQA_pct | 18 | 1.42713 | 2.36129 | 0.099648 | CONDITIONAL_ASSOCIATION_ONLY |
| IFEval_pct | 18 | 7.67128 | 10.14 | -6.95111 | CONDITIONAL_ASSOCIATION_ONLY |
| MATH Lvl 5_pct | 18 | 1.57118 | 2.54809 | -0.113293 | CONDITIONAL_ASSOCIATION_ONLY |
| MMLU-PRO_pct | 18 | 3.95029 | 7.4625 | 0.0635805 | CONDITIONAL_ASSOCIATION_ONLY |
| MUSR_pct | 18 | 2.22844 | 3.06639 | -1.35552 | CONDITIONAL_ASSOCIATION_ONLY |
| benchmark_mean_aux | 18 | 2.67648 | 4.39374 | -0.398486 | CONDITIONAL_ASSOCIATION_ONLY |

## 与G4直接Benchmark模型的隔离

- G4直接模型选择是否使用Loss桥接：False。
- 直接模型使用C2/C1审计、C3时间、C4元数据和C8 corrected任务分数。
- 直接模型的情景预测与贡献分解不引用本文件的预测值或残差。

## 允许与禁止表述

允许：条件关联、桥接误差、来源差异、不可迁移性。

禁止：可靠统一Loss->Benchmark转换、因果技术进度、用桥接残差替代直接Benchmark模型、用Loss下降直接推未来Benchmark点数。
