"""Thin science bindings/output-path adapter; no solver or Runner source changes."""
from pathlib import Path
from copy import deepcopy
import os,json
def need(ok,reason):
 if not ok:raise ValueError(reason)
def bind_original_case(reference,batch_row,job_row,database_path):
 science_batch='K6V3_TIME_DIAG2_V1_BATCH_001'
 need(batch_row['name'] in [science_batch,science_batch+'__EXEC__'+reference['case_id']],'original_science_batch_or_exact_execution_subbatch_required')
 need(job_row['batch_id']==batch_row['id'],'job_batch_mismatch')
 need(str(Path(job_row['input_fsp_path']).resolve()).lower()==str(Path(reference['source_fsp']['path']).resolve()).lower(),'job_source_path_mismatch')
 need(job_row['input_fsp_sha256']==reference['source_fsp']['sha256'],'job_source_sha_mismatch')
 need(reference['attempt_id']=='attempt_001','original_attempt_required')
 need(reference['case_id'] in ['K6V3_TIME_DIAG2_A1_5NM_6PS','K6V3_TIME_DIAG2_A2_5NM_6PS'],'original_science_case_required')
 need(reference['physics_contract_sha']=='51212d0c69f2112add3ee4008eb51a8aa94e380c39624d93d31e5f75e7be0e36','frozen_six_ps_required')
 return {'science_identity':{'dataset_id':'APCD_COUPLING_V3_TIME_DIAG2_V1','case_id':reference['case_id'],'attempt_id':'attempt_001'},'case_id':reference['case_id'],'attempt_id':'attempt_001','batch_id':'K6V3_TIME_DIAG2_V1_BATCH_001','runner_batch_name':batch_row['name'],'runner_database':str(Path(database_path).resolve()),'runner_batch_row_id':batch_row['id'],'runner_job_id':job_row['id'],'physics_contract_sha':reference['physics_contract_sha'],'source_fsp_sha':reference['source_fsp']['sha256'],'source_fsp':reference['source_fsp']['path'],'case_request_sha':reference['case_request_sha256'],'inherited_budget_ceiling':2,'per_case_ceiling':1,'new_budget':0,'runner_attempt_tag':None}
def write_binding_exclusive(path,binding):
 p=Path(path);p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x',encoding='utf-8') as f:json.dump(binding,f,indent=2);f.flush();os.fsync(f.fileno())
def validate_entry_binding(binding,request):
 need((binding['case_id'],binding['attempt_id'])==(request.case_id,request.attempt_id),'science_entry_identity_mismatch')
 need(binding['source_fsp_sha']==request.pre_fsp_sha256,'science_entry_source_sha_mismatch')
 need(binding['physics_contract_sha']==request.physical_contract_sha256,'science_entry_contract_mismatch')
 need(binding['case_request_sha']==request.request_sha256,'science_entry_request_mismatch')
def simulate_bound_entry(binding,request,budget,runner,fixture_root,launch_port):
 """Only an explicit isolated test fixture may invoke this zero-solver port."""
 root=Path(fixture_root).resolve();db=Path(runner.db_path).resolve();ledger=Path(budget.path).resolve()
 need('identity_fixture' in root.parts,'explicit_identity_fixture_required')
 need(root in db.parents and root in ledger.parents,'fixture_storage_escape')
 need(budget.config.mode=='TEST_FIXTURE_ONLY','production_not_supported_by_simulation')
 validate_entry_binding(binding,request)
 # Existing write-ahead, writer mutex, one-case budget and replay rules are reused.
 budget.prepare_entry(request,'ISOLATED_TEST_OWNER')
 budget.mark_launch_request(request,'ISOLATED_TEST_OWNER')
 tag='TEST_EXECUTION_TAG_JOB_'+str(binding['runner_job_id'])
 runner._record_solver_entry(binding['runner_job_id'],tag)
 return launch_port({**binding,'runner_attempt_tag':tag})
def output_pair(output_root,batch_row_id,job_id):
 from apcd_gpu_v2.artifacts import bundle_inventory
 root=Path(output_root).resolve();fsp=root/f'batch_{batch_row_id}'/f'job_{job_id}_output.fsp'
 need(root in fsp.resolve().parents,'native_output_path_escape')
 inventory=bundle_inventory(fsp,'run_output.h5')
 h5=fsp.with_suffix('')/'run_output.h5'
 return {'native_fsp':{'path':str(fsp),'sha256':inventory[fsp.name]['sha256']},'native_h5':{'path':str(h5),'sha256':inventory[h5.relative_to(fsp.parent).as_posix()]['sha256']},'inventory':inventory}
def routed_historical_record(existing_record,pair,profile_run_manifest,profile_run_manifest_sha,request_sha):
 """Path-only audit: preserve the historical case/attempt, never rename it DIAG2."""
 r=deepcopy(existing_record)
 need(r['case_id'] in ['K6GDP2_DEV_G001','K6GDP2_DEV_G004'],'historical_readonly_control_required')
 r.update(native_fsp=pair['native_fsp'],native_h5=pair['native_h5'],request_sha256=request_sha,physical_contract_file_sha256=r['physical_contract_sha256'])
 r['source_manifest']={'path':str(profile_run_manifest),'sha256':profile_run_manifest_sha}
 return r

def stage_native_read_view(pair,view_root,native_basename):
 """Preserve the declared native basename in an isolated byte-identical read view."""
 import shutil
 from k6_v2_pipeline.ingest import sha256_file
 name=Path(native_basename)
 need(name.name==native_basename and name.suffix.lower()=='.fsp','declared_native_basename_required')
 root=Path(view_root);root.mkdir(parents=True,exist_ok=False)
 target=root/name;h5=target.with_suffix('')/'run_output.h5';h5.parent.mkdir()
 shutil.copy2(pair['native_fsp']['path'],target);shutil.copy2(pair['native_h5']['path'],h5)
 need(sha256_file(target)==pair['native_fsp']['sha256'],'read_view_fsp_byte_identity')
 need(sha256_file(h5)==pair['native_h5']['sha256'],'read_view_h5_byte_identity')
 return {'fsp':str(target),'h5':str(h5),'declared_native_basename':native_basename,'native_fsp_sha256':pair['native_fsp']['sha256'],'native_h5_sha256':pair['native_h5']['sha256'],'original_artifacts_modified':False}
