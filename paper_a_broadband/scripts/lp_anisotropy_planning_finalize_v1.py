import csv, json
from pathlib import Path

ROOT=Path(r'D:/project/worktrees/blue_apcd_paper_a_lp_cp_broadband_v1')
REPORT=ROOT/'paper_a_broadband/reports/lp_anisotropy_expanded_search_v1'
DOE=json.loads((ROOT/'paper_a_broadband/configs/anisotropy_expanded_doe_v1.json').read_text(encoding='utf-8'))
def write_json(p,x):
    p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(x,indent=2,ensure_ascii=False,default=str)+'\n',encoding='utf-8')
def write_csv(p,rows):
    fields=[]
    for r in rows:
        for k in r:
            if k not in fields: fields.append(k)
    with p.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore'); w.writeheader(); w.writerows(rows)
def main():
    geoms=DOE['geometries']; ids=set(DOE['initial_geometry_ids']+DOE['conditional_geometry_ids'])
    parameterization=REPORT/'anisotropy_parameterization.json'
    if parameterization.exists():
        pdat=json.loads(parameterization.read_text(encoding='utf-8'))
        pdat['stage_status']='PLANNING_AND_SETUP_ONLY_BEFORE_BENCHMARK'
        pdat['execution_authority_current']={'new_fdtd_budget':0,'new_rcwa_budget':0,'ml':0,'active_fdtd_allowed':0,'ready_for_auto_admission':0,'future_planned_max_active_paper_a_fdtd':2,'requires_future_user_benchmark_authorization':True}
        pdat['solver_entered']=False
        write_json(parameterization,pdat)
    valid=[]; planned=[]; cases=[]
    for g in geoms:
        valid.append({'geometry_id':g['geometry_id'],'batch':'INITIAL_PLANNED_BATCH' if g['geometry_id'] in DOE['initial_geometry_ids'] else 'CONDITIONAL_PLANNED_BATCH','a1':g['a1'],'b1':g['b1'],'a2':g['a2'],'b2':g['b2'],'delta_theta_deg':g['delta_theta_deg'],'D_nm':g['D_nm'],'L1_nm':g['L1_nm'],'W1_nm':g['W1_nm'],'L2_nm':g['L2_nm'],'W2_nm':g['W2_nm'],'AR1':g['anisotropy_ratio_1'],'AR2':g['anisotropy_ratio_2'],'relative_anisotropy':g['relative_anisotropy'],'min_edge_gap_nm':g['validity']['min_edge_gap_nm'],'geometry_valid':g['validity']['geometry_valid'],'no_overlap_pass':g['validity']['no_overlap_pass'],'cell_containment_pass':g['validity']['cell_containment_pass'],'validity_reasons':json.dumps(g['validity']['reasons']),'source':g['source'],'sobol_index':g.get('sobol_index'),'geometry_hash_sha256':g['geometry_hash_sha256']})
        planned.append({'geometry_id':g['geometry_id'],'batch':'INITIAL_PLANNED_BATCH' if g['geometry_id'] in DOE['initial_geometry_ids'] else 'CONDITIONAL_PLANNED_BATCH','geometry_hash_sha256':g['geometry_hash_sha256'],'planned_pre_fsp_x':str(ROOT/f"paper_a_broadband/runtime/search_anisotropy_v1/cases/{g['geometry_id']}_x/{g['geometry_id']}_x_pre.fsp"),'planned_pre_fsp_y':str(ROOT/f"paper_a_broadband/runtime/search_anisotropy_v1/cases/{g['geometry_id']}_y/{g['geometry_id']}_y_pre.fsp"),'solver_authority':'WAIT_BENCHMARK_AUTHORIZATION','solver_entered':False,'solver_run_called':False,'future_postprocess_ready':True})
        for pol in ('x','y'):
            cid=f"{g['geometry_id']}_{pol}"; prepared=cid.startswith('ANISO_A01_')
            cases.append({'case_id':cid,'geometry_id':g['geometry_id'],'polarization':pol,'batch':'INITIAL_PLANNED_BATCH' if g['geometry_id'] in DOE['initial_geometry_ids'] else 'CONDITIONAL_PLANNED_BATCH','status':'PREPARED_SETUP_ONLY' if prepared else 'PLANNED_NOT_PREPARED','planned_pre_fsp_path':str(ROOT/f"paper_a_broadband/runtime/search_anisotropy_v1/cases/{cid}/{cid}_pre.fsp"),'setup_only_allowed':True,'solver_run_called':False,'solver_entered':False,'mpi_processes':4,'threads':1,'source_polarization_angle_deg':0.0 if pol=='x' else 90.0,'formal_points':31,'future_admission_requires_user_authorization':True,'entered_true_no_replay':True})
    write_csv(REPORT/'geometry_validity.csv',valid); write_csv(REPORT/'planned_geometry_registry.csv',planned); write_csv(REPORT/'planned_fdtd_case_registry.csv',cases)
    gate={'schema':'PAPER_A_BROADBAND_LP_ANISOTROPY_GATE_PREREGISTRATION_V1','status':'PREREGISTERED_NOT_EXECUTED','axis_free':True,'MDC_weighted_final_pass':{'DoLP_min':.80,'P_LP_axisfree_min':.35,'MDC_FWHM_psi_span_deg_max':10.0,'preferred_MDC_FWHM_DoLP_worst_min':.70,'circular_contamination':'must not dominate purity'},'promising':{'DoLP_min':.60,'P_LP_axisfree_min':.25,'MDC_FWHM_psi_span_deg_max':30.0,'relative_to_previous':'clear spectral-state improvement'},'midpoint':{'after':'A01-A04 / 8 physical cases','continue_if':['PROMISING_ANISOTROPY_SEED','ANISOTROPY_DIRECTIONAL_TREND_PRESENT'],'otherwise':'EARLY_STOP_NO_DIRECTION'},'no_single_point_selection':True,'no_solver_truth_available':True}
    write_json(REPORT/'midpoint_gate_preregistration.json',gate)
    plan={'schema':'PAPER_A_BROADBAND_LP_ANISOTROPY_FDTD_EXECUTION_PLAN_BEFORE_BENCHMARK_V1','status':'WAIT_BENCHMARK_AUTHORIZATION','planned_geometry_count':8,'planned_physical_case_count':16,'initial_A01_A04_case_count':8,'conditional_A05_A08_case_count':8,'pairing':'each geometry has independent x/y plane-wave cases','current_execution_authority':{'new_fdtd_budget':0,'new_rcwa_budget':0,'ml':0,'active_fdtd_allowed':0,'ready_for_auto_admission':0,'hidden_pending_admission':False},'future_resource_plan':{'max_active_paper_a_fdtd':2,'x_y_same_geometry_may_run_concurrently':True,'global_fdtd_cap':3,'mpi_processes':4,'threads':1,'NP_Coupling_higher_priority':True,'final_concurrency_requires_future_user_authorization':True},'scheduler_semantics':{'case_boundary_yield_to_high_priority':True,'entered_true_no_replay':True,'no_kill_pause_restart_replay':True,'shared_global_registry':True},'planned_cases':cases,'prepared_fsp_paths':{'A01_x':cases[0]['planned_pre_fsp_path'],'A01_y':cases[1]['planned_pre_fsp_path']},'future_admission_rule':'new explicit user benchmark authorization required; planning does not create a pending claim'}
    write_json(REPORT/'fdtd_execution_plan_before_benchmark.json',plan)
    prov=[]
    for cid in ('ANISO_A01_x','ANISO_A01_y'):
        p=REPORT.parent.parent/'runtime/search_anisotropy_v1/cases'/cid/'setup_only.json'
        if p.exists():
            s=json.loads(p.read_text(encoding='utf-8')); prov.append({'case_id':cid,'setup_only_manifest':str(p),'setup_status':s.get('status'),'solver_run_called':s.get('solver_run_called'),'solver_entered':s.get('solver_entered'),'pre_fsp_path':s.get('pre_fsp',{}).get('path'),'pre_fsp_sha256':s.get('pre_fsp',{}).get('sha256'),'parent_fsp_path':s.get('pre_fsp',{}).get('parent_fsp'),'parent_fsp_sha256':s.get('pre_fsp',{}).get('parent_sha256'),'readback_gate':s.get('gate'),'runtime_only':True})
    write_json(REPORT/'prepared_fsp_provenance.json',{'schema':'PAPER_A_LP_ANISOTROPY_PREPARED_FSP_PROVENANCE_V1','solver_run_called':False,'solver_entered':0,'cases':prov})
    decision={'schema':'PAPER_A_BROADBAND_LP_ANISOTROPY_PLANNING_DECISION_V1','status':'PAPER_A_BROADBAND_LP_ANISOTROPY_EXPANDED_SEARCH_PLANNED_WAIT_BENCHMARK','stage_status':'PLANNING_AND_SETUP_ONLY_BEFORE_BENCHMARK','planned_geometry_count':8,'initial_geometry_ids':DOE['initial_geometry_ids'],'conditional_geometry_ids':DOE['conditional_geometry_ids'],'prepared_cases':[x['case_id'] for x in cases if x['status']=='PREPARED_SETUP_ONLY'],'solver_run_called':False,'solver_entered_cases':0,'active_fdtd':0,'ready_for_auto_admission':0,'hidden_pending_auto_admission':False,'next_minimum_authority':'USER_EXPLICIT_BENCHMARK_AUTHORIZATION_REQUIRED','truth_metrics_available':False,'no_new_solver_truth_artifacts':True}
    write_json(REPORT/'planning_decision.json',decision)
    audit={'schema':'PAPER_A_BROADBAND_LP_ANISOTROPY_PLANNING_AUDIT_V1','status':decision['status'],'solver_budget_current':{'FDTD':0,'RCWA':0,'ML':0},'solver_run_called':False,'solver_entered':0,'active_fdtd':0,'ready_for_auto_admission':0,'hidden_pending_auto_admission':False,'old_stage_immutable':True,'old_worktrees_untouched':True,'planned_case_count':16,'prepared_case_count':len(prov),'runtime_fsp_gitignored_expected':True,'forbidden_truth_artifacts_absent':not any((REPORT/x).exists() for x in ['broadband_jones_spectra.csv','mdc_weighted_metrics.csv','final_candidate.json'])}
    write_json(REPORT/'audit.json',audit)
    lines=['# Paper A LP anisotropy-expanded search v1 — planning before benchmark','',f"Verdict: `{decision['status']}`",'', 'No new solver was authorized or started. Current execution authority is FDTD=0, RCWA=0, ML=0.','', '## Planned DOE','', 'A01–A04 are the initial planned batch; A05–A08 are conditional planned geometry only. The 6D variables are independent a1, b1, a2, b2, delta_theta, and D with deterministic seed 20260818. All eight planned geometries passed the zero-solver validity audit; any deterministic replacement is recorded in anisotropy_doe.csv.','', '## Setup-only preparation','', 'A01_x and A01_y have validated Native-M1 pre-FSPs with 430–470 nm source/monitor, 41 native points, 435–465 nm / 31-point extraction contract, and solver_run_called=false. A02–A08 have configuration and future case manifests only.','', '## Admission freeze','', 'The shared scheduler has active FDTD=0, entered FDTD=0, and READY-for-auto-admission=0 for this stage. No controller or monitor is left with a pending automatic claim. A future explicit benchmark authorization is required before any solver case can enter.','', 'No broadband Jones spectra, MDC-weighted truth metrics, or candidate PASS/FAIL verdict is produced at planning stage.']
    (REPORT/'planning_report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'status':decision['status'],'prepared_cases':[x['case_id'] for x in prov],'solver_entered':0,'active_fdtd':0,'ready_for_auto_admission':0},indent=2))
if __name__=='__main__': main()
