"""Standalone historical-field analysis. No Lumerical or production imports."""
import os
for _key in ('OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','OMP_NUM_THREADS'):
    os.environ[_key]='1'
import io
import json
import hashlib
import zipfile
from pathlib import Path
import numpy as np

C0=299792458.0
ETA=376.730313668
PERIOD=np.array([1740e-9,290e-9])
RCOND=1e-6
UNRESOLVED='UNRESOLVED_CONTRACT_FIELD'

def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''): h.update(b)
    return h.hexdigest()

def write_json(p,d):
    Path(p).write_text(json.dumps(d,indent=2,sort_keys=True,allow_nan=False)+'\n',encoding='utf-8')

def save_npz(p,arrays):
    # Fixed ZIP metadata makes the artifact bytes reproducible.
    with zipfile.ZipFile(p,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=1) as z:
        for k,a in sorted(arrays.items()):
            b=io.BytesIO();np.save(b,np.asarray(a),allow_pickle=False)
            item=zipfile.ZipInfo(k+'.npy',(1980,1,1,0,0,0));item.compress_type=zipfile.ZIP_DEFLATED
            z.writestr(item,b.getvalue(),compresslevel=1)

def weights(x):
    d=np.diff(x)
    if not np.all(d>0): raise ValueError('coordinates must increase')
    return np.r_[d[0]/2,(d[:-1]+d[1:])/2,d[-1]/2]

def transform_axis(x):
    """Finite-aperture quadrature at historical k nodes; inverse is regularized."""
    dx=float(np.median(np.diff(x)))
    k=2*np.pi*np.fft.fftshift(np.fft.fftfreq(len(x),dx))
    a=np.exp(-1j*k[:,None]*x[None,:])*weights(x)[None,:]
    u,s,v=np.linalg.svd(a,full_matrices=False)
    keep=s>s[0]*RCOND
    inv=(v.conj().T*np.where(keep,1/s,0))@u.conj().T
    audit={'spacing_min_m':float(np.diff(x).min()),'spacing_max_m':float(np.diff(x).max()),
           'spacing_median_m':dx,'uniform':bool(np.allclose(np.diff(x),dx,rtol=1e-7,atol=1e-16)),
           'rank_retained':int(keep.sum()),'rank_full':len(x),'rcond':RCOND,
           'condition_full':float(s[0]/s[-1]),'physical_range_m':[float(x[0]),float(x[-1])],
           'legacy_assumed_range_m':float((len(x)-1)*dx)}
    return k,a,inv,audit

def fold(k,period):
    g=2*np.pi/period; order=np.floor(k/g+.5).astype(np.int64)
    return k-order*g,order,order*g

def basis(kx,ky,k0):
    ux,uy=np.broadcast_arrays(kx/k0,ky/k0);rho=np.hypot(ux,uy)
    qx=np.divide(ux,rho,out=np.ones_like(rho),where=rho>1e-14)
    qy=np.divide(uy,rho,out=np.zeros_like(rho),where=rho>1e-14)
    w=np.sqrt((1-rho**2).astype(complex))
    s=np.stack([-qy,qx,np.zeros_like(rho)])
    pp=np.stack([w*qx,w*qy,-rho]);pm=np.stack([-w*qx,-w*qy,-rho])
    return s,pp,pm,w,rho,qx,qy

def project(e,h,b):
    """Use tangential E/H; longitudinal disagreement remains explicit residual."""
    s,pp,pm,w,rho,qx,qy=b
    if np.any(abs(w)<1e-12):raise ValueError('grazing directional basis unresolved')
    es=s[0]*e[0]+s[1]*e[1];eq=qx*e[0]+qy*e[1]
    hs=ETA*(s[0]*h[0]+s[1]*h[1]);hq=ETA*(qx*h[0]+qy*h[1])
    return np.stack([.5*(hs+eq/w),.5*(es-hq/w),.5*(hs-eq/w),.5*(es+hq/w)])

def reconstruct(a,b):
    s,pp,pm,*_=b
    e=pp*a[0]+s*a[1]+pm*a[2]+s*a[3]
    h=(s*(a[0]+a[2])-pp*a[1]-pm*a[3])/ETA
    return e,h

def propagate(a,kz,dz):
    return a*np.exp(1j*np.array([1,1,-1,-1])[:,None,None]*kz[None,:,:]*dz)

