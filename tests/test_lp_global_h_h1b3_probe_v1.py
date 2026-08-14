import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "lp_global_h_h1b3_probe_v1.py"
SPEC = importlib.util.spec_from_file_location("h1b3_under_test", SCRIPT)
H = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(H)


def test_exactly_four_h550_xy_and_no_h500_materialization():
    candidates = H.materialize_candidates()
    assert len(candidates) == 4
    assert H.MAX_SUBRUNS == 8
    assert H.POLARIZATIONS == ("x", "y")
    assert all(c["H_global_nm"] == c["J1_H_nm"] == c["J2_H_nm"] == 550.0 for c in candidates)
    assert all(c["J1_center_y_nm"] == 3.5 and c["J2_center_y_nm"] == -3.5 for c in candidates)


def test_parent_c_lineage_and_exact_d_success():
    d = H.d5(H.c_geometry(), H.parent_geometry())
    assert d == {"J1_side_nm": 0.0, "J2_length_nm": 0.0, "J2_width_nm": 0.0, "D_nm": -3.997287779188, "Psi_deg": -0.044384603831}


def test_candidate_legality_and_duplicate_hash_prevention():
    candidates, audit, _ = H.build_selection_audit()
    assert len(candidates) == 4
    assert len({c["exact_geometry_hash_sha256"] for c in candidates}) == 4
    assert all(c["legality"]["pass"] for c in candidates)
    assert all(row["status"] == "FROZEN_FOR_EXECUTION" for row in audit["rows"])
    assert all(row["legality"]["checks"]["no_previous_exact_physics_evidence"] for row in audit["rows"])


def test_requested_vs_actual_legal_displacements_are_recorded():
    candidates, audit, _ = H.build_selection_audit()
    by_id = {row["candidate_id"]: row for row in audit["rows"]}
    assert by_id["H1B3_F1_CONSERVATIVE_FORWARD"]["requested_displacement_5d_from_C"]["D_nm"] < 0
    assert by_id["H1B3_F1_CONSERVATIVE_FORWARD"]["actual_legal_displacement_5d_from_C"]["D_nm"] < 0
    assert by_id["H1B3_F2_FULL_FORWARD"]["actual_legal_displacement_5d_from_C"]["D_nm"] < by_id["H1B3_F1_CONSERVATIVE_FORWARD"]["actual_legal_displacement_5d_from_C"]["D_nm"]
    assert by_id["H1B3_F3_FORWARD_PLUS_PROJECTOR_COMPENSATION"]["exact_5d"]["J1_side_nm"] == 111
    assert len(candidates) == 4


def test_projector_compensation_audit_is_empirical_and_explicit():
    audit = H.compensation_audit()
    assert audit["status"] == "NO_SUPPORTED_PROJECTOR_COMPENSATION_DIRECTION"
    assert audit["fallback"] == "SECOND_CONSERVATIVE_LOCAL_NEIGHBOR"
    assert len(audit["variables"]) == 5
    assert all(row["classification"] == "LOCAL_EMPIRICAL_DIRECTION" for row in audit["variables"])


def test_circular_edge_and_projector_filtering():
    arc = H.H2.circular_arc([355.0, 5.0, 15.0])
    assert abs(arc["coverage_deg"] - 20.0) < 1e-9
    assert abs(H.BASELINE_H1B2_SPAN - 48.20045808425289) < 1e-12
    assert H.PROJECTOR_ERROR_MAX == 0.1864961370084426


def test_authoritative_merge_has_h1a_h1b1_h1b2_sources():
    old = H.dedup(H.old_h550_rows() + H.h1b1_rows() + H.h1b2_rows())
    assert len(H.old_h550_rows()) == 6
    assert len(H.h1b1_rows()) == 5
    assert len(H.h1b2_rows()) == 5
    assert len(old) == 16
    assert {row["source_class"] for row in old} == {"H1A_AUTHORITATIVE_FULL_JONES", "H1B1_AUTHORITATIVE_FULL_JONES", "H1B2_AUTHORITATIVE_FULL_JONES"}


def test_scheduler_and_runtime_contract():
    assert H.SLOT.GLOBAL_CAPACITY == 2
    assert H.SLOT.MAX_ACTIVE_FDTD_PER_BRANCH == 1
    assert H.SLOT.PROCESSES_PER_JOB == 4
    assert H.SLOT.THREADS_PER_JOB == 1
    assert "QUARANTINED_ENTERED_NO_RECOVERY" in H.H2.run_case.__code__.co_consts
    assert "H500_scheduled" in SCRIPT.read_text(encoding="utf-8")


def test_final_flags_and_robustness_are_defined():
    source = SCRIPT.read_text(encoding="utf-8")
    for token in ("FLAG_60_SECTOR", "FLAG_120_ML_RESTART", "SUPPORTED_LOCAL_REGION", "SINGLE_POINT_FRAGILE", "INCONCLUSIVE", "TARGETED_CONSTITUENT_RECONNAISSANCE"):
        assert token in source
