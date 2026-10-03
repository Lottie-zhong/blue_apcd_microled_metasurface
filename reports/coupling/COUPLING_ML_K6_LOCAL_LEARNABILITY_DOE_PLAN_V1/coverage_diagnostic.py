import sys,json,hashlib,math,csv,os,datetime
from pathlib import Path
import numpy as np
sys.stdout.reconfigure(encoding="utf-8",errors="replace")
W=Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1")
OUT=W/"reports/coupling/COUPLING_ML_K6_LOCAL_LEARNABILITY_DOE_PLAN_V1"
sys.path.insert(0,str(W/"scripts/coupling_ml"))
import pw_k6_stage1_32g_frozen_forward_h1_v1 as h1

def sha(p):
 h=hashlib.sha256()
 with open(p,"rb") as f:
  for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
 return h.hexdigest()
def qstats(x):
 x=np.asarray(x,float)
 return {"count":int(x.size),"min":float(np.min(x)),"q25":float(np.quantile(x,.25)),"median":float(np.median(x)),"mean":float(np.mean(x)),"q75":float(np.quantile(x,.75)),"q95":float(np.quantile(x,.95)),"max":float(np.max(x))}
def pearson(x,y):
 x=np.asarray(x,float);y=np.asarray(y,float)
 if np.std(x)==0 or np.std(y)==0:return None
 return float(np.corrcoef(x,y)[0,1])
def rankdata_avg(x):
 x=np.asarray(x,float); order=np.argsort(x,kind="mergesort");r=np.empty(len(x),float);i=0
 while i<len(x):
  j=i+1
  while j<len(x) and x[order[j]]==x[order[i]]:j+=1
  r[order[i:j]]=(i+1+j)/2.0;i=j
 return r
# Use only the formal per-case readers; do not open aggregate OOF/dataset archives, fit, or call a solver.
protocol=json.loads((OUT/"PREREGISTERED_PROTOCOL_V1.json").read_text(encoding="utf-8"))
assert protocol["status"]=="FROZEN_GEOMETRY_RULES_BEFORE_RESPONSE_ANALYSIS"
dec=h1.decoder_module()
exp=h1.jread(h1.EXP_PATH)
a20=h1.load20(dec)
a12=h1.load12(exp,dec)
data=h1.combine(a20,a12)
auth=h1.jread(W/"reports/coupling/PW_K6_STAGE1_32G_FROZEN_FORWARD_H1_V1/PW_K6_32G_DATASET_AUTHORITY_V1.json")
assert len(data["ids"])==32 and len(set(data["ids"]))==32 and data["chat"].shape==(32,21,7,2) and data["eta"].shape==(32,21,7) and data["pscale"].shape==(32,21)
assert data["ids"]==auth["ordered_geometry_ids"]
case={cid:i for i,cid in enumerate(data["ids"])}
g=np.asarray(data["geometry"],int)
assert np.array_equal(g,np.asarray(auth["ordered_D_nm"],int))
# Authority-listed individual state hashes are checked by the formal loaders.
prov={r["case_id"]:r for r in auth["case_provenance"]}
assert len(prov)==32 and all(prov[cid]["geometry_hash_sha256"]==hashlib.sha256(",".join(map(str,g[i])).encode("ascii")).hexdigest() for i,cid in enumerate(data["ids"]))
# 32G geometry-only coverage.
lo,hi=100,230
coord={f"D{i+1}_nm":{"min":int(np.min(g[:,i])),"q25":float(np.quantile(g[:,i],.25)),"median":float(np.median(g[:,i])),"mean":float(np.mean(g[:,i])),"q75":float(np.quantile(g[:,i],.75)),"max":int(np.max(g[:,i])),"count_le_110":int(np.sum(g[:,i]<=110)),"count_ge_220":int(np.sum(g[:,i]>=220))} for i in range(6)}
center=np.mean(g,axis=0)
D=np.sqrt(np.sum(((g[:,None,:]-g[None,:,:])/130.0)**2,axis=2));np.fill_diagonal(D,np.inf)
nearest=np.argmin(D,axis=1);nn=D[np.arange(32),nearest]
neigh={str(rad):np.sum((D<=rad),axis=1).astype(int) for rad in [0.5,0.75,1.0,1.25,1.5]}
# Connected components at the preregistered descriptive radius 1.0.
seen=set();components=[]
for i in range(32):
 if i in seen:continue
 stack=[i];seen.add(i);comp=[]
 while stack:
  a=stack.pop();comp.append(a)
  for j in np.where(D[a]<=1.0)[0]:
   if int(j) not in seen:seen.add(int(j));stack.append(int(j))
 components.append(sorted(comp))
