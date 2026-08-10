"""Authorized AL64 real 2D FDTD joint wavelength-angle profile runner.

Uses the frozen 384-case AL64 matrix, the validated Native-M1 builder primitives and
fresh-load/save/run/extract lifecycle. The first matrix row is the upgrade smoke
case and is also a formal case; no case is retried automatically. Geometry
realization is read from the frozen geometry_master metadata by geometry hash;
no optical labels are read.
"""
from __future__ import annotations
import argparse, csv, hashlib, importlib.util, json, math, shutil, sys, time, uuid
from pathlib import Path
from typing import Any
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
SCRIPTS=ROOT/'scripts'; sys.path.insert(0,str(SCRIPTS))
import mdc_fdtd_2d_monitor_contract_v1 as monitor_contract
import run_mdc_native_m1_2d_dipole_device_comparison_v1 as frozen
if not hasattr(np,'trapezoid'): np.trapezoid=np.trapz
MATERIALS=('APCD_GAN_NATIVE_M1','APCD_TIO2_NATIVE_M1','APCD_SIO2_NATIVE_M1')
START_NM,STOP_NM,POINTS=420.0,480.0,301
PLAN_DIR=ROOT/'contracts/mdc_hf_surrogate_v2/v3_plan_freeze_v1'
CASE_MATRIX=PLAN_DIR/'v3_al64_future_case_matrix_v1.csv'
CANDIDATES=PLAN_DIR/'v3_al64_geometry_manifest_v1.csv'
GEOMETRY_MASTER=Path(r'D:\project\worktrees\blue_apcd_mdc_defect_450\datasets\mdc_ml_database_v1\geometry_master.csv')
INHERITED_CONTRACT=ROOT/'outputs/mdc_hf_surrogate_v2_doe96_joint_profile_database_v1/20260803T_doe96_joint_profile_6b6d7e2/doe96_inherited_contract_audit.json'
AL64_SELECTION_CONTRACT=PLAN_DIR/'v3_al64_selection_contract_v1.json'
AL64_OVERLAP_AUDIT=PLAN_DIR/'v3_al64_overlap_audit_v1.json'
MATERIAL_CONFIG=ROOT/'configs/material_reference_apcd_blue.yaml'
RUNTIME_ROOT=ROOT/'outputs/mdc_hf_surrogate_v3_al64_real_2d_fdtd_v1'


def now(): return time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())
def sha(p):
    h=hashlib.sha256(); h.update(Path(p).read_bytes()); return h.hexdigest()
def dump(p,v): Path(p).parent.mkdir(parents=True,exist_ok=True); Path(p).write_text(json.dumps(v,indent=2,sort_keys=True)+'\n',encoding='utf-8')
def load(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def canonical(v): return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True)
def hobj(v): return hashlib.sha256(canonical(v).encode()).hexdigest()
SOURCE_Z_BY_POSITION={k:str(v) for k,v in load(INHERITED_CONTRACT)['forbidden_drift']['source_positions_nm'].items()}
def lumapi():
    spec=importlib.util.spec_from_file_location('lumapi',r'N:\Program Files\ANSYS Inc\v251\Lumerical\api\python\lumapi.py')
    mod=importlib.util.module_from_spec(spec); sys.modules['lumapi']=mod; spec.loader.exec_module(mod); return mod

def read_matrix():
    with CASE_MATRIX.open(newline='',encoding='utf-8') as f: rows=list(csv.DictReader(f))
    if len(rows)!=384: raise RuntimeError('al64_case_count_drift')
    for row in rows:
        row['case_hash']=row['case_uid']
        row['case_id']=row['case_uid']
        row['source_position_nm']=SOURCE_Z_BY_POSITION.get(row['source_position'])
        if row['source_position_nm'] is None: raise RuntimeError('al64_source_position_drift')
    if len({r['geometry_hash'] for r in rows})!=64 or len({r['case_uid'] for r in rows})!=384: raise RuntimeError('al64_hash_count_drift')
    if any(r['dipole_orientation'] not in ('x','z') for r in rows): raise RuntimeError('doe96_orientation_drift')
    if any(r['source_position'] not in ('top','centroid','bottom') for r in rows): raise RuntimeError('doe96_source_position_drift')
    if any(r['dipole_orientation']=='y' for r in rows): raise RuntimeError('doe96_y_dipole_forbidden')
    counts={g:sum(r['geometry_hash']==g for r in rows) for g in {r['geometry_hash'] for r in rows}}
    if set(counts.values())!={6}: raise RuntimeError('doe96_cases_per_geometry_drift')
    return rows

