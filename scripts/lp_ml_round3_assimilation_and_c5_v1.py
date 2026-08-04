"""Round-3 physics assimilation, clean-v3 materialization and C5 retraining.

This script consumes only accepted Round-3 checkpoints/CSV and the immutable
clean-v2 sources.  It never calls lumapi or a solver.
"""
from __future__ import annotations

import csv, hashlib, json, math, random, statistics, time
from collections import defaultdict
from pathlib import Path

import numpy as np
import torch
from torch import nn

ROOT=Path(r"D:\project\worktrees\blue_apcd_lp_stage11_4")
O=ROOT/"outputs/lp_ml_dataset_v1"; A=O/"analysis"; P=O/"plans"
CLEAN=O/"clean_v2"; STAGE=O/"staging/lp_ml_dataset_v1_round3_targeted_active_learning_attempt1_v1"
MERGED=CLEAN/"lp_ml_dataset_v1_merged_clean_v2_319_geometry_2871_rows.csv"; SPLIT=CLEAN/"split_clean_v2.csv"
PLAN=P/"lp_ml_dataset_v1_round3_64_candidate_plan_v1.csv"; PRE=A/"lp_ml_round3_pre_retrain_prospective_predictions_v1.json"
R3=A/"lp_ml_dataset_v1_round3_clean_accepted_58_geometry_522_rows.csv"; MERGED3=O/"clean_v3/lp_ml_dataset_v1_merged_clean_v3_round3_377_geometry_3393_rows.csv"
SPLIT3=O/"clean_v3/split_clean_v3.csv"; NORM3=O/"clean_v3/normalization_clean_v3.json"; MODELROOT=O/"clean_v3/model_runtime_round3_c5_v1"
WLS=[450.0+i*0.5 for i in range(9)]; SEEDS=[11,22,33,44,55]
T=['txx_real','txx_imag','txy_real','txy_imag','tyx_real','tyx_imag','tyy_real','tyy_imag']; F=['J1_side_nm','J2_length_nm','J2_width_nm','D_nm','sin_Psi','cos_Psi','wavelength_nm']

def sha_bytes(b): return hashlib.sha256(b).hexdigest()
def sha(p): return sha_bytes(p.read_bytes())
def read_csv(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def write_csv(p,rows,fields=None):
    p.parent.mkdir(parents=True,exist_ok=True); fs=fields or []
    if not fs:
        for r in rows:
            for k in r:
                if k not in fs:fs.append(k)
    with p.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fs,extrasaction='ignore');w.writeheader();w.writerows(rows)
def dump(p,x): p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
def feat(r):
    p=math.radians(float(r['Psi_deg']));return [float(r['J1_side_nm']),float(r['J2_length_nm']),float(r['J2_width_nm']),float(r['D_nm']),math.sin(p),math.cos(p),float(r['wavelength_nm'])]
def cphase(a,b): return abs(math.degrees(math.atan2(math.sin(math.radians(a-b)),math.cos(math.radians(a-b)))))
def metrics_from_vec(v):
    z=complex(float(v[0]),float(v[1]));x=complex(float(v[2]),float(v[3]));y=complex(float(v[4]),float(v[5]));yy=complex(float(v[6]),float(v[7]));J=np.array([[z,x],[y,yy]],complex);p=np.abs(J)**2;s=np.linalg.svd(J,compute_uv=False);return {'Txx':float(p[0,0]),'Txy':float(p[0,1]),'Tyx':float(p[1,0]),'Tyy':float(p[1,1]),'leakage':float(p[0,1]+p[1,0]+p[1,1]),'sigma2_over_sigma1':float(s[1]/max(s[0],1e-12)),'projection_error':float(1-abs(z)**2/max(np.sum(p),1e-12)),'phase_deg':float(math.degrees(math.atan2(z.imag,z.real))),'frobenius':float(np.linalg.norm(J))}

class B(nn.Module):
    def __init__(self): super().__init__(); self.net=nn.Sequential(nn.Linear(256,256),nn.SiLU(),nn.LayerNorm(256),nn.Dropout(.03),nn.Linear(256,256),nn.SiLU(),nn.LayerNorm(256),nn.Dropout(.03))
    def forward(self,x): return x+self.net(x)
class N(nn.Module):
    def __init__(self): super().__init__(); self.a=nn.Sequential(nn.Linear(7,256),nn.SiLU(),nn.LayerNorm(256));self.b=nn.Sequential(B(),B(),B(),B());self.c=nn.Linear(256,8)
    def forward(self,x): return self.c(self.b(self.a(x)))
