from __future__ import annotations
import csv, gzip, hashlib, json, math, re, random, shutil
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(r"D:/project/worktrees/blue_apcd_np_k6_mdc_v1")
OUT = ROOT / r"outputs/np_k6_m7_16g_forward_retraining_v1"
DATA = ROOT / r"outputs/np_k6_m6_formal_development_merge_v1/formal_development_hf_observations_352rows.csv"
LFROOT = ROOT / r"outputs/np_k6_ml_d0_database_foundation_v1"
LF_MANIFEST = LFROOT / "k6_lf_arrays_manifest.json"
LF_MASTER = LFROOT / "k6_design_space_master.csv.gz"
SCHEMA = ROOT / r"outputs/np_k6_m5b_forward_formulation_repair_v1/NP_K6_AUTHORITATIVE_OUTPUT_SCHEMA_V1.json"
M5B_PREREG = ROOT / r"outputs/np_k6_m5b_forward_formulation_repair_v1/NP_K6_M5B_FORMULATION_REPAIR_PREREG_V1.json"
M5B_OOF = ROOT / r"outputs/np_k6_m5b_forward_formulation_repair_v1/m5b_refit_candidate_oof.csv"
M5_DATA = ROOT / r"outputs/np_k6_m5_fullk6_forward_v0/m5_training_view_286rows.csv"
EXTERNAL = ROOT / r"outputs/np_k6_m5_fullk6_forward_v0/external_set_registry.json"
ORDERS = [-3, -2, -1, 0, 1, 2, 3]
WLS = list(range(445, 456))
SEEDS = [17, 29, 43]
EPOCHS = 80


def now():
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def dump(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, default=str) + "\n", encoding="utf-8")


