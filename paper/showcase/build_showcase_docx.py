from __future__ import annotations
from pathlib import Path
import re
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Cm, Pt
from docx_helpers import *
from showcase_data import ROOT, SHOW, TABLES, REFS, export_tables_and_maps

FIG=SHOW/'showcase_figures'
OUT_DOCX=SHOW/'SHOWCASE_MANUSCRIPT_V0_9.docx'
OUT_SOURCE=SHOW/'SHOWCASE_SOURCE.md'
V1=ROOT/'paper'/'manuscript'/'FULL_MANUSCRIPT_V1.md'
RAW=V1.read_text(encoding='utf-8').splitlines()
SRC=[]

def clean_line(s):
    s=s.strip()
    if not s or s.startswith('|') or s.startswith('>') or s.startswith('【') or s.startswith('图') and '占位' in s or s.startswith('表') and '占位' in s:
        return None
    if any(x in s for x in ['尚未','未冻结','当前没有','不填写','待补','BLOCKED','HOLD','占位','附表A1占位']):
        return None
    if s.startswith('『') or s.startswith('`'):
        return None
    s=s.replace('**','').replace('`','')
    reps={
        'CONDITIONAL_ASSOCIATION_ONLY':'仅条件关联','NOT_IDENTIFIABLE_PROGRESS':'进展不可识别','NOT_IDENTIFIABLE':'不可识别',
        'CONSTANT':'常数模型','SCENARIO_ONLY':'情景','FIXED_P0_NOT_OPTIMIZED':'p固定且不优化',
        'NOT_IDENTIFIED_NOT_OPTIMIZED':'Q不可识别且不优化','CONFLICT_EVIDENCE':'冲突证据','NO_NUMERIC_OPTIMUM':'无数值最优解',
        'OUT_OF_SUPPORT':'超出支持域','UNVALIDATED_FOR_EXTRAPOLATION':'时间外推未验证','CONDITIONAL_BASELINE_ONLY':'仅条件基线'
    }
    for a,b in reps.items(): s=s.replace(a,b)
    if re.match(r'^(L0|M0_6|MQ-add|MQ-eff\s*=|hat L|Q_C|Q_baseline(?:\(r\))?\s*=|N_phys|C_total|κ\(H\)|Λ=|∇|μ_|partial|eta\s*=|G_EXP|G_POWER|G_LOG|scale_associated_component|conditional_remainder|observed\s*=|dMQ-add|dN_B|dD_B|=6N|\+D_phys|\+ηN|\+μ_|H_crit\s*=)',s):
        return None
    if s.startswith('### ') or s.startswith('## ') or s.startswith('# '): return None
    return s

def segment(a,b):
    out=[]
    for line in RAW[a-1:b]:
        c=clean_line(line)
        if c: out.append(c)
    return out

def H(level,text):
    SRC.append(('#'*level)+' '+text)
    if level==1: add_h1(DOC,text)
    elif level==2: add_h2(DOC,text)
    else: add_h3(DOC,text)

def P(text,indent=True,source=True):
    if not text: return
    add_para(DOC,text,first=indent)
    if source: SRC.append(text)

def FORM(text,num):
    add_formula(DOC,text,num); SRC.append(f'$$ {text} ({num}) $$')

def FIGURE(file,cap):
    add_figure(DOC,FIG/file,cap); SRC.append(f'![{cap}](showcase_figures/{file})')

def TABLE(n):
    add_table(DOC,TABLES[n]); SRC.append(f'[{TABLES[n]["title"]}](showcase_tables/{TABLES[n]["file"]})')

def add_segment(lines):
    for x in lines:
        if x.startswith('- ') or x.startswith('1. ') or x.startswith('2. ') or x.startswith('3. ') or x.startswith('4. ') or x.startswith('5. ') or x.startswith('6. ') or x.startswith('7. ') or x.startswith('8. '): P(x,indent=False)
        else: P(x)

def cover(DOC):
    for _ in range(2): DOC.add_paragraph()
    add_title(DOC,'中国研究生创新实践系列大赛',15)
    add_title(DOC,'“华为杯”第二十三届中国研究生数学建模竞赛',16)
    DOC.add_paragraph()
    add_title(DOC,'算力约束下提升大语言模型能力的资源配置建模',20)
    add_title(DOC,'F题',14)
    for _ in range(4): DOC.add_paragraph()
    add_title(DOC,'阶段性完整候选稿 / INTERNAL REVIEW VERSION',15)
    add_title(DOC,'2026年9月25日',12)
    add_title(DOC,'当前科学版本：T06 / T07 / T05 / T08 冻结接口',10.5)

