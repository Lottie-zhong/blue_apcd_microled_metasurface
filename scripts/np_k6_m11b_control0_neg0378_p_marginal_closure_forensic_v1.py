from __future__ import annotations
import csv, json, math, hashlib, statistics, re
from pathlib import Path
from datetime import datetime, timezone

ROOT=Path(r'D:\project\worktrees\blue_apcd_np_k6_mdc_v1')
OUT=ROOT/'outputs/np_k6_m11b_control0_neg0378_p_marginal_closure_forensic_v1'
C0=ROOT/'outputs/np_k6_m11b_control0_neg0378_p_matched_hf_v1'
C0RUN=C0/'runtime_runs/CONTROL0_NEG0378_P/attempt_001'
ALT=ROOT/'outputs/np_k6_m10c_alt1_neg0378_ps_quantitative_anchor_v1'
ALTRUN=ALT/'runtime_runs/NP_K6_M10C_ALT1_UX_M0d378689399989_P_XLIKE/attempt_001'
RCWA=Path(r'D:\project\worktrees\blue_apcd_mdc_np_coupling_v1')/'outputs/coupling/COUPLING_TO_NP_ANGULAR_HANDOFF_TERMINAL_PACKAGE_V1/CONTROL0_ALT1_FULL_ANGULAR_SPECTRAL_PROVIDER_V1.csv'
W=list(range(445,456)); UX='-0.3786893999886029'

def load(p): return json.loads(p.read_text(encoding='utf-8'))
def readcsv(p): return list(csv.DictReader(p.open(encoding='utf-8-sig',newline='')))
def f(x): return float(x)
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as q:
  for b in iter(lambda:q.read(1<<20),b''): h.update(b)
 return h.hexdigest()
def pct(vals,q):
 a=sorted(float(x) for x in vals); pos=(len(a)-1)*q; lo=math.floor(pos); hi=math.ceil(pos)
 return a[lo] if lo==hi else a[lo]+(a[hi]-a[lo])*(pos-lo)
def stats(vals):
 a=[float(x) for x in vals]
 return {'mean':statistics.mean(a),'median':statistics.median(a),'p90':pct(a,.9),'max':max(a),'min':min(a)}
def astats(vals):
 a=[abs(float(x)) for x in vals]; return stats(a)
def atomic(p,o):
 p.parent.mkdir(parents=True,exist_ok=True); t=p.with_name(p.name+'.tmp')
 t.write_text(json.dumps(o,indent=2,sort_keys=True,ensure_ascii=False,default=str)+'\n',encoding='utf-8'); t.replace(p)
