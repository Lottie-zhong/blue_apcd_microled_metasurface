from __future__ import annotations

import hashlib
import importlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CONTRACT_DIR = ROOT / "contracts" / "coupling" / "medium_pw"
OUT = ROOT / "outputs" / "coupling_ml" / "FREEZE_V3_RESOURCE_HARDENING_AND_MEDIUM_PW_PREENTRY_V1"
FSP = OUT / "W2H_15294_MEDIUM_PW_SETUP_ONLY_WITH_MON_IN.fsp"
READBACK = OUT / "W2H_15294_MEDIUM_PW_SETUP_WITH_MON_IN_READBACK.json"
RESOURCE_METADATA = OUT / "W2H_15294_MEDIUM_PW_WITH_MON_IN_RESOURCE_METADATA.json"
API = Path(r"N:\Program Files\ANSYS Inc\v251\Lumerical\api\python")
MATERIAL_ROOT = Path(r"D:\project\worktrees\blue_apcd_mdc_hf_surrogate_v2\scripts")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def load(name: str) -> dict:
    return json.loads((CONTRACT_DIR / name).read_text(encoding="utf-8"))


def scalar(value):
    return value.tolist() if hasattr(value, "tolist") else value


def get(fd, name: str, prop: str):
    try:
        return scalar(fd.getnamed(name, prop))
    except Exception as exc:
        return {"unavailable": repr(exc)}


def material_register(fd):
    sys.path.insert(0, str(MATERIAL_ROOT))
    module = importlib.import_module("apcd_native_materials")
    for material in ("APCD_GAN_NATIVE_M1", "APCD_TIO2_NATIVE_M1", "APCD_SIO2_NATIVE_M1"):
        module.register_lumerical_sampled_material(fd, material)


def set_props(fd, props: dict):
    for key, value in props.items():
        fd.set(key, value)


def add_rect(fd, name: str, material: str, z0: float, z1: float, lx: float = 1740.0, ly: float = 290.0):
    fd.addrect()
    set_props(fd, {"name": name, "material": material, "x": 0.0, "y": 0.0, "x span": lx * 1e-9, "y span": ly * 1e-9, "z min": z0 * 1e-9, "z max": z1 * 1e-9})


def add_monitor(fd, name: str, z_nm: float, fields: bool):
    fd.addpower()
    set_props(fd, {"name": name, "monitor type": "2D Z-normal", "x": 0.0, "y": 0.0, "z": z_nm * 1e-9, "x span": 1740e-9, "y span": 290e-9, "override global monitor settings": 1, "use source limits": 1, "use wavelength spacing": 1, "frequency points": 21})
    if fields:
        # Lumerical 2025 R1 may not expose these monitor flags through set();
        # leave the native complex-field default enabled and record readback limits.
        for key in ("output E fields", "output H fields"):
            try:
                fd.set(key, 1)
            except Exception:
                pass


def add_mesh(fd, spec: dict):
    fd.addmesh()
    set_props(fd, {"name": spec["name"], "x": spec["x_nm"] * 1e-9, "y": spec["y_nm"] * 1e-9, "z": spec["z_nm"] * 1e-9, "x span": spec["x_span_nm"] * 1e-9, "y span": spec["y_span_nm"] * 1e-9, "z span": spec["z_span_nm"] * 1e-9, "override x mesh": 1, "override y mesh": 1, "override z mesh": 1, "set maximum mesh step": 1, "dx": spec["dx_nm"] * 1e-9, "dy": spec["dy_nm"] * 1e-9, "dz": spec["dz_nm"] * 1e-9})


