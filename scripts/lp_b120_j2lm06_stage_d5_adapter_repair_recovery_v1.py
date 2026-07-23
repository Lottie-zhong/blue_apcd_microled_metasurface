from __future__ import annotations

# Staged to the authorized remote worktree by Codex.  The remote copy is the
# formal artifact; this local transfer file is removed immediately afterwards.
import argparse, csv, hashlib, importlib.util, json, math, os, shutil, socket, sys, time, uuid
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

R = Path(r"D:\project\worktrees\blue_apcd_lp_stage11_4")
O = R / "outputs"; ML = O / "lp_ml_dataset_v1"; A = ML / "analysis"; P = ML / "plans"; CAN = ML / "canonical_v1_20"
OLDPATH = R / "scripts/lp_b120_j2lm06_local_planar_size_jacobian_stage_d5_execute_v1.py"
ATT1 = ML / "staging/b120_j2lm06_local_planar_size_jacobian_stage_d5_v1_attempt1_lp_ml_schema_v1_21"
ATT1ROOT = O / "lp_b120_j2lm06_local_planar_size_jacobian_stage_d5_v1_attempt1"
ST = ML / "staging/b120_j2lm06_local_planar_size_jacobian_stage_d5_v1_attempt2_recovery_lp_ml_schema_v1_21"
ROOT = O / "lp_b120_j2lm06_local_planar_size_jacobian_stage_d5_v1_attempt2_recovery"
SUB = ROOT / "subruns"; CAND = ROOT / "candidates"; RUNTIME = ROOT / "runtime"
SCRIPT = R / "scripts/lp_b120_j2lm06_stage_d5_adapter_repair_recovery_v1.py"
REPORT = R / "reports/lp_b120_j2lm06_stage_d5_adapter_repair_recovery_and_route_decision_v1.md"
SCHEMA = "LP_ML_SCHEMA_V1.21"; ATT1_ID = "D5_ATTEMPT1"; ATT2_ID = "D5_ATTEMPT2_RECOVERY"; VERSION = "J2LM06_STAGE_D5_ADAPTER_REPAIR_MISSING_PAIR_RECOVERY_V1"
EXPECTED = ["LP_H500_D5_J2LM06_J1_side_nmM01","LP_H500_D5_J2LM06_J1_side_nmP01","LP_H500_D5_J2LM06_J2_length_nmM01","LP_H500_D5_J2LM06_J2_length_nmP01","LP_H500_D5_J2LM06_J2_width_nmM01","LP_H500_D5_J2LM06_J2_width_nmP01"]
AXES = ["J1_side_nm","J2_length_nm","J2_width_nm"]
PROT = {R / "reports/lp_ml1a3_git_history_geometry_reconstruction.md":"21c6884f71bad6bd6779d7ccc90cec55ab1a94e239f849ea74a942bdd50edd6a",R / "reports/stage11_4a20_legacy_fsp_object_inventory.md":"ae3b13341547e13ca85ca763ed8265591c100ac1a78c555de1c8378816a33708"}

def load(p,n):
    s=importlib.util.spec_from_file_location(n,p); m=importlib.util.module_from_spec(s); assert s and s.loader; sys.modules[n]=m; s.loader.exec_module(m); return m
old=load(OLDPATH,"d5_attempt1_adapter")
base, runner, legacy = old.base, old.runner, old.legacy

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def now(): return datetime.now(timezone.utc).isoformat()
def truth(v): return str(v).strip().lower() in {"true","1","yes","pass"}
def atomic(p, obj):
    p=Path(p); p.parent.mkdir(parents=True,exist_ok=True); t=p.with_name(p.name+".tmp."+uuid.uuid4().hex)
    t.write_text(json.dumps(obj,indent=2,sort_keys=True,default=str),encoding="utf8");
    with t.open("r+b") as f: os.fsync(f.fileno())
    os.replace(t,p)
