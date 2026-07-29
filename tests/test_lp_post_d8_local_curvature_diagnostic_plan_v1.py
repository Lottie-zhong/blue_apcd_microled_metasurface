import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AN = ROOT / "outputs/lp_ml_dataset_v1/analysis"
PL = ROOT / "outputs/lp_ml_dataset_v1/plans"


def load(name):
    return json.loads((PL / name).read_text(encoding="utf-8"))


def test_selected_design_and_counts():
    d = load("b120_j2lm06_post_d8_local_curvature_diagnostic_plan_v1.json")
    assert d["diagnostic_design"] == "A_ANTIPODAL_TETRAHEDRAL_COMPLEMENT"
    assert d["anchor_id"] == "D8_TRV_PLAN_d6f4911593b64495"
    assert d["existing_probe_count"] == 4
    assert d["new_probe_count"] == 4
    assert len(d["probes"]) == 4


def test_active_and_fixed_variables():
    d = load("b120_j2lm06_post_d8_local_curvature_diagnostic_plan_v1.json")
    assert d["active_variables"] == ["J2_width_nm", "D_nm", "Psi_deg"]
    assert "J1_side_nm" in d["fixed_variables"]
    assert "J2_length_nm" in d["fixed_variables"]


def test_central_pairs_and_quantization():
    s = json.loads((AN / "b120_j2lm06_post_d8_curvature_central_symmetry_audit_v1.json").read_text())
    assert s["central_pair_count"] == 4
    assert s["max_normalized_residual_norm"] < 0.02
    assert s["raw_matrix"]["rank"] == 3
    assert s["centered_matrix"]["rank"] == 3
    assert s["internal_exact_unique"]
    assert s["internal_canonical_relative_unique"]
    assert s["internal_symmetry_unique"]
    assert not s["duplicate_against_canonical"]


def test_geometry_gate_and_four_rows():
    rows = list(csv.DictReader((AN / "b120_j2lm06_post_d8_curvature_mirror_geometry_gate_v1.csv").open(encoding="utf-8")))
    assert len(rows) == 4
    assert all(r["center_grid_pass"] == "True" for r in rows)
    assert all(r["manufacturing_pass"] == "True" for r in rows)
    assert all(r["duplicate_against_canonical"] == "False" for r in rows)


def test_future_matrix_and_labels():
    d = load("b120_j2lm06_post_d8_local_curvature_diagnostic_plan_v1.json")
    assert d["future_budget"] == {"authorization": "PLANNING_ONLY_NOT_AUTHORIZED", "geometries": 4, "wavelength_nm": [450], "x_y_subruns": 8}
    assert all(p["status"] == "PLANNED_NOT_RUN" for p in d["probes"])
    assert all(p["physics_fields"] == "ABSENT_NOT_SIMULATED" for p in d["probes"])
    assert all(p["prediction_label"] == "MODEL_PREDICTION_NOT_PHYSICS_LABEL" for p in d["probes"])


def test_no_execution_package_or_physics_staging():
    d = load("b120_j2lm06_post_d8_local_curvature_diagnostic_plan_v1.json")
    assert d["no_execution_package"] and d["no_physics_staging"]
    assert not (ROOT / "outputs/lp_ml_dataset_v1/execution_packages/b120_j2lm06_post_d8_local_curvature").exists()
    assert not (ROOT / "outputs/lp_ml_dataset_v1/staging/b120_j2lm06_post_d8_local_curvature").exists()


def test_contracts_are_planning_only_and_no_d9():
    e = load("b120_j2lm06_post_d8_local_curvature_execution_contract_v1.json")
    m = load("b120_j2lm06_post_d8_local_curvature_ml_label_contract_v1.json")
    v = load("b120_j2lm06_post_d8_local_curvature_validation_metric_contract_v1.json")
    assert e["status"] == m["status"] == v["status"] == "PLANNING_ONLY_NOT_AUTHORIZED"
    assert e["solver_calls"] == 0 and e["no_d9_authorization"]
    assert "D9" not in json.dumps(e)
    assert v["no_full_hessian"]


def test_comparison_and_checksum_manifest():
    c = json.loads((AN / "b120_j2lm06_post_d8_curvature_diagnostic_design_comparison_v1.json").read_text())
    assert c["selected_design"] == "ANTIPODAL_TETRAHEDRAL_COMPLEMENT"
    assert c["designs"]["A_ANTIPODAL_TETRAHEDRAL_COMPLEMENT"]["centered_matrix"]["rank"] == 3
    assert not c["hessian_claim"]
    manifest = json.loads((AN / "b120_j2lm06_post_d8_local_curvature_checksum_manifest_v1.json").read_text())
    for item in manifest["files"]:
        p = ROOT / item["path"]
        assert p.exists()
        assert hashlib.sha256(p.read_bytes()).hexdigest() == item["sha256"]
