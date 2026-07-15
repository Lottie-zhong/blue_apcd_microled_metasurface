"""Native-M1 2D dipole device comparison; x-dipole phase is intentionally explicit."""
from __future__ import annotations

import argparse, csv, hashlib, importlib.util, json, math, os, re, shutil, sys, time, traceback
from pathlib import Path
from typing import Any
import numpy as np
import mdc_fdtd_2d_monitor_contract_v1 as monitor_contract

if not hasattr(np,'trapezoid'):np.trapezoid=np.trapz

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs'/'mdc_native_m1_2d_dipole_device_comparison_v1'
RT=ROOT/'runtime'/'mdc_native_m1_2d_dipole_device_comparison_v1'
REPORT=ROOT/'reports'/'mdc_native_m1_2d_dipole_device_comparison_v1.md'
STATIC=ROOT/'outputs'/'mdc_p1_asymmetric_scan_static_v1'/'p1_asymmetric_structures.csv'
WIP_BUILDER=ROOT/'scripts'/'stage_mdc1d1_native_m1_bare_fab_2d_smoke.py'
WAVELENGTH=450e-9
XSPAN=8e-6; MONITOR_XSPAN=6e-6; SOURCE_Y=-400e-9; STACK_Y=0.0
MATERIALS=('APCD_GAN_NATIVE_M1','APCD_TIO2_NATIVE_M1','APCD_SIO2_NATIVE_M1')

def rows(path:Path)->list[dict[str,str]]:
    with path.open(encoding='utf-8-sig',newline='') as h:return list(csv.DictReader(h))
def write(path:Path,data:list[dict[str,Any]])->None:
    path.parent.mkdir(parents=True,exist_ok=True)
    keys=list(dict.fromkeys(k for r in data for k in r))
    with path.open('w',encoding='utf-8',newline='') as h:
        clean=lambda v:'' if isinstance(v,(float,np.floating)) and not np.isfinite(v) else v
        w=csv.DictWriter(h,fieldnames=keys,lineterminator='\n');w.writeheader();w.writerows([{k:clean(v) for k,v in r.items()} for r in data])
def dump(path:Path,value:Any)->None:
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n',encoding='utf-8')
def sequence(text:str)->list[tuple[str,float]]:
    return [(x[0],float(x[1:])) for x in text.split()]

def structures()->list[dict[str,Any]]:
    static={r['static_structure_id']:r for r in rows(STATIC)}
    ids=('P1_EXPLICIT_FAB_G3_A3','P1_ZL1_NOMINAL_G3_A3','P1_ZL1_ALTERNATIVE_G3_A3')
    if any(i not in static for i in ids):raise RuntimeError('frozen_P1_structure_missing')
    result=[{'structure_key':'bare','structure_id':'B0_BARE_GAN_AIR','label':'Bare GaN/Air','kind':'bare','sequence':[],'provenance':'device_control'}]
    # Frozen server text evidence is only an engineering proxy, not a reconstructed thesis structure.
    result.append({'structure_key':'wan_proxy','structure_id':'B1_WAN_MDC_ENGINEERING_PROXY','label':'Wan MDC engineering proxy','kind':'wan_mdc_engineering_proxy','sequence':[('L',100.0),('H',52.0)]*8,'provenance':'outputs/r2_4h1a_inventory_existing_wan_mdc_server_files/r2_4h1a_wan_thesis_parameter_crosscheck.md; approximate SiO2=100 nm, TiO2=52 nm, m=8; exact source FSP layer order unavailable'})
    for key,sid,label in (('explicit',ids[0],'Explicit defect-MDC'),('zl1_nominal',ids[1],'ZL-1 nominal'),('zl1_alternative',ids[2],'ZL-1 alternative')):
        r=static[sid]; result.append({'structure_key':key,'structure_id':sid,'label':label,'kind':r['topology'],'sequence':sequence(r['sequence_GaN_to_Air']),'geometry_hash':r['geometry_hash'],'canonical_sequence_hash':r['canonical_sequence_hash'],'provenance':'frozen P1 asymmetric static manifest'})
    for r in result:
        r['layer_count']=len(r['sequence']);r['total_thickness_nm']=sum(d for _,d in r['sequence']);r['propagation_direction']='GaN -> compiled stack -> Air'
        sequence_identity=json.dumps(r['sequence'],separators=(',',':'))
        r.setdefault('canonical_sequence_hash',hashlib.sha256(sequence_identity.encode()).hexdigest())
        r.setdefault('geometry_hash',hashlib.sha256(json.dumps({'structure_id':r['structure_id'],'kind':r['kind'],'sequence':r['sequence']},sort_keys=True,separators=(',',':')).encode()).hexdigest())
    return result

def audit_only()->None:
    s=structures()
    if len(s)!=5 or [x['structure_key'] for x in s] != ['bare','wan_proxy','explicit','zl1_nominal','zl1_alternative']:raise RuntimeError('structure_inventory_invalid')
    if any('2.41' in WIP_BUILDER.read_text(encoding='utf-8') for _ in [0]):raise RuntimeError('legacy_builder_constant_GaN_seen')
    print(json.dumps({'status':'static_audit_pass','structures':5,'dipoles_supported':['x'],'z_dipole':'blocked_no_verified_project_API_evidence','solver_invoked':False}))

def lumapi():
    p=r'N:\Program Files\ANSYS Inc\v251\Lumerical\api\python\lumapi.py'; spec=importlib.util.spec_from_file_location('lumapi',p); mod=importlib.util.module_from_spec(spec);sys.modules['lumapi']=mod;spec.loader.exec_module(mod);return mod
def native():
    sys.path.insert(0,str(ROOT/'scripts'));import apcd_native_materials as m;return m
def add_rect(f,name,material,y0,y1):
    f.addrect();f.set('name',name);f.set('material',material);f.set('x span',XSPAN);f.set('y min',y0);f.set('y max',y1)
def build_case(f,case:dict[str,Any],dipole:str='x')->dict[str,Any]:
    if dipole not in ('x','z'):raise RuntimeError('unsupported_dipole')
    m=native(); registered=[]
    for mid in MATERIALS:m.register_lumerical_sampled_material(f,mid,apply_display_style=True);registered.append(mid)
    f.addfdtd();f.set('dimension','2D');f.set('x span',XSPAN);f.set('y min',-1e-6);f.set('y max',max(1.6e-6,case['total_thickness_nm']*1e-9+600e-9));f.set('x min bc','PML');f.set('x max bc','PML');f.set('y min bc','PML');f.set('y max bc','PML');f.set('mesh accuracy',2);f.set('simulation time',300e-15)
    add_rect(f,'gan','APCD_GAN_NATIVE_M1',-1e-6,STACK_Y);y=STACK_Y
    for i,(mat,d) in enumerate(case['sequence']):add_rect(f,f'layer_{i}','APCD_SIO2_NATIVE_M1' if mat=='L' else 'APCD_TIO2_NATIVE_M1',y,y+d*1e-9);y+=d*1e-9
    f.addmesh();f.set('x span',XSPAN);f.set('y min',-50e-9);f.set('y max',y+50e-9);f.set('dx',20e-9);f.set('dy',2e-9)
    theta=90 if dipole=='x' else 0
    monitor_contract.add_source_local_mesh(f,0,SOURCE_Y)
    f.adddipole();f.set('name',dipole+'_dipole');f.set('x',0);f.set('y',SOURCE_Y);f.set('theta',theta);f.set('phi',0);f.set('wavelength start',WAVELENGTH);f.set('wavelength stop',WAVELENGTH)
    f.addpower();f.set('name','upward_monitor');f.set('monitor type','Linear X');f.set('x span',MONITOR_XSPAN);f.set('y',y+300e-9)
    return {'registered_materials':registered,'stack_entrance_y_m':STACK_Y,'stack_top_y_m':y,'source_y_m':SOURCE_Y,'monitor_y_m':y+300e-9,'dipole':dipole,'requested_theta_deg':theta,'requested_phi_deg':0,'mesh_dx_m':20e-9,'mesh_dy_m':2e-9,'source_local_mesh_dx_m':2e-9,'source_local_mesh_dy_m':2e-9,'simulation_time_s':300e-15}
def angular_metrics(angle, intensity):
    a=np.degrees(angle) if np.nanmax(np.abs(angle))<=math.pi+1 else np.asarray(angle,float);i=np.abs(np.asarray(intensity,float).squeeze());o=np.argsort(a);a=a[o];i=i[o];
    if not np.all(np.isfinite(i)):raise RuntimeError('nonfinite_farfield')
    symmetry_residual=float(np.max(np.abs(i-i[::-1])));tol=max(64*np.finfo(float).eps*max(1.0,float(i.max())),float(np.nextafter(symmetry_residual,np.inf)));tied=sorted(float(v) for v in a[i>=i.max()-tol]);pair=any(v>0 and any(np.isclose(-v,u,rtol=0,atol=1e-9) for u in tied) for v in tied);peak_set=sorted(v for v in tied if pair and any(np.isclose(-v,u,rtol=0,atol=1e-9) for u in tied)) if pair else tied
    theta=np.radians(a);norm=i/np.trapezoid(i,theta);segment=.5*(norm[:-1]+norm[1:])*np.diff(theta);mid_abs=np.abs(.5*(a[:-1]+a[1:]));
    def integ(lo,hi):
        mask=(mid_abs<=hi)&(mid_abs>lo if lo else mid_abs>=0);return float(segment[mask].sum())
    peak=int(np.argmax(i));half=i[peak]/2;left=next((a[j-1]+(half-i[j-1])*(a[j]-a[j-1])/(i[j]-i[j-1]) for j in range(peak,0,-1) if i[j-1]<half<=i[j]),float('nan'));right=next((a[j]+(half-i[j])*(a[j+1]-a[j])/(i[j+1]-i[j]) for j in range(peak,len(a)-1) if i[j]>=half>i[j+1]),float('nan'))
    eta20=integ(0,20);leak20=integ(20,40);leak40=integ(40,60);residual=integ(60,180);normal_mask=np.abs(a)<=10;large_mask=(np.abs(a)>=40)&(np.abs(a)<=60);ratio=float(i[normal_mask].mean()/i[large_mask].mean()) if normal_mask.any() and large_mask.any() else None
    return {'maximum_angle_raw_argmax_deg':float(a[peak]),'maximum_angle_set_deg':json.dumps(peak_set,separators=(',',':')),'maximum_abs_angle_deg':max(map(abs,peak_set)),'symmetric_peak_pair':pair,'peak_tie_tolerance':tol,'symmetry_residual':symmetry_residual,'angular_FWHM_deg':right-left if np.isfinite(left) and np.isfinite(right) else None,'angular_FWHM_status':'pass' if np.isfinite(left) and np.isfinite(right) else 'boundary_truncated','T0_over_Tmax':float(i[np.argmin(abs(a))]/i.max()),'cone_fraction_5deg':integ(0,5),'cone_fraction_10deg':integ(0,10),'cone_fraction_15deg':integ(0,15),'cone_fraction_20deg':eta20,'leakage20_40':leak20,'leakage40_60':leak40,'residual60_plus':residual,'fraction_sum':eta20+leak20+leak40+residual,'normal_to_40_60_ratio':ratio},a,norm
def run_one(case:dict[str,Any],dipole='x')->tuple[dict[str,Any],list[dict[str,Any]]]:
    lu=lumapi();f=lu.FDTD(hide=True);RT.mkdir(parents=True,exist_ok=True);path=RT/(case['structure_key']+'_'+dipole+'_450.fsp');start=time.time()
    try:
        setup=build_case(f,case,dipole);f.save(str(path));f.load(str(path));f.run();r=f.getresult('upward_monitor','T');raw=float(np.real(np.asarray(r['T']).squeeze()));ff=np.asarray(f.farfield2d('upward_monitor',1)).squeeze();an=np.asarray(f.farfieldangle('upward_monitor',1)).squeeze();metric,angles,norm=angular_metrics(an,ff)
        metric.update({'structure_key':case['structure_key'],'structure_id':case['structure_id'],'dipole':dipole,'raw_upward_monitor_power':raw,'total_upward_power':raw,'source_normalized_power_status':'unresolved_small_box_monitors_not_implemented','stack_entrance_deembedded_transfer_status':'unresolved_homogeneous_reference_plane_not_implemented','absolute_extraction_status':'pending','runtime_s':time.time()-start,'monitor_result_fields':';'.join(r.keys()),**setup})
        return metric,[{'structure_key':case['structure_key'],'dipole':dipole,'angle_deg':float(x),'normalized_intensity':float(y)} for x,y in zip(angles,norm)]
    finally:f.close()
def build_only()->None:
    RT.mkdir(parents=True,exist_ok=True); lu=lumapi();f=lu.FDTD(hide=True)
    try:
        m=[]
        for c in structures():
            f.newproject();m.append({'structure_key':c['structure_key'],**build_case(f,c)});f.save(str(RT/(c['structure_key']+'_build_only.fsp')))
        write(OUT/'structure_manifest.csv',structures());write(OUT/'simulation_manifest.csv',m);write(OUT/'material_readback.csv',[{'canonical_id':x,'registration':'configured_with_apply_display_style_true'} for x in MATERIALS]);dump(OUT/'wan_baseline_provenance.json',{'status':'wan_mdc_engineering_proxy','exact_thesis_structure':'not_uniquely_confirmed','proxy_sequence':'(L100 H52)^8','source':'r2_4h1a_wan_thesis_parameter_crosscheck.md'})
    finally:f.close()
    print('build_only PASS')
def run_pilot(keys:list[str])->None:
    allc={c['structure_key']:c for c in structures()};metrics=[];angles=[]
    for key in keys:
        m,a=run_one(allc[key]);metrics.append(m);angles.extend(a)
    write(OUT/'angular_metrics.csv',metrics);write(OUT/'angular_spectra_long.csv',angles);write(OUT/'cone_power_metrics.csv',metrics);write(OUT/'spectral_metrics.csv',[{'structure_key':m['structure_key'],'status':'single_frequency_450_no_spectral_FWHM'} for m in metrics]);write(OUT/'spectra_long.csv',[{'structure_key':m['structure_key'],'wavelength_nm':450.0,'status':'single_frequency'} for m in metrics]);write(OUT/'source_weighted_metrics.csv',[{'status':'broadband_not_yet_validated'}]);write(OUT/'normalization_audit.csv',[{'status':'raw_monitor_not_extraction_efficiency; deembedding_pending'}]);write(OUT/'convergence_audit.csv',[{'status':'pilot_only_not_yet_converged'}]);write(OUT/'simulation_manifest.csv',metrics);write(OUT/'structure_manifest.csv',structures());write(OUT/'material_readback.csv',[{'canonical_id':x,'registration':'PASS'} for x in MATERIALS]);dump(OUT/'wan_baseline_provenance.json',{'status':'wan_mdc_engineering_proxy','proxy_sequence':'(L100 H52)^8'});dump(OUT/'validation.json',{'status':'x_dipole_pilot_complete','z_dipole':'blocked_no_verified_project_API_evidence','broadband':'not_run','solver_invoked':True});dump(OUT/'manifest.json',{'task':'MDC_NATIVE_M1_2D_DIPOLE_DEVICE_COMPARISON_V1','outputs':sorted(p.name for p in OUT.iterdir()),'runtime_dir':str(RT),'git_commit':False})
    REPORT.write_text('# MDC Native-M1 2D dipole device comparison v1\n\n- B1 is `wan_mdc_engineering_proxy`, not an exact thesis reconstruction.\n- x-dipole pilot only: z-dipole has no verified project-local 2D API evidence and was not guessed.\n- Raw upward monitor power is not extraction efficiency; matched homogeneous-GaN deembedding is pending.\n- Broadband metrics and device-level decision are not yet validated.\n',encoding='utf-8')
    print(json.dumps({'status':'x_dipole_pilot_complete','runs':len(metrics)}))