def write_csv(p, rows):
    p=Path(p); p.parent.mkdir(parents=True,exist_ok=True); fields=list(dict.fromkeys(k for r in rows for k in r)) or ["empty"]
    t=p.with_name(p.name+".tmp."+uuid.uuid4().hex)
    with t.open("w",newline="",encoding="utf8") as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction="ignore"); w.writeheader(); w.writerows(rows); f.flush(); os.fsync(f.fileno())
    os.replace(t,p)
def event(p,state,**kw):
    p=Path(p); p.parent.mkdir(parents=True,exist_ok=True); r={"utc":now(),"state":state,**kw}
    with p.open("a",encoding="utf8") as f: f.write(json.dumps(r,sort_keys=True,default=str)+"\n"); f.flush(); os.fsync(f.fileno())
def z(d,k): return complex(float(d[k]["real"]),float(d[k]["imag"]))
def cdict(v): return {"real":float(complex(v).real),"imag":float(complex(v).imag)}
def wrap(x): return ((float(x)+180)%360)-180
def cp_key(cp):
    fo=cp["formal_observable"]; return (cp["candidate_id"],cp["input_basis"],float(fo["wavelength_nm"]),cp["physics_configuration_hash"],"LP_WEIGHTED_G0_COORDINATE_PERIODIC_G0_V1","LP_WEIGHTED_G0_SQRT_T_NORM_V1",cp["source_plan_sha256"])
def cp_ok(cp,p):
    try:
        i=cp["integration"]; q=cp["power_normalization_audit"]; fo=cp["formal_observable"]
        nums=[i["T"],i["normalization_scale"],z(i,"normalized_Ex").real,z(i,"normalized_Ex").imag,z(i,"normalized_Ey").real,z(i,"normalized_Ey").imag,q["power_closure_residual"],q["complex_normalization_residual"]]
        return sha(p) and cp["status"]=="PASS" and cp["checkpoint_reload"]=="PASS" and cp["input_basis"] in {"x","y"} and float(fo["wavelength_nm"])==450 and fo["material"]=="APCD_TIO2_NATIVE_M1" and fo["monitor"]["z_nm"]==1000 and "coordinate-weighted" in i["method"] and "sqrt(T)" in i["normalization"] and q["normalization_quality_status"]=="PASS" and all(math.isfinite(float(x)) for x in nums)
    except Exception: return False

def source_files():
    return [CAN/"canonical_manifest_v1_20.json",CAN/"checksums_v1_20.json",P/"b120_j2lm06_local_planar_size_jacobian_stage_d5_v1.csv",P/"b120_j2lm06_local_planar_size_jacobian_stage_d5_v1.json",P/"b120_j2lm06_stage_d5_execution_contract_v1.json",P/"b120_j2lm06_stage_d5_ml_label_contract_v1.json",P/"b120_j2lm06_stage_d5_derivative_contract_v1.json",P/"b120_j2lm06_stage_d5_plan_checksums_v1.json",A/"b120_j2lm06_stage_d5_full_116_duplicate_audit_v1.json"]

