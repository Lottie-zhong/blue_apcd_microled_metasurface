#!/usr/bin/env python3
"""Create R2-4A variable-thickness DBR inverse-design formulation docs."""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "r2_4a_normal_rcled_variable_dbr_inverse_design_formulation"
INDEX = ROOT / "reports" / "rcled_mdc_workspace_index.md"

VARIABLE_TIERS = [
    {"tier": 1, "risk": "low", "variable": "top_pair_count", "purpose": "coarse top mirror strength and outcoupling control", "suggested_bounds": "0..12 pairs"},
    {"tier": 1, "risk": "low", "variable": "bottom_pair_count", "purpose": "coarse bottom mirror strength control", "suggested_bounds": "0..18 pairs"},
    {"tier": 1, "risk": "low", "variable": "cavity_spacer_nm", "purpose": "main cavity phase control", "suggested_bounds": "200..700 nm"},
    {"tier": 1, "risk": "low", "variable": "top_termination_nm", "purpose": "top reflection phase and extraction tuning", "suggested_bounds": "0..100 nm"},
    {"tier": 1, "risk": "low", "variable": "bottom_termination_nm", "purpose": "bottom reflection phase tuning", "suggested_bounds": "0..100 nm"},
    {"tier": 1, "risk": "low", "variable": "source_position_fraction_in_cavity", "purpose": "LDOS / standing-wave placement", "suggested_bounds": "0.2..0.8 away from interfaces"},
    {"tier": 2, "risk": "medium", "variable": "top_high_index_scale", "purpose": "top DBR phase/bandwidth tuning", "suggested_bounds": "0.75..1.25 of nominal"},
    {"tier": 2, "risk": "medium", "variable": "top_low_index_scale", "purpose": "top DBR phase/bandwidth tuning", "suggested_bounds": "0.75..1.25 of nominal"},
    {"tier": 2, "risk": "medium", "variable": "bottom_high_index_scale", "purpose": "bottom DBR phase tuning", "suggested_bounds": "0.75..1.25 of nominal"},
    {"tier": 2, "risk": "medium", "variable": "bottom_low_index_scale", "purpose": "bottom DBR phase tuning", "suggested_bounds": "0.75..1.25 of nominal"},
    {"tier": 2, "risk": "medium", "variable": "pairwise_chirp_or_apodization", "purpose": "reduce competing modes and shape stopband", "suggested_bounds": "limited monotonic or smooth factors"},
    {"tier": 3, "risk": "high", "variable": "independent_top_layer_thicknesses", "purpose": "non-periodic top reflector optimization", "suggested_bounds": "20..180 nm each"},
    {"tier": 3, "risk": "high", "variable": "independent_bottom_layer_thicknesses", "purpose": "non-periodic bottom reflector optimization", "suggested_bounds": "20..180 nm each"},
    {"tier": 3, "risk": "high", "variable": "non_quarter_wave_non_periodic_dbr", "purpose": "full 1D inverse design after lower tiers fail", "suggested_bounds": "fabrication constrained"},
]

CONSTRAINTS = [
    {"constraint": "min_dielectric_layer_nm", "value": 20, "reason": "avoid fragile or poorly controlled ultrathin layers"},
    {"constraint": "max_dielectric_layer_nm", "value": 180, "reason": "avoid impractical thick layers unless explicitly justified"},
    {"constraint": "reported_thickness_quantization_nm", "value": "1 or 2", "reason": "fabrication-friendly reporting"},
    {"constraint": "source_interface_clearance", "value": "keep away from material interfaces", "reason": "avoid unstable LDOS/interface artifacts"},
    {"constraint": "avoid_ultra_high_q_low_extraction", "value": "penalize", "reason": "narrow but dark cavities are not useful source modules"},
    {"constraint": "multi_peak_penalty", "value": "penalize", "reason": "avoid competing spectral peaks"},
    {"constraint": "offaxis_power_20_to_60_deg", "value": "penalize", "reason": "normal RCLED target rejects off-axis dominance"},
    {"constraint": "top_vs_bottom_mirror", "value": "top weaker when needed", "reason": "support upward extraction"},
    {"constraint": "total_stack_thickness", "value": "reasonable", "reason": "manufacturing and simulation cost"},
]

