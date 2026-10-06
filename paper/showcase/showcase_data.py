from __future__ import annotations
from pathlib import Path
import csv

ROOT = Path(__file__).resolve().parents[2]
SHOW = ROOT / "paper" / "showcase"
TAB = SHOW / "showcase_tables"
TAB.mkdir(parents=True, exist_ok=True)

S = {
    "q01c_audit": "solution/outputs/quality_q01c/20260924T215718+08/audit.json",
    "q01c_summary": "solution/outputs/quality_q01c/20260924T215718+08/domain_summary.csv",
    "t03e": "diagnostics/TASK-T03E/20260925T020032+08/phase_b_frozen_validation/holdout_summary.json",
    "regmix_validation": "diagnostics/TASK-T06E-P/20260925T075729+08/mixture_audit/regmix_fixed_model_validation.csv",
    "t06_contract": "diagnostics/TASK-T06E-INTEGRATE/20260925T110904+08/t07_model_contract.json",
    "t06_params": "diagnostics/TASK-T06E-INTEGRATE/20260925T110904+08/t07_parameter_table.csv",
    "t06_gates": "diagnostics/TASK-T06E-B-R1/20260925T103130+08/corrected_gates/G1_G4_reconciliation.json",
    "b1_fit": "diagnostics/TASK-T06E-B/20260925T100306+08/fit/full_fit_predictions.csv",
    "t07_main": "diagnostics/TASK-T07/20260925T113744+08/budget_scenario_optima.csv",
    "t07_context": "diagnostics/TASK-T07/20260925T113744+08/context_sensitivity.csv",
    "t07_unc": "diagnostics/TASK-T07/20260925T113744+08/uncertainty_summary.csv",
    "t07_verify": "diagnostics/TASK-T07/20260925T113744+08/verification.json",
    "t05_decision": "diagnostics/TASK-T05/20260925T113355+0800/identifiability_decision.json",
    "t05_summary": "diagnostics/TASK-T05/20260925T113355+0800/run_summary.json",
    "t08_progress": "diagnostics/TASK-T08/20260925T142203+0800/taskwise_progress.csv",
    "t08_summary": "diagnostics/TASK-T08/20260925T142203+0800/run_summary.json",
    "t08_decomp": "diagnostics/TASK-T08/20260925T142203+0800/scale_non_scale_decomposition.csv",
    "t08_interface": "diagnostics/TASK-T08/20260925T142203+0800/t08_paper_interface.json",
}

