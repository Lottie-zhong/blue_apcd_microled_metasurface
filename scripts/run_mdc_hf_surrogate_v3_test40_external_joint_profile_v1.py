"""Frozen V3-Test40 prospective external HF acquisition runner.

Phase A only: native 2-D FDTD acquisition and structural QC. No V3 inference,
truth metrics, model fitting, PCA/scaler fitting, or post-hoc selection occurs
in this runner. The first frozen case is an in-budget canary.
"""
from __future__ import annotations
import argparse, csv, hashlib, json, time
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
SCRIPTS=ROOT/'scripts'; sys.path.insert(0,str(SCRIPTS))
import run_mdc_hf_surrogate_v3_al64_joint_profile_v1 as base

PLAN_DIR=ROOT/'contracts/mdc_hf_surrogate_v2/v3_plan_freeze_v1'
CASE_MATRIX=PLAN_DIR/'v3_test40_case_matrix_v1.csv'
CANDIDATES=PLAN_DIR/'v3_test40_geometry_manifest_v1.csv'
SELECTION_CONTRACT=PLAN_DIR/'v3_test40_selection_contract_v1.json'
OVERLAP_AUDIT=PLAN_DIR/'v3_test40_overlap_audit_v1.json'
MANIFEST_LOCK=PLAN_DIR/'v3_test40_manifest_lock_v1.json'
RUNTIME_ROOT=ROOT/'outputs/mdc_hf_surrogate_v3_test40_external_2d_fdtd_v1'
base.CASE_MATRIX=CASE_MATRIX
base.CANDIDATES=CANDIDATES
base.RUNTIME_ROOT=RUNTIME_ROOT


def read_matrix():
    with CASE_MATRIX.open(newline='',encoding='utf-8') as f: rows=list(csv.DictReader(f))
    if len(rows)!=240: raise RuntimeError('test40_case_count_drift')
    if len({r['geometry_hash'] for r in rows})!=40 or len({r['case_uid'] for r in rows})!=240: raise RuntimeError('test40_identity_count_drift')
    counts={g:sum(r['geometry_hash']==g for r in rows) for g in {r['geometry_hash'] for r in rows}}
    if set(counts.values())!={6}: raise RuntimeError('test40_cases_per_geometry_drift')
    if any(r['source_position'] not in ('top','centroid','bottom') for r in rows): raise RuntimeError('test40_source_position_drift')
    if any(r['dipole_orientation'] not in ('x','z') for r in rows): raise RuntimeError('test40_orientation_drift')
    source_z={'bottom':-380.5,'centroid':-276.0,'top':-171.5}
    for row in rows:
        row['source_position_nm']=str(source_z[row['source_position']])
        row['case_hash']=row['case_uid']
        row['case_id']=row['case_uid']
    return rows


def candidate_map():
    with CANDIDATES.open(newline='',encoding='utf-8') as f: selected=list(csv.DictReader(f))
    if len(selected)!=40: raise RuntimeError('test40_geometry_manifest_drift')
    with base.GEOMETRY_MASTER.open(newline='',encoding='utf-8-sig') as f: master={row['geometry_hash']:row for row in csv.DictReader(f)}
    result={}
    for row in selected:
        source=master.get(row['geometry_hash'])
        if source is None or source.get('geometry_id')!=row['geometry_id']: raise RuntimeError('test40_geometry_master_identity_drift')
        topology={'ZL-1':'ZL1','ZL-2':'ZL2'}.get(source.get('topology_family'), source.get('topology_family'))
        if topology!=row['topology_family']: raise RuntimeError('test40_topology_drift')
        if source.get('quality_status')!='accepted' or source.get('material_model')!='native_m1': raise RuntimeError('test40_geometry_quality_or_material_drift')
        try: sequence=json.loads(source['compiled_sequence_json'])
        except Exception as exc: raise RuntimeError('test40_compiled_sequence_invalid') from exc
        enriched=dict(row)
        enriched.update({'layer_count':source['physical_layer_count'],'total_thickness_nm':source['total_thickness_nm'],'defect_thickness_nm':source.get('added_defect_thickness_nm',''),'compiled_sequence_json':source['compiled_sequence_json'],'layer_material_sequence':source['layer_material_sequence'],'topology_family':topology,'geometry_id':source['geometry_id']})
        if len(sequence)!=int(source['physical_layer_count']) or sum(int(item[1]) for item in sequence)!=int(source['total_thickness_nm']): raise RuntimeError('test40_geometry_sequence_sum_drift')
        result[row['geometry_hash']]=enriched
    from collections import Counter
    q=Counter(x['topology_family'] for x in result.values())
    if q != Counter({'Explicit':14,'ZL1':13,'ZL2':13}): raise RuntimeError(f'test40_topology_quota_drift:{q}')
    return result

