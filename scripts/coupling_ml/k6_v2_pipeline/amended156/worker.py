"""Single CPU executor for the approved268 logical fits; fail closed budget ledger."""
import os,sys,json,datetime,time,traceback,hashlib
from pathlib import Path
from dataclasses import asdict
import numpy as np
from . import adapter as A,engine as E
from k6_v2_pipeline import h1
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def log(s):print(now(),s,flush=True)
def main():
 import torch
 torch.set_num_threads(2);torch.set_num_interop_threads(1)
 pre=A.read(A.OUT/'TRAINING_PREFLIGHT_REPORT.json')
 if pre['status']!='PASS' or pre['zero_fit_counts']['production']!=0:raise ValueError('zero_fit_preflight_not_admitted')
 freeze=A.read(A.OUT/'EXECUTION_SOURCE_FREEZE.json')
 for q in freeze['files']:
  if A.sha(q['path'])!=q['sha256']:raise ValueError('execution_source_changed:'+q['path'])
 col=A.load_collection(False);plan=A.build_plan();by={c.case_id:c for c in col.training_cases()};E._validate_development_case_map(by,plan)
 lp=A.OUT/'FIT_EXECUTION_LEDGER.json'
 ledger=A.read(lp) if lp.exists() else {'schema':'156G_268_CPU_FIT_EXECUTION_LEDGER_V1','budget':268,'fits':{},'solver_entries':0,'confirmation_response_access':0,'local_fits':0,'NP_fits':0,'standalone_P_scale_fits':0,'source_freeze_sha256':A.sha(A.OUT/'EXECUTION_SOURCE_FREEZE.json')}
 if ledger['source_freeze_sha256']!=A.sha(A.OUT/'EXECUTION_SOURCE_FREEZE.json'):raise ValueError('ledger_source_freeze_changed')
 if len(ledger['fits'])>268:raise ValueError('fit_budget_exceeded')
 artifact=A.OUT/'models'
 def execute(task,resolved=None):
  output=artifact/task.phase/task.task_id;existing=ledger['fits'].get(task.task_id)
  if existing and existing['task_sha256']!=task.fingerprint():raise ValueError('fit_identity_changed')
  if existing and existing['status']!='COMPLETE':
   if task.model_kind!='CARTESIAN_MLP' or not (output/'progress.pt').exists():raise ValueError('spent_fit_without_recoverable_progress:'+task.task_id)
  if not existing:
   if len(ledger['fits'])>=268:raise ValueError('fit_budget_ceiling')
   ledger['fits'][task.task_id]={'status':'STARTED','task_sha256':task.fingerprint(),'task':asdict(task),'started_utc':now(),'fresh_logical_fit_count':1,'source_freeze_sha256':ledger['source_freeze_sha256'],'156_inventory_sha256':A.INVENTORY_SHA};A.write(lp,ledger)
  start=time.monotonic();log('FIT_START '+task.task_id)
  try:
   run=E.run_fit_task(task,by,artifact/task.phase,device='cpu',resume=True,refit_authorization=resolved)
   meta=A.read(output/'fit_manifest.json')
   # Independent persisted model recovery; no extra fit and no oracle correction.
   saved=E._load_cached_fit(task,output,meta['data_sha256']);sample_ids=task.prediction_case_ids or task.train_case_ids[:3]
   xx=np.array([by[c].ordered_D_nm for c in sample_ids],float)
   a,b=E.predict_fit_run(run,xx);aa,bb=E.predict_fit_run(saved,xx)
   if not (np.array_equal(a,aa) and np.array_equal(b,bb)):raise ValueError('fitted_save_reload_prediction_mismatch')
   check={'status':'PASS','absolute_delta_C_hat':float(np.max(abs(a-aa))),'absolute_delta_P_scale':float(np.max(abs(b-bb))),'tolerance':'exact prediction equality','sample_case_ids':list(sample_ids),'CPU_only':True,'amendment_source_sha256':ledger['source_freeze_sha256'],'data_sha256':meta['data_sha256']}
   A.write(output/'AMENDMENT_PROVENANCE_AND_RELOAD.json',check)
   ledger['fits'][task.task_id].update(status='COMPLETE',completed_utc=now(),wall_seconds=time.monotonic()-start,fit_manifest_sha256=A.sha(output/'fit_manifest.json'),artifact_sha256=meta['artifact_sha256'],input_sha256=meta['data_sha256'],preprocessing_case_ids=list(task.train_case_ids),best_update=run.best_update,actual_updates=run.actual_updates,validation_loss=run.validation_loss,reload=check)
   A.write(lp,ledger);log('FIT_COMPLETE '+task.task_id+' '+str(sum(q['status']=='COMPLETE' for q in ledger['fits'].values()))+'/268')
   return run
  except Exception as exc:
   ledger['fits'][task.task_id].update(status='FAILED_PRESERVED_NO_NEW_FIT',error=repr(exc),failure_utc=now(),traceback=traceback.format_exc());A.write(lp,ledger);raise
 inner=[]
 for t in plan.inner_tasks:inner.append(execute(t))
 resolved=E.resolve_refit_tasks(plan,inner)
 A.write(A.OUT/'INNER_SELECTED_CONFIGURATIONS.json',{'outer_selections':{str(k):asdict(v) for k,v in resolved.outer_selections.items()},'final_krr_gamma':resolved.final_krr_gamma,'final_krr_alpha':resolved.final_krr_alpha,'final_mlp_weight_decay':resolved.final_mlp_weight_decay,'final_mlp_updates_by_seed':resolved.final_mlp_updates_by_seed,'selection_inputs':'inner train/validation only; no outer selection','final_and_curve_tasks':[asdict(t) for t in resolved.curve_tasks+resolved.final_tasks]})
 refits=[]
 for t in resolved.curve_tasks+resolved.final_tasks:refits.append(execute(t,resolved))
 if len(ledger['fits'])!=268 or any(q['status']!='COMPLETE' for q in ledger['fits'].values()):raise ValueError('268_fits_not_complete')
 A.write(A.OUT/'TRAINING_COMPLETION.json',{'status':'COMPLETE','completed_utc':now(),'counts':plan.counts.to_dict(),'fits_started':268,'fits_complete':268,'extra_fits':0,'solver':0,'confirmation_response_access':0,'local_fits':0,'NP_fits':0,'CPU_only':True,'ledger_sha256':A.sha(lp)})
 from .evaluation import main as evaluate
 evaluate(col,plan,refits)
 log('268_FITS_AND_DEVELOPMENT_EVALUATION_COMPLETE')
if __name__=='__main__':main()