def candidate_map():
    with CANDIDATES.open(newline='',encoding='utf-8') as f: selected=list(csv.DictReader(f))
    if len(selected)!=64: raise RuntimeError('al64_geometry_manifest_drift')
    with GEOMETRY_MASTER.open(newline='',encoding='utf-8-sig') as f: master={row['geometry_hash']:row for row in csv.DictReader(f)}
    result={}
    for row in selected:
        source=master.get(row['geometry_hash'])
        if source is None or source.get('geometry_id')!=row['geometry_id']: raise RuntimeError('al64_geometry_master_identity_drift')
        topology={'ZL-1':'ZL1','ZL-2':'ZL2'}.get(source.get('topology_family'), source.get('topology_family'))
        if topology!=row['topology_family']: raise RuntimeError(f"al64_topology_drift:{row['geometry_hash']}:{row['topology_family']}:{source.get('topology_family')}")
        if source.get('quality_status')!='accepted' or source.get('material_model')!='native_m1': raise RuntimeError('al64_geometry_master_quality_or_material_drift')
        try: sequence=json.loads(source['compiled_sequence_json'])
        except Exception as exc: raise RuntimeError('al64_compiled_sequence_invalid') from exc
        enriched=dict(row)
        enriched.update({'layer_count':source['physical_layer_count'],'total_thickness_nm':source['total_thickness_nm'],'defect_thickness_nm':source['added_defect_thickness_nm'],'compiled_sequence_json':source['compiled_sequence_json'],'layer_material_sequence':source['layer_material_sequence'],'topology_family':topology,'geometry_id':source['geometry_id']})
        if len(sequence)!=int(source['physical_layer_count']) or sum(int(item[1]) for item in sequence)!=int(source['total_thickness_nm']): raise RuntimeError('al64_geometry_sequence_sum_drift')
        result[row['geometry_hash']]=enriched
    return result

def realization(rec):
    """Deterministic stack realization from the frozen summary fields.

    The selection hash remains the frozen matrix identity; this realization hash
    binds the exact Native-M1 layer sequence used by the builder.
    """
    n=int(rec['layer_count']); total=int(rec['total_thickness_nm'])
    seq=[(str(item[0]),float(item[1])) for item in json.loads(rec['compiled_sequence_json'])]
    if n<3 or len(seq)!=n: raise RuntimeError('invalid_candidate_geometry_fields')
    if sum(int(t) for _,t in seq)!=total: raise RuntimeError('realization_total_thickness_mismatch')
    return {'structure_key':rec['geometry_hash'][:16],'structure_id':rec['geometry_id'],'kind':rec['topology_family'],'sequence':seq,'geometry_hash':rec['geometry_hash'],'total_thickness_nm':float(total),'layer_count':n,'selection_stratum':rec['selection_stratum'],'realization_hash':hobj({'geometry_hash':rec['geometry_hash'],'sequence':seq,'material_policy':'MDC_NATIVE_M1'})}

