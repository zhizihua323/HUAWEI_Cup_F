# TASK-T06E-INTEGRATE 主控集成审查

结论：通过。B-R1纠正了profile物理坐标和G4候选口径；22/22全拟合点复现，MQ-add的G1–G4全部通过。因此MQ-add获得`B6_SOURCE_CONDITIONAL_ACCEPTED`资格，但只限B6来源内。

联合主模型仍为`M0_B1`，`quality_enabled=false`、`mixture_transport_enabled=false`。A侧`Q_baseline`与B侧`Q_score`没有样本级配对，桥接继续为`NOT_IDENTIFIABLE`；H1–H3及跨接B1的质量效应均为`SCENARIO_ONLY`。MQ-eff的eta触及下界，只作敏感性。B8保留为与B6方向冲突的证据，不估计反向统一系数。

P分支预注册的21个情景原样保留，未新增、删除或调序。集成只把已验收的B1、B6参数和资格填入槽位，没有重拟合模型，也没有执行预算优化。RegMix线性模型只在1M来源内具备验证支持；60M/1B为跨尺度运输审计，向B1运输仍是情景。固定域质量下`Q_mix=p^Tq`位于p列空间，因此Q与完整p不能作为两个独立自由坐标同时优化。
