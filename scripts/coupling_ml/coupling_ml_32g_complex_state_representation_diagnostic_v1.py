"""Read-only scientific input analysis; CPU only, no solver/runner imports."""
import os,sys,json,hashlib,csv,importlib.util,datetime,subprocess
from pathlib import Path
os.environ['CUDA_VISIBLE_DEVICES']=''
os.environ['OMP_NUM_THREADS']='1';os.environ['OPENBLAS_NUM_THREADS']='1'
sys.dont_write_bytecode=True
import numpy as np
from sklearn.decomposition import PCA
R=Path(r'D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1')
TASK='COUPLING_ML_32G_COMPLEX_STATE_REPRESENTATION_DIAGNOSTIC_V1'
O=R/'reports/coupling'/TASK
A=R/'reports/coupling/PW_K6_STAGE1_32G_FROZEN_FORWARD_H1_V1'
B=R/'reports/coupling/COUPLING_ML_NP_FORWARD_FEATURE_ABLATION_32G_CONFIRMATORY_V2'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def write(p,j):
 t=Path(str(p)+'.tmp');t.write_text(json.dumps(j,indent=2,sort_keys=True,allow_nan=False)+'\n',encoding='utf-8');os.replace(t,p)
def req(ok,msg):
 if not ok:raise RuntimeError(msg)
def stats(x):
 x=np.asarray(x,float);return {'median':float(np.median(x)),'q95':float(np.quantile(x,.95)),'max':float(np.max(x))}
