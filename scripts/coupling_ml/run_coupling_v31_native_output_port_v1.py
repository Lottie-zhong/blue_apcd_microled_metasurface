"""New Runner output-layout/importer port test; reuse prior scientific extraction."""
from pathlib import Path
import sys,json,shutil,importlib.util
import numpy as np
R=Path(r'D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1');O=R/'reports/coupling/APCD_COUPLING_DIAG2_V31_FINAL_EXECUTION_GATE_CLOSEOUT_V1';B=R/'reports/coupling/APCD_COUPLING_DIAG2_V3_1_BUDGET_MIGRATION_AND_AL_HANDOFF_V1';G=Path(r'D:\project\worktrees\blue_apcd_gpu_v2_serial_production_v1')
sys.path.insert(0,str(R/'scripts/coupling_ml'));sys.path.insert(0,str(G/'platform_v2'))
from coupling_v31_science_binding_v1 import output_pair,routed_historical_record,stage_native_read_view
from k6_v2_pipeline import generic_profile as GP,ingest as I,contracts as C
from apcd_gpu_v2.native_readonly import native_session,pinned_module
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def put(n,j):(O/n).write_text(json.dumps(j,indent=2,allow_nan=False,default=str)+'\n',encoding='utf-8')
proof=read(B/'HISTORICAL_NATIVE_REEXTRACTION.json');control=proof['cases'][0];assert control['case_id']=='K6GDP2_DEV_G001'
S=O/'new_runner_output_fixture';assert S.is_dir();root=S/'outputs';fsp=root/'batch_1/job_1_output.fsp';h5=fsp.with_suffix('')/'run_output.h5';assert h5.parent.is_dir()
assert fsp.is_file() and h5.is_file()
pair=output_pair(root,1,1);assert pair['native_fsp']['sha256']==control['native_pair']['fsp']['sha256'] and pair['native_h5']['sha256']==control['native_pair']['h5']['sha256']
view=stage_native_read_view(pair,S/'native_read_view',Path(control['native_pair']['fsp']['path']).name);load_fsp=Path(view['fsp'])
cfg=read(Path(r'D:\apcd_runtime\gpu_platform_v2_serial_production_v1\serial_config.json'));pin=cfg['truth_toolchain']['lumapi'];lum=pinned_module(pin['path'],pin['sha256'],'lumapi');session={};monitor_reads=[]
try:
 with native_session(lum.FDTD,{str(load_fsp):pair['native_fsp']['sha256']},session) as fd:
  fd.load(str(load_fsp))
  for mon in ['MON_IN','MON_PRENP','MON_POSTNP']:
   freq=np.asarray(fd.getdata(mon,'f')).reshape(-1);waves=299792458/freq*1e9;assert len(freq)==21 and np.allclose(np.sort(waves),np.arange(440,461),atol=1e-6,rtol=0)
   for comp in ['Ex','Ey','Ez','Hx','Hy','Hz']:
    a=np.asarray(fd.getdata(mon,comp));assert np.iscomplexobj(a) and np.isfinite(a).all();monitor_reads.append({'monitor':mon,'component':comp,'shape':list(a.shape),'complex':True,'finite':True})
