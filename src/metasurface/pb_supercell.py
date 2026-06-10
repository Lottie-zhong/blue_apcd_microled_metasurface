from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Optional, Union

from metasurface.config import PBSupercellConfig, RuntimeConfig, load_runtime_config
from metasurface.lumapi_runner import import_lumapi


PB_SUPERCELL_FIELDS = [
    "wavelength_nm",
    "atom_period_nm",
    "atoms",
    "supercell_period_nm",
    "length_nm",
    "width_nm",
    "height_nm",
    "rotation_step_deg",
    "target_order",
    "target_angle_deg",
    "transmission",
    "order_efficiency_total",
    "order_efficiency_rcp_estimate",
    "order_efficiency_lcp_estimate",
    "status",
    "note",
]


PB_ORDER_SPECTRUM_FIELDS = [
    "wavelength_nm",
    "incident_polarization",
    "output_polarization",
    "order_n",
    "order_m",
    "angle_deg",
    "transmission",
    "order_fraction",
    "order_efficiency_total",
    "order_efficiency_rcp_estimate",
    "order_efficiency_lcp_estimate",
    "status",
    "note",
]


@dataclass(frozen=True)
class PBSupercellRunner:
    config: PBSupercellConfig
    dry_run: bool = False
    runtime: Optional[RuntimeConfig] = None
    setup_only: bool = False
    fsp_output: Optional[Path] = None
    load_fsp: Optional[Path] = None
    extract_only: bool = False

    @classmethod
    def from_runtime_file(
        cls,
        config: PBSupercellConfig,
        runtime_path: Optional[Union[str, Path]],
        dry_run: bool,
        setup_only: bool = False,
        fsp_output: Optional[Union[str, Path]] = None,
        load_fsp: Optional[Union[str, Path]] = None,
        extract_only: bool = False,
    ) -> "PBSupercellRunner":
        runtime = None if dry_run or runtime_path is None else load_runtime_config(runtime_path)
        return cls(
            config=config,
            dry_run=dry_run,
            runtime=runtime,
            setup_only=setup_only,
            fsp_output=None if fsp_output is None else Path(fsp_output),
            load_fsp=None if load_fsp is None else Path(load_fsp),
            extract_only=extract_only,
        )

    def run(self) -> list[dict[str, object]]:
        if self.dry_run:
            return [build_pb_supercell_dry_run_row(self.config)]

        if self.runtime is None:
            raise ValueError("A runtime config is required when dry_run is False")
        if not self.runtime.enable_lumerical:
            raise RuntimeError("runtime.enable_lumerical is false; use --dry-run or update runtime.yaml")

        lumapi = import_lumapi(self.runtime)
        return [
            run_pb_supercell_lumerical(
                self.config,
                self.runtime,
                lumapi,
                setup_only=self.setup_only,
                fsp_output=self.fsp_output,
                load_fsp=self.load_fsp,
                extract_only=self.extract_only,
            )
        ]


def build_pb_supercell_dry_run_row(config: PBSupercellConfig) -> dict[str, object]:
    geometry = config.geometry
    return _row(
        config=config,
        transmission="",
        order_efficiency_total="",
        order_efficiency_rcp_estimate="",
        order_efficiency_lcp_estimate="",
        status="dry_run",
        note="PB supercell setup only; lumapi was not imported",
    )


def run_pb_supercell_lumerical(
    config: PBSupercellConfig,
    runtime: RuntimeConfig,
    lumapi: ModuleType,
    setup_only: bool = False,
    fsp_output: Optional[Path] = None,
    load_fsp: Optional[Path] = None,
    extract_only: bool = False,
) -> dict[str, object]:
    status = "error"
    note = ""
    transmission: object = ""
    order_efficiency_total: object = ""
    order_efficiency_rcp_estimate: object = ""
    order_efficiency_lcp_estimate: object = ""

    fdtd = None
    try:
        fdtd = lumapi.FDTD(hide=runtime.hide_gui)
        if load_fsp is not None:
            fdtd.load(str(load_fsp))
        else:
            _build_pb_supercell_model(fdtd, config)

        if setup_only:
            if fsp_output is not None:
                fsp_output.parent.mkdir(parents=True, exist_ok=True)
                fdtd.save(str(fsp_output))
                note = f"model saved to {fsp_output}; solver was not run"
            else:
                note = "model built; solver was not run"
            status = "setup_only"
        else:
            if not extract_only:
                fdtd.run()
            transmission = _safe_float(fdtd.transmission("T"))
            order_efficiency_total = _extract_order_efficiency_total(fdtd, "T", config, transmission)
            (
                order_efficiency_rcp_estimate,
                order_efficiency_lcp_estimate,
            ) = _extract_circular_order_efficiency_estimates(fdtd, "T", config, transmission)
            status = "ok"
            note = "RCP/LCP estimates use gratingpolar Etheta +/- i*Ephi spherical-basis convention"
    except Exception as exc:  # Lumerical exceptions vary by installation.
        note = f"{type(exc).__name__}: {exc}"
    finally:
        if fdtd is not None:
            try:
                fdtd.close()
            except Exception:
                pass

    return _row(
        config=config,
        transmission=transmission,
        order_efficiency_total=order_efficiency_total,
        order_efficiency_rcp_estimate=order_efficiency_rcp_estimate,
        order_efficiency_lcp_estimate=order_efficiency_lcp_estimate,
        status=status,
        note=note,
    )


