from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


APCD_DIFFRACTION_ORDER_FIELDS = [
    "K",
    "wavelength_nm",
    "supercell_period_nm",
    "target_angle_deg",
    "order_n",
    "order_m",
    "expected_theta_deg",
    "expected_ux",
    "expected_uy",
    "order_power_fraction_of_transmitted",
    "total_transmission",
    "order_efficiency_source_norm",
    "Ex_order_complex_real",
    "Ex_order_complex_imag",
    "Ey_order_complex_real",
    "Ey_order_complex_imag",
    "Ez_order_complex_real",
    "Ez_order_complex_imag",
    "input_basis",
    "output_basis",
    "target_channel",
    "notes",
]


APCD_ORDER_RESOLVED_JONES_FIELDS = [
    "K",
    "wavelength_nm",
    "target_angle_deg",
    "order_m",
    "order_n",
    "expected_theta_deg",
    "input_basis",
    "output_basis",
    "Jxx_real",
    "Jxx_imag",
    "Jxy_real",
    "Jxy_imag",
    "Jyx_real",
    "Jyx_imag",
    "Jyy_real",
    "Jyy_imag",
    "t_alpha_star_from_alpha_real",
    "t_alpha_star_from_alpha_imag",
    "t_beta_star_from_alpha_real",
    "t_beta_star_from_alpha_imag",
    "t_alpha_star_from_beta_real",
    "t_alpha_star_from_beta_imag",
    "t_beta_star_from_beta_real",
    "t_beta_star_from_beta_imag",
    "target_conversion",
    "alpha_cross_leakage",
    "beta_to_target_leakage",
    "beta_total_leakage",
    "target_order_ER_dB",
    "notes",
]


@dataclass(frozen=True)
class OrderResolvedJones:
    K: int
    order_m: int
    order_n: int
    expected_theta_deg: float
    J_xy: list[list[complex]]
    J_alpha_beta: list[list[complex]]
    total_transmission_x: float | None = None
    total_transmission_y: float | None = None
    order_efficiency_x: float | None = None
    order_efficiency_y: float | None = None
    notes: str = ""

    def to_schema_row(
        self,
        wavelength_nm: float = 633.0,
        target_angle_deg: float = 15.0,
    ) -> dict[str, object]:
        metrics = order_resolved_apcd_metrics(self.J_alpha_beta)
        return {
            "K": self.K,
            "wavelength_nm": wavelength_nm,
            "target_angle_deg": target_angle_deg,
            "order_m": self.order_m,
            "order_n": self.order_n,
            "expected_theta_deg": self.expected_theta_deg,
            "input_basis": "alpha_beta",
            "output_basis": "alpha_star_beta_star",
            "Jxx_real": self.J_xy[0][0].real,
            "Jxx_imag": self.J_xy[0][0].imag,
            "Jxy_real": self.J_xy[0][1].real,
            "Jxy_imag": self.J_xy[0][1].imag,
            "Jyx_real": self.J_xy[1][0].real,
            "Jyx_imag": self.J_xy[1][0].imag,
            "Jyy_real": self.J_xy[1][1].real,
            "Jyy_imag": self.J_xy[1][1].imag,
            "t_alpha_star_from_alpha_real": self.J_alpha_beta[0][0].real,
            "t_alpha_star_from_alpha_imag": self.J_alpha_beta[0][0].imag,
            "t_beta_star_from_alpha_real": self.J_alpha_beta[1][0].real,
            "t_beta_star_from_alpha_imag": self.J_alpha_beta[1][0].imag,
            "t_alpha_star_from_beta_real": self.J_alpha_beta[0][1].real,
            "t_alpha_star_from_beta_imag": self.J_alpha_beta[0][1].imag,
            "t_beta_star_from_beta_real": self.J_alpha_beta[1][1].real,
            "t_beta_star_from_beta_imag": self.J_alpha_beta[1][1].imag,
            "target_conversion": metrics["target_conversion"],
            "alpha_cross_leakage": metrics["alpha_cross_leakage"],
            "beta_to_target_leakage": metrics["beta_to_target_leakage"],
            "beta_total_leakage": metrics["beta_total_leakage"],
            "target_order_ER_dB": metrics["target_order_ER_dB"],
            "notes": self.notes,
        }


