from pathlib import Path
p=Path(r'paper/showcase/build_showcase_docx.py')
lines=p.read_text(encoding='utf-8').splitlines()
done=False
for i,line in enumerate(lines):
    if line.strip().startswith('if re.match') and 'Q_baseline' in line:
        lines[i]="    if re.match(r'^(L0|M0_6|MQ-add|MQ-eff\\s*=|hat L|Q_C|Q_baseline(?:\\(r\\))?\\s*=|N_phys|C_total|κ\\(H\\)|Λ=|∇|μ_|partial|eta\\s*=|G_EXP|G_POWER|G_LOG|scale_associated_component|conditional_remainder|observed\\s*=|dMQ-add|dN_B|dD_B|=6N|\\+D_phys|\\+ηN|\\+μ_|H_crit\\s*=)',s):"
        done=True
        break
if not done: raise SystemExit('regex line not found')
s='\n'.join(lines)+'\n'
s=s.replace("P('形式上可写L(N,D,Q,p)=L_0(N,D)+Delta_Q(Q_B)+Delta_p(p)，但当前数据不能同时识别A/B质量映射、质量效应和配比效应，因此该式不是已拟合的统一模型。',indent=True)","P('形式上可写L(N,D,Q,p)=L_0(N,D)+Delta_Q(Q_B)+Delta_p(p)，但当前数据不能同时识别A/B质量映射、质量效应和配比效应，因此该式不是已拟合的统一模型。',indent=True); FORM('L(N,D,Q,p)=L_0(N,D)+Delta_Q(Q_B)+Delta_p(p)',7)",1)
s=s.replace("H(3,'5.4.2  Loss–Benchmark识别性'); add_segment(segment(802,819))","H(3,'5.4.2  Loss–Benchmark识别性'); add_segment(segment(802,819)); FORM('Y_t(x)=m_t(x)+epsilon_t',14); P('其中epsilon_t为条件剩余项，桥接关系仅保留条件关联资格。',indent=True)",1)
repls=[
("FORM('partial L/partial x = -sKx^{-s-1}, E_x=Kx^{-s}/L',7)","FORM('partial L/partial x = -sKx^{-s-1}, E_x=Kx^{-s}/L',8)"),
("FORM('C_total(N,D,Q_A,H)=6ND+D[g(Q_A)-g(Q_0)]_+ + eta N D H',8)","FORM('C_total(N,D,Q_A,H)=6ND+D[g(Q_A)-g(Q_0)]_+ + eta N D H',9)"),
("FORM('kappa(H)10^18 N_B D_B <= C_budget, kappa(H)=6+eta H',9)","FORM('kappa(H)10^18 N_B D_B <= C_budget, kappa(H)=6+eta H',10)"),
("FORM('min L_0(N_B,D_B) s.t. C_total<=C_budget, N_B in [N_lo,N_hi], D_B in [D_lo,D_hi]',10)","FORM('min L_0(N_B,D_B) s.t. C_total<=C_budget, N_B in [N_lo,N_hi], D_B in [D_lo,D_hi]',11)"),
("FORM('grad L_0 = -lambda grad C_total, N_B partial L_0/partial N_B = D_B partial L_0/partial D_B',11)","FORM('grad L_0 = -lambda grad C_total, N_B partial L_0/partial N_B = D_B partial L_0/partial D_B',12)"),
("FORM('H_crit=6/eta=30000',12)","FORM('H_crit=6/eta=30000',13)"),
("FORM('g_t(x_i)=m_t(x_i)-m_t(x_ref), r_i=Y_i-m_t(x_i)',13)","FORM('g_t(x_i)=m_t(x_i)-m_t(x_ref), r_i=Y_i-m_t(x_i)',15)"),
]
for a,b in repls:
    if a not in s: raise SystemExit('missing '+a)
    s=s.replace(a,b,1)
p.write_text(s,encoding='utf-8')
print('patched')
