import csv
import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "lp_global_h_h1b1_probe_v1.py"
SPEC = importlib.util.spec_from_file_location("h1b1_test_module", SCRIPT)
H1B1 = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(H1B1)


def test_materialization_is_exactly_five_and_h550_only():
    rows = H1B1.materialize_candidates()
    assert len(rows) == 5
    assert len({r["candidate_id"] for r in rows}) == 5
    assert len({r["exact_geometry_hash_sha256"] for r in rows}) == 5
    assert all(r["H_global_nm"] == 550.0 for r in rows)
    assert all(r["J1_H_nm"] == r["J2_H_nm"] == 550.0 for r in rows)


def test_roles_cover_authorized_a_to_e():
    roles = [r["role"] for r in H1B1.materialize_candidates()]
    assert roles == [
        "A_lower_compatible_phase_edge_extension",
        "B_upper_compatible_phase_edge_extension",
        "C_J1_side_directed_contrast",
        "D_D_Psi_directed_contrast",
        "E_interior_projector_preserving_robustness_control",
    ]


def test_legality_and_exact_hashes_are_frozen():
    rows = H1B1.materialize_candidates()
    anchors = json.loads(H1B1.H0_ANCHORS.read_text(encoding="utf-8"))["anchors"]
    anchor_keys = {H1B1.anchor_key(row) for row in anchors}
    bounds = json.loads(H1B1.BOUNDS.read_text(encoding="utf-8"))
    seen = set()
    for row in rows:
        audit = H1B1.legality(row, bounds, anchor_keys, seen)
        assert audit["pass"], audit
        seen.add(row["exact_geometry_hash_sha256"])
        assert audit["direct_gap_nm"] >= 60.0
        assert audit["periodic_gap_x_nm"] >= 60.0
        assert audit["periodic_gap_y_nm"] >= 60.0


def test_budget_is_five_times_x_and_y_and_h500_is_excluded():
    rows = H1B1.materialize_candidates()
    cases = [(r["candidate_id"], p) for r in rows for p in H1B1.POLARIZATIONS]
    assert len(cases) == H1B1.MAX_SUBRUNS == 10
    assert {p for _, p in cases} == {"x", "y"}
    assert all(r["H_global_nm"] == H1B1.H_GLOBAL_NM for r in rows)
    assert H1B1.H_GLOBAL_NM != 500.0


def test_circular_span_wraps_across_zero():
    result = H1B1.phase_span([355.0, 5.0, 15.0])
    assert result["circular_coverage_deg"] == 20.0