def _build_pb_supercell_model(fdtd: object, config: PBSupercellConfig) -> None:
    geometry = config.geometry
    nm = 1e-9
    atom_period = geometry.atom_period_nm * nm
    supercell_period = geometry.atoms * atom_period
    length = geometry.length_nm * nm
    width = geometry.width_nm * nm
    height = geometry.height_nm * nm
    wavelength = config.target.wavelength_nm * nm

    z_min = -500 * nm
    z_max = height + 700 * nm
    source_z = -250 * nm
    monitor_z = height + 350 * nm

    fdtd.switchtolayout()
    fdtd.deleteall()

    fdtd.addfdtd()
    fdtd.set("dimension", "3D")
    fdtd.set("x span", supercell_period)
    fdtd.set("y span", atom_period)
    fdtd.set("z min", z_min)
    fdtd.set("z max", z_max)
    fdtd.set("x min bc", "Periodic")
    fdtd.set("x max bc", "Periodic")
    fdtd.set("y min bc", "Periodic")
    fdtd.set("y max bc", "Periodic")
    fdtd.set("z min bc", "PML")
    fdtd.set("z max bc", "PML")
    fdtd.set("mesh accuracy", 2)
    fdtd.set("simulation time", 1000e-15)

    x0 = -0.5 * supercell_period + 0.5 * atom_period
    for index in range(geometry.atoms):
        fdtd.addrect()
        fdtd.set("name", f"nanofin_{index:02d}")
        fdtd.set("x", x0 + index * atom_period)
        fdtd.set("y", 0)
        fdtd.set("x span", length)
        fdtd.set("y span", width)
        fdtd.set("z min", 0)
        fdtd.set("z max", height)
        fdtd.set("first axis", "z")
        fdtd.set("rotation 1", geometry.rotation_start_deg + index * geometry.rotation_step_deg)
        _set_material(fdtd, config)

    _add_circular_plane_wave_sources(fdtd, config, supercell_period, atom_period, source_z, wavelength)

    fdtd.addpower()
    fdtd.set("name", "T")
    fdtd.set("monitor type", "2D Z-normal")
    fdtd.set("x span", supercell_period)
    fdtd.set("y span", atom_period)
    fdtd.set("z", monitor_z)

    _apply_farfield_settings(fdtd, config)


def _add_circular_plane_wave_sources(
    fdtd: object,
    config: PBSupercellConfig,
    x_span: float,
    y_span: float,
    z: float,
    wavelength: float,
) -> None:
    normalized = config.target.incident_polarization.lower()
    if normalized not in {"lcp", "rcp"}:
        raise ValueError(f"Unsupported PB supercell incident_polarization: {config.target.incident_polarization}")
    y_phase_deg = 90 if normalized == "lcp" else -90
    amplitude = 1 / math.sqrt(2)
    for name, polarization_angle, phase in (
        ("source_x", 0, 0),
        ("source_y", 90, y_phase_deg),
    ):
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


