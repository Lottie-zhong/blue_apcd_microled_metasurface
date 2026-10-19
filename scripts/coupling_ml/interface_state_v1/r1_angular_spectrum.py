"""R1 Layer-A angular-spectrum reconciliation; historical inputs only."""
import os
for k in ('OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS'): os.environ[k]='1'
from pathlib import Path
import json, hashlib, zipfile, io, sys
import numpy as np

C0=299792458.0
MU0=4e-7*np.pi
ETA0=np.sqrt(MU0/(8.8541878128e-12))
RCOND=1e-6
GUARD=1e-3

def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''): h.update(b)
    return h.hexdigest()

def write_json(p,d): Path(p).write_text(json.dumps(d,indent=2,sort_keys=True,allow_nan=False)+'\n',encoding='utf-8')

def save_npz(p,arrays):
    with zipfile.ZipFile(p,'w',zipfile.ZIP_DEFLATED,compresslevel=1) as z:
        for k,a in sorted(arrays.items()):
            b=io.BytesIO();np.save(b,np.asarray(a),allow_pickle=False)
            i=zipfile.ZipInfo(k+'.npy',(1980,1,1,0,0,0));i.compress_type=zipfile.ZIP_DEFLATED
            z.writestr(i,b.getvalue(),compresslevel=1)

def weights(x):
    d=np.diff(x)
    if np.any(d<=0): raise ValueError('coordinates must increase')
    return np.r_[d[0]/2,(d[:-1]+d[1:])/2,d[-1]/2]

def uniform_grid(x,n): return np.linspace(float(x[0]),float(x[-1]),int(n))

def kgrid(x,y):
    # Equal-span Cartesian grid; this does not reuse the historical median-spacing assumption.
    dx=(x[-1]-x[0])/(len(x)-1);dy=(y[-1]-y[0])/(len(y)-1)
    kx=2*np.pi*np.fft.fftshift(np.fft.fftfreq(len(x),dx))
    ky=2*np.pi*np.fft.fftshift(np.fft.fftfreq(len(y),dy))
    return kx,ky

def direct(field,x,y,kx,ky):
    ax=np.exp(-1j*kx[:,None]*x[None,:])*weights(x)[None,:]
    ay=np.exp(-1j*ky[:,None]*y[None,:])*weights(y)[None,:]
    return ax@field@ay.T

def historical_svd(field,x,y):
    def one(c):
        d=float(np.median(np.diff(c)));k=2*np.pi*np.fft.fftshift(np.fft.fftfreq(len(c),d));a=np.exp(-1j*k[:,None]*c[None,:])*weights(c)[None,:]
        u,s,v=np.linalg.svd(a,full_matrices=False);keep=s>s[0]*RCOND
        inv=(v.conj().T*np.where(keep,1/s,0))@u.conj().T
        return k,a,inv,int(keep.sum()),float(s[0]/s[-1])
    kx,ax,ix,rx,cx=one(x);ky,ay,iy,ry,cy=one(y)
    return np.stack([ax@field@ay.T]),(kx,ky,ix,iy,rx,ry,cx,cy)

def interp1(a,src,dst,axis):
    a=np.moveaxis(np.asarray(a),axis,0);out=np.empty((len(dst),)+a.shape[1:],complex)
    for idx in np.ndindex(a.shape[1:]):
        q=a[(slice(None),)+idx]
        out[(slice(None),)+idx]=np.interp(dst,src,q.real)+1j*np.interp(dst,src,q.imag)
    return np.moveaxis(out,0,axis)

def interpolate(field,x,y,xu,yu): return interp1(interp1(field,x,xu,0),y,yu,1)

def fft_spectrum(field,xu,yu,kx,ky):
    dx=float(xu[1]-xu[0]);dy=float(yu[1]-yu[0])
    raw=np.fft.fftshift(np.fft.fft2(field))*dx*dy
    return raw*np.exp(-1j*(kx[:,None]*xu[0]+ky[None,:]*yu[0]))

def classify(kx,ky,k0):
    rho=np.sqrt(kx[:,None]**2+ky[None,:]**2)/k0
    return rho,(rho<1-GUARD),(rho>1+GUARD),(abs(rho-1)<=GUARD)

