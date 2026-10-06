# AI-assisted development disclosure: OpenAI Codex (GPT-5.6 Sol / GPT-6 Astra) assisted drafting and debugging; the authors reviewed the final code and outputs.
# Developer: OpenAI; official release dates: 2026-07-09 and 2026-09-03.
"""Audit C1--C8 and compute descriptive, non-causal evolution baselines.

AI-assisted: OpenAI Codex (OpenAI), used 2026-09-24.
Exact model/version and release date: not yet verified; see solution/README.md.
Original attachments are read only. Run: python solution/src/evolution_audit.py
This first-pass script deliberately does not extrapolate future benchmark scores.
"""
from pathlib import Path
import collections
import json
import os
import re

import numpy as np
import pandas as pd
from scipy.stats import pearsonr, spearmanr
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import LeaveOneOut

from common import DATA, SEED, configure_stdout, extended_path, output_dir, save_json, write_report

ROOT = DATA / "C_efficiency_evolution"
OUT = output_dir("evolution")
TASKS = ["IFEval", "BBH", "MATH Lvl 5", "GPQA", "MUSR", "MMLU-PRO"]
FILES = {
    "C1": "leaderboard_cleaned.csv", "C2": "leaderboard_enhanced.csv",
    "C3": "leaderboard_extended_timeseries.csv", "C4": "epoch_all_ai_models.csv",
    "C5": "loss_benchmark_bridge.csv", "C6": "loss_benchmark_bridge_expanded.csv",
    "C7": "model_architecture_metadata.csv",
}
# An explicit operational subset, not a legal determination of open-source status.
LICENSE_ALLOWLIST = {"apache-2.0", "mit", "gpl-3.0", "wtfpl", "afl-3.0", "bsd-3-clause-clear", "osl-3.0"}
CUSTOM_LICENSES = {"llama2", "llama3", "llama3.1", "llama3.2", "llama3.3", "gemma",
                   "creativeml-openrail-m", "bigscience-bloom-rail-1.0", "bigcode-openrail-m",
                   "openrail", "bigscience-openrail-m", "apple-ascl"}


def csv(name, frame):
    """UTF-8 BOM for Excel; gzip for the larger long-task table."""
    frame.to_csv(OUT / name, index=False, encoding="utf-8-sig")


def clean_json(value):
    if isinstance(value, dict):
        return {str(k): clean_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean_json(v) for v in value]
    if isinstance(value, np.generic):
        return clean_json(value.item())
    if isinstance(value, (float, np.floating)) and not np.isfinite(value):
        return None
    if isinstance(value, (pd.Timestamp, Path)):
        return str(value)
    return value


def jdump(name, value):
    save_json(OUT / name, clean_json(value))


def date_range(values):
    values = pd.to_datetime(values, errors="coerce", format="mixed")
    return {"valid": int(values.notna().sum()), "min": str(values.min()), "max": str(values.max())}


def numeric(value):
    try:
        value = float(value)
        return value if np.isfinite(value) else np.nan
    except (ValueError, TypeError):
        return np.nan


def normalize_name(value):
    return re.sub(r"[^a-z0-9]", "", str(value).lower())


def license_class(value):
    value = str(value).lower().strip()
    if value in LICENSE_ALLOWLIST:
        return "explicit_allowlist"
    if value in CUSTOM_LICENSES:
        return "custom_terms_review_needed"
    if value.startswith("cc-by-nc"):
        return "noncommercial_terms"
    if value in {"nan", "", "unknown", "other"}:
        return "unresolved"
    return "other_named_license"


def model_type(value):
    text = str(value).lower()
    if "continuously" in text:
        return "continued_pretrained"
    if "pretrained" in text:
        return "pretrained"
    if "chat" in text:
        return "chat"
    if "fine-tuned" in text:
        return "finetuned"
    if "merge" in text or "moerge" in text:
        return "merge"
    return "other"


def audit_tables(tables):
    profiles, summaries = [], {}
    for name, df in tables.items():
        summaries[name] = {"file": FILES[name], "rows": len(df), "columns": len(df.columns),
                           "exact_duplicate_rows": int(df.duplicated().sum())}
        if "Model" in df:
            summaries[name]["repeated_model_rows"] = int(df.Model.duplicated().sum())
        for col in df:
            s = df[col]
            v = pd.to_numeric(s, errors="coerce")
            profiles.append({"dataset": name, "column": col, "dtype": str(s.dtype),
                             "rows": len(df), "missing": int(s.isna().sum()),
                             "unique_nonmissing": int(s.nunique()), "numeric_values": int(v.notna().sum()),
                             "numeric_min": v.min(), "numeric_max": v.max(),
                             "example": str(s.dropna().iloc[0])[:160] if s.notna().any() else ""})
    csv("field_audit.csv", pd.DataFrame(profiles))
    summaries["dates"] = {
        "C1_submission": date_range(tables["C1"]["Submission Date"]),
        "C2_matched_publication": date_range(tables["C2"]["Epoch_AI_Publication_Date"]),
        "C4_publication": date_range(tables["C4"]["Publication date"]),
        "C4_last_modified": date_range(tables["C4"]["Last modified"]),
    }
    summaries["C7_context_lengths"] = sorted(tables["C7"].max_position_embeddings.unique().tolist())
    jdump("table_audit.json", summaries)
    return summaries


