# G1 文本盲审说明

状态：`WAITING_FOR_AUTHOR_REVIEW`。本文件不是模型评分结果，执行器不会生成任何人工评分。

## 作者任务

1. 请只查看 `manual_text_review_blind.csv`，不要查看 `manual_review_key.csv`、Q、Q分位、高冲突标签或组三分数。
2. 对每条 `text_redacted` 独立判断并填写：
   - `readability_1to5`：1–5整数。
   - `completeness_1to5`：1–5整数。
   - `contamination_0to2`：0无污染、1可疑、2明显垃圾/广告/模板污染。
   - `overall_quality_1to5`：1–5整数。
   - `review_notes_optional`：可选短备注，不得用于替代评分。
3. 不要使用AI、规则、模型或他人自动评分替代作者判断。
4. 将原盲审表另存为 `manual_text_review_completed.csv`，不要把完成值写回原始 `manual_text_review_blind.csv`。
5. 完成后交回原始blind表哈希与completed表；执行器只对有效填写记录做统计，不因结果方向而重新抽样。

## 文本说明

原始文本只做电子邮件、URL和非必要控制字符的必要脱敏；未改写正文。若文本中仍有敏感信息，请仅作为审阅材料处理。

共 60 条，覆盖 7 个domain，单一domain不超过12条。采样种子、配额、review_id和SHA256已冻结在 `sampling_seal.json`；seal时间早于任何人工评分文件。

## 停止条件

执行器现在停止于作者判断节点。收到有效的 `manual_text_review_completed.csv` 之前，不进行人工结果统计，也不生成 `paper/Q1_GAP_RESULT_FREEZE.md`。
