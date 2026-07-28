"""Offline NP P1-D4A candidate and no-run execution-package builder."""
from __future__ import annotations
import argparse,csv,hashlib,json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
LIB=ROOT/'outputs/np_k6_p1d2_broadband_library_27point_v1/library_long.csv'
RANK=ROOT/'outputs/np_k6_p1d2_sixbin_exhaustive_ranking_27point_v1'
OUT=ROOT/'outputs/np_k6_p1d4_k6x_candidate_freeze_v1'
PKG=ROOT/'outputs/np_k6_p1d4_k6x_execution_package_v1'
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,x): p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n',encoding='utf-8')
def readj(n): return json.loads((RANK/n).read_text(encoding='utf-8'))
def rows(n): return list(csv.DictReader((RANK/n).open(encoding='utf-8')))
def ds(row): return [int(x) for x in row['diameters_nm'].split(',')]
def cid(d): return 'NP_K6X_'+'_'.join(map(str,d))
def metric(row,k): return float(row[k])
def library():
  data=list(csv.DictReader(LIB.open(encoding='utf-8'))); by={}
  for r in data: by.setdefault(int(r['diameter_nm']),[]).append(r)
  return data,by
def candidate(row,role,by,pareto):
  d=ds(row); at450={int(r['diameter_nm']):r for r in sum((v for v in by.values()),[]) if int(r['wavelength_nm'])==450}
  phases=[float(at450[x]['txx_wrapped_phase_deg']) for x in d]
  amps=[float(r['txx_amplitude']) for x in d for r in by[x]]
  gaps=[290-(d[i]+d[(i+1)%6])/2 for i in range(6)]
  return {'role':role,'candidate_id':cid(d),'ordered_diameters_nm':d,'formal_diameter_ordering':'official passing-combination order; mapped to x-position slots only after sign bridge','phase_bin_order':['bin0','bin1','bin2','bin3','bin4','bin5'],'engineering_pass':row['all_legacy_engineering_gates_pass']=='True','pareto_member':tuple(d) in pareto,'d180_member':180 in d,'phase_rms_mean_deg':None,'phase_rms_mean_status':'not_present_in_formal_passing_schema','phase_rms_max_deg':metric(row,'phase_fit_RMS_band_max'),'max_phase_error_deg':metric(row,'maximum_phase_error_over_band'),'closure_error_450_deg':None,'closure_error_450_status':'threshold_not_frozen_and_not_present_in_formal_passing_schema','max_step_drift_deg':metric(row,'maximum_step_drift_peak_to_peak'),'min_T':metric(row,'minimum_T_over_band'),'min_abs_txx':min(amps),'amplitude_cv':metric(row,'amplitude_CV_band_max'),'phase_450_wrapped_deg':phases,'phase_error_status':'relative common-phase fit retained in formal ranking; absolute x-order sign withheld pending bridge','cyclic_edge_gaps_nm':gaps,'minimum_edge_gap_nm':min(gaps),'max_aspect_ratio':max(500/x for x in d),'geometry_hash':hashlib.sha256(json.dumps({'d':d,'p':[290,290],'h':500},sort_keys=True).encode()).hexdigest(),'source_file':'outputs/np_k6_p1d2_sixbin_exhaustive_ranking_27point_v1/passing_combinations.csv','source_sha256':sha(RANK/'passing_combinations.csv')}
