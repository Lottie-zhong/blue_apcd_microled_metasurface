import json
from pathlib import Path
from collections import defaultdict
R=Path(r'D:\project\worktrees\blue_apcd_lp_stage11_4'); S0=R/'outputs/lp_ml_dataset_v1/staging/lp_ml_dataset_v1_round1_smoke_attempt2_v1'; S1=R/'outputs/lp_ml_dataset_v1/staging/lp_ml_dataset_v1_round1_production_attempt1_v1'; A=R/'outputs/lp_ml_dataset_v1/analysis'
def load(p): return json.loads(p.read_text(encoding='utf-8'))
cs=[]
for S in [S0,S1]:
    for p in S.glob('subruns/*/*/checkpoint.json'): cs.append(load(p))
by=defaultdict(list)
for c in cs: by[c['candidate_id']].append(c)
def tsum(c):
    t=[float(r['source_T']) for r in c.get('rows',[])]; return {'input_polarization':c['input_polarization'],'min_T':min(t),'max_T':max(t),'T_vector':t,'wavelengths_nm':[float(r['wavelength_nm']) for r in c['rows']]}
neighbor_ids=['LPML_R1_GLOBAL_SOBOL_050','LPML_R1_GLOBAL_SOBOL_051','LPML_R1_GLOBAL_SOBOL_052','LPML_R1_GLOBAL_SOBOL_053']
failed=load(S1/'subruns/LPML_R1_GLOBAL_SOBOL_054/y/run_result.json'); x=load(S1/'subruns/LPML_R1_GLOBAL_SOBOL_054/x/checkpoint.json')
out={'failed_case':'LPML_R1_GLOBAL_SOBOL_054_y','failed_configuration_gate':failed.get('configuration_gate'),'failed_setup':failed.get('setup_before_save'),'failed_raw_T_available':False,'failed_raw_metadata_available':False,'accepted_failed_geometry_x':tsum(x),'neighbor_cases':{i:[tsum(c) for c in by[i]] for i in neighbor_ids if i in by},'builder_comparison':{'x_y_geometry_fields_same':True,'x_polarization_angle_deg':0.0,'y_polarization_angle_deg':90.0,'source_direction':'Forward','source_z_nm':-250.0,'monitor_z_nm':1000.0,'T_monitor_z_nm':1000.0,'monitor_type':'2D Z-normal','boundary':'x/y Periodic, z PML','material':'APCD_TIO2_NATIVE_M1','source_wavelength_start_stop_nm':[450.0,454.0],'local_monitor_frequency_points':9,'use_wavelength_spacing':True,'use_source_limits':True},'sign_convention_audit':{'transmission_is_raw_lumerical_directional_power':'YES','abs_T_fallback':'FORBIDDEN_AND_NOT_USED','monitor_normal_explicitly_overridden':'NO_IN_RUNNER','forward_source_and_transmission_side_geometry':'CONSISTENT_IN_SAVED_SETUP','failed_case_sign_resolution':'INDETERMINATE_WITHOUT_RAW_T'}}
(A/'lp_ml_round1_negative_t_direction_neighbor_audit_v1.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n',encoding='utf-8')
print(json.dumps({'neighbors':len(out['neighbor_cases']),'failed_raw_T':False},indent=2))
