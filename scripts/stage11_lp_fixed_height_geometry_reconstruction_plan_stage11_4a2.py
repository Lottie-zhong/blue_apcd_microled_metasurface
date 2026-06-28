from __future__ import annotations

import csv
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = REPO_ROOT / "reports"
A1_RESULTS = REPORT_DIR / "stage11_4a1_lp_hnew_results.csv"
A1_RANKING = REPORT_DIR / "stage11_4a1_lp_hnew_candidate_ranking.csv"
A1_HEIGHT_SUMMARY = REPORT_DIR / "stage11_4a1_lp_hnew_height_summary.csv"
A1_BOTTLENECK = REPORT_DIR / "stage11_4a1_lp_hnew_bottleneck_summary.md"
A1_NEXT = REPORT_DIR / "stage11_4a1_lp_hnew_recommended_next.md"
A1_REPORT = REPORT_DIR / "stage11_4a1_lp_hnew_report.md"

PLAN_MD = REPORT_DIR / "stage11_4a2_lp_geometry_reconstruction_plan.md"
CANDIDATE_SPACE_CSV = REPORT_DIR / "stage11_4a2_lp_geometry_reconstruction_candidate_space.csv"
MANIFEST_JSON = REPORT_DIR / "stage11_4a2_lp_geometry_reconstruction_manifest.json"
SUMMARY_JSON = REPORT_DIR / "stage11_4a2_lp_geometry_reconstruction_summary.json"

