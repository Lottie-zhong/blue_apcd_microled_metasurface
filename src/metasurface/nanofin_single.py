from __future__ import annotations

import csv
import cmath
import math
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Optional, Union

from metasurface.config import NanofinSingleConfig, RuntimeConfig, load_runtime_config
from metasurface.lumapi_runner import import_lumapi


SINGLE_NANOFIN_FIELDS = [
    "wavelength_nm",
    "period_nm",
    "length_nm",
    "width_nm",
    "height_nm",
    "rotation_deg",
    "incident_polarization",
    "transmission",
    "phase_rad",
    "farfield_peak",
    "farfield_shape",
    "status",
    "note",
]


@dataclass(frozen=True)
class SingleNanofinRunner:
    config: NanofinSingleConfig
    dry_run: bool = False
    runtime: Optional[RuntimeConfig] = None
    setup_only: bool = False
    fsp_output: Optional[Path] = None
    load_fsp: Optional[Path] = None
    extract_only: bool = False

    @classmethod
    def from_runtime_file(
        cls,
        config: NanofinSingleConfig,
        runtime_path: Optional[Union[str, Path]],
        dry_run: bool,
        setup_only: bool = False,
        fsp_output: Optional[Union[str, Path]] = None,
        load_fsp: Optional[Union[str, Path]] = None,
        extract_only: bool = False,
    ) -> "SingleNanofinRunner":
        runtime = None if dry_run or runtime_path is None else load_runtime_config(runtime_path)
        output_path = None if fsp_output is None else Path(fsp_output)
        input_path = None if load_fsp is None else Path(load_fsp)
        return cls(
            config=config,
            dry_run=dry_run,
            runtime=runtime,
            setup_only=setup_only,
            fsp_output=output_path,
            load_fsp=input_path,
            extract_only=extract_only,
        )

    def run(self) -> list[dict[str, object]]:
        if self.dry_run:
            return [build_single_nanofin_dry_run_row(self.config)]

        if self.runtime is None:
            raise ValueError("A runtime config is required when dry_run is False")
        if not self.runtime.enable_lumerical:
            raise RuntimeError("runtime.enable_lumerical is false; use --dry-run or update runtime.yaml")

        lumapi = import_lumapi(self.runtime)
        return [
            run_single_nanofin_lumerical(
                self.config,
                self.runtime,
                lumapi,
                setup_only=self.setup_only,
                fsp_output=self.fsp_output,
                load_fsp=self.load_fsp,
                extract_only=self.extract_only,
            )
        ]


def build_single_nanofin_dry_run_row(config: NanofinSingleConfig) -> dict[str, object]:
    geometry = config.geometry
    return {
        "wavelength_nm": config.target.wavelength_nm,
        "period_nm": geometry.period_nm,
        "length_nm": geometry.length_nm,
        "width_nm": geometry.width_nm,
        "height_nm": geometry.height_nm,
        "rotation_deg": geometry.rotation_deg,
        "incident_polarization": config.target.incident_polarization,
        "transmission": "",
        "phase_rad": "",
        "farfield_peak": "",
        "farfield_shape": "",
        "status": "dry_run",
        "note": "single nanofin setup only; lumapi was not imported",
    }


def run_single_nanofin_lumerical(
    config: NanofinSingleConfig,
    runtime: RuntimeConfig,
    lumapi: ModuleType,
    setup_only: bool = False,
    fsp_output: Optional[Path] = None,
    load_fsp: Optional[Path] = None,
    extract_only: bool = False,
) -> dict[str, object]:
    geometry = config.geometry
    note = ""
    transmission: object = ""
    phase_rad: object = ""
    farfield_peak: object = ""
    farfield_shape: object = ""
    status = "error"

    fdtd = None
    try:
        fdtd = lumapi.FDTD(hide=runtime.hide_gui)
        if load_fsp is not None:
            fdtd.load(str(load_fsp))
        else:
            _build_single_nanofin_model(fdtd, config)

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
            transmission, phase_rad, farfield_peak, farfield_shape = _extract_single_nanofin_results(fdtd, config)
            status = "ok"
    except Exception as exc:  # Lumerical exceptions vary by installation.
        note = f"{type(exc).__name__}: {exc}"
    finally:
        if fdtd is not None:
            try:
                fdtd.close()
            except Exception:
                pass

    return {
        "wavelength_nm": config.target.wavelength_nm,
        "period_nm": geometry.period_nm,
        "length_nm": geometry.length_nm,
        "width_nm": geometry.width_nm,
        "height_nm": geometry.height_nm,
        "rotation_deg": geometry.rotation_deg,
        "incident_polarization": config.target.incident_polarization,
        "transmission": transmission,
        "phase_rad": phase_rad,
        "farfield_peak": farfield_peak,
        "farfield_shape": farfield_shape,
        "status": status,
        "note": note,
    }