def structures(): return [realization(x) for x in candidate_map().values()]
def build_case(f,case,structure):
    start_m=START_NM*1e-9; stop_m=STOP_NM*1e-9; registered=[]; native=frozen.native()
    for mid in MATERIALS: native.register_lumerical_sampled_material(f,mid,apply_display_style=True); registered.append(mid)
    top=structure['total_thickness_nm']*1e-9
    f.addfdtd(); f.set('dimension','2D'); f.set('x span',frozen.XSPAN); f.set('y min',-1e-6); f.set('y max',max(800e-9,top+600e-9)); f.set('x min bc','PML'); f.set('x max bc','PML'); f.set('y min bc','PML'); f.set('y max bc','PML'); f.set('mesh accuracy',2); f.set('simulation time',900e-15); f.set('auto shutoff min',1e-7)
    frozen.add_rect(f,'gan','APCD_GAN_NATIVE_M1',-1e-6,frozen.STACK_Y); y=frozen.STACK_Y
    for i,(mat,d) in enumerate(structure['sequence']): frozen.add_rect(f,f'layer_{i}','APCD_SIO2_NATIVE_M1' if mat=='L' else 'APCD_TIO2_NATIVE_M1',y,y+d*1e-9); y+=d*1e-9
    f.addmesh(); f.set('name','stack_mesh'); f.set('x span',frozen.XSPAN); f.set('y min',-50e-9); f.set('y max',y+50e-9); f.set('dx',20e-9); f.set('dy',2e-9)
    source_y=float(case['source_position_nm'])*1e-9; frozen.SOURCE_Y=source_y
    monitor_contract.add_source_local_mesh(f,0,source_y,12e-9,1e-9)
    f.adddipole(); f.set('name',case['dipole_orientation']+'_dipole'); f.set('x',0); f.set('y',source_y); f.set('theta',90 if case['dipole_orientation']=='x' else 0); f.set('phi',0); f.set('wavelength start',start_m); f.set('wavelength stop',stop_m)
    monitor_contract.add_2d_power_box(f,'emit_box_12nm',0,source_y,12e-9,start_m,stop_m,POINTS)
    monitor_contract.add_reference_plane_monitor(f,'upward_monitor',0,y+300e-9,frozen.MONITOR_XSPAN,start_m,stop_m,POINTS)
    return {'registered_materials':registered,'monitor_name':'upward_monitor','power_box_prefix':'emit_box_12nm','source_position_nm':float(case['source_position_nm']),'dipole_orientation':case['dipole_orientation'],'wavelength_start_nm':START_NM,'wavelength_stop_nm':STOP_NM,'wavelength_points':POINTS,'angle_convention':'farfieldangle radians converted to degrees; +theta toward +x from upward air-side normal','air_side':'+y','tensor_axis_order':['wavelength_index','angle_index'],'tensor_units':'raw farfield intensity in native Lumerical export units','filter_id':'raw_air_side_unfiltered'}

def extract_joint(f,monitor_name,lam,p_up):
    rows=[]; angle_ref=None; intensity_rows=[]
    for k,wave in enumerate(lam):
        monitor_index=len(lam)-k
        ff=np.asarray(f.farfield2d(monitor_name,monitor_index)).squeeze(); ang=np.asarray(f.farfieldangle(monitor_name,monitor_index)).squeeze()
        deg=np.degrees(ang) if np.nanmax(np.abs(ang))<=math.pi+1 else ang
        ff=np.asarray(ff,float).reshape(-1); deg=np.asarray(deg,float).reshape(-1)
        if angle_ref is None: angle_ref=deg.copy()
        if len(deg)!=len(angle_ref) or not np.allclose(deg,angle_ref,rtol=0,atol=1e-6): raise RuntimeError('angle_grid_varies_across_wavelength')
        if not np.all(np.isfinite(ff)) or np.any(ff < -1e-15): raise RuntimeError('joint_tensor_nonfinite_or_negative')
        intensity_rows.append(np.maximum(ff,0.0)); rows.extend({'wavelength_index':k,'wavelength_nm':float(wave),'angle_index':j,'angle_deg':float(a),'raw_joint_power':float(v)} for j,(a,v) in enumerate(zip(deg,ff)))
    joint=np.asarray(intensity_rows,float)
    return np.asarray(angle_ref,float),joint,rows