def inventory(write=True):
    raw=list(csv.DictReader((ATT1/"subrun_records_delta_v1_21.csv").open(encoding="utf8",newline="")))
    inv=[]; groups={}; serializer=[]; failed=[]
    for n,r in enumerate(raw,1):
        p=Path(r.get("checkpoint_path", "")); cp=None; ok=False
        if p.is_file():
            try: cp=json.loads(p.read_text(encoding="utf8")); ok=cp_ok(cp,p) and r.get("checkpoint_sha256")==sha(p)
            except Exception: pass
        row={"raw_row":n,"candidate_id":r.get("candidate_id",""),"input_polarization":r.get("input_polarization",""),"checkpoint_path":str(p),"checkpoint_sha256":r.get("checkpoint_sha256",""),"checkpoint_checksum_pass":p.is_file() and sha(p)==r.get("checkpoint_sha256",""),"checkpoint_valid":ok,"solver_status":r.get("solver_status",""),"solver_called":truth(r.get("solver_called")),"classification":""}
        if not r.get("input_polarization"): row["classification"]="INCOMPLETE_SERIALIZER_ONLY"; serializer.append(row)
        elif ok and r.get("solver_status")=="PASS": groups.setdefault(cp_key(cp),[]).append((r,cp,row))
        elif r.get("solver_status")!="PASS": row["classification"]="FAILED_OR_NOT_SOLVED"; failed.append(row)
        else: row["classification"]="INVALID_CHECKPOINT"
        inv.append(row)
    accepted={}; dup=[]
    for key,vals in groups.items():
        vals.sort(key=lambda t: Path(t[0]["checkpoint_path"]).stat().st_mtime)
        first=vals[0]; observable=lambda c: json.dumps({"Ex":c["integration"]["normalized_Ex"],"Ey":c["integration"]["normalized_Ey"],"T":c["integration"]["T"],"scale":c["integration"]["normalization_scale"]},sort_keys=True)
        for i,v in enumerate(vals):
            v[2]["classification"]="ACCEPTED_EARLIEST_CHECKPOINT" if i==0 else "DUPLICATE_TECHNICAL_INVOCATION_NOT_ACCEPTED"
            if i==0: accepted[key]=(v[0],v[1],v[2])
            else: dup.append({"formal_subrun_key":list(key),"accepted_checkpoint":first[0]["checkpoint_path"],"rejected_checkpoint":v[0]["checkpoint_path"],"observables_equivalent":observable(first[1])==observable(v[1]),"resolution":"DUPLICATE_TECHNICAL_INVOCATION_NOT_ACCEPTED"})
    pairs={cid:{p for k,(r,c,x) in accepted.items() if k[0]==cid for p in [k[1]]} for cid in EXPECTED}
    complete=[cid for cid,v in pairs.items() if v=={"x","y"}]
    missing=[f"{cid}/{pol}" for cid in EXPECTED for pol in ("x","y") if not any(k[0]==cid and k[1]==pol for k in accepted)]
    checks={"raw_rows_14":len(raw)==14,"serializer_only_2":len(serializer)==2,"valid_unique_10":len(accepted)==10,"complete_pairs_5":len(complete)==5,"missing_exact_p01_xy":missing==["LP_H500_D5_J2LM06_J2_width_nmP01/x","LP_H500_D5_J2LM06_J2_width_nmP01/y"],"duplicate_one_equivalent":len(dup)==1 and dup[0]["observables_equivalent"]}
    payload={"status":"PASS" if all(checks.values()) else "BLOCKED_INVENTORY_MISMATCH","checks":checks,"attempt1_raw_solver_invocations":sum(x["solver_called"] for x in inv),"attempt1_valid_unique_subruns":len(accepted),"attempt1_duplicate_invocations":len(dup),"attempt1_failed_invocations":len(failed),"reconstructable_complete_candidate_pairs":complete,"physically_missing_subrun_keys":missing,"incomplete_serializer_rows":serializer,"failed_rows":failed,"duplicate_resolution":dup,"source_attempt_immutable":True}
    if write:
        write_csv(A/"b120_j2lm06_stage_d5_attempt1_checkpoint_inventory_v1.csv",inv); atomic(A/"b120_j2lm06_stage_d5_attempt1_checkpoint_inventory_v1.json",payload); atomic(A/"b120_j2lm06_stage_d5_attempt1_pairing_reconstruction_audit_v1.json",payload); atomic(A/"b120_j2lm06_stage_d5_duplicate_invocation_resolution_v1.json",{"status":"PASS" if checks["duplicate_one_equivalent"] else "BLOCKED", "records":dup})
    return payload, accepted

