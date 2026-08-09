from __future__ import annotations
import argparse,csv,hashlib,json,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2]; SRC=ROOT/'src'; sys.path.insert(0,str(SRC)); sys.path.insert(0,str(ROOT/'scripts/coupling'))
from apcd_coupling.result_schema import validate_result
from extract_joint_stage_a_orders import arr,order_rows

def sha(p):
 h=hashlib.sha256();
 with p.open('rb') as f:
  for block in iter(lambda:f.read(1024*1024),b''): h.update(block)
 return h.hexdigest()
def read(p): return json.loads(p.read_text(encoding='utf-8'))
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--output-dir',type=Path,required=True); ap.add_argument('--fixture-registry',type=Path,required=True); args=ap.parse_args(); out=args.output_dir.resolve(); setup=read(out/'setup_manifest.json'); case=read(out/'joint_case.json'); runtime=read(out/'runtime/attempt_001/run_state.json'); ledger=read(out/'runtime/attempt_001/entered_ledger.json');
 if not runtime.get('solver_completed'): raise RuntimeError('solver_completed=false')
 post=Path(runtime['post_fsp_path']);
 if sha(post)!=runtime['post_fsp_sha256']: raise RuntimeError('post-FSP hash mismatch')
 import lumapi
 fdtd=lumapi.FDTD(str(post),hide=True)
 try:
  tr=fdtd.getresult('transmission_monitor','T'); rr=fdtd.getresult('reflection_monitor','T'); wavelengths=arr(tr['lambda'])*1e9; T=float(np.real(arr(tr['T']))[0]); R=float(abs(np.real(arr(rr['T']))[0]));
  if len(wavelengths)!=1 or abs(float(wavelengths[0])-450)>1e-6: raise RuntimeError('unexpected wavelength')
  transmitted=order_rows(fdtd,'transmission_monitor',1,T,'+z'); reflected=order_rows(fdtd,'reflection_monitor',1,R,'-z')
 finally: fdtd.close()
 ts=sum(x['power_fraction_of_source'] for x in transmitted); rs=sum(x['power_fraction_of_source'] for x in reflected); bt={x['m']:x for x in transmitted}; group=case['control_group']; applicable=bool(case['np_candidate'].get('pillars'))
 closure=1-R-T; t_res=ts-T; r_res=rs-R
 ref_cfg=read(args.fixture_registry)['standalone_reference']; ref_path=Path(ref_cfg['path']); ref=read(ref_path)['at_450_nm']; vals={'eta_plus1':float(ref['plus1_absolute_efficiency']),'eta_zero':float(ref['zero_absolute_efficiency']),'eta_minus1':float(ref['minus1_absolute_efficiency']),'directionality':float(ref['directionality'])}
 if applicable:
  for order in (1,0,-1):
   if order not in bt: raise RuntimeError(f'missing transmitted order {order}')
  plus,zero,minus=bt[1],bt[0],bt[-1]; eta_plus=float(plus['power_fraction_of_source']); eta_zero=float(zero['power_fraction_of_source']); eta_minus=float(minus['power_fraction_of_source']); direction=float(eta_plus/(eta_plus+eta_minus)); theta=float(plus['theta_out_deg']); delta={'eta_plus1':eta_plus-vals['eta_plus1'],'eta_zero':eta_zero-vals['eta_zero'],'eta_minus1':eta_minus-vals['eta_minus1'],'directionality':direction-vals['directionality']}; sign={'m_plus_1':1,'m_plus_1_u_x':plus['u_x'],'m_plus_1_physical_kx_sign':plus['physical_kx_sign'],'contract':'m=+1 equals physical +x','pass':plus['m']==1 and plus['u_x']>0}; na={}
 else:
  eta_plus=eta_zero=eta_minus=theta=direction=None; delta=None; sign={'status':'NOT_APPLICABLE','reason':'B0/B1 have no NP grating geometry; nonzero orders are reported only as numerical leakage.','pass':True}; na={'eta_plus1':'NOT_APPLICABLE: no NP grating geometry','eta_zero':'NOT_APPLICABLE: no phase-gradient NP order metric','eta_minus1':'NOT_APPLICABLE: no NP grating geometry','theta_out_plus1_deg':'NOT_APPLICABLE: no physical +1 target order','directionality':'NOT_APPLICABLE: no physical +1/-1 target pair'}
 result={'schema_version':'joint_stage_a_control_result_v1','case_id':case['case_id'],'control_group':group,'interface_id':case['interface_candidate'].get('candidate_id'),'mdc_candidate_id':case['mdc_candidate']['candidate_id'],'mdc_geometry_hash':case['mdc_geometry_hash'],'np_candidate_id':case['np_candidate']['candidate_id'],'np_geometry_hash':case['np_geometry_hash'],'joint_stack_id':'APCD_MDC_NP_COUPLING_V1_STAGE_A_CONTROL_GROUPS','joint_geometry_hash':case['joint_geometry_hash'],'spacer_nm':case['spacer_nm'],'total_sio2_separation_nm':case['coordinates']['total_sio2_separation_nm'],'wavelength_nm':case['wavelength_nm'],'polarization':case['polarization'],'kx_over_k0':case['kx_over_k0'],'R_total':R,'T_total':T,'loss_or_residual':closure,'eta_t_orders':transmitted,'eta_r_orders':reflected,'eta_plus1':eta_plus,'eta_zero':eta_zero,'eta_minus1':eta_minus,'theta_out_plus1_deg':theta,'theta_plus1_deg':theta,'directionality':direction,'not_applicable':na,'power_closure':{'R_total_plus_T_total':R+T,'residual_1_minus_R_minus_T':closure,'estimated_native_material_absorption':closure,'formal_R_plus_T_tolerance':0.02,'formal_R_plus_T_pass':abs(closure)<=0.02,'absorption_accounted':0<=closure<=1,'pass':0<=closure<=1,'interpretation':'Native-M1 GaN is lossy; residual is reported and not forced to zero.'},'order_closure':{'transmitted_order_sum':ts,'reflected_order_sum':rs,'transmitted_residual':t_res,'reflected_residual':r_res,'tolerance':1e-8,'pass':abs(t_res)<=1e-8 and abs(r_res)<=1e-8},'source_contract_id':case['source_contract_id'],'material_contract_id':case['material_contract_id'],'coordinate_contract_id':case['coordinate_contract_id'],'mesh_contract_id':'RUN3A_NATIVE_M1_FDTD_SETTINGS_INHERITED_V1','pre_fsp_path':str(setup['pre_fsp_path']),'pre_fsp_sha256':ledger.get('pre_fsp_entry_sha256',ledger.get('pre_fsp_sha256')),'pre_fsp_current_sha256':runtime.get('pre_fsp_current_sha256'),'pre_fsp_post_entry_mutation':runtime.get('pre_fsp_post_entry_mutation'),'post_fsp_path':str(post),'post_fsp_sha256':runtime['post_fsp_sha256'],'solver_entered':True,'solver_completed':True,'source_commits':setup['source_commits'],'coupling_commit':setup['coupling_commit'],'raw_monitor_extraction_reference':{'post_fsp_path':str(post),'readonly_session':True,'run_called':False,'save_called':False},'standalone_reference':{'path':str(ref_path),'source_commit':ref_cfg['source_commit'],'path_sha256':sha(ref_path),'values':vals},'standalone_delta':delta,'sign_audit':sign}
 validate_result(result); resdir=out/'results'; resdir.mkdir(exist_ok=True); (resdir/'result.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8'); (resdir/'transmitted_orders.json').write_text(json.dumps(transmitted,indent=2,ensure_ascii=False)+'\n',encoding='utf-8'); (resdir/'reflected_orders.json').write_text(json.dumps(reflected,indent=2,ensure_ascii=False)+'\n',encoding='utf-8'); (resdir/'standalone_comparison.json').write_text(json.dumps({'reference':result['standalone_reference'],'delta':delta},indent=2,ensure_ascii=False)+'\n',encoding='utf-8'); rows=[{**x,'channel':'transmitted'} for x in transmitted]+[{**x,'channel':'reflected'} for x in reflected];
 with (resdir/'order_spectrum.csv').open('w',newline='',encoding='utf-8') as f: w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
 manifest={'schema_version':'stage_a_control_extraction_manifest_v1','case_id':case['case_id'],'control_group':group,'post_fsp_path':str(post),'post_fsp_sha256':runtime['post_fsp_sha256'],'result_path':str(resdir/'result.json'),'readonly_session':True,'run_called':False,'save_called':False,'order_sign_pass':result['sign_audit']['pass'],'power_closure_pass':result['power_closure']['pass'],'order_closure_pass':result['order_closure']['pass']}; (resdir/'extraction_manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n',encoding='utf-8'); print(json.dumps({'case_id':case['case_id'],'control_group':group,'R_total':R,'T_total':T,'eta_plus1':eta_plus,'eta_zero':eta_zero,'eta_minus1':eta_minus,'directionality':direction,'order_closure':result['order_closure']},indent=2))
if __name__=='__main__': main()
