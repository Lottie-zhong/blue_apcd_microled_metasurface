from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "lp_ml1" / "lp_ml1b1a_smoke_result_sanity_audit.py"
OUT = ROOT / "outputs" / "lp_ml1b1a_smoke_result_sanity_audit"
CANDIDATE_SUMMARY = OUT / "lp_ml1b1a_candidate_summary.csv"
ANOMALIES = OUT / "lp_ml1b1a_anomaly_flags.csv"
SUMMARY = OUT / "lp_ml1b1a_summary.json"
REPORT = ROOT / "reports" / "lp_ml1b1a_smoke_result_sanity_audit.md"
DECISION = ROOT / "reports" / "lp_ml1b1a_next_action_decision.md"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def test_script_runs_successfully() -> None:
    subprocess.run([sys.executable, str(SCRIPT)], cwd=ROOT, check=True)


def test_outputs_and_candidate_count() -> None:
    assert (OUT / "lp_ml1b1a_metric_summary.csv").exists()
    assert CANDIDATE_SUMMARY.exists()
    assert ANOMALIES.exists()
    assert SUMMARY.exists()
    assert REPORT.exists()
    assert DECISION.exists()
    assert len(read_csv(CANDIDATE_SUMMARY)) == 2


def test_anomaly_columns_and_decision_report() -> None:
    rows = read_csv(ANOMALIES)
    fields = set(rows[0].keys()) if rows else {"candidate_id", "wavelength_nm", "flag_type", "category", "message", "value", "threshold"}
    assert {"candidate_id", "wavelength_nm", "flag_type", "category", "message", "value", "threshold"}.issubset(fields)
    text = DECISION.read_text(encoding="utf-8")
    assert "Go" in text or "No-Go" in text


def test_reports_boundary_text() -> None:
    text = REPORT.read_text(encoding="utf-8") + DECISION.read_text(encoding="utf-8")
    assert "No FDTD was run" in text
    assert "No FMM solver was executed" in text
    assert "No heavy files were committed" in text


def test_no_heavy_or_runtime_staged_or_created_by_audit() -> None:
    staged = subprocess.check_output(["git", "diff", "--cached", "--name-only"], cwd=ROOT, text=True).splitlines()
    forbidden = (".fsp", ".ldf", ".h5", ".mat", ".npz", ".npy")
    assert not any(name.endswith(forbidden) for name in staged)
    assert not any("configs/runtime.yaml" in name.replace("\\", "/") for name in staged)
    assert not any(p.suffix in forbidden for p in OUT.rglob("*"))