def prepare_leaderboard(tables):
    """Keep exact model identity, select latest submission; ties use original order, never score."""
    c1, c2, c3 = tables["C1"], tables["C2"], tables["C3"]
    if not c1.equals(c2[c1.columns]):
        raise ValueError("C2 does not preserve C1 rows; positional metadata alignment is unsafe")
    lb = c2.copy()
    lb.insert(0, "source_row", np.arange(len(lb)))
    lb["submission_date"] = pd.to_datetime(lb["Submission Date"], errors="coerce")
    lb["matched_publication_date"] = pd.to_datetime(lb.Epoch_AI_Publication_Date, errors="coerce")
    lb["publication_after_submission_days"] = (lb.matched_publication_date - lb.submission_date).dt.days
    lb["type_group"] = lb.Type.map(model_type)
    lb["license_group"] = lb["Hub License"].map(license_class)
    lb["six_task_mean"] = lb[TASKS].mean(axis=1)
    lb["average_minus_six_task_mean"] = lb["Average ⬆️"] - lb.six_task_mean
    # Additional raw fields are joined by exact row equality of cleaned scores and fullname.
    parquet = pd.read_parquet(ROOT / "data" / "train-00000-of-00001.parquet")
    if not (parquet.fullname.eq(c1.Model).all() and np.allclose(parquet[TASKS], c1[TASKS])):
        raise ValueError("Parquet/C1 row alignment changed")
    for col in ["Model sha", "Base Model", "MoE", "Architecture", "Flagged", "Chat Template"] + [x + " Raw" for x in TASKS]:
        lb[col] = parquet[col]
    lb["selected_latest"] = False
    selected_indices = (lb.sort_values(["submission_date", "source_row"], na_position="first")
                        .drop_duplicates("Model", keep="last").index)
    lb.loc[selected_indices, "selected_latest"] = True
    csv("leaderboard_all_rows_audited.csv", lb)
    csv("leaderboard_duplicate_identity_rows.csv", lb[lb.Model.duplicated(keep=False)])
    csv("publication_chronology_flags.csv", lb[lb.publication_after_submission_days > 0])
    latest = lb[lb.selected_latest].copy()
    csv("leaderboard_latest_per_model.csv", latest)
    csv("license_type_counts.csv", latest.groupby(["license_group", "type_group"], dropna=False).size().rename("n_models").reset_index())

    # Never treat C3's repeated leaderboard rows as independent observations.
    rename = {"Params_B": "#Params (B)", "Average": "Average ⬆️", "MATH_Lvl5": "MATH Lvl 5", "MMLU_PRO": "MMLU-PRO"}
    c3audit = c3.rename(columns=rename).copy()
    c3audit["six_task_mean"] = c3audit[TASKS].mean(axis=1)
    c3audit["average_minus_six_task_mean"] = c3audit["Average ⬆️"] - c3audit.six_task_mean
    score_cols = ["Average ⬆️"] + TASKS
    def signature(row):
        return (row["Model"],) + tuple(round(float(row[x]), 8) for x in score_cols)
    signatures = set(lb.apply(signature, axis=1))
    c3audit["exact_model_score_match_C1"] = [signature(x) in signatures for _, x in c3audit.iterrows()]
    c3audit["use_for_same_protocol_baseline"] = c3audit.exact_model_score_match_C1 & c3audit.Source.eq("Open LLM Leaderboard")
    csv("C3_provenance_and_score_audit.csv", c3audit)
    # Existing C5 is nested in C6, not an additional independent sample.
    bridge_overlap = tables["C5"].merge(tables["C6"], on="Model", suffixes=("_C5", "_C6"))
    summary = {"unique_models": len(latest), "duplicate_extra_rows": len(lb) - len(latest),
               "c1_mean_max_absolute_discrepancy": float(lb.average_minus_six_task_mean.abs().max()),
               "C2_publication_after_submission": int((lb.publication_after_submission_days > 0).sum()),
               "C2_publication_later_over_7_days": int((lb.publication_after_submission_days > 7).sum()),
               "C3_same_model_scores_in_C1": int(c3audit.exact_model_score_match_C1.sum()),
               "C3_historical_rows": int(c3audit.Source.str.contains("Historical").sum()),
               "C3_historical_average_inconsistent": int((c3audit.Source.str.contains("Historical") & (c3audit.average_minus_six_task_mean.abs() > 1e-6)).sum()),
               "C5_C6_overlapping_models": len(bridge_overlap),
               "C5_C6_changed_losses": int((bridge_overlap.Val_Loss_C5 - bridge_overlap.Val_Loss_C6).abs().gt(1e-8).sum()),
               "C5_C6_changed_average": int((bridge_overlap.LB_Average_C5 - bridge_overlap.LB_Average_C6).abs().gt(1e-8).sum()),
               "license_allowlist": sorted(LICENSE_ALLOWLIST),
               "deduplication_rule": "Latest nonmissing submission date per exact Model; ties use last source row, without score selection",
               "date_policy": "Submission date for evaluation availability only. C2 publication matches require independent identity verification."}
    jdump("leaderboard_identity_audit.json", summary)
    return lb, latest, summary