def write_csv(path: Path, fields, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader(); w.writerows(rows)


def read_csv(path: Path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def parse_geometry(gid):
    ds = [float(x) for x in re.findall(r"D(\d+)", gid)]
    if len(ds) != 6:
        raise RuntimeError(f"geometry_order_parse_failed:{gid}")
    return ds


def load_rows():
    rows = read_csv(DATA)
    if len(rows) != 352:
        raise RuntimeError(f"formal_rows={len(rows)}")
    keys = [(r["case_id"], int(float(r["wavelength_nm"]))) for r in rows]
    if len(set(keys)) != 352:
        raise RuntimeError("duplicate_case_wavelength")
    geos = sorted({r["geometry_id"] for r in rows})
    if len(geos) != 16:
        raise RuntimeError(f"geometry_count={len(geos)}")
    counts = defaultdict(set)
    for r in rows:
        if r.get("quality_gate_pass") != "true" or r.get("diagnostic_only") != "false":
            raise RuntimeError("formal_quality_flag_mismatch")
        counts[r["geometry_id"]].add((r["polarization"].lower(), int(float(r["wavelength_nm"]))))
        parse_geometry(r["geometry_id"])
    if any(len(v) != 22 or {p for p, _ in v} != {"p", "s"} for v in counts.values()):
        raise RuntimeError("geometry_ps_wavelength_coverage_incomplete")
    return rows, geos


def load_lf(rows, geos):
    with gzip.open(LF_MASTER, "rt", encoding="utf-8") as f:
        design = list(csv.DictReader(f))
    dmap = {r["geometry_id"]: r for r in design}
    missing = [g for g in geos if g not in dmap]
    bad = [g for g in geos if dmap[g].get("split") != "development_pool"]
    if missing or bad:
        raise RuntimeError(f"lf_geometry_contract:{missing}:{bad}")
    index = {r["geometry_id"]: i for i, r in enumerate(design)}
    arrays = {}
    needed = defaultdict(list)
    for g in geos:
        i = index[g]; needed[i // 5000].append((g, i % 5000))
    for chunk, items in needed.items():
        z = np.load(LFROOT / "lf_chunks" / f"chunk_{chunk:03d}.npz")
        for g, loc in items:
            arrays[g] = (z["eta_m_proxy"][loc].astype(float), z["propagating_sum_proxy"][loc].astype(float))
    if set(arrays) != set(geos):
        raise RuntimeError("lf_chunk_coverage_incomplete")
    out = []
    for r in rows:
        eta, tp = arrays[r["geometry_id"]]
        i = int(float(r["wavelength_nm"])) - 445
        out.append({"geometry_id": r["geometry_id"], "wavelength_nm": int(float(r["wavelength_nm"])), "polarization": r["polarization"].lower(), "lf_T_proxy": float(tp[i]), **{f"lf_eta_m{m:+d}": float(eta[i, j]) for j, m in enumerate(ORDERS)}})
    return out, index


def make_arrays(rows, lf):
    X=[]; C=[]; N=[]; Y=[]; L=[]
    for r,l in zip(rows,lf):
        ds=parse_geometry(r["geometry_id"]); wl=float(r["wavelength_nm"]); pol=r["polarization"].lower()
        pflag=1.0 if pol == "p" else 0.0; sflag=1.0 if pol == "s" else 0.0
        X.append([d/230.0 for d in ds]+[(wl-450)/5.0, 0.0, pflag, sflag])
        C.append([(wl-450)/5.0, 0.0, pflag, sflag])
        mean=sum(ds)/6.0; gaps=[(ds[(i+1)%6]-ds[i])/230.0 for i in range(6)]
        N.append([[ds[i]/230.0,gaps[i],(ds[i]-ds[i-1])/230.0,(ds[(i+1)%6]-ds[i])/230.0,(ds[i]-mean)/230.0,i/5.0,1.0 if i==0 else 0.0] for i in range(6)])
        Y.append([float(r["R_total"])] + [float(r[f"eta_m{m:+d}"]) for m in ORDERS])
        L.append([float(l[f"lf_eta_m{m:+d}"]) for m in ORDERS] + [float(l["lf_T_proxy"])])
    return np.asarray(X,float),np.asarray(C,float),np.asarray(N,float),np.asarray(Y,float),np.asarray(L,float)


def norm_fit(a, tr):
    mu=a[tr].mean(0); sd=a[tr].std(0); sd[sd < 1e-8] = 1.0
    return (a-mu)/sd


def torch_fit(kind, X, C, N, Y, L, tr, te, seed):
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    torch.set_num_threads(2); torch.manual_seed(seed); np.random.seed(seed); random.seed(seed)
    xz=norm_fit(X,tr); lz=norm_fit(np.c_[X,L],tr); cz=norm_fit(C,tr); nz=norm_fit(N.reshape(len(N),-1),tr).reshape(len(N),6,7)
    class Direct(nn.Module):
        def __init__(self,res=False,dim=10):
            super().__init__(); self.res=res
            if res: self.i=nn.Linear(dim,64); self.b1=nn.Sequential(nn.GELU(),nn.Linear(64,64),nn.GELU(),nn.Linear(64,64)); self.b2=nn.Sequential(nn.GELU(),nn.Linear(64,64),nn.GELU(),nn.Linear(64,64))
            else: self.body=nn.Sequential(nn.Linear(dim,64),nn.GELU(),nn.Linear(64,64),nn.GELU())
            self.o=nn.Linear(64,8)
        def forward(self,x):
            if self.res:
                h=F.gelu(self.i(x)); h=h+self.b1(h); h=h+self.b2(h)
            else: h=self.body(x)
            return torch.sigmoid(self.o(h))
    class Residual(nn.Module):
        def __init__(self):
            super().__init__(); self.body=nn.Sequential(nn.Linear(18,64),nn.GELU(),nn.Linear(64,64),nn.GELU()); self.o=nn.Linear(64,8)
        def forward(self,x):
            z=self.o(self.body(x)); return torch.cat([torch.sigmoid(z[:,:1]),z[:,1:]],1)
    class CNN(nn.Module):
        def __init__(self):
            super().__init__(); self.c=nn.Sequential(nn.Conv1d(7,32,3,padding=1,padding_mode="circular"),nn.GELU(),nn.Conv1d(32,32,3,padding=1,padding_mode="circular"),nn.GELU(),nn.Conv1d(32,32,3,padding=1,padding_mode="circular"),nn.GELU()); self.ctx=nn.Linear(4,32); self.o=nn.Linear(32,8)
        def forward(self,n,c): return torch.sigmoid(self.o(self.c(n.transpose(1,2)).mean(2)+self.ctx(c)))
    if kind == "direct_mlp": model,inp,target=Direct(False,10),xz,Y
    elif kind == "resmlp": model,inp,target=Direct(True,10),xz,Y
    elif kind in {"residual_mlp", "corrected_residual_mlp"}: model,inp,target=Residual(),lz,np.c_[Y[:,:1],Y[:,1:]-L[:,:7]]
    elif kind == "circular_cnn": model,inp,target=CNN(),None,Y
    else: raise ValueError(kind)
    opt=torch.optim.Adam(model.parameters(),lr=0.01,weight_decay=1e-5); model.train()
    xt=torch.tensor(inp[tr] if inp is not None else nz[tr],dtype=torch.float32)
    ct=torch.tensor(cz[tr],dtype=torch.float32); yt=torch.tensor(target[tr],dtype=torch.float32)
    for _ in range(EPOCHS):
        opt.zero_grad(); pred=model(xt,ct) if kind=="circular_cnn" else model(xt); loss=((pred-yt)**2).mean(); loss.backward(); opt.step()
    model.eval();
    with torch.no_grad():
        p=model(torch.tensor(nz[te],dtype=torch.float32),torch.tensor(cz[te],dtype=torch.float32)) if kind=="circular_cnn" else model(torch.tensor(inp[te],dtype=torch.float32))
    p=p.detach().cpu().numpy()
    if kind in {"residual_mlp", "corrected_residual_mlp"}: p[:,1:]+=L[te,:7]
    return p


def ridge_pred(kind, X, C, Y, L, rows, tr, te):
    from sklearn.linear_model import Ridge
    feat=np.c_[X,L]; fz=norm_fit(feat,tr); eta_delta=Y[:,1:]-L[:,:7]
    if kind == "lf_global_bias":
        p=np.c_[np.full(len(te),Y[tr,0].mean()),L[te,:7]+eta_delta[tr].mean(0)]
        return p
    if kind == "lf_affine":
        a=np.c_[np.ones(len(rows)),C[:,0],C[:,2],C[:,3]]; az=norm_fit(a,tr); rr=Ridge(alpha=1e-5).fit(az[tr],Y[tr,0]); ee=Ridge(alpha=1e-5).fit(az[tr],eta_delta[tr]); return np.c_[rr.predict(az[te]),L[te,:7]+ee.predict(az[te])]
    if kind == "lf_ridge_residual":
        fit=Ridge(alpha=1e-2).fit(fz[tr],np.c_[Y[tr,0],eta_delta[tr]]); z=fit.predict(fz[te]); return np.c_[z[:,0],L[te,:7]+z[:,1:]]
    if kind == "lf_paired_shared_contrast":
        pairs={}
        for i,r in enumerate(rows): pairs.setdefault((r["geometry_id"],int(float(r["wavelength_nm"]))),{})[r["polarization"].lower()]=i
        pairkeys=[k for k,v in pairs.items() if "p" in v and "s" in v and v["p"] in set(tr) and v["s"] in set(tr)]
        common=[]; contrast=[]; pf=[]; rr=[]
        for k in pairkeys:
            ip,is_=pairs[k]["p"],pairs[k]["s"]; pf.append(feat[ip]); common.append((eta_delta[ip]+eta_delta[is_])/2); contrast.append((eta_delta[ip]-eta_delta[is_])/2); rr.extend([ip,is_])
        if not pf: return ridge_pred("lf_ridge_residual",X,C,Y,L,rows,tr,te)
        pf=np.asarray(pf); pz=(pf-pf.mean(0))/np.where(pf.std(0)<1e-8,1,pf.std(0)); cm=Ridge(alpha=1e-2).fit(pz,common); dm=Ridge(alpha=1e-2).fit(pz,contrast); rfit=Ridge(alpha=1e-2).fit(fz[tr],Y[tr,0])
        q=(feat[te]-pf.mean(0))/np.where(pf.std(0)<1e-8,1,pf.std(0)); common_hat=cm.predict(q); contrast_hat=dm.predict(q); eta=[]
        for j,i in enumerate(te): eta.append(L[i,:7]+common_hat[j]+(contrast_hat[j] if rows[i]["polarization"].lower()=="p" else -contrast_hat[j]))
        return np.c_[rfit.predict(fz[te]),np.asarray(eta)]
    raise ValueError(kind)


def project(p):
    q=np.asarray(p,float).copy(); q[:,0]=np.clip(q[:,0],0,1); q[:,1:]=np.maximum(q[:,1:],0)
    s=q[:,1:].sum(1); lim=np.maximum(0,1-q[:,0]); mask=s>lim
    q[mask,1:]*=(lim[mask]/np.maximum(s[mask],1e-12))[:,None]
    return q


def rank_corr(a,b):
    a=np.asarray(a,float); b=np.asarray(b,float)
    if len(a)<2 or np.std(a)==0 or np.std(b)==0:return float("nan")
    ra=np.empty(len(a)); rb=np.empty(len(b)); ra[np.argsort(a,kind="mergesort")]=np.arange(len(a)); rb[np.argsort(b,kind="mergesort")]=np.arange(len(b))
    return float(np.corrcoef(ra,rb)[0,1])


def broadband(rows, values):
    ix=ORDERS.index(1); d=defaultdict(list)
    for i,r in enumerate(rows): d[r["geometry_id"]].append((r["polarization"].lower(),int(float(r["wavelength_nm"])),values[i,1+ix]))
    return {g:float(np.mean([v for _,_,v in vals])) for g,vals in d.items()}


def metrics(rows,Y,pred,model,variant="raw"):
    eta=Y[:,1:]; pe=pred[:,1:]; r=pred[:,0]; trueT=eta.sum(1); pT=pe.sum(1); ae=np.abs(pred-Y); eae=np.abs(pe-eta)
    geos=sorted({x["geometry_id"] for x in rows}); gt=broadband(rows,Y); gp=broadband(rows,pred); order=np.argsort([-gt[g] for g in geos]); po=np.argsort([-gp[g] for g in geos]); rankpos={int(i):j+1 for j,i in enumerate(po)}
    geom={g:float(eae[[i for i,x in enumerate(rows) if x["geometry_id"]==g]].mean()) for g in geos}
    def finite(x): return x[np.isfinite(x)]
    rr=finite(np.abs(r-Y[:,0])); tm=np.abs(pT-trueT); energy=1-r-pT
    return {"model":model,"variant":variant,"order_profile_mae":float(eae.mean()),"order_profile_rmse":float(np.sqrt((eae**2).mean())),"median_abs_error":float(np.median(ae[np.isfinite(ae)])),"p90_abs_error":float(np.quantile(ae[np.isfinite(ae)],.9)),"max_abs_error":float(np.max(ae[np.isfinite(ae)])),"R_mae":float(rr.mean()) if len(rr) else None,"R_rmse":float(np.sqrt((rr**2).mean())) if len(rr) else None,"T_mae":float(tm.mean()),"T_rmse":float(np.sqrt((tm**2).mean())),"eta_plus1_mae":float(eae[:,ORDERS.index(1)].mean()),"eta_plus1_rmse":float(np.sqrt((eae[:,ORDERS.index(1)]**2).mean())),"eta_0_mae":float(eae[:,ORDERS.index(0)].mean()),"eta_minus1_mae":float(eae[:,ORDERS.index(-1)].mean()),"per_order_mae":{str(m):float(eae[:,j].mean()) for j,m in enumerate(ORDERS)},"worst_geometry":max(geom,key=geom.get),"worst_geometry_order_profile_mae":max(geom.values()),"geometry_errors":geom,"negative_power_violation_rate":float(np.mean(pred[:,1:]<0)),"R_legality_violation_rate":float(np.mean((r<0)|(r>1))) if len(rr) else None,"order_sum_T_mismatch_mae":float(np.mean(np.abs(pT-trueT)),),"energy_residual_mae":float(np.mean(np.abs(energy[np.isfinite(energy)]))) if np.isfinite(energy).any() else None,"energy_residual_max":float(np.max(np.abs(energy[np.isfinite(energy)]))) if np.isfinite(energy).any() else None,"ranking_spearman":rank_corr([gt[g] for g in geos],[gp[g] for g in geos]),"top3_recall":float(len(set(order[:3])&set(po[:3]))/3),"top5_recall":float(len(set(order[:5])&set(po[:5]))/5),"true_champion_geometry":geos[int(order[0])],"true_champion_predicted_rank":rankpos[int(order[0])],"near_champion_retrieval":int(len(set(order[:2])&set(po[:5])))}


def ps_audit(rows,Y,preds):
    out=[]; ix=ORDERS.index(1)
    pairs=defaultdict(dict)
    for i,r in enumerate(rows): pairs[(r["geometry_id"],int(float(r["wavelength_nm"])))][r["polarization"].lower()]=i
    for model,p in preds.items():
        for (g,w),q in pairs.items():
            if "p" not in q or "s" not in q: continue
            ip,is_=q["p"],q["s"]
            out.append({"model":model,"geometry_id":g,"wavelength_nm":w,"true_delta_eta_plus1":float(Y[ip,1+ix]-Y[is_,1+ix]),"pred_delta_eta_plus1":float(p[ip,1+ix]-p[is_,1+ix]),"abs_delta_error":float(abs((p[ip,1+ix]-p[is_,1+ix])-(Y[ip,1+ix]-Y[is_,1+ix]))),"true_delta_T":float(Y[ip,1:].sum()-Y[is_,1:].sum()),"pred_delta_T":float(p[ip,1:].sum()-p[is_,1:].sum())})
    return out


def learning_value(rows,Y,preds):
    old_rows=read_csv(M5_DATA); old_geos=sorted({r["geometry_id"] for r in old_rows}); common=set(old_geos)&set({r["geometry_id"] for r in rows})
    old_oof=read_csv(M5B_OOF); target={}
    for r in old_oof:
        if r["model"]=="corrected_residual_mlp" and r["variant"]=="raw" and r["geometry_id"] in common:
            target[(r["geometry_id"],r["polarization"].lower(),int(float(r["wavelength_nm"])))] = np.array([float(r["pred_R"]),* [float(r[f"pred_eta_m{m:+d}"]) for m in ORDERS]])
    idx={(r["geometry_id"],r["polarization"].lower(),int(float(r["wavelength_nm"]))):i for i,r in enumerate(rows)}
    result=[]
    for name,p in preds.items():
        q=[(idx[k],v) for k,v in target.items() if k in idx]
        if not q: continue
        ii=np.array([x[0] for x in q]); old=np.asarray([x[1] for x in q]); new=p[ii]; truth=Y[ii]
        result.append({"model":name,"common_hf13_rows":int(len(ii)),"old_m5b_order_profile_mae":float(np.abs(old[:,1:]-truth[:,1:]).mean()),"new_m7_order_profile_mae":float(np.abs(new[:,1:]-truth[:,1:]).mean()),"old_m5b_eta_plus1_mae":float(np.abs(old[:,1+ORDERS.index(1)]-truth[:,1+ORDERS.index(1)]).mean()),"new_m7_eta_plus1_mae":float(np.abs(new[:,1+ORDERS.index(1)]-truth[:,1+ORDERS.index(1)]).mean())})
    return result


def main():
    if OUT.exists():
        raise RuntimeError(f"refusing_existing_output:{OUT}")
    OUT.mkdir(parents=True)
    rows,geos=load_rows(); lf,lf_indices=load_lf(rows,geos)
    dataset_sha=sha256(DATA); lf_sha=sha256(LF_MANIFEST); master_sha=sha256(LF_MASTER); schema_sha=sha256(SCHEMA); m5b_sha=sha256(M5B_PREREG)
    lf_fields=["geometry_id","wavelength_nm","polarization","lf_T_proxy"]+[f"lf_eta_m{m:+d}" for m in ORDERS]
    write_csv(OUT/"lf_baseline_352rows.csv",lf_fields,lf)
    lf_manifest={"authority_id":"NP_K6_LF_BASELINE_16G_V1","rows":len(lf),"geometry_count":len(geos),"geometries":geos,"coverage_complete":True,"polarization_handling":"LF_BASELINE_POLARIZATION_BLIND_AT_CURRENT_SCOPE","legal_outputs":["eta_m_proxy","T_proxy"],"R_baseline_available":False,"source_library_manifest":"outputs\\np_k6_ml_d0_database_foundation_v1\\k6_lf_arrays_manifest.json","source_library_manifest_sha256":lf_sha,"source_geometry_master":"outputs\\np_k6_ml_d0_database_foundation_v1\\k6_design_space_master.csv.gz","source_geometry_master_sha256":master_sha,"geometry_indices":{g:lf_indices[g] for g in geos},"dataset_path":str(DATA.relative_to(ROOT)),"dataset_sha256":dataset_sha,"solver_calls":0,"sealed_target_reads":0,"external_target_reads":0,"no_hf_truth_used_to_generate_lf":True}
    dump(OUT/"lf_authority_completion.json",lf_manifest); dump(OUT/"lf_reproducibility_manifest.json",{"code_path":"scripts\\np_k6_m7_16g_forward_retraining_v1.py","dataset_sha256":dataset_sha,"lf_manifest_sha256":lf_sha,"master_sha256":master_sha,"output_schema_sha256":schema_sha,"solver_calls":0})
    if not EXTERNAL.exists(): raise RuntimeError("external_registry_missing")
    ext=json.loads(EXTERNAL.read_text(encoding="utf-8-sig"))
    if int(ext.get("geometry_count",0)) != 12 or ext.get("sealed_hf_target_read",0) != 0: raise RuntimeError("external_registry_contract")
    dump(OUT/"external_set_readiness.json",{"registry_id":"NP_K6_FORWARD_EXTERNAL_FROZEN_SET_V1","metadata_only":True,"geometry_count":12,"future_logical_cases":24,"sealed_target_reads":0,"external_target_reads":0,"development_geometry_intersection":[]})
    prereg={"preregistration_id":"NP_K6_M7_16G_FORWARD_RETRAINING_PREREG_V1","created_utc":now(),"scope":"16-geometry coupling-aware forward retraining","solver_calls":0,"dataset":{"path":str(DATA.relative_to(ROOT)),"sha256":dataset_sha,"rows":352,"geometries":16,"paired_PS_cases":32,"wavelengths":WLS,"u_x":[0.0],"capability":"NORMAL_INCIDENCE_ONLY","g01p_excluded":True,"g01s_absent":True},"lf_authority":{"id":"NP_K6_LF_BASELINE_16G_V1","path":"lf_baseline_352rows.csv","sha256":sha256(OUT/"lf_baseline_352rows.csv"),"R_available":False,"polarization_scope":"LF_BASELINE_POLARIZATION_BLIND_AT_CURRENT_SCOPE"},"input_contract":{"ordered_geometry":["D1","D2","D3","D4","D5","D6"],"condition":["wavelength_nm","u_x","polarization"],"diameter_sorting":False,"permutation_invariant_encoding":False},"output_contract":{"primary":["R"]+[f"eta_m{m:+d}" for m in ORDERS],"T_definition":"sum_all_tracked_eta","eta_plus1_symbolic_key":"eta_m+1","complex_labels":"COMPLEX_ORDER_CONTRACT_NOT_YET_READY"},"models":{"LF_only":"frozen physical baseline","LF_global_bias":"fold-local mean residual calibration","LF_affine":"fold-local wavelength/polarization affine residual calibration","LF_ridge_residual":"fold-local Ridge on ordered geometry+LF residual","LF_paired_shared_contrast":"fold-local paired common/contrast correction","corrected_residual_mlp":"18->64->64 residual target [R,HF_eta-LF_eta]","direct_mlp":"10->64->64 direct HF reference","resmlp":"10->64 residual blocks direct HF reference","circular_cnn":"M3 incumbent circular Conv1d"},"cv":{"outer":"16-fold Leave-One-Geometry-Out","held_out_unit":"both P/S and all 11 wavelengths","normalization":"fold-local","seeds":SEEDS,"epochs":EPOCHS,"sweep":False},"ranking":{"primary":"broadband eta(+1): mean wavelength then mean P/S","secondary":["Spearman","Top-3","Top-5","champion rank","near-champion","seed stability"]},"physics":{"raw_and_constrained_reported":True,"negative_power_rate":True,"order_sum_T_mismatch":True,"energy_budget_residual":True,"R_T_legality":True},"learning_value":{"common_hf13_comparison":True,"new_m6_geometry_heldout_analysis":True,"no_percent_improvement_claim":True},"external_governance":{"registry":"NP_K6_FORWARD_EXTERNAL_FROZEN_SET_V1","metadata_only":True,"never_training":True,"never_normalization":True,"never_model_selection":True,"future_hf_logical_cases":24},"promotion":{"stop_after_forward_assessment":True,"no_external_hf":True,"no_prospective_hf":True,"no_training_promotion":True}}
    prereg_path=OUT/"NP_K6_M7_16G_FORWARD_RETRAINING_PREREG_V1.json"; dump(prereg_path,prereg); prehash=sha256(prereg_path); dump(OUT/"preregistration_sha256.json",{"path":str(prereg_path.relative_to(ROOT)),"sha256":prehash,"must_precede_fit":True,"fit_started_after_write":True})
    X,C,N,Y,L=make_arrays(rows,lf); geo=np.asarray([r["geometry_id"] for r in rows]); all_preds={}; seed_preds={}; model_names=["direct_mlp","resmlp","corrected_residual_mlp","circular_cnn"]
    linear_names=["LF_global_bias","LF_affine","LF_ridge_residual","LF_paired_shared_contrast"]
    for name in linear_names: all_preds[name]=np.full_like(Y,np.nan,float)
    for name in model_names: seed_preds[name]={s:np.full_like(Y,np.nan,float) for s in SEEDS}
    fold_rows=[]
    for fold,g in enumerate(sorted(set(geo))):
        tr=np.where(geo!=g)[0]; te=np.where(geo==g)[0]
        for name in linear_names: all_preds[name][te]=ridge_pred({"LF_global_bias":"lf_global_bias","LF_affine":"lf_affine","LF_ridge_residual":"lf_ridge_residual","LF_paired_shared_contrast":"lf_paired_shared_contrast"}[name],X,C,Y,L,rows,tr,te)
        for name in model_names:
            for seed in SEEDS: seed_preds[name][seed][te]=torch_fit(name,X,C,N,Y,L,tr,te,seed)
        fold_rows.append({"fold":fold,"held_out_geometry":g,"test_rows":len(te),"train_rows":len(tr),"seed_count":len(SEEDS),"normalization_train_rows":len(tr)})
    for name in model_names: all_preds[name]=np.mean(np.stack(list(seed_preds[name].values())),axis=0)
    all_preds["LF_only"]=np.c_[np.full(len(Y),np.nan),L[:,:7]]
    order=["LF_only","LF_global_bias","LF_affine","LF_ridge_residual","LF_paired_shared_contrast","corrected_residual_mlp","direct_mlp","resmlp","circular_cnn"]
    write_csv(OUT/"fold_manifest.csv",list(fold_rows[0]),fold_rows)
    metric_rows=[]; constrained_rows=[]
    for name in order:
        metric_rows.append(metrics(rows,Y,all_preds[name],name,"raw")); constrained_rows.append(metrics(rows,Y,project(all_preds[name]),name,"constrained"))
    fields=["model","variant","order_profile_mae","order_profile_rmse","median_abs_error","p90_abs_error","max_abs_error","R_mae","R_rmse","T_mae","T_rmse","eta_plus1_mae","eta_plus1_rmse","eta_0_mae","eta_minus1_mae","worst_geometry","worst_geometry_order_profile_mae","negative_power_violation_rate","R_legality_violation_rate","order_sum_T_mismatch_mae","energy_residual_mae","energy_residual_max","ranking_spearman","top3_recall","top5_recall","true_champion_geometry","true_champion_predicted_rank","near_champion_retrieval","per_order_mae","geometry_errors"]
    write_csv(OUT/"model_metrics_raw.csv",fields,metric_rows); write_csv(OUT/"model_metrics_constrained.csv",fields,constrained_rows)
    rank_rows=[{k:r[k] for k in ("model","variant","ranking_spearman","top3_recall","top5_recall","true_champion_geometry","true_champion_predicted_rank","near_champion_retrieval")} for r in metric_rows]
    write_csv(OUT/"ranking_metrics.csv",list(rank_rows[0]),rank_rows)
    ps=ps_audit(rows,Y,all_preds); write_csv(OUT/"combined_hf16_ps_audit.csv",list(ps[0]),ps)
    ps_sum=[]
    for name in order:
        q=[r for r in ps if r["model"]==name]; ps_sum.append({"model":name,"overall_mean_abs_delta_eta_plus1_error":float(np.mean([r["abs_delta_error"] for r in q])),"overall_max_abs_delta_eta_plus1_error":float(np.max([r["abs_delta_error"] for r in q])),"true_mean_abs_delta_eta_plus1":float(np.mean([abs(r["true_delta_eta_plus1"]) for r in q])),"true_max_abs_delta_eta_plus1":float(np.max([abs(r["true_delta_eta_plus1"]) for r in q]))})
    write_csv(OUT/"combined_hf16_ps_summary.csv",list(ps_sum[0]),ps_sum)
    residual=[]
    for j,m in enumerate(ORDERS):
        d=Y[:,1+j]-L[:,j]; residual.append({"output":f"eta_m{m:+d}","mean_bias":float(d.mean()),"mae":float(np.abs(d).mean()),"median_abs":float(np.median(np.abs(d))),"p90_abs":float(np.quantile(np.abs(d),.9)),"max_abs":float(np.max(np.abs(d))),"new_m6_rows":int(sum(r["dataset_source"]=="m6_formal_g02_g04_v1" for r in rows))})
    dt=Y[:,1:].sum(1)-L[:,7]; residual.append({"output":"T_proxy","mean_bias":float(dt.mean()),"mae":float(np.abs(dt).mean()),"median_abs":float(np.median(np.abs(dt)),),"p90_abs":float(np.quantile(np.abs(dt),.9)),"max_abs":float(np.max(np.abs(dt))),"new_m6_rows":66})
    write_csv(OUT/"lf_to_hf_residual_audit.csv",list(residual[0]),residual)
    lv=learning_value(rows,Y,all_preds); write_csv(OUT/"common_hf13_learning_value.csv",list(lv[0]) if lv else ["model"],lv)
    new3=set(r["geometry_id"] for r in rows if r["dataset_source"]=="m6_formal_g02_g04_v1"); new3rows=[]
    for r in metric_rows:
        name=r["model"]; p=all_preds[name]; ii=np.array([i for i,x in enumerate(rows) if x["geometry_id"] in new3]); new3rows.append({"model":name,"new_m6_geometry_count":len(new3),"new_m6_rows":len(ii),"order_profile_mae":float(np.abs(p[ii,1:]-Y[ii,1:]).mean()),"eta_plus1_mae":float(np.abs(p[ii,1+ORDERS.index(1)]-Y[ii,1+ORDERS.index(1)]).mean()),"T_mae":float(np.abs(p[ii,1:].sum(1)-Y[ii,1:].sum(1)).mean())})
    write_csv(OUT/"new_m6_heldout_analysis.csv",list(new3rows[0]),new3rows)
    physics={"raw":metric_rows,"constrained":constrained_rows,"output_order":ORDERS,"T_definition":"sum_all_tracked_eta","R_LF_baseline":"unavailable","order_identity_complete":True,"wavelength_identity":WLS,"polarization_identity":["p","s"],"u_x_scope":[0.0],"out_of_scope_prediction_attempts":0,"raw_vs_constrained_reported":True}
    dump(OUT/"physics_consistency_metrics.json",physics)
    dump(OUT/"complex_feasibility_audit.json",{"status":"COMPLEX_ORDER_CONTRACT_NOT_YET_READY","solver_calls":0,"sealed_target_reads":0,"wrapped_phase_synthesis":False})
    write_csv(OUT/"model_comparison.csv",["model","numerical_order_profile_mae","ranking_spearman","worst_geometry_mae","physics_energy_residual_mae"],[{"model":r["model"],"numerical_order_profile_mae":r["order_profile_mae"],"ranking_spearman":r["ranking_spearman"],"worst_geometry_mae":r["worst_geometry_order_profile_mae"],"physics_energy_residual_mae":r["energy_residual_mae"]} for r in metric_rows])
    pred_rows=[]
    for name in order:
        p=all_preds[name]
        for i,r in enumerate(rows):
            pred_rows.append({"case_id":r["case_id"],"geometry_id":r["geometry_id"],"polarization":r["polarization"],"wavelength_nm":int(float(r["wavelength_nm"])),"model":name,"variant":"ensemble_raw","pred_R":float(p[i,0]) if np.isfinite(p[i,0]) else "nan","pred_T":float(p[i,1:].sum()),**{f"pred_eta_m{m:+d}":float(p[i,1+j]) for j,m in enumerate(ORDERS)}})
    write_csv(OUT/"oof_predictions_16g.csv",list(pred_rows[0]),pred_rows)
    dump(OUT/"learning_value_audit.json",{"common_hf13":lv,"new_m6_heldout":new3rows,"m5b_membership_path":str(M5_DATA.relative_to(ROOT)),"m5b_oof_path":str(M5B_OOF.relative_to(ROOT)),"no_uncontrolled_percentage_claims":True})
    dump(OUT/"solver_zero_audit.json",{"fdtd_run_calls":0,"lumapi_solver_run_calls":0,"new_hf_acquisition":0,"external_hf_calls":0,"sealed_hf_target_reads":0,"inverse_design":0,"checkpoint_count":0,"active_solver_processes":False})
    dump(OUT/"m7_training_run_manifest.json",{"status":"COMPLETE","preregistration_sha256":prehash,"preregistration_path":str(prereg_path.relative_to(ROOT)),"fit_started_after_preregistration":True,"fit_finished_utc":now(),"rows":352,"geometries":16,"paired_cases":32,"models":order,"seeds":SEEDS,"epochs":EPOCHS,"solver_calls":0,"external_hf_calls":0,"sealed_target_reads":0,"device":"torch"})
    print(json.dumps({"status":"PASS","output":str(OUT),"rows":352,"geometries":16,"prereg_sha256":prehash,"models":order,"solver_calls":0},indent=2))


if __name__ == "__main__":
    main()
