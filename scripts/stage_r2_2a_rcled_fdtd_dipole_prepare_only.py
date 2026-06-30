#!/usr/bin/env python3
"""Prepare-only package for R2-2A 2D FDTD dipole validation.

This script writes manifests and docs only. It must not import lumapi, create
FSP/LDF files, or launch Lumerical/FDTD.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "r2_2a_rcled_fdtd_dipole_prepare_only"
R2_1B = ROOT / "outputs" / "r2_1b_rcled_highres_tmm_shortlist_verify" / "r2_1b_fdtd_recommendation.csv"
INDEX = ROOT / "reports" / "rcled_mdc_workspace_index.md"

PRIMARY_IDS = ["R2_1_00227", "R2_1_00223", "R2_1_04067"]
CONTROL_IDS = ["R2_1_00359", "R2_1_02653"]
WAVELENGTH_NM = 453
DIPOLES = ["x", "y"]

METRIC_DEFS = [
    ("spectral_FWHM_nm", "Full width at half maximum of spectral response near 453 nm."),
    ("angular_FWHM_deg", "Angular full width at half maximum at 453 nm."),
    ("peak_abs_angle_deg", "Absolute value of the peak emission angle."),
    ("eta5/eta10/eta20/eta30", "Cone collection efficiencies within +/-5, +/-10, +/-20, +/-30 deg."),
    ("I_normal_0_5deg", "Integrated or averaged intensity proxy over 0-5 deg."),
    ("I_offaxis_20_30deg", "Integrated or averaged intensity proxy over 20-30 deg."),
    ("normal_offaxis_ratio", "I_normal_0_5deg / I_offaxis_20_30deg."),
    ("x/y incoherent average", "Add x- and y-dipole powers only; do not add fields coherently."),
]

SUCCESS = {
    "angular_FWHM_deg": {"ideal": "<=10", "acceptable": "<=25"},
    "peak_abs_angle_deg": {"ideal": "<=5", "acceptable": "<=10"},
    "normal_offaxis_ratio": {"ideal": ">1.5", "acceptable": ">1"},
    "spectral_FWHM_nm": {"ideal": "<=6", "acceptable": "<=8"},
}


def read_r2_1b() -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    if not R2_1B.exists():
        raise FileNotFoundError(f"Missing R2-1B recommendation CSV: {R2_1B}")
    with R2_1B.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    by_id = {r["candidate_id"]: r for r in rows}
    missing = [cid for cid in PRIMARY_IDS + CONTROL_IDS if cid not in by_id]
    if missing:
        raise ValueError(f"Missing expected candidate rows in R2-1B CSV: {missing}")
    return [by_id[cid] for cid in PRIMARY_IDS], [by_id[cid] for cid in CONTROL_IDS]


def slim_candidate(row: dict[str, str]) -> dict[str, str]:
    keys = [
        "candidate_id", "role", "family", "cavity_validity_class",
        "top_pair_count", "bottom_pair_count", "cavity_span_nm", "termination",
        "spectral_FWHM_nm_at_theta0_interpolated",
        "angular_FWHM_deg_at_453_interpolated",
        "peak_abs_angle_deg_at_453", "normal_offaxis_ratio_at_453",
        "top_mirror_extraction_risk", "highres_pass_level",
    ]
    return {k: row.get(k, "") for k in keys}


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def build_manifest(primary: list[dict[str, str]]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    run_index = 1
    for cand in primary:
        for dipole in DIPOLES:
            rows.append({
                "run_index": run_index,
                "case_id": f"R2_2A_{cand['candidate_id']}_453_center_{dipole}",
                "candidate_id": cand["candidate_id"],
                "family": cand.get("family", ""),
                "top_pair_count": cand.get("top_pair_count", ""),
                "bottom_pair_count": cand.get("bottom_pair_count", ""),
                "cavity_span_nm": cand.get("cavity_span_nm", ""),
                "termination": cand.get("termination", ""),
                "wavelength_nm": WAVELENGTH_NM,
                "source_position": "center",
                "source_x_nm": 0,
                "source_y_offset_nm": 0,
                "dipole_orientation": dipole,
                "simulation_dimensionality": "2D",
                "later_combination": "incoherent_power_average",
                "status": "planned_not_run",
                "no_fdtd_in_this_stage": True,
            })
            run_index += 1
    return rows


def reuse_audit() -> str:
    candidates = []
    for path in sorted((ROOT / "scripts").glob("stage_r*.py")):
        name = path.name.lower()
        if any(token in name for token in ["r1c1", "r1c2", "r1c4", "r2_1"]):
            candidates.append(path.name)
    lines = [
        "# R2-2A Reuse Audit", "",
        "No script was imported or executed for FDTD. This is a prepare-only audit.", "",
        "Likely reusable pieces for the later R2-2 FDTD runner:",
    ]
    lines += [f"- `{name}`" for name in candidates]
    lines += [
        "", "Reuse candidates should be checked later for:",
        "- 2D simulation mapping and physical x/y dipole orientation handling.",
        "- vertical stack construction from top/bottom pair counts and cavity_span_nm.",
        "- angular extraction at 453 nm and x/y incoherent power averaging.",
        "", "Safety marker: no lumapi import, no FDTD solve, no .fsp/.ldf generation in R2-2A.",
    ]
    return "\n".join(lines)


def update_index() -> None:
    marker = "## R2-2A FDTD Dipole Prepare-Only Package"
    block = f"""
{marker}