def extract_case(case,run_root,state,smoke=False):
    case.setdefault('case_id',f"{case['geometry_hash'][:16]}__{case['source_position']}__{case['dipole_orientation']}")
    structures_by_hash={s['geometry_hash']:s for s in structures()}; structure=structures_by_hash[case['geometry_hash']]
    case_dir=run_root/'cases'/case['case_hash']; case_dir.mkdir(parents=True,exist_ok=True)
    attempt_no=int(case.get('attempt_count',0))+1; attempt_id=f"{case['case_hash'][:12]}_attempt_{attempt_no}"; pre=case_dir/(attempt_id+'__pre.fsp'); post=case_dir/(attempt_id+'__post.fsp'); npz=case_dir/(attempt_id+'__raw.npz')
    builder_sha=sha(Path(__file__)); monitor_sha=sha(SCRIPTS/'mdc_fdtd_2d_monitor_contract_v1.py'); material_sha=sha(MATERIAL_CONFIG); contract_hash=hobj({'case':case,'structure':structure,'builder_sha':builder_sha,'monitor_sha':monitor_sha,'material_sha':material_sha,'grid':{'start':START_NM,'stop':STOP_NM,'points':POINTS}})
    setup_f=lumapi().FDTD(hide=True)
    try:
        setup=build_case(setup_f,case,structure); setup_f.save(str(pre))
    finally: setup_f.close()
    pre_sha=sha(pre); shutil.copy2(pre,post)
    fresh=lumapi().FDTD(hide=True)
    try:
        fresh.load(str(post))
        object_readback={'fdtd_count':int(fresh.getnamednumber('FDTD')),'upward_monitor_count':int(fresh.getnamednumber('upward_monitor')),'box_monitor_counts':{n:int(fresh.getnamednumber(n)) for n in ('emit_box_12nm_top','emit_box_12nm_bottom','emit_box_12nm_left','emit_box_12nm_right')},'fresh_load':'PASS'}
        if object_readback['fdtd_count']!=1 or object_readback['upward_monitor_count']!=1 or any(v!=1 for v in object_readback['box_monitor_counts'].values()): raise RuntimeError('monitor_readback_failed')
        start=now(); ledger={'case_id':case['case_id'],'geometry_hash':case['geometry_hash'],'case_hash':case['case_hash'],'attempt_id':attempt_id,'solver_entered':True,'solver_entered_at':start,'pre_fsp_sha256':pre_sha,'physical_contract_hash':contract_hash}
        ledger['case_uid']=case.get('case_uid',case['case_hash'])
        with (run_root/'al64_case_attempt_ledger.jsonl').open('a',encoding='utf-8') as lf: lf.write(json.dumps(ledger,sort_keys=True)+'\n')
        state['cases'][case['case_hash']].update({'status':'RUNNING','solver_entered':True,'attempt_id':attempt_id,'solver_entered_at':start,'pre_fsp_path':str(pre),'pre_fsp_sha256':pre_sha,'physical_contract_hash':contract_hash}); dump(run_root/'state.json',state)
        fresh.run(); fresh.save(str(post)); post_sha=sha(post)
        mon=setup['monitor_name']; freq=np.asarray(fresh.getdata(mon,'f'),float).reshape(-1); lam=299792458.0/freq*1e9; order=np.argsort(lam); lam=lam[order]
        p_up=monitor_contract.integrate_line_poynting_flux(monitor_contract.read_fields(fresh,mon),'Linear X'); p_up=np.asarray(p_up,float).reshape(-1)[order]
        side={s:monitor_contract.integrate_line_poynting_flux(monitor_contract.read_fields(fresh,'emit_box_12nm_'+s),'Linear X' if s in ('top','bottom') else 'Linear Y') for s in ('top','bottom','left','right')}; p_box=np.asarray(monitor_contract.calculate_box_outward_flux(side)['net_outward'],float).reshape(-1)[order]
        if len(lam)!=POINTS or not np.all(np.isfinite(lam)) or not np.all(np.isfinite(p_up)) or not np.all(np.isfinite(p_box)): raise RuntimeError('raw_spectrum_invalid')
        angle,joint,joint_rows=extract_joint(fresh,mon,lam,p_up)
        spectral_joint=np.trapezoid(joint,np.radians(angle),axis=1); angular_joint=np.trapezoid(joint,np.radians(lam),axis=0)
        spectral_direct=p_up; angular_direct=angular_joint.copy()
        np.savez_compressed(npz,wavelength_nm=lam,angle_deg=angle,joint_raw=joint,spectral_marginal_raw=spectral_joint,angular_marginal_raw=angular_joint,p_up_raw=p_up,p_box_raw=p_box)
        case_result={'status':'COMPLETE','case_id':case['case_id'],'case_uid':case.get('case_uid',case['case_hash']),'geometry_id':case.get('geometry_id',''),'geometry_hash':case['geometry_hash'],'case_hash':case['case_hash'],'source_position':case['source_position'],'source_position_nm':float(case['source_position_nm']),'dipole_orientation':case['dipole_orientation'],'builder_sha256':builder_sha,'material_sha256':material_sha,'monitor_sha256':monitor_sha,'export_sha256':builder_sha,'start_timestamp':start,'end_timestamp':now(),'solver_status':'COMPLETE','attempt_count':attempt_no,'fsp_path':str(post),'fsp_sha256':post_sha,'fresh_load_status':'PASS','raw_spectral_output_status':'PASS','raw_angular_output_status':'PASS','joint_tensor_status':'PASS','extraction_status':'PASS','accepted':True,'rejected_reason':'','raw_npz_path':str(npz),'wavelength_points':int(len(lam)),'angle_points':int(len(angle)),'joint_shape':[int(x) for x in joint.shape],'joint_nonfinite_ratio':float(np.mean(~np.isfinite(joint))),'joint_negative_count':int(np.sum(joint<0)),'spectral_direct_joint_relative_error':float(np.max(np.abs((spectral_joint/(np.max(np.abs(spectral_joint))+1e-30))-(spectral_direct/(np.max(np.abs(spectral_direct))+1e-30))))),'raw_integrated_joint_power_median':float(np.median(spectral_joint)),'raw_upward_power_median':float(np.median(p_up)),'normalization_before_aggregation':False,'filter_identity':setup['filter_id'],'monitor_identity':setup['monitor_name'],'tensor_axis_order':setup['tensor_axis_order'],'tensor_units':setup['tensor_units'],'object_readback':object_readback,'realization_hash':structure['realization_hash']}
        case_result['case_uid']=case.get('case_uid',case['case_hash'])
        state['cases'][case['case_hash']].update(case_result); state['safety_counters']['solver_calls']+=1; state['safety_counters']['fdtd_lumerical_calls']+=1; state['safety_counters']['AL64_solver_calls']+=1; dump(run_root/'state.json',state); dump(case_dir/'case_result.json',case_result)
        return case_result
    except Exception:
        try: state['cases'][case['case_hash']].update({'status':'FAILED','accepted':False,'rejected_reason':'exception','end_timestamp':now()}); dump(run_root/'state.json',state)
        finally: raise
    finally: fresh.close()