def metrics(a,b):
    a=a.ravel();b=b.ravel(); na=np.linalg.norm(a);nb=np.linalg.norm(b)
    mask=(abs(a)>abs(a).max()*1e-6)&(abs(b)>abs(b).max()*1e-6)
    ph=np.angle(b[mask]*a[mask].conj())
    ac=np.corrcoef(abs(a),abs(b))[0,1] if np.std(abs(a))*np.std(abs(b))>0 else 1.
    corr=np.vdot(a,b)/(na*nb) if na*nb else 0j
    return {'complex_relative_L2':float(np.linalg.norm(b-a)/max(na,1e-300)),
            'amplitude_relative_L2':float(np.linalg.norm(abs(b)-abs(a))/max(na,1e-300)),
            'amplitude_correlation':float(ac),'complex_correlation_real':float(corr.real),
            'complex_correlation_imag':float(corr.imag),'spatial_overlap':float(abs(corr)**2),
            'phase_rms_rad':float(np.sqrt(np.mean(ph**2))) if len(ph) else 0.,
            'phase_abs_p95_rad':float(np.quantile(abs(ph),.95)) if len(ph) else 0.,
            'phase_abs_max_rad':float(max(abs(ph))) if len(ph) else 0.,'phase_samples':int(len(ph)),
            'phase_mask':'both amplitudes > 1e-6 respective maximum; numerical diagnostic only'}

def check_metadata(d):
    for key,row in d['authority'].items():
        if row['authority_status'] not in ['FROZEN','DERIVED','PROTOTYPE','UNRESOLVED']: raise ValueError(key)
        if row['value']==UNRESOLVED and row['authority_status']!='UNRESOLVED':raise ValueError(key)
        if row['authority_status']=='FROZEN' and not row.get('provenance'):raise ValueError(key)
    required=['logical_reference_plane_z','actual_sample_plane_z','propagation_medium','time_harmonic_convention','fourier_sign_convention','coordinate_system','unit_cell_origin','phase_origin','unit_cell_dimensions','reciprocal_lattice','bloch_k','solver_order','physical_order','polarization_basis','normalization_type','source_amplitude_orientation']
    if not all(k in d['authority'] for k in required):raise ValueError('incomplete metadata')

def schema(m):
    def row(value,status,provenance):return {'value':value,'authority_status':status,'provenance':provenance}
    de=str(m/'M2R_PHASE_PRESERVING_DEEMBEDDING_CONTRACT_V1.json');bl=str(m/'M2R_BLOCH_FOLDING_AND_G_INDEX_CONTRACT_V1.json')
    authority={
      'logical_reference_plane_z':row(1212e-9,'FROZEN',str(m/'M2R_MONITOR_PLANE_SEMANTICS_AUDIT_V1.json')+'#logical_operator_plane'),
      'actual_sample_plane_z':row(1225e-9,'FROZEN','M2Q raw z and M2R sampled_source_field_plane'),
      'delta_z':row(-13e-9,'DERIVED','logical minus actual'),
      'propagation_medium':row({'name':'Air','n':1.,'impedance_ohm':ETA},'FROZEN',de),
      'coordinate_system':row('right-handed xyz; z normal; positive order adds +x/+y reciprocal vector','DERIVED','M2Q source contract; M2R Bloch contract'),
      'unit_cell_dimensions':row(PERIOD.tolist(),'FROZEN',bl),
      'unit_cell_origin':row([0.,0.],'FROZEN',str(m/'M2R_BLOCH_FLOQUET_BRIDGE_CONTRACT_V1.json')+'#phase_origin'),
      'phase_origin':row([0.,0.,1212e-9],'DERIVED','M2R origin and logical plane'),
      'time_harmonic_convention':row(UNRESOLVED,'UNRESOLVED','No explicit frozen solver time convention located; prototype exp(-i omega t) inferred from M2R up exp(+i kz dz), not promoted to FROZEN'),
      'fourier_sign_convention':row('forward exp(-i k.r); inverse exp(+i k.r)','FROZEN',str(m/'M2R_PHASE_ORIGIN_AUDIT_V1.json')),
      'reciprocal_lattice':row('G=(mx*2pi/Lx,my*2pi/Ly)','FROZEN',bl),
      'bloch_k':row('[-pi/Lx,pi/Lx) x [-pi/Ly,pi/Ly); physical k=k_B+G','FROZEN',bl),
      'solver_order':row(UNRESOLVED,'UNRESOLVED','Finite PML dipole raw has no grating solver order; no universal BFAST mapping assigned'),
      'physical_order':row('signed reciprocal indices mx,my; never inferred from array position','FROZEN',bl),
      'polarization_basis':row('S=(-qy,qx,0); P_d=(d*w*qx,d*w*qy,-rho); normal q=(1,0), P_up=+x, P_down=-x; complex bilinear Maxwell basis','DERIVED',de),
      'normalization_type':row('raw E/H unchanged; spectral amplitudes are quadrature integrals; dipolepower is reference, sourcepower auxiliary','FROZEN','M2Q-R1 recovery metadata'),
      'source_amplitude_orientation':row('per-source physical contract: amplitude 1, phase 0 deg; X or Z electric dipole','FROZEN','M2Q X/Z physical contracts')}
    d={'schema_version':'APCD_COUPLING_INTERFACE_STATE_V1','contract_status':'INTERFACE_STATE_V1_CONTRACT_DRAFT','authority':authority,
       'channel_identity':['k_Bx','k_By','Gx','Gy','polarization','propagation_direction'],
       'channel_fields':['wavelength','frequency','physical_kx','physical_ky','k_Bx','k_By','Gx','Gy','physical_order','solver_order','polarization','propagation_direction','channel_type','complex_amplitude_real','complex_amplitude_imag','normalization_type','reference_quantity','source_contract_id','source_position','source_orientation'],
       'array_layout':'amplitude: [frequency, channel(P_up,S_up,P_down,S_down), kx, ky]; coordinates factored by axis; reference/source metadata JSON',
       'prototype_time_convention':'exp(-i omega t), DERIVED from M2R, solver provenance unresolved',
       'numeric_policy':{'quadrature':'actual-coordinate trapezoid NUDFT; no field resampling','k_nodes':'same nodes as M2R for comparison, NOT assertion of uniform physical sampling','inverse':'separable truncated-SVD inverse of quadrature map','svd_rcond':RCOND,'full_basis':'all 401x401 physical-k nodes retained; singular directions removed explicitly','truncated_basis':'G=(0,0) only counterexample; never used as main state','algorithm_tolerance':1e-10,'real_field_diagnostic_tolerance':1e-4,'tolerances_are_scientific_acceptance':False},
       'claim':'COMMON_INTERFACE_REPRESENTATION_PARTIAL','power_normalized_interface_validated':False,'source_invariant_operator_validated':False}
    check_metadata(d);return d

