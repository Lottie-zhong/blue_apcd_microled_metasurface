#!/usr/bin/env python3
"""R2-4G3 update dipole-aware proxy thresholds from negative dataset.

Python-only reject/risk proxy definition. No Lumerical/lumapi/FDTD/FSP.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

ROOT = Path(r"D:\project\worktrees\blue_apcd_rcled_mdc")
OUT = ROOT / "outputs" / "r2_4g3_update_dipole_aware_proxy_thresholds_from_negative_dataset"
INPUTS = {
    "G1": ROOT / "outputs" / "r2_4g1_negative_dataset_feature_table_dipole_aware_proxy",
    "G0": ROOT / "outputs" / "r2_4g0_dipole_aware_proxy_spec_minimal_validation_plan",
    "F3": ROOT / "outputs" / "r2_4f3_f0_shortlist_fdtd_failure_audit_proxy_breakdown",
    "F1": ROOT / "outputs" / "r2_4f1_f0_0781_tri_point_xdipole_fdtd_guard",
    "F2": ROOT / "outputs" / "r2_4f2_f0_0204_tri_point_xdipole_fdtd_guard",
    "E2": ROOT / "outputs" / "r2_4e2_e1_0236_tri_point_xdipole_fdtd_guard",
    "D8": ROOT / "outputs" / "r2_4d8_source_position_failure_diagnosis_proxy_redesign",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


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
    missing_inputs = [f"{k}:{v}" for k, v in INPUTS.items() if not v.exists()]
    negatives = read_csv(INPUTS["G1"] / "r2_4g1_unified_negative_dataset.csv")
    features = read_csv(INPUTS["G1"] / "r2_4g1_dipole_aware_feature_table.csv")

    failure_modes = [
        {
            "candidate_id": "D5_BASE_13461",
            "failure_mode": "center_only_false_positive / source_position_instability / 30-40_deg_lobe",
            "proxy_red_flags": "center_only_false_positive_flag;source_position_instability_flag;thirty_forty_lobe_failure_flag",
            "required_reject_rules": "reject center-only verdict; require tri-point; reject dominant 30-40 lobe",
            "status": "stopped",
        },
        {
            "candidate_id": "E1_0236",
            "failure_mode": "stable_faroffaxis_49_52deg / leaky_guided_like_channel / proxy_false_positive",
            "proxy_red_flags": "stable_faroffaxis_channel_flag;proxy_false_positive_flag;fortyfive_fiftyfive_lobe_failure_flag",
            "required_reject_rules": "reject severe >45 deg peak risk; reject 45-55 lobe; flag guided/leaky channel risk",
            "status": "stopped",
        },
        {
            "candidate_id": "F0_0781",
            "failure_mode": "stable_offnormal_around_26deg / broad_40_60_channel",
            "proxy_red_flags": "near_normal_failure_flag;broad_40_60_failure_flag;top_MDC_angle_filter_false_positive_risk",
            "required_reject_rules": "reject offnormal 20-30 deg if final target; allow only as intermediate baseline label",
            "status": "stopped",
        },
        {
            "candidate_id": "F0_0204",
            "failure_mode": "severe_faroffaxis_46_67deg / broad_FWHM / source_position_mismatch",
            "proxy_red_flags": "severe_faroffaxis_gt45deg_risk;broad_fwhm_failure_flag;source_position_instability_flag",
            "required_reject_rules": "reject >45 deg peak; reject broad FWHM; reject center-vs-bilateral mismatch",
            "status": "stopped",
        },
    ]
    write_csv(OUT / "r2_4g3_negative_failure_modes.csv", failure_modes)

    rules = [
        rule("center_only_false_positive_risk", "center_only_false_positive_flag or missing tri-point evidence", "true -> hard_reject", "hard_reject", "Center-only results repeatedly failed x-line validation.", "D5_BASE_13461", "center-only false positive"),
        rule("source_position_instability_risk", "source_position_peak_std_deg or source_position_instability_flag", "std > 5 deg -> hard_reject; 2-5 deg -> strong_warning", "hard_reject", "Source-position ensemble must remain stable before FDTD expansion.", "D5_BASE_13461;F0_0204", "source-position instability"),
        rule("thirty_forty_lobe_risk", "measured/proxy 30-40 deg lobe fraction", ">=0.25 or dominant over normal cone -> hard_reject", "hard_reject", "D5 and F0 routes revived 30-40 deg energy.", "D5_BASE_13461;F0_0204", "30-40 deg off-axis lobe"),
        rule("fortyfive_fiftyfive_lobe_risk", "measured/proxy 45-55 deg lobe fraction", ">=0.25 or dominant over normal cone -> hard_reject", "hard_reject", "E1_0236 and F0_0204 showed far-offaxis/leaky-like channels.", "E1_0236;F0_0204", "45-55 deg far-offaxis lobe"),
        rule("broad_40_60_faroffaxis_risk", "40-60 deg broad lobe fraction", ">=0.30 -> hard_reject; 0.20-0.30 -> strong_warning", "hard_reject", "F0_0781 and F0_0204 failed through broad high-angle response.", "F0_0781;F0_0204", "broad 40-60 deg channel"),
        rule("stable_offnormal_20_30deg_risk", "peak_abs_angle proxy/risk near 20-30 deg", "20 <= peak_abs <= 30 -> strong_warning; hard_reject for final pass if >8 deg", "strong_warning", "25-30 deg can be intermediate literature baseline but not final relaxed target pass.", "F0_0781", "stable off-normal around 26 deg"),
        rule("severe_faroffaxis_gt45deg_risk", "peak_abs_angle risk", ">45 deg -> hard_reject", "hard_reject", "Severe far-offaxis peaks are incompatible with normal RCLED target.", "E1_0236;F0_0204", "faroffaxis >45 deg"),
        rule("broad_fwhm_risk", "angular_FWHM proxy/risk", ">20 deg -> hard_reject for final pass; 15-20 deg -> strong_warning", "hard_reject", "Relaxed target angular FWHM is <=20 deg, but Python-only cannot claim success.", "F0_0781;F0_0204", "broad angular FWHM"),
        rule("normal_offaxis_low_risk", "normal_offaxis proxy/risk", "<=1.0 -> hard_reject; 1.0-1.5 -> strong_warning", "hard_reject", "All FDTD failures had normal/offaxis <=1.", "E1_0236;F0_0781;F0_0204", "weak normal cone"),
        rule("spectral_proxy_success_but_angular_failure_risk", "spectral_FWHM good but angular flags active", "spectral_FWHM<=10 nm and any angular hard flag -> hard_reject", "hard_reject", "Spectral narrowing did not guarantee angular narrowing.", "E1_0236;F0_0781;F0_0204", "spectral success / angular failure"),
        rule("high_top_mirror_guided_leaky_channel_risk", "high top mirror / high-R cavity route with faroffaxis flags", "high top DBR/MDC plus 45-55 or 40-60 risk -> hard_reject", "hard_reject", "High top reflectors can trap or redirect energy into leaky channels.", "E1_0236;F0_0204", "guided/leaky channel"),
        rule("top_MDC_angle_filter_false_positive_risk", "top_MDC route with 20-60 offaxis risk", "top_MDC route and offnormal/faroffaxis warning -> strong_warning; hard_reject if final target flags fail", "strong_warning", "Top MDC angular filter proxy failed on F0_0781.", "F0_0781", "top MDC false positive"),
    ]
    write_csv(OUT / "r2_4g3_proxy_v1_risk_rules.csv", rules)

    write_text(OUT / "r2_4g3_proxy_v1_scoring_definition.md", """
