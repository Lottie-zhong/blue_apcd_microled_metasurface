"""DIAG2 real-output acceptance. LOAD/extract only; never run/save/replay."""
from pathlib import Path
import sys,json,os,sqlite3,hashlib,importlib.util,shutil,csv,re,traceback
import numpy as np,h5py
R=Path(r'D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1');P=Path(r'D:\apcd_runtime\gpu_platform_v2_serial_production_v1\minimal_runner_v3');B=R/'reports/coupling/APCD_COUPLING_ML_GPU_V31_FINAL_HANDOFF_AND_DIAG2_BINDING';D=R/'reports/coupling/APCD_COUPLING_DIAG2_V31_CONTROLLED_REAL_EXECUTION_V1';G=Path(r'D:\project\worktrees\blue_apcd_gpu_v2_serial_production_v1')
sys.path[:0]=[str(R/'scripts/coupling_ml'),str(R/'scripts'),str(G/'platform_v2')]
from diag2_v31_bound_admission_view_v1 import reconcile,validate_manifest
from k6_v2_pipeline import ingest as I,contracts as C,generic_profile as GP
from k6_v2_pipeline.postprocess_contract_resolver import _source_fields,_validate_resolved_fields
from apcd_gpu_v2.native_readonly import native_session,pinned_module
from apcd_gpu_v2.artifacts import bundle_inventory
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
def put(p,v):Path(p).write_text(json.dumps(v,indent=2,ensure_ascii=False,allow_nan=False,default=lambda x:x.tolist() if hasattr(x,'tolist') else str(x)),encoding='utf-8')
def desc(p):return dict(path=str(p),sha256=I.sha256_file(p))
def atom(p,j):
 tmp=p.with_suffix('.postprocess.tmp');put(tmp,j);os.replace(tmp,p)
def stop_log(p):
 text=Path(p).read_text(errors='replace');progress=re.findall(r'([\d.eE+-]+)% complete\. Elapsed simulation time: ([\d.eE+-]+) secs\..*?Auto Shutoff: ([\d.eE+-]+)',text)
 return dict(path=str(p),progress=[dict(percent=float(a),physical_time_s=float(b),auto_shutoff=float(c)) for a,b,c in progress],safe_terminal_lines=[l for l in text.splitlines()[-18:] if not any(x in l.lower() for x in ['license','context','command','-shared'])],gpu_confirmed='Detected GPU 0: NVIDIA GeForce RTX 3080' in text,datatype='real32' if 'Using datatype: real32' in text else 'unknown')
