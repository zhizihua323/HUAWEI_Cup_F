# TASK-T06E：来源内缩放律与质量条件关系验证、尺度桥接情景及T07接口

日期：2026-09-25  
状态：正式执行总施工单；仅授权后续分别执行`TASK-T06E-B`和`TASK-T06E-P`，本文件生成时不执行。  
唯一上位方法文件：`tasks/TASK-T06_尺度桥接识别性与广义缩放律方法裁决.md`。本施工单与其他历史设计、旧代码或旧报告冲突时，以上位方法文件为准。

## 【总任务目标】

在不改动既有质量、缩放律和配比产物的前提下，形成两个可以独立并行执行、互不共享写入的证据分支：

- `TASK-T06E-B`：验证B1来源内基础缩放律；在B6上对`MQ-add`做确认性验证；将`MQ-eff`固定为敏感性；用B7新增点做冻结模型的同源扩展；用B8做共同支持与支持外的冲突压力测试；给出参数识别性和条件不确定性。
- `TASK-T06E-P`：从T03E接口构造冻结的A侧锚点与H0–H4桥接情景；审计既有RegMix线性配比接口、跨尺度运输、p–Q双重计数；在执行前冻结有限的scenario registry；交回T07情景侧候选接口。

两个分支只交付各自的候选接口与证据，不自行拼接联合模型，不自行宣布跨来源质量效应成立。最后的`TASK-T06E-INTEGRATE`只供后续主控只读验收和集成裁决使用。

工程完成与科学候选通过必须分开登记。`MQ-add`被拒绝、A/B桥接继续`NOT_IDENTIFIABLE`、联合主模型保持`M0_B1`，均可构成合格的任务结果。

## 【冻结的总方法决定】

1. 联合主模型默认且始终为`primary_model=M0_B1`、`quality_enabled=false`、`mixture_transport_enabled=false`。
2. B6主质量候选固定为`MQ-add`；其null固定为`M0,6`。`MQ-eff`只作敏感性，不得在`MQ-add`失败后接替主候选。
3. G1–G4严格使用上位T06裁决的门槛，禁止移动、改名、改分母或选择性报告。
4. 正式A侧质量为`Q_baseline`；`Q_C`只作敏感性。不存在已估计的A/B质量映射。旧`Q_ref=0.5`只能保留为历史旧情景，不能恢复为标定结果。
5. B7的360个B6重复点不进入训练、bootstrap或测试分母；新增90点只预测，不调参。
6. B8不与B6合并；共同支持和支持外分别压力测试；旧`k=-20`边界解不得进入参数表或T07接口。B8方向、B6方向和`k=0`必须并列保存。
7. RegMix既有linear模型冻结；不得因测试结果重选quadratic。1M是部署测试，60M/1B是跨尺度迁移，10B/70B是估算情景、不是验证真值。
8. `Mfull`不得联合重新拟合`rho_Q`、`tau_p`、`r_B1`或映射`h`；只生成来源和假设明确的有限情景。
9. B6关系即使通过，也只能称“B6来源内已验证的条件关系”。一旦跨接B1或A侧Q，仍须标记`SCENARIO_ONLY`。
10. 不以p值、训练R²、最好看的图或最低的情景Loss作为模型升级依据。

## 【并行隔离与共同只读边界】

### 输出目录

- B分支只写：`diagnostics/TASK-T06E-B/<run_id>/`
- P分支只写：`diagnostics/TASK-T06E-P/<run_id>/`
- 后续主控集成只写：`diagnostics/TASK-T06E-INTEGRATE/<run_id>/`

`run_id`必须是实际启动时间，格式为`YYYYMMDDTHHMMSS+08`；若目录已存在必须非零退出，禁止覆盖。失败run原样保留，并与正式run明确区分。

### 分支独立性

1. 两个执行AI不得读取对方新建的run目录，不得等待或消费对方的中间结果。
2. 两分支不得写共享源码目录。全部新增执行代码、配置、测试、临时文件和源码快照必须放在本分支run目录内的`code/`、`config/`、`tmp/`、`code_snapshot/`等子目录。
3. 两分支共同使用的上位T06文件及00–05文档均只读，并在各自`input_manifest.json`中登记同一个T06文件SHA256。
4. P分支的情景接口必须用参数槽位和来源标签表示尚未取得的B分支结果，不得提前读取B分支或复制其参数。最终数值拼接由主控集成完成。
5. 两分支不得修改`00_PROJECT_BRIEF.md`至`05_REVIEW_LOG.md`、`tasks/`下施工单、任何旧run或任何`solution/outputs/`产物。

### 全局禁止事项

- 不修改、覆盖、重命名或删除`solution/outputs/scaling/`、`solution/outputs/mixture/`、T03E/Q01C正式run及其旧run。
- 不修改现有主Q、Q_C公式、19条缺失记录处理或T03E冻结阈值。
- 不读取、扫描、解压或重算真实A1–A3；P分支只能读取冻结的T03E接口。
- 不启动T07，不输出“最优预算配置”，不修改成本函数，不生成最终联合主模型。
- 不把B7重复点当独立证据，不把B8并入B6，不把A12–A15估算Loss当真值。
- 不创建未在执行前scenario registry登记的情景，不删除结果不利的已登记情景。

---

# A. TASK-T06E-B

## 【任务名称】

B1/B6/B7/B8来源内缩放律、质量条件关系、冲突压力和参数识别性验证。

## 【输入】

### 必须读取

- 上位方法与项目口径：
  - `tasks/TASK-T06_尺度桥接识别性与广义缩放律方法裁决.md`
  - `00_PROJECT_BRIEF.md`至`05_REVIEW_LOG.md`
  - `tmp/environment_review/数据说明.txt`
