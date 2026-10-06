# TASK-Q01A 交回说明（客观事实摘要）

- 状态：PARTIAL；退出码 2；run目录：`C:\Users\28762\Desktop\The Huawei Cup National Postgraduate Mathematical Modeling Contest\GPT_Workspace\diagnostics\TASK-Q01A\20260924T142229+08`。
- 本次仅完成缺失模式诊断；未选择或实施最终缺失处理策略，未删除记录、未填0、未生成最终Q、未覆盖旧quality产物。等待主控GPT审查TASK-Q01B。
- 全量扫描：三文件各单遍解压，解析成功 272505 行，唯一键 261086，重复行 11419；三份压缩文件SHA256与旧清单/旧audit一致，扫描后复核哈希不变。
- 逐文件行数：A1=51230；A2_arxiv=17523；A3_github=203752。
- 六个口径与文件视图（ALL）：A1_calibration: n=40943, 11主Q完整=40930, would_Q_nan=13, 25特征完整=40930；A1_holdout: n=10287, 11主Q完整=10282, would_Q_nan=5, 25特征完整=10282；A1_all_unique: n=51230, 11主Q完整=51212, would_Q_nan=18, 25特征完整=51212；extension_overlap_A1: n=11419, 11主Q完整=11419, would_Q_nan=0, 25特征完整=11419；extension_new_records: n=209856, 11主Q完整=209855, would_Q_nan=1, 25特征完整=209855；all_unique: n=261086, 11主Q完整=261067, would_Q_nan=19, 25特征完整=261067；file_unique_first_A1: n=51230, 11主Q完整=51212, would_Q_nan=18, 25特征完整=51212；file_unique_first_A2_arxiv: n=16104, 11主Q完整=16104, would_Q_nan=0, 25特征完整=16104；file_unique_first_A3_github: n=193752, 11主Q完整=193751, would_Q_nan=1, 25特征完整=193751。
- 提取层非有限（all_unique，按特征）：modernbert_professionalism: nan=6, +inf=0, -inf=0, 合计=6/261086；modernbert_reasoning: nan=13, +inf=0, -inf=0, 合计=13/261086。
- 原始层NaN元素（文件|字段：元素数）：A1|modernbert_professionalism: 30；A1|modernbert_reasoning: 78；A3_github|modernbert_professionalism: 6。
- 原始层列表长度不符行数：无。
- complete-case仅计数（all_unique）：11主Q未覆盖 19 行，25特征未覆盖 19 行；仅计数、不构成处理建议。
- 已知异常域分布（域|特征|口径）：commoncrawl|modernbert_professionalism|A1_calibration: run_missing=3, A1=3, ext_new=0, ext_overlap=0；commoncrawl|modernbert_professionalism|A1_holdout: run_missing=1, A1=1, ext_new=0, ext_overlap=0；commoncrawl|modernbert_professionalism|A1_all_unique: run_missing=4, A1=4, ext_new=0, ext_overlap=0；commoncrawl|modernbert_professionalism|all_unique: run_missing=4, A1=4, ext_new=0, ext_overlap=0；commoncrawl|modernbert_professionalism|file_unique_first_A1: run_missing=4, A1=4, ext_new=0, ext_overlap=0；wikipedia|modernbert_professionalism|A1_holdout: run_missing=1, A1=1, ext_new=0, ext_overlap=0；wikipedia|modernbert_professionalism|A1_all_unique: run_missing=1, A1=1, ext_new=0, ext_overlap=0；wikipedia|modernbert_professionalism|all_unique: run_missing=1, A1=1, ext_new=0, ext_overlap=0；wikipedia|modernbert_professionalism|file_unique_first_A1: run_missing=1, A1=1, ext_new=0, ext_overlap=0；wikipedia|modernbert_reasoning|A1_calibration: run_missing=10, A1=10, ext_new=0, ext_overlap=0；wikipedia|modernbert_reasoning|A1_holdout: run_missing=3, A1=3, ext_new=0, ext_overlap=0；wikipedia|modernbert_reasoning|A1_all_unique: run_missing=13, A1=13, ext_new=0, ext_overlap=0。
- 验收检查：40 项，PASS 33，FAIL 7，NOT_CHECKED 0；详见 checks.json。
- 限制：仅统计掩码与分母，不判断MCAR/MAR/MNAR，不把“集中”当因果；主Q数值与任何处理效果均未重算；A18正文未读取，旧版本外的其他A/B/C表未使用。

## 交回主控GPT的待裁决问题（Q01B，仅列问题）
1. 11个主Q特征出现非有限值时，处理原则（保留/排除/其他）和判定所需的最低证据标准是什么？
2. 是否区分域与验证角色（calibration/holdout/extension_new/extension_overlap）分别处理，理由与可接受差异如何界定？
3. 覆盖率与域间可比性的权衡标准是什么（各域有效分母差异多大时触发额外处理）？
4. 下游所有汇总是否必须显式披露有效n与非有限占比，并要求何种验证来证明处理不引入偏差？
5. 扩展重叠副本与A1中同一键、同一异常状态的记录，是否可视为同一证据？重复行应如何计入分母披露？
6. 现有证据是否足够，是否需要补充诊断（例如指标联合模式、按子域/来源分层的更多口径）？