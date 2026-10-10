import json,hashlib,subprocess,sqlite3,psutil,datetime
from pathlib import Path
rt=Path(r'D:\apcd_runtime\gpu_v2_unknown_closure_20261010_v1');v=Path(r'D:\project\worktrees\blue_apcd_gpu_platform_v2_cleanroom_v1');c=Path(r'D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1');oldrt=Path(r'D:\apcd_runtime\gpu_platform_v2_native_acceptance_20261009_v1')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
old=json.loads((rt/'source_recovery.json').read_text(encoding='utf-8'));print('MATCH_PATHS',sorted(set(q['path'] for q in old['matches'])))
src=Path(r'C:\Users\dell\AppData\Local\Temp\mdc_complex_prior_fsp_inventory.py');p=psutil.Process(30336);inventory={'pid':p.pid,'create_time':p.create_time(),'commandline':p.cmdline(),'source_exists':src.is_file(),'source_sha256':sha(src) if src.is_file() else None,'source_text':src.read_text(encoding='utf-8') if src.is_file() else None}
report=c/'reports/coupling/COUPLING_K6_V2_REMAINING127_STARTUP_REVALIDATION_V1';ledger=json.loads((report/'QUEUE_EXECUTION_LEDGER_V1.json').read_text(encoding='utf-8'))
g027=[]
def walk(obj,path=''):
 if isinstance(obj,dict):
  if any(x=='K6GDP2_DEV_G027' for x in obj.values() if isinstance(x,str)):g027.append({'json_path':path,'record':obj})
  for k,z in obj.items():walk(z,path+'/'+k)
 elif isinstance(obj,list):
  for k,z in enumerate(obj):walk(z,path+'/'+str(k))
walk(ledger)
status=[];r=Path(r'D:\apcd_runtime\gpu_production_runner_v1')
for p in (r/'runs/K6GDP2_DEV_G027').glob('*/*/status.json'):
 status.append({'path':str(p),'sha256':sha(p),'record':json.loads(p.read_text(encoding='utf-8'))})
for p in (r/'requests/scheduled_run_one_v1').glob('*/result.json'):
 text=p.read_text(encoding='utf-8')
 if 'K6GDP2_DEV_G027' in text:status.append({'path':str(p),'sha256':sha(p),'record':json.loads(text)})
# Existing offline ledgers only, read-only connections, no entry writes.
dbs=[]
for runtime in [Path(r'D:\apcd_runtime\gpu_platform_v2_offline_20261009_v1'),oldrt]:
 for p in list(runtime.rglob('*.sqlite3'))+list(runtime.rglob('*.db')):
  db=sqlite3.connect(p.as_uri()+'?mode=ro',uri=True)
  try:
   tables=[x[0] for x in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")];data={t:[list(x) for x in db.execute('SELECT * FROM "'+t.replace('"','""')+'" LIMIT 40')] for t in tables};integrity=db.execute('PRAGMA integrity_check').fetchall();dbs.append({'path':str(p),'schema':tables,'integrity':integrity,'rows':data,'read_only':True})
  finally:db.close()
reuse={}
for name in ['g025_native_load.json','g025_actual_importer.json','g027_exact_systemcheck.json','license_scope.json','ssh_detached_fixture.json','real_native_exception_close.json']:
 p=v/'platform_v2/reports/native_acceptance_v1'/name;reuse[name]={'path':str(p),'sha256':sha(p),'original_commit':'05fa4f6d51535386635fee0a6b0cedcf496faa49'}
proof={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'inventory_30336':inventory,'g027_ledger_records':g027,'g027_runtime_status':status,'offline_ledger_readonly':dbs,'reused_receipts':reuse,'no_native_api_calls':True,'no_solver_calls':True}
(rt/'qualification_details.json').write_text(json.dumps(proof,indent=2,default=str),encoding='utf-8')
print('INVENTORY_SOURCE',inventory['source_exists'],inventory['source_sha256'],inventory['create_time']);print('G027_LEDGER',g027);print('G027_STATUS',[(q['path'],q['record'].get('status'),q['record'].get('solver_entered'),q['record'].get('reason'),q['record'].get('exit_code')) for q in status]);print('DBS',[(q['path'],q['schema'],q['rows'].get('worker_slot'),q['integrity']) for q in dbs]);print('REUSE',reuse)
