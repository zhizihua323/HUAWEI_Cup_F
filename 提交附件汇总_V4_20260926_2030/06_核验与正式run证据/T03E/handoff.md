# TASK-T03E handoff (COMPLETE_PENDING_REVIEW evidence pack)

**Executor status: COMPLETE_PENDING_REVIEW**

**D = Q_baseline remains the official main result.** C = Q_baseline * (1 - 0.02 * P) is only a preregistered rule-sensitivity candidate.

## 1. Run identity

- run_id: 20260925T020032+08
- run directory: diagnostics\TASK-T03E\20260925T020032+08
- official input: C:\Users\28762\Desktop\The Huawei Cup National Postgraduate Mathematical Modeling Contest\GPT_Workspace\solution\outputs\quality_q01c\20260924T215718+08\quality_features_scores.parquet
- input SHA256: 9e9393ab5120a342eac9ff5446a13fd2674728cc7de37e190621bb25d835e20a

## 2. Domain labels and active correction domains

- calibration labels observed: arxiv, book, c4, commoncrawl, github, stackexchange, wikipedia
- active correction domains: c4, commoncrawl, wikipedia
  - book: INSUFFICIENT_CALIBRATION
  - c4: ACTIVE
  - commoncrawl: ACTIVE
  - wikipedia: ACTIVE

## 3. Frozen thresholds

| domain | indicator | q0.95 | q0.99 | q0.005 | q0.995 | n |
|---|---|---|---|---|---|---|
| c4 | top_2gram | 10.068169900367069 | 17.10498651675123 | 0.0 | 20.920010222335815 |  |
| c4 | top_3gram | 10.236220472440944 | 19.403145377828928 | 0.0 | 24.635815775809203 |  |
| commoncrawl | top_2gram | 6.255321791464951 | 10.793186190584164 | 0.3948158072041508 | 12.849200304645828 |  |
| commoncrawl | top_3gram | 5.977031450843722 | 10.383268579318552 | 0.0 | 12.759083312427727 |  |
| wikipedia | top_2gram | 17.880728527955668 | 26.539302446642385 | 0.0 | 32.692207792207554 |  |
| wikipedia | top_3gram | 13.0 | 26.0 | 0.0 | 32.0 |  |

## 4. Bootstrap (200 replicates, seed 20260925)

| domain | n | joint pass | required | status |
|---|---|---|---|---|
| c4 | 8041 | 200 | 190 | PASS |
| commoncrawl | 7688 | 200 | 190 | PASS |
| wikipedia | 8013 | 200 | 190 | PASS |

## 5. Freeze seal and read order

- freeze_manifest SHA256: bdb3edc11637853f4e5488aad37fd1afae8d2a3c96532088a3c424dc810aa93f
- FREEZE_SEALED time: 2026-09-25T02:00:35+08:00
- first_holdout_read_time: 2026-09-25T02:00:40.710+08:00
- first_extension_read_time: 2026-09-25T02:00:40.902+08:00
- order satisfied: True

## 6. Holdout

- status: ACCEPT_STABILITY
  - c4: n=1959, Spearman=0.9999883272381607, Jaccard=1.0, |dmean(P)|=0.0046029844992003, OOS=0.006636038795303726, status=PASS
  - commoncrawl: n=1948, Spearman=0.9999688802130032, Jaccard=0.9897959183673469, |dmean(P)|=0.003167884968536889, OOS=0.014373716632443531, status=PASS
  - wikipedia: n=1973, Spearman=0.999982999217464, Jaccard=1.0, |dmean(P)|=0.0008853537485004649, OOS=0.008109477952356817, status=PASS

## 7. Extension

- status: NOT_TESTED_FOR_ACTIVE_CORRECTION
- overlap rows: 11419, reproduced: 11419, mismatches: 0

## 8. RegMix/Loss identifiability

- status: NOT_IDENTIFIABLE
  - 11 of 17 RegMix domains have no quality-domain mapping (quality_domain="(none)"), so the mapping is neither complete nor unique
  - the existing mixture model already includes the full pile composition vector w as features, so with fixed domain qualities q_d the aggregate Q_mix is a deterministic function of w inside that model; adding Q_mix therefore cannot be read as independent quality information
  - the B-side experiment table does carry ['Q_score'] over 360 experiment rows, but no documented join key links A-side quality rows/domains to those experiment_id values, so no reliable sample-level or experiment-level A-to-B pairing exists in the read-only inputs
  - no independent quality variation under a fixed composition w is available in the read-only inputs (one loss per mixture, one aggregate quality per domain)

## 9. Checks and verification

- executor checks: {'PASS': 22, 'NOT_CHECKED': 1}
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
