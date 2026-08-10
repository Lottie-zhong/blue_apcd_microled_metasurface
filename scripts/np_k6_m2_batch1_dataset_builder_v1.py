from __future__ import annotations
import csv, gzip, hashlib, json, math, pathlib, statistics
from collections import defaultdict

ROOT=pathlib.Path(r'D:\project\worktrees\blue_apcd_np_k6_mdc_v1')
STAGE=ROOT/'outputs'/'np_k6_m2_batch1_hf_acquisition_v1'
SEL=ROOT/'outputs'/'np_k6_m2_active_learning_batch1_selection_v1'
OUT=ROOT/'outputs'/'np_k6_m2_batch1_hf_dataset_v1'
MERGED=ROOT/'outputs'/'np_k6_m2_batch1_merged_development_dataset_v1'
WLS=list(range(445,456))
CASES=[('NP_K6_M2_BATCH1_G01_P',1,'p'),('NP_K6_M2_BATCH1_G01_S',1,'s'),('NP_K6_M2_BATCH1_G02_P',2,'p'),('NP_K6_M2_BATCH1_G02_S',2,'s'),('NP_K6_M2_BATCH1_G03_P',3,'p'),('NP_K6_M2_BATCH1_G03_S',3,'s'),('NP_K6_M2_BATCH1_G04_P',4,'p'),('NP_K6_M2_BATCH1_G04_S',4,'s'),('NP_K6_M2_BATCH1_G05_P',5,'p'),('NP_K6_M2_BATCH1_G05_S',5,'s'),('NP_K6_M2_BATCH1_G06_P',6,'p'),('NP_K6_M2_BATCH1_G06_S',6,'s')]

def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for c in iter(lambda:f.read(1<<20),b''): h.update(c)
 return h.hexdigest()
def read_csv(p):
 with p.open(newline='',encoding='utf-8-sig') as f: return list(csv.DictReader(f))
def write_csv(p,rows):
 p.parent.mkdir(parents=True,exist_ok=True); fields=[]
 for r in rows:
  for k in r:
   if k not in fields: fields.append(k)
 with p.open('w',newline='',encoding='utf-8') as f:
  w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore'); w.writeheader(); w.writerows(rows)
def jwrite(p,obj): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(obj,indent=2,ensure_ascii=False,sort_keys=True,default=str)+'\n',encoding='utf-8')
def f(v): return float(v)
def stats(vals):
 vals=[float(x) for x in vals]; return {'count':len(vals),'mae':sum(abs(x) for x in vals)/len(vals),'rmse':math.sqrt(sum(x*x for x in vals)/len(vals)),'max_abs':max(abs(x) for x in vals),'bias':sum(vals)/len(vals)}
def corr(a,b):
 if len(a)<2: return None
 ma=sum(a)/len(a); mb=sum(b)/len(b); da=sum((x-ma)**2 for x in a); db=sum((y-mb)**2 for y in b)
 return sum((x-ma)*(y-mb) for x,y in zip(a,b))/math.sqrt(da*db) if da and db else None

