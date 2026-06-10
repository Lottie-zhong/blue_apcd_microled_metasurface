from __future__ import annotations

import cmath
import csv
import math
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Optional, Union

import numpy as np

from metasurface.config import (
    APCDDimerMaterialConfig,
    APCDNanopillarConfig,
    APCDSingleDimerConfig,
    RuntimeConfig,
    load_runtime_config,
)
from metasurface.lumapi_runner import import_lumapi


APCD_DIMER_RESULT_FIELDS = [
    "wavelength_nm",
    "period_x_nm",
    "period_y_nm",
    "height_nm",
    "target_polarization_type",
    "psi_deg",
    "chi_deg",
    "transmission_lcp",
    "transmission_rcp",
    "transmission_x",
    "transmission_y",
    "total_transmission",
    "T_R_from_L",
    "T_L_from_L",
    "T_R_from_R",
    "T_L_from_R",
    "t_xx",
    "t_xy",
    "t_yx",
    "t_yy",
    "t_alpha_star_from_alpha",
    "t_beta_star_from_alpha",
    "t_alpha_star_from_beta",
    "t_beta_star_from_beta",
    "T_alpha",
    "T_beta",
    "PD",
    "target_conversion",
    "opposite_spin_leakage",
    "conversion_to_leakage_ratio",
    "spin_ER_dB",
    "gate_pass",
    "status",
    "note",
]


@dataclass(frozen=True)
class APCDGeometryValidation:
    same_cell_min_gap_nm: float
    periodic_image_min_gap_nm: float
    minimum_gap_nm: float
    minimum_allowed_gap_nm: float
    nearest_pair_description: str
    passed: bool = True


class APCDRunDiagnosticError(RuntimeError):
    def __init__(
        self,
        message: str,
        diagnostics: list[str],
        debug_fsp_path: Optional[Path] = None,
    ) -> None:
        super().__init__(message)
        self.diagnostics = diagnostics
        self.debug_fsp_path = debug_fsp_path


@dataclass(frozen=True)
class APCDSingleDimerRunner:
    config: APCDSingleDimerConfig
    dry_run: bool = False
    runtime: Optional[RuntimeConfig] = None
    setup_only: bool = False
    fsp_output: Optional[Path] = None

    @classmethod
    def from_runtime_file(
        cls,
        config: APCDSingleDimerConfig,
        runtime_path: Optional[Union[str, Path]],
        dry_run: bool,
        setup_only: bool = False,
        fsp_output: Optional[Union[str, Path]] = None,
    ) -> "APCDSingleDimerRunner":
        runtime = None if dry_run or runtime_path is None else load_runtime_config(runtime_path)
        output_path = None if fsp_output is None else Path(fsp_output)
        return cls(
            config=config,
            dry_run=dry_run,
            runtime=runtime,
            setup_only=setup_only,
            fsp_output=output_path,
        )

    def run(self) -> dict[str, object]:
        if self.dry_run:
            return build_apcd_single_dimer_dry_run_row(self.config)

        if self.runtime is None:
            raise ValueError("A runtime config is required when dry_run is False")
        if not self.runtime.enable_lumerical:
            raise RuntimeError("runtime.enable_lumerical is false; use --dry-run or update runtime.yaml")

        lumapi = import_lumapi(self.runtime)
        if self.setup_only:
            output_path = self.fsp_output or self.config.output.result_dir / "apcd_single_dimer_633nm_setup.fsp"
            return run_apcd_single_dimer_setup_only(self.config, self.runtime, lumapi, output_path)
        return run_apcd_single_dimer_lumerical(self.config, self.runtime, lumapi)


def build_apcd_single_dimer_dry_run_row(config: APCDSingleDimerConfig) -> dict[str, object]:
    return _result_row(
        config=config,
        matrix={},
        target_conversion="",
        opposite_spin_leakage="",
        ratio="",
        spin_er_db="",
        gate_pass="",
        status="dry_run",
        note="single APCD dimer setup only; lumapi was not imported",
    )


def run_apcd_single_dimer_lumerical(
    config: APCDSingleDimerConfig,
    runtime: RuntimeConfig,
    lumapi: ModuleType,
) -> dict[str, object]:
    try:
        if config.target.output_basis == "alpha_beta":
            return _run_apcd_single_dimer_alpha_beta(config, runtime, lumapi)
        if config.target.output_basis != "circular":
            raise ValueError(f"Unsupported APCD output_basis: {config.target.output_basis}")
        matrix = {
            "L": _run_one_incidence(config, runtime, lumapi, incident_polarization="LCP"),
            "R": _run_one_incidence(config, runtime, lumapi, incident_polarization="RCP"),
        }
        target_conversion = abs(matrix["L"]["R"]) ** 2
        opposite_spin_leakage = abs(matrix["R"]["R"]) ** 2 + abs(matrix["R"]["L"]) ** 2
        ratio = (target_conversion + config.target.eps) / (opposite_spin_leakage + config.target.eps)
        spin_er_db = 10 * math.log10(ratio)
        gate_pass = (
            spin_er_db > config.target.spin_er_threshold_db
            or ratio > config.target.conversion_to_leakage_threshold
        )
        return _result_row(
            config=config,
            matrix=matrix,
            target_conversion=target_conversion,
            opposite_spin_leakage=opposite_spin_leakage,
            ratio=ratio,
            spin_er_db=spin_er_db,
            gate_pass=gate_pass,
            status="ok",
            note="Circular basis convention: R=(Ex+iEy)/sqrt(2), L=(Ex-iEy)/sqrt(2)",
        )
    except APCDRunDiagnosticError as exc:
        return _result_row(
            config=config,
            matrix={},
            target_conversion="",
            opposite_spin_leakage="",
            ratio="",
            spin_er_db="",
            gate_pass=False,
            status="error",
            note=f"{type(exc).__name__}: {exc}",
            diagnostics=exc.diagnostics,
            debug_fsp_path=exc.debug_fsp_path,
        )
    except Exception as exc:
        return _result_row(
            config=config,
            matrix={},
            target_conversion="",
            opposite_spin_leakage="",
            ratio="",
            spin_er_db="",
            gate_pass=False,
            status="error",
            note=f"{type(exc).__name__}: {exc}",
        )


def run_apcd_single_dimer_setup_only(
    config: APCDSingleDimerConfig,
    runtime: RuntimeConfig,
    lumapi: ModuleType,
    fsp_output: Union[str, Path],
) -> dict[str, object]:
    fdtd = None
    output_path = Path(fsp_output)
    try:
        fdtd = lumapi.FDTD(hide=runtime.hide_gui)
        incident_polarization = "X" if config.target.output_basis == "alpha_beta" else "LCP"
        _build_apcd_single_dimer_model(fdtd, config, incident_polarization=incident_polarization)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fdtd.save(str(output_path))
        return _result_row(
            config=config,
            matrix={},
            target_conversion="",
            opposite_spin_leakage="",
            ratio="",
            spin_er_db="",
            gate_pass="",
            status="setup_only",
            note=f"model saved to {output_path}; solver was not run",
        )
    except Exception as exc:
        return _result_row(
            config=config,
            matrix={},
            target_conversion="",
            opposite_spin_leakage="",
            ratio="",
            spin_er_db="",
            gate_pass=False,
            status="error",
            note=f"{type(exc).__name__}: {exc}",
        )
    finally:
        if fdtd is not None:
            try:
                fdtd.close()
            except Exception:
                pass