def basis(kx,ky,k0,d):
    rho=np.sqrt(kx[:,None]**2+ky[None,:]**2)/k0
    qx=np.divide(kx[:,None],rho*k0,out=np.ones_like(rho),where=rho>1e-14)
    qy=np.divide(ky[None,:],rho*k0,out=np.zeros_like(rho),where=rho>1e-14)
    w=np.sqrt((1-rho*rho).astype(complex));s=np.stack([-qy,qx,np.zeros_like(rho)])
    p=np.stack([d*w*qx,d*w*qy,-rho]);kh=np.stack([rho*qx,rho*qy,d*w])
    return s,p,kh,w,rho

def modal_project(spec,kx,ky,k0,temporal_sign):
    """Tangential four-channel projection; caller restricts interpretation to propagating mask."""
    rho=np.sqrt(kx[:,None]**2+ky[None,:]**2)/k0
    qx=np.divide(kx[:,None],rho*k0,out=np.ones_like(rho),where=rho>1e-14)
    qy=np.divide(ky[None,:],rho*k0,out=np.zeros_like(rho),where=rho>1e-14)
    w=np.sqrt((1-rho*rho).astype(complex));s=np.stack([-qy,qx,np.zeros_like(rho)])
    pup=np.stack([w*qx,w*qy,-rho]);pdown=np.stack([-w*qx,-w*qy,-rho])
    e=spec[:3];h=spec[3:]
    es=s[0]*e[0]+s[1]*e[1];eq=qx*e[0]+qy*e[1]
    hs=temporal_sign*ETA0*(s[0]*h[0]+s[1]*h[1]);hq=temporal_sign*ETA0*(qx*h[0]+qy*h[1])
    a=np.stack([.5*(hs+eq/w),.5*(es-hq/w),.5*(hs-eq/w),.5*(es+hq/w)])
    er=pup*a[0]+s*a[1]+pdown*a[2]+s*a[3]
    hr=(s*(a[0]+a[2])-pup*a[1]-pdown*a[3])/ETA0*temporal_sign
    return a,np.concatenate([er,hr])

def l2(a,mask=None):
    q=a if mask is None else a[...,mask]
    return float(np.linalg.norm(q))

def rel(a,b,mask): return float(np.linalg.norm((a-b)[...,mask])/max(np.linalg.norm(a[...,mask]),1e-300))

def maxwell(spec,kx,ky,f,mask):
    k0=2*np.pi*f/C0;om=2*np.pi*f
    rho,_,_,_=classify(kx,ky,k0)
    rows=[]
    for d in (1,-1):
        kz=d*np.sqrt(np.maximum(k0*k0-kx[:,None]**2-ky[None,:]**2,0.0))
        kv=np.stack([np.broadcast_to(kx[:,None],rho.shape),np.broadcast_to(ky[None,:],rho.shape),kz])
        e=spec[:3];h=spec[3:]
        cross=np.stack([kv[1]*e[2]-kv[2]*e[1],kv[2]*e[0]-kv[0]*e[2],kv[0]*e[1]-kv[1]*e[0]])
        rhs=om*MU0*h
        div_e=kv[0]*e[0]+kv[1]*e[1]+kv[2]*e[2]
        div_h=kv[0]*h[0]+kv[1]*h[1]+kv[2]*h[2]
        for temporal in (1,-1):
            scale=max(l2(cross,mask),l2(rhs,mask),1e-300)
            fixed=l2(cross-temporal*rhs,mask)/scale
            den=np.vdot(rhs[...,mask],rhs[...,mask])
            fit=np.vdot(rhs[...,mask],cross[...,mask])/den if abs(den)>0 else 0j
            fit_res=l2(cross-fit*rhs,mask)/scale
            rows.append({'direction':d,'temporal_sign':temporal,'fixed_residual':fixed,'best_H_scale':{'real':float(fit.real),'imag':float(fit.imag),'abs':float(abs(fit))},'fitted_residual':fit_res,'divE_ratio':l2(div_e,mask)/max(l2(kv*e,mask),1e-300),'divH_ratio':l2(div_h,mask)/max(l2(kv*h,mask),1e-300)})
    best=min(rows,key=lambda r:r['fixed_residual'])
    return {'candidates':rows,'best_fixed':best}

def modal_metrics(spec,kx,ky,f,mask,temporal):
    k0=2*np.pi*f/C0;a,recon=modal_project(spec,kx,ky,k0,temporal)
    closure=rel(spec,recon,mask)
    dk=abs((kx[1]-kx[0])*(ky[1]-ky[0]))/(2*np.pi)**2
    prop=np.where(mask,np.sqrt(np.maximum(1-(kx[:,None]**2+ky[None,:]**2)/k0**2,0)),0)
    p=float(np.sum(prop*(abs(a[0])**2+abs(a[1])**2-abs(a[2])**2-abs(a[3])**2)/(2*ETA0)*dk))
    return {'spectral_EH_reconstruction_relative_L2':closure,'modal_propagating_net_power':p,'temporal_sign':temporal}

