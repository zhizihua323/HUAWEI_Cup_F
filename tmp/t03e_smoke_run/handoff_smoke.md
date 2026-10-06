# TASK-T03E handoff (COMPLETE_PENDING_REVIEW evidence pack)

**Executor status: COMPLETE_PENDING_REVIEW**

**D = Q_baseline remains the official main result.** C = Q_baseline * (1 - 0.02 * P) is only a preregistered rule-sensitivity candidate.

## 1. Run identity

- run_id: synthetic
- run directory: C:\Users\28762\Desktop\The Huawei Cup National Postgraduate Mathematical Modeling Contest\GPT_Workspace\tmp\t03e_smoke_run
- official input: x
- input SHA256: y

## 2. Domain labels and active correction domains

- calibration labels observed: book, c4
- active correction domains: c4
  - book: INSUFFICIENT_CALIBRATION

## 3. Frozen thresholds

| domain | indicator | q0.95 | q0.99 | q0.005 | q0.995 | n |
|---|---|---|---|---|---|---|
| c4 | top_2gram | 1.0 | 2.0 | 0.5 | 2.5 | 4000 |
| c4 | top_3gram | 3.0 | 4.0 | 2.5 | 4.5 | 4000 |

## 4. Bootstrap (200 replicates, seed 20260925)

| domain | n | joint pass | required | status |
|---|---|---|---|---|
| c4 | 2 | 200 | 190 | PASS |

## 5. Freeze seal and read order

- freeze_manifest SHA256: z
- FREEZE_SEALED time: t0
- first_holdout_read_time: t1
- first_extension_read_time: t2
- order satisfied: True

## 6. Holdout

- status: ACCEPT_STABILITY
  - c4: n=1, Spearman=1.0, Jaccard=1.0, |dmean(P)|=0.0, OOS=0.0, status=PASS

## 7. Extension

- status: MIGRATION_OK
- overlap rows: 1, reproduced: 1, mismatches: 0

## 8. RegMix/Loss identifiability

- status: NOT_IDENTIFIABLE
  - r

## 9. Checks and verification

- executor checks: {'PASS': 20}
- verification: pending

## 10. Limitations and open items for the controller

- item

## 11. Prior exposure

- part of the A1 holdout summaries was inspected in earlier project work, so this stage is a parameter-freeze validation, not a fully blinded test; holdout was used only for the preregistered accept/reject decision

## 12. Explicit non-claims

- Q_C is not final_Q, not best_Q and not a replacement of the official main Q
- no A/B candidate, PCA/entropy/CRITIC weighting or lambda learning was run
- RegMix/Loss identification was not established; no new bridge model was fitted