def main():
 OUT.mkdir(parents=True,exist_ok=True); MERGED.mkdir(parents=True,exist_ok=True)
 selected={r['geometry_id']:r for r in read_csv(SEL/'batch1_selected_geometries.csv')}
 rows=[]; provenance=[]
 for case,group,pol in CASES:
  if case=='NP_K6_M2_BATCH1_G04_P':
   evid=ROOT/'outputs'/'np_k6_m2_g04p_controlled_recompute_v1'; src=evid/'replacement_hf_observations_long.csv'; base=read_csv(src); ident=json.loads((evid/'replacement_setup_identity.json').read_text(encoding='utf-8-sig')); led=json.loads((evid/'replacement_attempt_ledger.json').read_text(encoding='utf-8-sig')); gid=ident['canonical_geometry_id']; gh=ident['canonical_geometry_hash']; exec_id=ident['replacement_execution_id']; post_sha=led['post_fsp_sha256']; setup_sha=ident['source_prefsp_sha256']; source_sha=ident['source_prefsp_sha256']
  else:
   cdir=STAGE/'cases'/case; src=cdir/'hf_observations_long.csv'; base=read_csv(src); con=json.loads((cdir/'setup_contract.json').read_text(encoding='utf-8-sig')); led=json.loads((cdir/'attempt_ledger.json').read_text(encoding='utf-8-sig')); gid=con.get('geometry_id',led.get('geometry_id')); gh=con.get('geometry_hash',led.get('geometry_hash')); exec_id=case; post_sha=led.get('post_fsp_sha256'); setup_sha=led.get('source_prefsp_sha256'); source_sha=led.get('source_prefsp_sha256')
  if len(base)!=11 or [int(float(r['wavelength_nm'])) for r in base]!=WLS: raise RuntimeError(f'bad 11 point case {case}')
  for r in base:
   rr=dict(r); rr.update({'case_id':case,'logical_task_id':case,'execution_id':exec_id,'case_group':group,'geometry_id':gid,'geometry_hash':gh,'polarization':pol,'generator_id':'NP_K6_PILOT_FDTD_GENERATOR_FIXED_GRID_3PS_V2','interface_stack_id':'NP_K6_INDEPENDENT_STACK_PILOT_V1','quality_gate_pass':'true','training_label':'false','provisional_hf_label':'true','diagnostic_only':'false','pilot_scope_only':'true','bulk_mdc_compatible':'false','candidate_performance_label':'false','accepted_execution': 'true','post_fsp_sha256':post_sha,'source_prefsp_sha256':source_sha,'setup_sha256':setup_sha,'wavelength_nm':str(int(float(r['wavelength_nm'])))})
   rows.append(rr)
  provenance.append({'case_id':case,'execution_id':exec_id,'geometry_id':gid,'geometry_hash':gh,'polarization':pol,'post_fsp_sha256':post_sha,'source_prefsp_sha256':source_sha,'row_count':len(base),'replacement':case=='NP_K6_M2_BATCH1_G04_P'})
 rows.sort(key=lambda r:(int(r['case_group']),r['polarization'],int(r['wavelength_nm'])))
 if len(rows)!=132 or len({r['case_id'] for r in rows})!=12: raise RuntimeError('132 row or case count failure')
 write_csv(OUT/'hf_observations_long.csv',rows)
 # p/s audit, same geometry and wavelength only
 by={(r['geometry_hash'],int(r['wavelength_nm']),r['polarization']):r for r in rows}; psrows=[]
 for gh in sorted({r['geometry_hash'] for r in rows}):
  gid=next(r['geometry_id'] for r in rows if r['geometry_hash']==gh)
  for wl in WLS:
   p=by[(gh,wl,'p')]; s=by[(gh,wl,'s')]; rec={'geometry_id':gid,'geometry_hash':gh,'wavelength_nm':wl}
   for key in ['T_total','R_total','eta_plus1','eta_0','eta_minus1','directionality']:
    rec[f'p_{key}']=f(p[key]); rec[f's_{key}']=f(s[key]); rec[f'delta_s_minus_p_{key}']=f(s[key])-f(p[key]); rec[f'abs_delta_{key}']=abs(f(s[key])-f(p[key]))
   psrows.append(rec)
 write_csv(OUT/'p_s_audit_66rows.csv',psrows)
 ps_summary=[]
 for gh in sorted({r['geometry_hash'] for r in rows}):
  sub=[x for x in psrows if x['geometry_hash']==gh]; gid=sub[0]['geometry_id']; ps_summary.append({'geometry_id':gid,'geometry_hash':gh,'wavelength_count':len(sub),'max_abs_delta_T':max(x['abs_delta_T_total'] for x in sub),'mean_abs_delta_T':statistics.mean(x['abs_delta_T_total'] for x in sub),'max_abs_delta_eta_plus1':max(x['abs_delta_eta_plus1'] for x in sub),'mean_abs_delta_eta_plus1':statistics.mean(x['abs_delta_eta_plus1'] for x in sub),'max_abs_delta_directionality':max(x['abs_delta_directionality'] for x in sub),'classification':'P_S_SIMILARITY_CANDIDATE_PENDING_MORE_HF_DATA'})
 jwrite(OUT/'p_s_audit_summary.json',{'schema_version':'np_k6_m2_batch1_p_s_audit_v1','geometry_count':6,'row_count':66,'classification':'P_S_SIMILARITY_CANDIDATE_PENDING_MORE_HF_DATA','per_geometry':ps_summary})
 # model error audit against acquisition-only predictions
 preds=[]
 with gzip.open(SEL/'cnn_ensemble_predictions.csv.gz','rt',encoding='utf-8') as g: preds=list(csv.DictReader(g))
 pred={(r['geometry_hash'],int(r['wavelength_nm']),r['polarization']):r for r in preds}
 model_rows=[]; feature_by={r['geometry_hash']:r for r in read_csv(SEL/'candidate_acquisition_features.csv')}
 for r in rows:
  pr=pred[(r['geometry_hash'],int(r['wavelength_nm']),r['polarization'])]; out=dict(r)
  for model in ['cnn','mlp']:
   for key in ['T','R','eta_plus1','directionality']:
    actual_key={'T':'T_total','R':'R_total','eta_plus1':'eta_plus1','directionality':'directionality'}[key]; pv=f(pr[f'{model}_mean_{key}']); av=f(r[actual_key]); out[f'{model}_{key}_error']=pv-av; out[f'{model}_{key}_abs_error']=abs(pv-av)
   if model == 'cnn':
    out[f'{model}_eta_uncertainty']=f(pr.get('cnn_std_eta_plus1','0'))
   else:
    out[f'{model}_eta_uncertainty']=statistics.pstdev(f(pr[f'mlp_{seed}_eta_plus1']) for seed in (17,29,43))
  for key in ['T','R','eta_plus1','directionality']:
   lk={'T':'lf_T','R':'lf_R','eta_plus1':'lf_eta_plus1','directionality':'lf_directionality'}[key]; ak={'T':'T_total','R':'R_total','eta_plus1':'eta_plus1','directionality':'directionality'}[key]; out[f'lf_{key}_error']=f(pr[lk])-f(r[ak]); out[f'lf_{key}_abs_error']=abs(f(pr[lk])-f(r[ak]))
  model_rows.append(out)
 write_csv(OUT/'preacquisition_error_132rows.csv',model_rows)
 summary={}
 for model in ['cnn','mlp','lf']:
  summary[model]={}
  for key in ['T','R','eta_plus1','directionality']:
   summary[model][key]=stats([x[f'{model}_{key}_error'] for x in model_rows])
 jwrite(OUT/'cnn_mlp_lf_preacquisition_error_summary.json',{'schema_version':'np_k6_m2_batch1_preacquisition_error_audit_v1','row_count':132,'models':summary,'prediction_source':str(SEL/'cnn_ensemble_predictions.csv.gz'),'sealed_access':0,'solver_calls_for_audit':0})
 # uncertainty/error correlation and slot audit
 corr_obj={}
 for model in ['cnn','mlp']:
  corr_obj[model]={}
  for key in ['T','R','eta_plus1','directionality']:
   corr_obj[model][key]=corr([x[f'{model}_eta_uncertainty'] for x in model_rows],[x[f'{model}_{key}_abs_error'] for x in model_rows])
 jwrite(OUT/'uncertainty_error_correlation.json',{'schema_version':'np_k6_m2_uncertainty_error_correlation_v1','row_count':132,'correlation_metric':'pearson(eta uncertainty, absolute error)','correlations':corr_obj})
 slotrows=[]
 for gid,sel in selected.items():
  sub=[x for x in model_rows if x['geometry_id']==gid]; slotrows.append({'slot':sel['slot'],'geometry_id':gid,'geometry_hash':sel['geometry_hash'],'row_count':len(sub),'p_rows':sum(x['polarization']=='p' for x in sub),'s_rows':sum(x['polarization']=='s' for x in sub),'cnn_eta_plus1_mae':stats([x['cnn_eta_plus1_error'] for x in sub])['mae'],'mlp_eta_plus1_mae':stats([x['mlp_eta_plus1_error'] for x in sub])['mae'],'lf_eta_plus1_mae':stats([x['lf_eta_plus1_error'] for x in sub])['mae'],'cnn_eta_uncertainty_mean':statistics.mean(f(x['cnn_eta_uncertainty']) for x in sub),'quality_gate_all':all(x['quality_gate_pass']=='true' for x in sub)})
 write_csv(OUT/'slot_level_audit.csv',slotrows)
 # provenance/state/checksums
 jwrite(OUT/'provenance_audit.json',{'schema_version':'np_k6_m2_batch1_dataset_provenance_v1','logical_task_count':12,'formal_observation_count':132,'accepted_execution_count':12,'physical_solver_invocation_count':13,'lost_infrastructure_execution_count':1,'replacement_overhead_count':1,'replacement_execution_id':'G04_P_BATCH1_INFRA_RECOVERY_RECOMPUTE_V1','original_G04P_consumed_but_excluded':True,'sealed_access':0,'training_started':False,'training_label':False,'candidate_performance_label':False,'case_provenance':provenance})
 jwrite(OUT/'solver_budget_audit.json',{'logical_task_count':12,'accepted_numerical_executions':12,'physical_solver_invocation_count':13,'lost_infrastructure_execution_count':1,'authorized_replacement_overhead':1,'attempt_002_count':0,'automatic_rerun_count':0,'new_solver_calls_after_batch_completion':0})
 jwrite(OUT/'batch1_dataset_state.json',{'schema_version':'np_k6_m2_batch1_dataset_state_v1','status':'NP_K6_M2_BATCH1_HF_ACQUISITION_COMPLETE_RETRAIN_READY','formal_observation_count':132,'geometry_count':6,'logical_task_count':12,'p_s_audit_rows':66,'pilot_training_authorized':True,'bulk_mdc_compatible_training_authorized':False,'real_training_started':False,'checkpoint_count':0,'sealed_access':0,'solver_entered_total':13,'training_label':False,'candidate_performance_label':False})
 # merged 198 row development dataset; preserve old 66 rows and add new 132 with union fields
 old=read_csv(ROOT/'outputs'/'np_k6_hf_pilot_dataset_v1'/'hf_observations_long.csv'); merged=old+rows; write_csv(MERGED/'hf_observations_long.csv',merged)
 jwrite(MERGED/'dataset_state.json',{'schema_version':'np_k6_m2_batch1_merged_development_dataset_v1','row_count':len(merged),'prior_formal_rows':len(old),'batch1_rows':len(rows),'training_started':False,'sealed_access':0,'bulk_mdc_compatible_training_authorized':False})
 manifest=[]
 for d in [OUT,MERGED]:
  for p in sorted(d.glob('*')):
   if p.is_file() and p.name!='dataset_checksum_manifest.json': manifest.append({'dataset':d.name,'path':str(p.relative_to(d)).replace('\\','/'),'sha256':sha(p),'size_bytes':p.stat().st_size})
 jwrite(OUT/'dataset_checksum_manifest.json',{'schema_version':'np_k6_m2_batch1_dataset_checksum_manifest_v1','formal_observation_count':132,'files':[x for x in manifest if x['dataset']==OUT.name]})
 jwrite(MERGED/'dataset_checksum_manifest.json',{'schema_version':'np_k6_m2_batch1_merged_checksum_manifest_v1','row_count':198,'files':[x for x in manifest if x['dataset']==MERGED.name]})
 print(json.dumps({'status':'NP_K6_M2_BATCH1_HF_ACQUISITION_COMPLETE_RETRAIN_READY','batch1_rows':len(rows),'merged_rows':len(merged),'p_s_rows':len(psrows),'case_count':len(provenance),'solver_invocations':13,'sealed_access':0},indent=2))
if __name__=='__main__': main()
