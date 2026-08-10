import argparse,csv,datetime as dt,importlib.util,json,math,sys
from pathlib import Path
R=Path(__file__).resolve().parents[1];O=R/"outputs/lp_global_h_h1a";P=R/"reports/stage_h1a_global_h";sys.path.insert(0,str(R))
def lm(p,n):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);assert s and s.loader;s.loader.exec_module(m);return m
A=lm(R/"scripts/lp_global_h_h1a_probe_v1.py","h1a_off");Z=lm(R/"scripts/lp_global_h_h0_audit_v1.py","h0_off")
def num(v):
 try:v=float(v);return v if math.isfinite(v) else None
 except(TypeError,ValueError):return None
def yes(v):return str(v).strip().upper() in {"1","TRUE","YES","PASS","ACCEPTED","COMPLETE"}
def rd(p,d=None):return json.loads(p.read_text(encoding="utf8")) if p.exists() else d
def cr(p):
 if not p.exists():return []
 with p.open(encoding="utf8-sig",newline="") as f:return list(csv.DictReader(f))
def acc(r):
 for k in("accepted","authoritative_accepted","acceptance_status","status"):
  if k in r and str(r[k]).strip():return yes(r[k])
 return True
def ph(r):
 for k in("phi_arg_txx_deg","phase_wrapped_deg","phase_deg","phase"):
  x=num(r.get(k))
  if x is not None:return x%360
 a,b=num(r.get("txx_real")),num(r.get("txx_imag"));return None if a is None or b is None else math.degrees(math.atan2(b,a))%360
def key(r):return(str(r.get("geometry_hash_sha256") or r.get("exact_geometry_hash_sha256") or r.get("authoritative_id") or ""),num(r.get("H_global_nm",r.get("height_nm"))),str(r.get("polarization") or ""))
def uniq(rows):
 d={}
 for r in rows:
  if not acc(r):continue
  k=key(r);old=d.get(k)
  if old is None or(str(old.get("status","")).upper()!="ACCEPTED" and str(r.get("status","")).upper()=="ACCEPTED"):d[k]=dict(r)
 return list(d.values())
def pe(r):
 return not(yes(r.get("x_only")) or str(r.get("evidence_scope","")).upper().startswith("PHASE_ONLY") or ("projector_eligible" in r and str(r["projector_eligible"]).strip() and not yes(r["projector_eligible"])) or ("Jones_complete" in r and str(r["Jones_complete"]).strip() and not yes(r["Jones_complete"]))) and yes(r.get("Jones_complete",True))
def norm(rows,full=False):
 z=[]
 for r in uniq(rows):
  h,p=num(r.get("H_global_nm",r.get("height_nm"))),ph(r)
  if h is not None and p is not None and(not full or pe(r)):
   x=dict(r);x.update(H_global_nm=h,phi_arg_txx_deg=p);z.append(x)
 return z
def analyze(pr,fr,ref=500.0):
 p,f=norm(pr),norm(fr,True);refs={key(r)[0]:r for r in p if key(r)[1]==ref};tab=[]
 for r in p:
  q=refs.get(key(r)[0]);x=dict(r);x.update(delta_phi_vs_H500_deg=A.circ_diff(r["phi_arg_txx_deg"],q["phi_arg_txx_deg"]) if q else None,x_only_excluded_from_projector=True);tab.append(x)
 ii=[];ss=[]
 for h in sorted({r["H_global_nm"] for r in p}):
  a=[r for r in tab if r["H_global_nm"]==h];v=[r for r in a if r["delta_phi_vs_H500_deg"] is not None];d=[r["delta_phi_vs_H500_deg"] for r in v];c=A.circular_central(d) if d else None;rr=A.circular_residuals(d,c) if d and c is not None else [];ff=[r for r in f if r["H_global_nm"]==h];rank=sorted(ff,key=lambda r:num(r.get("projector_error_apcd_v1",r.get("projection_error"))) or 1e99);co=rank[:max(1,math.ceil(len(rank)*.5))] if rank else [];pairs=[abs(A.circ_diff(x["phi_arg_txx_deg"],y["phi_arg_txx_deg"])) for i,x in enumerate(co) for y in co[i+1:]]
  ii.append({"H_global_nm":h,"common_shift_C_deg":c,"rms_residual_deg":math.sqrt(sum(x*x for x in rr)/len(rr)) if rr else None,"max_abs_residual_deg":max((abs(x) for x in rr),default=None),"anchor_residuals_deg":{key(r)[0]:x for r,x in zip(v,rr)}})
  ss.append({"H_global_nm":h,"phase_only_count":len(a),"anchor_phase_circular_coverage_deg":Z.circular_phase_span([r["phi_arg_txx_deg"] for r in a])["circular_coverage_deg"],"projector_compatible_count":len(co),"projector_compatible_phase_circular_coverage_deg":Z.circular_phase_span([r["phi_arg_txx_deg"] for r in co])["circular_coverage_deg"] if co else 0.0,"projector_compatible_pair_separations_deg":pairs,"x_only_rows_in_phase_scope_excluded":len(a)-len(ff)})
 flags={"FLAG_60_SECTOR":any(max(x["projector_compatible_pair_separations_deg"],default=0)>=60 for x in ss),"FLAG_120_ML_RESTART":any(x["projector_compatible_phase_circular_coverage_deg"]>=120 for x in ss)}
 return {"schema":"LP_GLOBAL_H_H1A_OFFLINE_ANALYSIS_RESULT_V1","reference_height_nm":ref,"authoritative_phase_row_count":len(p),"authoritative_projector_row_count":len(f),"heights_observed_nm":sorted({r["H_global_nm"] for r in p}),"per_anchor_phi_table":tab,"interactions":ii,"fixed_height_spans":ss,"flags":flags,"verdict":"H1A_INCONCLUSIVE","references":{"H500_dedicated_probe_projector_compatible_deg":A.H500_DEDICATED_REFERENCE_DEG,"H500_historical_quantile_reference_deg":A.H500_HISTORICAL_QUANTILE_REFERENCE_DEG,"separate":True},"scope":{"x_only_phase_allowed":True,"x_only_projector_allowed":False,"full_jones_requires_xy":True,"synthetic_rows_are_not_physics":True}}
