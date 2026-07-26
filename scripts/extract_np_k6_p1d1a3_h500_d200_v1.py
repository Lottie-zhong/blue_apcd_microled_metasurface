"""D200 read-only recovery plus actual-FSP spectral availability audit."""
from __future__ import annotations
import argparse, hashlib, json, math, sys
from pathlib import Path
from extract_np_k6_p1d1a0_h500_d110_v1 import ROOT, finite, sha, write

TARGET=list(range(445,456))
def wrap(x):
    v=(x+180)%360-180
    return v+360 if v<=-180 else v
def axis_from(result):
    for k in ('lambda','wavelength'):
        if k in result:return [float(x)*1e9 for x in result[k].reshape(-1)]
    if 'f' in result:return [299792458/float(x)*1e9 for x in result['f'].reshape(-1)]
    return []
def audit_case(lumapi,path):
    before=sha(path); f=lumapi.FDTD(hide=True)
    try:
        f.load(str(path)); axes={}
        for name in ('T_fields','R_fields'):
            try: axes[name]=axis_from(f.getresult(name,'E'))
            except Exception: axes[name]=[]
    finally:f.close()
    after=sha(path)
    merged=axes['T_fields'] or axes['R_fields']; rounded=[round(x) for x in merged]
    if before!=after:raise RuntimeError(f'read-only FSP changed: {path}')
    if all(x in rounded for x in TARGET) and len(rounded)>=11:category='full_11point_coverage'
    elif len(rounded)<=1:category='center_only'
    elif merged:category='partial_sparse_coverage'
    else:category='monitor_spectral_data_missing'
    return {'path':str(path),'fingerprint_before':before,'fingerprint_after':after,'monitor_wavelength_axis_nm':axes,'wavelength_axis_nm':merged,'frequency_point_count':len(merged),'minimum_wavelength_nm':min(merged) if merged else None,'maximum_wavelength_nm':max(merged) if merged else None,'exact_445_present':445 in rounded,'exact_450_present':450 in rounded,'exact_455_present':455 in rounded,'full_445_to_455_coverage':category=='full_11point_coverage','category':category}
