from __future__ import annotations
import csv, json, hashlib, datetime, math, random, statistics
from pathlib import Path
from collections import defaultdict

ROOT=Path(r"D:\\project\\worktrees\\blue_apcd_np_k6_mdc_v1")
M4=ROOT/"outputs"/"np_k6_m4_batch2_geometry_selection_v1"
M5=ROOT/"outputs"/"np_k6_m5_fullk6_forward_v0"
M5B=ROOT/"outputs"/"np_k6_m5b_forward_formulation_repair_v1"
OUT=ROOT/"outputs"/"np_k6_m6_error_region_acquisition_design_v1"
WLS=list(range(445,456))

def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''): h.update(b)
 return h.hexdigest()
def read_csv(p):
 with p.open(encoding='utf-8-sig',newline='') as f: return list(csv.DictReader(f))
def write_csv(p,rows):
 p.parent.mkdir(parents=True,exist_ok=True)
 if not rows: return
 with p.open('w',encoding='utf-8',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
def dump(p,x): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(x,indent=2,sort_keys=True)+"\n",encoding='utf-8')
def f(x):
 try: return float(x)
 except Exception: return float('nan')
def finite(x):
 try:
  v=float(x)
 except Exception:
  return None
 return v if math.isfinite(v) else None
def norm(vals):
 a=[float(x) for x in vals]; good=[x for x in a if math.isfinite(x)]; repl=statistics.median(good) if good else 0.0; a=[x if math.isfinite(x) else repl for x in a]; lo=min(a); hi=max(a)
 return [0.5 if hi-lo<1e-12 else (x-lo)/(hi-lo) for x in a]
def parse_ds(g):
 import re
 return [float(x) for x in re.findall(r'D(\d+)',g)]
def pairwise_dist(a,b):
 return math.sqrt(sum((float(x)-float(y))**2 for x,y in zip(a,b)))
def distances_to(points,ref):
 return [min((pairwise_dist(p,q) for q in ref),default=float('nan')) for p in points]
def quant(values,q):
 a=sorted(float(x) for x in values if math.isfinite(float(x)))
 if not a:return float('nan')
 return float(a[min(len(a)-1,max(0,int(round(q*(len(a)-1)))) )])

def load_authority():
 OUT.mkdir(parents=True,exist_ok=True)
 sel=read_csv(M4/"m4_candidate_selection_long.csv")
 feat=read_csv(M4/"m4_geometry_feature_space.csv")
 effective={r['geometry_id']:r for r in feat if r['is_effective_candidate']=='True'}
 hf_rows=read_csv(M5/"m5_training_view_286rows.csv")
 hf13=sorted({r['geometry_id'] for r in hf_rows})
 external=json.loads((M5/"external_set_registry.json").read_text(encoding='utf-8'))
 ext_ids={r['geometry_id'] for r in external['geometries']}
 selected={r['geometry_id']:r for r in sel}
 overlap_hf=sorted(set(effective)&set(hf13)); overlap_ext=sorted(set(effective)&ext_ids)
 duplicate_hash=len({r['geometry_hash'] for r in effective.values()}) != len(effective)
 ordered_bad=[]
 for gid,r in selected.items():
  ds=parse_ds(gid)
  if any(abs(float(r[f'D{i}'])-ds[i])>1e-9 for i in range(6)): ordered_bad.append(gid)
 # M5B authority values are read-only; no sealed target is consulted.
 m5b_dec=json.loads((M5B/"m5b_final_decision.json").read_text(encoding='utf-8'))
 if m5b_dec.get('status')!='NP_K6_M5B_FORMULATION_REPAIR_COMPLETE_MORE_DEVELOPMENT_HF_REQUIRED': raise RuntimeError('unexpected M5B authority')
 audit={'m4_effective_candidate_count':len(effective),'hf13_geometry_count':len(hf13),'hf13_ids':hf13,'existing_hf_overlap':overlap_hf,'external_overlap':overlap_ext,'duplicate_geometry_hash':duplicate_hash,'physical_order_bad':ordered_bad,'sealed_target_reads':0,'external_target_reads':0,'solver_calls':0,'development_candidate_count_after_exclusion':len(set(effective)-set(hf13)-ext_ids),'source_selection_sha256':sha(M4/"m4_candidate_selection_long.csv"),'source_feature_sha256':sha(M4/"m4_geometry_feature_space.csv"),'m5b_decision':m5b_dec}
 if overlap_ext or duplicate_hash or ordered_bad: raise RuntimeError('M6 split/provenance hard stop')
 candidates=[selected[g] for g in sorted(set(effective)-set(hf13)-ext_ids)]
 featmap={r['geometry_id']:r for r in feat}
 return candidates,featmap,hf13,ext_ids,audit,hf_rows