def matrix():
 q=[("single J1 square builder","READY_REUSE","scripts/lp_ml_inverse_stage1_fdt_validation_runner_v1.py:72-88"),("single J2 rectangle builder","READY_REUSE","scripts/lp_ml_inverse_stage1_fdt_validation_runner_v1.py:72-88"),("x/y complex transmission extractor","READY_REUSE","scripts/lp_ml_inverse_stage1_fdt_validation_runner_v1.py:99-115"),("phase/amplitude atlas utility","NOT_APPLICABLE","atlas forbidden in zero-solver stage"),("geometry legality checker","READY_REUSE","scripts/lp_5d_phase_reachability_probe_v1.py:187-217"),("direct/periodic gap checker","READY_REUSE","scripts/lp_5d_phase_reachability_probe_v1.py:191-217"),("integer dimension / half-grid center checker","READY_REUSE","scripts/lp_ml_contract_plan.py:54"),("APCD_TIO2_NATIVE_M1 registration","READY_REUSE","scripts/lp_ml_inverse_stage1_fdt_validation_runner_v1.py:27,73"),("same phase/reference convention","READY_REUSE","scripts/lp_global_h_h0_audit_v1.py and H1A physical_contract()")]
 return{"schema":"LP_GLOBAL_H_H1B_H2_ZERO_SOLVER_READINESS_MATRIX_V1","inspection_only":True,"solver_entered_new":0,"rows":[{"item":a,"status":b,"evidence":c} for a,b,c in q],"new_geometry_created":False}
def audit():
 ps=list(O.rglob("attempt_provenance*.json"));vs=[rd(p,{}) for p in ps];m=rd(O/"run_manifest.json",{}) or {};q=rd(O/"license_readiness.json",{}) or {};e=rd(O/"entered_accounting_v1.json",{}) or {};n=max(int(m.get("solver_subruns_entered",0)),int(e.get("solver_subruns_entered",0)));f=[p for p in O.rglob("*") if p.is_file() and p.suffix.lower() in{".fsp",".fspx"}];v=q.get("latest_verdict") or m.get("readiness_verdict") or "NOT_PROBED"
 return{"schema":"LP_GLOBAL_H_H1A_RUNTIME_READINESS_AUDIT_V1","branch":m.get("branch"),"head":m.get("head"),"runtime_guard":{"guard_present":A.runner_guard_path().exists(),"singleton_guard_implemented":True},"readiness_verdict":v,"historical_attempts":{"brief_stated_count":26,"live_audit_count":len(ps),"discrepancy_preserved":len(ps)!=26,"all_solver_entered_false":all(x.get("solver_entered") is False for x in vs),"all_status_failed":all(str(x.get("status","")).upper()=="FAILED" for x in vs)},"solver_accounting":{"solver_entered":n,"solver_budget_planned":48,"solver_entered_fraction":f"{n}/48","H500_scheduled":bool(m.get("H500_scheduled",False)),"new_physics_fdtd_runs":0},"h1a_fsp_fspx_count":len(f),"active_solver_snapshot":A.solver_isolation_snapshot(),"offline_pipeline_status":"READY_WAITING_AUTHORITATIVE_H1A_ACCEPTED_DATA","physics_contract_modified":False,"final_state":"H1A_OFFLINE_READY_WAITING_LICENSE_OR_MESSAGING" if v!="LUMERICAL_READY" else "H1A_OFFLINE_READY_WAITING_PHYSICS_QUEUE"}