def loss_fn(pr,y):
    raw=nn.functional.smooth_l1_loss(pr,y);rel=torch.mean(torch.abs(pr-y)/(torch.abs(y)+1e-3));pt=pr[:,0]**2+pr[:,1]**2;yt=y[:,0]**2+y[:,1]**2;py=pr[:,6]**2+pr[:,7]**2;yy=y[:,6]**2+y[:,7]**2;power=torch.mean(torch.abs(pt-yt)+torch.abs(py-yy));rank=torch.mean(torch.abs(torch.sqrt(pt+py+1e-8)-torch.sqrt(yt+yy+1e-8)));phase=torch.mean(1-torch.cos(torch.atan2(pr[:,1],pr[:,0])-torch.atan2(y[:,1],y[:,0])));lp=(pr[:,2]**2+pr[:,3]**2+pr[:,4]**2+pr[:,5]**2)/(pt+py+1e-6);ly=(y[:,2]**2+y[:,3]**2+y[:,4]**2+y[:,5]**2)/(yt+yy+1e-6);projection=torch.mean(torch.abs(lp-ly));return raw+.25*rel+.10*power+.05*rank+.05*projection+.05*phase
def make_batches(idx_by_geom,train_ids,steps,rng):
    flat=[i for g in train_ids for i in idx_by_geom[g]];out=[]
    for _ in range(steps):
        rng.shuffle(flat);b=flat[:64]
        if len(b)<64:b=b+flat[:64-len(b)]
        out.append(b)
    return out
def train_c5(rows,train_idx,val_idx,mu,sd):
    dev=torch.device('cuda' if torch.cuda.is_available() else 'cpu');X=torch.tensor(np.asarray([feat(r) for r in rows],np.float32),device=dev);Y=torch.tensor(np.asarray([[float(r[k]) for k in T] for r in rows],np.float32),device=dev);X=(X-torch.tensor(mu,dtype=torch.float32,device=dev))/torch.tensor(sd,dtype=torch.float32,device=dev);MODELROOT.mkdir(parents=True,exist_ok=True);paths=[];info=[];by=defaultdict(list)
    for i in train_idx:by[rows[i]['candidate_id']].append(i)
    ids=sorted(by);steps=max(1,math.ceil(len(train_idx)/64));amp=torch.cuda.is_available()
    for seed in SEEDS:
        random.seed(seed);np.random.seed(seed);torch.manual_seed(seed)
        if torch.cuda.is_available():torch.cuda.manual_seed_all(seed)
        m=N().to(dev);opt=torch.optim.AdamW(m.parameters(),lr=3e-4,weight_decay=1e-4);sched=torch.optim.lr_scheduler.LambdaLR(opt,lambda e:(e+1)/10 if e<10 else 1e-6/3e-4+(1-1e-6/3e-4)*(.5*(1+math.cos(math.pi*(e-10)/(500-10)))));best=1e99;best_state=None;bad=0;rng=random.Random(seed);t0=time.time()
        for ep in range(500):
            m.train()
            for b in make_batches(by,ids,steps,rng):
                opt.zero_grad(set_to_none=True)
                with torch.cuda.amp.autocast(enabled=amp): l=loss_fn(m(X[b]),Y[b])
                l.backward();nn.utils.clip_grad_norm_(m.parameters(),1.0);opt.step()
            sched.step();m.eval()
            with torch.no_grad():v=float(nn.functional.smooth_l1_loss(m(X[val_idx]),Y[val_idx]).cpu())
            if v<best-1e-7:best=v;bad=0;best_state={k:q.detach().cpu().clone() for k,q in m.state_dict().items()}
            else:bad+=1
            if bad>=50:break
        m.load_state_dict(best_state);path=MODELROOT/f'residual_mlp_seed_{seed}.pt';torch.save({'model_state_dict':m.state_dict(),'candidate':'C5_ROUND3_TARGETED_RETRAIN','seed':seed,'from_scratch':True,'warm_start':False,'feature_order':F,'target_order':T,'normalization_sha256':sha(NORM3),'epochs':ep+1,'best_validation_smooth_l1':best},path);paths.append(path);info.append({'seed':seed,'epochs':ep+1,'best_validation_smooth_l1':best,'runtime_s':time.time()-t0,'checkpoint_sha256':sha(path)})
    return paths,info,dev