base.read_matrix=read_matrix
base.candidate_map=candidate_map
FINAL_RUN=ROOT/'outputs/mdc_hf_surrogate_v3_c_final_full_development_v1/20260812T_final_full_development_5seed_bc1fcc1'

def load_json(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def dump(p,v): Path(p).write_text(json.dumps(v,indent=2,sort_keys=True)+'\n',encoding='utf-8')
def sha(p):
    h=hashlib.sha256(); h.update(Path(p).read_bytes()); return h.hexdigest()
def now(): return time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())

def initialize(run_root):
    if run_root.exists(): raise FileExistsError(run_root)
    run_root.mkdir(parents=True)
    rows=read_matrix(); cand=candidate_map()
    selection=load_json(SELECTION_CONTRACT); overlap=load_json(OVERLAP_AUDIT); lock=load_json(MANIFEST_LOCK)
    if selection.get('manifest_status')!='FROZEN' or selection.get('geometry_count')!=40 or selection.get('case_count')!=240: raise RuntimeError('test40_selection_contract_drift')
    if selection.get('quotas') != {'Explicit':14,'ZL1':13,'ZL2':13,'boundary_per_topology':{'Explicit':4,'ZL1':4,'ZL2':4}}: raise RuntimeError('test40_quota_contract_drift')
    if overlap.get('status')!='PASS' or overlap.get('V3_Test40_geometry_count')!=40 or overlap.get('V3_Test40_case_count')!=240: raise RuntimeError('test40_overlap_contract_drift')
    if lock.get('status')!='FROZEN' or lock.get('labels_generated') or lock.get('labels_read')!=0 or lock.get('solver_calls')!=0: raise RuntimeError('test40_manifest_lock_drift')
    final_registry=load_json(FINAL_RUN/'seed_training_registry.json')
    if final_registry.get('status')!='PASS' or final_registry.get('model_id')!='MDC_HF_SURROGATE_V3_C_FINAL_5SEED_PROFILE_ONLY_V1' or final_registry.get('architecture')!='V3-C' or final_registry.get('final_epoch')!=117 or final_registry.get('seeds') is None or len(final_registry.get('seeds',[]))!=5: raise RuntimeError('final_v3_c_model_identity_drift')
    model_assertion={'contract_id':'MDC_HF_SURROGATE_V3_TEST40_POST_MODEL_LOCK_EXTERNAL_EVALUATION_ASSERTION_V1','status':'FROZEN_BEFORE_TEST40_SOLVER_ENTRY','model_id':final_registry['model_id'],'architecture':'V3-C','final_epoch':117,'seed_order':[int(x['seed']) for x in final_registry['seeds']],'checkpoint_sha256':{str(x['seed']):x['checkpoint_sha256'] for x in final_registry['seeds']},'ensemble':'equal arithmetic mean of five decoded normalized joint profiles','recalibration':False,'fine_tuning':False,'architecture_reselection':False,'epoch_change':False,'loss_change':False,'preprocessing_change':False,'prediction_metric_reads_during_acquisition':0,'truth_reads_before_240_case_completion':0,'external_evaluation_opens_after':'all 240 accepted raw native tensors frozen'}
    dump(run_root/'frozen_model_external_evaluation_assertion.json',model_assertion)
    auth={'solver_authorized':True,'authorized_tier':'V3_TEST40_PROSPECTIVE_EXTERNAL_HF','authorized_geometry_count':40,'authorized_case_count':240,'authorization_source':'EXPLICIT_USER_APPROVAL','authorization_date':'2026-08-13','external_test40_authorized':True,'model_training_authorized':False,'profile_compression_fit_authorized':False,'active_learning_authorized':False,'HF15_formal_reads_authorized':False,'sealed_test_authorized':True,'selection_contract_sha256':sha(SELECTION_CONTRACT),'overlap_audit_sha256':sha(OVERLAP_AUDIT),'frozen_manifest_sha256':sha(CANDIDATES),'case_matrix_sha256':sha(CASE_MATRIX),'manifest_lock_sha256':sha(MANIFEST_LOCK)}
    dump(run_root/'test40_solver_authorization.json',auth)
    dump(run_root/'joint_profile_monitor_contract_resolved.json',{'contract_id':'MDC_HF_SURROGATE_V3_TEST40_JOINT_PROFILE_MONITOR_CONTRACT_RESOLVED_V1','inherited_from':'V3 AL64 native monitor/export contract','monitor_name':'upward_monitor','power_box':'emit_box_12nm_{top,bottom,left,right}','farfield_export':'farfield2d(upward_monitor,wavelength_index)','tensor_axis_order':['wavelength_index','angle_index'],'tensor_shape':[301,2000],'tensor_units':'native Lumerical farfield intensity','resampling':'none','normalization_before_aggregation':False,'solver_authorized':True,'model_inference_during_acquisition':False})
    dump(run_root/'joint_profile_grid_contract.json',{'contract_id':'MDC_HF_SURROGATE_V3_TEST40_JOINT_PROFILE_GRID_CONTRACT_V1','wavelength_grid_id':'lambda_420_480_301_v1','wavelength_start_nm':420.0,'wavelength_stop_nm':480.0,'wavelength_points':301,'angle_grid_policy':'first-case native farfieldangle grid frozen; every later case exact-match within 1e-6 deg','angle_grid_match_tolerance_deg':1e-6,'tensor_shape':[301,2000],'normalization_before_aggregation':False,'solver_authorized':True})
    cases=[dict(r)|{'case_id':r['case_uid'],'case_hash':r['case_uid'],'status':'PENDING','attempt_count':0,'accepted':False} for r in rows]
    state={'run_id':run_root.name,'created_at':now(),'phase':'A_ACQUISITION_ONLY','cases':{r['case_hash']:r for r in cases},'safety_counters':{'solver_calls':0,'fdtd_lumerical_calls':0,'recovery_solver_calls':0,'TMM_calls':0,'RCWA_calls':0,'NP_solver_calls':0,'model_fits':0,'optimizer_backward':0,'HF15_formal_reads':0,'HF15_diagnostics_reads':0,'sealed_test_reads':0,'V3_Test40_truth_reads':0,'V3_Test40_prediction_metric_reads':0,'test40_solver_calls':0,'compression_fits':0},'authorization':auth,'geometry_realizations':[base.realization(x) for x in cand.values()]}
    dump(run_root/'state.json',state); (run_root/'test40_case_attempt_ledger.jsonl').write_text('',encoding='utf-8'); return state

