# TASK-Q01C-R1 交回说明（恢复机制与日志精准小修）

- 状态：COMPLETE_PENDING_REVIEW；R1目录：`C:\Users\28762\Desktop\The Huawei Cup National Postgraduate Mathematical Modeling Contest\GPT_Workspace\diagnostics\TASK-Q01C-R1\20260924T225550+08`
- 跨进程实证：P1 pid=14776 被监督进程终止 → P2 pid=11700 使用 --resume 复用其检查点。
- P2 对已完成阶段新增扫描次数：2；检查点 hash 前后一致：True。
- CLI 契约：--resume（拒绝已 finalize、校验后复用、失败即停）、--stage（依赖不足退出 6；单阶段仅执行所选阶段并记录 SKIPPED）、--probe-resume（只读资格报告）。
- 检查点协议：payload → meta → checkpoint.COMPLETE，阶段标记为 <stage>.stage.COMPLETE，S20/S30/S40 的检查点标记不再被阶段标记覆盖。
- 日志：R1 主命令、P1、P2、probe、独立验证命令均由实际 argv 记录；每个 R1 阶段有 start + 唯一终态；P1 被外部终止由监督进程写 termination_evidence.json。
- extension 来源隔离：holdout / extension overlap / extension new 三类极端值扰动后，calibration 参数逐字段不变（见 extension_isolation_test.json）。
- 正式科学run：56/56 manifest 匹配，状态 COMPLETE_PENDING_REVIEW 未变；之前 7 个 run 与旧证据未变。
- 未读取/未哈希/未解压 A1–A3（本任务全程仅使用合成 fixture）。

## 保留的历史限制（NOT_VERIFIABLE）
- historical TASK-Q01C scientific-run main command：the command was never persisted by the original TASK-Q01C environment.json (commands list was empty); it cannot be reconstructed honestly

## 待主控审查
- 是否接受 --hold-after-stage 作为仅测试用的中断钩子（只暂停、不改科学语义）。
- 是否接受“阶段标记输出哈希会随后续阶段合法改写而失效”的口径（跨进程恢复仅依赖 数据检查点绑定）。
- 是否需要在未来运行中把 s50_verify 的终端事件纳入 S50 内的证据文件。