def multi_g(weight,kx,ky):
    bx,ox,gx=fold(kx,PERIOD[0]);by,oy,gy=fold(ky,PERIOD[1]);g=2*np.pi/PERIOD
    nx=max(4,int(np.ceil(g[0]/abs(kx[1]-kx[0]))));ny=max(16,int(np.ceil(g[1]/abs(ky[1]-ky[0]))))
    ix=np.minimum(nx-1,np.floor((bx/g[0]+.5)*nx).astype(int));iy=np.minimum(ny-1,np.floor((by/g[1]+.5)*ny).astype(int))
    bins=[{} for _ in range(nx*ny)]
    for i in range(len(kx)):
        for j in range(len(ky)):
            d=bins[ix[i]*ny+iy[j]]; key=(int(ox[i]),int(oy[j]));d[key]=d.get(key,0.)+float(weight[i,j])
    threshold=.001*max(max(d.values(),default=0.) for d in bins); rows=[]
    for b,d in enumerate(bins):
        ranked=sorted(d.items(),key=lambda kv:(-kv[1],kv[0]));total=sum(d.values());cum=0.;gs=[]
        for (mx,my),w in ranked:
            cum+=w;gs.append({'order':[mx,my],'weight':w,'cumulative_fraction':cum/total if total else 0.,'significant':w>=threshold})
        rows.append({'bin':b,'significant_G_count':sum(v['significant'] for v in gs),'dominant_G':gs[0]['order'] if gs else 'EMPTY','channels':gs})
    return {'bins':[nx,ny],'threshold':threshold,'threshold_policy':'0.001 global max bin/G weight; M2R threshold reused; no forced significant channel','weight_policy':'sum wavelength/direction/P/S amplitude squared at logical plane; support, NOT power; differs from M2R w-weighted score','multi_G_bins':sum(v['significant_G_count']>1 for v in rows),'max_significant_G':max(v['significant_G_count'] for v in rows),'rows':rows}

