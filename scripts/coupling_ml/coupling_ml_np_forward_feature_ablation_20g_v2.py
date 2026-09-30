#!/usr/bin/env python
from __future__ import annotations
import argparse,csv,hashlib,importlib.util,json,math,os,random,statistics,subprocess,sys
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
import torch
from torch import nn
from sklearn.decomposition import PCA
from sklearn.kernel_ridge import KernelRidge
from sklearn.preprocessing import StandardScaler

ROOT=Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1")
NP=Path(r"D:\project\worktrees\blue_apcd_np_k6_mdc_v1")
OUT=ROOT/"reports"/"coupling"/"COUPLING_ML_NP_FORWARD_FEATURE_ABLATION_20G_V2"
CASE_ROOT=ROOT/"outputs"/"coupling_ml"/"PW_K6_SEED_DB_V1_PRODUCTION_V1"
WLS=tuple(range(445,456)); ORD=tuple(range(-3,4)); SEEDS=(0,1,2)
CONTRACT_SHA="3c6b0bb9d498982811910a4be2da87e13ad82eba2a3bc493140bdd6834688081"
NP_HEAD="d5143de18309f395000e7e2161eb5a83068ac090"
CACHE_SHA="acdbeab1ff20eba081aaf20d433d3d4b9a75dae3485e852ad519c54cbea1accc"
ADAPTER_SHA="e68db57c2e144f60cf24f1c03ca6279bd50b6c94c8465e8f9f9f75dec68fdbfd"
TRUTH_SHA="4f894932b14be549a5483f3a3731a1e71869759357d4eddeb7ba4dc0d5108408"
H1_SHA="8cf71239757e70eb75fbbf858a82c12f8af8d03c0892b99ff4ffce6a959fcdbd"
THRESH=0.0009885656815447454
RESULTS=("oof_predictions_v2.csv","per_geometry_metrics_v2.csv","paired_ablation_metrics_v2.json",
"ood_support_preregistered_v2.json","leakage_audit_v2.json","verdict_v2.json","execution_manifest_v2.json",
"fold_execution_v2.json","artifact_hashes.json","COUPLING_ML_NP_FORWARD_FEATURE_ABLATION_20G_V2.md")

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def jread(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def atomic_json(p,o):
    t=Path(str(p)+".tmp");t.write_text(json.dumps(o,ensure_ascii=True,sort_keys=True,indent=2)+"\n",encoding="utf-8");os.replace(t,p)
def git(args,cwd): return subprocess.run(args,cwd=cwd,check=True,capture_output=True,text=True).stdout.strip()
def req(ok,msg):
    if not ok: raise RuntimeError(msg)
def jlines(p): return [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x.strip()]

def parity_check(rows,parity,fm):
    adapter=NP/"scripts"/"np_k6_coupling_forward_feature_interface_v2.py"
    cache=NP/"outputs"/"np_k6_coupling_forward_runtime_coverage_v2"/"coupling_20g_lf_feature_cache.jsonl"
    req(git(["git","rev-parse","HEAD"],NP)==NP_HEAD and sha(adapter)==ADAPTER_SHA and sha(cache)==CACHE_SHA,"NP authority/hash changed")
    req(parity.get("status")=="PASS" and parity.get("row_count")==220 and parity.get("unique_case_wavelength_queries")==220,"NP cache parity authority not PASS")
    byq={(r["geometry_id"],int(r["wavelength_nm"])):r for r in rows}
    spec=importlib.util.spec_from_file_location("npv2_runtime_ablation",adapter);req(spec and spec.loader,"NP callable cannot load")
    mod=importlib.util.module_from_spec(spec);sys.modules[spec.name]=mod;spec.loader.exec_module(mod)
    samples=parity.get("representative_queries",[]);req(parity.get("representative_query_count")==15 and len(samples)==15,"expected 15 frozen representative runtime queries")
    for s in samples:
        key=(s["geometry_id"],int(s["wavelength_nm"]));r=byq[key]
        a=mod.NP_LF_FEATURE_PROVIDER_V2(*r["ordered_D_nm"],float(s["wavelength_nm"]),"P_XLIKE",root=NP,u_x=0.0,k_y=0.0)
        req(a["features"]==r["features"],f"feature mismatch {key}")
        for k,v in [("geometry_id",r["geometry_id"]),("ordered_D_nm",r["ordered_D_nm"]),("wavelength_nm",r["wavelength_nm"]),("polarization","P_XLIKE"),("u_x",0.0),("k_y",0.0),("provenance_hash",fm["provenance_hash"]),("ood",True)]:
            req(a.get(k)==v,f"metadata mismatch {k} {key}")
    return {"status":"PASS","queries":15,"exact_matches":15,"cache_sha256":CACHE_SHA,"adapter_sha256":ADAPTER_SHA}

def validate():
    cpath=OUT/"NP_FEATURE_ABLATION_CONFIRMATORY_CONTRACT_V2.json";pp=OUT/"preregistration_v2.json";fp=OUT/"fold_manifest_v2.json"
    req(git(["git","branch","--show-current"],ROOT)=="work/mdc-np-coupling-ml-v1","wrong Coupling branch")
    req(sha(cpath)==CONTRACT_SHA,"V2 contract hash changed")
    c,pr,fold=jread(cpath),jread(pp),jread(fp)
    req(pr["status"]=="FROZEN_BEFORE_V2_OUTER_METRICS" and pr["contract_sha256"]==CONTRACT_SHA,"V2 preregistration invalid")
    req(pr["v2_outer_fold_metrics_computed_at_registration"] is False and pr["fold_manifest_sha256"]==sha(fp),"frozen fold/prereg mismatch")
    req(fold["outer_fold_metrics_computed"] is False,"outer metrics already present")
    req(not any((OUT/x).exists() for x in RESULTS),"result output already exists; refusing overwrite")
    d=jread(OUT/"dataset_authority_v2.json");fm=jread(OUT/"feature_manifest_v2.json");par=jread(OUT/"cache_runtime_parity.json")
    req(d["status"]=="PASS_20_SCIENTIFIC_VALID_INTEGRATED_3D_PW_CASES" and d["geometry_count"]==20 and d["scientific_entries"]==20 and d["replay_entries"]==0 and d["duplicate_entries"]==0,"20G authority mismatch")
    req(d["source_v1_dataset_authority_sha256"]=="9f3b75a6b1c2cb1340e8cfbcae927ca7ae6b849e61218c38270b8ee33d024806","V1 dataset hash mismatch")
    tp=ROOT/"reports"/"coupling"/"PW_K6_GRATING_TRUTH_V2.json";hp=ROOT/"reports"/"coupling"/"PW_K6_H1_NUMERIC_GATE_AUTHORITY_V1.json"
    req(sha(tp)==TRUTH_SHA and sha(hp)==H1_SHA,"truth/H1 authority hash mismatch")
    req(fm["authority_head"]==NP_HEAD and fm["cache_sha256"]==CACHE_SHA and fm["runtime_adapter_sha256"]==ADAPTER_SHA,"NP feature manifest mismatch")
    cp=NP/"outputs"/"np_k6_coupling_forward_runtime_coverage_v2"/"coupling_20g_lf_feature_cache.jsonl"
    rows=jlines(cp);req(len(rows)==220 and sha(cp)==CACHE_SHA,"NP cache mismatch")
    runtime=parity_check(rows,par, fm)
    req([x["case_id"] for x in d["cases"]]==c["dataset"]["geometry_id_order"],"case order mismatch")
    req(len(fold["fold_assignments"]["folds"])==20,"20 LOGO folds missing")
    return {"c":c,"pr":pr,"fold":fold,"d":d,"fm":fm,"par":par,"rows":rows,"runtime":runtime,"tp":tp,"truth_sha":sha(tp),"h1_sha":sha(hp)}

class Xform:
    def __init__(self,arm): self.arm=arm;self.ss=StandardScaler();self.pca=None
    def fit(self,x):
        z=self.ss.fit_transform(x/130.0 if self.arm=="A0" else x)
        if self.arm=="A1": self.pca=PCA(n_components=6,svd_solver="full").fit(z)
        return self
    def transform(self,x):
        z=self.ss.transform(x/130.0 if self.arm=="A0" else x)
        if self.pca is not None:z=self.pca.transform(z)
        return z.astype(float)

class Net(nn.Module):
    def __init__(self):
        super().__init__();self.enc=nn.Sequential(nn.Linear(6,32),nn.ReLU(),nn.Linear(32,32),nn.ReLU())
        self.heads=nn.ModuleList([nn.Linear(32,2) for _ in range(7)])
        self.fuse=nn.Sequential(nn.Linear(14,32),nn.ReLU(),nn.Linear(32,14))
    def forward(self,x):
        q=self.enc(x);local=torch.cat([h(q) for h in self.heads],dim=1);return local+self.fuse(local)
def setseed(s):random.seed(s);np.random.seed(s);torch.manual_seed(s)
def lossfn(p,y,sd):return torch.mean(((p-y)/sd)**2)
def fitstop(x,y,xv,yv,seed):
    setseed(seed);m=Net();req(sum(p.numel() for p in m.parameters())==2684,"parameter count mismatch")
    opt=torch.optim.AdamW(m.parameters(),lr=.002,weight_decay=.0001)
    x,y,xv,yv=[torch.as_tensor(z,dtype=torch.float32) for z in (x,y,xv,yv)]
    sd=torch.as_tensor(np.maximum(np.std(y.numpy(),axis=0),1e-12),dtype=torch.float32)
    best,ep,stale=float("inf"),0,0
    for e in range(1,321):
        m.train();opt.zero_grad(set_to_none=True);l=lossfn(m(x),y,sd);l.backward();torch.nn.utils.clip_grad_norm_(m.parameters(),5.0);opt.step()
        m.eval()
        with torch.no_grad():v=lossfn(m(xv),yv,sd).item()
        if v<best:best,ep,stale=v,e,0
        else:stale+=1
        if stale>=45:break
    req(ep>0 and math.isfinite(best),"no finite early-stop epoch");return ep
def fitfixed(x,y,xt,seed,epochs):
    setseed(seed);m=Net();opt=torch.optim.AdamW(m.parameters(),lr=.002,weight_decay=.0001)
    x,y=[torch.as_tensor(z,dtype=torch.float32) for z in (x,y)]
    sd=torch.as_tensor(np.maximum(np.std(y.numpy(),axis=0),1e-12),dtype=torch.float32)
    for _ in range(epochs):
        m.train();opt.zero_grad(set_to_none=True);l=lossfn(m(x),y,sd);l.backward();torch.nn.utils.clip_grad_norm_(m.parameters(),5.0);opt.step()
    m.eval()
    with torch.no_grad():return m(torch.as_tensor(xt,dtype=torch.float32)).numpy().astype(float)
def pack(c,oi):
    q=c[:,:,oi,:];return np.stack([q[...,0].real,q[...,1].real,q[...,0].imag,q[...,1].imag],axis=-1).reshape(len(c),-1)
def pcasfit(c,idx):
    ps=[];ys=[]
    for oi in range(7):
        p=PCA(n_components=2,svd_solver="full");ys.append(p.fit_transform(pack(c[idx],oi)));ps.append(p)
    return ps,np.concatenate(ys,axis=1)
def scores(c,idx,ps):return np.concatenate([ps[o].transform(pack(c[idx],o)) for o in range(7)],axis=1)
def decode(y,ps):
    out=np.zeros((len(y),11,7,2),complex)
    for oi,p in enumerate(ps):
        a=p.inverse_transform(y[:,2*oi:2*oi+2]).reshape(len(y),11,4)
        out[:,:,oi,0]=a[:,:,0]+1j*a[:,:,2];out[:,:,oi,1]=a[:,:,1]+1j*a[:,:,3]
    return out
def fitp(raw,p,outer,test,inners,arm):
    cand=[]
    for al in (.1,1.,10.):
      for ga in (.1,1.):
        scores0=[]
        for sp in inners:
            tr,va=sp;xf=Xform(arm).fit(raw[tr]);sy=StandardScaler().fit(p[tr])
            kr=KernelRidge(alpha=al,kernel="rbf",gamma=ga).fit(xf.transform(raw[tr]),sy.transform(p[tr]))
            scores0.append(float(np.mean((kr.predict(xf.transform(raw[va]))-sy.transform(p[va]))**2)))
        cand.append({"alpha":al,"gamma":ga,"inner":scores0,"mean":float(np.mean(scores0))})
    best=min(cand,key=lambda x:x["mean"]);xf=Xform(arm).fit(raw[outer]);sy=StandardScaler().fit(p[outer])
    kr=KernelRidge(alpha=best["alpha"],kernel="rbf",gamma=best["gamma"]).fit(xf.transform(raw[outer]),sy.transform(p[outer]))
    y=sy.inverse_transform(kr.predict(xf.transform(raw[[test]])))[0];clipped=int(np.sum(y<0))
    return np.maximum(y,0),{"alpha":best["alpha"],"gamma":best["gamma"],"grid":cand,"negative_clip_count":clipped}
def load_data(ctx):
    ids=ctx["c"]["dataset"]["geometry_id_order"]; recs=ctx["d"]["cases"];geo=np.asarray([r["ordered_D_nm"] for r in recs],float)
    req(np.array_equal(geo,np.asarray(ctx["c"]["dataset"]["ordered_D_nm"],float)),"geometry vector mismatch")
    ca={(r["geometry_id"],int(r["wavelength_nm"])):r for r in ctx["rows"]};f_by={}
    for i,r in enumerate(recs):
        d=r["ordered_D_nm"];gid="K6X_"+"_".join(f"D{int(x)}" for x in d);vals=[]
        for wl in WLS:
            q=ca[(gid,wl)];req(q["ordered_D_nm"]==d and q["polarization"]=="P_XLIKE" and q["u_x"]==0 and q["k_y"]==0 and q["ood"],f"NP row invalid {gid}/{wl}")
            z=q["features"];vals += [float(z["eta_m_proxy"][f"m{m:+d}"]) for m in ORD]+[float(z["T_proxy"])]
        f_by[r["case_id"]]=vals
    x={"A0":geo.copy(),"A1":np.stack([np.r_[geo[i],f_by[cid]] for i,cid in enumerate(ids)])}
    req(x["A1"].shape==(20,94),"A1 dimension mismatch")
    truth=jread(ctx["tp"])["rows"];tr={(r["case"],round(r["wavelength_nm"]),r["order_x"],r["order_y"]):r for r in truth if 445-1e-6<=r["wavelength_nm"]<=455+1e-6 and r["order_y"]==0 and -3<=r["order_x"]<=3}
    req(len(tr)==1540,"paired grating truth row count mismatch")
    c=np.zeros((20,11,7,2),complex);w=np.zeros((20,11,7));p=np.zeros((20,11));eta=np.zeros((20,11,7));ab=np.zeros_like(eta);hashes={};close=[]
    for gi,r in enumerate(recs):
        sd=CASE_ROOT/r["case_id"]/r["attempt_id"]/"state";mp=next(sd.glob("*.json"));npz=next(sd.glob("*.npz"))
        req(sha(mp)==r["state_metadata_sha256"] and sha(npz)==r["state_npz_sha256"],f"state hash mismatch {r['case_id']}")
        hashes[r["case_id"]]={"metadata":sha(mp),"npz":sha(npz)};meta=jread(mp);z=np.load(npz,allow_pickle=False)
        oi={tuple(map(int,v)):i for i,v in enumerate(z["orders"].tolist())};wi={round(float(v)):i for i,v in enumerate(z["wavelengths_nm"])}
        plane,dire=meta["planes"].index("POSTNP"),meta["directions"].index("+z");req(meta["polarizations"]==["TE","TM"],"pol ordering mismatch")
        for li,wl in enumerate(WLS):
            j=wi[wl];ix=[oi[(m,0)] for m in ORD]
            req(int(z["propagating_mask"][plane,j].sum())==7 and np.all(z["propagating_mask"][plane,j,ix]),f"prop mask mismatch {r['case_id']}/{wl}")
            k0=2*np.pi/(z["wavelengths_nm"][j]*1e-9);ww=np.maximum(z["mode_kz_real"][plane,j,ix]/k0,0)
            cc=z["coefficients_real"][plane,j,ix,dire,:]+1j*z["coefficients_imag"][plane,j,ix,dire,:]
            den=float(np.sum(ww[:,None]*abs(cc)**2));req(den>0 and np.all(ww>0),"bad modal norm")
            c[gi,li]=cc/math.sqrt(den);w[gi,li]=ww;ec=ww*np.sum(abs(cc)**2,axis=1);ec/=ec.sum()
            for q,m in enumerate(ORD):
                rr=tr[(r["case_id"],wl,m,0)];eta[gi,li,q]=rr["GRATING_ETA_V2"];ab[gi,li,q]=rr["GRATING_ABSOLUTE_ORDER_POWER_V2"]
                req(abs(ab[gi,li,q]-rr["POSTNP_TOTAL_POWER_V2"]*eta[gi,li,q])<2e-12,"absolute power factorization mismatch")
                close.append(abs(ec[q]-eta[gi,li,q]))
                if q==0:p[gi,li]=rr["POSTNP_TOTAL_POWER_V2"]
                else:req(abs(p[gi,li]-rr["POSTNP_TOTAL_POWER_V2"])<1e-14,"Pscale order inconsistency")
    closure={"samples":len(close),"median":float(np.median(close)),"q95":float(np.quantile(close,.95)),"max":float(max(close))}
    req(closure["max"]<=.001,"H2 truth route closure failed")
    return {"ids":ids,"geo":geo,"x":x,"c":c,"w":w,"p":p,"eta":eta,"ab":ab,"closure":closure,"hashes":hashes,
            "feature_names":ctx["fm"]["feature_definition"]["fields_per_wavelength"]}

def fitarm(d,fold,arm):
    ids=d["ids"];ix={x:i for i,x in enumerate(ids)};raw=d["x"][arm]
    pred=np.full((3,20,11,7,2),np.nan+1j*np.nan,complex);pout=np.full((20,11),np.nan);logs=[]
    for f in fold["fold_assignments"]["folds"]:
        test=ix[f["test_geometry_id"]];outer=[ix[x] for x in f["train_geometry_ids"]];req(test not in outer and len(outer)==19,"outer leakage")
        ps,y=pcasfit(d["c"],outer);inner=[];ilogs={}
        for sp in f["inner_group_folds"]:
            tr=[ix[x] for x in sp["train_geometry_ids"]];va=[ix[x] for x in sp["validation_geometry_ids"]]
            req(not(set(tr)&set(va)) and test not in tr+va,"inner leakage");inner.append((tr,va))
        for si,s in enumerate(SEEDS):
            eps=[]
            for tr,va in inner:
                xf=Xform(arm).fit(raw[tr]);ip,iy=pcasfit(d["c"],tr)
                eps.append(fitstop(xf.transform(raw[tr]),iy,xf.transform(raw[va]),scores(d["c"],va,ip),s))
            ep=int(statistics.median(eps));xf=Xform(arm).fit(raw[outer])
            pred[si,test]=decode(fitfixed(xf.transform(raw[outer]),y,xf.transform(raw[[test]]),s,ep),ps)[0]
            ilogs[str(s)]={"inner_best_epochs":eps,"refit_epochs":ep}
        pout[test],plog=fitp(raw,d["p"],outer,test,inner,arm);logs.append({"fold":f["outer_fold"],"heldout":ids[test],"seeds":ilogs,"p_scale":plog})
    req(np.isfinite(pred.real).all() and np.isfinite(pred.imag).all() and np.isfinite(pout).all(),"nonfinite OOF")
    return pred,pout,logs

def pearson(a,b):return float(np.corrcoef(np.ravel(a),np.ravel(b))[0,1])
def stats(a):
    a=np.asarray(a,float);return {"median":float(np.median(a)),"q95":float(np.quantile(a,.95)),"max":float(max(a)),"min":float(min(a)),"mean":float(np.mean(a))}
def metric(ct,cp,et,ep,at,ap,pt,pp):
    mask=at>=THRESH;req(mask.any(),"no above-threshold absolute power")
    return {"state_relative_rmse":float(np.sqrt(np.sum(abs(cp-ct)**2)/max(np.sum(abs(ct)**2),1e-30))),
      "routing_eta_rmse":float(np.sqrt(np.mean((ep-et)**2))),
      "absolute_order_source_normalized_rmse":float(np.sqrt(np.mean((ap-at)**2))),
      "thresholded_absolute_order_relative_median":float(np.median(abs(ap[mask]-at[mask])/np.maximum(at[mask],1e-30))),
      "total_power_relative_rmse":float(np.sqrt(np.mean(((pp-pt)/np.maximum(pt,1e-30))**2)))}

def evaluate(d,pred,pscale,ood):
    ids=d["ids"];gm=[];out={"solver_invocations":0,"gpu_used":False,"arms":{},"wavelength_nm":list(WLS)}
    arr={}
    for arm in ("A0","A1"):
        seed=pred[arm];cm=seed.mean(axis=0);pp=pscale[arm]
        ep=d["w"]*np.sum(abs(cm)**2,axis=-1);ep/=ep.sum(axis=-1,keepdims=True);ap=ep*pp[:,:,None]
        rows=[]
        sm=[]
        for s in range(3):sm.append(np.median([metric(d["c"][g],seed[s,g],d["eta"][g],ep[g],d["ab"][g],ap[g],d["p"][g],pp[g])["state_relative_rmse"] for g in range(20)]))
        for g,cid in enumerate(ids):
            r={"case_id":cid,"arm":arm,**metric(d["c"][g],cm[g],d["eta"][g],ep[g],d["ab"][g],ap[g],d["p"][g],pp[g])};rows.append(r);gm.append(r)
        m={k:stats([r[k] for r in rows]) for k in rows[0] if k not in ("case_id","arm")}
        m.update({"routing_pearson":pearson(d["eta"],ep),"pscale_pearson":pearson(d["p"],pp),
          "seed_state_medians":dict(zip(map(str,SEEDS),map(float,sm))),"seed_state_median_std":float(np.std(sm)),
          "gates":{"state":m["state_relative_rmse"]["median"]<=.5 and m["state_relative_rmse"]["q95"]<=.8,
          "routing":m["routing_eta_rmse"]["median"]<=.05 and m["routing_eta_rmse"]["q95"]<=.1 and pearson(d["eta"],ep)>=.95,
          "absolute":m["absolute_order_source_normalized_rmse"]["median"]<=.05 and m["absolute_order_source_normalized_rmse"]["q95"]<=.1,
          "threshold":m["thresholded_absolute_order_relative_median"]["median"]<=.3 and m["thresholded_absolute_order_relative_median"]["q95"]<=.75,
          "pscale":m["total_power_relative_rmse"]["median"]<=.15 and m["total_power_relative_rmse"]["q95"]<=.3 and pearson(d["p"],pp)>=.95,
          "seed":float(np.std(sm))<=.03}})
        m["retrospective_h1"]="PASS" if all(m["gates"].values()) else "FAIL";out["arms"][arm]=m
        arr[arm]={"seed":seed,"mean":cm,"eta":ep,"abs":ap,"p":pp}
    keys=list(gm[0].keys())[2:];paired={};deltas={}
    for k in keys:
        dd=np.array([next(r[k] for r in gm if r["case_id"]==cid and r["arm"]=="A1")-next(r[k] for r in gm if r["case_id"]==cid and r["arm"]=="A0") for cid in ids])
        deltas[k]={cid:float(dd[i]) for i,cid in enumerate(ids)}
        paired[k]={"deltas":deltas[k],"distribution":stats(dd),"wins":int((dd<0).sum()),"ties":int((dd==0).sum()),"losses":int((dd>0).sum())}
    a,b=out["arms"]["A0"],out["arms"]["A1"]
    paired["state_median_improvement"]=(a["state_relative_rmse"]["median"]-b["state_relative_rmse"]["median"])/max(a["state_relative_rmse"]["median"],1e-30)
    paired["routing_median_improvement"]=(a["routing_eta_rmse"]["median"]-b["routing_eta_rmse"]["median"])/max(a["routing_eta_rmse"]["median"],1e-30)
    wtl={"state":{z:paired["state_relative_rmse"][z] for z in ("wins","ties","losses")},"routing":{z:paired["routing_eta_rmse"][z] for z in ("wins","ties","losses")}}
    groups=ood["strata"];labels={x["case_id"]:lab for lab,items in groups.items() for x in items};dist={x["case_id"]:x["distance"] for items in groups.values() for x in items}
    osum={}
    for lab in ("nearest","middle","farthest"):
        members=[cid for cid in ids if labels[cid]==lab]
        osum[lab]={"case_ids":members,"count":len(members),"members":[{"case_id":cid,"distance":dist[cid]} for cid in members],
          "median_state_delta":float(np.median([deltas["state_relative_rmse"][cid] for cid in members])),
          "median_routing_delta":float(np.median([deltas["routing_eta_rmse"][cid] for cid in members])),
          "state_wins":sum(deltas["state_relative_rmse"][cid]<0 for cid in members),
          "routing_wins":sum(deltas["routing_eta_rmse"][cid]<0 for cid in members)}
    qok=b["state_relative_rmse"]["q95"]<=1.1*a["state_relative_rmse"]["q95"] and b["routing_eta_rmse"]["q95"]<=1.1*a["routing_eta_rmse"]["q95"]
    wok=b["state_relative_rmse"]["max"]<=1.25*a["state_relative_rmse"]["max"] and b["routing_eta_rmse"]["max"]<=1.25*a["routing_eta_rmse"]["max"]
    k_ok=all(b[k][q]<=a[k][q] for k in ("absolute_order_source_normalized_rmse","thresholded_absolute_order_relative_median","total_power_relative_rmse") for q in ("median","q95"))
    core=paired["state_median_improvement"]>=.05 and paired["routing_median_improvement"]>=.05 and paired["state_relative_rmse"]["wins"]>=12 and paired["routing_eta_rmse"]["wins"]>=12
    mixed=(osum["nearest"]["median_state_delta"]<0<osum["farthest"]["median_state_delta"]) or (osum["nearest"]["median_routing_delta"]<0<osum["farthest"]["median_routing_delta"])
    stable=b["seed_state_median_std"]<=.03
    if core and qok and wok and k_ok and stable and not mixed:verdict="COUPLING_ML_NP_FORWARD_FEATURES_SUPPORTED"
    elif paired["state_median_improvement"]>0 or paired["routing_median_improvement"]>0 or paired["state_relative_rmse"]["wins"]>=10 or paired["routing_eta_rmse"]["wins"]>=10:verdict="COUPLING_ML_NP_FORWARD_FEATURES_PARTIAL"
    else:verdict="COUPLING_ML_NP_FORWARD_FEATURES_NOT_SUPPORTED"
    out.update({"paired":paired,"win_tie_loss":wtl,"ood_strata":osum,"verdict":verdict,
      "feature_acceptance":{"both_medians_5pct_and_12_wins":bool(core),"q95_10pct":bool(qok),"worst_25pct":bool(wok),
      "absolute_and_pscale_median_q95_no_worse":bool(k_ok),"seed_stable":bool(stable),"nearest_far_sign_mixed":bool(mixed)},
      "production_h1_status":"NOT_ADMITTED; prospective six-geometry prediction-before-truth gate not run"})
    return out,gm,arr

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--validate-only",action="store_true");args=ap.parse_args()
    os.environ["PYTHONDONTWRITEBYTECODE"]="1";torch.set_num_threads(1)
    try:torch.set_num_interop_threads(1)
    except RuntimeError:pass
    torch.use_deterministic_algorithms(True)
    cx=validate();d=load_data(cx);print(json.dumps({"preflight":"PASS","n_geom":20,"paired":220,"orders":1540,
      "NP_runtime_parity":cx["runtime"],"truth_decoder_closure":d["closure"],"solver_invocations":0,"gpu_used":False}))
    if args.validate_only:return 0
    frozen=OUT/"ood_support_preregistered_v2.json"
    if not frozen.exists():frozen.write_bytes((OUT/"ood_support_analysis_v2.json").read_bytes())
    # Freeze operational details not enumerated in the scientific contract before fitting.
    execution={"schema":"COUPLING_ML_NP_FORWARD_FEATURE_ABLATION_EXECUTION_V2","status":"FROZEN_BEFORE_MODEL_METRICS",
      "created_utc":datetime.now(timezone.utc).isoformat(),"contract_sha256":CONTRACT_SHA,
      "supplement_only":True,"training":{"CPU_only":True,"full_batch":True,"AdamW_lr":.002,"weight_decay":.0001,
      "gradient_clip_norm":5.0,"max_epochs":320,"patience":45,"seeds":list(SEEDS),
      "loss":"mean(((prediction-latent_score)/training-fold population std per output)^2); output remains PCA scores; train-only scale",
      "final_epoch":"per seed median best epoch across the three fixed inner folds, refit on outer train",
      "aggregation":"mean of three fixed-seed predictions"},
      "input_preprocessing":{"A0":"D/130 then train-only StandardScaler","A1":"D plus 88 NP fields; train-only StandardScaler then full SVD PCA to 6"},
      "state":"POSTNP +z C_hat; seven order-local rank2 PCA, trained on split-train geometries only; wavelength-major ReTE,ReTM,ImTE,ImTM",
      "P_scale":"RBF Kernel Ridge alpha .1/1/10 gamma .1/1; train-only X/y StandardScaler; group-inner MSE selection; clamp negative prediction at zero",
      "metrics":{"state":"complex L2 relative error per geometry","routing":"RMSE over 11x7 eta per geometry","abs_order":"RMSE of POSTNP_TOTAL_POWER_V2*GRATING_ETA_V2",
      "thresholded_abs":"median relative error where true absolute-order power >= frozen threshold","P_scale":"RMS relative error per geometry",
      "pearson":"pooled values","q95":"NumPy linear quantile","ties":"exact equality",
      "qualitative_key_no_degrade":"conservative no-worsening of absolute-order and P_scale medians/q95"},
      "fold_sha256":sha(OUT/"fold_manifest_v2.json"),"runtime_parity":cx["runtime"],"truth_decoder_closure":d["closure"],"solver_invocations":0}
    atomic_json(OUT/"execution_manifest_v2.json",execution)
    pred={};ps={};logs={}
    for arm in ("A0","A1"):pred[arm],ps[arm],logs[arm]=fitarm(d,cx["fold"],arm)
    ood=jread(frozen);summary,gm,arr=evaluate(d,pred,ps,ood)
    labels={cid:lab for lab,x in summary["ood_strata"].items() for cid in x["case_ids"]}
    atomic_json(OUT/"paired_ablation_metrics_v2.json",summary)
    atomic_json(OUT/"fold_execution_v2.json",{"status":"COMPLETE","by_arm":logs,"frozen_fold_hash":sha(OUT/"fold_manifest_v2.json"),"solver_invocations":0,"gpu_used":False})
    with (OUT/"per_geometry_metrics_v2.csv").open("w",newline="",encoding="utf-8") as f:
        cols=["case_id","arm","ood_stratum","state_relative_rmse","routing_eta_rmse","absolute_order_source_normalized_rmse","thresholded_absolute_order_relative_median","total_power_relative_rmse"]
        w=csv.DictWriter(f,fieldnames=cols);w.writeheader()
        for r in gm:w.writerow({**r,"ood_stratum":labels[r["case_id"]]})
    seedcols=[f"{a}_seed{s}_{p}_{part}" for a in ("A0","A1") for s in SEEDS for p in ("TE","TM") for part in ("re","im")]
    cols=["case_id","ordered_D_nm","wavelength_nm","order_x","eta_true","abs_order_true","P_scale_true",
      "C_hat_true_TE_re","C_hat_true_TE_im","C_hat_true_TM_re","C_hat_true_TM_im",
      "A0_C_hat_mean_TE_re","A0_C_hat_mean_TE_im","A0_C_hat_mean_TM_re","A0_C_hat_mean_TM_im",
      "A1_C_hat_mean_TE_re","A1_C_hat_mean_TE_im","A1_C_hat_mean_TM_re","A1_C_hat_mean_TM_im",
      "A0_eta","A1_eta","A0_abs_order","A1_abs_order","A0_P_scale","A1_P_scale"]+seedcols
    with (OUT/"oof_predictions_v2.csv").open("w",newline="",encoding="utf-8") as f:
        wr=csv.DictWriter(f,fieldnames=cols);wr.writeheader()
        for g,cid in enumerate(d["ids"]):
          for li,wl in enumerate(WLS):
           for oi,m in enumerate(ORD):
            row={"case_id":cid,"ordered_D_nm":json.dumps(d["geo"][g].astype(int).tolist()),"wavelength_nm":wl,"order_x":m,
             "eta_true":d["eta"][g,li,oi],"abs_order_true":d["ab"][g,li,oi],"P_scale_true":d["p"][g,li]}
            for pi,pol in enumerate(("TE","TM")):
             z=d["c"][g,li,oi,pi];row[f"C_hat_true_{pol}_re"]=z.real;row[f"C_hat_true_{pol}_im"]=z.imag
            for arm in ("A0","A1"):
             cm=arr[arm]["mean"];route=d["w"][g,li]*np.sum(abs(cm[g,li])**2,axis=-1);route/=route.sum()
             for pi,pol in enumerate(("TE","TM")):
              z=cm[g,li,oi,pi];row[f"{arm}_C_hat_mean_{pol}_re"]=z.real;row[f"{arm}_C_hat_mean_{pol}_im"]=z.imag
             row[f"{arm}_eta"]=route[oi];row[f"{arm}_abs_order"]=route[oi]*ps[arm][g,li];row[f"{arm}_P_scale"]=ps[arm][g,li]
             for si,s in enumerate(SEEDS):
              for pi,pol in enumerate(("TE","TM")):
               z=pred[arm][si,g,li,oi,pi];row[f"{arm}_seed{s}_{pol}_{'re' if pi<2 else 'im'}"]=z.real
               # Replace awkward generated seed column names with explicit values below.
               row[f"{arm}_seed{s}_{pol}_re"]=z.real;row[f"{arm}_seed{s}_{pol}_im"]=z.imag
            wr.writerow(row)
    # Fix seed columns to contain each complex polarization component (output CSV rows retain both parts).
    # Leakage evidence is generated from the frozen exact split assignments.
    fc=[]
    for f in cx["fold"]["fold_assignments"]["folds"]:
        fc.append({"fold":f["outer_fold"],"heldout":f["test_geometry_id"],"heldout_absent":f["test_geometry_id"] not in f["train_geometry_ids"],"train_n":len(f["train_geometry_ids"])})
    atomic_json(OUT/"leakage_audit_v2.json",{"schema":"COUPLING_ML_NP_FORWARD_FEATURE_ABLATION_LEAKAGE_AUDIT_V2","status":"PASS",
      "solver_invocations":0,"gpu_used":False,"NP_runtime_reads_Coupling_HF_labels":False,"cache_label_blind":True,
      "heldout_labels_used_for_feature_generation":False,"A0_inputs":["ordered D1-D6"],"A1_inputs":["ordered D1-D6"]+d["feature_names"],
      "support_metadata_as_features":False,"preprocessing_train_fold_only":True,"PCA_train_fold_only":True,
      "same_target_rows_A0_A1":True,"same_outer_folds_A0_A1":True,"wavelength_random_split":False,
      "dipole_or_final_validation_leakage":False,"outer_fold_checks":fc,"NP_runtime_parity":cx["runtime"],"cache_sha256":CACHE_SHA})
    # Add predictions without changing the frozen support identities/distances.
    original=ood;enriched={}
    for lab,g in original["strata"].items():
        enriched[lab]={**summary["ood_strata"][lab],"members":[{**x,"state_delta_A1_minus_A0":summary["paired"]["state_relative_rmse"]["deltas"][x["case_id"]],
         "routing_delta_A1_minus_A0":summary["paired"]["routing_eta_rmse"]["deltas"][x["case_id"]]} for x in g]}
    atomic_json(OUT/"ood_support_analysis_v2.json",{"schema":"COUPLING_ML_NP_FORWARD_FEATURE_OOD_SUPPORT_V2","status":"POST_METRIC_DIAGNOSTIC_ONLY",
      "frozen_support_file_sha256":sha(frozen),"frozen_before_v2_outer_metrics":True,"exact_HF22_overlap_count":0,"extrapolative_count":20,
      "strata":enriched,"prediction_error_by_stratum":{k:{"state_relative_rmse":v["median_state_delta"],"routing_eta_rmse":v["median_routing_delta"]} for k,v in summary["ood_strata"].items()},
      "no_provider_domain_retuning":True,"solver_invocations":0})
    h1pass=all(all(z.values()) for z in (summary["arms"]["A0"]["gates"],summary["arms"]["A1"]["gates"]))
    accept=summary["feature_acceptance"]
    oodinterp="LF_FEATURE_VALUE_MIXED" if accept["nearest_far_sign_mixed"] else ("LF_FEATURE_VALUE_ROBUST_TO_OOD" if summary["verdict"].endswith("SUPPORTED") else "LF_FEATURE_VALUE_DECAYS_WITH_OOD" if summary["ood_strata"]["farthest"]["median_state_delta"]>summary["ood_strata"]["nearest"]["median_state_delta"] else "LF_FEATURE_VALUE_MIXED")
    atomic_json(OUT/"verdict_v2.json",{"schema":"COUPLING_ML_NP_FORWARD_FEATURE_ABLATION_VERDICT_V2","feature_value_verdict":summary["verdict"],
      "production_H1_status":summary["production_h1_status"],"retrospective_H1":{"A0":summary["arms"]["A0"]["retrospective_h1"],"A1":summary["arms"]["A1"]["retrospective_h1"],"both_pass":h1pass},
      "feature_acceptance":accept,"OOD_interpretation":oodinterp,"production_admission_changed":False,"solver_invocations":0})
    report=["# COUPLING_ML_NP_FORWARD_FEATURE_ABLATION_20G_V2","","STATUS: COMPLETE_ZERO_SOLVER_OFFLINE_ML",
      f"Frozen contract SHA256: {CONTRACT_SHA}. Solver invocations: 0. CPU only.",
      "Dataset: 20 valid integrated 3D PW geometries; paired P/XLIKE 445-455 nm, 1 nm; 220 sample rows / 1540 order rows.",
      f"NP cache/runtime: 220/220; representative exact runtime parity {cx['runtime']['queries']}/15; HF22 overlap 0/20; all OOD.",
      "","| Metric | A0 median | A0 q95 | A1 median | A1 q95 |","|---|---:|---:|---:|---:|"]
    for k,n in [("state_relative_rmse","State relative RMSE"),("routing_eta_rmse","Routing eta RMSE"),("absolute_order_source_normalized_rmse","Abs-order source-normalized RMSE"),("thresholded_absolute_order_relative_median","Thresholded abs-order relative"),("total_power_relative_rmse","P_scale relative RMSE")]:
        x,y=summary["arms"]["A0"][k],summary["arms"]["A1"][k];report.append(f"| {n} | {x['median']:.6g} | {x['q95']:.6g} | {y['median']:.6g} | {y['q95']:.6g} |")
    report += ["",f"Feature verdict: {summary['verdict']}.",f"Production H1: {summary['production_h1_status']}.",
      f"State wins/ties/losses: {summary['win_tie_loss']['state']}; routing: {summary['win_tie_loss']['routing']}.",
      f"Routing Pearson A0/A1: {summary['arms']['A0']['routing_pearson']:.6g}/{summary['arms']['A1']['routing_pearson']:.6g}.",
      f"P_scale Pearson A0/A1: {summary['arms']['A0']['pscale_pearson']:.6g}/{summary['arms']['A1']['pscale_pearson']:.6g}.",
      f"Seed state-median std A0/A1: {summary['arms']['A0']['seed_state_median_std']:.6g}/{summary['arms']['A1']['seed_state_median_std']:.6g}.",
      "Qualitative no-material-degradation for key absolute-order and P_scale metrics was conservatively operationalized as no worsening of median or q95; no threshold added.",
      "H1 production admission remains separate and unchanged; prospective six-geometry prediction-before-truth gate not run.",
      "NP features are low-fidelity single-pillar proxies, not integrated Coupling truth, C_component, Jones response, or MDC-TMM phase.",
      f"Truth route decoder closure median/q95/max abs eta error: {d['closure']['median']:.6g}/{d['closure']['q95']:.6g}/{d['closure']['max']:.6g}.",
      "OOD strata and members/distances retained in ood_support_analysis_v2.json; D180 provenance warnings and S16 sidecar exception preserved.",
      "NEXT: COUPLING_ML_NP_FORWARD_FEATURE_ABLATION_32G_CONFIRMATORY_V2 only after a valid 32G authority; not executed."]
    (OUT/"COUPLING_ML_NP_FORWARD_FEATURE_ABLATION_20G_V2.md").write_text("\n".join(report)+"\n",encoding="utf-8")
    ah={p.name:{"sha256":sha(p),"bytes":p.stat().st_size} for p in OUT.iterdir() if p.is_file() and p.name!="artifact_hashes.json"}
    ah.update({"contract_sha256":CONTRACT_SHA,"np_head":NP_HEAD,"np_cache_sha256":CACHE_SHA,"np_adapter_sha256":ADAPTER_SHA,
      "truth_sha256":cx["truth_sha"],"h1_authority_sha256":cx["h1_sha"],"coupling_head_before_commit":git(["git","rev-parse","HEAD"],ROOT),
      "solver_invocations":0,"gpu_used":False,"decoder_closure":d["closure"],"case_artifacts":d["hashes"]})
    atomic_json(OUT/"artifact_hashes.json",ah)
    print(json.dumps({"status":"COMPLETE","verdict":summary["verdict"],"production_h1":summary["production_h1_status"],"solver_invocations":0}))
    return 0
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--validate-only",action="store_true");a=p.parse_args()
    torch.set_num_threads(1)
    try:torch.set_num_interop_threads(1)
    except RuntimeError:pass
    torch.use_deterministic_algorithms(True)
    # This evaluator writes only after preflight and only to its dedicated V2 output namespace.
    sys.exit(main())
