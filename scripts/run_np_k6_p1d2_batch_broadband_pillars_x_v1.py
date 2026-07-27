"""Sequential, restart-safe wrapper for the frozen P1-D2 broadband pillar runner.

The only lumapi call is deliberately kept in ``_solve_once``.  Normal resume
paths use trusted lightweight results or a read-only post-FSP extraction.
"""
from __future__ import annotations

import argparse, csv, hashlib, json, os, sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import run_np_k6_p1d2b_broadband_pillar_x_v1 as single

AUTHORIZED_BATCH_DIAMETERS_NM = tuple(range(120, 231, 5))
CONTINUATION_AFTER_D180_NM = tuple(range(185, 231, 5))
PROTECTED_DIAMETERS_NM = (100, 105, 110, 115)
OUT = ROOT / "outputs" / "np_k6_p1d2_batch_d120_d230_v1"


def utc() -> str: return datetime.now(timezone.utc).isoformat()
def sha(value: Any) -> str: return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
def read(path: Path, fallback: Any) -> Any: return json.loads(path.read_text(encoding="utf-8")) if path.exists() else fallback
def atomic(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True); tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"); os.replace(tmp, path)
def case_out(d: int) -> Path:
    return ROOT / "outputs" / f"np_k6_p1d2b_broadband_d{d}_x_v1"
def allowed(values: list[int]) -> bool:
    return values == list(AUTHORIZED_BATCH_DIAMETERS_NM)
def continuation_allowed(values: list[int]) -> bool:
    return values == list(CONTINUATION_AFTER_D180_NM)
def contract() -> dict[str, Any]:
    return {"batch_mode":"sequential_checkpointed_foreground_v1", "authorized_diameters_nm":list(AUTHORIZED_BATCH_DIAMETERS_NM), "authorized_diameter_count":23, "maximum_new_solver_runs":23, "one_solver_run_max_per_diameter":True, "skip_trusted_completed_cases":True, "resume_from_checkpoint":True, "global_source_monitor_contract_frozen":True, "protected_evidence_diameters_nm":list(PROTECTED_DIAMETERS_NM), "polarization":"x", "normal_incidence":True, "wavelength_grid_nm":single.shared.target_axis(), "monitor_count":33, "sampling_backend":single.shared.BACKEND, "blank_id":"NP_P1D2_BROADBAND_FIXED_REFERENCE_BLANK_X"}
def initial_progress(values: list[int]) -> dict[str, Any]:
    return {"contract_hash":sha(contract()), "authorized_diameters_nm":values, "cases":{str(d):{"case_id":f"NP_P1D2_BROADBAND_PILLAR_H500_D{d}_X", "diameter_nm":d, "status":"pending", "attempt_count":0, "solver_entered_count":0, "solver_completed_count":0} for d in values}, "created_utc":utc()}
def trusted(d: int) -> bool:
    out=case_out(d); summary=read(out / "verification_summary.json", {})
    return (out / "results.json").exists() and summary.get("individual_pillar_spectral_quality") in {"pass", "warning_valid"} and any(v == "pass" for k,v in summary.items() if k.endswith("FORMAL_STATUS"))
def checkpoint(progress: dict[str,Any], ledger_path: Path, heartbeat_path: Path, d: int, status: str, progress_path: Path | None = None, **more: Any) -> None:
    row=progress["cases"][str(d)]; previous_status=row.get("status"); stamp=utc(); row.update(status=status, updated_utc=stamp, **more)
    atomic(progress_path or OUT / "batch_progress.json", progress)
    with ledger_path.open("a", encoding="utf-8", newline="\n") as f: f.write(json.dumps({"timestamp_utc":stamp, "diameter_nm":d, "case_id":row["case_id"], "previous_status":previous_status, "status":status, **more}, sort_keys=True)+"\n")
    done=sum(x["status"] in {"formal_pass","trusted_recovered"} for x in progress["cases"].values())
    atomic(heartbeat_path, {"updated_utc":utc(), "current_diameter_nm":d, "current_stage":status, "completed_count":done, "remaining_count":len(progress["cases"])-done})
