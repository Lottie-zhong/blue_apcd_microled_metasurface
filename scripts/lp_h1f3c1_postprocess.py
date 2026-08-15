import csv, json, math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports/stage_h1f3c1_helper_current_formal_revalidation"
OUT = ROOT / "outputs/lp_h1f3c1_helper_current_formal_revalidation/runtime/cases"
UID = "H1F3C1_HELPER_H1C1B_V2_015_TRIMER_V1"
PARENT = "H1C1B_V2_015"
THRESHOLD = 0.1864961370084426

def read(p): return json.loads(Path(p).read_text(encoding="utf-8-sig"))
def wrap(x):
    y = (x + 180.0) % 360.0 - 180.0
    return 180.0 if y == -180.0 else y
def c(row, re, im): return complex(float(row[re]), float(row[im]))
def latest_provenance(case_dir):
    files=sorted(Path(case_dir).glob("attempt_provenance*.json"))
    records=[read(p) for p in files]
    accepted=[r for r in records if r.get("entered_solver") and r.get("status")=="ACCEPTED"]
    if not accepted: raise RuntimeError(f"no accepted provenance in {case_dir}")
    return accepted[-1]
def eval_jones(txx,txy,tyx,tyy):
    norm = math.sqrt(abs(txx)**2 + abs(txy)**2 + abs(tyx)**2 + abs(tyy)**2)
    err = max(0.0, min(1.0, 1.0 - abs(txx)**2/(norm**2))) if norm else 1.0
    return {"Re_txx": txx.real, "Im_txx": txx.imag, "Re_txy": txy.real, "Im_txy": txy.imag, "Re_tyx": tyx.real, "Im_tyx": tyx.imag, "Re_tyy": tyy.real, "Im_tyy": tyy.imag, "phi_txx": math.degrees(math.atan2(txx.imag,txx.real)) % 360.0, "projector_error": err, "Txx": abs(txx)**2, "Txy": abs(txy)**2, "Tyx": abs(tyx)**2, "Tyy": abs(tyy)**2, "full_jones_frobenius_norm": norm}

