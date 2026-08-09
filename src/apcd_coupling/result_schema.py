from __future__ import annotations

import math
from typing import Any

REQUIRED_RESULT_FIELDS = {
    "case_id", "control_group", "interface_id", "mdc_candidate_id", "mdc_geometry_hash", "np_candidate_id", "np_geometry_hash", "joint_stack_id", "joint_geometry_hash", "spacer_nm", "wavelength_nm", "polarization", "kx_over_k0", "R_total", "T_total", "eta_t_orders", "eta_r_orders", "eta_plus1", "eta_zero", "eta_minus1", "theta_out_plus1_deg", "directionality", "power_closure", "order_closure", "source_contract_id", "material_contract_id", "coordinate_contract_id", "mesh_contract_id", "pre_fsp_path", "pre_fsp_sha256", "post_fsp_path", "post_fsp_sha256", "solver_entered", "solver_completed", "source_commits", "coupling_commit",
}

POLARIZATION_RESULT_FIELDS = {
    "polarization_branch", "theta_air_in_deg", "ux_in", "uy_in", "real_kx_in", "incident_state", "incident_state_hash", "source_kx_contract", "source_polarization_readback", "order_equation_audit", "provenance_hashes", "sign_audit",
}

BROADBAND_RESULT_FIELDS = {
    "broadband_grid_nm", "spectrum_index", "broadband_state_id", "no_interpolation", "no_extrapolation",
}


def _finite(result: dict[str, Any], keys: tuple[str, ...]) -> None:
    for key in keys:
        value = float(result[key])
        if not math.isfinite(value):
            raise ValueError(f"result field {key} is not finite")


def validate_result(result: dict[str, Any]) -> dict[str, Any]:
    missing = sorted(REQUIRED_RESULT_FIELDS - set(result))
    if missing:
        raise ValueError(f"result schema missing fields: {missing}")
    _finite(result, ("R_total", "T_total"))
    if result.get("control_group") in {"POL_ANGLE_MATRIX", "POL_ANGLE_BROADBAND"}:
        missing = sorted(POLARIZATION_RESULT_FIELDS - set(result))
        if missing:
            raise ValueError(f"polarization-angle result schema missing fields: {missing}")
        if result.get("control_group") == "POL_ANGLE_BROADBAND":
            missing = sorted(BROADBAND_RESULT_FIELDS - set(result))
            if missing:
                raise ValueError(f"broadband polarization result schema missing fields: {missing}")
            expected_grid = [float(value) for value in range(445, 456)]
            if [float(value) for value in result["broadband_grid_nm"]] != expected_grid:
                raise ValueError("broadband result must declare exact 445-455 nm grid")
            if not any(abs(float(result["wavelength_nm"]) - value) <= 1e-6 for value in expected_grid):
                raise ValueError("broadband wavelength is outside exact grid")
            if result["no_interpolation"] is not True or result["no_extrapolation"] is not True:
                raise ValueError("broadband result cannot use interpolation or extrapolation")
        elif float(result["wavelength_nm"]) != 450.0:
            raise ValueError("polarization-angle matrix is exact 450 nm only")
        if result["polarization_branch"] not in {"P_XLIKE", "S_YLIKE"}:
            raise ValueError("invalid incident polarization branch")
        if result["polarization"] != ("x" if result["polarization_branch"] == "P_XLIKE" else "y"):
            raise ValueError("polarization and incident branch disagree")
        _finite(result, ("theta_air_in_deg", "ux_in", "uy_in", "real_kx_in", "eta_plus1", "eta_zero", "eta_minus1", "theta_out_plus1_deg", "directionality"))
        if abs(float(result["uy_in"])) > 1e-12:
            raise ValueError("ky/k0 must be zero")
        k0 = 2.0 * math.pi / (float(result["wavelength_nm"]) * 1e-9)
        if abs(float(result["real_kx_in"]) - k0 * float(result["ux_in"])) > max(abs(float(result["real_kx_in"])), 1.0) * 1e-9:
            raise ValueError("real_kx_in does not match k0*ux_in")
        if result["source_kx_contract"].get("pass") is not True:
            raise ValueError("source-kx closure failed")
        if result["source_polarization_readback"].get("pass") is not True:
            raise ValueError("source polarization readback failed")
        if result["order_equation_audit"].get("all_rows_pass") is not True:
            raise ValueError("oblique diffraction order equation audit failed")
        if result["sign_audit"].get("pass") is not True:
            raise ValueError("m=+1 sign audit failed")
        if result.get("no_polarization_averaging") is not True:
            raise ValueError("polarization-angle result must declare no polarization averaging")
        if result["solver_entered"] is not True or result["solver_completed"] is not True:
            raise ValueError("completed result must record solver_entered and solver_completed")
        if not isinstance(result["eta_t_orders"], list) or not isinstance(result["eta_r_orders"], list):
            raise ValueError("order results must be lists")
        return result
    if result["polarization"] != "x" or float(result["kx_over_k0"]) != 0.0:
        raise ValueError("result is outside the authorized Stage-A scope")
    if result.get("eta_plus1") is not None:
        _finite(result, ("eta_plus1", "eta_zero", "eta_minus1", "theta_out_plus1_deg", "directionality"))
    elif not isinstance(result.get("not_applicable"), dict):
        raise ValueError("B0/B1 require explicit NOT_APPLICABLE reasons")
    if result["solver_entered"] is not True or result["solver_completed"] is not True:
        raise ValueError("completed result must record solver_entered and solver_completed")
    if not isinstance(result["eta_t_orders"], list) or not isinstance(result["eta_r_orders"], list):
        raise ValueError("order results must be lists")
    return result