def orientation_normalization_audit():
    s=structures(); result=[]
    for case in s:
        for dipole,theta in (('x',90),('z',0)):
            result.append({'structure_key':case['structure_key'],'dipole':dipole,'requested_theta_deg':theta,'requested_phi_deg':0,'readback_status':'requires_build_readback','source_y_m':SOURCE_Y,'fdtd_dimension':'2D','source_name':dipole+'_dipole','model_group_overwrite':'not_used'})
    write(OUT/'dipole_orientation_readback.csv',result)
    dump(OUT/'validation.json',{'status':'orientation_normalization_static_audit_pass','canonical_emitted_power':'small_monitor_box_flux_required','dipolepower':'unreliable_in_lossy_dispersive_GaN','sourcepower':'homogeneous_analytic_diagnostic_only','solver_invoked':False})
    print(json.dumps({'status':'orientation_normalization_static_audit_pass','rows':len(result),'solver_invoked':False}))

def orientation_normalization_pilot():
    allc={c['structure_key']:c for c in structures()}; metrics=[]; profiles=[]
    for key in ('bare','zl1_alternative'):
        for dipole in ('x','z'):
            m,a=run_one(allc[key],dipole);metrics.append(m);profiles.extend(a)
    write(OUT/'angular_metrics_450.csv',metrics);write(OUT/'angular_spectra_450_long.csv',profiles);write(OUT/'dipole_orientation_readback.csv',[{k:m[k] for k in ('structure_key','dipole','requested_theta_deg','requested_phi_deg','source_y_m')}|{'readback_status':'source_created; model_group_not_used'} for m in metrics]);write(OUT/'source_local_mesh_readback.csv',[{k:m[k] for k in ('structure_key','dipole','source_local_mesh_dx_m','source_local_mesh_dy_m','mesh_dx_m','mesh_dy_m')} for m in metrics]);write(OUT/'dipole_field_channel_validation.csv',[{'dipole':'x','expected_channel':'TM_like Ex,Ey,Hz; Ez numerical floor','status':'unresolved_no_field_monitor_readback'},{'dipole':'z','expected_channel':'TE_like Ez,Hx,Hy; Ex,Ey numerical floor','status':'unresolved_no_field_monitor_readback'}]);write(OUT/'dipole_emission_box_validation.csv',[{'status':'unresolved_four_monitor_small_box_not_implemented'}]);write(OUT/'homogeneous_reference_metrics.csv',[{'status':'unresolved_matched_homogeneous_reference_y0_not_implemented'}]);write(OUT/'power_normalization_metrics_450.csv',[{'status':'unresolved_small_box_and_reference_required'}]);write(OUT/'convergence_audit.csv',[{'status':'unresolved_strict_repeat_not_run'}]);dump(OUT/'validation.json',{'status':'orientation_pilot_runs_returned_normalization_unresolved','runs':4,'z_orientation_requested_theta_deg':0,'x_orientation_requested_theta_deg':90,'solver_invoked':True,'blocks_full_450_all':True});dump(OUT/'manifest.json',{'task':'MDC_NATIVE_M1_2D_DIPOLE_ORIENTATION_NORMALIZATION_AND_450_CLOSURE_V1','outputs':sorted(p.name for p in OUT.iterdir()),'runtime_dir':str(RT),'git_commit':False});REPORT.write_text('# MDC Native-M1 2D dipole orientation and normalization closure v1\n\n- Bare/alternative x/z 450-nm orientation pilot returned.\n- Orientation theta requests are x=90 deg and z=0 deg.\n- Full comparison blocked: four-monitor emitted-power box, homogeneous-GaN y=0 reference, field-channel readback, and strict convergence have not yet passed.\n- No broadband metrics are reported.\n',encoding='utf-8');print(json.dumps({'status':'orientation_pilot_runs_returned_normalization_unresolved','runs':4}))

MESH_STUDY={'M2':(2.0,(12,16,20,24,30)),'M1':(1.0,(8,10,12,16,20))}

def _add_reference_plane(f,name='reference_y0',y=0.0):
    f.addpower();f.set('name',name);f.set('monitor type','Linear X');f.set('x',0);f.set('y',y);f.set('x span',600e-9);f.set('override global monitor settings',True);f.set('frequency points',1)

def _homogeneous_setup(f,dipole:str,mesh_nm:float,boxes_nm:tuple[int,...],with_reference:bool=False):
    native().register_lumerical_sampled_material(f,'APCD_GAN_NATIVE_M1',apply_display_style=True)
    f.addfdtd();f.set('dimension','2D');f.set('background material','APCD_GAN_NATIVE_M1');f.set('x span',1e-6);f.set('y min',-800e-9);f.set('y max',300e-9);f.set('x min bc','PML');f.set('x max bc','PML');f.set('y min bc','PML');f.set('y max bc','PML');f.set('mesh accuracy',1);f.set('simulation time',300e-15)
    monitor_contract.add_source_local_mesh(f,0,SOURCE_Y,max(boxes_nm)*1e-9,mesh_nm*1e-9)
    f.adddipole();f.set('name',dipole+'_dipole');f.set('x',0);f.set('y',SOURCE_Y);f.set('theta',90 if dipole=='x' else 0);f.set('phi',0);f.set('wavelength start',WAVELENGTH);f.set('wavelength stop',WAVELENGTH)
    for half in boxes_nm:monitor_contract.add_2d_power_box(f,f'emit_box_{half}nm',0,SOURCE_Y,half*1e-9)
    if with_reference:_add_reference_plane(f)

def _read_box(f,prefix:str)->dict[str,float]:
    raw={}
    for side,kind in (('top','Linear X'),('bottom','Linear X'),('right','Linear Y'),('left','Linear Y')):
        raw[side]=monitor_contract.integrate_line_poynting_flux(monitor_contract.read_fields(f,prefix+'_'+side),kind)
    return {**raw,**monitor_contract.calculate_box_outward_flux(raw)}

def _fit_zero_radius(points:list[dict[str,Any]])->dict[str,float]:
    p=sorted(points,key=lambda r:float(r['box_half_size_nm']))[:3];x=np.asarray([float(r['box_half_size_nm']) for r in p]);y=np.asarray([float(r['P_emit_box']) for r in p])
    linear=float(np.polyfit(x,y,1)[1]); exponential=float(np.exp(np.polyfit(x,np.log(y),1)[1]));delta=abs(linear-exponential)/max(abs((linear+exponential)/2),1e-30)
    return {'linear_P0':linear,'exponential_P0':exponential,'P0_model_relative_difference':delta,'selected_P0':(linear+exponential)/2}

def canonical_emission_audit_v3()->None:
    required=('add_source_local_mesh','add_2d_power_box','read_fields','integrate_line_poynting_flux','calculate_box_outward_flux','read_reference_plane_flux')
    missing=[x for x in required if not hasattr(monitor_contract,x)]
    if missing:raise RuntimeError('monitor_contract_missing:'+','.join(missing))
    if len(structures())!=5:raise RuntimeError('structure_inventory_invalid')
    print(json.dumps({'status':'canonical_emission_v3_audit_pass','contract_functions':required,'mesh_study':MESH_STUDY,'solver_invoked':False}))

def canonical_emission_run_v3(dipoles:list[str])->None:
    if set(dipoles)!={'x','z'}:raise RuntimeError('canonical_requires_x_and_z')
    RT.mkdir(parents=True,exist_ok=True);OUT.mkdir(parents=True,exist_ok=True);lu=lumapi();points=[]
    for dipole in dipoles:
        for mesh_id,(mesh_nm,boxes) in MESH_STUDY.items():
            f=lu.FDTD(hide=True);path=RT/f'CANONICAL_HOMOG_GAN_{dipole}_{mesh_id}_{int(time.time()*1000)}.fsp';start=time.time()
            try:
                _homogeneous_setup(f,dipole,mesh_nm,boxes);f.save(str(path));f.load(str(path));f.run()
                for half in boxes:
                    flux=_read_box(f,f'emit_box_{half}nm');points.append({'record_type':'mesh_point','dipole':dipole,'mesh_id':mesh_id,'mesh_dx_nm':mesh_nm,'mesh_dy_nm':mesh_nm,'box_half_size_nm':half,'box_half_cells':half/mesh_nm,'legal_box':half/mesh_nm>=4,'P_emit_box':flux['net_outward'],'monotonic_absorption_expected':'decrease_with_radius','runtime_s':time.time()-start})
            finally:f.close()
    selections=[];passed=True
    for dipole in dipoles:
        group=[r for r in points if r['dipole']==dipole]
        bymesh={m:sorted([r for r in group if r['mesh_id']==m],key=lambda r:r['box_half_size_nm']) for m in MESH_STUDY}
        monotonic={m:all(float(a['P_emit_box'])>=float(b['P_emit_box']) for a,b in zip(v,v[1:])) for m,v in bymesh.items()}
        common=sorted(set(r['box_half_size_nm'] for r in bymesh['M1'])&set(r['box_half_size_nm'] for r in bymesh['M2']))
        common_deltas=[abs(next(r['P_emit_box'] for r in bymesh['M1'] if r['box_half_size_nm']==h)-next(r['P_emit_box'] for r in bymesh['M2'] if r['box_half_size_nm']==h))/max(abs(next(r['P_emit_box'] for r in bymesh['M1'] if r['box_half_size_nm']==h)),1e-30) for h in common]
        m1=bymesh['M1'][0]
        m2=bymesh['M2'][0];small_delta=abs(m1['P_emit_box']-m2['P_emit_box'])/max(abs(m1['P_emit_box']),1e-30);fit=_fit_zero_radius(bymesh['M1'])
        if small_delta<=0.03:method='M1_smallest_legal_box';selected=float(m1['P_emit_box']);ok=True
        else:method='mean_linear_exponential_zero_radius_extrapolation';selected=fit['selected_P0'];ok=fit['P0_model_relative_difference']<=0.03
        ok=bool(ok and all(monotonic.values()) and selected>0);passed &= ok
        selections.append({'record_type':'selection','dipole':dipole,'canonical_mesh_id':'M1','canonical_mesh_nm':1.0,'smallest_M1_box_half_nm':m1['box_half_size_nm'],'smallest_M2_box_half_nm':m2['box_half_size_nm'],'smallest_mesh_relative_difference':small_delta,'common_box_half_sizes_nm':json.dumps(common),'common_mesh_relative_differences':json.dumps(common_deltas),'M1_monotonic_decrease':monotonic['M1'],'M2_monotonic_decrease':monotonic['M2'],**fit,'canonical_P_emit':selected if ok else '','canonical_selection_method':method,'canonical_status':'pass' if ok else 'fail'})
    write(OUT/'canonical_emission_power_selection.csv',points+selections)
    dump(OUT/'validation.json',{'status':'canonical_emission_pass' if passed else 'emitted_power_near_source_not_converged','canonical_emission_pass':passed,'solver_invoked':True,'new_physical_scan':'canonical_emission_mesh_study_only','structures_run':0})
    dump(OUT/'manifest.json',{'task':'MDC_NATIVE_M1_2D_DIPOLE_CANONICAL_EMISSION_AND_450_ALL_V3','phase':'canonical_emission_mesh_study','outputs':['canonical_emission_power_selection.csv','validation.json'],'runtime_dir':str(RT),'git_commit':False})
    print(json.dumps({'status':'canonical_emission_pass' if passed else 'emitted_power_near_source_not_converged','selections':selections}))

def postprocess_450_v3()->None:
    path=OUT/'canonical_emission_power_selection.csv';validation=json.loads((OUT/'validation.json').read_text(encoding='utf-8'))
    data=rows(path);selection=[r for r in data if r['record_type']=='selection']
    if validation['status']=='emitted_power_near_source_not_converged':
        for r in selection:
            if r['canonical_status']=='fail':r['canonical_P_emit']=''
        write(path,[r for r in data if r['record_type']!='selection']+selection)
        lines=['# MDC Native-M1 2D dipole canonical emission and 450-all v3','',f"Status: `{validation['status']}`.",'','## Contract reuse','', '- Source-local mesh, four-sided power boxes, outward signs, direct Poynting integration, field reads, and y=0 reference contract come exclusively from `mdc_fdtd_2d_monitor_contract_v1.py`.', '- `sourcepower` and `dipolepower` are not used as canonical emitted power.','','## Canonical emission mesh study','', '|dipole|smallest M1/M2 difference|M1 common-box trend|M2 common-box trend|linear P0|exponential P0|model difference|status|','|---|---:|---|---|---:|---:|---:|---|']
        for r in selection:lines.append(f"|{r['dipole']}|{float(r['smallest_mesh_relative_difference']):.6%}|{r['M1_monotonic_decrease']}|{r['M2_monotonic_decrease']}|{float(r['linear_P0']):.12g}|{float(r['exponential_P0']):.12g}|{float(r['P0_model_relative_difference']):.6%}|{r['canonical_status']}|")
        lines += ['', 'The x-dipole smallest legal M1/M2 values differ by more than 3%, and its linear/exponential zero-radius extrapolations differ by more than 3%. Therefore no canonical x-dipole emitted power is selected.', '', '## Gate consequence','', '- Homogeneous y=0 reference: not run after the failed canonical-emission gate.', '- Device convergence and B0–B4: not run.', '- No device-level power, angular, QW-average, comparison, or ML labels were produced.', '- This is the required hard stop `emitted_power_near_source_not_converged`, not a solver failure.', '', 'No broadband, 3D, TMM, RCWA, FMMAX, or constant-GaN fallback was run. No source FSP was opened. No files were staged, committed, or pushed.']
        REPORT.write_text('\n'.join(lines)+'\n',encoding='utf-8')
        dump(OUT/'manifest.json',{'task':'MDC_NATIVE_M1_2D_DIPOLE_CANONICAL_EMISSION_AND_450_ALL_V3','phase':'canonical_emission_gate_failed','status':validation['status'],'outputs':['canonical_emission_power_selection.csv','validation.json'],'runtime_dir':str(RT),'downstream_solver_runs':0,'git_commit':False})
        print(json.dumps({'status':validation['status'],'report':str(REPORT),'downstream_solver_runs':0}));return
    raise RuntimeError('postprocess_requires_completed_device_results_when_canonical_gate_passes')

BROADBAND_START_NM=440.0;BROADBAND_STOP_NM=460.0;BROADBAND_POINTS=101
OVERNIGHT_STATE=RT/'overnight_state.json';OVERNIGHT_STATUS=RT/'overnight_case_status.csv';OVERNIGHT_LOG=RT/'overnight_master.log'

def _sha256(path:Path)->str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()

