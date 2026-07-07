from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "lp_ml1" / "lp_ml1b2b_batch01_diagnostic_audit.py"
OUT = ROOT / "outputs" / "lp_ml1b2b_36case_pilot"
GEOM = OUT / "batch_01" / "lp_ml1b2b_batch01_geometry_response_join.csv"
REMAIN = OUT / "lp_ml1b2b_remaining_batch_composition.csv"
REC = OUT / "lp_ml1b2b_next_batch_recommendation.json"
REPORT = ROOT / "reports" / "lp_ml1b2b_batch01_diagnostic_and_next_batch_audit.md"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def test_script_runs() -> None:
    subprocess.run([sys.executable, str(SCRIPT)], cwd=ROOT, check=True)


def test_outputs_exist_and_shape() -> None:
    assert GEOM.exists()
    assert REMAIN.exists()
    assert REC.exists()
    assert REPORT.exists()
    assert len(read_csv(GEOM)) == 6
    assert len(read_csv(REMAIN)) == 5


def test_recommendation_and_boundaries() -> None:
    rec = json.loads(REC.read_text(encoding="utf-8"))
    assert rec["recommended_next_batch_id"]
    assert rec["no_fdtd_run"] is True
    text = REPORT.read_text(encoding="utf-8")
    assert "No FDTD was run" in text
    assert "Do not declare K=6 readiness" in text


def test_no_heavy_or_runtime_staged() -> None:
    staged = subprocess.check_output(["git", "diff", "--cached", "--name-only"], cwd=ROOT, text=True).splitlines()
    forbidden = (".fsp", ".ldf", ".log", ".h5", ".mat", ".npz", ".npy")
    assert not any(name.endswith(forbidden) for name in staged)
    assert not any("configs/runtime.yaml" in name.replace("\\", "/") for name in staged)
