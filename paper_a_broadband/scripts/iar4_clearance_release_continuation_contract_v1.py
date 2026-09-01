from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import math
import os
import subprocess
from pathlib import Path

import mpmath as mp

ROOT = Path(r"D:/project/worktrees/blue_apcd_paper_a_lp_cp_broadband_v1")
PKG = ROOT / "paper_a_broadband"
OUT = PKG / "reports/iar4_clearance_release_continuation_contract_v1"
DOMAIN = PKG / "reports/integrated_aware_lp_redesign_contract_v1/integrated_local_domain_authority.json"
INITIAL = PKG / "reports/integrated_aware_lp_redesign_contract_v1/integrated_candidate_registry_initial.csv"
CONDITIONAL = PKG / "reports/integrated_aware_lp_redesign_contract_v1/integrated_candidate_registry_conditional.csv"
POOL = PKG / "reports/integrated_aware_lp_redesign_contract_v1/integrated_feasible_pool.csv"
PARAM = PKG / "reports/lp_anisotropy_feasible_space_v2/feasible_space_parameterization.json"
RULE = PKG / "scripts/lp_anisotropy_feasible_space_v2.py"
HP_RULE = PKG / "scripts/a02_pre_admission_geometry_audit_v2.py"
PROTECTED = PKG / "reports/ic1_solver_ready_runner/dry_run.json"
PROTECTED_SHA = "52f70e630cc64e89be8e65adf1a402b4816c435c41232c39886167f6afc6567c"
mp.mp.dps = 100

def sj(x):
    return hashlib.sha256(json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode()).hexdigest()

