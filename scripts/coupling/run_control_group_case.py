from __future__ import annotations
import argparse, hashlib, json, subprocess, sys, time
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]; SRC=ROOT/'src'
if str(SRC) not in sys.path: sys.path.insert(0,str(SRC))
from apcd_coupling.joint_case_schema import canonical_hash

def now(): return datetime.now(timezone.utc).isoformat()
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for block in iter(lambda:f.read(1024*1024),b''): h.update(block)
 return h.hexdigest()
def read(p): return json.loads(p.read_text(encoding='utf-8'))
def atomic(p,obj):
 p.parent.mkdir(parents=True,exist_ok=True); tmp=p.with_suffix(p.suffix+'.tmp'); tmp.write_text(json.dumps(obj,indent=2,ensure_ascii=False)+'\n',encoding='utf-8'); tmp.replace(p)
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--output-dir',type=Path,required=True); args=ap.parse_args(); out=args.output_dir.resolve(); case=read(out/'joint_case.json'); setup=read(out/'setup_manifest.json'); group=case['control_group']; case_id=case['case_id']; pre=Path(setup['pre_fsp_path']); pre=(ROOT/pre).resolve() if not pre.is_absolute() else pre; entry_sha=setup['pre_fsp_sha256']
 if not setup['setup_gate']['pass']: raise RuntimeError('setup gate not PASS')
 if sha(pre)!=entry_sha: raise RuntimeError('pre-FSP hash mismatch before solver entry')
 budget_path=ROOT/'registries/coupling/solver_budget_registry.json'; budget=read(budget_path); authorized=budget.get('authorized_control_cases',[])+budget.get('authorized_spacer_cases',[])+budget.get('authorized_broadband_cases',[])
 if group in ('NB_T0','NB_T79','NB_T237') and budget.get('status')=='BROADBAND_RECONCILIATION_POLICY_FROZEN_DIAGNOSTIC_ONLY': raise RuntimeError('broadband solver execution requires new authorization after diagnostic policy freeze')
 if case_id not in authorized: raise RuntimeError(f'case not authorized: {case_id}')
 if budget.get('entered_runs',0)>=budget.get('budgets',{}).get('FDTD',0): raise RuntimeError('FDTD budget exhausted')
 completed=set(budget.get('completed_case_ids',[]));
 if case_id in completed: raise RuntimeError('case already completed; replay forbidden')
 stage=read(ROOT/'contracts/coupling/stage_a_direct_fullwave_contract_v1.json'); physical_hash=canonical_hash({'case':case,'stage_contract':stage}); commit=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip(); attempt='attempt_001'; runtime_dir=out/'runtime'/attempt; runtime_dir.mkdir(parents=True,exist_ok=True); ledger_path=runtime_dir/'entered_ledger.json'; post=(runtime_dir/f'{case_id}_{attempt}_post.fsp').resolve(); log=runtime_dir/'solver_controller.log'
 entered={'schema_version':'solver_entered_ledger_v1','case_id':case_id,'control_group':group,'attempt_id':attempt,'solver_entered':True,'entered_timestamp':now(),'pre_fsp_path':str(pre),'pre_fsp_entry_sha256':entry_sha,'physical_contract_hash':physical_hash,'joint_geometry_hash':case['joint_geometry_hash'],'source_commits':setup['source_commits'],'coupling_commit':commit,'automatic_replay_forbidden':True}; atomic(ledger_path,entered); log.write_text(f"{entered['entered_timestamp']} solver_entered=true control_group={group} case_id={case_id} pre_fsp_entry_sha256={entry_sha}\n",encoding='utf-8')
 budget['entered_runs']=int(budget.get('entered_runs',0))+1; budget['entered_case_ids']=budget.get('entered_case_ids',[])+[case_id]; budget['entered_attempts']=budget.get('entered_attempts',[])+[{'case_id':case_id,'attempt_id':attempt,'entered_timestamp':entered['entered_timestamp'],'pre_fsp_entry_sha256':entry_sha}]; budget['status']='STAGE_A_CONTROL_GROUPS_RUNNING'; atomic(budget_path,budget)
 setup['solver_entered']=True; setup['solver_entered_timestamp']=entered['entered_timestamp']; setup['entered_ledger_path']=str(ledger_path); atomic(out/'setup_manifest.json',setup)
 try:
  import lumapi
  fdtd=lumapi.FDTD(str(pre),hide=True)
  try:
   log.write_text(log.read_text(encoding='utf-8')+f"{now()} lifecycle=load_complete run_start=true\n",encoding='utf-8'); start=time.time(); fdtd.run(); elapsed=time.time()-start; fdtd.save(str(post)); log.write_text(log.read_text(encoding='utf-8')+f"{now()} lifecycle=run_complete post_save=true elapsed_s={elapsed:.3f}\n",encoding='utf-8')
  finally: fdtd.close()
  post_sha=sha(post); current_sha=sha(pre); mutation={'detected':current_sha!=entry_sha,'entry_sha256':entry_sha,'current_path_sha256':current_sha,'evidence':'Lumerical setup-side mutation observed after solver lifecycle; entry-time identity remains immutable in entered_ledger.json.','replay_policy':'No replay; each control case has one entered attempt.'}; runtime={'schema_version':'control_group_run_state_v1','case_id':case_id,'control_group':group,'attempt_id':attempt,'pre_fsp_path':str(pre),'pre_fsp_entry_sha256':entry_sha,'pre_fsp_current_sha256':current_sha,'pre_fsp_post_entry_mutation':mutation,'post_fsp_path':str(post),'post_fsp_sha256':post_sha,'solver_entered':True,'solver_completed':True,'physical_contract_hash':physical_hash,'source_commits':setup['source_commits'],'coupling_commit':commit,'completed_timestamp':now()}; atomic(runtime_dir/'run_state.json',runtime); setup.update({'solver_completed':True,'post_fsp_path':str(post),'post_fsp_sha256':post_sha,'pre_fsp_current_sha256':current_sha,'pre_fsp_post_entry_mutation':mutation}); atomic(out/'setup_manifest.json',setup); budget['engine_completed']=int(budget.get('engine_completed',0))+1; budget['controller_returned']=int(budget.get('controller_returned',0))+1; budget['post_saved']=int(budget.get('post_saved',0))+1; budget['completed_case_ids']=budget.get('completed_case_ids',[])+[case_id]; budget['completed_attempts']=budget.get('completed_attempts',[])+[{'case_id':case_id,'attempt_id':attempt,'post_fsp_sha256':post_sha,'completed_timestamp':runtime['completed_timestamp']}]; budget['status']='STAGE_A_CONTROL_GROUPS_RUNNING' if budget['entered_runs']<budget['budgets']['FDTD'] else 'STAGE_A_CONTROL_GROUPS_ALL_COMPLETED'; atomic(budget_path,budget); print(json.dumps(runtime,indent=2))
 except Exception as exc:
  failure={'case_id':case_id,'control_group':group,'attempt_id':attempt,'solver_entered':True,'failure_type':type(exc).__name__,'failure_text':str(exc),'automatic_replay_forbidden':True}; atomic(runtime_dir/'run_failure.json',failure); budget['status']='STAGE_A_CONTROL_GROUPS_ENTERED_FAILURE_REPLAY_FORBIDDEN'; atomic(budget_path,budget); raise
if __name__=='__main__': main()