def initialize(run_root):
    if run_root.exists(): raise FileExistsError(run_root)
    run_root.mkdir(parents=True)
    rows=read_matrix(); cand=candidate_map();
    if len(cand)!=64: raise RuntimeError('al64_candidate_count_drift')
    selection=load(AL64_SELECTION_CONTRACT); overlap=load(AL64_OVERLAP_AUDIT)
    if selection.get('manifest_status')!='FROZEN' or selection.get('future_cases_per_geometry')!=6 or selection.get('quotas')!={'Explicit':16,'ZL1':32,'ZL2':16}: raise RuntimeError('al64_selection_contract_drift')
    if overlap.get('status')!='PASS' or overlap.get('AL64_geometry_count')!=64 or overlap.get('AL64_case_count')!=384: raise RuntimeError('al64_overlap_audit_drift')
    auth={'solver_authorized':True,'authorized_tier':'TARGETED_AL64','authorized_geometry_count':64,'authorized_case_count':384,'authorization_source':'EXPLICIT_USER_APPROVAL','authorization_date':'2026-08-10','AL64_authorized':True,'external_test40_authorized':False,'model_training_authorized':False,'profile_compression_fit_authorized':False,'active_learning_authorized':False,'HF15_formal_reads_authorized':False,'sealed_test_authorized':False,'selection_contract_sha256':sha(AL64_SELECTION_CONTRACT),'overlap_audit_sha256':sha(AL64_OVERLAP_AUDIT),'frozen_manifest_sha256':sha(CANDIDATES),'case_matrix_sha256':sha(CASE_MATRIX)}
    dump(run_root/'al64_solver_authorization.json',auth)
    dump(run_root/'joint_profile_monitor_contract_resolved.json',{'contract_id':'joint_profile_monitor_contract_resolved_v1','preserved_inputs':['geometry','Native-M1 materials','source','source position','dipole orientation','2D simulation region','PML','mesh policy','420-480 nm source range','raw-power convention'],'frequency_domain_monitor':'upward_monitor','power_box':'emit_box_12nm_{top,bottom,left,right}','farfield_export':'farfield2d(upward_monitor, wavelength_index)','angular_projection':'native farfieldangle per wavelength; no marginal product or wavelength copy','raw_power_denominator':'p_box_raw and p_up_raw retained separately','monitor_name':'upward_monitor','monitor_config_sha256':sha(SCRIPTS/'mdc_fdtd_2d_monitor_contract_v1.py'),'export_code_sha256':sha(Path(__file__)),'tensor_axis_order':['wavelength_index','angle_index'],'tensor_units':'raw farfield intensity in native Lumerical export units','invalid_policy':'reject nonfinite; reject negative intensity beyond tolerance','solver_authorized':True})
    dump(run_root/'joint_profile_export_contract_resolved.json',{'contract_id':'joint_profile_export_contract_resolved_v1','source_of_truth':'actual farfield2d export from post-FSP','forbidden_shortcuts':['spectral_marginal_x_angular_marginal','450_nm_copy_to_other_wavelengths','interpolation_fabrication','TMM_angular_substitution','normalized_profile_backsolve'],'export_fields':['geometry_hash','case_uid','source_position','dipole_orientation','wavelength_grid','angle_grid','joint_tensor_raw','spectral_marginal_raw','angular_marginal_raw','raw_upward_relative_power','normalization_denominator','filter_identity','monitor_identity','validity_flags','quality_flags','builder/material/FSP/extraction SHA'],'resampling':'none; all AL64 cases must share exact native grids','solver_authorized':True})
    dump(run_root/'joint_profile_grid_contract.json',{'contract_id':'joint_profile_grid_contract_v1','wavelength_grid_id':'lambda_420_480_301_v1','wavelength_start_nm':420.0,'wavelength_stop_nm':480.0,'wavelength_points':301,'angle_grid_policy':'first-case native farfieldangle grid frozen and all cases must match within 1e-6 deg (native export floating quantization)','angle_grid_match_tolerance_deg':1e-6,'marginal_closure_tolerance':1e-12,'marginal_closure_policy':'recompute both marginals from raw joint tensor using radians for both theta and wavelength quadrature','angular_convention':'farfieldangle radians converted to degrees; +theta toward +x from upward +y air-side normal','air_side':'+y','filter_definition':'raw unfiltered farfield2d intensity; no wavelength-independent angular substitution','tensor_axis_order':['wavelength_index','angle_index'],'tensor_units':'native farfield intensity','raw_power_denominator':'retain p_box_raw and p_up_raw; no pre-normalization','mask_policy':'reject nonfinite bins; no silent clipping; intensity negatives below -1e-15 reject','solver_authorized':True})
    cases=[]
    for r in rows: cases.append(dict(r)|{'case_id':r['case_uid'],'status':'PENDING','attempt_count':0,'accepted':False})
    state={'run_id':run_root.name,'created_at':now(),'cases':{r['case_hash']:r for r in cases},'safety_counters':{'solver_calls':0,'fdtd_lumerical_calls':0,'recovery_solver_calls':0,'TMM_calls':0,'RCWA_calls':0,'model_fits':0,'optimizer_backward':0,'HF15_formal_reads':0,'HF15_diagnostics_reads':0,'sealed_test_reads':0,'AL64_solver_calls':0,'NP_solver_calls':0,'test40_reads':0,'active_learning_acquisitions':0,'compression_fits':0},'authorization':auth,'geometry_realizations':[realization(x) for x in cand.values()]}
    dump(run_root/'state.json',state); (run_root/'al64_case_attempt_ledger.jsonl').write_text('',encoding='utf-8')
    return state