# R2-4G3 Proxy v1 Scoring Definition

Proxy v1 is a reject/risk proxy, not a success predictor. The dataset has only negative samples, so it cannot train or claim a positive pass classifier.

Relaxed final FDTD targets remain:
- spectral FWHM <= 10 nm;
- angular FWHM <= 20 deg;
- peak_abs_angle <= 8 deg.

These are final FDTD pass targets, not Python-only success claims.

Risk-score proposal:
- hard_reject component: +100 each;
- strong_warning component: +20 each;
- weak_warning component: +5 each.

Candidate FDTD entry gate for future G4 output:
- no hard_reject;
- total_risk_score < 40;
- no D5-like, E1-like, F0_0781-like, or F0_0204-like red flags;
- source_position_status remains `requires_tri_point_FDTD`, never `pass`;
- candidate must include route family and full structure parameters;
- shortlist maximum 1 primary + 1 backup;
- if no candidate passes, output no-pass and do not force shortlist.

Do not overfit by rejecting all literature-seeded routes unless they match known failure modes. A 25-30 deg route may be recorded as an intermediate literature baseline, but not as final relaxed-target pass.
""")

    write_text(OUT / "r2_4g3_g4_candidate_generator_requirements.md", """
# R2-4G3 G4 Candidate Generator Requirements

