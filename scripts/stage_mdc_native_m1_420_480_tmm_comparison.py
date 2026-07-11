import csv,json,math
from pathlib import Path
import numpy as np
import apcd_native_materials as M
from mdc_tmm_core import emission_tmm
R=Path(__file__).resolve().parents[1];O=R/'outputs/mdc_native_m1_420_480_tmm_comparison';REP=R/'reports/mdc_defect_450/mdc_native_m1_420_480_tmm_comparison.md';CASES={'EX_N3_L79_H45_C156':[('L',79),('H',45)]*3+[('L',156)]+[('H',45),('L',79)]*3,'ZL1_N3_M3_L78_H46':[('H',46),('L',78),('H',46),('L',78),('H',46),('L',312),('H',46),('L',78),('H',46),('L',78),('H',46),('L',78)]}
def main():
 O.mkdir(parents=True,exist_ok=True);d=M.get_native_epsilon_samples('APCD_SIO2_NATIVE_M1');w=d['frequency_hz'];lam=299792458e9/w;assert lam.min()<=420 and lam.max()>=480
 rows=[];ang=[]
 for cid,l in CASES.items():
  for a in range(0,61,10):
   for pol in ('TE','TM'):
    wl=np.arange(420,480.001,.1);T=np.array([emission_tmm(l,float(x),a,pol,'native_m1')['T'] for x in wl]);i=np.where((T[1:-1]>T[:-2])&(T[1:-1]>=T[2:]))[0]+1;inds=sorted(i,key=lambda j:T[j],reverse=True);main=inds[0] if len(inds) else int(np.argmax(T));sec=inds[1] if len(inds)>1 else None;z=np.where(T>=T[main]/2)[0];rows.append({'candidate':cid,'angle_deg':a,'polarization':pol,'main_peak_nm':wl[main],'main_peak_T':T[main],'spectral_FWHM_nm':wl[z[-1]]-wl[z[0]],'secondary_peak_nm':'' if sec is None else wl[sec],'secondary_peak_T':'' if sec is None else T[sec],'stopband_left_nm':wl[max(0,main-20)],'stopband_right_nm':wl[min(len(wl)-1,main+20)],'T448':T[280],'T450':T[300],'T453':T[330],'energy_residual_max':max(abs(emission_tmm(l,float(x),a,pol,'native_m1')['R']+emission_tmm(l,float(x),a,pol,'native_m1')['T']-1) for x in wl[::20])})
  for x in (448,450,453):
   vals=[(a,(emission_tmm(l,x,a,'TE','native_m1')['T']+emission_tmm(l,x,a,'TM','native_m1')['T'])/2) for a in range(0,61,2)];mx=max(vals,key=lambda q:q[1]);ang.append({'candidate':cid,'wavelength_nm':x,'maximum_transmission_angle_deg':mx[0],'maximum_at_0deg':mx[0]==0,'half_power_width_deg':sum(v>=mx[1]/2 for _,v in vals)*2,'T_at_max':mx[1]})
 def wr(n,x):
  with (O/n).open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=x[0]);w.writeheader();w.writerows(x)
 wr('spectra_420_480.csv',rows);wr('spectral_metrics.csv',rows);wr('local_peaks.csv',rows);wr('angle_metrics_448_450_453.csv',ang);wr('candidate_summary.csv',[r for r in rows if r['angle_deg']==0 and r['polarization']=='TE']);(O/'summary.json').write_text(json.dumps({'native_range_nm':[float(lam.min()),float(lam.max())],'candidates':list(CASES)},indent=2));REP.write_text('# Native-M1 420–480 nm TMM comparison\n\nPure-film plane-wave TMM only; peaks are not dipole far-field peaks.\n');print(json.dumps({'range':[float(lam.min()),float(lam.max())],'rows':len(rows)}))
if __name__=='__main__':main()
