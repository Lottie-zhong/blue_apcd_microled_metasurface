"""Zero-science audit of unmodified formal APIs against fresh isolated SQLite fixtures."""
import sys,ast,json,hashlib,sqlite3,types,importlib,shutil,datetime,traceback,uuid
from pathlib import Path
sys.dont_write_bytecode=True
rt=Path(r'D:\apcd_runtime\gpu_v2_legacy_ingress_fence_20261010_v1')
v1=Path(r'D:\project\worktrees\blue_apcd_gpu_production_runner_v1\scripts\shared_fdtd')
roots={'v1':v1,'installed_reconciler':Path(r'D:\apcd_runtime\shared_v3_backend\01e2320ebf237bdbcd52573665520d57705d2800_gitblob\scripts\shared_fdtd'),'pinned_pw_launcher':Path(r'D:\apcd_runtime\shared_v3_backend\pw_powernorm_v1_aaaa25b53a9a3322\scripts\shared_fdtd'),'coupling':Path(r'D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1\scripts\shared_fdtd')}
stage=rt/'shadow_validation'/uuid.uuid4().hex[:8];stage.mkdir(parents=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
src=v1/'gpu_runner_v1/adapter.py';text=src.read_text(encoding='utf-8-sig');node=next(n for n in ast.parse(text).body if isinstance(n,ast.FunctionDef) and n.name=='read_global_entry_control');guard_source=ast.get_source_segment(text,node)
class RunnerError(RuntimeError):pass
g={'Path':Path,'sqlite3':sqlite3,'hashlib':hashlib,'json':json,'RunnerError':RunnerError,'_sha256':sha,'GLOBAL_ENTRY_CONTROL_SCHEMA':'APCD_GPU_RUNNER_GLOBAL_ENTRY_CONTROL_READONLY_V1','GLOBAL_ENTRY_CONTROL_DB_PATH':stage/'NEVER_USE_DEFAULT.sqlite3'}
exec(compile(guard_source,str(src),'exec'),g);guard=g['read_global_entry_control']
def stable_guard(path):
 # Establish a read-only anchor before the exact guard hashes WAL files. It avoids
 # an isolated first-reader WAL creation/deletion being mistaken for a concurrent writer.
 con=sqlite3.connect(path.as_uri()+'?mode=ro',uri=True)
 try:con.execute('SELECT COUNT(*) FROM sqlite_master').fetchone();return guard(path)
 finally:con.close()
rows=[];source_identity={};counter=0
for label,root in roots.items():
 shadow=stage/'source'/label/'control_v3'
 if not shadow.exists():shutil.copytree(root/'control_v3',shadow,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
 package='fence_shadow_'+label;m=types.ModuleType(package);m.__path__=[str(shadow)];sys.modules[package]=m
 dbmod=importlib.import_module(package+'.db');amod=importlib.import_module(package+'.allocator')
 source_identity[label]={'root':str(root),'db_sha256':sha(root/'control_v3/db.py'),'allocator_sha256':sha(root/'control_v3/allocator.py'),'schema_sha256':sha(root/'control_v3/schema.sql')}
 def fresh(name):
  global counter
  counter+=1;p=stage/('fixture_'+label+'_'+name+'_'+str(counter)+'.sqlite3');assert not p.exists();assert p.resolve().is_relative_to(stage.resolve())
  db=dbmod.ControlDB(p);db.initialize(shadow/'schema.sql');return db,amod.Allocator(db)
 def state(db,table):
  with db.connect(readonly=True) as con:return [dict(q) for q in con.execute('SELECT * FROM '+table)]
 def decision(db,a,branch,**kw):
  with db.immediate() as con:return a._admission_decision(con,branch,**kw)
 def test(name,fn):
  row={'implementation':label,'test':name}
  try:row.update(result='PASS',evidence=fn())
  except Exception:row.update(result='FAIL',error=traceback.format_exc())
  rows.append(row)
 def scoped_hold():
  db,a=fresh('scope');slots=state(db,'slots');limits=state(db,'branch_limits');gen=state(db,'admission_control')[0]['control_generation'];h=db.set_hold(scope='COUPLING_ML',reason_code='OFFLINE_SCOPE_AUDIT',created_by='zero-science-fixture')
  c=decision(db,a,'coupling_ml');t=decision(db,a,'traditional');assert 'NEW_ENTRY_HOLD' in c['reasons'] and 'NEW_ENTRY_HOLD' in t['reasons'];assert state(db,'slots')==slots and state(db,'branch_limits')==limits
  try:stable_guard(db.path)
  except RunnerError as e:blocked=str(e)
  else:raise AssertionError('V1 guard failed to reject global hold')
  released=db.release_hold(h['hold_id'],released_by='offline-fixture',release_authority_hash='fixture-only',evidence={'sandbox':True});assert state(db,'admission_control')[0]['control_generation']==gen+2;assert decision(db,a,'traditional')['eligible']
  assert not state(db,'lease_events');return {'coupling_reasons':c['reasons'],'traditional_reasons':t['reasons'],'v1_guard':blocked,'slots_and_limits_unchanged':True,'rollback_global_hold':released['global_hold'],'rollback_generation_monotonic':True,'scientific_entries':0}
 def branch_gap():
  db,a=fresh('branch');before=state(db,'branch_limits');tr=next(z for z in before if z['branch_id']=='traditional');cou=next(z for z in before if z['branch_id']=='coupling_ml');a.set_branch_limit('coupling_ml',cou['cap'],enabled=False,preferred=json.loads(cou['preferred_slot_order']));c=decision(db,a,'coupling_ml');t=decision(db,a,'traditional');native=stable_guard(db.path)
  assert 'BRANCH_DISABLED' in c['reasons'] and t['eligible'] and native['result']=='PASS';assert next(z for z in state(db,'branch_limits') if z['branch_id']=='traditional')==tr
  a.set_branch_limit('coupling_ml',cou['cap'],enabled=True,preferred=json.loads(cou['preferred_slot_order']));assert decision(db,a,'coupling_ml')['eligible'];assert not state(db,'lease_events')
  return {'coupling_reasons':c['reasons'],'traditional_decision':t['eligible'],'v1_read_global_entry_control':native['result'],'traditional_row_unchanged':True,'formal_branch_rollback_pass':True,'whole_runner_was_not_invoked':True,'scientific_entries':0}
 def traditional_reserved():
  db,a=fresh('reserved');lease=a.acquire('traditional','OFFLINE_FAKE_CASE','attempt_001');before=state(db,'slots');first=decision(db,a,'traditional',lease=lease,final=True);assert first['eligible'];a.set_branch_limit('coupling_ml',2,enabled=False,preferred=['GLOBAL_SLOT_2','GLOBAL_SLOT_3','GLOBAL_SLOT_1']);after=decision(db,a,'traditional',lease=lease,final=True)
  assert after['owner_fencing_reservation']['slot'] and not after['owner_fencing_reservation']['generation'] and 'OWNER_FENCING_OR_RESERVATION_INVALID' in after['reasons'];assert state(db,'slots')==before;assert all(z['event_type']!='SCIENTIFIC_SOLVER_ENTERED' for z in state(db,'lease_events'))
  return {'before_eligible':first['eligible'],'after_reasons':after['reasons'],'owner_slot_unchanged':True,'generation_invalidated':True,'scientific_entries':0}
 def live_preservation():
  db,a=fresh('live');lease=a.acquire('traditional','OFFLINE_LIVE_FIXTURE','attempt_001')
  # Fixture initialization only: no scientific entry method or scientific event.
  with db.immediate() as con:con.execute("UPDATE slots SET state='LIVE' WHERE slot_id=?",(lease.slot_id,))
  before=state(db,'slots');db.set_hold(scope='COUPLING_ML',reason_code='FIXTURE',created_by='fixture');assert state(db,'slots')==before;a.set_branch_limit('coupling_ml',2,enabled=False,preferred=['GLOBAL_SLOT_2','GLOBAL_SLOT_3','GLOBAL_SLOT_1']);assert state(db,'slots')==before
  assert all(z['event_type']!='SCIENTIFIC_SOLVER_ENTERED' for z in state(db,'lease_events'));return {'live_slot_and_owner_tokens_unchanged':True,'only_fixture_db_mutated':str(db.path),'actual_process_survival_not_tested_by_this_fixture':True,'scientific_entries':0}
 for name,fn in [('scoped_hold_is_global_and_rollback',scoped_hold),('branch_disable_does_not_cover_v1_global_guard',branch_gap),('branch_generation_invalidates_traditional_reserved_lease',traditional_reserved),('controls_preserve_live_owner_fixture',live_preservation)]:test(name,fn)
proof={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_identity':source_identity,'v1_guard_source':{'path':str(src),'file_sha256':sha(src),'function_sha256':hashlib.sha256(guard_source.encode()).hexdigest(),'lines':[node.lineno,node.end_lineno],'execution':'exact AST function, explicit sandbox db argument; no adapter construction'},'tests':rows,'pass_count':sum(z['result']=='PASS' for z in rows),'fail_count':sum(z['result']!='PASS' for z in rows),'official_control_mutations':0,'solver_calls':0,'native_api_calls':0,'scheduler_mutations':0,'production_db_writes':0,'limitations':['No production admission attempts performed','No Scheduler demand-start attempts performed','Guard PASS establishes branch-control coverage gap, not whole Runner admission']}
p=rt/'shadow_validation.json'
if p.exists() and not (rt/'shadow_validation_first.json').exists():shutil.copy2(p,rt/'shadow_validation_first.json')
p.write_text(json.dumps(proof,indent=2),encoding='utf-8');print('SHADOW',proof['pass_count'],'PASS',proof['fail_count'],'FAIL');print(json.dumps([z for z in rows if z['result']!='PASS'],indent=2));sys.exit(bool(proof['fail_count']))
