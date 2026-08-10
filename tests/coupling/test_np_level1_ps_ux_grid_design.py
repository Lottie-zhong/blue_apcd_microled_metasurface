import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "contracts/coupling/np_level1_ps_ux_grid_design_v1.json"
REUSE = ROOT / "registries/coupling/np_level1_cross_branch_reuse_registry_v1.json"
THRESHOLDS = ROOT / "registries/coupling/np_level1_order_threshold_registry_v1.json"
NODES = ROOT / "reports/coupling/np_level1_ps_ux_grid_nodes_v1.csv"


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_zero_solver_and_authoritative_provider_contract():
    contract = read_json(CONTRACT)
    assert contract["status"] == "PASS"
    assert all(value == 0 for value in contract["solver_authorization"].values())
    assert contract["authoritative_mdc_provider"]["status"] == "PASS"
    assert contract["authoritative_mdc_provider"]["formal_band_nm"] == [445, 455]
    assert contract["np_surrogate_status"] == "NP_ANGULAR_SURROGATE_CAPABILITY_NOT_ESTABLISHED"
    assert contract["m2_non_substitution"].startswith("M2 angular reuse count = 0")


def test_p0_s0_reuse_is_formal_and_no_m2_substitution():
    reuse = read_json(REUSE)
    assert reuse["status"] == "PASS"
    assert reuse["m2_angular_reuse_count"] == 0
    assert reuse["np_source_writes"] == 0
    for branch in ("P", "S"):
        case = reuse["cases"][branch]
        assert case["reuse_decision"] == "REUSABLE_LEVEL1_NP_ANCHOR"
        assert all(case["gates"].values())
        assert case["ux"] == 0.0
        assert case["wavelengths_nm"] == list(range(445, 456))
        assert case["post_fsp_sha256"]
        assert case["result_artifact_sha256"]
        assert case["interface_stack_id"] == "NP_K6_INDEPENDENT_STACK_PILOT_V1"


def test_p_s_mass_support_and_side_audit_are_independent_and_closed():
    contract = read_json(CONTRACT)
    for branch in ("P", "S"):
        analysis = contract["mass_analysis"][branch]
        assert analysis["wavelength_scope_nm"] == list(range(445, 456))
        assert abs(analysis["ux_mass_closure"] - 1.0) <= 1e-12
        assert abs(analysis["mass_by_side"]["closure"] - 1.0) <= 1e-12
        for fraction in ("80", "90", "95", "99"):
            assert 0 < analysis["symmetric_support"][fraction]["u_abs"] < 1
            assert analysis["symmetric_support"][fraction]["captured_mass"] >= int(fraction) / 100


def test_threshold_registry_and_nodes_are_deterministic_and_non_grazing():
    contract = read_json(CONTRACT)
    thresholds = read_json(THRESHOLDS)
    rows = thresholds["threshold_rows"]
    assert thresholds["registry_id"] == "NP_LEVEL1_ORDER_THRESHOLD_REGISTRY_V1"
    assert len(rows) == 88
    for row in rows:
        assert 445 <= row["lambda_nm"] <= 455
        assert -1 <= row["ux_transition"] <= 1
        assert abs(row["ux_transition"] + row["m"] * row["lambda_nm"] / 1740.0 - row["u_out_at_transition"]) <= 1e-12
        assert row["opening_closing"] in {"opening", "closing"}
    for branch in ("P", "S"):
        design = contract["node_design"][branch]
        assert design["uniform_grid_shortcut"] is False
        for level in ("minimum", "recommended"):
            nodes = design[level]["final_proposed_nodes"]
            assert all(abs(float(node["ux"])) < 1 for node in nodes)
            assert any(abs(float(node["ux"])) <= 1e-15 for node in nodes)
            assert design[level]["new_solver_count"] == sum(abs(float(node["ux"])) > 1e-15 for node in nodes)
    assert contract["solver_budget"]["recommended"]["TOTAL_NEW_NP_3D_BROADBAND_CASES"] >= contract["solver_budget"]["minimum"]["TOTAL_NEW_NP_3D_BROADBAND_CASES"]


def test_machine_readable_node_table_retains_p_s_and_reuse_fields():
    with NODES.open("r", encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert {row["polarization"] for row in rows} == {"P", "S"}
    assert {row["grid_level"] for row in rows} == {"minimum", "recommended"}
    for branch in ("P", "S"):
        central = [row for row in rows if row["polarization"] == branch and row["ux"] == "0.0"]
        assert central
        assert all(row["reusable"] == "True" and row["needs_new_solver"] == "False" for row in central)
        assert all(abs(float(row["ux"])) < 1 for row in rows if row["polarization"] == branch)
