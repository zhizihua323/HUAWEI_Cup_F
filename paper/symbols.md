# 统一符号、单位与命名约定

> 建立时间：2026-09-24。用途：统一四问、正文、代码字段和图表标签。符号定义不等于模型已经完成；`状态` 必须与证据状态一致。
>
> 特别限制：A 表质量分、B 表质量变量和 C 表 Benchmark 不能因名称都含“质量/能力”而直接等价或互换。

## 1. 状态标签

| 状态 | 含义 |
|---|---|
| `GIVEN` | 题目或数据说明直接给出 |
| `DEFINED` | 本队已明确使用的记号，定义可见于现有文件 |
| `BASELINE` | 已有首轮输出，但只在该基线的证据边界内使用 |
| `PARTIAL` | 只完成部分处理，不能作最终结论 |
| `SCENARIO` | 依赖未验证假设的情景量，不能称标定结果 |
| `RESERVED` | 为后续统一而预留，当前没有实现或结果 |
| `COLLISION` | 名称与既有变量冲突，正文禁止继续沿用简称 |

## 2. 题目级核心符号

| 规范符号 | 允许简称/代码字段 | 含义 | 单位/范围 | 状态与依据 |
|---|---|---|---|---|
| `N` | `N` | 模型参数量；成本公式使用实际参数个数 | 参数个数，>0 | `GIVEN`：题目问题三 |
| `N_B` | `N_params_B`, `N_B` | 以十亿为单位的参数量，仅用于 B 表拟合/呈现 | 10^9 参数，>0 | `GIVEN/DEFINED`：`scaling_params.json` 明示单位 |
| `D` | `D` | 训练 token 数；成本公式使用实际 token 数 | token，>0 | `GIVEN`：题目问题三 |
| `D_B` | `D_tokens_B`, `D_B` | 以十亿 token 为单位的训练数据量，仅用于 B 表拟合/呈现 | 10^9 token，>0 | `GIVEN/DEFINED`：`scaling_params.json` 明示单位 |
| `C` | `C` | 总算力预算 | FLOPs，题目建议至少考察三个量级 | `GIVEN`：题目问题三 |
| `C_train` | `Ctrain` | 基础训练算力开销 | FLOPs | `GIVEN`：`C_train = 6ND` |
| `C_Q` | `CQ` | 相对基线质量 `Q_0` 的质量提升增量成本 | FLOPs | `GIVEN`：`C_Q = D[g(Q)-g(Q_0)]_+` |
| `C_attn` | `Cattn` | 长上下文注意力与缓存近似开销 | FLOPs | `GIVEN`：`C_attn = eta N D L_ctx` |
| `Q` | `Q` | 可比较、越高越好的数据质量标量 | 归一化标量；具体范围待统一 | `GIVEN/PARTIAL`：题目要求定义到可比较尺度 |
| `Q_0` | `Q0` | 质量提升前的基线质量 | 与 `Q` 同一尺度 | `GIVEN/RESERVED`：数值尚未冻结 |
| `p` | `p` | 17 个训练领域的数据配比向量 | 单纯形：`p_i >= 0`、`sum_i p_i = 1` | `GIVEN/DEFINED`：A 表为 17 域 |
| `L_ctx` | `Lctx` | 上下文窗口长度，问题三外生给定，不作为内点寻优变量 | 长度单位按题目/C7 原字段 | `GIVEN`：题目问题三 |
| `eta` | `η` | 长文本注意力成本系数 | 题目给定为 `2 x 10^-4` | `GIVEN`：原题问题三；数值来源为题目而非运行结果 |
| `L` | `loss`, `Loss` | 验证集交叉熵损失 | 交叉熵，越低越好 | `GIVEN`：题目问题二 |
| `S_bench` | `Benchmark`, `benchmark_score` | 下游 Benchmark 得分/综合能力指标 | 通常为 0–100，但须按具体数据核验 | `GIVEN/RESERVED`：问题四；禁止使用裸 `B`，因其与标度律系数冲突 |
| `t` | `date`, `time` | 问题四时间轴上的可比时间 | 按提交、发布或版本日期之一统一定义 | `RESERVED`：口径未冻结 |

## 3. 单位硬约束

1. 成本公式 `6ND` 使用实际参数数 `N` 和实际 token 数 `D`。
2. B 表字段若为十亿单位，必须先转换：
   `N = N_B x 10^9`，`D = D_B x 10^9`。
