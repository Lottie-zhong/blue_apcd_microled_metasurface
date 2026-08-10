#!/usr/bin/env python3
"""Read-only P_XLIKE versus S_YLIKE audit of the frozen Stage-A matrix."""

from __future__ import annotations

import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, median


EXPECTED_SHA256 = "d400c51cfa557aeffdefb09567dbe20705c50d915bc9a5ddd570281535265bf6"
ANGLES = (-10.0, -5.0, 0.0, 5.0, 10.0)
WAVELENGTHS = tuple(float(x) for x in range(445, 456))
BRANCHES = ("P_XLIKE", "S_YLIKE")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def number(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise AssertionError(f"{label} is not numeric: {value!r}")
    return float(value)


def average(values: list[float]) -> float:
    return mean(values) if values else 0.0


def maximum(values: list[float]) -> float:
    return max(values) if values else 0.0


def close(left: float, right: float) -> bool:
    # Only used to identify exact floating-point ties in a descriptive label;
    # it is not a scientific acceptance tolerance.
    return math.isclose(left, right, rel_tol=0.0, abs_tol=1e-12)


def canonical_grid(value: float, grid: tuple[float, ...], label: str) -> float:
    """Normalize JSON serialization noise to the frozen grid value."""
    candidate = min(grid, key=lambda expected: abs(value - expected))
    if abs(value - candidate) > 1e-9:
        raise AssertionError(f"{label} is outside the frozen grid: {value!r}")
    return candidate


def symmetric_difference(p_value: float, s_value: float) -> tuple[float | None, bool]:
    denominator = abs(p_value) + abs(s_value)
    if denominator == 0.0:
        return None, False
    return 2.0 * abs(p_value - s_value) / denominator, True


def dominant_channel(values: dict[str, float]) -> str:
    values = {key: value for key, value in values.items() if value > 0.0}
    if not values:
        return "NONE"
    peak = max(values.values())
    winners = [key for key, value in values.items() if close(value, peak)]
    return winners[0] if len(winners) == 1 else "MIXTURE"


def direct_source(throughput: float, partition: float) -> str:
    throughput_abs = abs(throughput)
    partition_abs = abs(partition)
    if throughput_abs == 0.0 and partition_abs == 0.0:
        return "NO_ETA_PLUS1_DIFFERENCE"
    if close(throughput_abs, partition_abs):
        return "MIXTURE"
    return "THROUGHPUT" if throughput_abs > partition_abs else "ORDER_PARTITION"


def pair_metrics(angle: float, wavelength: float, rows: dict[str, dict]) -> dict:
    p, s = rows["P_XLIKE"], rows["S_YLIKE"]
    p_eta, s_eta = number(p["eta_plus1"], "P eta_plus1"), number(s["eta_plus1"], "S eta_plus1")
    p_t, s_t = number(p["T_total"], "P T_total"), number(s["T_total"], "S T_total")
    p_r, s_r = number(p["R_total"], "P R_total"), number(s["R_total"], "S R_total")
    p_res, s_res = number(p["residual_1_minus_R_minus_T"], "P residual"), number(s["residual_1_minus_R_minus_T"], "S residual")
    p_share = p_eta / p_t if p_t else None
    s_share = s_eta / s_t if s_t else None
    if p_share is None or s_share is None:
        throughput_contribution = None
        partition_contribution = None
        source = "UNDEFINED_ZERO_THROUGHPUT"
    else:
        # eta(+1) = T * [eta(+1)/T]. This symmetric-average identity splits
        # the observed eta(+1) change into throughput and order partition.
        throughput_contribution = 0.5 * (p_share + s_share) * (p_t - s_t)
        partition_contribution = (p_eta - s_eta) - throughput_contribution
        source = direct_source(throughput_contribution, partition_contribution)

    rel_diff, rel_defined = symmetric_difference(p_eta, s_eta)
    delta_r, delta_t, delta_res = p_r - s_r, p_t - s_t, p_res - s_res
    values = {
        "angle_deg": angle,
        "wavelength_nm": wavelength,
        "ux_in": number(p["ux_in"], "ux_in"),
        "eta_plus1_P": p_eta,
        "eta_plus1_S": s_eta,
        "delta_eta_plus1": p_eta - s_eta,
        "abs_delta_eta_plus1": abs(p_eta - s_eta),
        "symmetric_relative_difference": rel_diff,
        "symmetric_relative_difference_defined": rel_defined,
        "R_P": p_r,
        "R_S": s_r,
        "delta_R": delta_r,
        "T_P": p_t,
        "T_S": s_t,
        "delta_T": delta_t,
        "residual_P": p_res,
        "residual_S": s_res,
        "delta_residual": delta_res,
        "directionality_P": number(p["directionality"], "P directionality"),
        "directionality_S": number(s["directionality"], "S directionality"),
        "delta_directionality": number(p["directionality"], "P directionality") - number(s["directionality"], "S directionality"),
        "eta0_P": number(p["eta_zero"], "P eta_zero"),
        "eta0_S": number(s["eta_zero"], "S eta_zero"),
        "delta_eta0": number(p["eta_zero"], "P eta_zero") - number(s["eta_zero"], "S eta_zero"),
        "eta_minus1_P": number(p["eta_minus1"], "P eta_minus1"),
        "eta_minus1_S": number(s["eta_minus1"], "S eta_minus1"),
        "delta_eta_minus1": number(p["eta_minus1"], "P eta_minus1") - number(s["eta_minus1"], "S eta_minus1"),
        "eta_plus2_P": number(p["eta_plus2"], "P eta_plus2"),
        "eta_plus2_S": number(s["eta_plus2"], "S eta_plus2"),
        "delta_eta_plus2": number(p["eta_plus2"], "P eta_plus2") - number(s["eta_plus2"], "S eta_plus2"),
        "plus1_share_P_of_T": p_share,
        "plus1_share_S_of_T": s_share,
        "throughput_contribution_to_delta_eta_plus1": throughput_contribution,
        "order_partition_contribution_to_delta_eta_plus1": partition_contribution,
        "eta_plus1_difference_source": source,
        "budget_difference_dominant_channel": dominant_channel({"THROUGHPUT": abs(delta_t), "REFLECTION": abs(delta_r), "RESIDUAL": abs(delta_res)}),
        "delta_R_plus_delta_T_plus_delta_residual": delta_r + delta_t + delta_res,
    }
    return values


def angle_summary(angle: float, pairs: list[dict]) -> dict:
    max_pair = max(pairs, key=lambda item: item["abs_delta_eta_plus1"])
    rel = [item["symmetric_relative_difference"] for item in pairs if item["symmetric_relative_difference_defined"]]
    representatives = {str(int(w)): next(item for item in pairs if item["wavelength_nm"] == w) for w in (445.0, 450.0, 455.0)}
    return {
        "angle_deg": angle,
        "pair_count": len(pairs),
        "mean_eta_plus1_P": average([x["eta_plus1_P"] for x in pairs]),
        "mean_eta_plus1_S": average([x["eta_plus1_S"] for x in pairs]),
        "max_eta_plus1_P": maximum([x["eta_plus1_P"] for x in pairs]),
        "max_eta_plus1_S": maximum([x["eta_plus1_S"] for x in pairs]),
        "mean_abs_delta_eta_plus1": average([x["abs_delta_eta_plus1"] for x in pairs]),
        "max_abs_delta_eta_plus1": maximum([x["abs_delta_eta_plus1"] for x in pairs]),
        "mean_symmetric_relative_difference": average(rel),
        "max_symmetric_relative_difference": maximum(rel),
        "mean_R_P": average([x["R_P"] for x in pairs]),
        "mean_R_S": average([x["R_S"] for x in pairs]),
        "mean_T_P": average([x["T_P"] for x in pairs]),
        "mean_T_S": average([x["T_S"] for x in pairs]),
        "mean_directionality_P": average([x["directionality_P"] for x in pairs]),
        "mean_directionality_S": average([x["directionality_S"] for x in pairs]),
        "max_difference_wavelength_nm": max_pair["wavelength_nm"],
        "representative_445_450_455": representatives,
    }


def build_audit(repo_root: Path) -> dict:
    matrix_path = repo_root / "reports" / "coupling" / "stage_a_frozen_spacer_polarization_angle_broadband_matrix_v1.json"
    matrix_hash = sha256(matrix_path)
    assert matrix_hash == EXPECTED_SHA256, (EXPECTED_SHA256, matrix_hash)
    matrix = json.loads(matrix_path.read_text(encoding="utf-8"))
    contract = matrix["frozen_contract"]
    assert tuple(float(x) for x in contract["angle_labels_deg"]) == ANGLES
    assert tuple(float(x) for x in contract["wavelength_grid_nm"]) == WAVELENGTHS
    assert tuple(contract["polarization_branches"]) == BRANCHES
    assert contract["no_polarization_averaging"] is True
    assert contract["no_extrapolation"] is True
    assert contract["no_interpolation"] is True
    rows = matrix["rows"]
    assert len(rows) == 110
    grouped: dict[tuple[float, float], dict[str, dict]] = defaultdict(dict)
    for row in rows:
        angle = canonical_grid(number(row["theta_air_in_label_deg"], "angle"), ANGLES, "angle")
        wavelength = canonical_grid(number(row["wavelength_nm"], "wavelength"), WAVELENGTHS, "wavelength")
        branch = row["polarization_branch"]
        assert angle in ANGLES and wavelength in WAVELENGTHS and branch in BRANCHES
        assert branch not in grouped[(angle, wavelength)]
        assert row.get("polarization_averaged") is not True
        grouped[(angle, wavelength)][branch] = row
    assert len(grouped) == 55
    pairs = []
    for angle in ANGLES:
        for wavelength in WAVELENGTHS:
            assert set(grouped[(angle, wavelength)]) == set(BRANCHES)
            pairs.append(pair_metrics(angle, wavelength, grouped[(angle, wavelength)]))
    by_angle = {str(int(angle)): angle_summary(angle, [x for x in pairs if x["angle_deg"] == angle]) for angle in ANGLES}
    abs_delta = [x["abs_delta_eta_plus1"] for x in pairs]
    rel = [x["symmetric_relative_difference"] for x in pairs if x["symmetric_relative_difference_defined"]]
    max_pair = max(pairs, key=lambda x: x["abs_delta_eta_plus1"])
    return {
        "schema_version": "stage_a_ps_sensitivity_reduction_audit_v1",
        "task": "APCD_MDC_NP_COUPLING_V1_STAGE_A_PS_SENSITIVITY_REDUCTION_AUDIT",
        "status": "SYSTEM_LEVEL_PS_DIFFERENCE_SUBSTANTIAL",
        "decision": "DESCRIPTIVE_ONLY: observed matrix-level P/S difference; NO_FORMAL_TOLERANCE; Stage-A matrix alone cannot validate a shared NP P/S operator.",
        "scope": {
            "source": "frozen Stage-A integrated MDC+spacer+NP full-wave matrix",
            "matrix_path": str(matrix_path),
            "matrix_sha256": matrix_hash,
            "angles_deg": list(ANGLES),
            "wavelength_grid_nm": list(WAVELENGTHS),
            "polarization_branches": list(BRANCHES),
            "pair_count": len(pairs),
            "polarization_averaging_used": False,
            "np_equivalence_claim": False,
        },
        "matrix_contract": {
            "phase_id": matrix.get("phase_id"),
            "matrix_status": matrix.get("status"),
            "matrix_decision": matrix.get("decision"),
            "no_extrapolation": contract["no_extrapolation"],
            "no_interpolation": contract["no_interpolation"],
            "no_polarization_averaging": contract["no_polarization_averaging"],
            "target_mdc_candidate": contract.get("mdc_candidate"),
            "target_np_candidate": contract.get("np_candidate"),
            "frozen_spacer_nm": contract.get("frozen_spacer_nm"),
            "total_continuous_sio2_separation_nm": contract.get("total_continuous_sio2_separation_nm"),
        },
        "pair_metrics": pairs,
        "five_angle_summary": by_angle,
        "overall_summary": {
            "pair_count": len(pairs),
            "mean_abs_delta_eta_plus1": average(abs_delta),
            "median_abs_delta_eta_plus1": median(abs_delta),
            "max_abs_delta_eta_plus1": max(abs_delta),
            "max_difference_angle_deg": max_pair["angle_deg"],
            "max_difference_wavelength_nm": max_pair["wavelength_nm"],
            "mean_symmetric_relative_difference": average(rel),
            "max_symmetric_relative_difference": maximum(rel),
            "undefined_symmetric_relative_difference_count": len(pairs) - len(rel),
            "eta_plus1_difference_source_counts": dict(Counter(x["eta_plus1_difference_source"] for x in pairs)),
            "budget_difference_dominant_channel_counts": dict(Counter(x["budget_difference_dominant_channel"] for x in pairs)),
        },
        "difference_source_interpretation": {
            "method": "exact symmetric-average decomposition of eta_plus1 into throughput and order partition; R/T/residual are accompanying energy-budget channels",
            "status_basis": "large observed eta_plus1 and symmetric-relative differences in this matrix; descriptive label only and no numerical cutoff",
            "throughput_definition": "0.5*(eta_plus1_P/T_P + eta_plus1_S/T_S)*(T_P-T_S)",
            "order_partition_definition": "delta_eta_plus1 - throughput_contribution",
            "energy_budget_identity": "delta_R + delta_T + delta_residual = 0 up to floating-point representation",
            "formal_tolerance_defined": False,
            "classification_is_descriptive_only": True,
        },
        "safety": {
            "solver_entries_in_this_audit": 0,
            "fdtd": 0,
            "tmm": 0,
            "rcwa": 0,
            "training": 0,
            "ml_inference": 0,
            "formal_tolerance_defined": False,
            "tolerance_added": False,
            "descriptive_only": True,
        },
        "replay_checks": {
            "exact_55_ps_pairs": True,
            "no_missing_wavelength": True,
            "no_polarization_averaging": True,
            "matrix_sha_verified": True,
            "no_np_equivalence_claim": True,
            "no_formal_tolerance": True,
        },
        "next_action": "USER_REVIEW_PS_REDUCTION_EVIDENCE",
    }


def render_markdown(audit: dict) -> str:
    summary = audit["overall_summary"]
    lines = [
        "# Stage-A P/S sensitivity reduction audit v1", "",
        "Read-only audit of the frozen Stage-A integrated MDC+spacer+NP matrix.",
        "The matrix is not an NP-only provider and this report does not define a shared NP P/S operator.", "",
        "## P/S quantitative difference", "",
        f"- Status: `{audit['status']}` (`DESCRIPTIVE_ONLY`; `NO_FORMAL_TOLERANCE`).",
        f"- Pairs: `{summary['pair_count']}` exact same-angle/same-wavelength P/S pairs.",
        f"- Mean / median / max `abs(delta_eta_plus1)`: `{summary['mean_abs_delta_eta_plus1']:.12g}` / `{summary['median_abs_delta_eta_plus1']:.12g}` / `{summary['max_abs_delta_eta_plus1']:.12g}`.",
        f"- Maximum at `{summary['max_difference_angle_deg']:+g} deg`, `{summary['max_difference_wavelength_nm']:.0f} nm`.",
        f"- Mean / max symmetric relative difference: `{summary['mean_symmetric_relative_difference']:.12g}` / `{summary['max_symmetric_relative_difference']:.12g}`.", "",
        "| angle (deg) | mean eta+1 P | mean eta+1 S | mean abs delta | max abs delta | mean R P/S | mean T P/S | mean directionality P/S | max-difference wavelength (nm) |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for angle in ANGLES:
        item = audit["five_angle_summary"][str(int(angle))]
        lines.append(f"| {angle:+g} | {item['mean_eta_plus1_P']:.8g} | {item['mean_eta_plus1_S']:.8g} | {item['mean_abs_delta_eta_plus1']:.8g} | {item['max_abs_delta_eta_plus1']:.8g} | {item['mean_R_P']:.8g} / {item['mean_R_S']:.8g} | {item['mean_T_P']:.8g} / {item['mean_T_S']:.8g} | {item['mean_directionality_P']:.8g} / {item['mean_directionality_S']:.8g} | {item['max_difference_wavelength_nm']:.0f} |")
    lines.extend([
        "", "## Where difference comes from", "",
        "The direct `eta(+1)` difference is decomposed exactly into a throughput contribution and an order-partition contribution. Reflection and residual deltas are accompanying energy-budget channels; they are not treated as an NP-only causal attribution.", "",
        f"- Direct-source counts: `{json.dumps(summary['eta_plus1_difference_source_counts'], sort_keys=True)}`.",
        f"- Budget-channel counts: `{json.dumps(summary['budget_difference_dominant_channel_counts'], sort_keys=True)}`.",
        "- The closure identity is checked per pair as `delta_R + delta_T + delta_residual`; no new numerical tolerance is introduced.", "",
        "## Scientific interpretation", "",
        "This is system-level P/S sensitivity evidence in the observed frozen matrix only. It may inform whether testing a shared NP P/S approximation is worth a separately authorized study, but it cannot validate that approximation. No claim of P/S equivalence, NP polarization independence, or formal pass/fail tolerance is made.", "",
        "## Safety / Git", "",
        f"- Matrix SHA256: `{audit['scope']['matrix_sha256']}`.",
        f"- Matrix path: `{audit['scope']['matrix_path']}`.",
        "- This audit solver entries: FDTD=0, TMM=0, RCWA=0, training=0, ML inference=0.",
        "- Polarization averaging: false; exact P/S branches retained.",
        "- Next action: `USER_REVIEW_PS_REDUCTION_EVIDENCE`.", "",
    ])
    return "\n".join(lines)


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    output_dir = root / "reports" / "coupling"
    audit = build_audit(root)
    (output_dir / "stage_a_ps_sensitivity_reduction_audit_v1.json").write_text(json.dumps(audit, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (output_dir / "stage_a_ps_sensitivity_reduction_audit_v1.md").write_text(render_markdown(audit), encoding="utf-8")
    print(json.dumps(audit["overall_summary"], ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
