import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("h1b2", ROOT / "scripts/lp_global_h_h1b2_probe_v1.py")
MOD = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MOD)


def test_materializes_exactly_five_unique_h550_candidates():
    candidates, audit = MOD.build_selection_audit()
    assert len(candidates) == 5
    assert len({row["exact_geometry_hash_sha256"] for row in candidates}) == 5
    assert len({MOD.physical_key(row) for row in candidates}) == 5
    assert all(row["H_global_nm"] == 550.0 for row in candidates)
    assert all(row["legality"]["pass"] for row in candidates)
    assert len(audit["rows"]) == 5


def test_circular_arc_handles_wrap_without_linear_span_error():
    arc = MOD.circular_arc([355.0, 5.0, 15.0])
    assert abs(arc["coverage_deg"] - 20.0) < 1e-12
    assert abs(arc["arc_start_deg"] - 355.0) < 1e-12
    assert abs(arc["arc_end_deg"] - 15.0) < 1e-12
    assert abs(MOD.ccw_distance(355.0, 15.0) - 20.0) < 1e-12


def test_candidate_parent_and_displacement_provenance_is_present():
    candidates = MOD.materialize_candidates()
    assert all(row["parent_reference_id"] for row in candidates)
    assert all(row["displacement_basis"] for row in candidates)
    assert all(row["supporting_authoritative_evidence"] for row in candidates)
    assert all(row["expected_edge_target"] in {"lower", "upper", "interior_control"} for row in candidates)


def test_h1b2_budget_and_contract_constants():
    assert MOD.MAX_GEOMETRIES == 5
    assert MOD.MAX_SUBRUNS == 10
    assert MOD.POLARIZATIONS == ("x", "y")
    assert MOD.H_GLOBAL_NM == 550.0
    assert MOD.PERIOD_NM == 432.0
    assert MOD.MATERIAL == "APCD_TIO2_NATIVE_M1"
