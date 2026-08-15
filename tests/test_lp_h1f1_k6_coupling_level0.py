import csv
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports/stage_h1f1_k6_coupling_level0"


def load_search():
    path = ROOT / "scripts/lp_h1f1_k6_coupling_level0.py"
    spec = importlib.util.spec_from_file_location("h1f1_search_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_strict_bank_and_grid():
    mod = load_search()
    seeds = mod.load_seeds()
    assert len(seeds) == 12
    assert len({s["exact_hash"] for s in seeds}) == 12
    assert all(s["wavelength_grid_nm"] == mod.GRID for s in seeds)


def test_cycle_canonicalization_and_mirror_directionality():
    mod = load_search()
    seq = (0, 1, 2, 3, 4, 5)
    assert mod.canonical_cycle(seq) == mod.canonical_cycle((2, 3, 4, 5, 0, 1))
    assert mod.canonical_cycle(seq) != mod.canonical_cycle(tuple(reversed(seq)))


def test_period_and_proxy_orders():
    mod = load_search()
    assert not mod.fundamental_period_6p((0, 1, 0, 1, 0, 1))["FUNDAMENTAL_PERIOD_6P"]
    assert mod.fundamental_period_6p((0, 1, 2, 3, 4, 5))["FUNDAMENTAL_PERIOD_6P"]
    seeds = mod.load_seeds()
    proxy = mod.proxy_for_sequence((0, 1, 2, 3, 4, 5), seeds)
    assert len(proxy) == 9
    assert all("m-1_jones" in row and "m0_jones" in row and "m1_jones" in row for row in proxy)


def test_frozen_manifest_and_fullwave_accounting():
    manifest = json.loads((REPORT / "h1f1_candidate_manifest.json").read_text(encoding="utf-8-sig"))
    assert manifest["status"] == "FROZEN_READY_FOR_SETUP"
    assert manifest["candidate_count"] == 3
    assert manifest["wavelength_grid_nm"] == [450.0 + 0.5 * i for i in range(9)]
    assert all(c["no_position_shift"] and c["no_local_geometry_mutation"] for c in manifest["candidates"])
    roles = {c["role"] for c in manifest["candidates"]}
    assert roles == {"K6_L0_MEAN_TARGET_ORDER_CHAMPION", "K6_L0_WORST_WAVELENGTH_ROBUST_CHAMPION", "K6_L0_POLARIZATION_CONTRAST_CHAMPION"}
    accounting = json.loads((REPORT / "h1f1_solver_accounting.json").read_text(encoding="utf-8-sig"))
    assert (accounting["planned_formal_cases"], accounting["entered_formal_cases"], accounting["accepted_formal_cases"]) == (6, 6, 6)
    assert accounting["quarantine_cases"] == accounting["replay_cases"] == 0
    with (REPORT / "h1f1_order_resolved_fullwave.csv").open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 594
    assert {r["polarization"] for r in rows} == {"x", "y"}
    assert {-1, 0, 1}.issubset({int(r["order_n"]) for r in rows})


def test_registry_baseline_and_level1_gate():
    registry = json.loads((REPORT / "h1f1_k6_registry_audit.json").read_text(encoding="utf-8-sig"))
    assert registry["rows"] == 594
    assert registry["local_dimer_registry_rows"] == 578
    assert registry["separate_from_local_registry"] is True
    assert registry["ml_admitted"] is False
    baseline = json.loads((REPORT / "h1f1_h1d1_baseline_comparison.json").read_text(encoding="utf-8-sig"))
    assert baseline["read_only_reused"] is True and baseline["rerun"] is False
    final = json.loads((REPORT / "h1f1_final.json").read_text(encoding="utf-8-sig"))
    assert final["level1_auto_started"] is False