def epoch_links(epoch, latest):
    """Exact normalized name candidates only; record ambiguities and reject fuzzy transfer."""
    index = collections.defaultdict(list)
    for i, name in enumerate(epoch.Model):
        index[normalize_name(name)].append(i)
    rows = []
    for _, x in latest.iterrows():
        keys = [normalize_name(x.Model), normalize_name(x.Model.split("/")[-1])]
        candidates = sorted(set(i for k in keys for i in index[k]))
        row = {"leaderboard_Model": x.Model, "candidate_count": len(candidates), "candidate_epoch_models": " | ".join(epoch.iloc[candidates].Model)}
        if len(candidates) == 1:
            e = epoch.iloc[candidates[0]]
            row.update({"epoch_Model": e.Model, "Parameters": e.Parameters,
                        "epoch_parameter_ratio_to_C1": numeric(e.Parameters) / (x["#Params (B)"] * 1e9) if x["#Params (B)"] > 0 else np.nan,
                        "publication_date": e["Publication date"], "N_C1_B": x["#Params (B)"],
                        "training_compute_FLOP": e["Training compute (FLOP)"],
                        "training_dataset_size_raw": e["Training dataset size (total)"],
                        "dataset_size_notes": e["Dataset size notes"],
                        "open_weights": e["Open model weights?"], "domain": e.Domain,
                        "status": "unique_exact_normalized_name_candidate_requires_size_and_variant_check"})
        else:
            row["status"] = "ambiguous" if candidates else "unmatched"
        rows.append(row)
    links = pd.DataFrame(rows)
    csv("C4_exact_name_match_candidates.csv", links)
    macro = epoch.copy()
    macro["publication_date_parsed"] = pd.to_datetime(macro["Publication date"], errors="coerce")
    macro["numeric_training_dataset_size"] = pd.to_numeric(macro["Training dataset size (total)"], errors="coerce")
    macro["language_domain"] = macro.Domain.fillna("").str.contains("Language", case=False)
    macro["reported_open_weights"] = macro["Open model weights?"].fillna("").str.lower().eq("yes")
    # Dataset units differ by model/domain; numeric does not mean comparable tokens.
    csv("C4_language_open_macro_metadata.csv", macro[macro.language_domain & macro.reported_open_weights][[
        "Model", "Publication date", "Parameters", "Training compute (FLOP)", "Training dataset size (total)",
        "Dataset size notes", "Parameters notes", "Open model weights?", "Confidence"]])
    unique = links.candidate_count.eq(1)
    ratios = links.epoch_parameter_ratio_to_C1
    summary = {"matched_unique_name_candidates": int(unique.sum()), "ambiguous_candidates": int(links.candidate_count.gt(1).sum()),
               "candidate_parameter_ratio_outside_half_to_two": int((unique & ratios.notna() & ~ratios.between(.5, 2)).sum()),
               "language_reported_open_weights_rows": int((macro.language_domain & macro.reported_open_weights).sum()),
               "policy": "No C4 N/D/C transfer to temporal baseline until identity, dense/active parameter convention, and dataset units are verified."}
    jdump("C4_matching_summary.json", summary)
    return summary


