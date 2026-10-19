"""Frozen 440-460 nm finite-K6 setup builder; legacy 445-455 code is untouched."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Sequence

import numpy as np

API = Path(r"N:\Program Files\ANSYS Inc\v251\Lumerical\api\python")
WAVELENGTHS_NM = tuple(float(x) for x in range(440, 461))
NP_NAMES = tuple(f"NP_bar_{i}" for i in range(0, 6))
MONITOR_NAMES = ("upward_monitor", "downward_monitor")
SOURCE_BOX_NAMES = ("source_box_top", "source_box_bottom", "source_box_left", "source_box_right")
MATERIAL = "APCD_TIO2_NATIVE_M1"
BUILDER_ID = "WIDEBAND_440_460_2DFDTD_BUILDER_V1"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def lumapi_module():
    if str(API) not in sys.path:
        sys.path.insert(0, str(API))
    import lumapi  # type: ignore
    return lumapi


def scalar(value: Any) -> Any:
    array = np.asarray(value)
    if array.size == 1:
        return array.reshape(-1)[0].item()
    return value


def get(fd: Any, obj: str, prop: str) -> Any:
    try:
        return scalar(fd.getnamed(obj, prop))
    except Exception:
        return None


def setnamed(fd: Any, obj: str, prop: str, value: Any) -> None:
    fd.setnamed(obj, prop, value)


def object_names(fd: Any) -> list[str]:
    return sorted(str(x).replace("::model::", "").strip(":") for x in fd.getobjectlist("::model::"))


def model_snapshot(fd: Any) -> dict[str, Any]:
    props = ("x", "y", "z", "x span", "y span", "z span", "material", "theta", "phi", "wavelength start", "wavelength stop", "frequency points", "monitor type")
    fdtd_props = props + ("dimension", "x min bc", "x max bc", "y min bc", "y max bc", "pml profile", "pml layers", "simulation time", "auto shutoff min", "mesh accuracy")
    rows = {}
    for name in object_names(fd):
        rows[name] = {prop: get(fd, name, prop) for prop in (fdtd_props if name == "FDTD" else props)}
    return rows


def expected_validation(geometry_nm: Sequence[float]) -> dict[str, Any]:
    if len(geometry_nm) != 6 or not all(np.isfinite(geometry_nm)):
        raise ValueError("exactly six finite geometry widths are required")
    return {
        "builder_id": BUILDER_ID,
        "geometry_nm": [float(x) for x in geometry_nm],
        "wavelengths_nm": list(WAVELENGTHS_NM),
        "monitor_names": list(MONITOR_NAMES),
        "source_box_names": list(SOURCE_BOX_NAMES),
        "expected_fdtd_x_span_um": 23.0,
        "expected_monitor_x_span_um": 19.0,
        "upward_monitor_y_um": 3.0,
        "downward_monitor_y_um": -1.2,
        "source_x_nm": 0.0,
        "source_physical_z_nm": -276.0,
        "mesh_accuracy": 2,
        "pml_profile": 2,
        "pml_layers": 32,
        "simulation_time_ps": 1.0,
        "auto_shutoff": 1e-6,
        "material": MATERIAL,
    }


def build_setup(template: Path, output: Path, geometry_nm: Sequence[float]) -> dict[str, Any]:
    """Build only; no run call exists in this function."""
    template, output = Path(template), Path(output)
    if not template.is_file():
        raise FileNotFoundError(template)
    if output.exists():
        raise FileExistsError(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    fd = lumapi_module().FDTD(str(template), hide=True)
    try:
        names = set(object_names(fd))
        if not set(NP_NAMES).issubset(names):
            raise RuntimeError(f"historical template missing NP bars: {sorted(set(NP_NAMES) - names)}")
        for name, width in zip(NP_NAMES, geometry_nm):
            setnamed(fd, name, "x span", float(width) * 1e-9)
            setnamed(fd, name, "material", MATERIAL)
        setnamed(fd, "FDTD", "x span", 23e-6)
        for prop, value in (("x min bc", "PML"), ("x max bc", "PML"), ("y min bc", "PML"), ("y max bc", "PML"), ("pml profile", 2), ("pml layers", 32), ("mesh accuracy", 2), ("simulation time", 1e-12), ("auto shutoff min", 1e-6)):
            setnamed(fd, "FDTD", prop, value)
        for prop, value in (("x", 0.0), ("y", -276e-9), ("theta", 90.0), ("phi", 0.0), ("wavelength start", 440e-9), ("wavelength stop", 460e-9)):
            setnamed(fd, "source_dipole", prop, value)
        monitor_positions = {"upward_monitor": (0.0, 3e-6), "downward_monitor": (0.0, -1.2e-6), "source_box_top": (0.0, -251e-9), "source_box_bottom": (0.0, -301e-9), "source_box_left": (-50e-9, -276e-9), "source_box_right": (50e-9, -276e-9)}
        for name in (*MONITOR_NAMES, *SOURCE_BOX_NAMES):
            setnamed(fd, name, "x", monitor_positions[name][0])
            setnamed(fd, name, "y", monitor_positions[name][1])
            if name in MONITOR_NAMES:
                setnamed(fd, name, "x span", 19e-6)
            setnamed(fd, name, "frequency points", 21)
        fd.save(str(output))
    finally:
        fd.close()
    return validate_setup(output, geometry_nm)


def validate_setup(path: Path, geometry_nm: Sequence[float]) -> dict[str, Any]:
    path = Path(path)
    fd = lumapi_module().FDTD(str(path), hide=True)
    try:
        rows = model_snapshot(fd)
    finally:
        fd.close()
    checks: dict[str, bool] = {}
    f = rows.get("FDTD", {})
    s = rows.get("source_dipole", {})
    checks["dimension_2d"] = f.get("dimension") == "2D"
    checks["fdtd_x_23um"] = np.isclose(float(f.get("x span", 0)) * 1e6, 23.0)
    checks["four_side_pml"] = all(f.get(k) == "PML" for k in ("x min bc", "x max bc", "y min bc", "y max bc"))
    checks["pml_32_profile_2"] = float(f.get("pml layers", 0)) == 32 and float(f.get("pml profile", 0)) == 2
    checks["mesh_accuracy_2"] = np.isclose(float(f.get("mesh accuracy", 0)), 2)
    checks["time_1ps_shutoff_1e6"] = np.isclose(float(f.get("simulation time", 0)), 1e-12) and np.isclose(float(f.get("auto shutoff min", 0)), 1e-6)
    checks["source_identity"] = np.isclose(float(s.get("x", 99)), 0) and np.isclose(float(s.get("y", 99)) * 1e9, -276) and np.isclose(float(s.get("theta", 0)), 90) and np.isclose(float(s.get("phi", 99)), 0)
    checks["wavelength_440_460"] = np.isclose(float(s.get("wavelength start", 0)) * 1e9, 440) and np.isclose(float(s.get("wavelength stop", 0)) * 1e9, 460)
    checks["six_native_m1_bars"] = all(rows.get(name, {}).get("material") == MATERIAL for name in NP_NAMES)
    checks["geometry_widths"] = all(np.isclose(float(rows.get(name, {}).get("x span", 0)) * 1e9, float(width)) for name, width in zip(NP_NAMES, geometry_nm))
    checks["upward_monitor"] = np.isclose(float(rows.get("upward_monitor", {}).get("x", 99)), 0) and np.isclose(float(rows.get("upward_monitor", {}).get("y", 99)) * 1e6, 3) and np.isclose(float(rows.get("upward_monitor", {}).get("x span", 0)) * 1e6, 19) and int(float(rows.get("upward_monitor", {}).get("frequency points", 0))) == 21
    checks["downward_monitor"] = np.isclose(float(rows.get("downward_monitor", {}).get("x", 99)), 0) and np.isclose(float(rows.get("downward_monitor", {}).get("y", 99)) * 1e6, -1.2) and np.isclose(float(rows.get("downward_monitor", {}).get("x span", 0)) * 1e6, 19) and int(float(rows.get("downward_monitor", {}).get("frequency points", 0))) == 21
    checks["source_boxes_frequency"] = all(int(float(rows.get(name, {}).get("frequency points", 0))) == 21 for name in SOURCE_BOX_NAMES)
    return {"path": str(path), "size": path.stat().st_size, "sha256": sha256_file(path), "rows": rows, "checks": checks, "pass": bool(all(checks.values()))}


def frozen_contract(template: Path, source_path: Path) -> dict[str, Any]:
    return {
        "schema_version": "WIDEBAND_BUILDER_CONTRACT_V1",
        "builder_id": BUILDER_ID,
        "source_path": str(source_path),
        "template_path": str(template),
        "template_sha256": sha256_file(template),
        "physical_model": {"dimension": "2D finite x-y; native y is physical z", "K_dimers": 6, "fdtd_x_span_um": 23.0, "monitor_x_span_um": 19.0, "boundaries": "four-side PML", "mdc": "frozen historical setup", "spacer_nm": 237.0, "source": {"object": "source_dipole", "x_nm": 0.0, "physical_z_nm": -276.0, "orientation": "X", "theta_deg": 90.0, "phi_deg": 0.0}, "material": MATERIAL, "mesh_accuracy": 2, "pml_profile": 2, "pml_layers": 32, "simulation_time_ps": 1.0, "auto_shutoff": 1e-6},
        "wavelengths_nm": list(WAVELENGTHS_NM),
        "frequency_points": 21,
        "monitors": {"upward_monitor": {"y_um": 3.0, "x_span_um": 19.0, "raw": ["Ex", "Ey", "Ez", "Hx", "Hy", "Hz"], "P_up": True}, "downward_monitor": {"y_um": -1.2, "x_span_um": 19.0, "raw": ["Ex", "Ey", "Ez", "Hx", "Hy", "Hz"], "active_label": "RAW_ONLY_NOT_ACTIVE_LABEL"}, "source_boxes": list(SOURCE_BOX_NAMES)},
        "no_spectral_shortcuts": ["0.5 nm", "0.1 nm"],
    }
