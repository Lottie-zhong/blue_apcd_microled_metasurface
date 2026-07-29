from __future__ import annotations
import hashlib,json,os,platform,shutil,sys,traceback
from datetime import datetime,timezone
from pathlib import Path
R=Path(__file__).resolve().parents[1]; CASE='K6_BLANK_FIXED_REFERENCE_X'; SRC=R/'outputs/np_k6_p1d4b_k6x_fullwave_v1/runtime_prefsp/K6_BLANK_FIXED_REFERENCE_X.fsp'; D=R/'outputs/np_k6_p1d4b_k6x_fullwave_v1/runtime_runs'/CASE/'attempt_001'; RUN=D/(CASE+'_attempt_001.fsp'); POST=D/(CASE+'_attempt_001_post.fsp'); E=R/'outputs/np_k6_p1d4b_k6x_blank_run1_freeze_v1'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def now():return datetime.now(timezone.utc).isoformat()
def atomic(p,x):
 t=p.with_suffix(p.suffix+'.tmp');t.write_text(json.dumps(x,indent=2),encoding='utf-8');os.replace(t,p)
def main():
 import lumapi
 if D.exists():raise RuntimeError('attempt directory already exists; no rerun permitted')
 D.mkdir(parents=True);E.mkdir(parents=True)
 frozen='fb12c80d30e53357702e1b0f01470272cd7911c257c6a77bde2d680546c6918c'
 if sha(SRC)!=frozen:raise RuntimeError('source pre-FSP SHA mismatch')
 shutil.copyfile(SRC,RUN)
 if sha(RUN)!=frozen:raise RuntimeError('run copy SHA mismatch')
 man=json.loads((R/'outputs/np_k6_p1d4b_k6x_prefsp_freeze_v1/stage_manifest.json').read_text())
 ledger={'case_id':CASE,'case_type':'blank_calibration','candidate_physics_claim':False,'attempt_id':'attempt_001','source_prefsp_path':str(SRC),'source_prefsp_sha256':frozen,'run_copy_path':str(RUN),'run_copy_sha256':sha(RUN),'physical_contract_hash':man['contract_hash'],'material_contract_hash':'MAT2_NATIVE_M1_228b32d','entered':False,'engine_completed':False,'controller_returned':False,'post_saved':False,'created_timestamp':now(),'host':platform.node(),'python_path':sys.executable,'lumerical_version':'v251'}
 atomic(D/'entered_ledger.json',ledger); atomic(E/'entered_ledger.json',ledger)
 fdtd=None
 try:
  fdtd=lumapi.FDTD(str(RUN),hide=True); ledger['controller_started_timestamp']=now();ledger['prefsp_opened']=True;atomic(D/'entered_ledger.json',ledger);atomic(E/'entered_ledger.json',ledger)
  ledger['entered']=True;ledger['solver_entered_timestamp']=now();atomic(D/'entered_ledger.json',ledger);atomic(E/'entered_ledger.json',ledger)
  fdtd.run()
  ledger['engine_completed']=True;ledger['engine_returned_timestamp']=now();atomic(D/'entered_ledger.json',ledger);atomic(E/'entered_ledger.json',ledger)
  fdtd.save(str(POST));ledger['post_saved']=POST.exists();ledger['post_fsp_path']=str(POST);ledger['post_fsp_sha256']=sha(POST) if POST.exists() else None;ledger['post_saved_timestamp']=now();atomic(D/'entered_ledger.json',ledger);atomic(E/'entered_ledger.json',ledger)
 finally:
  if fdtd is not None:
   try:fdtd.close()
   except:pass
 ledger['controller_returned']=True;ledger['controller_returned_timestamp']=now();atomic(D/'entered_ledger.json',ledger);atomic(E/'entered_ledger.json',ledger)
 atomic(E/'controller_status.json',{'controller_started':True,'pre_fsp_opened':ledger.get('prefsp_opened',False),'solver_entered':ledger['entered'],'engine_completed':ledger['engine_completed'],'post_saved':ledger['post_saved'],'controller_returned':True})
 atomic(E/'post_fsp_checksum.json',{'path':ledger.get('post_fsp_path'),'sha256':ledger.get('post_fsp_sha256'),'case_type':'blank_calibration','candidate_physics_claim':False})
if __name__=='__main__':main()