def csvwrite(p,rows):
 with p.open('w',encoding='utf-8',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def git(*args):return subprocess.run(['git','-C',str(R),*args],check=True,capture_output=True,text=True).stdout.strip()
def gauge(c):
 # Largest own amplitude, deterministic first-index ties. Carries anchor index.
 a=abs(c);flat=c.reshape(*c.shape[:-2],14);ix=np.argmax(abs(flat),axis=-1)
 anchor=np.take_along_axis(flat,ix[...,None],axis=-1)[...,0]
 common=np.angle(anchor);relative=np.angle(c*np.exp(-1j*common)[...,None,None])
 return a,common,relative,ix
def ungauge(a,p,q):return a*np.exp(1j*(p[...,None,None]+q))
def diagnose(t,p):
 a,b=abs(t),abs(p);den=np.sum(a*a);sse=np.sum(abs(p-t)**2)
 amp=np.sum((b-a)**2);phase=np.maximum(abs(p-t)**2-(b-a)**2,0)
 dp=np.angle(p*np.conj(t));weak=a<=.01*np.max(a,axis=(-2,-1),keepdims=True)
 z=np.sum(np.conj(p)*t,axis=(-2,-1));rot=np.exp(1j*np.angle(z));aligned=p*rot[...,None,None]
 # separate order alignment preserves TE/TM relationship within each order.
 zo=np.sum(np.conj(p)*t,axis=-1);po=p*np.exp(1j*np.angle(zo))[...,None]
 return {'state_relative_rmse':float(np.sqrt(sse/den)), 'amplitude_relative_rmse':float(np.sqrt(amp/den)),
 'amplitude_sse_fraction':float(amp/max(sse,1e-30)), 'phase_sse_fraction':float(np.sum(phase)/max(sse,1e-30)),
 'amplitude_weighted_phase_rmse_rad':float(np.sqrt(np.sum(a*a*dp*dp)/den)),
 'strong_phase_rmse_rad':float(np.sqrt(np.sum(a*a*dp*dp*(~weak))/max(np.sum(a*a*(~weak)),1e-30))),
 'weak_coordinate_fraction':float(np.mean(weak)), 'weak_truth_energy_fraction':float(np.sum(a*a*weak)/den),
 'weak_complex_sse_fraction':float(np.sum(abs(p-t)**2*weak)/max(sse,1e-30)),
 'oracle_common_aligned_rmse':float(np.sqrt(np.sum(abs(aligned-t)**2)/den)),
 'oracle_common_explained_sse_fraction':float(1-np.sum(abs(aligned-t)**2)/max(sse,1e-30)),
 'oracle_order_aligned_rmse':float(np.sqrt(np.sum(abs(po-t)**2)/den)),
 'oracle_cross_order_phase_extra_sse_fraction':float((np.sum(abs(aligned-t)**2)-np.sum(abs(po-t)**2))/max(sse,1e-30)),
 'TE_truth_energy_fraction':float(np.sum(a[...,0]**2)/den)}
def main():
 O.mkdir(parents=True,exist_ok=True)
 req(git('branch','--show-current')=='work/mdc-np-coupling-ml-v1','wrong branch')
 authority=read(A/'PW_K6_32G_DATASET_AUTHORITY_V1.json')
 inputs={}
 for base in [A,B]:
  manifest=read(base/'artifact_hashes.json')
  for n,v in manifest.items():
   if isinstance(v,dict) and 'sha256' in v:v=v['sha256']
   if (base/n).is_file() and isinstance(v,str) and len(v)==64:
    req(sha(base/n)==v,'artifact hash mismatch '+n);inputs[str((base/n).relative_to(R))]=v
 decoder=R/'scripts/shared_fdtd/tools/pw_complex_floquet_state_v1.py'
 req(sha(decoder)==authority['h2_decoder_sha256'],'H2 changed')
 gatepath=R/'reports/coupling/PW_K6_H1_NUMERIC_GATE_AUTHORITY_V1.json'
 req(sha(gatepath)==authority['h1_gate_sha256'],'H1 changed')
 inputs[str(decoder.relative_to(R))]=sha(decoder);inputs[str(gatepath.relative_to(R))]=sha(gatepath)
 folds=read(B/'fold_manifest_v2.json')['fold_assignments']['folds'];ids=authority['ordered_geometry_ids']
 req(len(folds)==32 and [f['test_geometry_id'] for f in folds]==ids,'fold identity')
 for f in folds:
  req(set(f['train_geometry_ids'])==set(ids)-{f['test_geometry_id']},'outer leakage')
  for sp in f['inner_group_folds']:
   req(not(set(sp['train_geometry_ids'])&set(sp['validation_geometry_ids'])) and f['test_geometry_id'] not in sp['train_geometry_ids']+sp['validation_geometry_ids'],'inner leakage')
 protocol={'task':TASK,'frozen_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'head':git('rev-parse','HEAD'),
 'scope':'integrated 3D periodic PW; fixed top MDC; 237 nm spacer; ordered K6; air; no bottom DBR; ZERO SOLVER',
 'inputs_sha256':inputs,'schema':'POSTNP +z, m=-3..3,y=0, TE/TM complex coordinates; C_hat plus independent P_scale; raw C_PW audited separately',
 'comparisons':['FULL archived M5 OOF seeds 0,1,2 and mean','445-455 archived paired A0/A1 seeds 0,1,2 and mean','polar/gauge reversible round trip','ORACLE DIAGNOSTIC local rank2 x7 vs joint rank14 train-fold PCA projection'],
 'weak_rule':'truth amplitude <= 1% of maximum coordinate amplitude within same geometry/wavelength; diagnostic only; no masking complex RMSE; report weak count/energy/SSE',
 'phase_rule':'principal circular angle(pred*conj(truth)); amplitude-squared weighting; zero truth weight zero; zero prediction phase undefined (reported count), no inferred phase information',
 'gauge_rule':'per wavelength anchor is largest own amplitude among 14 TE/TM coordinates, ties first flattened index; all-zero anchor phase=0; carry reference index; relative angles principal, reconstruction exp(i theta); no single-scalar order assumption',
 'oracle_rule':'common alignment from all 14 held-out truth coordinates, per wavelength; order alignment separately over TE/TM, diagnostic only; no H1/model claims',
 'pca_rule':'outer train only; local2 x7 and joint14 real coordinates same latent budget; held-out truth projection ORACLE DIAGNOSTIC; no latent predictor training, no selection',
 'folds':'32 geometry LOGO; same existing 3 grouped inner folds; seeds 0,1,2; no wavelength random splits',
 'metrics':'exact amplitude/phase SSE identity; weighted phase; common/order alignment; original H1 gates and threshold; geometry/wavelength/order rows',
 'tolerance':'absolute 1e-12 from existing packed-truth parity checks used for round trip and preservation; H2 Stage1 truth discrepancy <=.001 retained; no relaxation',
 'no_new_predictor':True,'no_solver':True}
 # Freeze before any new metrics; re-entry must retain identical protocol.
 protocol_path=O/'protocol.json'
 if protocol_path.exists():
  old=read(protocol_path);req(old['inputs_sha256']==inputs,'resume input change');protocol=old
 else:write(protocol_path,protocol)
 checkpoint={'task':TASK,'phase':'PROTOCOL_FROZEN','project_root':str(R),'canonical_root':r'D:\project\blue_apcd_microled_metasurface','host':'DESKTOP-NNE313K','user':'dell','transport':'NetBird SSH 100.81.105.58, same LAN use 192.168.1.107','branch':git('branch','--show-current'),'initial_head':protocol['head'],'authority_paths':[str(A),str(B),str(gatepath),str(decoder)],'protocol_sha256':sha(protocol_path),'boundary':'ZERO SOLVER; no Runner/reserve/HF/inverse; no truth/gate/H2 change','route':'fixed MDC reliable K6 -> variable MDC joint K6 -> multi-angle K4/K6/K9 -> sparse dipole certification','recovery_entry':'Read CONTINUATION.md then protocol.json and checkpoint.json before executing this script; existing inputs/predictions reused; no retraining','solver_invocations':0,'gpu_runner_invocations':0}
 write(O/'checkpoint.json',checkpoint)
 (O/'CONTINUATION.md').write_text('# '+TASK+'\n\nRecovery: read this file, checkpoint.json, protocol.json, then results.json and audit.json if present.\nFormal worktree: '+str(R)+'\nBranch: work/mdc-np-coupling-ml-v1\nHost/user: DESKTOP-NNE313K / dell; NetBird 100.81.105.58, LAN first 192.168.1.107. Reuse existing SSH authentication.\nCanonical root: D:\\project\\blue_apcd_microled_metasurface\n\nScientific route and authority paths are recorded in checkpoint.json. Fixed MDC K6 forward comes first. Never sort D1..D6. Current task is representation diagnosis only. ZERO SOLVER, no Runner/HF/reserves/inverse search. Preserve S35 FAILED_POSTENTRY and separate LOAD-only history; do not reopen historical 20G FSP forensics.\n\nResume script: scripts/coupling_ml/coupling_ml_32g_complex_state_representation_diagnostic_v1.py. It verifies input hashes and reuses archived OOF predictions. Protocol was saved before diagnostic computation. New fitted bases are outer-train-only; held-out latent projections and phase alignments are ORACLE DIAGNOSTIC. No new predictor or production admission.\n',encoding='utf-8')
 z=np.load(A/'dataset_truth_32g.npz');q=np.load(A/'oof_predictions_20g_32g.npz')
 req(z['C_hat'].shape==(32,21,7,2) and list(z['case_ids'])==ids,'truth schema')
 c=z['C_hat'];w=z['modal_weights'];pt=z['P_scale'];et=z['eta'];at=z['absolute_order_power']
 # Raw NPZ hashes and original physical scale retained, never substitute truth scale into model.
 raw=[];norm=[]
 for rec in authority['case_provenance']:
  p=Path(rec['state_path']);req(sha(p)==rec['state_sha256'],'state provenance '+rec['case_id']);inputs[str(p)]=sha(p)
  zz=np.load(p);ix=[list(map(tuple,zz['orders'].astype(int))).index((m,0)) for m in range(-3,4)]
  cc=np.take(zz['coefficients_real'][2],ix,axis=1)[:,:,0,:]+1j*np.take(zz['coefficients_imag'][2],ix,axis=1)[:,:,0,:]
  raw.append(cc)
 raw=np.array(raw);norm=np.sqrt(np.sum(w[...,None]*abs(raw)**2,axis=(-2,-1)))
 req(np.max(abs(raw/norm[...,None,None]-c))<=1e-12,'raw/C_hat parity')
 spec=importlib.util.spec_from_file_location('frozen_h2',decoder);h2=importlib.util.module_from_spec(spec);sys.modules[spec.name]=h2;spec.loader.exec_module(h2)
 mw=np.array([[[h2._mode(m,0,float(wl),1.,1,pol)['power_z_per_abs_e2'] for pol in ['TE','TM']] for m in range(-3,4)] for wl in range(440,461)])
 def decode(cp,ps,ws,mws):
  modal=ws[...,None]*abs(cp)**2;v=modal.sum(axis=-1);eta=v/np.maximum(v.sum(axis=-1,keepdims=True),1e-30)
  power=np.sum(mws[None,...]*abs(cp)**2,axis=(-2,-1));physical=cp*np.sqrt(ps/np.maximum(power,1e-30))[...,None,None]
  absolute=np.sum(mws[None,...]*abs(physical)**2,axis=-1)
  return eta,eta*ps[...,None],physical,absolute
 parity={}
 for label,arr in [('C_hat',c),('raw_C_PW',raw)]:
  ga=gauge(arr);back=ungauge(*ga[:3]);req(np.max(abs(arr-back))<=1e-12,'gauge parity')
  polar=abs(arr)*np.exp(1j*np.angle(arr));req(np.max(abs(arr-polar))<=1e-12,'polar parity')
  parity[label]={'gauge_max_abs':float(np.max(abs(back-arr))),'polar_max_abs':float(np.max(abs(polar-arr))),'reference_switch_count':int(np.sum(ga[3][:,1:]!=ga[3][:,:-1])),'zero_anchor_rows':int(np.sum(np.max(abs(arr),axis=(-2,-1))==0))}
 e0,a0,phys0,ap0=decode(c,pt,w,mw);e1,a1,phys1,ap1=decode(ungauge(*gauge(c)[:3]),pt,w,mw)
 preservation={'routing_max_abs':float(np.max(abs(e0-e1))),'absolute_max_abs':float(np.max(abs(a0-a1))),'total_max_abs':float(np.max(abs(a0.sum(-1)-a1.sum(-1)))),'mode_power_factorization_max_abs':float(np.max(abs(ap0-a0))),'existing_truth_routing_difference':float(np.max(abs(e0-et))), 'note':'reparameterization compared to original frozen H2 output; preexisting modal/grating discrepancy preserved, not forced to zero'}
 rawback=ungauge(*gauge(raw)[:3]);rawpower=np.sum(mw[None,...]*abs(raw)**2,axis=-1);rawbackpower=np.sum(mw[None,...]*abs(rawback)**2,axis=-1)
 preservation['raw_order_power_max_abs']=float(np.max(abs(rawpower-rawbackpower)))
 preservation['raw_total_power_max_abs']=float(np.max(abs(rawpower.sum(-1)-rawbackpower.sum(-1))))
 req(max(preservation[k] for k in ['raw_order_power_max_abs','raw_total_power_max_abs'])<=1e-12,'raw H2 preservation')
 req(max(preservation[k] for k in ['routing_max_abs','absolute_max_abs','total_max_abs','mode_power_factorization_max_abs'])<=1e-12,'H2 preservation')
 arms={'FULL':(c,q['32g_pred_c_hat_mean'],pt,q['32g_pred_pscale'],et,at,w,mw,range(440,461),q['32g_pred_c_hat_seed'])}
 with (B/'oof_predictions_v2.csv').open(encoding='utf-8',newline='') as f:rows=list(csv.DictReader(f))
 lookup={(r['case_id'],int(r['wavelength_nm']),int(r['order_x'])):r for r in rows}
 req(len(lookup)==2464,'paired unique rows')
 for arm in ['A0','A1']:
  cp=np.zeros((32,11,7,2),complex);ps=np.zeros((32,11));seed=np.zeros((3,32,11,7,2),complex)
  for g,cid in enumerate(ids):
   for l,wl in enumerate(range(445,456)):
    for o,m in enumerate(range(-3,4)):
     rr=lookup[cid,wl,m];ps[g,l]=float(rr[arm+'_P_scale'])
     for k,pol in enumerate(['TE','TM']):
      cp[g,l,o,k]=float(rr[arm+'_C_hat_mean_'+pol+'_re'])+1j*float(rr[arm+'_C_hat_mean_'+pol+'_im'])
      req(abs(c[g,l+5,o,k]-(float(rr['C_hat_true_'+pol+'_re'])+1j*float(rr['C_hat_true_'+pol+'_im'])))<=1e-12,'paired truth parity')
      for s in range(3):seed[s,g,l,o,k]=float(rr[f'{arm}_seed{s}_{pol}_re'])+1j*float(rr[f'{arm}_seed{s}_{pol}_im'])
  arms[arm]=(c[:,5:16],cp,pt[:,5:16],ps,et[:,5:16],at[:,5:16],w[:,5:16],mw[5:16],range(445,456),seed)
 results={};allgeom=[];detail=[];h1compare={};predraw={}
 threshold=read(gatepath)['chart_numeric_authority']['thresholded_absolute_order_relative']['significance_threshold']
 for arm,(ct,cp,ptrue,pp,etr,atr,ws,mws,wls,seeds) in arms.items():
  ep,ap,physical,physicalpowers=decode(cp,pp,ws,mws);predraw[arm]=physical
  diags=[];metrics=[]
  for g,cid in enumerate(ids):
   dg=diagnose(ct[g],cp[g]);dg.update({'arm':arm,'case_id':cid});diags.append(dg)
   mask=atr[g]>=threshold
   met={'state_relative_rmse':dg['state_relative_rmse'],'routing_eta_rmse':float(np.sqrt(np.mean((ep[g]-etr[g])**2))),'absolute_order_source_normalized_rmse':float(np.sqrt(np.mean((ap[g]-atr[g])**2))),'thresholded_absolute_order_relative_median':float(np.median(abs(ap[g][mask]-atr[g][mask])/atr[g][mask])),'total_power_relative_rmse':float(np.sqrt(np.mean(((pp[g]-ptrue[g])/ptrue[g])**2)))}
   metrics.append(met);allgeom.append({**dg,**met})
   for l,wl in enumerate(wls):
    for o,m in enumerate(range(-3,4)):
     dd=diagnose(ct[g,l:l+1,o:o+1],cp[g,l:l+1,o:o+1]) if arm else {}
     detail.append({'arm':arm,'case_id':cid,'wavelength_nm':wl,'order_x':m,'state_sse':float(np.sum(abs(cp[g,l,o]-ct[g,l,o])**2)),'amplitude_sse':float(np.sum((abs(cp[g,l,o])-abs(ct[g,l,o]))**2)),'phase_sse':float(np.sum(abs(cp[g,l,o]-ct[g,l,o])**2-(abs(cp[g,l,o])-abs(ct[g,l,o]))**2)),'truth_energy':float(np.sum(abs(ct[g,l,o])**2)),'routing_error':float(ep[g,l,o]-etr[g,l,o]),'absolute_order_error':float(ap[g,l,o]-atr[g,l,o]),'pscale_relative_error':float((pp[g,l]-ptrue[g,l])/ptrue[g,l])})
  summary={k:stats([v[k] for v in metrics]) for k in metrics[0]}
  corr=float(np.corrcoef(etr.ravel(),ep.ravel())[0,1]);pcorr=float(np.corrcoef(ptrue.ravel(),pp.ravel())[0,1])
  seedmed=[float(np.median([diagnose(ct[g],ss[g])['state_relative_rmse'] for g in range(32)])) for ss in seeds];sd=float(np.std(seedmed))
  lim=read(gatepath)['chart_numeric_authority'];gates={}
  for name,key,authoritykey in [('state','state_relative_rmse','state_relative_rmse'),('routing','routing_eta_rmse','routing_eta_rmse'),('absolute','absolute_order_source_normalized_rmse','absolute_order_source_normalized_rmse'),('threshold','thresholded_absolute_order_relative_median','thresholded_absolute_order_relative'),('pscale','total_power_relative_rmse','total_power_relative')]:
   limits=lim[authoritykey];gates[name]=summary[key]['median']<=limits['median_max'] and summary[key]['q95']<=limits['q95_max']
  gates['routing'] &= corr>=lim['routing_eta_rmse']['pearson_min'];gates['pscale'] &= pcorr>=lim['total_power_relative']['pearson_min'];gates['seed']=sd<=lim['seed_state_median_std_max']
  h1compare[arm]={'metrics':summary,'gates':gates,'H1':'PASS' if all(gates.values()) else 'FAIL','routing_pearson':corr,'pscale_pearson':pcorr,'seed_medians':seedmed,'seed_std':sd,'production':'NOT_ADMITTED'}
  archived=read(A/'PW_K6_FROZEN_FORWARD_H1_32G_V1.json') if arm=='FULL' else read(B/'paired_ablation_metrics_v2.json')['arms'][arm]
  for k in summary:
   for sk in ['median','q95','max']:req(abs(summary[k][sk]-archived['metrics'][k][sk] if arm=='FULL' else summary[k][sk]-archived[k][sk])<=1e-12,'archived metric parity '+arm+k)
  results[arm]={'aggregate':diagnose(ct,cp),'geometry_summary':{k:stats([d[k] for d in diags]) for k in diags[0] if k not in ['arm','case_id']},'seed_diagnostics':[diagnose(ct,ss) for ss in seeds],'zero_prediction_coordinates':int(np.sum(abs(cp)==0)), 'physical_C_PW_diagnostic':diagnose(raw if arm=='FULL' else raw[:,5:16],physical),'physical_reconstruction_power_max_abs':float(np.max(abs(physicalpowers-ap)))}
 csvwrite(O/'per_geometry.csv',allgeom);csvwrite(O/'geometry_wavelength_order.csv',detail)
 # Equal rank14 local-vs-joint oracle projection; no learned held-out path.
 pcarows=[];localfloors=[];scoreerrors=[];crosses=[]
 def pack(v):return np.stack([v.real,v.imag],axis=-1).reshape(len(v),-1)
 def unpack(v,shape):v=v.reshape(*shape,2);return v[...,0]+1j*v[...,1]
 for g,cid in enumerate(ids):
  tr=[i for i in range(32) if i!=g];local=np.zeros_like(c[g:g+1]);joint=None
  for o in range(7):
   pc=PCA(n_components=2,svd_solver='full').fit(pack(c[tr,:,o,:]));local[:,:,o,:]=unpack(pc.inverse_transform(pc.transform(pack(c[g:g+1,:,o,:]))),(1,21,2))
  pc=PCA(n_components=14,svd_solver='full').fit(pack(c[tr]));joint=unpack(pc.inverse_transform(pc.transform(pack(c[g:g+1]))),(1,21,7,2))
  floor=c[g:g+1]-local;score=arms['FULL'][1][g:g+1]-local
  localfloors.append(float(np.sum(abs(floor)**2)));scoreerrors.append(float(np.sum(abs(score)**2)));crosses.append(float(abs(2*np.real(np.sum(np.conj(floor)*score)))))
  pcarows.append({'case_id':cid,'local_rank2x7_oracle_rmse':diagnose(c[g:g+1],local)['state_relative_rmse'],'joint_rank14_oracle_rmse':diagnose(c[g:g+1],joint)['state_relative_rmse'],'local_truncation_sse':localfloors[-1],'in_basis_prediction_sse':scoreerrors[-1],'orthogonality_cross_term_abs':crosses[-1]})
 csvwrite(O/'train_fold_pca_oracle.csv',pcarows)
 order=[]
 for o,m in enumerate(range(-3,4)):
  d=diagnose(c[:,:,o:o+1,:],arms['FULL'][1][:,:,o:o+1,:]);order.append({'order_x':m,**d})
 csvwrite(O/'order_local_diagnostics.csv',order)
 npattr={k:{'median_A1_minus_A0':float(np.median([allgeom[64+i][k]-allgeom[32+i][k] for i in range(32)])),'wins':int(sum(allgeom[64+i][k]<allgeom[32+i][k] for i in range(32)))} for k in ['state_relative_rmse','amplitude_relative_rmse','amplitude_weighted_phase_rmse_rad','routing_eta_rmse','absolute_order_source_normalized_rmse','total_power_relative_rmse']}
 tails={cid:{arm:next(v for v in allgeom if v['case_id']==cid and v['arm']==arm) for arm in arms} for cid in ['K6V1_S31','K6V1_S33','K6V1_EXT08']}
 fullsse=float(np.sum(abs(arms['FULL'][1]-c)**2))
 decomposition={'label':'ORACLE DIAGNOSTIC orthogonal error accounting; no oracle predictor','local_truncation_sse_fraction':sum(localfloors)/fullsse,'in_basis_prediction_sse_fraction':sum(scoreerrors)/fullsse,'max_cross_term_abs':max(crosses)}
 req(abs(sum(localfloors)+sum(scoreerrors)-fullsse)<=1e-10,'PCA orthogonal decomposition')
 result={'status':'COMPLETE_ZERO_SOLVER_DIAGNOSTIC','dataset':{'geometries':32,'full_rows':672,'full_order_rows':4704,'paired_rows':352,'paired_order_rows':2464,'components':'TE/TM, no Jones operator claim'},'arms':results,'h1':h1compare,'reconstruction_parity':parity,'h2_preservation':preservation,'order_local_vs_joint':{'label':'ORACLE DIAGNOSTIC; no held-out prediction claim','local':stats([v['local_rank2x7_oracle_rmse'] for v in pcarows]),'joint':stats([v['joint_rank14_oracle_rmse'] for v in pcarows]),'error_accounting':decomposition},'NP_attribution_445_455':npattr,'tails':tails,'solver_invocations':0,'runner_invocations':0,'new_HF':0,'retraining':False}
 write(O/'results.json',result)
 audit={'status':'PASS','input_hashes':inputs,'protocol_sha256':sha(protocol_path),'protocol_frozen_before_new_metrics':True,'fold_count':32,'seeds':[0,1,2],'no_preprocessing_fit_on_test':True,'pca_oracle_projection_explicit':True,'no_new_predictor_or_H1_admission':True,'no_truth_scale_in_prediction':True,'support_distance_training_input':False,'round_trip':'PASS','H2_preservation':'PASS','original_H1_metric_parity':'PASS <=1e-12','S35_history':'FAILED_POSTENTRY + independent LOAD-only recovery preserved','historical_20g_limitation':authority['historical_20g_artifact_provenance_limitation'],'ZERO_SOLVER':True,'solver_invocations':0,'runner_invocations':0}
 write(O/'audit.json',audit)
 checkpoint.update({'phase':'ANALYSIS_AND_AUDIT_COMPLETE','completed_artifacts':['results.json','audit.json','per_geometry.csv','geometry_wavelength_order.csv','train_fold_pca_oracle.csv','order_local_diagnostics.csv'],'next':'scientific review; no automatic proposed experiment'});write(O/'checkpoint.json',checkpoint)
 print(json.dumps({'arms':{k:v['aggregate'] for k,v in results.items()},'pca':result['order_local_vs_joint'],'NP':npattr,'parity':parity,'preservation':preservation},indent=2))
if __name__=='__main__':main()
