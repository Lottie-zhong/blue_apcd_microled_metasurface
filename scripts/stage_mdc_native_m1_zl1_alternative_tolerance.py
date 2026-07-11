from __future__ import annotations
import csv, json, math, sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
from apcd_native_materials import get_native_epsilon_samples, material_metadata
from mdc_tmm_core import emission_tmm

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs'/'mdc_native_m1_zl1_alternative_tolerance'
REPORT=ROOT/'reports'/'mdc_defect_450'/'mdc_native_m1_zl1_alternative_tolerance.md'
SEED=20260711
CASES={
 'ZL1_N3_M3_L78_H46':[('H',46),('L',78),('H',46),('L',78),('H',46),('L',312),('H',46),('L',78),('H',46),('L',78),('H',46),('L',78)],
 'ZL1_N3_M3_L79_H44_C316':[('H',44),('L',79),('H',44),('L',79),('H',44),('L',316),('H',44),('L',79),('H',44),('L',79),('H',44),('L',79)],
}

def fwhm(x,y):
 x=np.asarray(x,float); y=np.asarray(y,float); i=int(np.argmax(y)); h=float(y[i])/2; l=i
 while l>0 and y[l]>=h:l-=1
 r=i
 while r<len(y)-1 and y[r]>=h:r+=1
 if l==0 or r==len(y)-1:return float('nan'),True
 xl=x[l]+(h-y[l])*(x[l+1]-x[l])/(y[l+1]-y[l]); xr=x[r-1]+(h-y[r-1])*(x[r]-x[r-1])/(y[r]-y[r-1]); return float(xr-xl),False

def gate(m):
 m['spectral_target_pass']=bool(448<=m['spectral_peak_nm']<=453 and m['T450']>=.60 and 2<=m['spectral_FWHM_nm']<=12)
 m['angular_target_pass']=bool(abs(m['max_angle_450_deg'])<=5 and m['angular_FWHM_450_deg']<=35)
 m['combined_pass']=bool(m['spectral_target_pass'] and m['angular_target_pass']); return m

def metric(seq):
 coarse=np.arange(420.,480.0001,.1); vals=[]
 for w in coarse:
  a=emission_tmm(seq,float(w),0,'TE','native_m1'); b=emission_tmm(seq,float(w),0,'TM','native_m1'); vals.append((a['T']+b['T'])/2)
 vals=np.asarray(vals); ci=int(np.argmax(vals)); cp=float(coarse[ci]); fine=np.arange(max(420.,cp-5),min(480.,cp+5)+1e-9,.02); fv=np.asarray([(emission_tmm(seq,float(w),0,'TE','native_m1')['T']+emission_tmm(seq,float(w),0,'TM','native_m1')['T'])/2 for w in fine]); fi=int(np.argmax(fv)); peak=float(fine[fi]); fw,clip=fwhm(fine,fv)
 def T(w,a):
  te=emission_tmm(seq,w,a,'TE','native_m1'); tm=emission_tmm(seq,w,a,'TM','native_m1'); return (te['T']+tm['T'])/2,max(abs(te['R']+te['T']-1),abs(tm['R']+tm['T']-1))
 t448=T(448,0)[0]; t450=T(450,0)[0]; t453=T(453,0)[0]; angles=np.arange(-60.,60.0001,1.); av=np.asarray([T(450,float(a))[0] for a in angles]); ai=int(np.argmax(av)); ma=float(angles[ai]); aw,aclip=fwhm(angles,av); imax=float(np.max(av)); i0=float(av[60]); sym=float(max(abs(av[i]-av[-i-1]) for i in range(60))); residual=max(T(float(w),float(a))[1] for w in (448,450,453) for a in (0,20,40,60))
 return gate({'spectral_peak_nm':peak,'spectral_FWHM_nm':fw,'T448':t448,'T450':t450,'T453':t453,'max_angle_450_deg':ma,'angular_FWHM_450_deg':aw,'I0_over_Imax_450':i0/imax if imax else float('nan'),'strict_normal':abs(ma)<=1,'near_normal':abs(ma)<=5,'angle_symmetry_error_max':sym,'energy_residual_max':float(residual),'spectral_boundary_clipped':clip,'angular_boundary_clipped':aclip,'sequence_json':json.dumps(seq,separators=(',',':'))})

