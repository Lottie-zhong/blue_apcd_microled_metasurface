from __future__ import annotations

import csv, hashlib, json, math
from collections import defaultdict
from pathlib import Path

import numpy as np

from mdc_tmm_core import emission_tmm

ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'outputs/mdc_native_m1_topology_coarse_scan'; REP=ROOT/'reports/mdc_defect_450'
WLS=np.arange(430.,470.01,.5); BLUE=np.arange(448.,453.01,.5); META={'material_policy_id':'MDC_NATIVE_M1','material_model':'native_m1','high_index_material_id':'APCD_TIO2_NATIVE_M1','low_index_material_id':'APCD_SIO2_NATIVE_M1','defect_material_id':'APCD_SIO2_NATIVE_M1','interpolation_source_quantity':'complex_epsilon','interpolation_axis':'frequency_hz','interpolation_method':'linear','complex_index_reconstruction':'physical_principal_square_root','extrapolation_policy':'forbidden','propagation_direction':'GaN -> reverse(stack) -> Air'}

def compile_layers(logical):
    out=[]
    for m,d in logical:
        if out and out[-1][0]==m: out[-1]=(m,out[-1][1]+d)
        else: out.append((m,d))
    return out
def sequence_text(seq): return ' '.join(f'{m}{d}' for m,d in seq)
def candidates():
    for n in range(2,6):
      for h in range(42,48):
       for l in range(76,83):
        for c in range(152,163):
         x=[('L',l),('H',h)]*n+[('L',c)]+[('H',h),('L',l)]*n; yield ('Explicit',f'EX_N{n}_L{l}_H{h}_C{c}',{'N':n,'L_nm':l,'H_nm':h,'C_nm':c},x)
    for n in range(2,7):
      for m in (1,3,5):
       for h in range(42,48):
        for l in range(76,83):
         x=[('H',h),('L',l)]*n+[('L',l)]*m+[('H',h),('L',l)]*n; yield ('ZL-1',f'ZL1_N{n}_M{m}_L{l}_H{h}',{'N':n,'M_added':m,'L_nm':l,'H_nm':h,'effective_central_L_thickness_nm':m*l},x)
    for n in range(2,7):
      for h in range(42,48):
       for l in range(76,83):
        x=[('H',h),('L',l)]*n+[('L',l),('H',h)]*n; yield ('ZL-2',f'ZL2_N{n}_L{l}_H{h}',{'N':n,'L_nm':l,'H_nm':h,'defect_origin':'natural_L_L_interface','effective_defect_thickness_nm':2*l},x)
def avg(layers,w,a):
    te=emission_tmm(layers,w,a,'TE','native_m1'); tm=emission_tmm(layers,w,a,'TM','native_m1'); return te['T'],tm['T'],(te['T']+tm['T'])/2,max(te['R']+te['T'],tm['R']+tm['T'])
def fwhm(w,t):
    i=int(np.argmax(t)); half=t[i]/2; left=next((w[j] for j in range(i,0,-1) if t[j-1]<half<=t[j]),w[0]); right=next((w[j] for j in range(i,len(w)-1) if t[j]>=half>t[j+1]),w[-1]); return float(w[i]),float(t[i]),float(right-left)
def ranked(rows,perf):
    def gate(r): return abs(r['peak_error_nm'])<= (1 if perf else 1.5) and r['T450']>=.7 and r['FWHM_nm']<= (4 if perf else 12) and (perf or r['FWHM_nm']>=4) and r['T450_20deg']<= (.06 if perf else .2) and r['normal_to_40_60_ratio']>= (60 if perf else 20)
    for r in rows:r['gate_pass']=gate(r)
    return sorted(rows,key=lambda r:(not r['gate_pass'],r['FWHM_nm'] if perf else r['total_layer_count_compiled'],abs(r['peak_error_nm']),-r['normal_to_40_60_ratio'],-r['T450']))[:10]