- 原始B侧表，只读：
  - `F题/real_attachments/B_scaling_laws/pythia_training_log_existing.csv`（B1）
  - `F题/real_attachments/B_scaling_laws/supplementary_NQ_experiment.csv`（B6）
  - `F题/real_attachments/B_scaling_laws/supplementary_NQ_experiment_expanded.csv`（B7）
  - `F题/real_attachments/B_scaling_laws/supplementary_NQ_experiment_large.csv`（B8）
- 既有缩放律结果，只读：
  - `solution/outputs/scaling/scaling_params.json`
  - `model_comparison.csv`
  - `quality_audit.json`
  - `quality_B6_validation.csv`
  - `quality_within_ND_slopes.csv`
  - `quality_scenario_predictions.csv`
  - `external_validation.csv`
  - `validation_by_model.csv`
  - `bootstrap_parameters.csv`或该目录中实际存在的对应80次B1参数文件
  - `solution/reports/scaling_baseline.md`

### 可选只读验证输入

- B2、B4、B5：只作冻结B1模型的迁移验证。
- B3、B10：只作插值/估算一致性对照，不作为真值。
- B9、B11、B12：只作范围、模型族或检查点元数据，不拟合质量参数。

### 输入前置锚点

正式计算前必须确认并写入`input_audit.json`：

- B1为1176行、8个N规模；单位为十亿参数/十亿token。
- B6为360行、9个N、5个D、8个唯一Q水平、45个N-D组；Q水平应为`{0.1,0.2,0.3,0.4,0.6,0.8,0.9,1.0}`。
- B6冻结训练支持`Q<=0.6`应有225行；高Q压力集`Q>0.6`应有135行。
- B7为450行；按精确键`(N_params_B,D_tokens_B,Q_score)`与B6比较应有360个重复键和90个新增键。重复键还须比较Loss是否一致。
- B8为1704行、150个N-D组；与B6的共同`(N,D,Q)`键按既有审计应为160个。

任一锚点不符，必须在读取到差异后停止，不得临时改分母或继续拟合。

## 【输出目录】

仅写`diagnostics/TASK-T06E-B/<run_id>/`。至少建立：

- `code/`、`config/`、`code_snapshot/`
- `fit/`、`validation/`、`profiles/`、`bootstrap/`
- `b7_extension/`、`b8_stress/`、`verification/`

## 【允许修改】

仅允许新建和修改本分支run目录内的文件。运行代码必须随run保存，不得写回`solution/src/`或旧输出目录。可以在本分支内缓存经过输入manifest绑定的只读表副本，但不得改动内容或以缓存替代来源登记。

## 【禁止项】

- 不读取A侧T03E接口、A1–A17或RegMix产物；本分支不做A/B桥接和配比审计。
- 不重新比较并选择B1的四种历史配置；基础配置固定为`point__linear`。
- 不用B2/B4/B5/B7/B8选择模型、调整边界或调参。
- 不对B6与B8联合拟合；不估计统一正负质量参数。
- 不把相邻检查点或B6的360行当作360个独立实验做逐行bootstrap。
- 不对输出Loss做clip来掩盖负预测或模型失效。

## 【冻结模型】

记`N,D`均使用十亿单位，`q*=0.6`。

1. `M0_B1`及`M0,6`：
   `L=E+A*N^(-alpha)+B*D^(-beta)`。
2. `MQ-add`，唯一B6主候选：
   `L=M0,6-k_add*(Q-0.6)`，`k_add>=0`。
3. `MQ-eff`，仅敏感性：
   `L=E+A*N^(-alpha)+B*D^(-beta)*exp[-eta*(Q-0.6)]`，`eta>=0`，派生`k_eff=eta/beta`。
4. 组内方向诊断使用不带符号约束的组内去均值斜率；不得用`k_add>=0`约束后的拟合结果自证G1/G3方向。
5. 只允许一个交互诊断：`(Q-Qbar_g)`、其与`log(N/N*)`、`log(D/D*)`的乘积；`N*、D*`为冻结训练支持的几何均值。两个交互只诊断，不能加入主候选或T07参数。

## 【随机种子】

- B6 N簇bootstrap抽样唯一基础种子：`20260925`，使用`numpy.random.Generator(PCG64)`。
- 优化多起点唯一基础种子：`20260926`，使用`scipy.stats.qmc.Sobol(scramble=True)`。
- 稳定派生规则：模型offset为`M0=0`、`MQ-add=100000`、`MQ-eff=200000`；阶段offset为`full=0`、`leave_N=10000`、`leave_D=20000`、`bootstrap=30000`、`profile=40000`；再加按升序冻结的fold或replicate编号。实际seed逐项写入CSV。
- 禁止使用Python进程随机hash派生seed，禁止失败后换seed。

## 【求解器与版本】

执行环境必须记录并优先固定为：Python 3.13.9、NumPy 2.3.5、SciPy 1.16.3、pandas 2.3.3、pyarrow 21.0.0。若SciPy主/次版本不是1.16，或`least_squares`行为无法按本施工单实现，停止交主控，不得更换求解器后继续。

非线性拟合统一使用`scipy.optimize.least_squares`：

- `method='trf'`
- `loss='linear'`
- `jac='3-point'`
- `x_scale=1.0`
- `ftol=xtol=gtol=1e-12`
- `max_nfev=100000`
- 全部数值使用IEEE float64

目标函数是本节冻结的加权平方残差；不得换成Huber/soft-L1、点加权之外的历史配置或执行后选出的损失函数。

## 【参数变换、优化坐标与边界】

