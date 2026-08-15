import importlib.util
import json
import math
from pathlib import Path

ROOT = Path(r"D:\project\worktrees\blue_apcd_lp_global_h_manifold_v1")
REPORT = ROOT / "reports/stage_h1f3b_k6_position_mode_level2"


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def test_manifest_and_seeds():
    m = json.loads((REPORT / "h1f3b_candidate_manifest.json").read_text())
    assert m["status"] == "FROZEN_READY_FOR_SOLVER"
    assert m["candidate_count"] == 4
    assert m["max_new_formal_cases"] == 8
    assert m["ml_admitted"] is False
    assert {x["base_candidate_uid"] for x in m["candidates"]} == {"K6_L0_A", "K6_L1_C"}
    assert {x["A_nm"] for x in m["candidates"]} == {-10.0, 10.0}


def test_exact_mode_vectors_and_invariants():
    m = json.loads((REPORT / "h1f3b_candidate_manifest.json").read_text())
    for c in m["candidates"]:
        sign = 1 if c["A_nm"] > 0 else -1
        base = c["base_site_positions_nm"]
        deltas = [p["x_nm"] - q["x_nm"] for p, q in zip(c["site_positions_nm"], base)]
        expected = [sign * 10.0 * math.cos(2 * math.pi * n / 6) for n in range(6)]
        assert all(abs(a - b) < 1e-12 for a, b in zip(deltas, expected))
        assert abs(sum(deltas)) < 1e-12
        assert all(p["y_nm"] == q["y_nm"] for p, q in zip(c["site_positions_nm"], base))
        assert c["local_geometries"] == [s for s in m["selected_seeds"] if s["seed_uid"] == c["base_candidate_uid"]][0]["ordered_local_geometries"]
        assert c["P_supercell_nm"] == 2591.446716


def test_equivalence_and_legality():
    eq = json.loads((REPORT / "h1f3b_physical_equivalence_audit.json").read_text())
    assert all(x["all_three_distinct"] and not x["cyclic_redundancy_detected"] for x in eq["seeds"].values())
    legal = json.loads((REPORT / "h1f3b_geometry_legality.json").read_text())
    assert legal["period"]["fundamental_period_6P"]
    assert all(x["pass"] and x["no_overlap"] and x["no_y_motion"] and x["P_unchanged"] and x["local_geometry_unchanged"] for x in legal["layouts"].values())


def test_runner_preflight_contract():
    mod = load(ROOT / "scripts/lp_h1f3b_runner.py", "h1f3b_runner_test")
    result = mod.preflight()
    assert result["status"] == "READY"
    assert result["planned_formal_cases"] == 8
    assert result["live_solver_accounting"]["lp_active_fdtd_jobs"] == 0
    assert result["live_solver_accounting"]["active_fdtd_jobs"] < 2