def compute_grating_period_nm(wavelength_nm: float, target_angle_deg: float) -> float:
    sin_theta = math.sin(math.radians(target_angle_deg))
    if sin_theta <= 0:
        raise ValueError("target_angle_deg must give a positive grating period")
    return wavelength_nm / sin_theta


def build_alpha_beta_basis(psi_deg: float, chi_deg: float) -> dict[str, tuple[complex, complex]]:
    psi = math.radians(psi_deg)
    chi = math.radians(chi_deg)
    alpha = (
        math.cos(chi) * math.cos(psi) - 1j * math.sin(chi) * math.sin(psi),
        math.cos(chi) * math.sin(psi) + 1j * math.sin(chi) * math.cos(psi),
    )
    beta = (-alpha[1].conjugate(), alpha[0].conjugate())
    basis = {
        "alpha": _normalize_vector(alpha),
        "beta": _normalize_vector(beta),
    }
    basis["alpha_star"] = (basis["alpha"][0].conjugate(), basis["alpha"][1].conjugate())
    basis["beta_star"] = (basis["beta"][0].conjugate(), basis["beta"][1].conjugate())
    return basis


def build_jones_xy_from_columns(
    x_input_output: tuple[complex, complex],
    y_input_output: tuple[complex, complex],
) -> list[list[complex]]:
    return [
        [x_input_output[0], y_input_output[0]],
        [x_input_output[1], y_input_output[1]],
    ]


def transform_jones_xy_to_alpha_beta(
    jones_xy: list[list[complex]],
    *,
    psi_deg: float,
    chi_deg: float,
) -> list[list[complex]]:
    basis = build_alpha_beta_basis(psi_deg, chi_deg)
    input_basis = [basis["alpha"], basis["beta"]]
    output_basis = [basis["alpha_star"], basis["beta_star"]]
    transformed: list[list[complex]] = []
    for output_vector in output_basis:
        row = []
        for input_vector in input_basis:
            linear_output = _matrix_vector_product(jones_xy, input_vector)
            row.append(_inner_product(output_vector, linear_output))
        transformed.append(row)
    return transformed


def order_resolved_apcd_metrics(
    jones_alpha_beta: list[list[complex]],
    eps: float = 1e-12,
) -> dict[str, float]:
    t_alpha_star_from_alpha = jones_alpha_beta[0][0]
    t_beta_star_from_alpha = jones_alpha_beta[1][0]
    t_alpha_star_from_beta = jones_alpha_beta[0][1]
    t_beta_star_from_beta = jones_alpha_beta[1][1]
    target_conversion = abs(t_alpha_star_from_alpha) ** 2
    alpha_cross_leakage = abs(t_beta_star_from_alpha) ** 2
    beta_to_target_leakage = abs(t_alpha_star_from_beta) ** 2
    beta_total_leakage = beta_to_target_leakage + abs(t_beta_star_from_beta) ** 2
    target_order_er_db = 10 * math.log10((target_conversion + eps) / (beta_to_target_leakage + eps))
    return {
        "target_conversion": target_conversion,
        "alpha_cross_leakage": alpha_cross_leakage,
        "beta_to_target_leakage": beta_to_target_leakage,
        "beta_total_leakage": beta_total_leakage,
        "target_order_ER_dB": target_order_er_db,
    }