每个训练折单独定义`L*=median(y_train)`和`s_y=max(IQR(y_train),1e-8)`；二者仅用于数值坐标/残差尺度，必须保存。所有Loss必须为有限正数，否则停止。

- `E=L*exp(u_E)`，`A=L*exp(u_A)`，`B=L*exp(u_B)`。
- `alpha=exp(u_alpha)`，`beta=exp(u_beta)`。
- `k_add=L*exp(u_k)`；`eta=exp(u_eta)`。
- E/A/B/k的比例边界为`[1e-8,1e3]*L*`。
- alpha/beta边界为`[1e-4,4]`。
- eta边界为`[1e-6,50]`。
- `k=0`只通过独立null或profile端点表示，不用`log(0)`，也不以极小正值冒充null。

B6拟合按N-D组等权：对组g中每行使用`w_i=1/n_g`，再将全部权重归一化为和1，残差为`sqrt(w_i)*(prediction-y_i)/s_y`。B1保持D09/D10的逐点等权，残差为`(prediction-y_i)/s_y`。这些权重同时进入目标、Jacobian和验证指标的对应宏/微口径，禁止混用。

## 【有限多起点】

- 完整训练和每个确认性fold：变换坐标的中心点，加32个Sobol点，共33个起点。
- 每个bootstrap replicate：中心点加8个Sobol点，共9个起点。
- 每个profile固定点对剩余参数再优化：中心点加8个Sobol点，共9个起点。
- Sobol点只映射到每个变换坐标边界内部的`[5%,95%]`区间，不从边界启动。
- 选择有限目标值最小的收敛解；保存所有起点、终值、状态、nfev和目标差。若同一任务没有任何收敛有限解，标记FAIL，不扩大边界、增加起点或更换算法。

## 【Jacobian、秩和条件数】

G4只能在上述统一变换坐标和目标残差上判断：

1. 在最优解处计算`J=dr/du`；`r`包含冻结权重和`s_y`尺度。
2. 每列按其L2范数缩放：`Jc=J*diag(1/||J_j||_2)`。若任一列范数为0或非有限，直接判秩失败。
3. 对`Jc`做SVD。有效秩阈值固定为`singular_value/s_max>1e-8`；必须满列秩。
4. 条件数固定为`cond=s_max/s_min`，要求`cond<1e8`。
5. 不得在原始量纲参数Jacobian上计算条件数后与门槛比较；不得按模型结果另选列缩放。

## 【profile设置】

对最终冻结训练支持上的M0,6、MQ-add和MQ-eff分别执行profile；B1五参数也须审计既有点估计的profile可辨识性。

- 对每个正参数，在其上述固定变换边界上取41个等距变换坐标点，并额外加入全局最优点；去重后升序。
- `k_add`和`eta`另加0端点；0端点固定该质量模块为null含义，剩余参数重新优化。
- 每个profile点用9个冻结多起点重优化其余参数。
- 以`SSE_min+3.841458820694124*sigma_hat^2`定义描述性profile集合，其中`sigma_hat^2=SSE_min/(n-rank)`；它只用于可辨识性诊断，不是模型选择p值。
- 若该集合触及任一固定硬边界、存在不可分离多极小值，或profile计算未覆盖全部冻结网格，则标记`WEAKLY_IDENTIFIED/UNBOUNDED_PROFILE`，不得扩大边界后追求有界。
- profile总拟合尝试上限按预定义网格自然确定；不得执行后补点。任何跳过点及原因必须逐项保存。

## 【validation splits】

### B1

- 基础拟合只用B1。
- leave-model-size-out：按8个唯一N整组留一。
- late-token：每条N轨迹按D升序，前`floor(0.8*n)`训练，后续记录测试；并保存每条轨迹边界。
- B2/B4/B5只在B1模型冻结后预测；B3/B10只作插值/估算对照。

### B6确认性支持

所有G1–G4模型选择、参数冻结和bootstrap只使用`Q<=0.6`的225行。`Q>0.6`的135行在模型及参数完全冻结后才允许首次进入压力预测，不参与模型选择、边界、初值、profile、bootstrap或任何调优。

- leave-N：9折；每折测试一个完整N的全部D与`Q<=0.6`行，预期每折测试25行、训练200行。
- leave-D：5折；每折测试一个完整D的全部N与`Q<=0.6`行，预期每折测试45行、训练180行。
- 每个fold的`M0,6`与`MQ-add`必须使用逐键完全相同的训练和测试集合；通过`validation_splits.csv`的key hash和集合相等检查证明。
- 主分数为各fold RMSE等权平均，同时报告pooled RMSE；bias统一为`prediction-actual`。
- Q高端压力只报告冻结模型的RMSE、MAE、bias、Spearman、支持状态与逐N/D表现，不反馈选择。

### G1–G4冻结门槛

- G1：在`Q<=0.6`支持内，45个N-D组分别用无符号约束线性斜率；至少80%为负。零斜率、不可估计组和实际分母单列；不可估计组不从分母静默删除。
- G2：相对完全同折的`M0,6`，leave-N和leave-D的宏平均RMSE各至少改善5%；且leave-N至少8/9折、leave-D至少4/5折满足`RMSE_MQadd<=1.10*RMSE_M0`。对照RMSE为0时该折为`NOT_COMPARABLE`并使G2不能通过，禁止添加epsilon。
- G3：200次按完整N水平簇重采样，簇内保留D/Q结构；至少190次拟合数值成功，成功样本中至少`ceil(0.90*n_success)`次给出负向的组内无符号约束斜率。重复抽中的N按抽样重数加权，不能伪装成新N身份。条件稳定性只代表9个N簇。
- G4：支持内预测全部有限且非负；无参数触碰固定优化边界；变换并列缩放后的Jacobian满列秩且条件数<1e8；多起点、联合bootstrap与profile均须报告。若预测通过但profile无界或存在不可分离最优解，只能标记来源内预测器`WEAKLY_IDENTIFIED`，结构参数不得进入T07的identified栏。

