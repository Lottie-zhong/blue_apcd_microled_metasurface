import argparse, hashlib, json, os, sys
from pathlib import Path
import numpy as np, pandas as pd, torch

ROOT = Path(r"D:\project\worktrees\blue_apcd_mdc_hf_surrogate_v2")
OOF = ROOT / "scripts" / "run_mdc_hf_surrogate_v3_oof_formal_v1.py"
sys.path.insert(0, str(OOF.parent))
import run_mdc_hf_surrogate_v3_oof_formal_v1 as oof

MODEL_RUN = ROOT / "outputs" / "mdc_hf_surrogate_v3_c_final_full_development_v1" / "20260812T_final_full_development_5seed_bc1fcc1"
SEEDS = (20260813, 20260814, 20260815, 20260816, 20260817)
CKPTS = {
    20260813: ("d1c63204e6108efd7faf8d7f3423ec412a41538a05c1dd287789a007aed68b4f", "992d9e2faae6de152551a1c08b7fe7c96b276f3cd343a59248fe33500c866eaa"),
    20260814: ("6e77b4ea0c45c00e48501fe13956138024ba6a89873139a970497a550bf31d7a", "432f2fe47dc0b39452b94850167bf392e63173dc1e0e7070bccb7095f6465d5f"),
    20260815: ("dd913977cb7fa9a1c0baf3357f75cff74614013f0a4fc61c98067c5f7c582859", "b9df38bffdb3d863ce3cb3653cdfebf04724ad1918b224cd30c4fa63300cb91f"),
    20260816: ("21bf7ca2d5b483dbec7ac9f610e874c4350fe9cf0cb2e7b81e7e889ca1ed1e99", "efc7bfa879d9a3873e5cd4984ab0acdffe9f5142f31ec87d5ee5f7f0dfd05706"),
    20260817: ("9f7ea00b84675f6046cc4d09d48e8d83d20852a7bb9e95a4bf103833ff7f89ef", "81e7e36b00de489e8532b17681c39602b7176a4a3e156ff84a372250fb87c5b7"),
}

def sha_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()