def setup_sections(doc):
    sec=doc.sections[0]; sec.page_width=Cm(21); sec.page_height=Cm(29.7); sec.top_margin=Cm(2.5); sec.bottom_margin=Cm(2.3); sec.left_margin=Cm(2.7); sec.right_margin=Cm(2.7); sec.header.is_linked_to_previous=False; sec.footer.is_linked_to_previous=False
    for p in sec.header.paragraphs: p.text=''
    sec2=doc.add_section(WD_SECTION.NEW_PAGE)
    for s in (sec2,):
        s.page_width=sec.page_width; s.page_height=sec.page_height; s.top_margin=sec.top_margin; s.bottom_margin=sec.bottom_margin; s.left_margin=sec.left_margin; s.right_margin=sec.right_margin; s.header.is_linked_to_previous=False; s.footer.is_linked_to_previous=False
    page_start(sec2,1); add_page_number_footer(sec2)
    return sec2

def new_numbered_section(doc,start=None):
    s=doc.add_section(WD_SECTION.NEW_PAGE); base=doc.sections[0]
    s.page_width=base.page_width; s.page_height=base.page_height; s.top_margin=base.top_margin; s.bottom_margin=base.bottom_margin; s.left_margin=base.left_margin; s.right_margin=base.right_margin; s.header.is_linked_to_previous=False; s.footer.is_linked_to_previous=False; add_page_number_footer(s);
    if start is not None: page_start(s,start)
    return s

