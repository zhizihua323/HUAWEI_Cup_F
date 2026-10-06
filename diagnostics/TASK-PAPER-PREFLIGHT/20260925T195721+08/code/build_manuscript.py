from pathlib import Path
import re
root=Path.cwd(); src=root/'paper/manuscript/FULL_MANUSCRIPT_V1.md'; out=root/'paper/preflight/FULL_MANUSCRIPT_PREFLIGHT.md'
t=src.read_text(encoding='utf-8')
t=t.replace('# 算力约束下提升大语言模型能力的资源配置建模\n\n## 摘要', '''# 算力约束下提升大语言模型能力的资源配置建模

> 状态：`PREFLIGHT_CLEAN_COPY`。本文件只在预检副本中清理旧状态、术语、公式/图表占位和引用锚点，不生成最终DOCX/PDF。冻结科学数字保持原样；G1/G2/G4未验收位置保留显式占位。
>
> 临时语法：`{{CITE:key}}`是已核验文献锚点，最终按正文首次引用顺序转阿拉伯数字；`{{ASSET:ID}}`是图表registry锚点；`{{EQ:ID}}`是公式registry锚点。
>
> 官方版式落点：封面使用附件3模板；摘要页从页码1开始，页脚中部；无页眉；一级标题四号黑体居中；其他汉字小四号宋体、单倍行距。目录在DOCX阶段生成。

## 摘要''')
old_status='本文把四问拆成“数据质量与配比—来源条件标度关系—跨源情景桥接—预算优化与能力预测”的递进结构。问题一和问题二先建立可审计的基础关系，问题三在此基础上来做资源分配，问题四再把交叉熵损失映射到下游能力。由于问题三和问题四的结果尚未冻结，本稿只集中完成问题一、问题二及其可支持的结论。'
new_status='本文把四问拆成“数据质量与配比—来源条件标度关系—跨源情景桥接—预算优化与能力情景”的递进结构。问题一和问题二先建立可审计的基础关系，问题三在预算约束下处理资源分配，问题四再审计交叉熵损失与下游Benchmark之间的识别边界。现有Q1-Q4稳定正文可统一组织；G1、G2和G4主控验收尚未完成，相关新增结果在本预检副本中只保留显式占位，不预写结论。'
t=t.replace(old_status,new_status)
old_q3='若进一步比较同等算力下的局部收益，可分别用训练成本C_train=6N_physD_phys对参数和数据维度的边际成本，但质量成本函数和问题三预算约束尚未冻结，因此本文不在问题二给出跨维度货币化最优比例。'
new_q3='若进一步比较同等算力下的局部收益，可分别用训练成本C_train=6N_physD_phys考察参数和数据维度的边际成本；问题二不承担跨维度货币化最优比较，该比较由问题三在独立预算主合同中处理。'
t=t.replace(old_q3,new_q3)
repl=[
('经典标度律通常以参数规模和数据量解释验证损失的变化','经典标度律通常以参数规模和数据量解释验证损失的变化{{CITE:kaplan2020scaling;bahri2024explaining;hoffmann2022training}}'),
('22个原始质量字段展开为25个标量特征','22个原始质量字段展开为25个标量特征{{CITE:zhuang2025metarater;penedo2024fineweb;warner2025modernbert}}'),
('冻结的RegMix线性Scheffé模型为','冻结的RegMix线性Scheffé模型为{{CITE:liu2024regmix;scheffe1958mixtures;aitchison1982compositional}}'),
('模型评价采用13个验证领域的等权MSE改善率和逐域Spearman秩相关','模型评价采用13个验证领域的等权MSE改善率和逐域Spearman秩相关{{CITE:spearman1904general}}'),
('B6用于来源内的质量条件关系。','B6用于来源内的质量条件关系。'),
('B1用于经典参数—数据标度律的正式主拟合','B1用于经典参数—数据标度律的正式主拟合{{CITE:biderman2023pythia}}'),
('主模型使用多起点SLSQP','主模型使用多起点SLSQP{{CITE:scipy2026slsqp}}'),
('主可比层要求同一模型、同一验证集、同一最终checkpoint口径。','主可比层要求同一模型、同一验证集、同一最终checkpoint口径。六个Benchmark分别采用IFEval{{CITE:zhou2023ifeval}}、BBH{{CITE:suzgun2023bbh}}、MATH Lvl 5{{CITE:hendrycks2021math}}、GPQA{{CITE:rein2023gpqa}}、MUSR{{CITE:sprague2023musr}}和MMLU-PRO{{CITE:wang2024mmlupro}}的公开定义。C8逐任务评测结果来自Open LLM Leaderboard官方详细结果快照{{CITE:openllmleaderboard2025results}}；历史元数据来自Epoch AI官方模型数据集{{CITE:epochai2026models}}。'),
('Loss下降与Benchmark提升可能相关，但相关性不等价于可迁移预测关系','Loss下降与Benchmark提升可能相关，但相关性不等价于可迁移预测关系，且表观涌现会受到指标与阈值选择影响{{CITE:schaeffer2023emergent}}'),
('M0_B1参数的条件百分位很窄','M0_B1参数的条件百分位很窄{{CITE:efron1979bootstrap}}'),
]
for a,b in repl:
    if a in t:t=t.replace(a,b)
