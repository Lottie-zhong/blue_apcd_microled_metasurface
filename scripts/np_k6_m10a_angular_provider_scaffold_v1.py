from __future__ import annotations
from typing import Iterable, Mapping, Sequence

KEY_FIELDS = ("geometry_hash", "u_x_identity", "polarization", "wavelength_contract", "physics_contract_id")

def make_angular_unique_key(row: Mapping[str, object]) -> tuple:
    return tuple(row[k] for k in KEY_FIELDS)

def build_residual_rows(rcwa_rows: Iterable[Mapping[str, object]], fdtd_rows: Iterable[Mapping[str, object]], fields: Sequence[str] = ("eta_plus1", "eta_0", "eta_minus1", "R_total", "T_total")) -> list[dict]:
    """Pure scaffold: joins already-authorized RCWA/FDTD rows; never runs a solver or fits a model."""
    rcwa = {make_angular_unique_key(r): r for r in rcwa_rows}
    result = []
    for truth in fdtd_rows:
        key = make_angular_unique_key(truth)
        base = rcwa.get(key)
        if base is None:
            continue
        row = {k: truth.get(k) for k in KEY_FIELDS}
        for field in fields:
            row[f"delta_{field}"] = float(truth[field]) - float(base[field])
        result.append(row)
    return result

def E_MDC_weighted(weights: Mapping[str, float], truth: Mapping[str, float], prediction: Mapping[str, float]) -> dict[str, float]:
    """Mock-testable metric interface; weights must come from a future formal MDC authority."""
    def err(name: str) -> float:
        return abs(float(prediction[name]) - float(truth[name]))
    order = [k for k in truth if k.startswith("eta_m")]
    out = {
        "weighted_eta_plus1_error": weights.get("eta_plus1", 0.0) * err("eta_plus1"),
        "weighted_T_error": weights.get("T_total", 0.0) * err("T_total"),
        "weighted_order_profile_error": (sum(err(k) for k in order) / len(order)) if order else 0.0,
        "weighted_PS_contrast_error": weights.get("PS_contrast", 0.0) * err("PS_contrast") if "PS_contrast" in truth else 0.0,
    }
    out["weighted_total"] = sum(out.values())
    return out

def provider_error_to_candidate_margin_ratio(provider_error: float, candidate_separation: float) -> float | None:
    if candidate_separation <= 0:
        return None
    return float(provider_error) / float(candidate_separation)
