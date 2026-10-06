# Prior exposure statement (TASK-T03E)

- Parts of the A1 holdout summaries were already inspected during earlier project work
  (the Q01C run reported holdout coverages and the T03 design work reviewed summary tables).
- Those historical summaries must not be used here for tuning: no lambda, threshold, active-domain
  set, formula or gate was chosen from holdout or extension values, and this run re-estimates every
  frozen parameter on A1 calibration only.
- Because of that history this stage is **not** a fully blinded test. The accurate description is
  "validation after parameter freeze" (参数冻结后的验证).
- Holdout results are used only for the preregistered accept/reject decision.
- Extension results are used only for transport/reproduction checks and never for model selection.