# Insert introduction and renumber original chapters with sentinels before adding the introduction.
t=t.replace('# 1 问题重述','@@CH2@@')
t=t.replace('# 2 问题分析','@@CH3@@')
t=t.replace('# 3 数据预处理与符号说明','@@CH4@@')
t=t.replace('# 4 问题一','@@CH6@@')
t=t.replace('# 5 问题二','@@CH7@@')
t=t.replace('# 6 问题三','@@CH8@@')
t=t.replace('# 7 问题四','@@CH9@@')
# Renumber numbered subheadings from high original chapter to low.
for a,b in [(7,9),(6,8),(5,7),(4,6),(3,4),(2,3),(1,2)]:
    t=re.sub(rf'^(##|###) {a}\.',lambda m,b=b:m.group(1)+f' {b}.',t,flags=re.M)
intro='''# 1 引言与问题背景

大语言模型能力由参数规模、训练数据量、数据质量、领域配比和算力预算共同约束。经典标度律用参数与数据规模解释验证损失的经验下降{{CITE:kaplan2020scaling;bahri2024explaining;hoffmann2022training}}，但已有关系通常不能直接回答数据质量、配比和有限算力之间的联合配置问题。高质量数据还涉及数据选择、指标设计和评测口径，相关影响不能由单一规模变量替代{{CITE:asai2026openscholar;zhuang2025metarater;penedo2024fineweb}}。

题目要求建立从质量评价、领域配比、广义标度关系、预算配置到Benchmark前沿的统一分析链。本文不预设外部模型或论文结论可以直接迁移到给定数据，而是逐层检查来源、支持域和识别资格。对可估计关系给出条件结果，对不可识别量和冲突证据保留明确边界，对未完成验收的G1、G2、G4部分只保留占位。

@@CH2@@'''
t=t.replace('@@CH2@@',intro)
for a,b in [('@@CH3@@','# 3 总体分析与技术路线'),('@@CH4@@','# 4 数据、假设与符号说明'),('@@CH6@@','# 6 问题一'),('@@CH7@@','# 7 问题二'),('@@CH8@@','# 8 问题三'),('@@CH9@@','# 9 问题四')]:t=t.replace(a,b)
# A few section titles need the new final wording.
t=t.replace('## 4.1 数据来源与预处理','## 4.1 数据来源与预处理')
t=t.replace('## 4.2 模型假设','## 4.2 模型假设')
t=t.replace('## 4.3 符号说明','## 4.3 符号说明')
# Add explicit G1/G2/G4 placeholders.
t=t.replace('## 6.5 规则敏感性与冲突验证','## 6.5 规则敏感性与冲突验证\n\n【G1_PENDING：Q1扩展冲突稳定性与A18可靠性核验尚未主控验收；此处不得填写新增数字或宣称Q1最终关闭。】')
t=t.replace('## 7.9 问题二的正式结论边界','## 7.9 问题二的正式结论边界\n\n【G2_PENDING：Q2附加迁移/外推及最终来源边界尚未主控验收；现有B1/B6来源内结果保持原样，不得由本预检扩展到统一L(N,D,Q,p)。】')
t=t.replace('## 9.8 未来12/24个月情景资格','## 9.8 未来12/24个月情景资格\n\n【G4_PENDING：Q4最终前沿情景/直接Benchmark模型尚未主控验收；仅保留现有CONDITIONAL_BASELINE_ONLY与NOT_IDENTIFIABLE_PROGRESS边界，不生成未来数值。】')
# Convert scattered figure/table placeholders to registry anchors.
assets={
'【附表A1占位：17×13线性Scheffé系数矩阵】':'{{ASSET:APP-TAB-A1}}','【表4-1占位：质量记录、有效分母、缺失与覆盖率】':'{{ASSET:TAB-02}}','【表4-2占位：三组质量均值、分歧范围与高分歧比例】':'{{ASSET:TAB-03}}','图4-1占位：质量指标方向统一、缺失传播与三组聚合流程图。':'{{ASSET:FIG-02}}','图4-2占位：领域质量分布与三组分歧诊断图。':'{{ASSET:FIG-02}}','【表4-3占位：1M检验、60M与1B运输结果及模型适用边界】':'{{ASSET:TAB-04}}','图4-3占位：1M预测—实际散点与跨尺度误差诊断图。':'{{ASSET:FIG-03}}','【表5-1占位：M0_B1参数、支持范围与验证状态】':'{{ASSET:TAB-05}}','图5-1占位：B1标度律拟合与残差诊断图。':'{{ASSET:FIG-04}}','【表5-2占位：MQ-add参数与条件区间】':'{{ASSET:TAB-06}}','【表5-3占位：MQ-add的G1—G4验收表】':'{{ASSET:TAB-06}}','图5-2占位：B6质量方向、留组误差与k_add profile图。':'{{ASSET:FIG-04}}','图5-3占位：A/B质量尺度不可识别与H0—H4情景边界图。':'{{ASSET:FIG-05}}','【表5-4占位：配比运输与Q-p识别状态】':'{{ASSET:TAB-07}}','表6-1占位：三档正式主结果。':'{{ASSET:TAB-08}}','表6-2占位：H=2048、4096、8192、32768、131072的完整上下文敏感性表。':'{{ASSET:TAB-09}}','表6-3占位：三类质量成本的S03情景结果。':'{{ASSET:TAB-10}}','表6-4占位：配比运输情景表。':'{{ASSET:TAB-10}}','表6-5占位：主结果参数不确定性。':'{{ASSET:TAB-10}}','表7-1占位：六任务条件基线与条件区间。':'{{ASSET:TAB-12}}','表7-2占位：历史分层与有效分母表。':'{{ASSET:TAB-13}}','表7-3占位：Loss空间情景与Benchmark空间分离表。':'{{ASSET:TAB-14}}','表7-4占位：六类不确定性清单。':'{{ASSET:TAB-14}}','【附录A占位：数据来源与变量定义】':'{{ASSET:TAB-01}}','【附录B占位：完整系数和验证表】':'{{ASSET:APP-TAB-A1}}','【附录C占位：复现实验与代码入口】':'{{ASSET:APP-TAB-A2}}'}
for a,b in assets.items():t=t.replace(a,b)
# Formula anchors, applied only to the specific strings in the preflight copy.
forms=[('Q_baseline(r) = (U_r + K_r + R_r)/3。','EQ-Q1-01'),('D_range = max(U,K,R) − min(U,K,R)，','EQ-Q1-02'),('hat L_j(p) = sum_i beta_{ij} p_i， j=1,...,13。','EQ-Q1-05'),('Q_C(r) = Q_baseline(r) [1 − 0.02 P(r)]，','EQ-Q1-04'),('L0(N_B,D_B) = E + A_N N_B^(−α_N) + B_D D_B^(−β_D)，','EQ-Q2-01'),('M0_6(N_B,D_B) = E_6 + A_6 N_B^(−α_6) + B_6 D_B^(−β_6)','EQ-Q2-02'),('MQ-add(N_B,D_B,Q_score) = M0_6(N_B,D_B) − k_add (Q_score − 0.6)， 0.1≤Q_score≤0.6。','EQ-Q2-03'),('MQ-eff = E + A_N N_B^(−α_N) + B_D [D_B exp(−η(Q_score−0.6))]^(−β_D)。','EQ-Q2-04'),('∂L0/∂N_B = −α_N A_N N_B^(−α_N−1) < 0，','EQ-Q2-05'),('∂L0/∂D_B = −β_D B_D D_B^(−β_D−1) < 0。','EQ-Q2-06'),('E_N = (∂L0/∂N_B)(N_B/L0) = −α_N A_N N_B^(−α_N)/L0，','EQ-Q2-07'),('E_D = (∂L0/∂D_B)(D_B/L0) = −β_D B_D D_B^(−β_D)/L0。','EQ-Q2-08'),('∂MQ-add/∂Q_score = −k_add，0≤0.1≤Q_score≤0.6。','EQ-Q2-03'),('dMQ-add = −α_6 A_6 N_B^(−α_6−1)dN_B − β_6 B_6 D_B^(−β_6−1)dD_B − k_add dQ_score。','EQ-Q2-09'),('dN_B/dQ_score = −k_add / [α_6 A_6 N_B^(−α_6−1)]，','EQ-Q2-10'),('dD_B/dQ_score = −k_add / [β_6 B_6 D_B^(−β_6−1)]。','EQ-Q2-11'),('N_phys=10^9 N_B， D_phys=10^9 D_B。','EQ-Q3-01'),('C_total(N,D,Q_A,H)','EQ-Q3-02'),('κ(H)=6+ηH。','EQ-Q3-03'),('C_total=κ(H)N_physD_phys=κ(H)10^18 N_B D_B≤C_budget。','EQ-Q3-04'),('Λ=L0(N_B,D_B)+λ[C_total(N_B,D_B)−C_budget]','EQ-Q3-07'),('∇L0=−λ∇C_total。','EQ-Q3-08'),('等价地，N_B∂L0/∂N_B=D_B∂L0/∂D_B。','EQ-Q3-09'),('H_crit=6/η=30000。','EQ-Q3-10'),('G_EXP(Q_A)=10^7 exp(6Q_A)，','EQ-Q3-11'),('Δp=coeff.mean(axis=0)·(p−p0)。','EQ-Q3-12'),('scale_associated_component=m_t(x_i)−m_t(x_ref)。','EQ-Q4-02'),('conditional_remainder=observed−m_t(x_i)。','EQ-Q4-03'),('observed=fitted+conditional_remainder，','EQ-Q4-04')]
for a,e in forms:t=t.replace(a,a+' {{EQ:'+e+'}}')
# Normalize symbols in prose/formulas only; frozen numeric values and model IDs remain unchanged.
for a,b in [('alpha_N','α_N'),('beta_D','β_D'),('alpha_6','α_6'),('beta_6','β_6'),('kappa','κ'),('Delta_p','Δp')]:t=t.replace(a,b)
# Add unified validation chapter and renumber evaluation, improvement, conclusion and front/back matter.
validation='''# 10 统一模型检验与灵敏度

本章只汇总已冻结的检验，不新增模型。数据分母与缺失传播由Q01C正式run核验；质量规则稳定性和holdout由T03E正式run核验；B1/B6的参数profile、留组预测、重采样和数值识别由T06冻结接口报告；预算可行性、单位、KKT和H敏感性由T07正式run核验；Loss-Benchmark识别、留组/时间外验证和未来资格由T05/T08正式run核验。各检验的适用范围和资格标签必须随结果保留，不能把重采样解释为联合后验，也不能把情景或条件关联写成因果结论。

【G1_PENDING：Q1扩展冲突稳定性与A18可靠性核验尚未主控验收；本章不得补写其新增数字。】
【G2_PENDING：Q2附加迁移/外推及最终来源边界尚未主控验收；本章不得补写统一广义标度律的新增结果。】
【G4_PENDING：Q4最终前沿情景/直接Benchmark模型尚未主控验收；本章不得生成未来N、D、compute、Loss或Benchmark增量。】

'''
t=t.replace('# 8 模型评价与推广',validation+'# 11 模型评价')
t=t.replace('## 8.1 模型优点','## 11.1 模型优点').replace('## 8.2 模型局限','## 11.2 模型局限').replace('## 8.3 推广边界','# 12 改进与推广\n\n## 12.1 推广边界').replace('# 9 结论','# 13 结论')
old_refs='# 参考文献\n\n[待补参考文献1：经典缩放律来源]\n[待补参考文献2：RegMix配比方法来源]\n[待补参考文献3：Pythia模型族来源]\n[待补参考文献4：Benchmark评测来源]\n[待补参考文献5：质量评价方法来源]'
new_refs='# 14 参考文献（预检库）\n\n最终参考文献表只导出正文实际使用的已核验条目；排序按正文首次引用顺序。完整元数据见`REFERENCE_VERIFICATION.csv`，BibTeX见`references_verified.bib`。本稿正文中的`{{CITE:key}}`在DOCX阶段统一替换为编号；未使用的方法候选不得进入最终参考文献表。\n\n# 15 AI工具使用声明\n\n需合并`AI_DISCLOSURE_DRAFT.md`。精确底层模型与发布日期为`TO_CONFIRM_BY_AUTHOR`；至少列明OpenAI Codex、OpenAI、已确认版本、使用日期、用途和人工核验责任。'
t=t.replace(old_refs,new_refs).replace('# 附录说明','# 16 附录与复现说明')
t+='\n\n---\n\n## 预检副本控制说明\n\n本副本没有生成最终图表、DOCX或PDF。G1/G2/G4占位、临时citation/asset/formula锚点和参考文献筛选必须在后续验收与排版阶段按registry处理。原始V1、00-05、稳定正文和正式run均未修改。\n'
out.write_text(t,encoding='utf-8')
print(out)



