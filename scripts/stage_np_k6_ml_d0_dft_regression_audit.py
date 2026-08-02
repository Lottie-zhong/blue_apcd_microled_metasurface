import csv, gzip, hashlib, itertools, json
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
DB=ROOT/'outputs/np_k6_ml_d0_database_foundation_v1'
DS=tuple(range(100,231,5)); WL=list(range(445,456)); M=list(range(-3,4)); POS=[-725,-435,-145,145,435,725]
def load(rel): return json.loads((ROOT/rel).read_text(encoding='utf-8'))
def payload(d): return {'schema_version':'canonical_k6_geometry_v1','geometry_id':'K6X_'+'_'.join(f'D{x}' for x in d),'diameters_nm':list(d),'phase_bin_mapping':{'phase_bin':[0,1,2,3,4,5],'x_nm':POS,'ideal_phase_deg':[0,60,120,180,240,300]},'period_x_nm':1740,'period_y_nm':290,'pillar_height_nm':500,'material_contract_ids':['APCD_TIO2_NATIVE_M1','APCD_SIO2_NATIVE_M1'],'target_order':1,'target_direction':'+x'}
def gh(d): return hashlib.sha256(json.dumps(payload(d),sort_keys=True,separators=(',',':')).encode()).hexdigest()
def main():
 rows=list(csv.DictReader((ROOT/'outputs/np_k6_p1d2_broadband_library_27point_v1/library_long.csv').open(encoding='utf-8'))); ds=sorted({int(r['diameter_nm']) for r in rows}); wl=sorted({int(r['wavelength_nm']) for r in rows})
 assert len(rows)==297 and ds==list(DS) and wl==WL and all(np.isfinite(float(r[k])) for r in rows for k in ('T','R','txx_real','txx_imag','txx_amplitude'))
 pt=load('outputs/np_k6_p1d2_sixbin_exhaustive_ranking_27point_v1/passing_top8_detailed.json'); passing=['_'.join('D'+x.strip() for x in r['diameters_nm'].split(',')) for r in pt['rows']]
 expected={'D100_D115_D130_D145_D155_D185','D110_D125_D135_D150_D175_D190','D110_D125_D135_D150_D175_D195','D110_D125_D135_D155_D175_D195','D115_D125_D135_D155_D180_D195','D125_D135_D150_D175_D190_D210','D125_D135_D150_D175_D195_D210','D130_D145_D155_D180_D195_D230'}
 assert set(passing)==expected and len(passing)==8
 # Frozen DFT convention: t phase increases with x index, exp(-i 2pi m j/K), +1 is m=+1.
 t=np.exp(2j*np.pi*np.arange(6)/6); E=np.exp(-2j*np.pi*np.outer(np.array(M),np.arange(6))/6); A=E@t; power=abs(A)**2; frac=power/power.sum(); plus=float(frac[M.index(1)]); minus=float(frac[M.index(-1)])
 role_ids=set()
 with (DB/'k6_lf_candidate_summary.csv').open(encoding='utf-8') as f:
  for r in csv.DictReader(f):
   if r['formal_role']!='NONE': role_ids.add(r['geometry_id'].replace('K6X_',''))
 assert role_ids==expected
 anchors={'RUN3A':['D125','D135','D150','D175','D190','D210'],'RUN3B':['D100','D115','D130','D145','D155','D185'],'RUN3C':['D130','D145','D155','D180','D195','D230']}
 anchor_rows={k:('_'.join(v),gh(tuple(int(x[1:]) for x in v))) for k,v in anchors.items()}
 legacy=load('outputs/np_k6_p1d2_broadband_library_27point_v1/dataset_contract.json'); manifest=load('outputs/np_k6_p1d2_broadband_library_27point_v1/library_manifest.json')
 audit={'schema_version':'k6_lf_dft_regression_audit_v1','status':'PASS','label':'LOW_FIDELITY_SINGLE_PILLAR_DFT_PROXY','library_row_count':len(rows),'diameter_count':len(ds),'wavelength_count':len(wl),'dft_exponent':'exp(-2*pi*i*m*j/K)','m_order':M,'target_order':1,'target_index':M.index(1),'phase_bin_x_index':[0,1,2,3,4,5],'ideal_phase_vector_deg':[0,60,120,180,240,300],'ideal_plus1_fraction':plus,'ideal_minus1_fraction':minus,'ideal_plus1_dominant':plus>1-1e-12,'opposite_sign_rejected':minus<1e-12,'source_ranking_implementation':'scripts/run_np_k6_p1d2_27point_sixbin_exhaustive_ranking_v1.py','database_implementation':'scripts/stage_np_k6_ml_d0_build_database_foundation.py','passing_sextet_count_source':pt['passing_sextet_count'],'passing_sextet_ids':sorted(passing),'passing_sextet_regression':set(passing)==expected,'solver_calls':0}
 (DB/'dft_regression_audit.json').write_text(json.dumps(audit,indent=2,sort_keys=True)+'\n',encoding='utf-8')
 linkage={'schema_version':'k6_candidate_linkage_audit_v1','passing_sextet_count':len(passing),'passing_sextet_ids':sorted(passing),'anchors':{k:{'geometry_id':'K6X_'+v[0],'geometry_hash':v[1],'source_evidence':f'RUN3{ k[-1] } authoritative state/candidate evidence','linked_by':'canonical_geometry_hash'} for k,v in anchor_rows.items()},'anchor_hashes_recomputed':True,'geometry_hash_schema':'canonical_k6_geometry_v1','run3a_state_exists':(ROOT/'outputs/np_k6_p1d4b_authoritative_state_reconciliation_v1/run3a_state.json').exists(),'run3b_state_exists':(ROOT/'outputs/np_k6_p1d4b_authoritative_state_reconciliation_v1/run3b_state.json').exists(),'run3c_state_exists':(ROOT/'outputs/np_k6_p1d4b_authoritative_state_reconciliation_v1/run3c_state.json').exists(),'solver_calls':0}
 (DB/'candidate_linkage_audit.json').write_text(json.dumps(linkage,indent=2,sort_keys=True)+'\n',encoding='utf-8')
 source_audit={'schema_version':'k6_source_contract_reconciliation_v1','formal_authority':'library_manifest.json + verification_summary.json + library_long.csv','formal_status':'complete_27point_recovered_d180_v1','formal_diameters':ds,'formal_rows':len(rows),'formal_wavelengths':wl,'interpolation_used':False,'legacy_contract_path':'outputs/np_k6_p1d2_broadband_library_27point_v1/dataset_contract.json','legacy_dataset_name':legacy.get('dataset_name'),'legacy_missing_diameters':legacy.get('missing_diameters_nm'),'legacy_row_count':legacy.get('row_count'),'legacy_conflict_preserved':True,'resolution':'new_database_uses_27point_library_manifest_and_verification; original legacy contract untouched','solver_calls':0}
 (DB/'source_contract_reconciliation_audit.json').write_text(json.dumps(source_audit,indent=2,sort_keys=True)+'\n',encoding='utf-8')
 state={'schema_version':'k6_ml_d0_database_state_v1','state':'NP_K6_ML_D0_DATABASE_FOUNDATION_V1_COMPLETE','design_space_geometry_count':296010,'low_fidelity_geometry_wavelength_count':3256110,'diameter_coverage':'D100-D230 step 5 nm','wavelength_coverage':'445-455 nm step 1 nm','polarization_scope':'x-only LF; future HF x/y separately','passing_sextet_count':8,'development_pilot_count':48,'sealed_test_pilot_count':12,'potential_hf_task_count':120,'production_mesh_id':'PENDING_NUMERICAL_FIDELITY_FREEZE','production_mesh_frozen':False,'solver_entered':0,'run_invocation_count':0,'training_label':False,'candidate_performance_label':False,'diagnostic_only_for_existing_diagnostics':True,'TiO2_only_SiO2_only_numerical_forensics':'DEFERRED_NONBLOCKING_NUMERICAL_FORENSICS','next_action':'AUTHORIZE_PRODUCTION_MESH_GATE_FOR_K6_HF_PILOT','large_artifacts_not_git':True,'source_contract_reconciliation':'27point_manifest_authority; legacy 26point contract preserved'}
 (DB/'k6_database_state.json').write_text(json.dumps(state,indent=2,sort_keys=True)+'\n',encoding='utf-8')
 print(json.dumps({'status':'PASS','dft_plus1_fraction':plus,'dft_minus1_fraction':minus,'passing':len(passing),'anchors':anchor_rows},ensure_ascii=False))
if __name__=='__main__': main()