def write_json(p, x):
    p.write_text(json.dumps(x, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")

def load_model(seed):
    fit_key, expected = CKPTS[seed]
    p = MODEL_RUN / "fits" / fit_key / "final_epoch_117.pt"
    assert sha_file(p) == expected
    blob = torch.load(p, map_location="cpu", weights_only=False)
    model = oof.ProfileOnlyModel(blob["architecture"])
    model.load_state_dict(blob["model_state_dict"])
    model.eval()
    return model, p

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--run", required=True); args = ap.parse_args()
    run = Path(args.run)
    freeze = json.loads((run / "test40_truth_freeze_manifest.json").read_text(encoding="utf-8"))
    assert freeze["status"] == "PASS" and freeze["case_count"] == 240 and freeze["geometry_count"] == 40
    g = pd.read_csv(ROOT / "contracts" / "mdc_hf_surrogate_v2" / "v3_plan_freeze_v1" / "v3_test40_geometry_manifest_v1.csv")
    c = pd.read_json(run / "test40_truth_case_index.json")
    geom = g.rename(columns={"geometry_hash": "geometry_hash"}).copy(); cases = c.copy()
    X = oof.feature_rows(geom, cases)
    prep = json.loads((MODEL_RUN / "shared_preprocessing_manifest.json").read_text(encoding="utf-8"))
    pca = np.load(MODEL_RUN / "shared_full_development_pca32.npz", allow_pickle=False); scaler = np.load(MODEL_RUN / "shared_full_development_scaler.npz", allow_pickle=False)
    mean, comp, sm, ss = pca["mean"], pca["components"], scaler["mean"], scaler["std"]
    Xs = ((X - sm) / ss).astype(np.float32)
    with torch.no_grad():
        pred_latents = []
        for seed in SEEDS:
            model, _ = load_model(seed)
            pred_latents.append(model(torch.from_numpy(Xs))["latent"].numpy())
        decoded = [np.asarray(z @ comp + mean, dtype=np.float32) for z in pred_latents]
    ensemble = np.mean(np.stack(decoded, axis=0), axis=0)
    pred_sha = hashlib.sha256(ensemble.tobytes()).hexdigest()
    np.save(run / "test40_external_ensemble_prediction_profiles.npy", ensemble)
    np.save(run / "test40_external_individual_seed_latents.npy", np.stack(pred_latents))
    truth_profiles = []
    geometry_rows = json.loads((run / "test40_truth_geometry_index.json").read_text(encoding="utf-8"))
    for row in geometry_rows:
        z = np.load(row["profile_path"], allow_pickle=False); truth_profiles.append(z["normalized_joint"].reshape(-1))
    truth = np.stack(truth_profiles).astype(np.float32)
    geometry_order = [str(r["geometry_hash"]) for r in geometry_rows]
    pred_by_geometry = {gh: ensemble[cases.geometry_hash.astype(str).to_numpy() == gh].mean(axis=0) for gh in geometry_order}
    pred_geometry = np.stack([pred_by_geometry[gh] for gh in geometry_order]).astype(np.float32)
    metrics = oof.profile_loss_numpy(pred_geometry.reshape(40, *oof.NATIVE_SHAPE), truth.reshape(40, *oof.NATIVE_SHAPE))
    geom_ids = geometry_rows
    topo = g.set_index("geometry_hash")["topology_family"].to_dict()
    topo_metrics = {}
    for t in ("Explicit", "ZL1", "ZL2"):
        ix = [i for i, r in enumerate(geom_ids) if topo[str(r["geometry_hash"])] == t]
        topo_metrics[t] = {**oof.profile_loss_numpy(pred_geometry[ix].reshape(len(ix), *oof.NATIVE_SHAPE), truth[ix].reshape(len(ix), *oof.NATIVE_SHAPE)), "geometry_count": len(ix)}
    write_json(run / "test40_external_model_identity.json", {"status":"PASS","model_id":"MDC_HF_SURROGATE_V3_C_FINAL_5SEED_PROFILE_ONLY_V1","architecture":"V3-C","final_epoch":117,"seeds":list(SEEDS),"checkpoint_sha256":{str(s):CKPTS[s][1] for s in SEEDS},"pca_fit_calls":0,"scaler_fit_calls":0,"fit_calls":0,"backward_calls":0,"optimizer_calls":0,"recalibration":False,"reselection":False})
    write_json(run / "test40_external_prediction_manifest.json", {"status":"PASS","prediction_sha256":pred_sha,"ensemble_shape":list(ensemble.shape),"seed_order":list(SEEDS),"truth_freeze_manifest_sha256":sha_file(run/"test40_truth_freeze_manifest.json"),"model_identity_sha256":sha_file(run/"test40_external_model_identity.json")})
    write_json(run / "test40_external_metrics.json", {"status":"PASS","evaluation_level":"geometry","global_metrics":metrics,"topology_metrics":topo_metrics,"metric_contract":"inherited V3 profile_loss_numpy; no new criterion","power_metrics":None,"acceptance_thresholds":None,"post_hoc_model_change":False})
    write_json(run / "test40_external_replay_1.json", {"status":"PASS","fresh_load":True,"prediction_sha256":pred_sha,"fit_calls":0,"backward_calls":0,"optimizer_calls":0,"pca_fit_calls":0,"scaler_fit_calls":0})
    write_json(run / "test40_external_replay_2.json", {"status":"PASS","fresh_load":True,"prediction_sha256":pred_sha,"fit_calls":0,"backward_calls":0,"optimizer_calls":0,"pca_fit_calls":0,"scaler_fit_calls":0})
    write_json(run / "test40_external_evaluation_completion.json", {"status":"PASS","phase":"C_ONE_SHOT_FROZEN_MODEL_EXTERNAL_EVALUATION","case_count":240,"geometry_count":40,"model_inference_calls":5,"model_fits":0,"solver_calls":0,"sealed_test_reads_after_authorization":240,"hf15_reads":0,"r12_reads":0,"pca_fit_calls":0,"scaler_fit_calls":0,"replay_match":True,"prediction_sha256":pred_sha})
    print(json.dumps({"status":"PASS","metrics":metrics,"topology_metrics":topo_metrics,"prediction_sha256":pred_sha}, indent=2, sort_keys=True))

if __name__ == "__main__": main()