def seal_failed_case_local(progress: dict[str,Any], ledger_path: Path, heartbeat_path: Path, d: int, failure_reason: str, forensic_note: str, progress_path: Path | None = None) -> bool:
    """Atomically seal a locally failed case.  A seal is terminal and never retried."""
    if d != 180: raise ValueError("only D180 is authorized for this sealed local-failure continuation")
    row=progress["cases"][str(d)]
    if row.get("status") == "sealed_failed_case_local": return False
    if row.get("status") in {"formal_pass", "trusted_recovered"}: raise RuntimeError("completed evidence cannot be sealed as failed")
    provenance={"failure_reason":failure_reason, "forensic_note":forensic_note, "attempt_count_at_seal":row.get("attempt_count",0), "solver_entered_count_at_seal":row.get("solver_entered_count",0), "solver_completed_count_at_seal":row.get("solver_completed_count",0), "sealed_utc":utc(), "retry_prohibited":True}
    checkpoint(progress,ledger_path,heartbeat_path,d,"sealed_failed_case_local",progress_path,forensic_provenance=provenance)
    return True
def metrics(rows: list[dict[str,Any]]) -> dict[str,Any]:
    amps=np.array([r["txx"]["amplitude"] for r in rows]); energy=np.array([r["energy_residual"] for r in rows]); recon=np.array([r["x_input_reconstruction_residual"] for r in rows])
    phase=np.degrees(np.unwrap([r["txx"]["phase_rad_wrapped"] for r in rows])); fit=np.polyfit(single.shared.target_axis(), phase, 1)
    return {"T_min_over_band":float(min(r["T"] for r in rows)), "T_max_over_band":float(max(r["T"] for r in rows)), "R_total_min_over_band":float(min(r["R_total"] for r in rows)), "R_total_max_over_band":float(max(r["R_total"] for r in rows)), "txx_amplitude_min_over_band":float(amps.min()), "txx_amplitude_max_over_band":float(amps.max()), "txx_amplitude_CV_over_band":float(amps.std()/amps.mean()), "cross_pol_max_over_band":float(max(r["tyx"]["amplitude"] for r in rows)), "energy_residual_max_over_band":float(energy.max()), "reconstruction_residual_max_over_band":float(recon.max()), "phase_linear_fit_slope_deg_per_nm":float(fit[0])}
def write_case(d: int, s: dict[str,Any], pre: dict[str,Any], post: dict[str,Any], solver_counts: tuple[int,int]) -> None:
    out=case_out(d); out.mkdir(parents=True, exist_ok=True); rows=post["rows"]
    if len(rows)!=11 or not np.allclose([r["wavelength_nm"] for r in rows], single.shared.target_axis(), atol=1e-6, rtol=0): raise RuntimeError("exact 11-point axis required")
    m=metrics(rows); quality="pass" if max(m["energy_residual_max_over_band"],m["reconstruction_residual_max_over_band"])<=.03 else "warning_valid" if max(m["energy_residual_max_over_band"],m["reconstruction_residual_max_over_band"])<=.08 else "fail_data_quality"
    formal="pass" if quality != "fail_data_quality" else "fail"; result={"case_id":s["case_id"],"rows":rows}; single._write(out/"results.json",result); single._write(out/"spectral_metrics.json",m)
    single._write(out/"wavelength_axis_audit.json",{"target_axis":single.shared.target_axis(),"configured_axis":pre["configured_axis_nm"],"extracted_axis":[r["wavelength_nm"] for r in rows],"exact_axis_gate":True,"interpolation_used":False,"nearest_neighbor_used":False,"sampling_backend":single.shared.BACKEND})
    single._write(out/"blank_pillar_contract_diff.json",pre["contract_diff"]); single._write(out/"physical_contract.json",{"case_id":s["case_id"],"diameter_nm":d,"radius_nm":d/2,"gap_nm":290-d,"aspect_ratio":500/d,"sampling_backend":single.shared.BACKEND,"target_axis_nm":single.shared.target_axis(),"blank_pillar_contract_diff_hash":pre["contract_diff"]["comparison_hash"],"interpolation_used":False,"nearest_neighbor_used":False})
    single._write(out/"run_manifest.json",{"case_id":s["case_id"],"pre_fsp":pre["fingerprint"],"post_fsp":post["fingerprint"],"new_solver_run_entered":solver_counts[0],"new_solver_run_completed":solver_counts[1],"created_utc":utc()})
    single._write(out/"verification_summary.json",{"P1D2_BATCH_FORMAL_STATUS":formal,"individual_pillar_spectral_quality":quality,"finite_data_gate":True,"denominator_safety_gate":True,"blank_pillar_axis_match_gate":True,"post_fsp_readonly_gate":True,"metrics":m})
    with (out/"results.csv").open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=["wavelength_nm","T","R_raw","R_total","txx_amplitude","txx_phase_deg_wrapped","tyx_amplitude","energy_residual","x_input_reconstruction_residual"]); w.writeheader()
        for r in rows: w.writerow({"wavelength_nm":r["wavelength_nm"],"T":r["T"],"R_raw":r["R_raw"],"R_total":r["R_total"],"txx_amplitude":r["txx"]["amplitude"],"txx_phase_deg_wrapped":r["txx"]["phase_deg_wrapped"],"tyx_amplitude":r["tyx"]["amplitude"],"energy_residual":r["energy_residual"],"x_input_reconstruction_residual":r["x_input_reconstruction_residual"]})
