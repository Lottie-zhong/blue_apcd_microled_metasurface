import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("lp_h1a_probe", ROOT / "scripts/lp_global_h_h1a_probe_v1.py")
MOD = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MOD)


def test_h500_is_not_scheduled():
    anchors, _ = MOD.load_anchors()
    planned = MOD.planned_cases(anchors)
    assert len(anchors) == 6
    assert len(planned) == 48
    assert {row["H_global_nm"] for row in planned} == {400.0, 450.0, 550.0, 600.0}


def test_unified_height_contract_and_bottom_plane():
    contract = MOD.RUNNER.unified_h_geometry_contract(450.0)
    assert contract["J1_H_nm"] == contract["J2_H_nm"] == 450.0
    assert contract["bottom_plane_nm"] == 0.0
    assert contract["source_z_nm"] == -250.0
    assert contract["monitor_z_nm"] == 1000.0
    assert contract["period_x_nm"] == contract["period_y_nm"] == 432.0


def test_case_identity_binds_height_and_exact_hash():
    anchors, _ = MOD.load_anchors()
    left = MOD.case_identity(anchors[0], 400.0, "x", "head")
    right = MOD.case_identity(anchors[0], 450.0, "x", "head")
    assert left["H_global_nm"] == 400.0
    assert left["exact_geometry_hash_sha256"] == anchors[0]["exact_geometry_hash_sha256"]
    assert MOD.sha256_obj(left) != MOD.sha256_obj(right)


def test_circular_delta_and_central_residual():
    assert MOD.circ_diff(5.0, 355.0) == 10.0
    assert MOD.circ_diff(355.0, 5.0) == -10.0
    central = MOD.circular_central([359.0, 1.0])
    assert min(abs(MOD.circ_diff(central, 0.0)), abs(MOD.circ_diff(central, 360.0))) < 1e-9
    residuals = MOD.circular_residuals([359.0, 1.0], central)
    assert max(abs(value) for value in residuals) <= 1.0


def test_local_sensitivity_uses_circular_finite_difference():
    values = {400.0: 359.0, 450.0: 1.0, 500.0: 3.0, 550.0: 5.0, 600.0: 7.0}
    assert MOD.local_sensitivity(values, 400.0) == 0.04
    assert MOD.local_sensitivity(values, 500.0) == 0.04


def test_fixed_h_grouping_and_x_only_exclusion():
    anchors, _ = MOD.load_anchors()
    phi = []
    full = []
    for anchor in anchors[:2]:
        for height in MOD.ALL_HEIGHTS_NM:
            phi.append({"authoritative_id": anchor["authoritative_id"], "geometry_hash_sha256": anchor["exact_geometry_hash_sha256"], "H_global_nm": height, "delta_phi_vs_H500_deg": 0.0})
            full.append({"authoritative_id": anchor["authoritative_id"], "geometry_hash_sha256": anchor["exact_geometry_hash_sha256"], "H_global_nm": height, "Jones_complete": True, "phase_wrapped_deg": 10.0 + height / 100.0, "projection_error_apcd_v1": 0.01, "Txx": 0.9})
    _, spans = MOD.interaction_tables(phi, full, 2)
    assert [row["H_global_nm"] for row in spans] == list(MOD.ALL_HEIGHTS_NM)
    assert all(row["full_jones_count"] == 2 for row in spans)
    x = {"rows": [{"weighted_Ex_real": 1.0, "weighted_Ex_imag": 0.0}], "case_id": "x"}
    phase = MOD.phase_only_row(anchors[0], 400.0, x, "test")
    assert phase["Jones_complete"] is False
    assert phase["projector_eligible"] is False


def test_exact_hash_and_entered_case_protection(tmp_path):
    anchors, _ = MOD.load_anchors()
    anchor = anchors[0]
    identity = MOD.case_identity(anchor, 400.0, "x", "head")
    MOD.RUNTIME = tmp_path
    result = MOD.run_case(None, anchor, 400.0, "x", "head", MOD.physical_contract("head"), [{"solver_entered": True, "case_identity_sha256": MOD.sha256_obj(identity)}])
    assert result["status"] == "QUARANTINED_ENTERED_NO_RECOVERY"
    assert result["solver_entered"] is True