def main():
  OUT.mkdir(parents=True,exist_ok=True);PKG.mkdir(parents=True,exist_ok=True)
  data,by=library(); passing=rows('passing_combinations.csv'); pareto={tuple(ds(x)) for x in rows('pareto_front.csv')}
  summary=readj('candidate_release_summary.json'); phase_d=summary['phase_champion']; phase=next(x for x in passing if ds(x)==phase_d)
  remaining=[x for x in passing if x is not phase]
  balanced=sorted(remaining,key=lambda x:(-metric(x,'minimum_T_over_band'),-min(float(r['txx_amplitude']) for d in ds(x) for r in by[d]),metric(x,'amplitude_CV_band_max'),metric(x,'phase_fit_RMS_band_max'),cid(ds(x))))[0]
  remaining=[x for x in remaining if x is not balanced]
  p=[x for x in remaining if tuple(ds(x)) in pareto]
  if not p: p=remaining
  broad=sorted(p,key=lambda x:(metric(x,'maximum_step_drift_peak_to_peak'),metric(x,'phase_fit_RMS_band_max'),metric(x,'minimum_T_over_band')*-1,cid(ds(x))))[0]
  selected=[candidate(phase,'PHASE_ORIENTED',by,pareto),candidate(balanced,'TRANSMISSION_BALANCED',by,pareto),candidate(broad,'BROADBAND_PARETO_REPRESENTATIVE',by,pareto)]
  assert len({x['candidate_id'] for x in selected})==3 and all(x['engineering_pass'] for x in selected)
  input_files=['candidate_release_summary.json','passing_top8_detailed.json','exhaustive_search_manifest.json','d180_participation_audit.json','ranking_change_from_26point.json','p1d3_y_scope_staleness_audit.json']
  checks={str((RANK/x).relative_to(ROOT)).replace('\\','/') : sha(RANK/x) for x in input_files};checks[str(LIB.relative_to(ROOT)).replace('\\','/')]=sha(LIB)
  audit=[]
  for x in passing:
   q=candidate(x,'UNSELECTED',by,pareto);audit.append(q)
  dump(OUT/'candidate_source_checksums.json',checks)
  dump(OUT/'passing_top8_unified_audit.json',{'schema_note':'phase RMS mean and 450 closure are unavailable in formal passing schema; null values are intentional, not interpolated','field_mapping':{'phase_rms_max_deg':'phase_fit_RMS_band_max','max_phase_error_deg':'maximum_phase_error_over_band','max_step_drift_deg':'maximum_step_drift_peak_to_peak','min_T':'minimum_T_over_band','amplitude_cv':'amplitude_CV_band_max'},'rows':audit})
  dump(OUT/'selected_k6x_candidates.json',{'selected_candidate_count':3,'candidates':selected})
  dump(OUT/'phase_bin_mapping.json',{'status':'orientation_sign_bridge_required','candidates':[{'candidate_id':x['candidate_id'],'diameters_nm':x['ordered_diameters_nm'],'wrapped_phase_450_deg':x['phase_450_wrapped_deg'],'phase_bin_order':x['phase_bin_order']} for x in selected]})
  orient={'status':'HARD_GATE_ORIENTATION_AMBIGUOUS','incident_direction':'normal incidence, source injection axis z, forward +z transmission','transmitted_side':'top/+z monitor plane, inherited P1-D2 reference z=900 nm','x_position_order':'withheld: official diameter order is preserved but not asserted as +x placement','phase_progression':'withheld pending direct sign bridge','target_order':'+1 requested, but its mapping to physical +x requires a direct gratingn/gratingu1 bridge','evidence':['docs/np_k6_p1a_unitcell_solver_reuse_audit_v1.md: order-resolved grating-vector scaffold','outputs/stage13_6_lp_phase_coordinate_patch_audit/stage13_6_audit_report.md: no direct proof gratingn +1 equals ux>0'],'mirror_diagnostic_status':'not a candidate; no solver authorized'}
  dump(OUT/'orientation_sign_convention_contract.json',orient)
  dump(OUT/'selection_decision_audit.json',{'phase_source':'candidate_release_summary.phase_champion','transmission_order':['higher min_T','higher min_abs_txx','lower amplitude_cv','lower phase_rms_max when mean unavailable','candidate_id'],'broadband_order':['lower max_step_drift','lower phase_rms_max','closure unavailable','higher min_T','candidate_id'],'selected_ids':[x['candidate_id'] for x in selected]})
  dump(OUT/'candidate_freeze_manifest.json',{'stage_id':'NP_K6_P1D4_K6X_V1','preferred_stage_id':'NP_K6_P1D4_K6X_V1','resolved_stage_id':'NP_K6_P1D4_K6X_V1','resolution_reason':'no conflicting registry found during scoped audit','solver_entered':0,'input_sha256':checks,'orientation_status':orient['status']})
  geometry={'K':6,'period_x_nm':1740,'period_y_nm':290,'height_nm':500,'pillar_base_z_nm':0,'cross_section':'circular','material':'APCD_TIO2_NATIVE_M1 / Native-M1','candidates':[{'candidate_id':x['candidate_id'],'diameters_nm':x['ordered_diameters_nm'],'cyclic_edge_gaps_nm':x['cyclic_edge_gaps_nm'],'minimum_edge_gap_nm':x['minimum_edge_gap_nm'],'max_aspect_ratio':x['max_aspect_ratio'],'geometry_hash':x['geometry_hash']} for x in selected]}
  budget={'blank_budget':1,'candidate_budget':3,'max_entered_runs':4,'blank_reuse_condition':'only identical physical/monitor/provenance fingerprint with trusted post-FSP','current_solver_entered':0,'no_retry_on_controller_absence':True}
  monitor={'polarization':'x only','wavelength_axis_nm':list(range(445,456)),'source':'plane wave, normal incidence','monitor_contract':['all open transmitted orders from gratingn/gratingm/gratingu1/gratingu2','complex gratingvector when supported','total T, total R, absorption/numerical residual','450 nm near field and phase diagnostic'],'no_interpolation':True}
  dump(PKG/'execution_contract.json',{'status':orient['status'],'scope':['K6-x only','no K6-y','no MDC','no dipole','no tolerance sweep'],'solver_entered':0})
  dump(PKG/'solver_budget_contract.json',budget);dump(PKG/'geometry_contract.json',geometry);dump(PKG/'material_contract.json',{'material':geometry['material'],'background':'inherit P1-D2','substrate':'inherit P1-D2'});dump(PKG/'wavelength_monitor_contract.json',monitor)
  dump(PKG/'diffraction_order_contract.json',{'target_order':'+1','enumeration':'discover all open transmitted orders; do not hard-code +/-1','orientation_status':orient['status']})
  dump(PKG/'normalization_contract.json',{'source_normalization':'required','order_efficiency':'grating_fraction * total_transmission','power_balance':'T+R+A or equivalent residual'})
  dump(PKG/'provenance_contract.json',{'required_labels':['candidate_id','ordered_diameters','geometry_hash','physical_contract_hash','monitor_mapping_hash','polarization','wavelength','diffraction_order','attempt_id','solver-entered','engine-completed','controller-returned','post-saved'],'source_checksums':checks})
  dump(PKG/'case_allowlist.json',{'cases':['K6_FIXED_REFERENCE_BLANK']+[x['candidate_id'] for x in selected],'current_authorization':'no solver calls'})
  dump(PKG/'forbidden_actions.json',{'forbidden':['run','runjobs','MPI','sweepsolve','K6-y','dipole','MDC','tolerance sweep','unapproved candidate'],'current_solver_budget':0})
  dump(PKG/'preflight_manifest.json',{'pre_fsp_status':'not_generated','pre_fsp_count':0,'solver_entered':0,'orientation_status':orient['status'],'ready_for_solver':False})
if __name__=='__main__': main()