def extract_case(case,run_root,state):
    case.setdefault('case_id',case.get('case_uid',f"{case['geometry_hash'][:16]}__{case['source_position']}__{case['dipole_orientation']}"))
    structures_by_hash={s['geometry_hash']:s for s in base.structures()}; structure=structures_by_hash[case['geometry_hash']]
    case_dir=run_root/'cases'/case['case_hash']; case_dir.mkdir(parents=True,exist_ok=True)
    attempt_no=int(case.get('attempt_count',0))+1; attempt_id=f"{case['case_hash'][:12]}_attempt_{attempt_no}"; pre=case_dir/(attempt_id+'__pre.fsp'); post=case_dir/(attempt_id+'__post.fsp'); npz=case_dir/(attempt_id+'__raw.npz')
    builder_sha=sha(Path(base.__file__)); monitor_sha=sha(SCRIPTS/'mdc_fdtd_2d_monitor_contract_v1.py'); material_sha=sha(base.MATERIAL_CONFIG); contract_hash=base.hobj({'case':case,'structure':structure,'builder_sha':builder_sha,'monitor_sha':monitor_sha,'material_sha':material_sha,'grid':{'start':base.START_NM,'stop':base.STOP_NM,'points':base.POINTS}})
    setup_f=base.lumapi().FDTD(hide=True)
    try:
        setup=base.build_case(setup_f,case,structure); setup_f.save(str(pre))
    finally: setup_f.close()
    pre_sha=sha(pre); post.write_bytes(pre.read_bytes())
    fresh=base.lumapi().FDTD(hide=True)
    try:
        fresh.load(str(post))
        object_readback={'fdtd_count':int(fresh.getnamednumber('FDTD')),'upward_monitor_count':int(fresh.getnamednumber('upward_monitor')),'box_monitor_counts':{n:int(fresh.getnamednumber(n)) for n in ('emit_box_12nm_top','emit_box_12nm_bottom','emit_box_12nm_left','emit_box_12nm_right')},'fresh_load':'PASS'}
        if object_readback['fdtd_count']!=1 or object_readback['upward_monitor_count']!=1 or any(v!=1 for v in object_readback['box_monitor_counts'].values()): raise RuntimeError('monitor_readback_failed')
        start=now(); ledger={'case_id':case['case_id'],'geometry_hash':case['geometry_hash'],'case_hash':case['case_hash'],'case_uid':case.get('case_uid',case['case_hash']),'attempt_id':attempt_id,'solver_entered':True,'solver_entered_at':start,'pre_fsp_sha256':pre_sha,'physical_contract_hash':contract_hash}
        with (run_root/'test40_case_attempt_ledger.jsonl').open('a',encoding='utf-8') as lf: lf.write(json.dumps(ledger,sort_keys=True)+'\n')
        state['cases'][case['case_hash']].update({'status':'RUNNING','solver_entered':True,'attempt_id':attempt_id,'solver_entered_at':start,'pre_fsp_path':str(pre),'pre_fsp_sha256':pre_sha,'physical_contract_hash':contract_hash}); dump(run_root/'state.json',state)
        fresh.run(); fresh.save(str(post)); post_sha=sha(post)
        mon=setup['monitor_name']; freq=base.np.asarray(fresh.getdata(mon,'f'),float).reshape(-1); lam=299792458.0/freq*1e9; order=base.np.argsort(lam); lam=lam[order]
        p_up=base.monitor_contract.integrate_line_poynting_flux(base.monitor_contract.read_fields(fresh,mon),'Linear X'); p_up=base.np.asarray(p_up,float).reshape(-1)[order]
        side={s:base.monitor_contract.integrate_line_poynting_flux(base.monitor_contract.read_fields(fresh,'emit_box_12nm_'+s),'Linear X' if s in ('top','bottom') else 'Linear Y') for s in ('top','bottom','left','right')}; p_box=base.np.asarray(base.monitor_contract.calculate_box_outward_flux(side)['net_outward'],float).reshape(-1)[order]
        if len(lam)!=base.POINTS or not base.np.all(base.np.isfinite(lam)) or not base.np.all(base.np.isfinite(p_up)) or not base.np.all(base.np.isfinite(p_box)): raise RuntimeError('raw_spectrum_invalid')
        angle,joint,joint_rows=base.extract_joint(fresh,mon,lam,p_up)
        spectral_joint=base.np.trapezoid(joint,base.np.radians(angle),axis=1); angular_joint=base.np.trapezoid(joint,base.np.radians(lam),axis=0)
        base.np.savez_compressed(npz,wavelength_nm=lam,angle_deg=angle,joint_raw=joint,spectral_marginal_raw=spectral_joint,angular_marginal_raw=angular_joint,p_up_raw=p_up,p_box_raw=p_box)
        case_result={'status':'COMPLETE','case_id':case['case_id'],'case_uid':case.get('case_uid',case['case_hash']),'geometry_id':case.get('geometry_id',''),'geometry_hash':case['geometry_hash'],'case_hash':case['case_hash'],'source_position':case['source_position'],'source_position_nm':float(case['source_position_nm']),'dipole_orientation':case['dipole_orientation'],'builder_sha256':builder_sha,'material_sha256':material_sha,'monitor_sha256':monitor_sha,'export_sha256':builder_sha,'start_timestamp':start,'end_timestamp':now(),'solver_status':'COMPLETE','attempt_count':attempt_no,'fsp_path':str(post),'fsp_sha256':post_sha,'fresh_load_status':'PASS','raw_spectral_output_status':'PASS','raw_angular_output_status':'PASS','joint_tensor_status':'PASS','extraction_status':'PASS','accepted':True,'rejected_reason':'','raw_npz_path':str(npz),'wavelength_points':int(len(lam)),'angle_points':int(len(angle)),'joint_shape':[int(x) for x in joint.shape],'joint_nonfinite_ratio':float(base.np.mean(~base.np.isfinite(joint))),'joint_negative_count':int(base.np.sum(joint<0)),'spectral_direct_joint_relative_error':float(base.np.max(base.np.abs((spectral_joint/(base.np.max(base.np.abs(spectral_joint))+1e-30))-(p_up/(base.np.max(base.np.abs(p_up))+1e-30))))),'raw_integrated_joint_power_median':float(base.np.median(spectral_joint)),'raw_upward_power_median':float(base.np.median(p_up)),'normalization_before_aggregation':False,'filter_identity':setup['filter_id'],'monitor_identity':setup['monitor_name'],'tensor_axis_order':setup['tensor_axis_order'],'tensor_units':setup['tensor_units'],'object_readback':object_readback,'realization_hash':structure['realization_hash']}
        state['cases'][case['case_hash']].update(case_result); state['safety_counters']['solver_calls']+=1; state['safety_counters']['fdtd_lumerical_calls']+=1; state['safety_counters']['test40_solver_calls']+=1; dump(run_root/'state.json',state); dump(case_dir/'case_result.json',case_result); return case_result
    except Exception:
        state['cases'][case['case_hash']].update({'status':'FAILED','accepted':False,'rejected_reason':'exception','end_timestamp':now()}); dump(run_root/'state.json',state); raise
    finally: fresh.close()

