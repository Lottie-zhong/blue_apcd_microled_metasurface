#!/usr/bin/env python
"""Offline Stage-1 closeout, 32G authority, and frozen H1 rerun. No solver calls."""
from __future__ import annotations
import sys
sys.dont_write_bytecode=True
import argparse,csv,datetime,hashlib,importlib.util,json,math,os,subprocess,gc
from pathlib import Path
import h5py
import numpy as np
import torch
import pw_k6_stage1_32g_frozen_model_v1 as model

ROOT=Path(__file__).resolve().parents[2]
RUNTIME=Path(r"D:\apcd_runtime\gpu_production_runner_v1")
RUNNER=Path(r"D:\project\worktrees\blue_apcd_gpu_production_runner_v1")
OUT=ROOT/"reports"/"coupling"/"PW_K6_STAGE1_32G_FROZEN_FORWARD_H1_V1"
EXP_PATH=ROOT/"reports"/"coupling"/"PW_K6_FIXED_MDC_UNBIASED_EXPANSION_MANIFEST_V1.json"
DATA20_PATH=ROOT/"reports"/"coupling"/"COUPLING_ML_NP_FORWARD_FEATURE_ABLATION_20G_V1"/"dataset_authority.json"
TRUTH20_PATH=ROOT/"reports"/"coupling"/"PW_K6_GRATING_TRUTH_V2.json"
MODEL_REPORT=ROOT/"reports"/"coupling"/"PW_K6_STRUCTURED_FORWARD_MODEL_FREEZE_V1.md"
GATE_PATH=ROOT/"reports"/"coupling"/"PW_K6_H1_NUMERIC_GATE_AUTHORITY_V1.json"
DECODER_PATH=ROOT/"scripts"/"shared_fdtd"/"tools"/"pw_complex_floquet_state_v1.py"
CONTRACT="32e60a7830a449f2268356db5ffd41f4f22b297be9a1d82ebe97f97be995dea5"
EXP_SHA="4cf521c18576c34407c158a20f748fe560910909728bed5cdadf53ec9fbe2e7f"
DECODER_SHA="b6873c1fc9df447de16b62e60da9d0b4c978934d7d02db283ddb5713f2024d15"
GATE_SHA="8cf71239757e70eb75fbbf858a82c12f8af8d03c0892b99ff4ffce6a959fcdbd"
RUNNER_HEAD="1afa3e30f1de5e0192be6240a3754c89e2eb6f25"
RUNNER_PROD_HEAD="783bd5741eb5e6853a3be5532624f4282f9488b7"
HANDOFF_SHA="397e41476938392d43e7eaf6c5252425991a8bfa62b7fb88442bf5da4fe0feb7"
HANDOFF_JSON_SHA="ca7e4a9fcc15ccb60f4921feb788bf3663e1b8fd3c56f64892894cc8299df599"
RUNNER_AUTH_SHA="021951707cd94d62ca93076f5f2a6867b400df4c9921932286b32ffc1840972c"
QUAL_SHA="45f22f900ab07157527645815fb5ec14a98631a0ebaac9da25aad1c6e8b36c5f"
STAGE1=["K6V1_S35","K6V1_S39","K6V1_S21","K6V1_S42","K6V1_S36","K6V1_S31","K6V1_S45","K6V1_S32","K6V1_S47","K6V1_S33","K6V1_S37","K6V1_S48"]
RUNIDS={"K6V1_S35":"S35-20261002T044427Z-e702b2ac","K6V1_S39":"S39-20261002T075624Z-30a1c44a","K6V1_S21":"S21-20261002T101540Z-e2485c16","K6V1_S42":"S42-20261002T103354Z-9585d9a3","K6V1_S36":"S36-20261002T105352Z-671765bc","K6V1_S31":"S31-20261002T110823Z-90fa3875","K6V1_S45":"S45-20261002T112048Z-75711e99","K6V1_S32":"S32-20261002T113252Z-ea995543","K6V1_S47":"S47-20261002T114504Z-fcdf22c6","K6V1_S33":"S33-20261002T115716Z-490a6ee1","K6V1_S37":"S37-20261002T120931Z-f6a077e8","K6V1_S48":"S48-20261002T122143Z-b79ba53b"}
RESERVE={"K6V1_S22","K6V1_S40","K6V1_S24","K6V1_S43","K6V1_S44","K6V1_S46"}
C0=299792458.0
ETA0=376.730313668
AREA=1740e-9*290e-9
WLS=np.arange(440,461,dtype=float)
ORD=tuple(range(-3,4))

def req(ok,msg):
    if not ok: raise RuntimeError(msg)

def sha(p):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
    return h.hexdigest()

def jread(p): return json.loads(Path(p).read_text(encoding="utf-8"))

def jwrite(p,obj):
    Path(p).parent.mkdir(parents=True,exist_ok=True)
    Path(p).write_text(json.dumps(obj,ensure_ascii=True,sort_keys=True,indent=2,allow_nan=False)+"\n",encoding="utf-8")

