# TASK-T07：算力约束下资源配置联合优化

日期：2026-09-25。状态：正式执行施工单；本文件只定义后续执行，不授权本轮运行。

## 【任务目标】

在TASK-T06已经冻结的识别边界内，求解不同物理算力预算和科学情景下的资源配置。正式主分析只使用`M0_B1`，质量与配比只通过预注册情景进入。输出必须是“预算×情景”的一组条件最优解及稳健性结论，禁止包装成唯一确定真值。

## 【强制输入】

- `diagnostics/TASK-T06E-INTEGRATE/20260925T110904+08/t07_model_contract.json`
- `diagnostics/TASK-T06E-INTEGRATE/20260925T110904+08/t07_parameter_table.csv`
- `diagnostics/TASK-T06E-INTEGRATE/20260925T110904+08/scenario_registry_filled.csv`
- `diagnostics/TASK-T06E-INTEGRATE/20260925T110904+08/scenario_predictions.parquet`
- `diagnostics/TASK-T06E-INTEGRATE/20260925T110904+08/uncertainty_components.json`
- `diagnostics/TASK-T06E-B/20260925T100306+08/bootstrap/parameter_draws.parquet`
- `diagnostics/TASK-T06E-P/20260925T075729+08/mixture_audit/reference_p_reconciliation.csv`
- A4训练配比归一化表及冻结RegMix线性系数，只读；不得重拟合。
- C7上下文长度候选及审计结论，只读。
- 原题成本公式与附录B参数，以`recovery/2026-09-24/problem_text_from_docx.txt`复核；公式显示异常时必须回看原Word，不能猜测。

所有旧结果及00–05均只读。执行只写`diagnostics/TASK-T07/<run_id>/`。

## 【冻结模型和单位】

正式联合主模型为

`L0(N_B,D_B)=E+A*N_B^(-alpha)+B*D_B^(-beta)`，

其中`N_B,D_B`分别以十亿参数和十亿token计。成本必须先转换为`N=10^9 N_B`、`D=10^9 D_B`：

`C_total=6ND + D[g(Q)-g(Q0)]_+ + eta*N*D*H`，`eta=2e-4`。

禁止把十亿单位直接代入成本。解析登记`H_crit=6/eta=30000`。H是外生情景，不是内点决策变量。

附录B三类质量成本必须原样比较：

- `G_EXP`: `g(Q)=1e7*exp(6Q)`；
- `G_POWER`: `g(Q)=5e9*Q^4`；
- `G_LOG`: `g(Q)=2e9*ln(1+10Q)`。

质量情景使用A侧`Q_baseline`，成本参考点预注册为`Q0=q_A*=0.5695341857475174`。这是成本情景原点，不是A/B标定结果。`Q_C`只按已注册情景作成对敏感性。

## 【预算与外生H】

正式预算冻结为`1e18、1e20、1e22 FLOPs`。每档先做可行性证明；不可行时输出`INFEASIBLE`，不得更换预算。H只取C7已经审计的`2048、4096、8192、32768、131072`；主展示H为2048，其余为敏感性。必须显式标记H跨越30000临界值前后的成本结构。

## 【决策变量资格】

1. `S00_NULL_M0_B1`：只优化N和D。Q、p是模型平坦方向，必须记为`NOT_IDENTIFIED/NOT_OPTIMIZED`，不得把求解器任意返回值称作最优。
2. 质量情景：只在`scenario_registry_filled.csv`已有ID内使用H1–H3、rho、r_B1、add/eff和Q定义；跨源资格始终是`SCENARIO_ONLY`。Q范围限A侧calibration支持，映射后还须满足B6确认支持；超出即OOS，禁止clip。
3. 配比情景：质量固定在参考点。p满足17维非负单纯形，并优先用A4训练配比的凸包参数化`p=sum_m z_m p_m`、`z_m>=0、sum z_m=1`，避免无支持的单纯形顶点。原始全单纯形只可作标记清楚的OOS压力测试。
4. 不允许Q与完整p同时作为独立自由坐标。任何情景若同时请求二者自由变化，检查立即FAIL。
5. S17 B8只有方向冲突，没有可传输的数值反向系数；必须输出`NO_NUMERIC_OPTIMUM`并与k=0、B6情景并列讨论，禁止恢复旧`k=-20`。

