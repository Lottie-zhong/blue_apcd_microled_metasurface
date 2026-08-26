from __future__ import annotations
import copy, datetime as dt, hashlib, importlib.util, inspect, json, math, sys
from pathlib import Path
import numpy as np

ROOT=Path(r"D:/project/worktrees/blue_apcd_paper_a_lp_cp_broadband_v1")
SELECTION=ROOT/"paper_a_broadband/reports/lp_anisotropy_feasible_space_v2_balanced_selection/balanced_selected_candidates.json"
PREPARED=ROOT/"paper_a_broadband/reports/lp_anisotropy_feasible_space_v2_balanced_selection/prepared_fsp_provenance.json"
BASE_RUNNER=ROOT/"paper_a_broadband/scripts/lp_new_geometry_search_runner_v1.py"
PARENT_FSP=ROOT/"paper_a_broadband/runtime/reusable_fsp/lp/P1_LP_H1C1B_V2_009_Px_attempt_006_pre.fsp"
CURRENT_RUNTIME=ROOT/"paper_a_broadband/runtime/search_anisotropy_feasible_space_v2_balanced"
RECON_RUNTIME=ROOT/"paper_a_broadband/runtime/reconciliation_bf01_bf04_v1_rerun"
REPORT=ROOT/"paper_a_broadband/reports/bf01_bf04_provenance_reconciliation_v1"
AUTHORITY=ROOT/"paper_a_broadband/authority/paper_a_bf01_bf04_prepared_fsp_authority_v1.json"
MATERIAL="APCD_TIO2_NATIVE_M1"; SOURCE_START_NM=430.0; SOURCE_STOP_NM=470.0
CASES=[f"BF0{i}_{pol}" for i in range(1,5) for pol in ("x","y")]
sys.path.insert(0,r"N:/Program Files/ANSYS Inc/v251/Lumerical/api/python")

