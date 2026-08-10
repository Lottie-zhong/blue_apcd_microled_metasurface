import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "contracts/coupling/traditional_zl1_mdc_level1_real_fdtd_provider_v1.json"
REGISTRY = ROOT / "registries/coupling/traditional_zl1_mdc_level1_solver_registry_v1.json"
PROVIDER = ROOT / "reports/coupling/traditional_zl1_mdc_level1_provider_v1.json"
SUPPORT = ROOT / "reports/coupling/np_level1_ps_ux_grid_requirement_v1.json"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_formal_contract_keeps_six_cases_and_p_s_identity():
    contract = read(CONTRACT)
    assert contract["provider_id"] == "TRADITIONAL_ZL1_MDC_LEVEL1_REAL_FDTD_PROVIDER_V1"
    assert contract["geometry"]["total_thickness_nm"] == 975
    assert contract["geometry"]["extra_spacer_nm"] == 0
    assert len(contract["source_cases"]) == 6
    assert {case["source_orientation"] for case in contract["source_cases"]} == {"x", "z"}
    assert {case["interface_polarization_family"] for case in contract["source_cases"]} == {"P_TM_like", "S_TE_like"}
    assert contract["native_joint_tensor"]["shape"] == [301, 2000]
    assert contract["aggregation"]["unpolarized_plane_wave_average"] is False


def test_executed_provider_has_six_complete_cases_and_no_np_solver():
    registry = read(REGISTRY)
    provider = read(PROVIDER)
    assert registry["status"] == "PASS"
    assert registry["solver_entries"] == 6
    assert registry["replays"] == 0
    assert registry["NP_solver"] == 0
    assert provider["status"] == "PASS"
    assert provider["six_case_membership"] == ["TOP_X", "TOP_Z", "CENTROID_X", "CENTROID_Z", "BOTTOM_X", "BOTTOM_Z"]
    assert provider["safety"]["NP_solver"] == 0
    assert all(provider["quality_gates"].values())
    assert all(item["result"]["solver_status"] == "COMPLETE" for item in provider["raw_case_assets"])
    assert all(item["result"]["grid_shape"] == [301, 2000] for item in provider["raw_case_assets"])
    assert all(item["result"]["raw_joint_finite"] for item in provider["raw_case_assets"])
    assert all(item["result"]["raw_joint_negative_count"] == 0 for item in provider["raw_case_assets"])
    assert all(abs(item["result"]["theta_to_ux_mass_closure"] - 1.0) <= 1e-12 for item in provider["raw_case_assets"])
    assert all(item["result"]["setup_readback"]["checks"]["source_y"] for item in provider["raw_case_assets"])
    assert all(item["result"]["setup_readback"]["checks"]["theta"] for item in provider["raw_case_assets"])


def test_p_s_support_is_channel_resolved_and_closed():
    support = read(SUPPORT)
    assert support["np_solver_entries"] == 0
    assert support["np_equivalence_assumed"] is False
    for branch in ("P", "S"):
        coupling = support[branch]["coupling"]
        assert coupling["ux_mass_closure"] == 1.0
        assert coupling["support"]["symmetric_90_percent"]["u_abs"] > 0
        assert coupling["support"]["symmetric_95_percent"]["u_abs"] >= coupling["support"]["symmetric_90_percent"]["u_abs"]
        assert coupling["support"]["symmetric_99_percent"]["u_abs"] >= coupling["support"]["symmetric_95_percent"]["u_abs"]