def build_order_resolved_jones_schema_rows(
    K: int,
    wavelength_nm: float = 633.0,
    target_angle_deg: float = 15.0,
    psi_deg: float = 112.5,
    chi_deg: float = 22.5,
) -> list[dict[str, object]]:
    rows = []
    for order in (-1, 0, 1):
        theta = expected_order_angle_deg(
            order,
            wavelength_nm,
            compute_grating_period_nm(wavelength_nm, target_angle_deg),
        )
        rows.append(
            {
                field: ""
                for field in APCD_ORDER_RESOLVED_JONES_FIELDS
            }
        )
        rows[-1].update(
            {
                "K": K,
                "wavelength_nm": wavelength_nm,
                "target_angle_deg": target_angle_deg,
                "order_m": 0,
                "order_n": order,
                "expected_theta_deg": theta,
                "input_basis": f"alpha_beta_future_from_psi_{psi_deg}_chi_{chi_deg}",
                "output_basis": "alpha_star_beta_star_future",
                "notes": "dry-run schema row; not an optical result; no FDTD run",
            }
        )
    return rows


def write_order_resolved_jones_schema(rows: Iterable[dict[str, object]], path: Path) -> Path:
    rows = list(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=APCD_ORDER_RESOLVED_JONES_FIELDS)
        writer.writeheader()
        writer.writerows({field: row.get(field, "") for field in APCD_ORDER_RESOLVED_JONES_FIELDS} for row in rows)
    return path