# Pairwise truth response differences: all pairs are dependent descriptive observations.
chat=data["chat"];eta=data["eta"];ps=data["pscale"]
pairs=[]
for i in range(32):
 for j in range(i+1,32):
  dgeo=float(np.linalg.norm((g[i]-g[j])/130.0))
  ci=chat[i].reshape(-1);cj=chat[j].reshape(-1)
  dchat=float(2*np.linalg.norm(ci-cj)/max(float(np.linalg.norm(ci)+np.linalg.norm(cj)),1e-30))
  deta=float(np.sqrt(np.mean((eta[i]-eta[j])**2)))
  dps=float(np.mean(np.abs(np.log(np.maximum(ps[i],1e-30)/np.maximum(ps[j],1e-30)))))
  pairs.append({"geometry_distance":dgeo,"symmetric_C_hat_relative_L2":dchat,"routing_RMS_difference":deta,"P_scale_mean_abs_log_ratio":dps,"case_i":data["ids"][i],"case_j":data["ids"][j]})
assert len(pairs)==496
fixed_bins=protocol["coverage_protocol"]["fixed_distance_bins"]
bins=[]
for lo,hi in fixed_bins:
 sel=[p for p in pairs if p["geometry_distance"]>=lo and (hi is None or p["geometry_distance"]<hi)]
 q={"lo_inclusive":lo,"hi_exclusive":hi,"pair_count":len(sel)}
 for key in ["symmetric_C_hat_relative_L2","routing_RMS_difference","P_scale_mean_abs_log_ratio"]:
  arr=np.asarray([p[key] for p in sel],float) if sel else np.asarray([])
  q[key]=qstats(arr) if len(arr) else None
 bins.append(q)
x=np.asarray([p["geometry_distance"] for p in pairs]);
relationships={"pair_count":len(pairs),"independent_sample_warning":"496 pairs share the same 32 geometry groups; correlation/bins are descriptive and not inferential n=496","pearson":{},"spearman":{},"fixed_distance_bins":bins}
for key in ["symmetric_C_hat_relative_L2","routing_RMS_difference","P_scale_mean_abs_log_ratio"]:
 y=np.asarray([p[key] for p in pairs],float)
 relationships["pearson"][key]=pearson(x,y);relationships["spearman"][key]=pearson(rankdata_avg(x),rankdata_avg(y))
# Per-geometry local-neighbor differences support the clustering view; no derivative interpretation.
neighbor_rows=[]
for i,cid in enumerate(data["ids"]):
 j=int(nearest[i]);neighbor_rows.append({"case_id":cid,"ordered_D_nm":",".join(map(str,g[i])),"nearest_case_id":data["ids"][j],"nearest_distance_normalized":float(nn[i]),"neighbors_le_0p5":int(neigh["0.5"][i]),"neighbors_le_0p75":int(neigh["0.75"][i]),"neighbors_le_1p0":int(neigh["1.0"][i]),"nearest_C_hat_symmetric_relative_L2":float(2*np.linalg.norm(chat[i]-chat[j])/max(np.linalg.norm(chat[i])+np.linalg.norm(chat[j]),1e-30)),"nearest_routing_RMS":float(np.sqrt(np.mean((eta[i]-eta[j])**2))),"nearest_P_scale_mean_abs_log_ratio":float(np.mean(np.abs(np.log(np.maximum(ps[i],1e-30)/np.maximum(ps[j],1e-30)))))} )