def execute_acceptance(index):
 key='A'+str(index+1);ledger=read(B/'DIAG2_SCIENCE_LEDGER.json');binding=ledger['cases'][index];recon=reconcile(ledger);assert recon['cases'][index]['entered_count']==1
 con=sqlite3.connect(Path(binding['runner_db']).as_uri()+'?mode=ro',uri=True);con.row_factory=sqlite3.Row;job=dict(con.execute('SELECT * FROM jobs WHERE id=?',(binding['runner_job_id'],)).fetchone());con.close();assert job['status']=='COMPLETED',job
 validate_manifest(ledger,read(B/(binding['case_id']+'_MANIFEST.json')),P/'minimal_batch_runner_v3.1_final.py')
 out=D/(key+'_science');out.mkdir(exist_ok=False);fsp=Path(job['output_fsp_path']);assert I.sha256_file(fsp)==job['output_sha256'];root=fsp.parent
 h5s=sorted(p for p in root.rglob('*.h5') if p.stat().st_size>0);assert h5s,'NATIVE_H5_MISSING';native_h5=next((p for p in h5s if 'output.partial' in str(p)),h5s[0]);native=dict(native_fsp=desc(fsp),native_h5=desc(native_h5));GP._verify_native_outputs(native);put(out/'NATIVE_OUTPUT_INVENTORY.json',dict(fsp=native['native_fsp'],h5_files=[dict(**desc(p),bytes=p.stat().st_size) for p in h5s],job=job))
 bundle_view=out/'bundle_inventory_view';bundle_view.mkdir();bf=bundle_view/'paired.fsp';os.link(fsp,bf);(bundle_view/'paired').mkdir();os.link(native_h5,bundle_view/'paired'/native_h5.name);bi=bundle_inventory(bf,native_h5.name);put(out/'NATIVE_H5_FINITE_EH_CHECK.json',dict(status='PASS',inventory=bi,original_files_modified=False,view='read-only hardlink pairing for existing bundle_inventory, not another science identity'))
 contract_path=R/'reports/coupling/APCD_COUPLING_V21_SCIENCE_CONTRACT_CLOSEOUT_V1/SCIENCE_CONTRACT_6PS.json';pc=read(contract_path);assert I.sha256_file(contract_path)==binding['physical_contract_sha256'];fields,section=_source_fields(pc);_validate_resolved_fields(fields)
 geometry=next(x for x in pc['case_geometry_binding']['cases'] if x['case_id']==binding['case_id']);assert geometry['attempt_id']==binding['attempt_id'];proof=read(R/('reports/coupling/APCD_GPU_V2_COUPLING_TIME_DIAG2_ADMISSION_RECOVERY_V1/'+key+'_SETUP_LOAD_PROOF.json'));assert proof['candidate_fsp_sha256']==binding['source_fsp_sha256'] and proof['fresh_native_load'];assert proof['simulation_time_s']==6e-12 and proof['mesh_override_step_nm']==[5.,5.,5.] and proof['auto_shutoff_min']==1e-6
 put(out/'POSTPROCESS_CONTRACT_BINDING.json',dict(source_contract=desc(contract_path),source_section=section,fields=fields,original_case_request_sha256=binding['case_request_sha256'],original_external_execution_id=binding['external_execution_id'],projection_function='existing certified _source_fields/_validate_resolved_fields; V31 ledger supplies authority; no V2 admission or new scientific identity',setup_proof_path=str(R/('reports/coupling/APCD_GPU_V2_COUPLING_TIME_DIAG2_ADMISSION_RECOVERY_V1/'+key+'_SETUP_LOAD_PROOF.json'))))
 cfg=read(P.parent/'serial_config.json');pins=cfg['truth_toolchain'];sys.path[:0]=[str(Path(pins['postprocessor']['path']).parent),str(Path(pins['lumapi']['path']).parent)]
 post=pinned_module(pins['postprocessor']['path'],pins['postprocessor']['sha256'],'diag2_real_frozen_post');lum=pinned_module(pins['lumapi']['path'],pins['lumapi']['sha256'],'lumapi');dec=pinned_module(pins['decoder']['path'],pins['decoder']['sha256'],'diag2_real_frozen_h2');h1=pinned_module(str(R/'scripts/coupling_ml/pw_k6_stage1_32g_frozen_forward_h1_v1.py'),C.H1_EVALUATOR_SOURCE_SHA256,'diag2_real_frozen_h1')
 pcfg=dict(pw_contract=fields,case=binding['case_id'],attempt=binding['attempt_id'],task='DIAG2_REAL_'+key,run_fsp=str(fsp));sessions=[];load_path=fsp
 # Preserve all native companion H5 paths in an isolated readview when atomic FSP rename changed its basename.
 for attempt in range(2):
  session={};sessions.append(session)
  try:
   with native_session(lum.FDTD,{str(load_path):job['output_sha256']},session) as fd:
    fd.load(str(load_path));post.load_only_validate(fd,pcfg)
    raw,metrics,paths=post.postprocess(fd,pcfg,str(out))
    native_results={}
    for name in ['status','autoshutoff level','total gpu sms','total processes','total threads','simulation run time','peak memory']:
     try:native_results[name]=fd.getresult('FDTD',name)
     except Exception as e:native_results[name]=dict(unavailable=str(e)[:180])
   break
  except Exception:
   put(out/('NATIVE_SESSION_FAILURE_'+str(attempt)+'.json'),dict(session=session,error=traceback.format_exc()))
   if attempt:raise
   view=out/'native_read_view';view.mkdir();load_path=view/'output.partial.fsp';shutil.copyfile(fsp,load_path)
   for hp in h5s:
    dest=view/hp.relative_to(root);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(hp,dest)
   # If save retains the input external bundle, its original relative input/ layout is also preserved.
 put(out/'NATIVE_SESSIONS.json',sessions);put(out/'NATIVE_FDTD_RESULTS.json',native_results)
 assert all(s.get('close_called') and all(e['api'] not in ['run','save','switchtolayout','eval'] for e in s['events']) for s in sessions)
 for name in ['order_sign','reference_plane_deembedding','lossy_gan']:assert metrics[name]['status']=='PASS',(name,metrics[name])
 status=metrics.get('solver_status');arr=np.asarray(status)
 if isinstance(status,dict):
  candidates=[np.asarray(v).reshape(-1) for k,v in status.items() if k.lower()=='status'];assert candidates,'SOLVER_STATUS_UNRESOLVED';status_code=int(candidates[0][0])
 else:status_code=int(arr.reshape(-1)[0])
 assert status_code in [1,2],('SOLVER_NOT_NORMALLY_COMPLETE',status_code)
 log=stop_log(root/'input_p0.log');assert log['gpu_confirmed'],'GPU_BACKEND_NOT_PROVEN';put(out/'SOLVER_STOP_EVIDENCE.json',dict(**log,status_code=status_code,stop_reason='AUTO_SHUTOFF' if status_code==2 else 'FULL_6PS_MAXIMUM',official_status_reference='https://optics.ansys.com/hc/en-us/articles/360034382534-FDTD-solver-Simulation-Object'))
 st=h1.state_data(paths['state_npz'],paths['state_metadata'],I.sha256_file(paths['state_npz']),dec);p=h1.pscale_eh(paths['raw_fields'],paths['raw_json']);eta=np.array([[float(o['power_fraction_of_monitor_total']) for o in row] for row in metrics['orders']['post']]);absolute=p[:,None]*eta
 source_fraction=np.array([[float(o['power_fraction_of_source']) for o in row] for row in metrics['orders']['post']]);assert np.allclose(source_fraction,absolute,rtol=1e-3,atol=1e-9),'FROZEN_ORDER_POWER_MAPPING_FAIL'
 imported=C.CaseTruth(binding['case_id'],binding['attempt_id'],'TIME_CONVERGENCE_DIAGNOSTIC_ONLY',tuple(geometry['ordered_D_nm']),st['chat'],p,eta,absolute,dict(original_binding=binding,native=native,profile_id=GP.PROFILE_ID,extractor_sha256=C.H1_EVALUATOR_SOURCE_SHA256,h2_sha256=C.H2_DECODER_SHA256))
 numeric=GP._validate_609d_numeric_payload(imported);target=C.pack_model_target(imported.c_hat,p)
 labels=out/'labels_609d.npz';np.savez_compressed(labels,case_id=binding['case_id'],attempt_id=binding['attempt_id'],C_hat_real=imported.c_hat.real,C_hat_imag=imported.c_hat.imag,P_scale=p,eta=eta,absolute_order=absolute,model_target=target,wavelengths_nm=np.arange(440,461),orders=np.arange(-3,4))
 truth=out/'truth.h5'
 with h5py.File(truth,'x') as hf:
  for k,v in dict(case_id=binding['case_id'],attempt_id=binding['attempt_id'],physics_contract_sha256=binding['physical_contract_sha256'],external_execution_id=binding['external_execution_id'],source_fsp_sha256=binding['source_fsp_sha256'],native_fsp_sha256=native['native_fsp']['sha256'],native_h5_sha256=native['native_h5']['sha256'],profile_id=GP.PROFILE_ID).items():hf.attrs[k]=v
  for k,v in dict(C_hat_real=imported.c_hat.real,C_hat_imag=imported.c_hat.imag,P_scale=p,eta=eta,absolute_order=absolute,model_target=target).items():hf.create_dataset(k,data=v)
  for k,v in dict(raw_json=raw,metrics_json=metrics).items():hf.create_dataset(k,data=json.dumps(v,default=lambda x:x.tolist() if hasattr(x,'tolist') else str(x)),dtype=h5py.string_dtype('utf-8'))
  with np.load(paths['raw_fields'],allow_pickle=False) as z:
   group=hf.create_group('EH_complex')
   for name in z.files:group.create_dataset(name,data=z[name],compression='gzip',compression_opts=1)
 inv=read(R/'reports/coupling/APCD_COUPLING_ML_156G_DATASET_CLOSURE_AND_TRAINING_PROTOCOL_REVIEW_V1/DEVELOPMENT_156G_DATASET_INVENTORY.json');anchor=next(x for x in inv['cases'] if x['case_id']==geometry['anchor_case_id']);oldpin=anchor['artifacts']['label'];assert I.sha256_file(oldpin['path'])==oldpin['sha256'];old=np.load(oldpin['path'],allow_pickle=False);oc=old['C_hat_real']+1j*old['C_hat_imag'];op=old['P_scale'];oe=old['eta'];oa=old['absolute_order']
 sq=abs(imported.c_hat-oc)**2;energy=abs(oc)**2;mask=energy/energy.sum(axis=(1,2),keepdims=True)>=1e-4;phase=np.angle(imported.c_hat*oc.conj());state=np.sqrt(sq.sum(axis=(1,2))/energy.sum(axis=(1,2)));phase_rmse=np.sqrt(np.sum(energy*mask*phase**2,axis=(1,2))/np.sum(energy*mask,axis=(1,2)));routing=np.max(abs(eta-oe),axis=1);power=abs(p-op)/op;apower=np.max(abs(absolute-oa),axis=1)
 flags=dict(state_relative_L2_max=float(state.max()),routing_max_abs=float(routing.max()),absolute_order_max_abs=float(apower.max()),P_scale_max_relative=float(power.max()),phase_energy_weighted_RMSE_max_rad=float(phase_rmse.max()))
 limits=dict(state_relative_L2_max=.02,routing_max_abs=.005,absolute_order_max_abs=.005,P_scale_max_relative=.01,phase_energy_weighted_RMSE_max_rad=.05);decisions={k:flags[k]<=limits[k] for k in flags}
 rows=[]
 for i,wl in enumerate(range(440,461)):rows.append(dict(wavelength_nm=wl,eta_plus1_3ps=float(oe[i,4]),eta_plus1_6ps=float(eta[i,4]),Pplus1_3ps=float(oa[i,4]),Pplus1_6ps=float(absolute[i,4]),P_scale_3ps=float(op[i]),P_scale_6ps=float(p[i]),state_relative_L2=float(state[i]),routing_max_abs=float(routing[i]),absolute_order_max_abs=float(apower[i]),P_scale_relative=float(power[i]),phase_weighted_RMSE=float(phase_rmse[i])))
 with (out/'WAVELENGTH_3PS_6PS_COMPARISON.csv').open('w',newline='',encoding='utf-8') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 original=read(R/'reports/coupling/APCD_COUPLING_DIAG2_V3_1_BUDGET_MIGRATION_AND_AL_HANDOFF_V1/HISTORICAL_NATIVE_REEXTRACTION.json');oldref=next(x for x in original['cases'] if x['case_id']==geometry['anchor_case_id']);oldrecord=read(oldref['readonly_record']);rawdiff={}
 with np.load(oldrecord['raw_npz']['path'],allow_pickle=False) as zo,np.load(paths['raw_fields'],allow_pickle=False) as zn:
  for name in zn.files:
   if name not in zo.files or zn[name].shape!=zo[name].shape:rawdiff[name]=dict(status='GRID_OR_SHAPE_MISMATCH');continue
   a,b=zo[name],zn[name]
   if np.iscomplexobj(a):
    denom=np.linalg.norm(a);rawdiff[name]=dict(relative_L2=float(np.linalg.norm(b-a)/denom) if denom>0 else None,max_abs_delta=float(np.max(abs(b-a))),max_amplitude_delta=float(np.max(abs(abs(b)-abs(a)))))
   else:rawdiff[name]=dict(array_equal=bool(np.array_equal(a,b)),max_abs_delta=float(np.max(abs(b-a))))
 comparison=dict(anchor_case_id=geometry['anchor_case_id'],old_label=oldpin,new_label=desc(labels),metrics=flags,frozen_thresholds=limits,frozen_threshold_source=str(R/'reports/coupling/APCD_COUPLING_ML_V3_DOE56_OVERNIGHT_PRODUCTION_DESIGN_V1/V3_NUMERICAL_VALIDATION_PLAN.md'),flags=decisions,all_numerical_flags_pass=all(decisions.values()),phase_mask_power_fraction=1e-4,no_oracle_phase_alignment=True,label609_max_abs_delta=float(np.max(abs(target-C.pack_model_target(oc,op)))),label609_RMSE=float(np.sqrt(np.mean((target-C.pack_model_target(oc,op))**2))),raw_complex_field_comparison=rawdiff,old_stop=stop_log(Path(oldref['native_pair']['fsp']['path']).parent/'run_p0.log'),new_stop=log,energy_closure=metrics['max_energy_closure'],energy_caveat='Frozen R+T+A closure uses A=1-R-T; algebraic identity is not independent volumetric absorption validation')
 put(out/'TIME_CONVERGENCE_COMPARISON.json',comparison)
 receipt=dict(schema='APCD_COUPLING_V31_REAL_SCIENCE_RECEIPT_V1',science_owner=GP.SCIENCE_OWNER_ID,case_id=binding['case_id'],attempt_id=binding['attempt_id'],external_execution_id=binding['external_execution_id'],original_case_request_sha256=binding['case_request_sha256'],physics_contract_sha256=binding['physical_contract_sha256'],native=native,source_fsp_sha256=binding['source_fsp_sha256'],solver_entry=recon['cases'][index]['entry'],real_gpu_confirmed=True,fresh_load_verified=True,monitors_valid=True,truth_valid=True,labels_valid=True,label_validation_profile=GP.PROFILE_ID,numeric=numeric,labels=desc(labels),truth_h5=desc(truth),state_npz=desc(paths['state_npz']),raw_npz=desc(paths['raw_fields']),solver_status_code=status_code,stop_reason='AUTO_SHUTOFF' if status_code==2 else 'FULL_6PS_MAXIMUM',normal_termination_status_reference='https://optics.ansys.com/hc/en-us/articles/360034382534-FDTD-solver-Simulation-Object',label_receipt_scope='Current V31 ledger binding + unmodified frozen H1 state_data/pscale_eh, H2 and coupling_609d_v1 numeric validator. No V2 Admission created, no frozen importer source modified.',numerical_comparison_flags=decisions,scientific_acceptance='PASS' if all(decisions.values()) else 'HOLD_NUMERICAL_REVIEW',A2_allowed=index==0 and all(decisions.values()),no_replay=True)
 put(out/'SCIENCE_RECEIPT.json',receipt);ledger=read(B/'DIAG2_SCIENCE_LEDGER.json');ledger['cases'][index].update(truth_valid=True,labels_valid=True,scientific_acceptance=receipt['scientific_acceptance'],science_receipt=str(out/'SCIENCE_RECEIPT.json'),status='SCIENTIFIC_ACCEPTANCE_PASS' if all(decisions.values()) else 'HOLD_NUMERICAL_REVIEW');ledger['entered_total']=reconcile(ledger)['entered_total'];atom(B/'DIAG2_SCIENCE_LEDGER.json',ledger)
 put(D/(key+'_SCIENTIFIC_ACCEPTANCE.json'),receipt);print(key,receipt['scientific_acceptance'],json.dumps(flags),flush=True)
case_index=int(os.environ.get('APCD_DIAG2_POSTPROCESS_CASE_INDEX','0'))
try:execute_acceptance(case_index)
except Exception:
 put(D/(('A'+str(case_index+1))+'_SCIENTIFIC_ACCEPTANCE_HOLD.json'),dict(error=traceback.format_exc(),A2='HOLD',solver_replay_allowed=False));raise
