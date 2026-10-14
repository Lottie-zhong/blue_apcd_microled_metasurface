import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from apcd_gpu_v2.artifacts import sha256
from apcd_gpu_v2.config import digest
from apcd_gpu_v2.general import (Admission, Pin, Platform, Registry, GeneralBudget,
    build_requests, load_batch, read_json, verify_acl)
from apcd_gpu_v2.ledger import Refused
from apcd_gpu_v2.trusted_admission import (OwnerIntent, FixturePrincipal, _paths,
    issue_and_initialize, require_science_owner, verify_issued_admission)
from test_general_runner import setup, batch, write


FAULTS=['partial_temporary_write','reservation_committed','genesis_committed',
        'admission_committed','ledger_committed','activation_committed']


def packet(tmp_path,name='UNSEEN_ADMISSION_BATCH',hold=False,real=False):
    platform,registry,_=setup(tmp_path)
    source_rows=None
    evidence={}
    if real:
        from test_diag2_contract_compatibility import frozen_inputs
        mp,_,original,cp,_,contract,contract_sha=frozen_inputs()
        source_rows=original['batch']['cases']
        ids=[r['case_id'] for r in source_rows]
        geom={r['case_id']:r['ordered_D1_D6_nm'] for r in source_rows}
        manifest,old_admission,ledger=batch(platform,original['batch']['batch_id'],hold=hold,
            case_ids=ids,contract_payload=contract,physical_identity_sha=contract_sha,
            role='TIME_CONVERGENCE_DIAGNOSTIC_ONLY',geometries=geom)
        cert=Path(os.environ['APCD_TEST_COUPLING_ROOT'])/'reports/coupling/APCD_COUPLING_V21_SCIENCE_CONTRACT_CLOSEOUT_V1/COUPLING_609D_PROFILE_CERTIFICATION.json'
        binding=Path(os.environ['APCD_TEST_COUPLING_ROOT'])/'reports/coupling/APCD_COUPLING_DIAG2_FINAL_ADMISSION_BINDING_V1/FINAL_ADMISSION_BINDING_CHECK.json'
        evidence={k:dict(path=str(p),sha256=sha256(p)) for k,p in [('frozen_manifest',mp),('frozen_contract',cp),('frozen_profile_certification',cert),('final_science_binding',binding)]}
    else:
        manifest,old_admission,ledger=batch(platform,name,hold=hold)
    # Only the old isolated helper's fabricated authority is removed, never production data.
    ledger.unlink();Path(old_admission.path).unlink()
    doc=read_json(manifest.path)
    provenance=[]
    for i,row in enumerate(doc['cases']):
        if source_rows:
            source=source_rows[i]
            Path(row['source_fsp']['path']).write_bytes(Path(source['candidate_pre_fsp_path']).read_bytes())
            row['source_fsp']['sha256']=sha256(row['source_fsp']['path'])
            Path(row['source_manifest']['path']).write_bytes(Path(source['setup_input']['source_manifest_path']).read_bytes())
            row['source_manifest']['sha256']=sha256(row['source_manifest']['path'])
            project={k:v for k,v in row.items() if k not in ['case_request_sha256','source_acceptance']}
            row['case_request_sha256']=digest(dict(schema='APCD_COUPLING_CASE_REQUEST_CANON_V1',case_request=project,source_acceptance_path=row['source_acceptance']['path']))
            proof=read_json(row['source_acceptance']['path'])
            proof.update(source_fsp_sha=row['source_fsp']['sha256'],source_manifest_sha256=row['source_manifest']['sha256'],case_request_sha256=row['case_request_sha256'])
            row['source_acceptance']=write(Path(row['source_acceptance']['path']),proof)
            run=dict(path=source['source_run_truth']['source_run_fsp_path'],sha256=source['source_run_truth']['source_run_fsp_sha256'])
            pre=dict(path=source['setup_input']['source_setup_pre_fsp_path'],sha256=source['setup_input']['source_setup_pre_fsp_sha256'])
            original_manifest=dict(path=source['setup_input']['source_manifest_path'],sha256=source['setup_input']['source_manifest_sha256'])
        else:
            folder=Path(row['source_fsp']['path']).parent
            prefile=folder/(row['case_id']+'_prior_setup.fsp');prefile.write_bytes(b'ISOLATED_3PS_INPUT_FIXTURE')
            runfile=folder/(row['case_id']+'_prior_run.fsp');runfile.write_bytes(b'ISOLATED_PRIOR_TRUTH_FIXTURE')
            pre=dict(path=str(prefile),sha256=sha256(prefile));run=dict(path=str(runfile),sha256=sha256(runfile));original_manifest=row['source_manifest']
        auxiliary=[]
        if source_rows:
            auxiliary=[dict(path=source['setup_input']['source_setup_spec_path'],sha256=source['setup_input']['source_setup_spec_sha256']),
                dict(path=source['setup_input']['source_load_proof_path'],sha256=source['setup_input']['source_load_proof_sha256']),
                dict(path=source['candidate_setup_load_proof_path'],sha256=source['candidate_setup_load_proof_sha256']),
                dict(path=source['setup_readback_audit_path'],sha256=source['setup_readback_audit_sha256'])]
        provenance.append(dict(case_id=row['case_id'],attempt_id=row['attempt_id'],source_run_truth=run,
            setup_input=pre,candidate_setup=row['source_fsp'],source_manifest=original_manifest,auxiliary=auxiliary))
    doc['manifest_sha']=digest({k:v for k,v in doc.items() if k!='manifest_sha'})
    manifest=Pin(**write(Path(manifest.path),doc))
    control=read_json(doc['science_control']['path']);control['manifest_sha']=doc['manifest_sha'];write(Path(doc['science_control']['path']),control)
    release=write(Path(platform.runtime_root)/'science/fixture_release_inventory.json',dict(fixture_only=True,code_inventory_is_test_evidence=True))
    if not evidence:evidence={'test_evidence':release}
    intent=OwnerIntent(schema_version='APCD_GPU_V21_SCIENCE_OWNER_ISSUANCE_INTENT_V1',intent_id=doc['batch_id']+'_INTENT',
        science_owner=platform.science_owner_id,science_owner_sid=platform.science_owner_sid,
        batch_id=doc['batch_id'],manifest_file_sha256=manifest.sha256,manifest_sha256=doc['manifest_sha'],
        approved_case_set=doc['approved_case_set'],approved_entry_budget=2,per_case_entry_limit=1,no_replay=True,
        profile_id='coupling_609d_v1',profile_certification_sha256=platform.profiles[0].certification.sha256,
        release_inventory=release,scientific_evidence=evidence,case_provenance=provenance,
        scope='SCIENCE_ADMISSION_AND_LEDGER_GENESIS_ONLY',solver_entry_authorized=False,fixture_only=True)
    intent_pin=Pin(**write(Path(platform.science_root)/doc['batch_id']/'intent.json',intent.model_dump(mode='json')))
    actor=FixturePrincipal(platform.science_owner_sid,platform.runtime_root)
    return platform,registry,manifest,intent_pin,ledger,actor


