from pathlib import Path
import json,numpy as np
import r1_angular_spectrum as r

ROOT=Path(r'D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1')
BASE=ROOT/'outputs/coupling_ml/M2Q_CENTROID_XZ_3D_COMPLEX_SOURCE_PILOT_ACQUISITION_V1'
OUT=ROOT/'outputs/coupling_ml/INTERFACE_STATE_V1_R1_MAXWELL_ANGULAR_SPECTRUM_RECONCILIATION'

def tukey(n,alpha=.1):
    q=np.ones(n);x=np.linspace(0,1,n);left=x<alpha/2;right=x>1-alpha/2
    q[left]=.5*(1+np.cos(2*np.pi/alpha*(x[left]-alpha/2)))
    q[right]=.5*(1+np.cos(2*np.pi/alpha*(x[right]-1+alpha/2)))
    return q

def main():
    report={'window':'none_vs_tukey_alpha_0.1','purpose':'diagnostic only; no Layer-B G weights promoted'}
    for case in ['X','Z']:
        raw=BASE/f'M2Q_CENTROID_{case}_COMPLEX_SOURCE_RAW_V1.npz'
        x,y,f,fields,d=r.load_case(raw);fi=5;kx,ky=r.kgrid(x,y);ff=f[fi];k0=2*np.pi*ff/r.C0;_,mask,_,_=r.classify(kx,ky,k0)
        sp=np.stack([r.direct(fields[j,:,:,fi],x,y,kx,ky) for j in range(6)])
        win=tukey(len(x))[:,None]*tukey(len(y))[None,:]
        sw=np.stack([r.direct(fields[j,:,:,fi]*win,x,y,kx,ky) for j in range(6)])
        no=r.maxwell(sp,kx,ky,ff,mask);yes=r.maxwell(sw,kx,ky,ff,mask)
        report[case]={'wavelength_nm':float(r.C0/ff*1e9),'no_window_maxwell':no,'window_maxwell':yes,'window_vs_no_window_propagating_spectral_L2':r.rel(sw,sp,mask),'no_window_modal':r.modal_metrics(sp,kx,ky,ff,mask,1),'window_modal':r.modal_metrics(sw,kx,ky,ff,mask,1),'apodization_field_energy_fraction':float(np.sum(abs(fields[:,:,:,fi]*win)**2)/np.sum(abs(fields[:,:,:,fi])**2))}
    r.write_json(OUT/'WINDOW_SENSITIVITY_450NM.json',report)
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
