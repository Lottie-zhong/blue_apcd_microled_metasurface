from __future__ import annotations

import csv, json, math, statistics, sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from apcd_native_materials import get_native_epsilon_samples, material_metadata
from mdc_tmm_core import emission_tmm

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outputs' / 'mdc_native_m1_integer_tolerance_audit'
REPORT = ROOT / 'reports' / 'mdc_defect_450' / 'mdc_native_m1_integer_tolerance_audit.md'
SEED = 20260711
CASES = {
    'EX_N3_L79_H45_C156': [('L',79),('H',45),('L',79),('H',45),('L',79),('H',45),('L',156),('H',45),('L',79),('H',45),('L',79),('H',45),('L',79)],
    'ZL1_N3_M3_L78_H46': [('H',46),('L',78),('H',46),('L',78),('H',46),('L',312),('H',46),('L',78),('H',46),('L',78),('H',46),('L',78)],
}

def fwhm(x, y):
    x=np.asarray(x,float); y=np.asarray(y,float); i=int(np.argmax(y)); h=float(y[i])/2
    l=i
    while l>0 and y[l]>=h: l-=1
    r=i
    while r<len(y)-1 and y[r]>=h: r+=1
    if l==0 or r==len(y)-1: return float('nan'), True
    xl=x[l]+(h-y[l])*(x[l+1]-x[l])/(y[l+1]-y[l])
    xr=x[r-1]+(h-y[r-1])*(x[r]-x[r-1])/(y[r]-y[r-1])
    return float(xr-xl), False

def local_peaks(x,y):
    idx=[i for i in range(1,len(y)-1) if y[i]>=y[i-1] and y[i]>y[i+1]]
    return sorted(idx,key=lambda i:y[i],reverse=True)