def main():
 OUT.mkdir(parents=True,exist_ok=True); REP.mkdir(parents=True,exist_ok=True); logical=list(candidates()); assert len(logical)==2688 and len({x[1] for x in logical})==2688
 manifest=[]; groups=defaultdict(list)
 for fam,cid,geo,seq in logical:
  comp=compile_layers(seq); key=sequence_text(comp); h=hashlib.sha256(key.encode()).hexdigest()[:16]; groups[h].append(cid); manifest.append({**META,'candidate_id':cid,'topology_id':fam,'geometry':json.dumps(geo),'logical_layer_sequence':sequence_text(seq),'compiled_layer_sequence':key,'physical_sequence_hash':h,'total_layer_count_logical':len(seq),'total_layer_count_compiled':len(comp),'total_thickness_nm':sum(d for _,d in comp)})
 for row in manifest: row['duplicate_group_id']='DUP_'+row['physical_sequence_hash'];
 reps={h:next(r for r in manifest if r['physical_sequence_hash']==h) for h in groups}; values={}; blue=[]
 for h,r in reps.items():
  layers=[(part[0],float(part[1:])) for part in r['compiled_layer_sequence'].split()]; spectrum=[avg(layers,float(w),0) for w in WLS]; ts=np.array([x[2] for x in spectrum]); peak,tp,width=fwhm(WLS,ts); at={w:avg(layers,w,0) for w in (448,449,450,451,452,453)}; ang={a:avg(layers,450,a) for a in (10,20,30,40,45,50,55,60)}; normal=np.mean([avg(layers,450,a)[2] for a in (0,5,10)]); high=np.mean([ang[a][2] for a in (40,45,50,55,60)]); values[h]={'peak_wavelength_nm':peak,'peak_error_nm':peak-450,'Tpeak':tp,'FWHM_nm':width,'T450':at[450][2],'T448':at[448][2],'T449':at[449][2],'T451':at[451][2],'T452':at[452][2],'T453':at[453][2],'blue_448_453_min':min(at[w][2] for w in at),'blue_448_453_mean':float(np.mean([at[w][2] for w in at])),'T450_10deg':ang[10][2],'T450_20deg':ang[20][2],'T450_30deg':ang[30][2],'T450_40deg':ang[40][2],'T450_50deg':ang[50][2],'T450_60deg':ang[60][2],'normal_to_40_60_ratio':normal/(high+1e-12),'TE_TM_split_20deg':abs(ang[20][0]-ang[20][1]),'TE_TM_split_40deg':abs(ang[40][0]-ang[40][1]),'peak_count':int(np.sum(np.isclose(ts,tp))),'energy_max':max(x[3] for x in spectrum+list(ang.values()))};
  for w in BLUE:
   te,tm,t,_=avg(layers,float(w),0); blue.append({**META,'physical_sequence_hash':h,'wavelength_nm':float(w),'theta_air_external':0,'T_TE':te,'T_TM':tm,'T_unpolarized':t})
 metrics=[{**r,**values[r['physical_sequence_hash']]} for r in manifest]; assert all(np.isfinite(float(x[k])) for x in metrics for k in ('T450','Tpeak','FWHM_nm','energy_max'))
 def write(name,rows):
  with (OUT/name).open('w',newline='',encoding='utf-8') as f:
   w=csv.DictWriter(f,fieldnames=sorted({k for r in rows for k in r}));w.writeheader();w.writerows(rows)
 write('manifest.csv',manifest);write('unique_physical_sequences.csv',list(reps.values()));write('metrics_all.csv',metrics);write('blue_448_453_all.csv',[{**b,'candidate_id':cid} for b in blue for cid in groups[b['physical_sequence_hash']]])
 fab=[x for fam in ('Explicit','ZL-1','ZL-2') for x in ranked([r for r in metrics if r['topology_id']==fam],False)]; perf=[x for fam in ('Explicit','ZL-1','ZL-2') for x in ranked([r for r in metrics if r['topology_id']==fam],True)]; write('shortlist_fab.csv',fab);write('shortlist_perf.csv',perf);write('shortlist_global.csv',ranked(metrics,False)[:20]+ranked(metrics,True)[:20])
 summary={'logical_candidates':2688,'unique_physical_sequences':len(reps),'duplicate_groups':sum(len(v)>1 for v in groups.values()),'seed_candidate_id':'EX_N3_L79_H45_C156','seed_rank_fab':next(i+1 for i,r in enumerate(ranked(metrics,False)) if r['candidate_id']=='EX_N3_L79_H45_C156') if any(r['candidate_id']=='EX_N3_L79_H45_C156' for r in ranked(metrics,False)) else None};(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2));(OUT/'scan_summary.json').write_text(json.dumps(summary,indent=2));
 (REP/'mdc1b_legacy_material_source_audit.md').write_text('# MDC1B legacy material source audit\n\nMDC1A/MDC1B used constant `SiO2=1.426`, `TiO2=2.535`, `GaN=2.41`, not spectral dispersion. This is a historical constant-index model, not the Native-M1 baseline. Ratio reused: mean T450(0–10 deg) / mean T450(40–60 deg).\n')
 (REP/'mdc_native_m1_topology_coarse_scan.md').write_text('# Native-M1 topology coarse scan\n\nLogical candidates: 2688. Unique physical sequences: '+str(len(reps))+'.\n\nNative-M1 only; GaN -> reverse(stack) -> Air. FAB/PERF shortlists are in the output CSVs. Recommended refine candidate: '+fab[0]['candidate_id']+'.\n')
 print(json.dumps(summary))
if __name__=='__main__':main()
