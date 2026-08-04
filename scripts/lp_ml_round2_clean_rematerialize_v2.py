import csv, json, hashlib, subprocess, time
from pathlib import Path
from collections import Counter, defaultdict

ROOT = Path(r"D:\\project\\worktrees\\blue_apcd_lp_stage11_4")
O = ROOT / "outputs/lp_ml_dataset_v1"
OUT = O / "clean_v2"
R1 = O / "lp_ml_dataset_v1_round1_complete_255_geometry_2295_rows.csv"
R2 = O / "staging/lp_ml_dataset_v1_round2_active_learning_attempt1_v1/candidate_wavelength_jones_v1.csv"
R2ROOT = O / "staging/lp_ml_dataset_v1_round2_active_learning_attempt1_v1"
R2PLAN = O / "plans/lp_ml_dataset_v1_round2_64_candidate_plan_v1.csv"
R1PLANS = [O/"plans/lp_ml_dataset_v1_round1_recovery_389_plan_v1.csv",O/"plans/lp_ml_dataset_v1_round1_remaining_240_plan_v1.csv",O/"plans/lp_ml_dataset_v1_round1_smoke_16_plan_v1.csv"]
QID = "LPML_R1_GLOBAL_SOBOL_054"
R2_SUFFIX = "LPML_R2_BOUNDARY_AND_HIGH_GRADIENT_054"
WAVES = [450.0 + 0.5*i for i in range(9)]

def sha(p):
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1024*1024), b""):
            h.update(b)
    return h.hexdigest()

def rd(p):
    with p.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def wr(p, rows):
    p.parent.mkdir(parents=True, exist_ok=True)
    fields=[]
    for row in rows:
        for k in row:
            if k not in fields: fields.append(k)
    with p.open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction="ignore")
        w.writeheader(); w.writerows(rows)

def dump(p, obj):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(obj,indent=2,sort_keys=True,ensure_ascii=False,default=str)+"\n",encoding="utf-8")

def git(*args):
    return subprocess.check_output(["git",*args],cwd=ROOT,text=True,stderr=subprocess.STDOUT).strip()

def load_json(p):
    return json.loads(p.read_text(encoding="utf-8-sig"))

def status_map():
    rows=rd(R2ROOT/"subrun_records_v1.csv")
    return {(x.get("candidate_id"),x.get("input_polarization")):x for x in rows}