def job(j):
 cid,seq,mode,idx,extra=j; r=metric(seq); r.update({'candidate_id':cid,'scan_mode':mode,'sample_index':idx,'sample_id':f'{mode}_{cid}_{idx:04d}'}); r.update(extra); return r

def run(jobs):
 with ProcessPoolExecutor(max_workers=4) as p:return list(p.map(job,jobs,chunksize=4))

def write(name,rows):
 fields=[]
 for r in rows:
  for k in r:
   if k not in fields:fields.append(k)
 with (OUT/name).open('w',newline='',encoding='utf-8') as f:
  w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader()
  for r in rows:
   rr=dict(r)
   for k,v in rr.items():
    if isinstance(v,float) and not math.isfinite(v):rr[k]=''
   w.writerow(rr)

def summary(rows,cid,mode):
 o={'candidate_id':cid,'scan_mode':mode,'count':len(rows)}
 for k in ('spectral_peak_nm','spectral_FWHM_nm','T450','max_angle_450_deg','angular_FWHM_450_deg','I0_over_Imax_450'):
  a=np.asarray([float(r[k]) for r in rows if r.get(k) not in ('',None) and math.isfinite(float(r[k]))],float)
  if len(a)==0:a=np.asarray([0.0])
  o[k+'_mean']=float(np.mean(a));o[k+'_std']=float(np.std(a));o[k+'_min']=float(np.min(a));o[k+'_max']=float(np.max(a));o[k+'_valid_count']=int(len(a))
 for k in ('strict_normal','near_normal','spectral_target_pass','angular_target_pass','combined_pass'):o[k+'_rate']=float(np.mean([bool(r[k]) for r in rows]))
 o['boundary_spectral_count']=sum(bool(r.get('spectral_boundary_clipped')) for r in rows);o['boundary_angular_count']=sum(bool(r.get('angular_boundary_clipped')) for r in rows);return o

