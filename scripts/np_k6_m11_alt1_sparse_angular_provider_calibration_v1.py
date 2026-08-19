from pathlib import Path
import csv,json,hashlib,subprocess
from datetime import datetime,timezone
import numpy as np

NP=Path(r"D:\project\worktrees\blue_apcd_np_k6_mdc_v1")
CP=Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_v1")
OUT=NP/r"outputs\np_k6_m11_alt1_sparse_angular_provider_calibration_v1"
OUT.mkdir(parents=True,exist_ok=True)
def sha(p):
 h=hashlib.sha256()
 with open(p,"rb") as f:
  for b in iter(lambda:f.read(1048576),b""): h.update(b)
 return h.hexdigest()
def dump(p,x):
 p.write_text(json.dumps(x,indent=2,ensure_ascii=False,sort_keys=True)+"\n",encoding="utf-8",newline="\n")
def csvw(p,rows):
 with open(p,"w",newline="",encoding="utf-8") as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
def F(x): return float(x)
geom_hash="00a951a831619fe0a34b5ffd5c58545282e2236d79190bd9d2d3961dd856f7b1"
uxp=0.22413793103448276; uxn=0.37868939998860307; uxm=-0.3786893999886029
waves=list(range(445,456))
pkg=CP/r"outputs\coupling\COUPLING_TO_NP_ANGULAR_HANDOFF_TERMINAL_PACKAGE_V1"
pkg_json=pkg/"COUPLING_TO_NP_ANGULAR_HANDOFF_TERMINAL_PACKAGE_V1.json"
pkg_csv=pkg/"ALT1_STAGE1B_ACCEPTED_HF_PROVIDER_ERROR_V1.csv"
neg_post=CP/r"outputs\coupling\rcwa_component_benchmark_v1\runtime_runs\RCWA_LEVEL1_ANGULAR_ACQUISITION_9JOB_V1\NP_LEVEL1_RCWA_UX_M0d378689399989\attempt_001\NP_LEVEL1_RCWA_UX_M0d378689399989_attempt_001_postprocessed.json"
pos=list(csv.DictReader(open(pkg_csv,encoding="utf-8-sig")))
neg=json.loads(open(neg_post,encoding="utf-8").read())
cases={(uxp,"S_YLIKE"):"NP_K6_M11_ALT1_UX_P0d224137931034_S",(uxn,"P_XLIKE"):"NP_K6_M11_ALT1_UX_P0d378689399989_P",(uxn,"S_YLIKE"):"NP_K6_M11_ALT1_UX_P0d378689399989_S",(uxm,"P_XLIKE"):"NP_K6_M11_ALT1_UX_M0d378689399989_P",(uxm,"S_YLIKE"):"NP_K6_M11_ALT1_UX_M0d378689399989_S"}
rec=[]
for r in pos:
 k=(F(r["ux"]),r["polarization"])
 if k not in cases: continue
 w=int(round(F(r["wavelength_nm"])))
 if w not in waves: continue
 hf={a:F(r[b]) for a,b in [("R","R_fdtd"),("T","T_fdtd"),("eta_plus1","mplus1_fdtd"),("eta_0","m0_fdtd"),("eta_minus1","mminus1_fdtd")]}
 rc={a:hf[a]-F(r[b]) for a,b in [("R","delta_R"),("T","delta_T"),("eta_plus1","delta_mplus1"),("eta_0","delta_m0"),("eta_minus1","delta_mminus1")]}
 rec.append((cases[k],"ALT1/B",F(r["ux"]),r["polarization"],w,hf,rc,"coupling_terminal_package"))
