# Prior exposure statement (TASK-T03E)

- Parts of the A1 holdout summaries were already inspected during earlier project work
  (the Q01C run reported holdout coverages and the T03 design work reviewed summary tables).
- In addition, two earlier executions of this identical frozen specification
  (diagnostics/TASK-T03E/20260925T015757+08 and diagnostics/TASK-T03E/20260925T015930+08) reached
  PHASE B and therefore read A1 holdout and extension values before this run. Both used the same
  lambda, thresholds, active domains, formula, candidate version and gates and produced the same
  candidate values; they stopped on defects of the independent verifier (a status-machine and
  coverage-format mismatch, one wrong fixture expectation, and an incomplete recording of the
  RegMix connection check), never on a rule failure of the executor. This run repeats the unchanged
  frozen specification with the corrected scripts, which are sealed again before any validation
  value is read.
- No lambda, threshold, active-domain set, formula, gate or candidate version was chosen from
  holdout or extension values: every frozen parameter in this run is re-estimated on A1
  calibration only.
- Because of that history this stage is **not** a fully blinded test. The accurate description is
  "validation after parameter freeze" (参数冻结后的验证).
- Holdout results are used only for the preregistered accept/reject decision.
- Extension results are used only for transport/reproduction checks and never for model selection.