# Output source and label provenance summary from authority-based loaders.
records=a20["provenance"]+a12["records"]
assert len(records)==32 and {r["case_id"] for r in records}==set(data["ids"])
parity=a20["parity"]+a12["parity"]
# Production time/storage estimate from the existing single-slot Runner logs, never launching it.
R=h1.RUNTIME;reg=h1.jread(R/"registry.json");runmap={q["case_id"]:q for q in reg.get("runs",[]) if q.get("case_id") in h1.STAGE1}
qual=h1.jread(h1.RUNNER/"reports"/"apcd_gpu_production_runner_v1"/"GENERIC_SETUP_VALIDATOR_ZERO_SOLVER_20261002.json");qm={q["case_id"]:q for q in qual["cases"]}
perf=[]
for cid in h1.STAGE1:
 rec=runmap[cid];rd=Path(rec["run_dir"]);sp=rd/"status.json";st=h1.jread(sp) if sp.exists() else {}
 total_bytes=0;file_count=0
 if rd.exists():
  for root,dirs,files in os.walk(rd):
   for name in files:
    p=Path(root)/name
    try:total_bytes+=p.stat().st_size;file_count+=1
    except OSError:pass
 q=qm[cid]; prep=[]
 for k in ["pre_fsp_path","authority_manifest_path","load_only_validation_path"]:
  p=Path(q[k]); prep.append(p.stat().st_size if p.exists() else None)
 created=st.get("created_unix");done=st.get("done_unix");entered=st.get("solver_entered_unix")
 perf.append({"case_id":cid,"registry_state":rec.get("state"),"status_state":st.get("state"),"created_to_done_seconds":float(done-created) if created and done else None,"entered_to_done_seconds":float(done-entered) if entered and done else None,"run_artifact_bytes":total_bytes,"run_file_count":file_count,"setup_fsp_bytes":prep[0],"authority_manifest_bytes":prep[1],"load_only_validation_bytes":prep[2],"with_setup_artifacts_bytes":total_bytes+sum(v or 0 for v in prep)})
completed=[r for r in perf if r["created_to_done_seconds"] is not None and r["status_state"]=="DONE"]
completed_storage=[r["with_setup_artifacts_bytes"] for r in completed]
times=[r["created_to_done_seconds"] for r in completed]
assert len(completed)>=10, f"insufficient completed Stage-1 timings: {len(completed)}"
recovery=R/"recovery"/"K6V1_S35"/"attempt_001"/h1.RUNIDS["K6V1_S35"]
recovery_summary={"path":str(recovery),"exists":recovery.exists()}
if recovery.exists():
 sfile=recovery/"recovery_003"/"recovery_status.json"
 if sfile.exists():
  rr=h1.jread(sfile);recovery_summary.update({k:rr.get(k) for k in ["recovery_state","solver_invocations_before","solver_invocations_after","solver_run_called_during_recovery","replay_count","created_utc","completed_utc","recovery_completed_utc"]})
 rb=0;fc=0
 for root,dirs,files in os.walk(recovery):
  for f in files:
   p=Path(root)/f
   try:rb+=p.stat().st_size;fc+=1
   except OSError:pass
 recovery_summary.update({"recovery_artifact_bytes":rb,"file_count":fc})