def csvwrite(p,rows,fields):
    with open(p,"w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction="ignore"); w.writeheader(); w.writerows(rows)

def git(root,*args,check=True):
    p=subprocess.run(["git","-C",str(root),*args],capture_output=True,text=True,encoding="utf-8",errors="replace")
    if check and p.returncode: raise RuntimeError("git error "+str(args)+": "+p.stderr)
    return p.stdout.strip(),p.returncode

def runner_authority():
    branch,_=git(RUNNER,"branch","--show-current"); head,_=git(RUNNER,"rev-parse","HEAD"); dirty,_=git(RUNNER,"status","--porcelain")
    anc=subprocess.run(["git","-C",str(RUNNER),"merge-base","--is-ancestor",RUNNER_PROD_HEAD,"HEAD"])
    fs={"handoff_md":RUNNER/"docs"/"APCD_GPU_PRODUCTION_RUNNER_V1_HANDOFF.md",
      "handoff_json":RUNNER/"APCD_GPU_PRODUCTION_RUNNER_V1_HANDOFF.json",
      "authority_json":RUNNER/"APCD_GPU_PRODUCTION_RUNNER_V1_AUTHORITY.json",
      "qualification":RUNNER/"reports"/"apcd_gpu_production_runner_v1"/"GENERIC_SETUP_VALIDATOR_ZERO_SOLVER_20261002.json"}
    actual={k:sha(p) for k,p in fs.items()}
    exp={"handoff_md":HANDOFF_SHA,"handoff_json":HANDOFF_JSON_SHA,"authority_json":RUNNER_AUTH_SHA,"qualification":QUAL_SHA}
    req(branch=="codex/apcd-gpu-production-runner-v1" and head==RUNNER_HEAD and not dirty,"frozen Runner checkout changed")
    req(anc.returncode==0 and actual==exp,"Runner frozen authority verification failed")
    return {"platform":"APCD_GPU_PRODUCTION_RUNNER_V1","mode":"GPU-only, single-slot, serial","branch":branch,"head":head,
      "frozen_production_code_head":RUNNER_PROD_HEAD,"production_head_ancestor":True,"clean":True,"hashes":actual,
      "modified_by_task":False,"new_platform_qualification":False}

def decoder_module():
    req(sha(DECODER_PATH)==DECODER_SHA,"frozen H2 decoder hash mismatch")
    s=importlib.util.spec_from_file_location("frozen_h2_pw",DECODER_PATH)
    m=importlib.util.module_from_spec(s); sys.modules[s.name]=m; s.loader.exec_module(m)
    return m

def trapw(x):
    x=np.asarray(x,float).reshape(-1); req(len(x)>1 and np.all(np.diff(x)>0),"coordinates not increasing")
    w=np.empty_like(x); w[0]=(x[1]-x[0])/2; w[-1]=(x[-1]-x[-2])/2; w[1:-1]=(x[2:]-x[:-2])/2
    return w

def state_data(npzpath,metapath,expected,dec):
    req(Path(npzpath).is_file() and sha(npzpath)==expected,"state NPZ absent/hash mismatch: "+str(npzpath))
    meta=jread(metapath); req(meta.get("sha256")==expected,"state metadata SHA mismatch")
    req(meta.get("schema_version")=="PW_COMPLEX_FLOQUET_STATE_V1" and meta.get("planes")==["IN","PRENP","POSTNP"]
      and meta.get("directions")==["+z","-z"] and meta.get("polarizations")==["TE","TM"],"state metadata schema mismatch")
    z=np.load(npzpath,allow_pickle=False)
    req(z["coefficients_real"].shape==(3,21,81,2,2) and np.allclose(z["wavelengths_nm"],WLS,rtol=0,atol=1e-8),"state shape/wavelength mismatch")
    ox={tuple(map(int,v)):i for i,v in enumerate(z["orders"].tolist())}; ix=[ox[(m,0)] for m in ORD]
    pi=meta["planes"].index("POSTNP"); di=meta["directions"].index("+z")
    masks=np.take(z["propagating_mask"][pi],ix,axis=1); req(masks.sum(axis=1).tolist()==[7]*21,"required orders not all propagating")
    c=np.take(z["coefficients_real"][pi],ix,axis=1)[:,:,di,:]+1j*np.take(z["coefficients_imag"][pi],ix,axis=1)[:,:,di,:]
    kz=np.take(z["mode_kz_real"][pi],ix,axis=1); req(np.isfinite(c.real).all() and np.isfinite(c.imag).all() and (kz>0).all(),"invalid C_PW/kz")
    w=np.zeros((21,7)); pw=np.zeros((21,7,2)); op=np.zeros((21,7))
    for j,wl in enumerate(WLS):
        k0=2*np.pi/(wl*1e-9)
        for q,mn in enumerate(ORD):
            te=dec._mode(mn,0,float(wl),1.0,1,"TE"); tm=dec._mode(mn,0,float(wl),1.0,1,"TM")
            req(abs(kz[j,q]-te["kz_rad_m"].real)<=max(1e-5,abs(kz[j,q])*1e-11),"stored and frozen H2 kz disagree")
            w[j,q]=kz[j,q]/k0; pw[j,q]=[te["power_z_per_abs_e2"],tm["power_z_per_abs_e2"]]
            op[j,q]=np.sum(pw[j,q]*np.abs(c[j,q])**2)
    den=np.sum(w[:,:,None]*np.abs(c)**2,axis=(1,2)); req(np.isfinite(den).all() and (den>0).all(),"C_hat denominator invalid")
    chat=c/np.sqrt(den)[:,None,None]; total=op.sum(axis=1); etam=op/np.maximum(total[:,None],1e-30)
    return {"chat":chat,"weights":w,"modal_order":op,"modal_total":total,"eta_modal":etam,"state_sha":sha(npzpath),"meta_sha":sha(metapath)}

def pscale_eh(npzpath,rawjson):
    meta=jread(rawjson); pin=np.asarray(meta["canonical_state"]["normalization"]["incident_power_per_area"],float)
    req(pin.shape==(21,) and (pin>0).all() and np.isfinite(pin).all(),"incident power/area invalid")
    with np.load(npzpath,allow_pickle=False) as z:
        freq=z["POSTNP_f"].reshape(-1); wls=C0/freq*1e9
        req(np.allclose(wls,WLS,rtol=0,atol=1e-7),"raw wavelength order mismatch")
        wx=trapw(z["POSTNP_x"]); wy=trapw(z["POSTNP_y"])
        ex=z["POSTNP_Ex"][:,:,0,:]; ey=z["POSTNP_Ey"][:,:,0,:]
        hx=z["POSTNP_Hx"][:,:,0,:]; hy=z["POSTNP_Hy"][:,:,0,:]
        flux=.5*np.real(ex*np.conj(hy)-ey*np.conj(hx))
        peh=np.sum(wx[:,None,None]*wy[None,:,None]*flux,axis=(0,1))
    p=peh/(AREA*pin); req(p.shape==(21,) and (p>0).all() and np.isfinite(p).all(),"raw E/H P_scale invalid")
    return p

def load20(dec):
    da=jread(DATA20_PATH); truth=jread(TRUTH20_PATH)
    req(da.get("included_geometry_count")==20 and da.get("polarization")=="P_XLIKE only","formal 20G authority mismatch")
    req(truth.get("schema")=="PW_K6_GRATING_TRUTH_V2" and len(truth.get("rows",[]))==2940,"formal 20G truth row count mismatch")
    tm={(x["case"],int(round(x["wavelength_nm"])),int(x["order_x"]),int(x["order_y"])):x for x in truth["rows"]}
    ids=[]; geo=[]; cc=[]; pp=[]; ee=[]; aa=[]; ww=[]; prov=[]; parity=[]
    for rec in da["cases"]:
        cid=rec["case_id"]; req(rec["scientific_validation"]=="PASS" and rec["solver_returned"] and not rec["replay"],"20G truth not valid: "+cid)
        npz=Path(rec["state_npz_path"]); meta=Path(rec["artifact_hashes"]["state"]["metadata_path"])
        req(sha(meta)==rec["artifact_hashes"]["state"]["metadata_sha256"],"20G state metadata hash mismatch: "+cid)
        st=state_data(npz,meta,rec["state_npz_sha256"],dec)
        p=np.zeros(21); e=np.zeros((21,7)); a=np.zeros((21,7)); modalrow=np.zeros((21,7))
        for j,wl in enumerate(WLS.astype(int)):
            for q,mn in enumerate(ORD):
                row=tm[(cid,int(wl),int(mn),0)]
                if q==0: p[j]=float(row["POSTNP_TOTAL_POWER_V2"])
                else: req(abs(p[j]-float(row["POSTNP_TOTAL_POWER_V2"]))<1e-13,"20G scale differs within order rows")
                e[j,q]=float(row["GRATING_ETA_V2"]); a[j,q]=float(row["GRATING_ABSOLUTE_ORDER_POWER_V2"])
                modalrow[j,q]=float(row.get("C_PW_MODAL_ORDER_POWER",a[j,q]))
            req(abs(e[j].sum()-1)<1e-9 and np.max(np.abs(a[j]-p[j]*e[j]))<2e-12,"20G total/eta factorization mismatch")
        ee0=float(np.max(np.abs(st["eta_modal"]-e)))
        pe0=float(np.max(np.abs(st["modal_total"]-p)/np.maximum(p,1e-30)))
        mo0=float(np.max(np.abs(st["modal_order"]-modalrow)/np.maximum(modalrow,1e-30)))
        req(np.isfinite([ee0,pe0,mo0]).all(),f"20G H2 parity diagnostic is nonfinite: {cid}")
        ids.append(cid); geo.append(rec["ordered_D_nm"]); cc.append(st["chat"]); pp.append(p); ee.append(e); aa.append(a); ww.append(st["weights"])
        prov.append({"case_id":cid,"cohort":"FROZEN_20G","ordered_D_nm":rec["ordered_D_nm"],"geometry_hash_sha256":rec["geometry_hash_sha256"],
          "state_path":str(npz),"state_sha256":st["state_sha"],"state_metadata_sha256":st["meta_sha"],
          "truth_authority":"PW_K6_GRATING_TRUTH_V2","scientific_validation":"PASS","replay":False})
        parity.append({"case_id":cid,"h2_eta_max_abs_error":ee0,"modal_pscale_max_relative_error":pe0,"modal_order_max_relative_error":mo0})
    return {"ids":ids,"geometry":np.asarray(geo,float),"chat":np.asarray(cc),"pscale":np.asarray(pp),"eta":np.asarray(ee),
      "absolute":np.asarray(aa),"weights":np.asarray(ww),"provenance":prov,"parity":parity}

def load12(exp,dec):
    qp=RUNNER/"reports"/"apcd_gpu_production_runner_v1"/"GENERIC_SETUP_VALIDATOR_ZERO_SOLVER_20261002.json"
    q=jread(qp); qm={v["case_id"]:v for v in q.get("cases",[])}
    req(sha(qp)==QUAL_SHA and q.get("result")=="PASS" and q.get("cases_requested")==12 and q.get("cases_passed")==12
      and q.get("scientific_entries")==0 and q.get("solver_invocations")==0 and set(qm)==set(STAGE1),
      "generic zero-solver qualification report mismatch")
    reg=jread(RUNTIME/"registry.json"); rows=reg.get("runs",[])
    sr=[r for r in rows if r.get("case_id") in STAGE1]
    req(len(sr)==12 and {r["case_id"] for r in sr}==set(STAGE1) and not ({r["case_id"] for r in rows}&RESERVE),"Stage-1/reserve registry mismatch")
    exps=exp["training_expansion_stage1"]; req([x["candidate_id"] for x in exps]==STAGE1,"Stage-1 manifest order mismatch")
    rm={r["case_id"]:r for r in sr}; recs=[]; ids=[]; geo=[]; cc=[]; pp=[]; ee=[]; aa=[]; ww=[]; parity=[]
    for ex in exps:
        cid=ex["candidate_id"]; rid=RUNIDS[cid]; row=rm[cid]; run=Path(row["run_dir"])
        req(row["run_id"]==rid and row["attempt_id"]=="attempt_001","run identity mismatch: "+cid)
        qv=qm[cid]
        st0=jread(run/"status.json")
        req(st0.get("run_id")==rid and st0.get("solver_entered") is True and st0.get("solver_invocations")==1,"entry count mismatch: "+cid)
        man=jread(run/"manifest.json"); d=ex["ordered_D_nm"]
        req(man["geometry"]==d and man["physical_contract_sha256"]==CONTRACT,"case contract/geometry mismatch: "+cid)
        req(qv.get("ordered_D_nm")==d and qv.get("contract_sha256")==CONTRACT
          and qv.get("mesh_authority")=="PW_K6_5NM_FULL_PERIOD_MESH_AUTHORITY_V1"
          and qv.get("validation",{}).get("status")=="PASS" and not qv.get("validation",{}).get("errors")
          and qv.get("solver_invocations")==0 and qv.get("scientific_entry_performed") is False and qv.get("solver_run_called") is False,
          "generic setup qualification mismatch: "+cid)
        req(qv.get("postprocess_dependency_preflight_status")=="PASS" and qv.get("postprocess_dependency_preflight_solver_called") is False
          and qv.get("wavelength_count")==21 and qv.get("monitor_names")==["MON_IN","MON_PRENP","MON_POSTNP","MON_REFLECTION"]
          and qv.get("load_only_semantic_parity",{}).get("status")=="PASS" and qv.get("load_only_semantic_parity",{}).get("mismatch_count")==0,
          "postprocess/monitor qualification mismatch: "+cid)
        ap=Path(qv["authority_manifest_path"]); lp=Path(qv["load_only_validation_path"]); pf=Path(qv["pre_fsp_path"])
        req(ap.is_file() and sha(ap)==qv["authority_manifest_sha256"] and lp.is_file() and sha(lp)==qv["load_only_validation_sha256"]
          and pf.is_file() and sha(pf)==qv["pre_fsp_sha256"]==qv["staged_fsp_sha256"],"generic qualification path/hash mismatch: "+cid)
        am=jread(ap)
        req(am.get("schema")=="PW_K6_5NM_FULL_PERIOD_MESH_AUTHORITY_V1_INPUT_V1" and am.get("case_id")==cid
          and am.get("attempt_id")=="attempt_001" and am.get("ordered_D_nm")==d and am.get("geometry_hash_sha256")==ex["geometry_hash_sha256"]
          and am.get("physical_contract_hash")==CONTRACT and am.get("canonical_pre_fsp_sha256")==qv["pre_fsp_sha256"]
          and am.get("mesh_implementation_authority")=="PW_K6_5NM_FULL_PERIOD_MESH_AUTHORITY_V1"
          and am.get("stage1_expansion_manifest_sha256")==EXP_SHA and am.get("scientific_entry_count")==0 and am.get("solver_run_called") is False,
          "authority-input manifest mismatch: "+cid)
        req("PW_K6_5NM_FULL_PERIOD_MESH_AUTHORITY_V1" in man["pre_fsp_path"] and man["pre_fsp_sha256"]==st0.get("pre_fsp_sha256") and man["pre_fsp_path"]==qv["pre_fsp_path"] and man["pre_fsp_sha256"]==qv["pre_fsp_sha256"]==qv["staged_fsp_sha256"],"canonical input FSP mismatch: "+cid)
        src=exp["frozen_physical_contract"]["contract"]
        req(src["source"]=="GaN to air +z normal-incidence X-pol" and src["wavelengths_nm"]==list(range(440,461)),"source/polarization contract mismatch")
        gp=jread(run/"gpu_standalone"/"forensics"/"process_exit_provenance.json")
        req(gp.get("reason")=="CHILD_RETURNED" and gp.get("child",{}).get("return_code")==0 and gp.get("child",{}).get("name")=="fdtd-solutions.exe","GPU child evidence mismatch: "+cid)
        recovered=(cid=="K6V1_S35")
        if recovered:
            truthbase=RUNTIME/"recovery"/cid/"attempt_001"/rid/"recovery_003"
            rs=jread(truthbase/"recovery_status.json"); val=jread(truthbase/"validation.json")
            req(st0.get("state")=="FAILED_POSTENTRY" and rs.get("recovery_state")=="LOAD_ONLY_POSTENTRY_TRUTH_RECOVERY"
              and rs.get("scientific_truth_status")=="TRUTH_VALID" and rs.get("solver_invocations_before")==1
              and rs.get("solver_invocations_after")==1 and rs.get("solver_run_called_during_recovery") is False
              and rs.get("replay_count")==0 and val.get("fresh_load_validation",{}).get("scientific_valid") is True
              and all(val.get("checks",{}).values()),"S35 recovery history/checks mismatch")
            final="RECOVERED_TRUTH_VALID"; truthh=truthbase/"truth.h5"; rec_truth_sha=rs.get("truth_h5_sha256")
        else:
            truthbase=run; val=jread(run/"validation.json"); rs={}
            req(st0.get("state")=="DONE" and st0.get("solver_returned_unix") is not None and
              val.get("fresh_load_verified") is True and val.get("scientific_valid") is True and val.get("state_valid") is True
              and val.get("monitors_valid") is True,"post-run validation mismatch: "+cid)
            final="DONE"; truthh=run/"truth.h5"; rec_truth_sha=st0.get("truth_h5_sha256")
        fsp=run/"run.fsp"; native=run/"run"/"run_output.h5"
        req(fsp.is_file() and native.is_file() and truthh.is_file(),"durable FSP/H5 missing: "+cid)
        fsha,nsha,tsha=sha(fsp),sha(native),sha(truthh)
        req(((recovered and not st0.get("run_fsp_sha256")) or fsha==st0.get("run_fsp_sha256")) and (not rec_truth_sha or tsha==rec_truth_sha),"durable artifact hash mismatch: "+cid)
        statef=list((truthbase/"state").glob("*pw_complex_floquet_state.npz")); metaf=list((truthbase/"state").glob("*pw_complex_floquet_state.json"))
        rawf=list((truthbase/"raw").glob("*_raw_complex_fields.npz")); rawj=list((truthbase/"raw").glob("*_raw.json")); orderf=list((truthbase/"orders").glob("*_orders.json"))
        req(len(statef)==len(metaf)==len(rawf)==len(rawj)==len(orderf)==1,"truth artifact set incomplete: "+cid)
        sm=jread(metaf[0]); st=state_data(statef[0],metaf[0],sm["sha256"],dec)
        rj=jread(rawj[0]); req(rj["case_id"]==cid and rj["contract"]["wavelengths_nm"]==list(range(440,461)),"raw contract mismatch: "+cid)
        oj=jread(orderf[0]); req(len(oj["post"])==21 and np.allclose(oj["wavelengths_nm"],WLS,rtol=0,atol=1e-8),"order truth wavelength mismatch")
        p=pscale_eh(rawf[0],rawj[0]); e=np.zeros((21,7))
        for j in range(21):
            od={(int(q["order_x"]),int(q["order_y"])):q for q in oj["post"][j]}
            req(set(od)=={(m,0) for m in ORD},"order set mismatch: "+cid)
            for qi,mn in enumerate(ORD): e[j,qi]=float(od[(mn,0)]["power_fraction_of_monitor_total"])
        req(np.max(np.abs(e.sum(axis=1)-1))<=1e-9,"order eta not normalized: "+cid)
        a=p[:,None]*e
        ee0=float(np.max(np.abs(st["eta_modal"]-e))); pe0=float(np.max(np.abs(st["modal_total"]-p)/np.maximum(p,1e-30)))
        req(ee0<=.001 and pe0<=.001,"Stage-1 H2/raw EH parity failed: "+cid)
        ids.append(cid); geo.append(d); cc.append(st["chat"]); pp.append(p); ee.append(e); aa.append(a); ww.append(st["weights"])
        closure=val.get("max_energy_closure",val.get("fresh_load_validation",{}).get("max_energy_closure"))
        recs.append({"case_id":cid,"attempt_id":"attempt_001","run_id":rid,"ordered_D_nm":d,"geometry_hash_sha256":ex["geometry_hash_sha256"],
          "scientific_entry_count":1,"solver_invocations":1,"replay_count":0,"raw_runner_state":st0.get("state"),"final_scientific_state":final,
          "solver_entered_utc":datetime.datetime.fromtimestamp(st0["solver_entered_unix"],datetime.timezone.utc).isoformat(),
          "solver_returned":True,"gpu_engine_confirmed":True,"post_run_fsp_path":str(fsp),"post_run_fsp_sha256":fsha,
          "post_run_fsp_sha256_source":"Runner status.json" if st0.get("run_fsp_sha256") else "computed from preserved run.fsp during closeout; original status was not backfilled",
          "native_h5_path":str(native),"native_h5_sha256":nsha,"truth_h5_path":str(truthh),"truth_h5_sha256":tsha,
          "state_npz_path":str(statef[0]),"state_npz_sha256":st["state_sha"],"raw_fields_path":str(rawf[0]),"raw_fields_sha256":sha(rawf[0]),
          "orders_path":str(orderf[0]),"orders_sha256":sha(orderf[0]),"validation_status":"PASS","energy_closure":closure,
          "fresh_load":"PASS","h2_eta_max_abs_error":ee0,"modal_pscale_max_relative_error":pe0,
          "recovery_history":"original FAILED_POSTENTRY + LOAD-only recovery" if recovered else "normal single-entry DONE"})
        parity.append({"case_id":cid,"h2_eta_max_abs_error":ee0,"modal_pscale_max_relative_error":pe0})
        del st,rj,oj
        gc.collect()
    req(ids==STAGE1 and all(len([r for r in rows if r.get("case_id")==cid])==1 for cid in STAGE1),"Stage-1 duplicate attempt/ordering issue")
    return {"ids":ids,"geometry":np.asarray(geo,float),"chat":np.asarray(cc),"pscale":np.asarray(pp),"eta":np.asarray(ee),
      "absolute":np.asarray(aa),"weights":np.asarray(ww),"records":recs,"parity":parity}

def combine(a,b):
    ids=a["ids"]+b["ids"]; g=np.concatenate([a["geometry"],b["geometry"]])
    req(len(ids)==32 and len(set(ids))==32 and len(set(tuple(int(v) for v in x) for x in g))==32,"32G order or uniqueness failed")
    req(not set(ids)&RESERVE,"reserve geometry included")
    d={"ids":ids,"geometry":g,"chat":np.concatenate([a["chat"],b["chat"]]),"pscale":np.concatenate([a["pscale"],b["pscale"]]),
      "eta":np.concatenate([a["eta"],b["eta"]]),"absolute":np.concatenate([a["absolute"],b["absolute"]]),"weights":np.concatenate([a["weights"],b["weights"]])}
    req(d["chat"].shape==(32,21,7,2) and d["pscale"].shape==(32,21) and d["eta"].shape==(32,21,7),"32G target shape mismatch")
    return d

def deltas(m20,m32):
    out={}
    for k in m20["metrics"]:
        out[k]={}
        for s in ("median","q95","max"):
            a=m20["metrics"][k][s]; b=m32["metrics"][k][s]; q=b-a
            out[k][s]={"20G":a,"32G":b,"absolute_delta":q,"relative_delta":q/max(abs(a),1e-30)}
    for k in ("routing_pearson","pscale_pearson","seed_state_median_std"):
        a=m20[k];b=m32[k];out[k]={"20G":a,"32G":b,"absolute_delta":b-a,"relative_delta":(b-a)/max(abs(a),1e-30)}
    p20={x["case_id"]:x for x in m20["per_geometry"]}; p32={x["case_id"]:x for x in m32["per_geometry"]}
    shared=[]
    for cid in p20:
        shared.append({"case_id":cid,**{k:{"20G":p20[cid][k],"32G":p32[cid][k],"delta":p32[cid][k]-p20[cid][k]} for k in m20["metrics"]}})
    out["shared_20_geometry_deltas"]=shared
    out["new_12_geometry_metrics"]=[x for x in m32["per_geometry"] if x["case_id"] not in p20]
    return out

def coverage_verdict(a,b):
    if b["retrospective_h1"]=="PASS": return "DATA_COVERAGE_WAS_MAJOR_BOTTLENECK"
    wins=[]
    for k in ("state_relative_rmse","routing_eta_rmse","absolute_order_source_normalized_rmse","thresholded_absolute_order_relative_median","total_power_relative_rmse"):
        for s in ("median","q95"): wins.append(b["metrics"][k][s]<a["metrics"][k][s]-1e-12)
    wins.extend([b["routing_pearson"]>a["routing_pearson"]+1e-12,b["pscale_pearson"]>a["pscale_pearson"]+1e-12,
      b["seed_state_median_std"]<a["seed_state_median_std"]-1e-12])
    score=sum(wins)/len(wins)
    if score>=.60:return "DATA_COVERAGE_HELPED_BUT_H1_REMAINS_INSUFFICIENT"
    if score<=.40:return "DATA_COVERAGE_NOT_PRIMARY_BOTTLENECK"
    return "MIXED"

def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--preflight",action="store_true"); args=parser.parse_args()
    req(EXP_PATH.is_file() and DATA20_PATH.is_file() and TRUTH20_PATH.is_file(),"canonical source file missing")
    exp=jread(EXP_PATH); req(sha(EXP_PATH)==EXP_SHA and exp["frozen_physical_contract"]["contract_sha256"]==CONTRACT,"expansion/contract authority mismatch")
    runner=runner_authority(); dec=decoder_module(); gate=jread(GATE_PATH)
    req(sha(GATE_PATH)==GATE_SHA and gate["source_hashes"]["structured_freeze_report"]==sha(MODEL_REPORT)
      and gate["source_hashes"]["state_code"]==DECODER_SHA,"frozen H1 authority/source mismatch")
    d12=load12(exp,dec); d20=load20(dec); d32=combine(d20,d12)
    da=jread(DATA20_PATH); req(d20["ids"]==[x["case_id"] for x in da["cases"]],"historical geometry order changed")
    if args.preflight:
        print(json.dumps({"status":"PASS","preflight_only":True,"solver_invocations":0,"runner":runner,
          "stage1_entries":12,"stage1_replays":0,"stage1_H2_eta_max_error":max(x["h2_eta_max_abs_error"] for x in d12["parity"]),
          "stage1_H2_Pscale_max_relative_error":max(x["modal_pscale_max_relative_error"] for x in d12["parity"]),
          "20g_geometries":20,"32g_geometries":len(d32["ids"]),"scalar_rows":672,"order_rows":4704,
          "reserve_included":False,"output_written":False},ensure_ascii=True,indent=2));return
    if OUT.exists():
        marker=OUT/"PW_K6_32G_DATASET_AUTHORITY_V1.json"
        req(marker.is_file() and jread(marker).get("generator")==Path(__file__).name,"existing output is not owned by this task")
    OUT.mkdir(parents=True,exist_ok=True)
    now=datetime.datetime.now(datetime.timezone.utc).isoformat()
    close={"schema":"PW_K6_STAGE1_12G_CLOSEOUT_AUTHORITY_V1","status":"PASS","created_utc":now,"runner_authority":runner,
      "expansion_manifest_sha256":sha(EXP_PATH),"physical_contract_sha256":CONTRACT,"case_order":STAGE1,"scientific_entries":12,
      "solver_invocation_total":12,"replay_total":0,"new_invocations_during_closeout":0,
      "s35_history":"original FAILED_POSTENTRY preserved; one entry; LOAD-only recovery_003 produced TRUTH_VALID; not rewritten as clean DONE",
      "reserve_cases_untouched":sorted(RESERVE),"cases":d12["records"]}
    jwrite(OUT/"PW_K6_STAGE1_12G_CLOSEOUT_AUTHORITY_V1.json",close)
    fields=["case_id","attempt_id","run_id","solver_invocations","replay_count","raw_runner_state","final_scientific_state","solver_entered_utc",
      "solver_returned","gpu_engine_confirmed","post_run_fsp_sha256","post_run_fsp_sha256_source","native_h5_sha256","truth_h5_sha256","validation_status","energy_closure","fresh_load","recovery_history"]
    csvwrite(OUT/"stage1_accounting.csv",d12["records"],fields)
    authority={"schema":"PW_K6_32G_DATASET_AUTHORITY_V1","status":"PASS","created_utc":now,"generator":Path(__file__).name,
      "ordered_union":"formal 20G order followed by Stage-1 manifest order; no sorting/permutation canonicalization",
      "geometry_count":32,"ordered_geometry_ids":d32["ids"],"ordered_D_nm":d32["geometry"].astype(int).tolist(),
      "scalar_geometry_wavelength_rows":672,"order_geometry_wavelength_rows":4704,"wavelengths_nm":list(range(440,461)),
      "polarization":"P_XLIKE incident; TE/TM outgoing Floquet coordinates","state_schema":"PW_COMPLEX_FLOQUET_STATE_V1 POSTNP +z, seven y=0 orders, TE/TM",
      "physical_contract_sha256":CONTRACT,"expansion_manifest_sha256":sha(EXP_PATH),"20g_dataset_authority_sha256":sha(DATA20_PATH),
      "20g_truth_sha256":sha(TRUTH20_PATH),"h1_gate_sha256":sha(GATE_PATH),"model_freeze_sha256":sha(MODEL_REPORT),"h2_decoder_sha256":sha(DECODER_PATH),
      "historical_20g_artifact_provenance_limitation":"HISTORICAL_20G_ARTIFACT_PROVENANCE_LIMITATION preserved; formal SCIENTIFIC_VALID 20G truth reused without reopening FSP forensics",
      "stage1_closeout":"PW_K6_STAGE1_12G_CLOSEOUT_AUTHORITY_V1.json",
      "case_provenance":d20["provenance"]+[{"case_id":r["case_id"],"cohort":"STAGE1_12G","ordered_D_nm":r["ordered_D_nm"],
        "geometry_hash_sha256":r["geometry_hash_sha256"],"run_id":r["run_id"],"attempt_id":r["attempt_id"],
        "scientific_state":r["final_scientific_state"],"state_path":r["state_npz_path"],"state_sha256":r["state_npz_sha256"],
        "raw_fields_path":r["raw_fields_path"],"raw_fields_sha256":r["raw_fields_sha256"],"truth_h5_path":r["truth_h5_path"],
        "truth_h5_sha256":r["truth_h5_sha256"]} for r in d12["records"]],
      "truth_parity":{"20g":d20["parity"],"stage1_12g":d12["parity"],
        "20g_h2_eta_max_abs_error":max(x["h2_eta_max_abs_error"] for x in d20["parity"]),
        "20g_modal_pscale_max_relative_error":max(x["modal_pscale_max_relative_error"] for x in d20["parity"]),
        "stage1_h2_eta_max_abs_error":max(x["h2_eta_max_abs_error"] for x in d12["parity"]),
        "stage1_modal_pscale_max_relative_error":max(x["modal_pscale_max_relative_error"] for x in d12["parity"]),
        "stage1_pscale_source":"saved raw POSTNP E/H trapezoidal Poynting integral / unit-cell area / incident power per area; T_FDTD excluded"},
      "reserve_cases_included":False,"np_feature_confirmatory_v2_executed":False,"solver_invocations_in_this_analysis":0}
    jwrite(OUT/"PW_K6_32G_DATASET_AUTHORITY_V1.json",authority)
    np.savez_compressed(OUT/"dataset_truth_32g.npz",case_ids=np.asarray(d32["ids"]),ordered_D_nm=d32["geometry"],C_hat=d32["chat"],
      P_scale=d32["pscale"],eta=d32["eta"],absolute_order_power=d32["absolute"],modal_weights=d32["weights"])
    print("DATASET_PASS",json.dumps({"stage1_eta_max":authority["truth_parity"]["stage1_h2_eta_max_abs_error"],
      "stage1_pscale_max_rel":authority["truth_parity"]["stage1_modal_pscale_max_relative_error"],"rows":672,"orders":4704}),flush=True)
    m20,a20=model.run(d20); print("FROZEN_20G_DONE",json.dumps({"H1":m20["retrospective_h1"],"metrics":m20["metrics"]}),flush=True)
    m32,a32=model.run(d32); print("FROZEN_32G_DONE",json.dumps({"H1":m32["retrospective_h1"],"metrics":m32["metrics"]}),flush=True)
    jwrite(OUT/"PW_K6_FROZEN_FORWARD_H1_20G_V1.json",m20); jwrite(OUT/"PW_K6_FROZEN_FORWARD_H1_32G_V1.json",m32)
    dlt=deltas(m20,m32); verdict=coverage_verdict(m20,m32); dlt["data_coverage_verdict"]=verdict
    dlt["verdict_rule"]="32G all-gates pass => major; otherwise >=60% of 10 median/q95 diagnostics plus routing/scale Pearson and seed-stability directions improve => helped but insufficient; <=40% => not primary; otherwise mixed."
    jwrite(OUT/"PW_K6_20G_VS_32G_DELTAS_V1.json",dlt)
    keys=list(m20["metrics"]); r20={x["case_id"]:x for x in m20["per_geometry"]}; r32={x["case_id"]:x for x in m32["per_geometry"]}
    rows=[]
    for cid in d32["ids"]:
        q={"case_id":cid,"cohort":"FROZEN_20G" if cid in r20 else "STAGE1_12G"}
        for k in keys:
            q[k+"_20g"]=r20[cid][k] if cid in r20 else ""
            q[k+"_32g"]=r32[cid][k]
            q[k+"_delta"]=r32[cid][k]-r20[cid][k] if cid in r20 else ""
        rows.append(q)
    csvwrite(OUT/"per_geometry_metrics_20g_32g.csv",rows,["case_id","cohort"]+[k+s for k in keys for s in ("_20g","_32g","_delta")])
    np.savez_compressed(OUT/"oof_predictions_20g_32g.npz",case_ids=np.asarray(d32["ids"]),C_hat_truth_20g=d20["chat"],
      C_hat_truth_32g=d32["chat"],P_scale_truth_20g=d20["pscale"],P_scale_truth_32g=d32["pscale"],
      eta_truth_20g=d20["eta"],eta_truth_32g=d32["eta"],absolute_order_truth_20g=d20["absolute"],absolute_order_truth_32g=d32["absolute"],
      **{"20g_"+k:v for k,v in a20.items()},**{"32g_"+k:v for k,v in a32.items()})
    rep=["# PW_K6_STAGE1_32G_FROZEN_FORWARD_H1_V1","",f"Created UTC: {now}","",
      "## Stage-1 closeout","",
      "Twelve approved geometries have one entry each and zero replay. S35 retains original FAILED_POSTENTRY plus separately validated LOAD-only recovery; it is not rewritten as a clean DONE run. The other eleven are DONE/scientifically valid. This closeout and model analysis launched no solver.",
      "","| Case | Run | Entry | Replay | Final state | FSP SHA256 | Native H5 SHA256 | Truth H5 SHA256 | Validation | Closure |","|---|---|---:|---:|---|---|---|---|---|---:|"]
    for q in d12["records"]:
        rep.append("| {} | {} | {} | {} | {} | {} | {} | {} | {} | {:.3g} |".format(q["case_id"],q["run_id"],q["solver_invocations"],q["replay_count"],q["final_scientific_state"],q["post_run_fsp_sha256"],q["native_h5_sha256"],q["truth_h5_sha256"],q["validation_status"],q["energy_closure"]))
    rep += ["","Total Stage-1 entries: 12; replay: 0. S39 is the clean canary. Reserve geometries untouched.",
      "","## 32G dataset","",
      "Union order: formal frozen 20G order followed by Stage-1 manifest order. No sorting or permutation canonicalization. 32 unique geometries; 672 geometry-wavelength rows; 4,704 order rows; 440460 nm, 1 nm; P_XLIKE incident; TE/TM outputs.",
      "","Stage-1 P_scale comes from saved POSTNP raw E/H surface integration and saved incident power/area. Legacy T_FDTD was not used as total power. State/modal eta and total power are checked against the frozen H2 decoder and raw E/H closure.",
      "","The historical 20G artifact-provenance limitation remains explicit. Existing formal SCIENTIFIC_VALID 20G state/truth is used; no historical FSP forensic work was restarted.",
      "","## Frozen forward/H1 comparison","",
      "Model: PW_K6_STRUCTURED_FORWARD_MODEL_V1 M5 width 32; P_scale: frozen RBF Kernel Ridge; geometry LOGO with 3 grouped inner folds; seeds 0,1,2; CPU/offline; no architecture or threshold search.",
      "","| Metric | 20G median | 20G q95 | 20G worst | 32G median | 32G q95 | 32G worst |","|---|---:|---:|---:|---:|---:|---:|"]
    for k in keys:
        x=m20["metrics"][k]; y=m32["metrics"][k]
        rep.append(f"| {k} | {x['median']:.6g} | {x['q95']:.6g} | {x['max']:.6g} | {y['median']:.6g} | {y['q95']:.6g} | {y['max']:.6g} |")
    rep += ["","| Correlation/stability | 20G | 32G |","|---|---:|---:|",
      f"| Routing Pearson | {m20['routing_pearson']:.6g} | {m32['routing_pearson']:.6g} |",
      f"| P_scale Pearson | {m20['pscale_pearson']:.6g} | {m32['pscale_pearson']:.6g} |",
      f"| Seed state-median std | {m20['seed_state_median_std']:.6g} | {m32['seed_state_median_std']:.6g} |",
      "","H1 gates remain frozen and conjunctive. 20G: "+m20["retrospective_h1"]+"; 32G: "+m32["retrospective_h1"]+". Full gate values, per-geometry tails, absolute/relative deltas and OOF predictions are in the accompanying JSON, CSV and NPZ.",
      "","## Data-coverage verdict","",verdict,"",
      "Retrospective coverage comparison only; this does not establish prospective production admission or authorize more HF.",
      "NP-feature confirmatory V2 was not executed. GPU Runner source was not modified or newly qualified.",
      "","NEXT = CHART_REVIEW_32G_AND_NP_FORWARD_FEATURE_CONFIRMATORY_V2 (not executed).",""]
    rep=[x.replace(chr(19),"-") for x in rep]
    (OUT/"PW_K6_STAGE1_32G_FROZEN_FORWARD_H1_V1.md").write_text("\n".join(rep),encoding="utf-8")
    names=["PW_K6_STAGE1_12G_CLOSEOUT_AUTHORITY_V1.json","stage1_accounting.csv","PW_K6_32G_DATASET_AUTHORITY_V1.json","dataset_truth_32g.npz",
      "PW_K6_FROZEN_FORWARD_H1_20G_V1.json","PW_K6_FROZEN_FORWARD_H1_32G_V1.json","PW_K6_20G_VS_32G_DELTAS_V1.json",
      "per_geometry_metrics_20g_32g.csv","oof_predictions_20g_32g.npz","PW_K6_STAGE1_32G_FROZEN_FORWARD_H1_V1.md"]
    hashes={n:sha(OUT/n) for n in names}
    hashes["generator_script_sha256"]=sha(Path(__file__))
    hashes["model_module_sha256"]=sha(ROOT/"scripts"/"coupling_ml"/"pw_k6_stage1_32g_frozen_model_v1.py")
    jwrite(OUT/"artifact_hashes.json",hashes)
    print("ANALYSIS_COMPLETE",json.dumps({"H1_20G":m20["retrospective_h1"],"H1_32G":m32["retrospective_h1"],
      "verdict":verdict,"output":str(OUT),"hashes":hashes}),flush=True)

if __name__=="__main__": main()
