# TASK-T08 交接：规模/非规模分解与12/24个月情景

- run_id: `20260925T142203+0800`
- status: `COMPLETE_PENDING_CONTROLLER_REVIEW`
- forecast_origin: `2025-03-13`
- T05 eligibility: `CONDITIONAL_ASSOCIATION_ONLY`; six tasks and auxiliary mean remain `CONSTANT`.
- growth support: independent families `1`, valid family-level intervals `1`; identifiable `False`.
- main benchmark scale-associated component: exactly `0`; remainder is only a non-scale associated residual / conditional remainder.
- benchmark future output: `CONDITIONAL_BASELINE_ONLY` + `NOT_IDENTIFIABLE_PROGRESS`; no verified time trend.
- Loss space: `M0_B1` / `S00_NULL_M0_B1` / `H=2048` kept separate; growth scenarios `NOT_IDENTIFIABLE`; no Loss-to-benchmark conversion.
- checks: 18 entries, initial FAIL=0; independent verification: 32 checks, PASS=32, FAIL=0.
- output_manifest is generated only after this handoff, verification, checks, summary, log, and code_snapshot are frozen.

## Six-task baseline entries

| task | baseline points | conditional low | conditional high | 12m | 24m | future eligibility |
|---|---:|---:|---:|---|---|---|
| IFEval_pct | 22.165078 | 18.533524 | 26.172209 | NOT_IDENTIFIABLE_PROGRESS | NOT_IDENTIFIABLE_PROGRESS | CONDITIONAL_BASELINE_ONLY |
| BBH_pct | 30.840380 | 29.197147 | 32.272010 | NOT_IDENTIFIABLE_PROGRESS | NOT_IDENTIFIABLE_PROGRESS | CONDITIONAL_BASELINE_ONLY |
| MATH Lvl 5_pct | 1.068192 | 0.345274 | 1.747950 | NOT_IDENTIFIABLE_PROGRESS | NOT_IDENTIFIABLE_PROGRESS | CONDITIONAL_BASELINE_ONLY |
| GPQA_pct | 25.491371 | 24.646453 | 26.300336 | NOT_IDENTIFIABLE_PROGRESS | NOT_IDENTIFIABLE_PROGRESS | CONDITIONAL_BASELINE_ONLY |
| MUSR_pct | 36.451247 | 32.974301 | 39.625850 | NOT_IDENTIFIABLE_PROGRESS | NOT_IDENTIFIABLE_PROGRESS | CONDITIONAL_BASELINE_ONLY |
| MMLU-PRO_pct | 11.284195 | 11.045743 | 11.501670 | NOT_IDENTIFIABLE_PROGRESS | NOT_IDENTIFIABLE_PROGRESS | CONDITIONAL_BASELINE_ONLY |
| benchmark_mean_aux | 21.216744 | 20.737287 | 21.656458 | NOT_IDENTIFIABLE_PROGRESS | NOT_IDENTIFIABLE_PROGRESS | CONDITIONAL_BASELINE_ONLY |

## Boundary

This run does not modify 00-05, T05/T07, Q1/Q2/Q3, or the paper. It stops after T08 outputs are registered.
