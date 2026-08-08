import json
from pathlib import Path

ROOT = Path(r"D:\project\worktrees\blue_apcd_lp_stage11_4")
A = ROOT / "outputs/lp_ml_dataset_v1/analysis"

def payload():
    return json.loads((A / "lp_ml_round3_evidence_reconciliation_v1.json").read_text(encoding="utf-8"))

def test_ancestry_reconciled():
    p = payload()["ancestry"]
    assert p["expected_head_present"] and p["round3_commit_present"]
    assert p["expected_head_is_ancestor_of_head"]
    assert p["round3_commit_is_ancestor_of_head"]
    assert not p["head_is_ancestor_of_round3_commit"]
    assert p["ahead_behind"] == "0\t0"

def test_clean_v2_v3_lineage_and_quarantine():
    p = payload()
    assert p["status"] == "PASS"
    c2, c3 = p["source_artifacts"]["clean_v2"], p["source_artifacts"]["clean_v3"]
    assert (c2["geometries"], c2["rows"], c2["geometry_054_rows"]) == (319, 2871, 0)
    assert (c3["geometries"], c3["rows"], c3["geometry_054_rows"], c3["duplicate_rows"]) == (377, 3393, 0, 0)
    assert c3["clean_v2_geometry_subset"] and c3["round3_added_geometries"] == 58 and c3["round3_added_rows"] == 522

def test_accounting_and_risk_calibration():
    p = payload()
    a = p["source_artifacts"]["r3_accounting"]
    assert (a["planned"], a["entered"], a["unique"], a["duplicate"], a["accepted"], a["complete_geometries"], a["admitted_rows"]) == (128, 127, 126, 1, 121, 58, 522)
    r = p["risk_recalibration"]
    assert r["calibrated_spearman_cv"] > r["dispersion_only_spearman_cv"]
    assert r["calibrated_high_error_recall_cv"] > r["dispersion_only_high_error_recall_cv"]
    assert r["calibrated_high_error_low_risk_cv"] < r["dispersion_only_high_error_low_risk_cv"]
    assert p["constraints"]["solver_calls"] == 0
    assert not p["constraints"]["round4_executed"] and not p["constraints"]["inverse_fdtd"]