finally:put('NEW_OUTPUT_PATH_NORMALIZED_SESSION.json',session)
assert session.get('close_called') and not session['after_children'] and all(e['api'] not in ['run','runparallel','save','switchtolayout','eval'] for e in session['events'])
# Scientific extraction already passed; byte-identical native pair permits reuse of its state/raw artifacts.
H=R/'reports/coupling/APCD_COUPLING_V21_SCIENCE_CONTRACT_CLOSEOUT_V1/fixtures/HISTORICAL_READONLY_AUDIT_ONLY';mp=H/'HISTORICAL_MANIFEST_AUDIT_ONLY.json';ap=H/'HISTORICAL_ADMISSION_AUDIT_ONLY.json';cp=H/'HISTORICAL_PROFILE_CERTIFICATION_AUDIT_ONLY.json';man=read(mp);row=next(x for x in man['cases'] if x['case_id']==control['case_id'])
authority={'schema':GP.AUTHORITY_SCHEMA,'profile_id':GP.PROFILE_ID,'manifest':man,'manifest_file_sha':I.sha256_file(mp),'admission':read(ap),'admission_file_sha':I.sha256_file(ap),'certification':read(cp),'certification_file_sha':I.sha256_file(cp)}
pm=H/(control['case_id']+'_PROFILE_RUN_MANIFEST_AUDIT_ONLY.json');existing=read(control['readonly_record']);record=routed_historical_record(existing,pair,pm,I.sha256_file(pm),row['case_request_sha256'])
imported=GP.load_authorized_runner_case(record,expected_role=row['role'],root=R,authority=authority);receipt=GP.validate_authorized_labels(imported,authority=authority);assert receipt['outputs']==609
assert receipt['target_sha256']==control['numeric']['target_sha256']
assert imported.case_id==control['case_id'] and imported.attempt_id==control['attempt_id']
put('NEW_OUTPUT_PATH_RUN_RECORD_AUDIT_ONLY.json',record);put('NEW_OUTPUT_PATH_SCIENCE_RECEIPT_AUDIT_ONLY.json',{'audit_only':True,'historical_identity_preserved':True,'new_scientific_entry':False,'receipt':receipt})
tests=[{'name':'new_Runner_outputFSP_named_path_fresh_LOAD','pass':True},{'name':'native_complex_EH_21wavelengths','pass':True},{'name':'paired_native_H5_finiteEH_and_SHA','pass':True},{'name':'existing_609D_profile_import_and_label_SHA_match','pass':True}]
# Missing native H5 must not become labels-valid even when the job claims COMPLETED.
badroot=S/'missing_h5/outputs';badfsp=badroot/'batch_9/job_9_output.fsp';badfsp.parent.mkdir(parents=True);badfsp.write_bytes(b'CONTROLLED_NEGATIVE_NOT_FSP')
try:output_pair(badroot,9,9);raise AssertionError('missing H5 accepted')
except Exception as ex:
 assert 'NATIVE_H5_MISSING' in str(ex);tests.append({'name':'COMPLETED_without_H5_rejected','pass':True,'reason':str(ex)})
badrecord=json.loads(json.dumps(record));badrecord['native_h5']['sha256']='0'*64
try:GP._verify_native_outputs(badrecord);raise AssertionError('wrongH5SHA accepted')
except ValueError as ex:tests.append({'name':'wrong_nativeH5_SHA_rejected','pass':True,'reason':str(ex)})
badrecord=json.loads(json.dumps(record));badrecord['case_id']='K6V3_TIME_DIAG2_A1_5NM_6PS'
try:GP.load_authorized_runner_case(badrecord,expected_role=row['role'],root=R,authority=authority);raise AssertionError('history relabeled DIAG2')
except ValueError as ex:tests.append({'name':'history_must_not_be_renamed_6ps_DIAG2','pass':True,'reason':str(ex)})
put('NATIVE_OUTPUT_IMPORTER_INTERFACE.json',{'status':'PASS','scope':'New V3.1 output-path pair to frozen importer interface, using byte-identical legal historical native control; not6ps truth nor live Runner save guarantee','tests':tests,'pass':len(tests),'fail':0,'native_pair':pair,'read_view':view,'rename_only_failure':'Original serialized native basename must be preserved; raw byte rename lost Ex lookup; normalized copy changes no science bytes','monitor_reads':monitor_reads,'historical_source':str(B/'HISTORICAL_NATIVE_REEXTRACTION.json'),'historical_id':imported.case_id,'original_attempt':imported.attempt_id,'outputs':609,'target_sha256':receipt['target_sha256'],'science_receipt_sha256':receipt['science_receipt_sha256'],'extraction_reused_from':control['readonly_record'],'scientific_formulas_changed':False,'previous_two_case_extraction_repeated':False,'new_output_layout_fresh_LOAD_cases':1,'new_solver_entries':0,'DIAG2_6ps_truth':'NOT_RUN','production_ledger_writes':0,'new_entries_allowed_from_this_test':False})
print('NATIVE_OUTPUT_INTERFACE_PASS',len(tests),flush=True)