def main():
    plan=read_csv(PLAN);pred=json.loads(PRE.read_text(encoding='utf-8'));actual=read_csv(STAGE/'candidate_wavelength_jones_v1.csv');sub=read_csv(STAGE/'subrun_records_v1.csv');template=read_csv(MERGED);split2=read_csv(SPLIT)
    assert len(plan)==64 and len(pred['rows'])==64*9
    entered=json.loads((STAGE/'entered_accounting_v1.json').read_text(encoding='utf-8'))['solver_entries'];attempt_ids=[x['attempt_id'] for x in entered];dups=len(attempt_ids)-len(set(attempt_ids))
    byid={r['candidate_id']:r for r in plan}; complete_ids=sorted({r['candidate_id'] for r in actual});complete_ids=[x for x in complete_ids if sum(r['candidate_id']==x for r in actual)==9]
    if any(r['candidate_id']=='LPML_R1_GLOBAL_SOBOL_054' for r in actual): raise SystemExit('054_GATE')
    # Prospective evaluation before any C5 training.
    pmap={(r['candidate_id'],float(r['wavelength_nm'])):r for r in pred['rows']}; eval_rows=[]; errors=[]
    for r in actual:
        q=pmap[(r['candidate_id'],float(r['wavelength_nm']))]; a=np.array([float(r[k]) for k in T]);
        for model in ['C0','selected_blend','C1','C2','C3','C4']:
            pv=np.asarray(q[model],float);e=a-pv;errors.append({'candidate_id':r['candidate_id'],'wavelength_nm':float(r['wavelength_nm']),'model':model,'raw_mae':float(np.mean(np.abs(e))),'raw_rmse':float(np.sqrt(np.mean(e*e))),'frobenius':float(np.linalg.norm(e)),'phase_error_deg':cphase(metrics_from_vec(a)['phase_deg'],metrics_from_vec(pv)['phase_deg']),'Txx_error':abs(metrics_from_vec(a)['Txx']-metrics_from_vec(pv)['Txx']),'Tyy_error':abs(metrics_from_vec(a)['Tyy']-metrics_from_vec(pv)['Tyy']),'leakage_error':abs(metrics_from_vec(a)['leakage']-metrics_from_vec(pv)['leakage']),'sigma_error':abs(metrics_from_vec(a)['sigma2_over_sigma1']-metrics_from_vec(pv)['sigma2_over_sigma1']),'projection_error':abs(metrics_from_vec(a)['projection_error']-metrics_from_vec(pv)['projection_error'])})
    write_csv(A/'lp_ml_round3_prospective_evaluation_v1.csv',errors)
    summary={}
    for model in ['C0','selected_blend','C1','C2','C3','C4']:
        es=[x for x in errors if x['model']==model];summary[model]={'rows':len(es),'raw_jones_mae':statistics.mean(x['raw_mae'] for x in es),'raw_jones_rmse':math.sqrt(statistics.mean(x['raw_rmse']**2 for x in es)),'frobenius_mean':statistics.mean(x['frobenius'] for x in es),'frobenius_p95':float(np.percentile([x['frobenius'] for x in es],95)),'phase_mae_deg':statistics.mean(x['phase_error_deg'] for x in es),'Txx_mae':statistics.mean(x['Txx_error'] for x in es),'Tyy_mae':statistics.mean(x['Tyy_error'] for x in es),'leakage_mae':statistics.mean(x['leakage_error'] for x in es),'sigma2_ratio_mae':statistics.mean(x['sigma_error'] for x in es),'projection_error_mae':statistics.mean(x['projection_error'] for x in es)}
    # Materialize accepted rows with the immutable clean-v2 schema.
    fields=list(template[0].keys());plan_by={r['candidate_id']:r for r in plan};r3rows=[]
    for r in actual:
        q={k:'' for k in fields};q.update(r);g=plan_by[r['candidate_id']]
        for k in ['J1_side_nm','J2_length_nm','J2_width_nm','D_nm','Psi_deg','J1_center_x_nm','J1_center_y_nm','J2_center_x_nm','J2_center_y_nm','H_nm','period_x_nm','period_y_nm','material','direct_gap_nm','periodic_gap_nm','exact_geometry_hash_sha256','canonical_relative_geometry_hash_sha256','symmetry_equivalence_geometry_hash_sha256']:
            q[k]=g.get(k,q.get(k,''))
        q.update({'round_origin':'ROUND3','clean_materialization_version':'LP_ML_DATASET_V1_CLEAN_V3','clean_admission_status':'ADMITTED_COMPLETE_JONES','quarantine_status':'NOT_QUARANTINED','admission_source':'ROUND3_FORMAL_WEIGHTED_G0','quarantine_identity':'','physics_origin':'FORMAL_WEIGHTED_G0_PROSPECTIVE_ROUND3_TARGETED_ACTIVE_LEARNING','model_fill':'NONE','Jones_complete':'True','clean_split':''})
        r3rows.append(q)
    write_csv(R3,r3rows,fields)
    # Deterministic 48/8/8 geometry split for the accepted 58, preserving all v2 assignments.
    old_split={r['candidate_id']:r for r in split2};r3geoms=sorted({r['candidate_id'] for r in r3rows});assign={g:('train' if i<round(len(r3geoms)*48/58) else 'validation' if i<round(len(r3geoms)*56/58) else 'test') for i,g in enumerate(r3geoms)}
    srows=list(split2)
    for g in r3geoms:
        r=plan_by[g];srows.append({'candidate_id':g,'round':'ROUND3','split':assign[g],'category':r.get('category',''),'exact_geometry_hash_sha256':r['exact_geometry_hash_sha256'],'canonical_relative_geometry_hash_sha256':r['canonical_relative_geometry_hash_sha256'],'symmetry_equivalence_geometry_hash_sha256':r['symmetry_equivalence_geometry_hash_sha256'],'quarantine_status':'NOT_QUARANTINED'})
    write_csv(SPLIT3,srows,['candidate_id','round','split','category','exact_geometry_hash_sha256','canonical_relative_geometry_hash_sha256','symmetry_equivalence_geometry_hash_sha256','quarantine_status'])
    for r in r3rows:r['clean_split']=assign[r['candidate_id']]
    merged3rows=template+r3rows;write_csv(MERGED3,merged3rows,fields)
    train_geoms={r['candidate_id'] for r in srows if r['split']=='train'};train_rows=[r for r in merged3rows if r['candidate_id'] in train_geoms];mu=np.mean(np.asarray([feat(r) for r in train_rows],float),axis=0).tolist();sd=np.std(np.asarray([feat(r) for r in train_rows],float),axis=0).tolist();dump(NORM3,{'version':'LP_ML_DATASET_V1_CLEAN_V3_TRAIN_ONLY_NORMALIZATION','mean':mu,'std':sd,'feature_order':F,'train_geometry_count':len(train_geoms),'round3_complete_geometry_count':len(r3geoms),'source_dataset_sha256':sha(MERGED3)})
    train_idx=np.array([i for i,r in enumerate(merged3rows) if r['candidate_id'] in train_geoms],dtype=int);val_idx=np.array([i for i,r in enumerate(merged3rows) if r['candidate_id'] in {x['candidate_id'] for x in srows if x['split']=='validation'}],dtype=int);paths,train_info,dev=train_c5(merged3rows,train_idx,val_idx,mu,sd)
    dump(A/'lp_ml_round3_c5_training_v1.json',{'candidate':'C5_ROUND3_TARGETED_RETRAIN','seed_list':SEEDS,'from_scratch':True,'warm_start':False,'device':str(dev),'cuda_name':torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,'training_geometry_count':len(train_geoms),'validation_geometry_count':len({x['candidate_id'] for x in srows if x['split']=='validation'}),'checkpoint_hashes':[sha(p) for p in paths],'seed_results':train_info,'solver_calls':0,'merged_clean_v3_sha256':sha(MERGED3),'normalization_sha256':sha(NORM3)})
    dump(A/'lp_ml_round3_assimilation_summary_v1.json',{'planned_geometries':64,'complete_geometries':len(r3geoms),'coverage_gap':64-len(r3geoms),'accepted_rows':len(r3rows),'expected_rows_if_complete':576,'merged_geometry_count':len({r['candidate_id'] for r in merged3rows}),'merged_rows':len(merged3rows),'entered_subruns':len(entered),'unique_subruns':len(set(attempt_ids)),'duplicate_invocations':dups,'failed_subruns':128-len([x for x in sub if x.get('status')=='ACCEPTED']),'quarantined_cases':[x.get('subrun_id') for x in sub if x.get('status')!='ACCEPTED'],'prospective_evaluation':summary,'solver_calls':len(entered),'pre_retrain_predictions_sha256':sha(PRE),'pre_retrain_immutable':True,'status':'C5_TRAINED_WITH_PARTIAL_ROUND3_COVERAGE' if len(r3geoms)<64 else 'C5_TRAINED'})
    print(json.dumps({'complete_geometries':len(r3geoms),'accepted_rows':len(r3rows),'entered':len(entered),'unique_subruns':len(set(attempt_ids)),'duplicates':dups,'c5_checkpoints':[sha(p) for p in paths],'prospective':summary},indent=2))
if __name__=='__main__':main()