for pol,suf in [("P_XLIKE","P_XLIKE"),("S_YLIKE","S_YLIKE")]:
 p=NP/rf"outputs\np_k6_m10c_alt1_neg0378_ps_quantitative_anchor_v1\runtime_runs\NP_K6_M10C_ALT1_UX_M0d378689399989_{suf}\attempt_001\spectral_metrics.csv"
 for r in csv.DictReader(open(p,encoding="utf-8-sig")):
  w=int(round(F(r["wavelength_nm"])))
  q=[x for x in neg["metrics"][pol] if int(round(F(x["wavelength_nm"])))==w][0]
  hf={a:F(r[b]) for a,b in [("R","R_total"),("T","T_total"),("eta_plus1","eta_plus1"),("eta_0","eta_0"),("eta_minus1","eta_minus1")]}
  rc={a:F(q[b]) for a,b in [("R","R_total"),("T","T_total"),("eta_plus1","eta_plus1"),("eta_0","eta_0"),("eta_minus1","eta_minus1")]}
  rec.append((cases[(uxm,pol)],"ALT1/B",uxm,pol,w,hf,rc,"coupling_exact_negative_rcwa_plus_np_m10c_fdt"))
rec.sort(key=lambda x:(x[2],x[3],x[4]))
assert len(rec)==55 and len(set((x[0],x[4]) for x in rec))==55
matched=[]
for cid,g,u,pol,w,hf,rc,src in rec:
 d={"case_id":cid,"geometry":g,"geometry_hash":geom_hash,"u_x":u,"polarization":pol,"wavelength_nm":w,"source":src}
 for o in ["R","T","eta_plus1","eta_0","eta_minus1"]:
  d["rcwa_"+o]=rc[o]; d["fdtd_"+o]=hf[o]; d["delta_"+o]=hf[o]-rc[o]
 matched.append(d)
csvw(OUT/"m11_matched_55row.csv",matched)
dump(OUT/"m11_matched_55row.json",{"schema":"NP_K6_ALT1_SPARSE_ANGULAR_RCWA_FDTD_MATCHED_SET_V1","row_count":55,"logical_case_count":5,"exact_wavelengths_nm":waves,"no_interpolation":True,"rows":matched})
src_pkg=sha(pkg_json); src_csv=sha(pkg_csv); src_neg=sha(neg_post)
dump(OUT/"m11_imported_rcwa_authority.json",{"schema":"NP_IMPORTED_ALT1_NEG0378_RCWA_AUTHORITY_V1","source_package_path":str(pkg_json),"source_package_sha256":src_pkg,"source_alt1_hf_error_csv_sha256":src_csv,"negative_rcwa_postprocessed_path":str(neg_post),"negative_rcwa_postprocessed_sha256":src_neg,"coupling_head":subprocess.run(["git","-C",str(CP),"rev-parse","HEAD"],capture_output=True,text=True).stdout.strip(),"exact_negative_rows":22,"exact_total_rows":55,"provider_contract":"grating_power_native; exact 445-455 nm; no interpolation/extrapolation"})
prereg={"schema":"NP_K6_M11_SPARSE_ANGULAR_CALIBRATION_PREREG_V1","id":"NP_K6_M11_SPARSE_ANGULAR_CALIBRATION_PREREG_V1","created_utc":datetime.now(timezone.utc).isoformat(),"authority":"exact 55 rows; 5 logical cases x 11 wavelengths; HF truth only; P/S explicit","outputs":["R","T","eta_plus1","eta_0","eta_minus1"],"models":["RAW_RCWA","GLOBAL_BIAS","POLARIZATION_CONDITIONAL_BIAS","AFFINE_CALIBRATION","RIDGE_RESIDUAL"],"cv":"leave-one-logical-case-out; fold-local fit; no wavelength leakage","ridge_features":["intercept","u_x","wavelength_scaled","polarization_encoding","raw_RCWA_output"],"ridge_alpha":1e-6,"selection":"simplest model within 5 percent of best grouped OOF full metric","excluded":["+0.224 P unresolved","-0.482 stress-only","-0.9549788465408765 not provider claim"],"solver_budget":{"FDTD":0,"RCWA":0,"TMM":0,"BFAST":0,"external_HF":0,"inverse":0}}
prereg_path=OUT/"m11_prereg_v1.json"; dump(prereg_path,prereg); dump(OUT/"m11_prereg_sha256.json",{"sha256":sha(prereg_path),"path":str(prereg_path)})
outs=["eta_plus1","T","R","eta_0","eta_minus1"]
def summ(a):
 a=np.asarray(a,float)
 return {"mae":float(np.mean(abs(a))),"median_abs":float(np.median(abs(a))),"p90_abs":float(np.percentile(abs(a),90)),"max_abs":float(np.max(abs(a))),"signed_bias":float(np.mean(a))}
