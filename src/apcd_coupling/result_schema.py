from __future__ import annotations

import math
from typing import Any

REQUIRED_RESULT_FIELDS = {
    "case_id", "control_group", "interface_id", "mdc_candidate_id", "mdc_geometry_hash", "np_candidate_id", "np_geometry_hash", "joint_stack_id", "joint_geometry_hash", "spacer_nm", "wavelength_nm", "polarization", "kx_over_k0", "R_total", "T_total", "eta_t_orders", "eta_r_orders", "eta_plus1", "eta_zero", "eta_minus1", "theta_out_plus1_deg", "directionality", "power_closure", "order_closure", "source_contract_id", "material_contract_id", "coordinate_contract_id", "mesh_contract_id", "pre_fsp_path", "pre_fsp_sha256", "post_fsp_path", "post_fsp_sha256", "solver_entered", "solver_completed", "source_commits", "coupling_commit",
}

def validate_result(result: dict[str, Any]) -> dict[str, Any]:
    missing = sorted(REQUIRED_RESULT_FIELDS - set(result))
    if missing:
        raise ValueError(f"result schema missing fields: {missing}")
    for key in ("R_total", "T_total"):
        value = float(result[key])
        if not math.isfinite(value):
            raise ValueError(f"result field {key} is not finite")
    if result.get("eta_plus1") is not None:
        for key in ("eta_plus1", "eta_zero", "eta_minus1", "theta_out_plus1_deg", "directionality"):
            value = float(result[key])
            if not math.isfinite(value):
                raise ValueError(f"result field {key} is not finite")
    else:
        if not isinstance(result.get("not_applicable"), dict):
            raise ValueError("B0/B1 require explicit NOT_APPLICABLE reasons")
    if result["polarization"] != "x" or float(result["kx_over_k0"]) != 0.0:
        raise ValueError("result is outside the authorized Stage-A scope")
    if result["solver_entered"] is not True or result["solver_completed"] is not True:
        raise ValueError("completed result must record solver_entered and solver_completed")
    if not isinstance(result["eta_t_orders"], list) or not isinstance(result["eta_r_orders"], list):
        raise ValueError("order results must be lists")
    return result
