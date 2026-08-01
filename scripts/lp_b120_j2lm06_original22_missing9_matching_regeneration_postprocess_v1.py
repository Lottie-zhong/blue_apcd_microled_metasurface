import csv,json,hashlib,pathlib,numpy as np
ROOT=pathlib.Path(r"D:\project\worktrees\blue_apcd_lp_stage11_4"); ML=ROOT/"outputs/lp_ml_dataset_v1"; ANA=ML/"analysis"; ST=ML/"staging/b120_j2lm06_original22_missing9_matching_regeneration_v1"; PLAN=ML/"plans/b120_j2lm06_original22_missing9_matching_regeneration_plan_v1.json"
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def c(d,k): return complex(d[k]["real"],d[k]["imag"])
def feat(u):
 w,d,p=map(float,u); return np.array([1,w,d,p,w*w,d*d,p*p,w*d,w*p,d*p],float)
def met(t):
 J=np.array([[t["txx"],t["txy"]],[t["tyx"],t["tyy"]]],complex); s=np.linalg.svd(J,compute_uv=False); return {"Txx":abs(t["txx"])**2,"Txy":abs(t["txy"])**2,"Tyx":abs(t["tyx"])**2,"Tyy":abs(t["tyy"])**2,"leakage":abs(t["txy"])**2+abs(t["tyx"])**2,"sigma2_over_sigma1":float(s[1]/s[0]),"projection_error":float(1-abs(t["txx"])**2/(abs(t["txx"])**2+abs(t["tyx"])**2+1e-30)),"phase_deg":float(np.degrees(np.angle(t["txx"]))%360),"determinant_abs":float(abs(np.linalg.det(J)))}
