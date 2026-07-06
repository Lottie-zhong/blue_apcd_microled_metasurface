#!/usr/bin/env python3
"""R2-4H0 baseline pivot after proxy candidate failures.

Python-only documentation package. No Lumerical/lumapi/FDTD/FSP.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

ROOT = Path(r"D:\project\worktrees\blue_apcd_rcled_mdc")
OUT = ROOT / "outputs" / "r2_4h0_baseline_pivot_after_proxy_candidate_failures"
INPUTS = {
    "G3": ROOT / "outputs" / "r2_4g3_update_dipole_aware_proxy_thresholds_from_negative_dataset",
    "G1": ROOT / "outputs" / "r2_4g1_negative_dataset_feature_table_dipole_aware_proxy",
    "F3": ROOT / "outputs" / "r2_4f3_f0_shortlist_fdtd_failure_audit_proxy_breakdown",
    "F1": ROOT / "outputs" / "r2_4f1_f0_0781_tri_point_xdipole_fdtd_guard",
    "F2": ROOT / "outputs" / "r2_4f2_f0_0204_tri_point_xdipole_fdtd_guard",
    "E2": ROOT / "outputs" / "r2_4e2_e1_0236_tri_point_xdipole_fdtd_guard",
    "D8": ROOT / "outputs" / "r2_4d8_source_position_failure_diagnosis_proxy_redesign",
}


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    missing = [f"{k}:{v}" for k, v in INPUTS.items() if not v.exists()]

    baselines = [
        {
            "baseline_id": "Huang_RCLED_baseline",
            "source_type": "RCLED F-P cavity",
            "key_parameters": "literature RC microLED baseline; top DBR improves collimation",
            "spectral_FWHM_nm": "around 6.8",
            "divergence_deg": "around 78.7",
            "role": "reliable F-P narrow-spectrum baseline",
            "support_level": "literature experiment/simulation-supported as reported in prior RCLED notes",
            "baseline_use": "spectral-narrowing reference, not 20-deg angular claim",
        },
        {
            "baseline_id": "Lin_RCLED_baseline",
            "source_type": "manufacturable RCLED",
            "key_parameters": "m=10; bottom DBR >=10 pairs; top DBR 3-4 pairs; 160 um at 20 A/cm2",
            "spectral_FWHM_nm": "around 7.99",
            "divergence_deg": "around 66.2",
            "role": "manufacturable RCLED baseline",
            "support_level": "experiment-supported literature baseline",
            "baseline_use": "preferred practical RCLED spectral baseline",
        },
        {
            "baseline_id": "Wan_MDC_baseline",
            "source_type": "SiO2/TiO2 MDC microLED",
            "key_parameters": "blue 453 nm seed around SiO2=100 nm, TiO2=52 nm, m=8",
            "spectral_FWHM_nm": "experimental 28 to 18",
            "divergence_deg": "roughly 30 or within 60 depending context",
            "role": "MDC angular/spectral filtering baseline",
            "support_level": "experiment-supported MDC baseline with context-dependent angular result",
            "baseline_use": "angular/spectral filtering reference, not final APCD source claim",
        },
    ]
    write_csv(OUT / "r2_4h0_senior_baseline_table.csv", baselines)

    routes = [
        {
            "route_id": "A",
            "route_name": "Lin_RCLED_baseline_to_APCD_later",
            "pros": "8 nm spectral width; mature process; practical RCLED source baseline",
            "cons": "angular divergence still around 66 deg",
            "immediate_role": "baseline candidate for source-module narrative",
            "immediate_FDTD_allowed": "no",
        },
        {
            "route_id": "B",
            "route_name": "Wan_MDC_baseline_to_APCD_later",
            "pros": "angular filtering closer to RCLED-MDC source-module concept",
            "cons": "experimental spectrum around 18 nm, not 10 nm",
            "immediate_role": "MDC filtering baseline candidate",
            "immediate_FDTD_allowed": "no",
        },
        {
            "route_id": "C",
            "route_name": "RCLED_plus_MDC_combined_future_route",
            "pros": "full source-module story if later validated",
            "cons": "highest complexity; current self-generated candidates failed",
            "immediate_role": "future integration route, not immediate mainline",
            "immediate_FDTD_allowed": "no",
        },
        {
            "route_id": "D",
            "route_name": "keep_20deg_as_exploratory_simulation_target_only",
            "pros": "preserves ambitious target for later research",
            "cons": "not supported as current baseline claim",
            "immediate_role": "exploratory target only",
            "immediate_FDTD_allowed": "no",
        },
    ]
    write_csv(OUT / "r2_4h0_route_options.csv", routes)

    write_text(OUT / "r2_4h0_stop_g4_decision.md", """
# R2-4H0 Stop G4 Decision

Decision: stop G4 for now.

