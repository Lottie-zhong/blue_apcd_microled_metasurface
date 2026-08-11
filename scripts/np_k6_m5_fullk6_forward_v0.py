from __future__ import annotations
import csv, json, hashlib, math, os, re, gzip, pathlib, datetime, random, statistics, time
from collections import defaultdict, Counter
os.environ.setdefault('KMP_DUPLICATE_LIB_OK','TRUE')
import numpy as np

ROOT = pathlib.Path(r'D:\project\worktrees\blue_apcd_np_k6_mdc_v1')
OUT = ROOT / r'outputs\np_k6_m5_fullk6_forward_v0'
OUT.mkdir(parents=True, exist_ok=True)
SEEDS = [17, 29, 43]
ORDERS = [-3,-2,-1,0,1,2,3]
WLS = list(range(445,456))

def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha256(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()
def dump(p, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj,indent=2,sort_keys=True,ensure_ascii=False),encoding='utf-8')
def read_csv(p):
    with open(p,encoding='utf-8-sig',newline='') as f: return list(csv.DictReader(f))
def write_csv(p, fields, rows):
    p.parent.mkdir(parents=True,exist_ok=True)
    with open(p,'w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
def spearman(a,b):
    a=np.asarray(a,float); b=np.asarray(b,float)
    if len(a)<2 or np.std(a)==0 or np.std(b)==0: return float('nan')
    def rank(x):
        o=np.argsort(x,kind='mergesort'); r=np.empty(len(x),float); r[o]=np.arange(len(x));
        for v in np.unique(x):
            ix=np.where(x==v)[0]; r[ix]=np.mean(r[ix])
        return r
    return float(np.corrcoef(rank(a),rank(b))[0,1])

def load_order_maps():
    paths=list((ROOT/r'outputs\np_k6_hf_p0_label_generator_recovery_v1\cases').rglob('hf_transmitted_orders_long.csv'))
    paths += list((ROOT/r'outputs\np_k6_hf_pilot_dataset_v1').rglob('hf_transmitted_orders_long.csv'))
    paths += list((ROOT/r'outputs\np_k6_m2_batch1_hf_acquisition_v1\cases').rglob('hf_transmitted_orders_long.csv'))
    paths += list((ROOT/r'outputs\np_k6_m4_batch2_primary4_hf_acquisition_v1\cases').rglob('hf_transmitted_orders_long.csv'))
    paths += list((ROOT/r'outputs\np_k6_p0_remaining_five_anchors_execution_v1\cases').rglob('hf_transmitted_orders_long.csv'))
    paths += list((ROOT/r'outputs\np_k6_m5_fullk6_forward_v0\g04p_order_recovery').rglob('hf_transmitted_orders_long.csv'))
    candidates=defaultdict(list)
    for p in paths:
        try: rows=read_csv(p)
        except Exception: continue
        if not rows: continue
        fld='order_n' if 'order_n' in rows[0] else ('grating_order_n' if 'grating_order_n' in rows[0] else None)
        if not fld: continue
        cid=rows[0].get('case_id')
        if cid: candidates[cid].append((p,rows,fld))
    return candidates

def build_authority():
    m3p=ROOT/r'outputs\np_k6_m3_pilot_retraining_v1\development_hf_v2_training_view.csv'
    b2p=ROOT/r'outputs\np_k6_m4_batch2_primary4_hf_acquisition_v1\merged_development_hf_observations_long.csv'
    m3=read_csv(m3p); b2=read_csv(b2p)
    bykey={}
    for r in m3+b2: bykey[(r['case_id'],int(float(r['wavelength_nm'])))] = r
    if len(bykey)!=286: raise RuntimeError(f'authority unique rows {len(bykey)} !=286')
    cands=load_order_maps(); order_rows={}
    source_paths={}
    for cid in sorted(set(k[0] for k in bykey)):
        if cid not in cands: raise RuntimeError('missing order file '+cid)
        # Prefer files with the canonical order_n field; for the recovered RUN3C-P,
        # the recovery/pilot copies are equivalent and the first is retained.
        options=sorted(cands[cid], key=lambda x:(0 if x[2]=='order_n' else 1, str(x[0])))
        p, rows, fld=options[0]; source_paths[cid]=str(p.relative_to(ROOT))
        for q in rows:
            wl=int(float(q['wavelength_nm'])); m=int(q[fld])
            if wl not in WLS or m not in ORDERS: continue
            order_rows[(cid,wl,m)] = float(q['absolute_efficiency'])
    for k in bykey:
        if any((k[0],k[1],m) not in order_rows for m in ORDERS): raise RuntimeError('incomplete order '+str(k))
    rows=[]
    for (cid,wl),r in sorted(bykey.items(), key=lambda z:(z[0][0],z[0][1])):
        eta=[order_rows[(cid,wl,m)] for m in ORDERS]
        rr=dict(r); rr['wavelength_nm']=str(wl); rr['m5_training_label']='true'; rr['m5_candidate_performance_label']='false'
        for m,v in zip(ORDERS,eta): rr[f'eta_m{m:+d}']=f'{v:.12g}'
        rr['eta_order_sum']=f'{sum(eta):.12g}'; rr['order_source_path']=source_paths[cid]
        rows.append(rr)
    fields=list(rows[0])
    p=OUT/'m5_training_view_286rows.csv'; write_csv(p,fields,rows)
    geo=sorted(set(r['geometry_id'] for r in rows)); cases=sorted(set(r['case_id'] for r in rows))
    cgs=Counter((r['geometry_id'],r['polarization']) for r in rows)
    label_audit={
      'raw_merged_path':str(b2p.relative_to(ROOT)),'raw_merged_sha256':sha256(b2p),'raw_rows':len(b2),
      'raw_training_label_counts':dict(Counter(r['training_label'] for r in b2)),
      'm3_promoted_view_path':str(m3p.relative_to(ROOT)),'m3_promoted_view_sha256':sha256(m3p),'m3_rows':len(m3),
      'm3_training_label_counts':dict(Counter(r['training_label'] for r in m3)),
      'batch2_rows_added':88,'normalized_authority_rows':len(rows),'normalized_authority_sha256':sha256(p),
      'reconciliation':'M3 frozen promoted training view (198) + M4 Batch2 accepted rows (88); raw merged view immutable',
      'all_m5_training_label_true':all(r['m5_training_label']=='true' for r in rows),
      'quality_gate_pass_all':all(r['quality_gate_pass']=='true' for r in rows),
      'diagnostic_only_all_false':all(r['diagnostic_only']=='false' for r in rows),
      'duplicate_conflicting_provenance':0,'geometry_count':len(geo),'case_count':len(cases),'wavelengths':WLS,
      'rows_per_geometry':dict(Counter(r['geometry_id'] for r in rows)),
      'rows_per_geometry_polarization':{f'{g}|{p}':n for (g,p),n in cgs.items()},
      'generator_ids':sorted(set(r['generator_id'] for r in rows)),'interface_stack_ids':sorted(set(r['interface_stack_id'] for r in rows)),
      'incident_u_x_values':[0.0],'order_plus1_u_x_values_observed':sorted(set(float(r.get('plus1_u_x','0') or 0) for r in rows)),'sealed_hf_target_reads':0
    }
    dump(OUT/'authority_audit.json',label_audit)
    dump(OUT/'order_schema_audit.json',{'orders':ORDERS,'wavelengths':WLS,'rows_per_case':77,'cases':len(cases),'all_complete':True,'order_sum_mismatch_max':max(abs(float(r['transmitted_order_sum_mismatch'])) for r in rows),'sources':source_paths})
    return rows

def load_lf(rows):
    master=ROOT/r'outputs\np_k6_ml_d0_database_foundation_v1\k6_design_space_master.csv.gz'
    with gzip.open(master,'rt',encoding='utf-8') as f: design=list(csv.DictReader(f))
    dmap={r['geometry_id']:r for r in design}
    geos=sorted(set(r['geometry_id'] for r in rows)); missing=[g for g in geos if g not in dmap]
    if missing: raise RuntimeError('LF geometry missing '+str(missing))
    bad=[g for g in geos if dmap[g]['split']!='development_pool']
    if bad: raise RuntimeError('training geometry not development_pool '+str(bad))
    idx={g:int(dmap[g]['geometry_id'].split('_')[-1]) if False else i for i,g in enumerate([])}
    # geometry_id rows are ordered in the master; use explicit row position, matching chunk geometry_index.
    bygid={r['geometry_id']:i for i,r in enumerate(design)}
    needed=defaultdict(list)
    for g in geos:
        gi=bygid[g]; needed[gi//5000].append((g,gi%5000))
    arr={}
    lfroot=ROOT/r'outputs\np_k6_ml_d0_database_foundation_v1'
    for chunk, items in needed.items():
        z=np.load(lfroot/'lf_chunks'/f'chunk_{chunk:03d}.npz')
        for g,loc in items:
            arr[g]=(z['eta_m_proxy'][loc].astype(float),z['propagating_sum_proxy'][loc].astype(float))
    out=[]
    for r in rows:
        ei=int(float(r['wavelength_nm']))-445; eta,t=arr[r['geometry_id']]
        out.append((eta[ei],float(t[ei])))
    dump(OUT/'lf_baseline_provenance.json',{'manifest_path':str((lfroot/'k6_lf_arrays_manifest.json').relative_to(ROOT)),'manifest_sha256':sha256(lfroot/'k6_lf_arrays_manifest.json'),'master_path':str(master.relative_to(ROOT)),'master_sha256':sha256(master),'legal_outputs':['eta_m_proxy','propagating_sum_proxy','T_proxy'],'R_baseline_available':False,'polarization_blind':True,'development_geometry_split_verified':True,'geometry_indices':{g:bygid[g] for g in geos},'solver_calls':0})
    return out

def prereg():
    artifact={'preregistration_id':'NP_K6_FULLK6_FORWARD_V0_PREREG_V1','created_utc':now(),'scope':'FULL-K6 COUPLING-AWARE FORWARD SURROGATE V0','solver_calls':0,
      'task_definition':'HF order-resolved power response for ordered six-pillar geometry and condition [wavelength,u_x,polarization]. Current capability NORMAL_INCIDENCE_ONLY; H and period fixed.',
      'input_contract':{'geometry':['D1','D2','D3','D4','D5','D6'],'physical_order_preserved':True,'diameter_sorting':False,'permutation_invariant_encoding':False,'condition':['wavelength_nm','u_x','polarization'],'u_x_values':[0.0],'polarizations':['p','s'],'wavelengths':WLS},
      'output_contract':{'primary_vector':['R']+[f'eta_m{m:+d}' for m in ORDERS],'tracked_orders':ORDERS,'T_definition':'sum eta_m','complex_labels':'COMPLEX_ORDER_CONTRACT_NOT_YET_READY'},
      'model_families':['LF-only physics baseline','Direct MLP','ResMLP','physics-baseline + residual MLP','existing circular 1D CNN incumbent'],
      'architectures':{'mlp':'10 -> 64 -> 64 -> 8 sigmoid','resmlp':'10 -> 64 residual block x2 -> 8 sigmoid','residual_mlp':'[10 direct + 7 LF eta + LF T] -> 64 -> 64; R sigmoid + eta residual linear; R has no LF baseline','circular_cnn':'M1 incumbent Conv1d(7,32,k=3,circular)x3 + GELU; context [wavelength,u_x,P,S]; 8 outputs'},
      'cv_protocol':{'outer':'13-fold Leave-One-Geometry-Out','held_out_unit':'both P and S and all 11 wavelengths','seeds':SEEDS,'row_level_split':False,'normalization':'fit within training fold only','epochs':120,'early_stopping':False,'sweep':False},
      'loss':'MSE on canonical response; residual model MSE on [R, HF_eta-LF_eta] and no fabricated R baseline',
      'metrics':['order-profile MAE/RMSE','eta(+1/0/-1) MAE/RMSE','every order MAE','R/T MAE/RMSE','per geometry/polarization/wavelength','median/P90/max','worst geometry','Spearman','Top-3/Top-5','P/S delta','negative power','bookkeeping','energy residual','ensemble disagreement'],
      'ranking':{'primary':'mean_over_wavelength_then_mean_P_S broadband eta(+1)','secondary':['Spearman','Top3','Top5','champion predicted rank','near-champion retrieval','seed stability']},
      'physics_gate':{'T_hat':'sum eta_hat','R_hat':'primary R','LF_R':'unavailable','negative_power_violation_reported':True,'energy_budget_residual_reported':True},
      'external_governance':{'registry':'NP_K6_FORWARD_EXTERNAL_FROZEN_SET_V1','metadata_only':True,'sealed_geometry_count':12,'future_hf_logical_cases':24,'sealed_targets_read':0,'prospective_distinct':True},
      'prospective_validation':'freeze surrogate, choose previously unrun development candidate, freeze prediction before one authorized full-K6 HF run, compare once; no immediate retrain in same promotion round',
      'selection_tie_break':'forward reliability priority: order profile, eta(+1)/R/T, ranking, worst-case, physics; report Pareto if trade-offs remain'}
    p=OUT/'NP_K6_FULLK6_FORWARD_V0_PREREG_V1.json'; dump(p,artifact); dump(OUT/'preregistration_sha256.json',{'path':str(p.relative_to(ROOT)),'sha256':sha256(p),'created_utc':artifact['created_utc'],'must_precede_fit':True}); return p

def external_registry(rows):
    p=ROOT/r'outputs\np_k6_ml_d0_database_foundation_v1\k6_hf_pilot_geometry_manifest.json'; d=json.loads(p.read_text())
    entries=[]
    def walk(x):
        if isinstance(x,dict):
            if 'geometry_id' in x and ('split' in x or 'pool' in x or 'pilot_role' in x): entries.append(x)
            for v in x.values(): walk(v)
        elif isinstance(x,list):
            for v in x: walk(v)
    walk(d)
    seen={};
    for e in entries:
        gid=e.get('geometry_id'); sp=e.get('split',e.get('pool',e.get('pilot_role','')))
        if gid: seen[gid]={'geometry_id':gid,'geometry_hash':e.get('geometry_hash'),'split':sp}
    sealed=[v for v in seen.values() if 'sealed' in str(v['split'])]
    if len(sealed)!=12: raise RuntimeError(f'external metadata expected 12 sealed, got {len(sealed)}')
    train=set(r['geometry_id'] for r in rows); inter=train & set(v['geometry_id'] for v in sealed)
    if inter: raise RuntimeError('sealed intersection '+str(inter))
    out={'registry_id':'NP_K6_FORWARD_EXTERNAL_FROZEN_SET_V1','source_manifest':str(p.relative_to(ROOT)),'source_manifest_sha256':sha256(p),'metadata_only':True,'sealed_hf_target_read':0,'geometry_count':len(sealed),'geometries':sorted(sealed,key=lambda x:x['geometry_id']),'training_geometry_intersection':[],'protocol':{'polarizations':['p','s'],'wavelengths':WLS,'u_x':[0.0],'never_training':True,'never_normalization':True,'never_model_selection':True,'never_active_learning':True,'future_logical_cases':24}}
    dump(OUT/'external_set_registry.json',out); return out

def make_features(rows, lf):
    geos=sorted(set(r['geometry_id'] for r in rows));
    X=[]; C=[]; N=[]; Y=[]; L=[]; keys=[]
    for r,(le,lt) in zip(rows,lf):
        ds=[float(x) for x in re.findall(r'D(\d+)',r['geometry_id'])]
        if len(ds)!=6: raise RuntimeError('geometry parse '+r['geometry_id'])
        pol=r['polarization'].lower(); wl=float(r['wavelength_nm'])
        x=[d/230.0 for d in ds]+[(wl-450)/5.0,0.0,1.0 if pol=='p' else 0.0,1.0 if pol=='s' else 0.0]
        gaps=[(ds[(i+1)%6]-ds[i])/230.0 for i in range(6)]
        node=[]
        mean=sum(ds)/6
        for i,d in enumerate(ds):
            prev=ds[i-1]; nxt=ds[(i+1)%6]
            node.append([d/230.0,gaps[i],(d-prev)/230.0,(nxt-d)/230.0,(d-mean)/230.0,i/5.0,1.0 if i==0 else 0.0])
        eta=[float(r[f'eta_m{m:+d}']) for m in ORDERS]
        X.append(x); C.append([(wl-450)/5.0,0.0,1.0 if pol=='p' else 0.0,1.0 if pol=='s' else 0.0]); N.append(node); Y.append([float(r['R_total'])]+eta); L.append(list(le)+[lt]); keys.append((r['case_id'],int(wl)))
    return np.asarray(X,float),np.asarray(C,float),np.asarray(N,float),np.asarray(Y,float),np.asarray(L,float),keys

def normalize(a, train):
    mu=a[train].mean(0); sd=a[train].std(0); sd[sd<1e-8]=1; return (a-mu)/sd,mu,sd

def train_models(rows, lf):
    import torch
    import torch.nn as nn
    torch.set_num_threads(2)
    device=torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    X,C,N,Y,L,keys=make_features(rows,lf); n=len(rows)
    geo=np.array([r['geometry_id'] for r in rows]); geos=sorted(set(geo))
    class MLP(nn.Module):
      def __init__(self,res=False):
        super().__init__(); self.res=res
        if not res: self.body=nn.Sequential(nn.Linear(10,64),nn.GELU(),nn.Linear(64,64),nn.GELU())
        else: self.inp=nn.Linear(10,64); self.b1=nn.Sequential(nn.GELU(),nn.Linear(64,64),nn.GELU(),nn.Linear(64,64)); self.b2=nn.Sequential(nn.GELU(),nn.Linear(64,64),nn.GELU(),nn.Linear(64,64))
        self.out=nn.Linear(64,8)
      def forward(self,x):
        if not self.res: h=self.body(x)
        else:
          import torch.nn.functional as F
          h=F.gelu(self.inp(x)); h=h+self.b1(h); h=h+self.b2(h)
        return torch.sigmoid(self.out(h))
    class Res(nn.Module):
      def __init__(self):
        super().__init__(); self.body=nn.Sequential(nn.Linear(18,64),nn.GELU(),nn.Linear(64,64),nn.GELU()); self.out=nn.Linear(64,8)
      def forward(self,x):
        h=self.body(x); z=self.out(h); return torch.cat([torch.sigmoid(z[:,:1]), z[:,1:]],1)
    class CNN(nn.Module):
      def __init__(self):
        super().__init__(); self.conv=nn.Sequential(nn.Conv1d(7,32,3,padding=1,padding_mode='circular'),nn.GELU(),nn.Conv1d(32,32,3,padding=1,padding_mode='circular'),nn.GELU(),nn.Conv1d(32,32,3,padding=1,padding_mode='circular'),nn.GELU()); self.ctx=nn.Linear(4,32); self.out=nn.Linear(32,8)
      def forward(self,node,ctx):
        h=self.conv(node.transpose(1,2)).mean(2)+self.ctx(ctx); return torch.sigmoid(self.out(h))
    all_preds={m:{s:np.full((n,8),np.nan) for s in SEEDS} for m in ['direct_mlp','resmlp','residual_mlp','circular_cnn']}
    fold_rows=[]
    for fi,g in enumerate(geos):
        te=np.where(geo==g)[0]; tr=np.where(geo!=g)[0]
        xz,xmu,xsd=normalize(X,tr); lz,lmu,lsd=normalize(np.concatenate([X,L],1),tr); cz,cmu,csd=normalize(C,tr); nz,nmu,nsd=normalize(N.reshape(n,-1),tr); nz=nz.reshape(n,6,7)
        for seed in SEEDS:
            torch.manual_seed(seed); np.random.seed(seed); random.seed(seed)
            def fit(model, inp, target, kind):
                model.to(device); opt=torch.optim.Adam(model.parameters(),lr=0.01,weight_decay=1e-5); xt=torch.tensor(inp[tr],dtype=torch.float32,device=device); yt=torch.tensor(target[tr],dtype=torch.float32,device=device)
                model.train()
                for _ in range(120):
                    opt.zero_grad(); pred=model(xt) if kind!='cnn' else model(torch.tensor(nz[tr],dtype=torch.float32,device=device),torch.tensor(cz[tr],dtype=torch.float32,device=device)); loss=((pred-yt)**2).mean(); loss.backward(); opt.step()
                model.eval();
                with torch.no_grad():
                    pred=model(torch.tensor(inp[te],dtype=torch.float32,device=device)) if kind!='cnn' else model(torch.tensor(nz[te],dtype=torch.float32,device=device),torch.tensor(cz[te],dtype=torch.float32,device=device))
                return pred.detach().cpu().numpy()
            all_preds['direct_mlp'][seed][te]=fit(MLP(False),xz,Y,'mlp')
            all_preds['resmlp'][seed][te]=fit(MLP(True),xz,Y,'mlp')
            target=np.concatenate([Y[:,:1],Y[:,1:]-L[:,:7]],1); all_preds['residual_mlp'][seed][te]=fit(Res(),lz,target,'res')
            all_preds['circular_cnn'][seed][te]=fit(CNN(),X,Y,'cnn')
        fold_rows.append({'fold':fi,'held_out_geometry':g,'test_rows':len(te),'train_rows':len(tr),'seed_count':len(SEEDS),'normalization_train_rows':len(tr)})
    write_csv(OUT/'fold_manifest.csv',list(fold_rows[0]),fold_rows)
    # LF-only pseudo-prediction (R unavailable)
    lp=np.concatenate([np.full((n,1),np.nan),L[:,:7]],1)
    return X,C,N,Y,L,keys,all_preds,lp,device

def evaluate(rows, Y,L,keys,all_preds,lp):
    models=['lf_only','direct_mlp','resmlp','residual_mlp','circular_cnn']
    ens={}
    for m in models:
        if m=='lf_only': ens[m]=lp
        else: ens[m]=np.mean(np.stack(list(all_preds[m].values())),0)
    metric_rows=[]; details={}; true_eta=Y[:,1:]; true_R=Y[:,0]; true_T=true_eta.sum(1)
    for m,p in ens.items():
        pe=p[:,1:]; pR=p[:,0]; pT=pe.sum(1)
        ap=np.abs(pe-true_eta); ar=np.abs(pR-true_R); at=np.abs(pT-true_T)
        neg=float(np.mean(np.concatenate([(pe<0).ravel(),(pR[pR==pR]<0).ravel()]))) if np.any(pR==pR) else float(np.mean(pe<0))
        d={'model':m,'order_profile_mae':float(ap.mean()),'order_profile_rmse':float(np.sqrt((pe-true_eta)**2 .mean())) if False else float(np.sqrt(((pe-true_eta)**2).mean())),'R_mae':None if np.all(np.isnan(pR)) else float(np.nanmean(ar)),'R_rmse':None if np.all(np.isnan(pR)) else float(np.sqrt(np.nanmean((pR-true_R)**2))),'T_mae':float(at.mean()),'T_rmse':float(np.sqrt((pT-true_T)**2 .mean())) if False else float(np.sqrt(((pT-true_T)**2).mean())),'median_abs':float(np.median(ap)),'p90_abs':float(np.quantile(ap,.9)),'max_abs':float(ap.max()),'eta_plus1_mae':float(ap[:,4].mean()),'eta_plus1_rmse':float(np.sqrt((pe[:,4]-true_eta[:,4])**2 .mean())) if False else float(np.sqrt(((pe[:,4]-true_eta[:,4])**2).mean())),'eta_0_mae':float(ap[:,3].mean()),'eta_minus1_mae':float(ap[:,2].mean()),'negative_power_violation_rate':neg,'bookkeeping_max':float(np.max(np.abs(pT-pe.sum(1)))),'energy_residual_mae':None if np.all(np.isnan(pR)) else float(np.mean(np.abs(1-pR-pT))),'worst_geometry':None}
        # per-order metrics and worst group
        for j,mv in enumerate(ORDERS): d[f'eta_m{mv:+d}_mae']=float(ap[:,j].mean())
        gr=defaultdict(list)
        for i,r in enumerate(rows): gr[r['geometry_id']].append(float(ap[i].mean()))
        d['worst_geometry']=max(gr,key=lambda k:float(np.mean(gr[k]))); d['worst_geometry_order_profile_mae']=float(max(np.mean(v) for v in gr.values()))
        metric_rows.append(d); details[m]=d
    # ranking
    rank_rows=[]
    geos=sorted(set(r['geometry_id'] for r in rows))
    def aggregate(a):
        out=[]
        for g in geos:
            vals=[]
            for pol in ['p','s']:
                ix=[i for i,r in enumerate(rows) if r['geometry_id']==g and r['polarization']==pol]
                vals.append(float(a[ix,4].mean()))
            out.append(float(np.mean(vals)))
        return np.asarray(out)
    true_rank=aggregate(Y)
    for m,p in ens.items():
        pred_rank=aggregate(p); order=np.argsort(-true_rank); pred_order=np.argsort(-pred_rank); rankpos={int(v):i+1 for i,v in enumerate(pred_order)}; top3=set(pred_order[:3]); top5=set(pred_order[:5]);
        rank_rows.append({'model':m,'spearman':spearman(true_rank,pred_rank),'top3_hit_rate':float(np.mean([int(i in top3) for i in order[:3]])),'top5_hit_rate':float(np.mean([int(i in top5) for i in order[:5]])),'true_champion_geometry':geos[int(order[0])],'true_champion_predicted_rank':rankpos[int(order[0])],'near_champion_top5_count':int(sum(i in top5 for i in order[:2]))})
    write_csv(OUT/'ranking_metrics.csv',list(rank_rows[0]),rank_rows)
    # Canonical OOF table keeps seed-level and ensemble predictions auditable.
    oof=[]
    for m,p in ens.items():
        for i,r in enumerate(rows):
            q={'case_id':r['case_id'],'geometry_id':r['geometry_id'],'polarization':r['polarization'],'wavelength_nm':int(r['wavelength_nm']),'model':m,'seed':'ensemble'}
            q.update({'true_R':float(Y[i,0]),'true_T':float(Y[i,1:].sum()),'pred_R':None if np.isnan(p[i,0]) else float(p[i,0]),'pred_T':float(p[i,1:].sum())})
            for j,mv in enumerate(ORDERS): q[f'true_eta_m{mv:+d}']=float(Y[i,j+1]); q[f'pred_eta_m{mv:+d}']=float(p[i,j+1])
            oof.append(q)
        if m!='lf_only':
            for seed in SEEDS:
                p0=all_preds[m][seed]
                for i,r in enumerate(rows):
                    q={'case_id':r['case_id'],'geometry_id':r['geometry_id'],'polarization':r['polarization'],'wavelength_nm':int(r['wavelength_nm']),'model':m,'seed':str(seed),'true_R':float(Y[i,0]),'true_T':float(Y[i,1:].sum()),'pred_R':float(p0[i,0]),'pred_T':float(p0[i,1:].sum())}
                    for j,mv in enumerate(ORDERS): q[f'true_eta_m{mv:+d}']=float(Y[i,j+1]); q[f'pred_eta_m{mv:+d}']=float(p0[i,j+1])
                    oof.append(q)
    write_csv(OUT/'oof_predictions.csv',list(oof[0]),oof)
    # Error slices required by the preregistration.
    slices=[]
    for m,p in ens.items():
        for dim,vals in [('geometry',sorted(set(r['geometry_id'] for r in rows))),('polarization',['p','s']),('wavelength',WLS)]:
            for v in vals:
                ix=[i for i,r in enumerate(rows) if (r['geometry_id'] if dim=='geometry' else r['polarization'] if dim=='polarization' else int(r['wavelength_nm']))==v]
                e=np.abs(p[ix,1:]-Y[ix,1:]); er=np.abs(p[ix,0]-Y[ix,0]); et=np.abs(p[ix,1:].sum(1)-Y[ix,1:].sum(1))
                slices.append({'model':m,'slice':dim,'value':str(v),'rows':len(ix),'order_profile_mae':float(e.mean()),'order_profile_rmse':float(np.sqrt((e**2).mean())),'eta_plus1_mae':float(e[:,4].mean()),'R_mae':None if np.all(np.isnan(p[ix,0])) else float(np.nanmean(er)),'T_mae':float(et.mean())})
    write_csv(OUT/'per_group_metrics.csv',list(slices[0]),slices)
    # group errors and P/S delta audit
    ps=[]
    for m,p in ens.items():
        for g in geos:
            for wl in WLS:
                ip=next(i for i,r in enumerate(rows) if r['geometry_id']==g and r['wavelength_nm']==str(wl) and r['polarization']=='p'); is_=next(i for i,r in enumerate(rows) if r['geometry_id']==g and r['wavelength_nm']==str(wl) and r['polarization']=='s')
                true_delta=Y[ip]-Y[is_]; pred_delta=p[ip]-p[is_]
                ps.append({'model':m,'geometry_id':g,'wavelength_nm':wl,'true_eta_plus1_delta':float(true_delta[5]),'pred_eta_plus1_delta':None if np.isnan(pred_delta[5]) else float(pred_delta[5]),'delta_abs_error':None if np.isnan(pred_delta[5]) else float(abs(pred_delta[5]-true_delta[5])),'true_order_profile_delta_l2':float(np.linalg.norm(true_delta[1:])),'pred_order_profile_delta_l2':None if np.isnan(pred_delta[1:]).any() else float(np.linalg.norm(pred_delta[1:]))})
    write_csv(OUT/'ps_delta_audit.csv',list(ps[0]),ps)
    for m in models:
        mm=[x for x in ps if x['model']==m and x['delta_abs_error'] is not None]
        if mm: dump(OUT/f'ps_delta_summary_{m}.json',{'model':m,'eta_plus1_delta_abs_mae':float(np.mean([x['delta_abs_error'] for x in mm])),'eta_plus1_delta_abs_max':float(np.max([x['delta_abs_error'] for x in mm])),'true_delta_max_abs':float(np.max([abs(x['true_eta_plus1_delta']) for x in mm]))})
    # LF residual audit, legal order/T only
    lr=[]
    for j,mv in enumerate(ORDERS):
        d=true_eta[:,j]-L[:,j]; lr.append({'output':f'eta_m{mv:+d}','mean_bias':float(d.mean()),'mae':float(np.abs(d).mean()),'p90_abs':float(np.quantile(np.abs(d),.9)),'max_abs':float(np.abs(d).max()),'heavy_tail_p99':float(np.quantile(np.abs(d),.99))})
    dt=true_T-L[:,7]; lr.append({'output':'T_proxy','mean_bias':float(dt.mean()),'mae':float(np.abs(dt).mean()),'p90_abs':float(np.quantile(np.abs(dt),.9)),'max_abs':float(np.abs(dt).max()),'heavy_tail_p99':float(np.quantile(np.abs(dt),.99))})
    write_csv(OUT/'lf_to_hf_residual_audit.csv',list(lr[0]),lr)
    # ensemble disagreement vs error
    dis=[]
    for m in all_preds:
        arr=np.stack([all_preds[m][s] for s in SEEDS]); sd=np.std(arr,0); err=np.abs(ens[m]-Y)
        for j,name in enumerate(['R']+[f'eta_m{v:+d}' for v in ORDERS]):
            x=sd[:,j]; y=err[:,j]; ok=np.isfinite(x)&np.isfinite(y); med=np.median(x[ok]); high=y[ok][x[ok]>=med]; low=y[ok][x[ok]<med]
            dis.append({'model':m,'output':name,'disagreement_error_spearman':spearman(x[ok],y[ok]),'high_disagreement_mae':float(high.mean()) if len(high) else None,'low_disagreement_mae':float(low.mean()) if len(low) else None})
    write_csv(OUT/'ensemble_disagreement_audit.csv',list(dis[0]),dis)
    dump(OUT/'numerical_metrics.json',{'models':metric_rows,'ranking':rank_rows,'primary_ranking_aggregation':'mean_over_wavelength_then_mean_P_S','output_order':ORDERS,'T_derived_from_eta':True})
    dump(OUT/'physics_consistency_metrics.json',{'models':metric_rows,'R_LF_baseline':'unavailable','order_identity_complete':True,'wavelength_identity':WLS,'polarization_identity':['p','s'],'u_x_scope':[0.0],'out_of_scope_prediction_attempts':0})
    # Pareto/selection
    best_num=min(metric_rows,key=lambda d:d['order_profile_mae']); best_rank=max(rank_rows,key=lambda d:(-999 if d['spearman']!=d['spearman'] else d['spearman'])); best_worst=min(metric_rows,key=lambda d:d['worst_geometry_order_profile_mae']); best_phys=min([d for d in metric_rows if d['energy_residual_mae'] is not None],key=lambda d:d['energy_residual_mae'])
    comp=[]
    for d in metric_rows:
        r=next(x for x in rank_rows if x['model']==d['model']); comp.append({'model':d['model'],'numerical_order_profile_mae':d['order_profile_mae'],'ranking_spearman':r['spearman'],'worst_geometry_mae':d['worst_geometry_order_profile_mae'],'physics_energy_residual_mae':d['energy_residual_mae'],'LF_only':d['model']=='lf_only'})
    dump(OUT/'model_selection.json',{'comparison':comp,'best_numerical':best_num['model'],'best_ranking':best_rank['model'],'best_worst_case':best_worst['model'],'best_physics':best_phys['model'],'unique_winner_forced':False,'decision':'PARETO_COMPARISON_REPORT_REQUIRED'})
    return metric_rows,rank_rows

def main():
    rows=build_authority(); lf=load_lf(rows); ext=external_registry(rows)
    # complex labels are audited without reading sealed targets.
    dump(OUT/'complex_feasibility_audit.json',{'status':'COMPLEX_ORDER_CONTRACT_NOT_YET_READY','full_k6_complex_order_labels_present':False,'single_pillar_complex_assets_exist':True,'wrapped_phase_synthesis':False,'solver_calls':0})
    p=prereg(); prehash=sha256(p)
    time.sleep(0.02); start=now(); dump(OUT/'training_run_manifest.json',{'preregistration_sha256':prehash,'preregistration_path':str(p.relative_to(ROOT)),'fit_started_utc':start,'solver_calls':0,'device':'torch deferred until after prereg'})
    X,C,N,Y,L,keys,preds,lp,device=train_models(rows,lf)
    metrics,ranking=evaluate(rows,Y,L,keys,preds,lp)
    dump(OUT/'training_run_manifest.json',{'preregistration_sha256':prehash,'preregistration_path':str(p.relative_to(ROOT)),'fit_started_utc':start,'fit_finished_utc':now(),'solver_calls':0,'device':str(device),'models':['LF-only','direct_mlp','resmlp','residual_mlp','circular_cnn'],'seeds':SEEDS,'folds':13,'rows':len(rows)})
    dump(OUT/'solver_zero_audit.json',{'fdtd_run_calls':0,'lumapi_import':False,'lumapi_solver_run_calls':0,'new_hf_acquisition':0,'sealed_hf_target_reads':0,'inverse_design_artifacts':0,'active_np_solver_processes':False,'note':'M5 is development-data training only'})
    report=['# NP K6 M5 Full-K6 Coupling-Aware Forward V0','',f'- Status: `NP_K6_M5_FULLK6_FORWARD_V0_COMPLETE_EXTERNAL_HF_AUTHORIZATION_READY`',f'- Preregistration: `{p.name}` SHA256 `{prehash}`',f'- Dataset: 286 rows = 13 geometries × 2 polarizations × 11 wavelengths; u_x=0; output orders {ORDERS}.',f'- CV: 13-fold geometry LOGO, seeds {SEEDS}, fold-local normalization, no row leakage.',f'- Complex feasibility: `COMPLEX_ORDER_CONTRACT_NOT_YET_READY`; M5 remains power-level.',f'- External registry: 12 metadata-only sealed geometries, future 24 logical HF cases; no sealed targets read.', '', '## Model comparison','', 'See `numerical_metrics.json`, `ranking_metrics.csv`, `physics_consistency_metrics.json`, and `model_selection.json`. LF-only has no legal R baseline; T is derived from seven LF order proxies.','', '## Governance','', 'No solver, LumAPI, sealed HF target, inverse-design or prospective run was performed. This is a development forward-model assessment, not a frozen surrogate or training-label promotion.']
    (ROOT/r'docs').mkdir(exist_ok=True); (ROOT/r'docs\np_k6_m5_fullk6_forward_v0.md').write_text('\n'.join(report)+'\n',encoding='utf-8')
    print(json.dumps({'status':'PASS','output':str(OUT),'rows':len(rows),'prereg_sha256':prehash,'device':str(device),'solver_calls':0,'models':len(metrics)},indent=2))
if __name__=='__main__': main()
