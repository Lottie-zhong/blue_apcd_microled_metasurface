#!/usr/bin/env python
"""Response-blind V2 K6 geometry sampler; never reads response arrays or constructs an FSP."""
import csv,hashlib,itertools,json,platform
from pathlib import Path
from collections import Counter
import numpy as np,scipy
from scipy.stats import qmc

ROOT=Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1"); BASE=ROOT/"reports"/"coupling"
V1=BASE/"COUPLING_ML_K6_GLOBAL_DATASET_AND_LEARNING_PROTOCOL_V1"
OUT=BASE/"COUPLING_ML_K6_GLOBAL_PROTOCOL_SCIENTIFIC_REVISION_V2"
RUNNER=Path(r"D:\project\worktrees\blue_apcd_gpu_production_runner_v1")
PROTO=OUT/"REVISED_PREREGISTERED_PROTOCOL_V2.json"
PROTO_SHA="4a041dfc9b9fd8bbc79edfd792d698d0240163de157144029ad51a41c104f44a"
PATHS={
"domain":BASE/"PW_K6_GEOMETRY_DOMAIN_AUTHORITY_V1.json",
"dataset_authority":BASE/"PW_K6_STAGE1_32G_FROZEN_FORWARD_H1_V1"/"PW_K6_32G_DATASET_AUTHORITY_V1.json",
"truth_geometry":BASE/"PW_K6_STAGE1_32G_FROZEN_FORWARD_H1_V1"/"dataset_truth_32g.npz",
"expansion":BASE/"PW_K6_FIXED_MDC_UNBIASED_EXPANSION_MANIFEST_V1.json",
"exclusion":BASE/"PW_K6_GEOMETRY_EXCLUSION_REGISTRY_V1.json",
"pool":BASE/"PW_K6_EXTENSION_ELIGIBLE_CANDIDATE_POOL_V1.json",
"local":BASE/"COUPLING_ML_K6_LOCAL_LEARNABILITY_DOE_PLAN_V1"/"CANDIDATE_MANIFEST_V1.json",
"h1":BASE/"PW_K6_H1_NUMERIC_GATE_AUTHORITY_V1.json",
"v1protocol":V1/"PREREGISTERED_PROTOCOL_V1.json",
"v1csv":V1/"GLOBAL_DATASET_CANDIDATES_V1.csv",
"v1folds":V1/"DEVELOPMENT_FOLD_MANIFEST_V1.csv",
"v1audit":V1/"SAMPLING_COVERAGE_AUDIT_V1.json",
"v1report":V1/"COUPLING_ML_K6_GLOBAL_DATASET_AND_LEARNING_PROTOCOL_V1.md",
"v1generator":V1/"generate_global_dataset_design_v1.py",
"runner_md":RUNNER/"docs"/"APCD_GPU_PRODUCTION_RUNNER_V1_HANDOFF.md",
"runner_json":RUNNER/"APCD_GPU_PRODUCTION_RUNNER_V1_HANDOFF.json",
"runner_authority":RUNNER/"APCD_GPU_PRODUCTION_RUNNER_V1_AUTHORITY.json",
"monitor_report":BASE/"COUPLING_ML_POSTNP_MONITOR_VALIDITY_AUDIT_V1"/"POSTNP_MONITOR_VALIDITY_AUDIT_REPORT_V1.md",
"monitor_cont":BASE/"COUPLING_ML_POSTNP_MONITOR_VALIDITY_AUDIT_V1"/"CONTINUATION.md",
"ext02_cont":BASE/"COUPLING_ML_EXT02_TWO_AIR_PLANES_VALIDATION_V1"/"CONTINUATION.md",
"trainval_cont":BASE/"COUPLING_ML_TRAIN_VALIDATION_TRAJECTORY_AUDIT_V1"/"CONTINUATION.md",
"local_cont":BASE/"COUPLING_ML_K6_LOCAL_LEARNABILITY_DOE_PLAN_V1"/"CONTINUATION.md"}
EXPECTED={
"domain":"93915ffad1159517895f28e8258d3c2341e371cfab1d139a7872f287b919a31f",
"dataset_authority":"0fae0577247866549cf85db88ab5d6f924795423adca4b8cf2742449736f6f2e",
"truth_geometry":"fefc09bbd06d0da06664105540c4f5e0659a51b68b06a07df8c44ed413891d28",
"expansion":"4cf521c18576c34407c158a20f748fe560910909728bed5cdadf53ec9fbe2e7f",
"exclusion":"78f48a4400d5ab469a2054a8ad849d5cae16cb4bee042e2b542529a78973bb80",
"pool":"387112fda12b2fbee0b2e6e4185014e0fad4bbb825b2d9e6cded865b4988073d",
"local":"66fef2027885ac5c479072da3af78b6a5f975b53ef1dc1f6894751c96ee73cd4",
"h1":"8cf71239757e70eb75fbbf858a82c12f8af8d03c0892b99ff4ffce6a959fcdbd",
"v1protocol":"e18ea780917107c437d425293ff1da5628241221197e889cc22696e90d242abd",
"v1csv":"f09d238177054e71741670ae263411949731ff78108ac9fd00801a277fdd8c31",
"v1folds":"5e36a0628222de1b565505dc5c05ecd29b21f966cab422ad99a300b049c0e098",
"v1audit":"3137d5721f7524e0abe7c6df24ad3439cf908df69572376e9cd3f86cdf9d8d70",
"v1report":"f0ea9ec5691bf57ddb9ca7d9c2f25b39f6e0ce520a7b256cdd4165d9bd6fe766",
"v1generator":"295d2598fc97a9a1fa1282c1512155a8e27430c7f4f259d55fdd188136f67345",
"runner_md":"397e41476938392d43e7eaf6c5252425991a8bfa62b7fb88442bf5da4fe0feb7",
"runner_json":"ca7e4a9fcc15ccb60f4921feb788bf3663e1b8fd3c56f64892894cc8299df599",
"runner_authority":"021951707cd94d62ca93076f5f2a6867b400df4c9921932286b32ffc1840972c",
"monitor_report":"7069c764e780f8e5a98f980a026e0cd497268705a211da596bab38c8bb05e71f",
"local_cont":"e8e210122197aca0181ea243a2f642212f159dee71d404f2b9c51a154ccb7e94",
"trainval_cont":"e1ec647c9e6744159acdb858e6b8fb659a71b9d450504c5b98a838b39acf79d2",
"monitor_cont":"b4cd6e42fef431208084262079976102f31691924e69c727d6696f9097ada3ae",
"ext02_cont":"d77a27d3131cb7e8ce5144d8f3a1c9b2c65d6e9da4cef00a4a99bac3a5de9621"}
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def jread(p): return json.loads(Path(p).read_text(encoding="utf-8-sig"))
def jwrite(p,x):
    with Path(p).open("w",encoding="utf-8",newline="\n") as f:f.write(json.dumps(x,indent=2,ensure_ascii=True)+"\n")
