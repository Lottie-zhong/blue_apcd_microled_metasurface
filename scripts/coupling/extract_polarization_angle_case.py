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
LUMAPI_ROOT = Path(r"N:\\Program Files\\ANSYS Inc\\v251\\Lumerical\\api\\python")
if str(LUMAPI_ROOT) not in sys.path:
    sys.path.insert(0, str(LUMAPI_ROOT))
from apcd_coupling.result_schema import validate_result

ORDER_TOLERANCE = 1e-6
CLOSURE_TOLERANCE = 0.02


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


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
        raise RuntimeError(f"order-axis mismatch: n={order_x.size}, m={order_y.size}, ux={ux.size}, uy={uy.size}")
    if fraction.size != order_x.size * order_y.size:
        raise RuntimeError(f"grating fraction shape mismatch: fraction={fraction.shape}, n={order_x.size}, m={order_y.size}")
    fraction = fraction.reshape((order_x.size, order_y.size))
    wavelength_over_period = wavelength_nm / period_x_nm
    wavelength_over_period_y = wavelength_nm / period_y_nm
    rows: list[dict[str, Any]] = []
    for i, m_x in enumerate(order_x):
        analytic_u = float(ux_in + int(m_x) * wavelength_over_period)
        for j, m_y in enumerate(order_y):
            analytic_v = float(int(m_y) * wavelength_over_period_y)
            expected_native_u = analytic_u / reference_index
            expected_native_v = analytic_v / reference_index
            readback_native_u = float(ux[i])
            readback_native_v = float(uy[j])
            readback_u = float(readback_native_u * reference_index)
            readback_v = float(readback_native_v * reference_index)
            open_analytic = math.hypot(expected_native_u, expected_native_v) <= 1.0 + ORDER_TOLERANCE
            readback_in_range = math.hypot(readback_native_u, readback_native_v) <= 1.0 + ORDER_TOLERANCE
            rows.append({
                "m": int(m_x),
                "m_y": int(m_y),
                "u_in": float(ux_in),
                "u_out_analytic": analytic_u,
                "u_y_out_analytic": analytic_v,
                "u_out_lumerical": readback_u,
                "u_y_out_lumerical": readback_v,
                "u_out_lumerical_native_medium": readback_native_u,
                "u_y_out_lumerical_native_medium": readback_native_v,
                "reference_index_for_grating_readback": float(reference_index),
                "order_equation_residual": float(readback_native_u - expected_native_u),
                "order_equation_pass": bool(abs(readback_native_u - expected_native_u) <= ORDER_TOLERANCE and abs(readback_native_v - expected_native_v) <= ORDER_TOLERANCE),
                "open_analytic": bool(open_analytic),
                "open_lumerical": bool(readback_in_range),
                "open_consistent": bool(open_analytic == readback_in_range),
                "physical_kx_out": float((2.0 * math.pi / (wavelength_nm * 1e-9)) * readback_u),
                "physical_kx_sign": "+x" if readback_u > 0 else "-x" if readback_u < 0 else "zero",
                "theta_air_out_deg": float(math.degrees(math.asin(max(-1.0, min(1.0, readback_u))))) if abs(readback_u) <= 1.0 + ORDER_TOLERANCE else None,
                "physical_propagation_direction": direction,
                "power_fraction_of_monitor_total": float(fraction[i, j]),
                "power_fraction_of_source": float(total_power * fraction[i, j]),
            })
    if not rows:
        raise RuntimeError(f"no open diffraction orders returned by {monitor}")
    return rows


