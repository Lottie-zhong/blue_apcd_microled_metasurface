from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence


K = 6
FORWARD_BINS = [0, 60, 120, 180, 240, 300]
REVERSE_BINS = [300, 240, 180, 120, 60, 0]
DEFAULT_WAVELENGTH_NM = 450.0
DEFAULT_DIMER_PITCH_X_NM = 431.907786

COEFFICIENT_FIELDS = [
    "order_name",
    "supercell_index",
    "target_bin_deg",
    "candidate_id",
    "source_stage",
    "source_file",
    "geometry_family",
    "actual_common_phase_deg",
    "ideal_phase_deg",
    "phase_error_from_ideal_deg",
    "Tx",
    "field_amplitude_sqrt_Tx",
    "complex_coeff_real",
    "complex_coeff_imag",
    "dimer_center_index_units",
    "dimer_center_x_nm",
]

ARRAY_FACTOR_FIELDS = [
    "order_name",
    "diffraction_order_m",
    "array_factor_real",
    "array_factor_imag",
    "array_factor_abs",
    "strength",
    "relative_strength",
    "theta_deg",
    "theta_relation",
]

LAYOUT_PLAN_FIELDS = [
    "order_name",
    "supercell_index",
    "target_bin_deg",
    "candidate_id",
    "source_stage",
    "source_file",
    "geometry_family",
    "actual_common_phase_deg",
    "Tx",
    "dimer_center_index_units",
    "dimer_center_x_nm",
    "layout_status",
]


@dataclass(frozen=True)
class PhaseLibraryEntry:
    phase_bin_deg: int
    candidate_id: str
    actual_common_phase_deg: float
    phase_err_deg: float
    Tx: float
    blocked_y_leakage: float
    conversion_to_leakage_ratio: float
    matrix_error: float
    geometry_family: str
    source_stage: str
    source_file: str


@dataclass(frozen=True)
class Metadata:
    wavelength_nm: float | None = DEFAULT_WAVELENGTH_NM
    dimer_pitch_x_nm: float | None = DEFAULT_DIMER_PITCH_X_NM

    @property
    def supercell_period_nm(self) -> float | None:
        if self.dimer_pitch_x_nm is None:
            return None
        return self.dimer_pitch_x_nm * K

    @property
    def theta_relation(self) -> str:
        if self.wavelength_nm is None or self.supercell_period_nm is None:
            return "sin(theta_m) = m * lambda / Lambda"
        return f"sin(theta_m) = m * {self.wavelength_nm:g} / {self.supercell_period_nm:g}"


def read_phase_library(path: Path) -> dict[int, PhaseLibraryEntry]:
    rows = read_csv_rows(path)
    if not rows:
        raise ValueError(f"empty phase library: {path}")
    entries: dict[int, PhaseLibraryEntry] = {}
    for row in rows:
        phase_bin = int(round(float(row["phase_bin_deg"]))) % 360
        if phase_bin in entries:
            raise ValueError(f"duplicate phase bin {phase_bin}")
        entries[phase_bin] = PhaseLibraryEntry(
            phase_bin_deg=phase_bin,
            candidate_id=row["candidate_id"],
            actual_common_phase_deg=float(row["actual_common_phase_deg"]),
            phase_err_deg=float(row["phase_err_deg"]),
            Tx=float(row["selected_x_power"]),
            blocked_y_leakage=float(row["blocked_y_leakage"]),
            conversion_to_leakage_ratio=float(row["conversion_to_leakage_ratio"]),
            matrix_error=float(row["matrix_error"]),
            geometry_family=row.get("geometry_family", ""),
            source_stage=row.get("source_stage", ""),
            source_file=row.get("source_file", ""),
        )
    got = sorted(entries)
    if got != FORWARD_BINS:
        raise ValueError(f"Stage12-0 requires bins {FORWARD_BINS}; got {got}")
    return entries