3. 禁止把 `N_B`、`D_B` 直接代入 `6ND` 或 `eta N D L_ctx`。
4. B1 拟合中的 `D_B` 只保留三位小数，换算、预测和误差传播不得隐去该精度限制。
5. 任何图中轴标签必须写明是 `N`、`N_B`、`D` 或 `D_B`，不得只写“规模”。
6. C 表成本若来自公开元数据，另行核实是 FLOPs、GPU-hours 还是估计量，不与 `6ND` 自动等同。

## 4. 经典标度律与 B1 基线符号

题目给定经典形式：

`L(N,D) = E_0 + A_N N^(-alpha_N) + B_D D^(-beta_D)`

| 规范符号 | 输出字段别名 | 含义 | 单位 | 状态 |
|---|---|---|---|---|
| `E_0` | `E` | 不可约损失 | 与 `L` 相同 | `BASELINE`；参数值见结果登记表 |
| `A_N` | `A` | 参数量幂律系数 | 取决于 Loss 与 N 的尺度 | `BASELINE`；参数值见结果登记表 |
| `B_D` | `B` | 数据量幂律系数 | 取决于 Loss 与 D 的尺度 | `BASELINE`；参数值见结果登记表 |
| `alpha_N` | `alpha`, `α` | 参数规模指数 | 无量纲 | `BASELINE`；参数值见结果登记表 |
| `beta_D` | `beta`, `β` | 数据规模指数 | 无量纲 | `BASELINE`；参数值见结果登记表 |
| `k_Q` | `k` | 质量情景中的指数系数 | 取决于所设 Q 尺度 | `SCENARIO`：`UNVALIDATED_SCENARIO_ONLY` |
| `Q_ref` | `Q_ref` | 质量情景参考点 | 与所设 Q 同一尺度 | `SCENARIO`：当前 `0.5` 仅为锚定假设 |

仅允许在明确标记为情景时使用 B6 质量迁移形式：

`L = E_0 + A_N N_B^(-alpha_N) + B_D [D_B exp(k_Q (Q - Q_ref))]^(-beta_D)`。

该式不是已验收的完整 `L(N,D,Q,p)`：其中没有已标定的 `Q_A -> Q` 映射，也没有领域配比 `p`。

## 5. 问题一：质量评价符号

| 规范符号 | 含义 | 状态与限制 |
|---|---|---|
| `i` | 第 `i` 个质量指标/特征，原始字段共 22 个 | `GIVEN/PARTIAL`；原始字段与扩展标量特征不可混称 |
| `r` | 第 `r` 条质量记录 | `DEFINED` |
| `g` | 质量域，A1 含 7 个域，扩展集有 arxiv/github 分支 | `DEFINED` |
| `q_raw[r,i]` | 原始指标值，可能为标量或列表 | `PARTIAL`：列表须先按正式规则压缩为标量 |
| `q_dir[r,i]` | 统一为“越高越好”后的指标值 | `PARTIAL`：方向处理与缺失策略尚未终验 |
| `Q_A` | 由 A 表质量指标形成的综合质量分 | `PARTIAL`：现有汇总存在有效分母未闭合问题 |
| `Q_B` / `Q_score` | B 表质量变量 | `COLLISION`：不得与 `Q_A` 直接等价 |
| `K_conflict` | 冲突判据/冲突强度 | `RESERVED`：冲突定义与阈值尚未最终验收 |
| `R_resolve` | 冲突消解规则 | `RESERVED`：现有分歧诊断不等于消解成功 |

写作要求：先分别报告原始指标、方向转换、标量压缩和聚合层级，再谈综合分。若某条记录因非有限值被排除，必须记录该指标、该域的有效分母和排除规则。

## 6. 问题一：配比模型符号

| 规范符号 | 代码字段/示例 | 含义 | 状态与限制 |
|---|---|---|---|
| `p_i` | `train_the_pile_*` 归一化列 | 第 `i` 个训练领域比例，`i=1,...,17` | `DEFINED` |
| `ell_j(p)` | 13 个验证域 Loss 列 | 第 `j` 个验证域在配比 `p` 下的交叉熵损失 | `DEFINED` |
| `ell_bar(p)` | `mean_loss` 类目标 | 13 个验证域 Loss 的等权域均值 | `DEFINED`；等权是分析选择，不是题目给定事实 |
| `hat ell_j(p)` | 预测列 | 模型对第 `j` 域 Loss 的预测 | `BASELINE` |
| `MSE_j` | `mse` / 域误差 | 第 `j` 验证域均方误差 | `BASELINE` |
| `RMSE_j` | `rmse` | 第 `j` 验证域均方根误差 | `BASELINE` |
| `RMSE_eq` | `rmse_equal_domain_mean` | 逐域 RMSE 的等权平均 | `BASELINE`；不得与“全体样本合并 RMSE”混称 |
| `R2_eq` | `r2_equal_domain_mean` | 逐域 R² 的等权平均 | `BASELINE` |
| `rho_s` | `spearman_equal_domain_mean` | 逐域 Spearman 秩相关的等权平均 | `BASELINE` |