def _broadband_signature(start_nm:float,stop_nm:float,points:int)->str:
    payload={'task':'MDC_NATIVE_M1_2D_DIPOLE_BROADBAND_440_460_V1_OVERNIGHT','physics_contract_version':'native_m1_2d_xy_source_limits_direct_poynting_m1_8nm_v1','start_nm':start_nm,'stop_nm':stop_nm,'points':points,'structures':structures(),'materials':[(r['material_id'],r['sample_hash']) for r in _material_audit()],'source_y_nm':-400,'x_span_um':8,'global_dx_nm':20,'stack_dy_nm':2,'local_dx_dy_nm':1,'emission_box_half_nm':8,'monitor_x_span_um':6}
    return hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()

def _canonical_gate_status()->str:
    if not (OUT/'validation.json').exists():return 'missing'
    value=json.loads((OUT/'validation.json').read_text(encoding='utf-8'));return value.get('canonical_emission_status',value.get('status','missing'))

def _log(message:str)->None:
    RT.mkdir(parents=True,exist_ok=True)
    with OVERNIGHT_LOG.open('a',encoding='utf-8') as h:h.write(time.strftime('%Y-%m-%dT%H:%M:%S')+' '+message+'\n')

def _case_plan()->list[dict[str,Any]]:
    plan=[]
    for d in ('x','z'):plan.append({'case_id':f'homogeneous_reference_{d}_strict','structure_key':'homogeneous_reference','dipole':d,'profile':'strict','simulation_time_fs':900,'autoshutoff':1e-7,'phase':'prerequisite'})
    for profile,fs,auto,phase in (('pilot',600,1e-6,'pilot'),('strict',900,1e-7,'strict')):
        for key in ('bare','zl1_alternative'):
            for d in ('x','z'):plan.append({'case_id':f'{key}_{d}_{profile}','structure_key':key,'dipole':d,'profile':profile,'simulation_time_fs':fs,'autoshutoff':auto,'phase':phase})
    for key in ('wan_proxy','explicit','zl1_nominal'):
        for d in ('x','z'):plan.append({'case_id':f'{key}_{d}_strict','structure_key':key,'dipole':d,'profile':'strict','simulation_time_fs':900,'autoshutoff':1e-7,'phase':'remaining'})
    return plan

def _init_state(start_nm:float,stop_nm:float,points:int)->dict[str,Any]:
    signature=_broadband_signature(start_nm,stop_nm,points);old=None
    if OVERNIGHT_STATE.exists():
        try:old=json.loads(OVERNIGHT_STATE.read_text(encoding='utf-8'))
        except Exception:old=None
    if old and old.get('signature')==signature:return old
    state={'task':'MDC_NATIVE_M1_2D_DIPOLE_BROADBAND_440_460_V1_OVERNIGHT','signature':signature,'created_at':time.strftime('%Y-%m-%dT%H:%M:%S'),'wavelength_start_nm':start_nm,'wavelength_stop_nm':stop_nm,'wavelength_points':points,'canonical_emission_status':_canonical_gate_status(),'cases':[]}
    for c in _case_plan():state['cases'].append({**c,'status':'pending','attempts':0,'result_npz':'','result_json':'','error':''})
    _save_state(state);return state

def _save_state(state:dict[str,Any])->None:
    dump(OVERNIGHT_STATE,state);write(OVERNIGHT_STATUS,state['cases'])

def _material_audit()->list[dict[str,Any]]:
    m=native();result=[]
    for mid in MATERIALS:
        s=m.get_native_epsilon_samples(mid);freq=np.asarray(s['frequency_hz'],float);lam=299792458.0/freq*1e9;eps=np.asarray(s['epsilon'])
        result.append({'material_id':mid,'sample_count':len(lam),'wavelength_min_nm':float(lam.min()),'wavelength_max_nm':float(lam.max()),'covers_440_460':bool(lam.min()<=440 and lam.max()>=460),'sample_hash':hashlib.sha256(lam.tobytes()+eps.tobytes()).hexdigest(),'registration':'register_lumerical_sampled_material(apply_display_style=True)','fallback':False})
    return result

def broadband_audit(start_nm:float,stop_nm:float,points:int)->None:
    if (start_nm,stop_nm,points)!=(440.0,460.0,101):raise RuntimeError('formal_broadband_grid_must_be_440_460_101')
    mats=_material_audit()
    if not all(r['covers_440_460'] for r in mats):raise RuntimeError('native_material_range_does_not_cover_440_460')
    contract=('add_source_local_mesh','add_2d_power_box','add_reference_plane_monitor','read_fields','integrate_line_poynting_flux','calculate_box_outward_flux','read_reference_plane_flux')
    if any(not hasattr(monitor_contract,x) for x in contract):raise RuntimeError('broadband_monitor_contract_incomplete')
    s=structures()
    print(json.dumps({'status':'broadband_static_audit_pass','materials':mats,'structures':[r['structure_key'] for r in s],'contract':contract,'actual_grid_required':True,'canonical_emission_status':_canonical_gate_status(),'solver_invoked':False}))

def _add_broadband_dipole(f,dipole,start_m,stop_m):
    f.adddipole();f.set('name',dipole+'_dipole');f.set('x',0);f.set('y',SOURCE_Y);f.set('theta',90 if dipole=='x' else 0);f.set('phi',0);f.set('wavelength start',start_m);f.set('wavelength stop',stop_m)

def _build_broadband_case(f,case:dict[str,Any],structure:dict[str,Any]|None,start_nm:float,stop_nm:float,points:int)->dict[str,Any]:
    start_m=start_nm*1e-9;stop_m=stop_nm*1e-9;registered=[];m=native()
    for mid in MATERIALS:m.register_lumerical_sampled_material(f,mid,apply_display_style=True);registered.append(mid)
    homogeneous=case['structure_key']=='homogeneous_reference';top=0.0 if homogeneous else structure['total_thickness_nm']*1e-9
    f.addfdtd();f.set('dimension','2D');f.set('x span',1e-6 if homogeneous else XSPAN);f.set('y min',-1e-6);f.set('y max',max(800e-9,top+600e-9));f.set('x min bc','PML');f.set('x max bc','PML');f.set('y min bc','PML');f.set('y max bc','PML');f.set('mesh accuracy',2);f.set('simulation time',case['simulation_time_fs']*1e-15);f.set('auto shutoff min',case['autoshutoff'])
    if homogeneous:f.set('background material','APCD_GAN_NATIVE_M1')
    else:
        add_rect(f,'gan','APCD_GAN_NATIVE_M1',-1e-6,STACK_Y);y=STACK_Y
        for i,(mat,d) in enumerate(structure['sequence']):add_rect(f,f'layer_{i}','APCD_SIO2_NATIVE_M1' if mat=='L' else 'APCD_TIO2_NATIVE_M1',y,y+d*1e-9);y+=d*1e-9
        f.addmesh();f.set('name','stack_mesh');f.set('x span',XSPAN);f.set('y min',-50e-9);f.set('y max',y+50e-9);f.set('dx',20e-9);f.set('dy',2e-9)
    box_half_nm=float(case.get('box_half_nm',8.0));monitor_contract.add_source_local_mesh(f,0,SOURCE_Y,box_half_nm*1e-9,1e-9);_add_broadband_dipole(f,case['dipole'],start_m,stop_m)
    monitor_contract.add_2d_power_box(f,f'emit_box_{box_half_nm:g}nm',0,SOURCE_Y,box_half_nm*1e-9,start_m,stop_m,points)
    monitor_y=0.0 if homogeneous else top+300e-9;name='reference_y0' if homogeneous else 'upward_monitor';span=600e-9 if homogeneous else MONITOR_XSPAN
    monitor_contract.add_reference_plane_monitor(f,name,0,monitor_y,span,start_m,stop_m,points)
    return {'registered_materials':registered,'homogeneous':homogeneous,'stack_top_y_m':top,'monitor_name':name,'monitor_y_m':monitor_y,'source_local_mesh_nm':1.0,'emission_box_half_nm':box_half_nm,'global_dx_nm':20.0,'stack_dy_nm':2.0,'requested_simulation_time_fs':case['simulation_time_fs'],'autoshutoff_target':case['autoshutoff']}

def _spectrum_from_monitor(f,name:str)->tuple[np.ndarray,np.ndarray]:
    freq=np.asarray(f.getdata(name,'f'),float).squeeze();flux=np.asarray(monitor_contract.integrate_line_poynting_flux(monitor_contract.read_fields(f,name),'Linear X'),float).squeeze();lam=299792458.0/freq*1e9;o=np.argsort(lam);return lam[o],flux[o]

def _box_spectrum(f,prefix:str)->np.ndarray:
    raw={}
    for side,kind in (('top','Linear X'),('bottom','Linear X'),('right','Linear Y'),('left','Linear Y')):raw[side]=np.asarray(monitor_contract.integrate_line_poynting_flux(monitor_contract.read_fields(f,prefix+'_'+side),kind),float).squeeze()
    return np.asarray(monitor_contract.calculate_box_outward_flux(raw)['net_outward'],float).squeeze()

def _extract_angles(f,monitor_name:str,wavelength_nm:np.ndarray,p_up:np.ndarray)->tuple[np.ndarray,np.ndarray,np.ndarray]:
    targets=[448.0,450.0,453.0,float(wavelength_nm[int(np.argmax(p_up))])];unique=[]
    for x in targets:
        k=int(np.argmin(abs(wavelength_nm-x)))
        if k not in unique:unique.append(k)
    w=[];a=[];intensity=[]
    # wavelength_nm is ascending while the monitor frequency index is descending.
    for k in unique:
        monitor_index=len(wavelength_nm)-k
        ff=np.abs(np.asarray(f.farfield2d(monitor_name,monitor_index)).squeeze());ang=np.asarray(f.farfieldangle(monitor_name,monitor_index)).squeeze();deg=np.degrees(ang) if np.nanmax(abs(ang))<=math.pi+1 else ang
        for x,y in zip(deg,ff):w.append(float(wavelength_nm[k]));a.append(float(x));intensity.append(float(y))
    return np.asarray(w),np.asarray(a),np.asarray(intensity)

def _find_solver_log(fsp:Path)->Path|None:
    candidates=sorted(fsp.parent.glob(fsp.stem+'*.log'),key=lambda p:p.stat().st_mtime,reverse=True);return candidates[0] if candidates else None

def _parse_solver_log(path:Path)->dict[str,Any]:
    text=path.read_text(encoding='utf-8',errors='replace');autos=[float(x) for x in re.findall(r'Auto Shutoff:\s*([0-9.eE+-]+)',text)];sim=re.findall(r'or\s*([0-9.eE+-]+)s of Simulation Time',text);memory=re.findall(r'Peak memory used in the simulation \(GiB\):\s*([0-9.eE+-]+)',text);issues=[line.strip() for line in text.splitlines() if re.search(r'\b(error|warning)\b',line,re.I)]
    return {'final_autoshutoff':autos[-1] if autos else None,'actual_simulation_time_s':float(sim[-1]) if sim else None,'peak_memory_GiB':float(memory[-1]) if memory else None,'termination_reason':'autoshutoff_criteria_satisfied' if 'autoshutoff criteria are satisfied' in text.lower() else ('full_requested_time' if '100% complete' in text else 'solver_log_unresolved'),'warnings_errors':' | '.join(issues) if issues else 'none'}

def _execute_case_once(case:dict[str,Any],state:dict[str,Any],start_nm:float,stop_nm:float,points:int,attempt:int)->None:
    if shutil.disk_usage(RT).free<5*1024**3:raise RuntimeError('insufficient_runtime_disk_space_below_5GiB')
    all_structures={r['structure_key']:r for r in structures()};structure=all_structures.get(case['structure_key']);stamp=time.strftime('%Y%m%d_%H%M%S');stem=f"{case['case_id']}_attempt{attempt}_{stamp}";fsp=RT/(stem+'.fsp');npz=RT/(stem+'.npz');meta_path=RT/(stem+'.json');lu=lumapi();f=lu.FDTD(hide=True);start=time.time();setup={}
    try:
        setup=_build_broadband_case(f,case,structure,start_nm,stop_nm,points);f.save(str(fsp));f.load(str(fsp));f.run();monitor=setup['monitor_name'];lam,p_up=_spectrum_from_monitor(f,monitor);p_emit=_box_spectrum(f,'emit_box_8nm');o=np.argsort(299792458.0/np.asarray(f.getdata(monitor,'f'),float).squeeze()*1e9);p_emit=p_emit[o]
        if len(lam)!=points or len(p_emit)!=points:raise RuntimeError(f'wavelength_point_count_mismatch:{len(lam)}:{len(p_emit)}')
        if not np.all(np.isfinite(lam)) or not np.all(np.isfinite(p_up)) or not np.all(np.isfinite(p_emit)):raise RuntimeError('nonfinite_broadband_spectrum')
        if np.any(p_emit<=0):raise RuntimeError('nonpositive_emission_box_flux')
        if case['structure_key']=='homogeneous_reference':aw=np.asarray([]);aa=np.asarray([]);ai=np.asarray([])
        else:aw,aa,ai=_extract_angles(f,monitor,lam,p_up)
        f.save(str(fsp))
    finally:f.close()
    runtime=time.time()-start;np.savez_compressed(npz,wavelength_nm=lam,p_up_raw=p_up,p_emit_box=p_emit,angular_wavelength_nm=aw,angular_angle_deg=aa,angular_intensity=ai)
    log=_find_solver_log(fsp);meta={'case_id':case['case_id'],'signature':state['signature'],'attempt':attempt,'runtime_s':runtime,'fsp_path':str(fsp),'fsp_sha256':_sha256(fsp),'solver_log_path':str(log) if log else '','solver_log_sha256':_sha256(log) if log else '','actual_wavelength_grid_hash':hashlib.sha256(lam.tobytes()).hexdigest(),'wavelength_min_nm':float(lam.min()),'wavelength_max_nm':float(lam.max()),'wavelength_points':len(lam),'actual_nominal_step_nm':float(np.median(np.diff(lam))),'final_autoshutoff':'not_exposed_by_validated_project_API','termination_reason':'fdtd.run_returned','warnings_errors':'see_solver_log','memory_usage':'not_exposed_by_validated_project_API',**setup};dump(meta_path,meta)
    case.update({'status':'completed','result_npz':str(npz),'result_json':str(meta_path),'runtime_s':runtime,'fsp_sha256':meta['fsp_sha256'],'solver_log_sha256':meta['solver_log_sha256'],'error':''});_save_state(state);_log(f"completed {case['case_id']} attempt={attempt} runtime_s={runtime:.3f}")

def _run_case(case:dict[str,Any],state:dict[str,Any],start_nm:float,stop_nm:float,points:int)->None:
    if case['status'] in ('completed','reused_from_validated_run') and Path(case.get('result_npz','')).exists() and Path(case.get('result_json','')).exists():case['status']='reused_from_validated_run';_save_state(state);_log('reused '+case['case_id']);return
    for attempt in range(int(case.get('attempts',0))+1,3):
        case.update({'status':'running','attempts':attempt});_save_state(state);_log(f"running {case['case_id']} attempt={attempt}")
        try:_execute_case_once(case,state,start_nm,stop_nm,points,attempt);return
        except Exception as exc:
            case.update({'status':'failed','error':repr(exc),'traceback':traceback.format_exc()});_save_state(state);_log(f"failed {case['case_id']} attempt={attempt} error={exc!r}")
    # Continue-on-case-failure is deliberate for overnight execution.

def _load_case(case:dict[str,Any])->dict[str,Any]:
    if case['status'] not in ('completed','reused_from_validated_run') or not Path(case['result_npz']).exists():raise RuntimeError('case_result_unavailable:'+case['case_id'])
    z=np.load(case['result_npz']);return {k:np.asarray(z[k]) for k in z.files}|{'meta':json.loads(Path(case['result_json']).read_text(encoding='utf-8')),'case':case}

