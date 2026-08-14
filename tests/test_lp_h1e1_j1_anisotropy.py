import importlib.util
from pathlib import Path


_here = Path(__file__).resolve()
_candidates = [_here.parents[1] / "scripts" / "lp_h1e1_j1_anisotropy_probe.py", _here.with_name("lp_h1e1_j1_anisotropy_probe.py")]
SCRIPT = next(path for path in _candidates if path.exists())
spec = importlib.util.spec_from_file_location("h1e1", SCRIPT)
h1e1 = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(h1e1)


def parent(uid="P", side=109):
    return {"geometry_uid": uid, "exact_hash": uid * 64, "coordinates_5d": {"J1_side_nm": side, "J2_length_nm": 106, "J2_width_nm": 95, "D_nm": 205.08778608196053, "Psi_deg": -1.6764710468067516}, "trajectory": [{"phi_deg": 80 + i} for i in range(9)]}


def test_grid_exactly_nine_points():
    assert h1e1.GRID == [450.0 + 0.5 * i for i in range(9)]


def test_old_isotropic_maps_to_diagonal():
    p = parent(); ident = h1e1.identity(p, 109, 109, *h1e1.parent_center(p["coordinates_5d"]))
    assert ident["J1_length_nm"] == ident["J1_width_nm"] == 109


def test_bounds_are_closed():
    p = parent(); assert h1e1.legality(p, 102, 114, set())["checks"]["bounds_L"]
    assert h1e1.legality(p, 102, 114, set())["checks"]["bounds_W"]


def test_constant_mean_positive_and_negative():
    p = parent();
    for d in (-5, -1, 1, 5):
        row = h1e1.legality(p, 109 + d, 109 - d, set())
        assert row["checks"]["constant_mean"]


def test_legal_d_box_is_exact():
    assert h1e1.legal_ds(parent(side=109))["d_box"] == 5
    assert h1e1.legal_ds(parent(side=114))["d_box"] == 0


def test_integer_target_rounds_then_searches_inward():
    assert h1e1.nearest([1], 2 / 3) == 1
    assert h1e1.nearest([1, 2, 3, 4, 5], 14 / 3) == 5


def test_geometry_legality_requires_unique_hash():
    p = parent(); a = h1e1.legality(p, 111, 107, set()); assert a["pass"]
    assert not h1e1.legality(p, 111, 107, {a["exact_hash"]})["pass"]


def test_geometry_hash_changes_with_anisotropy():
    p = parent(); a = h1e1.legality(p, 111, 107, set()); b = h1e1.legality(p, 107, 111, set())
    assert a["exact_hash"] != b["exact_hash"]


def test_parent_center_is_half_grid():
    x, y = h1e1.parent_center(parent()["coordinates_5d"])
    assert (2 * x).is_integer() and (2 * y).is_integer()


def test_circular_difference_wraps():
    assert h1e1.cdiff(1, 359) == 2
    assert h1e1.cdiff(359, 1) == -2


def test_circular_coverage_wrap_case():
    result = h1e1.coverage([355, 5, 15])
    assert result["coverage_deg"] == 20
    assert result["largest_gap_deg"] == 340


def test_circular_coverage_singleton():
    assert h1e1.coverage([360])["coverage_deg"] == 0


def test_circular_coverage_duplicate_points():
    assert h1e1.coverage([10, 10, 10])["largest_gap_deg"] == 360


def test_identity_contains_unified_height():
    p = parent(); x, y = h1e1.parent_center(p["coordinates_5d"])
    ident = h1e1.identity(p, 111, 107, x, y)
    assert ident["H_global_nm"] == ident["J1_H_nm"] == ident["J2_H_nm"] == 550.0


def test_identity_contains_formal_extraction():
    p = parent(); x, y = h1e1.parent_center(p["coordinates_5d"])
    ident = h1e1.identity(p, 111, 107, x, y)
    assert "coordinate_weighted" in ident["observable"]
    assert "deduplicate" in ident["endpoint_convention"]


def test_projector_threshold_is_frozen():
    assert h1e1.PROJECTOR_ERROR_MAX == 0.1864961370084426


def test_solver_budget_is_sixteen():
    assert h1e1.MAX_SUBRUNS == 16


def test_polarization_pair_is_full_jones():
    assert h1e1.POLARIZATIONS == ("x", "y")


def test_grammar_version_is_independent_anisotropy():
    p = parent(); x, y = h1e1.parent_center(p["coordinates_5d"])
    assert h1e1.identity(p, 111, 107, x, y)["grammar_version"] == "J1_INDEPENDENT_ANISOTROPY_V1"


def test_ml_admission_contract_is_not_in_runner_constants():
    assert h1e1.MATERIAL == "APCD_TIO2_NATIVE_M1"


def test_legality_rejects_out_of_bounds():
    assert not h1e1.legality(parent(), 101, 117, set())["pass"]


def test_no_solver_state_is_created_by_import():
    assert callable(h1e1.run_all)
    assert callable(h1e1.make_manifest)
