# TASK-T05 交接：Loss–Benchmark 桥接与历史分层验证

- run_id：`20260925T113355+0800`
- 状态：`COMPLETE_PENDING_CONTROLLER_REVIEW`
- 最终资格：`CONDITIONAL_ASSOCIATION_ONLY`
- 执行边界：只使用 C01/C01-R1 冻结产物及只读 C1–C10；未重跑 C01/C01-R1，未重新解析 1958 个 C8 JSON，未修改旧 run、`evolution_audit.py` 或 00–05。

## 关键结论

1. C8 采用 R1 corrected 表：完整六任务模型 1854，partial 6，损坏 JSON 4。45 个桥接候选均来自完整模型；6 个 partial 与 4 个损坏文件只进入覆盖审计，均未赋分。
2. 主可比层为 C5 High 的 7 个 Pythia 完整模型，Loss 来自同一验证集、同一最终 checkpoint 口径。C6 High 与该 7 行重复，不是独立验证集。
3. C5 是 C6 的 43 行精确值子集；共同列为 `N_params_B`、`D_tokens_B`、`Val_Loss`、六任务 benchmark 与均值，43/43 行、10/10 列一致。32 个 C6 Medium 行不在 C5；C6 Medium 的 Loss 来自不同验证集/报告，只能称来源间迁移。
4. 主桥接内部按模型 ID 分组 5 折交叉验证；非主层使用 C6 扩展条件样本。切点 `2024-09-01` 在查看桥接指标前冻结。
5. 全部主任务内部一标准误选择结果为 `CONSTANT`：没有任何包含 Loss、规模、时间或族结构的候选达到 10% RMSE 改善和 Spearman≥0.5 的可升级门槛。
6. 主可比层的时间外切分为 5 train/2 test，Spearman 无法定义且改善为 0，时间外门槛失败；只有 Pythia 一个模型族，留族升级验证不可识别；主层无 ≥20B 模型，规模外升级验证不可执行。
7. Medium 缺 D 未插值，`logD` 保持缺失；`LOSS_SIZE_LOG_D` 仅作为观测 D 子样本候选，不进入 Medium 主结论。
8. 资格保持 `CONDITIONAL_ASSOCIATION_ONLY`，不是 `IDENTIFIED_PREDICTIVE_BRIDGE`；相关性和残差不得写成因果技术进步。

## 主要数值

| target | selected | internal RMSE | internal Spearman | improvement vs constant | time train/test | eligibility |
|---|---|---:|---:|---:|---|---|
| IFEval | CONSTANT | 2.2281 | -0.2887 | 0.00% | 5/2 | CONDITIONAL_ASSOCIATION_ONLY |
| BBH | CONSTANT | 1.2437 | -0.2887 | 0.00% | 5/2 | CONDITIONAL_ASSOCIATION_ONLY |
| MATH Lvl 5 | CONSTANT | 0.4585 | 0.0000 | 0.00% | 5/2 | CONDITIONAL_ASSOCIATION_ONLY |
| GPQA | CONSTANT | 0.5237 | -0.1443 | 0.00% | 5/2 | CONDITIONAL_ASSOCIATION_ONLY |
| MUSR | CONSTANT | 2.3630 | 0.1443 | 0.00% | 5/2 | CONDITIONAL_ASSOCIATION_ONLY |
| MMLU-PRO | CONSTANT | 0.1342 | -0.2887 | 0.00% | 5/2 | CONDITIONAL_ASSOCIATION_ONLY |
| Mean (auxiliary) | CONSTANT | 0.3232 | -0.2887 | 0.00% | 5/2 | CONDITIONAL_ASSOCIATION_ONLY |

## T08 接口

- `scale_progress`：可用但仅条件性，含 N 观测、D 观测子集和结构选择；不声称因果。
- `non_scale_residual`：可用，仅是条件残差/非规模关联；不得升级为因果技术进步。
- `time_trend`：时间外未通过，`validated_for_extrapolation=false`。
- `benchmark_prediction`：保留六个任务向量，均值只是辅助指标；主层范围限于 C5 High 同验证集定义。
- `uncertainty`：身份、Loss 口径、run 重复、模型误差、外推分开登记。
- `eligibility`：`CONDITIONAL_ASSOCIATION_ONLY`。

## 局限

- C5/C6 没有独立的同一 Loss 定义外部测试集；C6 High 只是重复 C5 High。
- 主可比样本仅 7 个模型，且只有一个模型族，预测桥接识别力不足。
- C6 Medium 的 68 行保留为条件/迁移层，不拼成纵向真值。
- 95 个双文件目录已审计；94 个含有效评测、1 个纯损坏目录。主桥接候选不落在这些目录中。
- 本次没有执行 T08，也没有更新 00–05。