def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--audit',type=Path,required=True);a=p.parse_args()
 hist=json.loads((ROOT/'outputs/np_k6_p1d1a_h500_x_v1/results.json').read_text()); ref=json.loads((ROOT/'outputs/np_k6_p1d0b_corner_pilot_v1/results.json').read_text()); d110=json.loads((ROOT/'outputs/np_k6_p1d1a0_h500_d110_v1/results.json').read_text());d140=json.loads((ROOT/'outputs/np_k6_p1d1a1_h500_d140_v1/results.json').read_text());d170=json.loads((ROOT/'outputs/np_k6_p1d1a2_h500_d170_v1/results.json').read_text());case=next(x for x in hist['cases'] if x['candidate_id']=='NP_P1D_H500_D200');blank=ref['blank'];post=ROOT/case['source_fsp']['path'];before=sha(post)
 if before['sha256']!=case['source_fsp']['sha256']:raise RuntimeError('D200 historical FSP mismatch')
 sys.path.insert(0,r'N:\Program Files\ANSYS Inc\v251\Lumerical\api\python');import lumapi
 # D200 contract is read only; actual monitor wavelengths are audited for every required FSP.
 f=lumapi.FDTD(hide=True)
 try:
  f.load(str(post));obj={'fdtd_z_min':float(f.getnamed('FDTD','z min')),'fdtd_z_max':float(f.getnamed('FDTD','z max')),'source_z':float(f.getnamed('source','z')),'source_polarization_angle':float(f.getnamed('source','polarization angle')),'source_wavelength_start':float(f.getnamed('source','wavelength start')),'pillar_z_min':float(f.getnamed('TiO2 pillar','z min')),'pillar_z_max':float(f.getnamed('TiO2 pillar','z max')),'pillar_radius':float(f.getnamed('TiO2 pillar','radius')),'pillar_material':str(f.getnamed('TiO2 pillar','material')),'T_z':float(f.getnamed('T_fields','z')),'R_z':float(f.getnamed('R_fields','z')),'T_result_present':bool(f.getresult('T_fields','E')),'R_result_present':bool(f.getresult('R_fields','E'))}
 finally:f.close()
 after=sha(post);expect={'fdtd_z_min':-1e-6,'fdtd_z_max':1.2e-6,'source_z':-5e-7,'source_polarization_angle':0,'source_wavelength_start':450e-9,'pillar_z_min':0,'pillar_z_max':500e-9,'pillar_radius':100e-9,'T_z':900e-9,'R_z':-750e-9}
 if before!=after or any(abs(obj[k]-v)>1e-12 for k,v in expect.items()) or obj['pillar_material']!='APCD_TIO2_NATIVE_M1' or not obj['T_result_present'] or not obj['R_result_present']:raise RuntimeError('D200 contract mismatch')
 b=complex(blank['ax']['real'],blank['ax']['imag']);txx=complex(case['ax']['real'],case['ax']['imag'])/b;tyx=complex(case['ay']['real'],case['ay']['imag'])/b
 result={'stage':'P1-D1A3','execution_mode':'foreground_ssh_synchronous_v1','recovery_mode':'readonly_existing_postrun','candidate_id':'NP_P1D_H500_D200','H_nm':500,'D_nm':200,'gap_nm':90,'polarization':'x','wavelength_nm':450,'pitch_x_nm':290,'period_y_nm':290,'pillar_base_z_nm':0,'pillar_top_z_nm':500,'transmission_reference_z_nm':900,'phase_deembedding_used':False,'reference_blank_id':blank['case_id'],'reference_blank_sha256':blank['post_fsp']['sha256'],'source_post_fsp':before,'post_fsp_readonly_after':after,'read_only_object_audit':obj,'T':case['T'],'R_raw':case['R_raw'],'R_total':-case['R_raw'],'energy_residual':case['energy_residual'],'ax':case['ax'],'ay':case['ay'],'txx':{'real':txx.real,'imag':txx.imag,'amplitude':abs(txx),'phase_rad_wrapped':math.atan2(txx.imag,txx.real),'phase_deg_wrapped':math.degrees(math.atan2(txx.imag,txx.real))},'tyx':{'real':tyx.real,'imag':tyx.imag,'amplitude':abs(tyx),'phase_rad_wrapped':math.atan2(tyx.imag,tyx.real),'phase_deg_wrapped':math.degrees(math.atan2(tyx.imag,tyx.real))},'cross_pol_fraction':case['cross_pol_fraction'],'co_pol_zero_order_power':abs(txx)**2,'cross_pol_zero_order_power':abs(tyx)**2,'x_input_reconstruction_residual':case['x_input_reconstruction_residual'],'new_solver_runs_started_this_thread':0,'new_solver_runs_completed_this_thread':0,'batch_status':'four_of_five_completed','p1d1a_h500_completed_candidates':['NP_P1D_H500_D110','NP_P1D_H500_D140','NP_P1D_H500_D170','NP_P1D_H500_D200'],'p1d1a_h500_line_complete':False,'polarization_completeness':'x_only','xy_symmetry_status':'pending_y_validation','candidate_polarization_quality':'not_assessed_x_only'}
 if not finite(result):raise RuntimeError('nonfinite D200')
 points=[d110,d140,d170,result];ph=[x['txx']['phase_deg_wrapped'] for x in points];deltas=[wrap(ph[i+1]-ph[i]) for i in range(3)];un=[ph[0]]
 for d in deltas:un.append(un[-1]+d)
 partial={'analysis_scope':'four_point_provisional_not_complete_phase_line','diameters_nm':[110,140,170,200],'wrapped_phase_deg':ph,'provisional_unwrapped_phase_deg':un,'adjacent_minimal_wrapped_delta_deg':deltas,'D110_to_D200_provisional_phase_span_deg':un[-1]-un[0],'provisional_four_point_unwrap':True,'P1C_D160_included':False,'full_2pi_from_D110_reached':un[-1]-un[0]>=360,'near_2pi_from_D110':330<=un[-1]-un[0]<360}
 paths={'blank':ROOT/'runtime_fsp/np_k6_p1d0b_corner_pilot_v1/P1D_FIXED_REFERENCE_BLANK_X_post.fsp','D110':ROOT/'runtime_fsp/np_k6_p1d1a_h500_x_v1/NP_P1D_H500_D110_post.fsp','D140':ROOT/'runtime_fsp/np_k6_p1d1a_h500_x_v1/NP_P1D_H500_D140_post.fsp','D170':ROOT/'runtime_fsp/np_k6_p1d1a_h500_x_v1/NP_P1D_H500_D170_post.fsp','D200':post};spectral={k:audit_case(lumapi,v) for k,v in paths.items()};cats=[x['category'] for x in spectral.values()];coverage='full_11point' if all(c=='full_11point_coverage' for c in cats) else ('center_only' if all(c=='center_only' for c in cats) else 'partial');availability={'target_wavelength_grid_nm':TARGET,'cases':spectral,'common_wavelength_axis_across_cases':len({tuple(round(z) for z in x['wavelength_axis_nm']) for x in spectral.values()})==1,'blank_and_pillars_share_same_axis':len({tuple(round(z) for z in x['wavelength_axis_nm']) for x in spectral.values()})==1,'spectral_availability_status':'sufficient_existing_spectral_coverage' if coverage=='full_11point' else 'insufficient_existing_spectral_coverage','EXISTING_FSP_SPECTRAL_COVERAGE':coverage,'PROVISIONAL_10NM_SPECTRAL_AUDIT':'pass' if coverage=='full_11point' else 'not_available','null_reason':None if coverage=='full_11point' else 'existing FSP monitor axes do not provide the required common 445-455 nm 11-point grid'}
 contract={'schema_version':1,'status':'proposed_ready','center_wavelength_nm':450,'band_min_nm':445,'band_max_nm':455,'wavelength_grid_nm':TARGET,'selected_height_nm':None,'dense_diameter_grid_nm':list(range(100,231,5)),'candidate_count':27,'polarization_primary':'x','final_candidate_y_validation':'required','blank_strategy':'one_new_broadband_fixed_reference_blank_x','P1D2_SOLVER_RELEASE':False,'engineering_thresholds':{'linear_phase_fit_rms_deg':10,'maximum_phase_error_deg':15,'amplitude_CV':0.10}}
 write(a.output/'results.json',result);(a.output/'results.csv').write_text('candidate_id,H_nm,D_nm,polarization,T,R_total,txx_amplitude,txx_phase_deg_wrapped\n'+f"NP_P1D_H500_D200,500,200,x,{result['T']},{result['R_total']},{abs(txx)},{result['txx']['phase_deg_wrapped']}\n");write(a.output/'partial_phase_analysis.json',partial);write(a.output/'spectral_availability_audit.json',availability);write(a.output/'run_manifest.json',{'candidate_id':result['candidate_id'],'post_fsp':before,'extractor_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'new_solver_runs_started_this_thread':0});write(a.output/'verification_summary.json',{'P1D1A3_FORMAL_STATUS':'pass','H500_D200_STATUS':'trusted_completed','H500_COMPLETED_COUNT':4,'P1D1A_NEXT_CANDIDATE':'NP_P1D_H500_D230','P1D1A_D230_READY':True,'EXISTING_FSP_SPECTRAL_COVERAGE':coverage,'PROVISIONAL_10NM_SPECTRAL_AUDIT':availability['PROVISIONAL_10NM_SPECTRAL_AUDIT'],'P1D2_BROADBAND_CONTRACT_STATUS':'proposed_ready','P1D2_SOLVER_RELEASE':False});write(ROOT/'outputs/np_k6_p1d2_broadband_contract_v1/broadband_library_contract.json',contract);write(ROOT/'outputs/np_k6_p1d2_broadband_contract_v1/run_manifest.json',{'proposed_only':True,'contract_sha256':hashlib.sha256(json.dumps(contract,sort_keys=True).encode()).hexdigest()});write(a.audit,{'before':before,'after':after,'D200_contract':obj})
if __name__=='__main__':main()
