# V3 adapter fault injection. All process invocations are labelled fixture Python.
import copy,json,sys,time
from pathlib import Path
import numpy as np
import pytest
from apcd_gpu_v2.artifacts import sha256
from apcd_gpu_v2.config import digest
from apcd_gpu_v2.ledger import Refused
from apcd_gpu_v2.serial import Pin,SerialRequest,SerialLedger,EquivalentBackend,controller
from apcd_gpu_v2.v3 import V3Config,V3Request,V3Budget,DATASET,FROZEN_MANIFEST_SHA,validate_registered,time_gate,registry_cases,morning_report
SOURCE=Path('D:/apcd_runtime/gpu_v3_interface_audit_20261011_v1/V3_NEW_CASE_REGISTRY.json')
FROZEN=Path('D:/project/worktrees/blue_apcd_mdc_np_coupling_ml_v1/reports/coupling/APCD_COUPLING_ML_V3_DOE56_OVERNIGHT_PRODUCTION_DESIGN_V1/V3_DOE56_FROZEN_GEOMETRY_MANIFEST.json')
def put(path,body):
 path.write_text(json.dumps(body));return dict(path=str(path),sha256=sha256(path))
def fixture(tmp_path):
 if not SOURCE.exists():pytest.skip('native source inventory not supplied')
 root=tmp_path/'zero_solver_v3';root.mkdir();src=json.loads(SOURCE.read_text());frozen={x['case_id']:x for x in json.loads(FROZEN.read_text())['cases']};rows=[]
 for x in src['cases']:
  a=x['artifacts'];row=dict(case_id=x['case_id'],attempt_id='attempt_001',role=x['frozen_role'],ordered_D_nm=x['ordered_D_nm'],pre_fsp=a['pre_fsp']['path'],pre_fsp_sha256=a['pre_fsp']['sha256'],source_manifest=a['source_manifest'],physical_contract=a['physical_contract'],physical_contract_sha256=a['physical_contract']['sha256'],frozen_case=frozen[x['case_id']],frozen_case_sha256=digest(frozen[x['case_id']]))
  if x['execution_role']=='DIAGNOSTIC_4NM':row['actual_contract_binding']=x['actual_contract_binding']
  rows.append(row)
 reg=put(root/'registry.json',dict(schema='V3_REGISTERED_BATCH_V1',dataset_id=DATASET,frozen_manifest_sha256=FROZEN_MANIFEST_SHA,cases=rows));queue=put(root/'queue.json',dict(registry_sha256=reg['sha256'],ordered_cases=rows))
 authority=put(root/'authority.json',dict(dataset_id=DATASET,max_new_entries=56,scientific_budget_approved=True))
 accept=put(root/'accept.json',dict(verdict='PASS',registry_sha256=reg['sha256']))
 gate=put(root/'diagnostic_gate.json',dict(schema='V3_COUPLING_NUMERICAL_GATE_RECEIPT_V1',advance_to_development=True,inputs=dict(registry=reg)))
 budget=root/'budget.json';put(budget,dict(dataset_id=DATASET,authorized_case_count=56,entered_count=0,truth_valid_count=0,labels_valid_count=0,remaining_unentered_count=56,entered_case_ids=[],truth_valid_case_ids=[],labels_valid_case_ids=[],remaining_unentered_case_ids=list(frozen),case_records={}))
 release=root/'release.json'
 cfg=V3Config.model_validate_json(json.dumps(dict(schema_version='APCD_V2_REGISTERED_V3_SERIAL_V1',dataset_id=DATASET,mode='PRODUCTION_EQUIVALENT',runtime_root=str(root),coupling_root=str(root),coupling_ledger=str(budget),registry=reg,budget_authority=authority,engineering_acceptance=accept,science_acceptance=accept,sealed_identity_acceptance=accept,identity_authority=accept,diagnostic_gate=gate,v3_data_root=str(root/'v3_data'),window=dict(deadline_unix=time.time()+90000,historical_5nm_q95_seconds=716.230),queue=queue,release=dict(path=str(release),sha256='0'*64),fdtd_executable=sys.executable,executable_sha256=sha256(sys.executable),gpu_resource='GPU license audit',native_h5_name='run_output.h5',physical_contract_sha256=rows[0]['physical_contract_sha256'],heartbeat_seconds=0.01)))
 def requests(c):
  return [V3Request.model_validate_json(json.dumps({**{k:x[k] for k in ['case_id','attempt_id','role','ordered_D_nm','pre_fsp','pre_fsp_sha256','source_manifest','physical_contract','physical_contract_sha256','frozen_case_sha256']},'dataset_id':DATASET,'registry_sha256':reg['sha256'],'config_sha256':c.sha256})) for x in rows]
 reqs=requests(cfg);releasepin=put(release,dict(schema='APCD_V3_FINITE_SERIAL_RELEASE_V1',dataset_id=DATASET,registry_sha256=reg['sha256'],queue_sha256=queue['sha256'],requests=[x.admission_sha256 for x in reqs],expires_unix=time.time()+90000,science_authorized=False,fixture_only=True));cfg=cfg.model_copy(update={'release':Pin.model_validate(releasepin)});reqs=requests(cfg)
 script=root/'fake.py';script.write_text('''# APCD_ZERO_SOLVER_FIXTURE
import sys,time
from pathlib import Path
import h5py,numpy as np
p=Path(sys.argv[1]);time.sleep(.05);p.write_bytes(b'NOT_NATIVE_SCIENTIFIC_TRUTH');p.with_suffix('').mkdir()
with h5py.File(p.with_suffix('')/'run_output.h5','w') as h:
 for c in ['Ex','Ey','Ez','Hx','Hy','Hz']:h.create_dataset('Monitor1/'+c,data=np.ones((2,2,1,21),complex))
''')
 return cfg,reqs,EquivalentBackend(script)