def compute_lf_bias(hf_rows):
 oof=read_csv(M5/"oof_predictions.csv")
 by={(r['case_id'],int(r['wavelength_nm'])):r for r in oof if r['model']=='lf_only' and r['seed']=='ensemble'}
 vals=[]
 for r in hf_rows:
  q=by[(r['case_id'],int(r['wavelength_nm']))]
  vals.append(float(r['eta_m+1'])-float(q['pred_eta_m+1']))
 return float(statistics.mean(vals)),float(statistics.pstdev(vals)),len(vals)

def build_prereg(audit):
 p={'preregistration_id':'NP_K6_M6_ERROR_REGION_ACQUISITION_PREREG_V1','created_utc':now(),'scope':'development-only error-region acquisition design; zero solver; no external/sealed target reads','candidate_universe':{'source':'M4 effective development candidate pool minus current HF13 and external registry','effective_source_count':audit['m4_effective_candidate_count'],'hf13_excluded':audit['existing_hf_overlap'],'external_excluded':audit['external_overlap'],'expected_final_count':audit['development_candidate_count_after_exclusion']},'inputs':['ordered physical D1...D6','adjacent jumps and standardized M4 physical feature space','LF eta(+1)/T/R and spectral proxies','CNN/MLP/LF disagreement','predicted P/S discrepancy','nearest-HF13 distance','M5B calibrated LF residual bias'],'proxy_definitions':{'eta_plus1_absolute_residual':'calibrated LF eta(+1) disagreement plus CNN/MLP and LF model discrepancy; heuristic only','full_order_profile':'aggregate normalized T/R/eta(+1)/directionality/non-target disagreement','RT_residual':'aggregate CNN-LF and CNN-MLP T/R disagreement','ps_contrast':'aggregate predicted P/S T/R/eta(+1)/directionality/non-target discrepancy','tail_error':'maximum normalized disagreement and robust-response stress','model_disagreement':'CNN-versus-MLP disagreement aggregate','coverage':'physical feature-space distance to current HF13, capped at 90th percentile','performance':'M4 performance potential, used only as one role component'},'normalization':'candidate-pool min-max after exclusions; physical distances from frozen standardized M4 feature space; no HF target normalization','roles':{'ERROR-1':'highest calibrated-LF residual risk without pathological exclusion','POLARIZATION-STRESS':'highest predicted P/S contrast information','COVERAGE-EXTRAPOLATION-CONTROL':'largest representative HF13 feature-space gap, capped against isolated extremes','PERFORMANCE+ERROR':'high broadband eta(+1) potential with material disagreement'},'selection_policy':{'primary4_quota':{'ERROR-1':1,'POLARIZATION-STRESS':1,'COVERAGE-EXTRAPOLATION-CONTROL':1,'PERFORMANCE+ERROR':1},'backups':8,'redundancy_penalty':'0.25 when physical feature distance below 1.0; deterministic greedy selection','tie_break':'score descending, then geometry_id ascending','expansion':'first6=Primary4+backup1-2; first8=first6+backup3-4','random_seed':20260812},'exclusions':['current HF13 geometries','sealed external registry geometries','duplicate geometry hashes','non-development geometry','formal external target values'],'solver_budget_package':{'primary4_logical_cases':8,'first6_logical_cases':12,'first8_logical_cases':16,'polarizations':['p','s'],'wavelengths':WLS,'u_x':[0.0]},'external_registry':'NP_K6_FORWARD_EXTERNAL_FROZEN_SET_V1','solver_calls':0,'sealed_target_reads':0,'external_target_reads':0,'inverse_design':0}
 path=OUT/(p['preregistration_id']+'.json'); dump(path,p); dump(OUT/'m6_preregistration_sha256.json',{'path':str(path.relative_to(ROOT)),'sha256':sha(path),'created_utc':p['created_utc'],'must_precede_final_identities':True}); return p,sha(path)