def _extract_order_efficiency_total(
    fdtd: object,
    monitor_name: str,
    config: PBSupercellConfig,
    transmission: object,
) -> object:
    target_n = int(str(config.target.target_order).replace("+", ""))
    target_m = 0
    grating_power = fdtd.grating(monitor_name)
    grating_n = fdtd.gratingn(monitor_name)
    grating_m = fdtd.gratingm(monitor_name)
    n_values = _flatten_values(grating_n)
    m_values = _flatten_values(grating_m)
    if len(m_values) == 1 and len(n_values) > 1:
        m_values = m_values * len(n_values)
    for index, (n_value, m_value) in enumerate(zip(n_values, m_values)):
        if int(round(float(n_value))) == target_n and int(round(float(m_value))) == target_m:
            return float(_flatten_values(grating_power)[index]) * float(transmission)
    return ""


def collect_pb_order_spectrum_from_fsp(
    config: PBSupercellConfig,
    runtime_path: Union[str, Path],
    fsp_path: Union[str, Path],
) -> list[dict[str, object]]:
    runtime = load_runtime_config(runtime_path)
    if not runtime.enable_lumerical:
        raise RuntimeError("runtime.enable_lumerical is false; update runtime.yaml")

    lumapi = import_lumapi(runtime)
    fdtd = None
    try:
        fdtd = lumapi.FDTD(hide=runtime.hide_gui)
        fdtd.load(str(fsp_path))
        fdtd.run()
        transmission = _safe_float(fdtd.transmission("T"))
        return extract_pb_order_spectrum(fdtd, "T", config, transmission)
    finally:
        if fdtd is not None:
            try:
                fdtd.close()
            except Exception:
                pass


def extract_pb_order_spectrum(
    fdtd: object,
    monitor_name: str,
    config: PBSupercellConfig,
    transmission: object,
) -> list[dict[str, object]]:
    n_values = _flatten_values(fdtd.gratingn(monitor_name))
    m_values = _flatten_values(fdtd.gratingm(monitor_name))
    if len(m_values) == 1 and len(n_values) > 1:
        m_values = m_values * len(n_values)
    fractions = _flatten_values(fdtd.grating(monitor_name))
    order_vectors = _flatten_order_vectors(fdtd.gratingpolar(monitor_name))

    rows: list[dict[str, object]] = []
    for index, n_value in enumerate(n_values):
        m_value = m_values[index] if index < len(m_values) else ""
        fraction = float(fractions[index]) if index < len(fractions) else ""
        total = fraction * float(transmission) if fraction != "" else ""
        rcp: object = ""
        lcp: object = ""
        if index < len(order_vectors):
            _, e_theta, e_phi = order_vectors[index]
            e_rcp = (complex(e_theta) + 1j * complex(e_phi)) / math.sqrt(2)
            e_lcp = (complex(e_theta) - 1j * complex(e_phi)) / math.sqrt(2)
            rcp = abs(e_rcp) ** 2 * float(transmission)
            lcp = abs(e_lcp) ** 2 * float(transmission)

        rows.append(
            {
                "wavelength_nm": config.target.wavelength_nm,
                "incident_polarization": config.target.incident_polarization,
                "output_polarization": config.target.output_polarization,
                "order_n": int(round(float(n_value))),
                "order_m": int(round(float(m_value))) if m_value != "" else "",
                "angle_deg": _order_angle_deg(config, float(n_value)),
                "transmission": transmission,
                "order_fraction": fraction,
                "order_efficiency_total": total,
                "order_efficiency_rcp_estimate": rcp,
                "order_efficiency_lcp_estimate": lcp,
                "status": "ok",
                "note": "RCP/LCP estimates use gratingpolar Etheta +/- i*Ephi spherical-basis convention",
            }
        )
    return rows


def _extract_circular_order_efficiency_estimates(
    fdtd: object,
    monitor_name: str,
    config: PBSupercellConfig,
    transmission: object,
) -> tuple[object, object]:
    target_index = _find_target_order_index(fdtd, monitor_name, config)
    if target_index is None:
        return "", ""
    order_vectors = _flatten_order_vectors(fdtd.gratingpolar(monitor_name))
    if target_index >= len(order_vectors):
        return "", ""
    _, e_theta, e_phi = order_vectors[target_index]
    e_rcp = (complex(e_theta) + 1j * complex(e_phi)) / math.sqrt(2)
    e_lcp = (complex(e_theta) - 1j * complex(e_phi)) / math.sqrt(2)
    return abs(e_rcp) ** 2 * float(transmission), abs(e_lcp) ** 2 * float(transmission)


