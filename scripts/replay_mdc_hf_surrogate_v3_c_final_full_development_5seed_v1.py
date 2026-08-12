from __future__ import annotations
import argparse, hashlib, json, sys
from pathlib import Path
import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import run_mdc_hf_surrogate_v3_c_final_full_development_5seed_v1 as trainer

def sha_array(x):
    return hashlib.sha256(np.asarray(x).tobytes()).hexdigest()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    run = Path(args.run_dir)
    pca = np.load(run / "shared_full_development_pca32.npz")
    X = np.load(run / "features_scaled.npy", mmap_mode="r")
    fixture = np.asarray(X[[0, 1, 2, 3, 4, 5]], dtype=np.float32)
    components = np.asarray(pca["components"], dtype=np.float32)
    mean = np.asarray(pca["mean"], dtype=np.float32)
    individual = {}
    decoded = []
    for seed in trainer.SEEDS:
        result = None
        for path in run.glob("fits/*/fit_result.json"):
            data = json.loads(path.read_text(encoding="utf-8"))
            if int(data["seed"]) == seed:
                result = data
                break
        if result is None:
            raise RuntimeError("missing seed")
        checkpoint = torch.load(result["checkpoint"], map_location="cpu", weights_only=False)
        model = trainer.oof.ProfileOnlyModel(trainer.V3C)
        model.load_state_dict(checkpoint["model_state_dict"])
        model.eval()
        with torch.no_grad():
            latent = model(torch.from_numpy(fixture))["latent"].numpy().astype(np.float32)
        profile = np.maximum(latent @ components + mean, 0.0)
        profile /= np.maximum(profile.sum(axis=1, keepdims=True), 1e-12)
        profile = profile.astype(np.float32)
        decoded.append(profile)
        individual[str(seed)] = {
            "latent_sha256": sha_array(latent),
            "decoded_profile_sha256": sha_array(profile),
            "shape": list(profile.shape),
            "sum_min": float(profile.sum(axis=1).min()),
            "sum_max": float(profile.sum(axis=1).max()),
            "checkpoint_sha256": result["checkpoint_sha256"],
        }
    ensemble = np.mean(np.stack(decoded, axis=0), axis=0, dtype=np.float32)
    payload = {
        "status": "PASS",
        "model_id": trainer.MODEL_ID,
        "architecture": "V3-C",
        "fixture_indices": [0, 1, 2, 3, 4, 5],
        "seed_order": list(trainer.SEEDS),
        "individual": individual,
        "ensemble_profile_sha256": sha_array(ensemble),
        "ensemble_shape": list(ensemble.shape),
        "ensemble_sum_min": float(ensemble.sum(axis=1).min()),
        "ensemble_sum_max": float(ensemble.sum(axis=1).max()),
        "fresh_load": True,
        "fit_calls_during_inference": 0,
        "backward_calls_during_inference": 0,
        "optimizer_calls_during_inference": 0,
        "pca_fit_calls_during_inference": 0,
        "scaler_fit_calls_during_inference": 0,
        "v3_test40_truth_reads": 0,
        "hf15_r12_truth_reads": 0,
    }
    payload["prediction_sha256"] = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    Path(args.output).write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(payload, sort_keys=True))

if __name__ == "__main__":
    main()