def _run_apcd_single_dimer_alpha_beta(
    config: APCDSingleDimerConfig,
    runtime: RuntimeConfig,
    lumapi: ModuleType,
) -> dict[str, object]:
    if config.target.psi_deg is None or config.target.chi_deg is None:
        raise ValueError("APCD alpha/beta extraction requires target.psi_deg and target.chi_deg")
    x_response = _run_one_linear_incidence(config, runtime, lumapi, incident_polarization="X")
    y_response = _run_one_linear_incidence(config, runtime, lumapi, incident_polarization="Y")
    jones_linear = [
        [x_response["Ex"], y_response["Ex"]],
        [x_response["Ey"], y_response["Ey"]],
    ]
    jones_alpha_beta = transform_linear_jones_to_alpha_beta(
        jones_linear,
        psi_deg=config.target.psi_deg,
        chi_deg=config.target.chi_deg,
    )
    t_alpha_star_from_alpha = jones_alpha_beta[0][0]
    t_beta_star_from_alpha = jones_alpha_beta[1][0]
    t_alpha_star_from_beta = jones_alpha_beta[0][1]
    t_beta_star_from_beta = jones_alpha_beta[1][1]
    t_alpha = abs(t_alpha_star_from_alpha) ** 2 + abs(t_beta_star_from_alpha) ** 2
    t_beta = abs(t_alpha_star_from_beta) ** 2 + abs(t_beta_star_from_beta) ** 2
    pd = (t_alpha - t_beta) / (t_alpha + t_beta + config.target.eps)
    return _result_row(
        config=config,
        matrix={},
        target_conversion=t_alpha,
        opposite_spin_leakage=t_beta,
        ratio=(t_alpha + config.target.eps) / (t_beta + config.target.eps),
        spin_er_db="",
        gate_pass="",
        status="ok",
        note=(
            "APCD paper basis: J_alpha_beta rows are alpha*, beta* outputs; "
            "columns are alpha, beta inputs. Linear Jones columns came from x- and y-polarized normal incidence."
        ),
        linear_matrix={
            "x": x_response,
            "y": y_response,
        },
        alpha_beta_matrix=jones_alpha_beta,
        alpha_beta_metrics={
            "t_alpha_star_from_alpha": t_alpha_star_from_alpha,
            "t_beta_star_from_alpha": t_beta_star_from_alpha,
            "t_alpha_star_from_beta": t_alpha_star_from_beta,
            "t_beta_star_from_beta": t_beta_star_from_beta,
            "T_alpha": t_alpha,
            "T_beta": t_beta,
            "PD": pd,
        },
        diagnostics=[
            *(str(item) for item in x_response.get("diagnostics", [])),
            *(str(item) for item in y_response.get("diagnostics", [])),
        ],
    )


def _run_one_linear_incidence(
    config: APCDSingleDimerConfig,
    runtime: RuntimeConfig,
    lumapi: ModuleType,
    incident_polarization: str,
) -> dict[str, complex]:
    setup_fdtd = None
    run_fdtd = None
    diagnostics: list[str] = []
    output_dir = config.output.result_dir.resolve()
    pre_run_path = output_dir / f"pre_run_{incident_polarization.upper()}.fsp"
    debug_path = output_dir / f"debug_after_run_{incident_polarization.upper()}.fsp"

    try:
        output_dir.mkdir(parents=True, exist_ok=True)

        setup_fdtd = lumapi.FDTD(hide=runtime.hide_gui)
        _build_apcd_single_dimer_model(setup_fdtd, config, incident_polarization)
        diagnostics.extend(_model_setup_diagnostics(config, incident_polarization))
        setup_fdtd.save(str(pre_run_path))
        diagnostics.append(f"pre_run_fsp_saved={pre_run_path}")

        try:
            setup_fdtd.close()
        except Exception:
            pass
        setup_fdtd = None

        run_fdtd = lumapi.FDTD(hide=False)
        run_fdtd.load(str(pre_run_path))
        diagnostics.append(f"pre_run_fsp_loaded={pre_run_path}")

        run_fdtd.run()
        diagnostics.append(f"fdtd.run completed after loading pre-run fsp for {incident_polarization}")
        diagnostics.append("switchtolayout_after_run=False")

        ex = _extract_monitor_complex(run_fdtd, "T_fields", "Ex", diagnostics)
        ey = _extract_monitor_complex(run_fdtd, "T_fields", "Ey", diagnostics)

        transmission = _extract_power_transmission(run_fdtd, "T", diagnostics)
        raw_column_power = abs(ex) ** 2 + abs(ey) ** 2

        if raw_column_power > 0:
            scale = math.sqrt(max(transmission, 0.0) / raw_column_power)
            diagnostics.append(
                f"field_column_power_normalized: raw={raw_column_power}, "
                f"target_T={transmission}, scale={scale}"
            )
            ex *= scale
            ey *= scale
        else:
            diagnostics.append("field_column_power_normalized: skipped because raw column power is zero")

        diagnostics.extend(_collect_fdtd_diagnostics(run_fdtd))
        diagnostics.append(f"debug_after_run_save_skipped_on_success={debug_path}")

        return {"Ex": ex, "Ey": ey, "transmission": transmission, "diagnostics": diagnostics}

    except APCDRunDiagnosticError:
        raise

    except Exception as exc:
        if run_fdtd is not None:
            debug_path = _save_debug_fsp(run_fdtd, debug_path, diagnostics)
            diagnostics.extend(_collect_fdtd_diagnostics(run_fdtd))
        elif setup_fdtd is not None:
            debug_path = _save_debug_fsp(setup_fdtd, output_dir / "debug_error_state.fsp", diagnostics)

        raise APCDRunDiagnosticError(
            f"{type(exc).__name__}: {exc}",
            diagnostics=diagnostics,
            debug_fsp_path=debug_path,
        ) from exc

    finally:
        for fdtd in (setup_fdtd, run_fdtd):
            if fdtd is not None:
                try:
                    fdtd.close()
                except Exception:
                    pass


def _run_one_incidence(
    config: APCDSingleDimerConfig,
    runtime: RuntimeConfig,
    lumapi: ModuleType,
    incident_polarization: str,
) -> dict[str, complex]:
    fdtd = None
    try:
        fdtd = lumapi.FDTD(hide=runtime.hide_gui)
        _build_apcd_single_dimer_model(fdtd, config, incident_polarization)
        fdtd.run()
        transmission = _safe_float(fdtd.transmission("T"))
        ex = _center_value(_squeeze(fdtd.getdata("T_fields", "Ex")))
        ey = _center_value(_squeeze(fdtd.getdata("T_fields", "Ey")))
        e_r = (ex + 1j * ey) / math.sqrt(2)
        e_l = (ex - 1j * ey) / math.sqrt(2)
        return {"R": e_r, "L": e_l, "transmission": transmission}
    finally:
        if fdtd is not None:
            try:
                fdtd.close()
            except Exception:
                pass


