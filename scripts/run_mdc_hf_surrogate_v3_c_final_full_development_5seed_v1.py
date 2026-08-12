"""Authorized MDC V3-C full-development 5-seed trainer.

This is separate from the 45-fit OOF runner.  It creates one shared
full-development PCA/scaler and exactly five fixed epoch-117 V3-C fits.
"""
from __future__ import annotations
import argparse, hashlib, json, math, os, random, subprocess, time
from pathlib import Path
from typing import Any

import numpy as np
import torch

import run_mdc_hf_surrogate_v3_oof_formal_v1 as oof

torch.set_num_threads(1)
MODEL_ID = "MDC_HF_SURROGATE_V3_C_FINAL_5SEED_PROFILE_ONLY_V1"
SEEDS = (20260813, 20260814, 20260815, 20260816, 20260817)
FINAL_EPOCHS = 117
PCA_COMPONENTS = 32
WARMUP = 10
MAX_SCHEDULER_EPOCHS = 400
LR = 3e-4
MIN_LR = 1e-6
BATCH_GEOMETRIES = 16
GRAD_CLIP = 1.0
V3C = {"id":"V3-C", "input_width":23, "latent_width":192,
       "profile_head_width":32, "residual_blocks":3,
       "residual_width":384, "dropout":0.0, "weight_decay":0.0}
WEIGHTS = {"profile":0.4117647058823529, "JS":0.23529411764705882,
           "spectral_CDF":0.17647058823529413,
           "angular_CDF":0.17647058823529413}
PROFILE_DIM = oof.PROFILE_DIM
NATIVE_SHAPE = oof.NATIVE_SHAPE

def sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()

def canonical(x: Any) -> str:
    return json.dumps(x, sort_keys=True, separators=(",",":"), ensure_ascii=False)

def sha_obj(x: Any) -> str:
    return hashlib.sha256(canonical(x).encode()).hexdigest()

def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)

def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))

def set_seed(seed: int) -> None:
    random.seed(seed); np.random.seed(seed % (2**32 - 1)); torch.manual_seed(seed)
    if torch.cuda.is_available(): torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True; torch.backends.cudnn.benchmark = False

def scheduler_factor(epoch: int) -> float:
    if epoch <= WARMUP: return epoch / WARMUP
    return (MIN_LR / LR) + (1 - MIN_LR / LR) * (1 + math.cos(math.pi * (epoch - WARMUP) / (MAX_SCHEDULER_EPOCHS - WARMUP))) / 2

def load_full_inputs():
    geom, cases, wavelength, angle_rad, _ = oof.load_inputs()
    if len(geom) != 200 or len(cases) != 1200 or cases.case_uid.nunique() != 1200:
        raise RuntimeError("HARD_GATE_FORMAL_MEMBERSHIP_200G1200C")
    if set(cases.groupby("geometry_hash").size().astype(int)) != {6}:
        raise RuntimeError("HARD_GATE_SIX_CASE_COMPLETENESS")
    if oof.read_json(oof.TEST40_LOCK).get("labels_read") != 0 or oof.read_json(oof.TEST40_LOCK).get("labels_generated") is not False:
        raise RuntimeError("HARD_GATE_V3_TEST40_SEALED")
    if oof.read_json(oof.TEST40_OVERLAP).get("status") != "PASS":
        raise RuntimeError("HARD_GATE_V3_TEST40_OVERLAP")
    return geom, cases, wavelength, angle_rad

def load_q(cases, wavelength, angle_rad, run: Path):
    parent = oof.REPO / "outputs" / "mdc_hf_surrogate_v3_oof_formal_v1" / "20260811T_formal_oof_29ee7c9" / "profile_q_memmap.f32"
    expected = 1200 * PROFILE_DIM * 4
    if not parent.exists() or parent.stat().st_size != expected:
        raise RuntimeError("HARD_GATE_DEVELOPMENT_Q_ARTIFACT_MISSING")
    # Parent q contains only legal DOE/V2/AL64 development rows in the same
    # canonical case order; no V3-Test40 target path is touched.
    q = np.memmap(parent, mode="r", dtype="float32", shape=(1200, PROFILE_DIM))
    return q, sha_file(parent)

