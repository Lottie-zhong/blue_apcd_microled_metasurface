from pathlib import Path
import json, sys
import numpy as np
ROOT=Path(r'D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1')
sys.path.insert(0,str(ROOT))
from scripts.shared_fdtd.tools import pw_complex_floquet_state_v1 as pw
from scripts.coupling_ml.k6_v2_pipeline import h1
ORDERS=np.arange(-3,4,dtype=int)
WAVELENGTHS=np.arange(440.,461.)
def phase(k): return np.exp(-2j*np.pi*ORDERS*k/6.0)
def transform_c(c,k): return np.asarray(c,complex)*phase(k).reshape((1,7,1))
def transform_d(d,k): return np.roll(np.asarray(d),int(k)%6)
def err(a,b):
    a=np.asarray(a);b=np.asarray(b);d=np.abs(a-b)
    return {'max_abs':float(d.max(initial=0.0)),
            'relative_l2':float(np.linalg.norm(d.ravel())/max(np.linalg.norm(b.ravel()),1e-30))}
def need(name,ok,details):
    if not ok: raise AssertionError(name+':'+json.dumps(details,sort_keys=True))
outdir=ROOT/'reports'/'coupling'/'APCD_COUPLING_272G_K6_CYCLIC_EQUIVARIANCE_V1'
outdir.mkdir(parents=True,exist_ok=True)
result={'schema':'K6_CYCLIC_LABEL_TRANSFORM_TEST_V1','status':'PASS','tests':{},
        'convention':{'T_D':'np.roll(D,+1)=[D6,D1,D2,D3,D4,D5]',
        'translation_x_nm':'+290','Fourier_kernel':'exp(-i*G_m*x)',
        'C_transform':'exp(-i*2*pi*m*k/6)','TE_TM':'diagonal; no exchange',
        'P_scale':'invariant'}}
# Geometry cycle and stabilizer-aware unique views.
d=np.array([100,115,130,145,160,175],int);back=d.copy()
for _ in range(6): back=transform_d(back,1)
e=float(np.max(np.abs(back-d)));need('geometry_six_cycle',e==0,{'max_abs_nm':e})
result['tests']['geometry_six_cycle']={'pass':True,'max_abs_nm':e}
families={'period1':[120]*6,'period2':[100,110,100,110,100,110],
          'period3':[100,110,120,100,110,120],'period6':[100,105,110,115,120,125]}
sizes={k:len({tuple(transform_d(v,s).tolist()) for s in range(6)}) for k,v in families.items()}
need('stabilizer_dedup',sizes=={'period1':1,'period2':2,'period3':3,'period6':6},sizes)
result['tests']['stabilizer_dedup']={'pass':True,'unique_views':sizes}
# Algebra over all 21 wavelengths, all seven m values, and both polarizations.
rng=np.random.default_rng(2720619)
c=rng.normal(size=(21,7,2))+1j*rng.normal(size=(21,7,2));c6=c.copy()
for _ in range(6):c6=transform_c(c6,1)
e=err(c6,c);need('complex_six_cycle',e['max_abs']<1e-12 and e['relative_l2']<1e-12,e)
magerr=max(err(np.abs(transform_c(c,k)),np.abs(c))['max_abs'] for k in range(6))
zeroerr=max(err(transform_c(c,k)[:,3,:],c[:,3,:])['max_abs'] for k in range(6))
need('complex_magnitude_invariance',magerr<1e-12,{'max_abs':magerr})
need('zero_order_invariance',zeroerr<1e-12,{'max_abs':zeroerr})
result['tests']['random_21lambda_7orders_TE_TM']={'pass':True,'complex_six_cycle':e,
    'magnitude_max_abs':magerr,'zero_order_max_abs':zeroerr,
    'wavelengths_nm':WAVELENGTHS.tolist(),'orders':ORDERS.tolist()}
# Production projector sign check: synthesize fields with the recorded x-shifted Fourier phase.
amps={}
for i,m in enumerate(ORDERS):
    for j,pol in enumerate(('TE','TM')):
        amps[(int(m),0,1,pol)]=complex(.23+.07*i+.03*j,-.19+.04*i-.02*j)
orders=tuple((int(m),0) for m in ORDERS)
p0=pw._plane_projection(pw._synthetic_raw(349,59,0.,1.,amps,WAVELENGTHS),
    np.ones(21,complex),orders=orders,z_reference_nm=0.)
base=np.asarray(p0['coefficients'])[:,:,0,:];synthetic={}
for k in range(6):
    shift={key:v*np.exp(-1j*2*np.pi*key[0]*k/6) for key,v in amps.items()}
    got=np.asarray(pw._plane_projection(pw._synthetic_raw(349,59,0.,1.,shift,WAVELENGTHS),
        np.ones(21,complex),orders=orders,z_reference_nm=0.)['coefficients'])[:,:,0,:]
    ee=err(got,base*phase(k).reshape((1,7,1)));synthetic[str(k)]=ee
    need('projector_sign_k'+str(k),ee['relative_l2']<1e-10,ee)
result['tests']['production_projector_sign']={'pass':True,'per_k':synthetic,
    'max_abs':max(x['max_abs'] for x in synthetic.values()),
    'max_relative_l2':max(x['relative_l2'] for x in synthetic.values())}
# Frozen H2 invariance using every geometry and wavelength in the existing 272G dataset.
data=np.load(ROOT/'reports'/'coupling'/'APCD_COUPLING_AL50_COMPLEX_AWARE_PRODUCTION_V1'/
             'STAGE_50'/'COMPLEX_DATASET.npz',allow_pickle=False)
cdata=np.asarray(data['C_hat'],complex);ps=np.asarray(data['P_scale'],float)
need('dataset_shape',cdata.shape==(272,21,7,2) and ps.shape==(272,21),
     {'c':cdata.shape,'p':ps.shape})
decoder=h1.load_h2_decoder();hbase=h1.reconstruct_h2(cdata,ps,decoder);h2errs={}
for k in range(6):
    ct=cdata*phase(k).reshape((1,1,7,1));hs=h1.reconstruct_h2(ct,ps,decoder)
    h2errs[str(k)]={name:err(hs[name],hbase[name]) for name in
                    ('eta','absolute_order','total_power','modal_order')}
    for name,ee in h2errs[str(k)].items():
        need('h2_'+name+'_k'+str(k),ee['max_abs']<1e-12 and ee['relative_l2']<1e-12,ee)
result['tests']['frozen_h2_all_272G_21lambda_TE_TM']={'pass':True,'shape':list(cdata.shape),
    'P_scale_shape':list(ps.shape),'per_k':h2errs,'plus1_index':int(np.where(ORDERS==1)[0][0])}
result['h2_identity']={'expected_sha256':h1.H2_DECODER_SHA256,'module':decoder.__file__}
p=outdir/'CYCLIC_LABEL_TRANSFORM_TESTS.json'
p.write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
print(json.dumps({'status':result['status'],'tests':result['tests'],'h2_identity':result['h2_identity'],'output':str(p)},ensure_ascii=False))