def write_order_resolved_jones_plan(
    K: int,
    path: Path,
    psi_deg: float = 112.5,
    chi_deg: float = 22.5,
) -> Path:
    lines = [
        f"# APCD K={K} Order-Resolved Jones Analysis Plan",
        "",
        "## Current State",
        "",
        "- K=6/K=7 setup-only scaffold has been completed.",
        "- Dimer-level structure group organization has been completed.",
        "- Phase 2.3A proved that a uniform scaffold is not equivalent to a +15 deg directional metagrating.",
        "- Phase 2.3B established the diffraction-order extraction scaffold.",
        "- There is still no real metagrating optical result.",
        "- This plan is not an optical result and no FDTD run was performed.",
        "- Current structure remains scaffold only.",
        "",
        "## Stage Goal",
        "",
        "- Establish a Jones-matrix analysis framework for each diffraction order.",
        "- Support future x/y input runs and combine their complex order fields into `J_xy`.",
        "- Transform `J_xy` into the APCD `alpha/beta -> alpha*/beta*` basis.",
        "- Prepare order-resolved APCD metrics.",
        "",
        "## APCD Target Channel",
        "",
        "The main metric is not total T and not ordinary grating power. The target channel is:",
        "",
        "```text",
        "t_{alpha*<-alpha}^{target order}",
        "```",
        "",
        "The suppressed channels are:",
        "",
        "- `t_{beta*<-alpha}`",
        "- `t_{alpha*<-beta}`",
        "- `t_{beta*<-beta}`",
        "",
        "Basis parameters:",
        "",
        f"- psi_deg: {psi_deg}",
        f"- chi_deg: {chi_deg}",
        "",
        "Matrix indexing convention:",
        "",
        "- `J_ab[0,0] = t_{alpha*<-alpha}`",
        "- `J_ab[1,0] = t_{beta*<-alpha}`",
        "- `J_ab[0,1] = t_{alpha*<-beta}`",
        "- `J_ab[1,1] = t_{beta*<-beta}`",
        "",
        "## Lumerical Extraction Relationship",
        "",
        "Future real runs need:",
        "",
        "1. x-polarized input run",
        "2. y-polarized input run",
        "3. for each run, `gratingvector`, `gratingpolar`, or an equivalent complex vector extraction per diffraction order",
        "4. construction of `J_xy = [[Ex_x, Ex_y], [Ey_x, Ey_y]]` for each order",
        "5. transformation to alpha/beta input and alpha*/beta* output basis",
        "",
        "`grating()` power fraction alone is not enough to construct a Jones matrix.",
        "",
        "## Later Route",
        "",
        "Step 2.3D: run one minimal K=6 uniform scaffold diagnostic only to verify order sign convention, extraction pipeline, and weak m=+/-1 response expected from a uniform scaffold.",
        "",
        "Step 2.4: design a dimer phase-state mechanism such that K dimer variants provide high `|t_{alpha*<-alpha}|`, low beta leakage, and prescribed phase `phi_i = +/-2*pi*i/K`.",
        "",
        "## Explicit Non-Goals",
        "",
        "- Do not claim +15 deg steering.",
        "- Do not treat the uniform scaffold as the final metagrating.",
        "- Do not use total transmission alone.",
        "- Do not use only `grating()` power as a Jones matrix substitute.",
        "- Do not switch to TiO2 or 450 nm.",
        "- Do not do ML.",
        "- Do not do a large sweep.",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def write_order_resolved_jones_dry_run_outputs(
    K: int,
    output_dir: Path,
    wavelength_nm: float = 633.0,
    target_angle_deg: float = 15.0,
    psi_deg: float = 112.5,
    chi_deg: float = 22.5,
) -> tuple[Path, Path, list[dict[str, object]]]:
    rows = build_order_resolved_jones_schema_rows(
        K=K,
        wavelength_nm=wavelength_nm,
        target_angle_deg=target_angle_deg,
        psi_deg=psi_deg,
        chi_deg=chi_deg,
    )
    schema_path = write_order_resolved_jones_schema(rows, output_dir / "order_resolved_jones_schema.csv")
    plan_path = write_order_resolved_jones_plan(K, output_dir / "order_resolved_jones_plan.md", psi_deg, chi_deg)
    return schema_path, plan_path, rows


def expected_order_angle_deg(order_m_or_n: int, wavelength_nm: float, period_nm: float) -> float:
    argument = order_m_or_n * wavelength_nm / period_nm
    if abs(argument) > 1:
        return math.nan
    return math.degrees(math.asin(argument))


def normalize_order_efficiency(grating_fraction: float, total_transmission: float) -> float:
    return grating_fraction * total_transmission


def build_expected_order_table(
    K: int,
    wavelength_nm: float = 633.0,
    target_angle_deg: float = 15.0,
    orders: Iterable[int] = (-1, 0, 1),
) -> list[dict[str, object]]:
    period_nm = compute_grating_period_nm(wavelength_nm, target_angle_deg)
    rows: list[dict[str, object]] = []
    for order in orders:
        theta = expected_order_angle_deg(order, wavelength_nm, period_nm)
        rows.append(
            {
                "K": K,
                "wavelength_nm": wavelength_nm,
                "supercell_period_nm": period_nm,
                "target_angle_deg": target_angle_deg,
                "order_n": order,
                "order_m": 0,
                "expected_theta_deg": theta,
                "expected_ux": math.sin(math.radians(theta)) if not math.isnan(theta) else math.nan,
                "expected_uy": 0.0,
                "order_power_fraction_of_transmitted": "",
                "total_transmission": "",
                "order_efficiency_source_norm": "",
                "Ex_order_complex_real": "",
                "Ex_order_complex_imag": "",
                "Ey_order_complex_real": "",
                "Ey_order_complex_imag": "",
                "Ez_order_complex_real": "",
                "Ez_order_complex_imag": "",
                "input_basis": "",
                "output_basis": "alpha_star_beta_star_future",
                "target_channel": "t_alpha_star_from_alpha_order_resolved_future",
                "notes": "dry-run schema row; not an optical result",
            }
        )
    return rows


def select_target_order_by_angle(
    order_table: list[dict[str, object]],
    target_angle_deg: float,
) -> dict[str, object]:
    return min(order_table, key=lambda row: abs(float(row["expected_theta_deg"]) - target_angle_deg))


def summarize_order_efficiencies(rows: list[dict[str, object]], epsilon: float = 1e-12) -> dict[str, float]:
    alpha_target = _float_or_zero(_find_metric(rows, "eta_alpha_to_target_order"))
    beta_target = _float_or_zero(_find_metric(rows, "eta_beta_to_target_order"))
    alpha_other = _float_or_zero(_find_metric(rows, "eta_alpha_to_other_orders"))
    return {
        "target_order_ER_dB": 10 * math.log10((alpha_target + epsilon) / (beta_target + epsilon)),
        "spin_selective_directionality_ratio": alpha_target / max(alpha_other + beta_target, epsilon),
    }


def extract_fdtd_grating_orders(
    fdtd: object,
    monitor_name: str = "T",
    K: int = 0,
    diagnostics: list[str] | None = None,
) -> list[dict[str, object]]:
    order_n = _as_list(fdtd.gratingn(monitor_name))
    order_m = _as_list(fdtd.gratingm(monitor_name))
    ux = _as_list(fdtd.gratingu1(monitor_name))
    uy = _as_list(fdtd.gratingu2(monitor_name))
    grating_fraction = _as_list(fdtd.grating(monitor_name))
    total_transmission = float(fdtd.transmission(monitor_name))
    vectors = _try_gratingvector(fdtd, monitor_name, diagnostics=diagnostics)
    order_vectors = _order_vectors_from_gratingvector(vectors, frequency_index=0, diagnostics=diagnostics)

    count = len(grating_fraction)
    rows: list[dict[str, object]] = []
    for index in range(count):
        vector = _vector_at(order_vectors, index)
        rows.append(
            {
                "K": K,
                "wavelength_nm": "",
                "supercell_period_nm": "",
                "target_angle_deg": "",
                "order_n": _value_at(order_n, index),
                "order_m": _value_at(order_m, index, default=0),
                "expected_theta_deg": "",
                "expected_ux": _value_at(ux, index),
                "expected_uy": _value_at(uy, index, default=0.0),
                "order_power_fraction_of_transmitted": grating_fraction[index],
                "total_transmission": total_transmission,
                "order_efficiency_source_norm": normalize_order_efficiency(float(grating_fraction[index]), total_transmission),
                "Ex_order_complex_real": vector[0].real if vector else "",
                "Ex_order_complex_imag": vector[0].imag if vector else "",
                "Ey_order_complex_real": vector[1].real if vector else "",
                "Ey_order_complex_imag": vector[1].imag if vector else "",
                "Ez_order_complex_real": vector[2].real if vector else "",
                "Ez_order_complex_imag": vector[2].imag if vector else "",
                "input_basis": "",
                "output_basis": "cartesian_vector_from_gratingvector",
                "target_channel": "future_order_resolved_alpha_beta",
                "notes": "extracted scaffold row; requires solved FDTD result",
            }
        )
    return rows


def write_diffraction_order_schema(rows: Iterable[dict[str, object]], path: Path) -> Path:
    rows = list(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=APCD_DIFFRACTION_ORDER_FIELDS)
        writer.writeheader()
        writer.writerows({field: row.get(field, "") for field in APCD_DIFFRACTION_ORDER_FIELDS} for row in rows)
    return path


def write_diffraction_order_extraction_plan(
    rows: list[dict[str, object]],
    path: Path,
) -> Path:
    if not rows:
        raise ValueError("Cannot write diffraction-order plan without rows")
    first = rows[0]
    K = int(first["K"])
    plus_row = next(row for row in rows if int(row["order_n"]) == 1)
    minus_row = next(row for row in rows if int(row["order_n"]) == -1)
    lines = [
        f"# APCD K={K} Diffraction-Order Extraction Plan",
        "",
        "## Current State",
        "",
        "- K=6/K=7 setup-only scaffold has been generated.",
        "- Dimer-level structure-group organization has been completed.",
        "- Phase 2.3A showed that a uniform scaffold is not equivalent to a +15 deg directional metagrating.",
        "- This file is not an optical result and no FDTD run was performed.",
        "- Current structure remains a scaffold only.",
        "",
        "## Stage Goal",
        "",
        "- Establish a grating-order extraction schema.",
        "- Prepare for later FDTD or RCWA result analysis.",
        "- Verify the diffraction-order sign convention.",
        "- Do not produce real optical efficiency conclusions in this stage.",
        "",
        "## Lumerical Basis",
        "",
        "- Ansys Lumerical FDTD grating projection commands can report grating-order direction and intensity for periodic structures.",
        "- `grating()` gives the power fraction in each order relative to transmitted power.",
        "- `transmission()` is needed with `grating()` to get source-normalized order efficiency.",
        "- `gratingn()`, `gratingm()`, `gratingu1()`, and `gratingu2()` identify order indices and direction unit-vector components.",
        "- `gratingvector()` and `gratingpolar()` are needed for later vector, polarization, phase, and order-resolved Jones analysis.",
        "- Do not use `grating()` alone to claim polarization-selective extraction.",
        "",
        "## Expected Order Mapping",
        "",
        f"- wavelength_nm: {first['wavelength_nm']}",
        f"- supercell_period_nm: {first['supercell_period_nm']}",
        f"- target_angle_deg: {first['target_angle_deg']}",
        f"- expected +1 theta_deg: {plus_row['expected_theta_deg']}",
        f"- expected -1 theta_deg: {minus_row['expected_theta_deg']}",
        "",
        "Lumerical order sign depends on +x/-x, monitor normal, and the u1/u2 convention. Plus-ramp or minus-ramp correspondence to GUI/FDTD +15 deg must be verified later by real diffraction-order extraction.",
        "",
        "## Output Metrics",
        "",
        "```text",
        "eta_order_source_norm = grating_fraction * total_transmission",
        "target_order_ER_dB = 10 log10(eta_alpha_to_target_order / eta_beta_to_target_order)",
        "spin_selective_directionality_ratio = eta_alpha_to_target_order / max(eta_alpha_to_other_orders + eta_beta_to_target_order, epsilon)",
        "```",
        "",
        "Final APCD metagrating evaluation must use the order-resolved target channel:",
        "",
        "```text",
        "t_{alpha*<-alpha}^{(m)}",
        "```",
        "",
        "Future real runs need x/y input-basis simulations, order-resolved Jones matrices, and conversion to input alpha/beta and output alpha*/beta* bases.",
        "",
        "Future metrics should include:",
        "",
        "- eta_alpha_to_target_order",
        "- eta_beta_to_target_order",
        "- target_order_ER_dB",
        "- eta_alpha_to_zero_order",
        "- eta_alpha_to_minus_order",
        "- spin_selective_directionality_ratio",
        "",
        "## Later Real-Run Route",
        "",
        "Step 1: run one small K=6 or K=7 uniform scaffold case only to validate extraction and order sign convention. Expected m=+/-1 orders should not be strong because the scaffold has no target-channel phase ramp.",
        "",
        "Step 2: design a dimer phase-state mechanism.",
        "",
        "Step 3: compare plus-ramp and minus-ramp candidates to identify which convention maps to +15 deg.",
        "",
        "## Explicit Non-Goals",
        "",
        "- Do not treat the current scaffold as the final metagrating.",
        "- Do not claim +15 deg steering.",
        "- Do not use total transmission alone.",
        "- Do not use only `grating()` to claim polarization-selective extraction.",
        "- Do not switch to TiO2 or 450 nm.",
        "- Do not do ML.",
        "- Do not do a large sweep.",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def write_diffraction_dry_run_outputs(
    K: int,
    output_dir: Path,
    wavelength_nm: float = 633.0,
    target_angle_deg: float = 15.0,
) -> tuple[Path, Path, list[dict[str, object]]]:
    rows = build_expected_order_table(K, wavelength_nm=wavelength_nm, target_angle_deg=target_angle_deg)
    schema_path = write_diffraction_order_schema(rows, output_dir / "diffraction_order_schema.csv")
    plan_path = write_diffraction_order_extraction_plan(rows, output_dir / "diffraction_order_extraction_plan.md")
    return schema_path, plan_path, rows


def _try_gratingvector(
    fdtd: object,
    monitor_name: str,
    diagnostics: list[str] | None = None,
) -> object | None:
    if not hasattr(fdtd, "gratingvector"):
        _append_diagnostic(diagnostics, "gratingvector unavailable: fdtd object has no gratingvector method")
        return None
    for args in ((monitor_name,), (monitor_name, 1)):
        try:
            result = fdtd.gratingvector(*args)
            _append_diagnostic(
                diagnostics,
                f"gratingvector{args} returned {_describe_array_like(result)}",
            )
            return result
        except Exception as exc:
            _append_diagnostic(
                diagnostics,
                f"gratingvector{args} failed: {type(exc).__name__}: {exc}",
            )
    return None


def _order_vectors_from_gratingvector(
    vectors: object | None,
    *,
    frequency_index: int,
    diagnostics: list[str] | None = None,
) -> list[object] | None:
    if vectors is None:
        return None
    try:
        import numpy as np

        array = np.asarray(vectors)
        if array.ndim >= 2 and array.shape[-1] == 3:
            if array.ndim == 4:
                if frequency_index >= array.shape[2]:
                    _append_diagnostic(
                        diagnostics,
                        f"gratingvector frequency_index={frequency_index} out of range for shape={array.shape}",
                    )
                    return None
                array = array[:, :, frequency_index, :]
            rows = array.reshape((-1, 3))
            _append_diagnostic(diagnostics, f"gratingvector normalized to order-vector rows={len(rows)}")
            return [tuple(row) for row in rows]
    except Exception as exc:
        _append_diagnostic(
            diagnostics,
            f"gratingvector ndarray normalization failed: {type(exc).__name__}: {exc}",
        )

    values = _as_list(vectors)
    if values and all(isinstance(value, (list, tuple)) and len(value) >= 3 for value in values):
        _append_diagnostic(diagnostics, f"gratingvector normalized from list rows={len(values)}")
        return values

    _append_diagnostic(diagnostics, "gratingvector could not be normalized to per-order Ex/Ey/Ez rows")
    return None


def _vector_at(vectors: list[object] | None, index: int) -> tuple[complex, complex, complex] | None:
    if vectors is None or index >= len(vectors):
        return None
    vector = vectors[index]
    if isinstance(vector, (list, tuple)) and len(vector) >= 3:
        return (complex(vector[0]), complex(vector[1]), complex(vector[2]))
    return None


def _describe_array_like(value: object) -> str:
    try:
        import numpy as np

        array = np.asarray(value)
        return f"type={type(value).__name__}, shape={array.shape}, dtype={array.dtype}"
    except Exception:
        return f"type={type(value).__name__}"


def _append_diagnostic(diagnostics: list[str] | None, message: str) -> None:
    if diagnostics is not None:
        diagnostics.append(message)


def _as_list(value: object) -> list[object]:
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    try:
        import numpy as np

        if isinstance(value, np.ndarray):
            return list(value.ravel())
    except Exception:
        pass
    return [value]


def _value_at(values: list[object], index: int, default: object = "") -> object:
    return values[index] if index < len(values) else default


def _find_metric(rows: list[dict[str, object]], name: str) -> object:
    for row in rows:
        if row.get("metric") == name:
            return row.get("value", 0)
    return 0


def _float_or_zero(value: object) -> float:
    try:
        return float(value)
    except Exception:
        return 0.0


def _normalize_vector(vector: tuple[complex, complex]) -> tuple[complex, complex]:
    norm = math.sqrt(abs(vector[0]) ** 2 + abs(vector[1]) ** 2)
    if norm == 0:
        raise ValueError("Cannot normalize zero vector")
    return (vector[0] / norm, vector[1] / norm)


def _matrix_vector_product(
    matrix: list[list[complex]],
    vector: tuple[complex, complex],
) -> tuple[complex, complex]:
    return (
        matrix[0][0] * vector[0] + matrix[0][1] * vector[1],
        matrix[1][0] * vector[0] + matrix[1][1] * vector[1],
    )


def _inner_product(
    basis_vector: tuple[complex, complex],
    field_vector: tuple[complex, complex],
) -> complex:
    return basis_vector[0].conjugate() * field_vector[0] + basis_vector[1].conjugate() * field_vector[1]