def fit_shared_pca(q, run: Path):
    X = np.asarray(q[:], dtype=np.float32)
    mean = X.mean(axis=0, dtype=np.float64).astype(np.float32)
    centered = X - mean
    gram = np.asarray(centered @ centered.T, dtype=np.float64)
    vals, vecs = np.linalg.eigh(gram)
    ix = np.argsort(vals)[::-1][:PCA_COMPONENTS]
    vals = np.maximum(vals[ix], 1e-18)
    components = np.asarray((vecs[:, ix].T @ centered) / np.sqrt(vals)[:, None], dtype=np.float32)
    signs = np.where(components[np.arange(PCA_COMPONENTS), np.argmax(np.abs(components), axis=1)] < 0, -1.0, 1.0).astype(np.float32)
    components *= signs[:, None]
    path = run / "shared_full_development_pca32.npz"
    np.savez(path, mean=mean, components=components, explained_eigenvalues=vals)
    return mean, components, {"fit_count":1, "components":32, "algorithm":"centered_gram_eigh_v1", "sha256":sha_file(path), "path":str(path)}

def fit_shared_scaler(Xraw: np.ndarray, run: Path):
    mean = Xraw.mean(axis=0, dtype=np.float64).astype(np.float32)
    std = Xraw.std(axis=0, dtype=np.float64).astype(np.float32)
    std[:len(oof.PARENT_FAMILY_FEATURES)] = 1.0
    std[len(oof.PARENT_FAMILY_FEATURES)+8:] = 1.0
    std = np.where(std < 1e-12, 1.0, std).astype(np.float32)
    path = run / "shared_full_development_scaler.npz"
    np.savez(path, mean=mean, std=std)
    return mean, std, {"fit_count":1, "sha256":sha_file(path), "path":str(path)}

def transform(q, mean, components, run: Path):
    z = np.empty((len(q), PCA_COMPONENTS), dtype=np.float32)
    for start in range(0, len(q), 16):
        z[start:start+16] = (np.asarray(q[start:start+16], dtype=np.float32) - mean) @ components.T
    np.save(run / "full_development_latent_targets.npy", z)
    return z

def geometry_batches(geom, cases, seed, epoch):
    order = sorted(geom.geometry_hash.astype(str), key=lambda h: sha_obj(["MDC_V3_FINAL_GEOMETRY_ORDER", seed, epoch, h]))
    groups = cases.groupby("geometry_hash", sort=False).indices
    out = []
    for start in range(0, len(order), BATCH_GEOMETRIES):
        out.append(np.concatenate([np.asarray(groups[h], dtype=np.int64) for h in order[start:start+BATCH_GEOMETRIES]]))
    return out

def param_sha(model):
    h = hashlib.sha256()
    for k,v in model.state_dict().items(): h.update(k.encode()); h.update(v.detach().cpu().numpy().tobytes())
    return h.hexdigest()

