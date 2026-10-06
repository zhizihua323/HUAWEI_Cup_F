# TASK-T06E-B-R1：profile坐标与G4门槛精准小修

日期：2026-09-25。状态：主控复审后的小修施工单；本文件不授权执行。

## 【任务背景】

原正式B分支：`diagnostics/TASK-T06E-B/20260925T100306+08/`。其输入、主拟合、折分、G1–G3、B7/B8、bootstrap和manifest经主控只读复核未发现错误，但profile固定参数实现存在确定的坐标错误，G4边界聚合范围也不符合主候选口径。因此原`REJECT_TO_M0_6`不能作为最终科学裁决，须在新R1目录中补正后重新判断G4。

上位文件：

- `tasks/TASK-T06_尺度桥接识别性与广义缩放律方法裁决.md`
- `tasks/TASK-T06E_来源内缩放律与质量条件关系验证_尺度桥接情景及T07接口.md`

冲突时以上位T06方法裁决为准。

## 【已确认错误】

### R1-01：profile固定值发生二次变换

原`profile_one.py`与`01_run_b_base.py`的profile路径将物理参数`fixed_value`直接写入对数优化坐标向量，再调用`decode(exp(u))`。因此固定物理值没有原样进入模型。

可复算证据：

- MQ-add全拟合`k_add=0.3544081081063713`。
- profile最接近该点的`fixed_value=0.35440810810637`，但保存的`k_add_conditional=3.774576805939331`，并非固定值。
- 该行profile SSE为`1.2539924950`，而全拟合SSE为`0.00964453848`。
- 22个参数profile在全拟合点均未进入描述集合，全部`n_inside_set=0`。该现象来自实现错误，不能解释成真实弱识别。

### R1-02：MQ-eff边界错误污染MQ-add的G4

原代码用`M0_6`、`MQ-add`、`MQ-eff`三个模型共同决定`boundary_ok`。实际MQ-add没有触碰边界；触界的是仅作敏感性的MQ-eff之`eta=1e-6`。G4是MQ-add主候选的验收门槛，MQ-eff不得使MQ-add的边界项失败。

## 【任务目标】

只修复并重算：

1. B1 M0、B6 M0,6、B6 MQ-add、B6 MQ-eff的全部冻结profile；
2. MQ-add的G4候选专属判定；
3. 基于修正后G4重新给出`ACCEPT_B6_SOURCE_RELATION`或`REJECT_TO_M0_6`；
4. 独立验证、日志、源码快照和manifest。

不得重拟合完整模型、折分模型、bootstrap、B7或B8；不得重算或移动G1–G3。

## 【输入】

- 原正式B分支全部文件，只读；重点：
  - `fit/scaling_parameters_by_source.csv`
  - `fit/full_fit_predictions.parquet`
  - `validation/candidate_comparison.csv`
  - `validation/validation_splits.csv`
  - `bootstrap/bootstrap_summary.csv`
  - `profiles/profile_inputs.json`
  - `profiles/jacobian_diagnostics.csv`
  - `config/solver_config.json`
  - `run_summary.json`、`checks.json`、`verification.json`
  - `output_manifest.json`
- B1、B6原始CSV，只读，仅用于以冻结模型和冻结训练支持重算profile残差。
- 上位T06/T06E施工单，只读。

不得读取T06E-P、A侧数据、B7/B8原始数据或任何T07输入。

## 【输出目录】

只写：`diagnostics/TASK-T06E-B-R1/<run_id>/`。

原B分支及全部旧B失败/候选run保持只读，不覆盖、不修补、不删除。

## 【允许修改范围】

仅在新R1目录内创建：修正后的profile实现、配置副本、profile结果、修正G4、独立verifier、日志、检查、源码快照和manifest。不得修改`solution/src/`、00–05、旧任务文件或旧输出。

## 【profile修正的唯一允许实现】

profile网格的`fixed_value`始终是物理参数值。以下两种实现任选其一，但必须只保留一个实现入口：

1. 将正的物理`fixed_value`先编码为对应优化坐标：
   `u_fixed=log(fixed_value/scale)`，其中E/A/B/k的`scale=L*`，alpha/beta/eta的`scale=1`；然后再随完整优化坐标一起decode。
2. 只decode自由优化坐标到物理参数，再将物理`fixed_value`直接写入物理参数向量；不得对它再次exp。

`k_add=0`和`eta=0`端点必须使用第二种物理向量构造或严格等价的显式null路径，禁止计算`log(0)`或用极小正数代替0。

每个保存的profile行必须满足：`<parameter>_conditional`与`fixed_value`在`atol=1e-12、rtol=1e-10`内一致。否则该行FAIL，不得进入profile集合。

## 【冻结求解设置】

完全沿用原正式B分支`config/solver_config.json`：Python/NumPy/SciPy版本、`least_squares(method='trf', loss='linear', jac='3-point', x_scale=1.0)`、容差、`max_nfev=100000`、参数边界、41点变换网格、全拟合点、零端点、每点9个起点、seed派生和profile阈值均不得改变。

不允许增加网格、增加起点、扩边界、换solver或降低收敛标准。冻结网格的数值失败照实登记并进入弱识别判断。

