from pathlib import Path
import json,hashlib,sqlite3,re,datetime,numpy as np,h5py
R=Path(r'D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1');D=R/'reports/coupling/APCD_COUPLING_ML_V3_DOE56_FULL_SCIENCE_PRODUCTION_V1';O=R/'reports/coupling/APCD_COUPLING_V3_NUMERICAL_GATE_FAILURE_FORENSIC_V1'
def j(p):return json.loads(Path(p).read_text())
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for a in iter(lambda:f.read(8*1024*1024),b''):h.update(a)
 return h.hexdigest()
def ah(a):
 a=np.ascontiguousarray(a);return hashlib.sha256(str(a.dtype).encode()+str(a.shape).encode()+a.tobytes()).hexdigest()
def dump(n,x):(O/n).write_text(json.dumps(x,indent=2)+'\n')
L=j(D/'v3_execution_authority_v1/V3_EXECUTION_LEDGER_V1.json');B=j(D/'science_admission_v1/BASELINE_REFERENCE_PINS.json')['baselines'];native=j(O/'NATIVE_PAYLOAD_SHA.json');ev=j(O/'SOLVER_INDEPENDENCE_EVIDENCE.json');repeat=j(O/'FIVE_NM_REPEATABILITY.json');pins=j(O/'SOURCE_SHA_INVENTORY.json')
c=sqlite3.connect('file:D:/apcd_runtime/gpu_platform_v2_serial_production_v1/ledger.sqlite3?mode=ro',uri=True)
for x in ev:
 cid=x['case_id'];rec=L['case_records'][cid];processes=[]
 for tm,payload in c.execute('select utc_unix,payload from events where request_sha=? and kind="ENGINE_PROCESS"',(rec['request_sha256'],)):
  p=json.loads(payload);item={k:p[k] for k in ['pid','ppid','creation_time','executable','working_directory','user'] if k in p};item['first_observed_utc']=datetime.datetime.fromtimestamp(tm,datetime.timezone.utc).isoformat()
  if not any(s.get('pid')==item.get('pid') and s.get('creation_time')==item.get('creation_time') for s in processes):processes.append(item)
 x['engine_processes']=processes;x['process_return_event_count']=sum(e['kind']=='PROCESS_RETURNED' for e in x['events']);x.pop('events')
 b=Path(rec['evidence']['bundle']['path']);log=b.parent.parent/'attempts'/rec['request_sha256']/'run_p0.log';txt=log.read_text(errors='replace');match=re.search(r'Simulation size in gridpoints:\s*(\d+) x (\d+) x (\d+)',txt);x['volume_grid_shape']=[int(v) for v in match.groups()]
 x['safe_log_lines']=[s for s in txt.splitlines() if not any(t in s.lower() for t in ['license','command','context','-shared']) and any(t in s.lower() for t in ['time step','datatype','simulation size','total number','time to run','simulation completed','multiprocessors','autoshutoff'])]
 x['source_to_solved_FSP_distinct']=x['source_setup_sha']!=x['solved_fsp_sha'];pins.append({'kind':cid+':engine_log','path':str(log),'sha256':sha(log),'bytes':log.stat().st_size})
for i,b in enumerate(B):
 old=Path(b['artifacts']['source_manifest']['path']).parent;path=old/'run/run_output.h5';cid=repeat[i]['diagnostic'];payload={}
 with h5py.File(path) as f:
  for gn in f:payload[gn]={k:ah(f[gn][k][()]) for k in f[gn]}
 repeat[i]['native_H5_dataset_payloads_bitwise_equal_to_historical']=payload==native[cid];repeat[i]['historical_native_h5_sha256']=sha(path);repeat[i]['new_native_h5_sha256']=next(p['sha256'] for p in pins if p['kind']==cid+':native_h5');pins.append({'kind':b['case_id']+':native_h5','path':str(path),'sha256':sha(path),'bytes':path.stat().st_size})
 status=j(b['artifacts']['runner_status']['path']);repeat[i]['historical_execution']={k:status[k] for k in ['case_id','attempt_id','run_id','solver_entered','solver_invocations','solver_entered_unix','solver_returned_unix','state']};repeat[i]['distinct_solver_wall_clock']=status['solver_returned_unix']<next(x['execution']['started_unix'] for x in ev if x['case_id']==cid)
dump('FIVE_NM_REPEATABILITY.json',repeat);dump('SOLVER_INDEPENDENCE_EVIDENCE.json',ev);dump('SOURCE_SHA_INVENTORY.json',pins)
print('REPEAT',[(r['diagnostic'],r['native_H5_dataset_payloads_bitwise_equal_to_historical'],r['distinct_solver_wall_clock']) for r in repeat]);print('ENGINES',[(x['case_id'],x['engine_processes'],x['safe_log_lines']) for x in ev])