TABLES = {
1: {"file":"table1_symbols.csv","title":"表1  主要符号、单位与含义","headers":["符号","单位/范围","含义"],"rows":[
["N","物理参数量","模型可训练参数总数"],["D","物理训练token数","训练语料中的token总数"],["N_B","十亿参数","N/10^9，供B1标度模型使用"],["D_B","十亿token","D/10^9，供B1标度模型使用"],["Q_A / Q_baseline","[0,1]","A侧操作性综合质量分"],["Q_B / Q_score","[0.1,0.6]","B6来源内实验质量水平"],["p","17维单纯形","训练领域配比向量"],["L","交叉熵Loss","验证集损失或模型预测损失"],["H","token","上下文长度，本文按外生变量处理"],["C","FLOPs","训练、质量增量与注意力成本合计"]],"note":"物理量与十亿单位严格区分；优化前先将N_B、D_B换算为N、D。","source":"paper/T07_RESULT_FREEZE.md；paper/T06_RESULT_FREEZE.md；原题附件A/B说明"},
2: {"file":"table2_data_assets.csv","title":"表2  数据资产、用途与问题对应","headers":["数据组","主要内容","正文用途","当前适用边界"],"rows":[
["A1—A3","质量信号样本与扩展记录","质量评分、冲突与敏感性","主Q只用11个完整特征；19条缺失不插补"],["A4—A15","RegMix训练、检验与估算配比表","17维配比到13域损失","1M同尺度支持；60M/1B为运输诊断；10B/70B为估算"],["A16—A17","领域映射与汇总","质量域对应与设计秩检查","17个训练域中6域有质量映射"],["B1","Pythia训练轨迹","来源内经典标度主模型M0_B1","仅限B1观测支持域"],["B6","质量条件实验","来源内加法质量候选MQ-add","0.1≤Q_score≤0.6"],["B8","反向共同支持实验","方向冲突证据","不合并、不解释为机制反转"],["C5/C6/C8","模型身份、Loss与六任务评测","Loss–Benchmark桥接与条件基线","主可比层7个Pythia模型；仅条件关联"]],"note":"A18原文核验和扩展集主动冲突修正未进入当前正式结论，后续补丁位置见SHOWCASE_PATCH_MAP.md。","source":"audit/FINAL_RESULT_SOURCE_OF_TRUTH.md；paper/manuscript/source_map_q1_q2.md；paper/T05_RESULT_FREEZE.md"},
3: {"file":"table3_q1_quality_core.csv","title":"表3  问题一质量评价核心结果","headers":["指标","数值","解释"],"rows":[
["物理记录数","272505","A1—A3读取记录"],["唯一键数","261086","按联合键去重"],["主Q有效/缺失","261067 / 19","缺失保留，不插补"],["覆盖率","99.9927%","有效唯一记录/唯一键"],["Q_baseline均值","0.4959665","11特征严格完整案例"],["标准差/中位数","0.1495539 / 0.4824785","主质量分布"],["P10/P90","0.3216459 / 0.6813344","低、高分位"],["三组均值","可用性0.6030192；知识性0.5341025；教育推理0.3507774","等组权聚合"],["平均分歧范围","0.3030182","组间最大值减最小值"],["分歧范围>0.5","6.3427%","预注册冲突诊断比例"]],"note":"Q_baseline是操作性综合分，不等同于人工真值或已校准的B侧质量。","source":S["q01c_summary"]+"；"+S["q01c_audit"]},
4: {"file":"table4_regmix_validation.csv","title":"表4  RegMix同尺度检验与跨尺度运输","headers":["尺度/数据","行数","角色","MSE改善","RMSE","Spearman","资格"],"rows":[
["1M训练","512","训练拟合","55.143%","0.272275","0.545705","训练支持"],["1M检验","256","独立部署检验","55.026%","0.226978","0.625074","同尺度支持"],["60M检验","256","固定模型运输","7.101%","1.517331","0.559150","运输诊断"],["1B检验","64","固定模型运输","-5.039%","3.188945","0.372299","运输诊断"],["10B估算","63","估算情景","-2.503%","3.580457","-0.453629","非真值"],["70B估算","63","估算情景","-2.469%","3.963318","-0.516465","非真值"]],"note":"1M MSE改善和Spearman为模型选择后的同尺度结果；负改善保留，不以估算数据替代真值。","source":S["regmix_validation"]},
5: {"file":"table5_scaling_parameters.csv","title":"表5  问题二正式模型与质量候选参数","headers":["模块","参数","估计值","状态"],"rows":[
["M0_B1","E","1.6897975629820348","来源内主模型"],["M0_B1","A_N","0.3539803206065571","来源内主模型"],["M0_B1","B_D","1.2403055835426349","来源内主模型"],["M0_B1","alpha_N","0.339976581941082","来源内主模型"],["M0_B1","beta_D","0.2798781285468448","来源内主模型"],["MQ-add(B6)","E_6","1.576717897667643","条件候选"],["MQ-add(B6)","A_6","0.6003432829036089","条件候选"],["MQ-add(B6)","B_6","1.3555803863625686","条件候选"],["MQ-add(B6)","alpha_6","0.2721341490204682","条件候选"],["MQ-add(B6)","beta_6","0.2912041980912658","条件候选"],["MQ-add(B6)","k_add","0.3544081081063713","来源内质量斜率"]],"note":"M0_B1观测支持为N_B∈[0.070542,11.965825]、D_B∈[0.134,299.893]；MQ-add仅限B6来源。","source":S["t06_contract"]+"；"+S["t06_params"]},
6: {"file":"table6_q2_qualification_marginal.csv","title":"表6  问题二资格、边际与替代摘要","headers":["分析对象","正式表达","资格/解释"],"rows":[
["G1方向","45个可估组中43组为负，负方向比例95.56%","来源内方向一致性通过"],["G2 leave-N","宏RMSE由0.0791587降至0.0529372，改善33.13%","确认性预测检验通过"],["G2 leave-D","宏RMSE由0.0818619降至0.0553288，改善32.41%","确认性预测检验通过"],["G3重采样","200/200成功且200/200方向一致","条件稳定性通过"],["G4数值识别","Jacobian满秩；条件数53.9441；6个profile有限分离","数值可识别性通过"],["A/B质量桥接","Q_A与Q_score无样本级配对","不可识别；H1—H3仅情景"],["边际与弹性","∂L/∂x=-sKx^(-s-1)；弹性=Kx^(-s)/L","可在冻结来源内条件计算"],["替代条件","dQ/dN=-[A_N alpha_N N_B^(-alpha_N-1)]/k_add","仅在MQ-add来源内形式成立"],["Q_mix与p","Q_mix=p^Tq","Q_mix位于p列空间；不能作两个独立坐标"],["B8","共同支持方向与B6相反","冲突证据；不合并"]],"note":"表中导数与替代式给出条件计算形式；本展示稿不把未冻结的G2附加迁移结果写成新数值结论。","source":"paper/T06_RESULT_FREEZE.md；"+S["t06_gates"]+"；"+S["t06_contract"]},
7: {"file":"table7_budget_optima.csv","title":"表7  三档预算正式主结果与数值可行性","headers":["预算/FLOPs","N_B","D_B","预测Loss","成本分项比例","KKT残差","边界状态"],"rows":[
["10^18","0.078248576","1.993850677","3.553996156","训练93.61%；注意力6.39%","1.364e-8","预算活跃；N、D内点"],["10^20","0.625922700","24.925757775","2.609142026","训练93.61%；注意力6.39%","2.360e-9","预算活跃；N、D内点"],["10^22","5.202388053","299.893000000","2.143211279","训练93.61%；注意力6.39%","0","预算与D上界活跃"]],"note":"N_B单位为十亿参数，D_B单位为十亿token；主模型Q、p均不优化。最大相对预算越界为9.4036e-13。","source":S["t07_main"]+"；"+S["t07_verify"]},
8: {"file":"table8_h_structural_transition.csv","title":"表8  上下文敏感性与结构变化关键点","headers":["预算/FLOPs","H","N_B","D_B","预测Loss","状态"],"rows":[
["10^18","2048","0.078248576","1.993850677","3.553996156","训练项主导；预算活跃"],["10^18","32768","0.070542000","1.129233998","3.760548676","N下界活跃；注意力项主导"],["10^18","131072","0.070542000","0.440050161","4.122370979","N下界活跃；Loss上升"],["10^20","2048","0.625922700","24.925757775","2.609142026","训练项主导；预算活跃"],["10^20","32768","0.462066369","17.239606686","2.709075632","注意力项主导"],["10^20","131072","0.301928905","10.281234401","2.867729717","注意力项主导"],["10^22","2048","5.202388053","299.893000000","2.143211279","D上界活跃"],["10^22","4096","4.889902989","299.893000000","2.147511844","D上界活跃"],["10^22","8192","4.625641625","283.025535111","2.155552218","D上界退出；转为内点"],["10^22","131072","2.415177499","128.528932110","2.270704237","注意力项主导"]],"note":"H_crit=6/eta=30000。结构转移只指活跃约束集合或弹性排序变化，不称物理相变。","source":S["t07_context"]},
9: {"file":"table9_q4_task_baseline.csv","title":"表9  问题四六任务条件基线与条件区间","headers":["Benchmark","常数基线/分","条件区间/分","规模关联项","未来12/24月增量"],"rows":[
["IFEval","22.165078","[18.533524, 26.172209]","0","不可识别"],["BBH","30.840380","[29.197147, 32.272010]","0","不可识别"],["MATH Lvl 5","1.068192","[0.345274, 1.747950]","0","不可识别"],["GPQA","25.491371","[24.646453, 26.300336]","0","不可识别"],["MuSR","36.451247","[32.974301, 39.625850]","0","不可识别"],["MMLU-PRO","11.284195","[11.045743, 11.501670]","0","不可识别"],["六任务均值（辅助）","21.216744","[20.737287, 21.656458]","0","不可识别"]],"note":"区间为主可比层7个Pythia模型上常数模型的条件区间，不是未来预测区间；均值只作辅助。","source":S["t08_progress"]+"；"+S["t08_interface"]},
10: {"file":"table10_conclusions_boundaries.csv","title":"表10  四问主要结论与适用边界","headers":["问题","当前可确认结论","不能外推的边界"],"rows":[
["问题一","11特征主Q；3组等权；1M配比约55.03% MSE改善","A/B质量不成统一尺度；跨尺度配比不重标定；A18未闭合"],["问题二","M0_B1主模型；B6 MQ-add条件接受；B8冲突保留","不能写统一L(N,D,Q,p)、因果质量效应或跨源最优"],["问题三","三档预算条件最优N/D；KKT与Hcrit=30000","1e22的D触上界；Q/p不联合优化；成本函数均为情景"],["问题四","六任务常数条件基线；非规模关联残差可描述","无统一Loss→Benchmark桥；时间外推不可识别；不生成未来数值"]],"note":"本表是展示稿的适用边界总表；结论以T06/T07/T05/T08冻结接口为准。","source":"paper/T06_RESULT_FREEZE.md；paper/T07_RESULT_FREEZE.md；paper/T05_RESULT_FREEZE.md；paper/T08_RESULT_FREEZE.md"},
}