def issue(p):return issue_and_initialize(p[0],p[2],p[3],fixture_principal=p[5])


def test_atomic_genesis_no_circular_sha_and_registry_starts_paused(tmp_path):
    p=packet(tmp_path);result=issue(p);ad=Pin(**result['admission']);m,a,_=load_batch(p[0],p[2],ad)
    ledger=read_json(p[4]);genesis=read_json(_paths(p[0],m.batch_id)['genesis'])
    assert ledger['entered_count']==0 and ledger['remaining_unentered_count']==2
    assert ledger['admission_sha256']==ad.sha256 and digest(genesis)==ledger['genesis_sha256']
    assert 'admission_sha256' not in genesis and 'activation' not in genesis
    assert a.issuance['fixture_only'] is True
    assert p[1].submit(p[2],ad)=='SUBMITTED_PAUSED'
    assert p[1].status()['batches'][0]['paused']==1 and p[1].ledger.audit()['tasks']==[]


@pytest.mark.parametrize('sid',['CONSUMER','OPERATOR','FOREIGN'])
def test_unauthorized_identity_cannot_issue(tmp_path,sid):
    p=packet(tmp_path)
    with pytest.raises(Refused,match='IDENTITY_REQUIRED'):
        issue_and_initialize(p[0],p[2],p[3],fixture_principal=FixturePrincipal(sid,p[0].runtime_root))
    assert not p[4].exists() and not (Path(p[0].science_root)/'_admissions').exists()