def build():
    mesh = load("MEDIUM_PW_MESH_CONTRACT_V1.json")
    temporal = load("MEDIUM_PW_TEMPORAL_CONTRACT_V1.json")
    monitor = load("MEDIUM_PW_MONITOR_CONTRACT_V1.json")
    OUT.mkdir(parents=True, exist_ok=True)
    if str(API) not in sys.path:
        sys.path.insert(0, str(API))
    import lumapi

    fd = lumapi.FDTD(hide=True)
    try:
        material_register(fd)
        fd.addfdtd()
        set_props(fd, {"dimension": "3D", "x span": 1740e-9, "y span": 290e-9, "z min": -600e-9, "z max": 3000e-9, "x min bc": "Periodic", "x max bc": "Periodic", "y min bc": "Periodic", "y max bc": "Periodic", "z min bc": "PML", "z max bc": "PML", "pml layers": 8, "mesh accuracy": 2, "mesh refinement": "conformal variant 1", "simulation time": temporal["maximum_physical_simulation_time_s"], "auto shutoff min": temporal["auto_shutoff_min"], "dt stability factor": 0.99})
        add_rect(fd, "GaN_substrate", "APCD_GAN_NATIVE_M1", -600.0, 0.0)
        z = 0.0
        for index, (material, thickness) in enumerate(mesh["physics"]["mdc_layers"], 1):
            add_rect(fd, f"MDC_LAYER_{index:02d}", material, z, z + thickness)
            z += thickness
        add_rect(fd, "SPACER_237NM", "APCD_SIO2_NATIVE_M1", z, z + 237.0)
        pillar_z0 = z + 237.0
        for index, (x_nm, diameter_nm) in enumerate(zip(mesh["physics"]["ordered_x_centers_nm"], mesh["physics"]["ordered_diameters_nm"]), 1):
            fd.addcircle()
            set_props(fd, {"name": f"NP_pillar_{index:02d}", "material": "APCD_TIO2_NATIVE_M1", "x": x_nm * 1e-9, "y": 0.0, "radius": diameter_nm * 0.5e-9, "z min": pillar_z0 * 1e-9, "z max": (pillar_z0 + 500.0) * 1e-9})
        fd.addplane()
        set_props(fd, {"name": "PW_SOURCE_X_NORMAL", "plane wave type": "Bloch/periodic", "injection axis": "z-axis", "direction": "Forward", "polarization angle": 0.0, "angle theta": 0.0, "angle phi": 0.0, "x": 0.0, "y": 0.0, "z": -276e-9, "x span": 1740e-9, "y span": 290e-9, "wavelength start": 440e-9, "wavelength stop": 460e-9})
        add_monitor(fd, "MON_IN", -100.0, True)
        add_monitor(fd, "MON_PRENP", 1200.0, True)
        add_monitor(fd, "MON_POSTNP", 2212.0, True)
        add_monitor(fd, "MON_REFLECTION", -400.0, False)
        for spec in sorted(mesh["mesh_overrides"], key=lambda item: -item["priority"]):
            add_mesh(fd, spec)
        fd.save(str(FSP))
    finally:
        fd.close()

    # Fresh independent LOAD-only validation. No run() call exists in this file.
    fresh = lumapi.FDTD(str(FSP), hide=True)
    try:
        solver = {prop: get(fresh, "FDTD", prop) for prop in ("dimension", "x span", "y span", "z min", "z max", "x min bc", "x max bc", "y min bc", "y max bc", "z min bc", "z max bc", "pml layers", "mesh accuracy", "mesh refinement", "simulation time", "auto shutoff min")}
        source = {prop: get(fresh, "PW_SOURCE_X_NORMAL", prop) for prop in ("plane wave type", "injection axis", "direction", "polarization angle", "angle theta", "angle phi", "z", "x span", "y span", "wavelength start", "wavelength stop")}
        monitors = {name: {prop: get(fresh, name, prop) for prop in ("monitor type", "z", "x span", "y span", "frequency points", "output E fields", "output H fields")} for name in ("MON_IN", "MON_PRENP", "MON_POSTNP", "MON_REFLECTION")}
        overrides = {spec["name"]: {prop: get(fresh, spec["name"], prop) for prop in ("x", "y", "z", "x span", "y span", "z span", "dx", "dy", "dz", "override x mesh", "override y mesh", "override z mesh", "set maximum mesh step")} for spec in mesh["mesh_overrides"]}
    finally:
        fresh.close()

    metadata = {"case_id": "W2H_15294", "setup_only": True, "solver_runs": 0, "scientific_solver_entries": 0, "resource_class": "HEAVY", "estimated_peak_ram_bytes": 8_000_000_000, "estimated_commit_bytes": 12_000_000_000, "mpi_ranks": 12, "threads": 1, "integrated_pw": True, "pw_integrated_max_concurrent": 1, "mesh_contract_sha256": sha256(CONTRACT_DIR / "MEDIUM_PW_MESH_CONTRACT_V1.json"), "temporal_contract_sha256": sha256(CONTRACT_DIR / "MEDIUM_PW_TEMPORAL_CONTRACT_V1.json"), "monitor_contract_sha256": sha256(CONTRACT_DIR / "MEDIUM_PW_MONITOR_CONTRACT_V1.json"), "created_utc": datetime.now(timezone.utc).isoformat()}
    RESOURCE_METADATA.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    readback = {"case_id": "W2H_15294", "fsp": str(FSP), "fsp_sha256": sha256(FSP), "solver": solver, "source": source, "monitors": monitors, "mesh_overrides": overrides, "resource_metadata": metadata, "load_only": True, "run_called": False, "solver_runs": 0}
    READBACK.write_text(json.dumps(readback, indent=2, default=str) + "\n", encoding="utf-8")
    print(json.dumps({"status": "SETUP_ONLY_BUILT_AND_FRESH_LOADED", "fsp": str(FSP), "fsp_sha256": readback["fsp_sha256"], "solver_runs": 0}, ensure_ascii=False))


if __name__ == "__main__":
    build()
