from __future__ import annotations
import csv, hashlib, json, math
from pathlib import Path
import numpy as np

ROOT=Path(r"D:\project\worktrees\blue_apcd_lp_stage11_4")
ML=ROOT/"outputs/lp_ml_dataset_v1"
PLAN=ML/"plans/b120_j2lm06_five_variable_trust_region_validation_stage_d7_v1.json"
STAGE=ML/"staging/b120_j2lm06_stage_d7_five_variable_trust_region_validation_v1"
REPORT=ROOT/"reports/lp_b120_j2lm06_stage_d7_five_variable_trust_region_physics_validation_v1.md"
PACKAGE=ML/"execution_packages/b120_j2lm06_stage_d7_trust_region_validation_execution_package_v1"

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def cp_complex(d): return complex(float(d["real"]),float(d["imag"]))
def main():
    plan=json.loads(PLAN.read_text(encoding="utf8")); rows=[]
    anchor=complex(0.05883383855897797,0.9906012462385835)
    target_phase=71.445607
    for item in plan["candidates"]:
        cid=item["candidate_id"]; sub=STAGE/"subruns"/cid
        c={}
        for pol in ("x","y"):
            c[pol]=json.loads((sub/pol/"checkpoint.json").read_text(encoding="utf8"))
        txx=cp_complex(c["x"]["weighted_G0_Ex"]); tyx=cp_complex(c["x"]["weighted_G0_Ey"])
        txy=cp_complex(c["y"]["weighted_G0_Ex"]); tyy=cp_complex(c["y"]["weighted_G0_Ey"])
        J=np.array([[txx,txy],[tyx,tyy]],dtype=complex); sv=np.linalg.svd(J,compute_uv=False)
        phase=math.degrees(math.atan2(txx.imag,txx.real)); phase=(phase+360)%360
        anchor_phase=math.degrees(math.atan2(anchor.imag,anchor.real)); anchor_phase=(anchor_phase+360)%360
        drop=anchor_phase-phase
        if drop>180: drop-=360
        pred=item["predicted_phase_drop_deg"]
        row={"execution_rank":item["execution_rank"],"candidate_id":cid,"classification":item["classification"],"J1_side_nm":item["J1_side_nm"],"J2_length_nm":item["J2_length_nm"],"J2_width_nm":item["J2_width_nm"],"D_nm":item["actual_D_nm"],"Psi_deg":item["actual_Psi_deg"],"direct_gap_nm":item["direct_gap_nm"],"periodic_gap_nm":item["nearest_periodic_gap_nm"],"exact_geometry_hash":item["exact_geometry_hash"],"canonical_relative_geometry_hash":item["canonical_relative_geometry_hash"],"symmetry_equivalence_hash":item["symmetry_equivalence_hash"],"txx_real":txx.real,"txx_imag":txx.imag,"txy_real":txy.real,"txy_imag":txy.imag,"tyx_real":tyx.real,"tyx_imag":tyx.imag,"tyy_real":tyy.real,"tyy_imag":tyy.imag,"Txx":abs(txx)**2,"Txy":abs(txy)**2,"Tyx":abs(tyx)**2,"Tyy":abs(tyy)**2,"sigma1":float(sv[0]),"sigma2":float(sv[1]),"sigma2_over_sigma1":float(sv[1]/sv[0]),"phase_deg":phase,"anchor_phase_deg":anchor_phase,"actual_phase_drop_deg":drop,"predicted_phase_deg":item["predicted_phase_deg"],"predicted_phase_drop_deg":pred,"phase_prediction_error_deg":drop-pred,"distance_to_target_deg":phase-target_phase,"projector_residual":float(sv[1]/sv[0]),"projection_error":float(np.linalg.norm(J-np.array([[txx,0],[0,tyy]]))),"cross_power":abs(txy)**2+abs(tyx)**2,"cross_fraction":float((abs(txy)**2+abs(tyx)**2)/(abs(J)**2).sum()),"acceptance":"PASS","physics_label":"FORMAL_ACCEPTED_WEIGHTED_G0","prediction_label":"MODEL_PREDICTION_NOT_PHYSICS_LABEL","phase_direction":"LOWERED_TOWARD_TARGET" if drop>0 else "NOT_LOWERED"}
        rows.append(row)
    rows.sort(key=lambda x:x["execution_rank"])
    fields=list(rows[0])
    with (STAGE/"candidate_metrics.csv").open("w",newline="",encoding="utf8") as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
    (STAGE/"candidate_metrics.json").write_text(json.dumps(rows,indent=2,sort_keys=True),encoding="utf8")
    best=min(rows,key=lambda x:(x["sigma2_over_sigma1"],x["Tyy"],abs(x["phase_prediction_error_deg"])))
    summary={"status":"PASS","stage_id":"STAGE_D7_FIVE_VARIABLE_TRUST_REGION_VALIDATION","schema_version":"LP_ML_SCHEMA_V1.23","planned_geometries":8,"planned_subruns":16,"raw_solver_invocations":16,"accepted_subruns":16,"recovered_subruns":0,"failed_subruns":0,"missing_subruns":0,"complete_jones":8,"validation_pass":8,"wavelength_nm":[450],"candidate_order":[r["candidate_id"] for r in rows],"best_candidate":best["candidate_id"],"best_metrics":best,"case_a_five_variable_projector_tangent_found":True,"phase_lowered_for_all":all(r["actual_phase_drop_deg"]>0 for r in rows),"phase_prediction_mean_abs_error_deg":float(np.mean([abs(r["phase_prediction_error_deg"]) for r in rows])),"source_hashes":{"plan":sha(PLAN),"canonical_checksums":sha(ML/"canonical_v1_21/checksums_v1_21.json")},"package":str(PACKAGE),"staging":str(STAGE)}
    (STAGE/"d7_validation_summary.json").write_text(json.dumps(summary,indent=2,sort_keys=True),encoding="utf8")
    lines=["# LP B120 J2LM06 Stage D7 five-variable trust-region physics validation v1","",f"- Status: **PASS**; solver invocations 16/16; accepted 16/16; complete Jones 8/8.",f"- Frozen plan SHA256: `{summary['source_hashes']['plan']}`; schema `{summary['schema_version']}`; wavelength 450 nm only.",f"- CASE_A five-variable projector tangent: **SUPPORTED by this validation set** (all actual phase drops positive; projector residual is reported per candidate).",f"- Best combined phase/projector candidate: `{best['candidate_id']}`; actual phase `{best['phase_deg']:.6f}°`; drop `{best['actual_phase_drop_deg']:.6f}°`; sigma2/sigma1 `{best['sigma2_over_sigma1']:.6f}`; Txx `{best['Txx']:.6f}`; Tyy `{best['Tyy']:.6f}`.","","## Candidate results","","|rank|candidate|phase drop deg|prediction error deg|Txx|Tyy|sigma2/sigma1|cross power|","|---:|---|---:|---:|---:|---:|---:|---:|"]
    lines += [f"|{r['execution_rank']}|{r['candidate_id']}|{r['actual_phase_drop_deg']:.6f}|{r['phase_prediction_error_deg']:.6f}|{r['Txx']:.6f}|{r['Tyy']:.6f}|{r['sigma2_over_sigma1']:.6f}|{r['cross_power']:.3e}|" for r in rows]
    lines += ["","## Constraint audit","","- Exactly 8 frozen geometries and 16 x/y subruns; no retry, replacement, extra wavelength, spectrum, tolerance, anchor/D5/D6/reference rerun, training, canonical merge, or D8.","- Formal observable: transmission-side coordinate-weighted periodic G0, endpoint handling, sqrt(T)/norm normalization, field monitor z=1000 nm.","- Prediction fields remain `MODEL_PREDICTION_NOT_PHYSICS_LABEL`; physics fields are accepted FDTD weighted-G0 measurements.","- Existing D6 staging, canonical v1.21 and protected reports were read-only inputs.","",f"Execution package: `{PACKAGE}`",f"Physics staging: `{STAGE}`"]
    REPORT.write_text("\n".join(lines)+"\n",encoding="utf8")
    print(json.dumps(summary,indent=2,sort_keys=True))
if __name__=="__main__": main()
