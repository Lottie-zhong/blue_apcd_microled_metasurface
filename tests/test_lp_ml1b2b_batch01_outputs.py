from __future__ import annotations

import csv
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "lp_ml1b2b_36case_pilot" / "batch_01"
RESULTS = OUT / "lp_ml1b2b_batch01_results.csv"
SUMMARY = OUT / "lp_ml1b2b_batch01_summary.json"
RANKING = OUT / "lp_ml1b2b_batch01_candidate_ranking.csv"
FAILURES = OUT / "lp_ml1b2b_batch01_failure_log.csv"
RUNTIME = OUT / "lp_ml1b2b_batch01_runtime_manifest.csv"
REPORT = ROOT / "reports" / "lp_ml1b2b_batch01_execution_report.md"
EXPECTED = {
    "LPML1A4_0028_B300_exploration_B300_H600",
    "LPML1A4_0049_B300_exploration_B300_H500",
    "LPML1A4_0093_B300_exploration_B300_H500",
    "LPML1A4_0157_B300_exploration_B300_H500",
    "LPML1A4_0178_B300_exploration_B300_H650",
    "LPML1A4_0196_B300_exploration_B300_H500",
}
JONES = {"txx_re", "txx_im", "txy_re", "txy_im", "tyx_re", "tyx_im", "tyy_re", "tyy_im"}


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def test_batch01_outputs_exist_and_counts() -> None:
    for path in [RESULTS, SUMMARY, RANKING, FAILURES, RUNTIME, REPORT]:
        assert path.exists()
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    assert summary["candidate_count"] == 6
    assert summary["expected_subruns"] == 108
    assert summary["expected_merged_rows"] == 54
    assert summary["merged_row_count"] == 54
    assert summary["failure_count"] == 0


def test_result_schema_and_candidates() -> None:
    data = rows(RESULTS)
    assert len(data) == 54
    assert {r["candidate_id"] for r in data} == EXPECTED
    assert JONES.issubset(data[0].keys())
    assert all(r["result_status"] == "ok" for r in data)


def test_ranking_and_boundaries() -> None:
    ranking = rows(RANKING)
    assert len(ranking) == 6
    text = REPORT.read_text(encoding="utf-8")
    assert "No full 36-case run was executed" in text
    assert "No 600-candidate run was executed" in text
    assert "No GUI, FMM solve, ML training, K=6, or coverage run was executed" in text


def test_no_heavy_or_runtime_staged() -> None:
    staged = subprocess.check_output(["git", "diff", "--cached", "--name-only"], cwd=ROOT, text=True).splitlines()
    forbidden = (".fsp", ".ldf", ".log", ".h5", ".mat", ".npz", ".npy")
    assert not any(name.endswith(forbidden) for name in staged)
    assert not any("configs/runtime.yaml" in name.replace("\\", "/") for name in staged)