def write():
 p,f=cr(O/"per_anchor_phi_vs_H.csv"),cr(O/"complete_jones_table.csv")
 if not p:
  an,h5=A.load_anchors();p=[];f=[]
  for a,s in zip(an,h5):
   x,y=A.h500_rows(a,s);f.append(x);p.append(y)
 r=analyze(p,f);a=audit();P.mkdir(parents=True,exist_ok=True)
 offline_contract={"schema":"LP_GLOBAL_H_H1A_OFFLINE_ANALYSIS_CONTRACT_V1","status":"READY","zero_solver":True,"required_metrics":["per_anchor_phi_vs_H","shortest_signed_circular_delta","common_shift_C","anchor_residuals","interaction_rms","interaction_max","fixed_H_anchor_coverage","fixed_H_projector_compatible_coverage","x_only_exclusion","dedicated_vs_historical_reference_separation","FLAG_60_SECTOR","FLAG_120_ML_RESTART"],"reuse":{"circular_span":"lp_global_h_h0_audit_v1.circular_phase_span","delta":"lp_global_h_h1a_probe_v1.circ_diff","common_shift":"lp_global_h_h1a_probe_v1.circular_central","residuals":"lp_global_h_h1a_probe_v1.circular_residuals"},"projector_compatible_semantics":"best_50_percent_by_projector_error_among_this_H1A_anchor_slice; no new absolute threshold","references":{"dedicated_probe":"separate from historical quantile/reference slice","historical_quantile":"separate from dedicated probe"},"current_result":r,"synthetic_fixture_path":"tests/fixtures/h1a_offline_synthetic_cases.json","physics_contract_modified":False}
 decision_contract={"schema":"LP_GLOBAL_H_H1A_DECISION_CONTRACT_V1","cases":[{"case":"CASE1","state":"H1A_COMMON_TRANSLATION_DOMINATED","when":"common translation dominated","action":"no ML or large atlas; wait Chart"},{"case":"CASE2","state":"H1A_GEOMETRY_DEPENDENT_H_RESPONSE_OBSERVED","when":"geometry dependent and FLAG_60_SECTOR=false","action":"candidate targeted constituent-manifold reconnaissance; no auto solver"},{"case":"CASE3","state":"H1A_FIXED_H_MAPPING_WORTH_CONTINUATION","when":"FLAG_60_SECTOR=true and FLAG_120_ML_RESTART=false","action":"fixed-H mapping may continue; no auto ML"},{"case":"CASE4","state":"H1A_ML_RESTART_PHYSICS_POTENTIAL","when":"FLAG_120_ML_RESTART=true","action":"requires fixed-H FDTD confirmation; no auto ML"}],"global_prohibitions":["ML","cVAE","inverse","K6","large_atlas","auto_solver"],"physics_contract_modified":False}
 v={"h1a_offline_analysis_contract.json":offline_contract,"h1a_decision_state_contract.json":decision_contract,"h1b_h2_readiness_matrix.json":matrix(),"h1a_runtime_readiness_audit.json":a}
 for n,x in v.items():(P/n).write_text(json.dumps(x,indent=2,sort_keys=True)+"\n",encoding="utf8")
 (P/"h1a_runtime_readiness_audit.md").write_text("\n".join(["# H1A runtime and offline-analysis readiness",f"- Status: {a['final_state']}",f"- Readiness: {a['readiness_verdict']}",f"- Solver accounting: {a['solver_accounting']['solver_entered_fraction']}",f"- H500 scheduled: {a['solver_accounting']['H500_scheduled']}",f"- H1A FSP/FSPX: {a['h1a_fsp_fspx_count']}",f"- Live attempts: {a['historical_attempts']['live_audit_count']} (brief stated {a['historical_attempts']['brief_stated_count']}); discrepancy preserved: {a['historical_attempts']['discrepancy_preserved']}","- Offline analyzer READY; x-only excluded from projector; H500 references separate","- Automatic ML/cVAE/inverse/K6/atlas/solver gates are false"])+"\n",encoding="utf8")
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--write-artifacts",action="store_true");x=p.parse_args()
 if not x.write_artifacts:raise SystemExit("offline-only; use --write-artifacts")
 write()