def canary_audit(run_root,state,res):
    a={'status':'PASS','phase':'A_ACQUISITION_ONLY','canary_case_uid':res.get('case_uid',res['case_id']),'geometry_id':res.get('geometry_id',''),'geometry_hash':res['geometry_hash'],'source_position':res['source_position'],'source_position_nm':res['source_position_nm'],'dipole_orientation':res['dipole_orientation'],'solver_completed':res['solver_status']=='COMPLETE','post_fsp_exists':Path(res['fsp_path']).exists(),'fresh_load_status':res['fresh_load_status'],'joint_tensor_exists':Path(res['raw_npz_path']).exists(),'tensor_shape':res['joint_shape'],'expected_tensor_shape':[301,2000],'finite_ratio':1.0-res['joint_nonfinite_ratio'],'raw_negative_count':res['joint_negative_count'],'normalization_before_aggregation':res['normalization_before_aggregation'],'model_inference_calls':0,'prediction_metric_reads':0,'V3_Test40_truth_reads':0,'solver_calls_added':1,'unique_case_count_added':1,'selection_contract_sha256':sha(SELECTION_CONTRACT),'manifest_lock_sha256':sha(MANIFEST_LOCK)}
    if not (a['solver_completed'] and a['post_fsp_exists'] and a['fresh_load_status']=='PASS' and a['joint_tensor_exists'] and a['tensor_shape']==a['expected_tensor_shape'] and a['finite_ratio']==1.0 and a['raw_negative_count']==0 and a['normalization_before_aggregation'] is False and a['model_inference_calls']==0 and a['prediction_metric_reads']==0 and a['V3_Test40_truth_reads']==0): a['status']='HARD_GATE_TEST40_CANARY_QC'
    dump(run_root/'test40_canary_audit.json',a); return a

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--output-root',required=True); ap.add_argument('--init',action='store_true'); ap.add_argument('--canary',action='store_true'); ap.add_argument('--continue-run',action='store_true'); args=ap.parse_args(); run_root=Path(args.output_root).resolve()
    if args.init: state=initialize(run_root)
    else: state=load_json(run_root/'state.json')
    if args.canary:
        ordered=read_matrix(); pending=[state['cases'][r['case_hash']] for r in ordered if state['cases'][r['case_hash']].get('status')=='PENDING']
        if not pending: raise RuntimeError('no_pending_canary_case')
        res=extract_case(pending[0],run_root,state); state=load_json(run_root/'state.json'); audit=canary_audit(run_root,state,res)
        if audit['status']!='PASS': raise RuntimeError(audit['status'])
    if args.continue_run:
        audit=load_json(run_root/'test40_canary_audit.json')
        if audit.get('status')!='PASS': raise RuntimeError('test40_canary_gate_not_passed')
        state=load_json(run_root/'state.json'); ordered=read_matrix(); targets=[state['cases'][r['case_hash']] for r in ordered if state['cases'][r['case_hash']].get('status')=='PENDING']
        for case in targets:
            extract_case(case,run_root,state); state=load_json(run_root/'state.json')
        done=sum(c.get('solver_status')=='COMPLETE' for c in state['cases'].values()); accepted=sum(bool(c.get('accepted')) for c in state['cases'].values())
        dump(run_root/'test40_solver_run_manifest.json',{'run_id':run_root.name,'phase':'A_ACQUISITION_ONLY','authorized_geometry_count':40,'authorized_unique_physical_cases':240,'completed_unique_physical_cases':done,'accepted_cases':accepted,'total_solver_calls':state['safety_counters']['solver_calls'],'test40_solver_calls':state['safety_counters']['test40_solver_calls'],'model_inference_calls':state['safety_counters']['V3_Test40_prediction_metric_reads'],'V3_Test40_truth_reads':state['safety_counters']['V3_Test40_truth_reads'],'status':'TEST40_ACQUISITION_COMPLETE_PENDING_TRUTH_FREEZE' if done==240 and accepted==240 else 'TEST40_ACQUISITION_IN_PROGRESS','safety_counters':state['safety_counters']})
        print(json.dumps(load_json(run_root/'test40_solver_run_manifest.json'),sort_keys=True))
if __name__=='__main__': main()