def _build_apcd_single_dimer_model(
    fdtd: object,
    config: APCDSingleDimerConfig,
    incident_polarization: str,
) -> None:
    validate_apcd_single_dimer_geometry(config)

    nm = 1e-9
    geometry = config.geometry
    simulation = config.simulation
    period_x = geometry.period_x_nm * nm
    period_y = geometry.period_y_nm * nm
    height = geometry.height_nm * nm
    substrate_thickness = simulation.substrate_thickness_nm * nm
    wavelength = config.target.wavelength_nm * nm

    z_min = -substrate_thickness
    z_max = height + simulation.z_padding_above_nm * nm
    source_z = -simulation.source_offset_nm * nm
    monitor_z = height + simulation.monitor_offset_nm * nm

    fdtd.switchtolayout()
    fdtd.deleteall()

    fdtd.addfdtd()
    fdtd.set("dimension", "3D")
    fdtd.set("x span", period_x)
    fdtd.set("y span", period_y)
    fdtd.set("z min", z_min)
    fdtd.set("z max", z_max)
    fdtd.set("x min bc", "Periodic")
    fdtd.set("x max bc", "Periodic")
    fdtd.set("y min bc", "Periodic")
    fdtd.set("y max bc", "Periodic")
    fdtd.set("z min bc", "PML")
    fdtd.set("z max bc", "PML")
    fdtd.set("mesh accuracy", simulation.mesh_accuracy)
    fdtd.set("simulation time", simulation.simulation_time_fs * 1e-15)

    fdtd.addrect()
    fdtd.set("name", "substrate")
    fdtd.set("x span", period_x)
    fdtd.set("y span", period_y)
    fdtd.set("z min", z_min)
    fdtd.set("z max", 0)
    _set_material(fdtd, config.material, is_substrate=True)

    for name, pillar in _apcd_nanopillars(config):
        _add_nanopillar(fdtd, config, pillar, name)
    _add_plane_wave_sources(fdtd, config, incident_polarization, period_x, period_y, source_z, wavelength)

    fdtd.addpower()
    fdtd.set("name", "T")
    fdtd.set("monitor type", "2D Z-normal")
    fdtd.set("x span", period_x)
    fdtd.set("y span", period_y)
    fdtd.set("z", monitor_z)

    fdtd.addprofile()
    fdtd.set("name", "T_fields")
    fdtd.set("monitor type", "2D Z-normal")
    fdtd.set("x span", period_x)
    fdtd.set("y span", period_y)
    fdtd.set("z", monitor_z)


def _add_nanopillar(
    fdtd: object,
    config: APCDSingleDimerConfig,
    pillar: APCDNanopillarConfig,
    name: str,
) -> None:
    nm = 1e-9
    shape = _normalized_pillar_shape(pillar)
    if shape == "rectangle":
        fdtd.addrect()
    else:
        fdtd.addpoly()
    fdtd.set("name", name)
    fdtd.set("x", pillar.x_nm * nm)
    fdtd.set("y", pillar.y_nm * nm)
    if shape == "rectangle":
        fdtd.set("x span", pillar.length_nm * nm)
        fdtd.set("y span", pillar.width_nm * nm)
    else:
        fdtd.set("vertices", np.array([[x * nm, y * nm] for x, y in _local_pillar_polygon_nm(pillar)], dtype=float))
    fdtd.set("z min", 0)
    fdtd.set("z max", config.geometry.height_nm * nm)
    fdtd.set("first axis", "z")
    fdtd.set("rotation 1", pillar.rotation_deg)
    _set_material(fdtd, config.material, is_substrate=False)


def validate_apcd_single_dimer_geometry(config: APCDSingleDimerConfig) -> APCDGeometryValidation:
    geometry = config.geometry
    polygons = {name: _pillar_polygon_nm(pillar) for name, pillar in _apcd_nanopillars(config)}

    same_cell_gap_nm = math.inf
    same_cell_pair = ""
    polygon_items = list(polygons.items())
    for index, (name_a, poly_a) in enumerate(polygon_items):
        for name_b, poly_b in polygon_items[index + 1 :]:
            gap_nm = _polygon_gap_nm(poly_a, poly_b)
            if gap_nm < same_cell_gap_nm:
                same_cell_gap_nm = gap_nm
                same_cell_pair = f"{name_a} to {name_b} in same periodic cell"
    minimum_gap_nm = same_cell_gap_nm
    nearest_pair = same_cell_pair

    periodic_gap_nm = math.inf
    nearest_periodic_pair = ""
    for shift_x, shift_y in _periodic_neighbor_shifts_nm(geometry.period_x_nm, geometry.period_y_nm):
        for central_name, central_polygon in polygons.items():
            for image_name, image_polygon in polygons.items():
                shifted_image = [(x + shift_x, y + shift_y) for x, y in image_polygon]
                gap_nm = _polygon_gap_nm(central_polygon, shifted_image)
                if gap_nm < periodic_gap_nm:
                    periodic_gap_nm = gap_nm
                    nearest_periodic_pair = (
                        f"{central_name} to {image_name} periodic image "
                        f"({shift_x:g}, {shift_y:g}) nm"
                    )

    if periodic_gap_nm < minimum_gap_nm:
        minimum_gap_nm = periodic_gap_nm
        nearest_pair = nearest_periodic_pair

    if minimum_gap_nm <= 0:
        raise ValueError(f"APCD periodic unit-cell geometry overlaps: {nearest_pair}")
    if minimum_gap_nm < geometry.minimum_gap_nm:
        raise ValueError(
            "APCD periodic unit-cell geometry gap is too small: "
            f"{minimum_gap_nm:.3g} nm < {geometry.minimum_gap_nm:.3g} nm ({nearest_pair})"
        )

    return APCDGeometryValidation(
        same_cell_min_gap_nm=same_cell_gap_nm,
        periodic_image_min_gap_nm=periodic_gap_nm,
        minimum_gap_nm=minimum_gap_nm,
        minimum_allowed_gap_nm=geometry.minimum_gap_nm,
        nearest_pair_description=nearest_pair,
    )


def _apcd_nanopillars(config: APCDSingleDimerConfig) -> list[tuple[str, APCDNanopillarConfig]]:
    pillars = [
        ("nanopillar_1", config.geometry.nanopillar_1),
        ("nanopillar_2", config.geometry.nanopillar_2),
    ]
    if config.geometry.nanopillar_helper is not None:
        pillars.append(("nanopillar_helper", config.geometry.nanopillar_helper))
    return pillars


def _periodic_neighbor_shifts_nm(period_x_nm: float, period_y_nm: float) -> list[tuple[float, float]]:
    return [
        (-period_x_nm, -period_y_nm),
        (-period_x_nm, 0),
        (-period_x_nm, period_y_nm),
        (0, -period_y_nm),
        (0, period_y_nm),
        (period_x_nm, -period_y_nm),
        (period_x_nm, 0),
        (period_x_nm, period_y_nm),
    ]


def _rotated_rectangle_corners_nm(pillar: APCDNanopillarConfig) -> list[tuple[float, float]]:
    return _rotate_and_translate_polygon_nm(pillar, _local_rectangle_corners_nm(pillar.length_nm, pillar.width_nm))


def _pillar_polygon_nm(pillar: APCDNanopillarConfig) -> list[tuple[float, float]]:
    return _rotate_and_translate_polygon_nm(pillar, _local_pillar_polygon_nm(pillar))