def _solve_once() -> None:
    fdtd=single.base._import_lumapi().FDTD(hide=True)
    try:
        fdtd.load(str(single.PRE)); print("SOLVER_RUN_CALL_ENTERING", flush=True); fdtd.run(); print("SOLVER_RUN_CALL_RETURNED", flush=True); fdtd.save(str(single.POST))
    finally: fdtd.close()
def execute_case(d: int, progress: dict[str,Any], ledger: Path, heartbeat: Path, permit_solver: bool) -> None:
    row=progress["cases"][str(d)]
    if row.get("status") == "sealed_failed_case_local": return
    if trusted(d): checkpoint(progress,ledger,heartbeat,d,"trusted_recovered",reason="trusted lightweight result exists"); return
    if row.get("solver_entered_count",0) and not single.POST.exists(): checkpoint(progress,ledger,heartbeat,d,"blocked_global",failure_reason="solver entered without trusted post-FSP; automatic rerun prohibited"); raise RuntimeError(f"D{d} requires manual recovery")
    single.configure(d); s=single.spec(); post_exists=single.POST.exists()
    if post_exists:
        post=single.extract(single.POST); pre=single.audit(single.POST,s); write_case(d,s,pre,post,(row.get("solver_entered_count",0),row.get("solver_completed_count",0))); checkpoint(progress,ledger,heartbeat,d,"formal_pass",recovered_post_fsp=True,result_hash=sha(post["rows"])); return
    pre=single.build_pre(s); checkpoint(progress,ledger,heartbeat,d,"setup_pass",pre_fsp=pre["fingerprint"])
    if not permit_solver: return
    checkpoint(progress,ledger,heartbeat,d,"solver_entered",attempt_count=row.get("attempt_count",0)+1,solver_entered_count=row.get("solver_entered_count",0)+1)
    _solve_once(); checkpoint(progress,ledger,heartbeat,d,"solver_completed",solver_completed_count=row.get("solver_completed_count",0)+1)
    post=single.extract(single.POST); write_case(d,s,pre,post,(1,1)); checkpoint(progress,ledger,heartbeat,d,"formal_pass",post_fsp=post["fingerprint"],result_hash=sha(post["rows"]))
def main() -> int:
    p=argparse.ArgumentParser(); p.add_argument("--diameters-nm",required=True); p.add_argument("--resume",action="store_true"); p.add_argument("--checkpoint-path",type=Path,default=OUT/"batch_progress.json"); p.add_argument("--maximum-new-solver-runs",type=int,default=23); p.add_argument("--no-solver",action="store_true"); p.add_argument("--seal-failed-case-local",type=int); p.add_argument("--failure-reason",default="D180 local failure sealed by authorized continuation"); p.add_argument("--forensic-note",default="") ; a=p.parse_args(); values=[int(x) for x in a.diameters_nm.split(",") if x]
    continuation=a.seal_failed_case_local is not None
    if continuation:
        if a.seal_failed_case_local != 180 or not a.resume or not continuation_allowed(values) or a.maximum_new_solver_runs != 10: raise ValueError("sealed D180 continuation requires --resume, D185-D230 order, and maximum-new-solver-runs 10")
    elif not allowed(values) or a.maximum_new_solver_runs != 23: raise ValueError("frozen batch is exactly D120-D230 in 5-nm order with solver maximum 23")
    OUT.mkdir(parents=True,exist_ok=True); atomic(OUT/"batch_execution_contract.json",contract()); progress=read(a.checkpoint_path,initial_progress(values)); ledger=OUT/"batch_case_ledger.jsonl"; heartbeat=OUT/"batch_heartbeat.json"
    if progress.get("authorized_diameters_nm") != list(AUTHORIZED_BATCH_DIAMETERS_NM): raise RuntimeError("checkpoint contract mismatch")
    if continuation: seal_failed_case_local(progress,ledger,heartbeat,180,a.failure_reason,a.forensic_note,a.checkpoint_path)
    single.blank_evidence()
    for d in values: execute_case(d,progress,ledger,heartbeat,not a.no_solver)
    return 0
if __name__ == "__main__": raise SystemExit(main())