def quant(seed,m):
    u=qmc.Sobol(d=6,scramble=True,seed=seed).random_base2(m=m)
    a=(100+5*np.floor(u*27).astype(np.int16)).astype(np.int16)
    _,idx=np.unique(a,axis=0,return_index=True);idx.sort()
    return a[idx],int(len(a)-len(idx))
def geo(v):
    x=np.asarray(v,dtype=float);return float(np.min(290-(x+np.roll(x,-1))/2)),float(145-np.max(x)/2)
def feasible(a):
    x=a.astype(float);return (np.min(290-(x+np.roll(x,-1,axis=1))/2,axis=1)>=60)&(145-x.max(axis=1)/2>=30)
def keys(a):
    c=np.ascontiguousarray(a,dtype=np.int16);return c.view(np.dtype((np.void,c.dtype.itemsize*6))).reshape(-1)
def mask(v):
    z=0
    for i,x in enumerate(v):
        if x==100:z|=1<<(2*i)
        elif x==230:z|=1<<(2*i+1)
    return z
def labels(m):
    r=[]
    for i in range(6):
        if m&(1<<(2*i)):r.append(f"D{i+1}=100")
        if m&(1<<(2*i+1)):r.append(f"D{i+1}=230")
    return r or ["INTERIOR"]
def stats(a):
    a=np.asarray(a,dtype=float)
    if not len(a):return {"n":0}
    q=np.quantile(a,[0,.05,.25,.5,.75,.95,1])
    return {"n":int(len(a)),"min":float(q[0]),"q05":float(q[1]),"q25":float(q[2]),"median":float(q[3]),"q75":float(q[4]),"q95":float(q[5]),"max":float(q[6]),"mean":float(a.mean())}
def dmat(a,b):
    A=np.asarray(a,dtype=float).reshape((-1,6));B=np.asarray(b,dtype=float).reshape((-1,6))
    if not len(A) or not len(B):return np.empty((len(A),len(B)))
    return np.sqrt(np.sum((A[:,None,:]-B[None,:,:])**2,axis=2))/130
def nn(a,b,same=False):
    d=dmat(a,b)
    if same:np.fill_diagonal(d,np.inf)
    return stats(d.min(axis=1)) if d.size else {"n":0}
def min_d2(c,r):
    P=np.asarray(c,dtype=float).reshape((-1,6));R=np.asarray(r,dtype=float).reshape((-1,6));o=np.empty(len(P))
    for s in range(0,len(P),2048):
        d=P[s:s+2048,None,:]-R[None,:,:];o[s:s+2048]=np.min(np.sum(d*d,axis=2),axis=1)/16900
    return o
def greedy(c,k,r):
    P=np.asarray(c,dtype=np.int16).reshape((-1,6))
    if len(P)<k:raise RuntimeError(f"Stratum short: {len(P)} < {k}")
    sc=min_d2(P,r);used=np.zeros(len(P),bool);out=[]
    for _ in range(k):
        j=int(np.argmax(np.where(used,-np.inf,sc)))
        if used[j] or not np.isfinite(sc[j]):raise RuntimeError("maximin exhausted")
        v=P[j].copy();out.append(tuple(int(x) for x in v));used[j]=1
        d=P.astype(float)-v.astype(float);sc=np.minimum(sc,np.sum(d*d,axis=1)/16900)
    return out