WAVELENGTHS = [451, 452, 453]
PASS_THRESHOLDS = {
    "strict": {"ratio_min": 6.0, "Tx_min": 0.45, "matrix_error_max": 0.50, "phase_error_max_deg": 25.0},
    "loose": {"ratio_min": 3.0, "Tx_min": 0.10, "matrix_error_max": 1.00, "phase_error_max_deg": 35.0},
}
FIELDNAMES = [
    "group_id", "height_nm", "phase_bin_deg", "wavelengths_nm", "variants_per_bin", "planned_cases",
    "priority", "candidate_family", "geometry_knobs", "purpose", "trigger", "early_stop_rule",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [{k: "" if v is None else str(v) for k, v in row.items()} for row in csv.DictReader(handle)]


def as_float(row: dict[str, str], key: str, default: float = 0.0) -> float:
    try:
        return float(row.get(key, "") or default)
    except ValueError:
        return default


def a1_facts() -> dict[str, object]:
    for path in [A1_RESULTS, A1_RANKING, A1_HEIGHT_SUMMARY, A1_BOTTLENECK, A1_NEXT, A1_REPORT]:
        if not path.exists():
            raise FileNotFoundError(path)
    heights = read_csv(A1_HEIGHT_SUMMARY)
    results = read_csv(A1_RESULTS)
    h600 = [r for r in results if int(float(r["height_nm"])) == 600]
    b300 = [r for r in h600 if int(float(r["phase_bin_deg"])) == 300]
    b240 = [r for r in h600 if int(float(r["phase_bin_deg"])) == 240]
    best_b300 = max(b300, key=lambda r: as_float(r, "conversion_to_leakage_ratio"), default={})
    best_b240 = max(b240, key=lambda r: as_float(r, "conversion_to_leakage_ratio"), default={})
    return {
        "height_summary": heights,
        "h600_b300_best_ratio": as_float(best_b300, "conversion_to_leakage_ratio"),
        "h600_b300_best_Tx": as_float(best_b300, "target_Tx"),
        "h600_b300_worst_phase_error": max([as_float(r, "phase_error_deg") for r in b300] or [0.0]),
        "h600_b240_best_ratio": as_float(best_b240, "conversion_to_leakage_ratio"),
        "h600_b240_worst_phase_error": max([as_float(r, "phase_error_deg") for r in b240] or [0.0]),
        "a1_recommendation": A1_NEXT.read_text(encoding="utf-8").strip(),
    }


def plan_rows() -> list[dict[str, str]]:
    wl = ";".join(str(w) for w in WAVELENGTHS)
    return [
        {
            "group_id": "S11_4A2_H600_B240_ROLE_RECOMBINE",
            "height_nm": "600", "phase_bin_deg": "240", "wavelengths_nm": wl,
            "variants_per_bin": "8", "planned_cases": "24", "priority": "primary",
            "candidate_family": "fixed_height_H600_J1J2_role_recombination",
            "geometry_knobs": "J1/J2 role-pair recombination; swap/no-swap; x/y/diag orientation; gap 40-120 nm; J2 length/width local perturbation",
            "purpose": "repair B240 first because A1 H600 B240 failed ratio, matrix, and phase",
            "trigger": "always first",
            "early_stop_rule": "stop this group after any candidate is strict at 451/452/453, else keep best leakage and matrix near-miss",
        },
        {
            "group_id": "S11_4A2_H600_B300_PHASE_PULL",
            "height_nm": "600", "phase_bin_deg": "300", "wavelengths_nm": wl,
            "variants_per_bin": "6", "planned_cases": "18", "priority": "secondary",
            "candidate_family": "fixed_height_H600_phase_pull_from_B300_high_ratio",
            "geometry_knobs": "swap/no-swap; x_pair/diag_pair; gap 60-120 nm; center offset; small J2 length/width perturbation",
            "purpose": "use H600 B300 high selectivity as phase-only repair seed",
            "trigger": "run after B240 group or in parallel if budget is available",
            "early_stop_rule": "stop after strict B300 or if phase error cannot be pulled below loose threshold in first half of variants",
        },
        {
            "group_id": "S11_4A2_H600_COVERAGE_0_60_120_180",
            "height_nm": "600", "phase_bin_deg": "0;60;120;180", "wavelengths_nm": wl,
            "variants_per_bin": "3", "planned_cases": "36", "priority": "coverage",
            "candidate_family": "fixed_height_H600_sixbin_coverage_reconstruction",
            "geometry_knobs": "role-pair recombination; orientation family; gap ladder; local width/length perturbation around H600 templates",
            "purpose": "only cover remaining bins after 240/300 show viable fixed-height behavior",
            "trigger": "run only if B240 or B300 reaches at least loose at all wavelengths",
            "early_stop_rule": "stop coverage once four bins have strict or loose candidates over 451/452/453",
        },
        {
            "group_id": "S11_4A2_H650_ESCAPE_HATCH_240_300",
            "height_nm": "650", "phase_bin_deg": "240;300", "wavelengths_nm": wl,
            "variants_per_bin": "3", "planned_cases": "18", "priority": "conditional_secondary",
            "candidate_family": "fixed_height_H650_bottleneck_escape_hatch",
            "geometry_knobs": "same reconstruction knobs as H600, limited to 240/300",
            "purpose": "test H650 only if H600 lacks enough phase diversity after bottleneck repair attempts",
            "trigger": "run only if H600 B240 and B300 both fail loose gates",
            "early_stop_rule": "stop immediately if H650 also fails loose gates for both 240 and 300",
        },
    ]


def total_cases(rows: list[dict[str, str]]) -> int:
    return sum(int(r["planned_cases"]) for r in rows)


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def build_manifest(rows: list[dict[str, str]], facts: dict[str, object]) -> dict[str, object]:
    return {
        "stage": "Stage11-4A2",
        "task": "LP fixed-height geometry reconstruction planning",
        "planning_only": True,
        "no_fdtd_run": True,
        "no_lumerical_run": True,
        "no_k6_metagrating": True,
        "primary_height_nm": 600,
        "secondary_optional_height_nm": 650,
        "excluded_heights_nm": [500, 700],
        "wavelengths_nm": WAVELENGTHS,
        "primary_bins_deg": [240],
        "secondary_bins_deg": [300],
        "coverage_bins_deg": [0, 60, 120, 180],
        "hard_future_case_budget": 96,
        "planned_future_extraction_cases": total_cases(rows),
        "pass_thresholds_reused_from_stage11_4a1": PASS_THRESHOLDS,
        "recommended_scope": "H600 first; H650 conditional only if H600 cannot cover enough phase diversity",
        "stage11_4a1_facts": facts,
        "run_groups": rows,
    }


def write_md(rows: list[dict[str, str]], manifest: dict[str, object]) -> None:
    lines = [
        "# Stage11-4A2 LP Fixed-Height Geometry Reconstruction Plan",
        "",
        "Planning only: no FDTD, no Lumerical, no K=6, no finite patch, no dipole, no DBR/RCLED, no H500 rescue.",
        "",
        "## Why H600 First",
        "",
        "Stage11-4A1 showed H600 is the least-bad fixed-height scout: H600 B300 kept high selectivity (ratio about 9.148, Tx about 0.957) but failed phase, while H600 B240 failed ratio/matrix/phase. H650 was worse overall, so H650 is only an escape hatch.",
        "",
        "## Why K=6 Remains Blocked",
        "",
        "No H600/H650/H700 height-scaled template produced strict or loose bins over 451/452/453 nm. K=6 remains blocked until a fixed-height six-bin LP projection-phase library exists.",
        "",
        "## Future A2 Run Groups",
        "",
        "| group | height | bins | cases | purpose |",
        "|---|---:|---|---:|---|",
    ]
    for row in rows:
        lines.append(f"| {row['group_id']} | {row['height_nm']} | {row['phase_bin_deg']} | {row['planned_cases']} | {row['purpose']} |")
    lines += [
        "",
        f"Total planned future extraction cases: {manifest['planned_future_extraction_cases']} / {manifest['hard_future_case_budget']}.",
        "",
        "## Early Stop Rules",
        "",
    ]
    for row in rows:
        lines.append(f"- {row['group_id']}: {row['early_stop_rule']}")
    lines += [
        "",
        "## Thresholds Reused From Stage11-4A1",
        "",
        "- strict: ratio >= 6, Tx >= 0.45, matrix_error <= 0.50, phase_error <= 25 deg",
        "- loose: ratio >= 3, Tx >= 0.10, matrix_error <= 1.00, phase_error <= 35 deg",
        "",
        "## Recommendation",
        "",
        "Use H600-only reconstruction first. Enable the H650 240/300 escape-hatch group only if H600 cannot produce loose 240/300 candidates. Do not start K=6 until fixed-height robust six-bin candidates exist.",
        "",
    ]
    PLAN_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    facts = a1_facts()
    rows = plan_rows()
    if total_cases(rows) > 96:
        raise RuntimeError("Stage11-4A2 plan exceeds 96 future extraction cases")
    write_csv(CANDIDATE_SPACE_CSV, rows)
    manifest = build_manifest(rows, facts)
    MANIFEST_JSON.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    SUMMARY_JSON.write_text(json.dumps({
        "stage": "Stage11-4A2",
        "planning_only": True,
        "recommended_scope": manifest["recommended_scope"],
        "planned_groups": len(rows),
        "planned_future_extraction_cases": total_cases(rows),
        "hard_future_case_budget": 96,
        "h600_only_first": True,
        "h650_conditional": True,
        "k6_blocked": True,
    }, indent=2), encoding="utf-8")
    write_md(rows, manifest)
    print(f"wrote {CANDIDATE_SPACE_CSV}")
    print(f"planned_future_extraction_cases={total_cases(rows)}")


if __name__ == "__main__":
    main()
