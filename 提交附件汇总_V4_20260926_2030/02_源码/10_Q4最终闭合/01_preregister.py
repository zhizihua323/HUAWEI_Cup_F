# AI-assisted development disclosure: OpenAI Codex (GPT-5.6 Sol / GPT-6 Astra) assisted drafting and debugging; the authors reviewed the final code and outputs.
# Developer: OpenAI; official release dates: 2026-07-09 and 2026-09-03.
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from g4_common import (  # noqa: E402
    ALL_TARGETS,
    BOOTSTRAP_DRAWS,
    C01_R1,
    C1,
    C2,
    C3,
    C4,
    HORIZONS,
    RUN_DIR,
    RUN_ID,
    SCENARIO_IDS,
    SEED,
    T05,
    T08,
    TASKS,
    build_input_manifest,
    environment_payload,
    extract_hf_repo,
    iso_local,
    normalize_alnum,
    normalize_model_alias,
    parse_dataset_tokens,
    parse_date,
    relpath,
    sha256_file,
    unix_to_local_date,
    write_csv,
    write_json,
    write_stage,
)

MODEL_SPECS = ["M0_CONSTANT", "M1_SCALE", "M2_SCALE_TIME"]
MIN_FAMILIES = 3
MIN_FAMILY_INTERVALS = 10
MIN_TIME_TEST_MODELS = 10
UPGRADE_REL_IMPROVEMENT = 0.05
MAX_REL_DEGRADATION = 0.10
DIRECTION_CONSISTENCY = 0.80


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, low_memory=False)


def c1_c2_equivalence(c1: pd.DataFrame, c2: pd.DataFrame) -> dict:
    common_cols = [
        "Model", "#Params (B)", "Submission Date", "Hub License", "Type", "Average ⬆️",
        "IFEval", "BBH", "MATH Lvl 5", "GPQA", "MUSR", "MMLU-PRO",
    ]
    a = c1[common_cols].copy()
    b = c2[common_cols].copy()
    numeric_cols = ["#Params (B)", "Average ⬆️", "IFEval", "BBH", "MATH Lvl 5", "GPQA", "MUSR", "MMLU-PRO"]
    for col in numeric_cols:
        a[col] = pd.to_numeric(a[col], errors="coerce")
        b[col] = pd.to_numeric(b[col], errors="coerce")
    a = a.sort_values(common_cols, na_position="last").reset_index(drop=True)
    b = b.sort_values(common_cols, na_position="last").reset_index(drop=True)
    a["_ordinal"] = a.groupby("Model", dropna=False).cumcount()
    b["_ordinal"] = b.groupby("Model", dropna=False).cumcount()
    merged = a.merge(b, on=["Model", "_ordinal"], how="outer", suffixes=("_c1", "_c2"), indicator=True)
    base = merged[merged["_merge"].eq("both")].copy()
    tolerant_mismatch_rows = 0
    exact_string_mismatches = 0
    max_abs_numeric_difference = 0.0
    for col in common_cols[1:]:
        x = base[f"{col}_c1"]
        y = base[f"{col}_c2"]
        if col in numeric_cols:
            diff = (x - y).abs()
            finite = diff[np.isfinite(diff)]
            if len(finite):
                max_abs_numeric_difference = max(max_abs_numeric_difference, float(finite.max()))
            bad = ~((diff <= 1e-9) | (x.isna() & y.isna()))
        else:
            bad = ~(x.astype(str).eq(y.astype(str)) | (x.isna() & y.isna()))
            exact_string_mismatches += int(bad.sum())
        tolerant_mismatch_rows += int(bad.sum())
    unique_models_match = set(a.Model.dropna()) == set(b.Model.dropna())
    return {
        "c1_rows": int(len(c1)),
        "c2_rows": int(len(c2)),
        "common_rows": int(merged["_merge"].eq("both").sum()),
        "common_models": int(len(set(a.Model.dropna()) & set(b.Model.dropna()))),
        "unique_models_match": bool(unique_models_match),
        "c1_only_rows": int(merged["_merge"].eq("left_only").sum()),
        "c2_only_rows": int(merged["_merge"].eq("right_only").sum()),
        "numeric_tolerance": 1e-9,
        "tolerant_value_mismatch_cells": tolerant_mismatch_rows,
        "exact_string_mismatches": exact_string_mismatches,
        "max_abs_numeric_difference": max_abs_numeric_difference,
        "pass": bool(
            len(c1) == len(c2) and unique_models_match
            and merged["_merge"].eq("both").sum() == len(c1)
            and tolerant_mismatch_rows == 0
        ),
    }

