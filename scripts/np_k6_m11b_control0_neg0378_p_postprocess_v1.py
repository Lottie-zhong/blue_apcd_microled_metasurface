from __future__ import annotations
import csv, json, hashlib, math, statistics
from pathlib import Path
from datetime import datetime, timezone

ROOT=Path(r'D:\project\worktrees\blue_apcd_np_k6_mdc_v1')
EVID=ROOT/'outputs'/'np_k6_m11b_control0_neg0378_p_matched_hf_v1'
RUN=EVID/'runtime_runs'/'CONTROL0_NEG0378_P'/'attempt_001'
COUP=Path(r'D:\project\worktrees\blue_apcd_mdc_np_coupling_v1')/'outputs'/'coupling'/'COUPLING_TO_NP_ANGULAR_HANDOFF_TERMINAL_PACKAGE_V1'
RCWA=COUP/'CONTROL0_ALT1_FULL_ANGULAR_SPECTRAL_PROVIDER_V1.csv'
ALT1_FDTD=ROOT/'outputs'/'np_k6_m10c_alt1_neg0378_ps_quantitative_anchor_v1'/'runtime_runs'/'NP_K6_M10C_ALT1_UX_M0d378689399989_P_XLIKE'/'attempt_001'/'spectral_metrics.csv'
W=list(range(445,456)); UX='-0.3786893999886029'; GEOM='5744baf84e4b4405711f0aabdbb7965c294d4b3e4f099f670457fbbbae1c2710'
def now(): return datetime.now(timezone.utc).isoformat()
def sha(p):
 h=hashlib.sha256();
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''): h.update(b)
 return h.hexdigest()
def atomic(p,o):
 p.parent.mkdir(parents=True,exist_ok=True); t=p.with_name(p.name+'.tmp'); t.write_text(json.dumps(o,indent=2,sort_keys=True,ensure_ascii=False,default=str)+'\n',encoding='utf-8'); t.replace(p)
def readcsv(p): return list(csv.DictReader(p.open(encoding='utf-8',newline='')))
def f(x): return float(x)
def stats(vals):
 vals=[abs(float(x)) for x in vals]; vals2=sorted(vals)
 return {'mae':sum(vals)/len(vals),'median':statistics.median(vals),'p90':vals2[max(0,math.ceil(.9*len(vals))-1)],'max':max(vals)}
