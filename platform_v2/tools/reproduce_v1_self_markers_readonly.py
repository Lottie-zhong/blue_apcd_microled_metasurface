import sys,os,json,hashlib
from pathlib import Path
from unittest.mock import patch
r=Path(r'D:\project\worktrees\blue_apcd_gpu_production_runner_v1');rt=Path(r'D:\apcd_runtime\gpu_production_runner_v1');sys.path.insert(0,str(r/'scripts/shared_fdtd/gpu_runner_v1'))
import adapter
out=rt/'diagnostics/GPU_RUNNER_AGENT_TAKEOVER_20261009_V1'
real_exists=Path.exists;real_read=adapter.read_json
def scenario(markers):
 def exists(p):
  if str(p) in markers:return True
  return real_exists(p)
 def read(p,default=None):
  if str(p) in markers:return {'pid':os.getpid(),'run_id':'AUDIT_SELF_ONLY'}
  return real_read(p,default)
 checks=[]
 with patch.object(Path,'exists',exists),patch.object(adapter,'read_json',read):
  for p in (rt/'runs').glob('*/*/*/status.json'):
   s=json.loads(p.read_text())
   if s.get('state')=='FAILED_POSTENTRY' and s.get('solver_process_lineage') is None:
    checks.append({'run_id':s['run_id'],'closeout_valid':adapter.validate_postentry_failure_closeout(rt,p,s)})
  return {'owner_probe':adapter.NativeAdapter.runner_owner_probe(rt),'closeouts':checks}
report={'schema':'V1_READ_ONLY_SELF_MARKER_REPRO_V1','baseline':scenario(set()),'self_runner_lock':scenario({str(rt/'.runner.lock')}),'self_worker_lock':scenario({str(rt/'scheduler_worker_v1.lock')}),'solver_invocations':0,'production_files_modified':False,'method':'Actual installed validator and actual historical receipts; only marker existence and self lock PID injected in memory.'}
(out/'self_marker_reproduction.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))