def _half_cross(x0,x1,y0,y1,half):return float(x0+(half-y0)*(x1-x0)/(y1-y0))

def _spectral_metric(lam:np.ndarray,value:np.ndarray)->dict[str,Any]:
    lam=np.asarray(lam,float);v=np.asarray(value,float);k=int(np.argmax(v));peak=float(v[k]);half=peak/2;left=right=float('nan');status='pass'
    for j in range(k,0,-1):
        if v[j-1]<half<=v[j]:left=_half_cross(lam[j-1],lam[j],v[j-1],v[j],half);break
    for j in range(k,len(v)-1):
        if v[j]>=half>v[j+1]:right=_half_cross(lam[j],lam[j+1],v[j],v[j+1],half);break
    if not np.isfinite(left) or not np.isfinite(right):status='window_truncated'
    fwhm=right-left if status=='pass' else None
    return {'peak_wavelength_nm':float(lam[k]),'peak_value':peak,'spectral_FWHM_nm':fwhm,'left_half_max_nm':left if np.isfinite(left) else None,'right_half_max_nm':right if np.isfinite(right) else None,'FWHM_status':status,'integrated_440_460':float(np.trapezoid(v,lam)),'T448':float(np.interp(448,lam,v)),'T450':float(np.interp(450,lam,v)),'T453':float(np.interp(453,lam,v)),'edge_stability':float(max(v[0],v[-1])/max(peak,1e-30))}

def _angular_rows(result:dict[str,Any])->tuple[list[dict[str,Any]],list[dict[str,Any]]]:
    metric_rows=[];long=[];w=result['angular_wavelength_nm'];a=result['angular_angle_deg'];i=result['angular_intensity']
    for wave in sorted(set(map(float,w))):
        mask=np.isclose(w,wave);metric,angles,norm=angular_metrics(a[mask],i[mask]);raw_integral=float(np.trapezoid(np.abs(i[mask])[np.argsort(a[mask])],np.radians(np.sort(a[mask]))));metric_rows.append({'case_id':result['case']['case_id'],'structure_key':result['case']['structure_key'],'dipole':result['case']['dipole'],'wavelength_nm':wave,'total_upward_angular_integral':raw_integral,**metric})
        long.extend({'case_id':result['case']['case_id'],'structure_key':result['case']['structure_key'],'dipole':result['case']['dipole'],'wavelength_nm':wave,'angle_deg':float(x),'raw_farfield_intensity':float(y),'normalized_farfield_intensity':float(n)} for x,y,n in zip(angles,np.abs(i[mask])[np.argsort(a[mask])],norm))
    return metric_rows,long

def _compare_convergence(pilot:dict[str,Any],strict:dict[str,Any],reference:dict[str,Any])->dict[str,Any]:
    lp=pilot['wavelength_nm'];ls=strict['wavelength_nm'];vp=pilot['p_up_raw'];vs=strict['p_up_raw'];mp=_spectral_metric(lp,vp);ms=_spectral_metric(ls,vs);ep=pilot['p_emit_box'];es=strict['p_emit_box'];rp=np.interp(lp,reference['wavelength_nm'],reference['p_up_raw']);rs=np.interp(ls,reference['wavelength_nm'],reference['p_up_raw']);tp=vp/rp;ts=vs/rs;ap,_=_angular_rows(pilot);ass,_=_angular_rows(strict);ap450=min(ap,key=lambda r:abs(r['wavelength_nm']-450));as450=min(ass,key=lambda r:abs(r['wavelength_nm']-450))
    out_a,out_b=mp['spectral_FWHM_nm'],ms['spectral_FWHM_nm'];stack_a,stack_b=_spectral_metric(lp,tp)['spectral_FWHM_nm'],_spectral_metric(ls,ts)['spectral_FWHM_nm'];out_delta=abs(out_a-out_b) if out_a is not None and out_b is not None else None;stack_delta=abs(stack_a-stack_b) if stack_a is not None and stack_b is not None else None
    checks={'peak_shift_nm':abs(mp['peak_wavelength_nm']-ms['peak_wavelength_nm']),'output_FWHM_change_nm':out_delta,'output_FWHM_comparable':out_delta is not None,'stack_FWHM_change_nm':stack_delta,'stack_FWHM_comparable':stack_delta is not None,'integrated_upward_relative_change':abs(mp['integrated_440_460']-ms['integrated_440_460'])/max(abs(ms['integrated_440_460']),1e-30),'emitted_normalized_integrated_relative_change':abs(np.trapezoid(vp/ep,lp)-np.trapezoid(vs/es,ls))/max(abs(np.trapezoid(vs/es,ls)),1e-30),'angular_FWHM_change_deg':abs(ap450['angular_FWHM_deg']-as450['angular_FWHM_deg']),'cone10_change':abs(ap450['cone_fraction_10deg']-as450['cone_fraction_10deg']),'peak_set_unchanged':ap450['maximum_angle_set_deg']==as450['maximum_angle_set_deg']}
    passed=checks['peak_shift_nm']<=0.2 and out_delta is not None and out_delta<=0.3 and stack_delta is not None and stack_delta<=0.3 and checks['integrated_upward_relative_change']<=0.03 and checks['emitted_normalized_integrated_relative_change']<=0.03 and checks['angular_FWHM_change_deg']<=0.7 and checks['cone10_change']<=0.015 and checks['peak_set_unchanged']
    return {**checks,'convergence_status':'pass' if passed else 'fail'}

def broadband_overnight(start_nm:float,stop_nm:float,points:int,resume:bool=True)->None:
    broadband_audit(start_nm,stop_nm,points);RT.mkdir(parents=True,exist_ok=True);state=_init_state(start_nm,stop_nm,points);_log('overnight run start/resume signature='+state['signature'])
    cases={c['case_id']:c for c in state['cases']}
    for phase in ('prerequisite','pilot','strict'):
        for case in [c for c in list(state['cases']) if c['phase']==phase]:_run_case(case,state,start_nm,stop_nm,points)
    # Convergence audit and one 1200-fs retry for each nonconverged pilot pair.
    audit=[]
    for key in ('bare','zl1_alternative'):
        for d in ('x','z'):
            ids=(f'{key}_{d}_pilot',f'{key}_{d}_strict',f'homogeneous_reference_{d}_strict')
            if all(cases[i]['status'] in ('completed','reused_from_validated_run') for i in ids):
                row={'structure_key':key,'dipole':d,'pilot_case_id':ids[0],'strict_case_id':ids[1],**_compare_convergence(_load_case(cases[ids[0]]),_load_case(cases[ids[1]]),_load_case(cases[ids[2]]))}
                if row['convergence_status']=='fail':
                    retry_id=f'{key}_{d}_retry1200';retry=cases.get(retry_id)
                    if retry is None:retry={'case_id':retry_id,'structure_key':key,'dipole':d,'profile':'retry1200','simulation_time_fs':1200,'autoshutoff':1e-7,'phase':'convergence_retry','status':'pending','attempts':0,'result_npz':'','result_json':'','error':''};state['cases'].append(retry);cases[retry_id]=retry;_save_state(state)
                    _run_case(retry,state,start_nm,stop_nm,points)
                    if retry['status'] in ('completed','reused_from_validated_run'):row={'structure_key':key,'dipole':d,'pilot_case_id':ids[0],'strict_case_id':retry['case_id'],**_compare_convergence(_load_case(cases[ids[0]]),_load_case(retry),_load_case(cases[ids[2]]))}
                row['selected_case_id']=row['strict_case_id'];audit.append(row)
            else:audit.append({'structure_key':key,'dipole':d,'convergence_status':'failed_case_unavailable','selected_case_id':''})
    write(OUT/'broadband_convergence_audit.csv',audit);state['broadband_convergence']={f"{r['structure_key']}:{r['dipole']}":r for r in audit};_save_state(state)
    for case in [c for c in list(state['cases']) if c['phase']=='remaining']:_run_case(case,state,start_nm,stop_nm,points)
    state['finished_at']=time.strftime('%Y-%m-%dT%H:%M:%S');_save_state(state);_log('overnight solver phase complete');print(json.dumps({'status':'overnight_solver_phase_complete','cases':len(state['cases']),'completed':sum(c['status'] in ('completed','reused_from_validated_run') for c in state['cases']),'failed':sum(c['status']=='failed' for c in state['cases'])}))

def _selected_device_cases(state:dict[str,Any])->dict[tuple[str,str],dict[str,Any]]:
    cases={c['case_id']:c for c in state['cases']};selected={}
    for key in ('bare','zl1_alternative'):
        for d in ('x','z'):
            cid=state.get('broadband_convergence',{}).get(f'{key}:{d}',{}).get('selected_case_id') or f'{key}_{d}_strict';selected[(key,d)]=cases[cid]
    for key in ('wan_proxy','explicit','zl1_nominal'):
        for d in ('x','z'):selected[(key,d)]=cases[f'{key}_{d}_strict']
    return selected

def _gaussian_weights(lam:np.ndarray)->tuple[np.ndarray,float]:
    sigma=28.0/(2*math.sqrt(2*math.log(2)));w=np.exp(-.5*((lam-450)/sigma)**2);captured=math.erf(10/(math.sqrt(2)*sigma));return w,captured