def flux(field,x,y):
    q=.5*np.real(field[0]*field[4].conj()-field[1]*field[3].conj())
    return float(np.sum(q*weights(x)[:,None]*weights(y)[None,:]))

def method_summary(name,specs,kx,ky,f,mask,raw_field,x,y):
    mm=[]
    for fi,ff in enumerate(f):
        mx=maxwell(specs[fi],kx,ky,ff,mask[fi])
        modp=[modal_metrics(specs[fi],kx,ky,ff,mask[fi],s) for s in (1,-1)]
        mm.append({'wavelength_nm':float(C0/ff*1e9),'maxwell':mx,'modal':modp})
    return mm

def compare(a,b,mask):
    vals=[]
    for i in range(len(mask)): vals.append(rel(a[i],b[i],mask[i]))
    return {'per_wavelength':vals,'max':max(vals),'mean':float(np.mean(vals))}

def load_case(raw):
    with np.load(raw,allow_pickle=False) as z: d={k:z[k] for k in z.files}
    x=d['x'].ravel();y=d['y'].ravel();f=d['f'].ravel();
    fields=np.stack([d[n][:,:,0,:] for n in ('Ex','Ey','Ez','Hx','Hy','Hz')])
    return x,y,f,fields,d

def analyze_case(raw,out):
    x,y,f,fields,d=load_case(raw);n=len(x);xu=uniform_grid(x,n);yu=uniform_grid(y,n);kx,ky=kgrid(x,y);rho=[];masks=[];a_specs=[];b_specs=[];c_specs=[]
    b_density={};
    for density in (n//2,n,2*n):
        xg=uniform_grid(x,density);yg=uniform_grid(y,density);kgx,kgy=kgrid(xg,yg);rows=[];b_at_native=[]
        for fi,ff in enumerate(f):
            interp=np.stack([interpolate(fields[j,:,:,fi],x,y,xg,yg) for j in range(6)])
            sp= np.stack([fft_spectrum(interp[j],xg,yg,kgx,kgy) for j in range(6)])
            _,pm,_,_=classify(kgx,kgy,2*np.pi*ff/C0)
            q=maxwell(sp,kgx,kgy,ff,pm)['best_fixed']
            rows.append({'wavelength_nm':float(C0/ff*1e9),'maxwell_best_fixed':q,'interpolated_flux':flux(interp,xg,yg)})
            if density==n:b_specs.append(sp)
        b_density[str(density)]={'grid_points':density,'rows':rows}
    for fi,ff in enumerate(f):
        sp=np.stack([direct(fields[j,:,:,fi],x,y,kx,ky) for j in range(6)]);a_specs.append(sp)
        c_specs.append(np.stack([historical_svd(fields[j,:,:,fi],x,y)[0][0] for j in range(6)]))
        _,pm,_,_=classify(kx,ky,2*np.pi*ff/C0);masks.append(pm)
    masks=np.stack(masks);a_specs=np.stack(a_specs);b_specs=np.stack(b_specs);c_specs=np.stack(c_specs)
    a_rows=method_summary('A_NUDFT',a_specs,kx,ky,f,masks,fields,x,y);b_rows=method_summary('B_UNIFORM_FFT',b_specs,kx,ky,f,masks,fields,x,y);c_rows=method_summary('C_SVD_DIAGNOSTIC',c_specs,kx,ky,f,masks,fields,x,y)
    # Real-space authority and interpolation effect use raw coordinates, no SVD reconstruction.
    real_flux=[flux(fields[:,:,:,fi],x,y) for fi in range(len(f))]
    interp_flux=[b_density[str(n)]['rows'][fi]['interpolated_flux'] for fi in range(len(f))]
    out.mkdir(parents=True,exist_ok=False)
    save_npz(out/'spectral_450nm.npz',{'kx':kx,'ky':ky,'A_EH':a_specs[5],'B_EH':b_specs[5],'C_EH':c_specs[5],'propagating_mask':masks[5]})
    summary={'case_id':raw.stem,'raw_path':str(raw),'raw_sha256':sha(raw),'grid':{'n':n,'x_min_m':float(x[0]),'x_max_m':float(x[-1]),'y_min_m':float(y[0]),'y_max_m':float(y[-1]),'x_spacing_min_m':float(np.diff(x).min()),'x_spacing_max_m':float(np.diff(x).max()),'x_spacing_median_m':float(np.median(np.diff(x))),'y_spacing_min_m':float(np.diff(y).min()),'y_spacing_max_m':float(np.diff(y).max()),'y_spacing_median_m':float(np.median(np.diff(y))),'uniform':bool(np.allclose(np.diff(x),np.median(np.diff(x)),rtol=1e-7,atol=1e-16) and np.allclose(np.diff(y),np.median(np.diff(y)),rtol=1e-7,atol=1e-16))},'methods':{'A_actual_coordinate_NUDFT':{'rows':a_rows},'B_linear_interpolation_uniform_FFT':{'rows':b_rows,'grid_density':b_density},'C_historical_median_spacing_SVD_diagnostic':{'rows':c_rows,'k_grid_is_historical_median_spacing':True}},'A_vs_B_propagating_spectral_relative_L2':compare(a_specs,b_specs,masks),'A_vs_C_propagating_spectral_relative_L2':'NOT_COMPARABLE_DIFFERENT_K_GRID','real_space_flux_W':real_flux,'uniform_interp_flux_W':interp_flux,'uniform_interp_flux_relative_error':[abs(u-r)/max(abs(r),1e-300) for u,r in zip(interp_flux,real_flux)],'path_C_physical_authority':False,'path_A_or_B_physical_cross_validation':True}
    write_json(out/'summary.json',summary)
    return summary

def main():
    root=Path(r'D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1');base=root/'outputs/coupling_ml/M2Q_CENTROID_XZ_3D_COMPLEX_SOURCE_PILOT_ACQUISITION_V1';out=root/'outputs/coupling_ml/INTERFACE_STATE_V1_R1_MAXWELL_ANGULAR_SPECTRUM_RECONCILIATION';out.mkdir(exist_ok=False)
    cases={};
    for case in ('X','Z'):
        raw=base/f'M2Q_CENTROID_{case}_COMPLEX_SOURCE_RAW_V1.npz';cases[case]=analyze_case(raw,out/f'CENTROID_{case}')
    write_json(out/'RAW_FIELD_SAMPLING_CONTRACT.json',{'status':'PARTIAL_AUTHORITY','evidence':{'exporter':'coupling_fdtd_adapter_v1.py read_arrays uses getdata for common x,y,z,f and Ex/Ey/Ez/Hx/Hy/Hz','export_metadata':{'unmodified_complex_arrays':True,'no_interpolation':True},'raw_shapes':'all six fields 401x401x1x11; common coordinate keys; finite complex128','monitor':'2D Z-normal source_interface_complex; configured z=1212 nm; returned z=1225 nm','component_specific_coordinates':'not present','yee_staggering':'not recorded','Lumerical_monitor_interpolation_semantics':'not recorded'},'conclusion':'common returned coordinate arrays and shapes are evidenced; component co-location versus internal Yee interpolation is unresolved; no postprocessing interpolation occurred'})
    # No BZ folding or revised multi-G claim until Layer A passes.
    report={'status':'PARTIAL','verdict':'PHYSICAL_KSPACE_REPRESENTATION_SUPPORTED_DIRECTIONAL_OPERATOR_UNRESOLVED','layer_A_gate_pass':False,'cases':cases,'m2r_bloch_reanalysis':'NOT_PERFORMED_LAYER_A_GATE_NOT_PASSED','zero_solver':True,'training_delta':0,'solver_entry_delta':0,'rerun_delta':0,'limitations':['raw component co-location/Yee semantics unresolved','finite-aperture spectrum is continuous, not inherently periodic discrete G','SVD is diagnostic only','propagating Maxwell residual and reconstruction must be interpreted with unknown H/temporal/grid semantics']}
    write_json(out/'R1_REPORT.json',report)
    write_json(out/'R1_SHA256_MANIFEST.json',{str(f.relative_to(out)):sha(f) for f in out.rglob('*') if f.is_file() and f.name!='R1_SHA256_MANIFEST.json'})
    print(json.dumps({'status':report['status'],'verdict':report['verdict'],'cases':{k:{'A_vs_B_max':v['A_vs_B_propagating_spectral_relative_L2']['max'],'grid':v['grid']} for k,v in cases.items()}},indent=2))

if __name__=='__main__': main()