def _find_target_order_index(fdtd: object, monitor_name: str, config: PBSupercellConfig) -> int | None:
    target_n = int(str(config.target.target_order).replace("+", ""))
    target_m = 0
    n_values = _flatten_values(fdtd.gratingn(monitor_name))
    m_values = _flatten_values(fdtd.gratingm(monitor_name))
    if len(m_values) == 1 and len(n_values) > 1:
        m_values = m_values * len(n_values)
    for index, (n_value, m_value) in enumerate(zip(n_values, m_values)):
        if int(round(float(n_value))) == target_n and int(round(float(m_value))) == target_m:
            return index
    return None


def _set_material(fdtd: object, config: PBSupercellConfig) -> None:
    if config.material.metasurface_index is not None:
        fdtd.set("material", "<Object defined dielectric>")
        fdtd.set("index", config.material.metasurface_index)
        return
    fdtd.set("material", config.material.metasurface)


def _apply_farfield_settings(fdtd: object, config: PBSupercellConfig) -> None:
    settings = config.far_field
    fdtd.eval(f"farfieldfilter({settings.far_field_filter});")
    fdtd.eval(f'farfieldsettings("far field filter",{settings.far_field_filter});')
    fdtd.eval(
        'farfieldsettings("override near field mesh",'
        f'{1 if settings.override_near_field_mesh else 0});'
    )
    fdtd.eval(
        'farfieldsettings("near field samples per wavelength",'
        f'{settings.near_field_samples_per_wavelength});'
    )


def _row(
    config: PBSupercellConfig,
    transmission: object,
    order_efficiency_total: object,
    order_efficiency_rcp_estimate: object,
    order_efficiency_lcp_estimate: object,
    status: str,
    note: str,
) -> dict[str, object]:
    geometry = config.geometry
    supercell_period_nm = geometry.atoms * geometry.atom_period_nm
    return {
        "wavelength_nm": config.target.wavelength_nm,
        "atom_period_nm": geometry.atom_period_nm,
        "atoms": geometry.atoms,
        "supercell_period_nm": supercell_period_nm,
        "length_nm": geometry.length_nm,
        "width_nm": geometry.width_nm,
        "height_nm": geometry.height_nm,
        "rotation_step_deg": geometry.rotation_step_deg,
        "target_order": config.target.target_order,
        "target_angle_deg": _target_angle_deg(config),
        "transmission": transmission,
        "order_efficiency_total": order_efficiency_total,
        "order_efficiency_rcp_estimate": order_efficiency_rcp_estimate,
        "order_efficiency_lcp_estimate": order_efficiency_lcp_estimate,
        "status": status,
        "note": note,
    }


def _target_angle_deg(config: PBSupercellConfig) -> object:
    ratio = config.target.wavelength_nm / (config.geometry.atoms * config.geometry.atom_period_nm)
    if abs(ratio) > 1:
        return ""
    return math.degrees(math.asin(ratio))


def _order_angle_deg(config: PBSupercellConfig, order_n: float) -> object:
    ratio = order_n * config.target.wavelength_nm / (config.geometry.atoms * config.geometry.atom_period_nm)
    if abs(ratio) > 1:
        return ""
    return math.degrees(math.asin(ratio))


def _safe_float(value: object) -> object:
    try:
        if hasattr(value, "item"):
            return value.item()
        values = [float(item) for item in _flatten_values(value)]
        if not values:
            return ""
        if len(values) == 1:
            return values[0]
        return sum(values) / len(values)
    except Exception:
        return value


def _flatten_values(value: object) -> list[object]:
    if hasattr(value, "flatten"):
        return list(value.flatten())
    if isinstance(value, (list, tuple)):
        values: list[object] = []
        for item in value:
            values.extend(_flatten_values(item))
        return values
    return [value]


def _flatten_order_vectors(value: object) -> list[tuple[object, object, object]]:
    if hasattr(value, "reshape"):
        return [tuple(row) for row in value.reshape(-1, 3)]
    if isinstance(value, (list, tuple)):
        if len(value) == 3 and not isinstance(value[0], (list, tuple)):
            return [(value[0], value[1], value[2])]
        vectors: list[tuple[object, object, object]] = []
        for item in value:
            vectors.extend(_flatten_order_vectors(item))
        return vectors
    return []


def write_pb_supercell_summary(rows: list[dict[str, object]], output_path: Union[str, Path]) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=PB_SUPERCELL_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return path


def write_pb_order_spectrum(rows: list[dict[str, object]], output_path: Union[str, Path]) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=PB_ORDER_SPECTRUM_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return path