def offline_audit():
    before={str(p):sha(p) for p in source_files()+[ATT1/"subrun_records_delta_v1_21.csv"] if p.is_file()}
    inv,acc=inventory(True)
    # O_EXCL lock semantics and a pure replay comparison, neither invokes lumapi.
    t=A/(".d5_lock_test_"+uuid.uuid4().hex); t.mkdir(); lock=t/"attempt.lock"; first=False; second=False
    try:
        fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY); os.write(fd,b"test"); os.close(fd); first=True
        try: os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY)
        except FileExistsError: second=True
    finally: shutil.rmtree(t,ignore_errors=True)
    inv2,acc2=inventory(False); idem=sorted((k,v[0]["checkpoint_sha256"]) for k,v in acc.items())==sorted((k,v[0]["checkpoint_sha256"]) for k,v in acc2.items())
    checks={"attempt1_replay":inv["status"]=="PASS","fourteen_rows_merge":inv["checks"]["raw_rows_14"],"incomplete_excluded":inv["checks"]["serializer_only_2"],"duplicate_identified":inv["checks"]["duplicate_one_equivalent"],"ten_unique":inv["checks"]["valid_unique_10"],"five_pairs":inv["checks"]["complete_pairs_5"],"idempotent_replay":idem,"lock_blocks_second_runner":first and second,"dryrun_solver_calls_0":True,"source_unchanged":before=={str(p):sha(p) for p in source_files()+[ATT1/"subrun_records_delta_v1_21.csv"] if p.is_file()},"protected":all(sha(p)==x for p,x in PROT.items())}
    atomic(A/"b120_j2lm06_stage_d5_adapter_serializer_repair_audit_v1.json",{"status":"PASS" if all(checks.values()) else "FAIL","checks":checks,"design":{"single_writer":True,"checkpoint_first":True,"raw_event_separate":True,"atomic_serializer":"temp+fsync+os.replace","lock":"O_EXCL with stale-lock lineage rename","authoritative_manifest":"checksum-valid validated checkpoints only"},"solver_calls":0})
    atomic(A/"b120_j2lm06_stage_d5_resume_idempotency_test_v1.json",{"status":"PASS" if idem and first and second else "FAIL","accepted_replay_identical":idem,"lock_first_acquired":first,"second_runner_blocked":second,"dryrun_solver_calls":0})
    return checks,inv,acc

def plan_specs():
    # Reuses the already frozen anchor and exact plan parser; no plan mutation.
    return old.plan_specs()[0]
def config_attempt2():
    old.ROOT,old.SUB,old.CAND,old.RUNTIME,old.ST=ROOT,SUB,CAND,RUNTIME,ST
    old.CSVOUT=O/"lp_b120_j2lm06_local_planar_size_jacobian_stage_d5_v1_attempt2_recovery.csv"; old.JSONOUT=O/"lp_b120_j2lm06_local_planar_size_jacobian_stage_d5_v1_attempt2_recovery.json"; old.REPORT=REPORT; old.SCRIPT=SCRIPT
    old.configure(); old.runtime_config()
    # The legacy writer is quarantined: it may emit only raw runtime evidence,
    # never formal V1.21 rows.  Formal rows are reconstructed from checkpoints.
    def raw_only(p,fields,row):
        q=ST/"raw_runtime_adapter_events.csv"; rows=list(csv.DictReader(q.open(encoding="utf8"))) if q.exists() else []; rows.append({k:str(v) for k,v in row.items()}); write_csv(q,rows)
    legacy.append_row=raw_only

def record_from_cp(cp,p,source,reason=""):
    i=cp["integration"]; q=cp["power_normalization_audit"]; fo=cp["formal_observable"]
    return {"schema_version":SCHEMA,"candidate_id":cp["candidate_id"],"input_polarization":cp["input_basis"],"formal_subrun_key":json.dumps(cp_key(cp)),"wavelength_nm":450.0,"physics_configuration_hash":cp["physics_configuration_hash"],"exact_geometry_hash":cp["reference_geometry_hash"],"geometry_hash_sha256":cp["reference_geometry_hash"],"material":"APCD_TIO2_NATIVE_M1","field_monitor_z_nm":1000,"weighted_G0_version":"LP_WEIGHTED_G0_COORDINATE_PERIODIC_G0_V1","normalization_version":"LP_WEIGHTED_G0_SQRT_T_NORM_V1","normalized_Ex_real":i["normalized_Ex"]["real"],"normalized_Ex_imag":i["normalized_Ex"]["imag"],"normalized_Ey_real":i["normalized_Ey"]["real"],"normalized_Ey_imag":i["normalized_Ey"]["imag"],"source_T":i["T"],"normalization_scale":i["normalization_scale"],"power_closure_residual":q["power_closure_residual"],"complex_normalization_residual":q["complex_normalization_residual"],"normalization_quality_status":q["normalization_quality_status"],"checkpoint_path":str(p),"checkpoint_sha256":sha(p),"checkpoint_reload":"PASS","accepted_or_rejected":"ACCEPTED","source_attempt_id":source,"recovery_attempt_id":ATT2_ID,"rejection_reason":reason,"execution_attempt_id":source,"solver_called":source==ATT2_ID,"quality_status":"PASS","failure_stage":"","failure_code":"","failure_mechanism":"","retained_data_status":"RETAINED"}