CANDIDATES = [
    {"candidate_id": "R2_1_00223", "implication": "rejected for normal RCLED", "status": "diagnostic_only", "reason": "symmetric +/-36 deg off-axis double-lobe in R2-2D/E/G"},
    {"candidate_id": "R2_1_00227", "implication": "deferred", "status": "too_similar_to_rejected_route", "reason": "likely same failure family as R2_1_00223"},
    {"candidate_id": "R2_1_04067", "implication": "available next smoke candidate", "status": "can_be_superseded_by_R2_4B", "reason": "different-family true two-mirror candidate"},
    {"candidate_id": "R2_1_00359", "implication": "top-filter control only", "status": "control", "reason": "not the main two-mirror normal RCLED route"},
    {"candidate_id": "R2_1_02653", "implication": "fallback/failed angular reference", "status": "reference", "reason": "not next main candidate"},
    {"candidate_id": "R2_1_02264", "implication": "deferred", "status": "high_top_mirror_extraction_risk", "reason": "postpone until safer route is checked"},
]

HIERARCHY = [
    {"stage": "R2-4A", "action": "formulation only", "solver": "none", "fdtd": False},
    {"stage": "R2-4B", "action": "TMM/STACK variable-thickness DBR optimization/screening", "solver": "TMM/STACK", "fdtd": False},
    {"stage": "R2-4C", "action": "choose 3 to 5 candidates and generate setup-only FSPs for GUI inspection", "solver": "setup only", "fdtd": False},
    {"stage": "R2-4D", "action": "run 453 nm FDTD smoke for center_x + center_z_outofplane only", "solver": "FDTD", "fdtd": True},
    {"stage": "R2-4E", "action": "if angular smoke passes, run broadband angle-resolved spectral FWHM validation", "solver": "FDTD", "fdtd": True},
    {"stage": "R2-4F", "action": "optional local adjoint or gradient refinement after near-pass", "solver": "adjoint/gradient", "fdtd": True},
]


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def append_index() -> None:
    if not INDEX.exists():
        return
    marker = "## R2-4A variable-thickness DBR formulation"
    text = INDEX.read_text(encoding="utf-8")
    if marker in text:
        return
    INDEX.write_text(text.rstrip() + f"\n\n{marker}\n\n- Formulated normal-RCLED variable-thickness DBR/cavity inverse-design route.\n- No FDTD, Lumerical, optimization, or adjoint run.\n- R2_1_04067 remains available, but R2-4B can supersede it with optimized candidates.\n- Output folder: outputs/r2_4a_normal_rcled_variable_dbr_inverse_design_formulation.\n", encoding="utf-8")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    write_csv(OUT / "r2_4a_design_variable_tiers.csv", VARIABLE_TIERS)
    write_csv(OUT / "r2_4a_fabrication_constraints.csv", CONSTRAINTS)
    write_csv(OUT / "r2_4a_candidate_implications.csv", CANDIDATES)

    write_text(OUT / "r2_4a_dbr_rcled_physics_logic.md", """
# R2-4A DBR/RCLED physics logic

DBR is not just a mirror. It provides complex reflection:

`r(lambda, theta, pol) = |r| exp(i phi)`

RCLED resonance depends on:

`2 k_z d + phi_top(lambda, theta, pol) + phi_bottom(lambda, theta, pol) = 2*pi*m`

R2_1_00223 failed because the current DBR/cavity phase selected an off-axis leaky/cavity mode near +/-36 deg instead of the normal direction. The inverse-design goal is to move the strongest real dipole-coupled cavity/outcoupling mode to lambda around 453 nm and theta near 0 deg.
""")

    write_text(OUT / "r2_4a_target_and_validation_criteria.md", """
# R2-4A target and validation criteria

Target: normal-direction RCLED source module around 453 nm for later APCD input.

Valid MQW incoherent pair: simulation_x + simulation_z_outofplane. The simulation_y cavity-normal dipole is invalid for this 2D MQW pair.

## Ideal final criteria

- incoherent peak_abs_angle_deg <= 5
- incoherent angular_FWHM_deg <= 10
- incoherent normal_offaxis_ratio > 1.5
- spectral_FWHM_nm <= 6

## Acceptable final criteria

- incoherent peak_abs_angle_deg <= 10
- incoherent angular_FWHM_deg <= 25
- incoherent normal_offaxis_ratio > 1.0
- spectral_FWHM_nm <= 8

Spectral FWHM must be evaluated in near-normal angular windows, for example |theta| <= 5 deg and |theta| <= 10 deg. Do not evaluate spectral FWHM at the rejected +/-36 deg off-axis lobe.
""")

    write_text(OUT / "r2_4a_merit_function_definition.md", """
# R2-4A merit function definition

A later TMM/STACK implementation should maximize a normal-RCLED merit proxy:

`M = positive_terms - penalty_terms`

## Positive terms

- high normal-window power near lambda = 453 nm
- high normal/off-axis ratio
- small peak_abs_angle_deg
- small angular_FWHM_deg
- small spectral_FWHM_nm in near-normal window
- adequate upward extraction proxy

## Penalty terms

- dominant peak outside |theta| <= 10 deg
- strong off-axis power in |theta| = 20 to 60 deg
- spectral peak outside 450 to 456 nm
- spectral_FWHM_nm > 8
- angular_FWHM_deg > 25
- too-high-Q / too-low-extraction designs
- layer thickness outside fabrication constraints
""")

    write_text(OUT / "r2_4a_proxy_to_fdtd_validation_hierarchy.md", """
# R2-4A proxy-to-FDTD validation hierarchy

Do not jump directly to full FDTD adjoint.

1. R2-4A: formulation only, no solver.
2. R2-4B: TMM/STACK variable-thickness DBR optimization / screening.
3. R2-4C: choose 3 to 5 candidates and generate setup-only FSPs for GUI inspection.
4. R2-4D: run 453 nm FDTD smoke for center_x + center_z_outofplane only.
5. R2-4E: only if angular smoke passes, run broadband angle-resolved spectral FWHM validation.
6. R2-4F: optional local adjoint or gradient refinement only after a near-pass candidate exists.

Why not direct adjoint first: the DBR/cavity is mostly 1D layered, so TMM/STACK is faster and more stable for initial exploration. Full FDTD adjoint for dipole angular/spectral objectives is more expensive and should be refinement, not first brute force. The R2_1_00223 failure proves plane-wave proxy is insufficient, so every optimized design still requires dipole-FDTD validation.
""")

    write_text(OUT / "r2_4a_next_steps.md", """
# R2-4A next steps

1. Keep R2_1_04067 available as the next different-family smoke candidate.
2. Prefer R2-4B TMM/STACK variable-thickness DBR screening before more manual FDTD trials.
3. Let R2-4B supersede R2_1_04067 if it finds clearly better normal-RCLED candidates.
4. Do not run off-axis spectral FWHM validation for the rejected R2_1_00223 double-lobe route.
""")

    write_text(OUT / "r2_4a_summary.md", """
# R2-4A normal-RCLED variable-thickness DBR formulation

No FDTD, Lumerical, optimization, or adjoint run was performed.

R2-4A defines a normal-direction RCLED source-module inverse-design formulation. The core physical point is that DBR phase and cavity phase determine whether the dipole-coupled mode exits near theta = 0 deg or leaks into off-axis modes. The rejected R2_1_00223 result showed a narrow symmetric +/-36 deg double-lobe, so the next main route should redesign the vertical DBR/cavity phase rather than validate that off-axis lobe further.

R2_1_04067 remains available as a different-family smoke candidate, but it can be superseded by R2-4B variable-thickness TMM/STACK candidates.
""")

    debug = {
        "stage": "R2-4A",
        "no_fdtd": True,
        "no_lumerical": True,
        "target_center_wavelength_nm": 453,
        "valid_mqw_pair": "simulation_x + simulation_z_outofplane",
        "invalid_dipole": "simulation_y cavity-normal",
        "variable_tiers": VARIABLE_TIERS,
        "constraints": CONSTRAINTS,
        "candidate_implications": CANDIDATES,
        "hierarchy": HIERARCHY,
    }
    (OUT / "r2_4a_formulation_debug.json").write_text(json.dumps(debug, indent=2), encoding="utf-8")
    append_index()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
