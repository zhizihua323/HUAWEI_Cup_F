# TASK-T03E handoff (COMPLETE_PENDING_REVIEW evidence pack)

**Executor status: INSUFFICIENT_EVIDENCE_KEEP_D**

**D = Q_baseline remains the official main result.** C = Q_baseline * (1 - 0.02 * P) is only a preregistered rule-sensitivity candidate.

## 1. Run identity

- run_id: t03e_complete_run
- run directory: C:\Users\28762\Desktop\The Huawei Cup National Postgraduate Mathematical Modeling Contest\GPT_Workspace\tmp\t03e_complete_run
- official input: C:\Users\28762\Desktop\The Huawei Cup National Postgraduate Mathematical Modeling Contest\GPT_Workspace\solution\outputs\quality_q01c\20260924T215718+08\quality_features_scores.parquet
- input SHA256: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa

## 2. Domain labels and active correction domains

- calibration labels observed: book, c4, github
- active correction domains: c4
  - book: INSUFFICIENT_CALIBRATION
  - c4: ACTIVE
  - commoncrawl: DESIGN_LABEL_ABSENT
  - wikipedia: ACTIVE

## 3. Frozen thresholds

| domain | indicator | q0.95 | q0.99 | q0.005 | q0.995 | n |
|---|---|---|---|---|---|---|
| c4 | top_2gram | 1.0 | 2.0 | 0.5 | 2.5 |  |
| c4 | top_3gram | 3.0 | 4.0 | 2.5 | 4.5 |  |

## 4. Bootstrap (200 replicates, seed 20260925)

| domain | n | joint pass | required | status |
|---|---|---|---|---|
| c4 | 3 | 200 | 190 | PASS |

## 5. Freeze seal and read order

- freeze_manifest SHA256: ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff
- FREEZE_SEALED time: 2026-09-25T00:00:00+08:00
- first_holdout_read_time: 2026-09-25T00:00:02.000+08:00
- first_extension_read_time: 2026-09-25T00:00:03.000+08:00
- order satisfied: True

## 6. Holdout

- status: INSUFFICIENT_EVIDENCE_KEEP_D
  - c4: n=3, Spearman=None, Jaccard=None, |dmean(P)|=None, OOS=None, status=INSUFFICIENT_N

## 7. Extension

- status: INSUFFICIENT_EXTENSION_EVIDENCE
- overlap rows: 1, reproduced: 1, mismatches: 0

## 8. RegMix/Loss identifiability

- status: NOT_IDENTIFIABLE
  - synthetic

## 9. Checks and verification

- executor checks: {'PASS': 21, 'NOT_CHECKED': 2}
- verification: see verification.json (independent verifier, written after checks.json)

## 10. Limitations and open items for the controller

- controller decision on whether the rule-sensitivity candidate deserves any further role; D = Q_baseline stays the official main result either way
- RegMix/Loss identification status is recorded as a method conclusion, not as a candidate failure
- holdout history was partly known before this stage: results are a parameter-freeze validation, not a fully blinded test
- extension transport evidence is reported per active domain; insufficient or not-tested statuses must not be quoted as transport success

## 11. Prior exposure

- part of the A1 holdout summaries was inspected in earlier project work, so this stage is a parameter-freeze validation, not a fully blinded test; holdout was used only for the preregistered accept/reject decision

## 12. Explicit non-claims

- Q_C is not final_Q, not best_Q and not a replacement of the official main Q
- no A/B candidate, PCA/entropy/CRITIC weighting or lambda learning was run
- RegMix/Loss identification was not established; no new bridge model was fitted