def analyze(raw_path,provenance,contract,out):
    with np.load(raw_path,allow_pickle=False) as z:raw={k:z[k] for k in z.files}
    x=raw['x'].ravel();y=raw['y'].ravel();f=raw['f'].ravel();nf=len(f);names=['Ex','Ey','Ez','Hx','Hy','Hz']
    assert all(raw[n].shape==(len(x),len(y),1,nf) and np.iscomplexobj(raw[n]) and np.isfinite(raw[n]).all() for n in names)
    kx,ax,ix,xa=transform_axis(x);ky,ay,iy,ya=transform_axis(y)
    bx,ox,gx=fold(kx,PERIOD[0]);by,oy,gy=fold(ky,PERIOD[1]);g0=(ox[:,None]==0)&(oy[None,:]==0)
    arrays={'wavelength':C0/f,'frequency':f,'x':x,'y':y,'physical_kx':kx,'physical_ky':ky,'k_Bx':bx,'k_By':by,'Gx':gx,'Gy':gy,'physical_order_x':ox,'physical_order_y':oy,'polarization':np.array(['P','S','P','S']),'propagation_direction':np.array([1,1,-1,-1]),'reference_quantity':raw['dipolepower'].ravel()}
    rows=[];amps=[];samples=[];residuals=[];classes=[];kwaves=[];weight=np.zeros((len(x),len(y)))
    for fi,ff in enumerate(f):
        fields=np.stack([raw[n][:,:,0,fi] for n in names]);spec=np.stack([ax@v@ay.T for v in fields]);b=basis(kx[:,None],ky[None,:],2*np.pi*ff/C0)
        a=project(spec[:3],spec[3:],b);er,hr=reconstruct(a,b);modal=np.concatenate([er,hr]);res=spec-modal
        kz=2*np.pi*ff/C0*b[3];target=propagate(a,kz,1212e-9-float(raw['z']));back=propagate(target,kz,float(raw['z'])-1212e-9)
        weight+=(abs(target)**2).sum(axis=0);amps.append(target);samples.append(a);residuals.append(res);kwaves.append(kz)
        cl=np.where(abs(b[4]**2-1)<=1e-12,0,np.where(b[4]**2<1,1,2)).astype(np.int8);classes.append(cl)
        full=np.stack([ix@v@iy.T for v in spec]);trunc=np.stack([ix@(v*g0)@iy.T for v in spec]);phys=np.stack([ix@v@iy.T for v in modal])
        flux=.5*np.real(fields[0]*fields[4].conj()-fields[1]*fields[3].conj());area=weights(x)[:,None]*weights(y)[None,:];pf=float(np.sum(flux*area))
        dk=abs((kx[1]-kx[0])*(ky[1]-ky[0]))/(2*np.pi)**2
        pspec=float(np.sum(.5*np.real(spec[0]*spec[4].conj()-spec[1]*spec[3].conj()))*dk)
        pmodal=float(np.sum(np.where(cl==1,b[3].real*((abs(a[0])**2+abs(a[1])**2)-(abs(a[2])**2+abs(a[3])**2))/(2*ETA),0))*dk)
        rows.append({'wavelength_nm':float(C0/ff*1e9),'full_basis_regularized_reconstruction':{n:metrics(fields[i],full[i]) for i,n in enumerate(names)},'G0_truncated_reconstruction':{n:metrics(fields[i],trunc[i]) for i,n in enumerate(names)},'Maxwell_modal_only_reconstruction':{n:metrics(fields[i],phys[i]) for i,n in enumerate(names)},'spectral_modal_residual_E_relative_L2':float(np.linalg.norm(res[:3])/np.linalg.norm(spec[:3])),'spectral_modal_residual_H_relative_L2':float(np.linalg.norm(res[3:])/np.linalg.norm(spec[3:])),'deembedding_roundtrip':metrics(a,back),'power_flux':{'sample_integrated_poynting_W':pf,'spectral_net_flux_W':pspec,'modal_propagating_net_power_W':pmodal,'spectral_relative_closure_error':abs(pspec-pf)/max(abs(pf),1e-300),'modal_relative_closure_error':abs(pmodal-pf)/max(abs(pf),1e-300),'dipolepower_W':float(raw['dipolepower'].ravel()[fi]),'normalization_warning':'finite-aperture quadrature diagnostic; no power-normalized operator certification'}})
        print('analyzed',raw_path.stem,fi+1,nf,flush=True)
    amps=np.stack(amps);arrays.update(complex_amplitude_real=amps.real,complex_amplitude_imag=amps.imag,sample_complex_amplitude=np.stack(samples),sample_spectral_residual=np.stack(residuals),channel_type=np.stack(classes),kz=np.stack(kwaves))
    save_npz(out/'state.npz',arrays)
    report={'case_id':provenance['case_id'],'raw_path':str(raw_path),'raw_sha256':sha(raw_path),'source_provenance':provenance,'source_contract_id':contract['physical_contract_hash'],'source_position':contract['source']['position_nm'],'source_orientation':contract['source']['orientation'],'source_contract':contract,'grid':{'x':xa,'y':ya},'inventory':{k:{'shape':list(v.shape),'dtype':str(v.dtype)} for k,v in raw.items()},'logical_reference_plane_z':1212e-9,'actual_sample_plane_z':float(raw['z']),'delta_z':1212e-9-float(raw['z']),'propagation_medium':'Air n=1','normalization_type':'unscaled raw-field spectral integral; no power-normalized claim','solver_order':UNRESOLVED,'spectral_residual_role':'auxiliary measured non-Maxwell residual at sample plane; not a physical channel; not propagated','rows':rows,'state_sha256':sha(out/'state.npz')}
    write_json(out/'metadata.json',report);write_json(out/'multi_g.json',multi_g(weight,kx,ky))
    return report,arrays