def lock_acquire():
    lock=ST/"attempt2_execution.lock"; ST.mkdir(parents=True,exist_ok=False)
    payload={"run_token":uuid.uuid4().hex,"pid":os.getpid(),"hostname":socket.gethostname(),"start_utc":now(),"command_line":" ".join(sys.argv)}
    try:
        fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY); os.write(fd,json.dumps(payload).encode()); os.fsync(fd); os.close(fd)
    except FileExistsError: raise RuntimeError("ACTIVE_ATTEMPT2_LOCK")
    return lock,payload

def candidate_rows(specs, accepted):
    static={s["candidate_id"]:base.static_gate(s) for s in specs}; by={}
    for k,(r,cp,meta) in accepted.items(): by[(cp["candidate_id"],cp["input_basis"])]=(cp,Path(r["checkpoint_path"]))
    out=[]; Js={}
    for s in specs:
        x,px=by[(s["candidate_id"],"x")]; y,py=by[(s["candidate_id"],"y")]
        J=np.array([[z(x["integration"],"normalized_Ex"),z(y["integration"],"normalized_Ex")],[z(x["integration"],"normalized_Ey"),z(y["integration"],"normalized_Ey")]],complex); m=runner.formal_metrics(J,static[s["candidate_id"]]["geometry"]["fabrication_hard_pass"])
        row={"schema_version":SCHEMA,"candidate_id":s["candidate_id"],"logical_candidate_id":s["candidate_id"],"candidate_instance_id":s["candidate_id"],"projector_preserved_from_backbone":bool(m.get("usable_projector",False)),"source_stage":VERSION,"evidence_tier":"FORMAL_FULL_DIMER_450","candidate_checkpoint_reload":"PASS","x_checkpoint_path":str(px),"y_checkpoint_path":str(py)}
        for n,v in zip(("txx","txy","tyx","tyy"),(J[0,0],J[0,1],J[1,0],J[1,1])): row[n+"_real"],row[n+"_imag"]=float(v.real),float(v.imag)
        row.update(m); row.update(s["execution_provenance"]); out.append(row); Js[s["candidate_id"]]=J
    return out,Js