def summary(rows):
    a=np.asarray(rows,dtype=np.int16).reshape((-1,6));n=len(a)
    ex=(a==100)|(a==230);near=(a<=110)|(a>=220);ba=ex.any(axis=1);bn=near.any(axis=1)
    coords={}
    for i in range(6):
        c=a[:,i];coords[f"D{i+1}"]={"min":int(c.min()),"max":int(c.max()),"unique_levels":int(len(np.unique(c))),"levels":[int(x) for x in np.unique(c)],"at100":int((c==100).sum()),"at230":int((c==230).sum()),"within10":int(((c<=110)|(c>=220)).sum())}
    proj=[];coarse=[]
    for i,j in itertools.combinations(range(6),2):
        proj.append(int(len(np.unique(a[:,[i,j]],axis=0))))
        bi=np.minimum(((a[:,i]-100)//5)//9,2);bj=np.minimum(((a[:,j]-100)//5)//9,2);coarse.append(len(set(zip(bi.tolist(),bj.tolist()))))
    bc=ex.sum(axis=1);g=[geo(v)[0] for v in a];m=[geo(v)[1] for v in a]
    return {"n":n,"boundary":{"exact_any":int(ba.sum()),"exact_fraction":float(ba.mean()),"within10_any":int(bn.sum()),"within10_fraction":float(bn.mean()),"boundary_coordinate_count_hist":{str(i):int((bc==i).sum()) for i in range(7)},"at100":[int((a[:,i]==100).sum()) for i in range(6)],"at230":[int((a[:,i]==230).sum()) for i in range(6)]},
      "coordinates":coords,"ordered_2d":{"unique_cells_out_of_729":{"min":min(proj),"median":float(np.median(proj)),"max":max(proj),"all_pairs":proj},"occupied_3x3_bins_out_of_9":{"min":min(coarse),"median":float(np.median(coarse)),"max":max(coarse),"all_pairs":coarse}},
      "within_set_normalized_nn":nn(a,a,True),"clearance_nm":stats(g),"half_cell_margin_nm":stats(m)}
def boundary_only(rows):
    a=np.asarray(rows,dtype=np.int16).reshape((-1,6))
    ex=(a==100)|(a==230);near=(a<=110)|(a>=220);bc=ex.sum(axis=1)
    return {"exact_any":int(ex.any(axis=1).sum()),"exact_fraction":float(ex.any(axis=1).mean()),
      "within10_any":int(near.any(axis=1).sum()),"within10_fraction":float(near.any(axis=1).mean()),
      "boundary_coordinate_count_hist":{str(i):int((bc==i).sum()) for i in range(7)},
      "at100":[int((a[:,i]==100).sum()) for i in range(6)],"at230":[int((a[:,i]==230).sum()) for i in range(6)]}
def probe(seed,refs):
    p,_=quant(seed,15);R=np.asarray(refs,float);ds=[]
    for s in range(0,len(p),512):
        d=p[s:s+512,None,:].astype(float)-R[None,:,:];ds.extend((np.sqrt(np.min(np.sum(d*d,axis=2),axis=1))/130).tolist())
    return {"seed":seed,"n":len(p),"nearest_distance":stats(ds)}
def main():
    OUT.mkdir(parents=True,exist_ok=True)
    if scipy.__version__!="1.15.3":raise RuntimeError(f"Requires SciPy1.15.3; got {scipy.__version__}")
    if sha(PROTO)!=PROTO_SHA:raise RuntimeError("V2 prereg hash mismatch")
    if jread(PROTO)["status"]!="FROZEN_BEFORE_V2_POINT_GENERATION":raise RuntimeError("Protocol not frozen")
    ih={k:sha(v) for k,v in PATHS.items()}
    for k,h in EXPECTED.items():
        if ih[k]!=h:raise RuntimeError(f"Frozen authority/input {k} hash mismatch: {ih[k]}")
    domain=jread(PATHS["domain"]);exp=jread(PATHS["expansion"]);exc=jread(PATHS["exclusion"]);pool=jread(PATHS["pool"]);local=jread(PATHS["local"])
    with np.load(PATHS["truth_geometry"],allow_pickle=False) as z:
        old_ids=[str(v) for v in z["case_ids"].tolist()]
        old=[tuple(int(x) for x in r) for r in z["ordered_D_nm"].tolist()]
    if len(old)!=32 or len(set(old))!=32:raise RuntimeError("Existing32 geometry inventory mismatch")
    lr=local["cases"];l12=[r for r in lr if r["role"]=="DEVELOPMENT_AXIS"];l4=[r for r in lr if r["role"]=="SEALED_CONFIRMATION_COMBINATION"]
    lv=[tuple(int(x) for x in r["ordered_D_nm"]) for r in lr]
    if (len(l12),len(l4),len(lv))!=(12,4,16):raise RuntimeError("Frozen local DOE count mismatch")
    with PATHS["v1csv"].open(encoding="utf-8-sig",newline="") as f:v1=list(csv.DictReader(f))
    vv=lambda r:tuple(int(r[f"D{i}_nm"]) for i in range(1,7))
    vg=[r for r in v1 if r["cohort"]=="GLOBAL_MAXIMIN"];vd=[r for r in vg if r["role"]=="DEVELOPMENT_GLOBAL"];vc=[r for r in vg if r["role"]=="SEALED_CONFIRMATION_GLOBAL"]
    vgv=[vv(r) for r in vg]
    reserves=[tuple(int(x) for x in r["ordered_D_nm"]) for r in exp["prospective_reserve_only"]]
    protected=[tuple(int(x) for x in r["ordered_D_nm"]) for r in exc["entries"]]
    source48=[tuple(int(x) for x in r["ordered_D_nm"]) for r in pool["entries"]]
    if (len(v1),len(vd),len(vc),len(vgv),len(reserves),len(protected),len(source48))!=(160,116,28,144,6,25,48):raise RuntimeError("Frozen point/ref count mismatch")
    refgroups={"existing32":old,"frozen_local16":lv,"reserve6":reserves,"protected25":protected,"source_pool48":source48,"V1_global144":vgv}
    refunion=set(x for g in refgroups.values() for x in g)
    if len(set(lv))!=16 or set(lv)&set(old):raise RuntimeError("Local points changed/duplicate")
    # Reconstruct V1 raw Sobol and selected group evidence before replacement.
    v1raw,v1dups=quant(20261004,15);v1ok=v1raw[feasible(v1raw)]
    v1s={"existing32":summary(old),"local12":summary([tuple(r["ordered_D_nm"]) for r in l12]),"local4":summary([tuple(r["ordered_D_nm"]) for r in l4]),
      "global_dev116":summary([vv(r) for r in vd]),"global_conf28":summary([vv(r) for r in vc]),"global144":summary(vgv),"all_new160":summary([vv(r) for r in v1])}
    if v1s["all_new160"]["boundary"]["exact_any"]!=112 or v1s["all_new160"]["boundary"]["within10_any"]!=151:raise RuntimeError("V1 boundary reconstruction differs from its frozen report")
    # V2 pool, numeric filters, then exact identity exclusions.
    raw,dups=quant(20261006,20);ok=raw[feasible(raw)]
    excluded=np.isin(keys(ok),keys(np.asarray(sorted(refunion),dtype=np.int16)));cand=ok[~excluded]
    if len(cand)<150000:raise RuntimeError("V2 sampled candidate pool unexpectedly small")
    masks=np.zeros(len(cand),np.int16)
    for i in range(6):
        masks|=(cand[:,i]==100).astype(np.int16)<<(2*i);masks|=(cand[:,i]==230).astype(np.int16)<<(2*i+1)
    selected=[];rows=[];cur=list(refunion)
    def add(v,role,stratum,stress=False,pat=None,rank=None):
        t=tuple(int(x) for x in v)
        if t in set(cur):raise RuntimeError(f"Duplicate selected vector {t}")
        rows.append({"case_id":"","role":role,"cohort":"V2_STRATIFIED_MAXIMIN","global_generation_order":len(rows)+1,
          "global_stratum":stratum,"exact_boundary_coordinates":sum(x in (100,230) for x in t),"boundary_stress":bool(stress),
          "face_pattern":";".join(labels(mask(t))),"stratum_rank":rank,"ordered_D_nm":t,"clearance":geo(t)[0],"margin":geo(t)[1]})
        selected.append(t);cur.append(t)
    # 88 interior; every fifth of first85 (17) is sealed core.
    interior=greedy(cand[masks==0],88,cur)
    for rank,v in enumerate(interior,1):
        conf=rank<=85 and rank%5==0
        add(v,"SEALED_CONFIRMATION_GLOBAL" if conf else "DEVELOPMENT_GLOBAL","INTERIOR",False,["INTERIOR"],rank)
    # Three candidates on every coordinate face. D1-D4 face representatives are one per face.
    for face in range(12):
        got=greedy(cand[masks==(1<<face)],3,cur)
        for rank,v in enumerate(got,1):
            conf=face<8 and rank==1
            add(v,"SEALED_CONFIRMATION_GLOBAL" if conf else "DEVELOPMENT_GLOBAL","SINGLE_FACE",False,labels(1<<face),rank)
    # Two confirm intersections cover both sides of D5 and D6.
    pair_confirm=[(1<<(2*4))|(1<<(2*5)),(1<<(2*4+1))|(1<<(2*5+1))]
    for rank,ma in enumerate(pair_confirm,1):
        v=greedy(cand[masks==ma],1,cur)[0];add(v,"SEALED_CONFIRMATION_GLOBAL","TWO_FACE_INTERSECTION",False,labels(ma),rank)
    pairs=list(itertools.combinations(range(6),2));options=[x for x in pairs if x!=(4,5)]
    prng=np.random.default_rng(20261008);order=prng.permutation(len(options));srng=np.random.default_rng(20261009);pair_info=[]
    for rank,k in enumerate(order[:10],1):
        i,j=options[int(k)];si,sj=(int(x) for x in srng.integers(0,2,size=2));ma=(1<<(2*i+si))|(1<<(2*j+sj))
        v=greedy(cand[masks==ma],1,cur)[0];add(v,"DEVELOPMENT_GLOBAL","TWO_FACE_INTERSECTION",False,labels(ma),rank)
        pair_info.append({"dimensions":[i+1,j+1],"faces":labels(ma),"mask":int(ma)})
    # Eight seeded three-face patterns, one sealed stress and seven development stress.
    triples=[]
    for ds in itertools.combinations(range(6),3):
        for ss in itertools.product((0,1),repeat=3):triples.append(sum(1<<(2*d+s) for d,s in zip(ds,ss)))
    trng=np.random.default_rng(20261007);tpatterns=[int(triples[int(i)]) for i in trng.permutation(len(triples))[:8]]
    for rank,ma in enumerate(tpatterns,1):
        v=greedy(cand[masks==ma],1,cur)[0];conf=rank==1
        add(v,"SEALED_CONFIRMATION_GLOBAL" if conf else "DEVELOPMENT_GLOBAL","TRIPLE_FACE_STRESS",True,labels(ma),rank)
    roles=Counter(r["role"] for r in rows);strata=Counter((r["role"],r["global_stratum"]) for r in rows)
    want={("DEVELOPMENT_GLOBAL","INTERIOR"):71,("SEALED_CONFIRMATION_GLOBAL","INTERIOR"):17,("DEVELOPMENT_GLOBAL","SINGLE_FACE"):28,
      ("SEALED_CONFIRMATION_GLOBAL","SINGLE_FACE"):8,("DEVELOPMENT_GLOBAL","TWO_FACE_INTERSECTION"):10,("SEALED_CONFIRMATION_GLOBAL","TWO_FACE_INTERSECTION"):2,
      ("DEVELOPMENT_GLOBAL","TRIPLE_FACE_STRESS"):7,("SEALED_CONFIRMATION_GLOBAL","TRIPLE_FACE_STRESS"):1}
    if len(rows)!=144 or len(set(selected))!=144 or dict(roles)!={"DEVELOPMENT_GLOBAL":116,"SEALED_CONFIRMATION_GLOBAL":28} or dict(strata)!=want:
        raise RuntimeError(f"Quota mismatch: {roles}; {strata}")
    for role,prefix in [("DEVELOPMENT_GLOBAL","K6GDP2_DEV_G"),("SEALED_CONFIRMATION_GLOBAL","K6GDP2_CONF_G")]:
        for n,r in enumerate(sorted((x for x in rows if x["role"]==role),key=lambda x:x["global_generation_order"]),1):r["case_id"]=f"{prefix}{n:03d}"
    records=[]
    for r in lr:
        v=tuple(int(x) for x in r["ordered_D_nm"]);role="DEVELOPMENT_LOCAL_AXIS" if r["role"]=="DEVELOPMENT_AXIS" else "SEALED_LOCAL_COMBINATION"
        records.append({"case_id":r["case_id"],"role":role,"cohort":"FROZEN_LOCAL_DOE","global_generation_order":"",
          "global_stratum":"LOCAL_AXIS" if role=="DEVELOPMENT_LOCAL_AXIS" else "LOCAL_COMBINATION","exact_boundary_coordinates":sum(x in (100,230) for x in v),
          "boundary_stress":False,"face_pattern":";".join(labels(mask(v))),"stratum_rank":"","ordered_D_nm":v,"clearance":geo(v)[0],"margin":geo(v)[1]})
    records+=rows
    if len(records)!=160 or len({r["case_id"] for r in records})!=160 or len({r["ordered_D_nm"] for r in records})!=160:raise RuntimeError("V2 pointset duplicate/count error")
    if set(selected)&refunion or min(geo(r["ordered_D_nm"])[0] for r in records)<60 or min(geo(r["ordered_D_nm"])[1] for r in records)<30:raise RuntimeError("Reference overlap or feasibility failure")
    fields=["case_id","role","cohort","global_generation_order","global_stratum","exact_boundary_coordinates","boundary_stress","face_pattern","stratum_rank",
      "D1_nm","D2_nm","D3_nm","D4_nm","D5_nm","D6_nm","min_periodic_neighbor_gap_nm","min_half_cell_lateral_margin_nm","ordered_geometry_sha256",
      "source_authority_enrolled","runner_approved","canonical_fsp_created_by_this_task","solver_authorized"]
    pcsv=OUT/"GLOBAL_DATASET_CANDIDATES_V2.csv"
    with pcsv.open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields,lineterminator="\n");w.writeheader()
        for r in records:
            v=r["ordered_D_nm"];it={k:r.get(k,"") for k in fields[:9]}
            it.update({f"D{i+1}_nm":int(v[i]) for i in range(6)});it.update({"min_periodic_neighbor_gap_nm":f"{r['clearance']:.6f}",
              "min_half_cell_lateral_margin_nm":f"{r['margin']:.6f}","ordered_geometry_sha256":hashlib.sha256(",".join(map(str,v)).encode("ascii")).hexdigest(),
              "source_authority_enrolled":"false","runner_approved":"false","canonical_fsp_created_by_this_task":"false","solver_authorized":"false"})
            w.writerow(it)
    # Four new-development outer folds: exact 3 local+29 global per fold.
    dl=sorted((r for r in records if r["role"]=="DEVELOPMENT_LOCAL_AXIS"),key=lambda r:r["case_id"])
    dg=sorted((r for r in records if r["role"]=="DEVELOPMENT_GLOBAL"),key=lambda r:r["global_generation_order"])
    fold={r["case_id"]:i%4+1 for i,r in enumerate(dl)}
    fold.update({r["case_id"]:i%4+1 for i,r in enumerate(dg)})
    fold_counts={str(i):{"geometry_groups":0,"local_axis":0,"global":0} for i in range(1,5)}
    fcsv=OUT/"DEVELOPMENT_FOLD_MANIFEST_V2.csv"
    with fcsv.open("w",encoding="utf-8",newline="") as f:
        w=csv.writer(f,lineterminator="\n");w.writerow(["case_id","outer_fold","role","global_stratum","D1_nm","D2_nm","D3_nm","D4_nm","D5_nm","D6_nm","all_21_wavelengths_grouped"])
        for r in sorted([*dl,*dg],key=lambda r:(fold[r["case_id"]],r["case_id"])):
            w.writerow([r["case_id"],fold[r["case_id"]],r["role"],r["global_stratum"],*r["ordered_D_nm"],"true"])
            x=fold_counts[str(fold[r["case_id"]])];x["geometry_groups"]+=1;x["local_axis" if r["role"]=="DEVELOPMENT_LOCAL_AXIS" else "global"]+=1
    if any(x!={"geometry_groups":32,"local_axis":3,"global":29} for x in fold_counts.values()):raise RuntimeError(f"Outer folds unbalanced: {fold_counts}")
    # Inner folds and nested 32/64/128 total-size train membership manifests.
    oldrecords=[{"case_id":cid,"role":"EXISTING32_TRAIN_ONLY","global_stratum":"EXISTING32","ordered_D_nm":v} for cid,v in zip(old_ids,old)]
    inner=[];curve=[];curves={}
    for of in range(1,5):
        val=[r for r in [*dl,*dg] if fold[r["case_id"]]==of];tn=[r for r in [*dl,*dg] if fold[r["case_id"]]!=of];pooltrain=[*oldrecords,*tn]
        orderin=sorted(pooltrain,key=lambda r:hashlib.sha256(",".join(map(str,r["ordered_D_nm"])).encode("ascii")).hexdigest())
        isizes=[0,0,0]
        for i,r in enumerate(orderin):
            inf=i%3+1;isizes[inf-1]+=1;inner.append([of,inf,r["case_id"],r["role"],*r["ordered_D_nm"],"true"])
        ltrain=sorted((r for r in tn if r["role"]=="DEVELOPMENT_LOCAL_AXIS"),key=lambda r:r["case_id"])
        gtrain=sorted((r for r in tn if r["role"]=="DEVELOPMENT_GLOBAL"),key=lambda r:r["global_generation_order"])
        if (len(val),len(tn),len(pooltrain),len(ltrain),len(gtrain))!=(32,96,128,9,87) or max(isizes)-min(isizes)>1:raise RuntimeError("Outer/inner pool count mismatch")
        lsubset=ltrain[::3];gsubset=greedy([r["ordered_D_nm"] for r in gtrain],29,[*old,*[r["ordered_D_nm"] for r in lsubset]])
        idmap={r["ordered_D_nm"]:r for r in gtrain};sub64=[*lsubset,*[idmap[v] for v in gsubset]]
        subsets={32:[],64:sub64,128:tn}
        for size in (32,64,128):
            train=[*oldrecords,*subsets[size]]
            if len(train)!=size or set(r["case_id"] for r in train)&set(r["case_id"] for r in val):raise RuntimeError("Curve size or heldout leakage")
            for r in train:curve.append([of,size,r["case_id"],r["role"],r["global_stratum"],*r["ordered_D_nm"],"true"])
        curves[str(of)]={"outer_validation":32,"outer_train":128,"inner_fold_sizes":isizes,
          "curve_sizes":[32,64,128],"size64_additions":{"local_axis":3,"global":29},
          "size128_additions":{"local_axis":sum(r["role"]=="DEVELOPMENT_LOCAL_AXIS" for r in tn),"global":sum(r["role"]=="DEVELOPMENT_GLOBAL" for r in tn)}}
    ic=OUT/"INNER_FOLD_MANIFEST_V2.csv"
    with ic.open("w",encoding="utf-8",newline="") as f:
        w=csv.writer(f,lineterminator="\n");w.writerow(["outer_fold","inner_fold","case_id","role","D1_nm","D2_nm","D3_nm","D4_nm","D5_nm","D6_nm","all_21_wavelengths_grouped"]);w.writerows(inner)
    lc=OUT/"LEARNING_CURVE_SUBSET_MANIFEST_V2.csv"
    with lc.open("w",encoding="utf-8",newline="") as f:
        w=csv.writer(f,lineterminator="\n");w.writerow(["outer_fold","training_geometry_count","case_id","role","global_stratum","D1_nm","D2_nm","D3_nm","D4_nm","D5_nm","D6_nm","all_21_wavelengths_grouped"]);w.writerows(curve)
    groups={"existing32":old,"frozen_local12_axis":[tuple(r["ordered_D_nm"]) for r in l12],"frozen_local4_combinations":[tuple(r["ordered_D_nm"]) for r in l4],
      "V1_global_development116":[vv(r) for r in vd],"V1_global_confirmation28":[vv(r) for r in vc],
      "V2_global_development116":[r["ordered_D_nm"] for r in rows if r["role"]=="DEVELOPMENT_GLOBAL"],
      "V2_global_confirmation28":[r["ordered_D_nm"] for r in rows if r["role"]=="SEALED_CONFIRMATION_GLOBAL"],
      "V2_new_development128":[r["ordered_D_nm"] for r in records if r["role"].startswith("DEVELOPMENT_")],
      "V2_new_confirmation32":[r["ordered_D_nm"] for r in records if r["role"].startswith("SEALED_")]}
    sums={k:summary(v) for k,v in groups.items()};pe=1-(25/27)**6;pn=1-(21/27)**6
    # Probe grid and raw V1/V2 pre-selection boundary stages.
    v1rawb=boundary_only(v1raw);v1okb=boundary_only(v1ok)
    rawb=boundary_only(raw);okb=boundary_only(ok);cb=boundary_only(cand)
    audit={"schema":"COUPLING_ML_K6_GLOBAL_PROTOCOL_SCIENTIFIC_REVISION_V2_COVERAGE_AUDIT","status":"GEOMETRY_ONLY_RESPONSE_BLIND",
      "preregistered_protocol_sha256":PROTO_SHA,"generator":{"path":"reports/coupling/COUPLING_ML_K6_GLOBAL_PROTOCOL_SCIENTIFIC_REVISION_V2/generate_global_dataset_design_v2.py","sha256":sha(Path(__file__)),
        "python":platform.python_version(),"numpy":np.__version__,"scipy":scipy.__version__},"input_sha256":ih,
      "uniform_discrete_domain":{"levels_per_coordinate":27,"grid_cardinality":27**6,"exact_boundary_probability":pe,"within10_probability":pn,
        "geometry_filters":{"all_grid_points_pass":True,"minimum_cyclic_gap_nm":60,"minimum_half_cell_margin_nm":30,"manufacturing_authority":"UNRESOLVED"}},
      "V1_boundary_bias":{"raw_sobol_seed20261004":{"draws":32768,"unique":len(v1raw),"duplicates":v1dups,"boundary":v1rawb},
        "after_numeric_filter":{"n":len(v1ok),"rejected":len(v1raw)-len(v1ok),"boundary":v1okb},
        "maximin144":v1s["global144"]["boundary"],"development116":v1s["global_dev116"]["boundary"],"confirmation28":v1s["global_conf28"]["boundary"],
        "explanation":"No response objective was used. Numeric filters reject no grid point; high-dimensional bounded-cube maximin selected edge extremes disproportionately."},
      "V2_sampler":{"seed":20261006,"sobol_power_m":20,"raw_unique":len(raw),"duplicates":dups,"raw_boundary":rawb,
        "after_numeric_filter":{"n":len(ok),"rejected":len(raw)-len(ok),"boundary":okb},
        "after_identity_exclusions":{"n":len(cand),"excluded":len(ok)-len(cand),"boundary":cb,"reference_overlap_nonexclusive":{k:int(np.isin(keys(ok),keys(np.asarray(v,dtype=np.int16))).sum()) for k,v in refgroups.items()}},
        "selected":{"n":len(rows),"roles":dict(roles),"role_strata":{f"{a}:{b}":int(n) for (a,b),n in strata.items()},
          "confirmation_core":{"interior":17,"single_face":8,"two_face":2,"n":27,"exact_face_fraction":10/27},
          "separate_stress":{"triple_face":1,"n":1},"dev_two_face_patterns":pair_info,
          "triple_face_patterns":[{"mask":m,"faces":labels(m)} for m in tpatterns]}},
      "required_group_coverage":sums,"uniform_expected_counts":{k:{"exact_boundary":len(v)*pe,"within10":len(v)*pn} for k,v in groups.items()},
      "distance":{"confirm_to_dev":nn(groups["V2_global_confirmation28"],groups["V2_global_development116"]),
        "new_confirm_to_new_dev":nn(groups["V2_new_confirmation32"],groups["V2_new_development128"]),
        "global_dev_to_old32":nn(groups["V2_global_development116"],old),"global_confirm_to_old32":nn(groups["V2_global_confirmation28"],old),
        "global_dev_to_local16":nn(groups["V2_global_development116"],lv),"global_confirm_to_local16":nn(groups["V2_global_confirmation28"],lv)},
      "coverage_probe":{"seed":20261008,"n":32768,"old32":probe(20261008,old),
        "old32_plus_new_development160":probe(20261008,[*old,*groups["V2_new_development128"]]),
        "old32_plus_all_new":probe(20261008,[*old,*groups["V2_new_development128"],*groups["V2_new_confirmation32"]])},
      "folds":{"outer":fold_counts,"inner_and_curve":curves,"inner_rows":len(inner),"learning_curve_rows":len(curve),"sizes":[32,64,128]},
      "integrity":{"new_points":len(records),"development":len(groups["V2_new_development128"]),"confirmation":len(groups["V2_new_confirmation32"]),
        "duplicates":0,"overlap_with_old_local_reserve_protected_sourcepool_v1proposals":0,
        "min_periodic_clearance_nm":min(geo(r["ordered_D_nm"])[0] for r in records),"min_lateral_margin_nm":min(geo(r["ordered_D_nm"])[1] for r in records),
        "source_authority_enrolled":False,"runner_approved":False,"canonical_fsp_created":False},
      "response_blindness":{"response_arrays_opened":False,"only_case_ids_and_ordered_D_nm_read_from_32G":True,"confirmation_response_access":False},
      "execution_counts":{"solver_entries":0,"training_fits":0,"pscale_only_fits":0,"new_fsps":0,"runner_invocations":0,"reserve_launches":0}}
    jwrite(OUT/"COVERAGE_AUDIT_V2.json",audit)
    hashes={k:{"path":str(v),"sha256":ih[k]} for k,v in PATHS.items()}
    jwrite(OUT/"AUTHORITY_HASHES_V2.json",{"schema":"COUPLING_ML_K6_GLOBAL_PROTOCOL_SCIENTIFIC_REVISION_V2_AUTHORITY_HASHES","files":hashes,
      "runner_worktree":{"branch":"codex/apcd-gpu-production-runner-v1","head":"2a6f515a1d28002bca3c4e30094dbf66e463fb17",
        "uncommitted_paths":["scripts/shared_fdtd/gpu_runner_v1/adapter.py","scripts/shared_fdtd/gpu_runner_v1/runner.py",
          "scripts/shared_fdtd/gpu_runner_v1/controlled_admission_authority_v1.json","scripts/shared_fdtd/gpu_runner_v1/controlled_admission_policy_v1.json",
          "scripts/shared_fdtd/gpu_runner_v1/controlled_admission_v1.py","scripts/shared_fdtd/gpu_runner_v1/test_controlled_admission_v1.py"],"draft_is_authority":False}})
    jwrite(OUT/"RUNNER_MONITOR_DEPENDENCIES_V2.json",{"schema":"COUPLING_ML_K6_GLOBAL_PROTOCOL_SCIENTIFIC_REVISION_V2_RUNNER_MONITOR_DEPENDENCIES",
      "task_counts":{"solver_entries":0,"training_fits":0,"pscale_only_fits":0,"new_fsps":0,"runner_invocations":0},
      "geometry_authority":{"sha256":ih["domain"],"status":"PASS_RECOVERED_CLOSED_CANDIDATE_DOMAIN","source_pool48":True,"eligible_source_count":32,"new_ids_enrolled":False,"manufacturing_authority":"UNRESOLVED"},
      "committed_runner":{"branch":"codex/apcd-gpu-production-runner-v1","head":"2a6f515a1d28002bca3c4e30094dbf66e463fb17","status":"READY","slots":1,"serial_only":True,"no_replay":True,"approved_stage1_ids":12,
        "v2_approved":0,"canonical_fsp_count":0,"case_manifest_count":0,"load_only_proofs":0,"handoff_sha256":ih["runner_md"],"authority_sha256":ih["runner_authority"]},
      "runner_draft":{"dirty_tracked":["scripts/shared_fdtd/gpu_runner_v1/adapter.py","scripts/shared_fdtd/gpu_runner_v1/runner.py"],
        "untracked":["scripts/shared_fdtd/gpu_runner_v1/controlled_admission_authority_v1.json","scripts/shared_fdtd/gpu_runner_v1/controlled_admission_policy_v1.json","scripts/shared_fdtd/gpu_runner_v1/controlled_admission_v1.py","scripts/shared_fdtd/gpu_runner_v1/test_controlled_admission_v1.py"],
        "formal_authority":False,"touched":False},
      "monitor":{"current_postnp_retained":True,"audit_sha256":ih["monitor_report"],"EXT02":"BLOCKED_PREENTRY; not numerical validation failure",
        "second_independent_postnp_plane":False,"production_monitor_changed":False},
      "future_requirements":["owner-approved geometry/case IDs","case-specific source manifest","canonical FSP path/hash","fresh LOAD-only and source/staged parity",
        "immutable Runner envelope","separate HF authorization"],"load_only_is_runner_admission":False,"load_only_is_postentry_truth_recovery":False})
    print(json.dumps({"status":"V2_GENERATION_COMPLETE","candidate_sha256":sha(pcsv),"outer_folds_sha256":sha(fcsv),"inner_folds_sha256":sha(ic),
      "learning_curve_sha256":sha(lc),"coverage_sha256":sha(OUT/"COVERAGE_AUDIT_V2.json"),"protocol_sha256":PROTO_SHA,
      "counts":{"V2_global_dev_exact_face":sums["V2_global_development116"]["boundary"]["exact_any"],
        "V2_global_conf_exact_face":sums["V2_global_confirmation28"]["boundary"]["exact_any"],
        "V2_global_dev_near10":sums["V2_global_development116"]["boundary"]["within10_any"],
        "V2_global_conf_near10":sums["V2_global_confirmation28"]["boundary"]["within10_any"],"folds":fold_counts},
      "fit_budget":281,"input_hashes":ih},ensure_ascii=False))
if __name__=="__main__":main()
