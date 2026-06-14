from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNNER_1D = REPO_ROOT / "scripts" / "stage11_lp_apcd_run_targeted_patch_fdtd_stage11_1d.py"
OUT_DIR = REPO_ROOT / "outputs" / "blue10k6_lp_apcd_stage11_1e_h500_gap_closure"


def load_runner_1d():
    spec = importlib.util.spec_from_file_location("stage11_1d_runner", RUNNER_1D)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import Stage11-1D runner: {RUNNER_1D}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_summary_1e(module, j1_rows, j2_rows, dry_run: bool) -> None:
    def count(rows, key, value):
        return sum(1 for r in rows if str(r.get(key, "")) == value)

    bad_h = [
        r.get("candidate_id", "")
        for r in list(j1_rows) + list(j2_rows)
        if str(r.get("height_nm", "500")).strip() not in {"500", "500.0", "500.000000"}
    ]
    lines = [
        "# Stage11-1E H500 Gap Closure FDTD Summary",
        "",
        f"mode = {'dry_run_no_lumerical' if dry_run else 'real_h500_single_pillar_fdtd_gap_closure'}",
        f"J1 result_count = {len(j1_rows)}",
        f"J1 success = {count(j1_rows, 'extraction_status', 'ok')}",
        f"J1 failed = {count(j1_rows, 'extraction_status', 'failed')}",
        f"J1 loose_pass = {count(j1_rows, 'identity_like_pass_loose', 'true')}",
        f"J1 strict_pass = {count(j1_rows, 'identity_like_pass_strict', 'true')}",
        f"J2 result_count = {len(j2_rows)}",
        f"J2 success = {count(j2_rows, 'extraction_status', 'ok')}",
        f"J2 failed = {count(j2_rows, 'extraction_status', 'failed')}",
        f"J2 loose_pass = {count(j2_rows, 'hwp_like_pass_loose', 'true')}",
        f"J2 strict_pass = {count(j2_rows, 'hwp_like_pass_strict', 'true')}",
        f"non_h500_case_count = {len(bad_h)}",
        "",
        "Evidence boundary: Stage11-1E ran only H500 single-pillar x/y normal-incidence extraction.",
        "No H600/H700 new FDTD, no dimer FDTD, and no K=6 full FDTD are run here.",
    ]
    module.SUMMARY_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    module = load_runner_1d()
    module.OUT_DIR = OUT_DIR
    module.J1_PLAN = OUT_DIR / "h500_j1_gap_closure_plan_stage11_1e.csv"
    module.J2_PLAN = OUT_DIR / "h500_j2_gap_closure_plan_stage11_1e.csv"
    module.FDTD_DIR = OUT_DIR / "fdtd_h500_gap_closure"
    module.J1_RESULT = OUT_DIR / "h500_j1_gap_closure_fdtd_results_stage11_1e.csv"
    module.J2_RESULT = OUT_DIR / "h500_j2_gap_closure_fdtd_results_stage11_1e.csv"
    module.SUMMARY_MD = OUT_DIR / "stage11_1e_h500_gap_closure_fdtd_summary.md"
    module.write_summary = lambda j1_rows, j2_rows, dry_run: write_summary_1e(module, j1_rows, j2_rows, dry_run)
    return int(module.main())


if __name__ == "__main__":
    raise SystemExit(main())