四项必须逐项产生`PASS/FAIL`。`MQ-add`只有四项全PASS才可登记`ACCEPT_B6_SOURCE_RELATION`；否则登记`REJECT_TO_M0_6`。`MQ-eff`运行相同数据切分和诊断，但永远只标`sensitivity`，不得获得替代主候选的状态。

## 【B7和B8协议】

### B7

先以精确键和逐列值重建重叠清单。360重复点只用于证明重复，不进入任何预测分母。90新增点在B6模型及全部选择状态冻结后预测，输出模型分别为M0,6、MQ-add及MQ-eff敏感性。B7结果不得改变`MQ-add`的accept/reject。

### B8

- 不拟合统一质量模型，不复用或传播旧`k=-20`。
- 按B6精确`(N,D,Q)`网格将B8划分为共同支持与支持外；共同支持必须再与B6真实行一一对照。
- 对冻结B6模型分别报告两部分的RMSE、MAE、bias、方向违背率、逐N-D组斜率与OOS原因。
- B8正方向、B6负方向和`k=0`三类证据并列进入B分支T07候选合同；不平均、不赋概率。
- B8仅能形成`CONFLICT_EVIDENCE`或`OUT_OF_SUPPORT_STRESS`，不能形成跨来源质量参数。

## 【参数不确定性】

- B1：只读复核既有80次按完整模型轨迹的bootstrap；其来源标签固定为`EXISTING_8_CLUSTER_CONDITIONAL`。若需复算参数预测一致性，可用冻结代码，但不得把1176点逐行重采样。
- B6：保存200次N簇bootstrap中所有成功和失败replicate；成功参数以joint draw保留，报告2.5%、50%、97.5%描述分位，但明确是9个N簇条件不确定性。
- 参数不确定性、模型结构差异、B8冲突和跨源运输情景不得合成一个统计置信区间。

## 【必须输出】

正式B分支run至少包含：

- `handoff.md`、`run_summary.json`、`environment.json`、`command_log.json`、`stage_status.jsonl`
- `input_manifest.json`、`input_audit.json`、`freeze_manifest.json`
- `config/solver_config.json`、`config/model_registry.json`
- `validation/validation_splits.csv`、`validation/candidate_comparison.csv`、`validation/validation_by_group.csv`
- `fit/scaling_parameters_by_source.csv`、`fit/full_fit_predictions.parquet`、`fit/multistart_results.csv`
- `validation/within_ND_quality_effects.csv`、`validation/interaction_diagnostics.csv`、`validation/high_Q_stress.csv`
- `profiles/profile_grid.csv`、`profiles/profile_summary.csv`、`profiles/jacobian_diagnostics.csv`
- `bootstrap/parameter_draws.parquet`、`bootstrap/bootstrap_summary.csv`
- `b7_extension/b7_overlap_audit.csv`、`b7_extension/b7_new90_predictions.csv`
- `b8_stress/b8_support_partition.csv`、`b8_stress/b8_stress_metrics.csv`、`b8_stress/b8_group_slopes.csv`
- `identifiability_matrix_B.csv`、`uncertainty_components_B.json`
- `t07_bside_contract_candidate.json`
- `checks.json`、`verification.json`、`changes.csv`
- `code/`、`code_snapshot/`、`output_manifest.json`

所有CSV/JSON必须记录模型、来源、data role、支持状态、分母及单位；不得只在handoff写结论。

## 【B分支checks】

至少逐项检查：输入哈希与上位方法哈希、上述行数/网格锚点、B1单位、B6训练/高Q隔离、M0/MQ逐折键完全相同、G1–G4精确阈值、无测试反馈、200次bootstrap seed与成功数、Jacobian坐标/列缩放、profile覆盖、多起点数量、B7 360/90隔离、B8共同支持/支持外隔离、旧k=-20未传播、B2/B4/B5未调参、B3/B10未作真值、全部旧产物只读、分支目录隔离、最终manifest一致。

新产生的关键检查不得使用`NOT_CHECKED`或`NOT_VERIFIABLE`；缺证据即FAIL。历史数据来源真实性、跨来源因果性等本来不可验证的限制应进入`limitations`，不能伪造成工程PASS。

## 【B分支独立verifier】

独立verifier必须位于本分支`verification/`，不得导入拟合模块来同时生成actual和expected。至少独立完成：

- 从原始B表重建行数、唯一网格、B6/B7/B8重叠和validation keys；
- 用保存参数直接重写三种公式并复算全部冻结预测及指标；
- 从逐折预测独立复算G1–G4，不读取执行器给出的最终PASS作为期望；
- 从保存Jacobian或独立有限差分复算列缩放、SVD秩和条件数；
- 检查bootstrap seed、N簇身份和Q>0.6零参与；
- 检查B7/B8分母、参数来源标签和禁止的旧k；
- 核验文件冻结顺序、代码快照及manifest。

verifier可以核验拟合结果，但不得重选模型、换solver或扩大profile。若执行器和verifier不一致，正式状态为FAIL并保留两者证据。

## 【B分支manifest】

所有命令、日志、summary、checks、verification和code snapshot先冻结，最后生成`output_manifest.json`；manifest自身可不登记。生成后不得改写任何已登记文件。最终只能做不落盘的只读核验；若需要保存修正，必须创建新的run，不能改正式run。

