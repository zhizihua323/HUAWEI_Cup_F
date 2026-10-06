from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path


ROOT = Path.cwd()
RUN = ROOT / "diagnostics/TASK-T06E-INTEGRATE/20260925T110904+08"


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


for path in (RUN / "code").glob("*.py"):
    shutil.copy2(path, RUN / "code_snapshot" / path.name)

review = """# TASK-T06E-INTEGRATE 主控集成审查

结论：通过。B-R1纠正了profile物理坐标和G4候选口径；22/22全拟合点复现，MQ-add的G1–G4全部通过。因此MQ-add获得`B6_SOURCE_CONDITIONAL_ACCEPTED`资格，但只限B6来源内。

联合主模型仍为`M0_B1`，`quality_enabled=false`、`mixture_transport_enabled=false`。A侧`Q_baseline`与B侧`Q_score`没有样本级配对，桥接继续为`NOT_IDENTIFIABLE`；H1–H3及跨接B1的质量效应均为`SCENARIO_ONLY`。MQ-eff的eta触及下界，只作敏感性。B8保留为与B6方向冲突的证据，不估计反向统一系数。

P分支预注册的21个情景原样保留，未新增、删除或调序。集成只把已验收的B1、B6参数和资格填入槽位，没有重拟合模型，也没有执行预算优化。RegMix线性模型只在1M来源内具备验证支持；60M/1B为跨尺度运输审计，向B1运输仍是情景。固定域质量下`Q_mix=p^Tq`位于p列空间，因此Q与完整p不能作为两个独立自由坐标同时优化。
"""
(RUN / "integration_review.md").write_text(review, encoding="utf-8")

handoff = """# TASK-T06E-INTEGRATE handoff

- Status: COMPLETE
- B-R1 review: PASS
- MQ-add: ACCEPT_B6_SOURCE_RELATION; B6 source-conditional only
- MQ-eff: SENSITIVITY_ONLY; eta at lower bound
- Joint primary: M0_B1, quality off, mixture transport off
- A/B bridge: NOT_IDENTIFIABLE
- RegMix to B1: SCENARIO_ONLY
- B8: CONFLICT_EVIDENCE
- Scenario registry: 21/21 sealed IDs retained
- No model refit; no T07 optimization executed

T07必须读取`t07_model_contract.json`、`t07_parameter_table.csv`与`scenario_registry_filled.csv`，按预算×科学情景输出结果，不得报告单一普适最优配置。
"""
(RUN / "handoff.md").write_text(handoff, encoding="utf-8")

manifest_files = []
for path in sorted(RUN.rglob("*")):
    if not path.is_file() or path.name == "output_manifest.json" or "__pycache__" in path.parts:
        continue
    manifest_files.append(
        {
            "path": str(path.relative_to(RUN)).replace("\\", "/"),
            "bytes": path.stat().st_size,
            "sha256": sha(path),
        }
    )
manifest = {
    "schema_version": 1,
    "run_id": "20260925T110904+08",
    "status": "COMPLETE",
    "manifest_generated_last": True,
    "file_count": len(manifest_files),
    "files": manifest_files,
}
(RUN / "output_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"status": "COMPLETE", "manifest_files": len(manifest_files)}, ensure_ascii=False))