def fit_one(run, geom, cases, Xs, z, mean, components, pca_sha, scaler_sha, q_sha, code_commit, seed):
    membership_sha = sha_obj(cases[["role","case_uid","geometry_hash","source_position","dipole_orientation"]].to_dict("records"))
    fit_id = {"model_id":MODEL_ID,"architecture_id":"V3-C","seed":seed,"membership_sha256":membership_sha,"pca_sha256":pca_sha,"scaler_sha256":scaler_sha,"loss_sha256":sha_file(oof.LOSS_CONTRACT),"optimizer_scheduler_sha256":sha_obj({"optimizer":"AdamW","lr":LR,"min_lr":MIN_LR,"warmup":WARMUP,"scheduler":"cosine_decay","scheduler_max_epochs":MAX_SCHEDULER_EPOCHS,"gradient_clip":GRAD_CLIP,"batch_geometry_groups":BATCH_GEOMETRIES}),"epoch_count":FINAL_EPOCHS}
    key = sha_obj(fit_id); directory = run / "fits" / key; directory.mkdir(parents=True, exist_ok=True)
    final = directory / f"final_epoch_{FINAL_EPOCHS}.pt"; result_path = directory / "fit_result.json"; state_path = directory / "resume_state.pt"
    if final.exists() and result_path.exists():
        rec = read_json(result_path)
        if rec.get("fit_id") != fit_id: raise RuntimeError("HARD_GATE_DUPLICATE_FORMAL_IDENTITY")
        return {**rec,"resumed":True}
    set_seed(seed); device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = oof.ProfileOnlyModel(V3C).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=0.0)
    sched = torch.optim.lr_scheduler.LambdaLR(opt, lambda e: scheduler_factor(e+1))
    start_epoch=0; history=[]; resume_count=0
    if state_path.exists():
        state=torch.load(state_path,map_location=device,weights_only=False)
        if state.get("fit_id") != fit_id: raise RuntimeError("HARD_GATE_RESUME_IDENTITY_MISMATCH")
        model.load_state_dict(state["model"]); opt.load_state_dict(state["optimizer"]); sched.load_state_dict(state["scheduler"]); start_epoch=int(state["epoch"]); history=list(state["history"]); resume_count=int(state.get("resume_count",0))+1
    x_t=torch.from_numpy(Xs).to(device); z_t=torch.from_numpy(z).to(device); comp_t=torch.from_numpy(components).to(device); mean_t=torch.from_numpy(mean).to(device)
    optimizer_steps=sum(int(h["optimizer_steps_this_epoch"]) for h in history); backward_calls=optimizer_steps
    for epoch in range(start_epoch+1, FINAL_EPOCHS+1):
        model.train(); sums={k:0.0 for k in WEIGHTS}; count=0; t0=time.time()
        for batch in geometry_batches(geom,cases,seed,epoch):
            opt.zero_grad(set_to_none=True); out=model(x_t[batch])["latent"]; pred=out@comp_t+mean_t; truth=z_t[batch]@comp_t+mean_t
            vals=oof.profile_loss_torch(pred.reshape(-1,*NATIVE_SHAPE),truth.reshape(-1,*NATIVE_SHAPE)); vals["total"].backward(); torch.nn.utils.clip_grad_norm_(model.parameters(),GRAD_CLIP); opt.step()
            count += 1; optimizer_steps += 1; backward_calls += 1
            for k in WEIGHTS: sums[k] += float(vals[k].detach().cpu())
        sched.step(); avg={k:sums[k]/count for k in WEIGHTS}; history.append({"seed":seed,"epoch":epoch,"total_loss":sum(WEIGHTS[k]*avg[k] for k in WEIGHTS),**{f"L_{k}":avg[k] for k in WEIGHTS},"lr":float(opt.param_groups[0]["lr"]),"wall_time_s":time.time()-t0,"optimizer_steps_this_epoch":count,"backward_calls_this_epoch":count,"scope":"FULL_DEVELOPMENT_IN_SAMPLE_TRAINING_SANITY_ONLY"})
        tmp=state_path.with_suffix(".pt.tmp"); torch.save({"fit_id":fit_id,"epoch":epoch,"model":model.state_dict(),"optimizer":opt.state_dict(),"scheduler":sched.state_dict(),"history":history,"resume_count":resume_count},tmp); os.replace(tmp,state_path)
    if len(history)!=FINAL_EPOCHS: raise RuntimeError("HARD_GATE_FINAL_EPOCH_INCOMPLETE")
    tmp=final.with_suffix(".pt.tmp"); torch.save({"model_state_dict":model.state_dict(),"architecture":V3C,"model_id":MODEL_ID,"seed":seed,"final_epoch":FINAL_EPOCHS,"fit_id":fit_id,"code_commit":code_commit},tmp); os.replace(tmp,final)
    rec={"status":"PASS","fit_id":fit_id,"fit_key":key,"seed":seed,"started":True,"completed":True,"resumed":resume_count>0,"resume_count":resume_count,"final_epoch":FINAL_EPOCHS,"history_count":len(history),"final_loss":history[-1]["total_loss"],"wall_time_s":sum(h["wall_time_s"] for h in history),"checkpoint":str(final),"checkpoint_sha256":sha_file(final),"parameter_sha256":param_sha(model),"optimizer_steps":optimizer_steps,"backward_calls":backward_calls,"pca_fit_count":0,"scaler_fit_count":0,"v3_test40_truth_reads":0,"hf15_r12_truth_reads":0}
    write_json(result_path,rec); write_json(directory/"history.json",{"status":"PASS","seed":seed,"epochs":history}); return rec

