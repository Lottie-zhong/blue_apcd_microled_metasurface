import csv,json,hashlib,math
from pathlib import Path
import numpy as np
from mdc_tmm_core import emission_tmm
R=Path(__file__).resolve().parents[1];O=R/'outputs/mdc_native_m1_shortlist_refine';P=R/'outputs/mdc_native_m1_topology_coarse_scan'
def layers(r):
 return [(x[0],float(x[1:])) for x in r['compiled_layer_sequence'].split()]
def avg(l,w,a):
 x=[emission_tmm(l,w,a,p,'native_m1') for p in ('TE','TM')];return x[0]['T'],x[1]['T'],(x[0]['T']+x[1]['T'])/2,max(z['R']+z['T'] for z in x)
def fwhm(w,t):
 i=int(np.argmax(t));h=t[i]/2
 def cross(a,b,ya,yb):return a+(h-ya)*(b-a)/(yb-ya)
 L=next((cross(w[j-1],w[j],t[j-1],t[j]) for j in range(i,0,-1) if t[j-1]<h<=t[j]),w[0]);Q=next((cross(w[j],w[j+1],t[j],t[j+1]) for j in range(i,len(w)-1) if t[j]>=h>t[j+1]),w[-1]);return w[i],t[i],Q-L
def main():
 O.mkdir(parents=True,exist_ok=True);rows=list(csv.DictReader((P/'metrics_all.csv').open()));by={r['candidate_id']:r for r in rows};sel=[]
 for fam in ('Explicit','ZL-1','ZL-2'):
  sel += [r for r in csv.DictReader((P/'shortlist_fab.csv').open()) if r['topology_id']==fam and r['gate_pass']=='true'][:3]
 sel += [by['EX_N3_L79_H45_C156']]
 sel += [r for r in csv.DictReader((P/'shortlist_global.csv').open()) if r['objective']=='PERF' and r['gate_pass']=='true'][:4]
 sel += [r for r in csv.DictReader((P/'shortlist_perf.csv').open()) if r['topology_id']=='ZL-1' and r['gate_pass']=='true'][:1]+[by['EX_N5_L82_H45_C153']]
 d={r['candidate_id']:r for r in sel};sel=list(d.values());wl=np.arange(435,465.001,.1);out=[];sp=[];blue=[];ang=[]
 for r in sel:
  l=layers(r);z=[]
  for w in wl:
   te,tm,t,e=avg(l,float(w),0);z.append((w,te,tm,t,e));sp.append({'candidate_id':r['candidate_id'],'wavelength_nm':w,'theta_air_external':0,'T_TE':te,'T_TM':tm,'T_unpolarized':t})
  peak,tp,fw=fwhm(wl,np.array([x[3] for x in z]));t450=next(x[3] for x in z if abs(x[0]-450)<.01);p20=max((avg(l,float(w),20)[2],w) for w in wl);a={x:avg(l,450,x) for x in range(0,61,2)};ratio=np.mean([a[x][2] for x in range(0,11,2)])/(np.mean([a[x][2] for x in range(40,61,2)])+1e-12)
  for w in np.arange(448,453.01,.25):
   for th in (0,10,20):
    te,tm,t,e=avg(l,float(w),th);blue.append({'candidate_id':r['candidate_id'],'wavelength_nm':w,'theta_air_external':th,'T_TE':te,'T_TM':tm,'T_unpolarized':t})
  for w in (448,450,453):
   for th in range(0,61,2):
    te,tm,t,e=avg(l,w,th);ang.append({'candidate_id':r['candidate_id'],'wavelength_nm':w,'theta_air_external':th,'T_TE':te,'T_TM':tm,'T_unpolarized':t})
  b=[x['T_unpolarized'] for x in blue if x['candidate_id']==r['candidate_id'] and x['theta_air_external']==0];m={**r,'material_model':'native_m1','peak_wavelength_0deg':peak,'peak_error_0deg':peak-450,'Tpeak_0deg':tp,'FWHM_0deg':fw,'T450_0deg':t450,'peak_wavelength_20deg':p20[1],'peak_shift_0_to_20deg':p20[1]-peak,'T450_20deg':a[20][2],'blue_448_453_min':min(b),'blue_448_453_mean':float(np.mean(b)),'normal_to_40_60_ratio':ratio,'TE_TM_split_20deg':abs(a[20][0]-a[20][1]),'TE_TM_split_40deg':abs(a[40][0]-a[40][1]),'angular_half_power_width_450':sum(x[1][2]>=a[0][2]/2 for x in a.items())*2,'total_layer_count':len(l),'total_thickness_nm':sum(x[1] for x in l)};out.append(m)
 def gate(x,k):return abs(x['peak_error_0deg'])<=(1 if k=='PERF' else 1.5) and x['T450_0deg']>=.7 and x['FWHM_0deg']<=(4 if k=='PERF' else 12) and (k=='PERF' or x['FWHM_0deg']>=4) and x['T450_20deg']<=(.06 if k=='PERF' else .2) and x['normal_to_40_60_ratio']>=(60 if k=='PERF' else 20)
 fab=sorted(out,key=lambda x:(not gate(x,'FAB'),x['total_layer_count'],abs(x['peak_error_0deg']),-x['normal_to_40_60_ratio']));perf=sorted(out,key=lambda x:(not gate(x,'PERF'),x['FWHM_0deg'],-x['normal_to_40_60_ratio']));zl=next(x for x in perf+fab if x['topology_id'].startswith('ZL'))
 for tag,x,k in [('MDC_NATIVE_M1_FAB_PROPOSED',fab[0],'FAB'),('MDC_NATIVE_M1_PERF_PROPOSED',perf[0],'PERF'),('MDC_NATIVE_M1_ZL_PROPOSED',zl,'ZL')]:x['proposal']=tag;x['gate']=gate(x,k if k!='ZL' else ('PERF' if gate(x,'PERF') else 'FAB'))
 def wr(n,a):
  with (O/n).open('w',newline='',encoding='utf-8') as f:w=csv.DictWriter(f,fieldnames=sorted({k for q in a for k in q}));w.writeheader();w.writerows(a)
 wr('refine_manifest.csv',sel);wr('metrics_refined.csv',out);wr('spectra_refined.csv',sp);wr('blue_refined.csv',blue);wr('angular_refined.csv',ang);wr('fdtd_proposed_shortlist.csv',[fab[0],perf[0],zl]);(O/'refine_manifest.json').write_text(json.dumps(sel,indent=2));(O/'summary.json').write_text(json.dumps({'count':len(sel),'proposals':[fab[0]['candidate_id'],perf[0]['candidate_id'],zl['candidate_id']]},indent=2));(R/'reports/mdc_defect_450/mdc_native_m1_shortlist_refine.md').write_text('# Native-M1 shortlist refine\n\nFDTD proposed shortlist only; not a final baseline.\n');print(len(sel))
if __name__=='__main__':main()