def sf(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def wj(p, x):
    p.parent.mkdir(parents=True, exist_ok=True)
    t = p.with_suffix(p.suffix + f".{os.getpid()}.tmp")
    t.write_text(json.dumps(x, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    os.replace(t, p)

def wc(p, rows):
    p.parent.mkdir(parents=True, exist_ok=True)
    fields = []
    for r in rows:
        for k in r:
            if k not in fields: fields.append(k)
    t = p.with_suffix(p.suffix + f".{os.getpid()}.tmp")
    with t.open("w", newline="", encoding="utf-8") as h:
        z = csv.DictWriter(h, fieldnames=fields, extrasaction="ignore")
        z.writeheader()
        for r in rows:
            z.writerow({k: json.dumps(v, ensure_ascii=False, sort_keys=True, default=str) if isinstance(v, (dict, list)) else v for k, v in r.items()})
    os.replace(t, p)

def rj(p): return json.loads(p.read_text(encoding="utf-8-sig"))
def rc(p):
    with p.open(encoding="utf-8-sig", newline="") as h: return list(csv.DictReader(h))
def git(*args): return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()
def mod(p, n):
    spec = importlib.util.spec_from_file_location(n, p)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

def ghash(g):
    keys = ["L1_nm","W1_nm","L2_nm","W2_nm","D_nm","delta_theta_deg","height_nm","period_x_nm","period_y_nm","theta1_deg","theta2_deg"]
    return sj({k:g[k] for k in keys})

def hp_input(l1,w1,l2,w2,d,t):
    return {"L1_nm":str(l1),"W1_nm":str(w1),"L2_nm":str(l2),"W2_nm":str(w2),"D_nm":str(d),"j1_rotation_deg":"0","j2_rotation_deg":str(t),"j1_center_x_nm":"0","j1_center_y_nm":str(mp.mpf(str(d))/2),"j2_center_x_nm":"0","j2_center_y_nm":str(-mp.mpf(str(d))/2),"validity":{}}

def geom(l1,w1,l2,w2,d,t):
    return {"L1_nm":int(l1),"W1_nm":int(w1),"L2_nm":int(l2),"W2_nm":int(w2),"D_nm":int(d),"delta_theta_deg":float(t),"theta1_deg":0.0,"theta2_deg":float(t),"j1_center_x_nm":0.0,"j1_center_y_nm":float(d)/2,"j2_center_x_nm":0.0,"j2_center_y_nm":-float(d)/2,"height_nm":525.0,"period_x_nm":432.0,"period_y_nm":432.0}

def norm(g):
    b={"a1":(.85,1.15),"b1":(.85,1.15),"a2":(.85,1.15),"b2":(.85,1.15),"delta_theta_deg":(0.,90.),"D_nm":(170.,220.)}
    v={"a1":float(g["L1_nm"])/230,"b1":float(g["W1_nm"])/100,"a2":float(g["L2_nm"])/180,"b2":float(g["W2_nm"])/90,"delta_theta_deg":float(g["delta_theta_deg"]),"D_nm":float(g["D_nm"])}
    return [(v[k]-lo)/(hi-lo) for k,(lo,hi) in b.items()]

def dist(a,b): return math.sqrt(sum((x-y)**2 for x,y in zip(a,b)))
def fq(l1,w1,l2,w2,d,t): return {"L1_nm":l1,"W1_nm":w1,"L2_nm":l2,"W2_nm":w2,"D_nm":d,"theta1_deg":0.,"theta2_deg":t,"j1_center_x_nm":0.,"j1_center_y_nm":d/2,"j2_center_x_nm":0.,"j2_center_y_nm":-d/2}
def fpass(c): return c["direct_clearance_nm"] >= 60-1e-9 and c["periodic_image_clearance_nm"] >= 60-1e-9 and c["cell_containment_pass"] and c["overlap_or_touching_pass"]

def exact(hp,l1,w1,l2,w2,d,t):
    q=geom(l1,w1,l2,w2,d,t)
    a=hp.geometry_audit(hp_input(l1,w1,l2,w2,d,t),mp.mpf("432"),mp.mpf("432"))
    return {"geometry":q,"geometry_hash_sha256_recomputed":ghash(q),"validity_audit_high_precision":a}

def main():
    if sf(PROTECTED)!=PROTECTED_SHA: raise RuntimeError("protected dry_run.json differs before audit")
    domain=rj(DOMAIN); param=rj(PARAM); initial=rc(INITIAL); conditional=rc(CONDITIONAL); pool=rc(POOL)
    gates={"direct_polygon_clearance_nm_ge":60.0,"periodic_image_polygon_clearance_nm_ge":60.0,"no_overlap_or_touching":True,"cell_containment":True,"integer_lateral_dimensions":True,"half_grid_centers":True,"no_sub_grid_geometry":True}
    bounds={"L1_nm":[251,264],"W1_nm":[87,91],"L2_nm":[194,203],"W2_nm":[77,80],"D_nm":[208,220],"delta_theta_deg":[80.0,90.0]}
    if domain["narrow_bounds"]!=bounds or domain["hard_gates_inherited"]!=gates or param["hard_gates"]!=gates: raise RuntimeError("frozen domain/gate mismatch")
    iar=next(x for x in initial if x["geometry_id"]=="IAR4"); c2r=next(x for x in conditional if x["geometry_id"]=="IAR-C2")
    i=(int(iar["L1_nm"]),int(iar["W1_nm"]),int(iar["L2_nm"]),int(iar["W2_nm"]),int(iar["D_nm"]),float(iar["delta_theta_deg"]))
    hp=mod(HP_RULE,"hp_rule"); rule=mod(RULE,"current_rule")
    base=geom(*i)
    iar4=exact(hp,*i); iar4["candidate_id"]="IAR4"; iar4["source_geometry_hash"] = iar["geometry_hash_sha256"]; iar4["source_geometry_hash_match"] = iar4["geometry_hash_sha256_recomputed"]==iar["geometry_hash_sha256"]

    def ev(d,t):
        c=rule.geom_core(fq(i[0],i[1],i[2],i[3],d,t)); return c,fpass(c)
    frontier=[]
    for d in range(208,221):
        grid=[(80+k*.01,ev(d,80+k*.01)[1]) for k in range(1001)]
        j=next((j for j,x in enumerate(grid) if x[1]),None)
        if j is None: raise RuntimeError(f"no frontier for D={d}")
        if j==0: root=80.
        else:
            lo,hi=grid[j-1][0],grid[j][0]
            for _ in range(60):
                mid=(lo+hi)/2
                if ev(d,mid)[1]: hi=mid
                else: lo=mid
            root=hi
        t=round(math.ceil((root-1e-12)*1e9)/1e9,9)
        a=exact(hp,i[0],i[1],i[2],i[3],d,t); h=a["validity_audit_high_precision"]
        while not h["current_inherited_gate_pass"]:
            t=round(t+1e-9,9); a=exact(hp,i[0],i[1],i[2],i[3],d,t); h=a["validity_audit_high_precision"]
        dr=float(h["direct_clearance_nm"]); pe=float(h["periodic_image_clearance_nm"])
        frontier.append({"D_nm":d,"fixed_L1_nm":i[0],"fixed_W1_nm":i[1],"fixed_L2_nm":i[2],"fixed_W2_nm":i[3],"continuous_boundary_estimate_deg":f"{root:.12f}","minimum_legal_delta_theta_deg_9dp":f"{t:.9f}","delta_theta_reduction_vs_IAR4_deg":f"{i[5]-t:.9f}","direct_clearance_nm":f"{dr:.12f}","periodic_clearance_nm":f"{pe:.12f}","global_minimum_clearance_nm":f"{min(dr,pe):.12f}","direct_headroom_over_60_nm":f"{dr-60:.12f}","periodic_headroom_over_60_nm":f"{pe-60:.12f}","minimum_headroom_over_60_nm":f"{min(dr,pe)-60:.12f}","nearest_pair":h["direct_same_cell_pillar_pair"] if dr<=pe else h["nearest_periodic_image_pair_all_objects"],"validity":"PASS","frontier_method":"current exact polygon rule; 0.01 deg bracket, 9-decimal quantization, high-precision confirmation"})
    choices=[x for x in frontier if float(x["minimum_legal_delta_theta_deg_9dp"])<i[5]-1e-9]
    chosen=min(choices,key=lambda x:(float(x["minimum_legal_delta_theta_deg_9dp"]),abs(int(x["D_nm"])-i[4]),-float(x["minimum_headroom_over_60_nm"]),int(x["D_nm"])))
    cr1=exact(hp,i[0],i[1],i[2],i[3],int(chosen["D_nm"]),float(chosen["minimum_legal_delta_theta_deg_9dp"]))
    cr1.update({"candidate_id":"IAR4-CR1","role":"ORIENTATION_CONTINUATION_WITH_D_CLEARANCE_COMPENSATION","status":"PROSPECTIVE_NOT_AUTHORIZED","difference_from_IAR4":{"L1_nm":0,"W1_nm":0,"L2_nm":0,"W2_nm":0,"D_nm":int(chosen["D_nm"])-i[4],"delta_theta_deg":float(chosen["minimum_legal_delta_theta_deg_9dp"])-i[5]},"current_inherited_gate_pass":cr1["validity_audit_high_precision"]["current_inherited_gate_pass"]})
    c2=exact(hp,int(c2r["L1_nm"]),int(c2r["W1_nm"]),int(c2r["L2_nm"]),int(c2r["W2_nm"]),int(c2r["D_nm"]),float(c2r["delta_theta_deg"]))
    c2.update({"candidate_id":"IAR-C2","role":"SAME_ORIENTATION_LOCAL_BASIN_AND_CLEARANCE_REFERENCE","status":"REFERENCE_ONLY_NOT_CAUSAL_CONTROL","source_geometry_hash":c2r["geometry_hash_sha256"],"source_geometry_hash_match":c2["geometry_hash_sha256_recomputed"]==c2r["geometry_hash_sha256"]})
    cg=c2["geometry"]; ig=iar4["geometry"]; c2["difference_from_IAR4"]={k:float(cg[k])-float(ig[k]) for k in ["L1_nm","W1_nm","L2_nm","W2_nm","D_nm","delta_theta_deg"]}; c2["normalized_6d_distance_from_IAR4"]=dist(norm(cg),norm(ig))
    c2["clearance_delta_vs_IAR4_nm"]={"direct":float(c2["validity_audit_high_precision"]["direct_clearance_nm"])-float(iar4["validity_audit_high_precision"]["direct_clearance_nm"]),"periodic":float(c2["validity_audit_high_precision"]["periodic_image_clearance_nm"])-float(iar4["validity_audit_high_precision"]["periodic_image_clearance_nm"])}
    rows=[]; failures=0; ivec=norm(ig)
    for r in pool:
        t=float(r["delta_theta_deg"])
        if t>=i[5]-1e-12: continue
        ds={k:int(r[k]) for k in ["L1_nm","W1_nm","L2_nm","W2_nm","D_nm"]}; core=rule.geom_core(fq(ds["L1_nm"],ds["W1_nm"],ds["L2_nm"],ds["W2_nm"],ds["D_nm"],t)); ok=fpass(core); match=abs(core["direct_clearance_nm"]-float(r["direct_clearance_nm"]))<1e-8 and abs(core["periodic_image_clearance_nm"]-float(r["periodic_image_clearance_nm"]))<1e-8 and r["geometry_hash_sha256"]==r["geometry_hash_recomputed"] and r["geometry_hash_recomputed_match"].lower()=="true"
        if not (ok and match): failures+=1
        q=geom(ds["L1_nm"],ds["W1_nm"],ds["L2_nm"],ds["W2_nm"],ds["D_nm"],t); minimum=min(core["direct_clearance_nm"],core["periodic_image_clearance_nm"])
        rows.append({"source_pool_sample_index":r["sample_index"],**ds,"delta_theta_deg":f"{t:.9f}","delta_theta_reduction_vs_IAR4_deg":f"{i[5]-t:.9f}","delta_L1_nm":ds["L1_nm"]-i[0],"delta_W1_nm":ds["W1_nm"]-i[1],"delta_L2_nm":ds["L2_nm"]-i[2],"delta_W2_nm":ds["W2_nm"]-i[3],"delta_D_nm":ds["D_nm"]-i[4],"direct_clearance_nm":f"{core['direct_clearance_nm']:.12f}","periodic_image_clearance_nm":f"{core['periodic_image_clearance_nm']:.12f}","minimum_clearance_nm":f"{minimum:.12f}","minimum_headroom_over_60_nm":f"{minimum-60:.12f}","normalized_6d_distance_from_IAR4":f"{dist(norm(q),ivec):.12f}","geometry_hash_sha256":r["geometry_hash_sha256"],"recomputed_current_rule_pass":ok,"stored_vs_recomputed_clearance_match":match,"source":"integrated_feasible_pool.csv; current inherited geometry-only pool; no optical metric"})
    rows.sort(key=lambda r:(float(r["normalized_6d_distance_from_IAR4"]),-float(r["minimum_headroom_over_60_nm"]),float(r["delta_theta_deg"]),int(r["source_pool_sample_index"])))
    for n,r in enumerate(rows,1): r["geometry_distance_rank"]=n
    solver={"NEW_FDTD_BUDGET":0,"solver_run_called":False,"solver_entered":0,"RCWA":0,"ML":0,"active_new_paper_a_fdtd":0,"ready_pending_hidden_auto_admission":False}
    candidate={"schema":"PAPER_A_IAR4_CLEARANCE_RELEASE_CONTINUATION_CANDIDATE_REGISTRY_V1","status":"ZERO_SOLVER_PROSPECTIVE_PLAN_ONLY","prospective_candidate_count":1,"future_authorized_truth_budget_maximum":4,"prospective_records":[{"candidate_id":"IAR4-CR1","role":cr1["role"],"status":cr1["status"],"geometry":cr1["geometry"],"geometry_hash_sha256_recomputed":cr1["geometry_hash_sha256_recomputed"],"difference_from_IAR4":cr1["difference_from_IAR4"],"direct_clearance_nm":cr1["validity_audit_high_precision"]["direct_clearance_nm"],"periodic_clearance_nm":cr1["validity_audit_high_precision"]["periodic_image_clearance_nm"],"normalized_6d_distance_from_IAR4":dist(norm(cr1["geometry"]),ivec),"no_solver_authorization":True}],"reference_records":[{"candidate_id":"IAR-C2","role":c2["role"],"status":c2["status"],"geometry":c2["geometry"],"geometry_hash_sha256_recomputed":c2["geometry_hash_sha256_recomputed"],"normalized_6d_distance_from_IAR4":c2["normalized_6d_distance_from_IAR4"],"no_orientation_only_claim":True}],"not_frozen":"No CR2 is needed because D-only route is feasible."}
    contract={"schema":"PAPER_A_IAR4_CLEARANCE_RELEASE_CONTINUATION_CONTRACT_V1","status":"ZERO_SOLVER_PRE_ADMISSION_PLAN","scientific_authority":{"strict_causal_pair":"IAR4 <-> IAR4-OC1","top_level_causal_verdict":"ORIENTATION_CAUSAL_EFFECT_WAVELENGTH_DEPENDENT","450_nm_interpretation":"smaller_delta_theta_favored","W_emit":"unresolved","no_optical_ranking":True},"IAR4_exact_authority":iar4,"fixed_for_D_only":base,"frozen_local_domain":bounds,"inherited_geometry_gates":gates,"validity_method":{"rule_script":str(RULE),"rule_sha256":sf(RULE),"corrected_high_precision_audit":str(HP_RULE),"corrected_high_precision_audit_sha256":sf(HP_RULE),"method":domain["validity_implementation"]["method"],"no_boundary_margin_substitution":True},"D_only_result":{"frontier_rows":len(frontier),"minimum_frontier_theta_deg":min(float(x["minimum_legal_delta_theta_deg_9dp"]) for x in frontier),"maximum_reduction_vs_IAR4_deg":i[5]-min(float(x["minimum_legal_delta_theta_deg_9dp"]) for x in frontier),"legal_D_at_theta_floor_80_deg":[int(x["D_nm"]) for x in frontier if float(x["minimum_legal_delta_theta_deg_9dp"])==80.0],"selected_CR1":{"candidate_id":"IAR4-CR1","D_nm":int(chosen["D_nm"]),"delta_theta_deg":float(chosen["minimum_legal_delta_theta_deg_9dp"]),"D_change_nm":int(chosen["D_nm"])-i[4],"theta_change_deg":float(chosen["minimum_legal_delta_theta_deg_9dp"])-i[5]}},"minimal_geometry_compensation_search":{"source_pool":str(POOL),"eligible_smaller_theta_count":len(rows),"recomputed_current_rule_failures":failures,"top_nonfrozen_reference":rows[0] if rows else None,"CR2_needed":False,"no_optical_score":True},"IAR_C2_reference_only":c2,"future_plan_only":{"candidate_plan":["IAR4-CR1","IAR-C2"],"future_maximum_FDTD_jobs":4,"future_jobs":"two geometries x/y","current_solver_authorization":0,"stop_loss":"Do not exceed the separately authorized 4-job truth budget; if future truth is not interpretable, stop and return to scope review."},"solver_accounting":solver,"DOE_changed":False,"A01_A08_reused":False}
    validity={"schema":"PAPER_A_IAR4_CLEARANCE_RELEASE_CONTINUATION_POLYGON_VALIDITY_AUDIT_V1","status":"PASS","current_rule_source":str(RULE),"current_rule_sha256":sf(RULE),"high_precision_rule_source":str(HP_RULE),"IAR4":iar4,"IAR4_CR1":cr1,"IAR-C2":c2,"D_theta_frontier":frontier,"frontier_all_current_gates_pass":all(x["validity"]=="PASS" for x in frontier),"boundary_margin_used_as_gate":False,"A01_A08_audit_reused":False}
    branch=git("branch","--show-current"); head=git("rev-parse","HEAD"); upstream=git("rev-parse","--abbrev-ref","--symbolic-full-name","@{u}"); ab=git("rev-list","--left-right","--count","HEAD...@{u}")
    prov={"schema":"PAPER_A_IAR4_CLEARANCE_RELEASE_CONTINUATION_PROVENANCE_V1","canonical_worktree":str(ROOT),"canonical_branch":branch,"canonical_head_at_generation":head,"upstream":upstream,"ahead_behind_at_generation":ab,"source_files":{str(p):sf(p) for p in [DOMAIN,INITIAL,CONDITIONAL,POOL,PARAM,RULE,HP_RULE]},"corrected_current_authority_used":True,"no_A01_A08_reuse":True,"protected_file":{"path":str(PROTECTED),"sha256_before":sf(PROTECTED),"expected_unchanged_sha256":PROTECTED_SHA},"solver_accounting":solver}
    val={"schema":"PAPER_A_IAR4_CLEARANCE_RELEASE_CONTINUATION_VALIDATION_V1","current_corrected_authority_used":True,"domain_bounds_unchanged":domain["narrow_bounds"]==bounds,"inherited_gates_unchanged":domain["hard_gates_inherited"]==gates and param["hard_gates"]==gates,"D_theta_frontier_recomputed":len(frontier)==13,"all_frontier_rows_high_precision_pass":all(x["validity"]=="PASS" for x in frontier),"selected_CR1_high_precision_pass":bool(cr1["current_inherited_gate_pass"]),"selected_CR1_theta_below_IAR4":float(chosen["minimum_legal_delta_theta_deg_9dp"])<i[5],"IAR4_source_hash_match":bool(iar4["source_geometry_hash_match"]),"IAR_C2_source_hash_match":bool(c2["source_geometry_hash_match"]),"IAR_C2_reference_only":c2["status"]=="REFERENCE_ONLY_NOT_CAUSAL_CONTROL","minimal_compensation_pool_reaudit_pass":failures==0,"prospective_candidate_count_le_2":True,"no_old_A01_A08_reuse":True,"no_optical_score_or_new_threshold":True,"DOE_changed":False,"NEW_FDTD_BUDGET_zero":True,"solver_run_called_false":True,"solver_entered_zero":True,"RCWA_zero":True,"ML_zero":True,"protected_untouched_before":sf(PROTECTED)==PROTECTED_SHA,"validation_status":"PASS"}
    if not all(v is True for k,v in val.items() if k not in {"schema","validation_status","DOE_changed"}):
        raise RuntimeError("validation failed")
    audit={"schema":"PAPER_A_IAR4_CLEARANCE_RELEASE_CONTINUATION_AUDIT_V1","status":"PASS","task":"PAPER_A_IAR4_CLEARANCE_RELEASE_CONTINUATION_CONTRACT_V1","canonical_head_at_generation":head,"solver_accounting":solver,"DOE_changed":False,"prospective_candidate_count":1,"frontier_rows":13,"eligible_compensation_pool_rows":len(rows),"pool_reaudit_failures":failures,"protected_file_sha256_before":sf(PROTECTED),"no_solver_invocation":True}
    OUT.mkdir(parents=True,exist_ok=True)
    wj(OUT/"continuation_contract.json",contract); wc(OUT/"d_theta_feasibility_frontier.csv",frontier)
    wj(OUT/"d_theta_feasibility_summary.json",{"schema":"PAPER_A_IAR4_D_THETA_FEASIBILITY_SUMMARY_V1","status":"PASS","IAR4_D_nm":i[4],"IAR4_delta_theta_deg":i[5],"minimum_legal_frontier_theta_deg":min(float(x["minimum_legal_delta_theta_deg_9dp"]) for x in frontier),"maximum_reduction_deg":i[5]-min(float(x["minimum_legal_delta_theta_deg_9dp"]) for x in frontier),"D_values_reaching_theta_floor_80_deg":[int(x["D_nm"]) for x in frontier if float(x["minimum_legal_delta_theta_deg_9dp"])==80.0],"selected_CR1":{"D_nm":int(chosen["D_nm"]),"delta_theta_deg":float(chosen["minimum_legal_delta_theta_deg_9dp"]),"direct_clearance_nm":cr1["validity_audit_high_precision"]["direct_clearance_nm"],"periodic_clearance_nm":cr1["validity_audit_high_precision"]["periodic_image_clearance_nm"]},"no_new_threshold":True})
    wc(OUT/"minimal_geometry_compensation_search.csv",rows); wj(OUT/"iar_c2_reference_audit.json",c2); wj(OUT/"candidate_registry.json",candidate); wj(OUT/"polygon_validity_audit.json",validity); wj(OUT/"validation_tests.json",val); wj(OUT/"provenance.json",prov); wj(OUT/"audit.json",audit)
    md=["# IAR4 clearance-release continuation contract","","Status: PASS (zero-solver geometry-only pre-admission planning).","","- Strict causal pair: IAR4 <-> IAR4-OC1.","- Top-level causal verdict: ORIENTATION_CAUSAL_EFFECT_WAVELENGTH_DEPENDENT; 450 nm smaller delta-theta favored.","- W_emit unresolved; no optical ranking, composite score, or new threshold used.","- Current corrected direct/periodic polygon authority used; A01-A08 planning validity artifacts not reused.","",f"IAR4 exact: L1/W1/L2/W2={i[0]}/{i[1]}/{i[2]}/{i[3]} nm, D={i[4]} nm, delta_theta={i[5]:.9f} deg, H=525.0 nm, Px=Py=432.0 nm.",f"IAR4 high-precision clearance: direct={iar4['validity_audit_high_precision']['direct_clearance_nm']} nm; periodic-image={iar4['validity_audit_high_precision']['periodic_image_clearance_nm']} nm.","","| D (nm) | min legal delta_theta (deg) | direct (nm) | periodic (nm) | min headroom over 60 (nm) |","|---:|---:|---:|---:|---:|"]
    md += [f"| {x['D_nm']} | {x['minimum_legal_delta_theta_deg_9dp']} | {x['direct_clearance_nm']} | {x['periodic_clearance_nm']} | {x['minimum_headroom_over_60_nm']} |" for x in frontier]
    md += ["",f"Theta floor 80 deg is legal for D={', '.join(str(int(x['D_nm'])) for x in frontier if float(x['minimum_legal_delta_theta_deg_9dp'])==80.0)} nm.",f"IAR4-CR1 prospective/not-authorized: D={int(chosen['D_nm'])} nm, delta_theta={float(chosen['minimum_legal_delta_theta_deg_9dp']):.9f} deg, D change={int(chosen['D_nm'])-i[4]:+d} nm, theta change={float(chosen['minimum_legal_delta_theta_deg_9dp'])-i[5]:+.9f} deg.",f"CR1 high-precision clearance: direct={cr1['validity_audit_high_precision']['direct_clearance_nm']} nm; periodic-image={cr1['validity_audit_high_precision']['periodic_image_clearance_nm']} nm.","No CR2 is needed because D-only is feasible. IAR-C2 remains reference-only and is not an orientation-only control.","","Future plan only: IAR4-CR1 + IAR-C2, x/y each, maximum 4 FDTD jobs after separate authorization. Current solver budget is zero.","No authoritative linewidth/aspect-ratio hard threshold was found; existing geometry gates are unchanged."]
    (OUT/"final_report.md").write_text("\n".join(md)+"\n",encoding="utf-8")
    if sf(PROTECTED)!=PROTECTED_SHA: raise RuntimeError("protected dry_run.json changed during audit")
    val["protected_untouched_after"] = True; val["generated_artifacts_written"] = True; wj(OUT/"validation_tests.json",val); audit["protected_file_sha256_after"] = sf(PROTECTED); wj(OUT/"audit.json",audit)
    print(json.dumps({"status":"PASS","head":head,"branch":branch,"frontier":frontier,"CR1":cr1,"C2":c2,"compensation_count":len(rows),"top_compensation":rows[0] if rows else None,"protected_sha":sf(PROTECTED),"solver":solver},ensure_ascii=False,default=str))

if __name__ == "__main__": main()