## 【B分支停止条件】

出现下列任一情况立即停止并保存失败证据：

- 输入锚点、单位、哈希或来源角色不符；
- 需要改变模型、G1–G4门槛、Q训练边界、求解器、参数边界或profile网格；
- Q>0.6、B7或B8进入模型选择/调参；
- M0与MQ折键不同，或B7重复点进入任何分母；
- optimizer无有限收敛解且需要增加起点/扩大边界；
- 旧产物发生变化，或进程尝试写P分支/集成目录；
- 任何代码尝试联合估计A/B映射、rho_Q、tau_p、r_B1或h；
- manifest生成后需要修改登记文件。

完成全部证据后状态只能写`COMPLETE_PENDING_CONTROLLER_REVIEW`，随后停止，不启动P分支、集成或T07。

---

# B. TASK-T06E-P

## 【任务名称】

T03E质量锚点、A/B桥接情景、冻结RegMix接口、跨尺度运输和p–Q识别性审计。

## 【输入】

### 必须读取

- `tasks/TASK-T06_尺度桥接识别性与广义缩放律方法裁决.md`
- `00_PROJECT_BRIEF.md`至`05_REVIEW_LOG.md`
- T03E正式只读接口：
  - `diagnostics/TASK-T03E/20260925T020032+08/t06_quality_interface.parquet`
  - `t06_quality_interface.json`
  - `handoff.md`
  - `freeze_manifest.json`、`output_manifest.json`及与接口直接有关的检查/验证文件
- B6原始表，只允许读取`Q_score`设计水平、N-D-Q键和来源标签，用于H3 B侧经验CDF；不得在P分支拟合Loss。
- 既有RegMix产物，只读：`solution/outputs/mixture/`中的`model.json`、`audit.json`、`metrics.csv`、17域归一化配比、线性系数、各尺度线性预测、训练参考与条件区间，以及`solution/reports/mixture_baseline.md`。
- A4–A17原始或登记表，只读，用于索引、配比、Loss、映射和来源角色复核。A12–A15只核对估算身份。
- `tmp/environment_review/数据说明.txt`、A16映射、A17汇总及03数据登记。

严禁读取A1–A3真实压缩文件。T03E Parquet是唯一A侧行级质量输入。

## 【输出目录】

仅写`diagnostics/TASK-T06E-P/<run_id>/`。至少建立：

- `code/`、`config/`、`code_snapshot/`
- `quality_anchor/`、`bridge/`、`mixture_audit/`
- `scenario_registry/`、`t07_candidate/`、`verification/`

## 【允许修改】

仅允许本分支run目录。可以生成只含接口所需字段的派生表、CDF阶梯、配比审计和符号参数槽位，不得回写T03E或RegMix。

## 【禁止项】

- 不拟合任何B1/B6/B7/B8模型，不读取B分支run，不估计B侧新参数。
- 不用A1 holdout、extension overlap/new估计`q_A*`、CDF、映射或情景参数。
- 不重拟合RegMix linear，不重新选择alpha，不因1M/60M/1B结果切换quadratic。
- 不估计`rho_Q`、`tau_p`、`r_B1`、H2斜率或H3形状；不做情景间“最优”选择。
- 不对11个未映射域填质量，不对6个映射域重新归一化后冒充17域总体。
- 不把`Q_mix=p^Tq`加入已含完整p的模型并解释为独立质量效应。

## 【q_A*精确定义】

从T03E接口严格筛选：

- `evaluation_role == 'A1_calibration'`
- `is_unique_first == True`
- `Q_valid == True`
- `Q_baseline`有限

精确域集合必须为：`arxiv, book, c4, commoncrawl, github, stackexchange, wikipedia`。先在每个域内计算未加权算术均值`mu_d=mean(Q_baseline)`，再计算：

`q_A*=(1/7)*sum_d mu_d`。

不得直接对全部文档求总体均值，不得按域样本量加权，不得使用Q_C重算锚点。必须输出每域`n_total/n_selected/n_Q_valid/mu_d`、七域集合检查和等权贡献。少任何一域、出现额外未裁决域、某域没有有限值或筛选口径不能复算，立即停止；不得临时改权、并域或回退全局均值。按正式接口预期筛选总数为40930；若不同则停止核验。

## 【H3 empirical CDF精确定义】

### A侧七域等权经验CDF

只用上述q_A*相同筛选集合。对每个域d：

`F_d(q)=n_d^(-1)*sum_i I(Q_baseline_di <= q)`。

定义七域等权右连续CDF：

`F_A(q)=(1/7)*sum_d F_d(q)`。

比较采用IEEE float64原值与`<=`；排序必须稳定并保留并列值。每个域总质量恰为1/7，因此不能把所有文档直接拼接成样本量加权CDF。Q_C敏感性也使用同一个由Q_baseline calibration冻结的`F_A`，不得另建Q_C CDF。

### B6唯一设计水平CDF

从B6读取有限`Q_score`，去除N-D网格重复后取得升序唯一水平`b_1<...<b_m`。预期`m=8`，每个唯一水平权重严格为`1/m`：

`F_B(x)=m^(-1)*sum_j I(b_j <= x)`。

不得因同一Q在多个N-D格出现而重复加权。广义逆固定为：

`F_B^{-1}(u)=inf{x: F_B(x)>=u}`；实现为`b_[max(1,ceil(m*u))]`，下标从1开始。仅为实现边界，`u=0`返回`b_1`，`u=1`返回`b_m`。