def build():
    export_tables_and_maps()
    global DOC, SRC
    DOC=Document(); configure_styles(DOC); cover(DOC)
    sec2=setup_sections(DOC)
    add_title(DOC,'算力约束下提升大语言模型能力的资源配置建模',16)
    add_title(DOC,'摘  要',15)
    abstract=segment(5,11)
    for x in abstract: P(x)
    p=DOC.add_paragraph(); p.paragraph_format.first_line_indent=Pt(0); r=p.add_run('关键词：'); set_run_font(r,cn='SimHei',size=12,bold=True); r=p.add_run('大语言模型；数据质量；缩放律；算力约束；RegMix；Loss–Benchmark桥接；条件情景'); set_run_font(r,size=12)
    SRC += ['## 摘要','']+abstract+['','关键词：大语言模型；数据质量；缩放律；算力约束；RegMix；Loss–Benchmark桥接；条件情景','']
    new_numbered_section(DOC,start=2); add_title(DOC,'目  录',15); add_toc(DOC); SRC += ['## 目录','','目录由Word域更新生成。','']

    new_numbered_section(DOC,start=3)
    H(1,'1  引言'); H(2,'1.1  问题背景'); add_segment(segment(19,22)); H(2,'1.2  问题重述'); add_segment(segment(23,46))
    H(1,'2  总体分析'); H(2,'2.1  总体建模思路')
    P('本文把四问组织为“数据侧关系—参数侧缩放—预算侧优化—能力侧识别”的链路。数据侧先统一质量、冲突与配比口径；参数侧以M0_B1为正式主模型，并在B6来源内检验质量候选；预算侧在冻结支持域内优化N_B和D_B；能力侧先检查Loss–Benchmark是否具备预测桥资格，再决定是否生成未来数值。')
    P('该路线把证据分为来源内条件关系、跨来源情景、不可识别量和冲突证据。跨源结果只说明给定假设下的条件表现，不写成已估计参数。')
    H(2,'2.2  总体流程图'); FIGURE('fig1_modeling_framework.png','图1  四问建模主线与证据分层框架。跨来源映射和未来输出均保留条件资格。')
    add_segment(segment(62,88))

    H(1,'3  模型假设'); add_segment(segment(115,145))
    H(1,'4  符号说明'); add_segment(segment(147,199)); TABLE(1)

    H(1,'5  模型建立与求解')
    H(2,'5.1  问题一')
    H(3,'5.1.1  数据预处理'); add_segment(segment(206,230)); FORM('Q_baseline(r) = [q_u(r)+q_k(r)+q_e(r)]/3',1)
    H(3,'5.1.2  综合质量评分'); add_segment(segment(253,272)); TABLE(3); FIGURE('fig2_q1_quality_conflict.png','图2  问题一质量评价、记录覆盖与冲突诊断。数据来源于Q01C正式质量run。')
    H(3,'5.1.3  冲突定义与消解'); add_segment(segment(231,240)); add_segment(segment(273,294)); FORM('D_range(r) = max_g q_g(r) - min_g q_g(r)',2); FORM('Q_C(r) = Q_baseline(r)[1-0.02P(r)], P(r)=[p_top2gram(r)+p_top3gram(r)]/2',3); P('本展示稿把A18文字核验和扩展集主动修正列为适用边界：当前数值结论只基于操作性评分的内部稳定性，不据此宣称人工文本质量认证。',indent=True)
    H(3,'5.1.4  领域配比模型'); add_segment(segment(241,252)); FORM('hat L_j(p) = sum_{i=1}^{17} beta_{ij} p_i, j=1,...,13',4)
    H(3,'5.1.5  结果与验证'); add_segment(segment(295,318)); TABLE(4); FIGURE('fig3_regmix_validation.png','图3  RegMix同尺度检验与跨尺度运输。右图仅使用1M检验配方；60M/1B只报告运输误差。')

    H(2,'5.2  问题二')
    H(3,'5.2.1  经典标度律'); add_segment(segment(324,357)); FORM('L_0(N_B,D_B) = E + A_N N_B^{-alpha_N} + B_D D_B^{-beta_D}',5); TABLE(5); FIGURE('fig4_b1_scaling_fit.png','图4  B1来源内M0_B1预测—实测与残差诊断。仅用于来源内拟合诊断。')
    H(3,'5.2.2  质量关系'); add_segment(segment(358,400)); FORM('MQ-add(N_B,D_B,Q_score)=M0_6(N_B,D_B)-k_add(Q_score-0.6), 0.1<=Q_score<=0.6',6)
    H(3,'5.2.3  配比关系'); add_segment(segment(419,434))
    H(3,'5.2.4  分层广义关系'); add_segment(segment(401,418)); add_segment(segment(435,447)); P('形式上可写L(N,D,Q,p)=L_0(N,D)+Delta_Q(Q_B)+Delta_p(p)，但当前数据不能同时识别A/B质量映射、质量效应和配比效应，因此该式不是已拟合的统一模型。',indent=True); FORM('L(N,D,Q,p)=L_0(N,D)+Delta_Q(Q_B)+Delta_p(p)',7)
    H(3,'5.2.5  边际、弹性与替代'); add_segment(segment(477,492)); FORM('partial L/partial x = -sKx^{-s-1}, E_x=Kx^{-s}/L',8); P('在MQ-add来源内，保持Loss不变时局部替代关系为 dQ/dN=-[A_6 alpha_6 N_B^{-alpha_6-1}]/k_add。该式只表示条件模型中的局部替代率，不能提升为真实因果兑换。',indent=True)
    H(3,'5.2.6  当前识别边界'); add_segment(segment(493,514)); TABLE(6)

    H(2,'5.3  问题三')
    H(3,'5.3.1  成本函数'); add_segment(segment(518,552)); FORM('C_total(N,D,Q_A,H)=6ND+D[g(Q_A)-g(Q_0)]_+ + eta N D H',9); FORM('kappa(H)10^18 N_B D_B <= C_budget, kappa(H)=6+eta H',10)
    H(3,'5.3.2  优化模型'); add_segment(segment(553,581)); FORM('min L_0(N_B,D_B) s.t. C_total<=C_budget, N_B in [N_lo,N_hi], D_B in [D_lo,D_hi]',11)
    H(3,'5.3.3  三档预算结果'); add_segment(segment(602,625)); TABLE(7); FIGURE('fig5_budget_optima.png','图5  三档预算条件最优N_B、D_B和预测Loss。10^22档D_B触B1支持上界。')
    H(3,'5.3.4  KKT与结构转移'); add_segment(segment(582,601)); FORM('grad L_0 = -lambda grad C_total, N_B partial L_0/partial N_B = D_B partial L_0/partial D_B',12); FORM('H_crit=6/eta=30000',13)
    H(3,'5.3.5  H敏感性'); add_segment(segment(626,662)); TABLE(8); FIGURE('fig6_h_sensitivity.png','图6  上下文H敏感性。虚线为H_crit=30000；该图不表示物理相变。')
    H(3,'5.3.6  情景分析'); add_segment(segment(663,733))

    H(2,'5.4  问题四')
    H(3,'5.4.1  Benchmark口径'); add_segment(segment(779,801))
    H(3,'5.4.2  Loss–Benchmark识别性'); add_segment(segment(802,819)); FORM('Y_t(x)=m_t(x)+epsilon_t',14); P('其中epsilon_t为条件剩余项，桥接关系仅保留条件关联资格。',indent=True)
    H(3,'5.4.3  当前历史分层'); add_segment(segment(844,857))
    H(3,'5.4.4  当前规模/非规模分析'); add_segment(segment(820,843)); FORM('g_t(x_i)=m_t(x_i)-m_t(x_ref), r_i=Y_i-m_t(x_i)',15)
    H(3,'5.4.5  当前未来情景资格'); add_segment(segment(858,912)); TABLE(9); FIGURE('fig7_q4_task_baseline_interval.png','图7  六任务条件基线与条件区间。当前口径为PROVISIONAL_Q4_CURRENT_FREEZE；区间不是未来预测区间。')

    H(1,'6  模型检验与灵敏度分析')
    for txt in [
        '问题一的检验包括记录分母、方向映射、三组聚合和规则稳定性。主Q有效261067条、缺失19条，未用插补掩盖；Q_C在c4、commoncrawl、wikipedia三个活跃域通过200次重采样和留出稳定性检查。',
        '问题二采用G1—G4确认性门槛：固定规模组内质量方向、留组预测、重采样稳定性和参数profile数值识别性。四项通过只支持B6来源内条件关系，不把A/B桥接、跨源运输或B8冲突升级。',
        '问题三同时检查预算、N/D支持、三项成本、预测Loss、Lagrange乘子和KKT残差。三档主结果最大KKT残差为2.793×10^-8，最大相对预算越界为9.4036×10^-13；1e22的D上界是冻结支持域下的边界解。',
        '问题四执行样本身份、任务覆盖、时间切点、留族和主层规模外验证。六个任务和辅助均值均选择常数模型，时间外验证未通过；条件区间不是迁移或预测区间。',
        'T06、T07、T05、T08的正式run均提供output manifest和独立verifier。核心数字可按FIGURE_SOURCE_MAP.csv和TABLE_SOURCE_MAP.csv回溯。'
    ]: P(txt)

    H(1,'7  模型评价'); H(2,'7.1  优点'); add_segment(segment(917,926)); H(2,'7.2  局限性'); add_segment(segment(929,939)); H(2,'7.3  推广边界'); add_segment(segment(941,943))
    H(1,'8  模型改进与推广')
    P('改进方向首先是为A/B质量建立同来源、同模型的配对观测并预注册可估计桥接函数；其次扩展模型族和规模层，使Loss–Benchmark桥能够完成留族与≥20B独立外验证；再次为RegMix配比补充跨尺度重标定或直接实验；最后进行A18原文和扩展集冲突稳定性的人工标注核验。')
    P('本文方法适用于来源明确、支持域可审计、质量与规模变量需要分层解释的资源分配问题。推广时应先检查识别性，再给条件最优解，最后分别报告参数不确定性、模型选择不确定性和结构不确定性。')
    H(1,'9  结论'); add_segment(segment(947,949)); TABLE(10)

    H(1,'参考文献')
    for r in REFS: P(r,indent=False)
    H(1,'AI工具使用说明')
    for t in [
        '工具名称：OpenAI Codex桌面应用；开发机构：OpenAI；使用日期：2026-09-25。当前客户端未向本地工作区提供可公开核对的具体模型快照编号，因此本文不填写未经核实的版本号；最终提交前应由参赛队依据实际运行记录补齐。',
        '使用范围：辅助整理输入文件、编排写作结构、生成图表和DOCX排版检查。未替代题目数据，未生成G1/G2/G4未来结果，未从参考论文复制文字或数字。所有核心数值均来自项目冻结接口或原始数据文件，并记录于源映射CSV。',
        '人工核验要求：最终提交前逐项复核公式、表格数字、引用编号、工具版本与发布日期、代码注释和正文语言，确认所有AI输出已理解、修改并符合竞赛规定。'
    ]: P(t)
    H(1,'附录')
    H(2,'附录A  数据与变量'); TABLE(2); P('原始数据共登记2012个文件、约551191693字节和40个逻辑数据编号；41个原始CSV完成SHA256核验。变量来源和适用域以表2和TABLE_SOURCE_MAP.csv为准。',indent=True)
    H(2,'附录B  核心参数和验证结果'); P('Q1质量分母为272505条物理记录、261086个唯一键、261067条有效和19条缺失。Q2 M0_B1参数为E=1.6897975629820348、A_N=0.3539803206065571、B_D=1.2403055835426349、alpha_N=0.339976581941082、beta_D=0.2798781285468448。Q3和Q4核心结果分别见表7、表9。',indent=True); P('T06、T07、T05、T08的output manifest、独立verifier和源码快照保留在原run目录；展示稿只重绘图表，不改变模型、参数或筛选。',indent=True)
    H(2,'附录C  复现入口'); P('质量主run：solution/outputs/quality_q01c/20260924T215718+08/；规则稳定性：diagnostics/TASK-T03E/20260925T020032+08/；问题二集成：diagnostics/TASK-T06E-INTEGRATE/20260925T110904+08/；问题三：diagnostics/TASK-T07/20260925T113744+08/；问题四桥接：diagnostics/TASK-T05/20260925T113355+0800/；问题四分解与情景：diagnostics/TASK-T08/20260925T142203+0800/。',indent=True); P('展示稿复现脚本为paper/showcase/generate_showcase_figures.py、showcase_data.py和build_showcase_docx.py。图表来源映射分别由FIGURE_SOURCE_MAP.csv和TABLE_SOURCE_MAP.csv给出。',indent=True)

    DOC.save(OUT_DOCX)
    OUT_SOURCE.write_text('# 算力约束下提升大语言模型能力的资源配置建模\n\n> 阶段性完整候选稿 / INTERNAL REVIEW VERSION\n\n'+'\n\n'.join(SRC)+'\n',encoding='utf-8')
    write_patch_handoff()
    print(OUT_DOCX)