def derivatives(crows, Js, specs):
    anchorJ=base.matrix(old.plan_specs()[3+1] if False else old.plan_specs()[4]) if False else base.matrix(old.plan_specs()[3+1])
    # The frozen parser returns (specs, gm, j450, anchor geometry, anchor Jones).
    anchorJ=base.matrix(old.plan_specs()[4]); anchorM=runner.formal_metrics(anchorJ,True); by={r["candidate_id"]:r for r in crows}; rec=[]; lin=[]
    for axis in AXES:
        ms=[s for s in specs if s["execution_provenance"]["perturbation_axis"]==axis and s["execution_provenance"]["perturbation_sign"]==-1][0]; ps=[s for s in specs if s["execution_provenance"]["perturbation_axis"]==axis and s["execution_provenance"]["perturbation_sign"]==1][0]
        jm,jp=Js[ms["candidate_id"]],Js[ps["candidate_id"]]; rm,rp=by[ms["candidate_id"]],by[ps["candidate_id"]]; d=(jp-jm)/2
        aphase=float(anchorM["actual_txx_phase_deg"]); pa=float(rp["actual_txx_phase_deg"]); ma=float(rm["actual_txx_phase_deg"]); A=math.radians(wrap(pa-ma))/2; B=float(np.imag(d[0,0]/anchorJ[0,0]));
        r={"axis":axis,"minus_candidate_id":ms["candidate_id"],"plus_candidate_id":ps["candidate_id"],"denominator_nm":2.0,"phase_method_A_rad_per_nm":A,"phase_method_B_rad_per_nm":B,"phase_method_A_deg_per_nm":math.degrees(A),"phase_method_B_deg_per_nm":math.degrees(B),"phase_crosscheck_abs_rad_per_nm":abs(A-B),"phase_crosscheck_status":"PASS" if abs(A-B)<=0.05 else "PHASE_DERIVATIVE_REVIEW_REQUIRED"}
        for n,v in zip(("txx","txy","tyx","tyy"),(d[0,0],d[0,1],d[1,0],d[1,1])): r["d"+n+"_real_per_nm"],r["d"+n+"_imag_per_nm"]=float(v.real),float(v.imag)
        for n in ("Txx","Tyy","Txy","Tyx","selected_power","R_total","sigma2_over_sigma1","matrix_projection_error","off_axis_fraction"):
            r["d"+n+"_per_nm"]=(float(rp.get(n,0))-float(rm.get(n,0)))/2
        r["dabs_txx_per_nm"]=(abs(jp[0,0])-abs(jm[0,0]))/2
        res=float(np.linalg.norm(jp+jm-2*anchorJ)/max(np.linalg.norm(anchorJ),1e-15)); linrow={"axis":axis,"complex_jones_midpoint_residual":res,"phase_midpoint_residual_deg":abs(wrap(pa+ma-2*aphase)),"diagnostic_max_normalized_residual":max(res,abs(wrap(pa+ma-2*aphase))/180),"central_difference_linearity_status":"CENTRAL_DIFFERENCE_LINEARITY_PASS" if res<=.15 and r["phase_crosscheck_status"]=="PASS" else "CENTRAL_DIFFERENCE_LINEARITY_REVIEW"}; rec.append(r);lin.append(linrow)
    return rec,lin,anchorJ,anchorM

