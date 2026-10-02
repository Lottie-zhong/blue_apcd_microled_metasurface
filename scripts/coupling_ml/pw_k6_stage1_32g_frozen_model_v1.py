"""Frozen width-32 PW K6 state and P_scale LOGO analysis; offline only."""
from __future__ import annotations
import math, random, statistics
import numpy as np
import torch
from torch import nn
from sklearn.decomposition import PCA
from sklearn.kernel_ridge import KernelRidge
from sklearn.model_selection import GroupKFold
from sklearn.preprocessing import StandardScaler

WLS = tuple(range(440, 461))
THRESHOLD = 0.0009885656815447454

class Xform:
    def __init__(self): self.ss = StandardScaler()
    def fit(self, x): self.ss.fit(np.asarray(x, float)/130.0); return self
    def transform(self, x): return self.ss.transform(np.asarray(x, float)/130.0).astype(float)

class Net(nn.Module):
    def __init__(self):
        super().__init__()
        self.enc=nn.Sequential(nn.Linear(6,32),nn.ReLU(),nn.Linear(32,32),nn.ReLU())
        self.heads=nn.ModuleList([nn.Linear(32,2) for _ in range(7)])
        self.fuse=nn.Sequential(nn.Linear(14,32),nn.ReLU(),nn.Linear(32,14))
    def forward(self,x):
        q=self.enc(x); local=torch.cat([h(q) for h in self.heads],dim=1)
        return local+self.fuse(local)

def req(ok,msg):
    if not ok: raise RuntimeError(msg)

def setseed(s):
    random.seed(s); np.random.seed(s); torch.manual_seed(s)

def lossfn(p,y,sd): return torch.mean(((p-y)/sd)**2)

def pack(c,oi):
    q=c[:,:,oi,:]
    return np.stack([q[...,0].real,q[...,1].real,q[...,0].imag,q[...,1].imag],axis=-1).reshape(len(c),-1)

def pcasfit(c,idx):
    ps=[]; ys=[]
    for oi in range(7):
        p=PCA(n_components=2,svd_solver="full"); ys.append(p.fit_transform(pack(c[idx],oi))); ps.append(p)
    return ps,np.concatenate(ys,axis=1)

def scores(c,idx,ps): return np.concatenate([ps[o].transform(pack(c[idx],o)) for o in range(7)],axis=1)

def decode(y,ps):
    out=np.zeros((len(y),len(WLS),7,2),complex)
    for oi,p in enumerate(ps):
        a=p.inverse_transform(y[:,2*oi:2*oi+2]).reshape(len(y),len(WLS),4)
        out[:,:,oi,0]=a[:,:,0]+1j*a[:,:,2]; out[:,:,oi,1]=a[:,:,1]+1j*a[:,:,3]
    return out

def fitstop(x,y,xv,yv,seed):
    setseed(seed); m=Net(); req(sum(p.numel() for p in m.parameters())==2684,"M5 parameter count mismatch")
    opt=torch.optim.AdamW(m.parameters(),lr=.002,weight_decay=.0001)
    x,y,xv,yv=[torch.as_tensor(z,dtype=torch.float32) for z in (x,y,xv,yv)]
    sd=torch.as_tensor(np.maximum(np.std(y.numpy(),axis=0),1e-12),dtype=torch.float32)
    best,ep,stale=float("inf"),0,0
    for e in range(1,321):
        m.train(); opt.zero_grad(set_to_none=True); l=lossfn(m(x),y,sd); l.backward()
        torch.nn.utils.clip_grad_norm_(m.parameters(),5.0); opt.step(); m.eval()
        with torch.no_grad(): v=lossfn(m(xv),yv,sd).item()
        if v<best: best,ep,stale=v,e,0
        else: stale+=1
        if stale>=45: break
    req(ep>0 and math.isfinite(best),"no finite early-stop epoch"); return ep

