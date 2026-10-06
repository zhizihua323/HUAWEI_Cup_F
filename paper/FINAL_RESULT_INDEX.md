# 最终结果索引与PAPER全文整合指令

日期：2026-09-25。状态：Q1–Q4科学建模链全部关闭；项目进入`PAPER INTEGRATION + FINAL REVIEW`。

## 唯一正式冻结接口

执行-PAPER只能使用以下四份文件中的结果、资格和限制：

1. `paper/T06_RESULT_FREEZE.md`：问题二缩放律、质量尺度桥接和联合模型边界。
2. `paper/T07_RESULT_FREEZE.md`：问题三预算约束资源配置正式结果。
3. `paper/T05_RESULT_FREEZE.md`：问题四Loss–Benchmark桥接资格与使用边界。
4. `paper/T08_RESULT_FREEZE.md`：问题四分解、历史描述与未来情景正式结果。

不得回到执行器口头汇报、旧run、superseded run、探索性表格或聊天记录中自行挑选数字。发现冻结接口之间存在冲突时停止整合并登记问题，不得自行择优。

## 现有稳定正文

- Q1/Q2：`paper/manuscript/Q1_Q2_STABLE_BODY.md`
- Q3：`paper/manuscript/Q3_STABLE_BODY.md`
- Q4：尚待严格依据`paper/T05_RESULT_FREEZE.md`与`paper/T08_RESULT_FREEZE.md`撰写。

## 执行-PAPER最终全文整合指令

1. 保留Q1/Q2稳定正文的已验收结论，只根据T06冻结接口统一符号、数字精度和限制措辞，不重做模型选择。
2. 核对Q3稳定正文与T07冻结接口逐项一致：三档预算、N/D/Loss、D上界、H临界值、质量成本、配比情景、B8冲突、KKT和参数不确定性。
3. 新写Q4时必须保留六任务向量；辅助均值不得替代单任务结果。明确主模型为CONSTANT、规模关联项为0的识别含义，并将剩余项只称条件剩余项或非规模关联残差。
4. 将2026-03-13和2027-03-13写成相对最后观测日期2025-03-13的12/24个月情景时点。不得生成未来N、D、Loss或benchmark增量数值。
5. 将六类不确定性分开叙述，不合成单一置信区间；所有`SCENARIO_ONLY`、`CONDITIONAL_ASSOCIATION_ONLY`、`NOT_IDENTIFIABLE`和`UNVALIDATED`资格必须保留。
6. 统一全文符号、单位、数据口径、表图编号和交叉引用；不得把十亿单位直接代入物理成本式，不得把相关性改写成因果。
7. 完成全文后执行一次结果数字逐项核对、禁用表述扫描、图表来源核对和参考文献/模板格式检查。该阶段只做论文整合与审阅，不新增科学模型或重新拟合。
