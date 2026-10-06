# REPRODUCTION AND ATTACHMENT AUDIT

日期：2026-09-25。

## 1. 现有可复现证据

| 类别 | 证据 | 状态 |
|---|---|---|
| 原始数据清单 | `solution/outputs/audit/raw_source_manifest.csv`、`dataset_registry.csv` | 存在；路径/大小核验，41个CSV哈希核验 |
| Q1源码 | `solution/src/quality_q01c*.py`、正式run `code_snapshot/` | 存在；主命令曾有历史`NOT_VERIFIABLE` |
| Q1检查点/恢复 | Q01C-R2 `midstage_interruption/`、`checkpoint_manifest.json` | 存在；13/13检查通过 |
| B/C/Q2/Q3/Q4源码 | 各正式run的`code/`和`code_snapshot/` | 存在；正式run称逐文件一致 |
| 环境记录 | 各run `environment.json`；`solution/outputs/audit/environment.json` | 存在；多为单机临时记录，无统一lock |
| 输入/输出清单 | 各run `input_manifest.json`、`output_manifest.json` | 存在；本次独立复核347项全部匹配 |
| verifier | 各正式run `verification.json`、verifier脚本 | 存在；Q01C 20/20、T03E 17/17、T05 28/28、T07 39/39、T08 32/32等 |
| 绘图源 | `solution/outputs/*_source.csv`及旧`plot_baselines.py` | 部分存在；正式图未生成 |
| AI记录 | `solution/README.md`、部分代码头注释 | 不完整；无最终AI披露 |

## 2. 复现阻断项

1. 根目录和`solution/`均无`requirements.txt`、`environment.yml`、`pyproject.toml`或lock文件。
2. `solution/README.md`仍说“当前阶段：数据审计和首轮基线”，不含正式run的统一入口。
3. 旧Q01C主命令未在环境JSON中持久化，历史状态保留为`NOT_VERIFIABLE`。
4. 没有一键复跑脚本；不同正式run依赖不同分支源码快照。
5. 原始数据约551 MB，不宜进入50 MB附件；当前solution约1.61 GB，diagnostics约486 MB，不能整包上传。
6. `solution/outputs/quality_q01c/20260924T215718+08/`单目录约264 MB，仅大Parquet/checkpoint就远超附件预算。
7. 旧基线图脚本修改时间晚于部分图文件，不能声称当前脚本原样生成所有旧图。
8. 23/48选定的正式/核心Python文件前20行没有AI辅助注释，不满足附件4的代码前置披露要求。

## 3. 推荐附件清单

目标：可审查、可复现、<50 MB，不携带原始数据。

必须包含：

- `README_REPRODUCE.md`：环境、数据路径、运行顺序、预期输出。
- `requirements-lock.txt`或`environment.yml`：Python、NumPy、pandas、pyarrow、SciPy、scikit-learn、Matplotlib等精确版本。
- `config/`：项目配置和正式run合同。
- `src/`：正式run对应的`code/`或`code_snapshot/`，去掉`__pycache__`。
- `evidence/formal_runs/`：保留`input_manifest.json`、`output_manifest.json`、`checks.json`、`verification.json`、`run_summary.json`、`handoff.md`。
- `results/`：只保留正文/附录引用的CSV、JSON和必要的小Parquet；大Parquet转为压缩摘要或排除。
- `figures/`：最终正文图和源数据。
- `tables/`：最终表格和源数据。
- `AI_DISCLOSURE.md`：工具、版本、日期、使用环节、人工核验方法。
- `SOURCE_MAP.md`：论文图表/数字到run和manifest字段的映射。

## 4. 绝对不要进入提交附件

- `F题/real_attachments/**`（原始比赛数据，约526 MB）。
- `tmp/**`、`__pycache__/**`、`.pyc`、临时日志、fixture、rejection tests。
- `_aborted_attempts/**`和所有失败/中间run。
- 全量`diagnostics/**`、全量`solution/outputs/**`。
- `quality_features_scores.parquet`及大型checkpoint Parquet（除非评审明确要求且可分卷）。
- `参考资料/**`、成品论文、模板副本、AI检测提示词。
- 00–05中未清理的内部过程文档；可保留精简状态说明。
- 任何包含学校、队号、姓名、账号、路径隐私或未脱敏身份信息的截图/日志。

## 5. 复现检查命令要求

最终附件至少要附：

```text
python -m pip install -r requirements-lock.txt
python run_all.py --paper-only
```

`run_all.py`应先验证输入manifest，再按Q1→Q2→Q3→Q4顺序调用固定run脚本，禁止在线重选模型；最后生成校验摘要。当前没有此文件。

## 6. 附件结论

- 当前没有可上传附件包。
- 现存的正式run证据质量较好，适合筛选后进入附件。
- 不能按“整个项目目录压缩”提交，50 MB限制和隐私/历史冗余都会导致失败。