H3为`h(q)=F_B^{-1}(F_A(q))`。A侧q若低于/高于冻结Q_baseline calibration全体经验最小/最大值，标记`OUT_OF_SUPPORT`且不静默截断；恰在边界可映射。必须输出CDF台阶表、并列处理、域权重和逐值映射。H3是`SCENARIO_ONLY`，CDF可复算不等于跨源对应关系已识别。

## 【H0–H4桥接资格】

|桥接|执行定义|资格|
|---|---|---|
|H0|`k=0`，不调用映射|`IDENTIFIED_NULL_BASELINE`，只表示不接入质量效应|
|H1|`h(q)=q`|`SCENARIO_ONLY`|
|H2|`h(q)=0.6+b*(q-q_A*)`，`b∈{0.5,1,2}`|`SCENARIO_ONLY`|
|H3|上述七域等权CDF到B6唯一Q水平的广义逆|`SCENARIO_ONLY`|
|H4|只保留B6方向，不产生A侧数值收益|`DIRECTION_ONLY_NOT_OPTIMIZABLE`|

不得将H1–H4中的任何一个标为estimated/calibrated/identified。`r_B1∈{0.2,0.6,0.9}`、`rho_Q∈{0,0.5,1}`和`tau_p∈{0,0.5,1}`均是固定情景；`tau_p=-1`仅为失败压力。旧0.5不进入正式r_B1集合。

## 【随机种子】

P分支基础种子登记为`20260927`。正式协议没有随机重采样或参数优化，结果应完全确定；若执行器需要随机抽样做展示或抽查，必须改为固定键排序后的确定性抽查，不能实际消费随机数。seed只作为“不应发生随机行为”的审计锚点。

## 【求解器与版本】

本分支`solver=NONE`，禁止非线性拟合、超参数搜索和随机优化。执行环境记录并冻结为Python 3.13.9、NumPy 2.3.5、pandas 2.3.3、pyarrow 21.0.0；线性代数审计只用`numpy.linalg.svd`。版本不符时停止交主控，不得因便利重拟合旧模型。

## 【参数变换】

- 无待优化参数，因此优化坐标、正参数变换均为`NOT_APPLICABLE_BY_DESIGN`。
- p保留17维原始单纯形坐标、原列顺序和零值；只允许按既有规则逐行除以行和复算旧归一化，不加CLR伪计数、不做ILR或重新建模。
- `Delta_p(p)=f_bar(p)-f_bar(p0)`，其中f_bar固定为13个验证域线性预测等权均值；p0必须从A4归一化训练配比独立复算并与`model.json.reference_p`逐项核对，不能由测试集重定义。
- 质量桥接只按H表作代数变换；不得学习斜率或尾部外推。

## 【有限多起点与profile】

均为`NOT_APPLICABLE_BY_DESIGN`，且明确禁止。若P分支代码出现optimizer、多起点、profile likelihood、CV调参或根据测试误差选择情景，检查必须FAIL。

## 【validation splits】

### T03E质量接口

- 只用A1 calibration、唯一首行、Q_valid记录构造q_A*和F_A。
- A1 holdout、extension overlap/new只核对未被读取为拟合输入的隔离证据，不参与锚点或CDF。
- Q_baseline是主输入，Q_C沿用相同q_A*、F_A、H参数，仅作为成对敏感性。

### RegMix

- A4/A5：512条训练数据，只复核既有linear及训练内选择记录，不重新训练。
- A6/A7：1M部署测试；用冻结linear相对“各验证域训练均值”baseline检查13域平均MSE至少改善5%，且13域均值Loss的Spearman至少0.5。测试历史已暴露，不能称新盲测。
- A8/A9：60M跨尺度迁移；A10/A11：1B跨尺度迁移。使用同样两个描述条件报告，但不据此校准或重选模型。
- A12–A15：仅估算情景，检查身份和训练配方重叠，不进入验证通过数。
- A6与A8配比若逐键相同，按同一配方簇做跨尺度成对审计，不当两套独立配方。

1M、60M、1B的绝对Loss误差和排序必须分别报告。即使两个条件都满足，也只能说明RegMix来源内相应尺度表现，不能证明可运输到B1 Loss。

## 【p–Q双重计数与映射审计】

1. 用符号恒等式和实际设计矩阵证明：固定域质量q时，`Q_mix=p^Tq`位于p的列空间；`theta^Tp+gamma Q_mix=(theta+gamma q)^Tp`。正则化的唯一数值解不构成gamma的识别。
2. 对已映射域明确区分direct/near/none；预期17个RegMix域中11个无质量映射。数量不符时停止。
3. 不把6个映射域重新归一化为总质量；缺失域保持`UNMAPPED`。
4. A17只能作为observed summary，不得当作A文档到B实验的连接键。
5. 输出三类变化：p直接配比效应、固定p质量变化（当前无数据）、由p机械诱导的Q变化。只有第一类由RegMix直接支持。
6. Mfull情景若同时含Q和p，必须标`REQUIRES_FIXED_P_QUALITY_INTERVENTION`；没有可行性证据时不得交给T07作为可独立优化的两个坐标。

## 【scenario registry执行前冻结】

在读取任何1M/60M/1B测试指标或生成情景派生量前，必须将以下ID、参数槽位、用途和顺序写入`scenario_registry/scenario_registry_preregistered.csv`并生成`SCENARIO_REGISTRY_SEAL.json`。seal后禁止新增、删除、重命名、调序或改变含义。

### null和质量参考

|scenario_id|冻结内容|
|---|---|
|S00_NULL_M0_B1|H0；quality off；mixture transport off；T07默认|
|S01_QREF_QA_H2_B1_R06_ADD|Q_baseline；H2 b=1；r_B1=0.6；rho_Q=1；additive；p固定/transport off；仅情景参考|