def run(args):
    run=Path(args.run_dir); run.mkdir(parents=True,exist_ok=True); geom,cases,wavelength,angle_rad=load_full_inputs(); Xraw=oof.feature_rows(geom,cases); q,q_sha=load_q(cases,wavelength,angle_rad,run)
    if args.preflight_only: return {"status":"PREFLIGHT_PASS","geometry_count":len(geom),"case_count":len(cases),"pca_fit_count":0,"scaler_fit_count":0}
    mean,components,pca=fit_shared_pca(q,run); z=transform(q,mean,components,run); sm,ss,scaler=fit_shared_scaler(Xraw,run); Xs=(Xraw-sm)/ss; np.save(run/"features_scaled.npy",Xs)
    membership_sha=sha_obj(cases[["role","case_uid","geometry_hash","source_position","dipole_orientation"]].to_dict("records")); write_json(run/"full_development_membership.json",{"status":"PASS","geometry_count":200,"case_count":1200,"cases_per_geometry":6,"membership_sha256":membership_sha,"roles":cases.groupby("role").size().to_dict(),"native_shape":list(NATIVE_SHAPE),"source_q_sha256":q_sha,"v3_test40_truth_reads":0,"hf15_r12_truth_reads":0}); write_json(run/"shared_preprocessing_manifest.json",{"status":"PASS","pca":pca,"scaler":scaler,"membership_sha256":membership_sha,"source_q_sha256":q_sha,"shared_by_seeds":list(SEEDS),"per_seed_pca_fit":False,"per_seed_scaler_fit":False})
    commit=subprocess.check_output(["git","-C",str(oof.REPO),"rev-parse","HEAD"],text=True).strip(); records=[]
    for seed in SEEDS:
        rec=fit_one(run,geom,cases,Xs,z,mean,components,pca["sha256"],scaler["sha256"],q_sha,commit,seed); records.append(rec); write_json(run/"training_accounting.json",{"planned":5,"started":len(records),"completed":sum(int(x["completed"]) for x in records),"resumed":sum(int(x["resumed"]) for x in records),"failed":0,"duplicate_formal_identities":0,"pca_fit_count":1,"scaler_fit_count":1,"solver_calls":0,"v3_test40_truth_reads":0,"hf15_r12_truth_reads":0,"status":"IN_PROGRESS"})
    write_json(run/"training_accounting.json",{"planned":5,"started":5,"completed":5,"resumed":sum(int(x["resumed"]) for x in records),"failed":0,"duplicate_formal_identities":0,"pca_fit_count":1,"scaler_fit_count":1,"solver_calls":0,"v3_test40_truth_reads":0,"hf15_r12_truth_reads":0,"status":"PASS"}); write_json(run/"seed_training_registry.json",{"status":"PASS","model_id":MODEL_ID,"architecture":"V3-C","final_epoch":FINAL_EPOCHS,"seeds":records,"selection":"none; retain all five"}); return {"status":"PASS","run_dir":str(run),"records":records}

if __name__ == "__main__":
    ap=argparse.ArgumentParser(); ap.add_argument("--run-dir",required=True); ap.add_argument("--preflight-only",action="store_true"); print(json.dumps(run(ap.parse_args()),indent=2,sort_keys=True))