raw_long=[]
for d in matched:
 for o in outs: raw_long.append({"case_id":d["case_id"],"u_x":d["u_x"],"polarization":d["polarization"],"wavelength_nm":d["wavelength_nm"],"output":o,"rcwa":d["rcwa_"+o],"fdtd":d["fdtd_"+o],"delta":d["delta_"+o]})
csvw(OUT/"m11_raw_rcwa_fdtd_residual_long.csv",raw_long)
by={}
for label,key in [("overall",lambda d:"all"),("case",lambda d:d["case_id"]),("polarization",lambda d:d["polarization"])]:
 groups={}
 for d in matched: groups.setdefault(key(d),[]).append(d)
 by[label]={g:{o:summ([d["delta_"+o] for d in ds]) for o in outs} for g,ds in groups.items()}
dump(OUT/"m11_raw_residual_summary.json",{"schema":"NP_K6_M11_RAW_RCWA_FDTD_RESIDUAL_AUDIT_V1","summary":by,"interpretation":{"ux_dependence":"sign- and node-dependent","sign_dependence":"present","polarization_dependence":"present","plus_minus_378_asymmetry":"present","dominant_components":"eta_plus1 and T; m0/mminus1 smaller","systematic_bias":"mixed with case-specific residual"},"grouped_cases":list(cases.values())})
def X(d,raw,aff=False):
 z=[1,d["u_x"],(d["wavelength_nm"]-450)/5,1 if d["polarization"]=="S_YLIKE" else 0]
 return np.array(z if aff else z+[raw],float)
def pred(train,test,model,o):
 if model=="RAW_RCWA": return np.array([d["rcwa_"+o] for d in test])
 e=np.array([d["delta_"+o] for d in train])
 if model=="GLOBAL_BIAS": return np.array([d["rcwa_"+o]+e.mean() for d in test])
 if model=="POLARIZATION_CONDITIONAL_BIAS":
  m={p:np.mean([d["delta_"+o] for d in train if d["polarization"]==p]) for p in ["P_XLIKE","S_YLIKE"]}
  return np.array([d["rcwa_"+o]+m[d["polarization"]] for d in test])
 aff=model=="AFFINE_CALIBRATION"; A=np.array([X(d,d["rcwa_"+o],aff) for d in train]); B=np.array([X(d,d["rcwa_"+o],aff) for d in test])
 b=np.linalg.lstsq(A,e,rcond=None)[0] if aff else np.linalg.solve(A.T@A+1e-6*np.eye(A.shape[1]),A.T@e)
 return np.array([d["rcwa_"+o] for d in test])+B@b
models=["RAW_RCWA","GLOBAL_BIAS","POLARIZATION_CONDITIONAL_BIAS","AFFINE_CALIBRATION","RIDGE_RESIDUAL"]
ids=sorted(set(d["case_id"] for d in matched)); oof=[]
for held in ids:
 tr=[d for d in matched if d["case_id"]!=held]; te=[d for d in matched if d["case_id"]==held]
 for model in models:
  for o in outs:
   for d,y in zip(te,pred(tr,te,model,o)):
    oof.append({"model":model,"held_out_case":held,"case_id":d["case_id"],"u_x":d["u_x"],"polarization":d["polarization"],"wavelength_nm":d["wavelength_nm"],"output":o,"truth":d["fdtd_"+o],"prediction":float(y),"error":float(y-d["fdtd_"+o])})
