from __future__ import annotations
import argparse,csv,hashlib,importlib.util,json,math,os,random,re,statistics,subprocess,sys,time
from datetime import datetime,timezone
from pathlib import Path
os.environ["PYTHONDONTWRITEBYTECODE"]="1"
os.environ["CUDA_VISIBLE_DEVICES"]=""
os.environ["OMP_NUM_THREADS"]="1"
os.environ["MKL_NUM_THREADS"]="1"
os.environ["OPENBLAS_NUM_THREADS"]="1"
sys.dont_write_bytecode=True
import numpy as np
import torch
from torch import nn
from sklearn.decomposition import PCA
from sklearn.kernel_ridge import KernelRidge
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import GroupKFold
ROOT=Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1")
NP=Path(r"D:\project\worktrees\blue_apcd_np_k6_mdc_v1")
OUT=ROOT/"reports"/"coupling"/"COUPLING_ML_NP_FORWARD_FEATURE_ABLATION_32G_CONFIRMATORY_V2"
OUT20=ROOT/"reports"/"coupling"/"COUPLING_ML_NP_FORWARD_FEATURE_ABLATION_20G_V2"
BASE32=ROOT/"reports"/"coupling"/"PW_K6_STAGE1_32G_FROZEN_FORWARD_H1_V1"
CASE_ROOT=ROOT/"outputs"/"coupling_ml"/"PW_K6_SEED_DB_V1_PRODUCTION_V1"
WLS=tuple(range(445,456)); FULL_WLS=tuple(range(440,461)); ORD=tuple(range(-3,4)); SEEDS=(0,1,2)
BASE_HEAD="374b7b57310d4a9e83006c9e536247eccaba04b6"
CONTRACT_SHA="3c6b0bb9d498982811910a4be2da87e13ad82eba2a3bc493140bdd6834688081"
PREREG_SHA="ccd1c777aea4c880b78603a618a08d66ad7f06d05ed2ad70f7c64c9aa39abacc"
PREREG_CHECKSUM_SHA="8b4b9020dd2e1044f9fb89140ec973820f214ab0ca0b2c4168422adf904cd6a2"
AUTH32_SHA="0fae0577247866549cf85db88ab5d6f924795423adca4b8cf2742449736f6f2e"
ART32_SHA="c19ba975817bde9ea09f0b42ffb09fb16eec11b67adc5bb06e933f43ef8edc03"
NP_HEAD="d5143de18309f395000e7e2161eb5a83068ac090"
CACHE_SHA="acdbeab1ff20eba081aaf20d433d3d4b9a75dae3485e852ad519c54cbea1accc"
ADAPTER_SHA="e68db57c2e144f60cf24f1c03ca6279bd50b6c94c8465e8f9f9f75dec68fdbfd"
SUPPORT_SHA="9f17668d95b14faabcb162f5d15e9a51357d0f31cb199df576ced3f8f169dca8"
HF22_SHA="5c5dca90928498c927663ad3eedbf502394a68c741feef836195573846ba1599"
TRUTH_SHA="4f894932b14be549a5483f3a3731a1e71869759357d4eddeb7ba4dc0d5108408"
H1_SHA="8cf71239757e70eb75fbbf858a82c12f8af8d03c0892b99ff4ffce6a959fcdbd"
H1_20_SHA="b9d039cfe97e47105ad799af2c48193191e5615630cc54154ca78c78243798f8"
H1_32_SHA="2374e7c18e2a4094a5db4c32c7b0c491039ee39abd51987a9b1e2ad84e37dec8"
STAGE1_SHA="cce338dbfdb87667dc696be29d06217b97fa41aec724d4d3b5ebe5f9fd3415ec"
DELTA_SHA="6fff751988d3f586d28c3fe54120bf5fd4c6afebb7aa47a0ae306bf2b00e3e2a"
BASE_REPORT_SHA="8b6f27db3501ab23866a745d9d0e19a11d8c994cef8c93bcdb1315072a9bafd9"
THRESH=0.0009885656815447454
V2_TEMPLATE_SHA="76213dbb50907dad6b3f8af9aa9928f352d0b745d5176443f4ae4052be5be63f"
PRE_FILES=("dataset_authority_v2.json","feature_manifest_v2.json","np_feature_rows_v2.csv","fold_manifest_v2.json","ood_support_preregistered_v2.json","preregistration_v2.json","execution_freeze_v2.json")
RESULTS=("oof_predictions_v2.csv","per_geometry_metrics_v2.csv","paired_ablation_metrics_v2.json","ood_support_analysis_v2.json","leakage_audit_v2.json","verdict_v2.json","execution_manifest_v2.json","fold_execution_v2.json","comparison_20g_vs_32g_v2.json","artifact_hashes.json","COUPLING_ML_NP_FORWARD_FEATURE_ABLATION_32G_CONFIRMATORY_V2.md")
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def jread(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def atomic_json(p,o):
    t=Path(str(p)+".tmp");t.write_text(json.dumps(o,ensure_ascii=True,sort_keys=True,indent=2)+"\n",encoding="utf-8");os.replace(t,p)
def git(args,cwd): return subprocess.run(args,cwd=cwd,check=True,capture_output=True,text=True).stdout.strip()
def req(ok,msg):
    if not ok: raise RuntimeError(msg)
def jlines(p): return [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x.strip()]

def parity_check(rows,parity,fm,mod=None):
    req(parity.get("status")=="PASS" and parity.get("row_count")==220 and parity.get("unique_case_wavelength_queries")==220,"NP cache parity authority not PASS")
    req(len(rows)==220 and fm.get("cache_sha256")==CACHE_SHA,"NP feature cache authority mismatch")
    return {"status":"PASS","cache_rows":220,"cache_sha256":CACHE_SHA,"runtime_queries_checked_in_full":0}

def validate():
    req(git(["git","rev-parse","HEAD"],ROOT)==BASE_HEAD,"Coupling HEAD changed before confirmatory run")
    req(git(["git","branch","--show-current"],ROOT)=="work/mdc-np-coupling-ml-v1","wrong Coupling branch")
    cpath=OUT20/"NP_FEATURE_ABLATION_CONFIRMATORY_CONTRACT_V2.json"
    pp=OUT20/"preregistration_v2.json"
    req(sha(cpath)==CONTRACT_SHA and sha(pp)==PREREG_SHA and sha(OUT20/"preregistration_v2.sha256")==PREREG_CHECKSUM_SHA,"frozen V2 contract/preregistration hash mismatch")
    c,pr=jread(cpath),jread(pp)
    req(pr.get("status")=="FROZEN_BEFORE_V2_OUTER_METRICS" and pr.get("contract_sha256")==CONTRACT_SHA,"frozen V2 preregistration invalid")
    req(pr.get("v2_outer_fold_metrics_computed_at_registration") is False,"V2 metric chronology invalid")
    req(c["feature_arms"]["A2"]["status"]=="NOT_AVAILABLE" and c["feature_arms"]["A3"]["status"]=="NOT_AVAILABLE","A2/A3 authority conflict")
    req(c["ood_stratification"]["use"]=="diagnostic only; never model input","OOD feature authority conflict")
    req(c["future_32g_reuse"]["reuse_exact_contract"] is True,"32G frozen contract reuse not authorized")
    baseah=jread(BASE32/"artifact_hashes.json")
    req(sha(BASE32/"artifact_hashes.json")==ART32_SHA,"32G artifact manifest hash mismatch")
    expected={"PW_K6_32G_DATASET_AUTHORITY_V1.json":AUTH32_SHA,"dataset_truth_32g.npz":"fefc09bbd06d0da06664105540c4f5e0659a51b68b06a07df8c44ed413891d28",
      "PW_K6_FROZEN_FORWARD_H1_20G_V1.json":H1_20_SHA,"PW_K6_FROZEN_FORWARD_H1_32G_V1.json":H1_32_SHA,
      "PW_K6_STAGE1_12G_CLOSEOUT_AUTHORITY_V1.json":STAGE1_SHA,"PW_K6_20G_VS_32G_DELTAS_V1.json":DELTA_SHA,
      "PW_K6_STAGE1_32G_FROZEN_FORWARD_H1_V1.md":BASE_REPORT_SHA}
    for k,v in expected.items(): req(baseah.get(k)==v and sha(BASE32/k)==v,"frozen 32G artifact mismatch: "+k)
    auth=jread(BASE32/"PW_K6_32G_DATASET_AUTHORITY_V1.json")
    req(auth.get("status")=="PASS" and auth.get("geometry_count")==32 and auth.get("scalar_geometry_wavelength_rows")==672 and auth.get("order_geometry_wavelength_rows")==4704,"32G dataset authority counts/status mismatch")
    req(auth.get("reserve_cases_included") is False and auth.get("physical_contract_sha256")=="32e60a7830a449f2268356db5ffd41f4f22b297be9a1d82ebe97f97be995dea5","32G physical authority mismatch")
    req(len(auth["ordered_geometry_ids"])==32 and len(set(auth["ordered_geometry_ids"]))==32 and len(auth["case_provenance"])==32,"32G ordered geometry authority invalid")
    req(auth["wavelengths_nm"]==list(FULL_WLS),"32G full wavelength authority mismatch")
    truth=ROOT/"reports"/"coupling"/"PW_K6_GRATING_TRUTH_V2.json"
    h1=ROOT/"reports"/"coupling"/"PW_K6_H1_NUMERIC_GATE_AUTHORITY_V1.json"
    req(sha(truth)==TRUTH_SHA and sha(h1)==H1_SHA,"frozen truth/H1 authority hash mismatch")
    old=OUT20
    oldd=jread(old/"dataset_authority_v2.json");fm=jread(old/"feature_manifest_v2.json")
    oldfold=jread(old/"fold_manifest_v2.json");par=jread(old/"cache_runtime_parity.json")
    req(sha(old/"dataset_authority_v2.json")==c["dataset"]["dataset_authority_v2_sha256"],"20G dataset authority hash mismatch")
    req(oldd.get("status")=="PASS_20_SCIENTIFIC_VALID_INTEGRATED_3D_PW_CASES" and oldd.get("geometry_count")==20 and oldd.get("scientific_entries")==20 and oldd.get("replay_entries")==0 and oldd.get("duplicate_entries")==0,"20G source authority mismatch")
    req([x["case_id"] for x in oldd["cases"]]==c["dataset"]["geometry_id_order"],"20G case order mismatch")
    req(len(oldfold["fold_assignments"]["folds"])==20 and oldfold["outer_fold_metrics_computed"] is False,"20G frozen fold authority mismatch")
    req(fm["authority_head"]==NP_HEAD and fm["cache_sha256"]==CACHE_SHA and fm["runtime_adapter_sha256"]==ADAPTER_SHA,"NP feature manifest mismatch")
    req(sha(NP/"scripts"/"np_k6_coupling_forward_feature_interface_v2.py")==ADAPTER_SHA,"NP adapter changed")
    req(git(["git","rev-parse","HEAD"],NP)==NP_HEAD and git(["git","branch","--show-current"],NP)=="work/np-k6-mdc-v1","NP frozen authority branch/HEAD mismatch")
    cache=NP/"outputs"/"np_k6_coupling_forward_runtime_coverage_v2"/"coupling_20g_lf_feature_cache.jsonl"
    req(sha(cache)==CACHE_SHA,"NP cache hash mismatch")
    rows=jlines(cache);req(len(rows)==220,"NP cache row count mismatch")
    support=NP/"outputs"/"np_k6_coupling_forward_feature_interface_v1"/"coupling_20g_domain_support.json"
    hf=NP/"outputs"/"np_k6_m8a_primary2_closeout_v1"/"hf22_formal_development_484rows.csv"
    req(sha(support)==SUPPORT_SHA and sha(hf)==HF22_SHA,"frozen NP HF22 support artifacts changed")
    sup=jread(support);req(sup["status"]=="PASS" and sup["hf22_geometry_count"]==22,"HF22 support authority mismatch")
    req(sup["source_authority_hashes"]["hf22_csv"]["sha256"]==HF22_SHA,"HF22 source hash not in support authority")
    cp=old/"cache_runtime_parity.json";req(len(sha(cp))==64 and par.get("status")=="PASS" and par.get("row_count")==220 and par.get("unique_case_wavelength_queries")==220,"cache parity missing or invalid")
    return {"c":c,"pr":pr,"auth32":auth,"baseah":baseah,"truth":truth,"h1":h1,"oldd":oldd,"fm":fm,"oldfold":oldfold,
      "par":par,"rows":rows,"cache":cache,"support_path":support,"support":sup,"hf22":hf,"old_support":jread(old/"ood_support_preregistered_v2.json"),
      "old_metrics":jread(old/"paired_ablation_metrics_v2.json"),"old_verdict":jread(old/"verdict_v2.json"),
      "old_oof":old/"oof_predictions_v2.csv","np_adapter":NP/"scripts"/"np_k6_coupling_forward_feature_interface_v2.py",
      "dataset_npz":BASE32/"dataset_truth_32g.npz","source_truth":truth}

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
    setseed(seed);m=Net().to("cpu");req(sum(p.numel() for p in m.parameters())==2684,"parameter count mismatch")
    opt=torch.optim.AdamW(m.parameters(),lr=.002,weight_decay=.0001)
    x,y,xv,yv=[torch.as_tensor(z,dtype=torch.float32,device="cpu") for z in (x,y,xv,yv)]
    sd=torch.as_tensor(np.maximum(np.std(y.numpy(),axis=0),1e-12),dtype=torch.float32,device="cpu")
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
    setseed(seed);m=Net().to("cpu");opt=torch.optim.AdamW(m.parameters(),lr=.002,weight_decay=.0001)
    x,y=[torch.as_tensor(z,dtype=torch.float32,device="cpu") for z in (x,y)]
    sd=torch.as_tensor(np.maximum(np.std(y.numpy(),axis=0),1e-12),dtype=torch.float32,device="cpu")
    for _ in range(epochs):
        m.train();opt.zero_grad(set_to_none=True);l=lossfn(m(x),y,sd);l.backward();torch.nn.utils.clip_grad_norm_(m.parameters(),5.0);opt.step()
    m.eval()
    with torch.no_grad():return m(torch.as_tensor(xt,dtype=torch.float32,device="cpu")).numpy().astype(float)
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
def make_support(ctx,ids,geo):
    import csv
    rows={}
    with ctx["hf22"].open("r",encoding="utf-8-sig",newline="") as f:
        for r in csv.DictReader(f):
            gid=r["geometry_id"];dims=tuple(int(x) for x in re.findall(r"D(\d+)",gid))
            req(len(dims)==6,"HF22 geometry id parse failed")
            rows[gid]=dims
    req(len(rows)==22,"HF22 support geometry count mismatch")
    points=sorted(set(rows.values()));req(len(points)==22,"duplicate HF22 vectors")
    req(len(ctx["support"]["cases"])==20,"V1 support audit lacks 20G cases")
    olddist={x["case_id"]:float(x["distance"]) for group in ctx["old_support"]["strata"].values() for x in group}
    raw=[]
    for cid,D in zip(ids,geo):
        tup=tuple(int(x) for x in D)
        candidates=[]
        for gid,g in rows.items():
            dist=float(np.sqrt(np.sum(((np.asarray(tup,float)-np.asarray(g,float))/130.0)**2)))
            candidates.append((dist,gid,g))
        candidates.sort(key=lambda z:(z[0],z[1]))
        dist,gid,nearest=candidates[0]
        exact=tup in set(points)
        runtime=all(100<=x<=230 and x%5==0 for x in tup)
        raw.append({"case_id":cid,"ordered_D_nm":list(tup),"exact_HF22_overlap":bool(exact),
          "nearest_HF22_distance":dist,"nearest_HF22_geometry_id":gid,"nearest_HF22_ordered_D_nm":list(nearest),
          "runtime_domain_valid":bool(runtime),"runtime_domain_contract":"six ordered D values on the 100..230 nm, 5 nm grid; paired wavelength 445..455 nm; P_XLIKE; ux=0; ky=0",
          "OOD_flag":bool(not exact),"within_positionwise_HF22_bounds_count":int(sum(min(g[i] for g in points)<=tup[i]<=max(g[i] for g in points) for i in range(6)))})
    old20=set(ctx["oldd"]["cases"][i]["case_id"] for i in range(20))
    req(set(olddist)==old20,"20G frozen support membership mismatch")
    for x in raw:
        if x["case_id"] in olddist:
            req(abs(x["nearest_HF22_distance"]-olddist[x["case_id"]])<=1e-12,"recomputed 20G distance differs from frozen V2 support")
    ordered=sorted(raw,key=lambda x:(x["nearest_HF22_distance"],x["case_id"]))
    parts=np.array_split(np.arange(len(ordered)),3)
    strata={}
    for name,ix in zip(("nearest","middle","farthest"),parts):
        strata[name]=[ordered[int(i)] for i in ix]
    res={"schema":"COUPLING_ML_NP_FORWARD_FEATURE_OOD_SUPPORT_V2","status":"FROZEN_BEFORE_32G_METRICS",
      "contract_sha256":CONTRACT_SHA,"distance_formula":"sqrt(sum(((D_i-g_i)/130 nm)^2)); ordered physical D1..D6, no permutation",
      "hf22_geometry_count":22,"hf22_unique_vectors":len(points),"support_exact_overlap_count":sum(x["exact_HF22_overlap"] for x in raw),
      "extrapolative_count":sum(x["OOD_flag"] for x in raw),"runtime_domain_valid_count":sum(x["runtime_domain_valid"] for x in raw),
      "ood_flag_count":sum(x["OOD_flag"] for x in raw),"contract_support_sha256":ctx["c"]["ood_stratification"]["support_sha256"],
      "np_support_manifest_sha256":sha(ctx["support_path"]),"hf22_csv_sha256":sha(ctx["hf22"]),
      "support_metadata_as_features":False,"strata_policy":"sort by (normalized nearest distance, case_id), then numpy.array_split into three ordered thirds",
      "strata":{k:[{"case_id":x["case_id"],"distance":x["nearest_HF22_distance"]} for x in v] for k,v in strata.items()},
      "geometries":raw}
    req(res["support_exact_overlap_count"]==0 and res["extrapolative_count"]==32 and res["runtime_domain_valid_count"]==32,"unexpected 32G HF22/domain status")
    req([len(strata[x]) for x in ("nearest","middle","farthest")]==[11,11,10],"32G OOD strata size mismatch")
    return res

def make_features(ctx,ids,geo):
    cache_by={(r["geometry_id"],int(r["wavelength_nm"])):r for r in ctx["rows"]}
    spec=importlib.util.spec_from_file_location("np_v2_confirmatory_runtime",ctx["np_adapter"])
    req(spec is not None and spec.loader is not None,"NP runtime adapter cannot load")
    mod=importlib.util.module_from_spec(spec);sys.modules[spec.name]=mod;spec.loader.exec_module(mod)
    feature_def=ctx["fm"]["feature_definition"];per=feature_def["fields_per_wavelength"]
    req(len(per)==8 and len(WLS)*len(per)==88,"V2 feature field contract mismatch")
    allrows=[];matrix=np.zeros((len(ids),88),float);runtime=0;cache_matches=0;newq=0
    for gi,(cid,D0) in enumerate(zip(ids,geo)):
        D=[int(x) for x in D0];gid="K6X_"+"_".join(f"D{x}" for x in D);flat=[]
        for wl in WLS:
            a=mod.NP_LF_FEATURE_PROVIDER_V2(*D,float(wl),"P_XLIKE",root=NP,u_x=0.0,k_y=0.0)
            req(a.get("geometry_id")==gid and a.get("ordered_D_nm")==D and int(a.get("wavelength_nm"))==wl,"NP provider query identity mismatch")
            req(a.get("polarization")=="P_XLIKE" and float(a.get("u_x"))==0.0 and float(a.get("k_y"))==0.0,"NP provider physical query mismatch")
            req(a.get("provenance_hash")==ctx["fm"]["provenance_hash"] and a.get("ood") is True,"NP feature provenance/OOD flag mismatch")
            ff=a["features"];vals=[float(ff["eta_m_proxy"][f"m{m:+d}"]) for m in ORD]+[float(ff["T_proxy"])]
            req(len(vals)==8 and np.isfinite(vals).all(),"NP feature values invalid")
            key=(gid,wl)
            if key in cache_by:
                cached=cache_by[key]
                req(cached["ordered_D_nm"]==D and cached["polarization"]=="P_XLIKE" and cached["u_x"]==0.0 and cached["k_y"]==0.0 and cached["ood"] is True,"NP cache query metadata mismatch")
                req(ff==cached["features"],f"NP runtime/cache exact mismatch {key}")
                cache_matches+=1
            else:newq+=1
            runtime+=1;flat.extend(vals)
            allrows.append({"case_id":cid,"geometry_id":gid,"ordered_D_nm":D,"wavelength_nm":wl,"polarization":"P_XLIKE","u_x":0.0,"k_y":0.0,
              "ood":True,"provenance_hash":a["provenance_hash"],"feature_values":vals})
        req(len(flat)==88,"per-geometry NP feature length mismatch")
        matrix[gi]=flat
    req(runtime==352 and cache_matches==220 and newq==132,"32G NP feature coverage/parity count mismatch")
    return matrix,allrows,{"status":"PASS","runtime_queries":runtime,"historical_cache_exact_matches":cache_matches,"new_12_geometry_runtime_queries":newq,
      "cache_sha256":CACHE_SHA,"adapter_sha256":ADAPTER_SHA,"gpu_used":False,"solver_invocations":0}

def make_folds(ids):
    folds=[]
    for oi,test in enumerate(ids,1):
        train=[x for x in ids if x!=test]
        req(len(train)==31 and test not in train,"outer LOGO construction error")
        inn=[]
        split=GroupKFold(n_splits=3)
        for tr,va in split.split(np.zeros((len(train),1)),groups=np.asarray(train,dtype=object)):
            trids=[train[int(i)] for i in tr];vaids=[train[int(i)] for i in va]
            req(not(set(trids)&set(vaids)) and test not in trids+vaids,"inner geometry leakage")
            inn.append({"train_geometry_ids":trids,"validation_geometry_ids":vaids})
        req(len(inn)==3,"inner split count mismatch")
        folds.append({"outer_fold":oi,"test_geometry_id":test,"train_geometry_ids":train,"test_metrics_computed":False,"inner_group_folds":inn})
    return {"schema":"COUPLING_ML_NP_FORWARD_FEATURE_ABLATION_FOLD_MANIFEST_V2","status":"FROZEN_BEFORE_32G_OUTER_METRICS",
      "source_v1_fold_manifest_sha256":"9d9fda434b9f711c817b0ba719267d01906d54a37e142fcab580f31128d0ec07",
      "outer_rule":"strict 32-fold LOGO by complete ordered geometry","inner_rule":"three GroupKFold geometry-group splits within each outer-training set",
      "fold_assignments":{"folds":folds},"outer_fold_metrics_computed":False,"same_folds_for_A0_A1":True,
      "strict_geometry_grouping":True,"wavelength_row_random_split":False}

def load_data(ctx):
    auth=ctx["auth32"];ids=auth["ordered_geometry_ids"];geo=np.asarray(auth["ordered_D_nm"],float)
    req(len(ids)==32 and geo.shape==(32,6),"32G ordered geometry vectors malformed")
    prov=auth["case_provenance"];req([x["case_id"] for x in prov]==ids,"32G provenance order mismatch")
    state_hashes={}
    for rec in prov:
        sp=Path(rec["state_path"])
        req(sp.exists() and sha(sp)==rec["state_sha256"],"32G state NPZ hash mismatch: "+rec["case_id"])
        req(rec.get("scientific_validation")=="PASS" or rec.get("scientific_state") in ("RECOVERED_TRUTH_VALID","DONE"),
            "32G case not scientifically valid: "+rec["case_id"])
        artifacts={"state_npz_sha256":sha(sp)}
        if "state_metadata_sha256" in rec:
            candidates=[q for q in sp.parent.glob("*.json") if sha(q)==rec["state_metadata_sha256"]]
            req(len(candidates)==1,"32G state metadata hash/path mismatch: "+rec["case_id"])
            artifacts["state_metadata_sha256"]=sha(candidates[0])
        else:
            req(rec.get("attempt_id")=="attempt_001" and "raw_fields_path" in rec and "truth_h5_path" in rec,
                "Stage-1 raw/HF provenance missing: "+rec["case_id"])
            for field,pathfield in (("raw_fields_sha256","raw_fields_path"),("truth_h5_sha256","truth_h5_path")):
                q=Path(rec[pathfield]);req(q.exists() and sha(q)==rec[field],"Stage-1 provenance hash mismatch: "+rec["case_id"]+" "+field)
                artifacts[field]=sha(q)
        state_hashes[rec["case_id"]]=artifacts
    z=np.load(ctx["dataset_npz"],allow_pickle=False)
    req(list(z["case_ids"].tolist())==ids and np.array_equal(z["ordered_D_nm"],geo),"32G packed truth case/geometry order mismatch")
    req(z["C_hat"].shape==(32,21,7,2) and z["P_scale"].shape==(32,21) and z["eta"].shape==(32,21,7) and z["absolute_order_power"].shape==(32,21,7) and z["modal_weights"].shape==(32,21,7),"32G packed truth shape mismatch")
    li=np.asarray([wl-440 for wl in WLS],int)
    c=np.asarray(z["C_hat"][:,li,:,:],complex);p=np.asarray(z["P_scale"][:,li],float)
    eta=np.asarray(z["eta"][:,li,:],float);ab=np.asarray(z["absolute_order_power"][:,li,:],float);w=np.asarray(z["modal_weights"][:,li,:],float)
    req(np.isfinite(c.real).all() and np.isfinite(c.imag).all() and np.isfinite(p).all() and np.isfinite(eta).all() and np.isfinite(ab).all() and np.isfinite(w).all(),"nonfinite paired truth")
    truth_rows=jread(ctx["truth"])["rows"]
    tr={(x["case"],int(round(x["wavelength_nm"])),int(x["order_x"]),int(x["order_y"])):x for x in truth_rows
        if 445-1e-6<=x["wavelength_nm"]<=455+1e-6 and x["order_y"]==0 and -3<=x["order_x"]<=3}
    formal_ids=set(x["case"] for x in truth_rows)
    req(formal_ids==set(ids[:20]) and len(tr)==20*11*7,"frozen formal truth coverage must be exactly the original 20G")
    parity=auth["truth_parity"];stage=parity["stage1_12g"];oldp=parity["20g"]
    req([x["case_id"] for x in oldp]==ids[:20] and [x["case_id"] for x in stage]==ids[20:],"32G truth-parity cohort/order mismatch")
    req(len(stage)==12 and len(oldp)==20,"32G truth-parity record count mismatch")
    for key,summary_key,field in [("20g","20g_h2_eta_max_abs_error","h2_eta_max_abs_error"),
                                  ("stage1_12g","stage1_h2_eta_max_abs_error","h2_eta_max_abs_error")]:
        req(abs(max(float(x[field]) for x in parity[key])-float(parity[summary_key]))<=1e-15,"authority H2 parity aggregate mismatch: "+key)
    for key,summary_key,field in [("20g","20g_modal_pscale_max_relative_error","modal_pscale_max_relative_error"),
                                  ("stage1_12g","stage1_modal_pscale_max_relative_error","modal_pscale_max_relative_error")]:
        req(abs(max(float(x[field]) for x in parity[key])-float(parity[summary_key]))<=1e-15,"authority Pscale parity aggregate mismatch: "+key)
    closure=[]
    for gi,cid in enumerate(ids):
        for l,wl in enumerate(WLS):
            norm=w[gi,l]*np.sum(abs(c[gi,l])**2,axis=-1);norm/=norm.sum()
            for oi,m in enumerate(ORD):
                if cid in formal_ids:
                    rr=tr[(cid,wl,m,0)]
                    req(abs(eta[gi,l,oi]-rr["GRATING_ETA_V2"])<=1e-12 and abs(ab[gi,l,oi]-rr["GRATING_ABSOLUTE_ORDER_POWER_V2"])<=1e-12,"packed truth/formal grating truth mismatch")
                    req(abs(p[gi,l]-rr["POSTNP_TOTAL_POWER_V2"])<=1e-12,"P_scale/formal truth mismatch")
                closure.append(abs(float(norm[oi])-eta[gi,l,oi]))
    closure_stats={"samples":len(closure),"median":float(np.median(closure)),"q95":float(np.quantile(closure,.95)),"max":float(max(closure))}
    req(closure_stats["max"]<=.001,"packed state to frozen-authority routing closure failed")
    old=[]
    with ctx["old_oof"].open("r",encoding="utf-8",newline="") as f: old=list(csv.DictReader(f))
    oldtrue={(r["case_id"],int(r["wavelength_nm"]),int(r["order_x"])):r for r in old}
    req(len(oldtrue)==20*11*7 and len(old)==20*11*7,"20G archived truth rows missing/duplicated")
    cmax=0.0
    for gi,cid in enumerate(ids[:20]):
        for l,wl in enumerate(WLS):
            for oi,m in enumerate(ORD):
                rr=oldtrue[(cid,wl,m)]
                for pi,pol in enumerate(("TE","TM")):
                    oldc=complex(float(rr[f"C_hat_true_{pol}_re"]),float(rr[f"C_hat_true_{pol}_im"]))
                    cmax=max(cmax,float(abs(oldc-c[gi,l,oi,pi])))
    req(cmax<=1e-12,"32G packed complex state differs from archived 20G frozen truth")
    req(abs(cmax)<1e-12,"complex-state parity tolerance")
    support=make_support(ctx,ids,geo);features,feature_rows,feature_check=make_features(ctx,ids,geo)
    folds=make_folds(ids)
    x={"A0":geo.copy(),"A1":np.concatenate([geo,features],axis=1)}
    req(features.shape==(32,88) and x["A1"].shape==(32,94),"A1 feature/input dimensions mismatch")
    return {"ids":ids,"geo":geo,"x":x,"c":c,"w":w,"p":p,"eta":eta,"ab":ab,"closure":closure_stats,"hashes":state_hashes,
      "feature_names":ctx["fm"]["feature_definition"]["fields_per_wavelength"],"feature_matrix":features,"feature_rows":feature_rows,
      "feature_check":feature_check,"support":support,"fold_manifest":folds,"paired_truth_rows":32*11*7,"formal_20g_truth_rows_crosschecked":len(tr),"source_truth_parity_summary":{
        "20g_h2_eta_max_abs_error":ctx["auth32"]["truth_parity"]["20g_h2_eta_max_abs_error"],
        "20g_modal_pscale_max_relative_error":ctx["auth32"]["truth_parity"]["20g_modal_pscale_max_relative_error"],
        "stage1_h2_eta_max_abs_error":ctx["auth32"]["truth_parity"]["stage1_h2_eta_max_abs_error"],
        "stage1_modal_pscale_max_relative_error":ctx["auth32"]["truth_parity"]["stage1_modal_pscale_max_relative_error"],
        "stage1_pscale_source":ctx["auth32"]["truth_parity"]["stage1_pscale_source"]},
      "packed_state_20g_parity_max_abs":cmax}

def fitarm(d,fold,arm):
    ids=d["ids"];ix={x:i for i,x in enumerate(ids)};raw=d["x"][arm];n=len(ids)
    pred=np.full((len(SEEDS),n,11,7,2),np.nan+1j*np.nan,complex);pout=np.full((n,11),np.nan);logs=[]
    for f in fold["fold_assignments"]["folds"]:
        test=ix[f["test_geometry_id"]];outer=[ix[x] for x in f["train_geometry_ids"]];req(test not in outer and len(outer)==31,"outer leakage")
        ps,y=pcasfit(d["c"],outer);inner=[]
        for sp in f["inner_group_folds"]:
            tr=[ix[x] for x in sp["train_geometry_ids"]];va=[ix[x] for x in sp["validation_geometry_ids"]]
            req(not(set(tr)&set(va)) and test not in tr+va,"inner leakage");inner.append((tr,va))
        ilogs={}
        for si,s in enumerate(SEEDS):
            eps=[]
            for tr,va in inner:
                xf=Xform(arm).fit(raw[tr]);ip,iy=pcasfit(d["c"],tr)
                eps.append(fitstop(xf.transform(raw[tr]),iy,xf.transform(raw[va]),scores(d["c"],va,ip),s))
            ep=int(statistics.median(eps));xf=Xform(arm).fit(raw[outer])
            pred[si,test]=decode(fitfixed(xf.transform(raw[outer]),y,xf.transform(raw[[test]]),s,ep),ps)[0]
            ilogs[str(s)]={"inner_best_epochs":eps,"refit_epochs":ep}
        pout[test],plog=fitp(raw,d["p"],outer,test,inner,arm)
        logs.append({"fold":f["outer_fold"],"heldout":ids[test],"seeds":ilogs,"p_scale":plog})
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
    ids=d["ids"];gm=[];out={"solver_invocations":0,"gpu_used":False,"paired_wavelength_nm":list(WLS),"geometry_count":32,"arms":{}};arr={}
    for arm in ("A0","A1"):
        seed=pred[arm];cm=seed.mean(axis=0);pp=pscale[arm]
        ep=d["w"]*np.sum(abs(cm)**2,axis=-1);ep/=ep.sum(axis=-1,keepdims=True);ap=ep*pp[:,:,None]
        rows=[];sm=[]
        for s in range(3):
            sm.append(np.median([metric(d["c"][g],seed[s,g],d["eta"][g],ep[g],d["ab"][g],ap[g],d["p"][g],pp[g])["state_relative_rmse"] for g in range(32)]))
        for g,cid in enumerate(ids):
            r={"case_id":cid,"arm":arm,**metric(d["c"][g],cm[g],d["eta"][g],ep[g],d["ab"][g],ap[g],d["p"][g],pp[g])};rows.append(r);gm.append(r)
        m={k:stats([r[k] for r in rows]) for k in rows[0] if k not in ("case_id","arm")}
        rp=pearson(d["eta"],ep);pc=pearson(d["p"],pp)
        m.update({"routing_pearson":rp,"pscale_pearson":pc,"seed_state_medians":dict(zip(map(str,SEEDS),map(float,sm))),
          "seed_state_median_std":float(np.std(sm)),
          "gates":{"state":m["state_relative_rmse"]["median"]<=.5 and m["state_relative_rmse"]["q95"]<=.8,
          "routing":m["routing_eta_rmse"]["median"]<=.05 and m["routing_eta_rmse"]["q95"]<=.1 and rp>=.95,
          "absolute":m["absolute_order_source_normalized_rmse"]["median"]<=.05 and m["absolute_order_source_normalized_rmse"]["q95"]<=.1,
          "threshold":m["thresholded_absolute_order_relative_median"]["median"]<=.3 and m["thresholded_absolute_order_relative_median"]["q95"]<=.75,
          "pscale":m["total_power_relative_rmse"]["median"]<=.15 and m["total_power_relative_rmse"]["q95"]<=.3 and pc>=.95,
          "seed":float(np.std(sm))<=.03}})
        m["retrospective_h1"]="PASS" if all(m["gates"].values()) else "FAIL";out["arms"][arm]=m
        arr[arm]={"seed":seed,"mean":cm,"eta":ep,"abs":ap,"p":pp}
    keys=list(gm[0].keys())[2:];paired={};deltas={}
    for k in keys:
        dd=np.array([next(r[k] for r in gm if r["case_id"]==cid and r["arm"]=="A1")-next(r[k] for r in gm if r["case_id"]==cid and r["arm"]=="A0") for cid in ids])
        deltas[k]={cid:float(dd[i]) for i,cid in enumerate(ids)}
        paired[k]={"deltas":deltas[k],"distribution":stats(dd),"wins":int((dd<0).sum()),"ties":int((dd==0).sum()),"losses":int((dd>0).sum()),
          "win_rate":float((dd<0).mean()),"tie_rate":float((dd==0).mean()),"loss_rate":float((dd>0).mean())}
    a,b=out["arms"]["A0"],out["arms"]["A1"]
    paired["state_median_improvement"]=(a["state_relative_rmse"]["median"]-b["state_relative_rmse"]["median"])/max(a["state_relative_rmse"]["median"],1e-30)
    paired["routing_median_improvement"]=(a["routing_eta_rmse"]["median"]-b["routing_eta_rmse"]["median"])/max(a["routing_eta_rmse"]["median"],1e-30)
    wtl={k:{z:paired[k][z] for z in ("wins","ties","losses","win_rate","tie_rate","loss_rate")} for k in keys}
    labels={x["case_id"]:lab for lab,items in ood["strata"].items() for x in items};dist={x["case_id"]:x["nearest_HF22_distance"] for x in ood["geometries"]}
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
    core=paired["state_median_improvement"]>=.05 and paired["routing_median_improvement"]>=.05 and paired["state_relative_rmse"]["wins"]>=20 and paired["routing_eta_rmse"]["wins"]>=20
    mixed=(osum["nearest"]["median_state_delta"]<0<osum["farthest"]["median_state_delta"]) or (osum["nearest"]["median_routing_delta"]<0<osum["farthest"]["median_routing_delta"])
    stable=b["seed_state_median_std"]<=.03
    if core and qok and wok and k_ok and stable and not mixed:verdict="COUPLING_ML_NP_FORWARD_FEATURES_SUPPORTED"
    elif paired["state_median_improvement"]>0 or paired["routing_median_improvement"]>0 or paired["state_relative_rmse"]["wins"]>=16 or paired["routing_eta_rmse"]["wins"]>=16:verdict="COUPLING_ML_NP_FORWARD_FEATURES_PARTIAL"
    else:verdict="COUPLING_ML_NP_FORWARD_FEATURES_NOT_SUPPORTED"
    out.update({"paired":paired,"win_tie_loss":wtl,"ood_strata":osum,"verdict":verdict,
      "feature_acceptance":{"both_medians_5pct_and_20_wins":bool(core),"q95_10pct":bool(qok),"worst_25pct":bool(wok),
      "absolute_and_pscale_median_q95_no_worse":bool(k_ok),"seed_stable":bool(stable),"nearest_far_sign_mixed":bool(mixed)},
      "production_h1_status":"NOT_ADMITTED; prospective six-geometry prediction-before-truth gate not run",
      "baseline_production_h1_status":"FAIL; frozen 32G baseline authority unchanged"})
    return out,gm,arr

def main():
    ap=argparse.ArgumentParser()
    g=ap.add_mutually_exclusive_group(required=True);g.add_argument("--freeze-only",action="store_true");g.add_argument("--resume-freeze-only",action="store_true");g.add_argument("--validate-only",action="store_true");g.add_argument("--run-confirmatory",action="store_true")
    args=ap.parse_args()
    os.environ["PYTHONDONTWRITEBYTECODE"]="1";os.environ["CUDA_VISIBLE_DEVICES"]=""
    torch.set_num_threads(1)
    try:torch.set_num_interop_threads(1)
    except RuntimeError:pass
    torch.use_deterministic_algorithms(True)
    req(all(p.device.type=="cpu" for p in Net().parameters()),"model default device is not CPU")
    cx=validate();d=load_data(cx)
    if args.resume_freeze_only:
        req(OUT.exists(),"partial premetric namespace absent")
        allowed=set(PRE_FILES)-{"execution_freeze_v2.json"}
        present={q.name for q in OUT.iterdir() if q.is_file()}
        req(present==allowed,"partial premetric namespace has unexpected/missing files")
        req(not any((OUT/x).exists() for x in RESULTS),"metrics/output already exist; cannot resume premetric freeze")
        da=jread(OUT/"dataset_authority_v2.json")
        req(da["geometry_id_order"]==d["ids"] and da["ordered_D_nm"]==d["geo"].astype(int).tolist(),"partial dataset authority differs from live frozen inputs")
        req(da["case_state_hashes"]==d["hashes"] and da["paired_truth_rows_verified"]==2464 and da["formal_20g_truth_rows_crosschecked"]==1540,"partial dataset provenance mismatch")
        req(da["source_truth_parity_summary"]==d["source_truth_parity_summary"] and da["truth_decoder_closure"]==d["closure"],"partial truth parity/closure mismatch")
        fm_partial=jread(OUT/"feature_manifest_v2.json")
        req(fm_partial["runtime_validation"]==d["feature_check"] and fm_partial["geometry_wavelength_rows"]==352 and fm_partial["support_metadata_as_features"] is False,"partial feature manifest mismatch")
        req(jread(OUT/"fold_manifest_v2.json")==d["fold_manifest"],"partial frozen folds mismatch")
        req(jread(OUT/"ood_support_preregistered_v2.json")==d["support"],"partial frozen support mismatch")
        pre=jread(OUT/"preregistration_v2.json")
        req(pre["source_contract_sha256"]==CONTRACT_SHA and pre["source_20g_preregistration_sha256"]==PREREG_SHA and
            pre["32g_fold_manifest_sha256"]==sha(OUT/"fold_manifest_v2.json") and pre["outer_fold_metrics_computed"] is False,
            "partial 32G preregistration mismatch")
        with (OUT/"np_feature_rows_v2.csv").open("r",encoding="utf-8",newline="") as f: stored=list(csv.DictReader(f))
        req(len(stored)==352,"partial NP feature rows missing")
        exp={(x["case_id"],x["wavelength_nm"]):x for x in d["feature_rows"]}
        for row in stored:
            key=(row["case_id"],int(row["wavelength_nm"]));x=exp[key]
            req(row["geometry_id"]==x["geometry_id"] and row["ordered_D_nm"]==json.dumps(x["ordered_D_nm"],separators=(",",":")),"partial feature row identity mismatch")
            for name,val in zip(d["feature_names"],x["feature_values"]):req(float(row[name])==val,"partial feature value mismatch")
        execution_freeze={"schema":"COUPLING_ML_NP_FORWARD_FEATURE_ABLATION_EXECUTION_V2","status":"PREMETRIC_INPUTS_FROZEN",
          "contract_sha256":CONTRACT_SHA,"runner_sha256":sha(Path(__file__)),"model_template_sha256":V2_TEMPLATE_SHA,
          "coupling_head":git(["git","rev-parse","HEAD"],ROOT),"np_head":NP_HEAD,"CPU_only":True,"CPU_threads":1,
          "all_inputs_and_folds_frozen_before_model_metrics":True,"metric_results_computed":False,"solver_invocations":0,"gpu_used":False,
          "created_utc":datetime.now(timezone.utc).isoformat()}
        atomic_json(OUT/"execution_freeze_v2.json",execution_freeze)
        lock={"schema":"COUPLING_ML_NP_FORWARD_FEATURE_32G_PREMETRIC_LOCK_V2","status":"FROZEN_BEFORE_MODEL_METRICS",
          "contract_sha256":CONTRACT_SHA,"runner_sha256":sha(Path(__file__)),"coupling_head":git(["git","rev-parse","HEAD"],ROOT),
          "np_head":NP_HEAD,"metric_results_computed":False,"pre_metric_files":{name:sha(OUT/name) for name in PRE_FILES},
          "solver_invocations":0,"gpu_used":False,"created_utc":datetime.now(timezone.utc).isoformat()}
        atomic_json(OUT/"premetric_freeze_manifest_v2.json",lock)
        print(json.dumps({"freeze_resume":"PASS","premetric_files":len(lock["pre_metric_files"]),"metric_results_computed":False,
          "solver_invocations":0,"gpu_used":False},sort_keys=True))
        return 0
    if args.freeze_only:
        req(not OUT.exists(),"output namespace already exists; refusing to overwrite")
        OUT.mkdir(parents=True)
        dataset={"schema":"COUPLING_ML_NP_FORWARD_FEATURE_ABLATION_32G_DATASET_AUTHORITY_V2","status":"PASS_32_SCIENTIFIC_VALID_INTEGRATED_3D_PW_CASES",
          "source_32g_authority_path":str(BASE32/"PW_K6_32G_DATASET_AUTHORITY_V1.json"),"source_32g_authority_sha256":AUTH32_SHA,
          "source_32g_artifact_manifest_sha256":ART32_SHA,"source_truth_npz_sha256":"fefc09bbd06d0da06664105540c4f5e0659a51b68b06a07df8c44ed413891d28",
          "truth_sha256":TRUTH_SHA,"physical_contract_sha256":cx["auth32"]["physical_contract_sha256"],
          "geometry_count":32,"paired_geometry_wavelength_rows":352,"paired_order_wavelength_rows":2464,"full_band_scalar_rows":672,"full_band_order_rows":4704,
          "geometry_id_order":d["ids"],"ordered_D_nm":d["geo"].astype(int).tolist(),"paired_wavelength_nm":list(WLS),"polarization":"P_XLIKE incident; outgoing TE/TM state",
          "scientific_entries":32,"stage1_entries":12,"stage1_replays":0,"replay_entries":0,"duplicate_entries":0,
          "case_provenance":cx["auth32"]["case_provenance"],"case_state_hashes":d["hashes"],
          "paired_truth_rows_verified":d["paired_truth_rows"],"formal_20g_truth_rows_crosschecked":d["formal_20g_truth_rows_crosschecked"],"source_truth_parity_summary":d["source_truth_parity_summary"],"truth_decoder_closure":d["closure"],
          "packed_state_20g_parity_max_abs":d["packed_state_20g_parity_max_abs"],"solver_invocations_in_this_analysis":0,"gpu_used":False}
        feature={"schema":"COUPLING_ML_NP_FORWARD_FEATURE_MANIFEST_V2","interface_id":"NP_K6_COUPLING_FORWARD_FEATURE_INTERFACE_V2",
          "provider_id":"NP_LF_FEATURE_PROVIDER_V2","role":"PHYSICS_INFORMED_AUXILIARY_FEATURE_PROVIDER",
          "authority_head":NP_HEAD,"branch":"work/np-k6-mdc-v1","runtime_adapter_path":str(cx["np_adapter"]),"runtime_adapter_sha256":ADAPTER_SHA,
          "interface_manifest_sha256":cx["fm"]["interface_manifest_sha256"],"provenance_hash":cx["fm"]["provenance_hash"],
          "np_cache_path":str(cx["cache"]),"np_cache_sha256":CACHE_SHA,"np_cache_rows":220,"runtime_validation":d["feature_check"],
          "paired_wavelength_nm":list(WLS),"polarization":"P_XLIKE","u_x":0.0,"k_y":0.0,"geometry_count":32,
          "geometry_wavelength_rows":352,"fields_per_wavelength":d["feature_names"],"count_per_wavelength":8,"count_per_geometry":88,
          "flatten_order":"wavelength-major; within wavelength eta_m_proxy m=-3..+3, then T_proxy",
          "feature_semantics":cx["fm"]["feature_definition"]["proxy_semantics"],
          "A0_input_dimension":6,"A1_input_dimension":94,"A1_inputs":"six ordered D1..D6 plus exactly the 88 frozen provider outputs",
          "support_metadata_as_features":False,"complex_amplitude":"NOT_EXPOSED","R":"UNAVAILABLE",
          "not_integrated_truth":True,"not_complex_scattering_operator":True,"not_Jones_matrix":True,"not_MDCxNP_cascade_truth":True,
          "OOD_is_diagnostic_only":True,"A2":"NOT_AVAILABLE","A3":"NOT_AVAILABLE","solver_invocations":0,"gpu_used":False}
        fold=d["fold_manifest"]
        prereg={"schema":"COUPLING_ML_NP_FORWARD_FEATURE_ABLATION_32G_PREREGISTRATION_V2","status":"FROZEN_BEFORE_32G_OUTER_METRICS",
          "source_contract_sha256":CONTRACT_SHA,"source_20g_preregistration_sha256":PREREG_SHA,
          "source_20g_fold_manifest_sha256":sha(OUT20/"fold_manifest_v2.json"),"32g_fold_manifest_sha256":None,
          "geometry_count":32,"outer_fold_metrics_computed":False,"paired_rows":352,"order_rows":2464,
          "fold_rule":"strict LOGO by complete ordered geometry; three GroupKFold geometry splits within each outer training set",
          "same_folds_A0_A1":True,"wavelength_row_random_split":False,"OOD_support_as_model_input":False,
          "contract_thresholds_modified":False,"model_or_preprocessing_modified":False,
          "contract_verdict_mapping":cx["c"]["verdict_mapping"],"contract_feature_acceptance":cx["c"]["feature_value_acceptance"],
          "frozen_at_coupling_head":git(["git","rev-parse","HEAD"],ROOT),"created_utc":datetime.now(timezone.utc).isoformat()}
        atomic_json(OUT/"dataset_authority_v2.json",dataset)
        atomic_json(OUT/"feature_manifest_v2.json",feature)
        with (OUT/"np_feature_rows_v2.csv").open("w",newline="",encoding="utf-8") as f:
            cols=["case_id","geometry_id","ordered_D_nm","wavelength_nm","polarization","u_x","k_y","ood","provenance_hash"]+d["feature_names"]
            wr=csv.DictWriter(f,fieldnames=cols);wr.writeheader()
            for r in d["feature_rows"]:
                vals=dict(zip(d["feature_names"],r["feature_values"]))
                wr.writerow({**{k:r[k] for k in ["case_id","geometry_id","wavelength_nm","polarization","u_x","k_y","ood","provenance_hash"]},
                    "ordered_D_nm":json.dumps(r["ordered_D_nm"],separators=(",",":")),**vals})
        atomic_json(OUT/"fold_manifest_v2.json",fold)
        atomic_json(OUT/"ood_support_preregistered_v2.json",d["support"])
        prereg["32g_fold_manifest_sha256"]=sha(OUT/"fold_manifest_v2.json")
        atomic_json(OUT/"preregistration_v2.json",prereg)
        freeze={"schema":"COUPLING_ML_NP_FORWARD_FEATURE_32G_PREMETRIC_FREEZE_V2","status":"FROZEN_BEFORE_MODEL_METRICS",
          "contract_sha256":CONTRACT_SHA,"runner_sha256":sha(Path(__file__)),"model_template_sha256":V2_TEMPLATE_SHA,
          "coupling_head":git(["git","rev-parse","HEAD"],ROOT),"np_head":NP_HEAD,"metric_results_computed":False,
          "pre_metric_files":{name:sha(OUT/name) for name in PRE_FILES if name!="execution_freeze_v2.json"},"solver_invocations":0,"gpu_used":False,
          "created_utc":datetime.now(timezone.utc).isoformat()}
        atomic_json(OUT/"execution_freeze_v2.json",freeze)
        lock={"schema":"COUPLING_ML_NP_FORWARD_FEATURE_32G_PREMETRIC_LOCK_V2","status":"FROZEN_BEFORE_MODEL_METRICS",
          "contract_sha256":CONTRACT_SHA,"runner_sha256":sha(Path(__file__)),"coupling_head":git(["git","rev-parse","HEAD"],ROOT),
          "np_head":NP_HEAD,"metric_results_computed":False,"pre_metric_files":{name:sha(OUT/name) for name in PRE_FILES},
          "solver_invocations":0,"gpu_used":False,"created_utc":datetime.now(timezone.utc).isoformat()}
        atomic_json(OUT/"premetric_freeze_manifest_v2.json",lock)
        print(json.dumps({"freeze":"PASS","geometry_count":32,"paired_rows":352,"order_rows":2464,"feature_cache_exact":220,"new_runtime_queries":132,
          "folds":32,"ood_exact_overlap":d["support"]["support_exact_overlap_count"],"strata":{k:len(v) for k,v in d["support"]["strata"].items()},
          "metric_results_computed":False,"solver_invocations":0,"gpu_used":False},sort_keys=True))
        return 0
    req(OUT.exists(),"premetric namespace missing; run --freeze-only first")
    fr=jread(OUT/"premetric_freeze_manifest_v2.json")
    if fr.get("software_recovery_record_sha256"):
        req(sha(OUT/"evaluation_software_recovery_v2.json")==fr["software_recovery_record_sha256"],"software recovery provenance changed")
    req(fr["status"]=="FROZEN_BEFORE_MODEL_METRICS" and fr["metric_results_computed"] is False,"premetric freeze manifest invalid")
    req(fr["contract_sha256"]==CONTRACT_SHA and fr["coupling_head"]==BASE_HEAD and fr["runner_sha256"]==sha(Path(__file__)),"freeze authority mismatch")
    for name,h in fr["pre_metric_files"].items():req(sha(OUT/name)==h,"premetric artifact changed: "+name)
    req(jread(OUT/"fold_manifest_v2.json")==d["fold_manifest"],"frozen 32G folds do not reproduce")
    req(jread(OUT/"ood_support_preregistered_v2.json")==d["support"],"frozen 32G support/OOD does not reproduce")
    req(jread(OUT/"feature_manifest_v2.json")["runtime_validation"]==d["feature_check"],"NP runtime feature parity does not reproduce")
    with (OUT/"np_feature_rows_v2.csv").open("r",encoding="utf-8",newline="") as f:
        stored=list(csv.DictReader(f))
    req(len(stored)==352,"frozen feature row count mismatch")
    for r in stored:
        expected=next(x for x in d["feature_rows"] if x["case_id"]==r["case_id"] and x["wavelength_nm"]==int(r["wavelength_nm"]))
        for name,val in zip(d["feature_names"],expected["feature_values"]):req(abs(float(r[name])-val)<=0.0,"frozen NP feature value mismatch")
    req(not any((OUT/x).exists() for x in RESULTS),"confirmatory results already exist; refusing rerun")
    preflight={"status":"PASS","contract_sha256":CONTRACT_SHA,"geometry_count":32,"paired_rows":352,"order_rows":2464,
      "np_feature_rows":352,"cache_exact":220,"new_runtime_queries":132,"ood_exact_overlap":0,"ood_count":32,"strata_sizes":[11,11,10],
      "folds":32,"solver_invocations":0,"gpu_used":False}
    if args.validate_only:
        print(json.dumps({"validation":"PASS",**preflight},sort_keys=True));return 0
    start=time.time();started=datetime.now(timezone.utc).isoformat()
    pred={};ps={};logs={}
    for arm in ("A0","A1"):
        print(json.dumps({"fit_arm":arm,"start_utc":datetime.now(timezone.utc).isoformat(),"cpu_threads":1}),flush=True)
        pred[arm],ps[arm],logs[arm]=fitarm(d,d["fold_manifest"],arm)
        print(json.dumps({"fit_arm":arm,"complete":True,"outer_folds":32,"seeds":list(SEEDS)}),flush=True)
    ood=jread(OUT/"ood_support_preregistered_v2.json")
    summary,gm,arr=evaluate(d,pred,ps,ood)
    labels={cid:lab for lab,x in summary["ood_strata"].items() for cid in x["case_ids"]}
    compare=comparison_20g_32g(cx["old_metrics"],summary)
    atomic_json(OUT/"paired_ablation_metrics_v2.json",summary)
    atomic_json(OUT/"fold_execution_v2.json",{"status":"COMPLETE","by_arm":logs,"frozen_fold_hash":sha(OUT/"fold_manifest_v2.json"),
      "solver_invocations":0,"gpu_used":False,"cpu_threads":1})
    with (OUT/"per_geometry_metrics_v2.csv").open("w",newline="",encoding="utf-8") as f:
        cols=["case_id","arm","ood_stratum","state_relative_rmse","routing_eta_rmse","absolute_order_source_normalized_rmse","thresholded_absolute_order_relative_median","total_power_relative_rmse"]
        wr=csv.DictWriter(f,fieldnames=cols);wr.writeheader()
        for r in gm:wr.writerow({**r,"ood_stratum":labels[r["case_id"]]})
    seedcols=[f"{a}_seed{s}_{pol}_{part}" for a in ("A0","A1") for s in SEEDS for pol in ("TE","TM") for part in ("re","im")]
    cols=["case_id","ordered_D_nm","wavelength_nm","order_x","eta_true","abs_order_true","P_scale_true",
      "C_hat_true_TE_re","C_hat_true_TE_im","C_hat_true_TM_re","C_hat_true_TM_im",
      "A0_C_hat_mean_TE_re","A0_C_hat_mean_TE_im","A0_C_hat_mean_TM_re","A0_C_hat_mean_TM_im",
      "A1_C_hat_mean_TE_re","A1_C_hat_mean_TE_im","A1_C_hat_mean_TM_re","A1_C_hat_mean_TM_im",
      "A0_eta","A1_eta","A0_abs_order","A1_abs_order","A0_P_scale","A1_P_scale"]+seedcols
    with (OUT/"oof_predictions_v2.csv").open("w",newline="",encoding="utf-8") as f:
        wr=csv.DictWriter(f,fieldnames=cols);wr.writeheader()
        for gi,cid in enumerate(d["ids"]):
            for li,wl in enumerate(WLS):
                for oi,m in enumerate(ORD):
                    row={"case_id":cid,"ordered_D_nm":json.dumps(d["geo"][gi].astype(int).tolist(),separators=(",",":")),
                      "wavelength_nm":wl,"order_x":m,"eta_true":d["eta"][gi,li,oi],"abs_order_true":d["ab"][gi,li,oi],"P_scale_true":d["p"][gi,li]}
                    for pi,pol in enumerate(("TE","TM")):
                        z=d["c"][gi,li,oi,pi];row[f"C_hat_true_{pol}_re"]=z.real;row[f"C_hat_true_{pol}_im"]=z.imag
                    for arm in ("A0","A1"):
                        cm=arr[arm]["mean"];route=d["w"][gi,li]*np.sum(abs(cm[gi,li])**2,axis=-1);route/=route.sum()
                        for pi,pol in enumerate(("TE","TM")):
                            z=cm[gi,li,oi,pi];row[f"{arm}_C_hat_mean_{pol}_re"]=z.real;row[f"{arm}_C_hat_mean_{pol}_im"]=z.imag
                        row[f"{arm}_eta"]=route[oi];row[f"{arm}_abs_order"]=route[oi]*ps[arm][gi,li];row[f"{arm}_P_scale"]=ps[arm][gi,li]
                        for si,s in enumerate(SEEDS):
                            for pi,pol in enumerate(("TE","TM")):
                                z=pred[arm][si,gi,li,oi,pi];row[f"{arm}_seed{s}_{pol}_re"]=z.real;row[f"{arm}_seed{s}_{pol}_im"]=z.imag
                    wr.writerow(row)
    atomic_json(OUT/"leakage_audit_v2.json",{"schema":"COUPLING_ML_NP_FORWARD_FEATURE_ABLATION_LEAKAGE_AUDIT_V2","status":"PASS",
      "solver_invocations":0,"gpu_used":False,"NP_runtime_reads_Coupling_HF_labels":False,"cache_label_blind":True,
      "heldout_labels_used_for_feature_generation":False,"A0_inputs":["ordered D1-D6"],"A1_inputs":["ordered D1-D6"]+d["feature_names"],
      "support_metadata_as_features":False,"preprocessing_train_fold_only":True,"PCA_train_fold_only":True,
      "same_target_rows_A0_A1":True,"same_outer_folds_A0_A1":True,"wavelength_random_split":False,
      "dipole_or_final_validation_leakage":False,"outer_fold_count":32,"outer_geometry_checks":[
      {"fold":f["outer_fold"],"heldout":f["test_geometry_id"],"heldout_absent":f["test_geometry_id"] not in f["train_geometry_ids"],"train_n":len(f["train_geometry_ids"])} for f in d["fold_manifest"]["fold_assignments"]["folds"]],
      "NP_runtime_parity":d["feature_check"],"cache_sha256":CACHE_SHA,"OOD_metadata_input":False})
    enriched={}
    for lab,items in ood["strata"].items():
        enriched[lab]={"count":len(items),"case_ids":[x["case_id"] for x in items],
          "median_state_delta":summary["ood_strata"][lab]["median_state_delta"],
          "median_routing_delta":summary["ood_strata"][lab]["median_routing_delta"],
          "state_wins":summary["ood_strata"][lab]["state_wins"],"routing_wins":summary["ood_strata"][lab]["routing_wins"],
          "members":[{**x,"state_delta_A1_minus_A0":summary["paired"]["state_relative_rmse"]["deltas"][x["case_id"]],
            "routing_delta_A1_minus_A0":summary["paired"]["routing_eta_rmse"]["deltas"][x["case_id"]]} for x in items]}
    atomic_json(OUT/"ood_support_analysis_v2.json",{"schema":"COUPLING_ML_NP_FORWARD_FEATURE_OOD_SUPPORT_V2","status":"POST_METRIC_DIAGNOSTIC_ONLY",
      "frozen_support_file_sha256":sha(OUT/"ood_support_preregistered_v2.json"),"frozen_before_32g_outer_metrics":True,
      "exact_HF22_overlap_count":ood["support_exact_overlap_count"],"extrapolative_count":ood["extrapolative_count"],
      "strata":enriched,"prediction_error_by_stratum":{k:{"state_relative_rmse_delta":v["median_state_delta"],"routing_eta_rmse_delta":v["median_routing_delta"]} for k,v in enriched.items()},
      "support_metadata_used_as_model_input":False,"solver_invocations":0})
    h1pass=all(all(v.values()) for v in (summary["arms"]["A0"]["gates"],summary["arms"]["A1"]["gates"]))
    accept=summary["feature_acceptance"]
    atomic_json(OUT/"verdict_v2.json",{"schema":"COUPLING_ML_NP_FORWARD_FEATURE_ABLATION_VERDICT_V2",
      "feature_value_verdict":summary["verdict"],"production_H1_status":summary["production_h1_status"],
      "baseline_production_H1_status":summary["baseline_production_h1_status"],
      "retrospective_H1":{"A0":summary["arms"]["A0"]["retrospective_h1"],"A1":summary["arms"]["A1"]["retrospective_h1"],"both_pass":h1pass},
      "feature_acceptance":accept,"feature_effect_replication_status":compare["overall_feature_effect_replication_status"],
      "production_admission_changed":False,"solver_invocations":0,"gpu_used":False})
    atomic_json(OUT/"comparison_20g_vs_32g_v2.json",compare)
    execution={"schema":"COUPLING_ML_NP_FORWARD_FEATURE_ABLATION_EXECUTION_V2","status":"COMPLETE_ZERO_SOLVER_CPU_ONLY",
      "contract_sha256":CONTRACT_SHA,"premetric_freeze_manifest_sha256":sha(OUT/"premetric_freeze_manifest_v2.json"),
      "started_utc":started,"completed_utc":datetime.now(timezone.utc).isoformat(),"elapsed_seconds":time.time()-start,
      "CPU_only":True,"torch_cuda_visible_devices":"","torch_cuda_available":"NOT_QUERIED","model_device":"CPU_EXPLICIT","CPU_threads":1,"deterministic_algorithms":True,
      "seeds":list(SEEDS),"geometry_count":32,"paired_rows":352,"target_order_rows":2464,"solver_invocations":0,"gpu_used":False,
      "gpu_runner_invocations":0,"HF_acquisitions":0,"architecture_search":False}
    atomic_json(OUT/"execution_manifest_v2.json",execution)
    report=["# COUPLING_ML_NP_FORWARD_FEATURE_ABLATION_32G_CONFIRMATORY_V2","",
      "STATUS: COMPLETE_ZERO_SOLVER_CPU_ONLY","",
      f"Frozen V2 contract SHA256: {CONTRACT_SHA}. Solver invocations: 0; GPU/Runner invocations: 0; additional HF: 0.",
      "Dataset: 32 frozen ordered geometries; paired P/XLIKE 445-455 nm at 1 nm; 352 geometry-wavelength rows / 2464 order rows.",
      f"NP V2: 220 cached queries exact runtime parity plus 132 new-geometry deterministic runtime queries; HF22 exact overlap {ood['support_exact_overlap_count']}/32; runtime-domain valid {ood['runtime_domain_valid_count']}/32.",
      f"Truth-state parity to archived 20G labels max absolute difference: {d['packed_state_20g_parity_max_abs']:.3g}; modal-to-routing closure max: {d['closure']['max']:.6g}.",
      "","## Confirmatory questions","",
      f"Q1 routing: A0 median/q95 {summary['arms']['A0']['routing_eta_rmse']['median']:.6g}/{summary['arms']['A0']['routing_eta_rmse']['q95']:.6g}; A1 {summary['arms']['A1']['routing_eta_rmse']['median']:.6g}/{summary['arms']['A1']['routing_eta_rmse']['q95']:.6g}; A1-A0 paired wins/ties/losses {summary['win_tie_loss']['routing_eta_rmse']['wins']}/{summary['win_tie_loss']['routing_eta_rmse']['ties']}/{summary['win_tie_loss']['routing_eta_rmse']['losses']}; Pearson A0/A1 {summary['arms']['A0']['routing_pearson']:.6g}/{summary['arms']['A1']['routing_pearson']:.6g}.",
      f"Q1 absolute order source-normalized: A0 median/q95 {summary['arms']['A0']['absolute_order_source_normalized_rmse']['median']:.6g}/{summary['arms']['A0']['absolute_order_source_normalized_rmse']['q95']:.6g}; A1 {summary['arms']['A1']['absolute_order_source_normalized_rmse']['median']:.6g}/{summary['arms']['A1']['absolute_order_source_normalized_rmse']['q95']:.6g}. Thresholded relative median/q95 A0 {summary['arms']['A0']['thresholded_absolute_order_relative_median']['median']:.6g}/{summary['arms']['A0']['thresholded_absolute_order_relative_median']['q95']:.6g}; A1 {summary['arms']['A1']['thresholded_absolute_order_relative_median']['median']:.6g}/{summary['arms']['A1']['thresholded_absolute_order_relative_median']['q95']:.6g}.",
      f"Q2 complex state: A0 median/q95/worst {summary['arms']['A0']['state_relative_rmse']['median']:.6g}/{summary['arms']['A0']['state_relative_rmse']['q95']:.6g}/{summary['arms']['A0']['state_relative_rmse']['max']:.6g}; A1 {summary['arms']['A1']['state_relative_rmse']['median']:.6g}/{summary['arms']['A1']['state_relative_rmse']['q95']:.6g}/{summary['arms']['A1']['state_relative_rmse']['max']:.6g}.",
      f"Q3 20G-to-32G feature-effect classification: {compare['overall_feature_effect_replication_status']} (routing and source-normalized absolute-order paired geometry median deltas; see comparison JSON).",
      f"Q4 production H1 unchanged: frozen 32G baseline H1 FAIL; confirmatory retrospective gates A0/A1 {summary['arms']['A0']['retrospective_h1']}/{summary['arms']['A1']['retrospective_h1']}; production remains NOT_ADMITTED because prospective six-geometry gate was not run.",
      "","## 20G vs 32G paired feature effects","",
      "| Metric | 20G median(A1-A0) | 32G median(A1-A0) | 20G wins/ties/losses | 32G wins/ties/losses |",
      "|---|---:|---:|---:|---:|"]
    for k,nm in [("state_relative_rmse","State"),("routing_eta_rmse","Routing"),("absolute_order_source_normalized_rmse","Absolute order"),("thresholded_absolute_order_relative_median","Thresholded absolute"),("total_power_relative_rmse","P_scale")]:
        p20=cx["old_metrics"]["paired"][k];p32=summary["paired"][k]
        report.append(f"| {nm} | {p20['distribution']['median']:.6g} | {p32['distribution']['median']:.6g} | {p20['wins']}/{p20['ties']}/{p20['losses']} | {p32['wins']}/{p32['ties']}/{p32['losses']} |")
    report += ["",f"Feature value verdict: {summary['verdict']}. 32G preregistered supported gate: {json.dumps(accept,sort_keys=True)}.",
      f"20G feature verdict was {cx['old_metrics']['verdict']}; 32G feature-effect replication status is {compare['overall_feature_effect_replication_status']}.",
      "20G and 32G H1 are independent frozen production authorities; baseline conclusion remains DATA_COVERAGE_NOT_PRIMARY_BOTTLENECK. No production H1 admission was changed.",
      "OOD/support strata are diagnostic only and were never passed to either predictor. NP LF features are auxiliary proxies, not integrated truth, a scattering operator, Jones matrix, or MDCxNP cascade.",
      "A2/A3 remain unavailable. No new model family, HF, prospective gate, inverse design, solver, or GPU work was run.",
      "","## OOD support strata",""]
    for lab in ("nearest","middle","farthest"):
        s=summary["ood_strata"][lab];report.append(f"- {lab} n={s['count']}: median state delta={s['median_state_delta']:.6g} (wins {s['state_wins']}), routing delta={s['median_routing_delta']:.6g} (wins {s['routing_wins']}).")
    report += ["","## H1 metrics","",
      "| Arm | State median/q95 | Routing median/q95/Pearson | Absolute median/q95 | Thresholded median/q95 | P_scale median/q95/Pearson | Seed std | H1 |",
      "|---|---|---|---|---|---|---:|---|"]
    for arm in ("A0","A1"):
        m=summary["arms"][arm]
        report.append(f"| {arm} | {m['state_relative_rmse']['median']:.6g}/{m['state_relative_rmse']['q95']:.6g} | {m['routing_eta_rmse']['median']:.6g}/{m['routing_eta_rmse']['q95']:.6g}/{m['routing_pearson']:.6g} | {m['absolute_order_source_normalized_rmse']['median']:.6g}/{m['absolute_order_source_normalized_rmse']['q95']:.6g} | {m['thresholded_absolute_order_relative_median']['median']:.6g}/{m['thresholded_absolute_order_relative_median']['q95']:.6g} | {m['total_power_relative_rmse']['median']:.6g}/{m['total_power_relative_rmse']['q95']:.6g}/{m['pscale_pearson']:.6g} | {m['seed_state_median_std']:.6g} | {m['retrospective_h1']} |")
    report += ["","NEXT: CHART_REVIEW_32G_H1_AND_NP_FEATURE_CONFIRMATORY_RESULT (not executed)."]
    (OUT/"COUPLING_ML_NP_FORWARD_FEATURE_ABLATION_32G_CONFIRMATORY_V2.md").write_text("\n".join(report)+"\n",encoding="utf-8")
    ah={p.name:{"sha256":sha(p),"bytes":p.stat().st_size} for p in sorted(OUT.iterdir()) if p.is_file() and p.name!="artifact_hashes.json" and p.name!="premetric_freeze_manifest_v2.json"}
    ah.update({"contract_sha256":CONTRACT_SHA,"preregistration_sha256":PREREG_SHA,"np_head":NP_HEAD,"np_cache_sha256":CACHE_SHA,
      "np_adapter_sha256":ADAPTER_SHA,"np_support_manifest_sha256":sha(cx["support_path"]),"hf22_csv_sha256":sha(cx["hf22"]),
      "32g_dataset_authority_sha256":AUTH32_SHA,"32g_artifact_manifest_sha256":ART32_SHA,"32g_truth_npz_sha256":"fefc09bbd06d0da06664105540c4f5e0659a51b68b06a07df8c44ed413891d28",
      "truth_sha256":TRUTH_SHA,"h1_authority_sha256":H1_SHA,"h1_20g_sha256":H1_20_SHA,"h1_32g_sha256":H1_32_SHA,
      "stage1_closeout_sha256":STAGE1_SHA,"baseline_delta_sha256":DELTA_SHA,"coupling_head_before_commit":BASE_HEAD,
      "confirmatory_runner_sha256":sha(Path(__file__)),"source_model_template_sha256":V2_TEMPLATE_SHA,"solver_invocations":0,"gpu_used":False,
      "NP_runtime_parity":d["feature_check"],"decoder_closure":d["closure"],"packed_state_20g_parity_max_abs":d["packed_state_20g_parity_max_abs"],
      "case_artifacts":d["hashes"],"premetric_manifest_sha256":sha(OUT/"premetric_freeze_manifest_v2.json")})
    atomic_json(OUT/"artifact_hashes.json",ah)
    print(json.dumps({"status":"COMPLETE","feature_verdict":summary["verdict"],"feature_effect_replication":compare["overall_feature_effect_replication_status"],
      "A0_H1":summary["arms"]["A0"]["retrospective_h1"],"A1_H1":summary["arms"]["A1"]["retrospective_h1"],
      "production_H1":"NOT_ADMITTED","solver_invocations":0,"gpu_used":False,"elapsed_seconds":execution["elapsed_seconds"]},sort_keys=True))
    return 0

def comparison_20g_32g(m20,m32):
    keys=("state_relative_rmse","routing_eta_rmse","absolute_order_source_normalized_rmse","thresholded_absolute_order_relative_median","total_power_relative_rmse")
    detail={}
    for k in keys:
        x=m20["paired"][k];y=m32["paired"][k]
        d20={"paired_delta_distribution":x["distribution"],"wins":x["wins"],"ties":x["ties"],"losses":x["losses"],
          "A1_minus_A0_arm_median":m20["arms"]["A1"][k]["median"]-m20["arms"]["A0"][k]["median"],
          "A1_minus_A0_arm_q95":m20["arms"]["A1"][k]["q95"]-m20["arms"]["A0"][k]["q95"]}
        d32={"paired_delta_distribution":y["distribution"],"wins":y["wins"],"ties":y["ties"],"losses":y["losses"],
          "A1_minus_A0_arm_median":m32["arms"]["A1"][k]["median"]-m32["arms"]["A0"][k]["median"],
          "A1_minus_A0_arm_q95":m32["arms"]["A1"][k]["q95"]-m32["arms"]["A0"][k]["q95"]}
        v20=float(x["distribution"]["median"]);v32=float(y["distribution"]["median"])
        if v20*v32<0:status="REVERSES"
        elif v20<0 and v32<0:
            if abs(v32)>abs(v20):status="STRENGTHENS"
            elif abs(v32)<abs(v20):status="WEAKENS"
            else:status="REPLICATES"
        elif v20>0 and v32>0:
            if abs(v32)>abs(v20):status="STRENGTHENS_DEGRADATION"
            elif abs(v32)<abs(v20):status="WEAKENS_DEGRADATION"
            else:status="REPLICATES_DEGRADATION"
        elif v20==0 and v32==0:status="REPLICATES_NO_MEDIAN_EFFECT"
        elif v20==0:status="NEW_32G_DIRECTION"
        else:status="NO_32G_MEDIAN_EFFECT"
        detail[k]={"20G":d20,"32G":d32,"direction_status":status}
    prim=[detail[k]["direction_status"] for k in ("routing_eta_rmse","absolute_order_source_normalized_rmse")]
    if "REVERSES" in prim: overall="REVERSES"
    elif all(x=="STRENGTHENS" for x in prim):overall="STRENGTHENS"
    elif all(x=="WEAKENS" for x in prim):overall="WEAKENS"
    elif all(x in ("REPLICATES","STRENGTHENS","WEAKENS") for x in prim):overall="REPLICATES"
    else:overall="MIXED_DIRECTION"
    strata={}
    for lab in ("nearest","middle","farthest"):
        a=m20["ood_strata"][lab];b=m32["ood_strata"][lab]
        strata[lab]={"20G":{"n":a["count"],"median_state_delta":a["median_state_delta"],"median_routing_delta":a["median_routing_delta"],"state_wins":a["state_wins"],"routing_wins":a["routing_wins"]},
          "32G":{"n":b["count"],"median_state_delta":b["median_state_delta"],"median_routing_delta":b["median_routing_delta"],"state_wins":b["state_wins"],"routing_wins":b["routing_wins"]}}
    return {"schema":"COUPLING_ML_NP_FORWARD_FEATURE_EFFECT_20G_VS_32G_V2","status":"COMPLETE",
      "classification_rule":"compare the sign and absolute magnitude of paired per-geometry median(A1-A0) for routing and source-normalized absolute-order errors; lower is favorable. This is descriptive only and does not change frozen gates.",
      "overall_feature_effect_replication_status":overall,"primary_metrics":{"routing_eta_rmse":prim[0],"absolute_order_source_normalized_rmse":prim[1]},
      "metrics":detail,"ood_strata":strata,"20G_feature_verdict":m20["verdict"],"32G_feature_verdict":m32["verdict"],
      "baseline_H1_independence_preserved":True,"production_H1_changed":False,"solver_invocations":0,"gpu_used":False}

if __name__=="__main__":
    sys.exit(main())
