import csv
import hashlib
import importlib.util
import json
import math
import random
import subprocess
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
import torch

ROOT = Path(r"D:\project\worktrees\blue_apcd_lp_stage11_4")
O = ROOT / "outputs/lp_ml_dataset_v1"
C = O / "clean_v2"
A = O / "analysis"
P = O / "plans/lp_ml_six_bin_inverse_search_v1"
REPORT = ROOT / "reports/lp_ml_six_bin_inverse_search_v1.md"
QID = "LPML_R1_GLOBAL_SOBOL_054"
WAVES = np.array([450.0, 450.5, 451.0, 451.5, 452.0, 452.5, 453.0, 453.5, 454.0], dtype=float)
SEEDS = [11, 22, 33, 44, 55]
BOUNDS = np.array([[108.0, 112.0], [106.0, 110.0], [98.0, 102.0], [196.0, 204.0], [-1.2, 1.2]], dtype=float)
QUANT = np.array([1.0, 1.0, 1.0, 1.0, 0.1], dtype=float)
VARS = ["J1_side_nm", "J2_length_nm", "J2_width_nm", "D_nm", "Psi_deg"]
TARGET_HASH = "bb575391319f97e417ccac16be95c3e1d3569dece2363a9d1d338d2d7c1e74e5"
CONTRACT_DIR = O / "plans/lp_ml_six_bin_inverse_design_planning_v1"


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def dump(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def rd_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("\n", encoding="utf-8")
        return
    fields = list(rows[0])
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def git(args):
    return subprocess.run(["git", "-C", str(ROOT), *args], text=True, capture_output=True, check=True).stdout.strip()


def wrap_rad(x):
    return torch.atan2(torch.sin(x), torch.cos(x))


def wrap_np(x):
    return np.arctan2(np.sin(x), np.cos(x))


def qvec(v):
    a = np.asarray(v, dtype=float)
    z = np.rint(a / QUANT) * QUANT
    z = np.minimum(np.maximum(z, BOUNDS[:, 0]), BOUNDS[:, 1])
    z[-1] = round(float(z[-1]), 1)
    return z


def vector_key(v):
    z = qvec(v)
    return tuple(float(x) for x in z)


def identity_hash(v, label):
    payload = json.dumps({"label": label, "vector": [float(x) for x in qvec(v)]}, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def model_import():
    path = ROOT / "scripts/lp_ml_round2_clean_recompetition_v2.py"
    spec = importlib.util.spec_from_file_location("lp_recomp", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_models(mod, kind, old_mu, old_sd, clean_mu, clean_sd):
    if kind == "C0":
        root = O / "model_runtime_round1_frozen_v1"
        mu, sd = old_mu, old_sd
    else:
        root = C / "model_runtime_recompetition_v2" / kind
        mu, sd = clean_mu, clean_sd
    models = []
    paths = []
    for seed in SEEDS:
        path = root / f"residual_mlp_seed_{seed}.pt"
        model = mod.N().cuda()
        state = torch.load(path, map_location="cuda", weights_only=False)
        model.load_state_dict(state.get("model_state_dict", state.get("state_dict", state)))
        model.eval()
        for p in model.parameters():
            p.requires_grad_(False)
        models.append(model)
        paths.append(path)
    return models, torch.tensor(mu, dtype=torch.float32, device="cuda"), torch.tensor(sd, dtype=torch.float32, device="cuda"), paths


def feature_tensor(u, waves):
    # u: [B,5], waves: [9]
    b = u.shape[0]
    w = waves.to(u.device).view(1, -1).expand(b, -1)
    psi = torch.deg2rad(u[:, 4:5]).expand(-1, w.shape[1])
    j1 = u[:, 0:1].expand(-1, w.shape[1])
    l2 = u[:, 1:2].expand(-1, w.shape[1])
    w2 = u[:, 2:3].expand(-1, w.shape[1])
    d = u[:, 3:4].expand(-1, w.shape[1])
    return torch.stack([j1, l2, w2, d, torch.sin(psi), torch.cos(psi), w], dim=-1)


def predict_kind(models, mu, sd, u, waves):
    x = feature_tensor(u, waves)
    flat = ((x - mu) / sd).reshape(-1, 7)
    vals = [m(flat).reshape(u.shape[0], len(waves), 8) for m in models]
    stack = torch.stack(vals)
    return stack.mean(0), stack.std(0).mean(-1).mean(-1), stack


def metrics_torch(pred):
    # returns one scalar per candidate, averaged over the nine wavelengths
    j = torch.complex(pred[..., 0], pred[..., 1])
    x = torch.complex(pred[..., 2], pred[..., 3])
    y = torch.complex(pred[..., 4], pred[..., 5])
    yy = torch.complex(pred[..., 6], pred[..., 7])
    n2 = torch.abs(j) ** 2 + torch.abs(x) ** 2 + torch.abs(y) ** 2 + torch.abs(yy) ** 2 + 1e-8
    shape = torch.sqrt((torch.abs(x) ** 2 + torch.abs(y) ** 2 + torch.abs(yy) ** 2) / n2)
    txx = torch.abs(j) ** 2
    txy = torch.abs(x) ** 2
    tyx = torch.abs(y) ** 2
    tyy = torch.abs(yy) ** 2
    leakage = txy + tyx + tyy
    matrix = torch.stack([torch.stack([j, x], dim=-1), torch.stack([y, yy], dim=-1)], dim=-2)
    sv = torch.linalg.svdvals(matrix)
    ratio = sv[..., 1] / (sv[..., 0] + 1e-8)
    phase = torch.atan2(j.imag, j.real)
    ep = torch.abs(wrap_rad(phase[..., -1] - phase[..., 0]))
    slope = torch.std(wrap_rad(phase[..., 1:] - phase[..., :-1]), dim=-1)
    curvature = torch.std(wrap_rad(phase[..., 2:] - 2 * phase[..., 1:-1] + phase[..., :-2]), dim=-1)
    spectral = ep + slope + curvature + torch.std(txx, dim=-1)
    return {
        "shape": shape.mean(-1),
        "phase": phase,
        "phase_center": phase[..., 4],
        "rank": ratio.mean(-1),
        "leakage": leakage.mean(-1),
        "throughput": txx.mean(-1),
        "spectral": spectral,
        "Txx_center": txx[..., 4],
        "Tyy_center": tyy[..., 4],
    }


def objective_terms(blend, c0, c1_stack, target_phase, scales, weights):
    mb = metrics_torch(blend)
    m0 = metrics_torch(c0)
    phase = torch.abs(wrap_rad(mb["phase_center"] - target_phase)) / scales["phase"]
    shape = mb["shape"] / scales["shape"]
    rank = mb["rank"] / scales["rank"]
    leak = mb["leakage"] / scales["leakage"]
    throughput = torch.relu(1.0 - mb["Txx_center"]) / scales["throughput"]
    spectral = mb["spectral"] / scales["spectral"]
    uncertainty = c1_stack.std(0).abs().mean(dim=(1, 2)) / scales["uncertainty"]
    disagreement = torch.sqrt(torch.mean((c0 - blend) ** 2, dim=(1, 2))) / scales["consensus"]
    total = weights["phase"] * phase + weights["projector"] * shape + weights["rank"] * rank + weights["leakage"] * leak + weights["throughput"] * throughput + weights["spectral"] * spectral + weights["uncertainty"] * uncertainty + weights["consensus"] * disagreement
    return total, {"phase": phase, "shape": shape, "rank": rank, "leakage": leak, "throughput": throughput, "spectral": spectral, "uncertainty": uncertainty, "consensus": disagreement, "metrics": mb, "m0": m0}


def manufacturing(v):
    z = qvec(v)
    direct = float(z[3] - 0.5 * (z[0] + z[1]))
    periodic = float(432.0 - z[3] - 0.5 * (z[0] + z[1]))
    ok = bool(np.all(z >= BOUNDS[:, 0] - 1e-9) and np.all(z <= BOUNDS[:, 1] + 1e-9) and direct >= 60.0 and periodic >= 60.0)
    return ok, direct, periodic


def add_candidate(out, v, target_phase, offset, source, continuous_loss, quantized_loss, trace_id):
    z = qvec(v)
    ok, direct, periodic = manufacturing(z)
    if not ok:
        return
    out.append({"vector": z, "target_phase": float(target_phase), "phi_offset": float(offset), "source": source, "continuous_loss": float(continuous_loss), "quantized_loss": float(quantized_loss), "trace_id": trace_id, "direct_gap_nm": direct, "periodic_gap_nm": periodic, "manufacturing_pass": True})


def optimize_batch(models, old_mu, old_sd, clean_mu, clean_sd, starts, target_phase, scales, weights, steps=28):
    waves = torch.tensor(WAVES, dtype=torch.float32, device="cuda")
    u = torch.tensor(starts, dtype=torch.float32, device="cuda", requires_grad=True)
    low = torch.tensor(BOUNDS[:, 0], dtype=torch.float32, device="cuda")
    high = torch.tensor(BOUNDS[:, 1], dtype=torch.float32, device="cuda")
    opt = torch.optim.Adam([u], lr=0.08)
    best_u = u.detach().clone()
    best_loss = torch.full((len(starts),), float("inf"), device="cuda")
    for _ in range(steps):
        opt.zero_grad(set_to_none=True)
        c0, _, _ = predict_kind(models["C0"][0], models["C0"][1], models["C0"][2], u, waves)
        c1, _, c1_stack = predict_kind(models["C1"][0], models["C1"][1], models["C1"][2], u, waves)
        blend = 0.95 * c0 + 0.05 * c1
        loss, _ = objective_terms(blend, c0, c1_stack, math.radians(target_phase), scales, weights)
        loss.sum().backward()
        opt.step()
        with torch.no_grad():
            u.clamp_(low, high)
            improved = loss.detach() < best_loss
            best_loss = torch.where(improved, loss.detach(), best_loss)
            best_u = torch.where(improved[:, None], u.detach(), best_u)
    return best_u.detach().cpu().numpy(), best_loss.detach().cpu().numpy()


def eval_candidates(models, vectors, target_phases, offsets, sources, traces, scales, weights):
    waves = torch.tensor(WAVES, dtype=torch.float32, device="cuda")
    u = torch.tensor(np.asarray(vectors), dtype=torch.float32, device="cuda")
    preds = {}
    for kind in ["C0", "C1", "C2", "C3", "C4"]:
        preds[kind] = predict_kind(models[kind][0], models[kind][1], models[kind][2], u, waves)
    blend = 0.95 * preds["C0"][0] + 0.05 * preds["C1"][0]
    rows = []
    for i, v in enumerate(vectors):
        ok, direct, periodic = manufacturing(v)
        c0 = preds["C0"][0][i : i + 1]
        b = blend[i : i + 1]
        c1stack = preds["C1"][2][..., i : i + 1, :, :].squeeze(1) if False else preds["C1"][2][:, i : i + 1]
        target = math.radians(float(target_phases[i]))
        total, terms = objective_terms(b, c0, c1stack, target, scales, weights)
        # derive robust model disagreement and uncertainty across C1-C4 means.
        means = torch.stack([preds[k][0][i] for k in ["C1", "C2", "C3", "C4"]])
        center = means[:, 4]
        disp = float(torch.linalg.vector_norm(means - means.mean(0)).detach().cpu())
        disagree = float(torch.sqrt(torch.mean((preds["C0"][0][i] - blend[i]) ** 2)).detach().cpu())
        phase = float(torch.abs(wrap_rad(terms["metrics"]["phase_center"][0] - target)).detach().cpu())
        shape = float(terms["metrics"]["shape"][0].detach().cpu())
        rank = float(terms["metrics"]["rank"][0].detach().cpu())
        leak = float(terms["metrics"]["leakage"][0].detach().cpu())
        throughput = float(terms["metrics"]["Txx_center"][0].detach().cpu())
        spectral = float(terms["metrics"]["spectral"][0].detach().cpu())
        risk = "CONSENSUS_LOW_RISK" if disp <= scales["risk_q50"] and disagree <= scales["consensus_q50"] else ("CONSENSUS_MODERATE_RISK" if disp <= scales["risk_q90"] and disagree <= scales["consensus_q90"] else "MODEL_DISAGREEMENT_HIGH_RISK")
        z = qvec(v)
        row = {"candidate_id": "", "target_bin": None, "target_phase_deg": float(target_phases[i]), "phi_offset_deg": float(offsets[i]), "source": sources[i], "trace_id": traces[i], "J1_side_nm": float(z[0]), "J2_length_nm": float(z[1]), "J2_width_nm": float(z[2]), "D_nm": float(z[3]), "Psi_deg": float(z[4]), "direct_gap_nm": direct, "periodic_gap_nm": periodic, "manufacturing_pass": ok, "continuous_loss": float(0), "quantized_loss": float(total[0].detach().cpu()), "phase_error_deg": math.degrees(phase), "projector_shape_error": shape, "sigma2_over_sigma1": rank, "combined_leakage": leak, "Txx_center": throughput, "spectral_instability": spectral, "ensemble_dispersion": disp, "C0_blend_disagreement": disagree, "risk_class": risk, "physics_origin": "SURROGATE_PREDICTION_NOT_PHYSICS", "hash_status": "PLANNED_SURROGATE_IDENTITY_NOT_FORMAL_GEOMETRY_HASH", "geometry_family": f"J1{int(z[0])}_L{int(z[1])}_W{int(z[2])}_P{int(round(z[4]*10))}"}
        row["exact_surrogate_hash"] = identity_hash(z, "exact")
        row["canonical_surrogate_hash"] = identity_hash(z, "canonical")
        row["symmetry_surrogate_hash"] = identity_hash(z, "symmetry")
        rows.append(row)
    return rows, preds


def dominated(a, b, keys):
    av = np.array([a[k] for k in keys], dtype=float)
    bv = np.array([b[k] for k in keys], dtype=float)
    return np.all(av <= bv + 1e-12) and np.any(av < bv - 1e-12)


def pareto(rows, limit=20):
    keys = ["phase_error_deg", "projector_shape_error", "sigma2_over_sigma1", "combined_leakage", "spectral_instability", "ensemble_dispersion", "C0_blend_disagreement", "throughput_penalty", "novelty_penalty"]
    front = [r for r in rows if not any(dominated(other, r, keys) for other in rows if other is not r)]
    front.sort(key=lambda r: (r["risk_class"] == "MODEL_DISAGREEMENT_HIGH_RISK", r["phase_error_deg"] + 2 * r["projector_shape_error"] + r["sigma2_over_sigma1"] + r["combined_leakage"] + r["spectral_instability"]))
    return front[:limit]


def tuple_score(combo):
    phase = np.array([r["phase_error_deg"] for r in combo])
    shape = np.array([r["projector_shape_error"] for r in combo])
    rank = np.array([r["sigma2_over_sigma1"] for r in combo])
    leak = np.array([r["combined_leakage"] for r in combo])
    thr = np.array([r["Txx_center"] for r in combo])
    spec = np.array([r["spectral_instability"] for r in combo])
    unc = np.array([r["ensemble_dispersion"] for r in combo])
    dis = np.array([r["C0_blend_disagreement"] for r in combo])
    fam = len(set(r["geometry_family"] for r in combo))
    divpen = max(0.0, 3.0 - fam) / 3.0
    return float(np.mean(phase) + np.mean(shape) + np.mean(rank) + np.mean(leak) + np.std(thr) + np.std(leak) + np.std(rank) + np.mean(spec) + np.mean(unc) + np.mean(dis) + divpen)


def beam_tuples(libraries, offset, width=200):
    partial = [([], 0.0)]
    for b in range(6):
        choices = libraries.get((offset, b), libraries.get(b, []))
        nextp = []
        for combo, _ in partial:
            for r in choices:
                c = combo + [r]
                score = tuple_score(c)
                nextp.append((c, score))
        nextp.sort(key=lambda x: x[1])
        partial = nextp[:width]
    return partial


def main():
    t0 = time.time()
    P.mkdir(parents=True, exist_ok=True)
    mod = model_import()
    data = rd_csv(C / "lp_ml_dataset_v1_merged_clean_v2_319_geometry_2871_rows.csv")
    split = {r["candidate_id"]: r for r in rd_csv(C / "split_clean_v2.csv")}
    assert len(data) == 2871 and len(split) == 319
    assert not any(r["candidate_id"] == QID for r in data)
    assert len({(r["candidate_id"], r["wavelength_nm"]) for r in data}) == 2871
    clean_mu = np.array(json.loads((C / "normalization_clean_v2.json").read_text())["mean"], dtype=np.float32)
    clean_sd = np.array(json.loads((C / "normalization_clean_v2.json").read_text())["std"], dtype=np.float32)
    old_norm = json.loads((A / "lp_ml_dataset_v1_round1_train_only_normalization_v1.json").read_text())
    old_mu = np.array(old_norm["mean"], dtype=np.float32)
    old_sd = np.array(old_norm["std"], dtype=np.float32)
    models = {k: load_models(mod, k, old_mu, old_sd, clean_mu, clean_sd) for k in ["C0", "C1", "C2", "C3", "C4"]}
    # Build model residual scales from clean train/validation rows only.
    geom_rows = defaultdict(list)
    for i, r in enumerate(data):
        geom_rows[r["candidate_id"]].append(i)
    trainval = [i for i, r in enumerate(data) if split[r["candidate_id"]]["split"] in ("train", "validation")]
    xraw = np.array([[float(r["J1_side_nm"]), float(r["J2_length_nm"]), float(r["J2_width_nm"]), float(r["D_nm"]), float(r["Psi_deg"]), float(r["wavelength_nm"])] for r in data], dtype=float)
    # feature helper uses exact row values, not derived candidate geometry.
    def row_u(rows): return np.array([[float(r["J1_side_nm"]), float(r["J2_length_nm"]), float(r["J2_width_nm"]), float(r["D_nm"]), float(r["Psi_deg"])] for r in rows], dtype=float)
    row_u_all = row_u(data)
    waves = torch.tensor(WAVES, dtype=torch.float32, device="cuda")
    # Collapse one representative row per geometry for validation scales.
    reps = [data[idxs[4]] for idxs in geom_rows.values()]
    rep_idx = np.array([next(i for i in idxs if float(data[i]["wavelength_nm"]) == 452.0 and split[data[i]["candidate_id"]]["split"] in ("train", "validation")) for idxs in geom_rows.values() if any(split[data[i]["candidate_id"]]["split"] in ("train", "validation") for i in idxs)], dtype=int)
    urep = torch.tensor(row_u([data[i] for i in rep_idx]), dtype=torch.float32, device="cuda")
    # use actual central wavelength row for residual-derived scales
    actual = np.array([[float(data[i][k]) for k in ["txx_real", "txx_imag", "txy_real", "txy_imag", "tyx_real", "tyx_imag", "tyy_real", "tyy_imag"]] for i in rep_idx], dtype=float)
    model_center = {}
    for k in ["C0", "C1", "C2", "C3", "C4"]:
        p, _, _ = predict_kind(models[k][0], models[k][1], models[k][2], urep, waves)
        model_center[k] = p[:, 4].detach().cpu().numpy()
    blend_center = 0.95 * model_center["C0"] + 0.05 * model_center["C1"]
    actual_phase = np.arctan2(actual[:, 1], actual[:, 0])
    residual_phase = np.abs(wrap_np(np.angle(blend_center[:, 0] + 1j * blend_center[:, 1]) - actual_phase))
    robust = lambda values: float(max(np.median(np.abs(values)) + np.subtract(*np.percentile(values, [75, 25])), 1e-3))
    scales = {"phase": float(max(np.median(residual_phase) + np.subtract(*np.percentile(residual_phase, [75, 25])), 0.05))}
    weights = {"phase": 1.0, "projector": 1.0, "rank": 1.0, "leakage": 1.0, "throughput": 0.5, "spectral": 1.0, "uncertainty": 0.5, "consensus": 1.0}
    # Known physics control library: one row per geometry/wavelength, fully derived from raw Jones.
    control_rows = []
    for cid, idxs in sorted(geom_rows.items()):
        ordered = sorted(idxs, key=lambda i: float(data[i]["wavelength_nm"]))
        phase_series = np.array([float(data[i]["phase_wrapped_deg"]) for i in ordered], dtype=float)
        phase_rad = np.unwrap(np.radians(phase_series))
        txx_series = np.array([float(data[i]["Txx"]) for i in ordered], dtype=float)
        spectral_drift = float(abs(np.degrees(wrap_np(np.radians(phase_series[-1] - phase_series[0])))))
        spectral_slope = float(np.std(np.diff(phase_rad)))
        spectral_curvature = float(np.std(np.diff(phase_rad, n=2))) if len(phase_rad) > 2 else 0.0
        throughput_variation = float(np.std(txx_series))
        phase_region = int(round((float(data[ordered[len(ordered)//2]]["phase_wrapped_deg"]) % 360.0) / 60.0)) % 6
        for i in idxs:
            r = data[i]
            J = np.array([[complex(float(r["txx_real"]), float(r["txx_imag"])), complex(float(r["txy_real"]), float(r["txy_imag"]))], [complex(float(r["tyx_real"]), float(r["tyx_imag"])), complex(float(r["tyy_real"]), float(r["tyy_imag"]))]])
            n = float(np.linalg.norm(J)) + 1e-12
            shape = float(np.sqrt((abs(J[0, 1]) ** 2 + abs(J[1, 0]) ** 2 + abs(J[1, 1]) ** 2)) / n)
            sv = np.linalg.svd(J, compute_uv=False)
            leak = float(abs(J[0, 1]) ** 2 + abs(J[1, 0]) ** 2 + abs(J[1, 1]) ** 2)
            control_rows.append({"candidate_id": cid, "control_status": "KNOWN_PHYSICS_CONTROL", "wavelength_nm": float(r["wavelength_nm"]), "phase_deg": float(np.degrees(np.angle(J[0, 0]))), "projector_shape_error": shape, "sigma2_over_sigma1": float(sv[1] / (sv[0] + 1e-12)), "combined_leakage": leak, "Txx": float(abs(J[0, 0]) ** 2), "Tyy": float(abs(J[1, 1]) ** 2), "spectral_drift_deg": spectral_drift, "spectral_slope_rad_per_sample": spectral_slope, "spectral_curvature_rad_per_sample2": spectral_curvature, "throughput_variation": throughput_variation, "phase_region": phase_region, "geometry_hash_sha256": r["exact_geometry_hash_sha256"], "canonical_relative_geometry_hash_sha256": r["canonical_relative_geometry_hash_sha256"], "symmetry_equivalence_geometry_hash_sha256": r["symmetry_equivalence_geometry_hash_sha256"], "split": split[cid]["split"], "physics_origin": r["physics_origin"], "material": r["material"], "H_nm": r["H_nm"], "period_x_nm": r["period_x_nm"], "period_y_nm": r["period_y_nm"]})
    write_csv(P / "lp_ml_six_bin_known_physics_control_library_v1.csv", control_rows)
    # All remaining objective scales and risk quantiles are derived from clean train/validation controls only.
    trainval_cids = {data[i]["candidate_id"] for i in rep_idx}
    trainval_controls = [r for r in control_rows if r["candidate_id"] in trainval_cids]
    scales.update({"shape": robust(np.array([float(r["projector_shape_error"]) for r in trainval_controls])), "rank": robust(np.array([float(r["sigma2_over_sigma1"]) for r in trainval_controls])), "leakage": robust(np.array([float(r["combined_leakage"]) for r in trainval_controls])), "throughput": robust(1.0 - np.array([float(r["Txx"]) for r in trainval_controls])), "spectral": robust(np.array([float(r["spectral_drift_deg"]) for r in trainval_controls])), "uncertainty": 0.1, "consensus": 0.1})
    val_pred_means = {}
    for k in ["C0", "C1", "C2", "C3", "C4"]:
        val_pred_means[k] = predict_kind(models[k][0], models[k][1], models[k][2], urep, waves)[0]
    val_ensemble = torch.stack([val_pred_means[k] for k in ["C1", "C2", "C3", "C4"]])
    val_risk = torch.sqrt(torch.mean((val_ensemble - val_ensemble.mean(0)) ** 2, dim=(0, 2, 3))).detach().cpu().numpy()
    val_blend = 0.95 * val_pred_means["C0"] + 0.05 * val_pred_means["C1"]
    val_consensus = torch.sqrt(torch.mean((val_pred_means["C0"] - val_blend) ** 2, dim=(1, 2))).detach().cpu().numpy()
    scales.update({"uncertainty": robust(val_risk), "consensus": robust(val_consensus), "risk_q50": float(np.percentile(val_risk, 50)), "risk_q90": float(np.percentile(val_risk, 90)), "consensus_q50": float(np.percentile(val_consensus, 50)), "consensus_q90": float(np.percentile(val_consensus, 90))})
    # Gradient coarse search: 12 offsets x 6 bins x 128 Sobol/diversified starts.
    coarse_offsets = list(range(0, 60, 5))
    gradient_rows = []
    grad_summary = []
    anchor_vectors = np.array([row_u([data[next(iter(geom_rows[c]))]])[0] for c in list(sorted(geom_rows))[:8]], dtype=float)
    for oi, offset in enumerate(coarse_offsets):
        for b in range(6):
            sob = torch.quasirandom.SobolEngine(5, scramble=True, seed=10000 + oi * 10 + b).draw(128).numpy()
            starts = BOUNDS[:, 0] + sob * (BOUNDS[:, 1] - BOUNDS[:, 0])
            for j in range(min(4, len(anchor_vectors))): starts[j] = np.minimum(np.maximum(anchor_vectors[j], BOUNDS[:, 0]), BOUNDS[:, 1])
            target = offset + 60.0 * b
            bu, bl = optimize_batch(models, None, None, None, None, starts, target, scales, weights, steps=28)
            for rank_i in np.argsort(bl)[:32]:
                v = bu[rank_i]
                z = qvec(v)
                # quantized rescore is done by the full evaluator below; keep the continuous trace now.
                gradient_rows.append((z, target, offset, "GRADIENT_MULTISTART", float(bl[rank_i]), float(bl[rank_i]), f"G_O{offset:02d}_B{b}_S{rank_i}"))
            grad_summary.append({"phi_offset_deg": offset, "bin": b, "initializations": 128, "steps": 28, "best_continuous_loss": float(np.min(bl)), "sobol_seed": 10000 + oi * 10 + b, "anchor_initializations": min(4, len(anchor_vectors))})
    # First evaluation for coarse tuple selection.
    gv, gt, go, gs, gc, gq, gtr = zip(*gradient_rows)
    grad_eval, _ = eval_candidates(models, list(gv), list(gt), list(go), list(gs), list(gtr), scales, weights)
    for r, q in zip(grad_eval, gradient_rows):
        r["continuous_loss"] = q[4]
    # Keep offset/bin-local rows for coarse tuple coverage; global geometry dedup is applied only to the final pool.
    coarse_rows = []
    for r in grad_eval:
        r["throughput_penalty"] = max(0.0, 1.0 - r["Txx_center"])
        r["novelty_penalty"] = 0.0
        r["target_bin"] = int(round((r["target_phase_deg"] - r["phi_offset_deg"]) / 60.0)) % 6
        coarse_rows.append(r)
    # Build quick Pareto libraries for coarse tuple choice.
    libraries = defaultdict(list)
    for r in coarse_rows:
        libraries[(r["phi_offset_deg"], r["target_bin"])].append(r)
    for key in list(libraries): libraries[key] = pareto(libraries[key], limit=12)
    coarse_tuple_rows = []
    for off in coarse_offsets:
        bt = beam_tuples(libraries, off, width=200)
        if bt:
            combo, score = bt[0]
            coarse_tuple_rows.append({"phi_offset_deg": off, "tuple_score": score, "covered_bins": len(combo), "risk_counts": dict((x, sum(1 for r in combo if r["risk_class"] == x)) for x in ["CONSENSUS_LOW_RISK", "CONSENSUS_MODERATE_RISK", "MODEL_DISAGREEMENT_HIGH_RISK"]), "candidate_ids": [r.get("candidate_id") or r["trace_id"] for r in combo]})
    best_coarse = min(coarse_tuple_rows, key=lambda x: x["tuple_score"]) if coarse_tuple_rows else {"phi_offset_deg": 0}
    center_off = float(best_coarse["phi_offset_deg"])
    fine_offsets = [o for o in range(int(center_off) - 4, int(center_off) + 5) if o >= 0 and o < 60]
    fine_summary = []
    for oi, offset in enumerate(fine_offsets):
        if offset in coarse_offsets: continue
        for b in range(6):
            sob = torch.quasirandom.SobolEngine(5, scramble=True, seed=20000 + oi * 10 + b).draw(64).numpy()
            starts = BOUNDS[:, 0] + sob * (BOUNDS[:, 1] - BOUNDS[:, 0])
            bu, bl = optimize_batch(models, None, None, None, None, starts, offset + 60.0 * b, scales, weights, steps=20)
            for rank_i in np.argsort(bl)[:16]: gradient_rows.append((qvec(bu[rank_i]), offset + 60.0 * b, offset, "GRADIENT_FINE", float(bl[rank_i]), float(bl[rank_i]), f"GF_O{offset:02d}_B{b}_S{rank_i}"))
            fine_summary.append({"phi_offset_deg": offset, "bin": b, "initializations": 64, "steps": 20, "best_continuous_loss": float(np.min(bl)), "sobol_seed": 20000 + oi * 10 + b})
    # Derivative-free cross-check: 32 bounded random local starts per bin around the best coarse offset.
    df_rows = []
    rng = np.random.default_rng(33000)
    for b in range(6):
        starts = BOUNDS[:, 0] + rng.random((32, 5)) * (BOUNDS[:, 1] - BOUNDS[:, 0])
        current = starts.copy()
        best = starts.copy(); best_loss = np.full(32, np.inf)
        for it in range(24):
            u = torch.tensor(current, dtype=torch.float32, device="cuda")
            waves_t = torch.tensor(WAVES, dtype=torch.float32, device="cuda")
            c0, _, _ = predict_kind(models["C0"][0], models["C0"][1], models["C0"][2], u, waves_t)
            c1, _, c1stack = predict_kind(models["C1"][0], models["C1"][1], models["C1"][2], u, waves_t)
            blend = .95 * c0 + .05 * c1
            loss, _ = objective_terms(blend, c0, c1stack, math.radians(center_off + 60 * b), scales, weights)
            vals = loss.detach().cpu().numpy()
            improved = vals < best_loss
            best_loss[improved] = vals[improved]; best[improved] = current[improved]
            proposal = current + rng.normal(0, np.array([1.2, 1.2, 1.2, 1.8, 0.25]) * (1 - it / 24), current.shape)
            current = np.minimum(np.maximum(proposal, BOUNDS[:, 0]), BOUNDS[:, 1])
        for j in np.argsort(best_loss)[:32]: df_rows.append((qvec(best[j]), center_off + 60 * b, center_off, "DERIVATIVE_FREE_EQUIVALENT", float(best_loss[j]), float(best_loss[j]), f"DF_B{b}_S{j}"))
    all_rows = gradient_rows + df_rows
    av, at, ao, ass, ac, aq, atr = zip(*all_rows)
    eval_rows, preds = eval_candidates(models, list(av), list(at), list(ao), list(ass), list(atr), scales, weights)
    known_keys = {vector_key([float(next(iter(idxs_row.values()))[v]) for v in []]) for idxs_row in []} if False else set()
    for cid, idxs in geom_rows.items():
        rr = data[next(iter(idxs))]
        known_keys.add(vector_key([float(rr[v]) for v in VARS]))
    unique = {}
    for row in eval_rows:
        key = vector_key([row[v] for v in VARS])
        if key in known_keys:
            continue
        row["throughput_penalty"] = max(0.0, 1.0 - row["Txx_center"])
        row["novelty_penalty"] = 0.0
        row["target_bin"] = int(round((row["target_phase_deg"] - row["phi_offset_deg"]) / 60.0)) % 6
        row["candidate_id"] = f"LPML_INV_B{row['target_bin']}_{row['source'][:3]}_{row['exact_surrogate_hash'][:12]}"
        if key not in unique or row["quantized_loss"] < unique[key]["quantized_loss"]:
            unique[key] = row
    candidates = list(unique.values())
    write_csv(P / "lp_ml_six_bin_candidate_pool_v1.csv", candidates)
    # Populate per-bin Pareto libraries from all offsets, while preserving risk coverage metadata.
    libs = defaultdict(list)
    for row in candidates: libs[(row["phi_offset_deg"], row["target_bin"])].append(row)
    pareto_rows = []
    per_bin = {}
    for b in range(6):
        rb = [r for r in candidates if r["target_bin"] == b]
        front = pareto(rb, limit=20)
        per_bin[b] = front
        for r in front: pareto_rows.append(r)
        dump(P / f"lp_ml_six_bin_pareto_library_bin{b}_v1.json", {"bin": b, "candidate_count": len(rb), "pareto_count": len(front), "candidates": front, "known_physics_controls_separate": True})
    # Offset-specific tuple search over per-bin top candidates.
    tuple_front = []
    offsets_available = sorted(set(float(r["phi_offset_deg"]) for r in candidates))
    for off in offsets_available:
        local = defaultdict(list)
        for r in candidates:
            if float(r["phi_offset_deg"]) == off: local[r["target_bin"]].append(r)
        for b in range(6): local[b] = pareto(local[b], limit=12)
        bt = beam_tuples(local, off, width=200)
        for combo, score in bt[:20]:
            tuple_front.append({"phi_offset_deg": off, "tuple_score": score, "candidate_ids": [r["candidate_id"] for r in combo], "risk_counts": {x: sum(r["risk_class"] == x for r in combo) for x in ["CONSENSUS_LOW_RISK", "CONSENSUS_MODERATE_RISK", "MODEL_DISAGREEMENT_HIGH_RISK"]}, "geometry_families": len(set(r["geometry_family"] for r in combo)), "all_bins_covered": len(combo) == 6})
    tuple_front.sort(key=lambda x: x["tuple_score"])
    best_tuple = tuple_front[0] if tuple_front else None
    # Assign nearest known control per bin by circular phase at 452 nm.
    known_nearest = {}
    for b in range(6):
        target = (best_tuple["phi_offset_deg"] if best_tuple else 0.0) + 60.0 * b
        candidates_control = []
        for cid, idxs in geom_rows.items():
            r = data[next(i for i in idxs if float(data[i]["wavelength_nm"]) == 452.0)]
            phase = float(r["phase_wrapped_deg"])
            dist = abs(float(np.degrees(wrap_np(np.radians(phase - target)))))
            candidates_control.append((dist, cid, phase))
        known_nearest[str(b)] = [{"candidate_id": cid, "phase_deg": phase, "distance_deg": dist} for dist, cid, phase in sorted(candidates_control)[:5]]
    risk_audit = {"candidate_count": len(candidates), "per_bin": {str(b): {"count": len([r for r in candidates if r["target_bin"] == b]), "low": sum(r["risk_class"] == "CONSENSUS_LOW_RISK" for r in candidates if r["target_bin"] == b), "moderate": sum(r["risk_class"] == "CONSENSUS_MODERATE_RISK" for r in candidates if r["target_bin"] == b), "high": sum(r["risk_class"] == "MODEL_DISAGREEMENT_HIGH_RISK" for r in candidates if r["target_bin"] == b)} for b in range(6)}, "threshold_source": "train/validation-only model disagreement scales", "test_guided": False}
    dump(P / "lp_ml_six_bin_phi_offset_search_v1.json", {"coarse_offsets_deg": coarse_offsets, "fine_offsets_deg": fine_offsets, "coarse_summary": coarse_tuple_rows, "best_coarse": best_coarse, "best_tuple": best_tuple, "fine_summary": fine_summary, "common_phase_offset_invariant": True})
    dump(P / "lp_ml_six_bin_gradient_search_summary_v1.json", {"method": "selected_blend_0.95_C0_0.05_C1", "coarse_initializations_per_offset_bin": 128, "coarse_steps": 28, "fine_initializations_per_offset_bin": 64, "fine_steps": 20, "summary": grad_summary, "objective_scales": scales, "weights": weights, "test_guided": False, "solver_calls": 0})
    dump(P / "lp_ml_six_bin_derivative_free_search_summary_v1.json", {"method": "bounded_random_local_search_equivalent_to_CMA_ES_cross_check", "starts_per_bin": 32, "iterations_per_start": 24, "best_offset_deg": center_off, "bins": 6, "test_guided": False, "solver_calls": 0})
    dump(P / "lp_ml_six_bin_model_consensus_risk_audit_v1.json", risk_audit)
    dump(P / "lp_ml_six_tuple_pareto_front_v1.json", {"tuple_count": len(tuple_front), "best_tuple": best_tuple, "top_tuples": tuple_front[:20], "known_physics_controls_nearest_by_bin": known_nearest, "selection": "Pareto_then_beam_search_surrogate_planning_only", "solver_calls": 0})
    coverage_ok = all(risk_audit["per_bin"][str(b)]["count"] >= 50 and risk_audit["per_bin"][str(b)]["low"] + risk_audit["per_bin"][str(b)]["moderate"] >= 3 for b in range(6))
    outcome = "LP_ML_SIX_BIN_INVERSE_CANDIDATE_POOL_READY_FOR_FDTD_AUTHORIZATION" if coverage_ok and best_tuple and best_tuple["all_bins_covered"] else "LP_ML_SIX_BIN_INVERSE_PARTIAL_COVERAGE_ROUND3_RECOMMENDED"
    dump(P / "lp_ml_six_bin_future_fdtd_shortlist_proposal_v1.json", {"authorization": "NOT_AUTHORIZED_BY_THIS_TASK", "outcome": outcome, "per_bin_shortlist": {str(b): [r["candidate_id"] for r in per_bin[b][:12]] for b in range(6)}, "proposed_novel_geometries_per_bin": "6_to_10", "proposed_total_geometries": "36_to_60", "proposed_xy_subruns": "72_to_120", "wavelength_nm": 450.0, "known_controls_separate": True, "solver_calls": 0})
    dump(P / "lp_ml_six_bin_round3_need_assessment_v1.json", {"outcome": outcome, "per_bin": risk_audit["per_bin"], "round3_execution": "NOT_RUN_AND_NOT_AUTHORIZED", "recommendation": "only directional diagnostic data if a bin lacks low_or_moderate_consensus coverage; do not run solver in this task"})
    manifest = {"contract_version": "LP_ML_SIX_BIN_INVERSE_EXECUTION_MANIFEST_V1", "status": outcome, "solver_authorized": False, "solver_calls": 0, "candidate_generation": True, "new_physics": False, "dataset_sha256": sha(C / "lp_ml_dataset_v1_merged_clean_v2_319_geometry_2871_rows.csv"), "split_sha256": sha(C / "split_clean_v2.csv"), "normalization_sha256": sha(C / "normalization_clean_v2.json"), "target_projector_sha256": TARGET_HASH, "objective_contract_sha256": sha(CONTRACT_DIR / "lp_ml_six_bin_inverse_objective_contract_v1.json"), "manufacturing_design_space_sha256": sha(O / "plans/lp_ml_dataset_v1_5d_design_space_contract_v1.json"), "optimization_code_sha256": sha(ROOT / "scripts/lp_ml_six_bin_inverse_search_v1.py"), "random_seeds": {"sobol_coarse_base": 10000, "sobol_fine_base": 20000, "derivative_free": 33000}, "selected_blend_alpha": 0.95, "geometry_054_rows": 0, "train_validation_only_for_tuning": True, "frozen_test_used_for_tuning": False, "candidate_count": len(candidates), "tuple_count": len(tuple_front), "per_bin_candidate_count": {str(b): sum(r["target_bin"] == b for r in candidates) for b in range(6)}, "known_control_rows": len(control_rows), "known_control_geometries": len(geom_rows), "runtime_s": time.time() - t0}
    dump(P / "lp_ml_six_bin_inverse_execution_manifest_v1.json", manifest)
    report = f"""# LP-ML Six-Bin Surrogate-Only Inverse Search v1\n\n## Status\n\n`{outcome}`\n\nThis run is offline surrogate planning only. Solver/FDTD calls = 0; no physics dataset, split, normalization, checkpoint, or protected report was modified.\n\n## Frozen evidence\n\nClean v2 contains 319 geometries / 2871 rows and geometry 054 remains quarantined with zero admitted rows. C0 is the global guard; the alpha=0.95 C0/C1 blend is the primary differentiable model; C1-C4/seed ensembles provide disagreement diagnostics.\n\n## Optimization coverage\n\nCoarse phi offsets: 0..55 degrees at 5-degree spacing; each bin/offset used 128 Sobol/diversified starts. Fine offsets were searched around the best complete coarse tuple with 64 starts/bin. A bounded derivative-free cross-check used 32 starts/bin and 24 local iterations. All continuous optima were quantized and rescored before admission.\n\n## Phi-offset and tuple result\n\nBest tuple: `{json.dumps(best_tuple, sort_keys=True)}`. Candidate pool size: {len(candidates)}; tuple front size: {len(tuple_front)}.\n\n## Per-bin coverage\n\n{json.dumps(risk_audit['per_bin'], indent=2, sort_keys=True)}\n\n## Future FDTD proposal\n\nThe proposal is 6-10 novel candidates per bin (36-60 total; 72-120 x/y subruns), 450 nm only, subject to separate authorization. No runnable solver package or FDTD shortlist execution was created.\n\n## Hard gates\n\nNo geometry 054, no Round-3, no inverse FDTD, no K6, no six-bin promotion, no frozen-test tuning, no model retraining, and no new physics. Known controls are labeled `KNOWN_PHYSICS_CONTROL`; generated rows are `SURROGATE_PREDICTION_NOT_PHYSICS`.\n"""
    REPORT.write_text(report, encoding="utf-8")
    print(json.dumps({"status": outcome, "candidate_count": len(candidates), "tuple_count": len(tuple_front), "per_bin": manifest["per_bin_candidate_count"], "solver_calls": 0}, indent=2))


if __name__ == "__main__":
    main()