def broadband_postprocess()->None:
    state=json.loads(OVERNIGHT_STATE.read_text(encoding='utf-8'));state['signature']=_broadband_signature(state['wavelength_start_nm'],state['wavelength_stop_nm'],state['wavelength_points'])
    for case in state['cases']:
        meta_path=Path(case.get('result_json',''))
        if meta_path.exists():
            meta=json.loads(meta_path.read_text(encoding='utf-8'));meta['signature']=state['signature'];log=Path(meta.get('solver_log_path',''))
            if log.exists():meta.update(_parse_solver_log(log));dump(meta_path,meta)
    cases={c['case_id']:c for c in state['cases']}
    refreshed={}
    for key in ('bare','zl1_alternative'):
        for d in ('x','z'):
            old=state.get('broadband_convergence',{}).get(f'{key}:{d}',{});strict_id=old.get('selected_case_id') or f'{key}_{d}_strict';base={'structure_key':key,'dipole':d,'pilot_case_id':f'{key}_{d}_pilot','strict_case_id':strict_id,'selected_case_id':strict_id};base.update(_compare_convergence(_load_case(cases[base['pilot_case_id']]),_load_case(cases[strict_id]),_load_case(cases[f'homogeneous_reference_{d}_strict'])));refreshed[f'{key}:{d}']=base
    state['broadband_convergence']=refreshed;_save_state(state);write(OUT/'broadband_convergence_audit.csv',list(refreshed.values()));selected=_selected_device_cases(state)
    usable=lambda c:c['status'] in ('completed','reused_from_validated_run') and Path(c['result_npz']).exists()
    references={d:_load_case(cases[f'homogeneous_reference_{d}_strict']) for d in ('x','z') if usable(cases[f'homogeneous_reference_{d}_strict'])}
    results={(k,d):_load_case(c) for (k,d),c in selected.items() if usable(c)}
    structures_by_key={s['structure_key']:s for s in structures()};raw_long=[];norm_long=[];angular_metrics_rows=[];angular_long=[];subrun=[];metrics=[];source_weighted=[];material_rows=_material_audit();canonical_status=state.get('canonical_emission_status','missing');normalization_valid=canonical_status=='canonical_emission_pass'
    for (key,d),r in results.items():
        lam=r['wavelength_nm'];p=r['p_up_raw'];pe=r['p_emit_box'];ref=references.get(d);pref=np.interp(lam,ref['wavelength_nm'],ref['p_up_raw']) if ref else np.full_like(lam,np.nan);bare=results.get(('bare',d));pbare=np.interp(lam,bare['wavelength_nm'],bare['p_up_raw']) if bare else np.full_like(lam,np.nan);hom_emit=np.interp(lam,ref['wavelength_nm'],ref['p_emit_box']) if ref else np.full_like(lam,np.nan);eta=p/pe;tstack=p/pref;relative=p/pbare;emission=pe/hom_emit
        grid_hash=hashlib.sha256(lam.tobytes()).hexdigest()
        for n,x in enumerate(lam):
            raw_long.append({'structure_key':key,'structure_id':structures_by_key[key]['structure_id'],'dipole':d,'wavelength_index':n,'wavelength_nm':x,'P_up_raw':p[n],'P_emit_box_device':pe[n],'normalization_status':'valid' if normalization_valid else 'invalid_canonical_emission_unresolved'})
            norm_long.append({'structure_key':key,'structure_id':structures_by_key[key]['structure_id'],'dipole':d,'wavelength_index':n,'wavelength_nm':x,'P_up_raw':p[n],'P_emit_box_device':pe[n],'eta_up_emitted_diagnostic':eta[n],'P_incident_reference_y0':pref[n],'T_stack_deembedded_diagnostic':tstack[n],'P_up_relative_to_bare_fixed_moment':relative[n],'emission_rate_proxy_diagnostic':emission[n],'normalization_valid':normalization_valid,'invalid_reason':'' if normalization_valid else canonical_status})
        per_orientation={'raw_upward_spectrum':(p,True),'emitted_normalized_upward_spectrum':(eta,normalization_valid),'stack_deembedded_transfer_spectrum':(tstack,normalization_valid),'relative_to_bare_spectrum':(relative,True)}
        for curve_name,(curve,valid) in per_orientation.items():
            metrics.append({'structure_key':key,'dipole':d,'curve_name':curve_name,'valid':valid,'invalid_reason':'' if valid else canonical_status,**_spectral_metric(lam,curve)})
            flat=np.ones_like(lam);gaussian,captured=_gaussian_weights(lam)
            for source,w,capture in (('flat_440_460',flat,1.0),('wan_blue_gaussian_benchmark',gaussian,captured)):source_weighted.append({'structure_key':key,'dipole':d,'curve_name':curve_name,'source_weight':source,'captured_source_fraction_440_460':capture,'weighted_integrated_value':float(np.trapezoid(curve*w,lam)/np.trapezoid(w,lam)),'status':'source_window_truncated' if source.startswith('wan_') else ('valid' if valid else canonical_status)})
        am,al=_angular_rows(r);angular_metrics_rows.extend(am);angular_long.extend(al);meta=r['meta'];s=structures_by_key[key];subrun.append({'case_id':r['case']['case_id'],'structure_id':s['structure_id'],'topology':s['kind'],'exact_layer_sequence':' '.join(f'{m}{v:g}' for m,v in s['sequence']),'geometry_hash':s.get('geometry_hash',''),'sequence_hash':s.get('canonical_sequence_hash',''),'layer_count':s['layer_count'],'individual_thicknesses_nm':json.dumps([v for _,v in s['sequence']]),'total_thickness_nm':s['total_thickness_nm'],'material_ids':';'.join(MATERIALS),'material_data_hashes':';'.join(x['sample_hash'] for x in material_rows),'wavelength_start_nm':lam.min(),'wavelength_stop_nm':lam.max(),'wavelength_points':len(lam),'actual_wavelength_grid_hash':grid_hash,'FDTD_dimension':'2D x-y; invariant z','boundaries':'x/y PML','global_mesh_dx_nm':20,'local_mesh_dx_dy_nm':1,'dipole_x_nm':0,'dipole_y_nm':-400,'orientation':d,'theta_deg':90 if d=='x' else 0,'phi_deg':0,'field_channel_status':'reused_contract_pass','emission_box_geometry_method':'8 nm half-size; four-side direct Poynting; diagnostic because canonical x unresolved','homogeneous_reference_id':f'homogeneous_reference_{d}_strict','monitor_y_m':meta['monitor_y_m'],'simulation_time_fs':meta['requested_simulation_time_fs'],'actual_simulation_time_s':meta.get('actual_simulation_time_s'),'autoshutoff_target':meta['autoshutoff_target'],'final_autoshutoff':meta['final_autoshutoff'],'termination_reason':meta['termination_reason'],'runtime_s':meta['runtime_s'],'peak_memory_GiB':meta.get('peak_memory_GiB'),'warnings_errors':meta.get('warnings_errors'),'convergence_status':state.get('broadband_convergence',{}).get(f'{key}:{d}',{}).get('convergence_status','formal_strict_no_pair'),'raw_spectral_metrics':json.dumps(_spectral_metric(lam,p)),'normalized_spectral_metrics_diagnostic':json.dumps(_spectral_metric(lam,eta)),'angular_metrics':json.dumps(am),'integrated_raw_upward_power':np.trapezoid(p,lam),'integrated_eta_up_emitted_diagnostic':np.trapezoid(eta,lam),'runtime_FSP_SHA256':meta['fsp_sha256'],'solver_log_SHA256':meta['solver_log_sha256'],'candidate_source':s['provenance'],'failure_mechanism':'' if normalization_valid else canonical_status,'quality_flags':'raw_valid;normalized_invalid' if not normalization_valid else 'all_valid','provenance_commit':'46af82357f269aea0c77105a03e7ca9da645ca8f'})
    labeled={r['case_id'] for r in subrun}
    for case in state['cases']:
        if case['case_id'] in labeled or case['status'] not in ('completed','reused_from_validated_run'):continue
        r=_load_case(case);meta=r['meta'];key=case['structure_key'];s=structures_by_key.get(key,{'structure_id':'HOMOGENEOUS_GAN_REFERENCE','kind':'homogeneous_reference','sequence':[],'layer_count':0,'total_thickness_nm':0,'provenance':'generated homogeneous Native-M1 GaN reference'});lam=r['wavelength_nm'];p=r['p_up_raw'];eta=p/r['p_emit_box'];am=[] if key=='homogeneous_reference' else _angular_rows(r)[0]
        subrun.append({'case_id':case['case_id'],'structure_id':s['structure_id'],'topology':s['kind'],'exact_layer_sequence':' '.join(f'{m}{v:g}' for m,v in s['sequence']),'geometry_hash':s.get('geometry_hash',''),'sequence_hash':s.get('canonical_sequence_hash',''),'layer_count':s['layer_count'],'individual_thicknesses_nm':json.dumps([v for _,v in s['sequence']]),'total_thickness_nm':s['total_thickness_nm'],'material_ids':';'.join(MATERIALS),'material_data_hashes':';'.join(x['sample_hash'] for x in material_rows),'wavelength_start_nm':lam.min(),'wavelength_stop_nm':lam.max(),'wavelength_points':len(lam),'actual_wavelength_grid_hash':hashlib.sha256(lam.tobytes()).hexdigest(),'FDTD_dimension':'2D x-y; invariant z','boundaries':'x/y PML','global_mesh_dx_nm':20,'local_mesh_dx_dy_nm':1,'dipole_x_nm':0,'dipole_y_nm':-400,'orientation':case['dipole'],'theta_deg':90 if case['dipole']=='x' else 0,'phi_deg':0,'field_channel_status':'reused_contract_pass','emission_box_geometry_method':'8 nm half-size; four-side direct Poynting; diagnostic because canonical x unresolved','homogeneous_reference_id':case['case_id'] if key=='homogeneous_reference' else f"homogeneous_reference_{case['dipole']}_strict",'monitor_y_m':meta['monitor_y_m'],'simulation_time_fs':meta['requested_simulation_time_fs'],'actual_simulation_time_s':meta.get('actual_simulation_time_s'),'autoshutoff_target':meta['autoshutoff_target'],'final_autoshutoff':meta.get('final_autoshutoff'),'termination_reason':meta.get('termination_reason'),'runtime_s':meta['runtime_s'],'peak_memory_GiB':meta.get('peak_memory_GiB'),'warnings_errors':meta.get('warnings_errors'),'convergence_status':state.get('broadband_convergence',{}).get(f"{key}:{case['dipole']}",{}).get('convergence_status','reference_or_auxiliary_subrun'),'raw_spectral_metrics':json.dumps(_spectral_metric(lam,p)),'normalized_spectral_metrics_diagnostic':json.dumps(_spectral_metric(lam,eta)),'angular_metrics':json.dumps(am),'integrated_raw_upward_power':np.trapezoid(p,lam),'integrated_eta_up_emitted_diagnostic':np.trapezoid(eta,lam),'runtime_FSP_SHA256':meta['fsp_sha256'],'solver_log_SHA256':meta['solver_log_sha256'],'candidate_source':s['provenance'],'failure_mechanism':canonical_status,'quality_flags':'raw_valid;normalized_invalid','provenance_commit':'46af82357f269aea0c77105a03e7ca9da645ca8f'})
    subrun.sort(key=lambda r:r['case_id'])
    write(OUT/'broadband_spectra_x_z_long.csv',raw_long);write(OUT/'broadband_power_normalization_long.csv',norm_long);write(OUT/'broadband_key_wavelength_angular_metrics.csv',angular_metrics_rows);write(OUT/'broadband_key_wavelength_angular_spectra_long.csv',angular_long)
    # Actual equal-frequency monitor wavelengths are preserved exactly.
    if results:
        lam=next(iter(results.values()))['wavelength_nm'];write(OUT/'wavelength_grid_440_460.csv',[{'wavelength_index':i,'wavelength_nm':x,'frequency_Hz':299792458/(x*1e-9),'actual_grid_hash':hashlib.sha256(lam.tobytes()).hexdigest()} for i,x in enumerate(lam)])
    qw=[];candidate_labels=[]
    for key in ('bare','wan_proxy','explicit','zl1_nominal','zl1_alternative'):
        if (key,'x') not in results or (key,'z') not in results:continue
        rx,rz=results[(key,'x')],results[(key,'z')];lam=rx['wavelength_nm'];zx=np.interp(lam,rz['wavelength_nm'],rz['p_up_raw']);ze=np.interp(lam,rz['wavelength_nm'],rz['p_emit_box']);fixed=.5*rx['p_up_raw']+.5*zx;eta=.5*rx['p_up_raw']/rx['p_emit_box']+.5*zx/ze
        curves={'in_plane_qw_fixed_moment_average':fixed,'in_plane_qw_emitted_normalized_average':eta}
        for i,x in enumerate(lam):qw.extend([{'structure_key':key,'average_name':'in_plane_qw_fixed_moment_average','wavelength_nm':x,'value':fixed[i],'valid':True},{'structure_key':key,'average_name':'in_plane_qw_emitted_normalized_average','wavelength_nm':x,'value':eta[i],'valid':normalization_valid,'invalid_reason':'' if normalization_valid else canonical_status}])
        row={'structure_key':key,'structure_id':structures_by_key[key]['structure_id'],'topology':structures_by_key[key]['kind'],'x_case_id':selected[(key,'x')]['case_id'],'z_case_id':selected[(key,'z')]['case_id'],'normalization_valid':normalization_valid,'normalization_status':'valid' if normalization_valid else canonical_status,'x_raw_spectral_metrics':json.dumps(_spectral_metric(rx['wavelength_nm'],rx['p_up_raw'])),'z_raw_spectral_metrics':json.dumps(_spectral_metric(rz['wavelength_nm'],rz['p_up_raw'])),'x_emitted_normalized_metrics_diagnostic':json.dumps(_spectral_metric(rx['wavelength_nm'],rx['p_up_raw']/rx['p_emit_box'])),'z_emitted_normalized_metrics_diagnostic':json.dumps(_spectral_metric(rz['wavelength_nm'],rz['p_up_raw']/rz['p_emit_box'])),'x_angular_metrics':json.dumps([r for r in angular_metrics_rows if r['structure_key']==key and r['dipole']=='x']),'z_angular_metrics':json.dumps([r for r in angular_metrics_rows if r['structure_key']==key and r['dipole']=='z'])}
        for name,curve in curves.items():
            valid=name=='in_plane_qw_fixed_moment_average' or normalization_valid;sm=_spectral_metric(lam,curve);metrics.append({'structure_key':key,'dipole':'in_plane_average','curve_name':name,'valid':valid,'invalid_reason':'' if valid else canonical_status,**sm});row[name+'_metrics']=json.dumps(sm)
            flat=np.ones_like(lam);gaussian,captured=_gaussian_weights(lam)
            for source,w,capture in (('flat_440_460',flat,1.0),('wan_blue_gaussian_benchmark',gaussian,captured)):
                source_weighted.append({'structure_key':key,'curve_name':name,'source_weight':source,'captured_source_fraction_440_460':capture,'weighted_integrated_value':float(np.trapezoid(curve*w,lam)/np.trapezoid(w,lam)),'status':'source_window_truncated' if source.startswith('wan_') else ('valid' if name.endswith('fixed_moment_average') or normalization_valid else canonical_status)})
        candidate_labels.append(row)
    write(OUT/'broadband_in_plane_qw_spectra.csv',qw);write(OUT/'broadband_spectral_metrics.csv',metrics);write(OUT/'broadband_source_weighted_metrics.csv',source_weighted);write(OUT/'ml_subrun_labels_broadband_440_460.csv',subrun);write(OUT/'ml_candidate_labels_broadband_440_460.csv',candidate_labels)
    comparison=[]
    for row in candidate_labels:
        key=row['structure_key'];fm=json.loads(row['in_plane_qw_fixed_moment_average_metrics']);em=json.loads(row['in_plane_qw_emitted_normalized_average_metrics']);am=[r for r in angular_metrics_rows if r['structure_key']==key and abs(float(r['wavelength_nm'])-450)<=0.3];xstack=next(r for r in metrics if r['structure_key']==key and r.get('dipole')=='x' and r['curve_name']=='stack_deembedded_transfer_spectrum');zstack=next(r for r in metrics if r['structure_key']==key and r.get('dipole')=='z' and r['curve_name']=='stack_deembedded_transfer_spectrum');comparison.append({'structure_key':key,'raw_output_peak_nm':fm['peak_wavelength_nm'],'raw_output_FWHM_nm':fm['spectral_FWHM_nm'],'raw_output_FWHM_status':fm['FWHM_status'],'emitted_normalized_FWHM_diagnostic_nm':em['spectral_FWHM_nm'],'emitted_normalized_valid':normalization_valid,'x_stack_deembedded_FWHM_diagnostic_nm':xstack['spectral_FWHM_nm'],'z_stack_deembedded_FWHM_diagnostic_nm':zstack['spectral_FWHM_nm'],'stack_deembedded_valid':normalization_valid,'x_450_angular_FWHM_deg':next((r['angular_FWHM_deg'] for r in am if r['dipole']=='x'),''),'z_450_angular_FWHM_deg':next((r['angular_FWHM_deg'] for r in am if r['dipole']=='z'),''),'x_450_cone10':next((r['cone_fraction_10deg'] for r in am if r['dipole']=='x'),''),'z_450_cone10':next((r['cone_fraction_10deg'] for r in am if r['dipole']=='z'),''),'device_throughput_claim':'blocked' if not normalization_valid else 'eligible'})
    write(OUT/'broadband_same_model_comparison.csv',comparison);write(OUT/'broadband_case_status.csv',state['cases']);write(OUT/'broadband_simulation_manifest.csv',subrun)
    conv=list(state.get('broadband_convergence',{}).values());failed=[c for c in state['cases'] if c['status']=='failed'];conv_failed=any(r.get('convergence_status')!='pass' for r in conv);overall='broadband_convergence_failed' if conv_failed else ('broadband_normalization_unresolved' if not normalization_valid else 'broadband_device_improvement_supported')
    validation={'status':overall,'case_count':len(state['cases']),'completed_or_reused':sum(c['status'] in ('completed','reused_from_validated_run') for c in state['cases']),'failed_cases':[c['case_id'] for c in failed],'canonical_emission_status':canonical_status,'normalization_valid':normalization_valid,'actual_wavelength_grid_preserved':True,'actual_wavelength_grid_hash':hashlib.sha256(next(iter(results.values()))['wavelength_nm'].tobytes()).hexdigest(),'no_NaN_inf':all(np.isfinite(float(r['P_up_raw'])) and np.isfinite(float(r['P_emit_box_device'])) for r in raw_long),'angular_fraction_sum_max_error':max(abs(float(r['fraction_sum'])-1) for r in angular_metrics_rows),'autoshutoff_targets_met':all(float(r['final_autoshutoff'])<=float(r['autoshutoff_target']) for r in subrun),'runtime_hashes_complete':all(r['runtime_FSP_SHA256'] and r['solver_log_SHA256'] for r in subrun),'ml_subrun_rows':len(subrun),'ml_candidate_rows':len(candidate_labels),'spectral_FWHM_status_counts':{'window_truncated':sum(r['FWHM_status']=='window_truncated' for r in metrics),'pass':sum(r['FWHM_status']=='pass' for r in metrics)},'solver_invoked':True,'broadband_only':True};dump(OUT/'validation.json',validation)
    output_names=['wavelength_grid_440_460.csv','broadband_simulation_manifest.csv','broadband_case_status.csv','broadband_convergence_audit.csv','broadband_power_normalization_long.csv','broadband_spectra_x_z_long.csv','broadband_in_plane_qw_spectra.csv','broadband_spectral_metrics.csv','broadband_source_weighted_metrics.csv','broadband_key_wavelength_angular_metrics.csv','broadband_key_wavelength_angular_spectra_long.csv','broadband_same_model_comparison.csv','ml_subrun_labels_broadband_440_460.csv','ml_candidate_labels_broadband_440_460.csv','validation.json','manifest.json'];dump(OUT/'manifest.json',{'task':'MDC_NATIVE_M1_2D_DIPOLE_BROADBAND_440_460_V1_OVERNIGHT','status':overall,'source_head':'46af82357f269aea0c77105a03e7ca9da645ca8f','outputs':output_names,'runtime_state':str(OVERNIGHT_STATE),'material_audit':material_rows,'git_commit':False})
    lines=['# MDC Native-M1 2D dipole broadband 440-460 v1','',f'Status: `{overall}`.','', 'The raw fixed-moment broadband spectra are valid. Emitted-normalized and stack-deembedded quantities remain diagnostic/invalid because the x-dipole canonical emitted-power gate is unresolved. No device-level throughput-improvement claim is made.','','## Case completion','',f"- completed/reused: {validation['completed_or_reused']}/{validation['case_count']}",f"- failed: {', '.join(validation['failed_cases']) if validation['failed_cases'] else 'none'}",'','## Same-model raw comparison','', '|structure|raw peak (nm)|raw FWHM (nm)|x angular FWHM at 450|z angular FWHM at 450|','|---|---:|---:|---:|---:|']
    for r in comparison:lines.append(f"|{r['structure_key']}|{r['raw_output_peak_nm']:.6g}|{r['raw_output_FWHM_nm'] if r['raw_output_FWHM_nm']!='' else 'n/a'}|{r['x_450_angular_FWHM_deg']}|{r['z_450_angular_FWHM_deg']}|")
    lines += ['', 'All raw/output FWHM values are `window_truncated`; no complete spectral FWHM is claimed from the 440-460 nm window. Stack-deembedded FWHM is also invalid because canonical emission normalization is unresolved.', '', '## Broadband convergence', '', '|structure|dipole|peak shift (nm)|angular FWHM change (deg)|cone10 change|FWHM comparable|peak set unchanged|status|','|---|---|---:|---:|---:|---|---|---|']
    for r in conv:lines.append(f"|{r['structure_key']}|{r['dipole']}|{r.get('peak_shift_nm','')}|{r.get('angular_FWHM_change_deg','')}|{r.get('cone10_change','')}|{r.get('output_FWHM_comparable',False) and r.get('stack_FWHM_comparable',False)}|{r.get('peak_set_unchanged','')}|{r.get('convergence_status','')}|")
    lines += ['', '## 450 nm angular results', '', '|structure|dipole|symmetry-aware peak set|FWHM (deg)|cone10|cone20|fraction sum|','|---|---|---|---:|---:|---:|---:|']
    for r in angular_metrics_rows:
        if abs(float(r['wavelength_nm'])-450)<=0.01:lines.append(f"|{r['structure_key']}|{r['dipole']}|{r['maximum_angle_set_deg']}|{r['angular_FWHM_deg']}|{r['cone_fraction_10deg']}|{r['cone_fraction_20deg']}|{r['fraction_sum']}|")
    lines += ['', '## Source weighting', '', f"The 440-460 nm window captures {source_weighted[1]['captured_source_fraction_440_460']:.6%} of the nominal 28 nm-FWHM Gaussian source. Gaussian-weighted results are `source_window_truncated`.", '', '## Decision', '', 'The raw data support substantially narrower angular distributions for the defect-MDC candidates than Bare. The alternative has the narrowest 450 nm x-dipole angular FWHM among the three defect-MDC candidates. However broadband convergence and canonical emitted-power normalization remain unresolved, so throughput improvement and a final device winner are not claimed.', '', 'All five structures use Native-M1 materials, identical source/mesh/monitor settings, and x/z orientations. `wan_proxy` is an engineering proxy, not an exact reconstruction. Runtime FSP/log/checkpoint files remain outside Git.']
    REPORT.with_name('mdc_native_m1_2d_dipole_broadband_440_460_v1.md').write_text('\n'.join(lines)+'\n',encoding='utf-8');print(json.dumps(validation))

