from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", type=Path, required=True)
    ap.add_argument("--run-id", required=True)
    args = ap.parse_args()
    run = args.workspace.resolve()/"diagnostics/TASK-T08"/args.run_id
    verification = read_json(run/"verification.json")
    summary = read_json(run/"run_summary.json")
    summary["verification"] = {"file": "verification.json", "status": "PASS" if verification["n_fail"] == 0 else "FAIL",
                               "n_checks": verification["n_checks"], "n_pass": verification["n_pass"], "n_fail": verification["n_fail"],
                               "verifier_is_independent": verification["verifier_is_independent"], "imports_execution_module": verification["imports_execution_module"]}
    summary["manifest_status"] = "PENDING_FINAL_GENERATION"
    summary["finalized_at_utc"] = datetime.now(timezone.utc).isoformat()
    (run/"run_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")

    snapshot = run/"code_snapshot"
    if snapshot.exists():
        raise RuntimeError("code_snapshot already exists; refusing to overwrite")
    snapshot.mkdir(parents=True)
    for path in sorted((run/"code").glob("*.py")):
        shutil.copy2(path, snapshot/path.name)

    checks = read_json(run/"checks.json")
    support = summary["historical_growth_support"]
    taskwise = __import__("pandas").read_csv(run/"taskwise_progress.csv")
    lines = [
        "# TASK-T08 交接：规模/非规模分解与12/24个月情景",
        "",
        f"- run_id: `{args.run_id}`",
        "- status: `COMPLETE_PENDING_CONTROLLER_REVIEW`",
        f"- forecast_origin: `{summary['forecast_origin']}`",
        "- T05 eligibility: `CONDITIONAL_ASSOCIATION_ONLY`; six tasks and auxiliary mean remain `CONSTANT`.",
        f"- growth support: independent families `{support['n_independent_model_families']}`, valid family-level intervals `{support['n_valid_family_level_intervals']}`; identifiable `{support['identifiable']}`.",
        "- main benchmark scale-associated component: exactly `0`; remainder is only a non-scale associated residual / conditional remainder.",
        "- benchmark future output: `CONDITIONAL_BASELINE_ONLY` + `NOT_IDENTIFIABLE_PROGRESS`; no verified time trend.",
        "- Loss space: `M0_B1` / `S00_NULL_M0_B1` / `H=2048` kept separate; growth scenarios `NOT_IDENTIFIABLE`; no Loss-to-benchmark conversion.",
        f"- checks: {checks['n_checks']} entries, initial FAIL={checks['n_fail']}; independent verification: {verification['n_checks']} checks, PASS={verification['n_pass']}, FAIL={verification['n_fail']}.",
        "- output_manifest is generated only after this handoff, verification, checks, summary, log, and code_snapshot are frozen.",
        "",
        "## Six-task baseline entries",
        "",
        "| task | baseline points | conditional low | conditional high | 12m | 24m | future eligibility |",
        "|---|---:|---:|---:|---|---|---|",
    ]
    for _, r in taskwise.iterrows():
        lines.append(f"| {r['benchmark_task']} | {r['constant_baseline_points']:.6f} | {r['conditional_interval_low_points']:.6f} | {r['conditional_interval_high_points']:.6f} | {r['progress_12m_status']} | {r['progress_24m_status']} | {r['benchmark_future_eligibility']} |")
    lines += ["", "## Boundary", "", "This run does not modify 00-05, T05/T07, Q1/Q2/Q3, or the paper. It stops after T08 outputs are registered.", ""]
    (run/"handoff.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print(json.dumps({"verification_pass": verification["n_pass"], "verification_fail": verification["n_fail"], "snapshot_files": len(list(snapshot.glob('*.py')))}, ensure_ascii=False))
    return 1 if verification["n_fail"] else 0


if __name__ == "__main__":
    raise SystemExit(main())


