# REFERENCE GAP AUDIT

日期：2026-09-25。  
本轮未联网，未新增或猜测书目信息。  
结论：**当前项目没有正式参考文献表，也没有任何正文引用；参考文献是提交级阻断项。**

## 1. 现状

- `paper/manuscript/FULL_MANUSCRIPT_V1.md`：`[1]`类引用0处；`\cite{}`0处。
- 参考文献部分只有5条占位：
  - 待补参考文献1：经典缩放律来源
  - 待补参考文献2：RegMix配比方法来源
  - 待补参考文献3：Pythia模型族来源
  - 待补参考文献4：Benchmark评测来源
  - 待补参考文献5：质量评价方法来源
- 未发现`.bib`、`.ris`、`.enw`、`.nbib`或正式参考文献表。
- 题目原文自带6条文献线索，可作为已给出的本地线索，但仍需按竞赛格式核验作者、卷期、页码和访问信息。

## 2. 题目已给出、可直接进入核验队列的条目

这些不是项目已核验文献，只是原题提供的候选：

| 候选 | 当前状态 |
|---|---|
| Bahri et al., Explaining neural scaling laws, PNAS 121(27), 2024, DOI 10.1073/pnas.2311878121 | 题目给出；需按竞赛格式整理 |
| Hoffmann et al., Training Compute-Optimal Large Language Models, NeurIPS 35, 2022 | 题目给出；需补页码/版本 |
| Xia et al., RegMix, ICML 2024 | 题目给出；需补完整作者/页码 |
| Biderman et al., Pythia, ICML 2023 | 题目给出；需补完整作者/页码 |
| Asai et al., Nature 650, 857–863, 2026, DOI 10.1038/s41586-025-10072-4 | 题目给出；需核验 |
| Schaeffer et al., Emergent Abilities, NeurIPS 36, 2023 | 题目给出；需补完整信息 |

`参考资料` 中的成品论文还列有Kaplan、Aitchison等文献，但它们是参考论文中的二手线索，本轮未联网核验，不能直接当作项目正式文献。

## 3. 必须补引用的位置

### MUST_ADD

1. 问题背景中的scaling law、参数/数据计算量和Chinchilla近似：引Hoffmann等及可选Kaplan等。
2. 背景中的Nature/OpenScholar数据质量与领域配比论述：引Asai等。
3. Q1质量评价、RegMix配比和Scheffé/成分数据建模：引Xia等；若使用成分数据方法，需补正式方法文献。
4. Q2 B1/Pythia轨迹：引Biderman等。
5. Q2质量候选/半合成实验：必须引用附件数据说明或对应实验来源；不能只引项目内部CSV。
6. Q3质量成本函数：引用题目附录B及所选成本函数来源；题目参数不能写成外部文献。
7. Q4 Loss–Benchmark关系、六任务Benchmark、开源模型时间轴和许可证口径：每个Benchmark至少一个正式来源；C1/C4/C5/C6/C8的官方来源必须列明。
8. AI使用披露：按竞赛规定列工具名称、版本/型号、开发机构、版本发布日期、使用环节和人工核验方式。

### SHOULD_ADD

- SLSQP/多起点优化方法、bootstrap、profile likelihood、Spearman和MSE定义。
- FineWeb-Edu、ModernBERT、Qurater等质量特征来源。
- 开源许可证、模型卡和评测时间戳的来源说明。
- 复现代码依赖（NumPy、pandas、SciPy、scikit-learn、Matplotlib、pyarrow）的官方引用或版本说明。

### OPTIONAL

- 模型评价方法、统计不确定性、可视化规范。
- 参考文献管理格式说明。
- 可复用的通用数学建模教材或方法资料。

## 4. 不可核实或疑似虚构文献

当前项目正文未填入具体虚构文献，因此暂未发现“以假文献冒充真文献”。但存在三类高风险状态：

1. 5条占位文献没有任何作者/出处，不能提交。
2. 参考论文中的文献记录未经独立核验。
3. 题目给出的2026 Nature信息虽在本地题面出现，但本轮不联网，不能扩展成其他版本、页码或DOI。

## 5. 最低动作

- 建立唯一`references.bib`或正式编号表。
- 先按正文首次引用顺序编号，再写段落。
- 所有数据来源、方法来源、Benchmark来源、AI工具来源分别落表。
- 最终扫描：正文每个`[n]`必须能在表中有唯一记录，表中每条记录必须至少被正文引用一次。
