import hashlib
import json
from pathlib import Path

ROOT = Path(r"D:\project\worktrees\blue_apcd_lp_stage11_4")
O = ROOT / "outputs/lp_ml_dataset_v1"
P = O / "plans/lp_ml_six_bin_inverse_design_planning_v1"
QID = "LPML_R1_GLOBAL_SOBOL_054"


def load(name):
    return json.loads((P / name).read_text(encoding="utf-8"))


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def test_clean_hashes_and_quarantine_boundary():
    checks = load("lp_ml_six_bin_inverse_planning_manifest_v1.json")
    assert checks["clean_source_hashes"] == {
        "merged": "ca2fd154eed8e9b2f41b92c2f2aaa95f77d451c7047e4056f84a430c56e67336",
        "split": "2a4223f802204e870cc7d28d956f5c705f9442ccdbad2ad9bd10fecab07ce661",
        "normalization": "13c7855b48d8c34e674ea67cb343df9414306cf43a943efdec6bba001f864167",
    }
    assert checks["geometry_054_admitted_rows"] == 0
    merged = O / "clean_v2/lp_ml_dataset_v1_merged_clean_v2_319_geometry_2871_rows.csv"
    assert QID not in {line.split(",", 1)[0] for line in merged.read_text(encoding="utf-8-sig").splitlines()[1:]}


def test_model_roles_and_no_sole_model_authority():
    c = load("lp_ml_six_bin_model_consensus_contract_v1.json")
    assert c["roles"]["C0"] == "CURRENT_CHAMPION_GLOBAL_DOMAIN_GUARD"
    assert "ALPHA_0P95" in c["roles"]["selected_blend"]
    assert "ENSEMBLE" in c["roles"]["C1_to_C4"]
    assert c["test_guided_selection"] is False
    assert "high-risk candidates cannot be sole" in c["high_risk_policy"]


def test_target_and_objective_contracts_are_full_jones_and_invariant():
    target = load("lp_ml_six_bin_inverse_physical_target_contract_v1.json")
    obj = load("lp_ml_six_bin_inverse_objective_contract_v1.json")
    conv = load("lp_ml_six_bin_target_convention_v1.json")
    assert target["target_type"] == "COMPLETE_COMPLEX_JONES"
    assert "PHASE_ONLY" in target["explicitly_not"]
    assert "TXX_ONLY" in target["explicitly_not"]
    assert "txy=tyx" not in target["jones_convention"]
    assert "min_c" in target["projector"]["shape_error"]
    assert "circular_distance" in obj["terms"]["phase_target_error"]
    assert "min_c" in obj["terms"]["projector_shape_error"]
    assert "projector_BCE" in obj["forbidden"]
    assert obj["recommended_initial_weights"]["phase"] == 1.0
    assert conv["phase_step_deg"] == 60.0
    assert conv["offset_invariance"]
    assert conv["closure"]["six_bin_closure"].startswith("circular_distance")


def test_tuple_pareto_and_hierarchy_contracts():
    tup = load("lp_ml_six_bin_tuple_objective_contract_v1.json")
    pareto = load("lp_ml_six_bin_pareto_selection_contract_v1.json")
    hierarchy = load("lp_ml_six_bin_k6_validation_hierarchy_v1.json")
    assert tup["scope"] == "PLANNING_AND_RANKING_ONLY"
    assert len(tup["components"]) >= 10
    assert pareto["candidate_list"] == "ABSENT_BY_CONTRACT"
    assert "LEVEL_6_FULL_K6_SUPERCELL_FULL_WAVE" in hierarchy["levels"]
    assert hierarchy["promotion_now"] is False


def test_no_candidate_generation_or_solver_package():
    manifest = load("lp_ml_six_bin_inverse_planning_manifest_v1.json")
    readiness = load("lp_ml_six_bin_inverse_readiness_gate_v1.json")
    budget = load("lp_ml_six_bin_prospective_fdtd_budget_v1.json")
    assert manifest["solver_calls"] == 0
    assert manifest["candidate_generation_executed"] is False
    assert manifest["candidate_list_present"] is False
    assert manifest["runnable_solver_package_present"] is False
    assert readiness["no_candidate_generation"] is True
    assert readiness["no_solver_authorization"] is True
    assert budget["authorization"] == "NOT_AUTHORIZED_BY_THIS_TASK"
    assert not any(p.suffix.lower() in {".fsp", ".fspx", ".ldf", ".h5", ".mat", ".npy", ".npz"} for p in P.rglob("*"))
    assert all(p.suffix.lower() == ".json" for p in P.iterdir())


def test_protected_reports_unchanged():
    manifest = load("lp_ml_six_bin_inverse_planning_manifest_v1.json")
    for rel, expected in manifest["protected_reports_sha256"].items():
        assert sha(ROOT / rel) == expected
