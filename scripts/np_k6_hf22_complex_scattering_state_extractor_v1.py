import sys, json, csv, math, cmath, hashlib, pathlib, time, traceback
import numpy as np
sys.path.insert(0, r"N:\\Program Files\\ANSYS Inc\\v251\\Lumerical\\api\\python")
import lumapi

ROOT = pathlib.Path(r"D:\\project\\worktrees\\blue_apcd_np_k6_mdc_v1")
OUT = ROOT / "outputs" / "np_k6_hf22_complex_scattering_state_extraction_v1"
OUT.mkdir(parents=True, exist_ok=True)
CSV = ROOT / "outputs" / "np_k6_m8a_primary2_closeout_v1" / "hf22_formal_development_484rows.csv"
SCOPED = [
 ROOT/"outputs/np_k6_m2_batch1_hf_acquisition_v1",
 ROOT/"outputs/np_k6_m4_batch2_primary4_hf_acquisition_v1",
 ROOT/"outputs/np_k6_m6_primary4_hf_acquisition_v1",
 ROOT/"outputs/np_k6_m7a_primary4_hf_acquisition_v1",
 ROOT/"outputs/np_k6_m8a_primary2_hf_acquisition_v1",
 ROOT/"outputs/np_k6_p0_remaining_five_anchors_execution_v1",
 ROOT/"outputs/np_k6_hf_p0_label_generator_recovery_v1",
 ROOT/"outputs/np_k6_m8a_attempt001_result_state_recovery_v1",
 ROOT/"outputs/np_k6_m2_g04p_controlled_recompute_v1",
]
C0 = 299792458.0
MU0 = 4e-7*np.pi
EPS0 = 1/(MU0*C0*C0)
PX = 1.740e-6
PY = 0.290e-6
ORDERS = list(range(-3,4))

def sha256_file(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(4*1024*1024),b''): h.update(b)
    return h.hexdigest()

def norm(s): return ''.join(ch for ch in str(s).upper() if ch.isalnum())

def json_safe(x):
    if isinstance(x, (np.integer,)): return int(x)
    if isinstance(x, (np.floating,)): return float(x)
    if isinstance(x, complex): return [float(x.real), float(x.imag)]
    if isinstance(x, np.ndarray): return x.tolist()
    raise TypeError(type(x).__name__)

def fnum(x):
    try: return float(x)
    except Exception: return float('nan')

def find_posts():
    out=[]
    for rr in SCOPED:
        if not rr.exists(): continue
        for p in rr.rglob('*.fsp'):
            low=p.name.lower()
            if 'post' in low or 'recovered' in low or 'recompute' in low:
                out.append(p)
    return out

def choose_post(case, posts):
    nc=norm(case)
    exact=[p for p in posts if nc in norm(str(p))]
    if exact:
        exact.sort(key=lambda p:(('recovered_post' not in p.name.lower()), ('post' not in p.name.lower()), len(str(p))))
        return exact[0], 'normalized_case_match'
    if case == 'NP_K6_M2_BATCH1_G04_P':
        q=[p for p in posts if 'G04_P_BATCH1_INFRA_RECOVERY_RECOMPUTE_V1_attempt_001_post' in p.name]
        if q: return q[0], 'controlled_recompute_case_bridge'
    return None, 'unresolved'

def interp_sio2_n(freq):
    p=ROOT/"outputs/material_reference/mdc_blue_oujizi_m/material_ref_native_sampled.csv"
    vals=[]
    if p.exists():
        with p.open(encoding='utf-8-sig', newline='') as f:
            for r in csv.DictReader(f):
                if r.get('material_name','').lower()!='sio222': continue
                try: vals.append((float(r['frequency_hz']), complex(float(r['epsilon_real']),float(r.get('epsilon_imag',0.0)))))
                except Exception: pass
    if not vals: return complex(1.4261792900678596,0.0)
    vals.sort()
    fs=np.array([v[0] for v in vals]); es=np.array([v[1] for v in vals])
    er=np.interp(freq,fs,es.real); ei=np.interp(freq,fs,es.imag)
    return cmath.sqrt(complex(er,ei))

with CSV.open(encoding='utf-8-sig', newline='') as f:
    truth_rows=list(csv.DictReader(f))
truth={(r['case_id'], round(float(r['wavelength_nm']),6)):r for r in truth_rows}
cases=sorted({r['case_id'] for r in truth_rows})
posts=find_posts()
post_map={}
for c in cases:
    p,how=choose_post(c,posts)
    post_map[c]=(p,how)