### 单因素质量扰动，相对S01仅改所列项

|scenario_id|唯一改动|
|---|---|
|S02_QC|Q_baseline→Q_C|
|S03_H1_IDENTITY|H2→H1|
|S04_H2_B05|b=0.5|
|S05_H2_B20|b=2|
|S06_H3_EQQUANTILE|H2→H3|
|S07_H4_DIRECTION_ONLY|H4；无数值Loss、不可优化|
|S08_RB1_02|r_B1=0.2|
|S09_RB1_09|r_B1=0.9|
|S10_RHOQ_00|rho_Q=0；质量项关闭，用于退化核验|
|S11_RHOQ_05|rho_Q=0.5|
|S12_EFF_KEEP_ETA|additive→effective-data，运输保持eta|
|S13_EFF_KEEP_K|additive→effective-data，运输保持k，需用目标beta重算eta|

### 单因素配比运输与冲突扰动

这些情景以S00为基础，quality保持off；只改变配比或冲突来源：

|scenario_id|唯一改动|
|---|---|
|S14_MIX_TAU05|tau_p=0.5|
|S15_MIX_TAU10|tau_p=1|
|S16_MIX_TAUM10_STRESS|tau_p=-1，仅失败压力|
|S17_B8_REVERSE_COMMON_SUPPORT|B8共同支持反向证据槽位；不使用旧k=-20，不生成支持外数值|

### 少量预注册极端组合

|scenario_id|冻结组合|
|---|---|
|X01_Q_HIGH|Q_baseline、H2 b=2、r_B1=0.2、rho_Q=1、additive、tau_p=0|
|X02_Q_CONSERVATIVE|Q_C、H2 b=0.5、r_B1=0.9、rho_Q=0.5、additive、tau_p=0|
|X03_H3_EFF|Q_baseline、H3、r_B1=0.6、rho_Q=1、effective-data保持eta、tau_p=0|

不得生成所有因素的笛卡尔积。S14–S16不与质量情景交叉；X01–X03不含p变化，以避免无可行性证据的Q/p联合自由变化。执行后不得因情景不利而删除，也不得为填图增加新ID。无法数值化的S07/S17仍保留，并明确`NO_NUMERIC_PREDICTION`或等待主控填入B分支候选槽位。

## 【必须输出】

正式P分支run至少包含：

- `handoff.md`、`run_summary.json`、`environment.json`、`command_log.json`、`stage_status.jsonl`
- `input_manifest.json`、`freeze_manifest.json`
- `quality_anchor/q_A_anchor_by_domain.csv`、`quality_anchor/q_A_anchor.json`
- `bridge/A_equal_domain_ecdf.csv`、`bridge/B6_unique_Q_ecdf.csv`、`bridge/H3_mapping_steps.csv`
- `bridge/quality_bridge_scenarios.json`、`bridge/bridge_qualification.csv`
- `mixture_audit/reference_p_reconciliation.csv`
- `mixture_audit/mixture_transport_audit.csv`、`mixture_audit/cross_scale_recipe_pairs.csv`
- `mixture_audit/domain_mapping_coverage.csv`、`mixture_audit/p_q_identifiability.json`
- `mixture_audit/regmix_fixed_model_validation.csv`
- `scenario_registry/scenario_registry_preregistered.csv`
- `scenario_registry/SCENARIO_REGISTRY_SEAL.json`
- `scenario_registry/scenario_inputs.parquet`：只含映射后Q、Delta_p、支持状态和参数槽位，不得提前填B分支新参数或联合Loss
- `identifiability_matrix_P.csv`、`uncertainty_components_P.json`
- `t07_candidate/t07_scenario_contract_candidate.json`
- `checks.json`、`verification.json`、`changes.csv`
- `code/`、`code_snapshot/`、`output_manifest.json`

## 【P分支checks】

至少逐项检查：T03E接口及上位方法hash；未访问A1–A3；q_A*筛选、七域精确集合、每域均值和七域等权；40930预期分母；H3七域等权CDF、右连续`<=`、B6唯一Q等权、广义逆边界；H0–H4资格；scenario seal先于测试读取和派生；21个预注册ID完整且无新增/删除；RegMix linear未重拟合/未重选；p0复算；13域等权目标；1M/60M/1B角色；10B/70B非真值；A6/A8配方重复；17域映射中11个none；p–Q列空间恒等；没有联合拟合；旧Q_ref=0.5未恢复；P分支没有读取B分支；旧产物不变；manifest一致。

新产生的关键要求不得`NOT_CHECKED/NOT_VERIFIABLE`。A/B映射本身应登记`SCENARIO_ONLY/NOT_IDENTIFIABLE`，不能将科学不可识别误记为工程检查失败，也不能伪造PASS。

## 【P分支独立verifier】

独立verifier不得导入执行模块。至少独立：

- 从T03E Parquet重筛q_A*记录，复算七域均值和等权锚点；
- 用显式计数公式复算F_A、B6唯一水平F_B及广义逆映射；
- 验证Q_C使用同一q_A*和F_A，未另行标定；
- 从A4重建p0并核对17列顺序、单纯形及零值；
- 从冻结线性系数直接复算抽查及全表预测、1M/60M/1B指标和13域聚合顺序；
- 用设计矩阵秩/投影残差与符号恒等式检查Q_mix列空间，但不得拟合gamma并解释其意义；
- 核验scenario registry seal时间、hash、ID全集、无笛卡尔积和无执行后变更；
- 检查代码中无optimizer、无测试驱动选择、无A1–A3路径访问、无B分支读取；
- 核验manifest与代码快照。

## 【P分支manifest】