def _normalized_pillar_shape(pillar: APCDNanopillarConfig) -> str:
    shape = str(getattr(pillar, "shape", "rectangle")).strip().lower().replace("-", "_")
    aliases = {
        "rect": "rectangle",
        "rounded": "rounded_rectangle",
        "rounded_rect": "rounded_rectangle",
        "racetrack": "capsule",
        "capsule_core": "capsule",
        "ellipse_core": "ellipse",
        "elliptical": "ellipse",
        "chamfered": "chamfered_rectangle",
        "chamfered_rect": "chamfered_rectangle",
        "notch": "notched_rectangle",
        "notched": "notched_rectangle",
        "notched_rect": "notched_rectangle",
        "slot": "notched_rectangle",
        "slotted_rectangle": "notched_rectangle",
        "slotted_rect": "notched_rectangle",
    }
    shape = aliases.get(shape, shape)
    supported = {
        "rectangle",
        "ellipse",
        "rounded_rectangle",
        "capsule",
        "chamfered_rectangle",
        "notched_rectangle",
    }
    if shape not in supported:
        raise ValueError(f"Unsupported APCD nanopillar shape: {pillar.shape}")
    return shape


def _local_pillar_polygon_nm(pillar: APCDNanopillarConfig) -> list[tuple[float, float]]:
    shape = _normalized_pillar_shape(pillar)
    if shape == "rectangle":
        return _local_rectangle_corners_nm(pillar.length_nm, pillar.width_nm)
    if shape == "ellipse":
        return _local_ellipse_polygon_nm(pillar.length_nm, pillar.width_nm, pillar.polygon_sides)
    if shape == "rounded_rectangle":
        radius = _bounded_shape_distance(
            pillar.corner_radius_nm,
            default=min(pillar.length_nm, pillar.width_nm) * 0.18,
            limit=min(pillar.length_nm, pillar.width_nm) / 2,
        )
        return _local_rounded_rectangle_polygon_nm(pillar.length_nm, pillar.width_nm, radius, pillar.polygon_sides)
    if shape == "capsule":
        return _local_capsule_polygon_nm(pillar.length_nm, pillar.width_nm, pillar.polygon_sides)
    if shape == "chamfered_rectangle":
        chamfer = _bounded_shape_distance(
            pillar.chamfer_nm,
            default=min(pillar.length_nm, pillar.width_nm) * 0.12,
            limit=min(pillar.length_nm, pillar.width_nm) / 2,
        )
        return _local_chamfered_rectangle_polygon_nm(pillar.length_nm, pillar.width_nm, chamfer)
    if shape == "notched_rectangle":
        depth = _bounded_shape_distance(
            pillar.notch_depth_nm,
            default=min(pillar.length_nm, pillar.width_nm) * 0.12,
            limit=pillar.length_nm / 3,
        )
        notch_width = _bounded_shape_distance(
            pillar.notch_width_nm,
            default=pillar.width_nm * 0.35,
            limit=pillar.width_nm * 0.8,
        )
        return _local_notched_rectangle_polygon_nm(
            pillar.length_nm,
            pillar.width_nm,
            depth,
            notch_width,
            pillar.notch_side,
        )
    raise ValueError(f"Unsupported APCD nanopillar shape: {pillar.shape}")


def _local_rectangle_corners_nm(length_nm: float, width_nm: float) -> list[tuple[float, float]]:
    half_length = length_nm / 2
    half_width = width_nm / 2
    return [
        (-half_length, -half_width),
        (half_length, -half_width),
        (half_length, half_width),
        (-half_length, half_width),
    ]


def _local_ellipse_polygon_nm(length_nm: float, width_nm: float, polygon_sides: int) -> list[tuple[float, float]]:
    sides = max(16, int(polygon_sides))
    half_length = length_nm / 2
    half_width = width_nm / 2
    return [
        (
            half_length * math.cos(2 * math.pi * index / sides),
            half_width * math.sin(2 * math.pi * index / sides),
        )
        for index in range(sides)
    ]


