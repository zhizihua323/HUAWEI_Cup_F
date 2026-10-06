# V3.1 最终引用闭环审计

审计日期：2026-09-26

## 结论

- `FINAL_MANUSCRIPT_V3_1` 实际使用并列出 **20** 条参考文献。
- `references_final.bib` 只保留这20条，并按正文首次出现顺序排列。
- `citation_map_final.csv` 已按V3.1章节、编号和资格词重建；旧的23条映射不再作为终稿依据。
- `reference_verification_final.csv` 只登记终稿实际引用的20条；未使用候选不混入最终集合。
- Open LLM Leaderboard的来源、commit和引用元数据已确认；复用许可仍未确认。终稿明确不随稿再分发该第三方原始快照，且不把公开访问解释为复用授权。
- 参考文献同步未改变任何模型、数据、数字、科学结论或资格词。

## 最终编号

| 编号 | 引用键 | 用途 |
|---:|---|---|
| 1 | `kaplan2020scaling` | 神经标度律背景 |
| 2 | `hoffmann2022training` | 计算最优训练背景 |
| 3 | `penedo2024fineweb` | 数据质量筛选背景 |
| 4 | `warner2025modernbert` | 质量评分器背景 |
| 5 | `xie2023dsir` | DSIR目标相关性背景 |
| 6 | `spearman1904general` | 秩相关方法 |
| 7 | `efron1979bootstrap` | bootstrap方法 |
| 8 | `openai_tools` | AI工具披露 |
| 9 | `liu2025regmix` | RegMix方法 |
| 10 | `scheffe1958mixtures` | 混合模型方法 |
| 11 | `biderman2023pythia` | Pythia数据来源 |
| 12--17 | 六项Benchmark来源 | IFEval、BBH、MATH、GPQA、MuSR、MMLU-Pro |
| 18 | `openllmleaderboard2025results` | 冻结评测快照来源 |
| 19 | `epochai2026models` | 模型算力与日期元数据来源 |
| 20 | `koenker1978regression` | 分位损失定义 |

## 提交边界

`references_word_numbered.docx` 是旧23条引用阶段的辅助文件，已被V3.1正文中的正式参考文献表取代，不得再用于终稿替换。最终依据为V3.1 DOCX/PDF、`references_final.bib`、`citation_map_final.csv`和本审计。
