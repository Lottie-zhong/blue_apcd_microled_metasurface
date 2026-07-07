from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "lp_ml1" / "lp_ml1b2a_36case_pilot_execution_plan.py"
OUT = ROOT / "outputs" / "lp_ml1b2a_36case_pilot_plan"
REPORT = ROOT / "reports" / "lp_ml1b2a_36case_pilot_execution_plan.md"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def test_script_runs_and_outputs_exist() -> None:
    subprocess.run([sys.executable, str(SCRIPT)], cwd=ROOT, check=True)
    assert (OUT / "lp_ml1b2a_pilot_queue_audit.csv").exists()
    assert (OUT / "lp_ml1b2a_batch_plan.csv").exists()
    assert (OUT / "lp_ml1b2a_summary.json").exists()
    assert REPORT.exists()


def test_queue_and_batches() -> None:
    audit = read_csv(OUT / "lp_ml1b2a_pilot_queue_audit.csv")
    batches = read_csv(OUT / "lp_ml1b2a_batch_plan.csv")
    summary = json.loads((OUT / "lp_ml1b2a_summary.json").read_text(encoding="utf-8"))
    assert len(audit) == 36
    assert all(row["geometry_complete"] == "true" for row in audit)
    assert len(batches) == 6
    assert all(row["candidate_count"] == "6" for row in batches)
    assert summary["planning_only_no_fdtd"] is True
    assert summary["planned_subruns"] == 648


def test_report_boundaries_and_runtime() -> None:
    text = REPORT.read_text(encoding="utf-8")
    assert "No FDTD was run" in text
    assert "No Lumerical GUI was opened" in text
    assert "No FMM solve was executed" in text
    assert "No model training was run" in text
    assert "No K=6 was started" in text
    assert "3.19 h" in text


def test_no_heavy_or_runtime_staged() -> None:
    staged = subprocess.check_output(["git", "diff", "--cached", "--name-only"], cwd=ROOT, text=True).splitlines()
    forbidden = (".fsp", ".ldf", ".log", ".h5", ".mat", ".npz", ".npy")
    assert not any(name.endswith(forbidden) for name in staged)
    assert not any("configs/runtime.yaml" in name.replace("\\", "/") for name in staged)