def validator(fsp,request,dest):
 label=dest/'synthetic_labels.npz';np.savez(label,C_hat=np.ones((21,7,2),complex),P_scale=np.ones(21))
 return dict(verdict='PASS',outputs=609,fresh_load_verified=True,actual_importer='load_verified_runner_case',test_double=True,labels_artifact=dict(path=str(label),sha256=sha256(label)),record={'fixture_only':True})
def test_exact56_registry_and_legacy_reject(tmp_path):
 cfg,rs,_=fixture(tmp_path);assert len(registry_cases(cfg))==56
 for r in rs:validate_registered(cfg,r)
 bad=rs[0].model_copy(update={'case_id':'K6V3_NOT_REGISTERED'})
 with pytest.raises(Refused,match='UNREGISTERED'):validate_registered(cfg,bad)
 with pytest.raises(Exception):SerialRequest.model_validate_json(rs[0].model_dump_json())
@pytest.mark.parametrize('key,value',[('attempt_id','attempt_002'),('role','SEALED_GLOBAL'),('physical_contract_sha256','0'*64),('pre_fsp_sha256','0'*64),('frozen_case_sha256','0'*64),('ordered_D_nm',(100,100,100,100,100,100))])
def test_case_binding_tamper_refused(tmp_path,key,value):
 cfg,rs,_=fixture(tmp_path)
 with pytest.raises(Refused):validate_registered(cfg,rs[0].model_copy(update={key:value}))
def test_window_boundary_and_contract_separation(tmp_path):
 cfg,rs,_=fixture(tmp_path);deadline=cfg.window.deadline_unix
 assert time_gate(cfg,rs[0],now=deadline-1016.230-1800)['allow_new_entry']
 with pytest.raises(Refused,match='WINDOW'):time_gate(cfg,rs[0],now=deadline-1016.230-1800+.1)
 assert time_gate(cfg,rs[1],now=deadline-2091-1800)['allow_new_entry']
 with pytest.raises(Refused):time_gate(cfg,rs[1],now=deadline-2000-1800)
def test_four_fake_diagnostics_truth_before_next_and_no_replay(tmp_path):
 cfg,rs,b=fixture(tmp_path);result=controller(cfg,rs[:4],b,validator);data=json.loads(Path(cfg.coupling_ledger).read_text());assert data['entered_count']==data['truth_valid_count']==4
 assert result['slot']['token'] is None
 assert {x['case_id']:x['contract_sha'] for x in result['tasks']}=={x.case_id:x.physical_contract_sha256 for x in rs[:4]}
 with pytest.raises(Refused,match='NO_REPLAY'):V3Budget(cfg).validate(rs[0])
 assert len(controller(cfg,rs[:4],b,validator)['events'])==len(result['events'])
 assert not (Path(cfg.v3_data_root)/'V3_DEVELOPMENT/published').exists()
@pytest.mark.parametrize('point',['coupling_receipt_committed','coupling_ledger_committed','before_local_mirror','after_local_mirror','launch_requested','process_started','solver_returned','truth_valid_before_coupling','coupling_truth_before_local'])
def test_v3_cross_ledger_uncertain_never_replays(tmp_path,point):
 cfg,rs,b=fixture(tmp_path)
 def fault(p):
  if p==point:raise RuntimeError('FAULT:'+p)
 with pytest.raises(RuntimeError):controller(cfg,rs[:2],b,validator,fault=fault)
 with pytest.raises(Refused,match='NO_REPLAY'):V3Budget(cfg).validate(rs[0])
 assert V3Budget(cfg).reconcile(rs[0])['receipt']
 assert SerialLedger(Path(cfg.runtime_root)/'ledger.sqlite3').audit()['slot']['token']
 # fixture process may still exist after fault injection; do not kill.
 time.sleep(.5)
