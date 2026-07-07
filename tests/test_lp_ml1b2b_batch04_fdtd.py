from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "lp_ml1" / "lp_ml1b2b_batch04_fdtd.py"


def load_module():
    spec = importlib.util.spec_from_file_location("batch04", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_batch04_constants_are_scoped_to_batch04():
    module = load_module()
    assert module.BATCH_ID == "LPML1B2A_BATCH_04"
    assert str(module.OUT).endswith("batch_04")
    assert module.RESULTS.name == "lp_ml1b2b_batch04_results.csv"
    assert module.SUMMARY.name == "lp_ml1b2b_batch04_summary.json"
    assert module.REPORT.name == "lp_ml1b2b_batch04_execution_report.md"


def test_batch04_selects_exactly_frozen_batch04_candidates():
    module = load_module()
    ids = module.batch_candidate_ids()
    assert len(ids) == 6
    assert ids[0] == "LPML1A4_0270_B240_exploration_B240_H600"
    assert ids[-1] == "LPML1A4_0536_global_escape_lhs_B180_H500"
