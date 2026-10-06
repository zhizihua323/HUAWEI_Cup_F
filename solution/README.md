# F题研究与复现工作区

本目录保存自行计算的分析源码、审计结果、模型结果和论文素材。原始材料始终从上一级 `F题/real_attachments` 只读加载，不修改或复制成另一份事实来源。

当前阶段：数据审计和首轮基线试验。所有模型结果均需结合适用范围与验证结果解释，尚非提交定稿。

## 运行环境

已检测用户Python：`D:\anaconda\python.exe`，Python 3.13.9，numpy 2.3.5，pandas 2.3.3，scipy 1.16.3，scikit-learn 1.7.2，matplotlib 3.10.6，pyarrow 21.0.0。

已检测Matlab启动器：`D:\MATLAB\bin\matlab.exe`。版本、许可与工具箱以实际启动检查为准。

本轮主要使用用户现有Python环境。脚本在任意当前目录运行时均应从自身路径定位数据。随机种子统一为20260924。所有基线与审计文件写入 `outputs`，论文素材写入 `reports`。

## 文件约定

- `src/common.py`：路径、输出与随机种子等共享功能。
- `src/quality_audit.py`：A1–A3质量信号审计、语义核验与可行时的质量基线。
- `src/mixture_baseline.py`：A4–A15配比数据审计和训练/检验基线。
- `src/scaling_baseline.py`：B数据审计、经典标度律与质量效应可识别性检查。
- `src/evolution_audit.py`：C数据审计、逐任务聚合与历史演进的初步检查。
- `reports`：方法、假设、限制与结果说明。

## AI辅助记录

本目录代码在OpenAI Codex辅助下完成。开发机构：OpenAI；使用日期：2026-09-24。精确模型/版本标识及版本发布日期尚待界面或正式来源核对，不填写推测信息。参赛团队须理解、审核、复跑后决定采用范围；最终提交时补齐实际使用工具信息。
