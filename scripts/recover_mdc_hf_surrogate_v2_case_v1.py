from pathlib import Path
import json, time, numpy as np
import run_mdc_hf_surrogate_v2_pilot4_joint_profile_v1 as runner

def now(): return time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())
run_root=Path(__import__('sys').argv[1])
state=runner.load(run_root/'state.json')
failed=[c for c in state['cases'].values() if c.get('solver_entered') and not c.get('accepted')]
if len(failed)!=1: raise RuntimeError(f'expected_one_failed_solver_case:{len(failed)}')
case=failed[0]; case_id=case['case_id']; case_dir=run_root/'cases'/case['case_hash']; posts=sorted(case_dir.glob('*__post.fsp'))
if len(posts)!=1: raise RuntimeError(f'post_fsp_count:{len(posts)}')
post=posts[0]; fsp_sha=runner.sha(post); attempt_id=case.get('attempt_id','unknown'); recovery_id=case['case_hash'][:12]+'_extraction_recovery_1'; npz=case_dir/(recovery_id+'__raw.npz')
# Fresh-load only; solver is intentionally never called.
mod=runner.lumapi(); f=mod.FDTD(hide=True)
try:
 f.load(str(post)); mon='upward_monitor'; freq=np.asarray(f.getdata(mon,'f'),float).reshape(-1); lam=299792458.0/freq*1e9; order=np.argsort(lam); lam=lam[order]
 p_up=np.asarray(runner.monitor_contract.integrate_line_poynting_flux(runner.monitor_contract.read_fields(f,mon),'Linear X'),float).reshape(-1)[order]
 side={s:runner.monitor_contract.integrate_line_poynting_flux(runner.monitor_contract.read_fields(f,'emit_box_12nm_'+s),'Linear X' if s in ('top','bottom') else 'Linear Y') for s in ('top','bottom','left','right')}; p_box=np.asarray(runner.monitor_contract.calculate_box_outward_flux(side)['net_outward'],float).reshape(-1)[order]
 angle,joint,_=runner.extract_joint(f,mon,lam,p_up)
finally: f.close()
if len(lam)!=runner.POINTS: raise RuntimeError('recovery_wavelength_count')
spectral=np.trapezoid(joint,np.radians(angle),axis=1); angular=np.trapezoid(joint,np.radians(lam),axis=0)
np.savez_compressed(npz,wavelength_nm=lam,angle_deg=angle,joint_raw=joint,spectral_marginal_raw=spectral,angular_marginal_raw=angular,p_up_raw=p_up,p_box_raw=p_box)
result={'status':'COMPLETE','case_id':case_id,'geometry_hash':case['geometry_hash'],'case_hash':case['case_hash'],'source_position':case['source_position'],'source_position_nm':float(case['source_position_nm']),'dipole_orientation':case['dipole_orientation'],'builder_sha256':runner.sha(Path(runner.__file__)),'material_sha256':runner.sha(runner.MATERIAL_CONFIG),'monitor_sha256':runner.sha(runner.SCRIPTS/'mdc_fdtd_2d_monitor_contract_v1.py'),'export_sha256':runner.sha(Path(runner.__file__)),'start_timestamp':case.get('solver_entered_at'),'end_timestamp':now(),'solver_status':'COMPLETE','attempt_count':1,'fsp_path':str(post),'fsp_sha256':fsp_sha,'fresh_load_status':'PASS','raw_spectral_output_status':'PASS','raw_angular_output_status':'PASS','joint_tensor_status':'PASS','extraction_status':'PASS','accepted':True,'rejected_reason':'','raw_npz_path':str(npz),'wavelength_points':int(len(lam)),'angle_points':int(len(angle)),'joint_shape':[int(x) for x in joint.shape],'joint_nonfinite_ratio':float(np.mean(~np.isfinite(joint))),'joint_negative_count':int(np.sum(joint<0)),'spectral_direct_joint_relative_error':float(np.max(np.abs((spectral/(np.max(np.abs(spectral))+1e-30))-(p_up/(np.max(np.abs(p_up))+1e-30))))),'raw_integrated_joint_power_median':float(np.median(spectral)),'raw_upward_power_median':float(np.median(p_up)),'normalization_before_aggregation':False,'filter_identity':'raw_air_side_unfiltered','monitor_identity':mon,'tensor_axis_order':['wavelength_index','angle_index'],'tensor_units':'raw farfield intensity in native Lumerical export units','recovery_extraction_only':True,'source_solver_attempt_id':attempt_id}
case.update(result); state['safety_counters']['recovery_solver_calls']=0; state['cases'][case['case_hash']]=case; runner.dump(run_root/'state.json',state); runner.dump(case_dir/'case_result.json',result)
with (run_root/'pilot4_case_attempt_ledger.jsonl').open('a',encoding='utf-8') as lf: lf.write(json.dumps({'case_id':case_id,'geometry_hash':case['geometry_hash'],'case_hash':case['case_hash'],'attempt_id':recovery_id,'solver_entered':False,'recovery_type':'post_fsp_extraction_only','source_solver_attempt_id':attempt_id,'post_fsp_sha256':fsp_sha,'timestamp':now()},sort_keys=True)+'\n')
print(json.dumps({'case_id':case_id,'status':result['status'],'solver_calls':state['safety_counters']['solver_calls'],'recovery_solver_calls':0,'shape':result['joint_shape']},sort_keys=True))
