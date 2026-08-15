import itertools,json,statistics
from pathlib import Path
import numpy as np
import lp_h1f1_k6_coupling_level0 as b
GRID=b.GRID
R=Path(__file__).resolve().parents[1];O=R/"reports/stage_h1f2_k6_frontier_level1"; A=["H1C1B_V2_005","H1C1B_V2_005","H1C1B_V2_015","H1C1B_V2_015","H1E3C_A_DECOUPLED_MINUS_H1C1B_V2_010","H1E3C_A_TIED_PLUS_H1C1B_V2_010"]; B={"H1C1B_V2_001":8,"H1C1B_V2_002":8,"H1C1B_V2_003":7,"H1C1B_V2_004":7,"H1C1B_V2_006":7}; E={"H1E3C_B_DECOUPLED_PLUS_GLOBAL_006":8,"H1E3C_C_DECOUPLED_PLUS_H1C1B_V2_009":7,"H1E3C_C_DECOUPLED_MINUS_H1C1B_V2_009":8}
def dist(a,z):
 x=lambda s:np.asarray([[r[n] for n in ("txx","txy","tyx","tyy")] for r in s["jones"]]);return float(np.linalg.norm(x(a)-x(z))/max(np.linalg.norm(x(a)),np.linalg.norm(x(z)),1e-30))
def load():
 s=b.load_seeds()
 for x in s:x.update(local_class="STRICT",projector_pass_count=9,failed_wavelengths_nm=[],worst_projector_error=max(r["projector_error"] for r in x["jones"]))
 bm=b.read_json(b.H1C1B_MANIFEST);bc={x["geometry_uid"]:x for x in bm["candidates"]};br=b.load_csv(b.H1C1B_JONES);nm={x["geometry_uid"]:x for x in b.read_json(R/"reports/stage_h1c1b_broadband_adaptive/h1c1b_near_miss_bank.json")["rows"]}
 em=b.read_json(b.H1E3C_MANIFEST);ec={x["geometry_uid"]:x for x in em["candidates"]};er=b.load_csv(b.H1E3C_JONES);f=[]
 for uid,n in {**B,**E}.items():
  rows=(br if uid in B else er)[uid];c=(bc if uid in B else ec)[uid];assert len(rows)==9 and all(str(r["full_jones_finite"])=="True" and str(r["full_jones_accepted"])=="True" and str(r["solver_replay"])=="False" for r in rows)
  x=b.seed_record(uid,c["exact_hash"],b.identity_from_candidate(c),rows,{"artifact":str(b.H1C1B_JONES if uid in B else b.H1E3C_JONES),"manifest":str(b.H1C1B_MANIFEST if uid in B else b.H1E3C_MANIFEST),"source_stage":"H1C1B_BROADBAND_ADAPTIVE" if uid in B else "H1E3C_J2_DECOUPLING_PROBE"});x.update(local_class=f"FRONTIER_{n}",projector_pass_count=n,failed_wavelengths_nm=nm[uid]["failed_wavelengths"] if uid in nm else json.loads(rows[0]["failed_wavelengths"]),worst_projector_error=max(float(r["projector_error"]) for r in rows));f.append(x)
 assert len(s)==12 and len(f)==8;return s,f
def choose(xs,k,eight=False):
 q=[]
 for c in itertools.combinations(xs,k):
  if eight and any(x["projector_pass_count"]!=8 for x in c):continue
  ds=[dist(x,z) for x,z in itertools.combinations(c,2)];q.append((min(ds or[0]),statistics.fmean(ds or[0]),-max(x["worst_projector_error"] for x in c),tuple(x["geometry_uid"] for x in c),c))
 return max(q,key=lambda z:z[:-1])[-1]
def search(xs):
 u=[x["geometry_uid"] for x in xs];seen=set();rec=[];cache=b.build_legality_cache(xs+xs)
 for q in itertools.permutations(range(6)):
  n=tuple(u[i] for i in q);k=min(n[i:]+n[:i] for i in range(6))
  if k in seen:continue
  seen.add(k);p=b.fundamental_period_6p(q)
  if not p["FUNDAMENTAL_PERIOD_6P"]:continue
  direct=cache["direct"][list(q)];yb=cache["y_bounds"][list(q)]
  cross=[cache["cross"][m-n][q[n],q[m]] for n in range(6) for m in range(n+1,6)]
  minimum=min(list(direct)+list(yb)+cross)
  l={"pass":minimum>0,"no_overlap":minimum>0,"minimum_clearance_nm":float(minimum),"minimum_direct_pillar_gap_nm":float(min(direct)),"minimum_cross_site_gap_nm":float(min(cross)),"periodic_boundary_gap_y_nm":float(min(yb)),"materials":[b.MATERIAL]*12,"H_global_nm":b.H_GLOBAL_NM,"P_supercell_nm":b.P_SUPERCELL_NM,"p_nm":b.P_NM,"positions_nm":[{"site":i,"x_nm":(i+.5)*b.P_NM,"y_nm":0} for i in range(6)]}
  if not l["pass"]:continue
  pr=b.proxy_for_sequence(q,xs);rec.append({"sequence_uids":list(n),"sequence_indices":list(q),"period_audit":p,"legality":l,"proxy":pr,"metrics":b.proxy_metrics(pr)})
 rec.sort(key=lambda x:(-x["metrics"]["mean_target_order_strength"],-x["metrics"]["worst_wavelength_target_order_strength"],-x["metrics"]["x_y_contrast_ratio"],x["metrics"]["mean_m0_xx_leakage"],tuple(x["sequence_uids"])))
 return rec[0],{"raw_permutations":720,"cyclic_unique":len(seen),"legal_fundamental":len(rec),"selection":"deterministic discrete diagnostics; no weighted scalar"}
