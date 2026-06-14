from __future__ import annotations

import csv
import math
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_ROOT / "outputs" / "blue10k6_lp_apcd_stage11_2a_h500_dimer_validation"
RESULT_CSV = OUT_DIR / "h500_dimer_fdtd_results_stage11_2a.csv"
SUMMARY_MD = OUT_DIR / "h500_dimer_6bin_summary_stage11_2a.md"
BEST_CSV = OUT_DIR / "h500_dimer_best_candidates_stage11_2a.csv"
GAP_MD = OUT_DIR / "h500_dimer_gap_diagnosis_stage11_2a.md"
PHASE_BINS = [0, 60, 120, 180, 240, 300]

BEST_FIELDS = [
    "bin_deg", "best_dimer_case_id", "source_pair_id", "dimer_selectivity_ratio", "target_x_power",
    "polarization_purity_x", "dimer_output_phase_deg", "dimer_vs_static_phase_error_deg",
    "dimer_pass_loose", "dimer_pass_strict", "status", "diagnosis",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return [{str(k): "" if v is None else str(v) for k, v in row.items()} for row in csv.DictReader(f)]


def write_csv(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def f(value: object, default: float = math.nan) -> float:
    try:
        if value is None or str(value).strip() == "":
            return default
        return float(value)
    except Exception:
        return default


def choose_best(rows: list[dict[str, str]]) -> dict[str, str] | None:
    if not rows:
        return None
    rows = sorted(
        rows,
        key=lambda r: (
            0 if r.get("dimer_pass_strict") == "true" else 1,
            0 if r.get("dimer_pass_loose") == "true" else 1,
            -f(r.get("dimer_selectivity_ratio")),
            -f(r.get("target_x_power")),
            f(r.get("dimer_vs_static_phase_error_deg")),
        ),
    )
    return rows[0]


def diagnosis(row: dict[str, str] | None) -> tuple[str, str]:
    if row is None:
        return "missing_dimer", "missing_dimer"
    if row.get("fdtd_status") != "ok":
        return "static_only_failed_dimer", "geometry infeasible or FDTD failed"
    if row.get("dimer_pass_strict") == "true":
        return "dimer_verified_strict", "passes strict dimer thresholds"
    if row.get("dimer_pass_loose") == "true":
        return "dimer_verified_loose", "passes loose dimer thresholds"
    reasons = []
    if f(row.get("dimer_vs_static_phase_error_deg")) > 25:
        reasons.append("coupling broke phase")
    if f(row.get("polarization_purity_x")) < 0.80:
        reasons.append("coupling increased x-input cross leakage")
    if f(row.get("dimer_selectivity_ratio")) < 3:
        reasons.append("coupling increased y leakage")
    if f(row.get("target_x_power")) < 0.10:
        reasons.append("target transmission too low")
    if not reasons:
        reasons.append("static model not transferable")
    return "static_only_failed_dimer", "; ".join(reasons)


def main() -> int:
    if not RESULT_CSV.exists():
        raise SystemExit(f"missing required input: {RESULT_CSV}")
    rows = read_csv(RESULT_CSV)
    best_rows = []
    lines = [
        "# Stage11-2A H500 Dimer 6-Bin Summary",
        "",
        "Evidence boundary: H500 dimer validation only. This is not K=6 steering and not a phase-gradient supercell.",
        "",
        "| bin_deg | candidate_count | best_dimer_case_id | source_pair_id | selectivity | target_x_power | purity_x | output_phase | phase_error_vs_static | loose | strict | status |",
        "|---:|---:|---|---|---:|---:|---:|---:|---:|---|---|---|",
    ]
    gap_lines = ["# Stage11-2A H500 Dimer Gap Diagnosis", ""]
    for bin_deg in PHASE_BINS:
        subset = [r for r in rows if int(f(r.get("bin_deg"))) == bin_deg]
        best = choose_best(subset)
        status, why = diagnosis(best)
        if best is None:
            lines.append(f"| {bin_deg} | 0 |  |  |  |  |  |  |  | false | false | missing_dimer |")
            best_rows.append({"bin_deg": str(bin_deg), "status": status, "diagnosis": why})
        else:
            lines.append(
                f"| {bin_deg} | {len(subset)} | {best['dimer_case_id']} | {best['source_pair_id']} | {best.get('dimer_selectivity_ratio','')} | {best.get('target_x_power','')} | {best.get('polarization_purity_x','')} | {best.get('dimer_output_phase_deg','')} | {best.get('dimer_vs_static_phase_error_deg','')} | {best.get('dimer_pass_loose','false')} | {best.get('dimer_pass_strict','false')} | {status} |"
            )
            best_rows.append(
                {
                    "bin_deg": str(bin_deg),
                    "best_dimer_case_id": best["dimer_case_id"],
                    "source_pair_id": best["source_pair_id"],
                    "dimer_selectivity_ratio": best.get("dimer_selectivity_ratio", ""),
                    "target_x_power": best.get("target_x_power", ""),
                    "polarization_purity_x": best.get("polarization_purity_x", ""),
                    "dimer_output_phase_deg": best.get("dimer_output_phase_deg", ""),
                    "dimer_vs_static_phase_error_deg": best.get("dimer_vs_static_phase_error_deg", ""),
                    "dimer_pass_loose": best.get("dimer_pass_loose", "false"),
                    "dimer_pass_strict": best.get("dimer_pass_strict", "false"),
                    "status": status,
                    "diagnosis": why,
                }
            )
        gap_lines.append(f"- {bin_deg} deg: {status}; {why}")
    SUMMARY_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    GAP_MD.write_text("\n".join(gap_lines) + "\n", encoding="utf-8")
    write_csv(BEST_CSV, best_rows, BEST_FIELDS)
    print(f"dimer_pass_loose_count={sum(1 for r in rows if r.get('dimer_pass_loose') == 'true')}")
    print(f"dimer_pass_strict_count={sum(1 for r in rows if r.get('dimer_pass_strict') == 'true')}")
    print(f"verified_bins_loose={','.join(str(r['bin_deg']) for r in best_rows if r.get('status') in {'dimer_verified_loose','dimer_verified_strict'})}")
    print(f"verified_bins_strict={','.join(str(r['bin_deg']) for r in best_rows if r.get('status') == 'dimer_verified_strict')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