def now(): return dt.datetime.now(dt.timezone.utc).isoformat()
def sha_file(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def canon(v): return json.dumps(v,sort_keys=True,ensure_ascii=False,separators=(",",":"),default=str).encode()
def sha_obj(v): return hashlib.sha256(canon(v)).hexdigest()
def write_json(p,v): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(v,indent=2,ensure_ascii=False,default=str)+"\n",encoding="utf-8")
def load_module(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None: raise RuntimeError("MODULE_LOAD_FAILED")
    m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
def jsonable(v):
    if isinstance(v,np.generic): return v.item()
    if isinstance(v,np.ndarray): return v.tolist()
    if isinstance(v,(list,tuple)): return [jsonable(x) for x in v]
    if isinstance(v,dict): return {str(k):jsonable(x) for k,x in v.items()}
    if isinstance(v,(str,int,float,bool)) or v is None: return v
    return str(v)
LENGTH_KEYS={"x","y","z","x span","y span","z span","x min","x max","y min","y max","z min","z max"}
def safe_get(f,obj,key):
    try:
        v=jsonable(f.getnamed(obj,key))
        if isinstance(v,(int,float)) and math.isfinite(float(v)):
            if key in LENGTH_KEYS: return float(v)*1e9
            if key=="simulation time": return float(v)*1e12
            return float(v)
        return v
    except Exception as e: return {"__readback_error__":f"{type(e).__name__}:{e}"}
def read_object(f,n,keys): return {k:safe_get(f,n,k) for k in keys}
def read_monitor(f,n,keys):
    base=[k for k in keys if k!="surface normal"]
    out=read_object(f,n,base)
    normal=safe_get(f,n,"surface normal")
    if isinstance(normal,dict) and "__readback_error__" in normal:
        monitor_type=out.get("monitor type")
        if monitor_type=="2D Z-normal":
            out["surface normal"]="Z"
            out["surface normal source"]="derived_from_monitor_type"
        else:
            out["surface normal"]=normal
            out["surface normal source"]="unresolved"
    else:
        out["surface normal"]=normal
        out["surface normal source"]="explicit_property"
    return out
def read_names(f):
    for method in ("getobjectlist","getall"):
        try: return jsonable(getattr(f,method)())
        except Exception: pass
    return {"__readback_error__":"OBJECT_LIST_API_UNAVAILABLE"}
def has_error(v):
    if isinstance(v,dict): return any(k=="__readback_error__" or has_error(x) for k,x in v.items())
    if isinstance(v,list): return any(has_error(x) for x in v)
    return False
def read_fsp(path,case_id,pol):
    import lumapi
    f=lumapi.FDTD(hide=True)
    try:
        f.load(str(path))
        pk=["x","y","z","x span","y span","z span","rotation 1","material"]
        sk=["source type","injection axis","direction","polarization angle","wavelength start","wavelength stop","x","y","z","x span","amplitude","phase","use global source settings"]
        mk=["monitor type","x","y","z","x span","y span","z span","surface normal","frequency points","use source limits","use wavelength spacing","override global monitor settings"]
        fk=["simulation time","mesh accuracy","dimension","x","y","z","x span","y span","z span","x min bc","x max bc","y min bc","y max bc","z min bc","z max bc","background index","pml layers"]
        objs={"pillar_1":read_object(f,"pillar_1",pk),"pillar_2":read_object(f,"pillar_2",pk)}
        source=read_object(f,"source",sk); mons={"T":read_monitor(f,"T",mk),"field_monitor":read_monitor(f,"field_monitor",mk)}; solver=read_object(f,"FDTD",fk)
        p1,p2=objs["pillar_1"],objs["pillar_2"]
        geom={"L1_nm":p1.get("x span"),"W1_nm":p1.get("y span"),"L2_nm":p2.get("x span"),"W2_nm":p2.get("y span"),"theta1_deg":p1.get("rotation 1"),"theta2_deg":p2.get("rotation 1"),"D_nm":abs(float(p1["y"])-float(p2["y"])) if isinstance(p1.get("y"),(int,float)) and isinstance(p2.get("y"),(int,float)) else None,"centers_nm":[[p1.get("x"),p1.get("y")],[p2.get("x"),p2.get("y")]],"H_nm":p1.get("z span"),"Px_nm":solver.get("x span"),"Py_nm":solver.get("y span"),"materials":[p1.get("material"),p2.get("material")]}
        sem={"geometry":geom,"objects":objs,"object_names":read_names(f),"source":source,"monitors":mons,"solver":solver}
        return {"case_id":case_id,"polarization":pol,"path":str(path),"sha256":sha_file(path),"size_bytes":path.stat().st_size,"last_write_utc":dt.datetime.fromtimestamp(path.stat().st_mtime,dt.timezone.utc).isoformat(),"semantic":sem,"readback_complete":not has_error(sem)}
    finally: f.close()
def expected_geometry(r):
    return {"L1_nm":float(r["L1_nm"]),"W1_nm":float(r["W1_nm"]),"L2_nm":float(r["L2_nm"]),"W2_nm":float(r["W2_nm"]),"theta1_deg":float(r["theta1_deg"]),"theta2_deg":float(r["theta2_deg"]),"D_nm":float(r["D_nm"]),"centers_nm":[[float(r["j1_center_x_nm"]),float(r["j1_center_y_nm"])],[float(r["j2_center_x_nm"]),float(r["j2_center_y_nm"])]],"H_nm":float(r["height_nm"]),"Px_nm":float(r["period_x_nm"]),"Py_nm":float(r["period_y_nm"]),"materials":[MATERIAL,MATERIAL]}
def expected_objects(r):
    h=float(r["height_nm"])
    return {"pillar_1":{"x":float(r["j1_center_x_nm"]),"y":float(r["j1_center_y_nm"]),"z":h/2.0,"x span":float(r["L1_nm"]),"y span":float(r["W1_nm"]),"z span":h,"rotation 1":float(r["theta1_deg"]),"material":MATERIAL},"pillar_2":{"x":float(r["j2_center_x_nm"]),"y":float(r["j2_center_y_nm"]),"z":h/2.0,"x span":float(r["L2_nm"]),"y span":float(r["W2_nm"]),"z span":h,"rotation 1":float(r["theta2_deg"]),"material":MATERIAL}}
def expected_case(r,pol,t):
    e=copy.deepcopy(t); e["geometry"]=expected_geometry(r); e["objects"]=expected_objects(r); e["source"]["polarization angle"]=0.0 if pol=="x" else 90.0; return e
def tol(p):
    if p.endswith("_nm") or "polarization angle" in p or "rotation" in p or "simulation time" in p: return 1e-6
    return 1e-9
def classify(a,b,p=""):
    if isinstance(a,dict) and isinstance(b,dict): return {k:classify(a.get(k),b.get(k),f"{p}.{k}".strip(".")) for k in sorted(set(a)|set(b))}
    if isinstance(a,list) and isinstance(b,list):
        if len(a)!=len(b): return {"classification":"DIFFERENT","a":a,"b":b}
        return [classify(x,y,f"{p}[{i}]") for i,(x,y) in enumerate(zip(a,b))]
    if isinstance(a,(int,float)) and isinstance(b,(int,float)):
        if float(a)==float(b): return {"classification":"IDENTICAL","a":a,"b":b}
        if abs(float(a)-float(b))<=tol(p): return {"classification":"NUMERICALLY_EQUIVALENT_WITH_EXPLICIT_TOLERANCE","a":a,"b":b,"tolerance":tol(p)}
        return {"classification":"DIFFERENT","a":a,"b":b}
    return {"classification":"IDENTICAL","a":a,"b":b} if a==b else {"classification":"DIFFERENT","a":a,"b":b}
def statuses(v):
    if isinstance(v,dict):
        out=[v["classification"]] if "classification" in v else []
        for x in v.values(): out.extend(statuses(x))
        return out
    if isinstance(v,list):
        out=[]
        for x in v: out.extend(statuses(x))
        return out
    return []
def rows():
    d=json.loads(SELECTION.read_text(encoding="utf-8")); r={x["geometry_id"]:x for x in d["candidates"] if x["geometry_id"] in {"BF01","BF02","BF03","BF04"}}
    if set(r)!={"BF01","BF02","BF03","BF04"}: raise RuntimeError("BAD_BALANCED_CASE_SET")
    return r
def geom(r):
    return {**r,"j1_length_nm":r["L1_nm"],"j1_width_nm":r["W1_nm"],"j2_length_nm":r["L2_nm"],"j2_width_nm":r["W2_nm"],"j1_rotation_deg":r["theta1_deg"],"j2_rotation_deg":r["theta2_deg"],"height_nm":r["height_nm"]}
def build(root,rs):
    if root.exists(): raise RuntimeError("RECON_OUTPUT_EXISTS")
    root.mkdir(parents=True,exist_ok=False); b=load_module(BASE_RUNNER,"canonical_setup_builder")
    b.ROOT=ROOT; b.RUNTIME=root; b.REPORT=REPORT; b.PARENT_FSP=PARENT_FSP; b.MATERIAL=MATERIAL; b.SOURCE_START=SOURCE_START_NM; b.SOURCE_STOP=SOURCE_STOP_NM; b.PROCESSES=12; b.THREADS=1
    src=inspect.getsource(b.make_pre_fsp)
    if ".run(" in src or "run(" in src.replace("switchtolayout(",""): raise RuntimeError("BUILDER_RUN_PRESENT")
    out={}
    for c in CASES:
        gid,pol=c.rsplit("_",1); z=b.make_pre_fsp(geom(rs[gid]),pol); q=Path(z["path"]); out[c]={"path":str(q),"sha256":sha_file(q),"source_sha256":z["parent_sha256"],"solver_run_called":False,"solver_entered":False,"mpi_processes_metadata":12,"threads_metadata":1}
    return out
def main():
    REPORT.mkdir(parents=True,exist_ok=True); rs=rows(); pm={x["case_id"]:x for x in json.loads(PREPARED.read_text(encoding="utf-8"))["cases"]}
    t=read_fsp(PARENT_FSP,"PARENT_TEMPLATE","x"); cur={c:read_fsp(Path(pm[c]["pre_fsp_path"]),c,c.rsplit("_",1)[1]) for c in CASES}
    fresh=build(RECON_RUNTIME/"primary",rs); fr={c:read_fsp(Path(v["path"]),c,c.rsplit("_",1)[1]) for c,v in fresh.items()}
    repeat=build(RECON_RUNTIME/"repeat",rs); rr={c:read_fsp(Path(v["path"]),c,c.rsplit("_",1)[1]) for c,v in repeat.items()}
    comp={}; repro={}; all_eq=t["readback_complete"]; all_complete=t["readback_complete"]
    for c in CASES:
        gid,pol=c.rsplit("_",1); a=expected_case(rs[gid],pol,t["semantic"]); cc=classify(a,cur[c]["semantic"]); fc=classify(a,fr[c]["semantic"]); rc=classify(fr[c]["semantic"],rr[c]["semantic"]); cs=sorted(set(statuses(cc))); fs=sorted(set(statuses(fc))); zs=sorted(set(statuses(rc)))
        comp[c]={"authority":a,"current":cur[c],"fresh":fr[c],"repeat":rr[c],"authority_vs_current":cc,"authority_vs_fresh":fc,"fresh_vs_repeat":rc,"current_statuses":cs,"fresh_statuses":fs,"repeat_statuses":zs}
        all_complete=all_complete and cur[c]["readback_complete"] and fr[c]["readback_complete"] and rr[c]["readback_complete"]; all_eq=all_eq and "DIFFERENT" not in cs and "DIFFERENT" not in fs and "DIFFERENT" not in zs
        repro[c]={"primary_sha256":fresh[c]["sha256"],"repeat_sha256":repeat[c]["sha256"],"binary_sha_identical":fresh[c]["sha256"]==repeat[c]["sha256"],"semantic_statuses":zs}
    sm={c:{"old_frozen_sha256":pm[c]["pre_fsp_sha256"],"current_sha256":cur[c]["sha256"],"current_path":cur[c]["path"],"current_size_bytes":cur[c]["size_bytes"],"fresh_sha256":fresh[c]["sha256"],"fresh_path":fresh[c]["path"],"repeat_sha256":repeat[c]["sha256"],"repeat_path":repeat[c]["path"]} for c in CASES}
    ft={c:fr[c]["semantic"]["solver"].get("simulation time") for c in CASES}; ct={c:cur[c]["semantic"]["solver"].get("simulation time") for c in CASES}; ts=t["semantic"]["solver"].get("simulation time"); bf08_absent=ts!=5.0 and all(v!=5.0 for v in ft.values()) and all(v!=5.0 for v in ct.values())
    root="BINARY_SERIALIZATION_PROVENANCE_DRIFT_SEMANTICALLY_IDENTICAL" if all_eq and all_complete else "PHYSICS_SEMANTIC_FSP_DRIFT_OR_INCOMPLETE_READBACK"; verdict="PASS_SEMANTIC_RECONCILIATION" if root.startswith("BINARY") and bf08_absent else "HARD_GATE_PHYSICS_SEMANTIC_RECONCILIATION"
    mf={"schema":"PAPER_A_BF01_BF04_SEMANTIC_FINGERPRINT_MANIFEST_V1","method":"canonical JSON SHA256 over physics-semantic readback; binary SHA256 retained separately","numeric_tolerance":{"length_nm":1e-6,"angle_deg":1e-6,"simulation_time_ps":1e-6,"other_numeric":1e-9},"template_semantic_fingerprint":sha_obj(t["semantic"]),"cases":{c:{"authority_fingerprint":sha_obj(comp[c]["authority"]),"current_fingerprint":sha_obj(comp[c]["current"]["semantic"]),"fresh_fingerprint":sha_obj(comp[c]["fresh"]["semantic"]),"repeat_fingerprint":sha_obj(comp[c]["repeat"]["semantic"])} for c in CASES}}
    audit={"schema":"BF01_BF04_PREPARED_FSP_PROVENANCE_RECONCILIATION_AUDIT_V1","timestamp_utc":now(),"verdict":verdict,"root_cause":root,"old_vs_current_vs_fresh":sm,"semantic_comparison_path":str(REPORT/"semantic_comparison.json"),"semantic_fingerprint_manifest_path":str(REPORT/"semantic_fingerprint_manifest.json"),"fresh_builder_reproducibility":repro,"template":{"path":str(PARENT_FSP),"sha256":sha_file(PARENT_FSP),"simulation_time_ps":ts,"validated_1ps_template_retained":ts==1.0},"bf08_5ps_replay_patch_absent":bf08_absent,"readback_complete":all_complete,"solver_counters":{"solver_run_called":False,"solver_entered":0,"new_fdtd_returned":0,"rcwa":0,"ml":0},"builder_contract":{"source_path":str(BASE_RUNNER),"builder_function":"make_pre_fsp","builder_source_contains_run":".run(" in inspect.getsource(load_module(BASE_RUNNER,"audit_builder").make_pre_fsp),"fresh_build_save_only":True,"mpi_processes_metadata":12,"threads_metadata":1},"old_history_preserved":True,"promotion":"NOT_PROMOTED" if verdict.startswith("HARD_GATE") else "FRESH_RECONCILED_SETUP_ONLY_INPUTS_PROMOTED"}
    write_json(REPORT/"old_current_fresh_sha_manifest.json",sm); write_json(REPORT/"semantic_comparison.json",comp); write_json(REPORT/"semantic_fingerprint_manifest.json",mf); write_json(REPORT/"fresh_builder_reproducibility.json",repro); write_json(REPORT/"audit.json",audit)
    lines=["# BF01-BF04 prepared-FSP provenance reconciliation","","Verdict: "+verdict,"Root cause: "+root,"","No FDTD/RCWA/ML solver was called. Current drifted FSPs were read-only; fresh FSPs were setup-only save artifacts from the canonical 1-ps parent template.","","| case | old SHA | current SHA | fresh SHA | repeat SHA | current semantic | fresh semantic |","|---|---|---|---|---|---|---|"]
    for c in CASES:
        x=sm[c]; lines.append("| "+c+" | "+x["old_frozen_sha256"][:12]+" | "+x["current_sha256"][:12]+" | "+x["fresh_sha256"][:12]+" | "+x["repeat_sha256"][:12]+" | "+str(comp[c]["current_statuses"])+" | "+str(comp[c]["fresh_statuses"])+" |")
    lines += ["","Validated 1-ps template retained: "+str(ts==1.0)+".","BF08 5-ps replay patch present: "+str(not bf08_absent)+".","Historical frozen binary hashes are preserved."]
    (REPORT/"report.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    if verdict.startswith("PASS"):
        auth={"schema":"PAPER_A_BF01_BF04_PREPARED_FSP_AUTHORITY_V1","status":"FRESH_SETUP_ONLY_INPUTS_AUTHORIZED_PENDING_SOLVER_ADMISSION","created_utc":now(),"supersedes":str(PREPARED),"supersedes_reason":"SUPERSEDED_PREPARED_FSP_BINARY_PROVENANCE; semantic identity demonstrated","scientific_truth_unchanged":True,"solver_entries_in_reconciliation":0,"builder_source":str(BASE_RUNNER),"parent_template":{"path":str(PARENT_FSP),"sha256":sha_file(PARENT_FSP),"simulation_time_ps":ts},"semantic_fingerprint_manifest":str(REPORT/"semantic_fingerprint_manifest.json"),"cases":{c:{"path":fresh[c]["path"],"sha256":fresh[c]["sha256"],"semantic_fingerprint":mf["cases"][c]["fresh_fingerprint"],"geometry_id":c.rsplit("_",1)[0],"polarization":c.rsplit("_",1)[1],"old_frozen_sha256":pm[c]["pre_fsp_sha256"],"binary_status":"SUPERSEDED_PREPARED_FSP_BINARY_PROVENANCE","solver_entered":False,"solver_run_called":False} for c in CASES},"production_metadata":{"mpi_processes":12,"threads":1,"paper_a_max_active_fdtd":1,"validity_gate":"PAPER_A_FDTD_PHYSICS_VALIDITY_GATE_V1"}}
        write_json(AUTHORITY,auth)
    print(json.dumps({"verdict":verdict,"root_cause":root,"audit":str(REPORT/"audit.json"),"authority":str(AUTHORITY) if verdict.startswith("PASS") else None,"solver_counters":audit["solver_counters"]},indent=2))
    return 0 if verdict.startswith("PASS") else 2
if __name__=="__main__": raise SystemExit(main())
