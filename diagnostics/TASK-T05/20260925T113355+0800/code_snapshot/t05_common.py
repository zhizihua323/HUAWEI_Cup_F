from __future__ import annotations
import json, hashlib, re, unicodedata
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
RAW = ROOT / "F题" / "real_attachments" / "C_efficiency_evolution"
C01 = ROOT / "diagnostics" / "TASK-C01" / "20260924T175553+08"
R1 = ROOT / "diagnostics" / "TASK-C01-R1" / "20260924T225308+08"
TASKS = ["IFEval", "BBH", "MATH Lvl 5", "GPQA", "MUSR", "MMLU-PRO"]
CUTOFF = pd.Timestamp("2024-09-01")
SEED = 20260925

def sha_text(s: str, n: int = 16) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:n]

def norm_name(s: object) -> str:
    if pd.isna(s):
        return ""
    x = unicodedata.normalize("NFKC", str(s)).strip().lower()
    x = x.replace("_", "/").replace("-", "")
    x = re.sub(r"[\s\.]+", "", x)
    return x

def parse_date(s: object):
    return pd.to_datetime(s, errors="coerce")

def model_family(name: object) -> str:
    s = "" if pd.isna(name) else str(name)
    low = s.lower()
    rules = [
        ("pythia", "Pythia"), ("qwen", "Qwen"), ("llama", "Llama"),
        ("gemma", "Gemma"), ("mixtral", "Mistral"), ("mistral", "Mistral"),
        ("falcon", "Falcon"), ("phi", "Phi"), ("yi", "Yi"),
        ("opt-", "OPT"), ("deepseek", "DeepSeek"), ("bloom", "BLOOM"),
        ("gpt-neox", "GPT-NeoX"), ("smollm", "SmolLM2"), ("zephyr", "Zephyr"),
    ]
    for key, fam in rules:
        if key in low:
            return fam
    if "/" in s:
        return s.split("/", 1)[0]
    return "Unresolved"

def unique_nonnull(series):
    vals = []
    for v in series:
        if pd.isna(v):
            continue
        t = str(v).strip()
        if t == "" or t.lower() in {"nan", "none", "null"}:
            continue
        if t not in vals:
            vals.append(t)
    return vals

def unique_dates(series):
    return sorted({pd.Timestamp(v) for v in pd.to_datetime(series, errors="coerce").dropna()})

def write_json(path: Path, obj: object):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

def loss_definition_record(source_table: str, row: pd.Series) -> dict:
    ls = str(row.get("Loss_Source", ""))
    lc = str(row.get("Loss_Comparability", ""))
    low = ls.lower()
    if "same validation" in lc.lower():
        validation_set = "Same validation set within Pythia attachment B"
        loss_kind = "training_log"
    elif "validation loss" in low:
        validation_set = "Report-specific validation set (not harmonized)"
        loss_kind = "validation_loss"
    elif "model card" in low:
        validation_set = "Model-card evaluation set (unspecified)"
        loss_kind = "model_card_reported_loss"
    elif "training loss" in low:
        validation_set = "Report-specific training evaluation (not harmonized)"
        loss_kind = "training_loss"
    elif "final loss" in low:
        validation_set = "Report-specific final evaluation (not harmonized)"
        loss_kind = "final_loss"
    elif "pile validation" in low:
        validation_set = "Pile validation set (report-specific)"
        loss_kind = "validation_loss"
    else:
        validation_set = "Not explicit in source table"
        loss_kind = "unspecified"
    if "at convergence" in low:
        stage = "convergence"
        token_position = "unspecified from table"
    elif "final checkpoint" in low:
        stage = "final checkpoint"
        token_position = f"D={row.get('D_tokens_B')}B tokens"
    elif "final loss" in low:
        stage = "final reported checkpoint"
        token_position = "unspecified from table"
    else:
        stage = "unspecified training stage"
        token_position = "unspecified from table"
    key = f"{ls}||{lc}"
    return {
        "loss_definition_id": "LD_" + sha_text(key, 12),
        "source_table": source_table,
        "loss_source": ls,
        "loss_comparability": lc,
        "loss_kind": loss_kind,
        "validation_set": validation_set,
        "training_stage": stage,
        "token_position": token_position,
    }