def csvwrite(p,rows):
 with p.open('w',newline='',encoding='utf-8') as out:
  w=csv.DictWriter(out,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
def main():
 cf=RUN/'spectral_metrics.csv'; co=RUN/'transmitted_orders.csv';
 if not cf.exists() or not co.exists(): raise RuntimeError('CONTROL0_EXTRACTION_MISSING')
 cfd={int(round(f(r['wavelength_nm']))):r for r in readcsv(cf)}
 if sorted(cfd)!=W: raise RuntimeError('CONTROL0_EXACT_11_REQUIRED')
 altfd={int(round(f(r['wavelength_nm']))):r for r in readcsv(ALT1_FDTD)}
 rr=readcsv(RCWA); rc={}
 for r in rr:
  if r['ux_exact']==UX and r['polarization']=='P_XLIKE' and r['candidate'] in ('CONTROL0','ALT1'): rc[(r['candidate'],int(round(f(r['wavelength_nm']))))]=r
 if len([k for k in rc if k[0]=='CONTROL0'])!=11 or len([k for k in rc if k[0]=='ALT1'])!=11: raise RuntimeError('RCWA_MATCHED_22_REQUIRED')
 metrics=['eta_plus1','eta_0','eta_minus1','T_total','R_total']
 matched=[]; residual=[]
 for wl in W:
  c=cfd[wl]; a=altfd[wl]; cr=rc[('CONTROL0',wl)]; ar=rc[('ALT1',wl)]
  row={'wavelength_nm':wl,'CONTROL0_FDTD_eta_plus1':f(c['eta_plus1']),'CONTROL0_RCWA_eta_plus1':f(cr['eta_mplus1']),'ALT1_FDTD_eta_plus1':f(a['eta_plus1']),'ALT1_RCWA_eta_plus1':f(ar['eta_mplus1']),'CONTROL0_FDTD_T':f(c['T_total']),'CONTROL0_RCWA_T':f(cr['T_total']),'ALT1_FDTD_T':f(a['T_total']),'ALT1_RCWA_T':f(ar['T_total']),'CONTROL0_FDTD_R':f(c['R_total']),'CONTROL0_RCWA_R':f(cr['R_total']),'ALT1_FDTD_R':f(a['R_total']),'ALT1_RCWA_R':f(ar['R_total']),'CONTROL0_FDTD_eta0':f(c['eta_0']),'CONTROL0_RCWA_eta0':f(cr['eta_m0']),'ALT1_FDTD_eta0':f(a['eta_0']),'ALT1_RCWA_eta0':f(ar['eta_m0']),'CONTROL0_FDTD_eta_minus1':f(c['eta_minus1']),'CONTROL0_RCWA_eta_minus1':f(cr['eta_mminus1']),'ALT1_FDTD_eta_minus1':f(a['eta_minus1']),'ALT1_RCWA_eta_minus1':f(ar['eta_mminus1'])}
  row['Delta_candidate_RCWA_eta_plus1']=row['ALT1_RCWA_eta_plus1']-row['CONTROL0_RCWA_eta_plus1']; row['Delta_candidate_HF_eta_plus1']=row['ALT1_FDTD_eta_plus1']-row['CONTROL0_FDTD_eta_plus1']
  row['Delta_candidate_RCWA_T']=row['ALT1_RCWA_T']-row['CONTROL0_RCWA_T']; row['Delta_candidate_HF_T']=row['ALT1_FDTD_T']-row['CONTROL0_FDTD_T']; row['Delta_candidate_RCWA_R']=row['ALT1_RCWA_R']-row['CONTROL0_RCWA_R']; row['Delta_candidate_HF_R']=row['ALT1_FDTD_R']-row['CONTROL0_FDTD_R']
  row['Delta_candidate_RCWA_directionality']=f(ar['directionality_plus1_vs_minus1'])-f(cr['directionality_plus1_vs_minus1']); row['Delta_candidate_HF_directionality']=f(a['directionality_plus1_over_pm1'])-f(c['directionality_plus1_over_pm1'])
  matched.append(row)
  for m in metrics:
   cv={'eta_plus1':f(cr['eta_mplus1']),'eta_0':f(cr['eta_m0']),'eta_minus1':f(cr['eta_mminus1']),'T_total':f(cr['T_total']),'R_total':f(cr['R_total'])}[m]
   hv=f(c[m]); residual.append({'geometry':'CONTROL0','polarization':'P_XLIKE','wavelength_nm':wl,'metric':m,'FDTD':hv,'RCWA':cv,'signed_error':hv-cv,'abs_error':abs(hv-cv)})
   av={'eta_plus1':f(ar['eta_mplus1']),'eta_0':f(ar['eta_m0']),'eta_minus1':f(ar['eta_mminus1']),'T_total':f(ar['T_total']),'R_total':f(ar['R_total'])}[m]; ah=f(a[m]); residual.append({'geometry':'ALT1','polarization':'P_XLIKE','wavelength_nm':wl,'metric':m,'FDTD':ah,'RCWA':av,'signed_error':ah-av,'abs_error':abs(ah-av)})
 atomic(EVID/'CONTROL0_NEG0378_P_RCWA_VS_FDTD_AUDIT_V1.json',{'case_id':'CONTROL0_NEG0378_P','post_fsp_sha256':sha(RUN/'CONTROL0_NEG0378_P_attempt_001_post.fsp'),'metrics':{m:stats([r['abs_error'] for r in residual if r['geometry']=='CONTROL0' and r['metric']==m]) for m in metrics},'signed_bias':{m:sum(r['signed_error'] for r in residual if r['geometry']=='CONTROL0' and r['metric']==m)/11 for m in metrics},'exact_wavelengths':W,'source_rcwa_sha256':sha(RCWA),'source_alt1_fdtd_sha256':sha(ALT1_FDTD)})
 csvwrite(EVID/'control0_rcwa_vs_fdtd_residual_long.csv',residual); csvwrite(EVID/'matched_control0_alt1_22row_table.csv',matched)
 # direction/order comparison
 signs=[(r['Delta_candidate_RCWA_eta_plus1'],r['Delta_candidate_HF_eta_plus1']) for r in matched]
 rc_sign=[x>0 for x,y in signs]; hf_sign=[y>0 for x,y in signs]
 if all(x==y for x,y in zip(rc_sign,hf_sign)): order_cls='PRESERVED'
 elif all(not y for y in hf_sign) and all(x for x in rc_sign): order_cls='REVERSED'
 elif any(x!=y for x,y in zip(rc_sign,hf_sign)): order_cls='MIXED_BY_WAVELENGTH'
 else: order_cls='WEAKENED'
 errsum=[abs(f(altfd[wl]['eta_plus1'])-f(rc[('ALT1',wl)]['eta_mplus1']))+abs(f(cfd[wl]['eta_plus1'])-f(rc[('CONTROL0',wl)]['eta_mplus1'])) for wl in W]
 sep=[abs(x) for x,y in signs]; ratio=[e/s if s>0 else float('inf') for e,s in zip(errsum,sep)]
 if order_cls=='REVERSED' or any(e>=s for e,s in zip(errsum,sep)): stability='DECISION_CHANGING' if order_cls=='REVERSED' else 'AT_RISK'
 elif order_cls=='PRESERVED': stability='STABLE'
 else: stability='MIXED'
 dep='MIXED_WAVELENGTH_DEPENDENCE'
 cvals=[r['abs_error'] for r in residual if r['geometry']=='CONTROL0']; avals=[r['abs_error'] for r in residual if r['geometry']=='ALT1']
 if statistics.mean(cvals)<0.5*statistics.mean(avals): dep='CONTROL0_ERROR_MUCH_SMALLER'
 elif statistics.mean(cvals)>2*statistics.mean(avals): dep='CONTROL0_ERROR_MUCH_LARGER'
 elif abs(statistics.mean(cvals)-statistics.mean(avals))/max(statistics.mean(avals),1e-12)<0.25: dep='SIMILAR_SYSTEMATIC_ERROR'
 atomic(EVID/'matched_candidate_separation_audit.json',{'rows':matched,'classification_by_primary_eta_plus1':order_cls,'rcwa_separation_summary':stats([r['Delta_candidate_RCWA_eta_plus1'] for r in matched]),'hf_separation_summary':stats([r['Delta_candidate_HF_eta_plus1'] for r in matched]),'geometry_dependent_provider_error':dep})
 atomic(EVID/'geometry_dependent_provider_error_audit.json',{'classification':dep,'CONTROL0_abs_error_mean':statistics.mean(cvals),'ALT1_abs_error_mean':statistics.mean(avals),'CONTROL0_abs_error_stats':stats(cvals),'ALT1_abs_error_stats':stats(avals),'metricwise':{m:{'CONTROL0':stats([r['abs_error'] for r in residual if r['geometry']=='CONTROL0' and r['metric']==m]),'ALT1':stats([r['abs_error'] for r in residual if r['geometry']=='ALT1' and r['metric']==m])} for m in metrics}})
 atomic(EVID/'p_side_two_sided_decision_stability.json',{'classification':stability,'primary_metric':'eta_plus1','per_wavelength_error_sum':dict(zip(W,errsum)),'per_wavelength_rcwa_separation':dict(zip(W,sep)),'ratio_error_sum_over_separation':dict(zip(W,ratio)),'ordering_classification':order_cls,'full_ps_stability_proven':False,'S_side_two_sided':'NOT_DIRECTLY_CALIBRATED'})
 rec='CONTROL0_S_MATCHED_HF_RECOMMENDED_FOR_FULL_DECISION_AUDIT' if dep not in ('CONTROL0_ERROR_MUCH_SMALLER','SIMILAR_SYSTEMATIC_ERROR') or stability!='STABLE' else 'CONTROL0_S_MATCHED_HF_NOT_NEEDED_YET'
 atomic(EVID/'control0_s_recommendation.json',{'recommendation':rec,'basis':{'provider_error_classification':dep,'p_side_stability':stability},'auto_run':False})
 atomic(EVID/'solver_budget_audit.json',{'authorized_new_solver_invocations':1,'actual_run_invocation_count':1,'control0_entered':1,'control0_s_entered':0,'alt1_rerun':0,'new_rcwa_calls':0,'external_hf':0,'training':0,'inverse':0,'coupling_writes':0,'attempt_002':0})
 atomic(EVID/'provenance_audit.json',{'task_id':'NP_K6_M11B_CONTROL0_NEG0378_P_MATCHED_HF_DECISION_BOUND_V1','case_id':'CONTROL0_NEG0378_P','attempt_id':'attempt_001','canonical_geometry_hash':GEOM,'u_x_exact':float(UX),'polarization':'P_XLIKE','setup_sha256':sha(EVID/'runtime_prefsp'/'CONTROL0_NEG0378_P_RUN3A.fsp'),'post_fsp_sha256':sha(RUN/'CONTROL0_NEG0378_P_attempt_001_post.fsp'),'coupling_package_path':str(COUP),'coupling_write_count':0,'no_interpolation':True,'no_extrapolation':True})
 atomic(EVID/'decision_audit.json',{'status':'NP_K6_M11B_CONTROL0_NEG0378_P_MATCHED_HF_COMPLETE_DECISION_AUDIT_READY','quality_gate_pass':json.loads((RUN/'quality_gate.json').read_text(encoding='utf-8')).get('quality_gate_pass'),'p_side_two_sided_decision_stability':stability,'full_p_s_two_sided_decision_stability_proven':False,'control0_s_recommendation':rec,'alt1_h1_handoff_remains_ready':True,'classification':order_cls})
 print(json.dumps({'status':'NP_K6_M11B_CONTROL0_NEG0378_P_MATCHED_HF_COMPLETE_DECISION_AUDIT_READY','provider_error_classification':dep,'p_side_stability':stability,'ordering':order_cls,'control0_s_recommendation':rec},indent=2))
if __name__=='__main__': main()
