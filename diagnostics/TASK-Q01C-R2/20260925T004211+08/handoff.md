# TASK-Q01C-R2 交回说明（恢复一致性与 S60 日志收口）

- 状态：COMPLETE_PENDING_REVIEW；R2目录：C:\Users\28762\Desktop\The Huawei Cup National Postgraduate Mathematical Modeling Contest\GPT_Workspace\diagnostics\TASK-Q01C-R2\20260925T004211+08
- 唯一恢复判定入口：validate_stage()（REUSABLE / NOT_STARTED / INVALID），正常 --resume 主循环、--stage 前置依赖、--probe-resume 三处共同调用。
- 不可变链：S20 ← S10/S11/S12 链身份；S30 ← S20 checkpoint payload；S40 ← S30 checkpoint payload；quality_features_scores.parquet 只作为 materialized output，未被任何 stage marker 绑定。
- 中后段跨进程：P1 pid=14452 在 S30 完成后被外部终止；P2 pid=15776 复用 s10–s30，新增计算 {"s10_scan_a1": 0, "s11_scan_a2": 0, "s12_scan_a3": 0, "s20_score_primary": 0, "s30_sensitivity": 0}。
- 三类拒绝路径（payload 损坏 / config 不匹配 / code fingerprint 不匹配）均由正常 --resume 硬停止：非零退出、零重算、零覆盖，probe 与 resume 判定一致。
- S60：stage_seconds/executed_stages/stage_terminal_events/stage_exit_codes 均包含 s60_finalize，stage_status 有 start 与唯一 terminal；独立验收器显式包含全部 STAGES。
- 回归：原科学 run 56/56、R1 run 与既有 Q01C run 零变化；A1–A3 未被 read/stat/hash/解压/扫描。

## 保留的历史 NOT_VERIFIABLE
- historical TASK-Q01C scientific-run main command：never persisted by the original run (environment.json commands list empty); cannot be reconstructed honestly

## 待主控审查
- 是否接受 --hold-after-stage 继续作为默认关闭的测试钩子。
- 是否接受 stage marker 仅绑定阶段局部不可变输出 + checkpoint identity 的职责边界。
- 是否需要在未来运行中把 S50 的独立验收也纳入 S60 之后的第二次只读复核。