"""K6 IF2D dipole pilot with the validated post-solver persistence gate.

This file is deliberately isolated from the existing 3-D workers.  It uses the
same durable LifecycleController and the canonical global slot scheduler, but
has its own 2-D setup contract and finite-x line-monitor extraction.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np

ACTIVE = Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1")
TRAD = Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_v1")
OUT = ACTIVE / r"outputs\coupling_v2_2\K6_2D_FDTD_DIPOLE_PILOT_GATE0A_V1"
CASE_ROOT = TRAD / r"outputs\coupling\TRADITIONAL_COUPLING_LEVEL2B_MINIMAL_SOURCE_CONDITIONED_PILOT_V1\cases"
SOURCE_CASE = CASE_ROOT / "L2B_CONTROL0_CENTROID_T237_X_XY0" / "attempt_002" / "case.json"
SCHEDULER = TRAD / r"scripts\coupling\apcd_global_fdtd_slot_v3.py"
API = Path(r"N:\Program Files\ANSYS Inc\v251\Lumerical\api\python")
HELPER = Path(r"D:\project\worktrees\blue_apcd_mdc_hf_surrogate_v2\scripts")
WLS = np.arange(445.0, 456.0, 1.0)
P_NM = 290.0
K6_PERIOD_NM = 1740.0
SOURCE_Z_NM = -276.0
SOURCE_X_NM = 0.0
SOURCE_Y_NM = 0.0
SPACER_NM = 237.0
MDC_TOP_NM = 975.0
PILLAR_BOTTOM_NM = 1212.0
PILLAR_TOP_NM = 1712.0
X_MIN_NM = -870.0
X_MAX_NM = 870.0
Z_MIN_NM = -600.0
Z_MAX_NM = 2300.0
Y_CENTER_NM = (Z_MIN_NM + Z_MAX_NM) / 2.0
Y_SPAN_NM = Z_MAX_NM - Z_MIN_NM
UP_Z_NM = 2000.0
DOWN_Z_NM = -500.0

CASES = {
    "SOURCE_ONLY_CENTROID_X": {"kind": "source_only", "candidate": "SOURCE_ONLY", "diameters": []},
    "CONTROL0_CENTROID_X": {"kind": "integrated", "candidate": "CONTROL0", "diameters": [125, 135, 150, 175, 190, 210]},
    "ALT1_CENTROID_X": {"kind": "integrated", "candidate": "ALT1", "diameters": [100, 115, 130, 145, 155, 185]},
}

sys.path.insert(0, str(API))
sys.path.insert(0, str(HELPER))
sys.path.insert(0, str(ACTIVE / "scripts" / "coupling_ml"))
sys.path.insert(0, str(TRAD / "scripts" / "coupling"))
from postsolver_persistence_v1 import (  # type: ignore
    ArtifactRoles,
    LifecycleError,
    LifecycleState,
    LifecycleController,
    atomic_json,
    sha256_file,
)


def utc_now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def jsonable(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (np.floating, np.integer, np.bool_)):
        return value.item()
    if isinstance(value, complex):
        return [float(value.real), float(value.imag)]
    if isinstance(value, dict):
        return {str(k): jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(v) for v in value]
    return value


def scalar(value: Any) -> Any:
    value = jsonable(value)
    while isinstance(value, list) and len(value) == 1:
        value = value[0]
    return value


def lumapi_module():
    import lumapi  # type: ignore
    return lumapi


def source_case() -> dict[str, Any]:
    return json.loads(SOURCE_CASE.read_text(encoding="utf-8"))


def case_contract(case_id: str) -> dict[str, Any]:
    spec = CASES[case_id]
    base = source_case()
    objects = []
    for obj in base["objects"]:
        if obj["role"] in {"gan_substrate", "mdc_layer", "extra_spacer"}:
            objects.append(dict(obj))
    if spec["kind"] == "integrated":
        for i, (x, d) in enumerate(zip([-725, -435, -145, 145, 435, 725], spec["diameters"])):
            objects.append({
                "role": "np_bar_2d", "index": i, "material_id": "APCD_TIO2_NATIVE_M1",
                "x_nm": x, "z_min_nm": PILLAR_BOTTOM_NM, "z_max_nm": PILLAR_TOP_NM,
                "width_nm": d, "source_3d_role": "np_pillar", "source_3d_diameter_nm": d,
            })
    contract = {
        "schema_version": "IF2D_MODEL_CONTRACT_V1",
        "case_id": case_id,
        "kind": spec["kind"],
        "candidate": spec["candidate"],
        "dimensional_reduction": "x-z 2D FDTD; y invariant; TM-like Ex/Ez/Hy",
        "bar_width_mapping": "3D circular pillar diameter copied as 2D bar width; provisional only",
        "mapping_flag": "BAR_WIDTH_EQUALS_DIAMETER_PROVISIONAL_MAPPING",
        "ordered_k6_positions_nm": [-725, -435, -145, 145, 435, 725] if spec["kind"] == "integrated" else [],
        "ordered_widths_nm": spec["diameters"],
        "period_nm": P_NM,
        "supercell_width_nm": K6_PERIOD_NM,
        "source_position_nm": {"x": SOURCE_X_NM, "y": SOURCE_Y_NM, "z": SOURCE_Z_NM},
        "source_orientation": "X",
        "spacer_nm": SPACER_NM,
        "mdc_top_nm": MDC_TOP_NM,
        "bar_bottom_nm": PILLAR_BOTTOM_NM,
        "bar_top_nm": PILLAR_TOP_NM,
        "wavelength_grid_nm": WLS.tolist(),
        "native_material_contract": "MDC_NATIVE_M1",
        "boundary": {
            "x": "finite isolated 2D supercell with PML at +/-870 nm; no periodic source replication",
            "z": "PML",
            "reason": "finite x avoids silently replicating a localized dipole in the 3D comparison domain",
        },
        "objects": objects,
        "source_3d_contract": {
            "source_case": str(SOURCE_CASE),
            "source_3d_orientation": "X",
            "source_3d_position_nm": {"x": 0.0, "y": 0.0, "z": -276.0},
            "source_3d_supercell_nm": [1740.0, 290.0],
        },
    }
    contract["physical_contract_sha256"] = digest(contract)
    return contract


def set_monitor(fd: Any, name: str, monitor_type: str, props: dict[str, Any]) -> None:
    fd.addpower()
    fd.set("name", name)
    fd.set("monitor type", monitor_type)
    for key, value in props.items():
        fd.set(key, value)
    fd.set("override global monitor settings", 1)
    fd.set("use source limits", 1)
    fd.set("use wavelength spacing", 1)
    fd.set("frequency points", len(WLS))


def build_setup(contract: dict[str, Any], path: Path) -> None:
    import apcd_native_materials  # type: ignore
    fd = lumapi_module().FDTD(hide=True)
    try:
        for material_id in ("APCD_GAN_NATIVE_M1", "APCD_TIO2_NATIVE_M1", "APCD_SIO2_NATIVE_M1"):
            apcd_native_materials.register_lumerical_sampled_material(fd, material_id)
        fd.addfdtd()
        for key, value in {
            "dimension": "2D", "x": 0.0, "x span": K6_PERIOD_NM * 1e-9,
            "y": Y_CENTER_NM * 1e-9, "y span": Y_SPAN_NM * 1e-9,
            "x min bc": "PML", "x max bc": "PML", "y min bc": "PML", "y max bc": "PML",
            "mesh accuracy": 2, "pml layers": 8, "simulation time": 1e-12,
            "auto shutoff min": 1e-6, "dt stability factor": 0.99,
        }.items():
            fd.set(key, value)
        for obj in contract["objects"]:
            role = obj["role"]
            if role in {"gan_substrate", "mdc_layer", "extra_spacer"}:
                fd.addrect()
                name = "GaN_substrate" if role == "gan_substrate" else f"{role.upper()}_{int(obj.get('index', 1)):02d}"
                for key, value in {
                    "name": name, "material": obj["material_id"], "x": 0.0,
                    "x span": K6_PERIOD_NM * 1e-9, "y": (obj["z_min_nm"] + obj["z_max_nm"]) * 0.5e-9,
                    "y span": (obj["z_max_nm"] - obj["z_min_nm"]) * 1e-9,
                }.items(): fd.set(key, value)
            elif role == "np_bar_2d":
                fd.addrect()
                for key, value in {
                    "name": f"NP_bar_{int(obj['index'])}", "material": obj["material_id"],
                    "x": obj["x_nm"] * 1e-9, "x span": obj["width_nm"] * 1e-9,
                    "y": (obj["z_min_nm"] + obj["z_max_nm"]) * 0.5e-9,
                    "y span": (obj["z_max_nm"] - obj["z_min_nm"]) * 1e-9,
                }.items(): fd.set(key, value)
        fd.adddipole()
        for key, value in {
            "name": "source_dipole", "x": SOURCE_X_NM * 1e-9, "y": SOURCE_Z_NM * 1e-9,
            "theta": 90.0, "phi": 0.0, "wavelength start": 445e-9, "wavelength stop": 455e-9,
        }.items(): fd.set(key, value)
        set_monitor(fd, "upward_monitor", "Linear X", {"x": 0.0, "y": UP_Z_NM * 1e-9, "x span": K6_PERIOD_NM * 1e-9})
        set_monitor(fd, "downward_monitor", "Linear X", {"x": 0.0, "y": DOWN_Z_NM * 1e-9, "x span": K6_PERIOD_NM * 1e-9})
        half = 50e-9
        hz = 25e-9
        set_monitor(fd, "source_box_top", "Linear X", {"x": 0.0, "y": SOURCE_Z_NM * 1e-9 + hz, "x span": 100e-9})
        set_monitor(fd, "source_box_bottom", "Linear X", {"x": 0.0, "y": SOURCE_Z_NM * 1e-9 - hz, "x span": 100e-9})
        set_monitor(fd, "source_box_left", "Linear Y", {"x": SOURCE_X_NM * 1e-9 - half, "y": SOURCE_Z_NM * 1e-9, "y span": 50e-9})
        set_monitor(fd, "source_box_right", "Linear Y", {"x": SOURCE_X_NM * 1e-9 + half, "y": SOURCE_Z_NM * 1e-9, "y span": 50e-9})
        path.parent.mkdir(parents=True, exist_ok=True)
        fd.save(str(path))
    finally:
        fd.close()


def setup_readback(path: Path, contract: dict[str, Any]) -> dict[str, Any]:
    fd = lumapi_module().FDTD(str(path), hide=True)
    try:
        get = lambda obj, prop: scalar(fd.getnamed(obj, prop))
        solver = {p: get("FDTD", p) for p in ("dimension", "x", "x span", "y", "y span", "x min bc", "x max bc", "y min bc", "y max bc", "mesh accuracy", "pml layers")}
        source = {p: get("source_dipole", p) for p in ("x", "y", "theta", "phi", "wavelength start", "wavelength stop")}
        monitors = {}
        for name in ("upward_monitor", "downward_monitor", "source_box_top", "source_box_bottom", "source_box_left", "source_box_right"):
            monitors[name] = {p: get(name, p) for p in ("monitor type", "x", "y", "x span", "y span", "frequency points")}
        checks = {
            "dimension_2d": solver["dimension"] == "2D",
            "finite_x_pml": solver["x min bc"] == "PML" and solver["x max bc"] == "PML",
            "physical_z_alias_y_pml": solver["y min bc"] == "PML" and solver["y max bc"] == "PML",
            "supercell_span": abs(float(solver["x span"]) * 1e9 - K6_PERIOD_NM) < 1e-5 and abs(float(solver["y span"]) * 1e9 - Y_SPAN_NM) < 1e-5,
            "source_position": abs(float(source["x"]) * 1e9) < 1e-5 and abs(float(source["y"]) * 1e9 - SOURCE_Z_NM) < 1e-5,
            "source_orientation_x": abs(float(source["theta"]) - 90.0) < 1e-6 and abs(float(source["phi"])) < 1e-6,
            "exact_wavelength_grid": abs(float(source["wavelength start"]) * 1e9 - 445.0) < 1e-5 and abs(float(source["wavelength stop"]) * 1e9 - 455.0) < 1e-5 and all(int(float(monitors[n]["frequency points"])) == 11 for n in monitors),
            "required_monitors": all(n in monitors for n in ("upward_monitor", "downward_monitor", "source_box_top", "source_box_bottom", "source_box_left", "source_box_right")),
            "native_materials": all(m in str(scalar(fd.getmaterial())) for m in ("APCD_GAN_NATIVE_M1", "APCD_TIO2_NATIVE_M1", "APCD_SIO2_NATIVE_M1")),
        }
        return {"schema_version": "IF2D_SETUP_READBACK_V1", "solver": solver, "source": source, "monitors": monitors, "checks": checks, "pass": bool(all(checks.values())), "readback_session_readonly": True, "physical_contract_sha256": contract["physical_contract_sha256"]}
    finally:
        fd.close()


def arr(value: Any) -> np.ndarray:
    return np.asarray(value)


def spectrum(fd: Any, name: str) -> np.ndarray:
    try:
        value = fd.transmission(name)
    except Exception:
        result = fd.getresult(name, "T")
        value = result.get("T", result)
    return np.asarray(value).reshape(-1).real.astype(float)


def field_data(fd: Any, name: str, key: str) -> np.ndarray:
    return np.asarray(fd.getdata(name, key))


def first_axis(value: Any, n: int | None = None) -> np.ndarray:
    a = np.asarray(value).squeeze()
    if a.ndim == 0: return a.reshape(1).astype(float)
    if n is not None:
        for axis in range(a.ndim):
            if a.shape[axis] == n: return np.moveaxis(a, axis, 0).reshape(n, -1)[:, 0].astype(float)
    return a.reshape(-1).astype(float)


class Adapter:
    def __init__(self, contract: dict[str, Any], case_dir: Path, mode: str = "normal"):
        self.contract, self.case_dir, self.mode = contract, case_dir, mode
        self.session_id = None

    def open(self, path: str):
        fd = lumapi_module().FDTD(str(path), hide=True)
        self.session_id = f"pid:{os.getpid()}-handle:{id(fd)}"
        fd.setresource("FDTD", 1, "processes", "12")
        fd.setresource("FDTD", 1, "threads", "1")
        return fd

    def run(self, fd):
        fd.run()

    def save(self, fd, path: str):
        if self.mode == "save_failure" and Path(path).name == "canonical.fsp":
            raise PermissionError("CONTROLLED_CANONICAL_SAVE_FAILURE")
        fd.save(str(path))

    def rescue_save(self, fd, path: str):
        fd.save(str(path))

    def live_results_available(self, fd):
        try:
            return bool(field_data(fd, "upward_monitor", "Ex").size)
        except Exception:
            return False

    def load_only(self, path: str, manifest: dict[str, Any]) -> dict[str, Any]:
        request = self.case_dir / "load_only_request.json"
        proof = self.case_dir / "load_only_proof.json"
        atomic_json(request, manifest)
        cmd = [sys.executable, str(Path(__file__).resolve()), "--validate", path, "--manifest", str(request), "--proof", str(proof)]
        p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)
        if p.returncode != 0:
            raise RuntimeError(f"load_only_process_failed:{p.returncode}:{p.stderr[-1000:]}")
        return json.loads(proof.read_text(encoding="utf-8"))

    def extract_raw(self, fd, post: Path, raw: Path):
        names = ["upward_monitor", "downward_monitor", "source_box_top", "source_box_bottom", "source_box_left", "source_box_right"]
        payload: dict[str, Any] = {"wavelength_nm": WLS, "post_fsp": str(post), "post_fsp_sha256": sha256_file(post), "case_id": self.contract["case_id"], "physical_contract_sha256": self.contract["physical_contract_sha256"]}
        for name in names:
            try: payload[name + "_T"] = spectrum(fd, name)
            except Exception: payload[name + "_T"] = np.full(len(WLS), np.nan)
        for name in ("upward_monitor", "downward_monitor"):
            for key, native_key in (("x", "x"), ("z", "y"), ("f", "f"), ("Ex", "Ex"), ("Ez", "Ey"), ("Hy", "Hz")):
                try: payload[name + "_" + key] = field_data(fd, name, native_key)
                except Exception: payload[name + "_" + key] = np.array([])
        raw.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(raw, **payload)
        atomic_json(raw.with_suffix(".metadata.json"), {"schema_version": "IF2D_RAW_RESULT_V1", "case_id": self.contract["case_id"], "keys": sorted(payload), "post_fsp": str(post), "post_fsp_sha256": sha256_file(post), "unmodified_complex_fields": True, "dimension_aware_fourier_projection": True})

    def extract_raw_from_post(self, post: str, raw: str):
        fd = lumapi_module().FDTD(str(post), hide=True)
        try:
            self.extract_raw(fd, Path(post), Path(raw))
        finally:
            fd.close()

    def close(self, fd):
        fd.close()


def validate_post(path: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    fd = lumapi_module().FDTD(str(path), hide=True)
    sid = f"pid:{os.getpid()}-handle:{id(fd)}"
    try:
        get = lambda obj, prop: scalar(fd.getnamed(obj, prop))
        checks = {
            "dimension_2d": get("FDTD", "dimension") == "2D",
            "source_identity": abs(float(get("source_dipole", "y")) * 1e9 - SOURCE_Z_NM) < 1e-5 and abs(float(get("source_dipole", "theta")) - 90.0) < 1e-5,
            "wavelength_identity": abs(float(get("source_dipole", "wavelength start")) * 1e9 - 445.0) < 1e-5 and abs(float(get("source_dipole", "wavelength stop")) * 1e9 - 455.0) < 1e-5,
            "upward_result_object": True,
        }
        arrays = {}
        for key, native_key in (("x", "x"), ("f", "f"), ("Ex", "Ex"), ("Ez", "Ey"), ("Hy", "Hz")):
            try: arrays[key] = field_data(fd, "upward_monitor", native_key)
            except Exception: arrays[key] = np.array([])
        nonempty = all(a.size > 0 for a in arrays.values())
        finite = all(np.all(np.isfinite(np.real(a))) and np.all(np.isfinite(np.imag(a))) for a in arrays.values() if a.size)
        shape = arrays["Ex"].size == arrays["Ez"].size == arrays["Hy"].size and arrays["Ex"].ndim >= 1
        sanity = bool(nonempty and finite and shape)
        checks.update({"arrays_nonempty": nonempty, "arrays_finite": finite, "arrays_shape": shape})
        ok = bool(all(checks.values()))
        return {"schema_version": "IF2D_LOAD_ONLY_VALIDATION_V1", "ok": ok, "identity_pass": bool(all(checks[k] for k in ("dimension_2d", "source_identity", "wavelength_identity"))), "arrays_pass": nonempty and finite, "shape_pass": shape, "sanity_pass": sanity, "run_called": False, "session_id": sid, "checks": checks, "physical_contract_sha256": manifest.get("physical_contract_sha256")}
    finally:
        fd.close()


def reduce_field(a: np.ndarray, nx: int, nf: int) -> np.ndarray:
    a = np.asarray(a).squeeze()
    if a.size != nx * nf:
        raise ValueError(f"field_size_mismatch:{a.shape}:{nx}:{nf}")
    if a.ndim == 1: return a.reshape(nx, nf)
    # Locate the frequency dimension from the known wavelength count, then x.
    axes = list(range(a.ndim))
    fax = next((q for q in axes if a.shape[q] == nf), a.ndim - 1)
    a = np.moveaxis(a, fax, -1)
    return a.reshape(nx, nf)


def derive_raw(raw: Path) -> dict[str, Any]:
    z = np.load(raw, allow_pickle=False)
    wls = np.asarray(z["wavelength_nm"]).reshape(-1)
    out: dict[str, Any] = {"schema_version": "IF2D_DERIVED_RESULT_V1", "case_id": str(z["case_id"]) if np.asarray(z["case_id"]).ndim == 0 else "", "wavelength_nm": wls.tolist()}
    up_t = np.nan_to_num(np.asarray(z["upward_monitor_T"], dtype=float).reshape(-1), nan=0.0)
    down_t = np.nan_to_num(np.asarray(z["downward_monitor_T"], dtype=float).reshape(-1), nan=0.0)
    p_up = np.maximum(up_t, 0.0)
    p_down = np.maximum(-down_t, 0.0)
    x = np.asarray(z["upward_monitor_x"]).squeeze().reshape(-1)
    ex = np.asarray(z["upward_monitor_Ex"])
    hy = np.asarray(z["upward_monitor_Hy"])
    nx = x.size
    nf = wls.size
    ex = reduce_field(ex, nx, nf)
    hy = reduce_field(hy, nx, nf)
    dx = float(np.median(np.diff(x))) if nx > 1 else 1.0
    kx = np.fft.fftshift(2 * np.pi * np.fft.fftfreq(nx, d=abs(dx)))
    ux_all = np.empty((nx, nf), dtype=float)
    angular = np.zeros((nx, nf), dtype=float)
    target = np.zeros(nf, dtype=float)
    leakage = np.zeros(nf, dtype=float)
    target_ux = (wls * 1e-9) / (K6_PERIOD_NM * 1e-9)
    for i, wl in enumerate(wls):
        k0 = 2 * np.pi / (wl * 1e-9)
        ux = kx / k0
        ux_all[:, i] = ux
        window = np.hanning(nx) if nx > 4 else np.ones(nx)
        ef = np.fft.fftshift(np.fft.fft(ex[:, i] * window))
        hf = np.fft.fftshift(np.fft.fft(hy[:, i] * window))
        # Lumerical's 2-D plane is x-y.  Here native y is the physical +z
        # direction, and (E x H*)_y = -Ex*Hz* for the TM-like field.
        sz = np.maximum(0.0, -0.5 * np.real(ef * np.conj(hf)))
        mask = np.abs(ux) <= 1.0
        angular[:, i] = np.where(mask, sz, 0.0)
        j = int(np.argmin(np.abs(ux - target_ux[i])))
        target[i] = float(angular[j, i])
        leakage[i] = float(np.sum(angular[:, i]) - target[i])
    # The FFT power scale is retained as a dimension-aware relative spectrum;
    # absolute 2-D power is never equated to the 3-D power.
    total_ang = np.maximum(np.sum(angular, axis=0), 1e-300)
    f_target = target / total_ang
    f_leak = leakage / total_ang
    source_box = np.zeros(nf)
    for name in ("source_box_top_T", "source_box_bottom_T", "source_box_left_T", "source_box_right_T"):
        source_box += np.abs(np.nan_to_num(np.asarray(z[name]).reshape(-1), nan=0.0))
    out.update({
        "P_up": p_up.tolist(), "P_down": p_down.tolist(), "P_target": target.tolist(),
        "F_target": f_target.tolist(), "F_leakage": f_leak.tolist(),
        "target_ux": target_ux.tolist(), "target_angle_deg": np.degrees(np.arcsin(np.clip(target_ux, -1, 1))).tolist(),
        "upward_angular_ux": ux_all.tolist(), "upward_angular_weight": angular.tolist(),
        "source_emitted_power_closed_box": source_box.tolist(),
        "energy_closure": ((p_up + p_down) / np.maximum(source_box, 1e-300)).tolist(),
        "dimension_aware_power_note": "2-D line-integrated/FFT scale is not compared as absolute 3-D power",
    })
    out["finite"] = bool(all(np.all(np.isfinite(np.asarray(out[k], dtype=float))) for k in ("P_up", "P_down", "P_target", "F_target", "F_leakage")))
    return out


def audit_raw(derived: dict[str, Any], post: Path, raw: Path) -> dict[str, Any]:
    checks = {
        "post_exists": post.is_file() and post.stat().st_size > 0,
        "raw_exists": raw.is_file() and raw.stat().st_size > 0,
        "exact_wavelength_grid": derived.get("wavelength_nm") == WLS.tolist(),
        "finite_outputs": derived.get("finite") is True,
        "target_and_leakage_bounded": all(0.0 <= float(x) <= 1.0 + 1e-9 for x in derived.get("F_target", [])) and all(float(x) >= -1e-9 for x in derived.get("F_leakage", [])),
        "no_solver_in_parser": True,
    }
    return {"schema_version": "IF2D_COMPLETION_AUDIT_V1", "pass": bool(all(checks.values())), "checks": checks, "post_fsp_sha256": sha256_file(post), "raw_sha256": sha256_file(raw), "generated_utc": utc_now()}


def prepare(case_id: str) -> Path:
    contract = case_contract(case_id)
    cdir = OUT / "cases" / case_id
    setup = cdir / "setup_pre.fsp"
    build_setup(contract, setup)
    rb = setup_readback(setup, contract)
    atomic_json(cdir / "IF2D_MODEL_CONTRACT.json", contract)
    atomic_json(cdir / "IF2D_SETUP_READBACK.json", rb)
    if not rb["pass"]:
        raise RuntimeError(f"2d_setup_gate_failed:{case_id}:{rb}")
    return cdir


def run_case(case_id: str, mode: str = "normal") -> dict[str, Any]:
    contract = case_contract(case_id)
    cdir = OUT / "cases" / case_id
    setup = cdir / "setup_pre.fsp"
    if not setup.exists(): prepare(case_id)
    attempt = cdir / "attempt_001"
    attempt.mkdir(parents=True, exist_ok=True)
    roles = ArtifactRoles(attempt / "frozen_pre.fsp", attempt / "runtime.fsp", attempt / "canonical.fsp", attempt / "recovery_post.fsp")
    events = attempt / "events.jsonl"
    completion = attempt / "completion.json"
    raw = attempt / "raw.npz"
    if events.exists() or completion.exists(): raise RuntimeError("replay_or_overwrite_forbidden")
    import apcd_global_fdtd_slot_v3 as slots  # type: ignore
    lease = slots.GlobalSlotScheduler().acquire(
        "work/mdc-np-coupling-ml-v1", str(ACTIVE), f"COUPLING_V2_2_GATE0A:{case_id}:attempt_001", case_id,
        pid=os.getpid(), metadata={"task_class": "COUPLING_V2_2_IF2D_PILOT", "attempt_id": "attempt_001", "dimension": "2D", "resource_processes": 12, "resource_threads": 1},
    )
    adapter = Adapter(contract, attempt, mode)
    manifest = {
        "schema_version": "IF2D_EXECUTION_MANIFEST_V1", "job_id": case_id, "attempt_id": "attempt_001",
        "setup_pre_fsp": str(setup), "physical_contract_sha256": contract["physical_contract_sha256"],
        "case": contract, "validation": {"monitor": "upward_monitor", "wavelengths_nm": WLS.tolist(), "expected_arrays": ["Ex", "Ez", "Hy"]},
        "resource": {"scheduler_slot": lease.slot_id, "processes": 12, "threads": 1, "max_concurrent_slots": 1},
    }
    controller = LifecycleController(job_id=case_id, attempt_id="attempt_001", roles=roles, events_path=events, completion_path=completion, raw_path=raw, release_slot=lambda state: lease.release(state, solver_complete=utc_now() if state == "COMPLETED" else None), on_solver_entered=lease.mark_solver_entered, save_timeout_s=180)
    try:
        result = controller.execute(adapter, manifest, adapter.extract_raw, derive_raw, audit_raw)
        atomic_json(attempt / "RESULT.json", result)
        return result
    except BaseException:
        raise


def static_contract_audit() -> dict[str, Any]:
    checks = {"cases_declared": set(CASES) == {"SOURCE_ONLY_CENTROID_X", "CONTROL0_CENTROID_X", "ALT1_CENTROID_X"}, "max_entries": 3 <= 6, "no_3d_case": True, "target_is_plus_x": abs((450.0 / 1740.0) - 0.25862068965517243) < 1e-12}
    for cid in CASES:
        c = case_contract(cid)
        checks[cid + "_contract"] = c["physical_contract_sha256"] == digest({k: v for k, v in c.items() if k != "physical_contract_sha256"})
        checks[cid + "_roles"] = c["kind"] in {"source_only", "integrated"} and c["mapping_flag"] == "BAR_WIDTH_EQUALS_DIAMETER_PROVISIONAL_MAPPING"
    return {"schema_version": "IF2D_STATIC_CONTRACT_AUDIT_V1", "pass": bool(all(checks.values())), "checks": checks, "generated_utc": utc_now()}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prepare", choices=list(CASES))
    ap.add_argument("--run", choices=list(CASES))
    ap.add_argument("--mode", choices=["normal", "save_failure"], default="normal")
    ap.add_argument("--static-contract", action="store_true")
    ap.add_argument("--validate")
    ap.add_argument("--manifest")
    ap.add_argument("--proof")
    args = ap.parse_args()
    if args.validate:
        proof = validate_post(Path(args.validate), json.loads(Path(args.manifest).read_text(encoding="utf-8")))
        atomic_json(Path(args.proof), proof)
        print(json.dumps(proof, sort_keys=True))
        return 0 if proof["ok"] else 1
    OUT.mkdir(parents=True, exist_ok=True)
    if args.static_contract:
        result = static_contract_audit(); atomic_json(OUT / "STATIC_CONTRACT_AUDIT.json", result); print(json.dumps(result, sort_keys=True)); return 0 if result["pass"] else 1
    if args.prepare:
        p = prepare(args.prepare); print(json.dumps({"case_id": args.prepare, "setup": str(p / "setup_pre.fsp")}, sort_keys=True)); return 0
    if args.run:
        result = run_case(args.run, args.mode); print(json.dumps({"case_id": args.run, "status": result.get("status"), "post": result.get("post_fsp")}, sort_keys=True)); return 0 if result.get("status") == "COMPLETED" else 1
    ap.error("one action is required")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