## 【有限执行矩阵】

- 21个既有科学`scenario_id`全部保留；在H=2048、三档预算下执行所有数值可用情景，S07/S17保留非数值状态。
- 三类质量成本只对S01主质量参考情景全做；k=0情景的质量成本为不适用。
- 五个H只对S00和S01做全预算敏感性。
- `Q_baseline/Q_C`、add/eff、keep-eta/keep-k、rho、r_B1、tau_p和运输失效均通过既有单因素或极端情景比较；不得执行后添加ID或删掉不利结果。
- 预算、成本函数和H是T07实验维度，不得冒充T06新科学scenario。

## 【数值求解】

- 主坐标为`log(N_B),log(D_B)`；Q使用有界logit坐标；配比凸包使用softmax权重并固定一个基准坐标消除平移冗余。
- 先做确定性粗网格/低差异点全局搜索，再用`scipy.optimize.minimize(method='SLSQP')`局部精修；随机种子`20260930`，所有起点和退出状态落盘。
- 每个配置至少保留最佳20个粗搜索可行点作为局部起点；不得因失败扩大支持域、改目标或换预算。
- 可利用预算等式消去一个变量，但仍须用原三项成本直接复算可行性。
- 可行性容差：`C_total<=C_budget*(1+1e-9)`；单纯形误差`<=1e-10`；支持域不得使用容差掩盖OOS。

## 【KKT、边界与结构转移】

每个数值解必须报告：预算残差、活跃约束、投影梯度/KKT残差、N/D/Q/p边界、粗搜与局部解差异、重复起点一致性和边际收益。结构转移预先定义为下列任一发生：活跃约束集合改变；质量成本份额跨越10%；Q由下界/内点/上界状态切换；p支持集变化；N/D的对数弹性排序交换。只凭数值缓慢变化不得称结构转移。

## 【参数不确定性】

- null主分析使用B1保存的80个整行参数draw，保留参数内协方差。
- 质量情景使用固定种子从B1整行draw和B6整行draw分别抽取200个条件组合；不得逐参数独立抽样，不得把跨源组合称为联合后验。
- 每个draw重新求解或用经误差证明的局部近似；报告配置与Loss的2.5/50/97.5分位、边界概率和情景失效比例。
- 结构不确定性保持分层：k=0、B6、B8方向冲突、add/eff、bridge、RegMix运输不得混成单一置信区间或赋予主观概率。

## 【必须输出】

- `run_summary.json`、`environment.json`、`input_manifest.json`、`command_log.json`、`stage_status.jsonl`
- `config/budgets.csv`、`config/optimization_matrix.csv`、`config/cost_functions.json`
- `feasibility_audit.csv`、`unit_conversion_audit.csv`
- `optimization_results.parquet`与论文表`budget_scenario_optima.csv`，至少含：budget、scenario、N、D、Q、p状态、H、predicted Loss、三项compute、boundary、support、marginal gain、uncertainty标签
- `solver_multistart.csv`、`kkt_boundary_checks.csv`、`marginal_returns.csv`
- `structural_transition_diagnostics.csv`、`support_oos_audit.csv`
- `parameter_draw_optima.parquet`、`uncertainty_summary.csv`
- `quality_cost_sensitivity.csv`、`context_sensitivity.csv`、`transport_failure_sensitivity.csv`
- `t08_or_paper_interface.json`、`handoff.md`、`checks.json`、`verification.json`
- `code/`、`code_snapshot/`、最后生成的`output_manifest.json`

## 【独立验证】

独立verifier不得导入执行模块。它须从输出解和冻结合同独立复算Loss、三项成本、预算可行性、支持状态、单纯形、S00解析一阶条件或高精度数值对照、至少三档预算、H临界值、三类g、21个scenario ID完整性、S17无数值、Q/p不联合自由、draw整行抽样和manifest。关键检查不得`NOT_CHECKED`。

## 【失败与停止条件】

发现单位不清、合同/manifest变化、成本公式与原题不符、Q/p被同时自由优化、S17被数值化、旧k=-20出现、质量或配比情景被称为统一识别效应、求解器靠放宽支持取得“更优”结果、或需要重拟合T06/RegMix时立即停止。执行结束只交主控验收，不启动T08或改写论文最终结论。