def test_fixture_never_authorizes_production_and_ordinary_json_is_not_admission(tmp_path):
    p=packet(tmp_path);ad=Pin(**issue(p)['admission']);m,a,_=load_batch(p[0],p[2],ad)
    production=p[0].model_copy(update={'mode':'PRODUCTION_GPU'})
    with pytest.raises(Refused,match='FIXTURE_CREDENTIAL'):
        verify_issued_admission(production,m,p[2],a,ad)
    with pytest.raises(Refused,match='FIXTURE_CREDENTIAL'):
        require_science_owner(production,p[5])
    with pytest.raises(Refused,match='TRUSTED_ISSUANCE_REQUIRED'):
        verify_issued_admission(p[0],m,p[2],a.model_copy(update={'issuance':None}),ad)


@pytest.mark.parametrize('mutation',['manifest_sha256','manifest_file_sha256','profile_certification_sha256','batch_id','approved_case_set','approved_entry_budget'])
def test_intent_tamper_fail_closed(tmp_path,mutation):
    p=packet(tmp_path);intent=read_json(p[3].path)
    intent[mutation]=('0'*64 if 'sha256' in mutation else ['UNKNOWN'] if mutation=='approved_case_set' else 3 if mutation=='approved_entry_budget' else 'FOREIGN_BATCH')
    bad=Pin(**write(Path(p[3].path),intent))
    with pytest.raises(Refused,match='INTENT_BINDING_CONFLICT'):issue_and_initialize(p[0],p[2],bad,fixture_principal=p[5])
    assert not p[4].exists()


@pytest.mark.parametrize('which',['source_fsp','setup_input','physics_contract'])
def test_source_setup_contract_sha_tamper_denied(tmp_path,which):
    p=packet(tmp_path);m=read_json(p[2].path);intent=read_json(p[3].path)
    path=m['cases'][0][which]['path'] if which!='setup_input' else intent['case_provenance'][0]['setup_input']['path']
    Path(path).write_bytes(b'CORRUPTION_FIXTURE')
    with pytest.raises(Refused,match='SHA_MISMATCH'):issue(p)
    assert not p[4].exists()


def test_missing_profile_and_admission_deny(tmp_path):
    p=packet(tmp_path)
    with pytest.raises(Refused,match='UNSUPPORTED_SCIENCE_PROFILE'):
        issue_and_initialize(p[0].model_copy(update={'profiles':[]}),p[2],p[3],fixture_principal=p[5])
    with pytest.raises((Refused,FileNotFoundError)):
        load_batch(p[0],p[2],Pin(path=str(Path(p[0].science_root)/'missing.json'),sha256='0'*64))
    assert not p[4].exists()


@pytest.mark.parametrize('point',FAULTS)
def test_real_process_exit_atomic_activation_and_explicit_recovery(tmp_path,point):
    p=packet(tmp_path)
    child="""import json,os,sys
from apcd_gpu_v2.general import Platform,Pin
from apcd_gpu_v2.trusted_admission import issue_and_initialize,FixturePrincipal
d=json.load(sys.stdin);p=Platform.model_validate(d['platform'])
def fault(step):
 if step==d['point']:os._exit(73)
issue_and_initialize(p,Pin(**d['manifest']),Pin(**d['intent']),fixture_principal=FixturePrincipal(p.science_owner_sid,p.runtime_root),fault=fault)
"""
    payload=dict(platform=p[0].model_dump(mode='json'),manifest=p[2].model_dump(),intent=p[3].model_dump(),point=point)
    stopped=subprocess.run([sys.executable,'-c',child],input=json.dumps(payload),capture_output=True,text=True,timeout=25)
    assert stopped.returncode==73,stopped.stderr
    paths=_paths(p[0],read_json(p[2].path)['batch_id'])
    if point!='activation_committed':
        with pytest.raises((Refused,FileNotFoundError)):
            load_batch(p[0],p[2],Pin(path=str(paths['admission']),sha256=sha256(paths['admission']) if paths['admission'].exists() else '0'*64))
    result=issue_and_initialize(p[0],p[2],p[3],fixture_principal=p[5],recover=True)
    load_batch(p[0],p[2],Pin(**result['admission']))
    assert read_json(p[4])['entered_count']==0 and read_json(p[4])['remaining_unentered_count']==2
    assert p[1].status()['batches']==[] and p[1].ledger.audit()['tasks']==[]


