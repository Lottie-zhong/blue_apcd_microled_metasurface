"""One deterministic train-only 1-NN phase transfer; no estimator fitting."""
from pathlib import Path
import sys,json,hashlib,datetime,subprocess,csv
import numpy as np
from scipy.stats import spearmanr
from k6_v2_pipeline.amended156 import adapter as A,evaluation as V
from k6_v2_pipeline import h1,contracts as C
ROOT=A.ROOT;TASK='COUPLING_ML_GEOMETRY_NEAREST_NEIGHBOR_PHASE_TRANSFER_AUDIT_V1';OUT=ROOT/'reports/coupling'/TASK
OLD=ROOT/'reports/coupling/COUPLING_ML_FULL_RANK_AMPLITUDE_CIRCULAR_PHASE_KRR_PILOT_V1'
LAST=ROOT/'reports/coupling/COUPLING_ML_LOCAL_SCALE_CIRCULAR_PHASE_KRR_PILOT_V1'
sys.path.insert(0,str(OLD));import structured_phase_pilot as S
D=S.D
def req(v,m):
    if not v:raise ValueError(m)
def jsonable(v):
    if isinstance(v,dict):return {k:jsonable(x) for k,x in v.items()}
    if isinstance(v,(list,tuple)):return [jsonable(x) for x in v]
    if isinstance(v,np.ndarray):return jsonable(v.tolist())
    if isinstance(v,np.generic):return v.item()
    return v
def put(n,v):A.write(OUT/n,jsonable(v))
def stats(x):
    a=np.asarray(x,float).reshape(-1);a=a[np.isfinite(a)];return V.summary(a) if len(a) else {'median':None,'q95':None,'mean':None,'worst':None}
def neighbor(train_ids,train_x,query_x):
    req(len(train_ids)==len(set(train_ids)) and len(train_ids)>0,'train_identity')
    x=np.asarray(train_x,float);q=np.asarray(query_x,float);req(x.shape==(len(train_ids),6) and q.ndim==2 and q.shape[1]==6 and np.isfinite(x).all() and np.isfinite(q).all(),'geometry_shape_or_finite')
    # Formal coordinates use the same130nm span; integer-lattice squared distances preserve exact ties.
    req(np.equal(x,np.rint(x)).all() and np.equal(q,np.rint(q)).all(),'formal_integer_grid')
    order=sorted(range(len(train_ids)),key=lambda j:train_ids[j]);xx=x[order].astype(np.int64);qq=q.astype(np.int64)
    raw2=((qq[:,None]-xx[None])**2).sum(-1);nn=raw2.argmin(1)
    return [train_ids[order[j]] for j in nn],np.sqrt(raw2[np.arange(len(q)),nn])/130.,np.sqrt(raw2[np.arange(len(q)),nn]),(raw2==raw2.min(1)[:,None]).sum(1)
def phase(c):
    a,u=D.unit(c);f=a*a/(a*a).sum((-2,-1),keepdims=True);mask=(f>=1e-4)&(a>0);return np.where(mask,u,1.+0j),mask,f
def tests():
    ids=['Z','A'];x=np.array([[105,100,100,100,100,100],[100,105,100,100,100,100]]);q=np.array([[100]*6]);n,d,r,t=neighbor(ids,x,q);req(n==['A'] and t[0]==2 and r[0]==5,'lexical_tie');n2,*_=neighbor(ids[::-1],x[::-1],q);req(n2==n,'enumeration_invariance')
    c=np.ones((2,21,7,2),complex);c[...,0]=0;u,m,f=phase(c);req(np.all(u[...,0]==1) and not m[...,0].any(),'zero_phase_rule');c[0,0,0,1]=1e-8j;u,m,f=phase(c);req(u[0,0,0,1]==1 and not m[0,0,0,1],'weak_rule_train_only')
    z=np.exp(1j*np.array([np.pi-1e-9,-np.pi+1e-9]));req(abs(np.angle(z[1]*z[0].conj()))<3e-9,'wrapping')
    a=np.ones((2,21,7,2));p=np.ones((2,21));dec=h1.load_h2_decoder();b=h1.reconstruct_h2(a.astype(complex),p,dec);e=h1.reconstruct_h2(a*np.exp(1j*np.arange(294).reshape(21,7,2)),p,dec);req(max(abs(b[k]-e[k]).max() for k in ['eta','absolute_order','total_power'])<1e-12,'phase_only_H2')
    try:neighbor(['A','A'],x,q)
    except ValueError:pass
    else:raise ValueError('duplicate_must_reject')
    req(not any(isinstance(n, __import__('ast').Call) and isinstance(n.func,__import__('ast').Attribute) and n.func.attr in ['fit','fit_transform'] for n in __import__('ast').walk(__import__('ast').parse(Path(__file__).read_text(encoding='utf-8')))),'fit_call_forbidden')
    return {'status':'PASS','checks':8,'estimator_fits':0,'scope':'tie, permutation, weak/zero phase, wrap, H2 preservation, duplicate rejection, no fit AST'}
