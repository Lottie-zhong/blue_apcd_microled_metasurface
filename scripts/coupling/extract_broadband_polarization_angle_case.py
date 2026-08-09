from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
LUMAPI_ROOT = Path(r"N:\Program Files\ANSYS Inc\v251\Lumerical\api\python")
if str(LUMAPI_ROOT) not in sys.path:
    sys.path.insert(0, str(LUMAPI_ROOT))

from apcd_coupling.result_schema import validate_result

ORDER_TOLERANCE = 1e-6
CLOSURE_TOLERANCE = 0.02
GRID = [float(value) for value in range(445, 456)]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def arr(value: Any) -> np.ndarray:
    return np.asarray(value).reshape(-1)


def order_rows(fdtd: Any, monitor: str, index: int, total_power: float, direction: str, ux_in: float, wavelength_nm: float, period_x_nm: float, period_y_nm: float, reference_index: float) -> list[dict[str, Any]]:
    fraction = np.real(arr(fdtd.grating(monitor, index)))
    order_x = np.rint(np.real(arr(fdtd.gratingn(monitor, index)))).astype(int)
    order_y = np.rint(np.real(arr(fdtd.gratingm(monitor, index)))).astype(int)
    ux = np.real(arr(fdtd.gratingu1(monitor, index)))
    uy = np.real(arr(fdtd.gratingu2(monitor, index)))
    if order_x.size == 0:
        order_x = np.asarray([0], dtype=int)
    if order_y.size == 0:
        order_y = np.asarray([0], dtype=int)
    if ux.size != order_x.size or uy.size != order_y.size:
        raise RuntimeError(f"order-axis mismatch for {monitor}: n={order_x.size}, m={order_y.size}, ux={ux.size}, uy={uy.size}")
    if fraction.size != order_x.size * order_y.size:
        raise RuntimeError(f"grating fraction shape mismatch for {monitor}: fraction={fraction.shape}, n={order_x.size}, m={order_y.size}")
    fraction = fraction.reshape((order_x.size, order_y.size))
    rows: list[dict[str, Any]] = []
    for i, m_x in enumerate(order_x):
        analytic_u = float(ux_in + int(m_x) * wavelength_nm / period_x_nm)
        for j, m_y in enumerate(order_y):
            analytic_v = float(int(m_y) * wavelength_nm / period_y_nm)
            expected_native_u = analytic_u / reference_index
            expected_native_v = analytic_v / reference_index
            readback_native_u = float(ux[i])
            readback_native_v = float(uy[j])
            readback_u = float(readback_native_u * reference_index)
            readback_v = float(readback_native_v * reference_index)
            open_analytic = math.hypot(expected_native_u, expected_native_v) <= 1.0 + ORDER_TOLERANCE
            open_readback = math.hypot(readback_native_u, readback_native_v) <= 1.0 + ORDER_TOLERANCE
            rows.append({
                "m": int(m_x), "m_y": int(m_y), "u_in": float(ux_in),
                "u_out_analytic": analytic_u, "u_y_out_analytic": analytic_v,
                "u_out_lumerical": readback_u, "u_y_out_lumerical": readback_v,
                "u_out_lumerical_native_medium": readback_native_u,
                "u_y_out_lumerical_native_medium": readback_native_v,
                "reference_index_for_grating_readback": float(reference_index),
                "order_equation_residual": float(readback_native_u - expected_native_u),
                "order_y_equation_residual": float(readback_native_v - expected_native_v),
                "order_equation_pass": bool(abs(readback_native_u - expected_native_u) <= ORDER_TOLERANCE and abs(readback_native_v - expected_native_v) <= ORDER_TOLERANCE),
                "open_analytic": bool(open_analytic), "open_lumerical": bool(open_readback),
                "open_consistent": bool(open_analytic == open_readback),
                "physical_kx_out": float((2.0 * math.pi / (wavelength_nm * 1e-9)) * readback_u),
                "physical_kx_sign": "+x" if readback_u > 0 else "-x" if readback_u < 0 else "zero",
                "theta_air_out_deg": float(math.degrees(math.asin(max(-1.0, min(1.0, readback_u))))) if abs(readback_u) <= 1.0 + ORDER_TOLERANCE else None,
                "physical_propagation_direction": direction,
                "power_fraction_of_monitor_total": float(fraction[i, j]),
                "power_fraction_of_source": float(total_power * fraction[i, j]),
            })
    if not rows:
        raise RuntimeError(f"no diffraction rows returned by {monitor} at index {index}")
    return rows


