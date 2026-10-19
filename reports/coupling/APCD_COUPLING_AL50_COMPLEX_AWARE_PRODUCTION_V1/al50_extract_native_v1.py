"""AL16 offline native-output extraction; never executes a solver or modifies old ledger."""
from pathlib import Path
import argparse,json,sys,sqlite3,os,hashlib,re
import numpy as np,h5py
R=Path(r'D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1')
P=Path(r'D:\apcd_runtime\gpu_platform_v2_serial_production_v1\minimal_runner_v3')
D=R/'reports/coupling/APCD_COUPLING_AL50_COMPLEX_AWARE_PRODUCTION_V1'
G=Path(r'D:\project\worktrees\blue_apcd_gpu_v2_serial_production_v1')
sys.path[:0]=[str(R/'scripts/coupling_ml'),str(R/'scripts'),str(G/'platform_v2')]
from k6_v2_pipeline import ingest as I,contracts as C,generic_profile as GP
from apcd_gpu_v2.native_readonly import native_session,pinned_module
from apcd_gpu_v2.artifacts import bundle_inventory
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
def put(p,v):Path(p).write_text(json.dumps(v,indent=2,ensure_ascii=False,allow_nan=False,default=lambda x:x.tolist() if hasattr(x,'tolist') else str(x)),encoding='utf-8')
def extract(case_id):
 package=read(D/'AL50_COMPLEX_PRODUCTION_MANIFEST.json');case=next(c for c in package['cases'] if c['case_id']==case_id)
 con=sqlite3.connect((P/'data/runner_v31.db').as_uri()+'?mode=ro',uri=True);con.row_factory=sqlite3.Row
 jobs=[dict(r) for r in con.execute('SELECT * FROM jobs WHERE external_execution_id=?',(case['external_execution_id'],))]
 entries=[dict(r) for r in con.execute('SELECT * FROM solver_entries WHERE external_execution_id=?',(case['external_execution_id'],))];con.close()
 assert len(jobs)==len(entries)==1,'One canonical REAL job/entry required; extraction does not authorize execution'
 job=jobs[0];entry=entries[0]
 assert job['status']=='COMPLETED' and job['execution_mode']=='REAL' and entry['execution_mode']=='REAL'
 for k in ['case_id','attempt_id','external_execution_id','physical_contract_sha256']:
  assert job[k]==case[k] and entry[k]==case[k],k
 assert job['input_fsp_sha256']==entry['pre_fsp_sha256']==case['source_fsp_sha256']
 fsp=Path(job['output_fsp_path']);assert I.sha256_file(fsp)==job['output_sha256']
 out=Path(case['science_output_directory']);out.mkdir(parents=True,exist_ok=False)
 contract=read(D/'FAST_FROZEN_PHYSICS_CONTRACT.json');assert I._canon(contract['contract'])==case['physical_contract_sha256']
 pins=read(P.parent/'serial_config.json')['truth_toolchain'];sys.path[:0]=[str(Path(pins['postprocessor']['path']).parent),str(Path(pins['lumapi']['path']).parent)]
 post=pinned_module(pins['postprocessor']['path'],pins['postprocessor']['sha256'],'al16_frozen_post');lum=pinned_module(pins['lumapi']['path'],pins['lumapi']['sha256'],'lumapi');dec=pinned_module(pins['decoder']['path'],pins['decoder']['sha256'],'al16_h2');h1=pinned_module(str(R/'scripts/coupling_ml/pw_k6_stage1_32g_frozen_forward_h1_v1.py'),C.H1_EVALUATOR_SOURCE_SHA256,'al16_h1')
 cfg=dict(pw_contract=contract['contract'],case=case_id,attempt=case['attempt_id'],task='AL50_COMPLEX_R03',run_fsp=str(fsp));session={}
 with native_session(lum.FDTD,{str(fsp):job['output_sha256']},session) as fd:
  fd.load(str(fsp));post.load_only_validate(fd,cfg);raw,metrics,paths=post.postprocess(fd,cfg,str(out));status=fd.getresult('FDTD','status')
 put(out/'NATIVE_SESSION.json',session);assert session['close_called'] and all(e['api'] not in ['run','save','switchtolayout','eval'] for e in session['events'])
 code=int(np.asarray(status).reshape(-1)[0]);assert code in [1,2],('native status',code)
 logpath=fsp.parent/'input_p0.log';logtext=logpath.read_text(encoding='utf-8',errors='replace')
 assert 'Detected GPU 0: NVIDIA GeForce RTX 3080' in logtext,'Actual RTX3080 GPU backend not proven'
 progress=re.findall(r'([\d.eE+-]+)% complete\. Elapsed simulation time: ([\d.eE+-]+) secs\..*?Auto Shutoff: ([\d.eE+-]+)',logtext)
 stop=dict(status_code=code,stop_reason='AUTO_SHUTOFF' if code==2 else 'MAXIMUM_3PS',source_log=str(logpath),gpu='RTX3080',progress=[dict(percent=float(a),physical_time_s=float(b),auto_shutoff=float(c)) for a,b,c in progress],maximum_time_is_not_convergence=True)
 put(out/'SOLVER_STOP_EVIDENCE.json',stop)
 for name in ['order_sign','reference_plane_deembedding','lossy_gan']:assert metrics[name]['status']=='PASS'
 st=h1.state_data(paths['state_npz'],paths['state_metadata'],I.sha256_file(paths['state_npz']),dec);p=h1.pscale_eh(paths['raw_fields'],paths['raw_json'])
 eta=np.array([[float(o['power_fraction_of_monitor_total']) for o in row] for row in metrics['orders']['post']]);absolute=p[:,None]*eta
 source_fraction=np.array([[float(o['power_fraction_of_source']) for o in row] for row in metrics['orders']['post']]);assert np.allclose(source_fraction,absolute,rtol=1e-3,atol=1e-9)
 imported=C.CaseTruth(case_id,case['attempt_id'],'AL50_FAST_DEVELOPMENT',tuple(case['ordered_D_nm']),st['chat'],p,eta,absolute,dict(profile_id=GP.PROFILE_ID,numerical_grade='ML_TRAINING_GRADE'))
 checks=GP._validate_609d_numeric_payload(imported);target=C.pack_model_target(imported.c_hat,p)
 assert st['eta_modal'].shape==(21,7) and np.isfinite(st['eta_modal']).all()
 arrays=dict(eta_H2=st['eta_modal'],P_plus1_H2=p*st['eta_modal'][:,4],C_hat_real=imported.c_hat.real,C_hat_imag=imported.c_hat.imag,P_scale=p,eta=eta,absolute_order=absolute,model_target=target,wavelengths_nm=np.arange(440,461),orders=np.arange(-3,4))
 np.savez_compressed(out/'labels_609d.npz',case_id=case_id,attempt_id=case['attempt_id'],**arrays)
 with h5py.File(out/'truth.h5','x') as hf:
  for k in ['case_id','attempt_id','external_execution_id','source_fsp_sha256','physical_contract_sha256','numerical_grade']:hf.attrs[k]=case[k]
  for k,v in arrays.items():hf.create_dataset(k,data=v)
  with np.load(paths['raw_fields'],allow_pickle=False) as z:
   eh=hf.create_group('EH_complex')
   for k in z.files:
    a=z[k];eh.create_dataset(k,data=a,compression='gzip' if a.ndim>0 else None)
  hf.create_dataset('metrics_json',data=json.dumps(metrics,default=lambda x:x.tolist() if hasattr(x,'tolist') else str(x)),dtype=h5py.string_dtype('utf-8'))
 # Native H5s generated by runner-owned save remain immutable; inventory each path.
 native_h5s=[x for x in fsp.parent.rglob('*.h5') if x.stat().st_size>0];assert native_h5s,'native H5 missing'
 view=out/'native_bundle_readview';view.mkdir();os.link(fsp,view/'paired.fsp');(view/'paired').mkdir();os.link(native_h5s[0],view/'paired'/native_h5s[0].name)
 inventory=bundle_inventory(view/'paired.fsp',native_h5s[0].name);put(out/'NATIVE_H5_FINITE_EH_CHECK.json',inventory)
 with (out/'TARGET_21_POINTS.csv').open('w',encoding='utf-8') as f:
  f.write('wavelength_nm,eta_plus1_native,eta_plus1_H2,P_scale,P_plus1_H2,P_plus1_native\n')
  # H2 power, not an independently redefined target.
  modal=st['eta_modal']
  for i in range(21):f.write(f'{440+i},{eta[i,4]},{modal[i,4]},{p[i]},{p[i]*modal[i,4]},{absolute[i,4]}\n')
 receipt=dict(case_id=case_id,attempt_id=case['attempt_id'],external_execution_id=case['external_execution_id'],runner_job_id=job['id'],entry_id=entry['id'],truth_valid='PASS',labels_valid='PASS',profile=GP.PROFILE_ID,numerical_grade='ML_TRAINING_GRADE',strict_convergence='NOT_CERTIFIED',solver_status=code,labels_numeric_checks=checks,native_fsp=dict(path=str(fsp),sha256=job['output_sha256']),native_h5=[dict(path=str(x),sha256=I.sha256_file(x)) for x in native_h5s],labels_sha256=I.sha256_file(out/'labels_609d.npz'),truth_h5_sha256=I.sha256_file(out/'truth.h5'),source_setup=case['source_fsp_sha256'],model_target_609d=True,entry_consumed_even_on_failure=True)
 put(out/'SCIENCE_RECEIPT.json',receipt)
 return receipt
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--case',required=True);args=p.parse_args();print(json.dumps(extract(args.case),indent=2))