state=[]; monitor_rows=[]; closure=[]; availability=[]; errors=[]
solver_calls=0
for ci,case in enumerate(cases,1):
    row0=next(r for r in truth_rows if r['case_id']==case)
    fsp,resolve_how=post_map[case]
    av={'case_id':case,'geometry_id':row0.get('geometry_id'),'geometry_hash':row0.get('geometry_hash'),'polarization':row0.get('polarization'),'resolved_by':resolve_how,'post_fsp_path':str(fsp.relative_to(ROOT)) if fsp else None,'load_ok':False,'complex_eh_complete':False,'gratingvector_ok':False,'wavelength_count':0,'error':None}
    if fsp is None:
        av['error']='post_fsp_not_resolved'; availability.append(av); continue
    try:
        av['post_fsp_size_bytes']=fsp.stat().st_size
        av['post_fsp_sha256']=sha256_file(fsp)
        fd=lumapi.FDTD(hide=True)
        fd.load(str(fsp)); av['load_ok']=True
        for side,mon,total_key,medium_sign in [('transmission','transmission_monitor','T_total',1),('reflection','reflection_monitor','R_total',-1)]:
            rr=fd.getresult(mon)
            keys=str(rr).splitlines() if isinstance(rr,str) else list(rr.keys())
            fields={k:np.squeeze(np.asarray(fd.getdata(mon,k))) for k in ['x','y','f','Ex','Ey','Ez','Hx','Hy','Hz']}
            x=np.squeeze(fields['x']); y=np.squeeze(fields['y']); freq=np.squeeze(fields['f'])
            eh_ok=all(np.iscomplexobj(fields[k]) and np.all(np.isfinite(fields[k])) for k in ['Ex','Ey','Ez','Hx','Hy','Hz'])
            av['complex_eh_complete']=bool(av['complex_eh_complete'] or eh_ok)
            av['wavelength_count']=int(freq.size)
            fd.putv('f',freq.reshape((-1,1))); fd.eval('np_sourcepower=sourcepower(f);'); sp=np.squeeze(np.asarray(fd.getv('np_sourcepower'))).astype(float)
            wx=np.ones(x.size); wy=np.ones(y.size); wx[[0,-1]]=0.5; wy[[0,-1]]=0.5
            dx=float(np.mean(np.diff(x))) if x.size>1 else 0.; dy=float(np.mean(np.diff(y))) if y.size>1 else 0.; area=(x[-1]-x[0])*(y[-1]-y[0])
            pz=0.5*np.real(fields['Ex']*np.conj(fields['Hy'])-fields['Ey']*np.conj(fields['Hx']))
            raw_flux=np.sum(wx[:,None,None]*wy[None,:,None]*pz,axis=(0,1))*dx*dy/sp
            for fi,ff in enumerate(freq):
                wl=C0/ff*1e9; key=(case,round(float(wl),6)); tr=truth.get(key)
                if tr is None: tr=min((r for r in truth_rows if r['case_id']==case),key=lambda r:abs(float(r['wavelength_nm'])-wl))
                total=fnum(tr[total_key]); stored_T=fnum(tr['T_total']); stored_R=fnum(tr['R_total'])
                try:
                    gv=np.asarray(fd.gratingvector(mon,fi+1)).squeeze()
                    gn=np.rint(np.real(np.asarray(fd.gratingn(mon,fi+1)).squeeze())).astype(int)
                    gu=np.real(np.asarray(fd.gratingu1(mon,fi+1)).squeeze())
                    frac=np.real(np.asarray(fd.grating(mon,fi+1)).squeeze())
                    av['gratingvector_ok']=True
                except Exception as e:
                    gv=np.zeros((0,3),complex); gn=np.zeros(0,int); gu=np.zeros(0); frac=np.zeros(0); errors.append({'case_id':case,'side':side,'wavelength_nm':wl,'error':'gratingvector:'+repr(e)})
                modal_sum=0.; order_count=0
                allowed_orders=set(ORDERS) if side=='transmission' else set(range(-5,6))
                nmed=1.0 if side=='transmission' else abs(interp_sio2_n(float(ff)))
                for j,m in enumerate(gn.tolist() if gn.size else []):
                    if m not in allowed_orders: continue
                    k0=2*np.pi/(wl*1e-9); kx=2*np.pi*m/PX; kz0=cmath.sqrt((nmed*k0)**2-kx*kx)
                    if kz0.real<=0 or abs(kz0.imag)>1e-8*max(kz0.real,1.0): prop=False; kz0=complex(kz0)
                    else: prop=True
                    comp=complex(gv[j,1]) if gv.ndim==2 and gv.shape[1]>=2 and str(row0.get('polarization','')).lower().startswith('s') else complex(gv[j,0]) if gv.ndim==2 and gv.shape[1]>=1 else complex('nan')
                    if not str(row0.get('polarization','')).lower().startswith('s') and gv.ndim==2 and gv.shape[1]>=3 and prop:
                        kz_signed=kz0.real if side=='transmission' else -kz0.real
                        comp=complex(gv[j,0])*(kz_signed/(nmed*k0))+complex(gv[j,2])*(-kx/(nmed*k0))
                    amp=math.sqrt(abs(total))*comp if prop and np.isfinite(comp.real) and np.isfinite(comp.imag) else complex('nan')
                    eff=float(abs(amp)**2) if prop else float('nan')
                    if prop: modal_sum+=eff; order_count+=1
                    state.append({'case_id':case,'geometry_id':row0.get('geometry_id'),'geometry_hash':row0.get('geometry_hash'),'polarization':row0.get('polarization'),'wavelength_nm':wl,'frequency_hz':float(ff),'side':side,'order_m':m,'order_scope':'required_m-3_to_m+3' if m in ORDERS else 'extended_reflection_open_order','u_x':float(gu[j]) if j<len(gu) else float('nan'),'power_fraction':float(frac[j]) if j<len(frac) else float('nan'),'absolute_efficiency':eff,'amplitude_re':float(amp.real),'amplitude_im':float(amp.imag),'propagating':prop,'monitor':mon,'sourcepower_W':float(sp[fi]),'normalization':'sqrt(formal_total_power)*gratingvector_component','phase_gauge':'raw_monitor_plane_complex_phase'} )
                closure.append({'case_id':case,'geometry_id':row0.get('geometry_id'),'polarization':row0.get('polarization'),'wavelength_nm':wl,'side':side,'formal_total':total,'formal_T':stored_T,'formal_R':stored_R,'modal_sum_abs_efficiency':modal_sum,'modal_minus_formal':modal_sum-total,'raw_signed_flux_over_sourcepower':float(raw_flux[fi]),'raw_positive_flux_over_sourcepower':float(raw_flux[fi] if side=='transmission' else -raw_flux[fi]),'raw_flux_isolated':bool(side=='transmission'),'order_count':order_count,'sourcepower_W':float(sp[fi]),'monitor_keys':'|'.join(keys),'x_points':int(x.size),'y_points':int(y.size),'x_min_m':float(x[0]),'x_max_m':float(x[-1]),'y_min_m':float(y[0]),'y_max_m':float(y[-1]),'medium_index_used':float(nmed)})
            monitor_rows.append({'case_id':case,'geometry_id':row0.get('geometry_id'),'polarization':row0.get('polarization'),'side':side,'monitor':mon,'monitor_result_keys':'|'.join(keys),'frequency_points':int(freq.size),'wavelength_min_nm':float(C0/freq.max()*1e9),'wavelength_max_nm':float(C0/freq.min()*1e9),'complex_EH_dtype':str(fields['Ex'].dtype),'complex_EH_shape':'x=%s,y=%s,f=%s'%(x.size,y.size,freq.size),'all_finite':bool(eh_ok),'x_span_m':float(x[-1]-x[0]),'y_span_m':float(y[-1]-y[0]),'raw_power_integral_available':True,'sourcepower_api':'sourcepower(f)'})
        fd.close()
        av['error']=None
    except Exception as e:
        av['error']=repr(e); errors.append({'case_id':case,'error':repr(e),'traceback':traceback.format_exc()})
        try: fd.close()
        except Exception: pass
    availability.append(av)
    if ci%4==0: print('PROGRESS',ci,'/',len(cases),flush=True)