def write_patch_handoff():
    patch='''# 展示稿补丁映射

## G1完成后

| 位置 | 替换范围 |
|---|---|
| 5.1.3 冲突定义与消解 | 用G1正式A18文本核验和扩展集冲突稳定性结果替换当前适用边界说明 |
| 图2、表3 | 若G1改变质量分或冲突规则，重绘图2并替换表3对应行 |
| 第6章、7.2、第9章、表10 | 按G1结果升级或缩小问题一的限制表述 |

## G2完成后

| 位置 | 替换范围 |
|---|---|
| 5.2.4 分层广义关系 | 若统一L(N,D,Q,p)可识别，替换形式上分解 |
| 5.2.5 边际、弹性与替代 | 用B2—B5、B9、B10正式迁移/外推和边际数值替换一般表达式 |
| 表5、表6、图4 | 补入G2新增参数、验证、资格和适用域 |
| 第6章、7.2、第9章、表10 | 按G2正式结果更新边界 |

## G4完成后

| 位置 | 替换范围 |
|---|---|
| 5.4.2—5.4.5 | 替换桥接识别、历史分层、规模/非规模分解和未来情景资格 |
| 图7、表9 | 当前为PROVISIONAL_Q4_CURRENT_FREEZE；G4改变任务向量或区间时必须替换 |
| 第6章、7.2、第9章、表10 | 仅当G4通过正式验证时替换未来数值；否则保留不可识别负结论 |
'''
    (SHOW/'SHOWCASE_PATCH_MAP.md').write_text(patch,encoding='utf-8')
    handoff='''# SHOWCASE HANDOFF

当前科学版本：T06 / T07 / T05 / T08。Q1、Q2、Q4为GAP_CLOSURE阶段展示，Q3为CLOSED_WITH_LIMITATION。

- DOCX：paper/showcase/SHOWCASE_MANUSCRIPT_V0_9.docx
- PDF：paper/showcase/SHOWCASE_MANUSCRIPT_V0_9.pdf
- 正文源：paper/showcase/SHOWCASE_SOURCE.md
- 图表：paper/showcase/showcase_figures/、paper/showcase/showcase_tables/
- 来源映射：FIGURE_SOURCE_MAP.csv、TABLE_SOURCE_MAP.csv

G1替换5.1.3、图2、表3、第6章、7.2、第9章和表10；G2替换5.2.4、5.2.5、表5、表6、图4、第6章、7.2、第9章和表10；G4替换5.4.2—5.4.5、图7、表9、第6章、7.2、第9章和表10。详细锚点见SHOWCASE_PATCH_MAP.md。

本文件对应阶段性内部展示稿，不得称为最终提交版。
'''
    (SHOW/'SHOWCASE_HANDOFF.md').write_text(handoff,encoding='utf-8')

if __name__=='__main__': build()




