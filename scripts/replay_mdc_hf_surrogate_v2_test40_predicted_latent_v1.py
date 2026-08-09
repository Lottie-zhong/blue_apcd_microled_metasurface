from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import joblib
import numpy as np
import torch
import torch.nn as nn


ROOT = Path(r"D:\project\worktrees\blue_apcd_mdc_hf_surrogate_v2")
DOE = ROOT / "outputs/mdc_hf_surrogate_v2_doe96_joint_profile_database_v1/20260803T_doe96_joint_profile_6b6d7e2"
FINAL = ROOT / "outputs/mdc_hf_surrogate_v2_m1_final_5seed_ensemble_v1/20260804T_final_m1_5seed_067c76b"
SEEDS = [20260804, 20260805, 20260806, 20260807, 20260808]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


class Block(nn.Module):
    def __init__(self):
        super().__init__()
        self.a = nn.Linear(256, 256)
        self.b = nn.Linear(256, 256)
        self.drop = nn.Dropout(0.05)

    def forward(self, x):
        return torch.nn.functional.gelu(x + self.drop(self.b(torch.nn.functional.gelu(self.a(x)))))


class Net(nn.Module):
    def __init__(self, dimension: int):
        super().__init__()
        self.inp = nn.Linear(dimension, 256)
        self.blocks = nn.ModuleList([Block() for _ in range(3)])
        self.h = nn.Linear(256, 128)
        self.lat = nn.Linear(128, 32)
        self.pow = nn.Linear(128, 1)
        self.aux = nn.Linear(128, 7)

    def forward(self, x):
        x = torch.nn.functional.gelu(self.inp(x))
        for block in self.blocks:
            x = block(x)
        x = torch.nn.functional.gelu(self.h(x))
        return self.lat(x), self.pow(x).squeeze(-1), self.aux(x)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--expected-profiles", required=True, type=Path)
    parser.add_argument("--expected-power", required=True, type=Path)
    parser.add_argument("--expected-log-power", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    features = np.load(args.input, allow_pickle=False).astype(np.float32)
    expected_profiles = np.load(args.expected_profiles, mmap_mode="r")
    expected_power = np.load(args.expected_power, allow_pickle=False).astype(np.float32)
    expected_log_power = np.load(args.expected_log_power, allow_pickle=False).astype(np.float32)
    if features.shape != (240, 23) or expected_profiles.shape != (240, 301, 2000) or expected_power.shape != (240,) or expected_log_power.shape != (240,):
        raise RuntimeError("HARD_GATE_TEST40_REPLAY_INPUT_SHAPE")

    target_scaler = json.loads((FINAL / "final_target_scaler_manifest.json").read_text(encoding="utf-8"))
    latent_mean = np.asarray(target_scaler["latent_mean"], np.float32)
    latent_std = np.asarray(target_scaler["latent_std"], np.float32)
    log_power_mean = float(target_scaler["log_power_mean"])
    log_power_std = float(target_scaler["log_power_std"])
    compressor = joblib.load(DOE / "final_profile_compressor.joblib")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    x = torch.from_numpy(features).to(device)
    latent_by_seed = []
    log_power_by_seed = []
    checkpoint_records = []
    with torch.inference_mode():
        for seed in SEEDS:
            checkpoint = FINAL / "checkpoints" / f"final_M1_seed{seed}.pt"
            payload = torch.load(checkpoint, map_location=device, weights_only=False)
            model = Net(features.shape[1]).to(device)
            model.load_state_dict(payload["model_state_dict"])
            model.eval()
            latent_std_prediction, log_power_std_prediction, _ = model(x)
            latent = latent_std_prediction.detach().cpu().numpy() * latent_std + latent_mean
            log_power = log_power_std_prediction.detach().cpu().numpy() * log_power_std + log_power_mean
            latent_by_seed.append(latent.astype(np.float32))
            log_power_by_seed.append(log_power.astype(np.float32))
            checkpoint_records.append({"seed": seed, "sha256": sha256(checkpoint)})

    latent_by_seed = np.asarray(latent_by_seed, np.float32)
    log_power_by_seed = np.asarray(log_power_by_seed, np.float32)
    latent_ensemble = latent_by_seed.mean(0, dtype=np.float32)
    log_power_ensemble = log_power_by_seed.mean(0, dtype=np.float32)
    power_ensemble = np.exp(log_power_ensemble).astype(np.float32)
    np.save(args.output / "test40_predicted_latent_by_seed.npy", latent_by_seed)
    np.save(args.output / "test40_predicted_latent_ensemble.npy", latent_ensemble)
    np.save(args.output / "test40_replayed_ensemble_log_power.npy", log_power_ensemble)

    component_mean = torch.from_numpy(compressor["mean"].astype(np.float32)).to(device)
    components = torch.from_numpy(compressor["components"].astype(np.float32)).to(device)
    latent_device = torch.from_numpy(latent_by_seed).to(device)
    maximum_difference = 0.0
    mean_difference_sum = 0.0
    element_count = 0
    expected_raw_hash = hashlib.sha256()
    replay_raw_hash = hashlib.sha256()
    with torch.inference_mode():
        for start in range(0, 240, 8):
            stop = min(start + 8, 240)
            ensemble_q = None
            for seed_index in range(len(SEEDS)):
                raw = latent_device[seed_index, start:stop] @ components + component_mean
                q = torch.clamp(raw, min=0.0)
                q = q / q.sum(1, keepdim=True).clamp_min(1e-12)
                ensemble_q = q if ensemble_q is None else ensemble_q + q
            ensemble_q = ensemble_q / float(len(SEEDS))
            ensemble_q = ensemble_q / ensemble_q.sum(1, keepdim=True).clamp_min(1e-12)
            replay = ensemble_q.reshape(-1, 301, 2000).detach().cpu().numpy().astype(np.float32)
            expected = np.asarray(expected_profiles[start:stop], np.float32)
            difference = np.abs(replay - expected)
            maximum_difference = max(maximum_difference, float(difference.max()))
            mean_difference_sum += float(difference.sum(dtype=np.float64))
            element_count += difference.size
            expected_raw_hash.update(expected.tobytes(order="C"))
            replay_raw_hash.update(replay.tobytes(order="C"))

    power_maximum_difference = float(np.max(np.abs(power_ensemble - expected_power)))
    log_power_maximum_difference = float(np.max(np.abs(log_power_ensemble - expected_log_power)))
    profile_tolerance = 1e-10
    log_power_tolerance = 2e-6
    power_tolerance = 1e-4
    status = "PASS_EXACT_FROZEN_PREDICTION_REPLAY" if maximum_difference <= profile_tolerance and log_power_maximum_difference <= log_power_tolerance and power_maximum_difference <= power_tolerance else "HARD_GATE_TEST40_PREDICTION_REPLAY_MISMATCH"
    manifest = {
        "status": status,
        "model_id": "MDC_HF_M1_GEOMETRY_CONDITIONED_DIRECT_FINAL_5SEED_V1",
        "replay_python_executable": sys.executable,
        "historical_training_python_executable_proven": False,
        "historical_training_environment_note": "checkpoint registry freezes torch/CUDA versions but not sys.executable or conda environment name",
        "torch_version": torch.__version__, "cuda_version": torch.version.cuda,
        "device": str(device), "checkpoint_loads": len(SEEDS), "checkpoints": checkpoint_records,
        "input_shape": list(features.shape), "input_sha256": sha256(args.input),
        "latent_by_seed_shape": list(latent_by_seed.shape), "latent_ensemble_shape": list(latent_ensemble.shape),
        "latent_ensemble_definition": "uniform arithmetic mean of five inverse-target-scaled latent-head outputs",
        "frozen_profile_replay_max_abs_difference": maximum_difference,
        "frozen_profile_replay_mean_abs_difference": mean_difference_sum / element_count,
        "frozen_profile_raw_sha256": expected_raw_hash.hexdigest(),
        "replayed_profile_raw_sha256": replay_raw_hash.hexdigest(),
        "frozen_log_power_replay_max_abs_difference": log_power_maximum_difference,
        "frozen_power_replay_max_abs_difference": power_maximum_difference,
        "profile_tolerance": profile_tolerance, "log_power_tolerance": log_power_tolerance,
        "power_tolerance": power_tolerance,
        "fit_calls": 0, "optimizer_calls": 0, "backward_calls": 0,
        "PCA_fit_calls": 0, "scaler_fit_calls": 0, "solver_calls": 0,
        "HF15_reads": 0, "R12_reads": 0, "sealed_reads": 0,
    }
    (args.output / "test40_predicted_latent_replay_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))
    if status != "PASS_EXACT_FROZEN_PREDICTION_REPLAY":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
