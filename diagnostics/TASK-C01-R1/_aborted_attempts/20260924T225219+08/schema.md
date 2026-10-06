# TASK-C01-R1 corrected table schemas

Source of every table below: the frozen run `diagnostics/TASK-C01/20260924T175553+08/`.
Nothing in this run re-read a raw attachment (`F题/real_attachments`).

## 1. `c8_directory_aggregate_corrected.csv` (one row per directory, 1863 rows)

| column | meaning |
|---|---|
| `directory` | model directory name as registered in `c8_parse_log.csv` |
| `n_files_total` | JSON files of that directory in the frozen parse log |
| `n_files_parse_success` | files with `parse_status == "ok"` |
| `n_files_parse_failed` | files with `parse_status != "ok"` |
| `has_parse_failure` | `n_files_parse_failed > 0` |
| `has_any_parseable_file` | `n_files_parse_success > 0` |
| `source_parse_incomplete` | `has_parse_failure` (the directory's archived source set is incomplete) |
| `n_task_slots_expected` | `n_files_parse_success * 6` (a failed parse produces no task slots) |
| `n_result_slots_in_group_table` | rows of this directory in `c8_group_scores_all_runs.csv` |
| `n_results_valid` | finite group scores contributed by this directory |
| `n_results_missing` | `n_task_slots_expected - n_results_valid` |
| `n_models_from_parse_ok` / `models_from_parse_ok` | model identities taken only from parseable files |
| `parse_ok_files` / `parse_failed_files` | explicit file lists |
| `file_accounting_identity_ok` | `n_files_total == n_files_parse_success + n_files_parse_failed` |

## 2. `c8_model_task_aggregate_corrected.csv` (model x six tasks, 11160 rows)

Base = the frozen `c8_model_task_aggregate.csv`. Added / changed columns:

| column | meaning |
|---|---|
| `n_files_total`, `n_files_parse_success`, `n_files_parse_failed` | directory coverage copied from table 1 |
| `has_parse_failure`, `has_any_parseable_file`, `source_parse_incomplete` | directory flags copied from table 1 |
| `n_file_slots_this_task` | `n_files_parse_success` (one slot per parseable file for this task) |
| `n_valid_results` | finite scores for this model and task (recomputed from the group detail) |
| `n_missing_results` | `n_file_slots_this_task - n_valid_results` (corrected definition) |
| `n_group_rows` | rows for this model+task in the group table |
| `orig_n_files_in_directory`, `orig_n_missing_results` | the frozen columns, kept for traceability |
| `n_valid_results_original`, `n_valid_results_agrees_with_original` | frozen vs recomputed value |
| `canonical_score_finite` | the canonical score is a finite number |
| `canonical_selection_basis`, `legacy_selection_basis` | the two pre-existing selection rules, **not** re-decided here |
| `all_scores`, `all_files`, `legacy_selection_rule_score` | preserved from the frozen table, so multi-run information is not lost |

## 3. `c8_model_wide_corrected.csv` (one row per model, 1860 rows)

| column | meaning |
|---|---|
| `model_key`, `Model` | directory key and resolved model name |
| `<task>` (6 columns) | canonical score of that task, 0-1 raw proportion |
| `<task>_n_valid` | number of valid results behind that canonical score |
| `n_tasks_valid` | number of the six tasks with a finite canonical score |
| `six_task_complete` | `n_tasks_valid == 6` |
| `six_task_mean_complete_only` | arithmetic mean of the six tasks **only** when `six_task_complete`; otherwise NaN |
| `partial_task_mean` | mean over the available tasks when `1 <= n_tasks_valid <= 5`; otherwise NaN |
| `n_files_total`, `n_files_parse_success`, `n_files_parse_failed`, `has_parse_failure`, `source_parse_incomplete` | directory coverage copied from table 1 |
| `legacy_partial_or_complete_mean` | the frozen skipna row mean, kept for traceability only |
| `legacy_mean_matches_c01_table` | the legacy column reproduces `six_task_mean_c8_raw` exactly |
| `mean_column_semantics` | free-text statement of the three mean columns |

### Non-negotiable semantics

`six_task_mean_complete_only` is the only column that may be called a six-task mean.
`legacy_partial_or_complete_mean` is a skipna row mean and must not be used as a six-task mean.

## 4. `repaired_checks.json`

Each entry carries `check_id`, `status`, `claim`, `key_c8_item`, `actual`, `expected`, `evidence`,
`verification_method`, `limitations`, `tolerance`. Statuses used: `PASS`, `WARN`, `FAIL`,
`NOT_CHECKED`, `NOT_VERIFIABLE`. `NOT_CHECKED` and `NOT_VERIFIABLE` are never counted as PASS.
