from __future__ import annotations
import csv, json, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PY=r"N:\anaconda_envs\RCP_LCP\python.exe"
SCRIPT=ROOT/"scripts/lp_ml1/lp_ml1a3_git_history_geometry_reconstruction.py"
OUT=ROOT/"outputs/lp_ml1a3_git_history_geometry_reconstruction"

def run(): subprocess.run([PY,str(SCRIPT)],cwd=ROOT,check=True)
def rows(p):
    with p.open("r",encoding="utf-8-sig",newline="") as f: return list(csv.DictReader(f))

def test_outputs_and_required_columns():
    run()
    for name in ["lp_ml1a3_history_file_index.csv","lp_ml1a3_candidate_geometry_recovered.csv","lp_ml1a3_run_ready_sources.csv","lp_ml1a3_unresolved_sources.csv","lp_ml1a3_summary.json"]:
        assert (OUT/name).exists()
    recovered=rows(OUT/"lp_ml1a3_candidate_geometry_recovered.csv")
    required={"candidate_id","H_nm","L1_nm","W1_nm","theta1_deg","L2_nm","W2_nm","theta2_deg","gap_or_dx_nm","pitch_nm","period_nm","evidence_label","confidence_level","source_commit","source_file","source_line_or_record","run_ready_geometry","notes"}
    assert recovered and required.issubset(recovered[0].keys())

def test_no_default_range_only_run_ready():
    run()
    recovered=rows(OUT/"lp_ml1a3_candidate_geometry_recovered.csv")
    assert not [r for r in recovered if "default" in r.get("notes","").lower() and r.get("run_ready_geometry")=="true"]

def test_decision_and_boundary_text():
    run()
    decision=(ROOT/"reports/lp_ml1a3_next_action_decision.md").read_text(encoding="utf-8")
    assert "Go" in decision or "No-Go" in decision
    report=(ROOT/"reports/lp_ml1a3_git_history_geometry_reconstruction.md").read_text(encoding="utf-8")
    for text in ["No FDTD was run","No Lumerical GUI was opened","No model was trained","No K=6 was attempted"]: assert text in report

def test_no_heavy_files_created():
    run()
    bad={".fsp",".ldf",".log"}
    assert not [p for p in OUT.rglob("*") if p.suffix.lower() in bad or any(x in p.name.lower() for x in ["monitor","farfield","raw"])]