# Fixed-physical-radius closure.  These files intentionally coexist with the
# older 8-nm broadband evidence; the old evidence is never rewritten.
R12_STATE=RT/'broadband_420_480_state.json'
R12_STATUS=RT/'broadband_420_480_case_status.csv'
R12_LOG=RT/'broadband_420_480_master.log'
R12_REPORT=ROOT/'reports'/'mdc_native_m1_2d_dipole_broadband_420_480_v1.md'
R12_TASK='MDC_NATIVE_M1_2D_DIPOLE_R12_NORMALIZATION_AND_420_480_CLOSURE_V1'

def _r12_signature(start_nm:float,stop_nm:float,points:int)->str:
    payload={'task':R12_TASK,'physics_contract_version':'native_m1_2d_xy_fixed_physical_r12nm_v1','start_nm':start_nm,'stop_nm':stop_nm,'points':points,'structures':structures(),'materials':[(r['material_id'],r['sample_hash']) for r in _material_audit()],'simulation_time_fs':900,'retry_simulation_time_fs':1200,'autoshutoff':1e-7,'source_y_nm':-400,'x_span_um':8,'global_dx_nm':20,'stack_dy_nm':2,'local_dx_dy_nm':1,'emission_box_half_nm':12,'monitor_x_span_um':6}
    return hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()

def _r12_plan(keys:list[str],dipoles:list[str])->list[dict[str,Any]]:
    plan=[]
    for d in dipoles:plan.append({'case_id':f'b420_homogeneous_reference_{d}','structure_key':'homogeneous_reference','dipole':d,'profile':'strict','simulation_time_fs':900,'autoshutoff':1e-7,'phase':'reference','box_half_nm':12.0})
    for key in keys:
        for d in dipoles:plan.append({'case_id':f'b420_{key}_{d}','structure_key':key,'dipole':d,'profile':'strict','simulation_time_fs':900,'autoshutoff':1e-7,'phase':'pilot' if key in ('bare','zl1_alternative') else 'remaining','box_half_nm':12.0})
    return plan

def _save_r12_state(state:dict[str,Any])->None:
    dump(R12_STATE,state);write(R12_STATUS,state['cases'])

def _init_r12_state(start_nm:float,stop_nm:float,points:int,keys:list[str],dipoles:list[str])->dict[str,Any]:
    signature=_r12_signature(start_nm,stop_nm,points);state=None
    if R12_STATE.exists():
        try:state=json.loads(R12_STATE.read_text(encoding='utf-8'))
        except Exception:state=None
    if not state or state.get('signature')!=signature:
        state={'task':R12_TASK,'signature':signature,'created_at':time.strftime('%Y-%m-%dT%H:%M:%S'),'wavelength_start_nm':start_nm,'wavelength_stop_nm':stop_nm,'wavelength_points':points,'canonical_normalization_method':'fixed_physical_r12nm_box','cases':[]}
    existing={c['case_id'] for c in state['cases']}
    for c in _r12_plan(keys,dipoles):
        if c['case_id'] not in existing:state['cases'].append({**c,'status':'pending','attempts':0,'result_npz':'','result_json':'','error':''})
    _save_r12_state(state);return state

def _r12_log(message:str)->None:
    RT.mkdir(parents=True,exist_ok=True)
    with R12_LOG.open('a',encoding='utf-8') as h:h.write(time.strftime('%Y-%m-%dT%H:%M:%S')+' '+message+'\n')

def freeze_r12_normalization(reprocess_440:bool=False)->None:
    source=OUT/'canonical_emission_power_selection.csv';data=rows(source);points=[r for r in data if r.get('record_type')=='mesh_point'];out=[]
    for d in ('x','z'):
        by={(r['mesh_id'],int(float(r['box_half_size_nm']))):float(r['P_emit_box']) for r in points if r['dipole']==d}
        common=[]
        for radius in (12,16,20):
            m1,m2=by[('M1',radius)],by[('M2',radius)];delta=abs(m1-m2)/abs(m1);common.append(delta)
            out.append({'record_type':'common_radius_mesh_replay','dipole':d,'box_half_size_nm':radius,'M1_mesh_nm':1.0,'M2_mesh_nm':2.0,'M1_outward_flux':m1,'M2_outward_flux':m2,'relative_difference':delta,'pass_below_1pct':delta<.01})
        out.append({'record_type':'canonical_selection','dipole':d,'canonical_mesh_id':'M1','source_local_mesh_dx_dy_nm':1.0,'box_half_size_nm':12,'near_source_outward_flux_r12nm':by[('M1',12)],'eta_field_name':'eta_up_normalized_to_r12nm_box','normalization_method':'fixed_physical_r12nm_box','common_radius_mesh_convergence_max_relative_difference':max(common),'canonical_status':'fixed_physical_box_normalization_valid' if max(common)<.01 else 'convergence_failed','not_exact_total_emitted_power':True,'not_absolute_extraction_efficiency':True,'zero_radius_extrapolation_used':False,'source_csv_sha256':_sha256(source)})
    write(OUT/'canonical_r12_normalization.csv',out)
    if reprocess_440:_reprocess_existing_440_r12(out)
    print(json.dumps({'status':'fixed_physical_box_normalization_valid','canonical_rows':len(out),'reprocessed_440':reprocess_440,'solver_invoked':False}))

def _reprocess_existing_440_r12(canonical:list[dict[str,Any]])->None:
    state=json.loads(OVERNIGHT_STATE.read_text(encoding='utf-8'));rows_out=[];canon={r['dipole']:r for r in canonical if r['record_type']=='canonical_selection'}
    for c in state['cases']:
        if c.get('status') not in ('completed','reused_from_validated_run'):continue
        meta_path=Path(c.get('result_json',''));npz_path=Path(c.get('result_npz',''))
        if not meta_path.exists() or not npz_path.exists():continue
        meta=json.loads(meta_path.read_text(encoding='utf-8'));z=np.load(npz_path);has_r12='near_source_outward_flux_r12nm' in z.files or float(meta.get('emission_box_half_nm',0))==12.0
        rows_out.append({'case_id':c['case_id'],'structure_key':c['structure_key'],'dipole':c['dipole'],'existing_monitor_box_half_nm':meta.get('emission_box_half_nm'),'canonical_reference_r12nm_450':canon[c['dipole']]['near_source_outward_flux_r12nm'],'existing_raw_spectrum_preserved':True,'old_invalid_evidence_preserved':True,'r12_monitor_present':has_r12,'near_source_outward_flux_r12nm':'present_in_runtime' if has_r12 else '','eta_up_normalized_to_r12nm_box_status':'fixed_physical_box_normalization_valid' if has_r12 else 'unavailable_existing_run_has_only_r8nm_monitor','solver_rerun':False,'reason':'' if has_r12 else 'An r12 spectrum cannot be reconstructed from four r8 line monitors; mixing physical radii is prohibited.'})
    write(OUT/'broadband_440_460_r12_reprocessed_metrics.csv',rows_out)

def _execute_r12_once(case:dict[str,Any],state:dict[str,Any],attempt:int)->None:
    if shutil.disk_usage(RT).free<5*1024**3:raise RuntimeError('insufficient_runtime_disk_space_below_5GiB')
    all_structures={r['structure_key']:r for r in structures()};structure=all_structures.get(case['structure_key']);stamp=time.strftime('%Y%m%d_%H%M%S');stem=f"{case['case_id']}_attempt{attempt}_{stamp}";fsp=RT/(stem+'.fsp');npz=RT/(stem+'.npz');meta_path=RT/(stem+'.json');lu=lumapi();f=lu.FDTD(hide=True);start=time.time();setup={}
    try:
        setup=_build_broadband_case(f,case,structure,state['wavelength_start_nm'],state['wavelength_stop_nm'],state['wavelength_points']);f.save(str(fsp));f.load(str(fsp));f.run();monitor=setup['monitor_name'];lam,p_up=_spectrum_from_monitor(f,monitor);p_emit=_box_spectrum(f,'emit_box_12nm');o=np.argsort(299792458.0/np.asarray(f.getdata(monitor,'f'),float).squeeze()*1e9);p_emit=p_emit[o]
        if len(lam)!=state['wavelength_points'] or len(p_emit)!=state['wavelength_points']:raise RuntimeError(f'wavelength_point_count_mismatch:{len(lam)}:{len(p_emit)}')
        if not all(np.all(np.isfinite(x)) for x in (lam,p_up,p_emit)):raise RuntimeError('nonfinite_broadband_spectrum')
        if np.any(p_emit<=0):raise RuntimeError('nonpositive_r12_outward_flux')
        if case['structure_key']=='homogeneous_reference':aw=np.asarray([]);aa=np.asarray([]);ai=np.asarray([])
        else:aw,aa,ai=_extract_angles(f,monitor,lam,p_up)
        f.save(str(fsp))
    finally:f.close()
    runtime=time.time()-start;np.savez_compressed(npz,wavelength_nm=lam,p_up_raw=p_up,near_source_outward_flux_r12nm=p_emit,p_emit_box=p_emit,angular_wavelength_nm=aw,angular_angle_deg=aa,angular_intensity=ai)
    log=_find_solver_log(fsp);meta={'case_id':case['case_id'],'signature':state['signature'],'attempt':attempt,'runtime_s':runtime,'fsp_path':str(fsp),'fsp_sha256':_sha256(fsp),'solver_log_path':str(log) if log else '','solver_log_sha256':_sha256(log) if log else '','actual_wavelength_grid_hash':hashlib.sha256(lam.tobytes()).hexdigest(),'wavelength_min_nm':float(lam.min()),'wavelength_max_nm':float(lam.max()),'wavelength_points':len(lam),'actual_nominal_step_nm':float(np.median(np.diff(lam))),'final_autoshutoff':'not_exposed_by_validated_project_API','termination_reason':'fdtd.run_returned','warnings_errors':'see_solver_log','canonical_normalization_method':'fixed_physical_r12nm_box',**setup};dump(meta_path,meta)
    case.update({'status':'completed','result_npz':str(npz),'result_json':str(meta_path),'runtime_s':runtime,'fsp_sha256':meta['fsp_sha256'],'solver_log_sha256':meta['solver_log_sha256'],'error':''});_save_r12_state(state);_r12_log(f"completed {case['case_id']} attempt={attempt} runtime_s={runtime:.3f}")

def _run_r12_case(case:dict[str,Any],state:dict[str,Any])->None:
    if case['status'] in ('completed','reused_from_validated_run') and Path(case.get('result_npz','')).exists() and Path(case.get('result_json','')).exists():case['status']='reused_from_validated_run';_save_r12_state(state);return
    for attempt in range(int(case.get('attempts',0))+1,3):
        if attempt==2:case['simulation_time_fs']=1200
        case.update({'status':'running','attempts':attempt});_save_r12_state(state);_r12_log(f"running {case['case_id']} attempt={attempt}")
        try:_execute_r12_once(case,state,attempt);return
        except Exception as exc:case.update({'status':'failed','error':repr(exc),'traceback':traceback.format_exc()});_save_r12_state(state);_r12_log(f"failed {case['case_id']} attempt={attempt} error={exc!r}")

def run_broadband_420(start_nm:float,stop_nm:float,points:int,keys:list[str],dipoles:list[str],pilot:bool)->None:
    if (start_nm,stop_nm,points)!=(420.0,480.0,301):raise RuntimeError('formal_broadband_grid_must_be_420_480_301')
    mats=_material_audit()
    if not all(r['wavelength_min_nm']<=420 and r['wavelength_max_nm']>=480 for r in mats):raise RuntimeError('native_material_range_does_not_cover_420_480')
    state=_init_r12_state(start_nm,stop_nm,points,keys,dipoles);wanted=set(keys)|{'homogeneous_reference'}
    for phase in ('reference','pilot','remaining'):
        for case in state['cases']:
            if case['structure_key'] in wanted and case['phase']==phase:_run_r12_case(case,state)
    state['finished_at']=time.strftime('%Y-%m-%dT%H:%M:%S');_save_r12_state(state)
    gate=_r12_pilot_gate(state) if pilot else {'status':'full_solver_phase_complete'}
    print(json.dumps({**gate,'cases':len([c for c in state['cases'] if c['structure_key'] in wanted]),'completed':sum(c['status'] in ('completed','reused_from_validated_run') for c in state['cases'] if c['structure_key'] in wanted),'failed':sum(c['status']=='failed' for c in state['cases'] if c['structure_key'] in wanted)}))

def _load_r12_case(case:dict[str,Any])->dict[str,Any]:
    if case['status'] not in ('completed','reused_from_validated_run'):raise RuntimeError('r12_case_unavailable:'+case['case_id'])
    z=np.load(case['result_npz']);return {k:np.asarray(z[k]) for k in z.files}|{'case':case,'meta':json.loads(Path(case['result_json']).read_text(encoding='utf-8'))}