## 【必须重算的profile】

- B1：M0_B1的E/A/B/alpha/beta，共5个。
- B6：M0,6共5个；MQ-add共6个；MQ-eff共6个。
- 合计22个参数profile。

所有B6 profile只用`Q<=0.6`的225行；B1使用1176行。不得读取Q>0.6、B7或B8参与profile。

## 【全拟合点一致性硬检查】

每个profile必须包含其正式全拟合物理参数点。固定在全拟合点并重优化其他参数后：

- `SSE_profile_at_full_point <= SSE_full*(1+1e-6)+1e-12`；
- 保存的固定物理参数必须满足上述`atol/rtol`一致性；
- 该点必须进入描述性profile集合。

任一参数不满足即为实现FAIL，立即停止；不得把它归类为`WEAKLY_IDENTIFIED`后继续验收。

## 【G4修正口径】

MQ-add的G4只由MQ-add主候选本身决定：

1. MQ-add在`Q<=0.6`支持内预测全部有限且非负；
2. MQ-add正式全拟合参数不触固定边界；
3. MQ-add在冻结变换坐标、冻结列L2缩放后的Jacobian满列秩，condition number `<1e8`；
4. MQ-add多起点成功；
5. 修正后的MQ-add六个profile均完成冻结网格核算，按上位规则判断是否`WEAKLY_IDENTIFIED`。

M0,6与MQ-eff的预测、边界、Jacobian和profile继续单独报告，但不进入MQ-add的`boundary_ok`、`multistart_ok`或profile gate。MQ-eff的eta触及下界必须登记为敏感性模型边界证据，不能污染MQ-add，也不能替补MQ-add。

修正后只按原G1、G2、G3布尔值和新G4重新计算：

`all_four_PASS = G1 & G2 & G3 & G4`。

- 全部通过：`ACCEPT_B6_SOURCE_RELATION`，仍只限B6来源内。
- 任一失败：`REJECT_TO_M0_6`。

不得为获得任一结论修改G1–G4门槛。

## 【禁止重算和禁止变化】

- 不重拟合B1/B6 full fit和leave-N/leave-D。
- 不重跑200次bootstrap。
- 不重算B7/B8或高Q压力。
- 不改变G1=43/45、G2既有折结果、G3=200/200等已有证据；只验证其来源hash并原样引用。
- 不修改P分支，不执行集成，不编制或执行T07/T05，不更新00–05。

## 【必须输出】

- `handoff.md`
- `run_summary.json`
- `input_manifest.json`
- `protected_original_run_check.json`
- `environment.json`
- `command_log.json`
- `stage_status.jsonl`
- `changes.csv`
- `corrected_profiles/profile_grid_corrected.csv`
- `corrected_profiles/profile_summary_corrected.csv`
- `corrected_profiles/profile_multistart_results.csv`
- `corrected_profiles/full_point_reproduction.csv`
- `corrected_gates/G4_corrected.json`
- `corrected_gates/G1_G4_reconciliation.json`
- `identifiability_matrix_B_corrected.csv`
- `t07_bside_contract_candidate_corrected.json`
- `checks.json`
- `verification.json`
- `code/`、`code_snapshot/`
- `output_manifest.json`

## 【独立verifier】

独立verifier不得导入修正执行模块。必须独立：

1. 从物理参数公式构造profile预测，验证固定值没有再次指数变换；
2. 对22个profile逐项核验固定值与conditional值；
3. 对22个全拟合点逐项复算SSE并验证硬阈值及`inside_set=True`；
4. 独立复算MQ-add的Jacobian列缩放、秩、condition number和边界；
5. 确认MQ-eff eta边界未进入MQ-add G4；
6. 确认G1–G3逐字节/逐字段来自原正式run且未重算、未更改；
7. 重新计算最终accept/reject布尔逻辑；
8. 核验原正式B run、P run及旧结果未变化；
9. 核验源码快照和manifest。

不得以执行模块输出的G4布尔值作为expected。

## 【验收标准】

- 22/22全拟合点profile复现硬检查通过。
- 所有完成行的固定物理值和conditional值一致。
- G4只按MQ-add候选口径计算；MQ-eff边界单列。
- 修正profile网格按预注册完成或将数值失败诚实传播为弱识别；不得将实现错误当弱识别。
- G1–G3、折分、bootstrap、B7/B8均未变化。
- 独立verifier 0 FAIL、0 NOT_CHECKED。
- 原B正式run、P正式run及既有输出0变化。
- R1 manifest全部匹配，生成后无登记文件改写。

## 【停止条件】

- 需要改solver、边界、网格、起点、seed、profile阈值或G1–G4门槛；
- 任一全拟合点仍不能复现正式SSE；
- 修复会改变full fit、fold、bootstrap、B7/B8结果；
- 发现原正式run或P run发生变化；
- 需要执行集成、T07或T05。

完成后只登记`COMPLETE_PENDING_CONTROLLER_REVIEW`并停止。原B run继续保留历史，不改写其`REJECT_TO_M0_6`；最终科学结论由主控结合R1补证后裁决。