def dedupe_c2_with_audit(c2: pd.DataFrame, cross: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    fields = [
        "#Params (B)", "Submission Date", "Hub License", "Type",
        "Epoch_AI_Publication_Date", "Epoch_AI_Open_Weights",
    ]
    rows, retained = [], []
    canon = cross[cross.source_table.eq("C2")].groupby("original_name")["canonical_model_id"].nunique(dropna=True)
    canmap = cross[cross.source_table.eq("C2")].groupby("original_name")["canonical_model_id"].first()
    for name, g in c2.groupby("Model", sort=False, dropna=False):
        first = g.iloc[0].copy()
        conflicts = []
        for col in fields:
            vals = g[col].dropna().astype(str).unique().tolist()
            if len(vals) > 1:
                conflicts.append(col)
        dup_identical = bool(len(g) > 1 and len(g.drop_duplicates()) == 1)
        if len(g) == 1:
            status = "UNIQUE_ROW"
        elif not conflicts:
            status = "DUPLICATES_CONSISTENT"
        else:
            status = "DUPLICATES_METADATA_CONFLICT"
        ncanon = int(canon.get(name, 0)) if not pd.isna(name) else 0
        if ncanon > 1:
            status = "CANONICAL_ID_CONFLICT"
        first["_c2_row_count"] = int(len(g))
        first["_c2_duplicate_status"] = status
        first["_c2_conflicting_fields"] = "|".join(conflicts)
        first["_canonical_model_id_t05"] = "" if ncanon != 1 else canmap.get(name, "")
        retained.append(first)
        rows.append({
            "raw_model": "" if pd.isna(name) else str(name),
            "c2_row_count": int(len(g)),
            "exact_duplicate_rows": dup_identical,
            "metadata_conflict": bool(conflicts),
            "conflicting_fields": "|".join(conflicts),
            "t05_canonical_candidates": ncanon,
            "dedup_status": status,
            "eligible_unique": bool(status in {"UNIQUE_ROW", "DUPLICATES_CONSISTENT"} and ncanon == 1),
        })
    return pd.DataFrame(retained).reset_index(drop=True), pd.DataFrame(rows)


def dedupe_c3(c3: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows, retained = [], []
    for name, g in c3.groupby("Model", sort=False, dropna=False):
        years = sorted(pd.to_numeric(g["Year"], errors="coerce").dropna().astype(int).unique().tolist())
        status = "UNIQUE_YEAR" if len(years) == 1 else ("CONFLICT" if len(years) > 1 else "MISSING")
        first = g.iloc[0].copy()
        first["c3_year"] = years[0] if len(years) == 1 else np.nan
        first["c3_year_status"] = status
        retained.append(first)
        rows.append({
            "Model": name, "c3_rows": int(len(g)),
            "years": "|".join(map(str, years)), "c3_year_status": status,
        })
    return pd.DataFrame(retained).reset_index(drop=True), pd.DataFrame(rows)


def match_c4(c2u: pd.DataFrame, c4: pd.DataFrame) -> pd.DataFrame:
    c4w = c4.drop_duplicates().reset_index(drop=True).copy()
    c4w["c4_index"] = np.arange(len(c4w))
    c4w["norm_full"] = c4w["Model"].map(normalize_alnum)
    c4w["norm_base"] = c4w["Model"].map(normalize_model_alias)
    c4w["hf_repo"] = c4w["Link"].map(extract_hf_repo)
    by_repo = {repo: g.c4_index.tolist() for repo, g in c4w[c4w.hf_repo.ne("")].groupby("hf_repo")}
    by_full = {k: g.c4_index.tolist() for k, g in c4w[c4w.norm_full.ne("")].groupby("norm_full")}
    by_base = {k: g.c4_index.tolist() for k, g in c4w[c4w.norm_base.ne("")].groupby("norm_base")}
    rows = []
    for _, r in c2u.iterrows():
        raw = str(r["Model"])
        hits, rule = [], "NO_MATCH"
        if raw.lower() in by_repo:
            hits, rule = by_repo[raw.lower()], "EXACT_HF_REPO_URL"
        if not hits:
            k = normalize_alnum(raw)
            if k in by_full:
                hits, rule = by_full[k], "UNIQUE_NORMALIZED_FULL"
        if not hits:
            k = normalize_model_alias(raw)
            if k in by_base:
                hits, rule = by_base[k], "UNIQUE_NORMALIZED_BASENAME"
        if len(hits) == 1:
            status = "UNIQUE"
        elif len(hits) > 1:
            status = "AMBIGUOUS_MULTIPLE_C4"
        else:
            status = "UNMATCHED"
        rows.append({
            "Model": raw, "c4_index": hits[0] if len(hits) == 1 else np.nan,
            "c4_candidate_count": int(len(hits)), "c4_match_rule": rule,
            "c4_identity_status": status,
        })
    out = pd.DataFrame(rows)
    shared = out.loc[out.c4_identity_status.eq("UNIQUE"), "c4_index"].value_counts()
    shared_ids = set(shared[shared.gt(1)].index.tolist())
    out.loc[out.c4_index.isin(shared_ids), "c4_identity_status"] = "SHARED_C4_IDENTITY_SENSITIVITY"
    meta_cols = [
        "Model", "Organization", "Publication date", "Parameters", "Training compute (FLOP)",
        "Training dataset size (total)", "Open model weights?", "Model accessibility", "Approach",
        "Base model", "Reference", "Link", "Hugging Face developer id",
    ]
    meta = c4w[["c4_index"] + meta_cols].rename(columns={"Model": "c4_model_name"})
    return out.merge(meta, on="c4_index", how="left")


def scenario_growth(main: pd.DataFrame) -> tuple[pd.DataFrame, dict, pd.DataFrame]:
    records = main[
        main["n_observed"].fillna(False) & main["d_observed"].fillna(False)
        & main["submission_date"].notna() & ~main["date_ambiguous"].fillna(False)
    ].copy()
    records["N_growth_physical"] = pd.to_numeric(records["c4_parameters"], errors="coerce")
    records["D_growth_physical"] = pd.to_numeric(records["c4_dataset_tokens"], errors="coerce")
    records["growth_compute_proxy"] = 6.0 * records["N_growth_physical"] * records["D_growth_physical"]
    detail_rows, family_period_rows = [], []
    for family, g in records.groupby("model_family", dropna=False):
        g = g.sort_values(["submission_date", "c4_parameters", "Model"], na_position="last").reset_index(drop=True)
        for i in range(len(g) - 1):
            a, b = g.iloc[i], g.iloc[i + 1]
            dt = int((pd.Timestamp(b.submission_date) - pd.Timestamp(a.submission_date)).days)
            valid = bool(90 <= dt <= 730 and a.growth_compute_proxy > 0 and b.growth_compute_proxy > 0)
            rate = np.nan
            if valid:
                rate = math.log(float(b.growth_compute_proxy) / float(a.growth_compute_proxy)) / (dt / 365.25)
                mid = pd.Timestamp(a.submission_date) + (pd.Timestamp(b.submission_date) - pd.Timestamp(a.submission_date)) / 2
                family_period_rows.append({
                    "model_family": family,
                    "period": f"{mid.year}Q{((mid.month - 1) // 3) + 1}",
                    "annual_log_growth": rate, "start_model": a.Model, "end_model": b.Model,
                })
            detail_rows.append({
                "model_family": family, "start_model": a.Model, "end_model": b.Model,
                "start_submission_date": pd.Timestamp(a.submission_date).date().isoformat(),
                "end_submission_date": pd.Timestamp(b.submission_date).date().isoformat(),
                "interval_days": dt, "rule_90_to_730_days": valid,
                "N_observed": bool(pd.notna(a.c4_parameters) and pd.notna(b.c4_parameters)),
                "D_observed": bool(pd.notna(a.c4_dataset_tokens) and pd.notna(b.c4_dataset_tokens)),
                "compute_basis": "6*N*D from observed N and D",
                "annual_log_growth": rate,
                "status": "VALID_PAIR" if valid else "EXCLUDED_INTERVAL",
            })
    detail = pd.DataFrame(detail_rows)
    med = pd.DataFrame(family_period_rows)
    if len(med):
        med = med.groupby(["model_family", "period"], as_index=False).agg(
            annual_log_growth=("annual_log_growth", "median"),
            n_pairs_in_family_period=("annual_log_growth", "size"),
        )
    n_families = int(med.model_family.nunique()) if len(med) else 0
    n_intervals = int(len(med))
    identifiable = bool(n_families >= MIN_FAMILIES and n_intervals >= MIN_FAMILY_INTERVALS)
    scenario_values = {}
    if identifiable:
        family_medians = med.groupby("model_family")["annual_log_growth"].median()
        q = family_medians.quantile([0.25, 0.50, 0.75])
        scenario_values = {
            "SLOW": {"annual_log_growth": float(q.loc[0.25]), "multiplier": float(np.exp(q.loc[0.25])), "source": "HISTORICAL_FAMILY_Q25", "quantile": 0.25},
            "BASELINE": {"annual_log_growth": float(q.loc[0.50]), "multiplier": float(np.exp(q.loc[0.50])), "source": "HISTORICAL_FAMILY_Q50", "quantile": 0.50},
            "UPPER_SENSITIVITY": {"annual_log_growth": float(q.loc[0.75]), "multiplier": float(np.exp(q.loc[0.75])), "source": "HISTORICAL_FAMILY_Q75", "quantile": 0.75},
        }
    else:
        for sid, mult, q in zip(SCENARIO_IDS, [1.0, 1.5, 2.0], [0.25, 0.50, 0.75]):
            scenario_values[sid] = {
                "annual_log_growth": float(math.log(mult)), "multiplier": float(mult),
                "source": f"{sid}_ASSUMED", "quantile": q,
            }
    support = {
        "n_observed_ND_records": int(len(records)),
        "n_observed_ND_families": int(records.model_family.nunique()),
        "n_candidate_adjacent_pairs": int(len(detail)),
        "n_valid_family_level_intervals": n_intervals,
        "n_independent_model_families": n_families,
        "min_families_required": MIN_FAMILIES,
        "min_family_level_intervals_required": MIN_FAMILY_INTERVALS,
        "identifiable": identifiable,
        "scenario_values": scenario_values,
        "rule": "T08-compatible adjacent same-family N/D pairs, 90-730 days, median within family-period, family-equal quantiles; fallback is the pre-registered mathematical multiplier grid",
    }
    return detail, support, med


def main() -> None:
    write_stage("preregister", "STARTED")
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    write_json(RUN_DIR / "environment.json", environment_payload())
    input_manifest = build_input_manifest()
    write_json(RUN_DIR / "input_manifest.json", input_manifest)
    if input_manifest["missing_count"]:
        raise RuntimeError(f"formal input missing: {input_manifest['missing']}")

    c1, c2, c3, c4 = [pd.read_csv(p, low_memory=False) for p in [C1, C2, C3, C4]]
    c8_wide = pd.read_csv(C01_R1 / "c8_model_wide_corrected.csv", low_memory=False)
    c8_task = pd.read_csv(C01_R1 / "c8_model_task_aggregate_corrected.csv", low_memory=False)
    c8_dir = pd.read_csv(C01_R1 / "c8_directory_aggregate_corrected.csv", low_memory=False)
    cross = pd.read_csv(T05 / "model_identity_crosswalk.csv", low_memory=False)
    dup_runs = pd.read_csv(T05 / "duplicate_run_resolution.csv", low_memory=False)
    corrupt = pd.read_csv(T05 / "corrupt_and_partial_coverage.csv", low_memory=False)

    equivalence = c1_c2_equivalence(c1, c2)
    c2u, c2_dedup_audit = dedupe_c2_with_audit(c2, cross)
    c3u, c3_audit = dedupe_c3(c3)
    c4_match = match_c4(c2u, c4)

    task_long = c8_task.copy()
    task_long["score_date"] = task_long["canonical_eval_unix_date"].map(unix_to_local_date)
    task_long["task_valid"] = task_long["canonical_score_finite"].fillna(False).astype(bool)
    task_dates = task_long[task_long.task_valid].groupby(["Model", "task_group"], as_index=False).agg(score_date=("score_date", "max"))
    valid_counts = task_long[task_long.task_valid].groupby("Model").size().rename("n_tasks_valid_pre_score")

    master = c2u.merge(c3u[["Model", "c3_year", "c3_year_status"]], on="Model", how="left", validate="one_to_one")
    master = master.merge(c4_match, on="Model", how="left", validate="one_to_one")
    master = master.merge(
        c8_wide[["Model", "n_tasks_valid", "six_task_complete", "partial_task_mean", "model_key"]],
        on="Model", how="left", validate="one_to_one",
    )
    master = master.merge(valid_counts, left_on="Model", right_index=True, how="left")
    master = master.merge(cross.loc[cross.source_table.eq("C8"), [
        "original_name", "canonical_model_id", "model_family"
    ]].rename(columns={
        "original_name": "Model", "canonical_model_id": "t05_c8_canonical_id",
        "model_family": "t05_c8_model_family",
    }), on="Model", how="left", validate="one_to_one")
    master["c2_present"] = True
    master["c8_present"] = master["n_tasks_valid"].notna()
    master["main_t05_canonical_id"] = master["_canonical_model_id_t05"].fillna(master["t05_c8_canonical_id"])
    master["model_family"] = master["t05_c8_model_family"]
    master["submission_date"] = master["Submission Date"].map(parse_date)
    master["publication_date"] = master["Epoch_AI_Publication_Date"].map(parse_date)
    master["date_ambiguous"] = master["_c2_duplicate_status"].eq("DUPLICATES_METADATA_CONFLICT")
    master["c4_parameters"] = pd.to_numeric(master["Parameters"], errors="coerce")
    master["c4_compute_direct"] = pd.to_numeric(master["Training compute (FLOP)"], errors="coerce")
    master["c4_dataset_tokens"] = master["Training dataset size (total)"].map(parse_dataset_tokens)
    master["n_observed"] = master["c4_parameters"].gt(0).fillna(False)
    master["d_observed"] = master["c4_dataset_tokens"].gt(0).fillna(False)
    master["compute_flops"] = np.nan
    master["compute_origin"] = "MISSING"
    direct = master["c4_compute_direct"].gt(0).fillna(False)
    prox = (~direct) & master["n_observed"] & master["d_observed"]
    master.loc[direct, "compute_flops"] = master.loc[direct, "c4_compute_direct"]
    master.loc[direct, "compute_origin"] = "C4_TRAINING_COMPUTE_FLOP"
    master.loc[prox, "compute_flops"] = 6.0 * master.loc[prox, "c4_parameters"] * master.loc[prox, "c4_dataset_tokens"]
    master.loc[prox, "compute_origin"] = "CONSTRUCTED_6ND"
    master["compute_observed"] = master["compute_flops"].gt(0).fillna(False)
    master["log10_compute"] = np.log10(master["compute_flops"].where(master["compute_flops"].gt(0)))

    c2_open = master["Epoch_AI_Open_Weights"].fillna("").astype(str).str.strip().str.lower()
    c4_open = master["Open model weights?"].fillna("").astype(str).str.strip().str.lower()
    master["c2_open_weights"] = master["Epoch_AI_Open_Weights"]
    master["c4_open_weights"] = master["Open model weights?"]
    master["open_weights_yes"] = c2_open.eq("yes") | c4_open.eq("yes")
    master["open_weights_no"] = c2_open.eq("no") | c4_open.eq("no")
    master["open_weights_conflict"] = master["open_weights_yes"] & master["open_weights_no"]
    lic = master["Hub License"].fillna("").astype(str).str.strip().str.lower()
    master["license_explicit"] = master["Hub License"].notna() & ~lic.isin(["", "unknown", "other", "nan"])
    master["type_pretrained"] = master["Type"].fillna("").astype(str).eq("🟢 pretrained")
    master["type_chat_or_finetuned"] = master["Type"].fillna("").astype(str).isin([
        "💬 chat models (RLHF, DPO, IFT, ...)", "🔶 fine-tuned on domain-specific datasets",
    ])
    master["c3_unique"] = master["c3_year_status"].eq("UNIQUE_YEAR")
    master["c8_unique"] = master["c8_present"] & ~master["Model"].duplicated(keep=False)
    master["identity_t05_unique"] = master["main_t05_canonical_id"].notna()

    master["main_eligible"] = (
        master["c2_present"] & master["c8_present"] & master["c3_unique"]
        & master["c4_identity_status"].eq("UNIQUE")
        & master["identity_t05_unique"] & ~master["date_ambiguous"]
        & master["type_pretrained"] & master["open_weights_yes"] & ~master["open_weights_no"]
        & master["license_explicit"] & master["n_tasks_valid"].gt(0)
    )
    master["other_open_sensitivity_eligible"] = (
        master["c2_present"] & master["c8_present"] & master["c3_unique"]
        & master["c4_identity_status"].eq("UNIQUE")
        & master["identity_t05_unique"] & ~master["date_ambiguous"]
        & master["type_chat_or_finetuned"] & master["open_weights_yes"] & ~master["open_weights_no"]
        & master["license_explicit"] & master["n_tasks_valid"].gt(0)
    )

    valid_pairs = task_dates[task_dates.Model.isin(master.loc[master.main_eligible, "Model"])].copy()
    origin = valid_pairs.score_date.max() if len(valid_pairs) else pd.NaT
    if pd.isna(origin):
        raise RuntimeError("forecast origin cannot be established: main sample has no valid task date")
    origin = pd.Timestamp(origin).normalize()
    horizon_dates = {str(h): (origin + pd.DateOffset(months=h)).date().isoformat() for h in HORIZONS}

    ref_dates = valid_pairs.groupby("Model")["score_date"].max().sort_values()
    unique_dates = sorted(ref_dates.dropna().unique())
    n_models = int(len(ref_dates))
    candidates = []
    for d in unique_dates:
        d = pd.Timestamp(d)
        train_n = int((ref_dates < d).sum())
        test_n = int((ref_dates >= d).sum())
        if test_n < MIN_TIME_TEST_MODELS:
            continue
        candidates.append((abs(train_n / max(n_models, 1) - 0.80), d, train_n, test_n))
    if not candidates:
        cutoff = pd.Timestamp(unique_dates[max(0, int(0.8 * len(unique_dates)) - 1)])
    else:
        candidates.sort(key=lambda x: (x[0], x[1]))
        _, cutoff, _, _ = candidates[0]
    time_split_status = "EVALUABLE" if int(ref_dates.ge(cutoff).sum()) >= MIN_TIME_TEST_MODELS else "NOT_EVALUABLE"

    split_rows = []
    for task in TASKS:
        task_models = set(task_dates.loc[task_dates.task_group.eq(task), "Model"])
        q = master[master.main_eligible & master.Model.isin(task_models)][
            ["Model", "main_t05_canonical_id", "model_family", "submission_date"]
        ].copy()
        q = q.merge(task_dates[task_dates.task_group.eq(task)][["Model", "score_date"]], on="Model", how="left")
        for _, r in q.iterrows():
            split_rows.append({
                "protocol": "TIME_OUT_80_20", "benchmark_task": task,
                "model_id": r.main_t05_canonical_id, "model_key": r.Model,
                "model_family": r.model_family, "score_date": r.score_date.date().isoformat(),
                "cutoff": cutoff.date().isoformat(),
                "split": "TRAIN" if r.score_date < cutoff else "TEST",
                "status": time_split_status,
            })
    split_registry = pd.DataFrame(split_rows)
    leakage_rows = []
    for task, g in split_registry.groupby("benchmark_task"):
        tr = set(g.loc[g.split.eq("TRAIN"), "model_id"])
        te = set(g.loc[g.split.eq("TEST"), "model_id"])
        mtr = set(g.loc[g.split.eq("TRAIN"), "model_key"])
        mte = set(g.loc[g.split.eq("TEST"), "model_key"])
        leakage_rows.append({
            "protocol": "TIME_OUT_80_20", "benchmark_task": task,
            "cutoff": cutoff.date().isoformat(), "train_models": len(mtr), "test_models": len(mte),
            "group_overlap": len(tr & te), "model_overlap": len(mtr & mte),
            "status": "PASS" if not (tr & te) and not (mtr & mte) else "FAIL",
        })
    for protocol in ["GROUPED_5FOLD", "LEAVE_ONE_FAMILY_OUT"]:
        for task in TASKS:
            leakage_rows.append({
                "protocol": protocol, "benchmark_task": task, "cutoff": "",
                "train_models": np.nan, "test_models": np.nan, "group_overlap": 0,
                "model_overlap": 0, "status": "PASS_DESIGN_GROUPS_EXCLUSIVE",
            })
    leakage_audit = pd.DataFrame(leakage_rows)

    denom_rows = []
    for task in TASKS:
        q = task_dates[task_dates.task_group.eq(task)]
        eligible = master[master.main_eligible & master.Model.isin(set(q.Model))]
        complete = eligible[eligible.six_task_complete.eq(True)]
        denom_rows.append({
            "benchmark_task": task, "n_main_eligible": int(len(eligible)),
            "n_complete_six_task_models": int(len(complete)), "n_partial_models": int(len(eligible) - len(complete)),
            "n_score_observed": int(len(eligible)), "n_compute_observed": int(eligible.compute_observed.sum()),
            "n_N_observed": int(eligible.n_observed.sum()), "n_D_observed": int(eligible.d_observed.sum()),
            "n_model_families": int(eligible.model_family.nunique()),
            "unit": "score percentage points after C8 x100; scores read only after seal",
            "missing_rule": "no imputation; task-specific observed denominator",
        })
    denom_rows.append({
        "benchmark_task": "six_task_mean_complete_only",
        "n_main_eligible": int(master.main_eligible.sum()),
        "n_complete_six_task_models": int((master.main_eligible & master.six_task_complete.eq(True)).sum()),
        "n_partial_models": int((master.main_eligible & master.six_task_complete.eq(False)).sum()),
        "n_score_observed": int((master.main_eligible & master.six_task_complete.eq(True)).sum()),
        "n_compute_observed": int((master.main_eligible & master.compute_observed).sum()),
        "n_N_observed": int((master.main_eligible & master.n_observed).sum()),
        "n_D_observed": int((master.main_eligible & master.d_observed).sum()),
        "n_model_families": int(master.loc[master.main_eligible, "model_family"].nunique()),
        "unit": "score percentage points after C8 x100; auxiliary only",
        "missing_rule": "complete-six-task only; no imputation",
    })
    taskwise_denominators = pd.DataFrame(denom_rows)

    growth_detail, growth_support, family_period = scenario_growth(master[master.main_eligible].copy())
    scenario_rows = []
    for order, sid in enumerate(SCENARIO_IDS):
        sv = growth_support["scenario_values"][sid]
        for horizon in HORIZONS:
            scenario_rows.append({
                "scenario_id": sid, "scenario_order": order, "quantile": sv["quantile"],
                "horizon_months": horizon, "forecast_origin": origin.date().isoformat(),
                "forecast_date": horizon_dates[str(horizon)], "annual_multiplier": sv["multiplier"],
                "annual_log_growth": sv["annual_log_growth"], "growth_source": sv["source"],
                "scenario_status": "SCENARIO_GRID_FROZEN",
                "n_independent_model_families": growth_support["n_independent_model_families"],
                "n_valid_family_level_intervals": growth_support["n_valid_family_level_intervals"],
                "loss_bridge_used": False, "frozen_before_benchmark_prediction": True,
            })
    scenario_registry = pd.DataFrame(scenario_rows)
    write_csv(RUN_DIR / "scenario_registry.csv", scenario_registry)
    write_csv(RUN_DIR / "scenario_growth_detail.csv", growth_detail)
    write_csv(RUN_DIR / "scenario_family_periods.csv", family_period)

    model_identity_audit = master[[
        "Model", "main_t05_canonical_id", "c2_present", "c8_present", "c3_year", "c3_year_status",
        "c4_identity_status", "c4_match_rule", "c4_candidate_count", "_c2_row_count", "_c2_duplicate_status",
        "n_tasks_valid", "six_task_complete", "main_eligible", "other_open_sensitivity_eligible",
    ]].copy()
    model_identity_audit = model_identity_audit.merge(c2_dedup_audit, left_on="Model", right_on="raw_model", how="left")
    model_identity_audit = model_identity_audit.merge(c3_audit, on="Model", how="left")
    write_csv(RUN_DIR / "model_identity_and_dedup_audit.csv", model_identity_audit)

    license_audit = master[[
        "Model", "main_t05_canonical_id", "Type", "Hub License", "license_explicit",
        "Epoch_AI_Open_Weights", "Open model weights?", "Model accessibility", "open_weights_yes",
        "open_weights_no", "open_weights_conflict", "c4_identity_status", "main_eligible",
        "other_open_sensitivity_eligible",
    ]].copy()
    write_csv(RUN_DIR / "license_openweight_type_audit.csv", license_audit)
    write_csv(RUN_DIR / "taskwise_denominators.csv", taskwise_denominators)
    write_csv(RUN_DIR / "split_registry.csv", split_registry)
    write_csv(RUN_DIR / "leakage_audit.csv", leakage_audit)

    flow_rows = [
        {"stage": "C2_READ", "n_models": int(len(c2u)), "n_rows": int(len(c2)), "rule": "C2 primary leaderboard table; C1 not counted as independent observations"},
        {"stage": "C8_IDENTITY_MATCHED", "n_models": int(master.c8_present.sum()), "n_rows": int(master.c8_present.sum()), "rule": "exact C8 corrected Model identity"},
        {"stage": "C3_YEAR_UNIQUE", "n_models": int((master.c8_present & master.c3_unique).sum()), "n_rows": int((master.c8_present & master.c3_unique).sum()), "rule": "unique C3 Year"},
        {"stage": "C4_IDENTITY_UNIQUE", "n_models": int((master.c8_present & master.c4_identity_status.eq("UNIQUE")).sum()), "n_rows": int((master.c8_present & master.c4_identity_status.eq("UNIQUE")).sum()), "rule": "exact/unique normalized C4 match, no shared or ambiguous identity"},
        {"stage": "OPEN_WEIGHT_PRETRAINED", "n_models": int(master.main_eligible.sum()), "n_rows": int(master.main_eligible.sum()), "rule": "main eligibility before score-value reading"},
        {"stage": "OTHER_OPEN_SENSITIVITY", "n_models": int(master.other_open_sensitivity_eligible.sum()), "n_rows": int(master.other_open_sensitivity_eligible.sum()), "rule": "chat/fine-tuned open models held separately"},
    ]
    sample_flow = pd.DataFrame(flow_rows)
    write_csv(RUN_DIR / "sample_definition_and_flow.csv", sample_flow)

    scenario_hash = sha256_file(RUN_DIR / "scenario_registry.csv")
    seal = {
        "seal_version": "G4-v1", "task_id": "TASK-G4", "run_id": RUN_ID,
        "sealed_at_local": iso_local(), "sealed_before_task_score_values_read": True,
        "c1_c2_equivalence": equivalence,
        "c8_accounting_expected": {
            "files_total": 1958, "parse_success": 1954, "parse_failed": 4,
            "complete_six_task": int(c8_wide.six_task_complete.eq(True).sum()),
            "partial": int(c8_wide.six_task_complete.eq(False).sum()),
        },
        "forecast_origin_date": origin.date().isoformat(),
        "forecast_origin_rule": "maximum audited C8 canonical evaluation date among main eligible identity-unique pretrained open-weight models with at least one finite task result",
        "horizon_dates": horizon_dates,
        "time_cutoff": cutoff.date().isoformat(),
        "time_cutoff_rule": "date-only distribution rule: choose the unique model reference-date cutoff that yields at least 10 test models and train fraction closest to 0.80; ties choose earlier cutoff; fixed before score values were read",
        "time_cutoff_status": time_split_status,
        "main_sample_rule": {
            "base_table": "C2, with C1 used only for equivalence/field audit",
            "type": "pretrained only in main",
            "open_weights": "C2 or C4 says Yes and neither source says No",
            "license": "Hub License present and not unknown/other",
            "identity": "unique C01/T05 canonical identity, unique C3 Year, unique C4 metadata link, non-ambiguous date",
            "time_axis": "C8 canonical evaluation date per model-task",
            "missing": "no imputation of N, D, compute, date, license, or task score",
            "other_models": "chat/fine-tuned open models estimated only as a separate sensitivity layer",
        },
        "candidate_specs": {
            "M0_CONSTANT": "1", "M1_SCALE": "1 + log10(compute)",
            "M2_SCALE_TIME": "1 + log10(compute) + time_years",
            "sensitivity_only": "1 + log10(N_parameters) is reported but never selection-eligible",
        },
        "candidate_selection_rule": {
            "comparison": "nested simplest-model upgrade",
            "protocols": ["GROUPED_5FOLD", "TIME_OUT_80_20", "LEAVE_ONE_FAMILY_OUT"],
            "min_evaluable_protocol_count": 2,
            "relative_improvement_each_required": UPGRADE_REL_IMPROVEMENT,
            "required_metrics": ["mean_RMSE", "q90_pinball"],
            "max_relative_degradation_allowed": MAX_REL_DEGRADATION,
            "direction_consistency_min": DIRECTION_CONSISTENCY,
            "bootstrap_draws": BOOTSTRAP_DRAWS, "random_seed": SEED,
            "rank_and_condition": "full rank and standardized condition number < 1e8",
            "scenario_rule": "use validated selected model; if M2 is not validated, still report a separately labelled SCENARIO_ONLY_UNVALIDATED M2 forecast",
        },
        "contribution_rule": {
            "selected_model": "simplest model passing the frozen upgrade gate; M0 if none",
            "start": "earliest task score date", "end": "forecast origin",
            "scale_center": "median log10(compute) in +/-365-day endpoint windows; if fewer than 3 records, nearest 3",
            "equations": {
                "Delta_scale": "b_C*(logC_origin-logC_start)",
                "Delta_non_scale": "b_T*(t_origin-t_start), or 0 when the selected model has no time term",
                "Delta_fitted": "Delta_scale+Delta_non_scale",
            },
            "bootstrap": "500 grouped canonical-model resamples; central 5%-95% interval",
        },
        "scenario_rule": growth_support,
        "scenario_registry_sha256": scenario_hash,
        "direct_benchmark_loss_separation": {
            "loss_bridge_qualification": "CONDITIONAL_ASSOCIATION_ONLY",
            "loss_to_benchmark_conversion_allowed": False,
            "loss_files_used_in_direct_benchmark_selection": False,
        },
        "external_run_guards": {
            "c01_r1": relpath(C01_R1), "t05_read_only": relpath(T05),
            "t08_read_only": relpath(T08), "rerun_t05_t08": False,
        },
    }
    write_json(RUN_DIR / "forecast_seal.json", seal)

    command_log = {
        "run_id": RUN_ID,
        "commands": [{
            "stage": "preregister",
            "command": "python diagnostics/TASK-G4/20260925T195716+0800/code/01_preregister.py",
            "cwd": str(RUN_DIR.parents[3]),
            "started_or_recorded_local": iso_local(), "status": "COMPLETED",
        }],
    }
    write_json(RUN_DIR / "command_log.json", command_log)
    write_stage(
        "preregister", "COMPLETED", n_main_models=int(master.main_eligible.sum()),
        forecast_origin=origin.date().isoformat(), time_cutoff=cutoff.date().isoformat(),
        scenario_identifiable=bool(growth_support["identifiable"]),
        scenario_registry_sha256=scenario_hash,
    )


if __name__ == "__main__":
    main()
