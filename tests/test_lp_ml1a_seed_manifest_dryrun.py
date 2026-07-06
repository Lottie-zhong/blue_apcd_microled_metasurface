from __future__ import annotations
import csv, json, subprocess
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
PY = r"N:\anaconda_envs\RCP_LCP\python.exe"
SCRIPT = ROOT / "scripts/lp_ml1/lp_ml1a_seed_manifest_dryrun.py"
OUT = ROOT / "outputs/lp_ml1a_seed_manifest_dryrun"

def run_script(): subprocess.run([PY, str(SCRIPT)], cwd=ROOT, check=True)
def rows(p):
    with p.open("r", encoding="utf-8-sig", newline="") as f: return list(csv.DictReader(f))

def test_manifest_dryrun_outputs_and_columns():
    run_script(); manifest = rows(OUT / "lp_ml1a_seed_manifest.csv")
    assert len(manifest) == 600
    required = {"candidate_id","target_bin_deg","sampling_group","source_candidate_id","source_stage","source_diagnosis_category","H_nm","L1_nm","W1_nm","theta1_deg","L2_nm","W2_nm","theta2_deg","gap_or_dx_nm","theta1_sin2","theta1_cos2","theta2_sin2","theta2_cos2","intended_lambda_min_nm","intended_lambda_max_nm","intended_lambda_points","intended_wavelengths_nm","run_policy","prepared_not_run","geometry_valid","geometry_reject_reason","duplicate_group_id","priority_score","notes"}
    assert required.issubset(manifest[0].keys())

def test_manifest_is_prepared_not_run_and_full_window():
    run_script(); manifest = rows(OUT / "lp_ml1a_seed_manifest.csv")
    assert all(r["prepared_not_run"] == "true" for r in manifest)
    assert all(r["run_policy"] == "LP-ML1B_periodic_plane_wave_fullwave_later" for r in manifest)
    assert all(r["intended_lambda_min_nm"] == "450" and r["intended_lambda_max_nm"] == "454" and r["intended_lambda_points"] == "9" for r in manifest)
    assert all(r["intended_wavelengths_nm"] == "450,450.5,451,451.5,452,452.5,453,453.5,454" for r in manifest)
    assert all(r["geometry_valid"] == "true" for r in manifest)

def test_rejects_report_rules_and_no_heavy_files():
    run_script(); assert (OUT / "lp_ml1a_rejected_candidates.csv").exists()
    report = (ROOT / "reports/lp_ml1a_seed_manifest_plan.md").read_text(encoding="utf-8")
    for text in ["No FDTD was run", "No Lumerical GUI was opened", "No model was trained", "No K=6 was attempted"]: assert text in report
    rules = (ROOT / "reports/lp_ml1a_geometry_rules.yaml").read_text(encoding="utf-8")
    for text in ["angle_periodicity_rule", "minimum_gap_no_overlap_rule", "minimum gap", "H_allowed_set"]: assert text in rules
    assert not [p for p in OUT.rglob("*") if p.suffix.lower() in {".fsp", ".ldf", ".log"}]

def test_summary_counts_are_600():
    run_script(); summary = json.loads((OUT / "lp_ml1a_seed_manifest_summary.json").read_text(encoding="utf-8"))
    assert summary["candidate_count"] == 600
    assert sum(summary["count_by_sampling_group"].values()) == 600
