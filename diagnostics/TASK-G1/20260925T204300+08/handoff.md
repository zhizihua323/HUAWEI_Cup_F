# TASK-G1 handoff

状态：`WAITING_FOR_AUTHOR_REVIEW`

- run_id：`20260925T204300+08`
- 扩展冲突稳定性：`PARTIALLY_STABLE`；阈值固定为Q01C的`>0.5`。
- 文本join：选择`Q01C_A1_raw_source`；A18仅完成候选审计，未用于抽样。
- 盲审包：60条，覆盖7个domain；seal已先于盲审表和人工评分生成。
- 盲审表不包含Q、Q分位、高冲突标签、组三分数、原始主键或模型预测；人工评分列全部留空。
- 独立验收：PASS，fail=0。
- 执行器没有生成任何人工评分，也没有生成`paper/Q1_GAP_RESULT_FREEZE.md`。

## 作者下一步

请按`manual_review_instructions.md`完成`manual_text_review_blind.csv`的副本，另存为`manual_text_review_completed.csv`，保持原始blind表不变。完成后交回执行器，继续人工结果统计和paper候选；届时不得重抽样或删除不利结果。

## 机器入口

`run_summary.json`、`sampling_seal.json`、`manual_text_review_blind.csv`、`manual_review_key.csv`、`checks.json`、`verification.json`、`output_manifest.json`。