def fitfixed(x,y,xt,seed,epochs):
    setseed(seed); m=Net(); opt=torch.optim.AdamW(m.parameters(),lr=.002,weight_decay=.0001)
    x,y=[torch.as_tensor(z,dtype=torch.float32) for z in (x,y)]
    sd=torch.as_tensor(np.maximum(np.std(y.numpy(),axis=0),1e-12),dtype=torch.float32)
    for _ in range(int(epochs)):
        m.train(); opt.zero_grad(set_to_none=True); l=lossfn(m(x),y,sd); l.backward()
        torch.nn.utils.clip_grad_norm_(m.parameters(),5.0); opt.step()
    m.eval()
    with torch.no_grad(): return m(torch.as_tensor(xt,dtype=torch.float32)).numpy().astype(float)

def fit_pscale(x,p,outer,test,inners):
    cand=[]
    for al in (.1,1.,10.):
      for ga in (.1,1.):
        vals=[]
        for tr,va in inners:
            xf=Xform().fit(x[tr]); sy=StandardScaler().fit(p[tr])
            kr=KernelRidge(alpha=al,kernel="rbf",gamma=ga).fit(xf.transform(x[tr]),sy.transform(p[tr]))
            vals.append(float(np.mean((kr.predict(xf.transform(x[va]))-sy.transform(p[va]))**2)))
        cand.append({"alpha":al,"gamma":ga,"inner_mse":vals,"mean_mse":float(np.mean(vals))})
    best=min(cand,key=lambda z:z["mean_mse"])
    xf=Xform().fit(x[outer]); sy=StandardScaler().fit(p[outer])
    kr=KernelRidge(alpha=best["alpha"],kernel="rbf",gamma=best["gamma"]).fit(xf.transform(x[outer]),sy.transform(p[outer]))
    y=sy.inverse_transform(kr.predict(xf.transform(x[[test]])))[0]; clipped=int(np.sum(y<0))
    return np.maximum(y,0),{"alpha":best["alpha"],"gamma":best["gamma"],"grid":cand,"negative_clip_count":clipped}

def folds(ids):
    result=[]
    for no,testid in enumerate(ids,1):
        trids=[z for z in ids if z!=testid]; x=np.zeros((len(trids),1)); inner=[]
        for ti,vi in GroupKFold(n_splits=3).split(x,groups=trids):
            tr=[trids[int(i)] for i in ti]; va=[trids[int(i)] for i in vi]
            req(not(set(tr)&set(va)) and set(tr)|set(va)==set(trids),"inner geometry leak")
            inner.append((tr,va))
        result.append((no,testid,trids,inner))
    return result

def met(ct,cp,et,ep,at,ap,pt,pp):
    mask=at>=THRESHOLD; req(mask.any(),"no significant true absolute power")
    return {"state_relative_rmse":float(np.sqrt(np.sum(abs(cp-ct)**2)/max(np.sum(abs(ct)**2),1e-30))),
      "routing_eta_rmse":float(np.sqrt(np.mean((ep-et)**2))),
      "absolute_order_source_normalized_rmse":float(np.sqrt(np.mean((ap-at)**2))),
      "thresholded_absolute_order_relative_median":float(np.median(abs(ap[mask]-at[mask])/np.maximum(at[mask],1e-30))),
      "total_power_relative_rmse":float(np.sqrt(np.mean(((pp-pt)/np.maximum(pt,1e-30))**2)))}

def summ(a):
    a=np.asarray(a,float); return {"median":float(np.median(a)),"q95":float(np.quantile(a,.95)),"max":float(np.max(a)),"min":float(np.min(a)),"mean":float(np.mean(a))}

def pear(a,b): return float(np.corrcoef(np.ravel(a),np.ravel(b))[0,1])