def build_order_coefficients(
    entries: dict[int, PhaseLibraryEntry],
    phase_order: Sequence[int],
    order_name: str,
    metadata: Metadata,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for index, phase_bin in enumerate(phase_order):
        entry = entries[phase_bin]
        amplitude = math.sqrt(entry.Tx)
        phase_rad = math.radians(entry.actual_common_phase_deg)
        coeff = amplitude * complex(math.cos(phase_rad), math.sin(phase_rad))
        center_index = index + 0.5
        center_x_nm: float | str = ""
        if metadata.dimer_pitch_x_nm is not None:
            center_x_nm = center_index * metadata.dimer_pitch_x_nm
        rows.append(
            {
                "order_name": order_name,
                "supercell_index": index,
                "target_bin_deg": phase_bin,
                "candidate_id": entry.candidate_id,
                "source_stage": entry.source_stage,
                "source_file": entry.source_file,
                "geometry_family": entry.geometry_family,
                "actual_common_phase_deg": entry.actual_common_phase_deg,
                "ideal_phase_deg": float(phase_bin),
                "phase_error_from_ideal_deg": wrap180(entry.actual_common_phase_deg - phase_bin),
                "Tx": entry.Tx,
                "field_amplitude_sqrt_Tx": amplitude,
                "complex_coeff_real": coeff.real,
                "complex_coeff_imag": coeff.imag,
                "dimer_center_index_units": center_index,
                "dimer_center_x_nm": center_x_nm,
            }
        )
    return rows


def compute_array_factor(
    coefficient_rows: Sequence[dict[str, object]],
    metadata: Metadata,
    diffraction_orders: Sequence[int] = (-3, -2, -1, 0, 1, 2, 3),
) -> list[dict[str, object]]:
    coeffs = [complex(float(row["complex_coeff_real"]), float(row["complex_coeff_imag"])) for row in coefficient_rows]
    values: list[tuple[int, complex, float]] = []
    for order in diffraction_orders:
        af = 0j
        for index, coeff in enumerate(coeffs):
            phase = -2.0 * math.pi * order * index / K
            af += coeff * complex(math.cos(phase), math.sin(phase))
        af /= K
        values.append((order, af, abs(af) ** 2))
    total_strength = sum(strength for _, _, strength in values)
    order_name = str(coefficient_rows[0]["order_name"]) if coefficient_rows else ""
    return [
        {
            "order_name": order_name,
            "diffraction_order_m": order,
            "array_factor_real": af.real,
            "array_factor_imag": af.imag,
            "array_factor_abs": abs(af),
            "strength": strength,
            "relative_strength": strength / total_strength if total_strength > 0 else "",
            "theta_deg": expected_theta_deg(order, metadata),
            "theta_relation": metadata.theta_relation,
        }
        for order, af, strength in values
    ]


def diagnose(coefficients: Sequence[dict[str, object]], array_factor_rows: Sequence[dict[str, object]]) -> dict[str, object]:
    sorted_orders = sorted(array_factor_rows, key=lambda row: float(row["strength"]), reverse=True)
    dominant = sorted_orders[0]
    runner_up = sorted_orders[1]
    tx_values = [float(row["Tx"]) for row in coefficients]
    weakest = min(coefficients, key=lambda row: float(row["Tx"]))
    runner_strength = float(runner_up["strength"])
    contrast = float("inf") if runner_strength == 0 else float(dominant["strength"]) / runner_strength
    return {
        "dominant_order_m": int(dominant["diffraction_order_m"]),
        "dominant_strength": float(dominant["strength"]),
        "dominant_relative_strength": float(dominant["relative_strength"]),
        "runner_up_order_m": int(runner_up["diffraction_order_m"]),
        "runner_up_strength": runner_strength,
        "order_contrast": contrast,
        "weakest_bin_deg": int(weakest["target_bin_deg"]),
        "weakest_Tx": float(weakest["Tx"]),
        "mean_Tx": sum(tx_values) / len(tx_values),
        "min_Tx": min(tx_values),
        "max_Tx": max(tx_values),
        "Tx_nonuniformity_span": max(tx_values) - min(tx_values),
    }


def choose_preferred_order(forward_diag: dict[str, object], reverse_diag: dict[str, object]) -> str:
    # The two orders are conjugate mirrors for a fixed library. Prefer the positive target order on ties.
    forward_score = float(forward_diag["dominant_relative_strength"])
    reverse_score = float(reverse_diag["dominant_relative_strength"])
    if not math.isclose(forward_score, reverse_score, rel_tol=1e-12, abs_tol=1e-12):
        return "forward" if forward_score > reverse_score else "reverse"
    if int(forward_diag["dominant_order_m"]) == 1:
        return "forward"
    return "reverse"


def build_layout_plan_rows(*coefficient_groups: Sequence[dict[str, object]]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for coefficients in coefficient_groups:
        for row in coefficients:
            rows.append(
                {
                    "order_name": row["order_name"],
                    "supercell_index": row["supercell_index"],
                    "target_bin_deg": row["target_bin_deg"],
                    "candidate_id": row["candidate_id"],
                    "source_stage": row["source_stage"],
                    "source_file": row["source_file"],
                    "geometry_family": row["geometry_family"],
                    "actual_common_phase_deg": row["actual_common_phase_deg"],
                    "Tx": row["Tx"],
                    "dimer_center_index_units": row["dimer_center_index_units"],
                    "dimer_center_x_nm": row["dimer_center_x_nm"],
                    "layout_status": "candidate_for_stage12_1_layout_fdtd_no_fdtd_run_in_stage12_0",
                }
            )
    return rows


def write_summary(
    path: Path,
    input_csv: Path,
    metadata: Metadata,
    forward_diag: dict[str, object],
    reverse_diag: dict[str, object],
    preferred_order: str,
) -> None:
    preferred_diag = forward_diag if preferred_order == "forward" else reverse_diag
    can_proceed = int(preferred_diag["dominant_order_m"]) in {-1, 1} and int(preferred_diag["weakest_bin_deg"]) == 240
    lines = [
        "# Stage12-0 H500 LP-APCD K=6 Analytic Handoff",
        "",
        "## Boundary",
        "",
        "- No FDTD was run.",
        "- No `.fsp` file was generated.",
        "- No LP steering completion is claimed.",
        "- This is analytic/layout only.",
        "",
        "## Input",
        "",
        f"- Frozen library: `{input_csv.as_posix()}`",
        "- Bins: `0, 60, 120, 180, 240, 300`.",
        "- Aperture coefficient convention: `sqrt(Tx) * exp(i * actual_common_phase_deg)`.",
        "",
        "## Metadata",
        "",
        f"- wavelength_nm: `{metadata.wavelength_nm}`",
        f"- dimer_pitch_x_nm: `{metadata.dimer_pitch_x_nm}`",
        f"- supercell period Lambda_nm: `{metadata.supercell_period_nm}`",
        f"- steering relation: `{metadata.theta_relation}`",
        "",
        "## Forward Order",
        "",
        f"- sequence: `{FORWARD_BINS}`",
        f"- dominant diffraction order: `{forward_diag['dominant_order_m']}`",
        f"- relative strength: `{forward_diag['dominant_relative_strength']:.6f}`",
        f"- order contrast: `{forward_diag['order_contrast']:.6f}`",
        f"- weakest bin: `{forward_diag['weakest_bin_deg']}` with Tx `{forward_diag['weakest_Tx']:.6f}`",
        "",
        "## Reverse Order",
        "",
        f"- sequence: `{REVERSE_BINS}`",
        f"- dominant diffraction order: `{reverse_diag['dominant_order_m']}`",
        f"- relative strength: `{reverse_diag['dominant_relative_strength']:.6f}`",
        f"- order contrast: `{reverse_diag['order_contrast']:.6f}`",
        f"- weakest bin: `{reverse_diag['weakest_bin_deg']}` with Tx `{reverse_diag['weakest_Tx']:.6f}`",
        "",
        "## Diagnosis",
        "",
        f"- Preferred order for Stage12-1: `{preferred_order}`.",
        f"- Expected target diffraction order: `{preferred_diag['dominant_order_m']}`.",
        "- Key risk bin: `240 deg`.",
        f"- Tx nonuniformity span: `{preferred_diag['Tx_nonuniformity_span']:.6f}`.",
        "- Nonuniform Tx is expected to reduce ideal order purity and seed weaker residual orders.",
        f"- Stage12-1 K=6 layout/FDTD can proceed: `{can_proceed}`.",
        "",
        "## Explicit Non-Claim",
        "",
        "This handoff is layout-ready analytic evidence only. It is not a K=6 FDTD result and not LP steering completion.",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def expected_theta_deg(order: int, metadata: Metadata) -> float | str:
    if metadata.wavelength_nm is None or metadata.supercell_period_nm is None:
        return ""
    value = order * metadata.wavelength_nm / metadata.supercell_period_nm
    if abs(value) > 1:
        return "evanescent"
    return math.degrees(math.asin(value))


def wrap180(value: float) -> float:
    return (value + 180.0) % 360.0 - 180.0


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [{str(k): "" if v is None else str(v) for k, v in row.items()} for row in csv.DictReader(handle)]


def write_csv_rows(rows: Iterable[dict[str, object]], path: Path, fields: Sequence[str]) -> None:
    row_list = list(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(row_list)