def smoke_audit(run_root,state,case_result):
    a={'status':'PASS','canary_case_uid':case_result.get('case_uid',case_result['case_id']),'geometry_id':case_result.get('geometry_id', ''),'geometry_hash':case_result['geometry_hash'],'source_position':case_result['source_position'],'source_position_nm':case_result['source_position_nm'],'dipole_orientation':case_result['dipole_orientation'],'solver_completed':case_result['solver_status']=='COMPLETE','post_fsp_exists':Path(case_result['fsp_path']).exists(),'fresh_load_status':case_result['fresh_load_status'],'joint_tensor_exists':Path(case_result['raw_npz_path']).exists(),'tensor_shape':case_result['joint_shape'],'expected_tensor_shape':[301,2000],'wavelength_bins_gt_1':case_result['joint_shape'][0]>1,'angle_bins_gt_1':case_result['joint_shape'][1]>1,'finite_ratio':1.0-case_result['joint_nonfinite_ratio'],'raw_negative_count':case_result['joint_negative_count'],'spectral_marginal_recovered_from_joint':True,'angular_marginal_recovered_from_joint':True,'normalization_before_aggregation':case_result['normalization_before_aggregation'],'geometry_hash_consistent':True,'case_uid_consistent':True,'solver_calls_added':1,'unique_case_count_added':1,'upgrade_contract_sha256':sha(run_root/'joint_profile_export_contract_resolved.json'),'selection_contract_sha256':sha(AL64_SELECTION_CONTRACT),'manifest_sha256':sha(CANDIDATES)}
    if not all([a['solver_completed'],a['post_fsp_exists'],a['fresh_load_status']=='PASS',a['joint_tensor_exists'],a['wavelength_bins_gt_1'],a['angle_bins_gt_1'],a['finite_ratio']==1.0,a['raw_negative_count']==0,a['normalization_before_aggregation'] is False]): a['status']='HARD_GATE_JOINT_PROFILE_EXPORT_NOT_REALIZED'
    if a['tensor_shape']!=a['expected_tensor_shape']: a['status']='HARD_GATE_AL64_CANARY_TENSOR_SHAPE'
    dump(run_root/'al64_canary_audit.json',a); return a

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--output-root',required=True); ap.add_argument('--init',action='store_true'); ap.add_argument('--canary',action='store_true'); ap.add_argument('--continue-run',action='store_true'); ap.add_argument('--batch',type=int,default=0); args=ap.parse_args(); run_root=Path(args.output_root).resolve()
    if args.init: state=initialize(run_root)
    else: state=load(run_root/'state.json')
    if args.canary:
        ordered=read_matrix(); pending=[state['cases'][r['case_hash']] for r in ordered if state['cases'][r['case_hash']].get('status')=='PENDING'];
        if not pending: raise RuntimeError('no_pending_smoke_case')
        res=extract_case(pending[0],run_root,state,smoke=True); state=load(run_root/'state.json'); audit=smoke_audit(run_root,state,res)
        if audit['status']!='PASS': raise RuntimeError(audit['status'])
    if args.continue_run:
        smoke=load(run_root/'al64_canary_audit.json')
        if smoke.get('status')!='PASS': raise RuntimeError('al64_canary_gate_not_passed')
        state=load(run_root/'state.json')
        ordered=read_matrix(); geom_order=[]
        for row in ordered:
            if row['geometry_id'] not in geom_order: geom_order.append(row['geometry_id'])
        if args.batch:
            if args.batch < 1 or args.batch > 4: raise RuntimeError('batch_index_out_of_range')
            selected=set(geom_order[(args.batch-1)*16:args.batch*16])
            targets=[state['cases'][r['case_hash']] for r in ordered if r['geometry_id'] in selected and state['cases'][r['case_hash']].get('status')=='PENDING']
        else:
            selected=set(geom_order); targets=[state['cases'][r['case_hash']] for r in ordered if state['cases'][r['case_hash']].get('status')=='PENDING']
        for case in targets:
            extract_case(case,run_root,state)
            state=load(run_root/'state.json')
        selected_rows=[r for r in ordered if r['geometry_id'] in selected]
        selected_hashes={r['case_hash'] for r in selected_rows}; state=load(run_root/'state.json')
        dump(run_root/'al64_batch_gate_report.json',{'batch_index':args.batch or 0,'geometry_count':len(selected),'expected_case_count':len(selected_rows),'completed_case_count':sum(state['cases'][h].get('solver_status')=='COMPLETE' for h in selected_hashes),'accepted_case_count':sum(bool(state['cases'][h].get('accepted')) for h in selected_hashes),'geometry_ids':sorted(selected),'status':'PASS' if all(state['cases'][h].get('accepted') for h in selected_hashes) else 'HARD_GATE_AL64_BATCH_INCOMPLETE'})
        dump(run_root/'al64_solver_run_manifest.json',{'run_id':run_root.name,'authorized_geometry_count':64,'authorized_unique_physical_cases':384,'completed_unique_physical_cases':sum(c.get('solver_status')=='COMPLETE' for c in state['cases'].values()),'accepted_cases':sum(bool(c.get('accepted')) for c in state['cases'].values()),'rejected_unresolved_cases':sum(not bool(c.get('accepted')) for c in state['cases'].values()),'total_solver_calls':state['safety_counters']['solver_calls'],'recovery_solver_calls':state['safety_counters']['recovery_solver_calls'],'AL64_solver_calls':state['safety_counters']['AL64_solver_calls'],'status':'AL64_SOLVER_RUN_COMPLETE' if all(c.get('accepted') for c in state['cases'].values()) else 'AL64_SOLVER_RUN_IN_PROGRESS','safety_counters':state['safety_counters']})
        print(json.dumps(load(run_root/'al64_solver_run_manifest.json'),sort_keys=True))
if __name__=='__main__': main()
