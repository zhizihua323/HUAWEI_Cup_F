from __future__ import annotations
import hashlib, json, shutil, sys
from datetime import datetime
from pathlib import Path
import platform
import numpy as np
import pandas as pd
import pyarrow

RUN = Path(__file__).resolve().parents[1]
WS = RUN.parents[2]

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

inputs = [
    ("project_brief", WS/"00_PROJECT_BRIEF.md", True),
    ("project_status", WS/"01_PROJECT_STATUS.md", True),
    ("project_decisions", WS/"02_DECISIONS.md", True),
    ("data_catalog", WS/"03_DATA_CATALOG.md", True),
    ("task_queue", WS/"04_TASK_QUEUE.md", True),
    ("review_log", WS/"05_REVIEW_LOG.md", True),
    ("upper_method_T06", WS/"tasks/TASK-T06_尺度桥接识别性与广义缩放律方法裁决.md", True),
    ("construction_order_T06E", WS/"tasks/TASK-T06E_来源内缩放律与质量条件关系验证_尺度桥接情景及T07接口.md", True),
    ("data_description", WS/"tmp/environment_review/数据说明.txt", True),
    ("T03E_interface_parquet", WS/"diagnostics/TASK-T03E/20260925T020032+08/t06_quality_interface.parquet", True),
    ("T03E_interface_json", WS/"diagnostics/TASK-T03E/20260925T020032+08/t06_quality_interface.json", True),
    ("T03E_handoff", WS/"diagnostics/TASK-T03E/20260925T020032+08/handoff.md", True),
    ("T03E_freeze_manifest", WS/"diagnostics/TASK-T03E/20260925T020032+08/phase_a_calibration_freeze/freeze_manifest.json", True),
    ("T03E_output_manifest", WS/"diagnostics/TASK-T03E/20260925T020032+08/output_manifest.json", True),
    ("T03E_checks", WS/"diagnostics/TASK-T03E/20260925T020032+08/checks.json", True),
    ("T03E_verification", WS/"diagnostics/TASK-T03E/20260925T020032+08/verification.json", True),
    ("B6_raw_design_table", WS/"F题/real_attachments/B_scaling_laws/supplementary_NQ_experiment.csv", True),
    ("RegMix_model", WS/"solution/outputs/mixture/model.json", True),
    ("RegMix_audit", WS/"solution/outputs/mixture/audit.json", True),
    ("RegMix_metrics", WS/"solution/outputs/mixture/metrics.csv", True),
    ("RegMix_report", WS/"solution/reports/mixture_baseline.md", True),
    ("RegMix_linear_coefficients", WS/"solution/outputs/mixture/linear_coefficients.csv", True),
    ("RegMix_observed_training_reference", WS/"solution/outputs/mixture/observed_training_reference.json", True),
    ("RegMix_test_1m_conditional_intervals", WS/"solution/outputs/mixture/test_1m_conditional_intervals.json", True),
    ("RegMix_aggregate_predictions", WS/"solution/outputs/mixture/aggregate_predictions.csv", True),
    ("RegMix_domain_metrics", WS/"solution/outputs/mixture/domain_metrics.csv", True),
]
for scale in ["train_1m","test_1m","test_60m","test_1B","est_10b","est_70b"]:
    inputs.append((f"RegMix_{scale}_normalized_p", WS/f"solution/outputs/mixture/{scale}_normalized_mixtures.csv", True))
    if scale == "train_1m":
        pred_name = "linear_train_1m_predictions.csv"
    else:
        pred_name = f"linear_{scale}_predictions.csv"
    inputs.append((f"RegMix_{scale}_linear_predictions", WS/f"solution/outputs/mixture/{pred_name}", True))

A_RAW = WS/"F题/real_attachments/A_data_value"
raw_map = {
    "A4_train_mixture_1m":"regmix_tables/train_mixture_1m.csv",
    "A5_train_loss_1m":"regmix_tables/train_pile_loss_1m.csv",
    "A6_test_mixture_1m":"regmix_tables/test_mixture_1m.csv",
    "A7_test_loss_1m":"regmix_tables/test_pile_loss_1m.csv",
    "A8_test_mixture_60m":"regmix_tables/test_mixture_60m.csv",
    "A9_test_loss_60m":"regmix_tables/test_pile_loss_60m.csv",
    "A10_test_mixture_1B":"regmix_tables/test_mixture_1B.csv",
    "A11_test_loss_1B":"regmix_tables/test_pile_loss_1B.csv",
    "A12_est_mixture_10b":"regmix_tables/est_mixture_10b.csv",
    "A13_est_loss_10b":"regmix_tables/est_pile_loss_10b.csv",
    "A14_est_mixture_70b":"regmix_tables/est_mixture_70b.csv",
    "A15_est_loss_70b":"regmix_tables/est_pile_loss_70b.csv",
    "A16_domain_mapping":"domain_mapping_guide.csv",
    "A17_domain_summary":"regmix_domain_summary.csv",
}
for key, rel in raw_map.items():
    inputs.append((key, A_RAW/rel, True))