def test_duplicate_issuance_and_entry_no_replay_no_refund(tmp_path):
    p=packet(tmp_path);result=issue(p);ad=Pin(**result['admission'])
    before=p[4].read_bytes()
    with pytest.raises(Refused,match='ALREADY_ISSUED'):issue(p)
    assert issue_and_initialize(p[0],p[2],p[3],fixture_principal=p[5],recover=True)['status']=='ALREADY_ACTIVE_NO_MUTATION'
    assert p[4].read_bytes()==before
    p[1].submit(p[2],ad);p[1].operate(read_json(p[2].path)['batch_id'],False)
    _,pairs=build_requests(p[0],p[2],ad);cfg,req=pairs[0]
    GeneralBudget(cfg).prepare_entry(req,'FIXTURE_OWNER',lambda _:None)
    with pytest.raises(Refused,match='NO_REPLAY|PRIOR_ENTRY'):GeneralBudget(cfg).prepare_entry(req,'OTHER_FIXTURE_OWNER',lambda _:None)
    issue_and_initialize(p[0],p[2],p[3],fixture_principal=p[5],recover=True)
    assert read_json(p[4])['entered_count']==1 and read_json(p[4])['remaining_unentered_count']==1


def test_coupling_genesis_commit_sqlite_registration_rollback(tmp_path):
    p=packet(tmp_path);ad=Pin(**issue(p)['admission'])
    with p[1].ledger.transaction() as db:db.execute("CREATE TRIGGER reject_batch BEFORE INSERT ON v21_batches BEGIN SELECT RAISE(ABORT,'fixture crash'); END")
    with pytest.raises(sqlite3.IntegrityError):p[1].submit(p[2],ad)
    assert p[1].status()['batches']==[] and read_json(p[4])['entered_count']==0
    with p[1].ledger.transaction() as db:db.execute('DROP TRIGGER reject_batch')
    assert p[1].submit(p[2],ad)=='SUBMITTED_PAUSED'
    assert read_json(p[4])['authorized_entry_budget']==2


def test_doe56_hold_cross_batch_and_existing_records_never_overwritten(tmp_path):
    p=packet(tmp_path,name='DOE56',hold=True)
    with pytest.raises(Refused,match='BATCH_SCIENCE_HOLD'):issue(p)
    assert not p[4].exists()
    (tmp_path/'other').mkdir();q=packet(tmp_path/'other',name='DIAG2_ONLY');p[4].parent.mkdir(exist_ok=True);p[4].write_text('{"historical":true}')
    old=p[4].read_bytes();issue(q);assert p[4].read_bytes()==old


def test_generic_write_acl_is_not_mistaken_for_read_only(tmp_path):
    p=packet(tmp_path);prod=p[0].model_copy(update={'mode':'PRODUCTION_GPU'})
    reader=lambda _:dict(owner=p[0].science_owner_sid,rules=[dict(sid='FOREIGN',rights=0x40000000,allow=True)])
    with pytest.raises(Refused,match='FOREIGN_AUTHORITY_WRITE'):verify_acl(prod,p[3].path,reader=reader)