用于首轮线性 Scheffé 基线的形式可写为：

`hat ell_j(p) = sum_i beta_ij p_i`，且 `sum_i p_i = 1`。

若以后使用二次交互项，必须另列系数和模型选择证据；不得把线性/二次结果择优选用来制造“最终模型”。

## 7. 问题二：广义标度律目标

目标规范符号：

`L = L(N, D, Q, p)`

该符号目前是**目标接口**，不是已有模型：

- `N`、`D` 部分有 B1 首轮基线；
- `Q` 只有 A 表的部分质量和 B 表未验证迁移情景；
- `p` 尚未接入标度律；
- 跨 A/B 来源的误差、量纲和独立性尚未完成验证；
- `partial L / partial N`、`partial L / partial D`、`partial L / partial Q` 与相应弹性均不可在完整模型验收前写成最终结果。

## 8. 问题三与问题四预留符号

| 规范符号 | 含义 | 状态 |
|---|---|---|
| `g(Q)` | 三类候选质量成本函数之一 | `GIVEN`，具体参数须回看原题 Word，避免纯文本上标丢失 |
| `x*` | 算力约束下联合配置 `x=(N,D,Q,p)` 的最优解 | `RESERVED` |
| `Delta S_scale` | 规模扩张对能力变化的贡献 | `RESERVED` |
| `Delta S_non-scale` | 非规模技术进步对能力变化的贡献 | `RESERVED` |
| `S_frontier(t+h)` | 未来 `h` 个月的前沿能力 | `RESERVED`，`h` 只能取题目要求的 12 或 24 个月 |
| `U_frontier` | 前沿预测不确定性集合/区间 | `RESERVED` |

没有输出文件时，这些符号只能出现在“模型设计”或“待完成任务”中，不能出现在“结果”中。

## 9. 输出字段到正文符号的映射

| 输出文件 | 输出字段 | 正文规范符号 | 强制说明 |
|---|---|---|---|
| `solution/outputs/scaling/scaling_params.json` | `parameters.E` | `E_0` | 首轮 B1 基线参数 |
| 同上 | `parameters.A` | `A_N` | 不使用裸 `A` 指数据集 |
| 同上 | `parameters.B` | `B_D` | 不使用裸 `B` 指 Benchmark |
| 同上 | `parameters.alpha` | `alpha_N` | 幂指数 |
| 同上 | `parameters.beta` | `beta_D` | 幂指数 |
| `solution/outputs/mixture/metrics.csv` | `rmse_equal_domain_mean` | `RMSE_eq` | 逐域等权，不等同于合并样本 RMSE |
| 同上 | `r2_equal_domain_mean` | `R2_eq` | 逐域等权 |
| 同上 | `spearman_equal_domain_mean` | `rho_s` | 逐域等权 |
| 质量输出 | 多种且暂不统一 | `Q_A` | 必须核对有效分母；不得复用为 `Q_B` |
| 标度情景输出 | `quality_scenario.k` | `k_Q` | 只能标为未验证情景 |

## 10. 命名冲突清单

- 数据编号 `A1–A18`、`B1–B12`、`C1–C10` 与数学系数 `A_N`、`B_D` 必须通过下标或上下文彻底区分。
- `B` 既可能是数据集族，也可能是标度律系数，还可能是 Benchmark；正文统一使用 `B_D` 和 `S_bench`，不写裸 `B`。
- `Q` 至少涉及 A 表质量分、B 表质量变量和问题三决策质量；分别写 `Q_A`、`Q_B/Q_score`、`Q`，禁止互换。
- `D` 是训练 token 数还是验证域编号必须由下标区分；配比验证域写 `j`，数据量写 `D`。
- `L` 是 Loss，问题三上下文长度写 `L_ctx`，不得简写为 `L`。
- `C` 是算力预算，数据编号 C1–C10 仅作数据 ID。
