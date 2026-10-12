"""Read-only four-case forensics. Writes only this task report directory. No solver/fit imports."""
from pathlib import Path
import json,hashlib,subprocess,sqlite3,csv,re,datetime
import numpy as np,h5py
R=Path(r'D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1')
D=R/'reports/coupling/APCD_COUPLING_ML_V3_DOE56_FULL_SCIENCE_PRODUCTION_V1'
O=R/'reports/coupling/APCD_COUPLING_V3_NUMERICAL_GATE_FAILURE_FORENSIC_V1'
ETA=376.730313668; LX=1740e-9; LY=290e-9
NAMES=['Ex','Ey','Ez','Hx','Hy','Hz']; IDS=['K6V3_NUM_REPEAT_A1','K6V3_NUM_MESH4_A1','K6V3_NUM_REPEAT_A2','K6V3_NUM_MESH4_A2']
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for chunk in iter(lambda:f.read(8*1024*1024),b''):h.update(chunk)
 return h.hexdigest()
def j(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def dump(name,x):(O/name).write_text(json.dumps(x,indent=2,allow_nan=False,default=lambda v:v.tolist() if isinstance(v,np.ndarray) else str(v))+'\n')
def ah(a):
 a=np.ascontiguousarray(a);return hashlib.sha256(str(a.dtype).encode()+str(a.shape).encode()+a.tobytes()).hexdigest()
pins=[]
def pin(a,kind):
 p=Path(a['path']);s=sha(p);assert s==a['sha256'],(kind,str(p),s,a['sha256']);pins.append({'kind':kind,'path':str(p),'sha256':s,'bytes':p.stat().st_size});return p
def weights(x):
 x=np.asarray(x).ravel();assert np.all(np.diff(x)>0);return np.r_[np.diff(x)[0]/2,(x[2:]-x[:-2])/2,np.diff(x)[-1]/2]
def basis(m,wl,index):
 k0=2*np.pi/(wl*1e-9);kx=2*np.pi*m/LX;kz=complex(np.sqrt(complex((index*k0)**2-kx*kx)))
 if kz.imag<0 or (kz.imag==0 and kz.real<0):kz=-kz
 s=np.array([0,1 if m>=0 else -1,0],complex); cols=[];powers=[]
 for dr in [1,-1]:
  kh=np.array([kx,0,dr*kz])/(index*k0);p=np.cross(s,kh);bn=p@p
  if abs(bn)>1e-24 and abs(bn-1)>1e-10:p/=np.sqrt(bn)
  for e in [s,p]:
   h=index/ETA*np.cross(kh,e);cols.append(np.r_[e,h]);powers.append(.5*np.cross(e,h.conj())[2].real)
 return np.stack(cols,axis=1),kz,np.asarray(powers)
def projection(z,plane,index,ref,orders):
 x=z[plane+'_x'].ravel();y=z[plane+'_y'].ravel();f=z[plane+'_f'].ravel();wl=299792458/f*1e9;ix=np.argsort(wl);wl=wl[ix];index=np.asarray(index)[ix]
 fields=np.stack([z[plane+'_'+name][:,:,0,ix] for name in NAMES],axis=-1)
 w=weights(x)[:,None]*weights(y)[None,:]/(LX*LY);out=np.empty((21,len(orders),4),complex);res=np.empty((21,len(orders)));cond=res.copy();power=np.empty_like(out.real)
 for oi,m in enumerate(orders):
  fourier=np.exp(-2j*np.pi*m*x[:,None]/LX)*w
  sample=np.einsum('xy,xyfc->fc',fourier,fields)
  for fi,v in enumerate(wl):
   mat,kz,powz=basis(m,v,index[fi]);c,_,rank,_=np.linalg.lstsq(mat,sample[fi],rcond=None);assert rank==4
   res[fi,oi]=np.linalg.norm(mat@c-sample[fi])/max(np.linalg.norm(sample[fi]),1e-300);cond[fi,oi]=np.linalg.cond(mat)
   out[fi,oi]=c*np.exp(1j*kz*(ref-float(z[plane+'_z']))*np.array([1,1,-1,-1]));power[fi,oi]=powz
 return out,power,res,cond
def recover(z,index):
 inc,ip,ir,ic=projection(z,'IN',index,-50e-9,[0]);inc=inc[:,0,1];pinarea=ip[:,0,1]*abs(inc)**2;assert np.all(pinarea>0)
 out,powz,res,cond=projection(z,'POSTNP',np.ones(21),1722e-9,list(range(-3,4)))
 c=out[:,:,:2].reshape(21,7,2)*(inc.conj()/abs(inc)/np.sqrt(pinarea))[:,None,None]
 wl=299792458/z['POSTNP_f'].ravel()*1e9;ix=np.argsort(wl);q=np.sqrt(1-(np.array(range(-3,4))[None,:]*wl[ix,None]*1e-9/LX)**2)
 chat=c/np.sqrt(np.sum(q[:,:,None]*abs(c)**2,axis=(1,2)))[:,None,None]
 x=z['POSTNP_x'].ravel();y=z['POSTNP_y'].ravel();flux=.5*(z['POSTNP_Ex'][:,:,0,:]*z['POSTNP_Hy'][:,:,0,:].conj()-z['POSTNP_Ey'][:,:,0,:]*z['POSTNP_Hx'][:,:,0,:].conj()).real
 flux=np.einsum('xyf,x,y->f',flux,weights(x),weights(y))[ix]/(LX*LY);ps=flux/pinarea;eta=q*np.sum(abs(chat)**2,axis=2)
 return chat,ps,eta,{'pin_per_area':pinarea,'post_flux_per_area':flux,'fit_residual':res,'condition':cond,'down_up_power_ratio':np.sum(abs(out[:,:,2:])**2*abs(powz[:,:,2:]),axis=(1,2))/np.sum(abs(out[:,:,:2])**2*powz[:,:,:2],axis=(1,2))}
def diff(a,b,path=''):
 if isinstance(a,dict) and isinstance(b,dict):return sum([diff(a.get(k,'<absent>'),b.get(k,'<absent>'),path+'/'+k) for k in sorted(set(a)|set(b))],[])
 if a==b:return []
 return [{'field':path,'five_nm':a,'four_nm':b}]
def table(name,rows):
 with (O/name).open('w',newline='',encoding='utf-8') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
ledgerpath=D/'v3_execution_authority_v1/V3_EXECUTION_LEDGER_V1.json';L=j(ledgerpath);guard={str(ledgerpath):sha(ledgerpath)}
assert L['entered_case_ids']==IDS
rgpath=Path(r'D:\apcd_runtime\gpu_v3_identity_recovery_20261011_v1\V3_REGISTERED_BATCH_INTERFACE_02.json');RG=j(rgpath);guard[str(rgpath)]=sha(rgpath)
basepath=D/'science_admission_v1/BASELINE_REFERENCE_PINS.json';BASE=j(basepath)['baselines']
gatepath=Path(r'D:\apcd_runtime\gpu_platform_v2_serial_production_v1\v3_data\PRODUCTION_CUSTODIAN_PRIVATE\windows\dae6b2d36628473f8320438745efb7b2\numerical_gate\receipt.json');guard[str(gatepath)]=sha(gatepath)
db=sqlite3.connect('file:D:/apcd_runtime/gpu_platform_v2_serial_production_v1/ledger.sqlite3?mode=ro',uri=True); db.row_factory=sqlite3.Row
allcases={};proofs={};rows=[];details=[];nativepayload={};parity={};endpoint={};repeat=[]
for cid in IDS:
 r=L['case_records'][cid];v=r['evidence']['validation'];record=v['record'];rr=next(x for x in RG['cases'] if x['case_id']==cid)
 pp=pin(rr['artifacts']['load_proof'],cid+':load');proofs[cid]=j(pp);pin(rr['artifacts']['pre_fsp'],cid+':setup');pin(rr['artifacts']['physical_contract'],cid+':contract');pin(rr['artifacts']['source_manifest'],cid+':source');pin(rr['artifacts']['setup_spec'],cid+':spec')
 rawpath=pin(record['raw_npz'],cid+':raw');pin(record['raw_metadata'],cid+':raw_metadata');pin(record['state_npz'],cid+':state');pin(record['state_metadata'],cid+':state_metadata');pin(record['truth_h5'],cid+':wrapper_h5');pin(record['orders_json'],cid+':orders');labelpath=pin(v['labels_artifact'],cid+':labels')
 entrypath=Path(r['v2_entry_receipt']);pins.append({'kind':cid+':entry','path':str(entrypath),'sha256':sha(entrypath)});assert sha(entrypath)==r['v2_entry_receipt_sha256']
 with h5py.File(record['truth_h5']['path']) as f:metrics=json.loads(f['metrics_json'][()].decode())
 index=np.array([complex(n['real'],n['imag']) for n in metrics['lossy_gan']['n_gan']]);raw={k:a for k,a in np.load(rawpath).items()};lab={k:a for k,a in np.load(labelpath).items()};chat=lab['C_hat_real']+1j*lab['C_hat_imag'];print(cid,'LABEL_KEYS',list(lab))
 rec,ps,eta,diagnostics=recover(raw,index);pslabel=lab['P_scale']
 parity[cid]={'raw_to_C_hat_max_abs':float(np.max(abs(rec-chat))),'raw_to_P_scale_max_abs':float(np.max(abs(ps-pslabel))),'raw_to_H2_eta_max_abs':float(np.max(abs(eta-lab['eta']))),'fit_residual_max':float(np.max(diagnostics['fit_residual'])),'condition_max':float(np.max(diagnostics['condition'])),'down_up_power_max':float(np.max(diagnostics['down_up_power_ratio']))}
 b=Path(r['evidence']['bundle']['path']);native=b/'run/run_output.h5';fsp=b/'run.fsp'
 pins.extend([{'kind':cid+':native_h5','path':str(native),'sha256':sha(native),'bytes':native.stat().st_size},{'kind':cid+':solved_fsp','path':str(fsp),'sha256':sha(fsp),'bytes':fsp.stat().st_size}])
 nz={};nh={}
 with h5py.File(native) as f:
  for gn in f:
   g=f[gn];nh[gn]={k:ah(g[k][()]) for k in g}
   p=next((p for p in ['IN','PRENP','POSTNP'] if abs(float(raw[p+'_z'])-float(g['z'][0])*1e-6)<1e-12),None)
   if not p:continue
   for k in ['x','y','z']:nz[p+'_'+k]=g[k][()]*1e-6
   nz[p+'_f']=raw[p+'_f']
   for k in NAMES:
    a=g[k][()].astype(float).transpose(2,1,0,3);nz[p+'_'+k]=(a[...,::2]+1j*a[...,1::2])/(ETA if k.startswith('H') else 1)
 nativepayload[cid]=nh
 nc,npow,ne,nd=recover(nz,index)
 parity[cid].update({'native_h5_to_C_hat_max_abs':float(np.max(abs(nc-chat))),'native_h5_to_C_hat_relative_L2':float(np.linalg.norm(nc-chat)/np.linalg.norm(chat)),'native_h5_to_P_scale_relative_max':float(np.max(abs(npow-pslabel)/pslabel)),'native_h5_mapping':'H/ETA0; no fitted complex scale'})
 endpoint[cid]={}
 for p in ['IN','PRENP','POSTNP']:
  a=np.stack([raw[p+'_'+n] for n in NAMES]);endpoint[cid][p]={'x_relative_closure':float(np.linalg.norm(a[:,0]-a[:,-1])/np.linalg.norm(a)),'y_relative_closure':float(np.linalg.norm(a[:,:,0]-a[:,:,-1])/np.linalg.norm(a)),'actual_z_nm':float(raw[p+'_z'])*1e9,'x_points':len(raw[p+'_x']),'y_points':len(raw[p+'_y']),'dx_nm_min_max':(np.diff(raw[p+'_x'].ravel())*1e9)[[0,-1]].tolist(),'dy_nm_min_max':(np.diff(raw[p+'_y'].ravel())*1e9)[[0,-1]].tolist()}
 events=[dict(e) for e in db.execute('select * from events where request_sha=? and kind in ("ENGINE_PROCESS","PROCESS_RETURNED")',(r['request_sha256'],))];safe=[]
 for e in events:
  payload=json.loads(e['payload']);procs=payload.get('processes',[])
  if isinstance(procs,dict):procs=list(procs.values())
  safe.append({'utc_unix':e['utc_unix'],'kind':e['kind'],'payload_sha256':hashlib.sha256(e['payload'].encode()).hexdigest(),'processes':[{k:p[k] for k in p if k.lower() in ['pid','creationdate','name','executablepath','creation_time','created_unix']} for p in procs if isinstance(p,dict)]})
 attempt=b.parent.parent/'attempts'/r['request_sha256'];log=attempt/'run_p0.log';text=log.read_text(errors='replace');safe_lines=[s for s in text.splitlines() if not any(t in s.lower() for t in ['license','command','context','-shared']) and any(t in s.lower() for t in ['simulation','grid','time step','iteration','shutoff','datatype','multiprocessor','completed','finished','elapsed'])]
 details.append({'case_id':cid,'attempt_id':record['attempt_id'],'request_sha':r['request_sha256'],'entry_receipt':str(entrypath),'execution':{k:vv for k,vv in r['evidence']['execution'].items() if k in ['native_wall_seconds','returncode','returned_unix','started_unix']},'events':safe,'engine_log':str(log),'engine_log_sha256':sha(log),'safe_log_lines':safe_lines,'label_sha':sha(labelpath),'native_h5_sha':sha(native),'solved_fsp_sha':sha(fsp),'source_setup_sha':rr['artifacts']['pre_fsp']['sha256']})
 allcases[cid]={'chat':chat,'ps':pslabel,'eta':eta,'raw':raw,'raw_payloads':{k:ah(a) for k,a in raw.items()},'normalization':diagnostics}
dump('INDEPENDENT_LABEL_PARITY.json',parity);dump('NATIVE_PAYLOAD_SHA.json',nativepayload);dump('SOLVER_INDEPENDENCE_EVIDENCE.json',details);dump('RAW_ENDPOINT_AND_GRID.json',endpoint)
for i,base in enumerate(BASE):
 cid=IDS[i*2];bp=pin(base['artifacts']['raw_npz'],base['case_id']+':frozen_baseline_raw');old={k:a for k,a in np.load(bp).items()};equal={k:np.array_equal(a,allcases[cid]['raw'][k]) for k,a in old.items()}
 repeat.append({'diagnostic':cid,'historical_reference':base['case_id'],'raw_container_sha_equal':sha(bp)==sha(L['case_records'][cid]['evidence']['validation']['record']['raw_npz']['path']),'all_raw_arrays_bitwise_equal':all(equal.values()),'member_parity':equal,'historical_source_manifest':base['artifacts']['source_manifest'],'historical_runner_status':base['artifacts']['runner_status']})
 pin(base['artifacts']['source_manifest'],base['case_id']+':manifest');pin(base['artifacts']['runner_status'],base['case_id']+':status')
dump('FIVE_NM_REPEATABILITY.json',repeat)
contractdiff={}
for anchor in ['A1','A2']:
 a=proofs['K6V3_NUM_REPEAT_'+anchor];b=proofs['K6V3_NUM_MESH4_'+anchor];ar=a.get('actual_readback',a['canonical_readback']);br=b.get('actual_readback',b['canonical_readback']);contractdiff[anchor]={'actual_setup_diff':diff(ar,br),'four_nm_nonmesh_validation':b.get('nonmesh_validation'),'four_nm_only_declared_mesh_difference':b.get('only_declared_mesh_difference')}
dump('COMPLETE_READBACK_CONTRACT_DIFF.json',contractdiff)
summ={};modalrows=[]
for anchor in ['A1','A2']:
 a=allcases['K6V3_NUM_REPEAT_'+anchor];b=allcases['K6V3_NUM_MESH4_'+anchor];c=a['chat'];p=b['chat'];sq=abs(p-c)**2;amp=(abs(p)-abs(c))**2;phase=sq-amp;energy=abs(c)**2;mask=energy/energy.sum(axis=(1,2),keepdims=True)>=1e-4;angle=np.angle(p*c.conj());den=energy.sum(axis=(1,2));state=np.sqrt(sq.sum(axis=(1,2))/den);q=np.sqrt(1-(np.arange(-3,4)[None,:]*np.arange(440,461)[:,None]*1e-9/LX)**2);ae=a['eta']*a['ps'][:,None];be=b['eta']*b['ps'][:,None]
 weighted=np.sqrt(np.sum(energy*mask*angle**2,axis=(1,2))/np.sum(energy*mask,axis=(1,2)));routing=np.max(abs(b['eta']-a['eta']),axis=1);power=abs(b['ps']-a['ps'])/a['ps'];absolute=np.max(abs(be-ae),axis=1)
 for fi,wl in enumerate(range(440,461)):
  rows.append({'anchor':anchor,'wavelength_nm':wl,'state_relative_L2':state[fi],'routing_max_abs':routing[fi],'absolute_order_max_abs':absolute[fi],'P_scale_relative':power[fi],'phase_weighted_rmse':weighted[fi],'amplitude_sse_fraction':amp[fi].sum()/sq[fi].sum(),'weak_sse_fraction':sq[fi][~mask[fi]].sum()/sq[fi].sum(),'P_5nm':a['ps'][fi],'P_4nm':b['ps'][fi],'incident_power_ratio_4_over_5':b['normalization']['pin_per_area'][fi]/a['normalization']['pin_per_area'][fi],'post_flux_ratio_4_over_5':b['normalization']['post_flux_per_area'][fi]/a['normalization']['post_flux_per_area'][fi]})
  for oi,m in enumerate(range(-3,4)):
   for pol in range(2):modalrows.append({'anchor':anchor,'wavelength_nm':wl,'m':m,'polarization':['TE','TM'][pol],'real_5nm':c[fi,oi,pol].real,'imag_5nm':c[fi,oi,pol].imag,'real_4nm':p[fi,oi,pol].real,'imag_4nm':p[fi,oi,pol].imag,'amplitude_5nm':abs(c[fi,oi,pol]),'amplitude_4nm':abs(p[fi,oi,pol]),'phase_difference_rad':angle[fi,oi,pol],'significant':bool(mask[fi,oi,pol]),'complex_sse':sq[fi,oi,pol],'amplitude_sse':amp[fi,oi,pol],'phase_sse':phase[fi,oi,pol],'routing_5nm':a['eta'][fi,oi],'routing_4nm':b['eta'][fi,oi],'absolute_5nm':ae[fi,oi],'absolute_4nm':be[fi,oi]})
 summ[anchor]={'state_max':float(state.max()),'state_median':float(np.median(state)),'worst_wavelength_nm':int(440+state.argmax()),'routing_max':float(routing.max()),'absolute_max':float(absolute.max()),'power_max':float(power.max()),'phase_max':float(weighted.max()),'amplitude_sse_fraction':float(amp.sum()/sq.sum()),'phase_sse_fraction':float(phase.sum()/sq.sum()),'weak_sse_fraction':float(sq[~mask].sum()/sq.sum()),'order_error_fraction':(sq.sum(axis=(0,2))/sq.sum()).tolist(),'TM_error_fraction':float(sq[:,:,1].sum()/sq.sum()),'incident_ratio_range':[float((b['normalization']['pin_per_area']/a['normalization']['pin_per_area']).min()),float((b['normalization']['pin_per_area']/a['normalization']['pin_per_area']).max())]}
table('WAVELENGTH_ERROR.csv',rows);table('MODAL_AMPLITUDE_PHASE.csv',modalrows);dump('ERROR_SUMMARY.json',summ)
# Independent algebra tests, no synthetic fit.
mat,kz,p=basis(1,450,1);coeff=np.array([1+.2j,.5-.3j,.02+.01j,-.03j]);got=np.linalg.lstsq(mat,mat@coeff,rcond=None)[0];assert np.max(abs(got-coeff))<1e-12
assert abs(weights(np.linspace(-LX/2,LX/2,349)).sum()-LX)<1e-20
assert np.max(abs((abs((1+.3j)-(.4-.2j))**2)-((abs(1+.3j)-abs(.4-.2j))**2+2*abs(1+.3j)*abs(.4-.2j)*(1-np.cos(np.angle((1+.3j)*(.4+.2j)))))))<1e-12
assert all(sha(p)==s for p,s in guard.items());assert all(sha(p['path'])==p['sha256'] for p in pins)
dump('SOURCE_SHA_INVENTORY.json',pins);dump('TEST_AND_SCOPE_AUDIT.json',{'basis_recovery':'PASS','trapezoidal_endpoint':'PASS','amplitude_phase_identity':'PASS','pinned_input_hashes_unchanged':True,'ledger_registry_gate_unchanged':guard,'new_solver':0,'new_fit':0,'replay':0,'confirmation_access':0,'payload_scope':IDS,'baseline_scope':[b['case_id'] for b in BASE],'advancement':'HOLD','audit_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()})
print('SUMMARY',json.dumps(summ));print('PARITY',json.dumps(parity));print('DIFF_FIELDS',{k:[v['field'] for v in x['actual_setup_diff']] for k,x in contractdiff.items()})