def test_gpu_hold_blocks_before_entry_even_after_science_issuance(monkeypatch,tmp_path):
    from apcd_gpu_v2 import serial,general
    p=packet(tmp_path);ad=Pin(**issue(p)['admission']);p[1].submit(p[2],ad)
    p[1].operate(read_json(p[2].path)['batch_id'],False)
    _,pairs=build_requests(p[0],p[2],ad);cfg,req=pairs[0]
    # Unreachable fixture-only production-branch injection: never a production credential.
    cfg=cfg.model_copy(update={'mode':'PRODUCTION_GPU'});req=req.model_copy(update={'config_sha256':cfg.sha256})
    monkeypatch.setattr(serial,'validate_admission',lambda *a:None)
    monkeypatch.setattr(general,'validate_general',lambda *a:None)
    monkeypatch.setattr(general,'validate_profile_admission',lambda *a:dict(fixture_only=True))
    monkeypatch.setattr(serial.NativeTruthValidator,'preflight',lambda *a:dict(fixture_only=True))
    def resource_hold(*a):raise Refused('GPU_RESOURCE_HOLD_FIXTURE')
    monkeypatch.setattr(serial,'native_preflight',resource_hold)
    monkeypatch.setattr(serial.subprocess,'Popen',lambda *a,**k:pytest.fail('solver launch attempted'))
    p[1].ledger.register(req,cfg)
    with pytest.raises(Refused,match='GPU_RESOURCE_HOLD'):
        serial.run_serial_case(cfg,req,p[1].ledger,serial.ProductionNativeBackend(),serial.NativeTruthValidator(cfg))
    assert read_json(p[4])['entered_count']==0


def test_real_a1_a2_contract_and_source_pins_through_trusted_fixture_genesis(tmp_path):
    p=packet(tmp_path,real=True);intent=read_json(p[3].path)
    before={pin['path']:sha256(pin['path']) for pin in intent['scientific_evidence'].values()}
    for row in intent['case_provenance']:
        for key in ['source_run_truth','setup_input','candidate_setup','source_manifest']:before[row[key]['path']]=sha256(row[key]['path'])
    ad=Pin(**issue(p)['admission']);m,a,profile=load_batch(p[0],p[2],ad)
    assert m.batch_id=='K6V3_TIME_DIAG2_V1_BATCH_001' and m.approved_entry_budget==2
    assert len(m.cases)==2 and all(x.simulation_time_s==6e-12 and x.mesh_nm==5 and x.auto_shutoff_min==1e-6 for x in m.cases)
    assert all(x.physics_contract.sha256=='51212d0c69f2112add3ee4008eb51a8aa94e380c39624d93d31e5f75e7be0e36' for x in m.cases)
    assert before=={path:sha256(path) for path in before}
    assert p[1].submit(p[2],ad)=='SUBMITTED_PAUSED' and read_json(p[4])['entered_count']==0


def test_activation_corruption_and_ledger_genesis_mismatch_fail_closed(tmp_path):
    p=packet(tmp_path);ad=Pin(**issue(p)['admission']);m,a,_=load_batch(p[0],p[2],ad)
    row=read_json(p[4]);row['genesis_sha256']='0'*64;write(p[4],row)
    with pytest.raises(Refused,match='GENESIS_IDENTITY_CONFLICT'):load_batch(p[0],p[2],ad)


def test_later_science_hold_blocks_entry_but_keeps_authority_readable_for_recovery(tmp_path):
    p=packet(tmp_path);ad=Pin(**issue(p)['admission']);m,a,_=load_batch(p[0],p[2],ad)
    p[1].submit(p[2],ad);p[1].operate(m.batch_id,False)
    control=read_json(m.science_control.path);control['hold']=True;write(Path(m.science_control.path),control)
    _,pairs=build_requests(p[0],p[2],ad)
    with pytest.raises(Refused,match='BATCH_SCIENCE_HOLD'):GeneralBudget(pairs[0][0]).validate(pairs[0][1])
    assert read_json(p[4])['entered_count']==0