def extract_c8(lb):
    """Parse every JSON; select lexicographically latest timestamp filename that parses per directory."""
    root = ROOT / "detailed_results"
    all_logs, selected, long_rows, group_rows = [], [], [], []
    n_directories = 0
    for dirname, _, files in os.walk(extended_path(root)):
        jsons = sorted([x for x in files if x.lower().endswith(".json")])
        if not jsons:
            continue
        n_directories += 1
        candidates = []
        for filename in jsons:
            path = Path(dirname) / filename
            try:
                with open(path, "r", encoding="utf-8") as handle:
                    doc = json.load(handle)
                if not isinstance(doc, dict) or not isinstance(doc.get("results"), dict):
                    raise ValueError("JSON lacks results mapping")
                candidates.append((filename, doc))
                all_logs.append({"directory": Path(dirname).name, "file": filename, "parseable": True, "error": "", "selected": False})
            except (json.JSONDecodeError, UnicodeDecodeError, OSError, ValueError) as err:
                all_logs.append({"directory": Path(dirname).name, "file": filename, "parseable": False, "error": str(err), "selected": False})
        if not candidates:
            continue
        filename, doc = candidates[-1]
        for entry in reversed(all_logs):
            if entry["directory"] == Path(dirname).name and entry["file"] == filename:
                entry["selected"] = True
                break
        res, conf = doc["results"], doc.get("config", {})
        name = doc.get("model_name")
        if not name:
            match = re.search(r"(?:^|,)pretrained=([^,]+)", str(conf.get("model_args", "")))
            name = match.group(1) if match else Path(dirname).name
        base = {"directory": Path(dirname).name, "Model": name, "file": filename,
                "model_sha": conf.get("model_sha", conf.get("model_revision", "")),
                "eval_unix_time": numeric(doc.get("date")), "N_params": numeric(conf.get("model_num_parameters")),
                "chat_template_present": bool(doc.get("chat_template")),
                "evaluation_git_hash": doc.get("git_hash", "")}
        mapping = {"BBH": ("leaderboard_bbh", "acc_norm,none"),
                   "MATH Lvl 5": ("leaderboard_math_hard", "exact_match,none"),
                   "GPQA": ("leaderboard_gpqa", "acc_norm,none"),
                   "MUSR": ("leaderboard_musr", "acc_norm,none"),
                   "MMLU-PRO": ("leaderboard_mmlu_pro", "acc,none")}
        row = dict(base)
        strict = res.get("leaderboard_ifeval", {})
        ivec = [numeric(strict.get(k)) for k in ["prompt_level_strict_acc,none", "inst_level_strict_acc,none"]]
        row["IFEval_raw_reported"] = float(np.mean(ivec))
        group_rows.append({**base, "task_group": "IFEval", "metric": "mean(prompt_level_strict_acc,inst_level_strict_acc)", "score": row["IFEval_raw_reported"]})
        for task, (key, metric) in mapping.items():
            row[task + "_raw_reported"] = numeric(res.get(key, {}).get(metric))
            group_rows.append({**base, "task_group": task, "metric": metric, "score": row[task + "_raw_reported"]})
        submap = doc.get("group_subtasks", {})
        group_keys = set(submap) | {"leaderboard"}
        # Preserve leaf scores, metric names, sample sizes and task versions.
        # These are subtask aggregates, not individual question-level responses.
        for task, vals in res.items():
            if task in group_keys or not isinstance(vals, dict):
                continue
            counts = doc.get("n-samples", {}).get(task, {})
            for metric, val in vals.items():
                if "," not in metric or "stderr" in metric:
                    continue
                if not np.isfinite(numeric(val)):
                    continue
                stem, sep, suffix = metric.partition(",")
                stderr = vals.get(stem + "_stderr" + sep + suffix)
                long_rows.append({"directory": base["directory"], "Model": name, "file": filename,
                                  "task": task, "metric": metric, "score": numeric(val), "stderr": numeric(stderr),
                                  "effective_n": numeric(counts.get("effective")) if isinstance(counts, dict) else numeric(counts),
                                  "task_version": doc.get("versions", {}).get(task),
                                  "fewshot": doc.get("n-shot", {}).get(task)})
        # True detailed-task math aggregation, computed directly from the seven leaves.
        mathkeys = submap.get("leaderboard_math_hard", [k for k in res if k.startswith("leaderboard_math_") and k != "leaderboard_math_hard"])
        mvals, weights = [], []
        for key in mathkeys:
            value = numeric(res.get(key, {}).get("exact_match,none"))
            count = doc.get("n-samples", {}).get(key, {})
            weight = numeric(count.get("effective")) if isinstance(count, dict) else numeric(count)
            if np.isfinite(value):
                mvals.append(value)
                weights.append(weight)
        row["math_leaf_count"] = len(mvals)
        row["math_leaf_macro"] = float(np.mean(mvals)) if mvals else np.nan
        row["math_leaf_sample_weighted"] = float(np.average(mvals, weights=weights)) if mvals and np.isfinite(weights).all() and np.sum(weights) > 0 else np.nan
        row["six_groups_complete"] = all(np.isfinite(row[x + "_raw_reported"]) for x in TASKS)
        selected.append(row)
    logs, per_model, long, groups = map(pd.DataFrame, [all_logs, selected, long_rows, group_rows])
    csv("C8_file_parse_log.csv", logs)
    csv("C8_corrupt_files.csv", logs[~logs.parseable])
    csv("C8_selected_models.csv", per_model)
    csv("C8_task_group_scores.csv", groups)
    csv("C8_leaf_task_metrics.csv.gz", long)
    math = long[long.task.str.startswith("leaderboard_math_") & long.metric.eq("exact_match,none")]
    csv("C8_math_leaf_scores.csv", math)
    csv("C8_math_task_summary.csv", math.groupby("task").agg(n_models=("score", "count"), mean_score=("score", "mean"), median_score=("score", "median"), q90=("score", lambda s: s.quantile(.9)), effective_n_min=("effective_n", "min"), effective_n_max=("effective_n", "max")).reset_index())
    joined = per_model.merge(lb[lb.selected_latest][["Model", "Model sha", "type_group", "license_group", "submission_date"] + TASKS + [x + " Raw" for x in TASKS]], on="Model", how="left", validate="many_to_one")
    joined["same_revision"] = joined.model_sha.astype(str).eq(joined["Model sha"].astype(str))
    for task in TASKS:
        joined[task + "_raw_difference"] = joined[task + "_raw_reported"] - joined[task + " Raw"]
    joined["math_macro_minus_parquet_raw"] = joined.math_leaf_macro - joined["MATH Lvl 5 Raw"]
    joined["math_weighted_minus_parquet_raw"] = joined.math_leaf_sample_weighted - joined["MATH Lvl 5 Raw"]
    csv("C8_C1_revision_and_raw_score_comparison.csv", joined)
    math_identity = math.merge(joined[["directory", "type_group", "license_group"]], on="directory", how="left", validate="many_to_one")
    csv("C8_math_task_by_type.csv", math_identity.groupby(["type_group", "task"], dropna=False).agg(n_models=("score", "count"), mean_score=("score", "mean"), median_score=("score", "median")).reset_index())
    summary = {"json_files": len(logs), "directories_with_json": n_directories,
               "parseable_json_files": int(logs.parseable.sum()), "corrupt_files": int((~logs.parseable).sum()),
               "selected_parseable_directories": len(per_model), "unique_model_names": int(per_model.Model.nunique()),
               "six_groups_complete": int(per_model.six_groups_complete.sum()),
               "seven_math_leaves_complete": int(per_model.math_leaf_count.eq(7).sum()),
               "leaf_metric_rows": len(long), "math_leaf_rows": len(math),
               "exact_model_match_C1": int(joined["Model sha"].notna().sum()),
               "same_revision_C1": int(joined.same_revision.sum()),
               "selection_rule": "Per directory, latest lexicographically sorted timestamp filename among parseable JSONs; all files audited",
               "metric_note": "Reported groups are raw proportions, unlike C1 normalized percentages. IFEval is mean of prompt/instance strict metrics. Leaf metrics, sample-weighted math and macro math are separately retained.",
               "individual_example_responses_present": False,
               "raw_score_difference_by_group_same_revision": {task: {"n": int(joined.loc[joined.same_revision, task + "_raw_difference"].notna().sum()), "median_abs": joined.loc[joined.same_revision, task + "_raw_difference"].abs().median(), "max_abs": joined.loc[joined.same_revision, task + "_raw_difference"].abs().max()} for task in TASKS}}
    jdump("C8_coverage_summary.json", summary)
    print(f"C8: {len(logs)} JSON / {n_directories} directories, {len(per_model)} selected, {len(math)} math leaf scores", flush=True)
    return summary, joined


