"""No-solver aggregate artifact writer for the completed 18-case matrix."""
from datetime import datetime, timezone
from pathlib import Path
import json
import sys
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import run_mdc_minimal_2d_fdtd_dipole_tmm_validation_v1 as r

OUT = ROOT / "outputs" / "mdc_fdtd_dipole_tmm_validation_v1" / "fdtd-matrix-20260729T092000Z-602d89c69258"

def dump(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")

state = json.loads((OUT / "state.json").read_text(encoding="utf-8"))
r.postprocess(OUT, state)
cases = state["cases"]
pd.DataFrame(cases).drop(columns=["inventory", "fresh_load_readback"], errors="ignore").to_parquet(OUT / "case_manifest.parquet", index=False)
dump(OUT / "pre_fsp_index.json", [{"case_id": c["case_id"], "path": c.get("pre_fsp", "forensic_salvage"), "sha256": c.get("pre_fsp_sha256", "forensic_not_recorded")} for c in cases])
dump(OUT / "post_fsp_index.json", [{"case_id": c["case_id"], "runtime": c.get("post_fsp", ""), "canonical": c.get("canonical_fsp", ""), "sha256": c.get("post_fsp_sha256", "")} for c in cases])
provenance = {"run_id": OUT.name, "generated_utc": datetime.now(timezone.utc).isoformat(),
              "execution_code_commit": "0745478ca1646cada114a610206075e6c6efd6a1",
              "solver_budget": {"cap": 19, "actual_solver_invocations_total": 19, "unique_physics_cases_completed": 18, "artifact_recovery_reruns": 1, "remaining_capacity": 0},
              "solver_calls_during_postprocess": 0, "formal_ml_label_eligible": False,
              "source_contract": "realistic_primary_mqw_3position_xz_incoherent_v1"}
dump(OUT / "provenance.json", provenance)
dump(OUT / "manifest.json", {"solver_cap": 19, "actual_solver_invocations_total": 19, "unique_physics_cases_completed": 18, "artifact_recovery_reruns": 1, "forensic_salvaged_cases": 1, "remaining_capacity": 0, "all_complete": all(c.get("status") == "COMPLETE" for c in cases), "postprocess_solver_calls": 0, "fresh_load_readback": state.get("fresh_load_readback", {}), "artifacts": ["case_manifest.parquet", "subrun_metrics.parquet", "spectral_raw.parquet", "spectral_normalized.parquet", "angular_filter_0.parquet", "angular_filter_0p2.parquet", "xz_average.parquet", "three_position_average.parquet", "candidate_ranking_comparison.parquet", "filter_sensitivity.parquet", "pre_fsp_index.json", "post_fsp_index.json", "provenance.json"]})