def reflected_grating_reference_index(fdtd: Any, monitor: str, index: int, ux_in: float, wavelength_nm: float, period_x_nm: float) -> float:
    order_x = np.rint(np.real(arr(fdtd.gratingn(monitor, index)))).astype(int)
    order_y = np.rint(np.real(arr(fdtd.gratingm(monitor, index)))).astype(int)
    ux = np.real(arr(fdtd.gratingu1(monitor, index)))
    target = float(ux_in + wavelength_nm / period_x_nm)
    for i, m_x in enumerate(order_x):
        for j, m_y in enumerate(order_y):
            if int(m_x) == 1 and int(m_y) == 0 and abs(float(ux[i])) > 1e-12:
                value = target / float(ux[i])
                if value > 0 and math.isfinite(value):
                    return float(value)
    raise RuntimeError(f"cannot calibrate reflected grating reference index at wavelength {wavelength_nm}")


def state_row(setup: dict[str, Any], runtime: dict[str, Any], index: int, wavelength_nm: float, t_value: float, r_value: float, transmitted: list[dict[str, Any]], reflected: list[dict[str, Any]], reflection_reference_index: float) -> dict[str, Any]:
    state = setup["state"]
    ux_in = float(state["ux"])
    period_x_nm = float(setup["case"]["np_candidate"]["period_x_nm"])
    period_y_nm = float(setup["case"]["np_candidate"]["period_y_nm"])
    by_t = {row["m"]: row for row in transmitted if row["m_y"] == 0}
    by_r = {row["m"]: row for row in reflected if row["m_y"] == 0}
    for order in (1, 0, -1):
        if order not in by_t or order not in by_r:
            raise RuntimeError(f"required m={order}, m_y=0 order missing at {wavelength_nm} nm")
    plus, zero, minus = by_t[1], by_t[0], by_t[-1]
    denominator = plus["power_fraction_of_source"] + minus["power_fraction_of_source"]
    directionality = float(plus["power_fraction_of_source"] / denominator) if denominator else 0.0
    m0_readback_ux = float(zero["u_out_lumerical"])
    target_real_kx = 2.0 * math.pi / (wavelength_nm * 1e-9) * ux_in
    readback_real_kx = 2.0 * math.pi / (wavelength_nm * 1e-9) * m0_readback_ux
    source_kx = {
        "implementation": "BFAST transmitted m=0 air-side readback",
        "target_ux": ux_in,
        "target_real_kx": target_real_kx,
        "readback_m0_ux_air": m0_readback_ux,
        "readback_m0_real_kx": readback_real_kx,
        "ux_residual": m0_readback_ux - ux_in,
        "real_kx_residual": readback_real_kx - target_real_kx,
        "real_kx_tolerance": max(abs(target_real_kx), 1.0) * ORDER_TOLERANCE,
        "sign_pass": (ux_in == 0.0 and abs(m0_readback_ux) <= 1e-6) or (ux_in > 0.0 and m0_readback_ux > 0.0) or (ux_in < 0.0 and m0_readback_ux < 0.0),
        "pass": abs(m0_readback_ux - ux_in) <= ORDER_TOLERANCE and abs(readback_real_kx - target_real_kx) <= max(abs(target_real_kx), 1.0) * ORDER_TOLERANCE,
    }
    transmitted_sum = sum(row["power_fraction_of_source"] for row in transmitted)
    reflected_sum = sum(row["power_fraction_of_source"] for row in reflected)
    closure = float(1.0 - t_value - r_value)
    result = {
        "schema_version": "stage_a_polarization_angle_broadband_result_row_v1",
        "case_id": setup["case_id"], "broadband_state_id": setup["case_id"], "broadband_grid_nm": GRID, "spectrum_index": index - 1,
        "control_group": "POL_ANGLE_BROADBAND", "interface_id": "SUPPORT_NONE",
        "mdc_candidate_id": setup["case"]["mdc_candidate"]["candidate_id"], "mdc_geometry_hash": setup["case"]["mdc_geometry_hash"],
        "np_candidate_id": setup["case"]["np_candidate"]["candidate_id"], "np_geometry_hash": setup["case"]["np_geometry_hash"],
        "joint_stack_id": "APCD_MDC_NP_COUPLING_V1_STAGE_A_FROZEN_SPACER_445_455_POLARIZATION_ANGLE_BROADBAND",
        "joint_geometry_hash": setup["case"]["joint_geometry_hash"], "spacer_nm": float(setup["case"]["spacer_nm"]),
        "wavelength_nm": float(wavelength_nm), "polarization": setup["case"]["polarization"], "polarization_branch": state["polarization_branch"],
        "theta_air_in_deg": float(state["theta_air_in_deg"]), "ux_in": ux_in, "uy_in": float(state["uy"]), "kx_over_k0": ux_in,
        "real_kx_in": target_real_kx, "incident_state": {**state, "wavelength_nm": float(wavelength_nm), "real_kx": target_real_kx},
        "incident_state_hash": setup["incident_state_hash"], "no_polarization_averaging": True, "no_interpolation": True, "no_extrapolation": True,
        "R_total": float(r_value), "T_total": float(t_value), "eta_t_orders": transmitted, "eta_r_orders": reflected,
        "eta_plus1": float(plus["power_fraction_of_source"]), "eta_zero": float(zero["power_fraction_of_source"]), "eta_minus1": float(minus["power_fraction_of_source"]),
        "theta_out_plus1_deg": float(plus["theta_air_out_deg"]), "directionality": directionality,
        "power_closure": {"R_total_plus_T_total": float(r_value + t_value), "residual_1_minus_R_minus_T": closure, "estimated_native_material_absorption": closure, "formal_R_plus_T_tolerance": CLOSURE_TOLERANCE, "formal_R_plus_T_pass": abs(closure) <= CLOSURE_TOLERANCE, "absorption_accounted": 0.0 <= closure <= 1.0, "pass": 0.0 <= closure <= 1.0, "interpretation": "Native-M1 GaN loss is reported as residual; R+T is not forced to 1."},
        "order_closure": {"transmitted_order_sum": transmitted_sum, "reflected_order_sum": reflected_sum, "transmitted_residual": transmitted_sum - t_value, "reflected_residual": reflected_sum - r_value, "tolerance": 1e-8, "pass": abs(transmitted_sum - t_value) <= 1e-8 and abs(reflected_sum - r_value) <= 1e-8},
        "source_kx_contract": source_kx,
        "source_polarization_readback": {"branch": state["polarization_branch"], "polarization_angle_deg": float(setup["readback"]["source"]["polarization angle"]), "pass": abs(float(setup["readback"]["source"]["polarization angle"]) - (0.0 if state["polarization_branch"] == "P_XLIKE" else 90.0)) <= 1e-9},
        "order_equation_audit": {"formula": "u_out_m(lambda)=ux_in+m*lambda/Lambda_x", "period_x_nm": period_x_nm, "period_y_nm": period_y_nm, "all_rows_pass": all(row["order_equation_pass"] and row["open_consistent"] for row in transmitted + reflected), "m_plus_1_adds_positive_reciprocal_momentum": plus["u_out_analytic"] > ux_in and plus["m"] == 1, "m_plus_1_physical_kx_sign": plus["physical_kx_sign"]},
        "source_contract_id": setup["case"]["source_contract_id"], "material_contract_id": setup["case"]["material_contract_id"], "coordinate_contract_id": setup["case"]["coordinate_contract_id"], "mesh_contract_id": "RUN3A_NATIVE_M1_FDTD_SETTINGS_INHERITED_V1",
        "pre_fsp_path": setup["pre_fsp_path"], "pre_fsp_sha256": setup["pre_fsp_sha256"], "post_fsp_path": runtime["post_fsp_path"], "post_fsp_sha256": runtime["post_fsp_sha256"],
        "solver_entered": True, "solver_completed": True, "source_commits": setup["source_commits"], "coupling_commit": setup["coupling_commit"],
        "raw_monitor_extraction_reference": {"post_fsp_path": runtime["post_fsp_path"], "readonly_session": True, "run_called": False, "save_called": False, "api": ["getresult(T)", "grating", "gratingn", "gratingm", "gratingu1", "gratingu2"]},
        "provenance_hashes": {"joint_geometry_hash": setup["case"]["joint_geometry_hash"], "incident_state_hash": setup["incident_state_hash"], "physical_contract_hash": setup["physical_contract_hash"], "pre_fsp_sha256": setup["pre_fsp_sha256"], "post_fsp_sha256": runtime["post_fsp_sha256"]},
        "sign_audit": {"m_plus_1": int(plus["m"]), "m_plus_1_u_x": float(plus["u_out_lumerical"]), "m_plus_1_physical_kx_sign": plus["physical_kx_sign"], "contract": "m=+1 adds positive reciprocal-lattice momentum and is physical +x relative to incident", "pass": plus["m"] == 1 and plus["u_out_analytic"] > ux_in},
        "reflection_grating_reference_index": float(reflection_reference_index),
    }
    validate_result(result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    out = args.output_dir.resolve()
    setup = read(out / "setup_manifest.json")
    runtime = read(out / "runtime/attempt_001/run_state.json")
    if not runtime.get("solver_completed"):
        raise RuntimeError("solver_completed=false")
    post = Path(runtime["post_fsp_path"])
    if sha256(post) != runtime["post_fsp_sha256"]:
        raise RuntimeError("post-FSP hash mismatch before extraction")
    if setup["setup_gate"]["pass"] is not True:
        raise RuntimeError("setup gate is not PASS")
    import lumapi
    fdtd = lumapi.FDTD(str(post), hide=True)
    try:
        transmission = fdtd.getresult("transmission_monitor", "T")
        reflection = fdtd.getresult("reflection_monitor", "T")
        wavelengths = np.real(arr(transmission["lambda"]) * 1e9)
        t_values = np.real(arr(transmission["T"]))
        r_values = np.abs(np.real(arr(reflection["T"])))
        if wavelengths.size != 11 or not np.allclose(wavelengths, GRID, rtol=0.0, atol=1e-6):
            raise RuntimeError(f"unexpected exact wavelength grid: {wavelengths.tolist()}")
        rows = []
        all_orders = []
        for index, wavelength in enumerate(wavelengths, start=1):
            transmitted = order_rows(fdtd, "transmission_monitor", index, float(t_values[index - 1]), "+z", float(setup["state"]["ux"]), float(wavelength), float(setup["case"]["np_candidate"]["period_x_nm"]), float(setup["case"]["np_candidate"]["period_y_nm"]), 1.0)
            reflected_reference_index = reflected_grating_reference_index(fdtd, "reflection_monitor", index, float(setup["state"]["ux"]), float(wavelength), float(setup["case"]["np_candidate"]["period_x_nm"]))
            reflected = order_rows(fdtd, "reflection_monitor", index, float(r_values[index - 1]), "-z", float(setup["state"]["ux"]), float(wavelength), float(setup["case"]["np_candidate"]["period_x_nm"]), float(setup["case"]["np_candidate"]["period_y_nm"]), reflected_reference_index)
            rows.append(state_row(setup, runtime, index, float(wavelength), float(t_values[index - 1]), float(r_values[index - 1]), transmitted, reflected, reflected_reference_index))
            all_orders.append({"wavelength_nm": float(wavelength), "transmitted": transmitted, "reflected": reflected})
    finally:
        fdtd.close()
    source_kx_pass = all(row["source_kx_contract"]["pass"] for row in rows)
    if not source_kx_pass:
        raise RuntimeError("HARD_GATE_BROADBAND_FIXED_UX_IMPLEMENTATION_UNRESOLVED: transmitted m=0 air-side ux does not close")
    results_dir = out / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    for row in rows:
        validate_result(row)
    summary = {"case_id": setup["case_id"], "polarization_branch": setup["state"]["polarization_branch"], "theta_air_in_deg": setup["state"]["theta_air_in_deg"], "ux_in": setup["state"]["ux"], "wavelength_grid_nm": GRID, "rows": len(rows), "no_polarization_averaging": True, "source_kx_closure_all_pass": source_kx_pass, "order_equation_all_pass": all(row["order_equation_audit"]["all_rows_pass"] for row in rows), "power_closure_all_pass": all(row["power_closure"]["pass"] for row in rows), "order_closure_all_pass": all(row["order_closure"]["pass"] for row in rows), "mean_eta_plus1": float(np.mean([row["eta_plus1"] for row in rows])), "min_eta_plus1": float(np.min([row["eta_plus1"] for row in rows])), "max_eta_plus1": float(np.max([row["eta_plus1"] for row in rows])), "mean_directionality": float(np.mean([row["directionality"] for row in rows])), "min_directionality": float(np.min([row["directionality"] for row in rows])), "mean_R": float(np.mean([row["R_total"] for row in rows])), "mean_T": float(np.mean([row["T_total"] for row in rows])), "mean_residual": float(np.mean([row["power_closure"]["residual_1_minus_R_minus_T"] for row in rows]))}
    (results_dir / "result.json").write_text(json.dumps({"schema_version": "stage_a_polarization_angle_broadband_case_result_v1", "summary": summary, "rows": rows}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (results_dir / "order_spectra.json").write_text(json.dumps(all_orders, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with (results_dir / "spectrum_rows.csv").open("w", newline="", encoding="utf-8") as handle:
        fields = ["case_id", "polarization_branch", "theta_air_in_deg", "ux_in", "wavelength_nm", "R_total", "T_total", "residual_1_minus_R_minus_T", "eta_plus1", "eta_zero", "eta_minus1", "theta_out_plus1_deg", "directionality", "m0_readback_ux_air", "source_ux_residual", "source_kx_pass", "order_equation_pass", "power_closure_pass", "order_closure_pass"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({"case_id": row["case_id"], "polarization_branch": row["polarization_branch"], "theta_air_in_deg": row["theta_air_in_deg"], "ux_in": row["ux_in"], "wavelength_nm": row["wavelength_nm"], "R_total": row["R_total"], "T_total": row["T_total"], "residual_1_minus_R_minus_T": row["power_closure"]["residual_1_minus_R_minus_T"], "eta_plus1": row["eta_plus1"], "eta_zero": row["eta_zero"], "eta_minus1": row["eta_minus1"], "theta_out_plus1_deg": row["theta_out_plus1_deg"], "directionality": row["directionality"], "m0_readback_ux_air": row["source_kx_contract"]["readback_m0_ux_air"], "source_ux_residual": row["source_kx_contract"]["ux_residual"], "source_kx_pass": row["source_kx_contract"]["pass"], "order_equation_pass": row["order_equation_audit"]["all_rows_pass"], "power_closure_pass": row["power_closure"]["pass"], "order_closure_pass": row["order_closure"]["pass"]})
    manifest = {"schema_version": "stage_a_broadband_polarization_extraction_manifest_v1", "case_id": setup["case_id"], "post_fsp_path": str(post), "post_fsp_sha256": runtime["post_fsp_sha256"], "result_path": str(results_dir / "result.json"), "readonly_session": True, "run_called": False, "save_called": False, "exact_grid_pass": True, "row_count": len(rows), "source_kx_pass": source_kx_pass, "order_equation_pass": summary["order_equation_all_pass"], "power_closure_pass": summary["power_closure_all_pass"], "order_closure_pass": summary["order_closure_all_pass"]}
    (results_dir / "extraction_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