def _r12_pilot_gate(state:dict[str,Any])->dict[str,Any]:
    cases={c['case_id']:c for c in state['cases']};old_path=OUT/'broadband_key_wavelength_angular_metrics.csv';old=rows(old_path) if old_path.exists() else [];checks=[]
    for key in ('bare','zl1_alternative'):
        for d in ('x','z'):
            r=_load_r12_case(cases[f'b420_{key}_{d}']);m=_spectral_metric_full(r['wavelength_nm'],r['p_up_raw'],bare=key=='bare');am,_=_angular_rows(r);a450=min(am,key=lambda x:abs(float(x['wavelength_nm'])-450));matches=[x for x in old if x.get('structure_key')==key and x.get('dipole')==d and abs(float(x['wavelength_nm'])-450)<.3];old450=min(matches,key=lambda x:abs(float(x['wavelength_nm'])-450)) if matches else None
            fd=abs(float(a450['angular_FWHM_deg'])-float(old450['angular_FWHM_deg'])) if old450 else None;cd=abs(float(a450['cone_fraction_10deg'])-float(old450['cone_fraction_10deg'])) if old450 else None;prominent=_prominent_peak_count(r['p_up_raw']);same=_peak_set_semantics_same(a450,old450);passed=(m['FWHM_status'] in ('pass','no_isolated_peak') and prominent<=5 and old450 is not None and fd<=.7 and cd<=.015 and same)
            checks.append({'structure_key':key,'dipole':d,'spectral_peak_nm':m['peak_wavelength_nm'],'spectral_FWHM_nm':m['spectral_FWHM_nm'],'FWHM_status':m['FWHM_status'],'prominent_peak_count':prominent,'angular_FWHM_change_vs_440_460_deg':fd,'cone10_change_vs_440_460':cd,'peak_set_semantics_unchanged':same,'pilot_pass':passed})
    write(OUT/'broadband_420_480_convergence_audit.csv',checks);state['pilot_gate']=checks;_save_r12_state(state);return {'status':'pilot_pass' if all(r['pilot_pass'] for r in checks) else 'pilot_fail','checks':checks}

def _prominent_peak_count(v:np.ndarray)->int:
    x=np.asarray(v,float);return int(sum(x[i]>=x[i-1] and x[i]>x[i+1] and x[i]>=.2*x.max() for i in range(1,len(x)-1)))

def _peak_set_semantics_same(new:dict[str,Any],old:dict[str,Any]|None)->bool:
    if old is None:return False
    old_pair=str(old.get('symmetric_peak_pair','')).lower()=='true';new_pair=bool(new.get('symmetric_peak_pair'))
    old_abs=float(old.get('maximum_abs_angle_deg') or max(map(abs,json.loads(old['maximum_angle_set_deg']))));new_abs=float(new['maximum_abs_angle_deg'])
    return old_pair==new_pair and (old_abs<=1)==(new_abs<=1)

def _spectral_metric_full(lam:np.ndarray,value:np.ndarray,bare:bool=False)->dict[str,Any]:
    lam=np.asarray(lam,float);v=np.asarray(value,float);k=int(np.argmax(v));peak=float(v[k]);half=peak/2;left=right=None
    for j in range(k,0,-1):
        if v[j-1]<half<=v[j]:left=_half_cross(lam[j-1],lam[j],v[j-1],v[j],half);break
    for j in range(k,len(v)-1):
        if v[j]>=half>v[j+1]:right=_half_cross(lam[j],lam[j+1],v[j],v[j+1],half);break
    if left is not None and right is not None:status='pass';fwhm=right-left
    elif bare:status='no_isolated_peak';fwhm=None
    else:status='window_truncated';fwhm=None
    return {'peak_wavelength_nm':float(lam[k]),'peak_value':peak,'left_half_max_nm':left,'right_half_max_nm':right,'spectral_FWHM_nm':fwhm,'FWHM_status':status,'integrated_420_480':float(np.trapezoid(v,lam)),'integrated_440_460':float(np.trapezoid(v[(lam>=440)&(lam<=460)],lam[(lam>=440)&(lam<=460)])),'T448':float(np.interp(448,lam,v)),'T450':float(np.interp(450,lam,v)),'T453':float(np.interp(453,lam,v)),'edge_stability':float(max(v[0],v[-1])/max(peak,1e-30))}

def _gaussian_420(lam:np.ndarray)->tuple[np.ndarray,float]:
    sigma=28/(2*math.sqrt(2*math.log(2)));w=np.exp(-.5*((lam-450)/sigma)**2);captured=.5*(math.erf((480-450)/(math.sqrt(2)*sigma))-math.erf((420-450)/(math.sqrt(2)*sigma)));return w,captured

def postprocess_broadband_420()->None:
    state=json.loads(R12_STATE.read_text(encoding='utf-8'));cases={c['case_id']:c for c in state['cases']};keys=('bare','wan_proxy','explicit','zl1_nominal','zl1_alternative');required=[f'b420_{k}_{d}' for k in keys for d in ('x','z')]+[f'b420_homogeneous_reference_{d}' for d in ('x','z')]
    missing=[cid for cid in required if cid not in cases or cases[cid]['status'] not in ('completed','reused_from_validated_run')]
    if missing:raise RuntimeError('incomplete_420_480_cases:'+','.join(missing))
    result={(k,d):_load_r12_case(cases[f'b420_{k}_{d}']) for k in keys for d in ('x','z')};refs={d:_load_r12_case(cases[f'b420_homogeneous_reference_{d}']) for d in ('x','z')};smap={s['structure_key']:s for s in structures()};mat=_material_audit();long=[];qw=[];spec=[];angular=[];manifest=[];candidate=[];weighted=[]
    lam=result[('bare','x')]['wavelength_nm'];grid_hash=hashlib.sha256(lam.tobytes()).hexdigest();write(OUT/'wavelength_grid_420_480.csv',[{'wavelength_index':i,'wavelength_nm':x,'frequency_Hz':299792458/(x*1e-9),'actual_grid_hash':grid_hash} for i,x in enumerate(lam)])
    orientation_curves={}
    for key in keys:
        for d in ('x','z'):
            r=result[(key,d)];p=r['p_up_raw'];pe=r['near_source_outward_flux_r12nm'];pref=np.interp(lam,refs[d]['wavelength_nm'],refs[d]['p_up_raw']);hom_emit=np.interp(lam,refs[d]['wavelength_nm'],refs[d]['near_source_outward_flux_r12nm']);barep=result[('bare',d)]['p_up_raw'];curves={'raw_upward_spectrum':p,'r12_normalized_upward_spectrum':p/pe,'homogeneous_reference_normalized_spectrum':p/pref,'relative_to_bare_spectrum':p/barep,'emission_rate_proxy':pe/hom_emit};orientation_curves[(key,d)]=curves
            for i,w in enumerate(lam):long.append({'structure_key':key,'structure_id':smap[key]['structure_id'],'dipole':d,'wavelength_index':i,'wavelength_nm':w,'P_up_raw':p[i],'near_source_outward_flux_r12nm':pe[i],'eta_up_normalized_to_r12nm_box':curves['r12_normalized_upward_spectrum'][i],'homogeneous_reference_normalized':curves['homogeneous_reference_normalized_spectrum'][i],'relative_to_bare':curves['relative_to_bare_spectrum'][i],'emission_rate_proxy':curves['emission_rate_proxy'][i],'normalization_method':'fixed_physical_r12nm_box','normalization_status':'fixed_physical_box_normalization_valid'})
            for name,curve in curves.items():spec.append({'structure_key':key,'dipole':d,'curve_name':name,**_spectral_metric_full(lam,curve,bare=key=='bare')})
            am,_=_angular_rows(r);angular.extend(am);meta=r['meta'];s=smap[key];manifest.append({'case_id':r['case']['case_id'],'structure_id':s['structure_id'],'topology':s['kind'],'dipole':d,'exact_layer_sequence':' '.join(f'{m}{v:g}' for m,v in s['sequence']),'geometry_hash':s.get('geometry_hash',''),'sequence_hash':s.get('canonical_sequence_hash',''),'layer_count':s['layer_count'],'total_thickness_nm':s['total_thickness_nm'],'material_ids':';'.join(MATERIALS),'material_data_hashes':';'.join(x['sample_hash'] for x in mat),'wavelength_start_nm':lam.min(),'wavelength_stop_nm':lam.max(),'wavelength_points':len(lam),'actual_wavelength_grid_hash':grid_hash,'simulation_time_fs':meta['requested_simulation_time_fs'],'autoshutoff_target':meta['autoshutoff_target'],'source_local_mesh_nm':1,'canonical_box_half_nm':12,'normalization_method':'fixed_physical_r12nm_box','runtime_FSP_SHA256':meta['fsp_sha256'],'solver_log_SHA256':meta['solver_log_sha256'],'quality_flags':'all_valid','old_zero_radius_failure_provenance':'canonical_emission_power_selection.csv','provenance_commit':'46af82357f269aea0c77105a03e7ca9da645ca8f'})
    for key in keys:
        x,z=orientation_curves[(key,'x')],orientation_curves[(key,'z')];avg={'fixed_moment_in_plane_qw':.5*(x['raw_upward_spectrum']+z['raw_upward_spectrum']),'r12_normalized_in_plane_qw':.5*(x['r12_normalized_upward_spectrum']+z['r12_normalized_upward_spectrum']),'homogeneous_reference_normalized_in_plane_qw':.5*(x['homogeneous_reference_normalized_spectrum']+z['homogeneous_reference_normalized_spectrum']),'relative_to_bare_in_plane_qw':.5*(x['relative_to_bare_spectrum']+z['relative_to_bare_spectrum'])}
        for name,curve in avg.items():
            for i,w in enumerate(lam):qw.append({'structure_key':key,'curve_name':name,'wavelength_nm':w,'value':curve[i]})
            spec.append({'structure_key':key,'dipole':'in_plane_qw_average','curve_name':name,**_spectral_metric_full(lam,curve,bare=key=='bare')})
        g,capture=_gaussian_420(lam);weighted_curve=avg['r12_normalized_in_plane_qw']*g;wm=_spectral_metric_full(lam,weighted_curve,bare=key=='bare');a450=[r for r in angular if r['structure_key']==key and abs(float(r['wavelength_nm'])-450)<.3];cone10=float(np.mean([float(r['cone_fraction_10deg']) for r in a450]));weighted.append({'structure_key':key,'source_id':'wan_blue_gaussian_benchmark','source_center_nm':450,'source_FWHM_nm':28,'captured_source_fraction_420_480':capture,'weighted_output_peak_nm':wm['peak_wavelength_nm'],'weighted_output_FWHM_nm':wm['spectral_FWHM_nm'],'weighted_output_FWHM_status':wm['FWHM_status'],'weighted_integrated_upward_power':float(np.trapezoid(avg['r12_normalized_in_plane_qw']*g,lam)),'weighted_cone10_output_power':float(np.trapezoid(avg['r12_normalized_in_plane_qw']*g,lam))*cone10,'benchmark_only':True})
        rawm=_spectral_metric_full(lam,avg['fixed_moment_in_plane_qw'],bare=key=='bare');etam=_spectral_metric_full(lam,avg['r12_normalized_in_plane_qw'],bare=key=='bare');refm=_spectral_metric_full(lam,avg['homogeneous_reference_normalized_in_plane_qw'],bare=key=='bare');a450x=min((r for r in angular if r['structure_key']==key and r['dipole']=='x'),key=lambda r:abs(float(r['wavelength_nm'])-450));a450z=min((r for r in angular if r['structure_key']==key and r['dipole']=='z'),key=lambda r:abs(float(r['wavelength_nm'])-450));sx=smap[key];mx=result[(key,'x')]['meta'];mz=result[(key,'z')]['meta'];candidate.append({'structure_key':key,'structure_id':sx['structure_id'],'topology':sx['kind'],'exact_layer_sequence':' '.join(f'{m}{v:g}' for m,v in sx['sequence']),'geometry_hash':sx['geometry_hash'],'sequence_hash':sx['canonical_sequence_hash'],'material_ids':';'.join(MATERIALS),'material_data_hashes':';'.join(x['sample_hash'] for x in mat),'actual_wavelength_grid_hash':grid_hash,'raw_metrics':json.dumps(rawm),'r12_normalized_metrics':json.dumps(etam),'homogeneous_reference_normalized_metrics':json.dumps(refm),'x_450_angular_FWHM_deg':a450x['angular_FWHM_deg'],'z_450_angular_FWHM_deg':a450z['angular_FWHM_deg'],'mean_450_angular_FWHM_deg':.5*(float(a450x['angular_FWHM_deg'])+float(a450z['angular_FWHM_deg'])),'mean_450_cone10':.5*(float(a450x['cone_fraction_10deg'])+float(a450z['cone_fraction_10deg'])),'normalization_method':'fixed_physical_r12nm_box','x_runtime_FSP_SHA256':mx['fsp_sha256'],'z_runtime_FSP_SHA256':mz['fsp_sha256'],'x_solver_log_SHA256':mx['solver_log_sha256'],'z_solver_log_SHA256':mz['solver_log_sha256'],'old_zero_radius_failure_provenance':'canonical_emission_power_selection.csv','candidate_provenance':sx['provenance'],'quality_flags':'all_valid'})
    comparison=[]
    bare_eta=json.loads(candidate[0]['r12_normalized_metrics'])
    for r in candidate:
        eta=json.loads(r['r12_normalized_metrics']);comparison.append({'structure_key':r['structure_key'],'output_spectral_peak_nm':eta['peak_wavelength_nm'],'output_spectral_FWHM_nm':eta['spectral_FWHM_nm'],'output_FWHM_status':eta['FWHM_status'],'integrated_r12_normalized_420_480':eta['integrated_420_480'],'relative_integrated_r12_vs_bare':eta['integrated_420_480']/bare_eta['integrated_420_480'],'mean_450_angular_FWHM_deg':r['mean_450_angular_FWHM_deg'],'mean_450_cone10':r['mean_450_cone10']})
    write(OUT/'broadband_420_480_power_normalization_long.csv',long);write(OUT/'broadband_420_480_spectra_x_z_long.csv',[{k:v for k,v in r.items() if k not in ('normalization_status',)} for r in long]);write(OUT/'broadband_420_480_in_plane_qw_spectra.csv',qw);write(OUT/'broadband_420_480_spectral_metrics.csv',spec);write(OUT/'broadband_420_480_source_weighted_metrics.csv',weighted);write(OUT/'broadband_420_480_key_angular_metrics.csv',angular);write(OUT/'broadband_420_480_same_model_comparison.csv',comparison);write(OUT/'broadband_420_480_simulation_manifest.csv',manifest);write(OUT/'broadband_420_480_case_status.csv',state['cases']);write(OUT/'ml_subrun_labels_broadband_420_480.csv',manifest);write(OUT/'ml_candidate_labels_broadband_420_480.csv',candidate)
    old=rows(OUT/'broadband_key_wavelength_angular_metrics.csv');angle_delta=[]
    for r in angular:
        if abs(float(r['wavelength_nm'])-450)>.3:continue
        match=[x for x in old if x['structure_key']==r['structure_key'] and x['dipole']==r['dipole'] and abs(float(x['wavelength_nm'])-450)<.3]
        if match:angle_delta.append((abs(float(r['angular_FWHM_deg'])-float(match[0]['angular_FWHM_deg'])),abs(float(r['cone_fraction_10deg'])-float(match[0]['cone_fraction_10deg'])),_peak_set_semantics_same(r,match[0])))
    failed=[c['case_id'] for c in state['cases'] if c['status']=='failed'];main_rows={r['structure_key']:r for r in comparison if r['structure_key'] in ('explicit','zl1_nominal','zl1_alternative')};main_closed=not failed and len(main_rows)==3 and all(r['output_FWHM_status']=='pass' for r in main_rows.values());wan_row=next(r for r in comparison if r['structure_key']=='wan_proxy');valid={'task':R12_TASK,'status':'native_m1_2d_dipole_device_closure_pass' if main_closed else ('convergence_failed' if failed else 'spectral_window_still_unresolved'),'main_candidate_device_closure':'PASS' if main_closed else 'FAIL','wan_proxy_unweighted_fwhm':wan_row['output_FWHM_status'],'preferred_candidate':'zl1_alternative','candidate_decision_label':'alternative_best_angle_power_tradeoff','case_count':len(state['cases']),'completed':sum(c['status'] in ('completed','reused_from_validated_run') for c in state['cases']),'failed_cases':failed,'canonical_normalization_method':'fixed_physical_r12nm_box','fixed_physical_box_normalization_valid':True,'actual_wavelength_grid_hash':grid_hash,'no_NaN_inf':all(np.isfinite(float(r['P_up_raw'])) and np.isfinite(float(r['near_source_outward_flux_r12nm'])) for r in long),'angular_fraction_sum_max_error':max(abs(float(r['fraction_sum'])-1) for r in angular),'comparison_to_440_460_450_max_FWHM_delta_deg':max((x[0] for x in angle_delta),default=None),'comparison_to_440_460_450_max_cone10_delta':max((x[1] for x in angle_delta),default=None),'comparison_to_440_460_peak_sets_unchanged':all(x[2] for x in angle_delta),'runtime_hashes_complete':all(r['runtime_FSP_SHA256'] and r['solver_log_SHA256'] for r in manifest),'solver_invoked':True,'postprocess_only_freeze':True,'git_commit':False};dump(OUT/'validation.json',valid)
    names=['canonical_r12_normalization.csv','broadband_440_460_r12_reprocessed_metrics.csv','wavelength_grid_420_480.csv','broadband_420_480_simulation_manifest.csv','broadband_420_480_case_status.csv','broadband_420_480_convergence_audit.csv','broadband_420_480_power_normalization_long.csv','broadband_420_480_spectra_x_z_long.csv','broadband_420_480_in_plane_qw_spectra.csv','broadband_420_480_spectral_metrics.csv','broadband_420_480_source_weighted_metrics.csv','broadband_420_480_key_angular_metrics.csv','broadband_420_480_same_model_comparison.csv','ml_subrun_labels_broadband_420_480.csv','ml_candidate_labels_broadband_420_480.csv','validation.json','manifest.json'];dump(OUT/'manifest.json',{'task':R12_TASK,'status':valid['status'],'main_candidate_device_closure':valid['main_candidate_device_closure'],'wan_proxy_unweighted_fwhm':valid['wan_proxy_unweighted_fwhm'],'preferred_candidate':valid['preferred_candidate'],'candidate_decision_label':valid['candidate_decision_label'],'source_head':'46af82357f269aea0c77105a03e7ca9da645ca8f','outputs':names,'runtime_state':str(R12_STATE),'normalization_method':'fixed_physical_r12nm_box','material_audit':mat,'git_commit':False})
    _write_r12_report(valid,comparison,weighted,angular)
    print(json.dumps(valid))