执行顺序必须为：冻结scenario registry → 读取允许的测试/迁移输入并完成审计 → 完成checks/verifier/handoff/log → 冻结全部登记文件 → 最后生成`output_manifest.json`。manifest后不得写登记文件。

## 【P分支停止条件】

出现下列任一情况立即停止：

- q_A*缺域、多域、分母不符或需要改变权重；
- T03E接口、B6 Q设计、RegMix域顺序/索引/哈希与登记冲突；
- scenario seal后需要新增、删除或修改ID；
- 需要使用holdout/extension估计锚点或CDF；
- 需要拟合映射、rho_Q、tau_p、r_B1、h或重拟合RegMix；
- 需要给未映射域填Q或把六域重新归一化成17域质量；
- 进程访问真实A1–A3、B分支run、集成目录或写入旧产物；
- manifest后需要修改登记文件。

完成后只写`COMPLETE_PENDING_CONTROLLER_REVIEW`并停止，不启动B分支、集成或T07。

---

# C. TASK-T06E-INTEGRATE（仅后续主控验收使用）

## 【性质与权限】

该阶段不是第三个执行AI任务。只有主控在B、P两个正式run均完成并分别通过只读复审后，才可新建`diagnostics/TASK-T06E-INTEGRATE/<run_id>/`。两个执行AI不得自行创建集成目录、互相读取结果、决定联合主模型或更新00–05。

## 【主控集成输入】

- B分支正式run及其manifest、checks、verification、B侧候选合同。
- P分支正式run及其manifest、checks、verification、scenario registry seal、情景侧候选合同。
- 上位T06方法文件及本施工单的冻结SHA256。

主控先分别验收，不能因为一个分支通过而默认另一个通过。任一分支返工时，不得用另一个分支掩盖。

## 【主控必须裁决】

1. B1来源内参数复核是否通过，是否存在`WEAKLY_IDENTIFIED`。
2. MQ-add的G1–G4是否逐项通过；失败时是否诚实退回M0,6；MQ-eff是否保持敏感性地位。
3. B7是否严格只用新增90点，B8是否分区且没有传播旧边界解。
4. q_A*、H3、H0–H4和scenario registry是否符合预注册；A/B映射继续标记为无估计映射。
5. RegMix冻结、尺度角色、p–Q双重计数和11/17未映射是否成立。
6. 两分支输入T06方法hash是否相同、输出manifest是否当前匹配、是否存在交叉写入或旧产物变化。
7. 哪些B侧参数为`IDENTIFIED_SOURCE_CONDITIONAL`、哪些为`WEAKLY_IDENTIFIED`，哪些跨源字段只能是`FIXED_SCENARIO`。

## 【集成规则】

- 最终T07默认仍写：`primary_model=M0_B1`、`quality_enabled=false`、`mixture_transport_enabled=false`。
- 即使MQ-add通过，也只登记`B6_SOURCE_CONDITIONAL_ACCEPTED`；跨接A/B1的情景保持`SCENARIO_ONLY`。
- MQ-add失败时，质量模块回到`k=0`；不得由MQ-eff、B7或B8替补为主候选。
- 主控只可使用P分支已seal的scenario IDs，把B分支参数/不确定性填入预留槽位。禁止增加情景、删掉不利情景或做新的联合拟合。
- B8、B6和k=0始终并列传播。不得给来源情景编造概率或平均参数。
- p与Q没有固定p质量干预证据时，不得在T07合同中同时启用为独立可优化变量。
- 集成可以产生情景Loss表，但不能运行预算优化或选择“最优配置”。

## 【集成候选产物】

仅在后续主控明确执行时产生：

- `integration_review.md`
- `branch_manifest_reconciliation.csv`
- `integrated_identifiability_matrix.csv`
- `scenario_registry_filled.csv`
- `scenario_predictions.parquet`
- `uncertainty_components.json`
- `support_and_extrapolation_rules.csv`
- `t07_model_contract.json`
- `t07_parameter_table.csv`
- `checks.json`、`verification.json`、`output_manifest.json`

`t07_model_contract.json`必须逐项给出公式、Loss量纲、参数来源/资格、Q允许范围、17维p单纯形及列顺序、N/D分来源联合支持、OOS规则、参数joint draws、Q_baseline/Q_C敏感性、B8冲突传播、禁止独立优化的坐标及成本单位换算。不得只交一个无来源的参数JSON。

## 【总FAIL规则】

任一情形使对应分支或集成FAIL：

- 改动旧scaling/mixture/T03E/Q01C结果或00–05；
- 读取真实A1–A3；
- 两分支交叉读取或共享写入；
- 移动G1–G4、用Q>0.6/B7/B8反馈选择；
- MQ-eff在MQ-add失败后接任主模型；
- 用B7重复点增加分母，或合并B6/B8；
- 把H1–H4、rho_Q、tau_p、r_B1称为估计/标定参数；
- 恢复旧Q_ref=0.5为正式标定；
- 重新训练RegMix或按测试重选quadratic；
- scenario seal后改变registry，或生成未登记笛卡尔积情景；
- 执行AI自行拼接、宣布联合主模型或启动T07；
- manifest生成后改写被登记文件。

## 【总完成条件】

两个分支各自交齐结构化证据、独立verifier、0个关键FAIL和一致manifest后，只能进入“等待主控分别复审”状态。本任务是否科学通过、MQ-add是否被接受、情景能否进入T07，均由后续主控在`TASK-T06E-INTEGRATE`裁决。

本施工单生成后停止。当前不执行`TASK-T06E-B`、`TASK-T06E-P`或`TASK-T06E-INTEGRATE`，不启动T07。
