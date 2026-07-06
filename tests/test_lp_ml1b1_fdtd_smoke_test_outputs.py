from __future__ import annotations

import csv
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "lp_ml1b1_fdtd_smoke_test"
RESULTS = OUT / "lp_ml1b1_smoke_results.csv"
SUMMARY = OUT / "lp_ml1b1_smoke_summary.json"
FAILURES = OUT / "lp_ml1b1_failure_log.csv"
RUNTIME = OUT / "lp_ml1b1_runtime_manifest.csv"
EXPECTED = {
    "LPML1A4_0028_B300_exploration_B300_H600",
    "LPML1A4_0234_B240_exploration_B240_H600",
}
JONES_COLUMNS = {"txx_re", "txx_im", "txy_re", "txy_im", "tyx_re", "tyx_im", "tyy_re", "tyy_im"}


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def test_output_files_exist() -> None:
    assert RESULTS.exists()
    assert SUMMARY.exists()
    assert FAILURES.exists()
    assert RUNTIME.exists()


def test_result_schema_and_candidates() -> None:
    data = rows(RESULTS)
    assert data
    assert JONES_COLUMNS.issubset(data[0].keys())
    ids = {row["candidate_id"] for row in data}
    assert ids == EXPECTED
    assert len(ids) <= 2
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    if summary["failed_rows"] == 0:
        assert len(data) == 18


def test_reports_state_extraction_and_heavy_boundary() -> None:
    report = (ROOT / "reports" / "lp_ml1b1_fdtd_smoke_test.md").read_text(encoding="utf-8")
    audit = (ROOT / "reports" / "lp_ml1b1_jones_extraction_audit.md").read_text(encoding="utf-8")
    assert "heavy files were not committed" in report
    assert "farfield3d intensity was not used for phase" in audit


def test_no_heavy_or_runtime_staged() -> None:
    staged = subprocess.check_output(["git", "diff", "--cached", "--name-only"], cwd=ROOT, text=True).splitlines()
    forbidden_suffixes = (".fsp", ".ldf", ".h5", ".mat", ".npz", ".npy")
    assert not any(name.endswith(forbidden_suffixes) for name in staged)
    assert not any("configs/runtime.yaml" in name.replace("\\", "/") for name in staged)