input_rows = []
for role, path, readonly in inputs:
    if not path.exists():
        raise RuntimeError(f"required input missing: {path}")
    input_rows.append({
        "role": role,
        "path": str(path.relative_to(WS)).replace("\\", "/"),
        "sha256": sha256(path),
        "bytes": int(path.stat().st_size),
        "read_only": bool(readonly),
    })
input_manifest = {
    "task_id":"TASK-T06E-P",
    "run_id":RUN.name,
    "created_local_time":datetime.now().astimezone().isoformat(timespec="seconds"),
    "files":input_rows,
    "file_count":len(input_rows),
    "protected_paths_not_read_or_modified":[
        "真实A1-A3压缩文件未访问",
        "TASK-T06E-B新run未访问",
        "TASK-T06E-INTEGRATE未创建未访问",
        "旧scaling/mixture/T03E/Q01C产物未写入"
    ],
    "upper_T06_sha256":next(x["sha256"] for x in input_rows if x["role"]=="upper_method_T06"),
    "construction_order_sha256":next(x["sha256"] for x in input_rows if x["role"]=="construction_order_T06E"),
    "T03E_interface_sha256":next(x["sha256"] for x in input_rows if x["role"]=="T03E_interface_parquet"),
}
(RUN/"input_manifest.json").write_text(json.dumps(input_manifest, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")

code_dir = RUN/"code"
snap_dir = RUN/"code_snapshot"
snap_dir.mkdir(exist_ok=True)
code_files = sorted(code_dir.glob("*.py"))
snap_rows = []
for p in code_files:
    shutil.copy2(p, snap_dir/p.name)
    snap_rows.append({"name":p.name,"sha256":sha256(p),"bytes":p.stat().st_size})
(RUN/"code_snapshot/code_snapshot_manifest.json").write_text(json.dumps({"files":snap_rows,"count":len(snap_rows),"copied_before_checks":True}, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")

seal_path = RUN/"scenario_registry/SCENARIO_REGISTRY_SEAL.json"
reg_path = RUN/"scenario_registry/scenario_registry_preregistered.csv"
freeze = {
    "task_id":"TASK-T06E-P",
    "run_id":RUN.name,
    "freeze_stage":"AFTER_SCENARIO_SEAL_AND_READONLY_DERIVATIONS_BEFORE_CHECKS",
    "scenario_registry_sha256":sha256(reg_path),
    "scenario_registry_seal_sha256":sha256(seal_path),
    "input_manifest_sha256":sha256(RUN/"input_manifest.json"),
    "source_snapshot_manifest_sha256":sha256(RUN/"code_snapshot/code_snapshot_manifest.json"),
    "source_code":snap_rows,
    "frozen_decision_artifacts":[
        {"path":"quality_anchor/q_A_anchor.json","sha256":sha256(RUN/"quality_anchor/q_A_anchor.json")},
        {"path":"bridge/quality_bridge_scenarios.json","sha256":sha256(RUN/"bridge/quality_bridge_scenarios.json")},
        {"path":"mixture_audit/p_q_identifiability.json","sha256":sha256(RUN/"mixture_audit/p_q_identifiability.json")},
        {"path":"t07_candidate/t07_scenario_contract_candidate.json","sha256":sha256(RUN/"t07_candidate/t07_scenario_contract_candidate.json")}
    ],
    "solver":"NONE",
    "dimensionless_units":{"p":"simplex","q_A":"score","Q_B":"score"},
    "normalization":{"q_A":"equal-domain arithmetic mean","p":"row-sum normalization preserving zeros"},
    "constraints":{"random_resampling_used":False,"B_model_fitted":False,"RegMix_refit":False,"T07_started":False},
    "environment":{"python":sys.version.split()[0],"numpy":np.__version__,"pandas":pd.__version__,"pyarrow":pyarrow.__version__,"platform":platform.platform()},
    "frozen_local_time":datetime.now().astimezone().isoformat(timespec="seconds"),
}
(RUN/"freeze_manifest.json").write_text(json.dumps(freeze, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
print(json.dumps({"input_count":len(input_rows),"code_count":len(snap_rows),"freeze_manifest":str(RUN/"freeze_manifest.json")}, ensure_ascii=False))