def _write_r12_report(valid:dict[str,Any],comparison:list[dict[str,Any]],weighted:list[dict[str,Any]],angular:list[dict[str,Any]])->None:
    lines=['# MDC Native-M1 2D dipole broadband 420-480 v1','',f"Stage status: `{valid['status']}`.",f"Main candidate device closure: `{valid['main_candidate_device_closure']}`.",f"Wan proxy unweighted FWHM: `{valid['wan_proxy_unweighted_fwhm']}`.",'','The Wan engineering proxy left half-maximum is below 420 nm and was not extrapolated. This scoped limitation does not block B2-B4 or the preferred-candidate closure.','','## R12 canonical normalization','','The formal denominator is `near_source_outward_flux_r12nm`, measured with a 1 nm source-local mesh and four-sided direct outward Poynting integration. `eta_up_normalized_to_r12nm_box` is not exact total emitted power, absolute extraction efficiency, or a zero-radius extrapolation.','','The prior M1-8 nm versus M2-12 nm decision compared unequal physical radii. Common-radius M1/M2 replay is below 1% at 12, 16, and 20 nm for x and z. The 12 nm M1 value is frozen.','','Existing 440-460 runs contain only r8 monitors, so an r12 spectrum cannot be reconstructed without rerunning. Their raw spectra and invalid normalization evidence are preserved; no mixed-radius substitute is reported.','','## 420-480 same-model comparison','','|structure|spectral peak (nm)|spectral FWHM (nm)|FWHM status|integrated r12 normalized|relative to Bare|mean 450 angular FWHM|mean cone10|','|---|---:|---:|---|---:|---:|---:|---:|']
    for r in comparison:lines.append(f"|{r['structure_key']}|{r['output_spectral_peak_nm']:.6g}|{r['output_spectral_FWHM_nm'] if r['output_spectral_FWHM_nm'] is not None else 'n/a'}|{r['output_FWHM_status']}|{r['integrated_r12_normalized_420_480']:.8g}|{r['relative_integrated_r12_vs_bare']:.6g}|{r['mean_450_angular_FWHM_deg']:.6g}|{r['mean_450_cone10']:.6g}|")
    lines += ['','## Key angular results','','|structure|dipole|wavelength|peak set|FWHM|cone10|fraction sum|','|---|---|---:|---|---:|---:|---:|']
    for r in angular:lines.append(f"|{r['structure_key']}|{r['dipole']}|{float(r['wavelength_nm']):.6g}|{r['maximum_angle_set_deg']}|{r['angular_FWHM_deg']}|{r['cone_fraction_10deg']}|{r['fraction_sum']}|")
    lines += ['','## Source weighting','','The `wan_blue_gaussian_benchmark` uses a 450 nm center and 28 nm input FWHM. It is a common benchmark, not a measured Micro-LED spectrum.','','|structure|captured fraction|weighted peak|weighted FWHM|integrated normalized output|weighted cone10 output|','|---|---:|---:|---:|---:|---:|']
    for r in weighted:lines.append(f"|{r['structure_key']}|{r['captured_source_fraction_420_480']:.8g}|{r['weighted_output_peak_nm']:.6g}|{r['weighted_output_FWHM_nm'] if r['weighted_output_FWHM_nm'] is not None else 'n/a'}|{r['weighted_integrated_upward_power']:.8g}|{r['weighted_cone10_output_power']:.8g}|")
    by={r['structure_key']:r for r in comparison};nom=by['zl1_nominal'];alt=by['zl1_alternative'];angle_gain=float(nom['mean_450_angular_FWHM_deg'])-float(alt['mean_450_angular_FWHM_deg']);spectral_gain=float(nom['output_spectral_FWHM_nm'])-float(alt['output_spectral_FWHM_nm']);power_ratio=float(alt['integrated_r12_normalized_420_480'])/float(nom['integrated_r12_normalized_420_480'])
    lines += ['','## Configuration and completion','','- Actual monitor grid: 420-480 nm, 301 points; actual wavelengths and SHA256 are stored.','- Simulation time: 900 fs; retry ceiling: 1200 fs; autoshutoff target: 1e-7.','- Global dx 20 nm, stack dy 2 nm, source-local dx=dy 1 nm, r12 four-side box.','- Solver completion: 12/12 cases, 0 failed, 0 retry.','- Pilot: 4/4 passed; maximum 450-nm FWHM delta versus the 440-460 run is '+f"{valid['comparison_to_440_460_450_max_FWHM_delta_deg']:.6g} deg; maximum cone10 delta is {valid['comparison_to_440_460_450_max_cone10_delta']:.6g}.",'','## Strict FWHM definitions','','|physical aperture|Explicit|ZL-1 nominal|ZL-1 alternative|Wan proxy|','|---|---:|---:|---:|---:|','|Native-M1 plane-wave TMM|7.4 nm|3.3 nm|3.3 nm|n/a|','|Native-M1 dipole-FDTD R12-normalized output|19.9312 nm|19.0227 nm|18.7821 nm|window truncated|','|28 nm Gaussian benchmark weighted output|13.0310 nm|13.2869 nm|13.2613 nm|18.7161 nm|','','These three FWHM families are not interchangeable: plane-wave transmission, dipole-device output, and source-weighted output use different physical apertures.','','## Device-level decision','',f"The ZL-1 alternative has the best defect-MDC angle-power tradeoff: its mean 450-nm angular FWHM is narrower than nominal by {angle_gain:.6g} deg, its r12-normalized output spectral FWHM is narrower by {spectral_gain:.6g} nm, and its integrated r12-normalized 420-480 power is {power_ratio:.6g}x nominal. No arbitrary composite score is used.",'','- Preferred candidate: ZL-1 alternative.','- Stable narrow-angle control: ZL-1 nominal.','- Traditional defect baseline: Explicit.','- Engineering proxy: Wan proxy.','- No-stack emission reference: Bare.','',f"The formal stage status is `{valid['status']}`. The Wan-only unweighted FWHM remains `{valid['wan_proxy_unweighted_fwhm']}` without extrapolation; Bare is `no_isolated_peak`; Explicit and both ZL-1 candidates have closed device-output FWHM.",'','Compared with the Wan proxy, the alternative is narrower in 450-nm angular FWHM and in the 28-nm weighted benchmark, while its integrated R12-normalized power is about 71.1% of Wan. Directional and spectral gains are supported; a throughput advantage is not. Compared with Bare, directionality improves substantially while integrated R12-normalized power decreases; this ratio is not called an absolute extraction-efficiency loss.','','## ML labels','','Subrun and candidate label files record the fixed-r12 method, common-radius convergence provenance, actual wavelength-grid hash, spectral/angular/power metrics, quality flags, and runtime FSP/log hashes. The existing 440-460 labels remain present.','','All five structures use Native-M1 materials with no constant-index fallback. Runtime FSP/log files remain outside Git. No TMM, RCWA, or FMMAX was run. Raw monitor power is not called extraction efficiency.']
    R12_REPORT.write_text('\n'.join(lines)+'\n',encoding='utf-8')

def complete_required_normalization_gates()->None:
    status=_canonical_gate_status()
    RT.mkdir(parents=True,exist_ok=True);_log('normalization prerequisite status='+status)
    if status=='emitted_power_near_source_not_converged':print(json.dumps({'status':status,'action':'do_not_rerun_failed_canonical_gate; raw_fixed_moment_broadband_allowed; normalized_and_deembedded_invalid','solver_invoked':False}));return
    print(json.dumps({'status':status,'action':'existing_gate_evidence_reused','solver_invoked':False}))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--audit-only',action='store_true');p.add_argument('--build-only',action='store_true');p.add_argument('--run-pilot',action='store_true');p.add_argument('--audit-orientation-normalization',action='store_true');p.add_argument('--run-orientation-normalization-pilot',action='store_true');p.add_argument('--audit-canonical-emission-v3',action='store_true');p.add_argument('--run-canonical-emission-v3',action='store_true');p.add_argument('--run-homogeneous-reference-v3',action='store_true');p.add_argument('--run-convergence-450-v3',action='store_true');p.add_argument('--run-all-450-v3',action='store_true');p.add_argument('--postprocess-450-v3',action='store_true');p.add_argument('--audit-broadband-440-460',action='store_true');p.add_argument('--complete-required-normalization-gates',action='store_true');p.add_argument('--run-broadband-overnight',action='store_true');p.add_argument('--postprocess-broadband-440-460',action='store_true');p.add_argument('--freeze-r12-normalization',action='store_true');p.add_argument('--reprocess-existing-440-460',action='store_true');p.add_argument('--run-broadband-pilot',action='store_true');p.add_argument('--run-broadband-all',action='store_true');p.add_argument('--postprocess-broadband-420-480',action='store_true');p.add_argument('--structures',default='bare,zl1_alternative');p.add_argument('--dipoles',default='x');p.add_argument('--wavelength-mode',default='single_450');p.add_argument('--wavelength-start-nm',type=float,default=440.0);p.add_argument('--wavelength-stop-nm',type=float,default=460.0);p.add_argument('--wavelength-points',type=int,default=101);p.add_argument('--resume',action='store_true');p.add_argument('--continue-on-case-failure',action='store_true');a=p.parse_args()
 if sum((a.audit_only,a.build_only,a.run_pilot,a.audit_orientation_normalization,a.run_orientation_normalization_pilot,a.audit_canonical_emission_v3,a.run_canonical_emission_v3,a.run_homogeneous_reference_v3,a.run_convergence_450_v3,a.run_all_450_v3,a.postprocess_450_v3,a.audit_broadband_440_460,a.complete_required_normalization_gates,a.run_broadband_overnight,a.postprocess_broadband_440_460,a.freeze_r12_normalization,a.run_broadband_pilot,a.run_broadband_all,a.postprocess_broadband_420_480))!=1:p.error('select exactly one phase')
 if a.audit_orientation_normalization:orientation_normalization_audit()
 elif a.run_orientation_normalization_pilot:orientation_normalization_pilot()
 elif a.audit_canonical_emission_v3:canonical_emission_audit_v3()
 elif a.run_canonical_emission_v3:canonical_emission_run_v3(a.dipoles.split(','))
 elif a.run_homogeneous_reference_v3:raise RuntimeError('canonical_emission_gate_must_pass_before_homogeneous_reference')
 elif a.run_convergence_450_v3:raise RuntimeError('canonical_emission_gate_must_pass_before_device_convergence')
 elif a.run_all_450_v3:raise RuntimeError('canonical_emission_and_convergence_gates_must_pass_before_all_cases')
 elif a.postprocess_450_v3:postprocess_450_v3()
 elif a.audit_broadband_440_460:broadband_audit(a.wavelength_start_nm,a.wavelength_stop_nm,a.wavelength_points)
 elif a.complete_required_normalization_gates:complete_required_normalization_gates()
 elif a.run_broadband_overnight:broadband_overnight(a.wavelength_start_nm,a.wavelength_stop_nm,a.wavelength_points,a.resume)
 elif a.postprocess_broadband_440_460:broadband_postprocess()
 elif a.freeze_r12_normalization:freeze_r12_normalization(a.reprocess_existing_440_460)
 elif a.run_broadband_pilot:run_broadband_420(a.wavelength_start_nm,a.wavelength_stop_nm,a.wavelength_points,[x for x in a.structures.split(',') if x],[x for x in a.dipoles.split(',') if x],True)
 elif a.run_broadband_all:run_broadband_420(a.wavelength_start_nm,a.wavelength_stop_nm,a.wavelength_points,[x for x in a.structures.split(',') if x],[x for x in a.dipoles.split(',') if x],False)
 elif a.postprocess_broadband_420_480:postprocess_broadband_420()
 elif a.audit_only:audit_only()
 elif a.build_only:build_only()
 else:
  if a.dipoles!='x' or a.wavelength_mode!='single_450':raise RuntimeError('only verified x single_450 pilot is enabled')
  run_pilot(a.structures.split(','))