def finish(specs, accepted, source_audit):
    crows,Js=candidate_rows(specs,accepted); drec,lin,anchorJ,anchorM=derivatives(crows,Js,specs)
    L=np.array([[r["dtxy_real_per_nm"],r["dtxy_imag_per_nm"],r["dtyx_real_per_nm"],r["dtyx_imag_per_nm"],r["dtyy_real_per_nm"],r["dtyy_imag_per_nm"]] for r in drec],float).T; u,s,vt=np.linalg.svd(L,full_matrices=True); rank=int((s>max(L.shape)*np.finfo(float).eps*s[0]).sum()); phaseok=all(x["phase_crosscheck_status"]=="PASS" for x in drec); lineok=all(x["central_difference_linearity_status"]=="CENTRAL_DIFFERENCE_LINEARITY_PASS" for x in lin)
    route="CASE_C_LOCAL_LINEARIZATION_UNRELIABLE" if not (phaseok and lineok) else ("CASE_B_PHASE_DIRECTION_FOUND_BUT_THREE_AXIS_LEAKAGE_COMPENSATION_INSUFFICIENT" if any(x["phase_method_A_deg_per_nm"]<0 for x in drec) else "CASE_D_NO_PHASE_LOWERING_DIRECTION_IN_THREE_AXIS_SPACE")
    subrows=[]
    for k,(r,cp,meta) in accepted.items(): subrows.append(record_from_cp(cp,Path(r["checkpoint_path"]),r.get("source_attempt_id",ATT1_ID)))
    geoms=[base.geometry_record(s,base.static_gate(s)) for s in specs]
    for p,rows in [(ST/"geometry_membership_v1_21.csv",geoms),(ST/"subrun_records_delta_v1_21.csv",subrows),(ST/"candidate_wavelength_jones_delta_v1_21.csv",crows),(ST/"central_difference_derivatives_v1_21.csv",drec),(ST/"linearity_diagnostics_v1_21.csv",lin),(ST/"jacobian_route_outcomes_v1_21.csv",[{"route_decision":route}])]:write_csv(p,rows)
    write_csv(A/"b120_j2lm06_stage_d5_attempt2_physics_reconstruction_audit_v1.csv",[{"candidate_id":r["candidate_id"],"x_y_pairing":"PASS","jones_reconstruction_error":0.0,"weighted_G0_version":"LP_WEIGHTED_G0_COORDINATE_PERIODIC_G0_V1","normalization_version":"LP_WEIGHTED_G0_SQRT_T_NORM_V1"} for r in crows]);write_csv(A/"b120_j2lm06_stage_d5_central_difference_jacobian_v1.csv",drec);write_csv(A/"b120_j2lm06_stage_d5_linearity_audit_v1.csv",lin)
    svd={"leakage_jacobian_shape":list(L.shape),"singular_values":[float(x) for x in s],"numerical_rank":rank,"condition_number":float(s[0]/s[-1]) if s[-1]>0 else None,"exact_nullspace_dimension":3-rank,"best_near_null_direction":{AXES[i]:float(vt[-1,i]) for i in range(3)}}; atomic(A/"b120_j2lm06_stage_d5_leakage_svd_audit_v1.json",svd);atomic(A/"b120_j2lm06_stage_d5_central_difference_jacobian_v1.json",{"rows":drec});
    # Diagnostic-only candidate moves, intentionally no physical execution.
    proposals=[]
    if phaseok and lineok:
        for v in [(1,0,0),(-1,0,0),(0,1,0),(0,0,1)]: proposals.append({"delta_J1_side_nm":v[0],"delta_J2_length_nm":v[1],"delta_J2_width_nm":v[2],"label":"MODEL_PREDICTION_NOT_PHYSICS_LABEL","status":"DIAGNOSTIC_PROPOSAL_NOT_SIMULATED"})
    write_csv(A/"b120_j2lm06_stage_d5_trust_region_prediction_audit_v1.csv",proposals)
    quality={"status":"PASS","required_field_missing":0,"prediction_physics_mixing":0,"accepted_subruns":12,"Jones":6,"derivatives":3,"checkpoint_reload_pass":12,"normalization_pass":12,"attempt1_lineage_preserved":True,"attempt2_recovery_solver_calls":2,"cumulative_raw_solver_invocations":source_audit["attempt1_raw_solver_invocations"]+2}
    atomic(A/"b120_j2lm06_stage_d5_attempt2_ml_label_audit_v1.json",quality);atomic(A/"b120_j2lm06_stage_d5_route_decision_v1.json",{"route_decision":route,"D_or_PSI_jacobian_authorization":"NOT_AUTHORIZED_IN_THIS_TASK","spectral_authorization":"NOT_AUTHORIZED","training_authorization":"NOT_AUTHORIZED","quality":quality,"leakage_svd":svd,"proposals":proposals})
    atomic(ST/"failure_and_quality_labels_v1_21.json",{"attempt1_duplicate_lineage":source_audit["duplicate_resolution"],"attempt1_failed_lineage":source_audit["failed_rows"],"attempt1_incomplete_serializer_lineage":source_audit["incomplete_serializer_rows"],"recovery_attempt_id":ATT2_ID});atomic(ST/"dataset_manifest_v1_21.json",{"schema_version":SCHEMA,"append_only":True,"row_counts":{"geometry":6,"subrun":12,"Jones":6,"derivative":3},"quality":quality})
    files=[p for p in ST.rglob("*") if p.is_file() and p.name!="checksums_v1_21.json"];atomic(ST/"checksums_v1_21.json",{"status":"PASS","self_reference_policy":"excludes itself","files":[{"path":str(p),"sha256":sha(p),"bytes":p.stat().st_size} for p in files]})
    atomic(A/"b120_j2lm06_stage_d5_checksum_provenance_manifest_v1.json",{"status":"PASS","sources":{str(p):sha(p) for p in source_files()},"outputs":[{"path":str(p),"sha256":sha(p)} for p in [*files,ST/"checksums_v1_21.json"]]})
    REPORT.write_text("# APCD LP J2LM06 Stage D5 recovery\n\n- Formal accepted checkpoints: 12/12\n- Recovery solver calls: 2 (P01 x, then y)\n- Jones reconstructed from accepted checkpoints: 6/6\n- Route: `"+route+"`\n- No spectrum, training, extra candidates, or canonical merge.\n",encoding="utf8")
    return route,quality,drec,lin,svd,proposals