def main():
 O.mkdir(parents=True,exist_ok=True);s,f=load();assert b.read_json(b.H1F0_ML_AUDIT)["versioned_local_dimer_rows"]==578
 sp=[r["phi_deg"] for x in s for r in x["jones"]];fp=[r["phi_deg"] for x in f for r in x["jones"]];md={x["geometry_uid"]:min(dist(x,z) for z in s) for x in f};gate="PASS_NEW_COMPLEX_DIRECTIONS" if any(x>1e-3 for x in md.values()) else "HARD_STOP_NO_NEW_DIRECTIONS"
 slim=lambda x:{"geometry_uid":x["geometry_uid"],"exact_hash":x["exact_hash"],"class":x["local_class"],"projector_pass_count":x["projector_pass_count"],"failed_wavelengths_nm":x["failed_wavelengths_nm"],"worst_projector_error":x["worst_projector_error"],"coordinates_5d":x["coordinates_5d"],"provenance":x["provenance"]}
 b.write_json(O/"h1f2_constituent_pool_audit.json",{"schema":"H1F2_CONSTITUENT_POOL_AUDIT_V1","versioned_local_dimer_rows":578,"strict_count":12,"frontier_8_count":4,"frontier_7_count":4,"frontier_eligible_count":8,"excluded_invalid_or_quarantine_in_audited_full_jones_pool":0,"lower_or_forbidden_not_admitted":True,"records":[slim(x) for x in s+f],"ml_admitted":False})
 def circular_coverage(values):
  vals=sorted((float(v)%360.0) for v in values)
  if not vals:return 0.0
  if len(vals)==1:return 0.0
  gaps=[(vals[(i+1)%len(vals)]-vals[i])%360.0 for i in range(len(vals))]
  return 360.0-max(gaps)
 phase_values=sp+fp
 b.write_json(O/"h1f2_frontier_phase_diversity.json",{"schema":"H1F2_FRONTIER_PHASE_DIVERSITY_V1","strict_plus_frontier_phase_circular_coverage_deg":circular_coverage(phase_values),"phase_raw_extrema_deg":{"min":min(phase_values) if phase_values else None,"max":max(phase_values) if phase_values else None},"frontier_min_complex_jones_distance_to_strict":md,"new_broadband_complex_directions_added":any(x>1e-3 for x in md.values()),"gate":gate,"basis":"complex J_xy; full-wave K6 alpha*/beta* audit mandatory"})
 sb={x["geometry_uid"]:x for x in s};ap=[sb[x] for x in A];opts=[q for q in set(itertools.permutations(tuple(A))) if min(q[i:]+q[:i] for i in range(6))!=min(tuple(A)[i:]+tuple(A)[:i] for i in range(6))];au=max(opts,key=lambda q:(sum(x!=z for x,z in zip(q,A)),q));ab,asr=search([sb[x] for x in au]);b.write_json(O/"h1f2_candidate_a_permutation_search.json",{"schema":"H1F2_CANDIDATE_A_PERMUTATION_SEARCH_V1",**asr,"same_multiset_as_h1f1_a":sorted(au)==sorted(A),"selected_sequence_uids":ab["sequence_uids"],"mirror_reversals_not_collapsed":True})
 bf=choose(f,2,True);cf=choose(f,3);bs=choose(s,4);cs=choose(s,3);bb,bsr=search(list(bs)+list(bf));cb,csr=search(list(cs)+list(cf));b.write_json(O/"h1f2_mixed_sequence_search.json",{"schema":"H1F2_MIXED_SEQUENCE_SEARCH_V1","selection_governance":"discrete diagnostics; no weighted scalar","B":{"strict_uids":[x["geometry_uid"] for x in bs],"frontier_uids":[x["geometry_uid"] for x in bf],"selected":bb,"search":bsr},"C":{"strict_uids":[x["geometry_uid"] for x in cs],"frontier_uids":[x["geometry_uid"] for x in cf],"selected":cb,"search":csr}})
 def make(uid,role,z,xs):
  m={x["geometry_uid"]:x for x in xs};q=[m[n] for n in z["sequence_uids"]];p={"candidate_uid":uid,"role":role,"sequence_uids":z["sequence_uids"],"sequence_hashes":[x["exact_hash"] for x in q],"constituent_classes":[x["local_class"] for x in q],"projector_pass_counts":[x["projector_pass_count"] for x in q],"site_positions_nm":[{"site":i,"x_nm":(i+.5)*b.P_NM,"y_nm":0} for i in range(6)],"p_nm":b.P_NM,"P_supercell_nm":b.P_SUPERCELL_NM,"P_y_nm":432.0,"H_global_nm":b.H_GLOBAL_NM,"material":b.MATERIAL,"fundamental_period_audit":z["period_audit"],"geometry_legality":z["legality"],"proxy":z["proxy"],"proxy_metrics":z["metrics"],"local_geometries":[x["identity"] for x in q],"no_position_shift":True,"no_local_geometry_mutation":True,"ml_admitted":False};p["candidate_hash"]=b.sha256_obj(p);return p
 C={"K6_L1_A":make("K6_L1_A","STRICT_ONLY_ORDERING_CONTROL",ab,[sb[x] for x in au]),"K6_L1_B":make("K6_L1_B","CONSERVATIVE_FRONTIER_MIX",bb,list(bs)+list(bf)),"K6_L1_C":make("K6_L1_C","PHASE_DIVERSITY_FRONTIER_STRESS",cb,list(cs)+list(cf))}
 b.write_json(O/"h1f2_candidate_manifest.json",{"schema":"H1F2_K6_CANDIDATE_MANIFEST_V1","status":"FROZEN_READY_FOR_SOLVER","candidate_count":3,"candidates":C,"p_nm":b.P_NM,"P_supercell_nm":b.P_SUPERCELL_NM,"P_y_nm":432.0,"H_global_nm":b.H_GLOBAL_NM,"wavelength_grid_nm":GRID,"processes":4,"threads":1,"max_new_formal_cases":6,"position_convention":"x_n=(n+.5)p,y=0; no shifts","freeze_sha256":b.sha256_obj(C),"ml_admitted":False})
 b.write_json(O/"h1f2_geometry_legality.json",{k:v["geometry_legality"] for k,v in C.items()});b.write_json(O/"h1f2_solver_accounting.json",{"schema":"H1F2_SOLVER_ACCOUNTING_V1","planned_formal_cases":6,"entered_formal_cases":0,"accepted_formal_cases":0,"quarantine_cases":0,"replay_cases":0,"max_active_global_fdtd":2,"max_active_lp_fdtd":1,"processes_per_job":4,"threads_per_job":1,"status":"FROZEN_PRE_SOLVER","ml_admitted":False})
 b.write_json(O/"h1f2_h1f1_comparison.json",{"schema":"H1F2_H1F1_COMPARISON_V1","full_wave_comparison_status":"PENDING_H1F2_SOLVER","H1F1_A_mean_eta_x_plus1":.0202,"H1F1_B_mean_eta_x_plus1":.01823,"H1F1_C_mean_eta_x_plus1":.00314,"local_registry_rows":578,"K6_registry_rows_before":594});b.write_json(O/"h1f2_proxy_vs_fullwave.json",{"schema":"H1F2_PROXY_VS_FULLWAVE_V1","proxy_annotation":"NON_AUTHORITATIVE_CONSTITUENT_ADDITIVE_DIAGNOSTIC","full_wave_status":"PENDING_H1F2_SOLVER"});b.write_json(O/"h1f2_k6_registry_audit.json",{"schema":"H1F2_K6_REGISTRY_AUDIT_V1","local_registry_rows_before":578,"local_registry_rows_unchanged":True,"K6_registry_rows_before":594,"new_k6_rows":0,"ml_admitted":False,"status":"PRE_SOLVER"});b.write_json(O/"h1f2_final.json",{"schema":"H1F2_FINAL_V1","status":"FROZEN_READY_FOR_SOLVER","physics_classification":"K6_COUPLING_AWARE_SIGNAL_WEAK_H1F1_FRONTIER_PROBE_PENDING","strict_count":12,"eligible_frontier_8_count":4,"eligible_frontier_7_count":4,"excluded_invalid_or_quarantine_count":0,"phase_diversity_gate":gate,"planned_new_solver_cases":6,"entered_new_solver_cases":0,"accepted_new_solver_cases":0,"quarantine_new_solver_cases":0,"replay_new_solver_cases":0,"local_registry_rows":578,"K6_registry_rows_before":594,"ml_admitted":False,"level2_auto_start":False});(O/"h1f2_summary.md").write_text("# H1F-2 K6 frontier Level-1\n\n- Status: FROZEN_READY_FOR_SOLVER\n- Strict: 12; frontier 8/9: 4; frontier 7/9: 4.\n- Diversity gate: "+gate+".\n- Planned/entered/accepted/quarantine/replay: 6/0/0/0/0.\n- Local registry: 578 unchanged; K6 registry before: 594; ML admitted: false.\n",encoding="utf-8")
if __name__=="__main__":main()