def freeze():
    OUT.mkdir(parents=True,exist_ok=True);req(not (OUT/'NEAREST_NEIGHBOR_PHASE_SPEC.json').exists(),'already_preregistered')
    req(subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()=='a1a28c3b212661e8964fdde8057dd86291a295a5','HEAD_review_required')
    pins={}
    for base in [LAST,OLD,A.OUT,S.NP.OUT,S.AUDIT]:
        p=base/'SHA_INVENTORY.json'
        for f in A.read(p)['files']:req(A.sha(f['path'])==f['sha256'],'input_hash:'+f['path']);pins[f['path']]=f['sha256']
        pins[str(p)]=A.sha(p)
    dom=ROOT/'reports/coupling/PW_K6_GEOMETRY_DOMAIN_AUTHORITY_V1.json';v=A.read(dom);req(v['geometry_grammar']['observed_bounds_nm']==[100,230] and v['geometry_grammar']['grid_step_nm']==5 and '/130.0' in v['distance_convention'],'geometry_range');pins[str(dom)]=A.sha(dom)
    pins[str(A.CLOSURE/'DEVELOPMENT_156G_DATASET_INVENTORY.json')]=A.INVENTORY_SHA
    put('NEAREST_NEIGHBOR_PHASE_SPEC.json',{'task':TASK,'utc_before_calculation':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_HEAD':'a1a28c3b212661e8964fdde8057dd86291a295a5','code_sha256':A.sha(Path(__file__)),'protected_files':[{'path':p,'sha256':s} for p,s in sorted(pins.items())],'foreign_index_sha256':hashlib.sha256(subprocess.check_output(['git','diff','--cached','--binary'],cwd=ROOT)).hexdigest(),'ordered_input':'D1..D6 no sorting/cyclic augmentation','geometry_scale':'(D-100)/130 for each coordinate; squared raw integer nm distance first; exact equal-distance tie lexical caseID','neighbors':'one nearest in corresponding outer124 train only; all train21wavelengths remain grouped; no querytruth in selection','phase_rule':'neighbor training energy fraction |c|²/sum14|c|²>=1e-4 and amplitude>0: c/abs(c); otherwise unit1. Same weak canonical targets asB, no querytruth or tunable threshold. WeakTE retained.','output':'21lambda x7orders(-3..3) x2TE/TM complex;294complex=588Cartesian+21positivePscale','reference_nm':1722,'input_polarization':'P_XLIKE, not complete incoming Jones operator','amplitude':'frozen C amplitude_head, verified identical B; P_scale sameOOF source; no new normalization or clipping','tolerance_H2_abs':1e-12,'distance_bins':[0,.1,.25,.5,'infinity'],'evaluation_phase_mask':'heldouttruth coordinate energy fraction>=1e-4, truth-amplitude² weights; evaluation only, not inference; sensitivities1e-6,1e-5,1e-4,1e-3,1e-2','comparison':'A/B/C original untouched; D fixed1NN; wins/loss tolerance1e-12. No selection amongst additional methods','next_decision':'A only if localized consistent evidence inclstate/phase wins and supported density; B if full-range neighbor evidence fails but coherent modal relation evidence supports physics direction; C if no defensible phase experiment. One recommendation, no execution','execution_counts':{'CPU_fits':0,'P_scale_fits':0,'FDTD':0,'replay':0,'confirmation_response_access':0},'development_only':True})
    put('SYNTHETIC_CHECKS.json',tests());print('PREREGISTERED_ZERO_FIT',flush=True)
def check():
    p=A.read(OUT/'NEAREST_NEIGHBOR_PHASE_SPEC.json');req(A.sha(Path(__file__))==p['code_sha256'],'code_changed')
    for q in p['protected_files']:req(A.sha(q['path'])==q['sha256'],'protected_changed:'+q['path'])
    return p
def evaluate():
    prot=check();col=A.load_collection(False);req(len(col.cases)==156,'156count');by={c.case_id:c for c in col.cases};meta={x['case_id']:x for x in A.inventory()['cases']};folds=A.read(LAST/'FOUR_FOLD_FIT_MANIFEST.json')['folds'];ids=sum([f['heldout_case_ids'] for f in folds],[]);req(len(ids)==len(set(ids))==124,'124_uniqueOOF');preds={};pps={}
    for arm,p in [('A',OLD/'A_OOF_PREDICTIONS.npz'),('B',OLD/'B_OOF_PREDICTIONS.npz'),('C',LAST/'C_OOF_PREDICTIONS.npz')]:
        with np.load(p,allow_pickle=False) as z:
            req(z['case_ids'].tolist()==ids,'OOF_alignment');preds[arm]=z['C_hat_real']+1j*z['C_hat_imag'];pps[arm]=z['P_scale'].copy()
            if arm=='C':amp=z['amplitude_head'].copy()
    req(np.array_equal(pps['A'],pps['B']) and np.array_equal(pps['B'],pps['C']),'P_scale_match');pp=pps['B'];rows=[];units=[];leak=[]
    for f in folds:
        tr=f['train_case_ids'];ho=f['heldout_case_ids'];req(len(tr)==124 and not set(tr)&set(ho) and (set(tr)|set(ho)).issubset(set(by)),'outer_identity_or_leakage');tx=np.array([by[i].ordered_D_nm for i in tr]);qx=np.array([by[i].ordered_D_nm for i in ho]);nn,nd,rd,ties=neighbor(tr,tx,qx)
        pu,reliable,frac=phase(np.array([by[n].c_hat for n in nn]));units.append(pu)
        # Saved C amplitude values were already checked elementwise against B. Recompute only the old predictor, never fit.
        import joblib
        payload=joblib.load(OLD/'models'/f['task_id']/'model.joblib');b,inf=S.save_prediction(payload,qx);ix=[ids.index(i) for i in ho];req(np.array_equal(inf['amplitude'],amp[ix]) and np.array_equal(b,preds['B'][ix]),'amplitude_or_B_checkpoint_mismatch')
        for k,i in enumerate(ho):
            req(nn[k] in tr and nn[k] not in ho and nn[k]!=i,'neighbor_leak')
            rows.append({'case_id':i,'fold':f['fold'],'ordered_D_nm':list(by[i].ordered_D_nm),'role':by[i].role,'stratum':meta[i]['stratum'],'nearest_train_case':nn[k],'neighbor_ordered_D_nm':list(by[nn[k]].ordered_D_nm),'neighbor_role':by[nn[k]].role,'normalized_distance':float(nd[k]),'raw_distance_nm':float(rd[k]),'tie_count':int(ties[k]),'weak_or_zero_coordinates':int((~reliable[k]).sum()),'weak_or_zero_training_energy_fraction':float((frac[k]*(~reliable[k])).sum()/21),'neighbor_truth_provenance':meta[nn[k]]})
        leak.append({'fold':f['fold'],'train_count':len(tr),'heldout_count':len(ho),'train_ids':tr,'heldout_ids':ho,'no_intersection':True,'outer_pool_not_selected':sorted(set(by)-set(tr)-set(ho)),'all_neighbors_in_train':True,'train_old32_count':sum(i.startswith('K6V1_') for i in tr),'query_truth_used_for_neighbor_selection':False,'source_manifest_sha256':A.sha(LAST/'FOUR_FOLD_FIT_MANIFEST.json')})
    preds['D']=amp*np.concatenate(units);np.savez_compressed(OUT/'D_OOF_PREDICTIONS.npz',case_ids=np.array(ids),C_hat_real=preds['D'].real,C_hat_imag=preds['D'].imag,P_scale=pp,amplitude_head=amp,transferred_phase=np.concatenate(units),nearest_train_case=np.array([r['nearest_train_case'] for r in rows]))
    ct=np.array([by[i].c_hat for i in ids]);pt=np.array([by[i].p_scale for i in ids]);et=np.array([by[i].eta for i in ids]);at=np.array([by[i].absolute_order for i in ids]);dec=h1.load_h2_decoder();reports={};per={};modal={};hs={};decomp={};sq=abs(ct)**2;den=sq.sum((1,2,3));frac=sq/sq.sum((2,3),keepdims=True)
    for arm,cp in preds.items():
        reports[arm]=h1.evaluate_original_h1(ct,cp,pt,pp,et,at,dec);hs[arm]=h1.reconstruct_h2(cp,pp,dec);angles=D.angular_stats(ct,cp,1e-4);am,ph,err,delta=D.error_decomposition(ct,cp);per[arm]={k:np.array([r[k] for r in reports[arm]['aggregate']['per_geometry']]) for k in reports[arm]['aggregate']['per_geometry'][0]};per[arm].update(amplitude_relative_rmse=np.sqrt(am.sum((1,2,3))/den),absolute_phase_rmse=np.array(angles['per_geometry_absolute']),relative_phase_rmse=np.array(angles['per_geometry_relative']),norm_ratio=np.sqrt((abs(cp)**2).sum((1,2,3))/den),nonzero_state_rmse=np.sqrt(err[:,:,[0,1,2,4,5,6]].sum((1,2,3))/sq[:,:,[0,1,2,4,5,6]].sum((1,2,3))))
        decomp[arm]={'amplitude_SSE':float(am.sum()),'phase_SSE':float(ph.sum()),'phase_fraction':float(ph.sum()/err.sum()),'angular':angles,'threshold_sensitivity':{str(th):D.angular_stats(ct,cp,th) for th in [1e-6,1e-5,1e-4,1e-3,1e-2]}};modal[arm]=[]
        for j in range(7):
            w=sq[:,:,j,1]*(frac[:,:,j,1]>=1e-4);pr=np.sqrt((w*np.angle(cp[:,:,j,1]*ct[:,:,j,1].conj())**2).sum(1)/w.sum(1));st=np.sqrt(err[:,:,j,:].sum((1,2))/sq[:,:,j,:].sum((1,2)));modal[arm].append({'m':j-3,'strong_TM_phase_rmse':stats(pr),'order_state_rmse':stats(st),'per_geometry':[{'case_id':i,'phase':float(pr[k]),'state':float(st[k])} for k,i in enumerate(ids)]})
    previous=A.read(LAST/'H1_H2_EVALUATION.json')['reports'];req(all(reports[k]==previous[k] for k in 'ABC'),'ABC_formal_H1_parity')
    hdiff={a:{k:float(abs(hs['D'][k]-hs[a][k]).max()) for k in ['eta','absolute_order','total_power']} for a in ['B','C']};req(max(v for q in hdiff.values() for v in q.values())<=1e-12,'H2_changed');absdiff=float(abs(abs(preds['D'])-amp).max());req(absdiff<=1e-12,'amplitude_changed')
    paired={}
    for metric in per['A']:
        pairs={}
        for a in 'ABC':
            dd=per['D'][metric]-per[a][metric];rr=[{'case_id':i,'fold':rows[k]['fold'],'A_or_B_or_C':float(per[a][metric][k]),'D':float(per['D'][metric][k]),'delta':float(dd[k])} for k,i in enumerate(ids)];pairs['D_minus_'+a]={'delta':stats(dd),'wins':int((dd< -1e-12).sum()),'losses':int((dd>1e-12).sum()),'ties':int((abs(dd)<=1e-12).sum()),'rows':rr,'worst10':sorted(rr,key=lambda x:x['delta'],reverse=True)[:10],'folds':{str(f['fold']):{'delta':stats([dd[ids.index(i)] for i in f['heldout_case_ids']]),'wins':sum(dd[ids.index(i)]< -1e-12 for i in f['heldout_case_ids']),'losses':sum(dd[ids.index(i)]>1e-12 for i in f['heldout_case_ids'])} for f in folds}}
        paired[metric]={**{arm:stats(per[arm][metric]) for arm in 'ABCD'},'paired':pairs}
    for k,r in enumerate(rows):
        r.update(state_error=float(per['D']['state_relative_rmse'][k]),phase_error=float(per['D']['absolute_phase_rmse'][k]),state_D_minus_A=float(per['D']['state_relative_rmse'][k]-per['A']['state_relative_rmse'][k]),phase_D_minus_B=float(per['D']['absolute_phase_rmse'][k]-per['B']['absolute_phase_rmse'][k]),distance_bin='<=0.1' if r['normalized_distance']<=.1 else ('(0.1,0.25]' if r['normalized_distance']<=.25 else ('(0.25,0.5]' if r['normalized_distance']<=.5 else '>0.5')))
    groups={};assoc={}
    selectors=[(b,[k for k,r in enumerate(rows) if r['distance_bin']==b]) for b in ['<=0.1','(0.1,0.25]','(0.25,0.5]','>0.5']]+[(s,[k for k,r in enumerate(rows) if r['stratum']==s]) for s in sorted(set(r['stratum'] for r in rows))]+[('LOCAL_AXIS',[k for k,r in enumerate(rows) if r['role']==C.ROLE_LOCAL_AXIS]),('GLOBAL',[k for k,r in enumerate(rows) if r['role']==C.ROLE_GLOBAL_DEV]),('ALL',list(range(124)))]
    for name,ix in selectors:
        groups[name]={'n':len(ix),'distance':stats([rows[k]['normalized_distance'] for k in ix]),'state':{a:stats(per[a]['state_relative_rmse'][ix]) for a in 'ABCD'},'phase':{a:stats(per[a]['absolute_phase_rmse'][ix]) for a in 'ABCD'},'state_D_minus_A':stats(per['D']['state_relative_rmse'][ix]-per['A']['state_relative_rmse'][ix])}
        if len(ix)>=3 and np.ptp([rows[k]['normalized_distance'] for k in ix])>1e-12:
            assoc[name]={m:float(spearmanr([rows[k]['normalized_distance'] for k in ix],per['D'][m][ix]).statistic) for m in ['state_relative_rmse','absolute_phase_rmse']}
    put('FOUR_FOLD_LEAKAGE_AUDIT.json',{'status':'PASS','folds':leak,'156_development':156,'OOF_unique':124,'old32_train_only':True,'confirmation_response_access':0});put('TRAIN_ONLY_NEIGHBOR_PROVENANCE.json',{'rows':rows,'tie_cases':sum(r['tie_count']>1 for r in rows),'weak_coordinates':sum(r['weak_or_zero_coordinates'] for r in rows),'inference_truth_source':'only neighbor outertrain labels; heldouttruth used only after prediction for evaluation'})
    put('FOUR_MODEL_PAIRED_RESULTS.json',paired);put('MODAL_PHASE_DISTANCE_ANALYSIS.json',{'modal':modal,'distance_groups':groups,'spearman_descriptive':assoc,'decomposition':decomp,'causality':'No causal or truephysical nonlocality proof; sparse globalneighbors and oneS31cluster confound pooledcorrelation'})
    put('LOCAL_GEOMETRY_COVERAGE.json',{'local':groups['LOCAL_AXIS'],'rows':[r for r in rows if r['role']==C.ROLE_LOCAL_AXIS],'global':groups['GLOBAL'],'missing':'K6LDA1_DEV_D6_M05','repeatability':'unverified +/-5nm crossrun numericalfloor; twoairplanes supports onecaseheightconsistency only'})
    put('H1_H2_DIAGNOSTIC.json',{'reports':reports,'ABC_formal_scores_exact':True,'P_scale_elementwise_identical':True,'amplitude_head_elementwise_identical':True,'complex_abs_vs_amplitude_head_max':absdiff,'H2_D_vs_B_C_max':hdiff,'seed_stability':'N/A deterministic KRR; not PASS','reference_nm':1722,'oracle_alignment':False})
    with (OUT/'FOUR_MODEL_PER_GEOMETRY.csv').open('w',encoding='utf-8',newline='') as f:
        keys=['case_id','fold','role','stratum','nearest_train_case','normalized_distance','raw_distance_nm'];metrics=list(per['A']);w=csv.DictWriter(f,fieldnames=keys+[a+'_'+m for a in 'ABCD' for m in metrics],lineterminator='\n');w.writeheader()
        for k,r in enumerate(rows):w.writerow({**{v:r[v] for v in keys},**{a+'_'+m:float(per[a][m][k]) for a in 'ABCD' for m in metrics}})
    check();put('FINAL_ISOLATION_CHECK.json',{'status':'PASS','execution_counts':prot['execution_counts'],'original_inputs_verified_unchanged':True,'confirmation_28_forecast_SHA_unchanged':True,'actual_test_fits':0,'ABC_H1_parity':True,'H2_preservation':True,'no_full156_neighbor_search':True});print('RESULTS',json.dumps({k:{a:paired[k][a] for a in 'ABCD'} for k in ['state_relative_rmse','absolute_phase_rmse','nonzero_state_rmse','routing_eta_rmse']}),flush=True);print('GROUPS',json.dumps(groups),flush=True);print('ASSOCIATIONS',json.dumps(assoc),flush=True)
if __name__=='__main__':
    if sys.argv[1]=='freeze':freeze()
    elif sys.argv[1]=='evaluate':evaluate()
    else:raise ValueError('unknown mode')