def write_csv(name, rows):
    p=OUT/name
    if not rows:
        p.write_text('',encoding='utf-8'); return
    keys=[]
    for r in rows:
        for k in r:
            if k not in keys: keys.append(k)
    with p.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=keys); w.writeheader(); w.writerows(rows)

write_csv('complex_scattering_state_long.csv',state)
write_csv('complex_monitor_contract_matrix.csv',monitor_rows)
write_csv('complex_power_closure_long.csv',closure)
(OUT/'complex_availability_matrix.json').write_text(json.dumps({'case_count':len(cases),'availability':availability,'cases_with_load':sum(bool(a['load_ok']) for a in availability),'cases_with_complex_EH':sum(bool(a['complex_eh_complete']) for a in availability),'cases_with_gratingvector':sum(bool(a['gratingvector_ok']) for a in availability),'errors':errors},ensure_ascii=False,indent=2,default=json_safe),encoding='utf-8')

def finite(vals): return [abs(float(x)) for x in vals if np.isfinite(float(x))]
modal_err=[abs(float(r['modal_minus_formal'])) for r in closure if np.isfinite(float(r['modal_minus_formal']))]
raw_err=[abs(float(r['raw_positive_flux_over_sourcepower'])-float(r['formal_total'])) for r in closure if r.get('raw_flux_isolated') and np.isfinite(float(r['raw_positive_flux_over_sourcepower']))]
raw_reflection=[abs(float(r['raw_positive_flux_over_sourcepower'])-float(r['formal_total'])) for r in closure if not r.get('raw_flux_isolated') and np.isfinite(float(r['raw_positive_flux_over_sourcepower']))]
summary={'closure_row_count':len(closure),'modal_abs_error_median':float(np.median(modal_err)) if modal_err else None,'modal_abs_error_q95':float(np.quantile(modal_err,.95)) if modal_err else None,'modal_abs_error_max':float(max(modal_err)) if modal_err else None,'raw_flux_transmission_abs_error_median':float(np.median(raw_err)) if raw_err else None,'raw_flux_transmission_abs_error_q95':float(np.quantile(raw_err,.95)) if raw_err else None,'raw_flux_transmission_abs_error_max':float(max(raw_err)) if raw_err else None,'raw_flux_reflection_nonisolated_abs_error_median':float(np.median(raw_reflection)) if raw_reflection else None,'raw_flux_reflection_nonisolated_abs_error_q95':float(np.quantile(raw_reflection,.95)) if raw_reflection else None,'modal_closure_pass':bool(modal_err and np.quantile(modal_err,.95)<=0.02 and max(modal_err)<=0.05),'raw_flux_transmission_closure_pass':bool(raw_err and np.quantile(raw_err,.95)<=0.02 and max(raw_err)<=0.05),'raw_reflection_flux_isolated':False,'formal_total_source':'hf22_formal_development_484rows.csv','note':'reflection raw E/H Poynting includes incident standing-field contribution at reflection plane; gratingvector order sum is the reflected-power closure chain; no per-case rescaling'}
(OUT/'complex_power_closure_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
norm_contract={'contract_id':'NP_K6_HF22_COMPLEX_SCATTERING_STATE_V1_NORMALIZATION','solver_calls':0,'transmission_amplitude':'sqrt(formal_T_total)*gratingvector component','reflection_amplitude':'sqrt(formal_R_total)*gratingvector component','order_set':ORDERS,'period_x_m':PX,'period_y_m':PY,'m_plus_1_physical_direction':'+x','input_basis':'P=TM, S=TE; P TM projection uses (kz/k0,0,-kx/k0), S uses y','incident_medium':'Native-M1 SiO2 (sio222) interpolated complex epsilon vs frequency','exit_medium':'air n=1.0','sourcepower':'sourcepower(f) read from loaded FSP; raw Poynting divided by sourcepower','absolute_efficiency':'|complex_amplitude|^2','historical_complex_convention_authority':False,'no_arbitrary_per_case_rescaling':True}
(OUT/'complex_normalization_contract.json').write_text(json.dumps(norm_contract,ensure_ascii=False,indent=2),encoding='utf-8')
phase={'phase_gauge_contract_id':'NP_K6_HF22_COMPLEX_PHASE_GAUGE_V1','phase_reference':'raw complex gratingvector at physical monitor plane','deembedding':False,'arbitrary_global_phase_alignment':False,'inter_case_absolute_phase':False,'reference_plane_identity':'transmission z=900 nm nominal; reflection z=-300 nm nominal','common_time_convention':'Lumerical complex frequency-domain field convention','warning':'No source/reference-field de-embedding was applied; phases are monitor-plane quantities.'}
(OUT/'complex_phase_gauge_contract.json').write_text(json.dumps(phase,ensure_ascii=False,indent=2),encoding='utf-8')
all_avail=len(availability)==len(cases) and all(a['load_ok'] and a['complex_eh_complete'] and a['gratingvector_ok'] for a in availability)
manifest={'dataset_id':'NP_K6_HF22_COMPLEX_SCATTERING_STATE_V1','status':'PASS' if summary['modal_closure_pass'] and summary['raw_flux_transmission_closure_pass'] and all_avail else 'PARTIAL_CLOSURE_OR_AVAILABILITY_FAILURE','scope':'22 geometries x P/S x 11 exact wavelengths','case_count':len(cases),'spectral_rows':len(truth_rows),'solver_run_calls':0,'save_calls':0,'load_only':True,'raw_EH_source':'post-FSP monitor datasets','monitor_names':['transmission_monitor','reflection_monitor'],'order_set':ORDERS,'reflection_extended_open_orders':'m=-5...+5 when open in Native-M1 SiO2; required vector remains -3...+3','m_plus_1_physical_plus_x':True,'complex_modal_dataset_claim':'Valid normalized gratingvector monitor-plane states only when closure summary passes; otherwise diagnostic/proxy only.','full_Jones_matrix_available':False,'reason_full_Jones_unavailable':'Each geometry/polarization is a single input state; no 2x2 input-column reconstruction.','external_MDC_accessed':False,'sealed_target_accessed':False,'errors':errors}
(OUT/'complex_extraction_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2,default=json_safe),encoding='utf-8')
checks={}
for p in OUT.iterdir():
 if p.is_file() and p.name!='complex_artifact_checksums.json': checks[p.name]={'sha256':sha256_file(p),'size_bytes':p.stat().st_size}
(OUT/'complex_artifact_checksums.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding='utf-8')
report=OUT.parent.parent/'reports'/'NP_K6_HF22_COMPLEX_SCATTERING_STATE_EXTRACTION_V1.md'
report.parent.mkdir(parents=True,exist_ok=True)
report.write_text(f'''# NP_K6_HF22_COMPLEX_SCATTERING_STATE_EXTRACTION_V1

Status: **{manifest['status']}**
Load-only solver calls: **0**; save calls: **0**; cases: **{len(cases)}/44**; spectral rows: **{len(truth_rows)}/484**.

## Availability

All scoped raw fields were requested from `transmission_monitor` and `reflection_monitor`. The archive exposes complex `Ex,Ey,Ez,Hx,Hy,Hz` and 11 frequencies per monitor when the corresponding case loads. Availability is in `complex_availability_matrix.json`.

## Modal and normalization contract

Lumerical `gratingvector()` is used as the complex order-state API. `m=-3...+3` is retained and `m=+1` means physical +x. P is explicitly TM-projected; S is TE (`y`) and no P/S averaging is performed. Absolute coefficient is `sqrt(formal total power) * gratingvector component`; no per-case rescaling is applied. Raw E/H is independently integrated through Poynting flux and `sourcepower(f)`.

## Closure

Median/q95/max modal absolute error: `{summary['modal_abs_error_median']}`, `{summary['modal_abs_error_q95']}`, `{summary['modal_abs_error_max']}`. Transmission raw E/H Poynting absolute error: `{summary['raw_flux_transmission_abs_error_median']}`, `{summary['raw_flux_transmission_abs_error_q95']}`, `{summary['raw_flux_transmission_abs_error_max']}`. Reflection raw E/H Poynting is intentionally marked non-isolated because the reflection plane contains the incident field; reflected-order closure uses `gratingvector` including open m=±4,±5 in SiO₂. Detailed rows are in `complex_power_closure_long.csv` and summary JSON. No closure failure is hidden by renormalization.

## Phase and Jones limitations

Phase is preserved at the physical monitor plane; no arbitrary global phase alignment or source-plane de-embedding was applied. A full 2x2 Jones matrix is unavailable because each geometry has one P and one S input column only; this dataset must not be used to claim polarization selectivity without the missing cross-input columns.

## Artifacts

The machine-readable extraction directory is `outputs/np_k6_hf22_complex_scattering_state_extraction_v1/`. The report and all artifact checksums are generated from LOAD-only reads. No solver result was created or modified.
''',encoding='utf-8')
print(json.dumps({'manifest':manifest,'summary':summary,'report':str(report.relative_to(ROOT))},ensure_ascii=False,indent=2,default=json_safe))
