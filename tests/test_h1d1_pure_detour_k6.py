import importlib.util
import json
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "lp_h1d1_pure_detour_k6.py"
spec = importlib.util.spec_from_file_location("h1d1_pure_detour_k6", SCRIPT)
assert spec and spec.loader
h1d1 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h1d1)


def test_manifest_has_exact_six_parent_copies_and_grid():
    manifest = h1d1.ensure_manifest()
    assert len(manifest["copies"]) == 6
    assert {row["geometry_hash"] for row in manifest["copies"]} == {h1d1.PARENT_HASH}
    assert manifest["wavelength_grid_nm"] == h1d1.GRID
    assert manifest["m_target"] == 1
    assert manifest["detour_sign_convention"] == "exp(-i*G_m*Delta_x)"
    assert manifest["position_sorted_phase_order"] == [60.0, 0.0, 300.0, 240.0, 180.0, 120.0]


def test_geometry_legality_matches_h1d0_reference():
    manifest = h1d1.ensure_manifest()
    result = h1d1.legality(manifest)
    assert result["pass"] is True
    assert result["no_overlap"] is True
    assert abs(result["minimum_clearance_computed_nm"] - 76.53990891658569) < 1e-9
    assert abs(result["boundary_margin_computed_nm"] - 63.22384745829277) < 1e-9


def test_authorized_budget_is_two_sequential_polarization_cases():
    assert h1d1.MAX_SUBRUNS == 2
    assert h1d1.POLARIZATIONS == ("x", "y")
    assert h1d1.PROCESSES == 4
    assert h1d1.THREADS == 1


def test_gratingvector_order_extraction_supports_one_broadband_case():
    class FakeFDTD:
        def transmission(self, _):
            return np.ones(9) * 0.5

        def gratingn(self, *_):
            return np.array([-1, 0, 1])

        def gratingm(self, *_):
            return np.array([0])

        def gratingu1(self, *_):
            return np.array([-0.2, 0.0, 0.2])

        def gratingu2(self, *_):
            return np.array([0.0])

        def grating(self, *_):
            return np.array([[0.1], [0.8], [0.1]])

        def gratingvector(self, *_):
            return np.array([[[0.1 + 0.0j, 0.0j, 0.0j]], [[0.8 + 0.0j, 0.0j, 0.0j]], [[0.1 + 0.0j, 0.0j, 0.0j]]])

    rows = h1d1.extract_orders(FakeFDTD(), "x")
    assert len(rows) == 27
    target = [row for row in rows if row["order_n"] == 1 and row["order_m"] == 0]
    assert len(target) == 9
    assert target[0]["order_efficiency_source_norm"] == 0.05
    assert target[0]["complex_source_normalized"] is True


def test_manifest_and_accounting_are_not_local_dimer_ml_registry():
    manifest = h1d1.ensure_manifest()
    assert manifest["contract"]["ml_admitted"] is False
    accounting = json.loads((h1d1.REPORT / "h1d1_solver_accounting.json").read_text(encoding="utf-8"))
    assert accounting["manifest_freeze_sha256"] == manifest["freeze_sha256"]


def test_xy_to_alpha_beta_returns_full_2x2_matrix():
    matrix = h1d1.transform_xy([[1 + 0j, 0j], [0j, 1 + 0j]])
    assert len(matrix) == 2 and all(len(row) == 2 for row in matrix)
