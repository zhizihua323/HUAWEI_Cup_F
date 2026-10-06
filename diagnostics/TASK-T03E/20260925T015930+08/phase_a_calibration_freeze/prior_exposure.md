# Prior exposure statement (TASK-T03E)

- Parts of the A1 holdout summaries were already inspected during earlier project work
  (the Q01C run reported holdout coverages and the T03 design work reviewed summary tables).
- In addition, an earlier execution of this identical frozen specification
  (diagnostics/TASK-T03E/20260925T015757+08) reached PHASE B and therefore read A1 holdout and
  extension values before this run. That earlier run kept identical parameters and produced
  identical candidate values, but its independent verifier stopped on defects of the verifier
  itself (a status-machine and coverage-format mismatch plus one wrong fixture expectation), not on
  a rule-failure of the executor. This run repeats the unchanged frozen specification with the
  corrected verifier source, which is sealed again before any validation value is read.
- No lambda, threshold, active-domain set, formula, gate or candidate version was chosen from
  holdout or extension values: every frozen parameter in this run is re-estimated on A1
  calibration only.
- Because of that history this stage is **not** a fully blinded test. The accurate description is
  "validation after parameter freeze" (参数冻结后的验证).
- Holdout results are used only for the preregistered accept/reject decision.
- Extension results are used only for transport/reproduction checks and never for model selection.