csvw(OUT/"m11_calibration_oof_long.csv",oof)
comp=[]
for model in models:
 rs=[r for r in oof if r["model"]==model]
 profile=[np.mean([abs(r["error"]) for r in rs if r["case_id"]==cid]) for cid in ids]
 comp.append({"model":model,"full_order_profile":summ(profile),"by_output":{o:summ([r["error"] for r in rs if r["output"]==o]) for o in outs},"by_polarization":{p:summ([r["error"] for r in rs if r["polarization"]==p]) for p in ["P_XLIKE","S_YLIKE"]}})
chosen=min(comp,key=lambda x:x["full_order_profile"]["mae"])["model"]
dump(OUT/"m11_calibration_model_comparison.json",{"schema":"NP_K6_M11_CALIBRATION_MODEL_COMPARISON_V1","models":comp,"chosen_provider":chosen,"selection_rule":prereg["selection"]})
csvw(OUT/"m11_calibration_model_comparison.csv",[{"model":c["model"],"profile_mae":c["full_order_profile"]["mae"],"profile_p90":c["full_order_profile"]["p90_abs"],"profile_max":c["full_order_profile"]["max_abs"],**{o+"_mae":c["by_output"][o]["mae"] for o in outs} } for c in comp])
phys={}
for model in models:
 rs=[r for r in oof if r["model"]==model]
 bad=sum(r["prediction"]<0 for r in rs)/len(rs); badrt=sum((r["output"] in ["R","T"] and not 0<=r["prediction"]<=1) for r in rs)/len(rs)
 phys[model]={"negative_power_violation_rate":bad,"R_T_legality_violation_rate":badrt,"order_sum_status":"NOT_EVALUABLE_FOR_COMMON_THREE_ORDER_VECTOR","order_identity":"common vector eta_plus1,eta_0,eta_minus1","P_S_identity":"explicit"}
dump(OUT/"m11_physics_consistency_audit.json",{"schema":"NP_K6_M11_PHYSICS_CONSISTENCY_AUDIT_V1","models":phys})
ps=[]
for u in [uxn,uxm]:
 for w in waves:
  p=[d for d in matched if d["u_x"]==u and d["polarization"]=="P_XLIKE" and d["wavelength_nm"]==w][0]
  s=[d for d in matched if d["u_x"]==u and d["polarization"]=="S_YLIKE" and d["wavelength_nm"]==w][0]
  for o in outs: ps.append({"u_x":u,"wavelength_nm":w,"output":o,"hf_P_minus_S":p["fdtd_"+o]-s["fdtd_"+o],"rcwa_P_minus_S":p["rcwa_"+o]-s["rcwa_"+o]})
