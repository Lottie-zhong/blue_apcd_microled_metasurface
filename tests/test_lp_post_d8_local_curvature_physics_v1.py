import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AN = ROOT / "outputs/lp_ml_dataset_v1/analysis"
PL = ROOT / "outputs/lp_ml_dataset_v1/plans"
ST = ROOT / "outputs/lp_ml_dataset_v1/staging/b120_j2lm06_post_d8_local_curvature_diagnostic_v1"
PKG = ROOT / "outputs/lp_ml_dataset_v1/execution_packages/b120_j2lm06_post_d8_local_curvature_diagnostic_execution_package_v1"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_solver_accounting_exact_matrix():
    d = load(AN / "b120_j2lm06_post_d8_curvature_solver_accounting_v1.json")
    assert d["planned_subruns"] == d["raw_solver_invocations"] == d["successful_completions"] == d["accepted_subruns"] == 8
    assert d["failed_invocations"] == d["duplicate_invocations"] == d["missing_subruns"] == d["unauthorized_runs"] == 0
    assert d["complete_jones"] == d["central_pairs"] == 4
    assert d["wavelength_nm"] == [450]


def test_subrun_records_and_checkpoint_lineage():
    rows = list(csv.DictReader((ST / "subrun_records.csv").open(encoding="utf-8")))
    assert len(rows) == 8
    assert {(r["candidate_id"], r["polarization"]) for r in rows} == {(c, p) for c in ["POSTD8_CURV_MIRROR_WP_DP_PP", "POSTD8_CURV_MIRROR_WP_DM_PM", "POSTD8_CURV_MIRROR_WM_DP_PM", "POSTD8_CURV_MIRROR_WM_DM_PP"] for p in ["x", "y"]}
    assert all(r["acceptance_status"] == "PASS" and r["reload_status"] == "PASS" for r in rows)
    assert all(r["wavelength_nm"] == "450.0" for r in rows)
    assert all(Path(r["checkpoint_path"]).exists() for r in rows)


def test_complete_candidate_metrics_and_label_separation():
    rows = load(ST / "candidate_metrics.json")
    assert len(rows) == 4
    for r in rows:
        assert r["status"] == "COMPLETE_ACCEPTED"
        assert r["physics_label"] == "FORMAL_ACCEPTED_WEIGHTED_G0"
        assert r["prediction_label"] == "MODEL_PREDICTION_NOT_PHYSICS_LABEL"
        for key in ["txx", "txy", "tyx", "tyy", "Txx", "Tyy", "sigma2_over_sigma1", "matrix_projection_error", "input_stokes", "output_stokes", "a0", "az", "ax", "ay"]:
            assert key in r


def test_odd_even_gradient_and_curvature():
    g = load(AN / "b120_j2lm06_post_d8_curvature_central_gradient_v1.json")
    d = load(AN / "b120_j2lm06_post_d8_curvature_directional_second_difference_v1.json")
    v = load(AN / "b120_j2lm06_post_d8_curvature_model_validation_v1.json")
    assert g["rank"] == 3
    assert len(g["singular_values"]) == 3
    assert len(g["normalized_gradient_phase_deg_per_unit"]) == 3
    assert len(g["leave_one_pair_out"]) == 4
    assert len(d["directions"]) == 4
    assert not d["hessian_claim"]
    assert not v["hessian_claim"]


def test_outcome_and_package():
    o = load(AN / "b120_j2lm06_post_d8_curvature_outcome_v1.json")
    assert o["outcome"] in {"CENTRAL_DIFFERENCE_GRADIENT_RECOVERED", "CURVATURE_DOMINANT_TRUST_REGION_SHRINK_REQUIRED", "SCALE_DRIFT_DOMINANT_WITH_BOUNDED_CURVATURE", "MIXED_NONLINEARITY_REMAINS_UNRESOLVED", "ACTIVE_BASIS_ROTATION_CONFIRMED", "HARD_GATE_DATA_CONFLICT"}
    assert o["solver_calls"] == 8 and o["new_complete_jones"] == 4
    p = load(PKG / "package_manifest.json")
    assert p["status"] == "EXECUTED_PASS"
    assert p["execution_status"]["raw_solver_invocations"] == 8
    assert p["no_heavy_artifacts_retained"]


def test_no_heavy_artifacts_or_forbidden_stage():
    for suffix in [".fsp", ".fspx", ".ldf", ".h5", ".mat", ".npy", ".npz"]:
        assert not list(ST.rglob("*" + suffix))
    assert not (ROOT / "outputs/lp_ml_dataset_v1/staging/b120_j2lm06_post_d8_local_curvature_diagnostic_v1/D9").exists()


def test_physics_checksum_manifest():
    m = load(AN / "b120_j2lm06_post_d8_curvature_physics_checksum_manifest_v1.json")
    assert m["solver_calls"] == 8
    for item in m["files"]:
        p = ROOT / item["path"]
        assert p.exists()
        assert hashlib.sha256(p.read_bytes()).hexdigest() == item["sha256"]