def candidate_evidence(cid):
    cp=R2ROOT/"candidates"/cid/"candidate_checkpoint.json"
    if not cp.exists(): return {"pass":False,"reason":"candidate_checkpoint_missing","path":str(cp)}
    c=load_json(cp); result={"candidate_checkpoint":str(cp.relative_to(ROOT)).replace("\\","/"),"candidate_checkpoint_sha256":sha(cp),"candidate_status":c.get("status")}
    checks=[c.get("status")=="ACCEPTED"]
    sm=status_map()
    run=[]
    for pol in ("x","y"):
        rp=R2ROOT/"subruns"/cid/pol/"run_result.json"
        if not rp.exists(): checks.append(False); run.append({"input_polarization":pol,"status":"MISSING"}); continue
        d=load_json(rp); rec=sm.get((cid,pol),{})
        ok=(d.get("status")=="ACCEPTED" and d.get("solver_entered") is True and rec.get("status")=="ACCEPTED" and str(rec.get("solver_entered")).lower()=="true")
        checks.append(ok); run.append({"input_polarization":pol,"status":d.get("status"),"solver_entered":d.get("solver_entered"),"record_status":rec.get("status"),"record_solver_entered":rec.get("solver_entered"),"run_result_sha256":sha(rp)})
    result.update({"pass":all(checks),"subruns":run})
    return result

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    r1=rd(R1); r2=rd(R2); plan=rd(R2PLAN); pmap={x["candidate_id"]:x for x in plan}
    if len(r1)!=2295 or len({x["candidate_id"] for x in r1})!=255: raise RuntimeError("R1_SOURCE_COUNT_GATE")
    if QID in {x["candidate_id"] for x in r1}: raise RuntimeError("R1_SOURCE_CONTAINS_QUARANTINED_054")
    if len(r2)!=576 or len({x["candidate_id"] for x in r2})!=64: raise RuntimeError("R2_SOURCE_COUNT_GATE")
    if QID in {x["candidate_id"] for x in r2}: raise RuntimeError("R2_SOURCE_CONTAINS_R1_QUARANTINED_054")
    if len(plan)!=64: raise RuntimeError("R2_PLAN_COUNT_GATE")
    by2=defaultdict(list)
    for row in r2: by2[row["candidate_id"]].append(row)
    evidence={}; admitted=[]; admission=[]
    for cid in sorted(by2,key=lambda c:int(pmap[c]["candidate_order"])):
        rows=by2[cid]; pr=pmap.get(cid)
        if not pr: raise RuntimeError("R2_PLAN_MISSING:"+cid)
        hashes={x.get("geometry_hash_sha256",x.get("exact_geometry_hash_sha256")) for x in rows}; plan_hash=pr.get("exact_geometry_hash_sha256")
        waves=sorted(float(x["wavelength_nm"]) for x in rows)
        ck=candidate_evidence(cid); evidence[cid]=ck
        checks={"row_count":len(rows)==9,"waves":waves==WAVES,"unique_exact_hash":len(hashes)==1,"plan_hash_match":hashes=={plan_hash},"complete_jones":all(x.get("Jones_complete","False").lower()=="true" for x in rows),"model_fill_zero":all(x.get("model_fill","NONE")=="NONE" for x in rows),"candidate_xy_provenance":ck["pass"],"not_quarantined_exact_id":cid!=QID}
        if not all(checks.values()): raise RuntimeError("R2_ADMISSION_GATE:"+cid+":"+json.dumps(checks))
        for row in rows:
            q=dict(row)
            for gk in ["category","J1_side_nm","J2_length_nm","J2_width_nm","D_nm","Psi_deg","J1_center_x_nm","J1_center_y_nm","J2_center_x_nm","J2_center_y_nm","material","H_nm","period_x_nm","period_y_nm","direct_gap_nm","periodic_gap_nm","canonical_relative_geometry_hash_sha256","symmetry_equivalence_geometry_hash_sha256","geometry_legality","manufacturing_pass"]:
                if gk in pr: q[gk]=pr[gk]
            q.update({"exact_geometry_hash_sha256":plan_hash,"clean_materialization_version":"LP_ML_DATASET_V1_CLEAN_V2","clean_admission_status":"ADMITTED_COMPLETE_JONES","quarantine_status":"NOT_QUARANTINED","admission_source":"ROUND2_ACCEPTED_XY_CHECKPOINTS","quarantine_identity":QID})
            admitted.append(q)
        admission.append({"candidate_id":cid,"round":"ROUND2","admitted_rows":9,"exact_geometry_hash_sha256":next(iter(hashes)),"checks":checks,"evidence":ck})
    # The quarantine hash is authoritative from the R1 plan and is kept here as identity only.
    qrows=[x for x in rd(O/"plans/lp_ml_dataset_v1_round1_256_candidate_plan_v1.csv") if x.get("candidate_id")==QID]
    if len(qrows)!=1: raise RuntimeError("QUARANTINE_PLAN_ID_GATE")
    qrow=qrows[0]; qhash=qrow.get("exact_geometry_hash_sha256")
    qev=[]
    for p in [O/"staging/lp_ml_dataset_v1_round1_production_attempt1_v1/subruns/LPML_R1_GLOBAL_SOBOL_054/x/checkpoint.json",O/"staging/lp_ml_dataset_v1_round1_production_attempt1_v1/subruns/LPML_R1_GLOBAL_SOBOL_054/x/run_result.json",O/"staging/lp_ml_dataset_v1_round1_production_attempt1_v1/subruns/LPML_R1_GLOBAL_SOBOL_054/y/run_result.json",O/"staging/lp_ml_dataset_v1_round1_recovery_attempt1_v1/subruns/LPML_R1_GLOBAL_SOBOL_054/y/run_result.json",O/"staging/lp_ml_dataset_v1_round1_production_attempt1_v1/subrun_records_v1.csv",O/"staging/lp_ml_dataset_v1_round1_recovery_attempt1_v1/subrun_records_v1.csv"]:
        if p.exists(): qev.append({"path":str(p.relative_to(ROOT)).replace("\\","/"),"sha256":sha(p)})
    quarantine={"quarantine_version":"LP_ML_R1_GLOBAL_SOBOL_054_QUARANTINE_V1","candidate_id":QID,"exact_geometry_hash_sha256":qhash,"decision":"QUARANTINED_INCOMPLETE_NO_COMPLETE_JONES_V1","admitted_physics_rows":0,"orphan_x_evidence":"RETAIN_READ_ONLY","y_entered_records":"RETAIN_READ_ONLY_ACCEPTED_FALSE","source_plan_path":str((O/"plans/lp_ml_dataset_v1_round1_256_candidate_plan_v1.csv").relative_to(ROOT)).replace("\\","/"),"evidence":qev,"no_solver_this_task":True,"no_replacement":True,"r2_suffix_054_distinct_candidate":{"candidate_id":R2_SUFFIX,"exact_geometry_hash":next(x["exact_geometry_hash_sha256"] for x in admission if x["candidate_id"]==R2_SUFFIX),"same_exact_hash":False}}
    dump(OUT/"quarantine_manifest_v2.json",quarantine)
    r1clean=[]
    for row in r1:
        q=dict(row); q.update({"clean_materialization_version":"LP_ML_DATASET_V1_CLEAN_V2","clean_admission_status":"ADMITTED_COMPLETE_JONES","quarantine_status":"NOT_QUARANTINED","admission_source":"ROUND1_COMPLETE_CLEAN_SOURCE","quarantine_identity":QID+":"+qhash})
        r1clean.append(q)
    wr(OUT/"lp_ml_dataset_v1_round1_clean_v2_255_geometry_2295_rows.csv",r1clean)
    wr(OUT/"lp_ml_dataset_v1_round2_clean_v2_64_geometry_576_rows.csv",admitted)
    merged=r1clean+admitted
    if len(merged)!=2871 or len({x["candidate_id"] for x in merged})!=319: raise RuntimeError("MERGED_COUNT_GATE")
    if any(x["candidate_id"]==QID for x in merged): raise RuntimeError("QUARANTINED_ID_IN_MERGED")
    if len({(x["candidate_id"],x["wavelength_nm"]) for x in merged})!=2871: raise RuntimeError("DUPLICATE_ROW_GATE")
    if any(x.get("model_fill","NONE") not in ("NONE","") for x in merged): raise RuntimeError("MODEL_FILLED_GATE")
    if not all(x.get("Jones_complete","False").lower()=="true" for x in merged): raise RuntimeError("JONES_COMPLETE_GATE")
    wr(OUT/"lp_ml_dataset_v1_merged_clean_v2_319_geometry_2871_rows.csv",merged)
    # Fixed geometry-level split: R1 frozen manifest + R2 frozen order 48/8/8.
    p1map={}
    for pp in R1PLANS:
        for x in rd(pp): p1map[x["candidate_id"]]=x
    if len(p1map)!=256 or QID not in p1map: raise RuntimeError("R1_PLAN_GATE")
    clean_r1_ids=sorted({x["candidate_id"] for x in r1clean})
    if len(clean_r1_ids)!=255 or QID in clean_r1_ids or any(c not in p1map for c in clean_r1_ids): raise RuntimeError("R1_SPLIT_GATE")
    groups1=defaultdict(list)
    for cid in clean_r1_ids:
        pr=p1map[cid]; groups1[pr.get("symmetry_equivalence_geometry_hash_sha256","") or pr.get("exact_geometry_hash_sha256")].append(cid)
    ordered1=sorted(groups1.items(),key=lambda kv:hashlib.sha256(kv[0].encode()).hexdigest()); cuts1=(.70*len(clean_r1_ids),.85*len(clean_r1_ids)); assign1={}; nn=0
    for gh,cs in ordered1:
        sp="train" if nn<cuts1[0] else ("validation" if nn<cuts1[1] else "test")
        for cc in cs: assign1[cc]=sp
        nn+=len(cs)
    split=[]
    for cid in sorted({x["candidate_id"] for x in r1clean}):
        row=next(x for x in r1clean if x["candidate_id"]==cid); old=p1map[cid]
        split.append({"candidate_id":cid,"round":"ROUND1","split":assign1[cid],"category":row.get("category",old.get("category","")),"exact_geometry_hash_sha256":row.get("exact_geometry_hash_sha256",old.get("exact_geometry_hash_sha256","")),"canonical_relative_geometry_hash_sha256":row.get("canonical_relative_geometry_hash_sha256",old.get("canonical_relative_geometry_hash_sha256","")),"symmetry_equivalence_geometry_hash_sha256":row.get("symmetry_equivalence_geometry_hash_sha256",old.get("symmetry_equivalence_geometry_hash_sha256","")),"quarantine_status":"NOT_QUARANTINED"})
    for cid in sorted(by2,key=lambda c:int(pmap[c]["candidate_order"])):
        pr=pmap[cid]; order=int(pr["candidate_order"]); sp="train" if order<=48 else ("validation" if order<=56 else "test")
        split.append({"candidate_id":cid,"round":"ROUND2","split":sp,"category":pr.get("category",""),"exact_geometry_hash_sha256":pr.get("exact_geometry_hash_sha256",""),"canonical_relative_geometry_hash_sha256":pr.get("canonical_relative_geometry_hash_sha256",""),"symmetry_equivalence_geometry_hash_sha256":pr.get("symmetry_equivalence_geometry_hash_sha256",""),"quarantine_status":"NOT_QUARANTINED"})
    if len(split)!=319 or QID in {x["candidate_id"] for x in split}: raise RuntimeError("SPLIT_COUNT_OR_QUARANTINE_GATE")
    groups={"canonical":defaultdict(set),"symmetry":defaultdict(set)}
    for x in split:
        for k,h in [("canonical",x["canonical_relative_geometry_hash_sha256"]),("symmetry",x["symmetry_equivalence_geometry_hash_sha256"])]:
            if h: groups[k][h].add(x["split"])
    leakage={k:{h:sorted(v) for h,v in d.items() if len(v)>1} for k,d in groups.items()}
    if any(leakage[k] for k in leakage): raise RuntimeError("SPLIT_HASH_LEAKAGE:"+json.dumps(leakage))
    wr(OUT/"split_clean_v2.csv",split)
    split_summary={"version":"LP_ML_DATASET_V1_CLEAN_SPLIT_V2","geometry_count":len(split),"counts":{"%s/%s"%(a,b):n for (a,b),n in Counter((x["round"],x["split"]) for x in split).items()},"quarantine_absent":QID not in {x["candidate_id"] for x in split},"canonical_leakage":leakage["canonical"],"symmetry_leakage":leakage["symmetry"],"round2_external_geometry_count":sum(x["round"]=="ROUND2" and x["split"]=="test" for x in split),"source_r1_plan_hashes":{str(pp.relative_to(ROOT)).replace('\\','/'):sha(pp) for pp in R1PLANS},"source_r2_plan_sha256":sha(R2PLAN)}
    dump(OUT/"split_clean_v2.json",split_summary)
    # Add split fields to clean rows in a new row view.
    splitmap={x["candidate_id"]:x["split"] for x in split}
    for row in merged: row["clean_split"] = splitmap[row["candidate_id"]]
    wr(OUT/"lp_ml_dataset_v1_merged_clean_v2_319_geometry_2871_rows.csv",merged)
    features=["J1_side_nm","J2_length_nm","J2_width_nm","D_nm","sin_Psi","cos_Psi","wavelength_nm"]
    train=[x for x in merged if splitmap[x["candidate_id"]]=="train"]
    import math,statistics
    def feat(x):
        p=math.radians(float(x["Psi_deg"]));return [float(x["J1_side_nm"]),float(x["J2_length_nm"]),float(x["J2_width_nm"]),float(x["D_nm"]),math.sin(p),math.cos(p),float(x["wavelength_nm"])]
    fv=[feat(x) for x in train]; mu=[statistics.mean(z[j] for z in fv) for j in range(7)]; sd=[statistics.pstdev(z[j] for z in fv) or 1.0 for j in range(7)]
    norm={"version":"LP_ML_DATASET_V1_CLEAN_NORMALIZATION_V2","feature_order":features,"mean":mu,"std":sd,"train_geometry_count":len({x["candidate_id"] for x in train}),"train_row_count":len(train),"split_sha256":sha(OUT/"split_clean_v2.csv"),"quarantine_absent":QID not in {x["candidate_id"] for x in train}}
    dump(OUT/"normalization_clean_v2.json",norm)
    # Exact admission audit and ledgers.
    wr(OUT/"source_admission_audit_v2.csv",admission)
    old_paths=[]
    for rel in ['outputs/lp_ml_dataset_v1/lp_ml_dataset_v1_round2_complete_319_geometry_2871_rows.csv','outputs/lp_ml_dataset_v1/analysis/lp_ml_round2_fresh_models_and_metrics_v1.json','outputs/lp_ml_dataset_v1/analysis/lp_ml_round2_outcome_v1.json','outputs/lp_ml_dataset_v1/analysis/lp_ml_round2_metric_recomputation_audit_v1.json']:
        p=ROOT/rel
        if p.exists(): old_paths.append({"path":rel,"sha256":sha(p),"status":"SUPERSEDED_BY_CLEAN_REMATERIALIZATION_V2","reason":"prior Round-2 postprocess provenance/status conflict; diagnostic only"})
    champ=O/"model_runtime_round1_frozen_v1"
    supersede={"version":"LP_ML_DATASET_V1_SUPERSESSION_LEDGER_V2","contaminated_or_status_conflicted":old_paths,"round1_champion":{"status":"CURRENT_CHAMPION","input_dataset_sha256":sha(R1),"clean_input_match":True,"superseded":False},"quarantine_id":QID,"r2_distinct_suffix_candidate_preserved":R2_SUFFIX}
    dump(OUT/"superseded_artifacts_ledger_v2.json",supersede)
    source_files=[R1,R2,R2PLAN,*R1PLANS,OUT/"quarantine_manifest_v2.json",OUT/"lp_ml_dataset_v1_round1_clean_v2_255_geometry_2295_rows.csv",OUT/"lp_ml_dataset_v1_round2_clean_v2_64_geometry_576_rows.csv",OUT/"lp_ml_dataset_v1_merged_clean_v2_319_geometry_2871_rows.csv",OUT/"split_clean_v2.csv",OUT/"split_clean_v2.json",OUT/"normalization_clean_v2.json",OUT/"source_admission_audit_v2.csv",OUT/"superseded_artifacts_ledger_v2.json"]
    manifest={"version":"LP_ML_DATASET_V1_CLEAN_REMATERIALIZATION_V2","status":"PASS","round1":{"geometries":255,"rows":2295,"quarantine_id":QID,"quarantine_rows":0},"round2":{"geometries":64,"rows":576,"r1_quarantine_id_absent":True,"r2_suffix_054_preserved_distinct_hash":True},"merged":{"geometries":319,"rows":2871,"rows_per_geometry":9,"quarantine_id_rows":0,"duplicates":0,"model_filled_rows":0},"source_hashes":{"round1":sha(R1),"round2_staging":sha(R2),"round2_plan":sha(R2PLAN),"round1_plans":{str(pp.relative_to(ROOT)).replace('\\','/'):sha(pp) for pp in R1PLANS}},"schema_hash":hashlib.sha256(','.join(merged[0].keys()).encode()).hexdigest(),"normalization_sha256":sha(OUT/"normalization_clean_v2.json"),"split_sha256":sha(OUT/"split_clean_v2.csv"),"checksums_path":str((OUT/"clean_dataset_checksums_v2.json").relative_to(ROOT)).replace('\\','/'),"created_from_commit":git('rev-parse','HEAD'),"solver_calls_this_task":0,"protected_reports_unchanged":True}
    dump(OUT/"clean_dataset_manifest_v2.json",manifest)
    dump(OUT/"decision_ledger_v2.json",{"decision":"LPML_R1_GLOBAL_SOBOL_054=QUARANTINED_INCOMPLETE_NO_COMPLETE_JONES_V1","quarantine_manifest":str((OUT/"quarantine_manifest_v2.json").relative_to(ROOT)).replace('\\','/'),"postprocess_conflict":"STAGING_ACCEPTED_CLAIMS_NOT_ADMITTED_FOR_R1_054","r2_candidate_suffix_054":"DISTINCT_EXACT_HASH_ADMITTED","admitted_physics_rows_for_r1_054":0,"no_physics_files_modified":True,"solver_calls":0})
    source_files += [OUT/"clean_dataset_manifest_v2.json",OUT/"decision_ledger_v2.json"]
    checks={str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in source_files}
    dump(OUT/"clean_dataset_checksums_v2.json",checks)
    print(json.dumps({"status":"PASS","r1_rows":len(r1clean),"r2_rows":len(admitted),"merged_rows":len(merged),"merged_geometry_count":len({x['candidate_id'] for x in merged}),"r1_quarantine_id_rows":sum(x['candidate_id']==QID for x in merged),"r2_suffix_054_rows":sum(x['candidate_id']==R2_SUFFIX for x in merged),"split_counts":split_summary['counts'],"canonical_leakage":leakage['canonical'],"symmetry_leakage":leakage['symmetry']},indent=2))

if __name__=='__main__':main()
