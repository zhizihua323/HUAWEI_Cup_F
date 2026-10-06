# G2 analytic derivatives, elasticities and local substitutions

The only formal expression is the layered law

`L_gen^(s)(N_B,D_B,Q_A,p)=L0_B1(N_B,D_B)+rho_Q^(s)*Delta_Q(h_s(Q_A))+tau_p^(s)*Delta_p(p;p0)`.

It is not a jointly identified four-variable response surface.

## Base B1 derivatives

- `dL0/dN_B = -alpha*A*N_B^(-alpha-1)`.
- `dL0/dD_B = -beta*B*D_B^(-beta-1)`.
- At `N_B=1, D_B=100`: `L0=2.3855781852625721`, `dL0/dN_B=-0.12034501947422563`, `dL0/dD_B=-0.00095662428769260563`.
- Local base elasticities: `E_N=N_B/L*dL/dN_B=-0.050446898038254688`; `E_D=D_B/L*dL/dD_B=-0.040100311681350885`.

## Quality derivative

For numeric H1-H3 scenarios,

`dL/dQ_A = -rho_Q^(s)*k_add*h_s'(Q_A)`,

with `h1'=1`, `h2'=b` for fixed `b in {0.5,1,2}`, and H3 the empirical quantile-step map. H3 is zero almost everywhere and undefined at CDF jumps, so only finite differences after fixing the scenario are allowed. H4 gives direction only.

For `S03_H1_IDENTITY`, `rho_Q=1`, `k_add=0.3544081081063713`, and `Q_A=0.56953418574751735`:

- `dL/dQ_A=-0.3544081081063713`.
- `E_Q=Q_A/L*dL/dQ_A=-0.08461157740276018`.

## Feasible mixture direction

For a feasible direction `v` with `sum(v)=0` and `p0+epsilon*v>=0` locally,

`D_v L = tau_p^(s)*c^T v`.

Using the frozen equal-domain mean RegMix contrast `c` and `v=e_github-e_arxiv`, `c^T v=0.061520492204242494`. Therefore the directional slope is `0.030760246102121247` for S14, `0.061520492204242494` for S15, and `-0.061520492204242494` for the S16 stress scenario. These are scenario slopes, not estimates of 17 independent domain marginal effects.

## Holding Loss fixed: local N/D substitution

- `(dN_B/dQ_A)|_L = -(dL/dQ_A)/(dL0/dN_B)`.
- `(dD_B/dQ_A)|_L = -(dL/dQ_A)/(dL0/dD_B)`.
- At the worked point under S03: `-2.9449337384691279` billion parameters per Q unit and `-370.47784868729372` billion tokens per Q unit.

## Local p-Q substitution

- If `Q_A` is fixed independently, use `D_v L=tau_p*c^T v`.
- If `Q_mix=p^T q` with fixed domain quality vector `q`, `Q_mix` lies in the p column space. Then `tau_p*c^T v` and the quality term cannot be interpreted as two independent effects. Only a fixed scenario linking `p` and `Q_mix` may be reported.
- No complementarity or substitution claim is transferred across B1, B6, A/RegMix, or B8 without the corresponding source qualification.
