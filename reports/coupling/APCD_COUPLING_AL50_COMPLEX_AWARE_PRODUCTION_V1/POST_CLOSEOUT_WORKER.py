from pathlib import Path
import json,time,sys,subprocess,traceback,datetime
D=Path('D:\\project\\worktrees\\blue_apcd_mdc_np_coupling_ml_v1\\reports\\coupling\\APCD_COUPLING_AL50_COMPLEX_AWARE_PRODUCTION_V1')
sys.stdout=open(D/'POST_CLOSEOUT_STDOUT.log','a',encoding='utf-8',buffering=1);sys.stderr=open(D/'POST_CLOSEOUT_STDERR.log','a',encoding='utf-8',buffering=1)
rd=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
try:
 while not ((D/'STAGE_50/STAGE_EVALUATION_COMPLETE.json').exists() and (D/'STAGE_44/STAGE_EVALUATION_COMPLETE.json').exists()):
  if (D/'PRODUCTION_HOLD.json').exists():raise RuntimeError('Production HOLD, no replay; inspect existing error')
  time.sleep(15)
 assert rd(D/'AL50_SCIENCE_LEDGER.json')['labels_valid']==50
 for name in ['CLOSEOUT.py','SCIENTIFIC_VERDICT.py','FIGURES.py']:
  rc=subprocess.run([sys.executable,str(D/name)],cwd=str(D));assert rc.returncode==0,(name,rc.returncode)
 (D/'POST_CLOSEOUT_COMPLETE.json').write_text(json.dumps({'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'production_and_models':'COMPLETE','visual_QA':'PENDING_ACTUAL_AGENT_REVIEW','solver_calls':0},indent=2))
except Exception:
 traceback.print_exc();(D/'POST_CLOSEOUT_HOLD.json').write_text(json.dumps({'error':traceback.format_exc(),'solver_calls':0},indent=2));raise