def load_inputs() -> dict:
    return {
        "C1": pd.read_csv(RAW / "leaderboard_cleaned.csv"),
        "C2": pd.read_csv(RAW / "leaderboard_enhanced.csv"),
        "C3": pd.read_csv(RAW / "leaderboard_extended_timeseries.csv"),
        "C4": pd.read_csv(RAW / "epoch_all_ai_models.csv"),
        "C5": pd.read_csv(RAW / "loss_benchmark_bridge.csv"),
        "C6": pd.read_csv(RAW / "loss_benchmark_bridge_expanded.csv"),
        "C7": pd.read_csv(RAW / "model_architecture_metadata.csv"),
        "C8_wide": pd.read_csv(R1 / "c8_model_wide_corrected.csv"),
        "C8_directory": pd.read_csv(R1 / "c8_directory_aggregate_corrected.csv"),
        "C8_task": pd.read_csv(R1 / "c8_model_task_aggregate_corrected.csv"),
        "C8_runs": pd.read_csv(C01 / "c8_group_scores_all_runs.csv"),
        "C8_parse": pd.read_csv(C01 / "c8_parse_log.csv"),
        "C8_corrupt": pd.read_csv(C01 / "c8_corrupt_files.csv"),
        "C8_file_counts": pd.read_csv(C01 / "c8_directory_file_counts.csv"),
        "C9": pd.read_parquet(RAW / "data" / "train-00000-of-00001.parquet"),
    }

def metadata_for_name(name: str, c1: pd.DataFrame, c2: pd.DataFrame) -> dict:
    r1 = c1[c1["Model"] == name]
    r2 = c2[c2["Model"] == name]
    dates = unique_dates(r1["Submission Date"]) if len(r1) else []
    pubdates = unique_dates(r2["Epoch_AI_Publication_Date"]) if len(r2) else []
    params = unique_nonnull(r1["#Params (B)"]) if len(r1) else []
    licenses = unique_nonnull(r1["Hub License"]) if len(r1) else []
    types = unique_nonnull(r1["Type"]) if len(r1) else []
    openw = unique_nonnull(r2["Epoch_AI_Open_Weights"]) if len(r2) else []
    def one(vals):
        return vals[0] if len(vals) == 1 else ""
    return {
        "submission_date": dates[0] if len(dates) == 1 else pd.NaT,
        "publication_date": pubdates[0] if len(pubdates) == 1 else pd.NaT,
        "hub_license": one(licenses) if len(licenses) <= 1 else "AMBIGUOUS",
        "model_type": one(types) if len(types) <= 1 else "AMBIGUOUS",
        "open_weights": one(openw) if len(openw) <= 1 else "AMBIGUOUS",
        "params_B": float(params[0]) if len(params) == 1 else np.nan,
        "date_ambiguous": len(dates) > 1,
    }