def temporal_baseline(latest):
    """Out-of-time validation. Submission date is not treated as model invention time."""
    valid = latest[latest.submission_date.notna() & latest["#Params (B)"].gt(0)].copy()
    valid["month"] = valid.submission_date.dt.to_period("M").astype(str)
    monthly = []
    scores, predictions, coefficients = [], [], []
    for scope in ["all_observed_sensitivity", "explicit_allowlist"]:
        scoped = valid if scope.startswith("all_") else valid[valid.license_group.eq("explicit_allowlist")]
        for kind in ["all_types", "pretrained", "chat", "finetuned", "merge"]:
            d = scoped.copy() if kind == "all_types" else scoped[scoped.type_group.eq(kind)].copy()
            if not len(d):
                continue
            for month, g in d.groupby("month"):
                monthly.append({"scope": scope, "type_group": kind, "month": month, "n_models": len(g),
                                "mean": g.six_task_mean.mean(), "median": g.six_task_mean.median(),
                                "q90": g.six_task_mean.quantile(.9), "q95": g.six_task_mean.quantile(.95),
                                "max": g.six_task_mean.max(), "best_model": g.loc[g.six_task_mean.idxmax(), "Model"],
                                "sparse_month_lt_20": len(g) < 20})
            if len(d) < 30:
                continue
            dates = np.sort(d.submission_date.unique())
            cutoff = pd.Timestamp(dates[int(np.floor(.8 * (len(dates) - 1)))])
            train = d.submission_date.lt(cutoff).to_numpy()
            if train.sum() < 20 or (~train).sum() < 5:
                continue
            origin = d.submission_date.min()
            feature_frame = pd.DataFrame({"log10_params_B": np.log10(d["#Params (B)"].to_numpy()),
                                          "years_since_first_submission": (d.submission_date - origin).dt.days.to_numpy() / 365.25}, index=d.index)
            if kind == "all_types":
                # Fixed list avoids using test-set category discovery as a fitting decision.
                for group in ["chat", "finetuned", "merge", "continued_pretrained", "other"]:
                    feature_frame["type_" + group] = d.type_group.eq(group).astype(float)
            y = d.six_task_mean.to_numpy()
            for spec in ["train_mean", "params_and_type", "params_date_and_type"]:
                cols = list(feature_frame)
                if spec == "params_and_type":
                    cols.remove("years_since_first_submission")
                if spec == "train_mean":
                    pred = np.repeat(y[train].mean(), (~train).sum())
                else:
                    fit = LinearRegression().fit(feature_frame.loc[train, cols], y[train])
                    pred = fit.predict(feature_frame.loc[~train, cols])
                    for col, coef in zip(cols, fit.coef_):
                        coefficients.append({"scope": scope, "type_group": kind, "specification": spec, "feature": col, "coefficient": coef, "intercept": fit.intercept_, "train_cutoff_exclusive": str(cutoff.date()), "date_origin": str(origin.date())})
                scores.append({"scope": scope, "type_group": kind, "specification": spec,
                               "train_n": int(train.sum()), "test_n": int((~train).sum()), "test_start": str(cutoff.date()),
                               "test_end": str(d.submission_date.max().date()), "RMSE": np.sqrt(mean_squared_error(y[~train], pred)),
                               "MAE": mean_absolute_error(y[~train], pred), "R2": r2_score(y[~train], pred),
                               "prediction_outside_0_100": int(((pred < 0) | (pred > 100)).sum())})
                for (_, row), estimate in zip(d.loc[~train].iterrows(), pred):
                    predictions.append({"scope": scope, "type_group": kind, "specification": spec, "Model": row.Model, "submission_date": row.submission_date, "actual": row.six_task_mean, "predicted": estimate})
    monthly = pd.DataFrame(monthly).sort_values(["scope", "type_group", "month"])
    monthly["cumulative_frontier"] = monthly.groupby(["scope", "type_group"])["max"].cummax()
    csv("monthly_capability_descriptive.csv", monthly)
    csv("temporal_holdout_metrics.csv", pd.DataFrame(scores))
    csv("temporal_holdout_predictions.csv", pd.DataFrame(predictions))
    csv("temporal_train_coefficients.csv", pd.DataFrame(coefficients))
    summary = {"valid_unique_models": len(valid), "date_range": date_range(valid.submission_date),
               "explicit_allowlist_models": int(valid.license_group.eq("explicit_allowlist").sum()),
               "n_fitted_and_reference_specifications": len(scores),
               "causal_interpretation": False, "future_forecasts_produced": False,
               "limitation": "Evaluation submission dates, not verified model release dates. Late-period holdout permits related model families across splits; not a leave-family-out generalization test."}
    jdump("temporal_summary.json", summary)
    return pd.DataFrame(scores), summary