def select(candidates,featmap,hf13,lf_bias,prereg_sha):
 # Build numeric candidate table from M4 prediction profiles; these are proxies, not HF labels.
 frows=[featmap[r['geometry_id']] for r in candidates]; matrix={r['geometry_id']:[f(r[f'feature_{i:02d}']) for i in range(20)] for r in frows}
 hfpts=[matrix[g] for g in hf13 if g in matrix]
 if not hfpts:
  # feature rows for HF13 are not effective candidates; recover their rows from full M4 feature table.
  allfeat=read_csv(M4/"m4_geometry_feature_space.csv"); am={r['geometry_id']:[f(r[f'feature_{i:02d}']) for i in range(20)] for r in allfeat}; hfpts=[am[g] for g in hf13 if g in am]
 candpts=[matrix[r['geometry_id']] for r in candidates]
 nearest=distances_to(candpts,hfpts)
 # Use frozen M4 columns. The LF bias is estimated only from HF13 authority and applied prospectively as a proxy.
 rec=[]
 raw={}
 for r,dist in zip(candidates,nearest):
  gid=r['geometry_id'];
  vals={k:f(r.get(k,'')) for k in ['cnn_lf_eta_plus1_discrepancy_mean','cnn_mlp_eta_plus1_discrepancy_mean','cnn_lf_T_discrepancy_mean','cnn_mlp_T_discrepancy_mean','cnn_lf_R_discrepancy_mean','cnn_mlp_R_discrepancy_mean','cnn_lf_directionality_discrepancy_mean','cnn_mlp_directionality_discrepancy_mean','cnn_lf_non_target_efficiency_discrepancy_mean','cnn_mlp_non_target_efficiency_discrepancy_mean','predicted_ps_T_discrepancy_mean','predicted_ps_R_discrepancy_mean','predicted_ps_eta_plus1_discrepancy_mean','predicted_ps_directionality_discrepancy_mean','predicted_ps_non_target_efficiency_discrepancy_mean','cnn_eta_plus1_mean','mlp_eta_plus1_mean','lf_eta_plus1_mean','predicted_eta_robust_mean','predicted_eta_robust_min','performance_score','coverage_score','conflict_score']}
  eta_abs=0.45*vals['cnn_lf_eta_plus1_discrepancy_mean']+0.35*vals['cnn_mlp_eta_plus1_discrepancy_mean']+0.20*abs(vals['mlp_eta_plus1_mean']-(vals['lf_eta_plus1_mean']+lf_bias))
  order=(sum(vals[k] for k in ['cnn_lf_T_discrepancy_mean','cnn_mlp_T_discrepancy_mean','cnn_lf_R_discrepancy_mean','cnn_mlp_R_discrepancy_mean','cnn_lf_eta_plus1_discrepancy_mean','cnn_mlp_eta_plus1_discrepancy_mean','cnn_lf_directionality_discrepancy_mean','cnn_mlp_directionality_discrepancy_mean','cnn_lf_non_target_efficiency_discrepancy_mean','cnn_mlp_non_target_efficiency_discrepancy_mean'])/10.0)
  rt=(vals['cnn_lf_T_discrepancy_mean']+vals['cnn_mlp_T_discrepancy_mean']+vals['cnn_lf_R_discrepancy_mean']+vals['cnn_mlp_R_discrepancy_mean'])/4.0
  ps=(vals['predicted_ps_T_discrepancy_mean']+vals['predicted_ps_R_discrepancy_mean']+vals['predicted_ps_eta_plus1_discrepancy_mean']+vals['predicted_ps_directionality_discrepancy_mean']+vals['predicted_ps_non_target_efficiency_discrepancy_mean'])/5.0
  model=(vals['cnn_mlp_T_discrepancy_mean']+vals['cnn_mlp_R_discrepancy_mean']+vals['cnn_mlp_eta_plus1_discrepancy_mean']+vals['cnn_mlp_directionality_discrepancy_mean']+vals['cnn_mlp_non_target_efficiency_discrepancy_mean'])/5.0
  tail=max(vals['cnn_lf_eta_plus1_discrepancy_mean'],vals['cnn_mlp_eta_plus1_discrepancy_mean'],vals['predicted_ps_eta_plus1_discrepancy_mean'],vals['cnn_mlp_directionality_discrepancy_mean'])
  raw[gid]={'eta_plus1_residual_proxy':eta_abs,'order_profile_error_proxy':order,'rt_error_proxy':rt,'ps_contrast_risk_proxy':ps,'model_disagreement':model,'tail_error_proxy':tail,'nearest_hf13_distance':dist,'performance_potential':0.6*vals['predicted_eta_robust_mean']+0.4*vals['performance_score'],'lf_eta_plus1_mean':vals['lf_eta_plus1_mean'],'calibrated_lf_eta_plus1':vals['lf_eta_plus1_mean']+lf_bias,'lf_eta_plus1_min':vals['lf_eta_plus1_mean'],'predicted_eta_robust_min':vals['predicted_eta_robust_min'],'predicted_eta_robust_mean':vals['predicted_eta_robust_mean'],'m4_role':r.get('role','')}
 for k in ['eta_plus1_residual_proxy','order_profile_error_proxy','rt_error_proxy','ps_contrast_risk_proxy','model_disagreement','tail_error_proxy','nearest_hf13_distance','performance_potential']:
  z=norm([raw[g][k] for g in raw])
  for g,v in zip(raw,z): raw[g][k+'_norm']=v
 def score(g,role):
  q=raw[g]
  if role=='ERROR-1': return .55*q['eta_plus1_residual_proxy_norm']+.25*q['order_profile_error_proxy_norm']+.20*q['tail_error_proxy_norm']
  if role=='POLARIZATION-STRESS': return .70*q['ps_contrast_risk_proxy_norm']+.30*q['model_disagreement_norm']
  if role=='COVERAGE-EXTRAPOLATION-CONTROL': return .75*q['nearest_hf13_distance_norm']+.25*(1-q['tail_error_proxy_norm'])
  return .50*q['performance_potential_norm']+.30*q['eta_plus1_residual_proxy_norm']+.20*q['model_disagreement_norm']
 roles=['ERROR-1','POLARIZATION-STRESS','COVERAGE-EXTRAPOLATION-CONTROL','PERFORMANCE+ERROR']
 chosen=[]; role_rows=[]
 for role in roles:
  order=sorted(raw,key=lambda g:(-score(g,role),g))
  best=None; bestadj=-1e9
  for g in order:
   penalty=.25*sum(max(0.0,1.0-pairwise_dist(matrix[g],matrix[h])) for h in chosen)
   adj=score(g,role)-penalty
   if adj>bestadj or (abs(adj-bestadj)<1e-12 and g<(best or '')): best,bestadj=g,adj
  chosen.append(best); role_rows.append((best,role,bestadj))
 # Backups use the same deterministic composite with diversity penalty.
 backups=[]; remaining=[g for g in raw if g not in chosen]
 for rank in range(1,9):
  def comp(g):
   q=raw[g]; base=.35*q['eta_plus1_residual_proxy_norm']+.25*q['ps_contrast_risk_proxy_norm']+.20*q['nearest_hf13_distance_norm']+.20*q['performance_potential_norm']
   pen=.25*sum(max(0.0,1.0-pairwise_dist(matrix[g],matrix[h])) for h in chosen+backups)
   return base-pen
  g=sorted(remaining,key=lambda x:(-comp(x),x))[0]; backups.append(g); remaining.remove(g)
 # Candidate rows and role scores.
 score_rows=[]
 for g in sorted(raw):
  q=raw[g]; row=next(r for r in candidates if r['geometry_id']==g); z={'geometry_id':g,'geometry_hash':row['geometry_hash'],'D1':row['D0'],'D2':row['D1'],'D3':row['D2'],'D4':row['D3'],'D5':row['D4'],'D6':row['D5'],'role':next((r for gg,r,a in role_rows if gg==g),'not_selected'),'candidate_rank_composite':None,'selection_rationale': ''}
  for k,v in q.items(): z[k]=finite(v)
  z['error1_role_score']=finite(score(g,'ERROR-1')); z['polarization_stress_role_score']=finite(score(g,'POLARIZATION-STRESS')); z['coverage_role_score']=finite(score(g,'COVERAGE-EXTRAPOLATION-CONTROL')); z['performance_error_role_score']=finite(score(g,'PERFORMANCE+ERROR'))
  if g in chosen: z['selection_rationale']='Primary4 role quota with redundancy-aware greedy selection'
  elif g in backups: z['selection_rationale']='Frozen expansion backup with redundancy-aware composite score'
  score_rows.append(z)
 for i,g in enumerate(backups,1):
  for z in score_rows:
   if z['geometry_id']==g: z['role']=f'backup_rank_{i}'; z['candidate_rank_composite']=i
 for i,g in enumerate(chosen,1):
  for z in score_rows:
   if z['geometry_id']==g: z['candidate_rank_composite']=i
 return raw,matrix,score_rows,chosen,backups