- Output: `outputs/r2_2a_rcled_fdtd_dipole_prepare_only`
- No FDTD run; no Lumerical launched; no `.fsp`/`.ldf` generated.
- Planned first-run cases: 3 R2 primary candidates x 2 dipole orientations = 6 cases.
- Candidates: R2_1_00227, R2_1_00223, R2_1_04067.
- Planned wavelength/source: 453 nm, center source only, x/y dipoles separately.
- Main validation target: narrow near-normal emission, not eta20/eta30 alone.
""".strip()
    old = INDEX.read_text(encoding="utf-8") if INDEX.exists() else "# RCLED MDC Workspace Index\n"
    if marker in old:
        old = old.split(marker)[0].rstrip()
    write_text(INDEX, old.rstrip() + "\n\n" + block)


def main() -> None:
    primary, controls = read_r2_1b()
    OUT.mkdir(parents=True, exist_ok=True)

    geometry = [slim_candidate(row) | {"first_run_batch": "yes"} for row in primary]
    geometry += [slim_candidate(row) | {"first_run_batch": "no_control_only"} for row in controls]
    manifest = build_manifest(primary)

    write_csv(OUT / "r2_2a_candidate_geometry_summary.csv", geometry)
    write_csv(OUT / "r2_2a_case_manifest.csv", manifest)
    (OUT / "r2_2a_case_manifest.json").write_text(json.dumps({
        "stage": "R2-2A_RCLED_FDTD_dipole_prepare_only",
        "no_fdtd_run": True,
        "no_lumerical_launch": True,
        "planned_case_count": len(manifest),
        "cases": manifest,
        "success_conditions": SUCCESS,
        "controls_recorded_not_in_first_batch": [slim_candidate(row) for row in controls],
    }, indent=2), encoding="utf-8")

    metric_lines = ["# R2-2A Metric Definitions", "", "Later extraction must report:"]
    metric_lines += [f"- `{name}`: {desc}" for name, desc in METRIC_DEFS]
    metric_lines += ["", "Success bands:"]
    for key, bands in SUCCESS.items():
        metric_lines.append(f"- `{key}`: ideal {bands['ideal']}; acceptable {bands['acceptable']}.")
    metric_lines += ["", "Do not use eta20/eta30 alone as success criteria."]
    write_text(OUT / "r2_2a_metric_definitions.md", "\n".join(metric_lines))

    order_lines = ["# R2-2A Planned Run Order", "", "Run only after explicit approval:", ""]
    order_lines += [f"{row['run_index']}. `{row['case_id']}`" for row in manifest]
    order_lines += ["", "Do not add source-y offsets, wavelength sweeps, or control candidates to the first run batch."]
    write_text(OUT / "r2_2a_run_order.md", "\n".join(order_lines))
    write_text(OUT / "r2_2a_reuse_audit.md", reuse_audit())

    summary = f"""
# R2-2A Prepare-Only Package

This package prepares the first 2D FDTD dipole validation plan for the three primary R2 RCLED source-module candidates from R2-1B.

No FDTD was run. Lumerical was not launched. No `.fsp`, `.ldf`, or raw monitor data were created.

## Planned first-run cases

- Candidates: `R2_1_00227`, `R2_1_00223`, `R2_1_04067`
- Wavelength: 453 nm only
- Source position: center only
- Dipoles: x and y separately
- Total planned cases: {len(manifest)}

## Controls recorded but not included

- `R2_1_00359`: top-filter control, not a true RCLED cavity.
- `R2_1_02653`: C2 fallback control, high-resolution angular FWHM failed.

## Success logic for later FDTD

The target is narrow near-normal emission. eta20/eta30 alone is not enough.

- angular_FWHM <= 10 deg ideal, <= 25 deg acceptable
- peak_abs_angle <= 5 deg ideal, <= 10 deg acceptable
- normal/offaxis ratio > 1.5 ideal, > 1 acceptable
- spectral FWHM <= 6 nm ideal, <= 8 nm acceptable

## Open mapping uncertainty

The main uncertainty is converting TMM `cavity_span_nm` into the exact FDTD vertical GaN/cavity geometry while preserving clean interfaces and the prior 2D mapping. The later FDTD runner should explicitly audit vertical layer placement before solving.
"""
    write_text(OUT / "r2_2a_summary.md", summary)

    next_steps = """
# R2-2A Next Steps

1. Review this prepare-only manifest.
2. If approved, create R2-2B 2D FDTD runner for only the six planned cases.
3. Before any solve, audit vertical mapping from TMM cavity_span_nm into FDTD geometry.
4. Extract x/y dipoles separately and combine powers incoherently.
5. Add controls only after the primary three candidates are understood.
"""
    write_text(OUT / "r2_2a_next_steps.md", next_steps)
    update_index()

    print(f"wrote {OUT}")
    print(f"planned_cases={len(manifest)}")


if __name__ == "__main__":
    main()
