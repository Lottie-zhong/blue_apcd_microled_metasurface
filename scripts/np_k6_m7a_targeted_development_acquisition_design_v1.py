from pathlib import Path
import csv,json,hashlib,datetime,math,random,runpy
import numpy as np

ROOT=Path(r"D:/project/worktrees/blue_apcd_np_k6_mdc_v1")
OUT=ROOT/"outputs/np_k6_m7a_targeted_development_acquisition_design_v1"
M7OUT=ROOT/"outputs/np_k6_m7_16g_forward_retraining_v1"
M6OUT=ROOT/"outputs/np_k6_m6_error_region_acquisition_design_v1"
DATA=ROOT/"outputs/np_k6_m6_formal_development_merge_v1/formal_development_hf_observations_352rows.csv"
G01="K6X_D110_D125_D130_D135_D140_D175"
WLS=list(range(445,456)); ORDERS=[-3,-2,-1,0,1,2,3]

def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha_bytes(b): return hashlib.sha256(b).hexdigest()
def sha(p): return sha_bytes(p.read_bytes())
def dump(name,obj):
    p=OUT/name; p.write_text(json.dumps(obj,indent=2,sort_keys=True)+"\n",encoding="utf-8"); return p
def read_csv(p):
    with p.open(encoding="utf-8",newline="") as f:return list(csv.DictReader(f))
def write_csv(name,fields,rows):
    with (OUT/name).open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
def parse(g): return [float(x[1:]) for x in g.split("_")[1:]]
def norm(vals):
    a=np.asarray(vals,float); lo=float(np.nanmin(a)); hi=float(np.nanmax(a));
    return np.zeros(len(a)) if hi-lo<1e-12 else (a-lo)/(hi-lo)