def main():
 OUT.mkdir(parents=True,exist_ok=True);REPORT.parent.mkdir(parents=True,exist_ok=True);d=get_native_epsilon_samples('APCD_SIO2_NATIVE_M1');lam=299792458e9/d['frequency_hz'];native=[float(lam.min()),float(lam.max())]
 if native[0]>420 or native[1]<480:raise RuntimeError('Native-M1 range does not cover 420-480')
 jobs=[]
 for i,(cid,seq) in enumerate(CASES.items()):jobs.append((cid,seq,'nominal',i,{}))
 nominal=run(jobs);write('nominal_metrics.csv',nominal)
 local_jobs=[];idx=0
 for cid,base in CASES.items():
  H0=44 if cid.endswith('C316') else 46;L0=79 if cid.endswith('C316') else 78;C0=316 if cid.endswith('C316') else 312
  for dh in range(-3,4):
   for dl in range(-3,4):
    for dc in range(-3,4):
     seq=[('H',H0+dh),('L',L0+dl),('H',H0+dh),('L',L0+dl),('H',H0+dh),('L',C0+dc),('H',H0+dh),('L',L0+dl),('H',H0+dh),('L',L0+dl),('H',H0+dh),('L',L0+dl)]
     local_jobs.append((cid,seq,'local_basin',idx,{'delta_H_nm':dh,'delta_L_nm':dl,'delta_center_nm':dc}));idx+=1
 local=run(local_jobs);write('local_basin_metrics.csv',local)
 rng=np.random.default_rng(SEED);mc_jobs=[]
 for cid,base in CASES.items():
  for b in (1,3,5):
   for j in range(300):
    seq=[];errs=[]
    for mat,t in base:e=int(rng.integers(-b,b+1));errs.append(e);seq.append((mat,int(t)+e))
    mc_jobs.append((cid,seq,f'independent_layer_{b}nm',j,{'error_bound_nm':b,'layer_errors_json':json.dumps(errs,separators=(',',':'))}))
 mc=run(mc_jobs);write('independent_mc_metrics.csv',mc)
 sums=[]
 for cid in CASES:
  sums.append(summary([r for r in nominal if r['candidate_id']==cid],cid,'nominal'))
  lr=[r for r in local if r['candidate_id']==cid]
  for b in (1,2,3):sums.append(summary([r for r in lr if abs(r['delta_H_nm'])<=b and abs(r['delta_L_nm'])<=b and abs(r['delta_center_nm'])<=b],cid,f'local_basin_pm{b}nm'))
  sums.append(summary(lr,cid,'local_basin_full_pm3nm'))
  for b in (1,3,5):sums.append(summary([r for r in mc if r['candidate_id']==cid and r['error_bound_nm']==b],cid,f'independent_layer_{b}nm'))
 write('comparison_summary.csv',sums)
 manifest={'seed':SEED,'native_range_nm':native,'wavelength_coarse_nm':[420,480,.1],'fine_step_nm':.02,'angle_range_deg':[-60,60,1],'probe_wavelengths_nm':[448,450,453],'cases':CASES,'counts':{'nominal':2,'local_basin':686,'independent_mc':1800}}
 (OUT/'run_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8');(OUT/'summary.json').write_text(json.dumps({'native_range_nm':native,'seed':SEED,'counts':manifest['counts'],'nominal_metrics':nominal,'material_metadata':{m:material_metadata(m) for m in ('APCD_TIO2_NATIVE_M1','APCD_SIO2_NATIVE_M1')},'no_fdtd':True},indent=2),encoding='utf-8')
 lines=['# Native-M1 ZL-1 alternative tolerance comparison','','Pure-film TMM only; no FDTD/Lumerical. Local basin uses ΔH/ΔL/Δcenter = −3…+3 nm integer offsets; MC seed 20260711.','', '## Nominal three core metrics','', '| candidate | peak | FWHM | T448 | T450 | T453 | 450 angle | angular FWHM | I0/Imax | strict | near |','|---|---:|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|']
 for r in nominal:lines.append(f"| {r['candidate_id']} | {r['spectral_peak_nm']:.3f} | {r['spectral_FWHM_nm']:.3f} | {r['T448']:.4f} | {r['T450']:.4f} | {r['T453']:.4f} | {r['max_angle_450_deg']:+.0f} | {r['angular_FWHM_450_deg']:.3f} | {r['I0_over_Imax_450']:.4f} | {r['strict_normal']} | {r['near_normal']} |")
 lines += ['', '## Local basin pass rates','', '| candidate | radius | spectral | angular | combined | peak mean±std | FWHM mean±std | angle mean±std | angular FWHM mean±std |','|---|---|---:|---:|---:|---|---|---|---|']
 for s in sums:
  if s['scan_mode'].startswith('local_basin'):lines.append(f"| {s['candidate_id']} | {s['scan_mode']} | {s['spectral_target_pass_rate']:.3f} | {s['angular_target_pass_rate']:.3f} | {s['combined_pass_rate']:.3f} | {s['spectral_peak_nm_mean']:.3f}±{s['spectral_peak_nm_std']:.3f} | {s['spectral_FWHM_nm_mean']:.3f}±{s['spectral_FWHM_nm_std']:.3f} | {s['max_angle_450_deg_mean']:+.3f}±{s['max_angle_450_deg_std']:.3f} | {s['angular_FWHM_450_deg_mean']:.3f}±{s['angular_FWHM_450_deg_std']:.3f} |")
 lines += ['', '## Independent layer errors','']
 for s in sums:
  if s['scan_mode'].startswith('independent_layer'):lines.append(f"- {s['candidate_id']} {s['scan_mode']}: spectral {s['spectral_target_pass_rate']:.3f}, angular {s['angular_target_pass_rate']:.3f}, combined {s['combined_pass_rate']:.3f}; peak {s['spectral_peak_nm_mean']:.3f}±{s['spectral_peak_nm_std']:.3f} nm; FWHM {s['spectral_FWHM_nm_mean']:.3f}±{s['spectral_FWHM_nm_std']:.3f} nm; angle {s['max_angle_450_deg_mean']:+.3f}±{s['max_angle_450_deg_std']:.3f}°; angular FWHM {s['angular_FWHM_450_deg_mean']:.3f}±{s['angular_FWHM_450_deg_std']:.3f}°.")
 lines += ['', '## Decision','', '- Alternative is compared using identical Native-M1 materials, 12-layer compiled geometry, gates, FWHM interpolation, and angle definitions.', '- Maximum-transmission angle is plane-wave TMM selection, not dipole far-field.', '- Boundary-clipped widths remain blank; no NaN/inf tokens are emitted.']
 REPORT.write_text('\n'.join(lines)+'\n',encoding='utf-8');print(json.dumps({'counts':manifest['counts'],'native_range_nm':native},indent=2))

if __name__=='__main__':main()
