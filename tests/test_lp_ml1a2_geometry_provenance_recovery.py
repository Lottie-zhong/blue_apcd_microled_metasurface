from __future__ import annotations
import csv, json, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PY=r"N:\anaconda_envs\RCP_LCP\python.exe"
SCRIPT=ROOT/"scripts/lp_ml1/lp_ml1a2_geometry_provenance_recovery.py"
OUT=ROOT/"outputs/lp_ml1a2_geometry_provenance_recovery"

def run(): subprocess.run([PY,str(SCRIPT)],cwd=ROOT,check=True)
def rows(p):
    with p.open("r",encoding="utf-8-sig",newline="") as f: return list(csv.DictReader(f))

def test_outputs_and_required_columns():
    run()
    for name in ["lp_ml1a2_geometry_lookup.csv","lp_ml1a2_geometry_recovery_summary.json","lp_ml1a2_run_ready_sources.csv","lp_ml1a2_unresolved_sources.csv","lp_ml1a2_manifest_with_recovered_geometry.csv"]:
        assert (OUT/name).exists()
    lookup=rows(OUT/"lp_ml1a2_geometry_lookup.csv")
    required={"candidate_id","H_nm","L1_nm","W1_nm","theta1_deg","L2_nm","W2_nm","theta2_deg","gap_or_dx_nm","pitch_or_period_nm","source_file","source_line_or_record","evidence_type","confidence_level","recovery_notes"}
    assert lookup and required.issubset(lookup[0].keys())

def test_default_manifest_geometry_not_run_ready_and_unresolved_written():
    run()
    joined=rows(OUT/"lp_ml1a2_manifest_with_recovered_geometry.csv")
    assert joined
    assert not [r for r in joined if r.get("recovered_confidence_level")=="unresolved" and r.get("run_ready_geometry")=="true"]
    unresolved=rows(OUT/"lp_ml1a2_unresolved_sources.csv")
    assert unresolved

def test_reports_boundaries_and_decision():
    run()
    report=(ROOT/"reports/lp_ml1a2_geometry_provenance_recovery.md").read_text(encoding="utf-8")
    for text in ["No FDTD was run","No Lumerical GUI was opened","No model was trained","No K=6 was attempted"]: assert text in report
    decision=(ROOT/"reports/lp_ml1a2_run_ready_decision.md").read_text(encoding="utf-8")
    assert "Go" in decision or "No-Go" in decision

def test_no_heavy_files_created():
    run()
    bad={".fsp",".ldf",".log"}
    assert not [p for p in OUT.rglob("*") if p.suffix.lower() in bad or any(x in p.name.lower() for x in ["monitor","farfield","raw"])]