def build_identity_crosswalk(data: dict) -> pd.DataFrame:
    c1, c2, c3, c4 = data["C1"], data["C2"], data["C3"], data["C4"]
    c5, c6, c7, c9 = data["C5"], data["C6"], data["C7"], data["C9"]
    wide = data["C8_wide"]
    ref_names = set(c1["Model"].dropna().astype(str)) | set(c5["Model"].astype(str)) | set(c6["Model"].astype(str)) | set(wide["Model"].astype(str))
    exact_ref = {n: "model::" + n for n in ref_names}
    norm_ref = {}
    for n in ref_names:
        norm_ref.setdefault(norm_name(n), set()).add(exact_ref[n])
    wide_meta = wide.set_index("Model", drop=False).to_dict("index")
    records = []
    meta_cache = {}
    c5_set = set(c5["Model"].astype(str))
    c6_set = set(c6["Model"].astype(str))

    def add_record(table, idx, original, canonical, status, note="", extra=None):
        extra = extra or {}
        name = extra.get("canonical_name", canonical.replace("model::", "") if canonical.startswith("model::") else "")
        if canonical.startswith("model::"):
            meta_key = canonical.replace("model::", "")
            if meta_key not in meta_cache:
                meta_cache[meta_key] = metadata_for_name(meta_key, c1, c2)
            meta = meta_cache[meta_key]
        else:
            meta = {}
        rec = {
            "source_table": table,
            "source_row_number": int(idx) + 1,
            "original_name": "" if pd.isna(original) else str(original),
            "canonical_model_id": canonical,
            "canonical_name": name,
            "match_status": status,
            "match_rule": note,
            "model_family": model_family(name or original),
            "params_B": meta.get("params_B", np.nan),
            "submission_date": meta.get("submission_date", pd.NaT),
            "publication_date": meta.get("publication_date", pd.NaT),
            "hub_license": meta.get("hub_license", ""),
            "open_weights": meta.get("open_weights", ""),
            "model_type": meta.get("model_type", ""),
            "date_ambiguous": meta.get("date_ambiguous", False),
            "c8_model_key": "",
            "c8_six_task_complete": pd.NA,
            "c5_present": False,
            "c6_present": False,
        }
        if name in wide_meta:
            wm = wide_meta[name]
            rec.update({
                "c8_model_key": wm.get("model_key", ""),
                "c8_six_task_complete": bool(wm.get("six_task_complete", False)),
            })
        rec["c5_present"] = rec["original_name"] in c5_set or rec["canonical_name"] in c5_set
        rec["c6_present"] = rec["original_name"] in c6_set or rec["canonical_name"] in c6_set
        rec.update(extra)
        records.append(rec)

    for idx, val in c1["Model"].items():
        add_record("C1", idx, val, exact_ref.get(str(val), "UNRESOLVED::C1::" + sha_text(str(val))), "exact_raw" if str(val) in exact_ref else "unmatched", "C1 canonical raw string")
    for idx, val in c2["Model"].items():
        add_record("C2", idx, val, exact_ref.get(str(val), "UNRESOLVED::C2::" + sha_text(str(val))), "exact_raw" if str(val) in exact_ref else "unmatched", "C2 exact raw string")
    for table, df, key in [("C3", c3, "Model"), ("C4", c4, "Model"), ("C7", c7, "model_name")]:
        for idx, val in df[key].items():
            s = "" if pd.isna(val) else str(val)
            if s in exact_ref:
                canonical, status, rule = exact_ref[s], "exact_raw", f"{table} exact raw string"
            else:
                hits = norm_ref.get(norm_name(s), set())
                if len(hits) == 1:
                    canonical, status, rule = next(iter(hits)), "unique_normalized", f"{table} unique normalized alias; not bridge-eligible"
                elif len(hits) > 1:
                    canonical, status, rule = f"AMBIGUOUS::{table}::{sha_text(s)}", "ambiguous", f"{table} normalized collision"
                else:
                    canonical, status, rule = f"UNRESOLVED::{table}::{sha_text(s)}", "unmatched", f"{table} no unique reference"
            add_record(table, idx, s, canonical, status, rule)
    for table, df in [("C5", c5), ("C6", c6)]:
        for idx, val in df["Model"].items():
            s = str(val)
            canonical = exact_ref.get(s, "UNRESOLVED::" + table + "::" + sha_text(s))
            add_record(table, idx, s, canonical, "exact_raw" if s in exact_ref else "unmatched", f"{table} exact bridge key")
    for idx, val in wide["Model"].items():
        s = str(val)
        canonical = exact_ref.get(s, "model::" + s)
        add_record("C8", idx, s, canonical, "exact_raw" if s in exact_ref else "unmatched", "C8 R1 corrected raw model field; no fuzzy identity")
    for idx, row in c9.iterrows():
        val = row.get("fullname", row.get("Model", ""))
        s = "" if pd.isna(val) else str(val)
        if s in exact_ref:
            canonical, status, rule = exact_ref[s], "exact_raw", "C9 exact fullname"
        else:
            hits = norm_ref.get(norm_name(s), set())
            canonical, status, rule = (next(iter(hits)), "unique_normalized", "C9 unique normalized mirror alias; not independent evidence") if len(hits) == 1 else (f"UNRESOLVED::C9::{sha_text(s)}", "unmatched", "C9 no unique reference")
        add_record("C9", idx, s, canonical, status, rule)
    out = pd.DataFrame(records)
    return out