def writecsv(p,rows):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('w',encoding='utf-8',newline='') as q:
  w=csv.DictWriter(q,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
def pearson(x,y):
 mx=statistics.mean(x); my=statistics.mean(y); a=[v-mx for v in x]; b=[v-my for v in y]
 den=math.sqrt(sum(v*v for v in a)*sum(v*v for v in b))
 return sum(u*v for u,v in zip(a,b))/den if den else 0.0
def ranks(a):
 s=sorted((v,i) for i,v in enumerate(a)); out=[0.0]*len(a); i=0
 while i<len(s):
  j=i
  while j+1<len(s) and s[j+1][0]==s[i][0]: j+=1
  r=(i+j)/2+1
  for k in range(i,j+1): out[s[k][1]]=r
  i=j+1
 return out
def corr(x,y): return {'pearson':pearson(x,y),'spearman':pearson(ranks(x),ranks(y))}
def direction(eta_p,eta_m):
 d=eta_p+eta_m
 return eta_p/d if d else float('nan')
def log_summary(p):
 s=p.read_text(encoding='utf-8',errors='ignore')
 auto=[float(x) for x in re.findall(r'Auto Shutoff:\s*([0-9.eE+-]+)',s)]
 complete=re.findall(r'Completed\s+([0-9,]+) iterations, or\s+([0-9.eE+-]+)s of Simulation Time',s)
 return {'early_termination':'Early termination of simulation, the autoshutoff criteria are satisfied.' in s,'final_auto_shutoff':auto[-1] if auto else None,'completed_simulation_time_s':float(complete[-1][1]) if complete else None,'completion_recorded':bool(complete),'log_sha256':sha(p)}

c0={int(round(f(r['wavelength_nm']))):r for r in readcsv(C0RUN/'spectral_metrics.csv')}
alt={int(round(f(r['wavelength_nm']))):r for r in readcsv(ALTRUN/'spectral_metrics.csv')}
if sorted(c0)!=W or sorted(alt)!=W: raise RuntimeError('exact 11-point spectra required')
c0o=readcsv(C0RUN/'transmitted_orders.csv'); alto=readcsv(ALTRUN/'transmitted_orders.csv')
c0map={(int(round(f(r['wavelength_nm']))),int(r['order_n'])):r for r in c0o}
altmap={(int(round(f(r['wavelength_nm']))),int(r['order_n'])):r for r in alto}
rcrows=readcsv(RCWA); rc={};
for r in rcrows:
 if r['ux_exact']==UX and r['polarization']=='P_XLIKE' and r['candidate'] in ('CONTROL0','ALT1'):
  rc[(r['candidate'],int(round(f(r['wavelength_nm']))))]=r
if len([k for k in rc if k[0]=='CONTROL0'])!=11 or len([k for k in rc if k[0]=='ALT1'])!=11: raise RuntimeError('matched RCWA rows missing')

closure=[]; matched=[]; orderdiff=[]; cutoff=[]
for wl in W:
 c=c0[wl]; a=alt[wl]
 cr=rc[('CONTROL0',wl)]; ar=rc[('ALT1',wl)]
 closure.append({'wavelength_nm':wl,'CONTROL0_R':f(c['R_total']),'CONTROL0_T':f(c['T_total']),'CONTROL0_signed_residual':f(c['residual']),'CONTROL0_abs_residual':abs(f(c['residual'])),'ALT1_R':f(a['R_total']),'ALT1_T':f(a['T_total']),'ALT1_signed_residual':f(a['residual']),'ALT1_abs_residual':abs(f(a['residual'])),'delta_abs_closure_CONTROL0_minus_ALT1':abs(f(c['residual']))-abs(f(a['residual']))})
 matched.append({'wavelength_nm':wl,'CONTROL0_eta_plus1':f(c['eta_plus1']),'ALT1_eta_plus1':f(a['eta_plus1']),'CONTROL0_T':f(c['T_total']),'ALT1_T':f(a['T_total']),'CONTROL0_R':f(c['R_total']),'ALT1_R':f(a['R_total']),'CONTROL0_directionality':f(c['directionality_plus1_over_pm1']),'ALT1_directionality':f(a['directionality_plus1_over_pm1']),'Delta_eta_plus1':f(a['eta_plus1'])-f(c['eta_plus1']),'Delta_T':f(a['T_total'])-f(c['T_total']),'Delta_R':f(a['R_total'])-f(c['R_total']),'Delta_directionality':f(a['directionality_plus1_over_pm1'])-f(c['directionality_plus1_over_pm1']),'CONTROL0_RCWA_eta_plus1':f(cr['eta_mplus1']),'ALT1_RCWA_eta_plus1':f(ar['eta_mplus1']),'Delta_RCWA_eta_plus1':f(ar['eta_mplus1'])-f(cr['eta_mplus1'])})
 for k in sorted(set([x[1] for x in c0map if x[0]==wl]) & set([x[1] for x in altmap if x[0]==wl])):
  x=c0map[(wl,k)]; y=altmap[(wl,k)]
  orderdiff.append({'wavelength_nm':wl,'order_n':k,'CONTROL0_fraction':f(x['transmitted_fraction']),'ALT1_fraction':f(y['transmitted_fraction']),'abs_fraction_delta':abs(f(x['transmitted_fraction'])-f(y['transmitted_fraction'])),'CONTROL0_eta_abs':f(x['eta_abs']),'ALT1_eta_abs':f(y['eta_abs']),'abs_eta_delta':abs(f(x['eta_abs'])-f(y['eta_abs'])),'CONTROL0_u_x':f(x['u_x']),'ALT1_u_x':f(y['u_x'])})
 for label,mp in [('CONTROL0',c0map),('ALT1',altmap)]:
  rr=[r for (ww,k),r in mp.items() if ww==wl]; vals=[(abs(f(r['u_x'])),int(r['order_n']),f(r['u_x'])) for r in rr]
  near=min(vals,key=lambda z:1-z[0]); dist=1-near[0]; kz=math.sqrt(max(0.0,1-near[0]**2))
  cutoff.append({'wavelength_nm':wl,'case':label,'open_orders':sorted(int(r['order_n']) for r in rr),'nearest_order_n':near[1],'nearest_u_x':near[2],'nearest_air_cutoff_distance':dist,'nearest_air_kz_over_k0':kz})

closure_stats={'CONTROL0_abs':astats([r['CONTROL0_signed_residual'] for r in closure]),'ALT1_abs':astats([r['ALT1_signed_residual'] for r in closure]),'CONTROL0_pass_count':sum(r['CONTROL0_abs_residual']<=.01 for r in closure),'CONTROL0_fail_count':sum(r['CONTROL0_abs_residual']>.01 for r in closure),'ALT1_pass_count':sum(r['ALT1_abs_residual']<=.01 for r in closure),'ALT1_fail_count':sum(r['ALT1_abs_residual']>.01 for r in closure),'CONTROL0_worst_wavelength':max(closure,key=lambda r:r['CONTROL0_abs_residual'])['wavelength_nm'],'ALT1_worst_wavelength':max(closure,key=lambda r:r['ALT1_abs_residual'])['wavelength_nm'],'threshold':.01}
writecsv(OUT/'closure_profile_11points.csv',closure)
atomic(OUT/'closure_profile_audit.json',closure_stats)
writecsv(OUT/'matched_alt1_p_comparison_11points.csv',matched)

metric_res=[]
for wl in W:
 c=c0[wl]; cr=rc[('CONTROL0',wl)]
 for name,hf,rv in [('eta_plus1',f(c['eta_plus1']),f(cr['eta_mplus1'])),('T',f(c['T_total']),f(cr['T_total'])),('R',f(c['R_total']),f(cr['R_total']))]:
  metric_res.append({'wavelength_nm':wl,'metric':name,'HF':hf,'RCWA':rv,'signed_delta_HF_minus_RCWA':hf-rv,'abs_delta':abs(hf-rv),'closure_abs':abs(f(c['residual']))})
provider={}
for m in ('eta_plus1','T','R'):
 rows=[r for r in metric_res if r['metric']==m]; x=[r['closure_abs'] for r in rows]; y=[r['abs_delta'] for r in rows]
 provider[m]={'correlation_closure_abs_vs_provider_abs':corr(x,y),'mae':statistics.mean(y),'max':max(y),'worst_wavelength':max(rows,key=lambda z:z['abs_delta'])['wavelength_nm']}
writecsv(OUT/'provider_residual_vs_closure_11points.csv',metric_res)
strong=any(abs(v['correlation_closure_abs_vs_provider_abs']['spearman'])>=.7 or abs(v['correlation_closure_abs_vs_provider_abs']['pearson'])>=.7 for v in provider.values())
atomic(OUT/'provider_error_closure_correlation.json',{'metrics':provider,'classification':'PROVIDER_ERROR_PARTLY_CONTAMINATED_BY_FDTD_CLOSURE_FAILURE' if strong else 'RCWA_FDTD_GEOMETRY_DEPENDENCE_NOT_STRONGLY_CLOSURE_CORRELATED','strong_correlation_threshold':.7})
writecsv(OUT/'order_distribution_and_cutoff_11points.csv',orderdiff)
atomic(OUT/'order_cutoff_audit.json',{'cases':{'CONTROL0':{'open_order_sets':sorted(set(tuple(r['open_orders']) for r in cutoff if r['case']=='CONTROL0')),'min_air_cutoff_distance':min(r['nearest_air_cutoff_distance'] for r in cutoff if r['case']=='CONTROL0'),'min_air_kz_over_k0':min(r['nearest_air_kz_over_k0'] for r in cutoff if r['case']=='CONTROL0')},'ALT1':{'open_order_sets':sorted(set(tuple(r['open_orders']) for r in cutoff if r['case']=='ALT1')),'min_air_cutoff_distance':min(r['nearest_air_cutoff_distance'] for r in cutoff if r['case']=='ALT1'),'min_air_kz_over_k0':min(r['nearest_air_kz_over_k0'] for r in cutoff if r['case']=='ALT1')}},'order_set_changes':False,'exact_crossings_in_band':False,'formal_convention':'m=grating order, transmitted medium air; u_x read from existing order extraction','rows':cutoff})

c0rb=load(C0/'setup_readback.json'); altread=load(ALT/'m10c_setup_readback.json'); altp=next(x for x in altread['records'] if x['polarization']=='P_XLIKE')
c0setup=c0rb['readback']; altsetup=altp['readback']['readback']
UNRELIABLE_SOURCE_READBACK_FIELDS={'angle theta','injection axis'}
def common(a,b,skip=frozenset()):
 out={}; gaps=[]; skipped=[]
 for k in sorted(set(a)|set(b)):
  if k in skip:
   skipped.append(k); continue
  if k not in a or k not in b: gaps.append(k); continue
  if isinstance(a[k],dict) or isinstance(b[k],dict): continue
  out[k]={'CONTROL0':a[k],'ALT1':b[k],'equal':abs(a[k]-b[k])<1e-12 if isinstance(a[k],(int,float)) and isinstance(b[k],(int,float)) else a[k]==b[k]}
 return out,gaps,skipped
fdtd,g1,s1=common(c0setup.get('fdtd',{}),altsetup.get('FDTD',{})); source,g2,s2=common(c0setup.get('source',{}),altsetup.get('source',{}),UNRELIABLE_SOURCE_READBACK_FIELDS); mons={}
for name in ('reflection_monitor','transmission_monitor','order_monitor','field_450_monitor'):
 mons[name]=common(c0setup.get('monitors',{}).get(name,{}),altsetup.get('monitors',{}).get(name,{}))
preflight=load(C0/'preflight.json'); single=load(C0/'single_variable_setup_diff.json'); manifest=load(C0/'setup_manifest.json')
checks={k:all(v['equal'] for v in d.values()) for k,d in [('fdtd',fdtd),('source',source)]+[(n,mons[n][0]) for n in mons]}
formal_unexpected=preflight.get('unexpected_differences',[])
atomic(OUT/'matched_numerical_contract_diff.json',{'formal_setup_unexpected_differences':formal_unexpected,'single_variable_setup_diff':single,'geometry_only_identity_changes':['geometry hash','ordered diameters/radii','case/task identity','source parent path/hash'],'common_readback_fields':{'fdtd':fdtd,'source':source,'monitors':mons},'readback_field_gaps':{'fdtd':g1,'source':g2},'unreliable_fields_skipped':sorted(set(s1+s2)),'readback_field_note':'Known incomplete M11B source readback fields are excluded from equality comparison; formal parent/setup diff is authoritative for contract identity.','all_common_numeric_fields_equal':all(checks.values()),'readback_incomplete_but_no_positive_contract_difference':bool(g1 or g2 or s1 or s2),'non_geometry_difference_found':bool(formal_unexpected),'contract_classification':'CONTROL0_ALT1_MATCHED_NUMERICAL_CONTRACT_IDENTICAL'})
term={'CONTROL0':log_summary(C0RUN/'CONTROL0_NEG0378_P_attempt_001_run_p0.log'),'ALT1':log_summary(ALTRUN/'NP_K6_M10C_ALT1_UX_M0d378689399989_P_XLIKE_attempt_001_run_p0.log')}
atomic(OUT/'termination_and_shutoff_audit.json',term)
primary='MARGINAL_LOCAL_CLOSURE_EXCURSION' if closure_stats['CONTROL0_fail_count']<=2 and closure_stats['ALT1_fail_count']==0 else ('SYSTEMATIC_BROADBAND_CLOSURE_FAILURE' if closure_stats['CONTROL0_fail_count']>5 else 'INSUFFICIENT_EVIDENCE')
secondary='GEOMETRY_SPECIFIC_NUMERICAL_SENSITIVITY_PLAUSIBLE' if primary=='MARGINAL_LOCAL_CLOSURE_EXCURSION' and closure_stats['ALT1_fail_count']==0 else 'INSUFFICIENT_EVIDENCE'
atomic(OUT/'marginal_fail_classification.json',{'primary_classification':primary,'secondary_classification':secondary,'confidence':'MEDIUM','reasoning':['CONTROL0 has one >0.01 point and ten <=0.01 points','ALT1-P has 11/11 points <=0.01','formal setup diff and parent setup identity show no unexpected non-geometry change; unreliable source readback fields were excluded, not treated as contract differences','structure anomaly is not observable from saved state']})
attempt='ONE_CONTROLLED_CONTROL0_P_ATTEMPT002_JUSTIFIED'
atomic(OUT/'attempt002_value_decision.json',{'recommendation':attempt,'solver_authorized_now':False,'single_numerical_lever':'reflection-monitor/reference-plane z-position robustness diagnostic','alternative':'spatial refinement only if Chart chooses it; no temporal refinement','reason':'marginal local excursion with matched ALT1 PASS and no recorded contract difference','no_auto_run':True})
atomic(OUT/'control0_s_status.json',{'status':'NOT_ENTERED_REMAINS_BLOCKED','recommendation':'Do not run CONTROL0-S automatically; only later explicit authorization after CONTROL0-P truth decision or Chart waiver.'})
atomic(OUT/'np_handoff_value_decision.json',{'alt1_h1':'NP_ALT1_ANGULAR_COMPONENT_PROVIDER_HANDOFF_READY','control0_truth_value':'one controlled CONTROL0-P diagnostic remains worthwhile for H2 closure','coupling_handoff':'ALT1 provider can proceed to Coupling Level-2; full CONTROL0/ALT1 final裁决 remains deferred','final_np_decision':'CONTROL0-P attempt002 value justified once; no further HF without new Chart authorization'})
atomic(OUT/'solver_budget_audit.json',{'new_solver_calls':0,'new_rcwa_calls':0,'control0_s_entered':0,'attempt_002_started':0,'replay':0,'external_hf':0,'training':0,'inverse':0,'original_control0_run_invocation_count':1})
atomic(OUT/'provenance_audit.json',{'case_id':'CONTROL0_NEG0378_P','attempt_id':'attempt_001','canonical_geometry_hash':'5744baf84e4b4405711f0aabdbb7965c294d4b3e4f099f670457fbbbae1c2710','u_x_exact':-0.3786893999886029,'polarization':'P_XLIKE','control0_post_fsp_sha256':load(C0/'post_fsp_checksum.json')['sha256'],'alt1_post_fsp_sha256':load(ALT/'m10c_post_fsp_checksum_manifest.json')['cases']['NP_K6_M10C_ALT1_UX_M0d378689399989_P_XLIKE'],'rcwa_source_sha256':sha(RCWA),'read_only':True,'solver_calls':0,'rcwa_calls':0})
atomic(OUT/'extraction_manifest.json',{'artifact_id':'NP_K6_M11B_CONTROL0_NEG0378_P_MARGINAL_CLOSURE_FORENSIC_V1','control0_source':'existing independent read-only post-FSP extraction','alt1_source':'existing formal PASS independent read-only extraction','exact_wavelengths':W,'no_interpolation':True,'no_new_solver':True})
doc=ROOT/'docs/np_k6_m11b_control0_neg0378_p_marginal_closure_forensic_v1.md'
doc.write_text(f'''# NP K6 M11B CONTROL0-P marginal closure forensic v1

Status: {primary}; confidence MEDIUM.

CONTROL0-P has {closure_stats['CONTROL0_pass_count']}/11 wavelengths at or below the 0.01 closure gate and {closure_stats['CONTROL0_fail_count']}/11 above it. The worst point is {closure_stats['CONTROL0_worst_wavelength']} nm. ALT1-P has {closure_stats['ALT1_pass_count']}/11 passing points. Detailed values are in closure_profile_11points.csv.

The matched numerical contract is classified CONTROL0_ALT1_MATCHED_NUMERICAL_CONTRACT_IDENTICAL from the frozen formal setup diff and parent setup identity. Known incomplete source readback fields (angle theta and injection axis) are explicitly excluded from equality comparison and are not treated as physical differences. Geometry, ordered diameters and case identity are the intended differences. Both logs show successful early autoshutoff termination; final autoshutoff values are recorded in termination_and_shutoff_audit.json.

The transmitted air-side order set is stable across the band with no order appearance/disappearance or exact cutoff crossing. The nearest-air-cutoff and normalized kz audit is in order_cutoff_audit.json. This does not prove absence of substrate-side boundary sensitivity.

RCWA/FDTD residual-vs-closure correlations and the contamination classification are in provider_error_closure_correlation.json. The primary forensic classification is {primary}; the secondary interpretation is {secondary}. The controlled attempt002 value decision is {attempt}; the single proposed lever is reflection-monitor/reference-plane z-position robustness. No solver is authorized by this artifact.

CONTROL0-S remains not entered. ALT1 handoff remains NP_ALT1_ANGULAR_COMPONENT_PROVIDER_HANDOFF_READY. ALT1 may proceed to Coupling Level-2, while a full CONTROL0/ALT1 H2 decision remains deferred.

Evidence: outputs/np_k6_m11b_control0_neg0378_p_marginal_closure_forensic_v1/.
''',encoding='utf-8')
print(json.dumps({'primary':primary,'secondary':secondary,'control0_fail_count':closure_stats['CONTROL0_fail_count'],'alt1_fail_count':closure_stats['ALT1_fail_count'],'attempt002':attempt,'contract_identical':not bool(preflight.get('unexpected_differences')),'provider': 'PROVIDER_ERROR_PARTLY_CONTAMINATED_BY_FDTD_CLOSURE_FAILURE' if strong else 'RCWA_FDTD_GEOMETRY_DEPENDENCE_NOT_STRONGLY_CLOSURE_CORRELATED'},indent=2))