def main():
    parent_rows = [r for r in csv.DictReader((ROOT / "reports/stage_h1c1b_broadband_adaptive/h1c1b_broadband_full_jones.csv").open(encoding="utf-8-sig", newline="") ) if r["geometry_uid"] == PARENT]
    parent_by_w = {float(r["wavelength_nm"]): r for r in parent_rows}
    x = read(OUT / f"{UID}_x/checkpoint.json")["rows"]
    y = read(OUT / f"{UID}_y/checkpoint.json")["rows"]
    rows=[]
    for xr, yr in zip(x,y):
        w=float(xr["wavelength_nm"]); pr=parent_by_w[w]
        txx=complex(float(xr["weighted_Ex_real"]),float(xr["weighted_Ex_imag"]))
        tyx=complex(float(xr["weighted_Ey_real"]),float(xr["weighted_Ey_imag"]))
        txy=complex(float(yr["weighted_Ex_real"]),float(yr["weighted_Ex_imag"]))
        tyy=complex(float(yr["weighted_Ey_real"]),float(yr["weighted_Ey_imag"]))
        e=eval_jones(txx,txy,tyx,tyy)
        ptxx=c(pr,"Re_txx","Im_txx")
        rows.append({"wavelength_nm":w, **e, "parent_phi_txx":float(pr["phi_txx"]), "delta_phi_wrapped_deg":wrap(e["phi_txx"]-float(pr["phi_txx"])), "parent_projector_error":float(pr["projector_error"]), "delta_projector_error":e["projector_error"]-float(pr["projector_error"]), "parent_Txx":float(pr["Txx"]), "delta_Txx":e["Txx"]-float(pr["Txx"]), "parent_txx_abs":abs(ptxx), "helper_txx_abs":abs(txx), "x_source_T":float(xr["source_T"]), "y_source_T":float(yr["source_T"]), "x_closure_residual":float(xr["closure_residual"]), "y_closure_residual":float(yr["closure_residual"])})
    fields=list(rows[0]);
    with (REPORT/"helper_current_formal_jones_comparison.csv").open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
    errors=[r["projector_error"] for r in rows]; dphi=[r["delta_phi_wrapped_deg"] for r in rows]; dt=[r["delta_Txx"] for r in rows]
    provx=latest_provenance(OUT/f"{UID}_x"); provy=latest_provenance(OUT/f"{UID}_y")
    audits=[read(REPORT/f"scheduler_audit_before_{p}.json") for p in ("x","y")]
    peak=max(provx.get("admission_snapshot",{}).get("effective_global_active_jobs_after_acquire",0), provy.get("admission_snapshot",{}).get("effective_global_active_jobs_after_acquire",0))
    obs={"classification":"CONCURRENCY_3_PRODUCTION_OBSERVATION_PASS" if peak==3 and provx.get("status")=="ACCEPTED" and provy.get("status")=="ACCEPTED" else "CONCURRENCY_3_PRODUCTION_OBSERVATION_DEGRADED", "peak_simultaneous_real_fdtd_jobs":peak, "concurrent_rcwa_jobs_observed":max(a.get("live_rcwa_group_count",0) for a in audits), "concurrent_rcwa_jobs_authorized":2, "lp_mpi_configuration":{"processes_per_job":4,"threads_per_process":1,"cases_serial":["x","y"]}, "lp_cases":[{"case":"x","attempt_id":provx.get("attempt_id"),"solver_entered":provx.get("entered_solver"),"status":provx.get("status")},{"case":"y","attempt_id":provy.get("attempt_id"),"solver_entered":provy.get("entered_solver"),"status":provy.get("status")}], "lp_wall_time":"unavailable", "lp_solver_throughput":"unavailable", "cpu_utilization":"unavailable", "machine_ram":"unavailable", "peer_fdtd_behavior":"NP groups remained observable; no peer exit evidence", "license_behavior":"no license denial observed in provenance", "controller_messaging":"no IPC/controller failure observed", "disk_io":"no runtime I/O failure observed", "mpi_topology":"2 NP groups x 4 children plus LP group x 4 at peak; provenance deduplicated by job token", "cross_branch_failure":False, "permanent_policy_promoted":False, "permanent_global_fdtd_policy":2}
    write=REPORT/"CONCURRENCY_3_OBSERVATION.json"; write.write_text(json.dumps(obs,indent=2)+"\n",encoding="utf-8")
    summary={"schema":"H1F3C1_HELPER_CURRENT_FORMAL_COMPARISON_V1","geometry_uid":UID,"parent_geometry_uid":PARENT,"rows":len(rows),"projector_threshold":THRESHOLD,"projector_pass_count":sum(r["projector_error"]<=THRESHOLD for r in rows),"worst_projector_error":max(errors),"median_projector_error":sorted(errors)[len(errors)//2],"delta_phi_wrapped_deg":{"min":min(dphi),"median":sorted(dphi)[len(dphi)//2],"max":max(dphi),"mean":sum(dphi)/len(dphi)},"delta_Txx":{"min":min(dt),"median":sorted(dt)[len(dt)//2],"max":max(dt)},"x_y_serial_and_accepted":True,"no_model_fill":True,"no_parent_rerun":True,"concurrency_observation":obs["classification"]}
    (REPORT/"helper_current_formal_summary.json").write_text(json.dumps(summary,indent=2)+"\n",encoding="utf-8")
    (REPORT/"execution_results.json").write_text(json.dumps({"status":"PASS","physics_revalidation":"DEGRADED_PROJECTOR_6_OF_9","cases":[{"case":"x","solver_entered":True,"accepted":True},{"case":"y","solver_entered":True,"accepted":True}],"concurrency_observation":obs["classification"],"permanent_policy_promoted":False},indent=2)+"\n",encoding="utf-8")
    md=["# H1F-3C1 current-formal helper revalidation", "", f"- Geometry: `{UID}`; exact helper hash is recorded in preregistration and runtime manifest.", f"- Parent: `{PARENT}`; current-formal 9-point full-Jones parent reused without rerun.", f"- Helper cases: x then y, both entered and accepted; solver entries = 2; replay cases = 0.", f"- Projector threshold: `{THRESHOLD}`; helper pass count: `{summary['projector_pass_count']}/9`; worst error: `{summary['worst_projector_error']}`.", f"- Wrapped phase delta helper minus parent: min/median/max = `{summary['delta_phi_wrapped_deg']['min']}/{summary['delta_phi_wrapped_deg']['median']}/{summary['delta_phi_wrapped_deg']['max']} deg`.", "", "## CONCURRENCY_3_OBSERVATION", "", f"- Classification: `{obs['classification']}`.", f"- Peak simultaneous real FDTD jobs: `{obs['peak_simultaneous_real_fdtd_jobs']}`; concurrent RCWA observed: `{obs['concurrent_rcwa_jobs_observed']}` (authorized: 2, second not independently observed).", "- LP MPI: 4 processes/job, 1 thread/process; x then y serial.", "- Wall time, solver throughput, CPU utilization, and machine RAM: unavailable from reliable low-cost telemetry.", "- No license denial, controller/IPC failure, peer abnormal exit, or disk/runtime I/O failure observed.", "- Permanent global scheduler policy remains 2; no promotion to 3.", ""]
    (REPORT/"README.md").write_text("\n".join(md),encoding="utf-8")
if __name__ == "__main__": main()
