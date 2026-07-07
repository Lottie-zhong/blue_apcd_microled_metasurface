from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "lp_ml1" / "lp_ml1b_seed_objective_audit_selectivity_first.py"
REPORT = ROOT / "reports" / "lp_ml1b_seed_objective_audit_selectivity_first.md"
SUMMARY = ROOT / "outputs" / "lp_ml1b2b_36case_pilot" / "lp_ml1b_seed_objective_audit_summary.json"
RECLASS = ROOT / "outputs" / "lp_ml1b2b_36case_pilot" / "batch_01" / "lp_ml1b_batch01_selectivity_first_reclass.csv"


def test_audit_outputs_selectivity_first_files():
    subprocess.run([sys.executable, str(SCRIPT)], cwd=ROOT, check=True)
    assert REPORT.exists()
    assert SUMMARY.exists()
    assert RECLASS.exists()

    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    assert summary["no_fdtd_run"] is True
    assert summary["conclusion"] == "not_selectivity_first_seed_generation"
    assert summary["a4_target_bin_source"] == "geometric_intent_sampling_group"
    assert summary["recommendation"] == "adjust_ranking_and_seed_logic_before_batch_02"
    assert summary["batch04_remains_recommended_if_next_fdtd_is_authorized"] is True

    rows = list(csv.DictReader(RECLASS.open(newline="", encoding="utf-8")))
    assert len(rows) == 6
    classes = {r["selectivity_first_class"] for r in rows}
    assert "high_Tx_but_nonselective" in classes
    assert "phase_near_but_nonselective" in classes
    assert all(r["projector_gate"] in {"pass", "near", "fail"} for r in rows)

    text = REPORT.read_text(encoding="utf-8")
    assert "mainly target-bin geometry exploration seeds" in text
    assert "Corrected LP-ML1B2C ranking hierarchy" in text
    assert "No FDTD was run" in text
