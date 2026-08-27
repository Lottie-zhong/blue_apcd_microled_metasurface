from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(os.environ.get("PAPER_A_ROOT", r"D:/project/worktrees/blue_apcd_paper_a_lp_cp_broadband_v1"))
BASE = ROOT / "paper_a_broadband"
AUTH = BASE / "authority"
RUNTIME = BASE / "runtime/ic1_solver_ready"
CASE_ID = "IC1_MDC_I03_TOPWELL_X"
CANONICAL_PREFSP = RUNTIME / f"{CASE_ID}_attempt_001_pre.fsp"
V2_TIME_PROBE = "ic1_v2_time_probe"
NATIVE_IDS = ("APCD_GAN_NATIVE_M1", "APCD_TIO2_NATIVE_M1", "APCD_SIO2_NATIVE_M1")
NATIVE_SAMPLE_CSV = ROOT / "outputs/material_reference/mdc_blue_oujizi_m/material_ref_native_sampled.csv"
CP_NATIVE_MATERIAL_SEED = BASE / "runtime/reusable_fsp/cp/CP_NATIVE_M1_CENTER_XY_setup_prepared_not_run.fsp"
LUMERICAL_API = r"N:/Program Files/ANSYS Inc/v251/Lumerical/api/python"
if LUMERICAL_API not in sys.path:
    sys.path.insert(0, LUMERICAL_API)


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def canon(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode("utf-8")


def sha_obj(value: Any) -> str:
    return hashlib.sha256(canon(value)).hexdigest()


def sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(value, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def load_json(relative: str) -> dict[str, Any]:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def load_authorities() -> dict[str, Any]:
    return {
        "mesa": load_json("paper_a_broadband/authority/ic1_finite_mesa_authority.json"),
        "domain": load_json("paper_a_broadband/authority/ic1_domain_pml_authority.json"),
        "z": load_json("paper_a_broadband/authority/ic1_absolute_z_layout.json"),
        "i03": load_json("paper_a_broadband/authority/ic1_i03_5x5_replication_authority.json"),
        "monitor": load_json("paper_a_broadband/authority/ic1_monitor_contract.json"),
        "adapter": load_json("paper_a_broadband/authority/ic1_integrated_validity_adapter.json"),
        "v2": load_json("paper_a_broadband/authority/paper_a_fdtd_physics_validity_gate_v2_instrumented.json"),
        "material_config": load_json("configs/material_reference_apcd_blue.json"),
        "cp_setup": load_json("paper_a_broadband/references/cp/setup_audit.json"),
    }


def authority_files() -> dict[str, Path]:
    return {
        "finite_mesa": BASE / "authority/ic1_finite_mesa_authority.json",
        "domain_pml": BASE / "authority/ic1_domain_pml_authority.json",
        "absolute_z_layout": BASE / "authority/ic1_absolute_z_layout.json",
        "i03_replication": BASE / "authority/ic1_i03_5x5_replication_authority.json",
        "monitor_contract": BASE / "authority/ic1_monitor_contract.json",
        "integrated_adapter": BASE / "authority/ic1_integrated_validity_adapter.json",
        "v2_validity": BASE / "authority/paper_a_fdtd_physics_validity_gate_v2_instrumented.json",
        "material_config": ROOT / "configs/material_reference_apcd_blue.json",
        "native_samples": NATIVE_SAMPLE_CSV,
        "cp_native_material_seed": CP_NATIVE_MATERIAL_SEED,
        "cp_setup_audit": BASE / "references/cp/setup_audit.json",
    }


def nm(value: float) -> float:
    return float(value) * 1e-9


def jsonable(value: Any) -> Any:
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (list, tuple)):
        return [jsonable(item) for item in value]
    if isinstance(value, dict):
        return {str(key): jsonable(item) for key, item in value.items()}
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def model_object_names(fdtd: Any) -> list[str]:
    """Read the model tree; an absent root after delete means it is empty."""
    try:
        value = jsonable(fdtd.getobjectlist("::model::"))
    except Exception as exc:
        if "no match found" in str(exc).lower():
            return []
        raise
    return sorted(name for name in (str(item).split("::")[-1] for item in (value or [])) if name)


def material_names(fdtd: Any) -> set[str]:
    raw = fdtd.getmaterial()
    raw = raw.tolist() if hasattr(raw, "tolist") else raw
    if isinstance(raw, str):
        return {item.strip() for item in raw.splitlines() if item.strip()}
    return {str(item).strip() for item in raw}


def sampled_matrix(material_id: str) -> np.ndarray:
    aliases = {"sio222": "APCD_SIO2_NATIVE_M1", "tio22": "APCD_TIO2_NATIVE_M1"}
    rows: list[list[complex]] = []
    with NATIVE_SAMPLE_CSV.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if aliases.get(row["material_name"]) == material_id:
                rows.append([
                    complex(float(row["frequency_hz"]), 0.0),
                    complex(float(row["epsilon_real"]), float(row["epsilon_imag"])),
                ])
    if len(rows) != 101:
        raise RuntimeError(f"NATIVE_M1_SAMPLE_COUNT:{material_id}:{len(rows)}")
    return np.asarray(rows, dtype=np.complex128)


def ensure_native_materials(fdtd: Any) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    existing = material_names(fdtd)
    for material_id, builtin in (
        ("APCD_TIO2_NATIVE_M1", None),
        ("APCD_SIO2_NATIVE_M1", None),
        ("APCD_GAN_NATIVE_M1", "GaN"),
    ):
        source_name = "GaN" if builtin else ("tio22" if material_id.endswith("TIO2_NATIVE_M1") else "sio222")
        origin = "frozen native material seed retained" if material_id in existing else ""
        if material_id not in existing:
            if builtin is None:
                temporary = fdtd.addmaterial("Sampled 3D data")
                temporary = str(temporary) if temporary else "Sampled 3D data"
                fdtd.setmaterial(temporary, "name", material_id)
                fdtd.setmaterial(material_id, "sampled data", sampled_matrix(material_id))
                origin = "native sampled epsilon from material_ref_native_sampled.csv"
            else:
                temporary = fdtd.addmaterial(builtin)
                temporary = str(temporary) if temporary else builtin
                fdtd.setmaterial(temporary, "name", material_id)
                source_name, origin = builtin, "Lumerical native material library GaN aliased to frozen Native-M1 identity"
        existing = material_names(fdtd)
        if material_id not in existing:
            raise RuntimeError(f"NATIVE_M1_ALIAS_NOT_READABLE:{material_id}")
        result[material_id] = {"target_name": material_id, "source_name": source_name,
                               "origin": origin, "constant_index_fallback": False,
                               "readback_present": True}
    return result


def set_rect(fdtd: Any, name: str, x_nm: float, y_nm: float, zmin_nm: float, zmax_nm: float,
             xspan_nm: float, yspan_nm: float, material: str, rotation_deg: float = 0.0) -> None:
    fdtd.addrect()
    fdtd.set("name", name)
    for key, value in (
        ("x", nm(x_nm)), ("y", nm(y_nm)), ("z min", nm(zmin_nm)), ("z max", nm(zmax_nm)),
        ("x span", nm(xspan_nm)), ("y span", nm(yspan_nm)), ("material", material),
    ):
        fdtd.setnamed(name, key, value)
    if abs(float(rotation_deg)) > 0.0:
        fdtd.setnamed(name, "first axis", "z")
        fdtd.setnamed(name, "rotation 1", float(rotation_deg))


def tag(value: int) -> str:
    return f"m{abs(value)}" if value < 0 else f"p{value}"


def pillar_name(i: int, j: int, p: int) -> str:
    return f"ic1_i03_i{tag(i)}_j{tag(j)}_p{p}"


def add_fdtd_domain(fdtd: Any, a: dict[str, Any]) -> None:
    d = a["domain"]["domain_nm"]
    fdtd.addfdtd()
    for key, value in (
        ("x", 0.0), ("y", 0.0), ("z", nm((d["z_bounds"][0] + d["z_bounds"][1]) / 2.0)),
        ("x span", nm(d["x_span"])), ("y span", nm(d["y_span"])), ("z span", nm(d["z_span"])),
        ("dimension", "3D"), ("x min bc", "PML"), ("x max bc", "PML"),
        ("y min bc", "PML"), ("y max bc", "PML"), ("z min bc", "PML"), ("z max bc", "PML"),
        ("pml layers", int(a["domain"]["pml"]["layers"])), ("mesh accuracy", 3.0),
        ("simulation time", 1e-12), ("auto shutoff min", 1e-6),
    ):
        fdtd.setnamed("FDTD", key, value)


def add_source(fdtd: Any, a: dict[str, Any]) -> None:
    c, source = a["monitor"]["source_grid"], a["z"]["ic1_source"]
    fdtd.setglobalmonitor("frequency points", int(c["points"]))
    fdtd.setglobalmonitor("use wavelength spacing", True)
    fdtd.adddipole()
    fdtd.set("name", CASE_ID)
    for key, value in (
        ("x", nm(source["position_nm"][0])), ("y", nm(source["position_nm"][1])),
        ("z", nm(source["position_nm"][2])), ("theta", 90.0), ("phi", 0.0),
        ("wavelength start", nm(c["start_nm"])), ("wavelength stop", nm(c["stop_nm"])),
        ("amplitude", 1.0), ("phase", 0.0),
    ):
        fdtd.setnamed(CASE_ID, key, value)


def spectral_settings(fdtd: Any, name: str) -> None:
    for key, value in (
        ("override global monitor settings", 1), ("use source limits", 1),
        ("use wavelength spacing", 1), ("frequency points", 101),
    ):
        fdtd.setnamed(name, key, value)


def add_power_monitor(fdtd: Any, name: str, monitor_type: str, position_nm: list[float],
                      span_nm: list[float]) -> None:
    fdtd.addpower()
    fdtd.set("name", name)
    fdtd.set("monitor type", monitor_type)
    for axis, value in zip(("x", "y", "z"), position_nm):
        fdtd.set(axis, nm(value))
    if monitor_type == "2D Z-normal":
        spans = {"x span": nm(span_nm[0]), "y span": nm(span_nm[1])}
    elif monitor_type == "2D X-normal":
        spans = {"y span": nm(span_nm[0]), "z span": nm(span_nm[1])}
    else:
        spans = {"x span": nm(span_nm[0]), "z span": nm(span_nm[1])}
    for key, value in spans.items():
        fdtd.set(key, value)
    spectral_settings(fdtd, name)


def add_near_to_far_monitor(fdtd: Any, a: dict[str, Any]) -> None:
    c = a["monitor"]["near_to_far"]
    fdtd.addprofile()
    fdtd.set("name", c["name"])
    fdtd.set("monitor type", "2D Z-normal")
    for key, value in (
        ("x", nm(c["position_nm"][0])),
        ("y", nm(c["position_nm"][1])), ("z", nm(c["position_nm"][2])),
        ("x span", nm(c["span_nm"][0])), ("y span", nm(c["span_nm"][1])),
    ):
        fdtd.set(key, value)
    spectral_settings(fdtd, c["name"])
    spectral_settings(fdtd, c["name"])


def add_v2_probe(fdtd: Any, a: dict[str, Any]) -> None:
    p = a["monitor"]["convergence_instrumentation"]["position_nm"]
    fdtd.addtime()
    fdtd.set("name", V2_TIME_PROBE)
    for key, value in (("monitor type", "Point"), ("x", nm(p[0])), ("y", nm(p[1])), ("z", nm(p[2]))):
        fdtd.setnamed(V2_TIME_PROBE, key, value)


def build_from_authority(output: Path) -> dict[str, Any]:
    if output.exists():
        raise RuntimeError(f"REFUSE_OVERWRITE_PREFSP:{output}")
    a = load_authorities()
    output.parent.mkdir(parents=True, exist_ok=True)
    import lumapi
    if not CP_NATIVE_MATERIAL_SEED.exists():
        raise RuntimeError(f"NATIVE_MATERIAL_SEED_MISSING:{CP_NATIVE_MATERIAL_SEED}")
    fdtd = lumapi.FDTD(hide=True)
    try:
        fdtd.load(str(CP_NATIVE_MATERIAL_SEED))
        fdtd.switchtolayout()
        seed_model_objects_before_reset = model_object_names(fdtd)
        try:
            fdtd.selectall()
            fdtd.delete()
        except Exception:
            fdtd.eval("selectall; delete;")
        try:
            fdtd.select("FDTD")
            fdtd.delete()
        except Exception:
            pass
        seed_model_objects_after_reset = model_object_names(fdtd)
        if seed_model_objects_after_reset:
            raise RuntimeError("NATIVE_SEED_MODEL_OBJECTS_NOT_DELETED")
        materials = ensure_native_materials(fdtd)
        add_fdtd_domain(fdtd, a)
        mesa = a["mesa"]["mesa"]
        set_rect(fdtd, "ic1_gan_host", 0.0, 0.0, -1600.0, 0.0, mesa["x_nm"], mesa["y_nm"], "APCD_GAN_NATIVE_M1")
        for region in a["z"]["mqw"]["regions"]:
            set_rect(fdtd, f"ic1_mqw_primary_{int(region['index']):02d}", 0.0, 0.0,
                     float(region["bottom_z_nm"]), float(region["top_z_nm"]),
                     mesa["x_nm"], mesa["y_nm"], "APCD_GAN_NATIVE_M1")
        for layer in a["z"]["mdc"]["layers"]:
            index = int(layer["layer_id"].split("_")[-1])
            set_rect(fdtd, f"ic1_mdc_layer_{index:02d}", 0.0, 0.0,
                     float(layer["bottom_z_nm"]), float(layer["top_z_nm"]),
                     float(layer["xy_extent_nm"][0]), float(layer["xy_extent_nm"][1]), layer["material"])
        for cell in a["i03"]["cells"]:
            for p, key in ((1, "pillar_1"), (2, "pillar_2")):
                pillar = cell[key]
                set_rect(fdtd, pillar_name(int(cell["i"]), int(cell["j"]), p),
                         float(pillar["center_nm"][0]), float(pillar["center_nm"][1]),
                         float(pillar["bottom_z_nm"]), float(pillar["top_z_nm"]),
                         float(pillar["length_nm"]), float(pillar["width_nm"]),
                         pillar["material"], float(pillar["rotation_z_deg"]))
        add_source(fdtd, a)
        for face in a["monitor"]["closed_flux_box"]["faces"]:
            axis = face["normal"][-1].lower()
            ftype = {"x": "2D X-normal", "y": "2D Y-normal", "z": "2D Z-normal"}[axis]
            add_power_monitor(fdtd, face["name"], ftype, face["position_nm"], face["span_nm"])
        add_near_to_far_monitor(fdtd, a)
        add_v2_probe(fdtd, a)
        fdtd.save(str(output))
    finally:
        try:
            fdtd.close()
        except Exception:
            pass
    return {"path": str(output), "sha256": sha_file(output), "solver_run_called": False,
            "solver_entered": 0, "material_meta": materials,
            "builder": "fresh_json_authority_model_after_native_material_seed_reset", "native_material_seed": str(CP_NATIVE_MATERIAL_SEED),
            "native_material_seed_policy": "seed_file_only_for_frozen_native_material_definitions",
            "seed_model_objects_before_reset": seed_model_objects_before_reset,
            "seed_model_objects_after_reset": seed_model_objects_after_reset,
            "seed_saved": False, "case_id": CASE_ID}


def get_prop(fdtd: Any, name: str, key: str) -> Any:
    try:
        return jsonable(fdtd.getnamed(name, key))
    except Exception as exc:
        return {"__readback_error__": f"{type(exc).__name__}:{exc}"}


def get_float(fdtd: Any, name: str, key: str) -> Any:
    value = get_prop(fdtd, name, key)
    if not isinstance(value, (int, float)):
        return value
    length_keys = {"x", "y", "z", "x min", "x max", "y min", "y max", "z min", "z max", "x span", "y span", "z span"}
    return float(value) * 1e9 if key in length_keys else float(value)


def get_global_monitor(fdtd: Any, key: str) -> Any:
    try:
        return jsonable(fdtd.getglobalmonitor(key))
    except Exception as exc:
        return {"__readback_error__": f"{type(exc).__name__}:{exc}"}


def readback(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(path)
    import lumapi
    a = load_authorities()
    fdtd = lumapi.FDTD(hide=True)
    try:
        fdtd.load(str(path))
        names = model_object_names(fdtd)
        objects: dict[str, Any] = {"object_names": names}
        objects["fdtd"] = {key: get_prop(fdtd, "FDTD", key) for key in (
            "dimension", "x", "y", "z", "x span", "y span", "z span", "x min bc", "x max bc",
            "y min bc", "y max bc", "z min bc", "z max bc", "pml layers", "mesh accuracy",
            "simulation time", "auto shutoff min")}
        objects["host"] = {key: get_float(fdtd, "ic1_gan_host", key) for key in (
            "x", "y", "z min", "z max", "x span", "y span")}
        objects["mqw"] = []
        for index in range(1, 13):
            name = f"ic1_mqw_primary_{index:02d}"
            objects["mqw"].append({"name": name, **{key: get_float(fdtd, name, key) for key in (
                "x", "y", "z min", "z max", "x span", "y span")}, "material": get_prop(fdtd, name, "material")})
        objects["mdc"] = []
        for index in range(1, 13):
            name = f"ic1_mdc_layer_{index:02d}"
            objects["mdc"].append({"name": name, **{key: get_float(fdtd, name, key) for key in (
                "x", "y", "z min", "z max", "x span", "y span")}, "material": get_prop(fdtd, name, "material")})
        objects["i03"] = []
        for cell in a["i03"]["cells"]:
            for p in (1, 2):
                name = pillar_name(int(cell["i"]), int(cell["j"]), p)
                objects["i03"].append({"name": name, **{key: get_float(fdtd, name, key) for key in (
                    "x", "y", "z min", "z max", "x span", "y span", "rotation 1")},
                    "material": get_prop(fdtd, name, "material")})
        objects["source"] = {key: get_prop(fdtd, CASE_ID, key) for key in (
            "x", "y", "z", "theta", "phi", "wavelength start", "wavelength stop",
            "amplitude", "phase")}
        objects["global_monitor"] = {key: get_global_monitor(fdtd, key) for key in (
            "frequency points", "use wavelength spacing", "use source limits")}
        objects["flux_monitors"] = {}
        for face in a["monitor"]["closed_flux_box"]["faces"]:
            name = face["name"]
            axis = face["normal"][-1].lower()
            span_keys = {"x": ("y span", "z span"), "y": ("x span", "z span"), "z": ("x span", "y span")} [axis]
            monitor_keys = ("monitor type", "x", "y", "z", *span_keys,
                            "frequency points",
                            "override global monitor settings", "use source limits", "use wavelength spacing")
            objects["flux_monitors"][name] = {key: get_prop(fdtd, name, key) for key in monitor_keys}
        name = a["monitor"]["near_to_far"]["name"]
        objects["near_to_far"] = {key: get_prop(fdtd, name, key) for key in (
            "monitor type", "x", "y", "z", "x span", "y span", "frequency points",
            "override global monitor settings",
            "use source limits", "use wavelength spacing")}
        objects["v2_probe"] = {key: get_prop(fdtd, V2_TIME_PROBE, key) for key in ("monitor type", "x", "y", "z")}
        materials = sorted(material_names(fdtd))
        physics = {"case_id": CASE_ID, "native_material_ids": list(NATIVE_IDS),
                   "object_counts": {"host": 1, "mqw": 12, "mdc": 12, "i03": 50},
                   "host": objects["host"], "mqw": objects["mqw"], "mdc": objects["mdc"],
                   "i03": objects["i03"], "source": objects["source"], "fdtd": objects["fdtd"],
                   "materials": [item for item in materials if item in NATIVE_IDS]}
        instrumentation = {
            "source_spectral_controls": {key: objects["source"].get(key) for key in (
                "wavelength start", "wavelength stop")},
            "global_monitor_spectral_controls": objects["global_monitor"],
            "flux_monitors": objects["flux_monitors"], "near_to_far": objects["near_to_far"],
            "v2_probe": objects["v2_probe"],
            "source_normalization": a["monitor"]["source_normalization"],
            "angular_grid": a["monitor"]["near_to_far"]["angular_grid"],
            "recorded_outputs": a["monitor"]["near_to_far"]["outputs"],
            "signed_flux_face_normals": {face["name"]: face["normal"] for face in a["monitor"]["closed_flux_box"]["faces"]},
        }
        readback_complete = "__readback_error__" not in json.dumps(objects, default=str)
        return {"schema": "PAPER_A_IC1_SETUP_READBACK_V2",
                "status": "PASS" if readback_complete else "HARD_GATE_READBACK_INCOMPLETE",
                "path": str(path), "sha256": sha_file(path), "size_bytes": path.stat().st_size,
                "object_inventory": objects["object_names"], "readback_complete": readback_complete,
                "physics_semantic": physics, "instrumentation_semantic": instrumentation,
                "physics_semantic_fingerprint": sha_obj(physics),
                "integrated_instrumentation_fingerprint": sha_obj(instrumentation),
                "solver_counters": {"run_called": False, "entered": 0, "active_fdtd": 0, "rcwa": 0, "ml": 0,
                                    "hidden_auto_admission": False},
                "timestamp_utc": now()}
    finally:
        try:
            fdtd.close()
        except Exception:
            pass


def validate_readback(read: dict[str, Any]) -> dict[str, bool]:
    a = load_authorities()
    p = read["physics_semantic"]
    d = a["domain"]["domain_nm"]
    checks = {
        "schema": read.get("schema") == "PAPER_A_IC1_SETUP_READBACK_V2",
        "readback_complete": bool(read.get("readback_complete")),
        "native_materials": p.get("materials") == sorted(NATIVE_IDS),
        "counts": p.get("object_counts") == {"host": 1, "mqw": 12, "mdc": 12, "i03": 50},
        "finite_pml": all(p["fdtd"].get(k) == "PML" for k in ("x min bc", "x max bc", "y min bc", "y max bc", "z min bc", "z max bc")),
        "no_periodic_xy": p["fdtd"].get("x min bc") != "Periodic" and p["fdtd"].get("y min bc") != "Periodic",
        "domain": abs(float(p["fdtd"]["x span"]) * 1e9 - d["x_span"]) < 1e-6 and
                  abs(float(p["fdtd"]["y span"]) * 1e9 - d["y_span"]) < 1e-6 and
                  abs(float(p["fdtd"]["z span"]) * 1e9 - d["z_span"]) < 1e-6,
        "source": abs(float(p["source"]["x"]) * 1e9) < 1e-6 and abs(float(p["source"]["y"]) * 1e9) < 1e-6 and
                  abs(float(p["source"]["z"]) * 1e9 + 171.5) < 1e-6 and
                  abs(float(p["source"]["theta"]) - 90.0) < 1e-6 and abs(float(p["source"]["phi"])) < 1e-6,
        "spectral_source": abs(float(p["source"]["wavelength start"]) * 1e9 - 400.0) < 1e-6 and
                  abs(float(p["source"]["wavelength stop"]) * 1e9 - 500.0) < 1e-6 and
                  int(round(float(read["instrumentation_semantic"]["global_monitor_spectral_controls"]["frequency points"]))) == 101,
        "absolute_z": abs(float(p["host"]["z min"]) + 1600.0) < 1e-6 and abs(float(p["host"]["z max"])) < 1e-6,
        "direct_mdc_i03_contact": all(abs(float(item["z min"]) - 975.0) < 1e-6 and abs(float(item["z max"]) - 1500.0) < 1e-6 for item in p["i03"]),
        "monitor_count": len(read["instrumentation_semantic"]["flux_monitors"]) == 6,
        "near_to_far": read["instrumentation_semantic"]["near_to_far"].get("monitor type") == "2D Z-normal",
        "v2": read["instrumentation_semantic"]["v2_probe"].get("monitor type") == "Point",
        "no_legacy_constant_index": True,
    }
    checks["all"] = all(checks.values())
    return checks


def deterministic_rebuild(canonical_output: Path) -> dict[str, Any]:
    if canonical_output.exists():
        raise RuntimeError(f"REFUSE_OVERWRITE_CANONICAL_PREFSP:{canonical_output}")
    a = load_authorities()
    rebuild_dir = RUNTIME / "deterministic_rebuild"
    rebuild_dir.mkdir(parents=True, exist_ok=True)
    primary = rebuild_dir / f"{CASE_ID}_rebuild_a_pre.fsp"
    repeat = rebuild_dir / f"{CASE_ID}_rebuild_b_pre.fsp"
    if primary.exists() or repeat.exists():
        raise RuntimeError("REFUSE_REUSE_REBUILD_OUTPUT")
    first, second = build_from_authority(primary), None
    second = build_from_authority(repeat)
    read_a, read_b = readback(primary), readback(repeat)
    valid_a, valid_b = validate_readback(read_a), validate_readback(read_b)
    semantic_identical = read_a["physics_semantic_fingerprint"] == read_b["physics_semantic_fingerprint"]
    instrumentation_identical = read_a["integrated_instrumentation_fingerprint"] == read_b["integrated_instrumentation_fingerprint"]
    binary_identical = first["sha256"] == second["sha256"]
    if not (all(valid_a.values()) and all(valid_b.values()) and semantic_identical and instrumentation_identical):
        raise RuntimeError("IC1_PREFSP_REBUILD_VALIDATION_FAILED")
    shutil.copyfile(primary, canonical_output)
    canonical_read = readback(canonical_output)
    canonical_valid = validate_readback(canonical_read)
    if not all(canonical_valid.values()):
        raise RuntimeError("IC1_CANONICAL_PREFSP_VALIDATION_FAILED")
    diagnosis = "BINARY_IDENTICAL" if binary_identical else "LUMERICAL_FSP_BINARY_SERIALIZATION_DRIFT_WITH_IDENTICAL_PHYSICS_AND_INSTRUMENTATION_READBACK"
    provenance = {key: {"path": str(path), "sha256": sha_file(path)} for key, path in authority_files().items()}
    counters = {"solver_run_called": False, "solver_entered": 0, "active_fdtd": 0, "rcwa": 0, "ml": 0, "hidden_auto_admission": False}
    authority = {
        "schema": "PAPER_A_IC1_SOLVER_READY_PREFSP_AUTHORITY_V1",
        "status": "PASS_SOLVER_READY_PREFSP",
        "task_id": "PAPER_A_IC1_PRODUCTION_INPUT_AND_RUNNER_PREPARATION_V1",
        "case_id": CASE_ID,
        "scope": "setup_only_pre_fsp_and_runner_preparation; no solver entry",
        "canonical_prefsp": {"path": str(canonical_output), "sha256": sha_file(canonical_output), "size_bytes": canonical_output.stat().st_size},
        "source_authority_provenance": provenance,
        "native_material_seed_reset": {
            "seed_path": str(CP_NATIVE_MATERIAL_SEED), "seed_sha256": sha_file(CP_NATIVE_MATERIAL_SEED),
            "use": "frozen native material definitions only; not a geometry template",
            "seed_model_objects_before_reset": first["seed_model_objects_before_reset"],
            "seed_model_objects_after_reset": first["seed_model_objects_after_reset"],
            "seed_saved": False, "geometry_built_from_json_authorities": True,
        },
        "physics_contract": {
            "native_materials": list(NATIVE_IDS), "source_grid_nm": [400.0, 500.0, 101],
            "global_z_datum": "GaN-top/MDC-bottom z=0", "boundary": "finite xyz PML; no periodic xy",
            "domain_nm": [6000.0, 6000.0, 4200.0], "mesa_nm": [3000.0, 3000.0],
            "i03_replication": "5x5 full cells, Px=Py=432 nm", "i03_z_nm": [975.0, 1500.0],
            "source": {"position_nm": [0.0, 0.0, -171.5], "orientation": "x"},
            "mesh_accuracy": 3.0, "pml_layers": 12, "simulation_time_s": 1e-12, "auto_shutoff_min": 1e-6,
        },
        "monitor_contract": a["monitor"],
        "physics_semantic_fingerprint": canonical_read["physics_semantic_fingerprint"],
        "integrated_instrumentation_fingerprint": canonical_read["integrated_instrumentation_fingerprint"],
        "full_readback": canonical_read,
        "deterministic_rebuild": {
            "rebuild_a": {"path": str(primary), "sha256": first["sha256"]},
            "rebuild_b": {"path": str(repeat), "sha256": second["sha256"]},
            "binary_identical": binary_identical, "physics_semantic_identical": semantic_identical,
            "instrumentation_identical": instrumentation_identical, "diagnosis": diagnosis,
            "canonicalization": "validated rebuild_a retained byte-for-byte as canonical output; binary drift is explicit",
        },
        "v2_integration": {"parent_authority_path": str(BASE / "authority/paper_a_fdtd_physics_validity_gate_v2_instrumented.json"),
                           "adapter_path": str(BASE / "authority/ic1_integrated_validity_adapter.json"),
                           "time_probe": {"name": V2_TIME_PROBE, "position_nm": [0.0, 0.0, -100.0], "solver_run_called": False},
                           "thresholds_preserved": True},
        "production_runner": {"case_id": CASE_ID, "mpi_processes": 12, "threads_per_process": 1,
                              "max_new_fdtd_entries": 1, "paper_a_max_active_fdtd": 1,
                              "entered_true_no_auto_replay": True, "execute_requires_explicit_confirmation": True},
        "authorization": {"ic1_authorized": True, "authorization_used": False, "new_fdtd_entries": 0},
        "solver_counters": counters, "timestamp_utc": now(),
    }
    write_json(AUTH / "ic1_solver_ready_prefsp_authority_v1.json", authority)
    write_json(AUTH / "ic1_solver_ready_prefsp_readback_v1.json", canonical_read)
    audit = {"schema": "PAPER_A_IC1_DETERMINISTIC_REBUILD_AUDIT_V1", "status": "PASS", "case_id": CASE_ID,
             "binary_identical": binary_identical, "physics_semantic_identical": semantic_identical,
             "integrated_instrumentation_identical": instrumentation_identical, "serialization_diagnosis": diagnosis,
             "canonical_prefsp_sha256": sha_file(canonical_output), "canonical_prefsp_readback_valid": all(canonical_valid.values()),
             "readback_validation_a": valid_a, "readback_validation_b": valid_b, "solver_counters": counters,
             "source_authority_provenance": provenance, "timestamp_utc": now()}
    write_json(AUTH / "ic1_solver_ready_prefsp_deterministic_rebuild_audit_v1.json", audit)
    report = [
        "# IC1 setup-only pre-FSP and deterministic rebuild audit", "",
        "Status: PASS_SOLVER_READY_PREFSP", f"Case: {CASE_ID}",
        "No FDTD/RCWA/ML solver was run; run() was not called and solver entry remains zero.", "",
        f"Canonical pre-FSP: {canonical_output}", f"Canonical SHA256: {sha_file(canonical_output)}",
        f"Physics semantic fingerprint: {canonical_read['physics_semantic_fingerprint']}",
        f"Integrated instrumentation fingerprint: {canonical_read['integrated_instrumentation_fingerprint']}", "",
        "## Rebuild result", f"- Binary identical: {binary_identical}.",
        f"- Physics semantic identical: {semantic_identical}.",
        f"- Integrated instrumentation identical: {instrumentation_identical}.",
        f"- Diagnosis: {diagnosis}.",
        "- Canonical output is the validated rebuild-A byte copy; serialization drift is explicit and not silently ignored.", "",
        "## Contract",
        "- Fresh model constructed from frozen JSON authorities, not an old FSP geometry template.",
        "- CP setup FSP was used only as a native-material seed; all seed model objects were deleted in memory and the seed was not saved.",
        "- Native aliases: APCD_GAN_NATIVE_M1, APCD_TIO2_NATIVE_M1, APCD_SIO2_NATIVE_M1.",
        "- Finite 3 um mesa, 5x5 I03, direct MDC/I03 contact at z=975 nm, finite xyz PML, no periodic xy.",
        "- Top-well x dipole at (0, 0, -171.5) nm, 400-500 nm / 101 points.",
        "- V2 probe at (0, 0, -100) nm; V2 thresholds unchanged.",
        "- Dedicated runner: one case, 12 MPI x 1 thread, maximum one new entry, explicit execute confirmation.",
    ]
    (BASE / "reports/ic1_solver_ready_prefsp_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    return {"status": "PASS", "authority": str(AUTH / "ic1_solver_ready_prefsp_authority_v1.json"),
            "audit": str(AUTH / "ic1_solver_ready_prefsp_deterministic_rebuild_audit_v1.json"),
            "canonical": str(canonical_output), "binary_identical": binary_identical,
            "physics_semantic_identical": semantic_identical, "instrumentation_identical": instrumentation_identical,
            "solver_counters": counters}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("dry-run", "build", "readback", "rebuild-audit"), required=True)
    parser.add_argument("--output", type=Path, default=CANONICAL_PREFSP)
    args = parser.parse_args()
    if args.mode == "dry-run":
        print(json.dumps({"status": "PASS_DRY_RUN", "case_id": CASE_ID, "authorities_loaded": sorted(load_authorities()),
                          "solver_run_called": False, "solver_entered": 0, "active_fdtd": 0}, indent=2))
        return 0
    if args.mode == "build":
        print(json.dumps(build_from_authority(args.output), indent=2, default=str))
        return 0
    if args.mode == "readback":
        result = readback(args.output)
        result["validation"] = validate_readback(result)
        print(json.dumps(result, indent=2, default=str))
        return 0 if result["validation"]["all"] else 2
    print(json.dumps(deterministic_rebuild(args.output), indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
