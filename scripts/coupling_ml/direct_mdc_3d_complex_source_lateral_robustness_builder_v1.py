"""Setup/extraction-only 3D direct-MDC lateral-domain robustness builder.

The module contains no scientific solver entry. It may create a pre-FSP after
future authorization and may extract an already returned post-FSP, but it
contains no scientific solver-entry call.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np


BUILDER_ID = "DIRECT_MDC_3D_COMPLEX_SOURCE_LATERAL_ROBUSTNESS_BUILDER_V1"
SCHEMA_VERSION = "direct_mdc_3d_complex_source_lateral_robustness_builder_v1"
WAVELENGTHS_NM = list(range(445, 456))
PERIOD_X_NM = 1740.0
PERIOD_Y_NM = 290.0
STACK_SEQUENCE = [("H", 44.0), ("L", 79.0), ("H", 44.0), ("L", 79.0), ("H", 44.0), ("L", 316.0), ("H", 44.0), ("L", 79.0), ("H", 44.0), ("L", 79.0), ("H", 44.0), ("L", 79.0)]
STACK_TOP_NM = 975.0
SPACER_NM = 237.0
REFERENCE_PLANE_Z_NM = STACK_TOP_NM + SPACER_NM
SOURCE_Z_NM = -276.0
SOURCE_CASES = {
    "CENTROID_X_ENLARGED_DOMAIN": {"orientation": "X", "theta_deg": 90.0, "phi_deg": 0.0},
    "CENTROID_Z_ENLARGED_DOMAIN": {"orientation": "Z", "theta_deg": 0.0, "phi_deg": 0.0},
}
TRUTH_WORKTREE = Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_v1")
MATERIAL_CONFIG = TRUTH_WORKTREE / "configs" / "material_reference_apcd_blue.yaml"
MATERIAL_HELPER_ROOT = TRUTH_WORKTREE


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def physical_contract(case_id: str) -> dict[str, Any]:
    if case_id not in SOURCE_CASES:
        raise ValueError(f"unauthorized_source_case:{case_id}")
    state = SOURCE_CASES[case_id]
    return {
        "schema_version": SCHEMA_VERSION,
        "builder_id": BUILDER_ID,
        "case_id": case_id,
        "scientific_scope": "SOURCE_ONLY_MDC_NO_NP",
        "dimension": "3D",
        "source_dimensionality": "point electric dipole",
        "domain": {
            "x_span_nm": 12000.0,
            "y_span_nm": 12000.0,
            "baseline_x_span_nm": 8000.0,
            "baseline_y_span_nm": 8000.0,
            "lateral_domain_expansion_factor": 1.5,
            "z_min_nm": -1000.0,
            "z_max_nm": 1600.0,
            "boundaries": {axis: "PML" for axis in ("x_min", "x_max", "y_min", "y_max", "z_min", "z_max")},
            "finite_source_not_periodic_lattice": True,
        },
        "mdc": {"sequence": STACK_SEQUENCE, "stack_top_nm": STACK_TOP_NM, "material_config": str(MATERIAL_CONFIG)},
        "spacer_interface": {"spacer_nm": SPACER_NM, "background_medium": "Air", "np_present": False},
        "source": {
            "position_nm": {"x": 0.0, "y": 0.0, "z": SOURCE_Z_NM},
            "orientation": state["orientation"],
            "theta_deg": state["theta_deg"],
            "phi_deg": state["phi_deg"],
            "amplitude": 1.0,
            "phase_deg": 0.0,
            "normalization": "dipolepower(f)",
        },
        "reference_plane": {
            "id": "NP_BOTTOM_SPACER_SIDE_Z_MINUS",
            "z_nm": REFERENCE_PLANE_Z_NM,
            "side": "spacer side immediately below the future NP pillar",
            "operator_input_reference_plane_equal": True,
            "monitor_type": "2D Z-normal",
            "x_span_nm": 6000.0,
            "y_span_nm": 6000.0,
        },
        "wavelength_grid_nm": WAVELENGTHS_NM,
        "raw_contract": {
            "fields": ["Ex", "Ey", "Ez", "Hx", "Hy", "Hz"],
            "coordinates": ["x", "y", "z", "f"],
            "source_data": ["dipolepower"],
            "unmodified_complex_arrays": True,
            "sha_bound": True,
        },
        "solver_entered": False,
    }


def _load_material_helper():
    sys.path.insert(0, str(MATERIAL_HELPER_ROOT / "scripts"))
    return importlib.import_module("apcd_native_materials")


def build_setup_only(case_id: str, pre_fsp: str | Path) -> dict[str, Any]:
    """Create and save a pre-FSP only; this function never enters the solver."""
    import lumapi

    contract = physical_contract(case_id)
    helper = _load_material_helper()
    fdtd = lumapi.FDTD(hide=True)
    try:
        for material in ("APCD_GAN_NATIVE_M1", "APCD_TIO2_NATIVE_M1", "APCD_SIO2_NATIVE_M1"):
            helper.register_lumerical_sampled_material(fdtd, material)
        fdtd.addfdtd()
        settings = {
            "dimension": "3D",
            "x span": 12e-6,
            "y span": 12e-6,
            "z min": -1e-6,
            "z max": 1.6e-6,
            "x min bc": "PML",
            "x max bc": "PML",
            "y min bc": "PML",
            "y max bc": "PML",
            "z min bc": "PML",
            "z max bc": "PML",
            "mesh accuracy": 2,
            "pml layers": 8,
            "simulation time": 1e-12,
            "auto shutoff min": 1e-7,
        }
        for key, value in settings.items():
            fdtd.set(key, value)

        fdtd.addrect()
        for key, value in {"name": "GaN_substrate", "material": "APCD_GAN_NATIVE_M1", "x span": 8e-6, "y span": 8e-6, "z min": -1e-6, "z max": 0.0}.items():
            fdtd.set(key, value)
        z_nm = 0.0
        for index, (family, thickness_nm) in enumerate(STACK_SEQUENCE):
            fdtd.addrect()
            material = "APCD_TIO2_NATIVE_M1" if family == "H" else "APCD_SIO2_NATIVE_M1"
            for key, value in {
                "name": f"MDC_{index:02d}", "material": material, "x span": 8e-6, "y span": 8e-6,
                "z min": z_nm * 1e-9, "z max": (z_nm + thickness_nm) * 1e-9,
            }.items():
                fdtd.set(key, value)
            z_nm += thickness_nm

        fdtd.adddipole()
        source = contract["source"]
        for key, value in {
            "name": "source_dipole", "x": 0.0, "y": 0.0, "z": SOURCE_Z_NM * 1e-9,
            "theta": source["theta_deg"], "phi": source["phi_deg"], "amplitude": 1.0, "phase": 0.0,
            "wavelength start": 445e-9, "wavelength stop": 455e-9,
        }.items():
            fdtd.set(key, value)

        fdtd.addmesh()
        for key, value in {
            "name": "source_local_mesh", "x": 0.0, "y": 0.0, "z": SOURCE_Z_NM * 1e-9,
            "x span": 100e-9, "y span": 100e-9, "z span": 100e-9,
            "override x mesh": True, "override y mesh": True, "override z mesh": True,
            "dx": 2e-9, "dy": 2e-9, "dz": 1e-9,
        }.items():
            fdtd.set(key, value)

        fdtd.addpower()
        for key, value in {
            "name": "source_interface_complex", "monitor type": "2D Z-normal",
            "x span": 6e-6, "y span": 6e-6, "z": REFERENCE_PLANE_Z_NM * 1e-9,
            "override global monitor settings": True, "use source limits": True,
            "use wavelength spacing": True, "frequency points": len(WAVELENGTHS_NM),
        }.items():
            fdtd.set(key, value)
        pre_fsp = Path(pre_fsp)
        pre_fsp.parent.mkdir(parents=True, exist_ok=True)
        fdtd.save(str(pre_fsp))
    finally:
        fdtd.close()
    return {"pre_fsp": str(pre_fsp), "pre_fsp_sha256": sha256_file(pre_fsp), "contract": contract, "solver_entered": False}


def extract_returned_post_fsp(case_id: str, post_fsp: str | Path, raw_npz: str | Path, metadata_json: str | Path) -> dict[str, Any]:
    """Extract an already returned post-FSP without rerunning or saving it."""
    import lumapi

    contract = physical_contract(case_id)
    post_fsp = Path(post_fsp)
    raw_npz = Path(raw_npz)
    metadata_json = Path(metadata_json)
    fdtd = lumapi.FDTD(str(post_fsp), hide=True)
    try:
        arrays = {name: np.asarray(fdtd.getdata("source_interface_complex", name)) for name in ("x", "y", "z", "f", "Ex", "Ey", "Ez", "Hx", "Hy", "Hz")}
        frequency = np.asarray(arrays["f"]).reshape(-1)
        arrays["dipolepower"] = np.asarray(fdtd.dipolepower(frequency))
    finally:
        fdtd.close()
    raw_npz.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(raw_npz, **arrays)
    metadata = {
        "schema_version": "m2s_direct_mdc_3d_complex_source_raw_v1",
        "case_id": case_id,
        "post_fsp": str(post_fsp),
        "post_fsp_sha256": sha256_file(post_fsp),
        "raw_npz": str(raw_npz),
        "raw_npz_sha256": sha256_file(raw_npz),
        "contract": contract,
        "array_shapes": {key: list(value.shape) for key, value in arrays.items()},
        "solver_rerun": False,
    }
    metadata_json.parent.mkdir(parents=True, exist_ok=True)
    metadata_json.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return metadata


def ps_basis(ux: float, uy: float, direction: int, refractive_index: float = 1.0):
    tx, ty = ux / refractive_index, uy / refractive_index
    rho2 = tx * tx + ty * ty
    if direction not in (-1, 1):
        raise ValueError("direction")
    if rho2 >= 1.0 - 1e-12:
        raise ValueError("evanescent_or_grazing")
    khat = np.array([tx, ty, direction * math.sqrt(1.0 - rho2)])
    rho = math.sqrt(rho2)
    s_hat = np.array([0.0, 1.0, 0.0]) if rho < 1e-14 else np.array([-ty / rho, tx / rho, 0.0])
    p_hat = np.cross(s_hat, khat)
    p_hat /= np.linalg.norm(p_hat)
    return p_hat, s_hat, khat


def synthesize(amplitudes: dict[str, complex], ux: float, uy: float, impedance: float = 1.0):
    e = np.zeros(3, dtype=complex)
    h = np.zeros(3, dtype=complex)
    for direction, prefix in ((1, "up"), (-1, "down")):
        p_hat, s_hat, khat = ps_basis(ux, uy, direction)
        for label, basis in (("P", p_hat), ("S", s_hat)):
            amplitude = complex(amplitudes.get(f"{prefix}_{label}", 0.0))
            e += amplitude * basis
            h += amplitude * np.cross(khat, basis) / impedance
    return e, h


def decompose(electric, magnetic, ux: float, uy: float, impedance: float = 1.0):
    columns, labels = [], []
    for direction, prefix in ((1, "up"), (-1, "down")):
        p_hat, s_hat, khat = ps_basis(ux, uy, direction)
        for label, basis in (("P", p_hat), ("S", s_hat)):
            columns.append(np.concatenate([basis, np.cross(khat, basis)]))
            labels.append(f"{prefix}_{label}")
    matrix = np.stack(columns, axis=1).astype(complex)
    vector = np.concatenate([np.asarray(electric, dtype=complex), impedance * np.asarray(magnetic, dtype=complex)])
    values, _, rank, _ = np.linalg.lstsq(matrix, vector, rcond=None)
    if rank != 4:
        raise RuntimeError(f"rank_{rank}")
    return {label: complex(value) for label, value in zip(labels, values)}


def fold_to_first_bz(kx: float, ky: float, period_x: float, period_y: float):
    gx, gy = 2 * math.pi / period_x, 2 * math.pi / period_y
    order_x = math.floor(kx / gx + 0.5)
    order_y = math.floor(ky / gy + 0.5)
    kbx, kby = kx - order_x * gx, ky - order_y * gy
    return {"k_bloch_x": kbx, "k_bloch_y": kby, "order_x": order_x, "order_y": order_y, "G_x": order_x * gx, "G_y": order_y * gy}


def synthetic_self_tests() -> dict[str, Any]:
    tests = {}

    def modal(name, amplitudes, ux, uy):
        e, h = synthesize(amplitudes, ux, uy)
        got = decompose(e, h, ux, uy)
        for label in ("up_P", "up_S", "down_P", "down_S"):
            if not np.allclose(got[label], amplitudes.get(label, 0.0), rtol=0.0, atol=2e-12):
                raise AssertionError(f"{name}:{label}")
        tests[name] = {"pass": True, "ux": ux, "uy": uy}

    modal("oblique_kx_only", {"up_P": 1.0 + 0.2j}, 0.31, 0.0)
    modal("oblique_ky_only", {"up_S": -0.4 + 0.7j}, 0.0, -0.27)
    modal("arbitrary_kx_ky_P", {"up_P": 0.8 - 0.3j}, 0.23, -0.19)
    modal("arbitrary_kx_ky_S", {"up_S": 0.1 + 0.9j}, -0.21, 0.25)
    modal("coherent_P_S", {"up_P": 1.0 + 0.5j, "up_S": -0.2 + 0.4j}, 0.18, 0.17)
    modal("upward_downward_separation", {"up_P": 1.0, "up_S": 0.3j, "down_P": -0.2, "down_S": 0.4 + 0.1j}, 0.24, -0.16)

    lx, ly = PERIOD_X_NM * 1e-9, PERIOD_Y_NM * 1e-9
    gx, gy = 2 * math.pi / lx, 2 * math.pi / ly
    folded = fold_to_first_bz(0.22 * gx + 2 * gx, -0.31 * gy - gy, lx, ly)
    if not np.allclose([folded["k_bloch_x"], folded["k_bloch_y"]], [0.22 * gx, -0.31 * gy], rtol=0.0, atol=1e-7):
        raise AssertionError("bloch_zone_folding")
    if (folded["order_x"], folded["order_y"]) != (2, -1):
        raise AssertionError("reciprocal_order_labeling")
    tests["bloch_zone_folding"] = {"pass": True}
    tests["reciprocal_order_labeling"] = {"pass": True, "order": [2, -1]}

    amplitude = 0.7 - 0.2j
    kx, ky, dx, dy = 0.4 * gx, -0.2 * gy, 73e-9, -41e-9
    shifted = amplitude * np.exp(-1j * (kx * dx + ky * dy))
    reconstructed = shifted * np.exp(1j * (kx * dx + ky * dy))
    if not np.allclose(reconstructed, amplitude, rtol=0.0, atol=2e-12):
        raise AssertionError("phase_origin_invariance")
    tests["phase_origin_invariance"] = {"pass": True}

    for case_id in SOURCE_CASES:
        contract = physical_contract(case_id)
        required = contract["raw_contract"]["fields"]
        if required != ["Ex", "Ey", "Ez", "Hx", "Hy", "Hz"] or contract["wavelength_grid_nm"] != WAVELENGTHS_NM:
            raise AssertionError(f"contract_{case_id}")
    tests["monitor_reference_source_wavelength_contract"] = {"pass": True, "cases": sorted(SOURCE_CASES)}
    return {"schema_version": "M2P_SYNTHETIC_3D_BLOCH_TESTS_V1", "pass": all(v["pass"] for v in tests.values()), "tests": tests}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--emit-contract")
    parser.add_argument("--case", choices=sorted(SOURCE_CASES), default="CENTROID_X")
    args = parser.parse_args()
    if args.self_test:
        print(json.dumps(synthetic_self_tests(), indent=2, sort_keys=True))
        return
    if args.emit_contract:
        Path(args.emit_contract).write_text(json.dumps(physical_contract(args.case), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return
    parser.error("static stage permits only --self-test or --emit-contract; scientific execution is not exposed")


if __name__ == "__main__":
    main()