def build_loss_catalog(c5: pd.DataFrame, c6: pd.DataFrame, wide: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for table, df in [("C5", c5), ("C6", c6)]:
        for _, r in df.iterrows():
            d = loss_definition_record(table, r)
            d.update({"Model": r["Model"], "D_tokens_B": r.get("D_tokens_B", np.nan), "Val_Loss": r.get("Val_Loss", np.nan)})
            rows.append(d)
    raw = pd.DataFrame(rows)
    recs = []
    for (lid,), g in raw.groupby(["loss_definition_id"], dropna=False):
        source_tables = sorted(g["source_table"].unique())
        models = set(g["Model"])
        w = wide[wide["Model"].isin(models)]
        d_avail = g["D_tokens_B"].notna().sum()
        rec = g.iloc[0].to_dict()
        n_c8_complete = int(w["six_task_complete"].sum())
        main_eligible = bool(
            "High (same model, same validation set)" in str(rec["loss_comparability"])
            and rec["loss_kind"] == "training_log"
            and n_c8_complete > 0
        )
        rec.update({
            "source_tables": "|".join(source_tables),
            "n_source_rows": int(len(g)),
            "n_unique_models": int(g["Model"].nunique()),
            "n_c8_exact": int(w["Model"].nunique()),
            "n_c8_complete": n_c8_complete,
            "n_c8_partial": int((~w["six_task_complete"]).sum()),
            "D_available_n": int(d_avail),
            "D_missing_n": int(g["D_tokens_B"].isna().sum()),
            "main_bridge_eligible": main_eligible,
            "role": "main_comparable" if main_eligible else "stratified_or_source_transfer_only",
            "exact_text_equivalent_across_sources": bool(len(source_tables) > 1),
            "note": "Exact Loss_Source and Loss_Comparability text; no semantic rescaling.",
        })
        recs.append(rec)
    out = pd.DataFrame(recs).drop(columns=["source_table", "Model", "D_tokens_B", "Val_Loss"], errors="ignore")
    return out.sort_values(["main_bridge_eligible", "source_tables", "loss_source"], ascending=[False, True, True])

def build_comparability_strata(c5: pd.DataFrame, c6: pd.DataFrame, wide: pd.DataFrame) -> pd.DataFrame:
    rows = []
    complete = set(wide.loc[wide["six_task_complete"], "Model"])
    partial = set(wide.loc[~wide["six_task_complete"], "Model"])
    def add(source, tag, models, comparability, loss_source, main, role, note):
        models = set(models)
        rows.append({
            "stratum_id": f"{source}:{sha_text(tag, 10)}",
            "source_table": source,
            "stratum": tag,
            "loss_comparability": comparability,
            "loss_source": loss_source,
            "n_source_rows": len(models),
            "n_unique_models": len(models),
            "n_c8_complete": len(models & complete),
            "n_c8_partial": len(models & partial),
            "D_available_n": int(c5[c5["Model"].isin(models)]["D_tokens_B"].notna().sum() + c6[c6["Model"].isin(models)]["D_tokens_B"].notna().sum()) if source == "C5+C6" else int((c5 if source == "C5" else c6)[(c5 if source == "C5" else c6)["Model"].isin(models)]["D_tokens_B"].notna().sum()),
            "main_bridge_eligible": main,
            "analysis_role": role,
            "note": note,
        })
    add("C5", "ALL_ROWS", set(c5["Model"]), "mixed", "all C5 sources", False, "descriptive", "Not pooled across definitions.")
    add("C6", "ALL_ROWS", set(c6["Model"]), "mixed", "all C6 sources", False, "descriptive", "Not pooled across definitions.")
    for (source, df) in [("C5", c5), ("C6", c6)]:
        for (lc, ls), g in df.groupby(["Loss_Comparability", "Loss_Source"], dropna=False):
            main = str(lc).startswith("High") and source == "C5"
            add(source, f"{lc} | {ls}", set(g["Model"]), lc, ls, main, "main_comparable" if main else "stratified_or_source_transfer_only", "Exact definition text from source table.")
    add("C5+C6", "C5_inside_C6_exact_model_and_values", set(c5["Model"]) & set(c6["Model"]), "mixed source text", "exact model overlap", False, "source_linkage_not_independent_validation", "C5 rows are a 43/43 exact-value subset of C6; this is linkage, not a held-out test.")
    add("C5+C6", "C5_High_to_C6_Medium_source_transfer", set(c5.loc[c5["Loss_Comparability"].str.startswith("High"), "Model"]) | set(c6.loc[c6["Loss_Comparability"].str.startswith("Medium"), "Model"]), "different validation sets", "C5 High vs C6 Medium", False, "source_transfer_only", "Never called ordinary holdout.")
    return pd.DataFrame(rows)

def build_duplicate_resolution(data: dict) -> pd.DataFrame:
    counts = data["C8_file_counts"].set_index("directory")
    parse = data["C8_parse"]
    runs = data["C8_runs"]
    c5_models = set(data["C5"]["Model"].astype(str))
    c6_models = set(data["C6"]["Model"].astype(str))
    rows = []
    for directory, cr in counts[counts["n_json_files"] > 1].iterrows():
        pg = parse[parse["directory"] == directory].copy()
        rg = runs[runs["directory"] == directory].copy()
        valid_files = sorted(rg["file"].dropna().astype(str).unique().tolist()) if len(rg) else []
        dates = sorted(pd.to_datetime(rg["eval_unix_date"], errors="coerce").dropna().unique()) if len(rg) else []
        distinct_dates = len(dates) > 1
        selected = ""
        reported = ""
        if distinct_dates:
            sel_dt = max(dates)
            sel = rg[pd.to_datetime(rg["eval_unix_date"], errors="coerce") == sel_dt].sort_values("file")
            selected = str(sel.iloc[0]["file"])
            rest = rg[pd.to_datetime(rg["eval_unix_date"], errors="coerce") != sel_dt]
            reported = "|".join(sorted(rest["file"].dropna().astype(str).unique().tolist()))
            rule = "retain_latest_clear_eval_timestamp_report_other"
            retained_n = 1
            order_basis = "distinct eval_unix_date"
        else:
            rule = "retain_all_runs_same_model_group_no_reliable_order"
            retained_n = len(valid_files)
            order_basis = "single/non-distinct evaluation timestamp; lexicographic filename is not treated as temporal order"
        model_names = sorted(set(pg["model_name"].dropna().astype(str)))
        bridge_target = bool(set(model_names) & (c5_models | c6_models))
        rows.append({
            "directory": directory,
            "n_files_total": int(cr["n_json_files"]),
            "parse_success_n": int((pg["parse_status"] == "ok").sum()),
            "parse_failed_n": int((pg["parse_status"] != "ok").sum()),
            "valid_run_files": "|".join(valid_files),
            "distinct_eval_timestamps_n": len(dates),
            "ordering_basis": order_basis,
            "resolution_rule": rule,
            "selected_file": selected,
            "reported_alternative_file": reported,
            "retained_run_count": retained_n,
            "model_identity_candidates": "|".join(model_names),
            "same_model_group_id": "group::" + (model_names[0] if len(model_names) == 1 else "directory::" + directory),
            "bridge_exact_match": bridge_target,
            "leakage_guard": "All retained runs of this model remain in one group if used downstream.",
            "note": "No C5/C6 bridge candidate belongs to a multi-file directory." if not bridge_target else "Bridge candidate check requires explicit group review.",
        })
    return pd.DataFrame(rows).sort_values("directory")

def build_coverage_file(data: dict) -> pd.DataFrame:
    corrupt = data["C8_corrupt"]
    wide = data["C8_wide"]
    directory = data["C8_directory"].set_index("directory")
    rows = []
    for _, r in corrupt.iterrows():
        d = directory.loc[r["directory"]]
        rows.append({
            "record_type": "corrupt_json",
            "record_id": f"{r['directory']}::{r['file']}",
            "model_or_directory": r["directory"],
            "source_file": r["file"],
            "parse_status": r["parse_status"],
            "n_valid_results": int(d["n_results_valid"]),
            "n_files_parse_success": int(d["n_files_parse_success"]),
            "n_files_parse_failed": int(d["n_files_parse_failed"]),
            "score_assigned": False,
            "complete_six_task_eligible": False,
            "coverage_effect": "May reduce task coverage; no imputation or score assignment.",
            "reason": str(r["error_message"]),
        })
    for _, r in wide[~wide["six_task_complete"]].iterrows():
        rows.append({
            "record_type": "partial_model",
            "record_id": r["model_key"],
            "model_or_directory": r["Model"],
            "source_file": "",
            "parse_status": "ok_partial_tasks",
            "n_valid_results": int(r["n_tasks_valid"]),
            "n_files_parse_success": int(r["n_files_parse_success"]),
            "n_files_parse_failed": int(r["n_files_parse_failed"]),
            "score_assigned": False,
            "complete_six_task_eligible": False,
            "coverage_effect": "Retained only for task-level/partial coverage; excluded from six-task means and bridge fitting.",
            "reason": f"n_tasks_valid={int(r['n_tasks_valid'])} < 6",
        })
    return pd.DataFrame(rows)

def build_bridge_dataset(data: dict) -> pd.DataFrame:
    wide = data["C8_wide"].copy()
    c5 = data["C5"].copy()
    c6 = data["C6"].copy()
    for df in [c5, c6]:
        df["_ld"] = [loss_definition_record("C5" if df is c5 else "C6", r)["loss_definition_id"] for _, r in df.iterrows()]
    x = c6.merge(wide[["Model", "model_key"] + TASKS + ["six_task_complete", "source_parse_incomplete", "n_files_total"]], on="Model", how="inner", validate="one_to_one")
    x = x[x["six_task_complete"]].copy()
    x = x.merge(c5[["Model", "D_tokens_B", "Val_Loss", "Loss_Source", "Loss_Comparability", "_ld"]].rename(columns={
        "D_tokens_B": "c5_D_tokens_B", "Val_Loss": "c5_Val_Loss", "Loss_Source": "c5_Loss_Source",
        "Loss_Comparability": "c5_Loss_Comparability", "_ld": "c5_loss_definition_id"
    }), on="Model", how="left", validate="one_to_one")
    x = x.rename(columns={"D_tokens_B": "c6_D_tokens_B", "Val_Loss": "c6_Val_Loss", "Loss_Source": "c6_Loss_Source", "Loss_Comparability": "c6_Loss_Comparability", "_ld": "c6_loss_definition_id", "N_params_B": "params_B"})
    for col in TASKS:
        x[col + "_pct"] = pd.to_numeric(x[col], errors="coerce") * 100.0
    x["benchmark_mean_aux"] = x[[c + "_pct" for c in TASKS]].mean(axis=1)
    x["c5_present"] = x["c5_Val_Loss"].notna()
    x["main_bridge_eligible"] = x["c5_present"] & x["c5_Loss_Comparability"].astype(str).str.startswith("High")
    x["analysis_role"] = np.where(x["main_bridge_eligible"], "main_comparable", "conditional_source_transfer_only")
    x["primary_loss_source"] = np.where(x["c5_present"], x["c5_Loss_Source"], x["c6_Loss_Source"])
    x["primary_loss_definition_id"] = np.where(x["c5_present"], x["c5_loss_definition_id"], x["c6_loss_definition_id"])
    x["primary_loss"] = np.where(x["c5_present"], x["c5_Val_Loss"], x["c6_Val_Loss"])
    x["D_tokens_B"] = np.where(x["c5_D_tokens_B"].notna(), x["c5_D_tokens_B"], x["c6_D_tokens_B"])
    x["loss_definition_comparable_to_main"] = x["main_bridge_eligible"]
    x["model_family"] = x["Model"].map(model_family)
    x["logN"] = np.log(pd.to_numeric(x["params_B"], errors="coerce"))
    x["logD"] = np.where(pd.to_numeric(x["D_tokens_B"], errors="coerce").notna(), np.log(pd.to_numeric(x["D_tokens_B"], errors="coerce")), np.nan)
    c1 = data["C1"]
    subm = []
    ambiguous = []
    for name in x["Model"]:
        dates = unique_dates(c1.loc[c1["Model"] == name, "Submission Date"])
        ambiguous.append(len(dates) > 1)
        subm.append(dates[0] if len(dates) == 1 else pd.NaT)
    x["submission_date"] = subm
    x["date_ambiguous"] = ambiguous
    x["time_days_from_cutoff"] = (pd.to_datetime(x["submission_date"], errors="coerce") - CUTOFF).dt.days
    x["scale_bin"] = pd.cut(pd.to_numeric(x["params_B"], errors="coerce"), bins=[-np.inf, 3.0, 20.0, np.inf], labels=["<=3B", ">3B to <20B", ">=20B"], right=False).astype(str)
    x["same_model_run_count"] = 1
    x["run_group_id"] = x["model_key"]
    x["c8_anchor"] = "TASK-C01-R1/c8_model_wide_corrected.csv"
    x["target_units"] = "leaderboard points (0-100), C8 fraction x 100"
    keep = ["model_key", "Model", "model_family", "params_B", "D_tokens_B", "submission_date", "time_days_from_cutoff", "scale_bin", "analysis_role", "main_bridge_eligible", "c5_present", "c5_Loss_Source", "c5_Loss_Comparability", "c5_loss_definition_id", "c6_Loss_Source", "c6_Loss_Comparability", "c6_loss_definition_id", "primary_loss_source", "primary_loss_definition_id", "primary_loss", "loss_definition_comparable_to_main", "logN", "logD", "same_model_run_count", "run_group_id", "date_ambiguous", "source_parse_incomplete", "n_files_total", "c8_anchor", "target_units"] + [c + "_pct" for c in TASKS] + ["benchmark_mean_aux"]
    return x[keep].sort_values("Model").reset_index(drop=True)

def build_split_registry(ds: pd.DataFrame) -> pd.DataFrame:
    rows = []
    # Grouped internal folds, assigned deterministically within each cohort; IDs are unique here.
    for cohort, mask in [("main_comparable", ds["main_bridge_eligible"]), ("conditional_full", pd.Series(True, index=ds.index))]:
        sub = ds.loc[mask, ["model_key", "Model"]].sort_values("Model").reset_index(drop=True)
        n = len(sub)
        k = min(5, max(2, n // 3)) if n >= 4 else max(1, n)
        groups = sub["Model"].tolist()
        # deterministic round-robin after seed-stable sorting avoids sklearn dependency during seal freeze.
        for i, row in sub.iterrows():
            fold = i % k if k > 1 else 0
            rows.append({"split_family": "internal_grouped", "split_id": cohort, "model_id": row["Model"], "run_group_id": row["Model"], "role": "train" if False else f"fold_{fold}", "reason": f"model-ID grouped fold among {n} unique models"})
    for _, r in ds.iterrows():
        sid = "time_cutoff_2024-09-01"
        if pd.isna(r["submission_date"]) or bool(r["date_ambiguous"]):
            role, reason = "unassigned", "submission date missing or ambiguous by exact Model"
        elif pd.Timestamp(r["submission_date"]) < CUTOFF:
            role, reason = "train", "submission date before frozen cutoff"
        else:
            role, reason = "test", "submission date on/after frozen cutoff"
        rows.append({"split_family": "time_oos", "split_id": sid, "model_id": r["Model"], "run_group_id": r["run_group_id"], "role": role, "reason": reason})
        role = "test_large" if float(r["params_B"]) >= 20 else "train_nonlarge"
        rows.append({"split_family": "scale_oos", "split_id": "holdout_ge20B", "model_id": r["Model"], "run_group_id": r["run_group_id"], "role": role, "reason": "frozen parameter-size stratum"})
        if r["main_bridge_eligible"]:
            rows.append({"split_family": "source_transfer", "split_id": "C5_High_to_C6_Medium", "model_id": r["Model"], "run_group_id": r["run_group_id"], "role": "train_source", "reason": "C5 High source anchor"})
        elif str(r["c6_Loss_Comparability"]).startswith("Medium"):
            rows.append({"split_family": "source_transfer", "split_id": "C5_High_to_C6_Medium", "model_id": r["Model"], "run_group_id": r["run_group_id"], "role": "test_source_transfer", "reason": "C6 Medium target source, not held out"})
    # family holdouts: test only when at least 3 remain after holdout; roles are generated per candidate family.
    for fam, g in ds.groupby("model_family"):
        if len(g) < 4:
            for _, r in g.iterrows():
                rows.append({"split_family": "leave_family", "split_id": f"holdout::{fam}", "model_id": r["Model"], "run_group_id": r["run_group_id"], "role": "insufficient_oos", "reason": f"family n={len(g)} < 4"})
            continue
        for _, r in g.iterrows():
            rows.append({"split_family": "leave_family", "split_id": f"holdout::{fam}", "model_id": r["Model"], "run_group_id": r["run_group_id"], "role": "test_family", "reason": "complete model family held out"})
        for _, r in ds[~ds["Model"].isin(g["Model"])].iterrows():
            rows.append({"split_family": "leave_family", "split_id": f"holdout::{fam}", "model_id": r["Model"], "run_group_id": r["run_group_id"], "role": "train_other_family", "reason": "training side of leave-family-out split"})
    return pd.DataFrame(rows)

def main():
    out = Path(__file__).resolve().parents[1]
    data = load_inputs()
    cross = build_identity_crosswalk(data)
    cross.to_csv(out / "model_identity_crosswalk.csv", index=False, encoding="utf-8-sig")
    loss_cat = build_loss_catalog(data["C5"], data["C6"], data["C8_wide"])
    loss_cat.to_csv(out / "loss_definition_catalog.csv", index=False, encoding="utf-8-sig")
    strata = build_comparability_strata(data["C5"], data["C6"], data["C8_wide"])
    strata.to_csv(out / "comparability_strata.csv", index=False, encoding="utf-8-sig")
    dup = build_duplicate_resolution(data)
    dup.to_csv(out / "duplicate_run_resolution.csv", index=False, encoding="utf-8-sig")
    cov = build_coverage_file(data)
    cov.to_csv(out / "corrupt_and_partial_coverage.csv", index=False, encoding="utf-8-sig")
    ds = build_bridge_dataset(data)
    ds.to_parquet(out / "bridge_analysis_dataset.parquet", index=False)
    split = build_split_registry(ds)
    split.to_csv(out / "split_registry.csv", index=False, encoding="utf-8-sig")
    summary = {
        "crosswalk_rows": int(len(cross)),
        "crosswalk_canonical_models": int(cross["canonical_model_id"].nunique()),
        "loss_definitions": int(len(loss_cat)),
        "comparability_strata": int(len(strata)),
        "multi_file_directories_checked": int(len(dup)),
        "coverage_rows": int(len(cov)),
        "bridge_models": int(len(ds)),
        "main_comparable_models": int(ds["main_bridge_eligible"].sum()),
        "conditional_source_transfer_models": int((~ds["main_bridge_eligible"]).sum()),
        "partial_models_excluded_from_bridge": int((~data["C8_wide"]["six_task_complete"]).sum()),
        "corrupt_json_excluded_from_scores": int(len(data["C8_corrupt"])),
        "execution_seal_sha256_expected": "7f6805e168f793040f9faa7889dd4eecba7964be19fef34247d470ed4e051e68",
    }
    write_json(out / "prepare_summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()