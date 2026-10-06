# TASK-Q01C 交回说明（事实摘要）

- 状态：COMPLETE_PENDING_REVIEW；run目录：`C:\Users\28762\Desktop\The Huawei Cup National Postgraduate Mathematical Modeling Contest\GPT_Workspace\diagnostics\TASK-Q01C-R1\20260924T225550+08\interruption_run\synthetic_run`；run_id：`synthetic_run`
- 阶段退出码：{'s11_scan_a2': 0, 's12_scan_a3': 0, 's20_score_primary': 0, 's30_sensitivity': 0, 's40_summarize': 0, 's50_verify': 0, 's60_finalize': 0}；峰值RSS：111.8 MB
- 物理记录 660，唯一键 660，重复 0；主Q有效 658，无效 2。
- 主分析：11 特征严格完整案例；缺失组不重分配权重；Q_valid=False 的行保持 Q=NaN。
- 敏感性：仅用 A1 calibration 对应域/特征中位数替换缺失特征；门槛全部通过=True，插补记录数=2，fallback=未使用。
- 独立终验：PASS 14，FAIL 0，NOT_CHECKED 0（见 checks.json / verification.json）。
- 受保护旧产物哈希变化：无；缺失文件：无。
- 检查点复用证据：0 次 resume probe，均未重新解压（见 checkpoint_manifest.json 与 stage_status.jsonl）。

## 机器入口
- input_manifest.json / environment.json / run_config.json / changes.csv
- checkpoints/ 与 checkpoint_manifest.json / stage_status.jsonl / run.log
- audit.json / raw_field_counts.csv / normalization.json
- quality_features_scores.parquet（272505 行，含 Q_valid、主Q、敏感性Q、缺失原因）
- domain_summary.csv / summary_denominators.csv / sensitivity_domain_summary.csv / sensitivity_comparison.csv
- imputation_parameters_sensitivity.json / imputation_applied_counts.csv
- feature_summary.csv / extension_shift.csv / unresolved_indicator_correlations.csv / indicator_direction_pending.csv
- conditional_bootstrap.csv / checks.json / verification.json / quality_baseline_q01c.md

## 限制与待主控审查
- 本状态为 COMPLETE_PENDING_REVIEW，不代表项目层验收；00–05 未更新。
- 敏感性列覆盖率 1.0 是构造结果，不能作为数据完整性证据。
- 分歧统计使用有效组（skipna），与主Q的严格完整案例口径不同，二者不可互相替代。
- 尚未运行配比/缩放/演化/优化/论文模块；下游使用主Q时应显式携带 Q_valid 过滤。
- 待审查：阈值布尔分母口径、敏感性域排序差异是否影响下游选型、是否需要把 Q_valid 覆盖率作为下游合并条件。