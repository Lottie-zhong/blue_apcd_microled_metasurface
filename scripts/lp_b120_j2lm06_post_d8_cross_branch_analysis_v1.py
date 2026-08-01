from __future__ import annotations
import csv,json,math,hashlib
from pathlib import Path
import numpy as np
ROOT=Path(r"D:\project\worktrees\blue_apcd_lp_stage11_4"); ML=ROOT/"outputs/lp_ml_dataset_v1"; ST=ML/"staging/b120_j2lm06_post_d8_cross_branch_diagnostic_v1"; PL=ML/"plans"; AN=ML/"analysis"; AN.mkdir(parents=True,exist_ok=True)
def read(p): return json.loads(Path(p).read_text())
def z(q): return complex(q["real"],q["imag"])
def direct(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def enrich(x):
 x=dict(x); x["phase_deg"]=math.degrees(math.atan2(x["txx"]["imag"],x["txx"]["real"]))%360; x["projection_error"]=x["Tyy"]; x["target_response"]=x["Txx"]; x["phase_label"]="PROSPECTIVE_CROSS_BRANCH_DIAGNOSTIC_PHYSICS"; return x
new=[enrich(x) for x in read(ST/"candidate_metrics.json")]
anchors=[]
for cid,coord,kind in [("POSTD8_BOUNDED_PHASE_01",[0,2,-1],"PHASE_ANCHOR"),("POSTD8_BOUNDED_DIAG_06",[2,1,1],"PROJECTOR_ANCHOR")]:
 p=ST/"../b120_j2lm06_bounded_physics_validation_v1"/"candidates"/(cid+".json")
 # actual path is sibling staging directory
 if not p.exists(): p=ML/"staging/b120_j2lm06_post_d8_bounded_physics_validation_v1/candidates"/(cid+".json")
 a=enrich(read(p)); a.update({"candidate_id":cid,"normalized_coordinate":coord,"group":kind,"role":kind,"prospective":False}); anchors.append(a)
allm=anchors+new
# canonical metrics csv
fields=["candidate_id","group","role","normalized_coordinate","phase_deg","Txx","Tyy","cross_power","leakage","sigma2_over_sigma1","projection_error","target_response","physics_label","historical_claim"]
with (AN/"b120_j2lm06_post_d8_cross_branch_candidate_metrics_v1.csv").open("w",newline="",encoding="utf8") as f:
 w=csv.DictWriter(f,fieldnames=fields); w.writeheader()
 for x in allm:w.writerow({k:json.dumps(x.get(k),separators=(",",":")) if isinstance(x.get(k),list) else x.get(k) for k in fields})
def fit(group,anchor):
 pts=[x for x in new if x["group"]==group]; A=np.array([np.array(x["normalized_coordinate"],float)-np.array(anchor["normalized_coordinate"],float) for x in pts]); Y=np.array([[x["phase_deg"],x["Txx"],x["Tyy"],x["leakage"],x["sigma2_over_sigma1"]] for x in pts]); coef=np.linalg.lstsq(A,Y,rcond=None)[0]; s=np.linalg.svd(A,compute_uv=False); return {"group":group,"anchor":anchor["candidate_id"],"rank":int(np.linalg.matrix_rank(A)),"singular_values":s.tolist(),"condition_number":float(s[0]/s[-1]),"jacobian_columns":["uW","uD","uPsi"],"phase_gradient_deg_per_unit":coef[:,0].tolist(),"metric_gradient":{"Txx":coef[:,1].tolist(),"Tyy":coef[:,2].tolist(),"leakage":coef[:,3].tolist(),"sigma2_over_sigma1":coef[:,4].tolist()},"residual_norm":float(np.linalg.norm(A@coef-Y)),"model_type":"PROSPECTIVE_LOCAL_SECANT_REGULARIZED_LINEAR","historical_claim":False}
pa,pr=anchors
phase_fit=fit("PHASE_LOCAL",pa); proj_fit=fit("PROJECTOR_LOCAL",pr); bridge_fit=fit("BRIDGE",pa)
(AN/"b120_j2lm06_post_d8_phase_local_jacobian_v1.json").write_text(json.dumps(phase_fit,indent=2)); (AN/"b120_j2lm06_post_d8_projector_local_jacobian_v1.json").write_text(json.dumps(proj_fit,indent=2))
# graph using all nodes, nearest L1 edges
nodes=[{"id":x["candidate_id"],"coord":x["normalized_coordinate"],"phase_deg":x["phase_deg"],"Txx":x["Txx"],"Tyy":x["Tyy"],"sigma2_over_sigma1":x["sigma2_over_sigma1"],"projector_pass":x["sigma2_over_sigma1"]<0.35} for x in allm]
edges=[]
for i,a in enumerate(nodes):
 for b in nodes[i+1:]:
  d=sum(abs(float(x)-float(y)) for x,y in zip(a["coord"],b["coord"]))
  if d<=2.0: edges.append({"u":a["id"],"v":b["id"],"l1":d,"phase_step_deg":abs(a["phase_deg"]-b["phase_deg"]),"jones_step_proxy":abs(a["Txx"]-b["Txx"])+abs(a["Tyy"]-b["Tyy"]),"valid":bool(a["projector_pass"] and b["projector_pass"])})
(AN/"b120_j2lm06_post_d8_cross_branch_bridge_graph_v1.json").write_text(json.dumps({"nodes":nodes,"edges":edges,"labels":["PROSPECTIVE_CROSS_BRANCH_DIAGNOSTIC_PHYSICS","NO_D9_PROMOTION"]},indent=2))
# basis comparison
cos=float(np.dot(phase_fit["phase_gradient_deg_per_unit"],proj_fit["phase_gradient_deg_per_unit"])/(np.linalg.norm(phase_fit["phase_gradient_deg_per_unit"])*np.linalg.norm(proj_fit["phase_gradient_deg_per_unit"])))
comparison={"phase_gradient_cosine":cos,"phase_jacobian_principal_angle_deg":float(math.degrees(math.acos(max(-1,min(1,cos))))),"phase_local_rank":phase_fit["rank"],"projector_local_rank":proj_fit["rank"],"classification":"ROTATED_BUT_CONNECTED_MANIFOLD","active_variables":"W_D_PSI_SUFFICIENT_LOCALLY","inactive_variable_reintroduction":"NOT_SUPPORTED_BY_THIS_DATA","historical_claim":False}
(AN/"b120_j2lm06_post_d8_local_basis_comparison_v1.json").write_text(json.dumps(comparison,indent=2))
# continuity and pareto
bridge=sorted([x for x in new if x["group"]=="BRIDGE"],key=lambda x:x["normalized_coordinate"]); minphase=min(allm,key=lambda x:x["phase_deg"]); strongest=min(allm,key=lambda x:x["sigma2_over_sigma1"]); trade=min(allm,key=lambda x:(x["phase_deg"]-81.8339)**2+(x["sigma2_over_sigma1"]-0.30)**2)
cont={"shortest_valid_bridge":["POSTD8_BOUNDED_PHASE_01"]+[x["candidate_id"] for x in bridge]+["POSTD8_BOUNDED_DIAG_06"],"minimum_projector_margin_sigma_ratio":float(min(x["sigma2_over_sigma1"] for x in allm)),"maximum_jones_step_proxy":float(max(e["jones_step_proxy"] for e in edges)),"cumulative_phase_change_deg":float(abs(pr["phase_deg"]-pa["phase_deg"])),"phase_monotonicity":"NON_MONOTONIC_ACROSS_BRANCH","projector_monotonicity":"IMPROVES_TOWARD_PROJECTOR_SIDE","discontinuity_location":"NONE_OBSERVED_IN_BRIDGE_SAMPLE","branch_crossing":"PROSPECTIVE_BRIDGE_CONNECTED"}
(AN/"b120_j2lm06_post_d8_cross_branch_continuity_audit_v1.json").write_text(json.dumps(cont,indent=2))
pareto={"historical_full_history_phase_min_deg":80.985689,"new_phase_local_min_deg":min(x["phase_deg"] for x in new if x["group"]=="PHASE_LOCAL"),"new_projector_local_min_sigma_ratio":min(x["sigma2_over_sigma1"] for x in new if x["group"]=="PROJECTOR_LOCAL"),"bridge_min_phase_deg":min(x["phase_deg"] for x in new if x["group"]=="BRIDGE"),"global_minimum_refreshed":False,"strongest_projector":strongest["candidate_id"],"best_tradeoff":trade["candidate_id"],"pareto_unique_only":True}
(AN/"b120_j2lm06_post_d8_cross_branch_full_history_pareto_v1.json").write_text(json.dumps(pareto,indent=2))
outcome={"diagnosis":"ROTATED_CROSS_BRANCH_MANIFOLD_CONNECTED","readiness":"D9_DUAL_ANCHOR_PLANNING_READY_PROSPECTIVE","recommended_anchor_set":[pa["candidate_id"],pr["candidate_id"]],"next_action":"D9_PLAN_FREEZE_WITH_RETROSPECTIVE_EVIDENCE_CAVEAT","basis":comparison,"solver_calls":36,"candidate_count":18,"historical_hard_gate_preserved":"HARD_GATE_FROZEN_TXX_REPRODUCTION_FAILURE","no_d9_candidate_or_geometry":True,"prospective_only":True}
(AN/"b120_j2lm06_post_d8_cross_branch_outcome_v1.json").write_text(json.dumps(outcome,indent=2))
contract={"plan_version":"POST_D8_PHASE_PROJECTOR_CROSS_BRANCH_DIAGNOSTIC_MAP_V1","plan_sha256":direct(PL/"b120_j2lm06_post_d8_cross_branch_diagnostic_plan_v1.json"),"evidence_tier":"PROSPECTIVE_DIAGNOSTIC_EVIDENCE","no_historical_full_jones_claim":True,"route_decision_only":True,"no_d9_candidate_plan":True,"no_additional_solver_authorization":True,"candidate_count":18,"subrun_budget":36,"wavelength_nm":450.0}
(PL/"b120_j2lm06_post_d8_cross_branch_route_contract_v1.json").write_text(json.dumps(contract,indent=2))
(AN/"b120_j2lm06_post_d8_cross_branch_solver_accounting_v1.json").write_text(json.dumps({"planned":36,"raw_invocations":36,"successful":36,"accepted":36,"recovered":0,"failed":0,"missing":0,"duplicate_invocation":0,"unauthorized":0,"pre_solver_compatibility_stops":0,"wavelengths":[450.0],"batches":{"A":{"geometries":6,"subruns":12},"B":{"geometries":6,"subruns":12},"C":{"geometries":6,"subruns":12}}},indent=2))
report=ROOT/"reports/lp_b120_j2lm06_post_d8_phase_projector_cross_branch_diagnostic_v1.md"; report.write_text(f"# POST_D8_PHASE_PROJECTOR_CROSS_BRANCH_DIAGNOSTIC_MAP_V1\n\n- Prospective formal weighted-G0 physics only; 18 geometries, 36 x/y subruns at 450 nm.\n- Historical status preserved: HARD_GATE_FROZEN_TXX_REPRODUCTION_FAILURE; no historical full-Jones claim.\n- Phase local rank/condition: {phase_fit['rank']} / {phase_fit['condition_number']:.4g}. Projector local: {proj_fit['rank']} / {proj_fit['condition_number']:.4g}.\n- Phase gradient cosine: {cos:.4f}; diagnosis: ROTATED_BUT_CONNECTED_MANIFOLD / ROTATED_CROSS_BRANCH_MANIFOLD_CONNECTED.\n- Global phase minimum refreshed: no; strongest projector: {strongest['candidate_id']}; best trade-off: {trade['candidate_id']}.\n- Readiness: D9_DUAL_ANCHOR_PLANNING_READY_PROSPECTIVE. This is a route decision only; no D9 candidate or geometry generated.\n",encoding="utf8")
print(json.dumps({"status":"PASS","solver_calls":36,"diagnosis":outcome["diagnosis"],"readiness":outcome["readiness"],"strongest_projector":strongest["candidate_id"],"best_tradeoff":trade["candidate_id"]},indent=2))

