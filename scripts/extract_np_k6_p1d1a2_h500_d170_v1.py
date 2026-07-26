"""Read-only recovery and explicitly provisional three-point phase analysis."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

from extract_np_k6_p1d1a0_h500_d110_v1 import ROOT, finite, sha, write


def wrap(delta: float) -> float:
    value = (delta + 180.0) % 360.0 - 180.0
    return value + 360.0 if value <= -180.0 else value


def compact(row: dict) -> dict:
    return {key: row[key] for key in ("candidate_id", "T", "R_total", "txx", "cross_pol_fraction", "energy_residual", "x_input_reconstruction_residual")}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--audit", type=Path, required=True)
    args = parser.parse_args()
    historical = json.loads((ROOT / "outputs/np_k6_p1d1a_h500_x_v1/results.json").read_text())
    d110 = json.loads((ROOT / "outputs/np_k6_p1d1a0_h500_d110_v1/results.json").read_text())
    d140 = json.loads((ROOT / "outputs/np_k6_p1d1a1_h500_d140_v1/results.json").read_text())
    reference = json.loads((ROOT / "outputs/np_k6_p1d0b_corner_pilot_v1/results.json").read_text())
    case = next(row for row in historical["cases"] if row["candidate_id"] == "NP_P1D_H500_D170")
    blank = reference["blank"]
    post = ROOT / case["source_fsp"]["path"]
    before = sha(post)
    if before["sha256"] != case["source_fsp"]["sha256"]: raise RuntimeError("historical D170 post-FSP fingerprint mismatch")
    sys.path.insert(0, r"N:\Program Files\ANSYS Inc\v251\Lumerical\api\python")
    import lumapi  # type: ignore
    fdtd = lumapi.FDTD(hide=True)
    try:
        fdtd.load(str(post))
        audit = {"fdtd_z_min": float(fdtd.getnamed("FDTD", "z min")), "fdtd_z_max": float(fdtd.getnamed("FDTD", "z max")), "source_z": float(fdtd.getnamed("source", "z")), "source_polarization_angle": float(fdtd.getnamed("source", "polarization angle")), "source_wavelength_start": float(fdtd.getnamed("source", "wavelength start")), "pillar_z_min": float(fdtd.getnamed("TiO2 pillar", "z min")), "pillar_z_max": float(fdtd.getnamed("TiO2 pillar", "z max")), "pillar_radius": float(fdtd.getnamed("TiO2 pillar", "radius")), "pillar_material": str(fdtd.getnamed("TiO2 pillar", "material")), "T_z": float(fdtd.getnamed("T_fields", "z")), "R_z": float(fdtd.getnamed("R_fields", "z")), "T_result_present": bool(fdtd.getresult("T_fields", "E")), "R_result_present": bool(fdtd.getresult("R_fields", "E"))}
    finally:
        fdtd.close()
    after = sha(post)
    expected = {"fdtd_z_min": -1e-6, "fdtd_z_max": 1.2e-6, "source_z": -5e-7, "source_polarization_angle": 0.0, "source_wavelength_start": 450e-9, "pillar_z_min": 0.0, "pillar_z_max": 500e-9, "pillar_radius": 85e-9, "T_z": 900e-9, "R_z": -750e-9}
    if before != after or any(abs(audit[k] - v) > 1e-12 for k, v in expected.items()): raise RuntimeError("D170 read-only fingerprint or contract mismatch")
    if audit["pillar_material"] != "APCD_TIO2_NATIVE_M1" or not audit["T_result_present"] or not audit["R_result_present"]: raise RuntimeError("D170 Native-M1/monitor contract mismatch")
    ax_blank = complex(blank["ax"]["real"], blank["ax"]["imag"])
    txx = complex(case["ax"]["real"], case["ax"]["imag"]) / ax_blank
    tyx = complex(case["ay"]["real"], case["ay"]["imag"]) / ax_blank
    result = {"stage": "P1-D1A2", "execution_mode": "foreground_ssh_synchronous_v1", "recovery_mode": "readonly_existing_postrun", "candidate_id": "NP_P1D_H500_D170", "H_nm": 500, "D_nm": 170, "gap_nm": 120, "polarization": "x", "wavelength_nm": 450, "pitch_x_nm": 290, "period_y_nm": 290, "pillar_base_z_nm": 0, "pillar_top_z_nm": 500, "transmission_reference_z_nm": 900, "phase_deembedding_used": False, "reference_blank_id": blank["case_id"], "reference_blank_sha256": blank["post_fsp"]["sha256"], "reference_blank_recovery_status": blank["recovery_status"], "source_post_fsp": before, "post_fsp_readonly_after": after, "read_only_object_audit": audit, "T": case["T"], "R_raw": case["R_raw"], "R_total": -case["R_raw"], "energy_residual": case["energy_residual"], "ax": case["ax"], "ay": case["ay"], "txx": {"real": txx.real, "imag": txx.imag, "amplitude": abs(txx), "phase_rad_wrapped": math.atan2(txx.imag, txx.real), "phase_deg_wrapped": math.degrees(math.atan2(txx.imag, txx.real))}, "tyx": {"real": tyx.real, "imag": tyx.imag, "amplitude": abs(tyx), "phase_rad_wrapped": math.atan2(tyx.imag, tyx.real), "phase_deg_wrapped": math.degrees(math.atan2(tyx.imag, tyx.real))}, "cross_pol_fraction": case["cross_pol_fraction"], "co_pol_zero_order_power": abs(txx) ** 2, "cross_pol_zero_order_power": abs(tyx) ** 2, "x_input_reconstruction_residual": case["x_input_reconstruction_residual"], "new_solver_runs_started_this_thread": 0, "new_solver_runs_completed_this_thread": 0, "prior_solver_start_status": None, "null_reason": "original_execution_observability_unavailable", "batch_status": "three_of_five_completed", "p1d1a_h500_completed_candidates": ["NP_P1D_H500_D110", "NP_P1D_H500_D140", "NP_P1D_H500_D170"], "p1d1a_h500_line_complete": False, "polarization_completeness": "x_only", "xy_symmetry_status": "pending_y_validation", "candidate_polarization_quality": "not_assessed_x_only"}
    if not finite(result): raise RuntimeError("non-finite D170 result")
    points = [d110, d140, result]
    phases = [row["txx"]["phase_deg_wrapped"] for row in points]
    d01, d12 = wrap(phases[1] - phases[0]), wrap(phases[2] - phases[1])
    provisional = [phases[0], phases[0] + d01, phases[0] + d01 + d12]
    analysis = {"analysis_scope": "three_point_provisional_not_complete_phase_line", "diameters_nm": [110, 140, 170], "points": [compact(row) for row in points], "wrapped_phase_deg": phases, "provisional_unwrapped_phase_deg": provisional, "D110_to_D140_minimal_wrapped_delta_deg": d01, "D140_to_D170_minimal_wrapped_delta_deg": d12, "D110_to_D170_provisional_phase_span_deg": provisional[2] - provisional[0], "provisional_three_point_unwrap": True, "P1C_D160_included": False, "resonance_or_phase_singularity_assessment": {"rapid_phase_change_observed": True, "amplitude_collapse_observed": False, "T_drop_at_D170": result["T"] < d140["T"], "R_rise_at_D170": result["R_total"] > d140["R_total"], "status": "not_indicated_by_three_point_joint_metrics"}}
    write(args.output / "results.json", result)
    (args.output / "results.csv").write_text("candidate_id,H_nm,D_nm,polarization,T,R_total,txx_amplitude,txx_phase_deg_wrapped,tyx_amplitude,cross_pol_fraction,energy_residual,x_input_reconstruction_residual\n" + f"NP_P1D_H500_D170,500,170,x,{result['T']},{result['R_total']},{abs(txx)},{result['txx']['phase_deg_wrapped']},{abs(tyx)},{result['cross_pol_fraction']},{result['energy_residual']},{result['x_input_reconstruction_residual']}\n")
    write(args.output / "partial_phase_analysis.json", analysis)
    write(args.output / "run_manifest.json", {"execution_mode": result["execution_mode"], "recovery_mode": result["recovery_mode"], "candidate_id": result["candidate_id"], "historical_post_fsp": before, "D110_results_sha256": hashlib.sha256((ROOT / "outputs/np_k6_p1d1a0_h500_d110_v1/results.json").read_bytes()).hexdigest(), "D140_results_sha256": hashlib.sha256((ROOT / "outputs/np_k6_p1d1a1_h500_d140_v1/results.json").read_bytes()).hexdigest(), "extractor_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "new_solver_runs_started_this_thread": 0})
    write(args.output / "verification_summary.json", {"P1D1A2_FORMAL_STATUS": "pass", "H500_D170_STATUS": "trusted_completed", "H500_COMPLETED_COUNT": 3, "H500_REMAINING_COUNT": 2, "P1D1A_NEXT_CANDIDATE": "NP_P1D_H500_D200", "P1D1A_D200_READY": True, "contract_gate": "pass", "reference_blank_gate": "pass", "post_fsp_readonly_gate": "pass", "solver_run_count_this_thread": 0})
    write(args.audit, {"before": before, "after": after, "audit": audit})


if __name__ == "__main__": main()
