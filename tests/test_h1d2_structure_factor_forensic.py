import csv
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "h1d2_structure_factor_forensic.py"
spec = importlib.util.spec_from_file_location("h1d2_structure_factor_forensic", SCRIPT)
assert spec and spec.loader
h1d2 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h1d2)


def test_zero_solver_guard_and_regular_lattice():
    manifest = h1d2.read_json(h1d2.MANIFEST)
    geometry = h1d2.load_physical_geometry(manifest)
    positions = sorted(row["x_nm"] for row in geometry["centers"])
    p = manifest["p_nm"]
    residuals = [positions[i] - (positions[0] + i * p) for i in range(6)]
    assert max(abs(value) for value in residuals) <= h1d2.TOL


def test_complete_pillar_translation_recovers_primitive_period():
    manifest = h1d2.read_json(h1d2.MANIFEST)
    geometry = h1d2.load_physical_geometry(manifest)
    physical = h1d2.physical_record(geometry, manifest["P_supercell_nm"])
    translated = h1d2.translated_record(geometry, manifest["P_supercell_nm"], manifest["p_nm"])
    assert translated == physical


def test_root_of_unity_structure_factor_selection_rule():
    manifest = h1d2.read_json(h1d2.MANIFEST)
    positions = sorted(row["x_nm"] for row in h1d2.load_physical_geometry(manifest)["centers"])
    P = manifest["P_supercell_nm"]
    assert abs(h1d2.structure_factor(positions, P, -1)) < 1e-12
    assert abs(h1d2.structure_factor(positions, P, 1)) < 1e-12
    assert abs(abs(h1d2.structure_factor(positions, P, 0)) - 6.0) < 1e-12
    assert abs(P / 6.0 - manifest["p_nm"]) < 1e-12


def test_no_detour_control_is_physical_duplicate():
    manifest = h1d2.read_json(h1d2.MANIFEST)
    geometry = h1d2.load_physical_geometry(manifest)
    positions = sorted(row["x_nm"] for row in geometry["centers"])
    control = {"pillars": []}
    for x in [positions[0] + n * manifest["p_nm"] for n in range(6)]:
        for row in geometry["pillars"]:
            if abs(row["dimer_x_nm"] - positions[0]) < h1d2.TOL:
                copy = dict(row)
                copy["dimer_x_nm"] = x
                copy["x_nm"] += x - positions[0]
                control["pillars"].append(copy)
    assert h1d2.physical_record(geometry, manifest["P_supercell_nm"]) == h1d2.physical_record(control, manifest["P_supercell_nm"])


def test_fullwave_comparison_is_m0_selection_consistent():
    manifest = h1d2.read_json(h1d2.MANIFEST)
    final = h1d2.read_json(h1d2.H1D1_FINAL)
    positions = sorted(row["x_nm"] for row in h1d2.load_physical_geometry(manifest)["centers"])
    rows, summary = h1d2.fullwave_comparison(final, positions, manifest["P_supercell_nm"])
    assert len(rows) == 9
    assert summary["classification"] == "STRUCTURE_FACTOR_EXPLAINS_ORDER_SELECTION"


def test_canonical_registry_unchanged_and_zero_solver_outputs_if_present():
    assert sum(1 for _ in csv.DictReader(h1d2.CANONICAL_REGISTRY.open(encoding="utf-8"))) == 488
    if (h1d2.REPORT / "h1d2_summary.md").exists():
        assert "solver_entered_delta=0" in (h1d2.REPORT / "h1d2_summary.md").read_text(encoding="utf-8")
