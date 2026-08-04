"""Offline validation-only selection for Round-3 C5 against frozen models."""
from __future__ import annotations
import csv, hashlib, json, math
from pathlib import Path
import numpy as np
import torch
from torch import nn

ROOT=Path(r"D:\project\worktrees\blue_apcd_lp_stage11_4")
O=ROOT/"outputs/lp_ml_dataset_v1"; A=O/"analysis"; C=O/"clean_v2"; V3=O/"clean_v3"
T=['txx_real','txx_imag','txy_real','txy_imag','tyx_real','tyx_imag','tyy_real','tyy_imag']
F=['J1_side_nm','J2_length_nm','J2_width_nm','D_nm','sin_Psi','cos_Psi','wavelength_nm']
SEEDS=[11,22,33,44,55]

def rd(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def sh(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,x): p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
def feat(r):
    p=math.radians(float(r['Psi_deg']))
    return [float(r['J1_side_nm']),float(r['J2_length_nm']),float(r['J2_width_nm']),float(r['D_nm']),math.sin(p),math.cos(p),float(r['wavelength_nm'])]
class B(nn.Module):
    def __init__(self):
        super().__init__();self.net=nn.Sequential(nn.Linear(256,256),nn.SiLU(),nn.LayerNorm(256),nn.Dropout(.03),nn.Linear(256,256),nn.SiLU(),nn.LayerNorm(256),nn.Dropout(.03))
    def forward(self,x): return x+self.net(x)
class N(nn.Module):
    def __init__(self):
        super().__init__();self.a=nn.Sequential(nn.Linear(7,256),nn.SiLU(),nn.LayerNorm(256));self.b=nn.Sequential(B(),B(),B(),B());self.c=nn.Linear(256,8)
    def forward(self,x): return self.c(self.b(self.a(x)))
def ensemble(paths,X,dev):
    vals=[]
    for p in paths:
        m=N().to(dev); d=torch.load(p,map_location=dev,weights_only=False);m.load_state_dict(d.get('model_state_dict',d));m.eval()
        with torch.no_grad(): vals.append(m(X).cpu().numpy())
    a=np.stack(vals); return a.mean(0),np.linalg.norm(a.std(axis=0),axis=1)
def metrics(pred,actual):
    e=pred-actual; fr=np.linalg.norm(e,axis=1)
    phase=[];txx=[];tyy=[];leak=[]
    for p,y in zip(pred,actual):
        zp=complex(p[0],p[1]);zy=complex(y[0],y[1]);
        phase.append(abs(math.degrees(math.atan2(math.sin(np.angle(zp)-np.angle(zy)),math.cos(np.angle(zp)-np.angle(zy))))))
        Mp=np.array([[complex(p[0],p[1]),complex(p[2],p[3])],[complex(p[4],p[5]),complex(p[6],p[7])]])
        My=np.array([[complex(y[0],y[1]),complex(y[2],y[3])],[complex(y[4],y[5]),complex(y[6],y[7])]])
        tx=abs(Mp[0,0])**2-abs(My[0,0])**2;ty=abs(Mp[1,1])**2-abs(My[1,1])**2
        lp=(abs(Mp[0,1])**2+abs(Mp[1,0])**2)/max(np.sum(abs(Mp)**2),1e-12);ly=(abs(My[0,1])**2+abs(My[1,0])**2)/max(np.sum(abs(My)**2),1e-12)
        txx.append(abs(tx));tyy.append(abs(ty));leak.append(abs(lp-ly))
    return {'rows':int(len(actual)),'raw_jones_mae':float(np.mean(abs(e))),'raw_jones_rmse':float(np.sqrt(np.mean(e*e))),'raw_jones_max':float(np.max(abs(e))),'frobenius_mean':float(np.mean(fr)),'frobenius_p95':float(np.percentile(fr,95)),'phase_mae_deg':float(np.mean(phase)),'Txx_mae':float(np.mean(txx)),'Tyy_mae':float(np.mean(tyy)),'leakage_mae':float(np.mean(leak))}
def main():
    base=rd(C/"lp_ml_dataset_v1_merged_clean_v2_319_geometry_2871_rows.csv"); new=rd(V3/"lp_ml_dataset_v1_merged_clean_v3_round3_377_geometry_3393_rows.csv")
    split2={r['candidate_id']:r for r in rd(C/'split_clean_v2.csv')};split3={r['candidate_id']:r for r in rd(V3/'split_clean_v3.csv')}
    rows=[]; keys=[]
    for r in new:
        cid=r['candidate_id']; s=split3.get(cid,split2.get(cid));
        if s is None: raise SystemExit(f'MISSING_SPLIT:{cid}')
        rnd=s.get('round','ROUND1' if cid in split2 else 'ROUND3'); rows.append(r); keys.append((rnd,s['split']))
    y=np.asarray([[float(r[k]) for k in T] for r in rows],np.float32); raw=np.asarray([feat(r) for r in rows],np.float32)
    n2=json.loads((C/'normalization_clean_v2.json').read_text()); n3=json.loads((V3/'normalization_clean_v3.json').read_text())
    dev=torch.device('cuda' if torch.cuda.is_available() else 'cpu');x2=torch.tensor((raw-np.asarray(n2['mean']))/np.asarray(n2['std']),dtype=torch.float32,device=dev);x3=torch.tensor((raw-np.asarray(n3['mean']))/np.asarray(n3['std']),dtype=torch.float32,device=dev)
    c0_paths=[O/'model_runtime_round1_frozen_v1'/f'residual_mlp_seed_{s}.pt' for s in SEEDS]; c1_paths=[C/'model_runtime_recompetition_v2/C1'/f'residual_mlp_seed_{s}.pt' for s in SEEDS]; c5_paths=[V3/'model_runtime_round3_c5_v1'/f'residual_mlp_seed_{s}.pt' for s in SEEDS]
    if not all(p.exists() for p in c0_paths+c1_paths+c5_paths): raise SystemExit('MODEL_CHECKPOINT_SET_INCOMPLETE')
    c0,_=ensemble(c0_paths,x2,dev);c1,_=ensemble(c1_paths,x2,dev);c5,_=ensemble(c5_paths,x3,dev)
    old=.95*c0+.05*c1
    pred={'C0':c0,'OLD_BLEND_095_C0_005_C1':old,'C5':c5}; domains=['ROUND1:validation','ROUND2:validation','ROUND3:validation']; idx={d:np.asarray([i for i,k in enumerate(keys) if f'{k[0]}:{k[1]}'==d],int) for d in domains}
    # Candidate and convex blends are all selected using validation only.
    candidates={'C0':c0,'OLD_BLEND_095_C0_005_C1':old,'C5':c5}
    for a in np.linspace(0,1,21):
        candidates[f'C0_C5_BLEND_{a:.2f}']=(1-a)*c0+a*c5
        candidates[f'OLD_C5_BLEND_{a:.2f}']=(1-a)*old+a*c5
    vm={name:{d:metrics(p[idx[d]],y[idx[d]]) for d in domains} for name,p in candidates.items()}
    baseline=np.mean([vm['C0'][d]['frobenius_mean'] for d in domains]); scored=[]
    for name,m in vm.items():
        score=float(np.mean([m[d]['frobenius_mean'] for d in domains])/max(baseline,1e-12)); scored.append({'candidate':name,'validation_score':score,'metrics':m,'validation_only':True})
    selected=min(scored,key=lambda q:q['validation_score']); name=selected['candidate']; frozen=candidates[name]
    # Tests are evaluated only after selection is frozen.
    test_domains=['ROUND1:test','ROUND2:test','ROUND3:test']; tidx={d:np.asarray([i for i,k in enumerate(keys) if f'{k[0]}:{k[1]}'==d],int) for d in test_domains}; tm={d:metrics(frozen[tidx[d]],y[tidx[d]]) for d in test_domains}
    c0tm={d:metrics(c0[tidx[d]],y[tidx[d]]) for d in test_domains}
    outcome='C5_SELECTED_VALIDATION_ONLY' if name=='C5' or 'BLEND' in name else 'C0_RETAINED_VALIDATION_ONLY'
    allidx={**idx,**tidx}
    out={'contract':'LP_ML_ROUND3_VALIDATION_ONLY_SELECTION_V1','selection_frozen_before_tests':True,'selected_model':name,'outcome':outcome,'device':str(dev),'cuda_name':torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,'domain_counts':{d:int(len(allidx[d])) for d in domains+test_domains},'validation_ranking':sorted(scored,key=lambda q:q['validation_score']),'selected_validation':selected,'selected_test_metrics':tm,'c0_test_metrics':c0tm,'clean_v2_sha256':sh(C/'lp_ml_dataset_v1_merged_clean_v2_319_geometry_2871_rows.csv'),'clean_v3_sha256':sh(V3/'lp_ml_dataset_v1_merged_clean_v3_round3_377_geometry_3393_rows.csv'),'solver_calls':0,'test_used_for_selection':False,'inverse_fdtd':False}
    dump(A/'lp_ml_round3_validation_selection_v1.json',out)
    with (A/'lp_ml_round3_validation_selection_v1.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.writer(f);w.writerow(['candidate','validation_score']);w.writerows([[q['candidate'],q['validation_score']] for q in sorted(scored,key=lambda q:q['validation_score'])])
    print(json.dumps({'selected_model':name,'outcome':outcome,'validation_score':selected['validation_score'],'test_metrics':tm,'solver_calls':0},indent=2))
if __name__=='__main__': main()
