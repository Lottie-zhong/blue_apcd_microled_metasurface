#!/usr/bin/env python3
"""R2-4D8 source-position failure diagnosis and proxy redesign.

Python-only: reads existing R2-4D7 CSV/JSON/MD outputs. It must not import
lumapi, open runtime FSP files, run FDTD, or generate any heavy simulation data.
"""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from statistics import mean, pstdev

ROOT = Path(r"D:\project\worktrees\blue_apcd_rcled_mdc")
D7 = ROOT / "outputs" / "r2_4d7_xline_xdipole_fdtd_scout_d5_primary"
OUT = ROOT / "outputs" / "r2_4d8_source_position_failure_diagnosis_proxy_redesign"
SCRIPT_NAME = "stage_r2_4d8_source_position_failure_diagnosis_proxy_redesign.py"
STAGE = "R2-4D8 source-position failure diagnosis / proxy redesign"
CANDIDATE = "D5_BASE_13461"

REQUIRED_D7 = [
    "r2_4d7_case_metrics.csv",
    "r2_4d7_xline_average_metrics.csv",
    "r2_4d7_source_position_robustness.csv",
    "r2_4d7_summary.md",
]
CASE_COLS = [
    "source_x_um",
    "peak_abs_angle_deg",
    "signed_peak_angle_deg",
    "angular_FWHM_deg",
    "eta5",
    "eta10",
    "eta20",
    "eta30",
    "normal_offaxis_ratio",
    "offaxis_20_60_response",
    "offaxis_30_40_response",
    "status",
    "error_message",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def write_json(path: Path, obj: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def f(row: dict[str, str], key: str) -> float:
    val = row.get(key, "")
    if val in ("", "missing", None):
        return math.nan
    try:
        return float(val)
    except ValueError:
        return math.nan


def safe(row: dict[str, str], key: str) -> object:
    return row[key] if key in row and row[key] != "" else "missing"


def require_inputs() -> None:
    missing = [str(D7 / name) for name in REQUIRED_D7 if not (D7 / name).exists()]
    if missing:
        raise FileNotFoundError("Missing D7 outputs: " + "; ".join(missing))
    runtime_fsp = D7 / "runtime_solve_fsp"
    if runtime_fsp.exists():
        # Deliberately do not read anything inside it. This records the boundary only.
        pass


def source_failure_table(case_rows: list[dict[str, str]]) -> list[dict[str, object]]:
    out = []
    for row in sorted(case_rows, key=lambda r: f(r, "source_x_um")):
        peak = f(row, "peak_abs_angle_deg")
        ratio = f(row, "normal_offaxis_ratio")
        off30 = f(row, "offaxis_30_40_response")
        normal = f(row, "normal_0_5_response")
        risk_flags = []
        if not math.isnan(peak) and 30 <= peak <= 40:
            risk_flags.append("30_40_lobe")
        if not math.isnan(ratio) and ratio < 1:
            risk_flags.append("normal_offaxis_below_1")
        if not math.isnan(off30) and not math.isnan(normal) and off30 > normal:
            risk_flags.append("off30_40_exceeds_normal")
        out.append({
            "candidate_id": safe(row, "candidate_id"),
            "source_x_um": safe(row, "source_x_um"),
            "peak_abs_angle_deg": safe(row, "peak_abs_angle_deg"),
            "signed_peak_angle_deg": safe(row, "signed_peak_angle_deg"),
            "angular_FWHM_deg": safe(row, "angular_FWHM_deg"),
            "eta5": safe(row, "eta5"),
            "eta10": safe(row, "eta10"),
            "eta20": safe(row, "eta20"),
            "eta30": safe(row, "eta30"),
            "normal_offaxis_ratio": safe(row, "normal_offaxis_ratio"),
            "offaxis_20_60_response": safe(row, "offaxis_20_60_response"),
            "offaxis_30_40_response": safe(row, "offaxis_30_40_response"),
            "status": safe(row, "status"),
            "error_message": safe(row, "error_message"),
            "risk_flags": ";".join(risk_flags) if risk_flags else "none",
        })
    return out


def find_center(case_rows: list[dict[str, str]]) -> dict[str, str]:
    return min(case_rows, key=lambda r: abs(f(r, "source_x_um")))


def summarize_instability(case_rows: list[dict[str, str]], robustness: dict[str, str]) -> dict[str, object]:
    peaks = [f(r, "peak_abs_angle_deg") for r in case_rows if not math.isnan(f(r, "peak_abs_angle_deg"))]
    ratios = [f(r, "normal_offaxis_ratio") for r in case_rows if not math.isnan(f(r, "normal_offaxis_ratio"))]
    return {
        "peak_abs_min_deg": min(peaks) if peaks else "missing",
        "peak_abs_max_deg": max(peaks) if peaks else "missing",
        "peak_abs_std_deg": pstdev(peaks) if len(peaks) > 1 else 0.0,
        "normal_offaxis_min": min(ratios) if ratios else "missing",
        "normal_offaxis_mean": mean(ratios) if ratios else "missing",
        "edge_unstable_flag": robustness.get("edge_dominated_or_unstable", "missing"),
        "solved_case_count": robustness.get("solved_case_count", "missing"),
        "failed_case_count": robustness.get("failed_case_count", "missing"),
    }


def proxy_terms() -> list[dict[str, object]]:
    return [
        {
            "term": "source_position_stability_penalty",
            "purpose": "Reject candidates whose peak angle or normal/offaxis ratio varies strongly over x-line source positions.",
            "proxy_measure": "std(peak_abs_angle over x positions) + penalty for min(normal/offaxis)<1",
            "why_needed_from_D7": "Center source looked near-normal but x-line ensemble failed.",
            "priority": "P0",
        },
        {
            "term": "edge_sensitivity_penalty",
            "purpose": "Penalize designs where near-edge source positions dominate or revive off-axis lobes.",
            "proxy_measure": "max edge peak_abs angle and edge/center normal_offaxis degradation",
            "why_needed_from_D7": "x=+/-0.70 um revived about 38.9 deg peaks; edge/unstable flag true.",
            "priority": "P0",
        },
        {
            "term": "30_40_deg_lobe_penalty",
            "purpose": "Directly suppress the known 30-40 degree off-axis failure channel.",
            "proxy_measure": "integrated response in |theta|=30-40 deg relative to 0-5 deg",
            "why_needed_from_D7": "Several source positions re-excited 30-40 deg lobes.",
            "priority": "P0",
        },
        {
            "term": "center_vs_xline_mismatch_penalty",
            "purpose": "Prevent a center-only proxy from overclaiming ensemble behavior.",
            "proxy_measure": "abs(center peak_abs - xline-average peak_abs) + ratio(center normal/offaxis / xline normal/offaxis)",
            "why_needed_from_D7": "Center peak was ~0 deg, but x-line average peak was ~14 deg and normal/offaxis was 0.18.",
            "priority": "P0",
        },
        {
            "term": "TE_TM_offaxis_risk_guard",
            "purpose": "Keep the existing TE/TM off-axis phase-risk guard as a prefilter, but do not let it replace source-position checks.",
            "proxy_measure": "TE/TM phase error margin at 20-60 deg and especially 30-40 deg",
            "why_needed_from_D7": "D5A risk looked localized enough, but FDTD source-position ensemble still failed.",
            "priority": "P1",
        },
    ]


def main() -> int:
    require_inputs()
    OUT.mkdir(parents=True, exist_ok=True)
    case_rows = read_csv(D7 / "r2_4d7_case_metrics.csv")
    avg_rows = read_csv(D7 / "r2_4d7_xline_average_metrics.csv")
    robust_rows = read_csv(D7 / "r2_4d7_source_position_robustness.csv")
    avg = avg_rows[0] if avg_rows else {}
    robustness = robust_rows[0] if robust_rows else {}
    center = find_center(case_rows)
    table = source_failure_table(case_rows)
    instability = summarize_instability(case_rows, robustness)

    center_peak = f(center, "peak_abs_angle_deg")
    avg_peak = f(avg, "peak_abs_angle_deg")
    center_ratio = f(center, "normal_offaxis_ratio")
    avg_ratio = f(avg, "normal_offaxis_ratio")
    mismatch = {
        "center_source_x_um": f(center, "source_x_um"),
        "center_peak_abs_angle_deg": center_peak,
        "xline_average_peak_abs_angle_deg": avg_peak,
        "delta_peak_abs_angle_deg": avg_peak - center_peak if not math.isnan(center_peak) and not math.isnan(avg_peak) else "missing",
        "center_normal_offaxis_ratio": center_ratio,
        "xline_average_normal_offaxis_ratio": avg_ratio,
        "normal_offaxis_ratio_drop": center_ratio - avg_ratio if not math.isnan(center_ratio) and not math.isnan(avg_ratio) else "missing",
        "xline_scout_verdict": avg.get("scout_verdict", "missing"),
    }

    write_csv(OUT / "r2_4d8_source_position_failure_table.csv", table)
    write_csv(OUT / "r2_4d8_proxy_redesign_terms.csv", proxy_terms())

    write_text(OUT / "r2_4d8_center_vs_xline_failure_diagnosis.md", f"""
# R2-4D8 Center-vs-X-Line Failure Diagnosis

D7 shows that center-only behavior is not representative for `{CANDIDATE}`.

| quantity | center source | x-line average |
|---|---:|---:|
| peak_abs_angle_deg | {mismatch['center_peak_abs_angle_deg']} | {mismatch['xline_average_peak_abs_angle_deg']} |
| normal/offaxis ratio | {mismatch['center_normal_offaxis_ratio']} | {mismatch['xline_average_normal_offaxis_ratio']} |
| eta20 | {safe(center, 'eta20')} | {safe(avg, 'eta20')} |
| eta30 | {safe(center, 'eta30')} | {safe(avg, 'eta30')} |

The center source is near-normal, but the x-line ensemble is not. Some x positions revive the 30-40 deg off-axis lobe, and the averaged normal/offaxis ratio remains below 1. Therefore the old center-only proxy failed because it optimized a single local source condition instead of source-position stability.
""")

    write_text(OUT / "r2_4d8_next_route_decision.md", f"""
# R2-4D8 Next Route Decision

Decision: stop `{CANDIDATE}` FDTD expansion.

- No y-dipole validation for D5.
- No z_outofplane validation for D5.
- No broadband validation for D5.
- No backup-candidate FDTD until a Python-only proxy redesign produces a justified shortlist.
- Next route: new stack/design-family search or limited FDTD-in-loop only after the proxy includes source-position stability, edge sensitivity, center-vs-xline mismatch, and 30-40 deg lobe penalties.
""")

    write_text(OUT / "r2_4d8_summary.md", f"""
# R2-4D8 Source-Position Failure Diagnosis / Proxy Redesign

Python-only diagnosis using existing R2-4D7 outputs. No Lumerical, lumapi, FDTD, FSP generation, or runtime FSP reads were used.

## D7 Diagnosis

- Candidate: `{CANDIDATE}`.
- D7 x-line x-dipole verdict: `{avg.get('scout_verdict', 'missing')}`.
- Center source peak_abs_angle_deg: {mismatch['center_peak_abs_angle_deg']}.
- X-line average peak_abs_angle_deg: {mismatch['xline_average_peak_abs_angle_deg']}.
- X-line average angular_FWHM_deg: {safe(avg, 'angular_FWHM_deg')}.
- Center normal/offaxis ratio: {mismatch['center_normal_offaxis_ratio']}.
- X-line average normal/offaxis ratio: {mismatch['xline_average_normal_offaxis_ratio']}.
- Source-position instability: peak_abs min/max/std = {instability['peak_abs_min_deg']} / {instability['peak_abs_max_deg']} / {instability['peak_abs_std_deg']} deg.
- normal/offaxis min/mean = {instability['normal_offaxis_min']} / {instability['normal_offaxis_mean']}.
- edge/unstable flag: {instability['edge_unstable_flag']}.

## One-line conclusion

`{CANDIDATE}` failed because center-source near-normal behavior does not survive the x-line source-position ensemble; off-axis 30-40 deg channels are re-excited away from center.
""")

    manifest = {
        "stage": STAGE,
        "candidate_id": CANDIDATE,
        "python_only": True,
        "lumapi_used": False,
        "fdtd_run": False,
        "fsp_read": False,
        "input_folder": str(D7),
        "output_folder": str(OUT),
        "required_inputs": REQUIRED_D7,
        "center_vs_xline": mismatch,
        "instability": instability,
        "route_decision": "stop_D5_FDTD_expansion_and_redesign_proxy",
        "generated_files": [
            "r2_4d8_summary.md",
            "r2_4d8_source_position_failure_table.csv",
            "r2_4d8_center_vs_xline_failure_diagnosis.md",
            "r2_4d8_proxy_redesign_terms.csv",
            "r2_4d8_next_route_decision.md",
            "r2_4d8_manifest.json",
        ],
    }
    write_json(OUT / "r2_4d8_manifest.json", manifest)
    print(json.dumps({"output": str(OUT), "one_line_conclusion": f"{CANDIDATE} fails because center-only near-normal emission collapses under x-line source-position averaging."}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
