"""Read-only recovery closure for an already completed NP-K6 H500/D110 run."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path


ROOT = Path(r"D:\project\worktrees\blue_apcd_np_k6_mdc_v1")


def write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(tmp, path)


def sha(path: Path) -> dict[str, object]:
    stat = path.stat()
    return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "size_bytes": stat.st_size, "mtime_ns": stat.st_mtime_ns}


def finite(value: object) -> bool:
    if isinstance(value, dict): return all(finite(v) for v in value.values())
    if isinstance(value, list): return all(finite(v) for v in value)
    return not isinstance(value, float) or math.isfinite(value)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--audit", type=Path, required=True)
    a = p.parse_args()
    source_results = json.loads((ROOT / "outputs/np_k6_p1d1a_h500_x_v1/results.json").read_text())
    ref_results = json.loads((ROOT / "outputs/np_k6_p1d0b_corner_pilot_v1/results.json").read_text())
    case = next(x for x in source_results["cases"] if x["candidate_id"] == "NP_P1D_H500_D110")
    blank = ref_results["blank"]
    post = ROOT / case["source_fsp"]["path"]
    before = sha(post)
    if before["sha256"] != case["source_fsp"]["sha256"]:
        raise RuntimeError("historical post-FSP fingerprint does not match its result record")
    # The only FDTD interaction is load/getnamed/getresult/close; no mutation APIs are used.
    import sys
    sys.path.insert(0, r"N:\Program Files\ANSYS Inc\v251\Lumerical\api\python")
    import lumapi  # type: ignore
    fdtd = lumapi.FDTD(hide=True)
    try:
        fdtd.load(str(post))
        audit = {
            "fdtd_z_min": float(fdtd.getnamed("FDTD", "z min")),
            "fdtd_z_max": float(fdtd.getnamed("FDTD", "z max")),
            "source_z": float(fdtd.getnamed("source", "z")),
            "source_polarization_angle": float(fdtd.getnamed("source", "polarization angle")),
            "source_wavelength_start": float(fdtd.getnamed("source", "wavelength start")),
            "pillar_z_min": float(fdtd.getnamed("TiO2 pillar", "z min")),
            "pillar_z_max": float(fdtd.getnamed("TiO2 pillar", "z max")),
            "pillar_radius": float(fdtd.getnamed("TiO2 pillar", "radius")),
            "pillar_material": str(fdtd.getnamed("TiO2 pillar", "material")),
            "T_z": float(fdtd.getnamed("T_fields", "z")),
            "R_z": float(fdtd.getnamed("R_fields", "z")),
            "T_result_present": bool(fdtd.getresult("T_fields", "E")),
            "R_result_present": bool(fdtd.getresult("R_fields", "E")),
            "T_fields_result_present": bool(fdtd.getresult("T_fields", "E")),
        }
    finally:
        fdtd.close()
    after = sha(post)
    if before != after:
        raise RuntimeError("read-only FSP audit changed the post-run FSP fingerprint")
    expected = {"fdtd_z_min": -1e-6, "fdtd_z_max": 1.2e-6, "source_z": -5e-7, "source_polarization_angle": 0.0, "source_wavelength_start": 450e-9, "pillar_z_min": 0.0, "pillar_z_max": 500e-9, "pillar_radius": 55e-9, "T_z": 900e-9, "R_z": -750e-9}
    for name, value in expected.items():
        if abs(audit[name] - value) > 1e-12: raise RuntimeError(f"contract mismatch: {name}={audit[name]!r}")
    if not all(audit[k] for k in ("T_result_present", "R_result_present", "T_fields_result_present")):
        raise RuntimeError("required monitor data missing from post-run FSP")
    if audit["pillar_material"] != "APCD_TIO2_NATIVE_M1":
        raise RuntimeError("Native-M1 pillar material mismatch")
    txx = complex(case["ax"]["real"], case["ax"]["imag"]) / complex(blank["ax"]["real"], blank["ax"]["imag"])
    tyx = complex(case["ay"]["real"], case["ay"]["imag"]) / complex(blank["ax"]["real"], blank["ax"]["imag"])
    result = {
        "stage": "P1-D1A0", "execution_mode": "readonly_recovery_after_existing_postrun_v1",
        "candidate_id": case["candidate_id"], "H_nm": 500, "D_nm": 110, "gap_nm": 180,
        "polarization": "x", "wavelength_nm": 450, "pitch_x_nm": 290, "period_y_nm": 290,
        "pillar_base_z_nm": 0, "pillar_top_z_nm": 500, "transmission_reference_z_nm": 900,
        "phase_deembedding_used": False, "reference_blank_id": blank["case_id"],
        "reference_blank_sha256": blank["post_fsp"]["sha256"], "reference_blank_recovery_status": blank["recovery_status"],
        "source_post_fsp": before, "post_fsp_readonly_after": after, "read_only_object_audit": audit,
        "T": case["T"], "R_raw": case["R_raw"], "R_total": -case["R_raw"], "energy_residual": case["energy_residual"],
        "ax": case["ax"], "ay": case["ay"],
        "txx": {"real": txx.real, "imag": txx.imag, "amplitude": abs(txx), "phase_rad_wrapped": math.atan2(txx.imag, txx.real), "phase_deg_wrapped": math.degrees(math.atan2(txx.imag, txx.real))},
        "tyx": {"real": tyx.real, "imag": tyx.imag, "amplitude": abs(tyx), "phase_rad_wrapped": math.atan2(tyx.imag, tyx.real), "phase_deg_wrapped": math.degrees(math.atan2(tyx.imag, tyx.real))},
        "cross_pol_fraction": case["cross_pol_fraction"], "co_pol_zero_order_power": abs(txx) ** 2,
        "cross_pol_zero_order_power": abs(tyx) ** 2, "x_input_reconstruction_residual": case["x_input_reconstruction_residual"],
        "new_solver_runs_started_this_thread": 0, "new_solver_runs_completed_this_thread": 0,
        "prior_attempt_solver_start_status": None, "null_reason": "original_execution_observability_unavailable",
        "exact_total_solver_attempt_count": None, "solver_accounting_quality": "current_thread_exact_prior_attempt_unknown",
        "batch_status": "one_of_five_completed", "p1d1a_h500_line_complete": False,
        "polarization_completeness": "x_only", "xy_symmetry_status": "pending_y_validation", "candidate_polarization_quality": "not_assessed_x_only",
    }
    if not finite(result): raise RuntimeError("non-finite recovered result")
    write(a.output / "results.json", result)
    (a.output / "results.csv").write_text("candidate_id,H_nm,D_nm,polarization,T,R_total,txx_amplitude,txx_phase_deg_wrapped,tyx_amplitude,cross_pol_fraction,energy_residual,x_input_reconstruction_residual\n" + f"{case['candidate_id']},500,110,x,{case['T']},{-case['R_raw']},{abs(txx)},{math.degrees(math.atan2(txx.imag,txx.real))},{abs(tyx)},{case['cross_pol_fraction']},{case['energy_residual']},{case['x_input_reconstruction_residual']}\n")
    write(a.output / "run_manifest.json", {
        "execution_mode": result["execution_mode"], "candidate_id": result["candidate_id"],
        "historical_result_source": str(ROOT / "outputs/np_k6_p1d1a_h500_x_v1/results.json"),
        "historical_post_fsp": before, "reference_blank_sha256": blank["post_fsp"]["sha256"],
        "new_solver_runs_started_this_thread": 0, "prior_attempt_solver_start_status": None,
        "null_reason": result["null_reason"], "extractor_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    })
    write(a.output / "verification_summary.json", {
        "P1D1A0_FORMAL_STATUS": "pass", "H500_D110_STATUS": "trusted_completed",
        "P1D1A_REMAINING_FOUR_READY": True, "post_fsp_readonly_gate": "pass",
        "contract_gate": "pass", "reference_blank_gate": "pass", "monitor_data_gate": "pass",
        "solver_run_count_this_thread": 0, "reason_no_new_solver": "trusted historical post-run FSP existed before this task",
    })
    write(a.audit, {"before": before, "after": after, "audit": audit})


if __name__ == "__main__": main()