time_summary={"completed_stage1_count":len(completed),"all_stage1_rows":perf,"created_to_done_sec":qstats(times),"entered_to_done_sec":qstats([r["entered_to_done_seconds"] for r in completed if r["entered_to_done_seconds"] is not None]),"serial_16_cases_estimate_using_median_min_max_sec":{"median_x16":float(np.median(times)*16),"mean_x16":float(np.mean(times)*16),"min_x16":float(np.min(times)*16),"max_x16":float(np.max(times)*16)},"storage_completed_stage1_with_pre_fsp_authority_bytes":qstats(completed_storage),"serial_16_case_storage_estimate_bytes":{"median_x16":int(np.median(completed_storage)*16),"mean_x16":int(np.mean(completed_storage)*16),"min_x16":int(np.min(completed_storage)*16),"max_x16":int(np.max(completed_storage)*16)},"postentry_recovery_history":{"observed_failed_postentry_count":1,"historical_case":"K6V1_S35","automatic_replay_count":0,"recovery":recovery_summary,"interpretation":"one prior post-entry failure among 12 Stage-1 identities is a small operational sample, not a probability estimate; a future post-entry failure consumes its entry, preserve artifacts and request review instead of auto-replay"},"basis":"11 Runner DONE Stage-1 cases; one S35 FAILED_POSTENTRY then separate LOAD-only truth recovery. Created-to-DONE uses status timestamps; storage sums case run directory plus pre-FSP, authority manifest, and LOAD-only proof. Single slot serial; does not include an unapproved diagnostic monitor variant."}
# Persist summaries and tables.
summary={"schema":"COUPLING_ML_K6_LOCAL_LEARNABILITY_32G_COVERAGE_DIAGNOSTIC_V1","task":"COUPLING_ML_K6_LOCAL_LEARNABILITY_DOE_PLAN_V1","created_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"authority":{"dataset_authority_sha256":sha(W/"reports/coupling/PW_K6_STAGE1_32G_FROZEN_FORWARD_H1_V1/PW_K6_32G_DATASET_AUTHORITY_V1.json"),"geometry_domain_authority_sha256":sha(W/"reports/coupling/PW_K6_GEOMETRY_DOMAIN_AUTHORITY_V1.json"),"expansion_manifest_sha256":sha(h1.EXP_PATH),"contract_sha256":h1.CONTRACT,"state_schema":auth["state_schema"],"formal_reader_source_sha256":sha(W/"scripts/coupling_ml/pw_k6_stage1_32g_frozen_forward_h1_v1.py"),"frozen_H2_sha256":h1.DECODER_SHA},"dataset":{"geometry_count":32,"geometry_wavelength_rows":672,"order_geometry_wavelength_rows":4704,"wavelengths_nm":[440,460,1],"orders_m":list(range(-3,4)),"ordered_ids":data["ids"],"dataset_state_hashes_checked":32,"state_hash_provenance":records,"solver_entries_in_this_task":0,"new_training_fits":0,"P_scale_fitting":0,"OOF_aggregate_archives_opened":False},"geometry_coverage":{"coordinate_summary":coord,"formal_normalized_distance":"sqrt(sum(((D_i-D'_i)/130)^2))","nearest_neighbor_distance":qstats(nn),"nearest_neighbor_by_geometry":[{"case_id":data["ids"][i],"nearest_case_id":data["ids"][int(nearest[i])],"distance":float(nn[i])} for i in range(32)],"neighbor_count_by_radius":{r:qstats(v) for r,v in neigh.items()},"radius_1p0_connected_component_sizes":sorted([len(x) for x in components],reverse=True),"geometry_centroid_nm":[float(v) for v in center],"pairwise_responses":relationships},"h2_modal_pscale_parity":{"20G_max_relative_error":max(q["modal_pscale_max_relative_error"] for q in a20["parity"]),"Stage1_12G_max_relative_error":max(q["modal_pscale_max_relative_error"] for q in a12["parity"]),"20G_max_eta_abs_error":max(q["h2_eta_max_abs_error"] for q in a20["parity"]),"Stage1_12G_max_eta_abs_error":max(q["h2_eta_max_abs_error"] for q in a12["parity"])},"time_storage_estimate":time_summary,"interpretation_limits":["Pairwise differences are descriptive: pairs share cases and are not independent observations.","Because multiple diameters vary between 32G cases, response differences are not single-coordinate derivatives or causal effects.","Local axis-step finite differences in the proposed DOE are only local response clues; four combos are insufficient to prove all cross-coordinate interactions negligible.","Geometry-domain authority does not include an independent manufacturing minimum-gap specification; all checks here establish only in-domain, on-grid, and non-overlapping cylinders."],"fit_or_solver_invocations":[]}
(OUT/"COVERAGE_DIAGNOSTIC_V1.json").write_text(json.dumps(summary,ensure_ascii=False,sort_keys=True,indent=2),encoding="utf-8")
with (OUT/"GEOMETRY_NEAREST_NEIGHBORS_V1.csv").open("w",encoding="utf-8",newline="") as f:
 fields=list(neighbor_rows[0].keys());wri=csv.DictWriter(f,fieldnames=fields);wri.writeheader();wri.writerows(neighbor_rows)
with (OUT/"PAIRWISE_RELATIONSHIP_BINS_V1.csv").open("w",encoding="utf-8",newline="") as f:
 fields=["lo_inclusive","hi_exclusive","pair_count","metric","mean","median","q95","max"]
 wri=csv.DictWriter(f,fieldnames=fields);wri.writeheader()
 for b in bins:
  for key in ["symmetric_C_hat_relative_L2","routing_RMS_difference","P_scale_mean_abs_log_ratio"]:
   s=b[key]
   if s:wri.writerow({"lo_inclusive":b["lo_inclusive"],"hi_exclusive":b["hi_exclusive"],"pair_count":b["pair_count"],"metric":key,"mean":s["mean"],"median":s["median"],"q95":s["q95"],"max":s["max"]})
(OUT/"TIME_STORAGE_ESTIMATE_V1.json").write_text(json.dumps(time_summary,ensure_ascii=False,sort_keys=True,indent=2),encoding="utf-8")
print(json.dumps({"geometry":summary["geometry_coverage"],"h2_parity":summary["h2_modal_pscale_parity"],"runtime":time_summary["created_to_done_sec"],"runtime_16":time_summary["serial_16_cases_estimate_using_median_min_max_sec"],"storage":time_summary["storage_completed_stage1_with_pre_fsp_authority_bytes"],"storage_16":time_summary["serial_16_case_storage_estimate_bytes"],"source_sha":summary["authority"]},ensure_ascii=False))