REFS = [
"[1] Bahri Y, Dyer E, Kaplan J, et al. Explaining neural scaling laws[J]. Proceedings of the National Academy of Sciences, 2024, 121(27). DOI:10.1073/pnas.2311878121.",
"[2] Kaplan J, McCandlish S, Henighan T, et al. Scaling laws for neural language models[EB/OL]. arXiv:2001.08361, 2020.",
"[3] Hoffmann J, Borgeaud S, Mensch A, et al. Training compute-optimal large language models[C]//Advances in Neural Information Processing Systems. 2022, 35.",
"[4] Xia M, Gao G, Wang C, et al. RegMix: Data mixture as regression for language model pre-training[C]//Proceedings of the 41st International Conference on Machine Learning. 2024.",
"[5] Biderman S, Schoelkopf H, Anthony Q, et al. Pythia: A suite for analyzing large language models across training and scaling[C]//Proceedings of the 40th International Conference on Machine Learning. 2023, 202:2398-2435.",
"[6] Asai A, et al. A large-scale study of data quality and composition for language model pre-training[J]. Nature, 2026, 650:857-863. DOI:10.1038/s41586-025-10072-4.",
"[7] Schaeffer R, Miranda B, Koyejo S. Are emergent abilities of large language models a mirage?[C]//Advances in Neural Information Processing Systems. 2023, 36.",
"[8] Penedo G, Kydlíček H, Ben Allal L, et al. The FineWeb datasets: Decanting the web for the finest text data at scale[EB/OL]. arXiv:2406.17557, 2024.",
"[9] Warner B, Chaffin A, Clavié B, et al. Smarter, better, faster, longer: A modern bidirectional encoder for fast, memory efficient, and long context finetuning and inference[EB/OL]. arXiv:2412.13663, 2024.",
"[10] Zhou J, Lu T, Mishra S, et al. Instruction-following evaluation for large language models[EB/OL]. arXiv:2311.07911, 2023.",
"[11] Suzgun M, Scales N, Schärli N, et al. Challenging BIG-Bench tasks and whether chain-of-thought can solve them[EB/OL]. arXiv:2210.09261, 2022.",
"[12] Hendrycks D, Burns C, Kadavath S, et al. Measuring mathematical problem solving with the MATH dataset[EB/OL]. arXiv:2103.03874, 2021.",
"[13] Rein D, Hou B L, Stickland A C, et al. GPQA: A graduate-level Google-proof Q&A benchmark[EB/OL]. arXiv:2311.12022, 2023.",
"[14] Sprague Z, Ye X, Bostrom K, et al. To CoT or not to CoT? Chain-of-thought helps mainly on math and symbolic reasoning[EB/OL]. arXiv:2406.01506, 2024.",
"[15] Wang Y, Ma X, Zhang G, et al. MMLU-Pro: A more robust and challenging multi-task language understanding benchmark[EB/OL]. arXiv:2406.01574, 2024.",
"[16] Koenker R, Bassett G. Regression quantiles[J]. Econometrica, 1978, 46(1):33-50.",
"[17] Chernozhukov V, Fernández-Val I, Galichon A. Quantile and probability curves without crossing[J]. Econometrica, 2010, 78(3):1093-1125.",
]