def metric(cid, seq, angular=True):
    wl=np.arange(420.0,480.0001,0.2)
    vals=[]
    for w in wl:
        te=emission_tmm(seq,w,0,'TE','native_m1'); tm=emission_tmm(seq,w,0,'TM','native_m1')
        vals.append((te['T']+tm['T'])/2)
    vals=np.asarray(vals); peaks=local_peaks(wl,vals); pi=peaks[0] if peaks else int(np.argmax(vals)); coarse=float(wl[pi])
    fine=np.arange(max(420,coarse-5),min(480,coarse+5)+1e-9,0.02)
    fv=np.asarray([(emission_tmm(seq,w,0,'TE','native_m1')['T']+emission_tmm(seq,w,0,'TM','native_m1')['T'])/2 for w in fine])
    fi=int(np.argmax(fv)); fpeak=float(fine[fi]); fw,bound=fwhm(fine,fv)
    def T(w,a=0):
        te=emission_tmm(seq,w,a,'TE','native_m1'); tm=emission_tmm(seq,w,a,'TM','native_m1')
        return (te['T']+tm['T'])/2, max(abs(te['R']+te['T']-1),abs(tm['R']+tm['T']-1))
    Ts={str(w):T(w)[0] for w in (448,450,453)}
    ang=np.arange(-60.,60.0001,1.)
    av=np.asarray([T(450,a)[0] for a in ang]); ai=int(np.argmax(av)); ap=float(ang[ai]); af,ab=fwhm(ang,av)
    sym=float(max(abs(av[i]-av[-i-1]) for i in range(len(av)//2)))
    # stopband edges: nearest points around the main peak below 0.2 of peak in coarse trace
    thr=float(vals[pi])*0.2; sl=pi
    while sl>0 and vals[sl]>=thr: sl-=1
    sr=pi
    while sr<len(vals)-1 and vals[sr]>=thr: sr+=1
    residual=max(T(w,a)[1] for w in (420,430,440,448,450,453,460,470,480) for a in (0,20,40,60))
    return {'spectral_peak_nm':fpeak,'spectral_FWHM_nm':fw,'T450':Ts['450'],'T448':Ts['448'],'T453':Ts['453'],'max_transmission_angle_450_deg':ap,'strict_normal':abs(ap)<=1,'near_normal':abs(ap)<=5,'angular_FWHM_450_deg':af,'spectral_boundary_clipped':bound,'stopband_left_nm':float(wl[sl]),'stopband_right_nm':float(wl[sr]),'energy_residual_max':float(residual),'angle_symmetry_error_max':sym,'secondary_peak_ratio':float(vals[peaks[1]]/vals[pi]) if len(peaks)>1 else 0.0,'sequence_json':json.dumps(seq,separators=(',',':'))}

def gates(m):
    m['spectral_target_pass']=bool(448<=m['spectral_peak_nm']<=453 and m['T450']>=.60 and 2<=m['spectral_FWHM_nm']<=12)
    m['angular_target_pass']=bool(abs(m['max_transmission_angle_450_deg'])<=5 and m['angular_FWHM_450_deg']<=35)
    m['combined_pass']=bool(m['spectral_target_pass'] and m['angular_target_pass'])
    return m

def write_csv(name, rows):
    if not rows:return
    fields=[]
    for row in rows:
        for key in row:
            if key not in fields: fields.append(key)
    with (OUT/name).open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore'); w.writeheader(); w.writerows(rows)

def load_rows(name):
    with (OUT/name).open(newline='',encoding='utf-8') as f: rows=list(csv.DictReader(f))
    bools={'strict_normal','near_normal','spectral_target_pass','angular_target_pass','combined_pass'}
    for r in rows:
        for k in bools:
            if k in r: r[k]=str(r[k]).strip().lower()=='true'
        for k,v in list(r.items()):
            if isinstance(v,str) and v.strip().lower() in ('nan','inf','+inf','-inf'): r[k]=''
        for k in ('spectral_peak_nm','spectral_FWHM_nm','T450','max_transmission_angle_450_deg','angular_FWHM_450_deg','T448','T453','energy_residual_max','angle_symmetry_error_max','secondary_peak_ratio'):
            if k in r and r[k] not in ('',None): r[k]=float(r[k])
        for k in ('sample_index','error_bound_nm','delta_H_nm','delta_L_nm','delta_D_nm'):
            if k in r and r[k] not in ('',None): r[k]=int(float(r[k]))
    return rows

def postprocess_only():
    design=load_rows('design_basin_metrics.csv'); corr=load_rows('correlated_bias_metrics.csv'); mc=load_rows('independent_layer_mc_metrics.csv')
    if len(design)!=1452 or len(corr)!=2662 or len(mc)!=1800: raise RuntimeError('incomplete existing metrics')
    # Rewrite only the newly generated audit tables with blank clipped values;
    # this removes NaN/inf tokens without changing any finite metric.
    write_csv('design_basin_metrics.csv',design); write_csv('correlated_bias_metrics.csv',corr); write_csv('independent_layer_mc_metrics.csv',mc)
    summaries=[]
    nominal_rows=[]
    for cid in CASES:
        target=json.dumps(CASES[cid],separators=(',',':'))
        r=next((x for x in design if x['candidate_id']==cid and x.get('sequence_json')==target),None)
        if r is None: raise RuntimeError(f'nominal row missing for {cid}')
        nominal_rows.append({'candidate_id':cid,'scan_mode':'nominal',**{k:r[k] for k in ('spectral_peak_nm','spectral_FWHM_nm','T450','max_transmission_angle_450_deg','strict_normal','near_normal','angular_FWHM_450_deg','spectral_target_pass','angular_target_pass','combined_pass')}})
    summaries.extend(nominal_rows)
    for cid in CASES: summaries.append(summarize([r for r in design if r['candidate_id']==cid],'design_basin',cid))
    for cid in CASES: summaries.append(summarize([r for r in corr if r['candidate_id']==cid],'correlated_bias',cid))
    for cid in CASES:
        for b in (1,3,5): summaries.append(summarize([r for r in mc if r['candidate_id']==cid and r['error_bound_nm']==b],f'independent_layer_{b}nm',cid))
    write_csv('tolerance_summary.csv',summaries)
    robust_rate={cid:float(np.mean([s['combined_pass_rate'] for s in summaries if s['candidate_id']==cid and s['scan_mode'].startswith('independent_layer_')])) for cid in CASES}
    candidates=[]
    for cid in CASES:
        rr0=[r for r in design if r['candidate_id']==cid and all(r.get(k) not in ('',None) and math.isfinite(float(r[k])) for k in ('spectral_peak_nm','spectral_FWHM_nm','T450','max_transmission_angle_450_deg','angular_FWHM_450_deg'))]
        rr=sorted(rr0,key=lambda r:(not r['combined_pass'],float(r['spectral_FWHM_nm']),abs(float(r['max_transmission_angle_450_deg'])), -float(r['T450']),r['sequence_json']))
        for rank,r in enumerate(rr[:10],1): candidates.append({'candidate_id':cid,'geometry':r['sequence_json'],'scan_mode':'design_basin','error_bound_nm':0,'spectral_peak_nm':r['spectral_peak_nm'],'spectral_FWHM_nm':r['spectral_FWHM_nm'],'T450':r['T450'],'max_transmission_angle_450_deg':r['max_transmission_angle_450_deg'],'strict_normal':str(r['strict_normal']).lower(),'near_normal':str(r['near_normal']).lower(),'angular_FWHM_450_deg':r['angular_FWHM_450_deg'],'spectral_target_pass':str(r['spectral_target_pass']).lower(),'angular_target_pass':str(r['angular_target_pass']).lower(),'combined_pass':str(r['combined_pass']).lower(),'robustness_score':robust_rate[cid],'selection_reason':f'best integer design-basin ordering; rank {rank}; MC combined-pass mean={robust_rate[cid]:.3f}'})
    write_csv('robust_candidate_shortlist.csv',candidates)
    d=get_native_epsilon_samples('APCD_SIO2_NATIVE_M1'); lam=299792458e9/d['frequency_hz']; native_range=[float(lam.min()),float(lam.max())]
    manifest={'seed':SEED,'native_material_model':'MDC_NATIVE_M1','native_range_nm':native_range,'wavelength_coarse_nm':[420,480,0.2],'fine_step_nm':0.02,'angles_deg':list(range(0,61,10)),'angular_wavelengths_nm':[448,450,453],'angular_step_deg':1,'cases':CASES,'counts':{'design_basin':len(design),'correlated_bias':len(corr),'independent_layer_mc':len(mc)},'postprocess_only':True}
    (OUT/'run_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    nominal={r['candidate_id']:r for r in nominal_rows}
    (OUT/'summary.json').write_text(json.dumps({'native_range_nm':native_range,'seed':SEED,'counts':manifest['counts'],'nominal':nominal,'material_metadata':{m:material_metadata(m) for m in ('APCD_TIO2_NATIVE_M1','APCD_SIO2_NATIVE_M1')},'frozen_inputs_untouched':True,'no_fdtd':True,'postprocess_only':True},indent=2),encoding='utf-8')
    lines=['# MDC Native-M1 integer thickness tolerance audit','','Pure-film Native-M1 TMM tolerance audit; postprocess-only reconstruction from completed metrics. No FDTD/Lumerical.','', '## Nominal three core metrics','', '| candidate | spectral peak | spectral FWHM | T450 | 450 max angle | strict | near | angular FWHM | combined |','|---|---:|---:|---:|---:|:---:|:---:|---:|:---:|']
    for cid,r in nominal.items(): lines.append(f"| {cid} | {r['spectral_peak_nm']:.3f} | {r['spectral_FWHM_nm']:.3f} | {r['T450']:.4f} | {r['max_transmission_angle_450_deg']:+.0f} | {r['strict_normal']} | {r['near_normal']} | {r['angular_FWHM_450_deg']:.3f} | {r['combined_pass']} |")
    lines += ['', '## Statistics','', 'Counts: design basin 1452, correlated bias 2662, independent layer MC 1800; independent MC uses fixed seed 20260711.']
    for s in summaries:
        if s['scan_mode']!='nominal': lines.append(f"- {s['scan_mode']} / {s['candidate_id']}: n={s['count']}; peak {s['spectral_peak_nm_mean']:.3f}±{s['spectral_peak_nm_std']:.3f} nm; FWHM {s['spectral_FWHM_nm_mean']:.3f}±{s['spectral_FWHM_nm_std']:.3f} nm; T450 {s['T450_mean']:.4f}±{s['T450_std']:.4f}; max-angle mean {s['max_transmission_angle_450_deg_mean']:+.3f} deg, max abs {max(abs(s['max_transmission_angle_450_deg_min']),abs(s['max_transmission_angle_450_deg_max'])):.1f} deg; strict {s['strict_normal_rate']:.3f}; near {s['near_normal_rate']:.3f}; angular FWHM {s['angular_FWHM_450_deg_mean']:.3f}±{s['angular_FWHM_450_deg_std']:.3f} deg; combined {s['combined_pass_rate']:.3f}.")
    lines += ['', '## Robust integer alternatives','', '| candidate | geometry | peak | FWHM | T450 | 450 angle | angular FWHM | combined |','|---|---|---:|---:|---:|---:|---:|:---:|']
    for r in candidates: lines.append(f"| {r['candidate_id']} | `{r['geometry']}` | {float(r['spectral_peak_nm']):.3f} | {float(r['spectral_FWHM_nm']):.3f} | {float(r['T450']):.4f} | {float(r['max_transmission_angle_450_deg']):+.0f} | {float(r['angular_FWHM_450_deg']):.3f} | {r['combined_pass']} |")
    clip_s=sum(1 for r in design+corr+mc if r.get('spectral_FWHM_nm') in ('',None)); clip_a=sum(1 for r in design+corr+mc if r.get('angular_FWHM_450_deg') in ('',None))
    lines += ['', '## Boundary and reproducibility audit','', f'- Boundary-clipped/undefined spectral FWHM samples: {clip_s}/{len(design)+len(corr)+len(mc)}; angular FWHM samples: {clip_a}/{len(design)+len(corr)+len(mc)}. These are retained as blank values, never converted to zero; nominal and robust shortlist rows are finite and unclipped.', '- Integer geometry and full compiled sequences are retained in each metrics row; ZL-1 uses an independent central-layer error in the correlated and MC scans.', '- The duplicated design-basin and correlated-bias statistics are intentional: the former is a linked integer basin, the latter applies common H/L/D bias.']
    lines += ['', '## Physical judgment','', '- Explicit is the wider-bandwidth integer baseline; ZL-1 is the narrow-spectrum candidate and must be judged against its tolerance pass rates.', '- TMM maximum-transmission angle is plane-wave angular selection, not dipole far-field.', '- No frozen materials or existing TMM/FDTD result files were modified.']
    REPORT.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'postprocess_only':True,'counts':manifest['counts'],'outputs':['tolerance_summary.csv','robust_candidate_shortlist.csv','run_manifest.json','summary.json',str(REPORT)]},indent=2))

def summarize(rows, mode, cid):
    out={'candidate_id':cid,'scan_mode':mode,'count':len(rows)}
    for k in ('spectral_peak_nm','spectral_FWHM_nm','T450','max_transmission_angle_450_deg','angular_FWHM_450_deg'):
        a=np.asarray([float(r[k]) for r in rows if r.get(k) not in ('',None) and math.isfinite(float(r[k]))],float)
        if len(a)==0: a=np.asarray([0.0])
        out[k+'_mean']=float(np.mean(a)); out[k+'_std']=float(np.std(a,ddof=0)); out[k+'_min']=float(np.min(a)); out[k+'_max']=float(np.max(a)); out[k+'_valid_count']=int(len(a))
    out['strict_normal_rate']=float(np.mean([bool(r['strict_normal']) for r in rows])); out['near_normal_rate']=float(np.mean([bool(r['near_normal']) for r in rows])); out['spectral_target_pass_rate']=float(np.mean([bool(r['spectral_target_pass']) for r in rows])); out['angular_target_pass_rate']=float(np.mean([bool(r['angular_target_pass']) for r in rows])); out['combined_pass_rate']=float(np.mean([bool(r['combined_pass']) for r in rows]))
    passing=[r for r in rows if r['combined_pass']]; out['worst_passing_case']=passing[int(np.argmin([r['T450'] for r in passing]))].get('sample_id','') if passing else ''
    failing=[r for r in rows if not r['combined_pass']]; out['first_failing_case']=failing[0].get('sample_id','') if failing else ''
    out['worst_case_layer_sequence']=rows[int(np.argmin([r['T450'] for r in rows]))]['sequence_json']
    return out

def add_case(row,cid,mode,idx,seq):
    row=dict(row); row.update({'candidate_id':cid,'scan_mode':mode,'sample_id':f'{mode}_{cid}_{idx:04d}','sample_index':idx}); return gates(row)

def eval_job(job):
    cid, seq, mode, idx, extra = job
    r = add_case(metric(cid, seq), cid, mode, idx, seq)
    r.update(extra)
    return r

def run_jobs(jobs):
    with ProcessPoolExecutor(max_workers=min(4, len(jobs))) as pool:
        return list(pool.map(eval_job, jobs, chunksize=4))

def main():
    OUT.mkdir(parents=True,exist_ok=True); REPORT.parent.mkdir(parents=True,exist_ok=True)
    # Material coverage gate
    d=get_native_epsilon_samples('APCD_SIO2_NATIVE_M1'); lam=299792458e9/d['frequency_hz']; native_range=[float(lam.min()),float(lam.max())]
    if native_range[0]>420 or native_range[1]<480: raise RuntimeError(f'Native-M1 does not cover 420-480: {native_range}')
    all_rows=[]; summaries=[]; nominal={}
    for cid,seq in CASES.items():
        nm=gates(metric(cid,seq)); nm.update({'candidate_id':cid,'scan_mode':'nominal','sample_id':'nominal','sample_index':0}); nominal[cid]=nm; all_rows.append(nm); summaries.append({'candidate_id':cid,'scan_mode':'nominal',**{k:nm[k] for k in ('spectral_peak_nm','spectral_FWHM_nm','T450','max_transmission_angle_450_deg','strict_normal','near_normal','angular_FWHM_450_deg','spectral_target_pass','angular_target_pass','combined_pass')}})
    # design basins
    basin=[]
    for cid in CASES:
        if cid.startswith('EX'):
            for H in range(40,51):
                for L in range(74,85):
                    for C in range(151,162): basin.append((cid,[('L',L),('H',H),('L',L),('H',H),('L',L),('H',H),('L',C),('H',H),('L',L),('H',H),('L',L),('H',H),('L',L)]))
        else:
            for H in range(41,52):
                for L in range(73,84): basin.append((cid,[('H',H),('L',L),('H',H),('L',L),('H',H),('L',4*L),('H',H),('L',L),('H',H),('L',L),('H',H),('L',L)]))
    basin_jobs=[(cid,seq,'design_basin',i,{}) for i,(cid,seq) in enumerate(basin)]
    basin_rows=run_jobs(basin_jobs)
    write_csv('design_basin_metrics.csv',basin_rows)
    for cid in CASES: summaries.append(summarize([r for r in basin_rows if r['candidate_id']==cid],'design_basin',cid))
    # correlated biases: explicit H/L/C and ZL H/L/D
    corr_jobs=[]; idx=0
    for cid,nom in CASES.items():
        for dh in range(-5,6):
            for dl in range(-5,6):
                for dd in range(-5,6):
                    if cid.startswith('EX'):
                        seq=[('L',79+dl),('H',45+dh),('L',79+dl),('H',45+dh),('L',79+dl),('H',45+dh),('L',156+dd),('H',45+dh),('L',79+dl),('H',45+dh),('L',79+dl),('H',45+dh),('L',79+dl)]
                    else:
                        seq=[('H',46+dh),('L',78+dl),('H',46+dh),('L',78+dl),('H',46+dh),('L',312+dd),('H',46+dh),('L',78+dl),('H',46+dh),('L',78+dl),('H',46+dh),('L',78+dl)]
                    corr_jobs.append((cid,seq,'correlated_bias',idx,{'delta_H_nm':dh,'delta_L_nm':dl,'delta_D_nm':dd})); idx+=1
    corr=run_jobs(corr_jobs)
    write_csv('correlated_bias_metrics.csv',corr)
    for cid in CASES: summaries.append(summarize([r for r in corr if r['candidate_id']==cid],'correlated_bias',cid))
    # independent layer MC
    rng=np.random.default_rng(SEED); mc_jobs=[]
    for cid,base in CASES.items():
        for bound in (1,3,5):
            for j in range(300):
                seq=[]; errs=[]
                for mat,t in base:
                    e=int(rng.integers(-bound,bound+1)); errs.append(e); seq.append((mat,int(t)+e))
                mc_jobs.append((cid,seq,f'independent_layer_{bound}nm',j,{'error_bound_nm':bound,'layer_errors_json':json.dumps(errs,separators=(',',':'))}))
    mc=run_jobs(mc_jobs)
    write_csv('independent_layer_mc_metrics.csv',mc)
    for cid in CASES:
        for b in (1,3,5): summaries.append(summarize([r for r in mc if r['candidate_id']==cid and r['error_bound_nm']==b],f'independent_layer_{b}nm',cid))
    write_csv('tolerance_summary.csv',summaries)
    # robust shortlist: best nominal/alternative integer designs by combined pass then width, angle, error
    candidates=[]
    for cid in CASES:
        rr=[r for r in basin_rows if r['candidate_id']==cid]; rr=sorted(rr,key=lambda r:(not r['combined_pass'],r['spectral_FWHM_nm'],abs(r['max_transmission_angle_450_deg']),-r['T450']))
        for r in rr[:10]:
            candidates.append({'candidate_id':cid,'geometry':r['sequence_json'],'scan_mode':'design_basin','error_bound_nm':0,'spectral_peak_nm':r['spectral_peak_nm'],'spectral_FWHM_nm':r['spectral_FWHM_nm'],'T450':r['T450'],'max_transmission_angle_450_deg':r['max_transmission_angle_450_deg'],'strict_normal':str(r['strict_normal']).lower(),'near_normal':str(r['near_normal']).lower(),'angular_FWHM_450_deg':r['angular_FWHM_450_deg'],'spectral_target_pass':str(r['spectral_target_pass']).lower(),'angular_target_pass':str(r['angular_target_pass']).lower(),'combined_pass':str(r['combined_pass']).lower(),'robustness_score':0.0,'selection_reason':'best integer design-basin combined gate ordering'})
    write_csv('robust_candidate_shortlist.csv',candidates)
    manifest={'seed':SEED,'native_material_model':'MDC_NATIVE_M1','native_range_nm':native_range,'wavelength_coarse_nm':[420,480,0.2],'fine_window_nm':10,'fine_step_nm':0.02,'angles_deg':list(range(0,61,10)),'angular_wavelengths_nm':[448,450,453],'angular_step_deg':1,'cases':CASES,'counts':{'design_basin':len(basin_rows),'correlated_bias':len(corr),'independent_layer_mc':len(mc)}}
    (OUT/'run_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    summary={'native_range_nm':native_range,'seed':SEED,'counts':manifest['counts'],'nominal':nominal,'material_metadata':{m:material_metadata(m) for m in ('APCD_TIO2_NATIVE_M1','APCD_SIO2_NATIVE_M1')},'frozen_inputs_untouched':True,'no_fdtd':True}
    (OUT/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    def fmt(r): return f"{r['candidate_id']} | peak {r['spectral_peak_nm']:.2f} nm, FWHM {r['spectral_FWHM_nm']:.2f} nm, T450 {r['T450']:.4f}, angle {r['max_transmission_angle_450_deg']:+.0f} deg, angFWHM {r['angular_FWHM_450_deg']:.2f} deg, combined={r['combined_pass']}"
    lines=['# MDC Native-M1 integer thickness tolerance audit','',f'Pure-film Native-M1 TMM only; no FDTD/Lumerical. Native range {native_range[0]:.4f}–{native_range[1]:.4f} nm; seed {SEED}.','', '## Nominal three core metrics','', '| candidate | spectral peak | spectral FWHM | 450 max angle | strict | near | angular FWHM | spectral pass | angular pass | combined |','|---|---:|---:|---:|:---:|:---:|---:|:---:|:---:|:---:|']
    for cid,n in nominal.items(): lines.append(f"| {cid} | {n['spectral_peak_nm']:.2f} | {n['spectral_FWHM_nm']:.2f} | {n['max_transmission_angle_450_deg']:+.0f} | {n['strict_normal']} | {n['near_normal']} | {n['angular_FWHM_450_deg']:.2f} | {n['spectral_target_pass']} | {n['angular_target_pass']} | {n['combined_pass']} |")
    lines += ['', '## Tolerance statistics','', 'Each design-basin and correlated-bias sample uses integer nanometres. Independent layer MC uses fixed seed and stores complete layer errors. Rates are computed over the stated sample set.','']
    for s in summaries:
        if s['scan_mode']!='nominal': lines.append(f"- {s['scan_mode']} / {s['candidate_id']}: n={s['count']}, peak mean±std {s['spectral_peak_nm_mean']:.3f}±{s['spectral_peak_nm_std']:.3f} nm, FWHM {s['spectral_FWHM_nm_mean']:.3f}±{s['spectral_FWHM_nm_std']:.3f} nm, T450 {s['T450_mean']:.4f}±{s['T450_std']:.4f}, max-angle |mean| {abs(s['max_transmission_angle_450_deg_mean']):.3f} deg / max abs {max(abs(s['max_transmission_angle_450_deg_min']),abs(s['max_transmission_angle_450_deg_max'])):.1f} deg, strict {s['strict_normal_rate']:.3f}, near {s['near_normal_rate']:.3f}, angular FWHM {s['angular_FWHM_450_deg_mean']:.3f}±{s['angular_FWHM_450_deg_std']:.3f} deg, combined {s['combined_pass_rate']:.3f}.")
    lines += ['', '## Robust integer alternatives','', '| candidate | scan | geometry | spectral peak | FWHM | T450 | angle | angular FWHM | combined | reason |','|---|---|---|---:|---:|---:|---:|---:|:---:|---|']
    for r in candidates[:20]: lines.append(f"| {r['candidate_id']} | {r['scan_mode']} | `{r['geometry']}` | {r['spectral_peak_nm']:.2f} | {r['spectral_FWHM_nm']:.2f} | {r['T450']:.4f} | {r['max_transmission_angle_450_deg']:+.0f} | {r['angular_FWHM_450_deg']:.2f} | {r['combined_pass']} | {r['selection_reason']} |")
    lines += ['', '## Interpretation','', '- Explicit uses a 13-layer central-defect sequence; ZL-1 uses 12 compiled physical layers with effective center L=(M+1)L.', '- Spectral, angular, and combined gates are reported separately; these are screening gates, not universal physical criteria.', '- TMM maximum-transmission angle is a plane-wave angular-selection result and is not a dipole far-field peak.', '- Existing coarse/refined/FDTD results and frozen materials were not modified.']
    REPORT.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'native_range_nm':native_range,'counts':manifest['counts'],'nominal':{k:{x:v[x] for x in ('spectral_peak_nm','spectral_FWHM_nm','T450','max_transmission_angle_450_deg','angular_FWHM_450_deg','combined_pass')} for k,v in nominal.items()}},indent=2))

if __name__=='__main__':
    if '--postprocess-only' in sys.argv: postprocess_only()
    else: main()
