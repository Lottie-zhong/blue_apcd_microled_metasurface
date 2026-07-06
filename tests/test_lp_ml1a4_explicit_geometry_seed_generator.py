from __future__ import annotations

import csv
import json
import math
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = r"N:\anaconda_envs\RCP_LCP\python.exe"
SCRIPT = ROOT / "scripts" / "lp_ml1" / "lp_ml1a4_explicit_geometry_seed_generator.py"
OUT = ROOT / "outputs" / "lp_ml1a4_explicit_geometry_seed_generator"


def run_script() -> None:
    subprocess.run([PY, str(SCRIPT)], cwd=ROOT, check=True)


def rows(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def test_manifest_and_pilot_outputs():
    run_script()
    manifest = rows(OUT / "lp_ml1a4_explicit_seed_manifest.csv")
    pilot = rows(OUT / "lp_ml1a4_pilot_recommendation.csv")
    assert len(manifest) == 600
    assert len(pilot) == 36
    required = {"candidate_id", "target_bin_deg", "sampling_group", "sampling_family", "geometry_source", "historical_geometry_recovered", "source_candidate_id", "source_provenance", "H_nm", "period_x_nm", "period_y_nm", "L1_nm", "W1_nm", "theta1_deg", "L2_nm", "W2_nm", "theta2_deg", "center_dx_nm", "center_dy_nm", "gap_or_dx_nm", "theta1_sin2", "theta1_cos2", "theta2_sin2", "theta2_cos2", "intended_lambda_min_nm", "intended_lambda_max_nm", "intended_lambda_points", "intended_wavelengths_nm", "run_policy", "prepared_not_run", "geometry_valid", "priority_score", "pilot_rank"}
    assert required.issubset(manifest[0].keys())


def test_manifest_flags_and_numeric_geometry():
    run_script()
    manifest = rows(OUT / "lp_ml1a4_explicit_seed_manifest.csv")
    numeric = ["H_nm", "period_x_nm", "period_y_nm", "L1_nm", "W1_nm", "theta1_deg", "L2_nm", "W2_nm", "theta2_deg", "center_dx_nm", "gap_or_dx_nm"]
    seen = set()
    for r in manifest:
        assert r["prepared_not_run"] == "true"
        assert r["run_policy"] == "LP-ML1B_periodic_plane_wave_fullwave_pilot_later"
        assert r["historical_geometry_recovered"] == "false"
        assert r["geometry_source"] == "LP-ML1A4_explicit_generator"
        assert r["geometry_valid"] == "true"
        assert r["intended_lambda_min_nm"] == "450" and r["intended_lambda_max_nm"] == "454" and r["intended_lambda_points"] == "9"
        assert r["intended_wavelengths_nm"] == "450,450.5,451,451.5,452,452.5,453,453.5,454"
        vals = tuple(float(r[k]) for k in numeric)
        assert all(math.isfinite(v) and v != 0 for v in vals if numeric[vals.index(v)] != "theta1_deg" and numeric[vals.index(v)] != "theta2_deg")
        full = tuple(r[k] for k in ["H_nm", "L1_nm", "W1_nm", "theta1_deg", "L2_nm", "W2_nm", "theta2_deg", "center_dx_nm"])
        assert full not in seen
        seen.add(full)


def test_reports_rules_and_no_heavy_files():
    run_script()
    report = (ROOT / "reports" / "lp_ml1a4_explicit_geometry_seed_plan.md").read_text(encoding="utf-8")
    for text in ["No FDTD was run", "No Lumerical GUI was opened", "No model was trained", "No K=6 was attempted"]:
        assert text in report
    rules = (ROOT / "reports" / "lp_ml1a4_explicit_geometry_rules.yaml").read_text(encoding="utf-8")
    for text in ["period_rule", "angle_periodicity_rule", "no_overlap_rule", "boundary_margin_rule", "height_allowed_set"]:
        assert text in rules
    assert (OUT / "lp_ml1a4_rejected_geometry.csv").exists()
    assert not [p for p in OUT.rglob("*") if p.suffix.lower() in {".fsp", ".ldf", ".log"} or any(x in p.name.lower() for x in ["monitor", "farfield", "raw"])]


def test_summary_counts():
    run_script()
    summary = json.loads((OUT / "lp_ml1a4_explicit_seed_summary.json").read_text(encoding="utf-8"))
    assert summary["candidate_count"] == 600
    assert summary["pilot_count"] == 36
    assert sum(summary["count_by_sampling_group"].values()) == 600
