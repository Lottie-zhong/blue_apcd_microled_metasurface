
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports/stage_h1c1b_broadband_adaptive"
MANIFEST = REPORT / "h1c1b_candidate_manifest.json"

def load_runner():
    spec = importlib.util.spec_from_file_location("h1c1b_runner", ROOT / "scripts/lp_global_h_h1c1b_adaptive_v2.py")
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module

def read(path):
    return json.loads(path.read_text(encoding="utf-8"))

def test_exact_24_and_frontier_allocation():
    d = read(MANIFEST)
    rows = d["candidates"]
    assert len(rows) == 24
    assert len({row["exact_hash"] for row in rows}) == 24
    counts = {}
    for row in rows[:12]:
        parent = row["proposal_audit"]["parent_reference_geometry"]
        counts[parent] = counts.get(parent, 0) + 1
    assert counts == {"GLOBAL_018": 3, "GLOBAL_002": 3, "C": 2, "GLOBAL_006": 2, "GLOBAL_015": 2}
    assert all(row["role"] == "SELECTIVITY_FRONTIER" for row in rows[:12])
    assert all(row["role"] == "PHASE_GAP_GLOBAL_EXPLORATION" for row in rows[12:])

def test_domain_legality_and_no_historical_frontier_hash():
    d = read(MANIFEST)
    assert all(row["legality"]["pass"] for row in d["candidates"])
    assert all(row["legality"]["checks"]["native_material"] for row in d["candidates"])
    old = set()
    for rel in ("reports/stage_h1c1a_broadband_global/h1c1a_candidate_manifest.json", "reports/stage_h1b2_global_h/h1b2_candidate_manifest.json"):
        old.update(row.get("exact_hash") or row.get("exact_geometry_hash_sha256") for row in read(ROOT / rel)["candidates"])
    assert not old.intersection({row["exact_hash"] for row in d["candidates"][:12]})

def test_grid_xy_full_jones_contract_and_budget():
    d = read(MANIFEST)
    assert d["wavelength_grid_nm"] == [450.0 + 0.5 * i for i in range(9)]
    assert d["solver_budget_planned"] == 48
    assert d["max_global_fdtd_concurrency"] == 2
    assert d["max_active_fdtd_per_branch"] == 1
    assert d["processes_per_job"] == 4
    assert d["threads_per_job"] == 1
    for row in d["candidates"]:
        assert set(row["broadband_case_identity"]) == {"x", "y"}
        assert all(identity["wavelength_grid_nm"] == d["wavelength_grid_nm"] for identity in row["broadband_case_identity"].values())
        assert all(identity["exact_geometry_hash_sha256"] == row["exact_hash"] for identity in row["broadband_case_identity"].values())

def test_v1_supersession_and_exploration_retention():
    d = read(MANIFEST)
    diff = read(REPORT / "h1c1b_proposal_v1_v2_diff.json")
    assert d["v1_supersession"]["original_solver_entered"] == 0
    assert len(diff["frontier_v1_points_superseded"]) == 12
    assert len(diff["exploration_retained_unchanged"]) == 12
    assert diff["coverage_after"] == ["GLOBAL_018", "GLOBAL_002", "C", "GLOBAL_006", "GLOBAL_015"]
    assert all(row["proposal_audit"]["reused_unchanged_from_v1"] for row in d["candidates"][12:])
    assert not any(row["proposal_audit"]["reused_unchanged_from_v1"] for row in d["candidates"][:12])

def test_runner_preflight_and_accounting():
    runner = load_runner()
    result = runner.preflight()
    assert result["status"] == "H1C1B_PREFLIGHT_PASS"
    accounting = read(REPORT / "h1c1b_solver_accounting.json")
    assert accounting["solver_subruns_entered"] == 48
    assert len(accounting["cases"]) == 48
    assert accounting["solver_subruns_accepted"] == 45
    assert sum(bool(row["quarantined"]) for row in accounting["cases"]) == 3
