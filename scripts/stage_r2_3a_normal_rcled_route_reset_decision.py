#!/usr/bin/env python3
"""Create R2-3A normal-RCLED route reset and next-candidate decision package."""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "r2_3a_normal_rcled_route_reset_decision"
INDEX = ROOT / "reports" / "rcled_mdc_workspace_index.md"

DECISIONS = [
    {
        "candidate_id": "R2_1_00223",
        "role": "rejected_normal_rcled",
        "decision": "reject_for_normal_rcled",
        "reason": "R2-2D failed normal criteria; R2-2E/R2-2G show symmetric +/-36 deg off-axis double-lobe with ~4.45 deg lobe FWHM.",
        "next_action": "diagnostic_only_no_offaxis_spectral_fwhm",
    },
    {
        "candidate_id": "R2_1_00227",
        "role": "deferred_similar_family",
        "decision": "defer",
        "reason": "Too similar to R2_1_00223; not the best next spend after the 00223 off-axis failure mode.",
        "next_action": "hold_until_different_family_candidates_are_checked",
    },
    {
        "candidate_id": "R2_1_04067",
        "role": "next_normal_rcled_smoke_candidate",
        "decision": "select_next",
        "reason": "Different-family true two-mirror candidate; best chance to test whether the off-axis failure is specific to the 00223-like route.",
        "next_action": "prepare minimal x_plus_z_outofplane 453 nm FDTD smoke when explicitly requested",
    },
    {
        "candidate_id": "R2_1_00359",
        "role": "top_filter_only_control",
        "decision": "keep_as_control",
        "reason": "Useful control for top-filter-only behavior, but not the main normal-RCLED source-module route.",
        "next_action": "do_not_run_before_main_two_mirror_check",
    },
    {
        "candidate_id": "R2_1_02653",
        "role": "fallback_failed_angular_reference",
        "decision": "keep_as_reference",
        "reason": "Fallback/failed angular reference, not the next main candidate.",
        "next_action": "use_for_comparison_only",
    },
    {
        "candidate_id": "R2_1_02264",
        "role": "deferred_high_extraction_risk",
        "decision": "defer",
        "reason": "High top-mirror extraction risk; postpone until a safer normal-RCLED check is completed.",
        "next_action": "defer",
    },
]

NEXT = [
    {
        "stage": "R2-3B_or_next_explicit_smoke",
        "candidate_id": "R2_1_04067",
        "run_type": "minimal_2d_fdtd_smoke_when_requested",
        "wavelength_nm": 453,
        "dipole_pair": "simulation_x + simulation_z_outofplane",
        "do_not_run_now": True,
        "selection_reason": "Different-family true two-mirror candidate, unlike R2_1_00223/R2_1_00227.",
    }
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
    marker = "## R2-3A normal-RCLED route reset"
    text = INDEX.read_text(encoding="utf-8")
    if marker in text:
        return
    INDEX.write_text(text.rstrip() + f"\n\n{marker}\n\n- R2_1_00223 rejected for normal RCLED after symmetric +/-36 deg off-axis double-lobe result.\n- Off-axis route marked diagnostic only; R2-2H off-axis spectral FWHM validation canceled.\n- Next normal-RCLED smoke candidate selected: R2_1_04067.\n- Output folder: outputs/r2_3a_normal_rcled_route_reset_decision.\n", encoding="utf-8")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    write_csv(OUT / "r2_3a_candidate_decision_table.csv", DECISIONS)
    write_csv(OUT / "r2_3a_next_candidate_manifest.csv", NEXT)

    write_text(OUT / "r2_3a_normal_source_criteria.md", """
# R2-3A normal-source criteria

## Ideal

- incoherent peak_abs_angle_deg <= 5
- incoherent angular_FWHM_deg <= 10
- incoherent normal_offaxis_ratio > 1.5
- spectral_FWHM_nm <= 6

## Acceptable

- incoherent peak_abs_angle_deg <= 10
- incoherent angular_FWHM_deg <= 25
- incoherent normal_offaxis_ratio > 1.0
- spectral_FWHM_nm <= 8

Spectral FWHM must be evaluated in a near-normal angular window such as |theta| <= 5 deg and/or |theta| <= 10 deg, not at the +/-36 deg off-axis lobes.
""")

    write_text(OUT / "r2_3a_rejected_offaxis_result_note.md", """
# R2-3A rejected off-axis result note

R2_1_00223 failed the normal RCLED source-module route. R2-2E/R2-2G showed the failure mode is a symmetric +/-36 deg off-axis double-lobe with lobe FWHM about 4.45 deg.

This is diagnostic only for the current normal-RCLED route. It should not be promoted to the main route, and R2-2H off-axis spectral FWHM validation is canceled.
""")

    write_text(OUT / "r2_3a_next_steps.md", """
# R2-3A next steps

1. Do not continue off-axis spectral FWHM validation for R2_1_00223.
2. Do not run R2_1_00227 next because it is too similar to R2_1_00223.
3. Use R2_1_04067 as the next normal-RCLED FDTD smoke candidate when a solve is explicitly requested.
4. Keep R2_1_00359 as top-filter-only control, R2_1_02653 as fallback/failed angular reference, and R2_1_02264 deferred for top-mirror extraction risk.
""")

    write_text(OUT / "r2_3a_summary.md", """
# R2-3A normal-RCLED route reset

No FDTD or Lumerical run was performed.

## Decision

R2_1_00223 is rejected for the normal-direction RCLED source-module route. Its R2-2D/R2-2E/R2-2G result is useful as a diagnostic off-axis double-lobe observation only, not as the main source-module target.

## Canceled path

R2-2H off-axis spectral FWHM validation is canceled. The main target remains near-normal RCLED emission with near-normal spectral FWHM.

## Next candidate

R2_1_04067 is selected as the next normal-RCLED FDTD smoke candidate because it is a different-family true two-mirror candidate. This is the shortest useful check after the R2_1_00223-like route produced symmetric off-axis lobes.
""")

    (OUT / "r2_3a_decision_debug.json").write_text(json.dumps({"decisions": DECISIONS, "next": NEXT}, indent=2), encoding="utf-8")
    append_index()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