def run(data):
    ids=data["ids"]; ix={v:i for i,v in enumerate(ids)}; n=len(ids); nw=len(WLS)
    c=data["chat"]; x=data["geometry"]; p=data["pscale"]
    pred=np.full((3,n,nw,7,2),np.nan+1j*np.nan,complex); phat=np.full((n,nw),np.nan)
    logs=[]
    for no,testid,trids,inner_ids in folds(ids):
        test=ix[testid]; outer=[ix[z] for z in trids]
        pcas,y=pcasfit(c,outer); inner=[]
        for trids0,vaids0 in inner_ids: inner.append(([ix[z] for z in trids0],[ix[z] for z in vaids0]))
        sl={}
        for si,seed in enumerate((0,1,2)):
            eps=[]
            for tr,va in inner:
                xf=Xform().fit(x[tr]); ip,iy=pcasfit(c,tr)
                eps.append(fitstop(xf.transform(x[tr]),iy,xf.transform(x[va]),scores(c,va,ip),seed))
            ep=int(statistics.median(eps)); xf=Xform().fit(x[outer])
            pred[si,test]=decode(fitfixed(xf.transform(x[outer]),y,xf.transform(x[[test]]),seed,ep),pcas)[0]
            sl[str(seed)]={"inner_best_epochs":eps,"refit_epochs":ep}
        phat[test],plog=fit_pscale(x,p,outer,test,inner)
        logs.append({"outer_fold":no,"heldout":testid,"seeds":sl,"p_scale":plog})
    req(np.isfinite(pred.real).all() and np.isfinite(pred.imag).all() and np.isfinite(phat).all(),"nonfinite OOF")
    pm=pred.mean(axis=0); etahat=np.zeros_like(data["eta"]); abhat=np.zeros_like(data["absolute"])
    for g in range(n):
        modal=data["weights"][g,:,:,None]*np.abs(pm[g])**2
        q=modal.sum(axis=-1); etahat[g]=q/np.maximum(q.sum(axis=-1,keepdims=True),1e-30)
        abhat[g]=etahat[g]*phat[g,:,None]
    rows=[{"case_id":ids[g],**met(c[g],pm[g],data["eta"][g],etahat[g],data["absolute"][g],abhat[g],p[g],phat[g])} for g in range(n)]
    keys=[k for k in rows[0] if k!="case_id"]; summary={k:summ([r[k] for r in rows]) for k in keys}
    seedmed={}
    for si,s in enumerate((0,1,2)):
        seedmed[str(s)]=float(np.median([met(c[g],pred[si,g],data["eta"][g],data["eta"][g],data["absolute"][g],data["absolute"][g],p[g],p[g])["state_relative_rmse"] for g in range(n)]))
    seedstd=float(np.std(list(seedmed.values())))
    gates={"state":summary["state_relative_rmse"]["median"]<=.5 and summary["state_relative_rmse"]["q95"]<=.8,
      "routing":summary["routing_eta_rmse"]["median"]<=.05 and summary["routing_eta_rmse"]["q95"]<=.1 and pear(data["eta"],etahat)>=.95,
      "absolute_order":summary["absolute_order_source_normalized_rmse"]["median"]<=.05 and summary["absolute_order_source_normalized_rmse"]["q95"]<=.1,
      "thresholded_absolute_order":summary["thresholded_absolute_order_relative_median"]["median"]<=.3 and summary["thresholded_absolute_order_relative_median"]["q95"]<=.75,
      "total_power":summary["total_power_relative_rmse"]["median"]<=.15 and summary["total_power_relative_rmse"]["q95"]<=.3 and pear(p,phat)>=.95,
      "seed_stability":seedstd<=.03}
    result={"geometry_count":n,"wavelength_count_per_geometry":nw,"solver_invocations":0,"gpu_used_for_training":False,
      "model":"PW_K6_STRUCTURED_FORWARD_MODEL_V1/M5 width 32","pscale_model":"PW_K6_PSCALE_MODEL_V1/RBF KernelRidge",
      "metrics":summary,"routing_pearson":pear(data["eta"],etahat),"pscale_pearson":pear(p,phat),
      "seed_state_medians":seedmed,"seed_state_median_std":seedstd,"gates":gates,
      "retrospective_h1":"PASS" if all(gates.values()) else "FAIL","per_geometry":rows,"fold_logs":logs}
    arrays={"pred_c_hat_seed":pred,"pred_c_hat_mean":pm,"pred_pscale":phat,"pred_eta":etahat,"pred_absolute_order":abhat}
    return result,arrays