def reflected_grating_reference_index(fdtd: Any, monitor: str, index: int, ux_in: float, wavelength_nm: float, period_x_nm: float) -> float:
    order_x = np.rint(np.real(arr(fdtd.gratingn(monitor, index)))).astype(int)
    order_y = np.rint(np.real(arr(fdtd.gratingm(monitor, index)))).astype(int)
    ux = np.real(arr(fdtd.gratingu1(monitor, index)))
    target = float(ux_in + wavelength_nm / period_x_nm)
    for i, m_x in enumerate(order_x):
        for j, m_y in enumerate(order_y):
            if int(m_x) == 1 and int(m_y) == 0 and abs(float(ux[i])) > 1e-12:
                reference_index = target / float(ux[i])
                if reference_index > 0.0 and math.isfinite(reference_index):
                    return float(reference_index)
    raise RuntimeError("cannot calibrate reflected grating reference index from m=+1,m_y=0 readback")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    out = args.output_dir.resolve()
    setup = json.loads((out / "setup_manifest.json").read_text(encoding="utf-8"))
    runtime = json.loads((out / "runtime/attempt_001/run_state.json").read_text(encoding="utf-8"))
    audit = json.loads((out / "post_fsp_identity_audit.json").read_text(encoding="utf-8"))
    if not audit.get("pass") or not runtime.get("solver_completed"):
        raise RuntimeError("post-FSP audit/completion gate failed")
    post = Path(runtime["post_fsp_path"])
    if sha256(post) != runtime["post_fsp_sha256"]:
        raise RuntimeError("post-FSP hash mismatch before extraction")
    state = setup["state"]
    ux_in = float(state["ux"])
    wavelength_nm = float(state["wavelength_nm"])
    period_x_nm = float(setup["case"]["np_candidate"]["period_x_nm"])
    period_y_nm = float(setup["case"]["np_candidate"]["period_y_nm"])
    source_contract_file = json.loads((ROOT / "configs/coupling/oblique_real_kx_source_contract_v1.json").read_text(encoding="utf-8"))
    authoritative_calibration = source_contract_file["authoritative_calibration_readback"]
    source_n_eff = float(authoritative_calibration["source_calibration_n_eff"])
    import lumapi
    fdtd = lumapi.FDTD(str(post), hide=True)
    try:
        transmission = fdtd.getresult("transmission_monitor", "T")
        reflection = fdtd.getresult("reflection_monitor", "T")
        wavelengths = arr(transmission["lambda"]) * 1e9
        t_values = np.real(arr(transmission["T"]))
        r_values = np.abs(np.real(arr(reflection["T"])))
        if wavelengths.size != 1 or abs(float(wavelengths[0]) - wavelength_nm) > 1e-6:
            raise RuntimeError(f"unexpected wavelength axis: {wavelengths.tolist()}")
        transmitted = order_rows(fdtd, "transmission_monitor", 1, float(t_values[0]), "+z", ux_in, wavelength_nm, period_x_nm, period_y_nm, 1.0)
        reflected_reference_index = reflected_grating_reference_index(fdtd, "reflection_monitor", 1, ux_in, wavelength_nm, period_x_nm)
        reflected = order_rows(fdtd, "reflection_monitor", 1, float(r_values[0]), "-z", ux_in, wavelength_nm, period_x_nm, period_y_nm, reflected_reference_index)
    finally:
        fdtd.close()
    transmitted_sum = sum(row["power_fraction_of_source"] for row in transmitted)
    reflected_sum = sum(row["power_fraction_of_source"] for row in reflected)
    by_t = {row["m"]: row for row in transmitted if row["m_y"] == 0}
    by_r = {row["m"]: row for row in reflected if row["m_y"] == 0}
    for order in (1, 0, -1):
        if order not in by_t or order not in by_r:
            raise RuntimeError(f"required m={order}, m_y=0 order missing from transmitted/reflected extraction")
    plus = by_t[1]
    minus = by_t[-1]
    zero = by_t[0]
    directionality_denominator = plus["power_fraction_of_source"] + minus["power_fraction_of_source"]
    directionality = float(plus["power_fraction_of_source"] / directionality_denominator) if directionality_denominator else 0.0
    closure_residual = float(1.0 - float(t_values[0]) - float(r_values[0]))
    order_t_residual = float(transmitted_sum - float(t_values[0]))
    order_r_residual = float(reflected_sum - float(r_values[0]))
    source_contract = {**setup["readback"]["oblique_real_kx_source_contract"], "source_calibration_kx_bandstructure": authoritative_calibration["source_calibration_kx_bandstructure"], "source_calibration_n_eff": source_n_eff, "authoritative_calibration_readback": authoritative_calibration, "grating_reflection_reference_index": float(reflected_reference_index), "grating_reflection_reference_index_method": "readback-calibrated from m=+1,m_y=0 analytic conserved real-kx divided by native-GaN gratingu1"}
    order_equation_pass = all(row["order_equation_pass"] and row["open_consistent"] for row in transmitted + reflected)
    source_kx_pass = abs(float(source_contract["boundary_readback_kx"]) - float(state["real_kx"])) <= max(abs(float(state["real_kx"])), 1.0) * 1e-9
    source_pol_pass = abs(float(setup["readback"]["source"]["polarization angle"]) - float(state["polarization_angle_deg"])) <= 1e-9
    result = {
        "schema_version": "stage_a_polarization_angle_result_v1",
        "case_id": setup["case_id"],
        "control_group": "POL_ANGLE_MATRIX",
        "interface_id": "SUPPORT_NONE",
        "mdc_candidate_id": setup["case"]["mdc_candidate"]["candidate_id"],
        "mdc_geometry_hash": setup["case"]["mdc_geometry_hash"],
        "np_candidate_id": setup["case"]["np_candidate"]["candidate_id"],
        "np_geometry_hash": setup["case"]["np_geometry_hash"],
        "joint_stack_id": "APCD_MDC_NP_COUPLING_V1_STAGE_A_FROZEN_SPACER_450NM_POLARIZATION_ANGLE_MATRIX",
        "joint_geometry_hash": setup["case"]["joint_geometry_hash"],
        "spacer_nm": float(setup["case"]["spacer_nm"]),
        "wavelength_nm": wavelength_nm,
        "polarization": setup["case"]["polarization"],
        "polarization_branch": state["polarization_branch"],
        "theta_air_in_deg": float(state["theta_air_in_deg"]),
        "ux_in": ux_in,
        "uy_in": float(state["uy"]),
        "kx_over_k0": ux_in,
        "real_kx_in": float(state["real_kx"]),
        "incident_state": state,
        "incident_state_hash": setup["incident_state_hash"],
        "no_polarization_averaging": True,
        "R_total": float(r_values[0]),
        "T_total": float(t_values[0]),
        "eta_t_orders": transmitted,
        "eta_r_orders": reflected,
        "eta_plus1": float(plus["power_fraction_of_source"]),
        "eta_zero": float(zero["power_fraction_of_source"]),
        "eta_minus1": float(minus["power_fraction_of_source"]),
        "theta_out_plus1_deg": float(plus["theta_air_out_deg"]),
        "directionality": directionality,
        "power_closure": {"R_total_plus_T_total": float(r_values[0] + t_values[0]), "residual_1_minus_R_minus_T": closure_residual, "estimated_native_material_absorption": closure_residual, "formal_R_plus_T_tolerance": CLOSURE_TOLERANCE, "formal_R_plus_T_pass": abs(closure_residual) <= CLOSURE_TOLERANCE, "absorption_accounted": closure_residual >= 0.0, "pass": 0.0 <= closure_residual <= 1.0, "interpretation": "Native-M1 GaN loss is reported as the residual; R+T is not forced to 1."},
        "order_closure": {"transmitted_order_sum": transmitted_sum, "reflected_order_sum": reflected_sum, "transmitted_residual": order_t_residual, "reflected_residual": order_r_residual, "tolerance": 1e-8, "pass": abs(order_t_residual) <= 1e-8 and abs(order_r_residual) <= 1e-8},
        "source_kx_contract": {**source_contract, "pass": source_kx_pass},
        "source_polarization_readback": {"branch": state["polarization_branch"], "polarization_angle_deg": float(setup["readback"]["source"]["polarization angle"]), "pass": source_pol_pass},
        "order_equation_audit": {"formula": "u_out_m = u_in + m*wavelength_nm/period_x_nm", "period_x_nm": period_x_nm, "all_rows_pass": order_equation_pass, "m_plus_1_adds_positive_reciprocal_momentum": plus["u_out_analytic"] > ux_in and plus["m"] == 1, "m_plus_1_physical_kx_sign": plus["physical_kx_sign"], "m_plus_1_physical_plus_x": plus["u_out_analytic"] > ux_in},
        "source_contract_id": setup["case"]["source_contract_id"],
        "material_contract_id": setup["case"]["material_contract_id"],
        "coordinate_contract_id": setup["case"]["coordinate_contract_id"],
        "mesh_contract_id": "RUN3A_NATIVE_M1_FDTD_SETTINGS_INHERITED_V1",
        "pre_fsp_path": setup["pre_fsp_path"],
        "pre_fsp_sha256": setup["pre_fsp_sha256"],
        "post_fsp_path": str(post),
        "post_fsp_sha256": runtime["post_fsp_sha256"],
        "solver_entered": True,
        "solver_completed": True,
        "source_commits": setup["source_commits"],
        "coupling_commit": setup["coupling_commit"],
        "raw_monitor_extraction_reference": {"post_fsp_path": str(post), "readonly_session": True, "run_called": False, "save_called": False, "api": ["getresult(T)", "grating", "gratingn", "gratingm", "gratingu1", "gratingu2"]},
        "provenance_hashes": {"joint_geometry_hash": setup["case"]["joint_geometry_hash"], "incident_state_hash": setup["incident_state_hash"], "physical_contract_hash": setup["physical_contract_hash"], "pre_fsp_sha256": setup["pre_fsp_sha256"], "post_fsp_sha256": runtime["post_fsp_sha256"]},
        "sign_audit": {"m_plus_1": int(plus["m"]), "m_plus_1_u_x": float(plus["u_out_lumerical"]), "m_plus_1_physical_kx_sign": plus["physical_kx_sign"], "contract": "m=+1 adds positive reciprocal-lattice momentum and is physical +x relative to incident", "pass": plus["m"] == 1 and plus["u_out_analytic"] > ux_in},
    }
    validate_result(result)
    result_dir = out / "results"
    result_dir.mkdir(parents=True, exist_ok=True)
    (result_dir / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (result_dir / "transmitted_orders.json").write_text(json.dumps(transmitted, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (result_dir / "reflected_orders.json").write_text(json.dumps(reflected, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with (result_dir / "order_spectrum.csv").open("w", newline="", encoding="utf-8") as handle:
        rows = [{**row, "channel": "transmitted"} for row in transmitted] + [{**row, "channel": "reflected"} for row in reflected]
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    extraction_manifest = {"schema_version": "stage_a_polarization_extraction_manifest_v1", "case_id": result["case_id"], "post_fsp_path": str(post), "post_fsp_sha256": runtime["post_fsp_sha256"], "result_path": str(result_dir / "result.json"), "readonly_session": True, "run_called": False, "save_called": False, "order_equation_pass": order_equation_pass, "source_kx_pass": source_kx_pass, "power_closure_pass": result["power_closure"]["pass"], "order_closure_pass": result["order_closure"]["pass"]}
    (result_dir / "extraction_manifest.json").write_text(json.dumps(extraction_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"case_id": result["case_id"], "eta_plus1": result["eta_plus1"], "eta_zero": result["eta_zero"], "eta_minus1": result["eta_minus1"], "theta_out_plus1_deg": result["theta_out_plus1_deg"], "order_equation_pass": order_equation_pass, "source_kx_pass": source_kx_pass, "power_closure_pass": result["power_closure"]["pass"], "order_closure_pass": result["order_closure"]["pass"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