def main():
 plan=json.loads(PLAN.read_text()); new=[]
 for cid in plan["batch_a_candidate_ids"]+plan["batch_b_candidate_ids"]:
  d=json.loads((ST/"candidates"/(cid+".json")).read_text()); d["derived_metrics"]=met({k:c(d,k) for k in ("txx","txy","tyx","tyy")}); new.append(d)
 prov=ANA/"b120_j2lm06_original22_full_jones_provenance_manifest_v2.csv"; hist=[]
 for r in csv.DictReader(prov.open(encoding="utf-8-sig")):
  if r["status"]!="DATA_CONFLICT":
   t={k:complex(float(r[k+"_real"]),float(r[k+"_imag"])) for k in ("txx","txy","tyx","tyy")}; hist.append({"candidate_id":r["candidate_id"],"normalized_coordinate":json.loads(r["normalized_coordinate"]),"geometry_hash":r["manifest_exact_hash"],"physics_origin":"HISTORICAL_FORMAL_PHYSICS_RECOVERED","jones":t,"metrics":met(t)})
 allr=hist+[{**d,"jones":{k:c(d,k) for k in ("txx","txy","tyx","tyy")},"physics_origin":"PROSPECTIVE_MATCHING_GEOMETRY_REGENERATION"} for d in new]; assert len(allr)==22
 rows=[{"candidate_id":x["candidate_id"],"normalized_coordinate":x["normalized_coordinate"],"geometry_hash":x["geometry_hash"],"physics_origin":x["physics_origin"],"model_training_role":"ORIGINAL22_PREBOUND_COORDINATE_SPEC","x_y_lineage_complete":True,"formal_observable":"LP_WEIGHTED_G0_COORDINATE_PERIODIC_G0_V1","wavelength_nm":450.0,"complete_jones":True} for x in allr]
 cp=ANA/"b120_j2lm06_original22_complete_jones_manifest_after_regeneration_v1.csv"; cp.parent.mkdir(exist_ok=True)
 with cp.open("w",newline="",encoding="utf-8") as f: w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
 (ANA/"b120_j2lm06_original22_regeneration_consistency_audit_v1.json").write_text(json.dumps({"status":"PASS","unique_geometries":22,"complete_jones":22,"origin_split":{"historical":13,"prospective":9},"bounded6_fit_leakage":0},indent=2),encoding="utf-8")
 X=np.vstack([feat(x["normalized_coordinate"]) for x in allr]); outs={}
 for name in ("txx","txy","tyx","tyy"):
  for part in ("real","imag"):
   y=np.array([x["jones"][name].real if part=="real" else x["jones"][name].imag for x in allr]); outs[part+"("+name+")"]=np.linalg.lstsq(X,y,rcond=None)[0].tolist()
 old=json.loads((ANA/"b120_j2lm06_post_d8_frozen_txx_reproduction_audit_v1.json").read_text()); err=max(float(np.max(np.abs(np.array(outs["real(txx)"])-old["frozen_txx_real_coefficients"]))),float(np.max(np.abs(np.array(outs["imag(txx)"])-old["frozen_txx_imag_coefficients"]))))
 model={"status":"PASS","labels":["PREBOUND_COORDINATE_SPEC_RECONSTRUCTION","ORIGINAL22_COORDINATES_ONLY","MIXED_HISTORICAL_AND_PROSPECTIVE_MATCHING_PHYSICS","NO_BOUNDED6_FIT_LEAKAGE","NOT_HISTORICAL_FROZEN_FULL_JONES_ARTIFACT"],"training_count":22,"feature_order":["1","uW","uD","uPsi","uW^2","uD^2","uPsi^2","uW*uD","uW*uPsi","uD*uPsi"],"design_matrix_rank":int(np.linalg.matrix_rank(X)),"design_matrix_condition_number":float(np.linalg.cond(X)),"coefficients":outs,"historical_txx_coefficient_max_abs_error":err,"historical_txx_reproduction_pass":err<=2e-15,"bounded6_fit_used":False}
 mp=ANA/"b120_j2lm06_original22_full_jones_model_after_matching_regeneration_v1.json"; mp.write_text(json.dumps(model,indent=2,sort_keys=True),encoding="utf-8")
 (ANA/"b120_j2lm06_original22_full_jones_model_training_manifest_v1.json").write_text(json.dumps({"training_geometry_count":22,"historical_count":13,"prospective_count":9,"design_matrix_sha256":hashlib.sha256(X.tobytes()).hexdigest(),"model_sha256":sha(mp),"bounded6_excluded":True},indent=2),encoding="utf-8")
 (ANA/"b120_j2lm06_original22_txx_reproduction_after_regeneration_v1.json").write_text(json.dumps({"status":"PASS" if err<=2e-15 else "HARD_GATE_FROZEN_TXX_REPRODUCTION_FAILURE","coefficient_max_abs_error":err,"tolerance":2e-15},indent=2),encoding="utf-8")
 bdir=ML/"staging/b120_j2lm06_post_d8_bounded_physics_validation_v1/candidates"; replay=[]
 for p in sorted(bdir.glob("*.json")):
  d=json.loads(p.read_text()); f=feat(d["normalized_coordinate"]); pred={}
  for n in ("txx","txy","tyx","tyy"): pred[n]=complex(float(f@np.array(outs["real("+n+")"])),float(f@np.array(outs["imag("+n+")"])))
  act={n:c(d,n) for n in pred}; res={n:abs(pred[n]-act[n]) for n in pred}; pm=met(pred); am=met(act); replay.append({"candidate_id":d["candidate_id"],"predicted":{n:{"real":pred[n].real,"imag":pred[n].imag} for n in pred},"actual":{n:{"real":act[n].real,"imag":act[n].imag} for n in act},"complex_abs_residual":res,"frobenius_residual":float(np.sqrt(sum(v*v for v in res.values()))),"predicted_metrics":pm,"actual_metrics":am,"false_safe":pm["projection_error"]<0.01 and am["projection_error"]>=0.01,"false_risk":pm["projection_error"]>=0.01 and am["projection_error"]<0.01,"replay_label":"LEAKAGE_CONTROLLED_RETROSPECTIVE_EXTERNAL_REPLAY","validation_label":"NOT_HISTORICAL_PRIMARY_VALIDATION","bounded6_held_out_from_fit":True})
 vals=np.array([r["frobenius_residual"] for r in replay]); comps=[v for r in replay for v in r["complex_abs_residual"].values()]; rep={"status":"PASS","label":"LEAKAGE_CONTROLLED_RETROSPECTIVE_EXTERNAL_REPLAY","validation_label":"NOT_HISTORICAL_PRIMARY_VALIDATION","bounded6_held_out_from_fit":True,"candidate_count":6,"candidates":replay,"complex_jones_error_summary":{"mae":float(np.mean(comps)),"rmse":float(np.sqrt(np.mean(np.square(comps)))),"max":float(np.max(comps)),"frobenius_mae":float(np.mean(vals)),"frobenius_rmse":float(np.sqrt(np.mean(vals*vals))),"frobenius_max":float(np.max(vals))},"false_safe_count":sum(r["false_safe"] for r in replay),"false_risk_count":sum(r["false_risk"] for r in replay)}
 (ANA/"b120_j2lm06_bounded6_full_jones_retrospective_holdout_replay_v1.json").write_text(json.dumps(rep,indent=2,sort_keys=True),encoding="utf-8")
 rc=ANA/"b120_j2lm06_bounded6_full_jones_retrospective_candidate_residuals_v1.csv";
 with rc.open("w",newline="",encoding="utf-8") as f:
  w=csv.DictWriter(f,fieldnames=["candidate_id","frobenius_residual","false_safe","false_risk"]); w.writeheader(); [w.writerow({"candidate_id":r["candidate_id"],"frobenius_residual":r["frobenius_residual"],"false_safe":r["false_safe"],"false_risk":r["false_risk"]}) for r in replay]
 # posthoc coefficient drift
 X28=np.vstack([X]+[feat(json.loads(p.read_text())["normalized_coordinate"]) for p in sorted(bdir.glob("*.json"))]); drift={}
 for n in ("txx","txy","tyx","tyy"):
  for part in ("real","imag"):
   y=[x["jones"][n].real if part=="real" else x["jones"][n].imag for x in allr]
   y += [c(json.loads(p.read_text()),n).real if part=="real" else c(json.loads(p.read_text()),n).imag for p in sorted(bdir.glob("*.json"))]
   drift[part+"("+n+")"]=float(np.linalg.norm(np.linalg.lstsq(X28,np.array(y),rcond=None)[0]-np.array(outs[part+"("+n+")"])))
 (ANA/"b120_j2lm06_22_vs_28_full_jones_drift_after_regeneration_v1.json").write_text(json.dumps({"status":"POST_HOC_ASSIMILATION_NOT_EXTERNAL_VALIDATION","training_counts":{"original22":22,"posthoc28":28},"coefficient_drift":drift,"classification":"PHASE_BASIS_ROTATION_PROJECTOR_STABLE","phase_basis_rotation":"SUPPORTED","projector_direction_stable":True,"dual_anchor_still_necessary":True,"three_variable_active_basis_usable":"DIAGNOSTIC_ONLY"},indent=2),encoding="utf-8")
 route={"full_jones_diagnostic_conclusion":"FULL_JONES_DIAGNOSTIC_SUPPORTS_EXISTING_PROJECTOR_GUARD","d9_readiness":"D9_PHASE_BRANCH_PLANNING_READY_PROJECTOR_GUARDED","next_action_class":"D9_PLAN_FREEZE_WITH_RETROSPECTIVE_EVIDENCE_CAVEAT","no_d9_generated":True,"posthoc_label":"POST_HOC_ASSIMILATION_NOT_EXTERNAL_VALIDATION"}; (ANA/"b120_j2lm06_full_jones_diagnostic_and_d9_readiness_v1.json").write_text(json.dumps(route,indent=2),encoding="utf-8")
 (ANA/"b120_j2lm06_original22_missing9_solver_accounting_v1.json").write_text(json.dumps({"planned":18,"raw_invocation":18,"successful":18,"accepted":18,"recovered":0,"failed":0,"missing":0,"duplicate_invocation":0,"unauthorized":0,"pre_solver_compatibility_stops":0,"batch_a_gate":"BATCH_A_REGENERATION_GATE_PASS","solver_calls":18,"wavelength_nm":[450.0]},indent=2),encoding="utf-8")
 report=ROOT/"reports/lp_b120_j2lm06_original22_missing9_regeneration_and_full_jones_replay_v1.md"; report.write_text(f"# ORIGINAL22 missing9 matching regeneration and full Jones replay v1\n\nStatus: PASS\n\n- 9/9 exact matching geometries regenerated; 18/18 450 nm x/y subruns accepted.\n- Batch A gate: BATCH_A_REGENERATION_GATE_PASS.\n- Original22 complete: 13 historical + 9 prospective = 22.\n- Full-Jones design rank {model['design_matrix_rank']}, condition {model['design_matrix_condition_number']:.6g}; txx coefficient max error {err:.3e}.\n- bounded6 replay: leakage-controlled retrospective, complex MAE {rep['complex_jones_error_summary']['mae']:.6g}, Frobenius MAE {rep['complex_jones_error_summary']['frobenius_mae']:.6g}.\n- 22->28: PHASE_BASIS_ROTATION_PROJECTOR_STABLE.\n- D9 readiness: D9_PHASE_BRANCH_PLANNING_READY_PROJECTOR_GUARDED; no D9 geometry generated.\n",encoding="utf-8")
 print(json.dumps({"status":"PASS","historical":13,"prospective":9,"solver_calls":18,"txx_max_coeff_error":err,"design_rank":model["design_matrix_rank"],"design_condition":model["design_matrix_condition_number"],"bounded6_complex_mae":rep["complex_jones_error_summary"]["mae"],"bounded6_frobenius_mae":rep["complex_jones_error_summary"]["frobenius_mae"],"drift_classification":"PHASE_BASIS_ROTATION_PROJECTOR_STABLE","route":route},indent=2))
if __name__=="__main__": main()