def _build_single_nanofin_model(fdtd: object, config: NanofinSingleConfig) -> None:
    geometry = config.geometry
    nm = 1e-9
    period = geometry.period_nm * nm
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
    fdtd.set("x span", period)
    fdtd.set("y span", period)
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

    fdtd.addrect()
    fdtd.set("name", "nanofin")
    fdtd.set("x span", length)
    fdtd.set("y span", width)
    fdtd.set("z min", 0)
    fdtd.set("z max", height)
    if geometry.rotation_deg:
        fdtd.set("first axis", "z")
        fdtd.set("rotation 1", geometry.rotation_deg)
    _set_nanofin_material(fdtd, config)

    fdtd.addplane()
    fdtd.set("name", "source")
    fdtd.set("injection axis", "z")
    fdtd.set("direction", "Forward")
    fdtd.set("x span", period)
    fdtd.set("y span", period)
    fdtd.set("z", source_z)
    fdtd.set("wavelength start", wavelength)
    fdtd.set("wavelength stop", wavelength)
    fdtd.set("polarization angle", _polarization_angle_deg(config.target.incident_polarization))

    fdtd.addpower()
    fdtd.set("name", "T")
    fdtd.set("monitor type", "2D Z-normal")
    fdtd.set("x span", period)
    fdtd.set("y span", period)
    fdtd.set("z", monitor_z)

    fdtd.addprofile()
    fdtd.set("name", "phase_monitor")
    fdtd.set("monitor type", "2D Z-normal")
    fdtd.set("x span", period)
    fdtd.set("y span", period)
    fdtd.set("z", monitor_z)

    _apply_farfield_settings(fdtd, config)


def _polarization_angle_deg(polarization: str) -> float:
    normalized = polarization.lower()
    if normalized in {"x", "x_pol", "x-polarized"}:
        return 0.0
    if normalized in {"y", "y_pol", "y-polarized"}:
        return 90.0
    raise ValueError(f"Unsupported single-nanofin polarization: {polarization}")


def _set_nanofin_material(fdtd: object, config: NanofinSingleConfig) -> None:
    if config.material.metasurface_index is not None:
        fdtd.set("material", "<Object defined dielectric>")
        fdtd.set("index", config.material.metasurface_index)
        return
    fdtd.set("material", config.material.metasurface)


def _apply_farfield_settings(fdtd: object, config: NanofinSingleConfig) -> None:
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


def _project_farfield_3d(fdtd: object, monitor_name: str, config: NanofinSingleConfig) -> object:
    settings = config.far_field
    illumination = 1 if settings.illumination.lower() == "gaussian spot" else 2
    index = 1 if settings.material_index.lower() == "auto" else float(settings.material_index)
    direction = 1 if settings.projection_direction.lower() == "auto" else int(settings.projection_direction)

    fdtd.eval(f"farfieldfilter({settings.far_field_filter});")
    return fdtd.farfield3d(
        monitor_name,
        1,
        settings.resolution_3d,
        settings.resolution_3d,
        illumination,
        1,
        1,
        index,
        direction,
    )


def _extract_single_nanofin_results(fdtd: object, config: NanofinSingleConfig) -> tuple[object, object, object, object]:
    transmission = _safe_float(fdtd.transmission("T"))
    phase_rad = _extract_center_phase_rad(fdtd, "phase_monitor", config.target.incident_polarization)
    farfield = _project_farfield_3d(fdtd, "T", config)
    farfield_values = [
        float(value)
        for value in _flatten_values(farfield)
        if math.isfinite(float(value))
    ]
    farfield_peak = max(farfield_values) if farfield_values else ""
    farfield_shape = "x".join(str(size) for size in _shape_of(farfield))
    return transmission, phase_rad, farfield_peak, farfield_shape


def _extract_center_phase_rad(fdtd: object, monitor_name: str, polarization: str) -> float:
    key = "Ex" if _polarization_angle_deg(polarization) == 0 else "Ey"
    field = _squeeze(fdtd.getdata(monitor_name, key))
    center_value = _center_value(field)
    return float(cmath.phase(center_value))


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
    squeezed = _squeeze(value)
    shape = _shape_of(squeezed)
    if not shape:
        return complex(squeezed)  # type: ignore[arg-type]
    current = squeezed
    for axis_size in shape:
        current = current[axis_size // 2]  # type: ignore[index]
    return complex(current)  # type: ignore[arg-type]


def _flatten_values(value: object) -> list[object]:
    squeezed = _squeeze(value)
    if hasattr(squeezed, "flatten"):
        return list(squeezed.flatten())
    if isinstance(squeezed, (list, tuple)):
        values: list[object] = []
        for item in squeezed:
            values.extend(_flatten_values(item))
        return values
    return [squeezed]


def write_single_nanofin_summary(rows: list[dict[str, object]], output_path: Union[str, Path]) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=SINGLE_NANOFIN_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return path