G4 may generate candidates only. It must not run FDTD.

G4 may output an FDTD shortlist only if proxy v1 shows:
- no hard_reject;
- total_risk_score below the defined gate;
- no D5-like / E1-like / F0_0781-like / F0_0204-like red flags;
- source_position_status = requires_tri_point_FDTD, not pass;
- route family and full structure parameters are present;
- shortlist size <= 1 primary + 1 backup.

If no candidate passes, G4 must output no-pass. It must not force a shortlist from failed routes.
""")

    write_text(OUT / "r2_4g3_fdtd_gate_rules.md", """
# R2-4G3 FDTD Gate Rules

- No immediate FDTD after G3.
- G4 may generate candidates only.
- Any FDTD after G4 requires explicit user approval.
- First FDTD remains tri-point x-dipole 453 nm only.
- Pass tri-point before y-dipole.
- Pass x/y before broadband.
- Fail stops candidate.
""")

    write_text(OUT / "r2_4g3_stop_rules.md", """
# R2-4G3 Stop Rules

- Do not revive D5_BASE_13461.
- Do not revive E1_0236.
- Do not revive F0_0781.
- Do not revive F0_0204.
- Do not pick any failed F0/F1/F2/F3/F4 route directly for FDTD.
- Do not run immediate FDTD.
- Do not treat proxy v1 as a success predictor.
""")

    write_text(OUT / "r2_4g3_summary.md", f"""
# R2-4G3 Update Dipole-Aware Proxy Thresholds

G3 converts the G1 negative dataset into proxy v1 reject/risk rules.

One-line conclusion: because the dataset contains only negatives, proxy v1 is a hard-reject/risk-screening rule set, not a success predictor.

Negative samples used: {len(negatives)} rows.
Risk components defined: {len(rules)}.

Immediate FDTD allowed: no.

Recommended G4 task name:
`R2-4G4_candidate_generator_with_proxy_v1_reject_guards`
""")

    write_json(OUT / "r2_4g3_manifest.json", {
        "stage": "R2-4G3 update dipole-aware proxy thresholds from negative dataset",
        "python_only": True,
        "no_lumerical": True,
        "no_lumapi": True,
        "no_fdtd": True,
        "proxy_v1_type": "reject/risk proxy",
        "not_success_predictor": True,
        "negative_sample_count": len(negatives),
        "risk_rule_count": len(rules),
        "inputs": {k: str(v) for k, v in INPUTS.items()},
        "missing_inputs": [f"{k}:{v}" for k, v in INPUTS.items() if not v.exists()],
        "recommended_G4_task": "R2-4G4_candidate_generator_with_proxy_v1_reject_guards",
        "immediate_fdtd_allowed": False,
    })

    print(json.dumps({"output": str(OUT), "negative_rows": len(negatives), "risk_rules": len(rules)}, indent=2))
    return 0


def rule(component: str, feature: str, condition: str, severity: str, rationale: str, samples: str, blocked: str) -> dict[str, str]:
    return {
        "risk_component": component,
        "input_feature": feature,
        "threshold_or_condition": condition,
        "severity": severity,
        "rationale": rationale,
        "negative_samples_triggered": samples,
        "intended_failure_mode_blocked": blocked,
    }


if __name__ == "__main__":
    raise SystemExit(main())