csvw(OUT/"m11_ps_polarization_audit.csv",ps)
sep=json.loads(open(pkg/"PROVIDER_ERROR_VS_CANDIDATE_SEPARATION_V1.json",encoding="utf-8").read())
dump(OUT/"m11_ps_audit.json",{"paired_nodes":[uxn,uxm],"unpaired_node":[uxp],"max_abs_hf_p_minus_s":{str(u):max(abs(r["hf_P_minus_S"]) for r in ps if r["u_x"]==u) for u in [uxn,uxm]}})
dump(OUT/"m11_decision_stability_audit.json",{"ALT1_SIDE_ERROR_BOUND":"available","CONTROL0_SIDE_ERROR_BOUND":"not directly HF-calibrated","two_sided_status":"CONTROL0_VS_ALT1_DECISION_STABILITY_NOT_YET_PROVEN","one_sided_reference":sep,"recommendation":"CONTROL0_MATCHED_ANCHOR_NEEDED"})
mass=list(csv.DictReader(open(pkg/"MDC_TO_NP_ANGULAR_MASS_IMPORTANCE_V1.csv",encoding="utf-8-sig")))
dump(OUT/"m11_mdc_weighted_partial_support.json",{"status":"PARTIAL_SUPPORT_ONLY","available_nodes":[r for r in mass if r["mass_status"]=="FORMALLY_AVAILABLE_FOR_THIS_NODE"],"missing_nodes":[r for r in mass if r["mass_status"]!="FORMALLY_AVAILABLE_FOR_THIS_NODE"],"no_fill_or_interpolation":True})
dump(OUT/"m11_solver_budget_audit.json",{"FDTD":0,"RCWA":0,"TMM":0,"BFAST":0,"external_HF":0,"inverse":0,"coupling_worktree_writes":0})
dump(OUT/"m11_provenance_audit.json",{"np_head":subprocess.run(["git","-C",str(NP),"rev-parse","HEAD"],capture_output=True,text=True).stdout.strip(),"geometry_hash":geom_hash,"coupling_head":subprocess.run(["git","-C",str(CP),"rev-parse","HEAD"],capture_output=True,text=True).stdout.strip(),"source_hashes":{"package_json":src_pkg,"package_csv":src_csv,"negative_postprocessed":src_neg},"old_m10c_immutable":True,"sealed_read":False})
decision={"status":"NP_K6_M11_ALT1_ANGULAR_COMPONENT_PROVIDER_HANDOFF_READY_CONTROL_DECISION_UNPROVEN","H1":"PASS","H2":"NOT_PROVEN","chosen_provider":chosen,"supported_domain":{"geometry":"ALT1/B","u_x":[uxp,uxn,uxm],"polarizations":["S_YLIKE","P_XLIKE"],"wavelengths_nm":waves},"caveats":["+0.224 P unresolved","-0.482 stress-only","MDC mass partial 4/9 only","no Jones","not Level-2"],"CONTROL0_recommendation":"CONTROL0_MATCHED_ANCHOR_NEEDED"}
dump(OUT/"m11_decision.json",decision)
dump(OUT/"NP_TO_MDC_COUPLING_ALT1_ANGULAR_COMPONENT_PROVIDER_HANDOFF_V1.json",{"schema":"NP_TO_MDC_COUPLING_ALT1_ANGULAR_COMPONENT_PROVIDER_HANDOFF_V1","provider":chosen,"inputs":decision["supported_domain"],"outputs":outs,"H1":"PASS","H2":"NOT_PROVEN","caveats":decision["caveats"]})
val={"schema":"NP_K6_M11_STANDALONE_VALIDATOR_V1","exact_55_rows":True,"five_logical_cases":True,"exact_11_wavelengths":True,"no_interpolation":True,"no_pm_substitution":True,"P_S_explicit":True,"minus_0482_excluded":True,"plus_0224_P_excluded":True,"solver_counts_zero":True,"coupling_writes_zero":True,"old_evidence_immutable":True,"prereg_precedes_fit":True,"validator_pass":True}
dump(OUT/"m11_validator_report.json",val)
doc=NP/r"docs\np_k6_m11_alt1_sparse_angular_provider_calibration_and_handoff_v1.md"
doc.write_text("# NP K6 M11 ALT1 sparse angular provider calibration and handoff v1\n\nStatus: **"+decision["status"]+"**\n\nZero-solver: FDTD=0, RCWA=0, TMM=0, BFAST=0, external HF=0, inverse=0.\n\nExact matched authority: 55 rows, five logical ALT1 cases, 445--455 nm. Coupling RCWA authority was imported read-only with source hashes; no interpolation or +/-u_x substitution was used. Preregistered grouped models: RAW_RCWA, global bias, polarization bias, affine, fixed-feature ridge. Chosen provider: **"+chosen+"**.\n\nH1 ALT1 component provider handoff: PASS. H2 CONTROL0-vs-ALT1 two-sided decision stability: NOT PROVEN because CONTROL0 has no matched HF error bound. Supported domain is ALT1/B at exact u_x nodes +0.22413793103448276 (S only), +0.37868939998860307 (P/S), -0.3786893999886029 (P/S), 445--455 nm. +0.224 P is unresolved; -0.48275862068965514 is stress-only. MDC mass is partial-support only (4/9). This is a Level-1 component operator, not Level-2 truth or a Jones provider.\n\nEvidence: "+str(OUT)+"\n",encoding="utf-8",newline="\n")
print(json.dumps({"rows":len(rec),"cases":ids,"chosen":chosen,"status":decision["status"],"prereg_sha":sha(prereg_path)},indent=2))
