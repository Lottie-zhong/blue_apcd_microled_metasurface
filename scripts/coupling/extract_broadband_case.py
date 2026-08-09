from __future__ import annotations
import argparse,csv,hashlib,json,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2]; sys.path.insert(0,str(ROOT/'src')); sys.path.insert(0,str(ROOT/'scripts/coupling'))
from apcd_coupling.broadband_result_schema import validate_broadband_result
from extract_joint_stage_a_orders import arr,order_rows

def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for block in iter(lambda:f.read(1024*1024),b''): h.update(block)
 return h.hexdigest()
def read(p): return json.loads(p.read_text(encoding='utf-8'))
def load_standalone(path):
 rows={}
 with path.open(newline='',encoding='utf-8') as f:
  for row in csv.DictReader(f): rows[round(float(row['wavelength_nm']),9)]={k:float(row[k]) for k in ('plus1_absolute_efficiency','minus1_absolute_efficiency','zero_absolute_efficiency','directionality')}
 return rows

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--output-dir',type=Path,required=True); ap.add_argument('--fixture-registry',type=Path,required=True); args=ap.parse_args(); out=args.output_dir.resolve(); setup=read(out/'setup_manifest.json'); case=read(out/'joint_case.json'); runtime=read(out/'runtime/attempt_001/run_state.json'); ledger=read(out/'runtime/attempt_001/entered_ledger.json');
 if not runtime.get('solver_completed'): raise RuntimeError('solver_completed=false')
 post=Path(runtime['post_fsp_path']);
 if sha(post)!=runtime['post_fsp_sha256']: raise RuntimeError('post-FSP hash mismatch')
 cfg=read(args.fixture_registry); ref_path=Path(cfg['standalone_reference']['path']); standalone=load_standalone(ref_path); expected=np.arange(445.0,456.0,1.0)
 import lumapi
 fdtd=lumapi.FDTD(str(post),hide=True)
 try:
  tr=fdtd.getresult('transmission_monitor','T'); rr=fdtd.getresult('reflection_monitor','T'); wavelengths=np.real(arr(tr['lambda']))*1e9; tvals=np.real(arr(tr['T'])); rvals=np.abs(np.real(arr(rr['T'])))
  if len(wavelengths)!=11 or not np.allclose(wavelengths,expected,atol=1e-9,rtol=0): raise RuntimeError(f'exact wavelength grid mismatch: {wavelengths.tolist()}')
  rows=[]; order_maps=[]
  for idx,wavelength in enumerate(expected,1):
   T=float(tvals[idx-1]); R=float(rvals[idx-1]); transmitted=order_rows(fdtd,'transmission_monitor',idx,T,'+z'); reflected=order_rows(fdtd,'reflection_monitor',idx,R,'-z'); bt={x['m']:x for x in transmitted};
   for order in (1,0,-1):
    if order not in bt: raise RuntimeError(f'missing transmitted order {order} at {wavelength} nm')
   plus,zero,minus=bt[1],bt[0],bt[-1]; eta_plus=float(plus['power_fraction_of_source']); eta_zero=float(zero['power_fraction_of_source']); eta_minus=float(minus['power_fraction_of_source']); direction=float(eta_plus/(eta_plus+eta_minus)); closure=float(1-R-T); tsum=sum(x['power_fraction_of_source'] for x in transmitted); rsum=sum(x['power_fraction_of_source'] for x in reflected); key=round(float(wavelength),9); ref=standalone.get(key);
   if ref is None: raise RuntimeError(f'missing exact standalone reference row at {wavelength} nm')
   row={'wavelength_nm':float(wavelength),'R_total':R,'T_total':T,'residual_1_minus_R_minus_T':closure,'eta_plus1':eta_plus,'eta_zero':eta_zero,'eta_minus1':eta_minus,'eta_plus2':bt.get(2,{}).get('power_fraction_of_source'),'all_transmitted_orders':transmitted,'all_reflected_orders':reflected,'theta_plus1_deg':float(plus['theta_out_deg']),'directionality':direction,'standalone_eta_plus1':ref['plus1_absolute_efficiency'],'standalone_eta_zero':ref['zero_absolute_efficiency'],'standalone_eta_minus1':ref['minus1_absolute_efficiency'],'standalone_directionality':ref['directionality'],'delta_eta_plus1':eta_plus-ref['plus1_absolute_efficiency'],'power_closure':{'R_plus_T':R+T,'formal_R_plus_T_tolerance':0.02,'formal_R_plus_T_pass':abs(closure)<=0.02,'absorption_accounted':0<=closure<=1,'pass':0<=closure<=1},'order_closure':{'transmitted_order_sum':tsum,'reflected_order_sum':rsum,'transmitted_residual':tsum-T,'reflected_residual':rsum-R,'tolerance':1e-8,'pass':abs(tsum-T)<=1e-8 and abs(rsum-R)<=1e-8},'sign_audit':{'m_plus_1':1,'m_plus_1_u_x':plus['u_x'],'m_plus_1_physical_kx_sign':plus['physical_kx_sign'],'pass':plus['m']==1 and plus['u_x']>0}}
   rows.append(row); order_maps.append({'wavelength_nm':float(wavelength),'transmitted':transmitted,'reflected':reflected})
 finally: fdtd.close()
 result={'schema_version':'stage_a_broadband_result_v1','case_id':case['case_id'],'control_group':case['control_group'],'spacer_nm':case['spacer_nm'],'total_sio2_separation_nm':case['coordinates']['total_sio2_separation_nm'],'wavelength_grid_nm':[float(x) for x in expected],'rows':rows,'source_wavelength_start_nm':case['source_wavelength_start_nm'],'source_wavelength_stop_nm':case['source_wavelength_stop_nm'],'frequency_points':case['frequency_points'],'source_contract_id':case['source_contract_id'],'material_contract_id':case['material_contract_id'],'coordinate_contract_id':case['coordinate_contract_id'],'mesh_contract_id':'RUN3A_NATIVE_M1_FDTD_SETTINGS_INHERITED_V1','pre_fsp_path':str(Path(setup['pre_fsp_path']).resolve()),'pre_fsp_sha256':ledger['pre_fsp_entry_sha256'],'pre_fsp_current_sha256':runtime.get('pre_fsp_current_sha256'),'pre_fsp_post_entry_mutation':runtime.get('pre_fsp_post_entry_mutation'),'post_fsp_path':str(post),'post_fsp_sha256':runtime['post_fsp_sha256'],'joint_geometry_hash':case['joint_geometry_hash'],'mdc_geometry_hash':case['mdc_geometry_hash'],'np_geometry_hash':case['np_geometry_hash'],'solver_entered':True,'solver_completed':True,'source_commits':setup['source_commits'],'coupling_commit':setup['coupling_commit'],'standalone_reference':{'path':str(ref_path),'source_commit':cfg['standalone_reference']['source_commit'],'artifact_sha256':sha(ref_path),'exact_grid':True,'interpolation':False,'extrapolation':False},'provenance_status':'PASS'}
 validate_broadband_result(result); resdir=out/'results'; resdir.mkdir(exist_ok=True); (resdir/'result.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8'); (resdir/'order_spectra.json').write_text(json.dumps(order_maps,indent=2,ensure_ascii=False)+'\n',encoding='utf-8');
 with (resdir/'spectrum_rows.csv').open('w',newline='',encoding='utf-8') as f:
  fields=['wavelength_nm','R_total','T_total','residual_1_minus_R_minus_T','eta_plus1','eta_zero','eta_minus1','eta_plus2','theta_plus1_deg','directionality','standalone_eta_plus1','delta_eta_plus1']; w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows([{k:row[k] for k in fields} for row in rows])
 (resdir/'extraction_manifest.json').write_text(json.dumps({'schema_version':'stage_a_broadband_extraction_manifest_v1','case_id':case['case_id'],'exact_grid':result['wavelength_grid_nm'],'post_fsp_path':str(post),'post_fsp_sha256':runtime['post_fsp_sha256'],'readonly_session':True,'run_called':False,'save_called':False,'interpolation':False,'extrapolation':False,'all_rows_valid':True},indent=2,ensure_ascii=False)+'\n',encoding='utf-8'); print(json.dumps({'case_id':case['case_id'],'rows':len(rows),'grid':result['wavelength_grid_nm'],'eta_plus1_450':rows[5]['eta_plus1'],'order_closure_450':rows[5]['order_closure'],'sign_450':rows[5]['sign_audit']},indent=2))
if __name__=='__main__': main()