def test_same_case_attempt_cannot_get_a_second_batch_budget(tmp_path):
    p=packet(tmp_path);issue(p);first=read_json(p[3].path)
    m,ad,ledger=batch(p[0],'ANOTHER_BATCH',case_ids=first['approved_case_set']);ledger.unlink();Path(ad.path).unlink()
    doc=read_json(m.path)
    second={**first,'intent_id':'OTHER_INTENT','batch_id':doc['batch_id'],'manifest_file_sha256':m.sha256,'manifest_sha256':doc['manifest_sha']}
    second['case_provenance']=[{**old,'candidate_setup':new['source_fsp']} for old,new in zip(first['case_provenance'],doc['cases'])]
    ip=Pin(**write(Path(p[0].science_root)/'other_intent.json',second))
    with pytest.raises(Refused,match='CROSS_BATCH_ATTEMPT_ALREADY_RESERVED'):
        issue_and_initialize(p[0],m,ip,fixture_principal=p[5])
    assert not ledger.exists()


def test_installed_old_admission_schema_refuses_new_fixture_envelope(tmp_path):
    p=packet(tmp_path);ad=Pin(**issue(p)['admission'])
    installed=Path(r'D:\apcd_runtime\gpu_platform_v2_serial_production_v1\releases\v21_diag2_validator_b9abe87058d6\platform_v2')
    assert installed.is_dir()
    child="from apcd_gpu_v2.general import Admission; import pathlib,sys; Admission.model_validate_json(pathlib.Path(sys.argv[1]).read_text(encoding='utf-8'))"
    env=dict(os.environ,PYTHONPATH=str(installed))
    result=subprocess.run([sys.executable,'-c',child,ad.path],env=env,cwd=p[0].runtime_root,capture_output=True,text=True,timeout=20)
    assert result.returncode!=0 and 'extra_forbidden' in result.stderr


def test_production_cli_cannot_be_used_with_fixture_authority(tmp_path):
    from apcd_gpu_v2.trusted_admission import main
    p=packet(tmp_path);pp=write(Path(p[0].runtime_root)/'platform.json',p[0].model_dump(mode='json'))
    args=['check','--platform',pp['path'],'--platform-sha256',pp['sha256'],'--manifest',p[2].path,'--manifest-sha256',p[2].sha256,'--intent',p[3].path,'--intent-sha256',p[3].sha256]
    assert main(args)==2 and not p[4].exists()


def test_fixture_root_smuggling_is_rejected_before_any_writer_lock(tmp_path):
    p=packet(tmp_path);outside=tmp_path/'outside_not_authorized'
    forged=p[0].model_copy(update={'science_root':str(outside)})
    with pytest.raises(Refused,match='AUTHORITY_PATH_ESCAPE'):
        issue_and_initialize(forged,p[2],p[3],fixture_principal=p[5])
    assert not outside.exists()


def test_partial_activation_recovery_never_overwrites_existing_science_records(tmp_path):
    p=packet(tmp_path)
    def stop(step):
        if step=='ledger_committed':raise RuntimeError('fixture stop')
    with pytest.raises(RuntimeError):issue_and_initialize(p[0],p[2],p[3],fixture_principal=p[5],fault=stop)
    value=read_json(p[4]);value['case_records']={'FOREIGN':{'solver_entered':True}};write(p[4],value)
    before=p[4].read_bytes()
    with pytest.raises(Refused,match='IMMUTABLE_ISSUANCE_ARTIFACT_CONFLICT'):
        issue_and_initialize(p[0],p[2],p[3],fixture_principal=p[5],recover=True)
    assert p[4].read_bytes()==before
    assert not _paths(p[0],value['batch_id'])['activation'].exists()


def test_non_general_production_paths_cannot_bypass_trusted_admission():
    from types import SimpleNamespace
    from apcd_gpu_v2 import serial
    cfg=SimpleNamespace(mode='PRODUCTION_GPU')
    with pytest.raises(Refused,match='TRUSTED_V21_ADMISSION_PATH_REQUIRED'):
        serial.run_serial_case(cfg,None,None,None,None)
    with pytest.raises(Refused,match='TRUSTED_V21_ADMISSION_PATH_REQUIRED'):
        serial.ProductionNativeBackend().execute(cfg,None,None,None,None,None)
    with pytest.raises(Refused,match='TRUSTED_V21_ADMISSION_PATH_REQUIRED'):
        serial.ProductionNativeBackend()._execute(cfg,None,None,None,None,None,None,None)