def coverage_metrics(ids,raw,matrix,hf13,allfeat):
 amap={r['geometry_id']:[f(r[f'feature_{i:02d}']) for i in range(20)] for r in allfeat}
 base=[amap[g] for g in hf13 if g in amap]; sel=[matrix[g] for g in ids]
 allpts=[matrix[g] for g in raw]
 def stats(ref):
  d=distances_to(allpts,ref); return {'mean':statistics.mean(d),'p90':quant(d,.90),'max':max(d),'min':min(d)}
 return stats(base),stats(base+sel),{'mean_pairwise':statistics.mean([pairwise_dist(matrix[a],matrix[b]) for i,a in enumerate(ids) for b in ids[i+1:]]) if len(ids)>1 else 0.0,'min_pairwise':min([pairwise_dist(matrix[a],matrix[b]) for i,a in enumerate(ids) for b in ids[i+1:]],default=0.0)}

def main():
 candidates,featmap,hf13,ext_ids,audit,hf_rows=load_authority()
 prereg,pre_sha=build_prereg(audit)
 lf_bias,lf_std,lf_n=compute_lf_bias(hf_rows)
 raw,matrix,score_rows,primary,backups=select(candidates,featmap,hf13,lf_bias,pre_sha)
 allfeat=read_csv(M4/"m4_geometry_feature_space.csv")
 # Comparison baselines use the identical candidate universe and deterministic seed.
 gids=sorted(raw); rng=random.Random(20260812); random4=sorted(rng.sample(gids,4)); perf4=sorted(gids,key=lambda g:(-f(next(r for r in candidates if r['geometry_id']==g).get('performance_score','')) ,g))[:4]; cov4=sorted(gids,key=lambda g:(-raw[g]['nearest_hf13_distance'],g))[:4]
 sets={'proposed_primary4':primary,'random4_seed_20260812':random4,'performance_only_top4':perf4,'coverage_only_top4':cov4,'proposed_first6':primary+backups[:2],'proposed_first8':primary+backups[:4]}
 comp=[]
 for name,ids in sets.items():
  base,added,pair=coverage_metrics(ids,raw,matrix,hf13,allfeat); riskq=sorted(raw,key=lambda g:-raw[g]['eta_plus1_residual_proxy']); psq=sorted(raw,key=lambda g:-raw[g]['ps_contrast_risk_proxy'])
  comp.append({'set':name,'size':len(ids),'geometry_ids':ids,'physical_mean_nearest_distance_before':base['mean'],'physical_mean_nearest_distance_after':added['mean'],'physical_p90_after':added['p90'],'physical_max_after':added['max'],'pairwise_mean_distance':pair['mean_pairwise'],'pairwise_min_distance':pair['min_pairwise'],'top_quartile_eta_residual_covered':sum(g in ids for g in riskq[:max(1,len(raw)//4)])/max(1,len(raw)//4),'top_quartile_ps_risk_covered':sum(g in ids for g in psq[:max(1,len(raw)//4)])/max(1,len(raw)//4)})
 write_csv(OUT/"m6_selection_comparison.csv",comp)
 # Runtime empirical distribution from completed P0/Batch1/M4 ledgers; G04-P is retained as infra-risk note, not clean sample.
 runt=[]; infra=[]
 for p in (ROOT/"outputs").rglob('attempt_ledger.json'):
  if not any(tag in str(p).lower() for tag in ['np_k6_m2_batch1','np_k6_m4_batch2_primary4','np_k6_p0_remaining_five_anchors_execution_v1']): continue
  try: d=json.loads(p.read_text(encoding='utf-8'))
  except Exception: continue
  if d.get('engine_completed') and d.get('controller_started_timestamp_utc') and d.get('engine_completed_timestamp_utc'):
   t=(datetime.datetime.fromisoformat(d['engine_completed_timestamp_utc'])-datetime.datetime.fromisoformat(d['controller_started_timestamp_utc'])).total_seconds()
   if d.get('post_saved'): runt.append(t)
   else: infra.append({'path':str(p.relative_to(ROOT)),'engine_seconds':t,'post_saved':False})
 runtime_summary={'clean_samples':len(runt),'clean_median_seconds':statistics.median(runt) if runt else None,'clean_p90_seconds':quant(runt,.90),'clean_max_seconds':max(runt) if runt else None,'clean_median_hours':(statistics.median(runt)/3600 if runt else None),'clean_p90_hours':(quant(runt,.90)/3600 if runt else None),'clean_max_hours':(max(runt)/3600 if runt else None),'infrastructure_loss_cases':infra,'source':'P0 remaining anchors + Batch1 + M4 Batch2 attempt ledgers','fixed_three_hour_assumption_used':False}
 write_csv(OUT/"m6_runtime_empirical_distribution.csv",[{'sample_seconds':x,'sample_hours':x/3600} for x in sorted(runt)])
 cost=[]
 for name,n in [('Primary4',4),('first6',6),('first8',8)]: cost.append({'batch':name,'geometry_count':n,'logical_cases_p_s':2*n,'median_total_hours':runtime_summary['clean_median_hours']*2*n,'p90_total_hours':runtime_summary['clean_p90_hours']*2*n,'max_total_hours':runtime_summary['clean_max_hours']*2*n})
 dump(OUT/"m6_solver_cost_package.json",{'runtime_empirical':runtime_summary,'costs':cost,'historical_max_risk_note':'G04-P engine completed but post-save was not recovered; infrastructure-loss is tracked separately and is not treated as a clean runtime sample.','solver_calls':0})
 # Expansion order and primary role evidence.
 rolemap={g:r for g,r,a in [(g,r,a) for g,r,a in []]}
 primary_rows=[]
 for i,g in enumerate(primary,1):
  z=next(x for x in score_rows if x['geometry_id']==g); primary_rows.append({'rank':i,'geometry_id':g,'geometry_hash':z['geometry_hash'],'role':z['role'],'selection_rationale':z['selection_rationale']})
 dump(OUT/"m6_primary4_selection.json",{'selection_id':'NP_K6_M6_ERROR_REGION_PRIMARY4_V1','preregistration_sha256':pre_sha,'primary4':primary_rows,'role_quota_satisfied':len({z['role'] for z in primary_rows})==4,'solver_calls':0})
 write_csv(OUT/"m6_candidate_scores.csv",score_rows)
 write_csv(OUT/"m6_ranked_backups.csv",[next(z for z in score_rows if z['geometry_id']==g) for g in backups])
 dump(OUT/"m6_expansion_order.json",{'primary4':primary,'first6':primary+backups[:2],'first8':primary+backups[:4],'backups_ranked':backups,'solver_calls':0})
 dump(OUT/"m6_selection_policy.json",{'preregistration_sha256':pre_sha,'policy':'role-quota plus redundancy-aware deterministic greedy selection','roles':['ERROR-1','POLARIZATION-STRESS','COVERAGE-EXTRAPOLATION-CONTROL','PERFORMANCE+ERROR'],'redundancy_penalty':'0.25*sum(max(0,1-distance)) for distance<1.0','tie_break':'score descending then geometry_id ascending','random_baseline_seed':20260812,'candidate_pool_count':len(candidates)})
 dump(OUT/"candidate_universe_audit.json",audit|{'candidate_ids':gids,'candidate_hashes':{r['geometry_id']:r['geometry_hash'] for r in candidates},'hf13_overlap_after_exclusion':sorted(set(gids)&set(hf13)),'external_overlap_after_exclusion':sorted(set(gids)&ext_ids),'lf_eta_plus1_residual_bias_hf13':lf_bias,'lf_eta_plus1_residual_std_hf13':lf_std,'lf_authority_rows':lf_n})
 dump(OUT/"m6_coverage_summary.json",{'comparisons':comp,'marginal_gain_primary4_to_first6':{'physical_mean_nearest_distance_after':next(x for x in comp if x['set']=='proposed_first6')['physical_mean_nearest_distance_after']-next(x for x in comp if x['set']=='proposed_primary4')['physical_mean_nearest_distance_after']},'marginal_gain_first6_to_first8':{'physical_mean_nearest_distance_after':next(x for x in comp if x['set']=='proposed_first8')['physical_mean_nearest_distance_after']-next(x for x in comp if x['set']=='proposed_first6')['physical_mean_nearest_distance_after']}})
 dump(OUT/"m6_external_registry_audit.json",{'registry_id':'NP_K6_FORWARD_EXTERNAL_FROZEN_SET_V1','geometry_count':12,'metadata_only':True,'sealed_hf_target_read':0,'used_as_m6_candidate':False,'training_geometry_intersection':[],'external_candidate_overlap':[],'solver_calls':0})
 m5b_pre=json.loads((M5B/'m5b_preregistration_sha256.json').read_text(encoding='utf-8')).get('sha256')
 dump(OUT/"m6_provenance_audit.json",{'candidate_source':'M4 effective development candidate pool','m5b_prereg_sha256':m5b_pre,'m6_prereg_sha256':pre_sha,'m4_selection_policy_hash':json.loads((M4/'m4_selection_policy.json').read_text())['policy_hash'],'hf13_source':'M5 m5_training_view_286rows.csv','sealed_registry_source':'M5 external_set_registry.json metadata only','duplicate_conflicting_provenance':0,'sealed_target_reads':0,'external_target_reads':0,'inverse_design_artifacts':0})
 dump(OUT/"m6_solver_zero_audit.json",{'solver_calls':0,'fdtd_run_calls':0,'lumapi_solver_run_calls':0,'external_hf_calls':0,'sealed_target_reads':0,'inverse_design_artifacts':0,'candidate_performance_labels_created':False})
 decision='NP_K6_M6_ERROR_REGION_ACQUISITION_DESIGN_READY_FOR_SOLVER_AUTHORIZATION'
 dump(OUT/"m6_decision.json",{'status':decision,'recommended_batch':'Primary4','primary4':primary,'backups':backups,'first6':primary+backups[:2],'first8':primary+backups[:4],'selection_is_heuristic':True,'external_hf_authorized':False,'solver_calls':0,'sealed_target_reads':0,'external_target_reads':0,'reason':'Proposed Primary4 covers distinct error, P/S, coverage and performance+error roles; baseline comparisons are descriptive and no claim of guaranteed superiority is made.'})
 print(json.dumps({'status':decision,'candidate_count':len(candidates),'primary4':primary,'backups':backups,'first6':primary+backups[:2],'first8':primary+backups[:4],'solver_calls':0,'prereg_sha256':pre_sha},indent=2))
if __name__=='__main__': main()