Rules:
- do not generate new proxy candidates;
- do not FDTD old candidates;
- keep D5_BASE_13461 stopped;
- keep E1_0236 stopped;
- keep F0_0781 stopped;
- keep F0_0204 stopped;
- do not continue blind candidate generation for 20 deg angular target.
""")

    write_text(OUT / "r2_4h0_failed_candidate_scientific_diagnosis.md", """
# R2-4H0 Failed Candidate Scientific Diagnosis

RCLED/MDC remains scientifically reasonable: literature supports Fabry-Perot spectral narrowing, DBR-assisted RCLED source modules, and SiO2/TiO2 MDC filtering near blue wavelengths.

The self-generated candidates failed because the current 1D stack/MDC Python proxy does not model finite MQW dipole-coupled off-axis and leaky/guided channels. It can rank spectral or plane-wave angular behavior, but it missed dipole-to-farfield coupling in D5, E1_0236, F0_0781, and F0_0204.

Spectral narrowing is easier and literature-supported. Angular narrowing to 20 deg is not yet supported by the current nonpolarized RCLED/MDC candidate search.
""")

    write_text(OUT / "r2_4h0_revised_target_hierarchy.md", """
# R2-4H0 Revised Target Hierarchy

Baseline target:
- spectral FWHM: use literature values, roughly 8-18 nm depending route;
- angular divergence: use literature values, roughly 30-70 deg depending route.

Exploratory target:
- spectral FWHM <= 10 nm;
- angular divergence or FWHM 20-30 deg.

Final APCD target:
- evaluate whether a narrower source improves CP/LP selectivity and directionality after APCD coupling.

Important: 20 deg is no longer mandatory for the current baseline claim. It remains an exploratory simulation target only.
""")

    write_text(OUT / "r2_4h0_recommended_h1_h2_plan.md", """
# R2-4H0 Recommended H1/H2 Plan

Recommended H1 task name:
`R2-4H1_choose_senior_literature_baseline_route_and_encode_parameters`

H1 should choose one baseline route and encode baseline parameters without FDTD.

Recommended H2 task name:
`R2-4H2_optional_lightweight_baseline_reproduction_sanity_model`

H2 is optional and requires explicit user approval. It may define a lightweight reproduction or sanity model, but H0 does not authorize immediate FDTD.

Recommended H3 direction:
`R2-4H3_APCD_coupling_narrative_and_experiment_simulation_plan`

H3 should plan how the chosen baseline source would be evaluated in APCD coupling later.
""")

    write_text(OUT / "r2_4h0_stop_allow_rules.md", """
# R2-4H0 Stop / Allow Rules

Stop:
- G4 candidate generator for now;
- direct FDTD from failed proxy routes;
- D5_BASE_13461, E1_0236, F0_0781, F0_0204 revival.

Allow:
- H1 route selection and baseline parameter encoding;
- H2 optional lightweight reproduction/sanity model only after explicit approval;
- H3 APCD coupling narrative and simulation plan.

Immediate FDTD: no.
Push: no.
""")

    write_text(OUT / "r2_4h0_summary.md", """
# R2-4H0 Baseline Pivot After Proxy Candidate Failures

H0 freezes the failed self-generated candidate search and pivots the RCLED/MDC source-module route toward senior/literature baseline selection.

One-line conclusion: stop G4 and use literature/senior RCLED or MDC baselines as the realistic source-module route before any further FDTD.

Immediate FDTD: no.
Recommended H1 task: `R2-4H1_choose_senior_literature_baseline_route_and_encode_parameters`.
""")

    write_json(OUT / "r2_4h0_manifest.json", {
        "stage": "R2-4H0 baseline pivot after proxy candidate failures",
        "python_only": True,
        "no_lumerical": True,
        "no_lumapi": True,
        "no_fdtd": True,
        "stop_G4": True,
        "stopped_candidates": ["D5_BASE_13461", "E1_0236", "F0_0781", "F0_0204"],
        "inputs": {k: str(v) for k, v in INPUTS.items()},
        "missing_inputs": missing,
        "recommended_H1_task": "R2-4H1_choose_senior_literature_baseline_route_and_encode_parameters",
        "immediate_fdtd_allowed": False,
        "outputs": [
            "r2_4h0_summary.md",
            "r2_4h0_stop_g4_decision.md",
            "r2_4h0_failed_candidate_scientific_diagnosis.md",
            "r2_4h0_senior_baseline_table.csv",
            "r2_4h0_route_options.csv",
            "r2_4h0_revised_target_hierarchy.md",
            "r2_4h0_recommended_h1_h2_plan.md",
            "r2_4h0_stop_allow_rules.md",
            "r2_4h0_manifest.json",
        ],
    })

    print(json.dumps({"output": str(OUT), "baseline_rows": len(baselines), "route_rows": len(routes), "missing": missing}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