def test_postentry_importer_failure_prevents_autofill(tmp_path):
 cfg,rs,b=fixture(tmp_path)
 def fail(*a):raise ValueError('IMPORTER_FAILURE')
 with pytest.raises(ValueError):controller(cfg,rs[:2],b,fail)
 assert json.loads(Path(cfg.coupling_ledger).read_text())['entered_count']==1
 assert SerialLedger(Path(cfg.runtime_root)/'ledger.sqlite3').audit()['slot']['token']
def test_partial_morning_excludes_response_payload(tmp_path):
 cfg,rs,_=fixture(tmp_path);data=json.loads(Path(cfg.coupling_ledger).read_text());cid=rs[-1].case_id;data['case_records'][cid]={'evidence':{'validation':{'C_hat':[123456789], 'labels_artifact':{'path':'SECRET_PATH','sha256':'1'*64}}},'error':'SECRET_RESPONSE'};Path(cfg.coupling_ledger).write_text(json.dumps(data))
 report=morning_report(cfg,{'tasks':[],'slot':{'token':None}},now=0);text=json.dumps(report);assert '123456789' not in text and 'SECRET_RESPONSE' not in text and 'SECRET_PATH' not in text
 assert report['entered']==0 and report['unentered']==56 and report['role_counts']['SEALED_EVALUATION']['total']==8

def test_development_publication_receipt_and_sealed_no_publication(tmp_path):
 cfg,rs,b=fixture(tmp_path);controller(cfg,[rs[4],rs[-1]],b,validator)
 data=json.loads(Path(cfg.coupling_ledger).read_text());dev=data['case_records'][rs[4].case_id]['published_development']
 assert dev['label']['sha256']==sha256(dev['label']['path'])
 receipt=json.loads(Path(dev['receipt']['path']).read_text());assert receipt['registry_sha256']==cfg.registry.sha256 and receipt['training_label_eligible'] is True
 assert data['case_records'][rs[-1].case_id]['published_development'] is None
 assert not (Path(cfg.v3_data_root)/'V3_DEVELOPMENT/published'/rs[-1].case_id).exists()
def test_diagnostic_failure_blocks_development_before_register(tmp_path):
 cfg,rs,b=fixture(tmp_path);p=Path(cfg.diagnostic_gate.path);v=json.loads(p.read_text());v['advance_to_development']=False;p.write_text(json.dumps(v));cfg=cfg.model_copy(update={'diagnostic_gate':Pin(path=str(p),sha256=sha256(p))});r=rs[4].model_copy(update={'config_sha256':cfg.sha256})
 with pytest.raises(Refused,match='DIAGNOSTIC'):controller(cfg,[r],b,validator)
 assert not SerialLedger(Path(cfg.runtime_root)/'ledger.sqlite3').audit()['tasks']
 assert json.loads(Path(cfg.coupling_ledger).read_text())['entered_count']==0
def test_window_stop_preserves_unentered_and_next_window_identity(tmp_path):
 cfg,rs,b=fixture(tmp_path);cfg=cfg.model_copy(update={'window':cfg.window.model_copy(update={'deadline_unix':time.time()+100})});r=rs[0].model_copy(update={'config_sha256':cfg.sha256})
 with pytest.raises(Refused,match='WINDOW'):controller(cfg,[r],b,validator)
 assert json.loads(Path(cfg.coupling_ledger).read_text())['remaining_unentered_count']==56
 assert SerialLedger(Path(cfg.runtime_root)/'ledger.sqlite3').audit()['slot']['token'] is None
 nextcfg=cfg.model_copy(update={'window':cfg.window.model_copy(update={'deadline_unix':time.time()+90000})});n=r.model_copy(update={'config_sha256':nextcfg.sha256});assert n.admission_sha256==r.admission_sha256 and n.case_id==r.case_id and n.attempt_id=='attempt_001'
 controller(nextcfg,[n],b,validator);assert json.loads(Path(cfg.coupling_ledger).read_text())['entered_count']==1
def test_completed_public_morning_report(tmp_path):
 cfg,rs,_=fixture(tmp_path);p=Path(cfg.coupling_ledger);d=json.loads(p.read_text());ids=d['remaining_unentered_case_ids'];d.update(entered_case_ids=ids,truth_valid_case_ids=ids,labels_valid_case_ids=ids,remaining_unentered_case_ids=[],entered_count=56,truth_valid_count=56,labels_valid_count=56,remaining_unentered_count=0);p.write_text(json.dumps(d))
 report=morning_report(cfg,{'tasks':[{'case_id':cid,'state':'TRUTH_VALID'} for cid in ids],'slot':{'token':None}})
 assert report['role_counts']['DEVELOPMENT']==dict(total=44,valid=44) and report['role_counts']['SEALED_EVALUATION']==dict(total=8,valid=8)
 assert report['unentered']==0 and report['replay']==0
