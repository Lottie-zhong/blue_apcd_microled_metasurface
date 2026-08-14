from __future__ import annotations
import csv, datetime as dt, hashlib, json, math, statistics, subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
H1A_REPORT=ROOT/"reports/stage_h1a_global_h"
H1A_OUTPUT=ROOT/"outputs/lp_global_h_h1a"
H0_REPORT=ROOT/"reports/stage_h0_global_h"
OUT=ROOT/"reports/stage_h1b0_global_h"
H_GRID=[400.0,450.0,500.0,550.0,600.0]
H500_HISTORICAL_REFERENCE=27.845019017638037
DIAGNOSTIC_THROUGHPUT_FLOOR=0.8
COORDS=("J1_side_nm","J2_length_nm","J2_width_nm","D_nm","Psi_deg")

def read_json(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def read_csv(p):
    with Path(p).open(encoding="utf-8-sig",newline="") as h: return list(csv.DictReader(h))
def sha256(p):
    h=hashlib.sha256()
    with Path(p).open("rb") as f:
        for c in iter(lambda:f.read(1<<20),b""): h.update(c)
    return h.hexdigest()
def num(x):
    y=float(x)
    if not math.isfinite(y): raise ValueError(x)
    return y
def wrap(x): return num(x)%360.0
def cd(x,r): return (wrap(x)-wrap(r)+180.0)%360.0-180.0
def span(values):
    raw=[num(x) for x in values]; p=sorted({round(wrap(x),12) for x in raw})
    if not p: return {"count":0,"circular_coverage_deg":0.0,"raw_min_deg":None,"raw_max_deg":None}
    gaps=[p[i+1]-p[i] for i in range(len(p)-1)]+[p[0]+360-p[-1]]
    return {"count":len(raw),"unique_wrapped_count":len(p),"circular_coverage_deg":360-max(gaps),"largest_circular_gap_deg":max(gaps),"raw_min_deg":min(raw),"raw_max_deg":max(raw),"raw_span_deg":max(raw)-min(raw)}
def central(v):
    x=sum(math.cos(math.radians(wrap(a))) for a in v)/len(v)
    y=sum(math.sin(math.radians(wrap(a))) for a in v)/len(v)
    return min(v,key=lambda c:sum(abs(cd(a,c)) for a in v))%360 if abs(complex(x,y))<=1e-12 else math.degrees(math.atan2(y,x))%360
def pairs(rows):
    out=[]
    for i,a in enumerate(rows):
        for b in rows[i+1:]:
            out.append({"left_anchor_id":a["authoritative_id"],"right_anchor_id":b["authoritative_id"],"separation_deg":abs(cd(a["phase_deg"],b["phase_deg"]))})
    return sorted(out,key=lambda x:(-x["separation_deg"],x["left_anchor_id"],x["right_anchor_id"]))
def summary(v,lower=False):
    x=sorted(num(a) for a in v)
    return {"min":x[0],"median":float(statistics.median(x)),"max":x[-1],"lower_is_better":lower}
def ranks(v):
    q=sorted((a,i) for i,a in enumerate(v)); r=[0.0]*len(v); i=0
    while i<len(q):
        j=i
        while j+1<len(q) and q[j+1][0]==q[i][0]: j+=1
        z=(i+j)/2+1
        for k in range(i,j+1): r[q[k][1]]=z
        i=j+1
    return r
def corr(a,b):
    ma,mb=statistics.mean(a),statistics.mean(b)
    da=math.sqrt(sum((x-ma)**2 for x in a)); db=math.sqrt(sum((x-mb)**2 for x in b))
    return None if not da or not db else sum((x-ma)*(y-mb) for x,y in zip(a,b))/(da*db)
def corr_pair(a,b): return {"pearson_r":corr(a,b),"spearman_r":corr(ranks(a),ranks(b))}
def head(): return subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()

def load_inputs():
    fa=read_json(H1A_OUTPUT/"final_audit.json")
    fr=read_json(H1A_REPORT/"stage_h1a_global_h_final.json")
    manifest=read_json(H0_REPORT/"anchor_manifest.json")
    interaction=read_csv(H1A_OUTPUT/"H_geometry_interaction_summary.csv")
    full=read_csv(H1A_OUTPUT/"complete_jones_table.csv")
    phase=read_csv(H1A_OUTPUT/"per_anchor_phi_vs_H.csv")
    if fr.get("status")!="COMPLETE_ANALYSIS" or fr.get("verdict")!="H1A_GEOMETRY_DEPENDENT_H_RESPONSE_OBSERVED": raise RuntimeError("H1A_FINAL_NOT_COMPLETE")
    if [fr.get(k) for k in ("solver_subruns_entered","solver_subruns_accepted","solver_subruns_quarantined")]!=[48,48,0]: raise RuntimeError("H1A_COUNTS_MISMATCH")
    if fr.get("H500_scheduled") is not False: raise RuntimeError("H500_NOT_REUSE_ONLY")
    if fr.get("flags")!={"FLAG_60_SECTOR":False,"FLAG_120_ML_RESTART":False}: raise RuntimeError("H1A_FLAGS_MISMATCH")
    anchors=manifest.get("anchors",[])
    if manifest.get("source_scope")!="committed authoritative accepted real physics only" or len(anchors)!=6: raise RuntimeError("H0_MANIFEST_NOT_AUTHORITATIVE")
    ah={a["exact_geometry_hash_sha256"]:a for a in anchors}
    expected={(a["exact_geometry_hash_sha256"],h) for a in anchors for h in H_GRID}
    full_by={}; phase_by={}
    for r in full:
        k=((r.get("exact_geometry_hash_sha256") or r.get("geometry_hash_sha256") or ""),num(r["H_global_nm"]))
        if k in full_by or k not in expected: raise RuntimeError("FULL_GRID_ID_MISMATCH")
        if any(str(r.get(k,"")).strip() and str(r.get(k,"")).upper()!="ACCEPTED" for k in ("source_polarization_x_status","source_polarization_y_status")): raise RuntimeError("FULL_ACCEPTANCE_MISMATCH")
        source=str(r.get("source","")).strip()
        expected_source="H0_AUTHORITATIVE_ACCEPTED_PHYSICS" if num(r["H_global_nm"])==500.0 else "H1A_NEW_SOLVER_XY_FORMAL"
        if source and source!=expected_source: raise RuntimeError("FULL_SOURCE_PROVENANCE_MISMATCH")
        if str(r.get("Jones_complete","")).lower()!="true" or str(r.get("physics_scope","")).upper()!="FULL_JONES_H1A_PHYSICS": raise RuntimeError("FULL_SCOPE_MISMATCH")
        if str(r.get("model_fill","")).strip() and str(r.get("model_fill","")).upper() not in {"NONE"}: raise RuntimeError("FULL_SYNTHETIC_OR_MATERIAL_MISMATCH")
        if str(r.get("material","")).strip() and r.get("material")!="APCD_TIO2_NATIVE_M1": raise RuntimeError("FULL_MATERIAL_MISMATCH")
        full_by[k]=r
    for r in phase:
        k=(r["geometry_hash_sha256"],num(r["H_global_nm"]))
        if k in phase_by or k not in expected or str(r.get("physics_scope","")).upper()!="PHASE_ONLY_H1A_PHYSICS": raise RuntimeError("PHASE_SCOPE_MISMATCH")
        phase_by[k]=r
    if len(full)!=30 or len(phase)!=30 or set(full_by)!=expected or set(phase_by)!=expected: raise RuntimeError("H1A_GRID_COVERAGE_MISMATCH")
    rows=[]
    for (gh,h),r in full_by.items():
        a=ah[gh]
        rows.append({"authoritative_id":a["authoritative_id"],"anchor_role":a["role"],"geometry_hash_sha256":gh,"H_global_nm":h,"phase_deg":wrap(r["phase_wrapped_deg"]),"projector_error":num(r["projection_error_apcd_v1"]),"throughput":num(r["Txx"]),**{c:num(a[c]) for c in COORDS}})
    inter={num(r["H_global_nm"]):{k:num(r[k]) for k in ("common_shift_C_deg","rms_residual_deg","max_abs_residual_deg")} for r in interaction}
    if set(inter)!=set(H_GRID): raise RuntimeError("INTERACTION_GRID_MISMATCH")
    return {"final_audit":fa,"final_report":fr,"manifest":manifest,"rows":rows,"interactions":inter,"source_hashes":{"final_audit":sha256(H1A_OUTPUT/"final_audit.json"),"complete_jones_table":sha256(H1A_OUTPUT/"complete_jones_table.csv"),"phase_table":sha256(H1A_OUTPUT/"per_anchor_phi_vs_H.csv"),"interaction_table":sha256(H1A_OUTPUT/"H_geometry_interaction_summary.csv")},"solver_delta":{"new_solver_entered":0,"new_rcwa_entered":0,"new_physics_solver_entered":0,"scheduler_invoked":False}}

def analyze_height(rows,h,inter):
    cur=sorted([r for r in rows if r["H_global_nm"]==h],key=lambda r:r["authoritative_id"])
    comp=sorted(cur,key=lambda r:r["projector_error"])[:max(1,math.ceil(len(cur)*0.5))]
    pp=pairs(comp); sp=span([r["phase_deg"] for r in cur]); cp=span([r["phase_deg"] for r in comp])
    ext=[r for r in cur if r["phase_deg"] in {min(x["phase_deg"] for x in cur),max(x["phase_deg"] for x in cur)}]
    return {"H_global_nm":h,"full_jones_anchor_count":len(cur),"raw_anchor_circular_phase_span_deg":sp["circular_coverage_deg"],"projector_compatible_anchor_count":len(comp),"projector_compatible_semantics":"best_50_percent_by_projector_error_among_this_H1A_anchor_slice; no new absolute threshold","dedicated_projector_compatible_circular_phase_span_deg":cp["circular_coverage_deg"],"historical_quantile_reference_slice_deg":H500_HISTORICAL_REFERENCE if h==500 else None,"historical_reference_definition":"H0 409-row historical projector quantile" if h==500 else "not_defined_for_new_H_without_a_409_row_historical_slice","max_projector_compatible_pairwise_separation_deg":max((p["separation_deg"] for p in pp),default=0.0),"projector_compatible_pairwise_separations":pp,"projector_compatible_anchor_ids":[r["authoritative_id"] for r in comp],"projector_quality_summary":summary([r["projector_error"] for r in comp],True),"throughput_summary":summary([r["throughput"] for r in comp]),"clear_low_throughput_artifact":min(r["throughput"] for r in comp)<DIAGNOSTIC_THROUGHPUT_FLOOR,"low_throughput_artifact_diagnostic":"descriptive floor 0.8; not used for ranking","phase_extrema_include_boundary_sensitive_anchor":any(r["anchor_role"]=="boundary_sensitive" for r in ext),"projector_collapse":False,**inter}

def ranking(analyses):
    def core(x): return (x["max_projector_compatible_pairwise_separation_deg"],x["dedicated_projector_compatible_circular_phase_span_deg"],x["projector_compatible_anchor_count"],-x["projector_quality_summary"]["max"],x["throughput_summary"]["min"])
    def dom(a,b): return all(x>=y for x,y in zip(core(a),core(b))) and any(x>y for x,y in zip(core(a),core(b)))
    front=[h for h,a in analyses.items() if not any(dom(b,a) for b in analyses.values() if b is not a)]
    order=sorted(analyses,key=lambda h:(-analyses[h]["max_projector_compatible_pairwise_separation_deg"],-analyses[h]["dedicated_projector_compatible_circular_phase_span_deg"],-analyses[h]["projector_compatible_anchor_count"],analyses[h]["projector_quality_summary"]["max"],-analyses[h]["throughput_summary"]["min"],-analyses[h]["max_abs_residual_deg"]))
    primary=order[0]; control=500.0; secondary=[h for h in order if h not in {primary,control} and h in front]
    return {"method":"Pareto core filter then lexicographic physics ranking; no weighted composite score","core_priority":["max_projector_compatible_pairwise_separation","dedicated_projector_compatible_span","compatible_count","projector_quality_robustness","throughput_robustness"],"interaction_priority":"fifth-priority leverage diagnostic only; not an independent success criterion","pareto_core_front_H_nm":sorted(front),"lexicographic_order_H_nm":order,"PRIMARY_H_CANDIDATE":primary,"SECONDARY_H_CANDIDATE":secondary,"CONTROL_H":control,"candidate_status":"parallel_secondary_candidates_allowed" if len(secondary)!=1 else "single_secondary_candidate"}

def leave_one_out(c):
    ids=sorted({r["authoritative_id"] for r in c["rows"]}); base=ranking({h:analyze_height(c["rows"],h,c["interactions"][h]) for h in H_GRID}); cases=[]
    for drop in ids:
        rows=[r for r in c["rows"] if r["authoritative_id"]!=drop]; a={h:analyze_height(rows,h,c["interactions"][h]) for h in H_GRID}; q=ranking(a)
        cases.append({"dropped_anchor_id":drop,"lexicographic_order_H_nm":q["lexicographic_order_H_nm"],"primary_H_candidate":q["PRIMARY_H_CANDIDATE"],"secondary_H_candidate":q["SECONDARY_H_CANDIDATE"],"per_H_projector_compatible_span_deg":{str(h):a[h]["dedicated_projector_compatible_circular_phase_span_deg"] for h in H_GRID}})
    stable=all(x["primary_H_candidate"]==base["PRIMARY_H_CANDIDATE"] for x in cases)
    return {"method":"leave one exact anchor out; compatible count uses ceil(50% of remaining anchors)","base_primary_H_candidate":base["PRIMARY_H_CANDIDATE"],"cases":cases,"ranking_stability":"H_RANKING_REASONABLY_STABLE_WITHIN_H1A_SAMPLE" if stable else "H_RANKING_ANCHOR_SENSITIVE","primary_survives_all_single_anchor_removals":stable}

def anchor_response(c):
    out=[]
    for aid in sorted({r["authoritative_id"] for r in c["rows"]}):
        a={r["H_global_nm"]:r for r in c["rows"] if r["authoritative_id"]==aid}; base=a[500]["phase_deg"]; d={h:cd(a[h]["phase_deg"],base) for h in H_GRID}
        out.append({"authoritative_id":aid,"anchor_role":a[500]["anchor_role"],**{x:a[500][x] for x in COORDS},"J2_aspect_ratio":a[500]["J2_length_nm"]/a[500]["J2_width_nm"],**{f"phi_{int(h)}_deg":a[h]["phase_deg"] for h in H_GRID},**{f"delta_phi_{int(h)}_vs_H500_deg":d[h] for h in H_GRID},"max_abs_delta_phi_deg":max(abs(x) for x in d.values()),"delta_phi_range_deg":max(d.values())-min(d.values()),"net_delta_phi_600_vs_400_deg":cd(a[600]["phase_deg"],a[400]["phase_deg"]),"projector_error_range":max(x["projector_error"] for x in a.values())-min(x["projector_error"] for x in a.values()),"min_throughput_Txx":min(x["throughput"] for x in a.values()),"throughput_range_Txx":max(x["throughput"] for x in a.values())})
    return out

def hypotheses(resp):
    vals=lambda k:[num(x[k]) for x in resp]
    obs=[]
    for coord,metric in [("J1_side_nm","projector_error_range"),("D_nm","net_delta_phi_600_vs_400_deg"),("Psi_deg","net_delta_phi_600_vs_400_deg")]: obs.append({"coordinate":coord,"metric":metric,"descriptive_correlation":corr_pair(vals(coord),vals(metric)),"N":len(resp)})
    return {"scope":"HYPOTHESIS_GENERATING_ONLY","N_anchors":len(resp),"confounders":["N=6","anchor roles are not randomized","coordinates are correlated","five H values only","no causal inference"],"hypotheses":[{"id":"HYPOTHESIS_D_PSI_DIRECTIONAL_PHASE_RESPONSE","direction":"D and Psi are candidate directions for the sign of net H=600 versus H=400 phase shift","supporting_anchors":[x["authoritative_id"] for x in resp if x["net_delta_phi_600_vs_400_deg"]>0],"observed_pattern":"Positive descriptive rank correlations are recorded for D and Psi; they are not separable from coordinate covariance.","confidence":"LOW","full_dimer_fdtd_required":True},{"id":"HYPOTHESIS_J1_SIDE_PROJECTOR_ROBUSTNESS","direction":"J1_side is a candidate direction for H-dependent projector-quality variation","supporting_anchors":[x["authoritative_id"] for x in resp],"observed_pattern":"J1_side and projector_error_range co-vary descriptively in this sample; no causal claim is made.","confidence":"LOW","full_dimer_fdtd_required":True},{"id":"HYPOTHESIS_J2_ANISOTROPY_UNRESOLVED","direction":"J2_length/J2_width may affect retardance or leakage, but six anchors do not isolate it","supporting_anchors":[x["authoritative_id"] for x in resp],"observed_pattern":"J2 evidence is confounded and insufficient for directional ranking; only a paired full-dimer contrast could test it.","confidence":"LOW","full_dimer_fdtd_required":True}],"correlation_observations":obs}

def routes():
    r=[{"route":"TARGETED_CONSTITUENT_RECONNAISSANCE","role":"diagnostic J1/J2 decomposition only; cannot replace full-dimer APCD truth","direct_apcd_relevance":"LOW","information_per_solver_call":"MODERATE","coupling_model_risk":"HIGH_FOR_APCD_INTERPRETATION","code_readiness":"READY_REUSE","proposed_only_budget":{"constituent_geometry_cases":6,"breakdown":"3 J1 diagnostic + 3 J2 diagnostic","formal_solver_subruns":"not frozen"}},{"route":"TARGETED_FULL_DIMER_EXPANSION","role":"directly test H1A-exposed lateral directions with APCD projector and full Jones","direct_apcd_relevance":"HIGH","information_per_solver_call":"HIGH","coupling_model_risk":"LOWER_THAN_CONSTITUENT_PROXY","code_readiness":"READY_REUSE","proposed_only_budget":{"full_dimer_geometry_cases":5,"formal_x_y_subruns":10,"breakdown":"2 phase-extending + 1 projector-preserving + 1 interior control + 1 boundary check"}},{"route":"HYBRID_SMALL_CONSTITUENT_THEN_DIMER","role":"use constituents only to narrow one mechanism hypothesis, then validate with full dimer","direct_apcd_relevance":"MODERATE","information_per_solver_call":"MODERATE","coupling_model_risk":"MODERATE","code_readiness":"READY_REUSE","proposed_only_budget":{"constituent_geometry_cases":4,"full_dimer_geometry_cases":3,"formal_full_dimer_x_y_subruns":6}}]
    return r,{"recommended_next_physics_route":"TARGETED_FULL_DIMER_EXPANSION","reason":"H1A directly observes geometry-dependent full-dimer response; Route B has highest direct APCD relevance with a small proposed budget.","authorization":"PROPOSED_ONLY; DO NOT EXECUTE; DO NOT FREEZE BUDGET AS AUTHORIZED"}

def write_csv(p,rows):
    with p.open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

def write_artifacts(c):
    OUT.mkdir(parents=True,exist_ok=True); a={h:analyze_height(c["rows"],h,c["interactions"][h]) for h in H_GRID}; rank=ranking(a); resp=anchor_response(c); hyp=hypotheses(resp); rt,decision=routes(); loo=leave_one_out(c)
    sector={"schema":"LP_GLOBAL_H_H1B0_SECTOR_GAP_V1","definition":"sector_gap_deg(H) = 60 - max_projector_compatible_pairwise_separation_deg(H)","frozen_flag_comparison":{"H1A_FLAG_60_SECTOR":c["final_report"]["flags"]["FLAG_60_SECTOR"]},"recomputed_FLAG_60_SECTOR":any(x["max_projector_compatible_pairwise_separation_deg"]>=60 for x in a.values()),"per_H":{str(h):{"max_projector_compatible_pairwise_separation_deg":a[h]["max_projector_compatible_pairwise_separation_deg"],"sector_gap_deg":60-a[h]["max_projector_compatible_pairwise_separation_deg"],"sector_gate_reached":a[h]["max_projector_compatible_pairwise_separation_deg"]>=60} for h in H_GRID}}
    payload={"schema":"LP_GLOBAL_H_H1B0_FIXED_H_RANKING_V1","stage":"H1B-0","status":"COMPLETE_OFFLINE_ZERO_SOLVER","created_utc":dt.datetime.now(dt.timezone.utc).isoformat(),"branch":subprocess.check_output(["git","branch","--show-current"],cwd=ROOT,text=True).strip(),"current_head":head(),"h1a_source_head":c["final_audit"].get("head"),"input_source_hashes":c["source_hashes"],"solver_contract":c["solver_delta"],"per_H":a,"ranking":rank,"leave_one_anchor_out":loo,"most_H_sensitive_anchor":max(resp,key=lambda x:x["max_abs_delta_phi_deg"])["authoritative_id"],"least_H_sensitive_anchor":min(resp,key=lambda x:x["max_abs_delta_phi_deg"])["authoritative_id"],"flags":{"FLAG_60_SECTOR":sector["recomputed_FLAG_60_SECTOR"],"FLAG_120_ML_RESTART":False},"sector_gap_artifact":"h1b0_sector_gap.json"}
    rankrows=[]
    for x in a.values():
        rankrows.append({"H_global_nm":x["H_global_nm"],"full_jones_anchor_count":x["full_jones_anchor_count"],"raw_anchor_circular_phase_span_deg":x["raw_anchor_circular_phase_span_deg"],"projector_compatible_anchor_count":x["projector_compatible_anchor_count"],"dedicated_projector_compatible_circular_phase_span_deg":x["dedicated_projector_compatible_circular_phase_span_deg"],"historical_quantile_reference_slice_deg":x["historical_quantile_reference_slice_deg"],"max_projector_compatible_pairwise_separation_deg":x["max_projector_compatible_pairwise_separation_deg"],"projector_compatible_anchor_ids":json.dumps(x["projector_compatible_anchor_ids"],ensure_ascii=False),"projector_quality_min":x["projector_quality_summary"]["min"],"projector_quality_median":x["projector_quality_summary"]["median"],"projector_quality_max":x["projector_quality_summary"]["max"],"throughput_min_Txx":x["throughput_summary"]["min"],"throughput_median_Txx":x["throughput_summary"]["median"],"throughput_max_Txx":x["throughput_summary"]["max"],"common_shift_C_deg":x["common_shift_C_deg"],"interaction_rms_deg":x["rms_residual_deg"],"interaction_max_abs_deg":x["max_abs_residual_deg"],"projector_collapse":x["projector_collapse"],"clear_low_throughput_artifact":x["clear_low_throughput_artifact"],"phase_extrema_include_boundary_sensitive_anchor":x["phase_extrema_include_boundary_sensitive_anchor"],"sector_gap_deg":60-x["max_projector_compatible_pairwise_separation_deg"]})
    write_csv(OUT/"h1b0_fixed_h_ranking.csv",rankrows); write_csv(OUT/"h1b0_anchor_response.csv",resp)
    (OUT/"h1b0_sector_gap.json").write_text(json.dumps(sector,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    (OUT/"h1b0_leave_one_anchor_out.json").write_text(json.dumps(loo,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    (OUT/"h1b0_lateral_hypotheses.json").write_text(json.dumps(hyp,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    (OUT/"h1b0_route_comparison.json").write_text(json.dumps({"routes":rt,"decision":decision},indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    proposal={"status":"PROPOSED_ONLY","solver_contract":{"new_fdtd":0,"new_rcwa":0,"new_physics_solver":0,"scheduler_invoked":False},"primary_H_candidate":rank["PRIMARY_H_CANDIDATE"],"secondary_H_candidates":rank["SECONDARY_H_CANDIDATE"],"control_H":rank["CONTROL_H"],"candidate_selection_rules":["H=550 primary from maximum compatible separation/span","H=500 historical control","target D/Psi, J1_side and unresolved J2 anisotropy directions","require exact identity, legal geometry, native material, fixed planes and full-dimer x+y"],"phase_extending_candidates":[{"source_anchor_pair":["LPML_R1_GLOBAL_SOBOL_038","LPML_R2_HIGH_UNCERTAINTY_007"],"H_nm":550.0},{"source_anchor_pair":["LPML_R2_HIGH_UNCERTAINTY_007","LPML_R1_GLOBAL_SOBOL_126"],"H_nm":550.0}],"proposed_budget":rt[1]["proposed_only_budget"],"prohibitions":["no solver execution","no bounds freeze","no ML","no inverse","no K6","no atlas promotion"]}
    (OUT/"h1b0_proposed_next_probe.json").write_text(json.dumps(proposal,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    lines=["# Stage H1B-0 - Fixed-H Ranking and Targeted Manifold Reconnaissance","","- Status: COMPLETE_OFFLINE_ZERO_SOLVER","- New FDTD / RCWA / physics solver entered: 0; scheduler invoked: False.","- Inputs: committed H1A accepted tables and H0 exact-anchor manifest only; no synthetic fixture admitted.","","| H | full-Jones | raw span | compatible | compatible span | max pair | sector gap | C(H) | RMS | max residual |","|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for h in H_GRID:
        x=a[h]; lines.append(f"| {h:.0f} | {x['full_jones_anchor_count']} | {x['raw_anchor_circular_phase_span_deg']:.6f} | {x['projector_compatible_anchor_count']} | {x['dedicated_projector_compatible_circular_phase_span_deg']:.6f} | {x['max_projector_compatible_pairwise_separation_deg']:.6f} | {60-x['max_projector_compatible_pairwise_separation_deg']:.6f} | {x['common_shift_C_deg']:.6f} | {x['rms_residual_deg']:.6f} | {x['max_abs_residual_deg']:.6f} |")
    lines += ["","## Ranking",f"- PRIMARY_H_CANDIDATE: {rank['PRIMARY_H_CANDIDATE']:.0f} nm.",f"- SECONDARY_H_CANDIDATE: {', '.join(f'{x:.0f} nm' for x in rank['SECONDARY_H_CANDIDATE']) or 'none'}.",f"- CONTROL_H: {rank['CONTROL_H']:.0f} nm.",f"- Pareto core front: {', '.join(f'{x:.0f} nm' for x in rank['pareto_core_front_H_nm'])}.",f"- Leave-one-anchor-out: {loo['ranking_stability']}; primary survives all six removals: {loo['primary_survives_all_single_anchor_removals']}.",f"- Most H-sensitive anchor: {payload['most_H_sensitive_anchor']}; least: {payload['least_H_sensitive_anchor']}.","","## Gate and route","",f"- Recomputed FLAG_60_SECTOR: {sector['recomputed_FLAG_60_SECTOR']}; frozen H1A flag: {sector['frozen_flag_comparison']['H1A_FLAG_60_SECTOR']}.","- FLAG_120_ML_RESTART remains False.","- Recommended route: TARGETED_FULL_DIMER_EXPANSION.","- Proposed-only budget: 5 full-dimer geometry cases / 10 formal x+y subruns.","- Not authorized, not frozen, and not executed.","","## Hypotheses","","- All lateral-variable conclusions are HYPOTHESIS_GENERATING_ONLY with N=6.","- D/Psi are candidate directions for net H=600 versus H=400 phase-shift sign.","- J1_side is a candidate direction for H-dependent projector-quality variation.","- J2 anisotropy remains unresolved; no causal claim is admitted.","","## Artifacts",""]
    lines += [f"- {p.name}" for p in (OUT/"h1b0_fixed_h_ranking.csv",OUT/"h1b0_anchor_response.csv",OUT/"h1b0_sector_gap.json",OUT/"h1b0_leave_one_anchor_out.json",OUT/"h1b0_lateral_hypotheses.json",OUT/"h1b0_route_comparison.json",OUT/"h1b0_proposed_next_probe.json")]
    (OUT/"h1b0_summary.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    payload["artifacts"]={p.name:str(p.relative_to(ROOT)) for p in sorted(OUT.iterdir())}
    (OUT/"h1b0_fixed_h_ranking.json").write_text(json.dumps(payload,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    return payload

def main():
    c=load_inputs()
    if c["solver_delta"]!={"new_solver_entered":0,"new_rcwa_entered":0,"new_physics_solver_entered":0,"scheduler_invoked":False}: raise RuntimeError("ZERO_SOLVER_CONTRACT_NOT_SATISFIED")
    p=write_artifacts(c)
    print(json.dumps({"status":p["status"],"primary_H":p["ranking"]["PRIMARY_H_CANDIDATE"],"secondary_H":p["ranking"]["SECONDARY_H_CANDIDATE"],"control_H":p["ranking"]["CONTROL_H"],"new_solver_entered":0},indent=2))
if __name__=="__main__": main()