def bridge_baseline(tables):
    """Use C6 once (C5 is nested), with high/medium strata and leave-one-model-out checks."""
    bridge = tables["C6"].copy()
    bridge["stratum"] = bridge.Loss_Comparability.str.split(" ").str[0]
    bridge["six_task_mean"] = bridge[["LB_IFEval", "LB_BBH", "LB_MATH", "LB_GPQA", "LB_MUSR", "LB_MMLU_PRO"]].mean(axis=1)
    bridge["average_discrepancy"] = bridge.LB_Average - bridge.six_task_mean
    csv("bridge_models_audited.csv", bridge)
    stats, preds = [], []
    for stratum in ["High", "Medium", "All_mixed_sensitivity"]:
        d = bridge if stratum.startswith("All") else bridge[bridge.stratum.eq(stratum)]
        x = d[["Val_Loss"]].to_numpy()
        for target in ["LB_Average", "LB_IFEval", "LB_BBH", "LB_MATH", "LB_GPQA", "LB_MUSR", "LB_MMLU_PRO"]:
            y = d[target].to_numpy()
            fit = LinearRegression().fit(x, y)
            estimate, reference = np.zeros(len(d)), np.zeros(len(d))
            for train, test in LeaveOneOut().split(x):
                estimate[test] = LinearRegression().fit(x[train], y[train]).predict(x[test])
                reference[test] = np.mean(y[train])
            pearson, p_p = pearsonr(x[:, 0], y)
            rho, p_s = spearmanr(x[:, 0], y)
            stats.append({"stratum": stratum, "target": target, "n_models": len(d),
                          "loss_min": x.min(), "loss_max": x.max(), "target_min": y.min(), "target_max": y.max(),
                          "pearson": pearson, "pearson_p_descriptive": p_p, "spearman": rho, "spearman_p_descriptive": p_s,
                          "slope": fit.coef_[0], "intercept": fit.intercept_,
                          "LOMO_RMSE": np.sqrt(mean_squared_error(y, estimate)),
                          "LOMO_MAE": mean_absolute_error(y, estimate),
                          "LOMO_R2": r2_score(y, estimate),
                          "LOMO_reference_mean_RMSE": np.sqrt(mean_squared_error(y, reference)),
                          "LOMO_prediction_outside_0_100": int(((estimate < 0) | (estimate > 100)).sum())})
            for (_, row), est, ref in zip(d.iterrows(), estimate, reference):
                preds.append({"stratum": stratum, "target": target, "Model": row.Model, "Val_Loss": row.Val_Loss, "actual": row[target], "LOMO_prediction": est, "LOMO_reference_mean": ref})
    stats = pd.DataFrame(stats)
    csv("bridge_correlations_and_LOMO.csv", stats)
    csv("bridge_LOMO_predictions.csv", pd.DataFrame(preds))
    # Check purported same-model/same-validation-set high stratum against actual B terminal rows.
    b = pd.read_csv(DATA / "B_scaling_laws" / "pythia_training_log_existing.csv")
    comparison = []
    model_column = next((c for c in ["model", "model_name", "Model"] if c in b.columns), None)
    if model_column:
        for _, row in bridge[bridge.stratum.eq("High")].iterrows():
            key = normalize_name(row.Model.split("/")[-1])
            matches = b[b[model_column].map(lambda s: normalize_name(str(s).split("/")[-1])).eq(key)]
            if len(matches):
                last = matches.sort_values("D_tokens_B").iloc[-1]
                comparison.append({"Model": row.Model, "bridge_loss": row.Val_Loss, "B_terminal_loss": last.val_loss,
                                   "loss_difference": row.Val_Loss - last.val_loss,
                                   "bridge_D_tokens_B": row.D_tokens_B, "B_terminal_D_tokens_B": last.D_tokens_B})
    csv("bridge_high_vs_B_final_checkpoints.csv", pd.DataFrame(comparison))
    jdump("bridge_summary.json", {"high_models": int(bridge.stratum.eq("High").sum()), "medium_models": int(bridge.stratum.eq("Medium").sum()),
                                  "missing_D": int(bridge.D_tokens_B.isna().sum()), "B_final_checkpoint_comparisons": len(comparison),
                                  "future_forecast_supported_in_this_pass": False,
                                  "note": "LOMO removes each exact model, not the model family. Mixed validation sets can create source confounding; high stratum only spans Pythia."})
    return stats, comparison


