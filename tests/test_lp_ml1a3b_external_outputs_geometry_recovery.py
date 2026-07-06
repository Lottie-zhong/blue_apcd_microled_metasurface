from __future__ import annotations
import csv, subprocess
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
PY = r"N:\anaconda_envs\RCP_LCP\python.exe"
SCRIPT = ROOT / "scripts" / "lp_ml1" / "lp_ml1a3b_external_outputs_geometry_recovery.py"
OUT = ROOT / "outputs" / "lp_ml1a3b_external_outputs_geometry_recovery"

def run_script(): subprocess.run([PY, str(SCRIPT)], cwd=ROOT, check=True)
def rows(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f: return list(csv.DictReader(f))

def test_outputs_exist_and_columns():
    run_script()
    for name in ["lp_ml1a3b_external_file_index.csv", "lp_ml1a3b_candidate_geometry_recovered.csv", "lp_ml1a3b_run_ready_sources.csv", "lp_ml1a3b_unresolved_sources.csv", "lp_ml1a3b_summary.json"]:
        assert (OUT / name).exists()
    rec = rows(OUT / "lp_ml1a3b_candidate_geometry_recovered.csv")
    required = {"candidate_id", "H_nm", "L1_nm", "W1_nm", "theta1_deg", "L2_nm", "W2_nm", "theta2_deg", "gap_or_dx_nm", "evidence_label", "confidence_level", "external_source_path", "run_ready_geometry"}
    assert rec and required.issubset(rec[0].keys())

def test_no_low_confidence_run_ready():
    run_script()
    rec = rows(OUT / "lp_ml1a3b_candidate_geometry_recovered.csv")
    assert not [r for r in rec if r["run_ready_geometry"] == "true" and r["evidence_label"] in {"unresolved", "partial_external_match_needs_manual_review"}]

def test_reports_boundaries_and_decision():
    run_script()
    decision = (ROOT / "reports" / "lp_ml1a3b_next_action_decision.md").read_text(encoding="utf-8")
    assert "Go" in decision or "No-Go" in decision
    report = (ROOT / "reports" / "lp_ml1a3b_external_outputs_geometry_recovery.md").read_text(encoding="utf-8")
    for text in ["No FDTD was run", "No Lumerical GUI was opened", "No model was trained", "No K=6 was attempted"]:
        assert text in report

def test_no_heavy_files_copied_or_created():
    run_script()
    bad = {".fsp", ".ldf", ".h5", ".mat", ".npz", ".npy"}
    assert not [p for p in OUT.rglob("*") if p.suffix.lower() in bad or any(x in p.name.lower() for x in ["monitor", "farfield", "raw"])]
    index = rows(OUT / "lp_ml1a3b_external_file_index.csv")
    parsed = [r for r in index if r["scan_status"] == "indexed_text"]
    assert not [r for r in parsed if Path(r["external_path"]).suffix.lower() in bad]