def _local_rounded_rectangle_polygon_nm(
    length_nm: float,
    width_nm: float,
    radius_nm: float,
    polygon_sides: int,
) -> list[tuple[float, float]]:
    half_length = length_nm / 2
    half_width = width_nm / 2
    radius = max(0.0, min(radius_nm, half_length, half_width))
    if radius <= 0:
        return _local_rectangle_corners_nm(length_nm, width_nm)
    arc_steps = max(4, int(polygon_sides) // 8)
    centers = [
        (half_length - radius, half_width - radius, 0.0),
        (-(half_length - radius), half_width - radius, math.pi / 2),
        (-(half_length - radius), -(half_width - radius), math.pi),
        (half_length - radius, -(half_width - radius), 3 * math.pi / 2),
    ]
    points: list[tuple[float, float]] = []
    for cx, cy, start in centers:
        for step in range(arc_steps + 1):
            angle = start + step * (math.pi / 2) / arc_steps
            points.append((cx + radius * math.cos(angle), cy + radius * math.sin(angle)))
    return points


def _local_capsule_polygon_nm(length_nm: float, width_nm: float, polygon_sides: int) -> list[tuple[float, float]]:
    sides = max(16, int(polygon_sides))
    points: list[tuple[float, float]] = []
    if length_nm >= width_nm:
        radius = width_nm / 2
        center_offset = max(0.0, length_nm / 2 - radius)
        half_steps = max(8, sides // 2)
        for step in range(half_steps + 1):
            angle = -math.pi / 2 + step * math.pi / half_steps
            points.append((center_offset + radius * math.cos(angle), radius * math.sin(angle)))
        for step in range(half_steps + 1):
            angle = math.pi / 2 + step * math.pi / half_steps
            points.append((-center_offset + radius * math.cos(angle), radius * math.sin(angle)))
    else:
        radius = length_nm / 2
        center_offset = max(0.0, width_nm / 2 - radius)
        half_steps = max(8, sides // 2)
        for step in range(half_steps + 1):
            angle = step * math.pi / half_steps
            points.append((radius * math.cos(angle), center_offset + radius * math.sin(angle)))
        for step in range(half_steps + 1):
            angle = math.pi + step * math.pi / half_steps
            points.append((radius * math.cos(angle), -center_offset + radius * math.sin(angle)))
    return points


def _local_chamfered_rectangle_polygon_nm(
    length_nm: float,
    width_nm: float,
    chamfer_nm: float,
) -> list[tuple[float, float]]:
    half_length = length_nm / 2
    half_width = width_nm / 2
    chamfer = max(0.0, min(chamfer_nm, half_length, half_width))
    if chamfer <= 0:
        return _local_rectangle_corners_nm(length_nm, width_nm)
    return [
        (-half_length + chamfer, -half_width),
        (half_length - chamfer, -half_width),
        (half_length, -half_width + chamfer),
        (half_length, half_width - chamfer),
        (half_length - chamfer, half_width),
        (-half_length + chamfer, half_width),
        (-half_length, half_width - chamfer),
        (-half_length, -half_width + chamfer),
    ]


def _local_notched_rectangle_polygon_nm(
    length_nm: float,
    width_nm: float,
    notch_depth_nm: float,
    notch_width_nm: float,
    notch_side: str | None,
) -> list[tuple[float, float]]:
    half_length = length_nm / 2
    half_width = width_nm / 2
    depth = max(0.0, min(notch_depth_nm, length_nm / 3))
    notch_half_width = max(0.0, min(notch_width_nm / 2, half_width * 0.8))
    side = "right" if notch_side is None else str(notch_side).strip().lower()
    if depth <= 0 or notch_half_width <= 0:
        return _local_rectangle_corners_nm(length_nm, width_nm)
    if side in {"right", "+x", "x+"}:
        return [
            (-half_length, -half_width),
            (half_length, -half_width),
            (half_length, -notch_half_width),
            (half_length - depth, -notch_half_width),
            (half_length - depth, notch_half_width),
            (half_length, notch_half_width),
            (half_length, half_width),
            (-half_length, half_width),
        ]
    if side in {"left", "-x", "x-"}:
        return [
            (-half_length, -half_width),
            (half_length, -half_width),
            (half_length, half_width),
            (-half_length, half_width),
            (-half_length, notch_half_width),
            (-half_length + depth, notch_half_width),
            (-half_length + depth, -notch_half_width),
            (-half_length, -notch_half_width),
        ]
    if side in {"top", "+y", "y+"}:
        return [
            (-half_length, -half_width),
            (half_length, -half_width),
            (half_length, half_width),
            (notch_half_width, half_width),
            (notch_half_width, half_width - depth),
            (-notch_half_width, half_width - depth),
            (-notch_half_width, half_width),
            (-half_length, half_width),
        ]
    if side in {"bottom", "-y", "y-"}:
        return [
            (-half_length, -half_width),
            (-notch_half_width, -half_width),
            (-notch_half_width, -half_width + depth),
            (notch_half_width, -half_width + depth),
            (notch_half_width, -half_width),
            (half_length, -half_width),
            (half_length, half_width),
            (-half_length, half_width),
        ]
    raise ValueError(f"Unsupported notch_side: {notch_side}")


def _bounded_shape_distance(value: float | None, *, default: float, limit: float) -> float:
    selected = default if value is None else float(value)
    return max(0.0, min(selected, limit))


def _rotate_and_translate_polygon_nm(
    pillar: APCDNanopillarConfig,
    local_polygon: list[tuple[float, float]],
) -> list[tuple[float, float]]:
    angle = math.radians(pillar.rotation_deg)
    cos_angle = math.cos(angle)
    sin_angle = math.sin(angle)
    corners = []
    for local_x, local_y in local_polygon:
        corners.append(
            (
                pillar.x_nm + local_x * cos_angle - local_y * sin_angle,
                pillar.y_nm + local_x * sin_angle + local_y * cos_angle,
            )
        )
    return corners


def _polygon_gap_nm(polygon_1: list[tuple[float, float]], polygon_2: list[tuple[float, float]]) -> float:
    if _polygons_overlap(polygon_1, polygon_2):
        return 0.0

    minimum = math.inf
    for index_1, point_1 in enumerate(polygon_1):
        next_1 = polygon_1[(index_1 + 1) % len(polygon_1)]
        for index_2, point_2 in enumerate(polygon_2):
            next_2 = polygon_2[(index_2 + 1) % len(polygon_2)]
            minimum = min(minimum, _segment_distance_nm(point_1, next_1, point_2, next_2))
    return float(minimum)


def _polygons_overlap(polygon_1: list[tuple[float, float]], polygon_2: list[tuple[float, float]]) -> bool:
    for polygon in (polygon_1, polygon_2):
        for index, point in enumerate(polygon):
            next_point = polygon[(index + 1) % len(polygon)]
            edge = (next_point[0] - point[0], next_point[1] - point[1])
            axis = (-edge[1], edge[0])
            axis_length = math.hypot(axis[0], axis[1])
            normalized_axis = (axis[0] / axis_length, axis[1] / axis_length)
            projection_1 = [_dot(point_1, normalized_axis) for point_1 in polygon_1]
            projection_2 = [_dot(point_2, normalized_axis) for point_2 in polygon_2]
            if max(projection_1) < min(projection_2) or max(projection_2) < min(projection_1):
                return False
    return True


def _segment_distance_nm(
    point_1: tuple[float, float],
    point_2: tuple[float, float],
    point_3: tuple[float, float],
    point_4: tuple[float, float],
) -> float:
    if _segments_intersect(point_1, point_2, point_3, point_4):
        return 0.0
    return min(
        _point_segment_distance_nm(point_1, point_3, point_4),
        _point_segment_distance_nm(point_2, point_3, point_4),
        _point_segment_distance_nm(point_3, point_1, point_2),
        _point_segment_distance_nm(point_4, point_1, point_2),
    )


def _segments_intersect(
    point_1: tuple[float, float],
    point_2: tuple[float, float],
    point_3: tuple[float, float],
    point_4: tuple[float, float],
) -> bool:
    orientation_1 = _orientation(point_1, point_2, point_3)
    orientation_2 = _orientation(point_1, point_2, point_4)
    orientation_3 = _orientation(point_3, point_4, point_1)
    orientation_4 = _orientation(point_3, point_4, point_2)
    eps = 1e-9
    if (
        orientation_1 * orientation_2 < -eps
        and orientation_3 * orientation_4 < -eps
    ):
        return True
    if abs(orientation_1) <= eps and _point_on_segment(point_3, point_1, point_2):
        return True
    if abs(orientation_2) <= eps and _point_on_segment(point_4, point_1, point_2):
        return True
    if abs(orientation_3) <= eps and _point_on_segment(point_1, point_3, point_4):
        return True
    if abs(orientation_4) <= eps and _point_on_segment(point_2, point_3, point_4):
        return True
    return False


def _point_on_segment(
    point: tuple[float, float],
    segment_start: tuple[float, float],
    segment_end: tuple[float, float],
) -> bool:
    return (
        min(segment_start[0], segment_end[0]) - 1e-9
        <= point[0]
        <= max(segment_start[0], segment_end[0]) + 1e-9
        and min(segment_start[1], segment_end[1]) - 1e-9
        <= point[1]
        <= max(segment_start[1], segment_end[1]) + 1e-9
    )


def _point_segment_distance_nm(
    point: tuple[float, float],
    segment_start: tuple[float, float],
    segment_end: tuple[float, float],
) -> float:
    segment = (segment_end[0] - segment_start[0], segment_end[1] - segment_start[1])
    segment_length_sq = _dot(segment, segment)
    if segment_length_sq == 0:
        return math.hypot(point[0] - segment_start[0], point[1] - segment_start[1])
    offset = (point[0] - segment_start[0], point[1] - segment_start[1])
    t = max(0.0, min(1.0, _dot(offset, segment) / segment_length_sq))
    closest = (segment_start[0] + t * segment[0], segment_start[1] + t * segment[1])
    return math.hypot(point[0] - closest[0], point[1] - closest[1])


def _orientation(
    point_1: tuple[float, float],
    point_2: tuple[float, float],
    point_3: tuple[float, float],
) -> float:
    return (point_2[0] - point_1[0]) * (point_3[1] - point_1[1]) - (
        point_2[1] - point_1[1]
    ) * (point_3[0] - point_1[0])


def _dot(point_1: tuple[float, float], point_2: tuple[float, float]) -> float:
    return point_1[0] * point_2[0] + point_1[1] * point_2[1]


def _add_plane_wave_sources(
    fdtd: object,
    config: APCDSingleDimerConfig,
    incident_polarization: str,
    x_span: float,
    y_span: float,
    z: float,
    wavelength: float,
) -> None:
    normalized = incident_polarization.lower()
    if normalized not in {"lcp", "rcp", "x", "y"}:
        raise ValueError(f"Unsupported incident polarization: {incident_polarization}")
    if normalized in {"x", "y"}:
        source_specs = ((f"source_{normalized}", 0 if normalized == "x" else 90, 0, 1),)
    else:
        y_phase_deg = 90 if normalized == "lcp" else -90
        amplitude = 1 / math.sqrt(2)
        source_specs = (
            ("source_x", 0, 0, amplitude),
            ("source_y", 90, y_phase_deg, amplitude),
        )
    for name, polarization_angle, phase, amplitude in source_specs:
        fdtd.addplane()
        fdtd.set("name", name)
        fdtd.set("injection axis", "z")
        fdtd.set("direction", "Forward")
        fdtd.set("x span", x_span)
        fdtd.set("y span", y_span)
        fdtd.set("z", z)
        fdtd.set("wavelength start", wavelength)
        fdtd.set("wavelength stop", wavelength)
        fdtd.set("polarization angle", polarization_angle)
        fdtd.set("phase", phase)
        fdtd.set("amplitude", amplitude)


def _model_setup_diagnostics(config: APCDSingleDimerConfig, incident_polarization: str) -> list[str]:
    return [
        f"incident_polarization={incident_polarization}",
        "expected_power_monitor=T",
        "expected_field_monitor=T_fields",
        f"output_basis={config.target.output_basis}",
        f"result_dir={config.output.result_dir}",
    ]


def _collect_fdtd_diagnostics(fdtd: object) -> list[str]:
    diagnostics = []
    for probe_name, probe in (
        ("objects", lambda: _try_fdtd_eval(fdtd, "?getnamed;")),
        ("T_result_probe", lambda: _try_getresult(fdtd, "T", "T")),
        ("T_fields_E_result_probe", lambda: _try_getresult(fdtd, "T_fields", "E")),
        ("T_fields_Ex_probe", lambda: _try_getdata_shape(fdtd, "T_fields", "Ex")),
        ("T_fields_Ey_probe", lambda: _try_getdata_shape(fdtd, "T_fields", "Ey")),
    ):
        diagnostics.append(f"{probe_name}: {probe()}")
    return diagnostics


def _try_fdtd_eval(fdtd: object, command: str) -> str:
    try:
        if hasattr(fdtd, "eval"):
            value = fdtd.eval(command)
            return _short_diagnostic_value(value)
        return "not available: fdtd.eval missing"
    except Exception as exc:
        return f"{type(exc).__name__}: {exc}"


def _try_getresult(fdtd: object, monitor_name: str, result_name: str) -> str:
    try:
        if hasattr(fdtd, "getresult"):
            value = fdtd.getresult(monitor_name, result_name)
            return _short_diagnostic_value(value)
        return "not available: fdtd.getresult missing"
    except Exception as exc:
        return f"{type(exc).__name__}: {exc}"


def _try_getdata_shape(fdtd: object, monitor_name: str, data_name: str) -> str:
    try:
        value = fdtd.getdata(monitor_name, data_name)
        shape = _shape_of(_squeeze(value))
        return f"available shape={shape}"
    except Exception as exc:
        return f"{type(exc).__name__}: {exc}"


def _extract_monitor_complex(
    fdtd: object,
    monitor_name: str,
    data_name: str,
    diagnostics: list[str],
) -> complex:
    try:
        value = fdtd.getdata(monitor_name, data_name)
        diagnostics.append(f"{monitor_name}.{data_name}: getdata succeeded")
        return _center_value(_squeeze(value))
    except Exception as exc:
        diagnostics.append(f"{monitor_name}.{data_name}: getdata failed: {type(exc).__name__}: {exc}")
    try:
        result = fdtd.getresult(monitor_name, "E")
        component = _component_from_monitor_result(result, data_name)
        diagnostics.append(f"{monitor_name}.{data_name}: getresult('E') fallback succeeded")
        return _center_value(_squeeze(component))
    except Exception as exc:
        diagnostics.append(f"{monitor_name}.{data_name}: getresult('E') fallback failed: {type(exc).__name__}: {exc}")
        raise


def _extract_power_transmission(
    fdtd: object,
    monitor_name: str,
    diagnostics: list[str],
) -> float:
    try:
        result = fdtd.getresult(monitor_name, "T")
        if isinstance(result, dict) and "T" in result:
            value = _squeeze(result["T"])
        else:
            value = _squeeze(result)

        if hasattr(value, "item"):
            transmission = float(value.item())
        elif isinstance(value, (list, tuple)):
            current = value
            while isinstance(current, (list, tuple)):
                current = current[0]
            transmission = float(current)
        else:
            transmission = float(value)

        diagnostics.append(f"{monitor_name}.T: power transmission extracted={transmission}")
        return transmission

    except Exception as exc:
        diagnostics.append(f"{monitor_name}.T: getresult('T') failed: {type(exc).__name__}: {exc}")

    try:
        value = fdtd.transmission(monitor_name)
        if hasattr(value, "item"):
            transmission = float(value.item())
        else:
            transmission = float(value)
        diagnostics.append(f"{monitor_name}.T: fdtd.transmission fallback extracted={transmission}")
        return transmission
    except Exception as exc:
        diagnostics.append(f"{monitor_name}.T: fdtd.transmission fallback failed: {type(exc).__name__}: {exc}")
        raise


def _component_from_monitor_result(result: object, data_name: str) -> object:
    if isinstance(result, dict) and data_name in result:
        return result[data_name]
    if hasattr(result, data_name):
        return getattr(result, data_name)
    try:
        return result[data_name]  # type: ignore[index]
    except Exception as exc:
        raise KeyError(f"{data_name} not found in T_fields E result") from exc


def _save_debug_fsp(fdtd: object, debug_path: Path, diagnostics: list[str]) -> Path:
    try:
        debug_path.parent.mkdir(parents=True, exist_ok=True)
        fdtd.save(str(debug_path))
        diagnostics.append(f"debug_fsp_saved={debug_path}")
    except Exception as exc:
        diagnostics.append(f"debug_fsp_save_failed={type(exc).__name__}: {exc}")
    return debug_path


def _short_diagnostic_value(value: object) -> str:
    if value is None:
        return "ok"
    text = str(value)
    if len(text) > 500:
        return text[:500] + "...<truncated>"
    return text


def apcd_alpha_beta_basis(psi_deg: float, chi_deg: float) -> dict[str, tuple[complex, complex]]:
    psi = math.radians(psi_deg)
    chi = math.radians(chi_deg)
    alpha = (
        math.cos(chi) * math.cos(psi) - 1j * math.sin(chi) * math.sin(psi),
        math.cos(chi) * math.sin(psi) + 1j * math.sin(chi) * math.cos(psi),
    )
    beta = (-alpha[1].conjugate(), alpha[0].conjugate())
    return {
        "alpha": alpha,
        "beta": beta,
        "alpha_star": (alpha[0].conjugate(), alpha[1].conjugate()),
        "beta_star": (beta[0].conjugate(), beta[1].conjugate()),
    }


def transform_linear_jones_to_alpha_beta(
    jones_linear: list[list[complex]],
    *,
    psi_deg: float,
    chi_deg: float,
) -> list[list[complex]]:
    basis = apcd_alpha_beta_basis(psi_deg, chi_deg)
    input_basis = [basis["alpha"], basis["beta"]]
    output_basis = [basis["alpha_star"], basis["beta_star"]]
    transformed: list[list[complex]] = []
    for output_vector in output_basis:
        row = []
        for input_vector in input_basis:
            linear_output = _matrix_vector_product(jones_linear, input_vector)
            row.append(_inner_product(output_vector, linear_output))
        transformed.append(row)
    return transformed


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


def _set_material(fdtd: object, material: APCDDimerMaterialConfig, is_substrate: bool) -> None:
    material_name = material.substrate_material_lumerical if is_substrate else material.meta_material_lumerical
    material_index = material.substrate_index if is_substrate else material.meta_index
    fdtd.set("material", material_name)
    if material_name == "<Object defined dielectric>" and material_index is not None:
        fdtd.set("index", material_index)


def _result_row(
    config: APCDSingleDimerConfig,
    matrix: dict[str, dict[str, complex]],
    target_conversion: object,
    opposite_spin_leakage: object,
    ratio: object,
    spin_er_db: object,
    gate_pass: object,
    status: str,
    note: str,
    linear_matrix: Optional[dict[str, dict[str, complex]]] = None,
    alpha_beta_matrix: Optional[list[list[complex]]] = None,
    alpha_beta_metrics: Optional[dict[str, object]] = None,
    diagnostics: Optional[list[str]] = None,
    debug_fsp_path: Optional[Path] = None,
) -> dict[str, object]:
    geometry_validation = _safe_geometry_validation(config)
    linear_matrix = linear_matrix or {}
    alpha_beta_matrix = alpha_beta_matrix or [["", ""], ["", ""]]
    alpha_beta_metrics = alpha_beta_metrics or {}
    return {
        "wavelength_nm": config.target.wavelength_nm,
        "period_x_nm": config.geometry.period_x_nm,
        "period_y_nm": config.geometry.period_y_nm,
        "height_nm": config.geometry.height_nm,
        "target_polarization_type": config.target.target_polarization_type,
        "psi_deg": config.target.psi_deg if config.target.psi_deg is not None else "",
        "chi_deg": config.target.chi_deg if config.target.chi_deg is not None else "",
        "transmission_lcp": matrix.get("L", {}).get("transmission", ""),
        "transmission_rcp": matrix.get("R", {}).get("transmission", ""),
        "transmission_x": linear_matrix.get("x", {}).get("transmission", ""),
        "transmission_y": linear_matrix.get("y", {}).get("transmission", ""),
        "total_transmission": _mean_transmission(matrix) if matrix else _mean_transmission(linear_matrix),
        "T_R_from_L": _complex_text(matrix.get("L", {}).get("R", "")),
        "T_L_from_L": _complex_text(matrix.get("L", {}).get("L", "")),
        "T_R_from_R": _complex_text(matrix.get("R", {}).get("R", "")),
        "T_L_from_R": _complex_text(matrix.get("R", {}).get("L", "")),
        "t_xx": _complex_text(linear_matrix.get("x", {}).get("Ex", "")),
        "t_xy": _complex_text(linear_matrix.get("y", {}).get("Ex", "")),
        "t_yx": _complex_text(linear_matrix.get("x", {}).get("Ey", "")),
        "t_yy": _complex_text(linear_matrix.get("y", {}).get("Ey", "")),
        "t_alpha_star_from_alpha": _complex_text(alpha_beta_matrix[0][0]),
        "t_beta_star_from_alpha": _complex_text(alpha_beta_matrix[1][0]),
        "t_alpha_star_from_beta": _complex_text(alpha_beta_matrix[0][1]),
        "t_beta_star_from_beta": _complex_text(alpha_beta_matrix[1][1]),
        "T_alpha": alpha_beta_metrics.get("T_alpha", ""),
        "T_beta": alpha_beta_metrics.get("T_beta", ""),
        "PD": alpha_beta_metrics.get("PD", ""),
        "target_conversion": target_conversion,
        "opposite_spin_leakage": opposite_spin_leakage,
        "conversion_to_leakage_ratio": ratio,
        "spin_ER_dB": spin_er_db,
        "gate_pass": gate_pass,
        "status": status,
        "note": note,
        "_config": config,
        "_geometry_validation": geometry_validation,
        "_jones_matrix_linear_basis": _linear_matrix_values(linear_matrix),
        "_jones_matrix_alpha_beta_basis": alpha_beta_matrix,
        "_diagnostics": diagnostics or [],
        "_debug_fsp_path": debug_fsp_path,
    }


def _linear_matrix_values(linear_matrix: dict[str, dict[str, complex]]) -> list[list[complex]]:
    if not linear_matrix:
        return [["", ""], ["", ""]]
    return [
        [linear_matrix.get("x", {}).get("Ex", ""), linear_matrix.get("y", {}).get("Ex", "")],
        [linear_matrix.get("x", {}).get("Ey", ""), linear_matrix.get("y", {}).get("Ey", "")],
    ]


def _safe_geometry_validation(config: APCDSingleDimerConfig) -> APCDGeometryValidation | None:
    try:
        return validate_apcd_single_dimer_geometry(config)
    except ValueError:
        return None


def jones_matrix_circular_basis(row: dict[str, object]) -> list[list[complex]]:
    return [
        [_parse_complex(row["T_R_from_L"]), _parse_complex(row["T_R_from_R"])],
        [_parse_complex(row["T_L_from_L"]), _parse_complex(row["T_L_from_R"])],
    ]


def jones_matrix_linear_basis(row: dict[str, object]) -> list[list[complex]]:
    matrix = row.get("_jones_matrix_linear_basis")
    if _is_complex_matrix(matrix):
        return matrix  # type: ignore[return-value]
    return [
        [_parse_complex(row["t_xx"]), _parse_complex(row["t_xy"])],
        [_parse_complex(row["t_yx"]), _parse_complex(row["t_yy"])],
    ]


def jones_matrix_alpha_beta_basis(row: dict[str, object]) -> list[list[complex]]:
    matrix = row.get("_jones_matrix_alpha_beta_basis")
    if _is_complex_matrix(matrix):
        return matrix  # type: ignore[return-value]
    return [
        [_parse_complex(row["t_alpha_star_from_alpha"]), _parse_complex(row["t_alpha_star_from_beta"])],
        [_parse_complex(row["t_beta_star_from_alpha"]), _parse_complex(row["t_beta_star_from_beta"])],
    ]


def _is_complex_matrix(value: object) -> bool:
    return (
        isinstance(value, list)
        and len(value) == 2
        and all(isinstance(row, list) and len(row) == 2 for row in value)
        and all(value[row][column] != "" for row in range(2) for column in range(2))
    )


def write_apcd_single_dimer_results(row: dict[str, object], output_path: Union[str, Path]) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=APCD_DIMER_RESULT_FIELDS)
        writer.writeheader()
        writer.writerow({field: row.get(field, "") for field in APCD_DIMER_RESULT_FIELDS})
    return path


def write_apcd_single_dimer_summary(row: dict[str, object], output_path: Union[str, Path]) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    config = row.get("_config")
    validation = row.get("_geometry_validation")
    lines = [
        "# APCD Periodic Unit-Cell 633 nm Summary",
        "",
        f"- status: {row['status']}",
        f"- target_conversion: {row['target_conversion']}",
        f"- opposite_spin_leakage: {row['opposite_spin_leakage']}",
        f"- conversion_to_leakage_ratio: {row['conversion_to_leakage_ratio']}",
        f"- spin_ER_dB: {row['spin_ER_dB']}",
        f"- t_alpha_star_from_alpha: {row['t_alpha_star_from_alpha']}",
        f"- t_beta_star_from_alpha: {row['t_beta_star_from_alpha']}",
        f"- t_alpha_star_from_beta: {row['t_alpha_star_from_beta']}",
        f"- t_beta_star_from_beta: {row['t_beta_star_from_beta']}",
        f"- T_alpha: {row['T_alpha']}",
        f"- T_beta: {row['T_beta']}",
        f"- PD: {row['PD']}",
        f"- total_transmission: {row['total_transmission']}",
        f"- gate_pass: {row['gate_pass']}",
        f"- note: {row['note']}",
    ]
    if isinstance(config, APCDSingleDimerConfig):
        p1 = config.geometry.nanopillar_1
        p2 = config.geometry.nanopillar_2
        helper = config.geometry.nanopillar_helper
        lines.extend(
            [
                "",
                "Geometry:",
                "",
                "- model: periodic APCD unit cell with one dimerized metamolecule; x/y boundaries are periodic, z boundaries are PML.",
                f"- layout_mode: {config.geometry.layout_mode}",
                f"- period_x_nm: {config.geometry.period_x_nm}",
                f"- period_y_nm: {config.geometry.period_y_nm}",
                f"- height_nm: {config.geometry.height_nm}",
                f"- material: {config.material.meta_material} on {config.material.substrate}",
                (
                    "- nanopillar_1: "
                    f"frac=({p1.frac_x}, {p1.frac_y}), "
                    f"x_nm={p1.x_nm}, y_nm={p1.y_nm}, "
                    f"length_nm={p1.length_nm}, width_nm={p1.width_nm}, "
                    f"rotation_deg={p1.rotation_deg}, rotation_rule={p1.rotation_rule}"
                ),
                (
                    "- nanopillar_2: "
                    f"frac=({p2.frac_x}, {p2.frac_y}), "
                    f"x_nm={p2.x_nm}, y_nm={p2.y_nm}, "
                    f"length_nm={p2.length_nm}, width_nm={p2.width_nm}, "
                    f"rotation_deg={p2.rotation_deg}, rotation_rule={p2.rotation_rule}"
                ),
                (
                    "- nanopillar_helper: none"
                    if helper is None
                    else "- nanopillar_helper: "
                    f"role={helper.role}, frac=({helper.frac_x}, {helper.frac_y}), "
                    f"x_nm={helper.x_nm}, y_nm={helper.y_nm}, "
                    f"length_nm={helper.length_nm}, width_nm={helper.width_nm}, "
                    f"rotation_deg={helper.rotation_deg}, rotation_rule={helper.rotation_rule}"
                ),
                "- rotation_note: no 180-degree angle folding is applied in the generated setup.",
                "- boundary_note: near a periodic boundary is not automatically wrong; overlap or too-small gap to periodic images is what fails validation.",
            ]
        )
    if isinstance(validation, APCDGeometryValidation):
        lines.extend(
            [
                "",
                "Geometry validation:",
                "",
                f"- same_cell_min_gap_nm: {validation.same_cell_min_gap_nm}",
                f"- periodic_image_min_gap_nm: {validation.periodic_image_min_gap_nm}",
                f"- nearest_pair_description: {validation.nearest_pair_description}",
                f"- minimum_gap_nm_threshold: {validation.minimum_allowed_gap_nm}",
                f"- validation_passed: {validation.passed}",
            ]
        )
    diagnostics = row.get("_diagnostics")
    debug_fsp_path = row.get("_debug_fsp_path")
    if diagnostics or debug_fsp_path:
        lines.extend(["", "Run diagnostics:", ""])
        if debug_fsp_path:
            lines.append(f"- debug_fsp_path: {debug_fsp_path}")
        if isinstance(diagnostics, list):
            for item in diagnostics:
                lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "Future paper-style APCD outputs:",
            "",
            "- jones_matrix_linear_basis.npy",
            "- jones_matrix_alpha_beta_basis.npy",
            "- results.csv",
            "- summary.md",
            "- metrics: t_alpha_star_from_alpha, t_beta_star_from_alpha, t_alpha_star_from_beta, t_beta_star_from_beta, T_alpha, T_beta, PD.",
            "- note: the paper Fig. 2 elliptical baseline is evaluated with x/y linear-basis Jones extraction and alpha/beta basis metrics, not only circular R/L metrics.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def write_jones_matrix_npy(row: dict[str, object], output_path: Union[str, Path]) -> Path:
    import numpy as np

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    matrix = np.array(jones_matrix_circular_basis(row), dtype=np.complex128)
    np.save(path, matrix)
    return path


def write_jones_matrix_linear_basis_npy(row: dict[str, object], output_path: Union[str, Path]) -> Path:
    import numpy as np

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    matrix = np.array(jones_matrix_linear_basis(row), dtype=np.complex128)
    np.save(path, matrix)
    return path


def write_jones_matrix_alpha_beta_basis_npy(row: dict[str, object], output_path: Union[str, Path]) -> Path:
    import numpy as np

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    matrix = np.array(jones_matrix_alpha_beta_basis(row), dtype=np.complex128)
    np.save(path, matrix)
    return path


def _complex_text(value: object) -> str:
    if value == "":
        return ""
    number = complex(value)  # type: ignore[arg-type]
    return f"{number.real:.16g}{number.imag:+.16g}j"


def _mean_transmission(matrix: dict[str, dict[str, object]]) -> object:
    transmissions = [
        float(values["transmission"])
        for values in matrix.values()
        if values.get("transmission", "") != ""
    ]
    if not transmissions:
        return ""
    return sum(transmissions) / len(transmissions)


def _safe_float(value: object) -> object:
    try:
        if hasattr(value, "item"):
            return value.item()
        return float(value)
    except Exception:
        return value


def _parse_complex(value: object) -> complex:
    if value == "":
        return 0 + 0j
    return complex(str(value))


def _squeeze(value: object) -> object:
    if hasattr(value, "squeeze"):
        return value.squeeze()
    while isinstance(value, (list, tuple)) and len(value) == 1:
        value = value[0]
    return value


def _shape_of(value: object) -> tuple[int, ...]:
    if hasattr(value, "shape"):
        return tuple(int(size) for size in value.shape if int(size) != 1)
    if isinstance(value, (list, tuple)):
        if not value:
            return (0,)
        return (len(value),) + _shape_of(value[0])
    return ()


def _center_value(value: object) -> complex:
    """Return spatially averaged complex field as zeroth-order approximation."""
    import numpy as np

    arr = np.array(_squeeze(value)).squeeze()
    if arr.shape == ():
        return complex(arr.item())
    return complex(np.mean(arr))
