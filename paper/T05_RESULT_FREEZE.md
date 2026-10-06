# T05 Loss–Benchmark结果冻结接口

日期：2026-09-25。资格：TASK-T05主控验收通过并关闭。正式证据目录为`diagnostics/TASK-T05/20260925T113355+0800/`。

## 最终资格

`CONDITIONAL_ASSOCIATION_ONLY`。现有证据不能升级为`IDENTIFIED_PREDICTIVE_BRIDGE`，也不支持因果解释。

## 样本与来源边界

- C8候选底座有1854个六任务完整模型、6个partial模型；4个损坏JSON只影响覆盖且不赋分。
- 完整桥接数据45个模型：主可比层为7个C5 High/Pythia模型，条件来源迁移层为38个C6 Medium模型。
- `google/gemma-7b-it`为partial，已排除于完整六任务桥接。
- C5是C6的精确43行子集，10个共同字段逐值一致；C6 High的7个主层模型不是独立验证样本。
- 主层只使用同一模型、同一验证集、最终checkpoint的C5 High Loss。38个Medium记录没有观测D，未插补。

## 模型与验证结论

六个benchmark任务及辅助均值在7个主层模型上全部选择`CONSTANT`。时间切点`2024-09-01`在指标计算前封存；时间外验证未通过。主层只有一个Pythia模型族，无法完成可靠的留模型族升级；也没有主层`>=20B`的独立规模外验证。因此不能把未选中的规模、Loss或时间候选用于正式预测。

`time_trend.available=false`且`validated_for_extrapolation=false`。六任务向量是正式输出，`benchmark_mean_aux`仅作辅助。

## T08允许使用

- 使用冻结常数模型和逐任务残差进行条件关联描述；
- 将`observed - fitted`称为“非规模关联残差”或“条件剩余项”；
- 按模型族、规模层、开放/许可、时间和任务做带分母的描述性分层；
- 把未来12/24个月结果写成预注册假设下的`SCENARIO_FORECAST`；
- 单独报告Loss空间缩放情景及其支持域。

## T08禁止使用

- 不得声称已有可靠统一Loss→Benchmark映射；
- 不得把条件残差称为因果技术或算法进步；
- 不得把C6 High当独立测试，或把C6 Medium当同口径验证；
- 不得插补Medium缺失D；
- 不得因常数模型结果不漂亮而改选SIZE/LOSS模型；
- 不得用简单时间回归做确定性12/24月benchmark预测；
- 不得把六任务均值代替任务向量。

正式output manifest 34项当前全部匹配；四项源码与snapshot逐文件一致。独立verifier未导入执行模块，28/28检查通过。