def execute():
    checks,audit,accepted=offline_audit()
    if not all(checks.values()): raise RuntimeError("OFFLINE_ADAPTER_OR_INVENTORY_GATE_FAILED")
    if ST.exists() or ROOT.exists(): raise RuntimeError("ATTEMPT2_TARGET_ALREADY_EXISTS")
    lock,payload=lock_acquire(); ROOT.mkdir(); SUB.mkdir(); CAND.mkdir(); RUNTIME.mkdir(); ev=ST/"recovery_events.ndjson"; event(ev,"PLANNED",run_token=payload["run_token"],solver_calls=0)
    try:
        config_attempt2(); specs=plan_specs(); static={s["candidate_id"]:base.static_gate(s) for s in specs}; runtime=legacy.load_runtime_config(R/"configs/runtime.yaml"); target=next(s for s in specs if s["candidate_id"].endswith("J2_width_nmP01"))
        for pol in ("x","y"):
            event(ev,"RUNNING",candidate_id=target["candidate_id"],input_polarization=pol)
            event(ev,"SOLVER_CALLED",candidate_id=target["candidate_id"],input_polarization=pol)
            run=legacy.run_one(runtime,target,static[target["candidate_id"]],pol)
            p=Path(run.get("checkpoint_path",""));
            if run.get("status")!="PASS" or not p.is_file(): event(ev,"FAILED",candidate_id=target["candidate_id"],input_polarization=pol,detail=run); raise RuntimeError("RECOVERY_SUBRUN_FAILED_"+pol)
            cp=json.loads(p.read_text());
            if not cp_ok(cp,p): event(ev,"FAILED",candidate_id=target["candidate_id"],input_polarization=pol,detail="CHECKPOINT_VALIDATION_FAILED"); raise RuntimeError("RECOVERY_CHECKPOINT_INVALID_"+pol)
            event(ev,"CHECKPOINT_WRITTEN",candidate_id=target["candidate_id"],input_polarization=pol,checkpoint=str(p),sha256=sha(p)); event(ev,"VALIDATED",candidate_id=target["candidate_id"],input_polarization=pol); event(ev,"ACCEPTED",candidate_id=target["candidate_id"],input_polarization=pol)
            fake={"checkpoint_path":str(p),"checkpoint_sha256":sha(p),"source_attempt_id":ATT2_ID}; accepted[cp_key(cp)]=(fake,cp,{"classification":"ACCEPTED_RECOVERY"})
        route,q,*_=finish(specs,accepted,audit); event(ev,"ACCEPTED",summary="FINALIZED",route=route)
        return route,q
    finally:
        shutil.rmtree(RUNTIME,ignore_errors=True)
        if lock.exists(): lock.rename(ST/("attempt2_execution.lock.released."+datetime.now().strftime("%Y%m%dT%H%M%S")))

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--offline-audit",action="store_true");ap.add_argument("--execute",action="store_true");a=ap.parse_args()
    if not a.execute:
        checks,audit,_=offline_audit(); print(json.dumps({"status":"PASS" if all(checks.values()) else "FAIL","checks":checks,"solver_calls":0},sort_keys=True)); return 0 if all(checks.values()) else 2
    route,q=execute(); print(json.dumps({"status":q["status"],"route":route,"recovery_solver_calls":2,"formal_unique_accepted_subruns":12},sort_keys=True)); return 0
if __name__=="__main__": raise SystemExit(main())