def export_tables_and_maps():
    src=[]
    for n,t in TABLES.items():
        path=TAB/t['file']
        with path.open('w',newline='',encoding='utf-8-sig') as f:
            w=csv.writer(f); w.writerow(t['headers']); w.writerows(t['rows'])
        src.append([f'表{n}',t['title'],path.relative_to(ROOT).as_posix(),t['source'],t['note']])
    with (SHOW/'TABLE_SOURCE_MAP.csv').open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.writer(f); w.writerow(['table_id','title','table_csv','source_files','note']); w.writerows(src)
    figs=[
    ['图1','四问建模主线与证据分层','paper/showcase/showcase_figures/fig1_modeling_framework.png','paper/FINAL_RESULT_INDEX.md；T06/T07/T05/T08冻结接口','结构图为作者绘制，不含新数值','CURRENT_FREEZE'],
    ['图2','问题一质量评价与冲突分析','paper/showcase/showcase_figures/fig2_q1_quality_conflict.png',S['q01c_summary'],'由冻结汇总数值重绘','CURRENT_FREEZE'],
    ['图3','RegMix同尺度检验与跨尺度运输','paper/showcase/showcase_figures/fig3_regmix_validation.png',S['regmix_validation']+'；solution/outputs/mixture/linear_test_1m_predictions.csv','1M为检验；60M/1B仅运输；10B/70B未作图','1M_SUPPORTED_TRANSPORT_ONLY'],
    ['图4','B1经典Scaling Law预测—实测','paper/showcase/showcase_figures/fig4_b1_scaling_fit.png',S['b1_fit'],'仅绘制M0_B1来源内样本','B1_SOURCE_CONDITIONAL'],
    ['图5','三档预算条件最优N_B—D_B配置','paper/showcase/showcase_figures/fig5_budget_optima.png',S['t07_main'],'固定H=2048、Q与p不优化','CURRENT_FREEZE'],
    ['图6','上下文敏感性与结构变化','paper/showcase/showcase_figures/fig6_h_sensitivity.png',S['t07_context'],'H为外生变量；结构变化限于活跃约束集合','CURRENT_FREEZE'],
    ['图7','六任务条件基线与条件区间','paper/showcase/showcase_figures/fig7_q4_task_baseline_interval.png',S['t08_progress'],'常数模型条件输出；不含未来点预测','PROVISIONAL_Q4_CURRENT_FREEZE'],
    ]
    with (SHOW/'FIGURE_SOURCE_MAP.csv').open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.writer(f); w.writerow(['figure_id','title','figure_path','source_files','treatment','qualification']); w.writerows(figs)

if __name__=='__main__':
    export_tables_and_maps()