def main():
    configure_stdout()
    np.random.seed(SEED)
    tables = {k: pd.read_csv(ROOT / name, low_memory=False) for k, name in FILES.items()}
    audit = audit_tables(tables)
    lb, latest, identity = prepare_leaderboard(tables)
    epoch = epoch_links(tables["C4"], latest)
    detail, joined = extract_c8(lb)
    temporal, timeinfo = temporal_baseline(latest)
    bridge, comparisons = bridge_baseline(tables)
    high = bridge[(bridge.stratum == "High") & (bridge.target == "LB_Average")].iloc[0]
    mixed = bridge[(bridge.stratum == "All_mixed_sensitivity") & (bridge.target == "LB_Average")].iloc[0]
    primary = temporal[(temporal.scope == "explicit_allowlist") & (temporal.type_group == "pretrained")]
    lines = [
        "# C附件首轮审计与能力演进基线", "", "执行日期：2026-09-24。性质：真实附件上的首轮审计与描述性基线；未生成未来能力预测。",
        "AI辅助：OpenAI Codex（OpenAI）；精确模型版本及发布日期待核对。", "",
        "## 数据范围及身份口径", "",
        f"C1/C2各4,576行，按精确Model名称共有{identity['unique_models']}个模型，多出的{identity['duplicate_extra_rows']}行属于重复模型身份。保留全部原始行并按提交日期取最新记录，日期并列时取原始末行，不按高分挑选。",
        f"C1六项得分均值与Average列最大绝对差为{identity['c1_mean_max_absolute_discrepancy']:.3g}。C1提交时间范围为{audit['dates']['C1_submission']['min'][:10]}—{audit['dates']['C1_submission']['max'][:10]}，不能当作模型发布时间。",
        f"C2发布日期匹配有{identity['C2_publication_after_submission']}行晚于提交日期，其中{identity['C2_publication_later_over_7_days']}行超过7天；已输出明细。1—2天偏差可能涉及时区或公开日期口径，大幅偏差需要核实模型变体及同名错配。本轮不采用该列作技术进步时间。",
        f"C3中{identity['C3_same_model_scores_in_C1']}行与C1模型和六项得分完全对应，不重复加入样本；另有{identity['C3_historical_rows']}条Historical记录，其中{identity['C3_historical_average_inconsistent']}条的Average与六维均值不一致。历史项中的0未提供缺失/实测区分，因此历史整理数据隔离展示，不参与同口径回归。",
        "许可证按显式allowlist、自定义条款、非商业条款、其他已命名、待核验五类保留；allowlist为本轮操作口径而非法律判断。主基线使用显式allowlist，全部观测作为敏感性对照，不把缺失许可证自动归为开源。预训练、聊天、微调、合并和持续预训练分开标注。", "",
        "## C4/C7元数据", "",
        f"C4共3,523行，发布时间跨度为{audit['dates']['C4_publication']['min'][:10]}—{audit['dates']['C4_publication']['max'][:10]}，与榜单截止时间不同。匹配采用去标点的小写全名或仓库basename精确匹配，得到{epoch['matched_unique_name_candidates']}个唯一名称候选，{epoch['ambiguous_candidates']}个歧义候选；其中{epoch['candidate_parameter_ratio_outside_half_to_two']}个唯一候选参数比偏离[0.5,2]。候选仍需核对变体及总参数/激活参数，未将未经核验的训练量补入模型。",
        "C4训练数据规模的数值字段并不保证单位均为tokens；保留Dataset size notes。C7上下文长度实际取值为 " + ", ".join(map(str, audit["C7_context_lengths"])) + "。", "",
        "## C8逐子任务的实际使用", "",
        f"扫描{detail['json_files']}个JSON、{detail['directories_with_json']}个模型目录，{detail['corrupt_files']}个文件无法解析；每目录选时间戳文件名最新且可解析的记录，得到{detail['selected_parseable_directories']}个目录，{detail['six_groups_complete']}个六维完整。全部选择与损坏日志均已保存。",
        f"实际提取{detail['leaf_metric_rows']}行叶子任务指标，其中数学七个子任务共{detail['math_leaf_rows']}行，{detail['seven_math_leaves_complete']}个模型数学七项完整。分别输出原始任务得分、标准误、样本数、task version、fewshot；生成数学领域均值/分位数及按模型类型的比较。JSON不含每一道题的作答记录，因此这里的“逐任务”指子任务级汇总，不能声称逐样本分析。",
        "C8的reported group是0—1原始指标，C1是经过榜单处理后的分数，两者不能直接相减作预测误差。已通过原始Parquet的Raw列及Model sha比较，并分别保留数学七项宏平均和按样本数加权平均；不同汇总方式的差异已留痕，不覆盖原始得分。", "",
        "## 历史基线与时间外检验", "",
        f"有效参数及提交时间的去重模型有{timeinfo['valid_unique_models']}个，显式allowlist内{timeinfo['explicit_allowlist_models']}个。按类型与许可口径输出逐月样本数、中位数、90%/95%分位、当月最大值及累计前沿；少于20模型的月份标记为稀疏。",
        "回归比较训练均值、log10参数量（含类型控制）、log10参数量+提交日期（含类型控制）三种规格。按独立提交日期的前80%/后20%划分，整天留后，不随机打散；所有系数仅由前期样本拟合。模型族仍可能跨期出现，后续必须增加leave-family-out检验。N/D/C未同时进入，避免人为共线性。",
    ]
    for _, row in primary.iterrows():
        lines.append(f"- 显式allowlist预训练组 {row.specification}：训练{row.train_n}、测试{row.test_n}，测试起点{row.test_start}，RMSE={row.RMSE:.3f}、MAE={row.MAE:.3f}、R²={row.R2:.3f}。")
    lines.extend(["", "时间项只是榜单提交批次与能力的条件关联，不是技术进步因果贡献；当前十个月左右的同协议窗口不足以直接论证多年增长率。", "", "## Loss—Benchmark桥接", "",
                  "C5的43模型全部包含于C6的75模型中，交叠Loss和Average未变化，因此仅对C6计数一次。高可比7个Pythia模型，其他68个为不同验证集近似Loss且D缺失；混合相关只作为敏感性展示。",
                  f"高可比组Loss范围[{high.loss_min:.4f},{high.loss_max:.4f}]，平均能力范围[{high.target_min:.3f},{high.target_max:.3f}]。Loss与Average Pearson={high.pearson:.3f}、Spearman={high.spearman:.3f}；留一模型线性桥接RMSE={high.LOMO_RMSE:.3f}，留一训练均值RMSE={high.LOMO_reference_mean_RMSE:.3f}，留一R²={high.LOMO_R2:.3f}。",
                  f"混合75模型相关Pearson={mixed.pearson:.3f}、留一RMSE={mixed.LOMO_RMSE:.3f}；该关系可能混入损失来源、分词器、模型族与评测协议差异，不作为跨族预测证明。高可比组与B终点匹配比较{len(comparisons)}个模型。",
                  "所有六任务均分别计算相关和留一模型指标。高可比样本只覆盖Pythia且能力跨度很窄，本轮不强行给出未来Benchmark预测，也不将混合组拟合优度视为已解决桥接问题。", "",
                  "## 可复现产物与下一步", "",
                  "运行 `python solution/src/evolution_audit.py` 可重建本报告及 `solution/outputs/evolution/` 的CSV/JSON。主要文件为 field_audit.csv、leaderboard_latest_per_model.csv、C3_provenance_and_score_audit.csv、C4_exact_name_match_candidates.csv、C8_file_parse_log.csv、C8_leaf_task_metrics.csv.gz、C8_math_task_summary.csv、monthly_capability_descriptive.csv、temporal_holdout_metrics.csv、bridge_correlations_and_LOMO.csv。",
                  "下一步先人工审核C2/C4模型身份及日期异常、核实C8汇总公式与版本，再建立按基础模型族的独立检验；只有桥接与历史口径通过验证后，才连接问题二/三开展附带不确定性的情景预测。"])
    write_report("evolution_baseline.md", "\n".join(lines) + "\n")
    jdump("run_summary.json", {"date": "2026-09-24", "seed": SEED, "identity": identity, "C4": epoch, "C8": detail, "temporal": timeinfo,
                               "bridge_high_average": high.to_dict(), "forecast_produced": False})
    print("Evolution audit complete:", OUT, flush=True)


if __name__ == "__main__":
    main()