def pair_dist(a,b): return float(np.linalg.norm(np.asarray(a,float)-np.asarray(b,float))/math.sqrt(len(a)))

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    hf=read_csv(DATA); m6=read_csv(M6OUT/"m6_candidate_scores.csv")
    ext=json.loads((ROOT/"outputs/np_k6_m5_fullk6_forward_v0/external_set_registry.json").read_text())
    ext_ids={x["geometry_id"] for x in ext["geometries"]}
    hf_ids={r["geometry_id"] for r in hf}
    # Freeze methodology before candidate identities are materialized.
    prereg={
      "preregistration_id":"NP_K6_M7A_TARGETED_ACQUISITION_PREREG_V1","created_utc":now(),"solver_calls":0,
      "scope":"zero-solver targeted development HF acquisition design only","candidate_source":"M6 frozen candidate_scores.csv, development-only proxy universe",
      "exclusion_policy":{"exclude_formal_hf16":True,"exclude_external_registry":True,"exclude_sealed_pool":True,"exclude_g01_geometry":G01,"exclude_duplicate_hash":True},
      "features":["ordered_D1_D6","adjacent_diameter_jumps","diameter_range","nearest_HF16_distance","LF_order_profile","LF_eta_plus1","LF_spectral_robustness","calibrated_LF_eta_plus1","Ridge_eta_plus1","residual_MLP_eta_plus1","CNN_eta_plus1","model_rank_disagreement","P_S_contrast_proxy","known_residual_cluster_proximity","geometry_diversity"],
      "roles":{"RESIDUAL-TAIL":"tail and systematic LF/model correction risk","RANKING-CHAMPION-STRESS":"performance with rank ambiguity and pairwise reversals","POLARIZATION-STRESS":"P/S contrast and structured-model instability","COVERAGE-CONTROL":"representative geometry/LF-response support"},
      "score_construction":{"residual_tail":"0.35 tail + 0.25 M7 model disagreement + 0.20 Ridge-CNN disagreement + 0.20 order-risk","ranking_ambiguity":"0.50 rank variance + 0.30 performance potential + 0.20 near-champion margin","polarization_stress":"0.70 P/S proxy + 0.20 predicted P/S disagreement + 0.10 residual risk","coverage_control":"0.55 nearest-HF16 distance + 0.25 LF response distance + 0.20 geometry diversity"},
      "normalization":"min-max fitted on eligible development candidate universe only","tie_break":"descending role score, then descending geometry_hash lexicographic","batch_sizes":{"Primary4":4,"first6":6,"first8":8},"backup_count":8,
      "solver_cost_protocol":{"mpi_processes":4,"threads":1,"verified_concurrency":2,"no_solver_in_this_stage":True,"runtime_source":"m6_solver_cost_package.json"},
      "promotion":"development promotion candidate only; external HF remains unauthorized"
    }
    pre_bytes=(json.dumps(prereg,sort_keys=True,indent=2)+"\n").encode(); (OUT/"NP_K6_M7A_TARGETED_ACQUISITION_PREREG_V1.json").write_bytes(pre_bytes); pre_sha=sha_bytes(pre_bytes)
    dump("preregistration_sha256.json",{"preregistration_id":prereg["preregistration_id"],"sha256":pre_sha,"fit_or_identity_selection_started_after_preregistration":True,"solver_calls":0})
    # Build eligible candidate universe from the frozen M6 table, after preregistration.
    source_ids={r["geometry_id"] for r in m6}; source_hashes={r["geometry_hash"] for r in m6}
    eligible=[]; excluded=[]
    for r in m6:
        gid=r["geometry_id"]; reasons=[]
        if gid==G01: reasons.append("G01_quarantine")
        if gid in hf_ids: reasons.append("formal_HF16_overlap")
        if gid in ext_ids: reasons.append("external_registry_overlap")
        if reasons: excluded.append({"geometry_id":gid,"reasons":reasons}); continue
        eligible.append(dict(r))
    if len({r["geometry_hash"] for r in eligible})!=len(eligible): raise RuntimeError("duplicate candidate hash")
    if not eligible: raise RuntimeError("empty eligible candidate universe")
    # Load frozen M7 runner functions, then score candidate rows using full-development fits only.
    mod=runpy.run_path(str(ROOT/"scripts/np_k6_m7_16g_forward_retraining_v1.py"),run_name="m7a_module")
    hf_lf=read_csv(M7OUT/"lf_baseline_352rows.csv")
    lf_map={(r["geometry_id"],int(float(r["wavelength_nm"])),r["polarization"]):r for r in hf_lf}
    import gzip
    master=ROOT/"outputs/np_k6_ml_d0_database_foundation_v1/k6_design_space_master.csv.gz"
    idx={}
    with gzip.open(master,"rt",encoding="utf-8") as f:
        for i,r in enumerate(csv.DictReader(f)):
            if r["geometry_id"] in {x["geometry_id"] for x in eligible}: idx[r["geometry_id"]]=i
    if len(idx)!=len(eligible): raise RuntimeError("candidate master linkage incomplete")
    needed={i//5000 for i in idx.values()}; lf_arrays={}
    for ch in needed:
        z=np.load(ROOT/f"outputs/np_k6_ml_d0_database_foundation_v1/lf_chunks/chunk_{ch:03d}.npz")
        for gid,gi in idx.items():
            if gi//5000==ch: lf_arrays[gid]=(z["eta_m_proxy"][gi%5000].astype(float),z["propagating_sum_proxy"][gi%5000].astype(float))
    def lf_for(gid,w,pol):
        eta,t=lf_arrays[gid]; k=w-445
        return {"geometry_id":gid,"wavelength_nm":str(w),"polarization":pol,"lf_T_proxy":str(float(t[k])),**{f"lf_eta_m{m:+d}":str(float(eta[k,j])) for j,m in enumerate(ORDERS)}}
    cr=[]; clf=[]
    for r in eligible:
        for pol in ("p","s"):
            for w in WLS:
                cr.append({"geometry_id":r["geometry_id"],"wavelength_nm":str(w),"polarization":pol,"R_total":"0",**{f"eta_m{m:+d}":"0" for m in ORDERS}}); clf.append(lf_for(r["geometry_id"],w,pol))
    combo=hf+cr; combo_lf=hf_lf+clf; X,C,N,Y,L=mod["make_arrays"](combo,combo_lf); tr=np.arange(len(hf)); te=np.arange(len(hf),len(combo))
    preds={"LF_only":np.c_[np.full(len(te),np.nan),L[te,:7]],"LF_global_bias":mod["ridge_pred"]("lf_global_bias",X,C,Y,L,combo,tr,te),"LF_affine":mod["ridge_pred"]("lf_affine",X,C,Y,L,combo,tr,te),"LF_ridge_residual":mod["ridge_pred"]("lf_ridge_residual",X,C,Y,L,combo,tr,te)}
    for kind,name in [("corrected_residual_mlp","corrected_residual_mlp"),("circular_cnn","circular_cnn"),("direct_mlp","direct_mlp"),("resmlp","resmlp")]:
        ps=[]
        for seed in (17,29,43): ps.append(mod["torch_fit"](kind,X,C,N,Y,L,tr,te,seed))
        preds[name]=np.mean(ps,axis=0); preds[name+"_seed_std"]=np.std(ps,axis=0)
    def pred_value(i,model): return float(preds[model][i,5])
    # Aggregate 11 wavelength/P/S predictions into geometry-level acquisition features.
    agg={}
    long=[]
    for j,r in enumerate(eligible):
        gid=r["geometry_id"]; start=j*22; inds=list(range(start,start+22));
        means={m:float(np.nanmean([pred_value(i,m) for i in inds])) for m in ("LF_only","LF_global_bias","LF_affine","LF_ridge_residual","corrected_residual_mlp","circular_cnn")}
        ps_contrast=float(np.mean([abs(pred_value(i,"corrected_residual_mlp")-pred_value(i+11,"corrected_residual_mlp")) for i in range(start,start+11)]))
        rankvals=np.array([means[m] for m in ("LF_only","LF_global_bias","LF_affine","LF_ridge_residual","corrected_residual_mlp","circular_cnn")]); ranks=np.argsort(np.argsort(-rankvals))+1
        rank_var=float(np.std(ranks)); pair_rev=float(np.mean([abs(rankvals[a]-rankvals[b]) for a in range(len(rankvals)) for b in range(a+1,len(rankvals))]))
        agg[gid]={"geometry_id":gid,"geometry_hash":r["geometry_hash"],"D1":r["D1"],"D2":r["D2"],"D3":r["D3"],"D4":r["D4"],"D5":r["D5"],"D6":r["D6"],"calibrated_eta_plus1":r.get("predicted_eta_robust_mean",""),"ridge_eta_plus1":means["LF_ridge_residual"],"residual_mlp_eta_plus1":means["corrected_residual_mlp"],"cnn_eta_plus1":means["circular_cnn"],"lf_eta_plus1":r.get("lf_eta_plus1_mean",""),"model_rank_variance":rank_var,"pairwise_model_reversal_proxy":pair_rev,"predicted_ps_contrast":ps_contrast,"nearest_hf16_distance":r.get("nearest_hf13_distance",""),"lf_response_distance":r.get("model_disagreement",""),"residual_tail_score":r.get("tail_error_proxy_norm","0"),"performance_score":r.get("performance_potential_norm","0"),"ps_risk_score":r.get("ps_contrast_risk_proxy_norm","0"),"geometry_span":max(parse(gid))-min(parse(gid)),"predicted_rank_vector":json.dumps(dict(zip(("LF_only","LF_global_bias","LF_affine","LF_ridge_residual","corrected_residual_mlp","circular_cnn"),ranks.tolist())),sort_keys=True)}
        for i in inds:
            row=cr[i]; long.append({"geometry_id":gid,"wavelength_nm":row["wavelength_nm"],"polarization":row["polarization"],"lf_eta_plus1":float(L[te[i],5]),"calibrated_eta_plus1":means["LF_global_bias"],"ridge_eta_plus1":pred_value(i,"LF_ridge_residual"),"residual_mlp_eta_plus1":pred_value(i,"corrected_residual_mlp"),"cnn_eta_plus1":pred_value(i,"circular_cnn"),"direct_model_eta_plus1":pred_value(i,"direct_mlp")})
    # Normalize and freeze role scores.
    ids=list(agg); fields=["residual_tail_score","performance_score","ps_risk_score","nearest_hf16_distance","lf_response_distance","model_rank_variance","predicted_ps_contrast","pairwise_model_reversal_proxy","geometry_span"]
    for f in fields:
        v=norm([float(agg[g][f] or 0) for g in ids]);
        for g,x in zip(ids,v): agg[g][f+"_norm"]=float(x)
    for g in ids:
        a=agg[g];
        a["ranking_ambiguity_score"]=float(0.50*a["model_rank_variance_norm"]+0.30*a["performance_score_norm"]+0.20*a["pairwise_model_reversal_proxy_norm"])
        a["residual_tail_role_score"]=float(0.35*a["residual_tail_score_norm"]+0.25*a["lf_response_distance_norm"]+0.20*a["pairwise_model_reversal_proxy_norm"]+0.20*a["model_rank_variance_norm"])
        a["polarization_stress_role_score"]=float(0.70*a["ps_risk_score_norm"]+0.20*a["predicted_ps_contrast_norm"]+0.10*a["residual_tail_score_norm"])
        a["coverage_control_role_score"]=float(0.55*a["nearest_hf16_distance_norm"]+0.25*a["lf_response_distance_norm"]+0.20*a["geometry_span_norm"])
        a["ranking_champion_stress_role_score"]=float(0.50*a["ranking_ambiguity_score"]+0.30*a["performance_score_norm"]+0.20*(1-a["nearest_hf16_distance_norm"]))
    def choose(rolefield,used):
        return sorted((agg[g] for g in ids if g not in used),key=lambda a:(-float(a[rolefield]),a["geometry_hash"]))[0]
    used=set(); roles=[]
    for role,field in [("RESIDUAL-TAIL","residual_tail_role_score"),("RANKING-CHAMPION-STRESS","ranking_champion_stress_role_score"),("POLARIZATION-STRESS","polarization_stress_role_score"),("COVERAGE-CONTROL","coverage_control_role_score")]:
        a=choose(field,used); used.add(a["geometry_id"]); a["acquisition_role"]=role; roles.append(a)
    role_ids={a["geometry_id"] for a in roles}
    for a in agg.values():
        if a["geometry_id"] not in role_ids:a["acquisition_role"]="backup"
    backups=sorted((a for a in agg.values() if a["geometry_id"] not in role_ids),key=lambda a:(-(0.35*a["residual_tail_role_score"]+0.30*a["ranking_champion_stress_role_score"]+0.20*a["polarization_stress_role_score"]+0.15*a["coverage_control_role_score"]),a["geometry_hash"]))[:8]
    primary4=[{**a,"selection_tier":"Primary4","expected_information_rationale":"role-diverse zero-solver proxy selection"} for a in roles]
    first6=primary4+[{**a,"selection_tier":"first6_backup"} for a in backups[:2]]; first8=first6+[{**a,"selection_tier":"first8_backup"} for a in backups[2:4]]
    all_candidates=[]
    for a in agg.values(): all_candidates.append({**a,"selection_tier":"Primary4" if a["geometry_id"] in role_ids else ("backup" if a["geometry_id"] in {x["geometry_id"] for x in backups} else "unselected"),"expected_information_rationale":"M7A deterministic role/coverage proxy"})
    flds=list(all_candidates[0]); write_csv("candidate_acquisition_features.csv",flds,all_candidates); write_csv("candidate_predictions_long.csv",list(long[0]),long)
    # Baselines and set audits.
    def baseline(key,seed=0):
        if key=="proposed": return [a["geometry_id"] for a in primary4]
        if key=="performance-only": return [a["geometry_id"] for a in sorted(agg.values(),key=lambda a:(-a["performance_score_norm"],a["geometry_hash"]))[:4]]
        if key=="residual-only": return [a["geometry_id"] for a in sorted(agg.values(),key=lambda a:(-a["residual_tail_score_norm"],a["geometry_hash"]))[:4]]
        if key=="coverage-only": return [a["geometry_id"] for a in sorted(agg.values(),key=lambda a:(-a["coverage_control_role_score"],a["geometry_hash"]))[:4]]
        return [a["geometry_id"] for a in sorted(agg.values(),key=lambda a:sha_bytes(a["geometry_hash"].encode()))[:4]]
    def set_metrics(sel):
        aa=[agg[g] for g in sel]; roleset=set()
        for a in aa:
            if a.get("acquisition_role") in ("RESIDUAL-TAIL","RANKING-CHAMPION-STRESS","POLARIZATION-STRESS","COVERAGE-CONTROL"):roleset.add(a["acquisition_role"])
        geom=[parse(a["geometry_id"]) for a in aa]; lf=[float(a["lf_eta_plus1"] or 0) for a in aa]
        d=[pair_dist(geom[i],geom[j]) for i in range(len(geom)) for j in range(i+1,len(geom))]
        return {"selected_geometry_ids":sel,"role_coverage":sorted(roleset),"role_coverage_count":len(roleset),"residual_risk_coverage":float(np.mean([a["residual_tail_score_norm"] for a in aa])),"ranking_ambiguity_coverage":float(np.mean([a["ranking_ambiguity_score"] for a in aa])),"ps_risk_coverage":float(np.mean([a["ps_risk_score_norm"] for a in aa])),"lf_response_space_coverage":float(np.std(lf)),"geometry_diversity":float(np.mean(d) if d else 0),"pairwise_redundancy":float(1-np.mean(norm(d)) if d else 0)}
    baselines={k:set_metrics(baseline(k)) for k in ("proposed","performance-only","residual-only","coverage-only","random4")}
    write_csv("baseline_acquisition_comparison.csv",["baseline"]+list(next(iter(baselines.values())).keys()),[{"baseline":k,**v} for k,v in baselines.items()])
    marg=[]
    for label,sel in [("HF16",list(hf_ids)),("HF16+Primary4",list(hf_ids)+[a["geometry_id"] for a in primary4]),("HF16+first6",list(hf_ids)+[a["geometry_id"] for a in first6]),("HF16+first8",list(hf_ids)+[a["geometry_id"] for a in first8])]:
        ac=[agg[g] for g in sel if g in agg]; marg.append({"set":label,"added_geometry_count":len(ac),"nearest_HF_distance_mean":float(np.mean([float(a["nearest_hf16_distance"] or 0) for a in ac])) if ac else 0,"residual_risk_mean":float(np.mean([a["residual_tail_score_norm"] for a in ac])) if ac else 0,"ranking_ambiguity_mean":float(np.mean([a["ranking_ambiguity_score"] for a in ac])) if ac else 0,"ps_risk_mean":float(np.mean([a["ps_risk_score_norm"] for a in ac])) if ac else 0,"lf_response_std":float(np.std([float(a["lf_eta_plus1"] or 0) for a in ac])) if ac else 0})
    write_csv("marginal_4_6_8_audit.csv",list(marg[0]),marg)
    cost=json.loads((M6OUT/"m6_solver_cost_package.json").read_text()); dump("solver_cost_and_budget_audit.json",{"source":str((M6OUT/"m6_solver_cost_package.json").relative_to(ROOT)),"source_sha256":sha(M6OUT/"m6_solver_cost_package.json"),"mpi_processes":4,"threads":1,"verified_concurrency":2,"proposal":{"Primary4":{"logical_cases":8,"median_total_hours":7.3838590788888885,"p90_total_hours":30.40280866222222,"max_total_hours":35.8882815},"first6":{"logical_cases":12,"median_total_hours":11.075788618333332,"p90_total_hours":45.604212993333334,"max_total_hours":53.83242225},"first8":{"logical_cases":16,"median_total_hours":14.767718157777777,"p90_total_hours":60.80561732444444,"max_total_hours":71.776563}},"solver_calls":0,"note":"budget only; no FDTD run"})
    dump("candidate_universe_audit.json",{"source_candidate_count":len(m6),"eligible_candidate_count":len(eligible),"excluded":excluded,"formal_HF16_overlap":sorted(set(source_ids)&hf_ids),"external_overlap":sorted(set(source_ids)&ext_ids),"sealed_target_reads":0,"external_target_reads":0,"g01_excluded":G01,"ordered_geometry":True,"duplicate_hash":False,"candidate_universe_sha256":sha_bytes("|".join(sorted(a["geometry_hash"] for a in eligible)).encode()),"preregistration_sha256":pre_sha})
    dump("selection_manifest.json",{"status":"NP_K6_M7A_TARGETED_DEVELOPMENT_ACQUISITION_READY_FOR_SOLVER_AUTHORIZATION","preregistration_sha256":pre_sha,"candidate_universe_size":len(eligible),"Primary4":primary4,"backups":backups,"first6":first6,"first8":first8,"roles_covered":sorted(a["acquisition_role"] for a in primary4),"external_authorized":False,"solver_calls":0,"external_target_reads":0,"sealed_target_reads":0})
    dump("solver_zero_audit.json",{"fdtd_run_calls":0,"lumapi_solver_run_calls":0,"new_hf_acquisition":0,"external_hf_calls":0,"sealed_hf_target_reads":0,"inverse_design":0,"checkpoint_count":0,"active_solver_processes":False})
    dump("provenance_audit.json",{"m7_preregistration_sha256":pre_sha,"m7_preregistration_path":str((OUT/"NP_K6_M7A_TARGETED_ACQUISITION_PREREG_V1.json").relative_to(ROOT)),"m7_output_source":str(M7OUT.relative_to(ROOT)),"m6_candidate_source_sha256":sha(M6OUT/"m6_candidate_scores.csv"),"external_registry_sha256":sha(ROOT/"outputs/np_k6_m5_fullk6_forward_v0/external_set_registry.json"),"solver_calls":0,"sealed_target_reads":0,"external_target_reads":0,"candidate_prediction_note":"full-development M7 fits used for design-only scoring; no HF truth for candidates"})
    dump("m7a_decision.json",{"status":"NP_K6_M7A_TARGETED_DEVELOPMENT_ACQUISITION_READY_FOR_SOLVER_AUTHORIZATION","recommended_batch":"Primary4","recommended_logical_cases":8,"recommendation":"Authorize only Primary4 if desired; first6/first8 remain expansion proposals","external_HF_authorized":False,"solver_calls":0})
    print(json.dumps({"status":"READY","preregistration_sha256":pre_sha,"candidate_universe":len(eligible),"primary4":[a["geometry_id"] for a in primary4],"backups":[a["geometry_id"] for a in backups],"first6":[a["geometry_id"] for a in first6],"first8":[a["geometry_id"] for a in first8],"solver_calls":0},sort_keys=True))
if __name__=="__main__": main()
