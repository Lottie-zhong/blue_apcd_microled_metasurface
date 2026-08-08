import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NP_ROOT = Path(r"D:\project\worktrees\blue_apcd_np_k6_mdc_v1")
FREEZE = "7a8588f6b5a1c96d88813f60406d418b488135fd"
PACKAGE_SHA = "0b7b45e838a0d73b92d63f8a45459bc46206677a91821fa474dacf4bd9028eaa"
FORMAL_SHA = "f034240634365f2c81a78feb0c8df4bc2ecc17db074734236d48c13deaffc7de"
HANDOFF_SHA = "4fcf8b5cbefb37ba8153ffadbf7bb4a141d6cbbb4fb296fe9fd2211e44226934"
STATUS = "APCD_MDC_NP_COUPLING_V1_EXPLORATORY_DIRECT_STAGE_A_READY_AWAITING_SOLVER_AUTHORIZATION"

def load(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))

def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def test_np_authoritative_freeze_and_artifact_hashes():
    lock = load("contracts/coupling/source_branch_lock_v1.json")
    np_lock = load("contracts/coupling/np_model_scope_lock_v1.json")
    formal = NP_ROOT / "outputs/np_k6_formal_source_scope_v1/formal_source_scope_v1.json"
    handoff = NP_ROOT / "outputs/np_k6_formal_source_scope_v1/coupling_handoff_manifest_v1.json"
    assert lock["sources"]["np"]["commit"] == FREEZE
    assert np_lock["source_commit"] == FREEZE
    assert np_lock["package_sha256"] == PACKAGE_SHA
    assert sha256(formal) == FORMAL_SHA == np_lock["formal_scope_artifact_sha256"]
    assert sha256(handoff) == HANDOFF_SHA == np_lock["handoff_manifest_sha256"]
    assert np_lock["scope_frozen"] is True

def test_joint_scope_forbids_offline_ranking_and_selects_direct_stage_a():
    lock = load("contracts/coupling/source_branch_lock_v1.json")
    resolution = load("outputs/mdc_np_coupling_v1/source_scope_resolution_v1.json")
    assert lock["status"].endswith("GOLDEN_FIXTURE_COMPLETE")
    assert lock["joint_scope"]["normalized_scope_enum"] == "EXPLORATORY_ONLY"
    assert lock["joint_scope"]["offline_screening_authorized"] is False
    assert lock["joint_scope"]["direct_stage_a_ready"] is True
    assert lock["joint_scope"]["next_route"] == "DIRECT_STAGE_A_FULLWAVE_VALIDATION"
    assert resolution["verification"]["offline_ranking_capability"] is False

def test_first_shot_is_fixed_baseline_450nm_xpol_normal_t_extra_zero():
    contract = load("contracts/coupling/stage_a_direct_fullwave_contract_v1.json")
    shot = contract["first_shot"]
    assert contract["joint_scope"] == "EXPLORATORY_ONLY"
    assert contract["solver_authorized"] is True
    assert contract["offline_screening_authorized"] is False
    assert shot == {
        "wavelength_nm": 450, "polarization": "x", "incidence": "normal",
        "u_x": 0.0, "ky_over_k0": 0.0, "t_extra_nm": 0,
        "source_scope": "NP formal standalone x-pol exact-point scope; joint result remains exploratory",
    }
    assert contract["coordinate_contract"]["diffraction_order_m_plus_1"] == "physical +x"
    assert contract["coordinate_contract"]["reference_plane"] == "NP pillar bottom"
    assert contract["comparison_priority"] == ["B3", "B1"]

def test_stage_a_scope_boundaries_are_explicit():
    contract = load("contracts/coupling/stage_a_direct_fullwave_contract_v1.json")
    exclusions = set(contract["known_exclusions"])
    assert "y-polarization" in exclusions
    assert "x/y averaging" in exclusions
    assert "oblique incidence and ?5/?10 degree samples" in exclusions
    assert "finite-SiO2 transfer" in exclusions
    assert "final MDC-NP stack transfer" in exclusions
    assert "quantitative joint-power prediction" in exclusions
    assert "surrogate/offline ranking" in exclusions
    assert "wavelength interpolation or extrapolation" in exclusions
    assert contract["t_extra_policy"]["baseline_nm"] == 0
    assert contract["t_extra_policy"]["future_candidates_nm"] == [0, 79, 158, 237]
    assert contract["safety"]["solver_runs_this_freeze"] == 0
    assert contract["safety"]["training_runs_this_freeze"] == 0
