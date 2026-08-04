"""Freeze the authorized Round-3 64-point plan and pre-solver predictions.

This is an offline planning artifact.  It never imports lumapi or starts a
solver.  The model loader is reused only for prospective surrogate outputs.
"""
from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import math
import subprocess
from pathlib import Path

import numpy as np
import torch

ROOT = Path(r"D:\project\worktrees\blue_apcd_lp_stage11_4")
O = ROOT / "outputs/lp_ml_dataset_v1"
P = O / "plans"
A = O / "analysis"
SEARCH = P / "lp_ml_six_bin_inverse_search_v1"
POOL = SEARCH / "lp_ml_six_bin_candidate_pool_v1.csv"
TUPLE = SEARCH / "lp_ml_six_tuple_pareto_front_v1.json"
MERGED = O / "clean_v2/lp_ml_dataset_v1_merged_clean_v2_319_geometry_2871_rows.csv"
SPLIT = O / "clean_v2/split_clean_v2.csv"
NORM = O / "clean_v2/normalization_clean_v2.json"
QUAR = O / "clean_v2/quarantine_manifest_v2.json"
MODEL_FREEZE = A / "lp_ml_round2_clean_recompetition_checksums_v2.json"
OUT_PLAN = P / "lp_ml_dataset_v1_round3_64_candidate_plan_v1.csv"
OUT_PLAN_JSON = P / "lp_ml_dataset_v1_round3_64_candidate_plan_v1.json"
OUT_PRED = A / "lp_ml_round3_pre_retrain_prospective_predictions_v1.json"
OUT_PRED_CSV = A / "lp_ml_round3_pre_retrain_prospective_predictions_v1.csv"
OUT_AUDIT = A / "lp_ml_round3_selection_audit_v1.json"
OUT_CONTRACT = P / "lp_ml_dataset_v1_round3_execution_contract_v1.json"
WAVES = [450.0 + 0.5 * i for i in range(9)]
SEEDS = [11, 22, 33, 44, 55]


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def dump(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def read_csv(path: Path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def geometry_hashes(row):
    j1 = int(round(float(row["J1_side_nm"])))
    l2 = int(round(float(row["J2_length_nm"])))
    w2 = int(round(float(row["J2_width_nm"])))
    d = float(row["D_nm"])
    psi = float(row["Psi_deg"])
    ax = d * math.cos(math.radians(psi)) / 2.0
    ay = d * math.sin(math.radians(psi)) / 2.0
    geom = {
        "J1_side_nm": j1, "J2_length_nm": l2, "J2_width_nm": w2,
        "D_nm": d, "Psi_deg": psi,
        "J1_center_x_nm": -ax, "J1_center_y_nm": -ay,
        "J2_center_x_nm": ax, "J2_center_y_nm": ay,
        "H_nm": 500.0, "period_x_nm": 432.0, "period_y_nm": 432.0,
        "material": "APCD_TIO2_NATIVE_M1",
    }
    exact = sha_bytes(json.dumps(geom, sort_keys=True, separators=(",", ":")).encode())
    canon = sha_bytes(json.dumps({
        "J1_side_nm": j1, "J2_length_nm": l2, "J2_width_nm": w2,
        "D_nm": round(d, 6), "Psi_abs_deg": round(abs(psi), 6),
    }, sort_keys=True, separators=(",", ":")).encode())
    sym = sha_bytes(json.dumps({
        "J1_side_nm": j1, "J2_length_nm": l2, "J2_width_nm": w2,
        "D_nm": round(d, 6), "Psi_abs_deg": round(abs(psi), 6), "axis_swap": False,
    }, sort_keys=True, separators=(",", ":")).encode())
    return geom, exact, canon, sym


def model_import():
    path = ROOT / "scripts/lp_ml_round2_clean_recompetition_v2.py"
    spec = importlib.util.spec_from_file_location("lp_round2_recompetition", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_model_pack(mod, kind, old_mu, old_sd, clean_mu, clean_sd):
    if kind == "C0":
        root = O / "model_runtime_round1_frozen_v1"
        mu, sd = old_mu, old_sd
    else:
        root = O / "clean_v2/model_runtime_recompetition_v2" / kind
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
    b = u.shape[0]
    w = waves.to(u.device).view(1, -1).expand(b, -1)
    psi = torch.deg2rad(u[:, 4:5]).expand(-1, w.shape[1])
    return torch.stack([
        u[:, 0:1].expand(-1, w.shape[1]), u[:, 1:2].expand(-1, w.shape[1]),
        u[:, 2:3].expand(-1, w.shape[1]), u[:, 3:4].expand(-1, w.shape[1]),
        torch.sin(psi), torch.cos(psi), w,
    ], dim=-1)


def predict(pack, u, waves):
    models, mu, sd, _ = pack
    x = ((feature_tensor(u, waves) - mu) / sd).reshape(-1, 7)
    vals = [m(x).reshape(u.shape[0], len(waves), 8) for m in models]
    stack = torch.stack(vals)
    return stack.mean(0), stack


def phase_and_metrics(arr):
    j = np.asarray(arr, dtype=float)
    z = j[..., 0] + 1j * j[..., 1]
    x = j[..., 2] + 1j * j[..., 3]
    y = j[..., 4] + 1j * j[..., 5]
    yy = j[..., 6] + 1j * j[..., 7]
    phase = np.degrees(np.angle(z))
    mat = np.stack([np.stack([z, x], axis=-1), np.stack([y, yy], axis=-1)], axis=-2)
    sv = np.linalg.svd(mat, compute_uv=False)
    power = np.abs(mat) ** 2
    return {
        "phase_deg": phase.tolist(),
        "phase_center_deg": float(phase[4]),
        "Txx": np.abs(z).astype(float).tolist(),
        "Tyy": np.abs(yy).astype(float).tolist(),
        "leakage": (np.abs(x) ** 2 + np.abs(y) ** 2 + np.abs(yy) ** 2).astype(float).tolist(),
        "cross_power": (np.abs(x) ** 2 + np.abs(y) ** 2).astype(float).tolist(),
        "sigma2_over_sigma1": (sv[..., 1] / np.maximum(sv[..., 0], 1e-12)).astype(float).tolist(),
        "projection_error": (1.0 - np.abs(z) ** 2 / np.maximum(np.sum(np.abs(mat) ** 2, axis=(-2, -1)), 1e-12)).astype(float).tolist(),
        "throughput": np.abs(z).astype(float).tolist(),
        "spectral_slope_deg": np.diff(np.unwrap(np.radians(phase))).astype(float).tolist(),
    }


def main():
    required = [POOL, TUPLE, MERGED, SPLIT, NORM, QUAR]
    missing = [str(p) for p in required if not p.exists()]
    if missing:
        raise SystemExit("SOURCE_GATE_MISSING:" + ",".join(missing))
    pool = read_csv(POOL)
    merged = read_csv(MERGED)
    existing_exact = {r.get("exact_geometry_hash_sha256") for r in merged}
    existing_canon = {r.get("canonical_relative_geometry_hash_sha256") for r in merged}
    existing_sym = {r.get("symmetry_equivalence_geometry_hash_sha256") for r in merged}
    if len({r.get("candidate_id") for r in merged}) != 319 or len(merged) != 2871:
        raise SystemExit("CLEAN_SOURCE_GATE")
    clean = []
    for p in pool:
        if "LPML_R1_GLOBAL_SOBOL_054" in p.get("candidate_id", ""):
            continue
        geom, exact, canon, sym = geometry_hashes(p)
        if exact in existing_exact or canon in existing_canon or sym in existing_sym:
            continue
        z = dict(p)
        z.update(geom)
        z["exact_geometry_hash_sha256"] = exact
        z["canonical_relative_geometry_hash_sha256"] = canon
        z["symmetry_equivalence_geometry_hash_sha256"] = sym
        z["direct_gap_nm"] = float(z["D_nm"]) - 0.5 * (float(z["J1_side_nm"]) + float(z["J2_length_nm"]))
        z["periodic_gap_nm"] = 432.0 - float(z["D_nm"]) - 0.5 * (float(z["J1_side_nm"]) + float(z["J2_length_nm"]))
        z["nearest_physics_distance"] = 0.0
        clean.append(z)
    if len(clean) < 64:
        raise SystemExit(f"UNIQUE_POOL_TOO_SMALL:{len(clean)}")
    # Score is frozen and deterministic.  Families are interleaved so every
    # requested bin covers distinct quantized geometry families where possible.
    for z in clean:
        z["family"] = z.get("geometry_family", f"J{int(float(z['J1_side_nm']))}_L{int(float(z['J2_length_nm']))}_W{int(float(z['J2_width_nm']))}_P{round(float(z['Psi_deg']), 1)}")
        z["disagreement_score"] = float(z.get("C0_blend_disagreement", 0.0))
        z["dispersion_score"] = float(z.get("ensemble_dispersion", 0.0))
        z["acq_score"] = float(z["disagreement_score"] + z["dispersion_score"] + 0.001 * float(z.get("phase_error_deg", 0.0)))
    selected = []
    used = set()
    used_canon = set()
    used_sym = set()
    quotas = {0: 8, 1: 8, 2: 8, 3: 12, 4: 12, 5: 12}
    def choose(rows, n, category):
        rows = sorted(rows, key=lambda z: (-z["acq_score"], z["candidate_id"]))
        got = []
        families = set()
        # First pass: family diversity, then high acquisition value.
        for z in rows:
            if len(got) >= n:
                break
            key = z["exact_geometry_hash_sha256"]
            if key in used or z["canonical_relative_geometry_hash_sha256"] in used_canon or z["symmetry_equivalence_geometry_hash_sha256"] in used_sym:
                continue
            if z["family"] in families and len(families) < 3:
                continue
            got.append(z); used.add(key); used_canon.add(z["canonical_relative_geometry_hash_sha256"]); used_sym.add(z["symmetry_equivalence_geometry_hash_sha256"]); families.add(z["family"])
        for z in rows:
            if len(got) >= n:
                break
            if z["exact_geometry_hash_sha256"] not in used and z["canonical_relative_geometry_hash_sha256"] not in used_canon and z["symmetry_equivalence_geometry_hash_sha256"] not in used_sym:
                got.append(z); used.add(z["exact_geometry_hash_sha256"]); used_canon.add(z["canonical_relative_geometry_hash_sha256"]); used_sym.add(z["symmetry_equivalence_geometry_hash_sha256"]); families.add(z["family"])
        for z in got:
            z["category"] = category
        return got
    for b, n in quotas.items():
        got = choose([z for z in clean if int(float(z["target_bin"])) == b], n, f"B{b}_TARGETED_ACTIVE_LEARNING")
        if len(got) != n:
            raise SystemExit(f"BIN_QUOTA_GATE:B{b}:{len(got)}")
        selected.extend(got)
    # Four controls: two tuple-neighbour rows and two low-disagreement maximin
    # rows.  We use source/trace hints from the frozen tuple, never test data.
    tuple_obj = json.loads(TUPLE.read_text(encoding="utf-8"))
    tuple_ids = set(tuple_obj.get("best_tuple", {}).get("candidate_ids", []))
    remaining = [z for z in clean if z["exact_geometry_hash_sha256"] not in used and z["canonical_relative_geometry_hash_sha256"] not in used_canon and z["symmetry_equivalence_geometry_hash_sha256"] not in used_sym]
    tuple_rows = [z for z in remaining if z.get("candidate_id") in tuple_ids]
    tuple_rows.sort(key=lambda z: (-z["acq_score"], z["candidate_id"]))
    controls = []
    for z in tuple_rows[:2]:
        z["category"] = "TUPLE_NEIGHBOR_CONTROL"; controls.append(z); used.add(z["exact_geometry_hash_sha256"]); used_canon.add(z["canonical_relative_geometry_hash_sha256"]); used_sym.add(z["symmetry_equivalence_geometry_hash_sha256"])
    remaining = [z for z in remaining if z["exact_geometry_hash_sha256"] not in used and z["canonical_relative_geometry_hash_sha256"] not in used_canon and z["symmetry_equivalence_geometry_hash_sha256"] not in used_sym]
    remaining.sort(key=lambda z: (z["disagreement_score"] + z["dispersion_score"], z["candidate_id"]))
    while len(controls) < 4 and remaining:
        if not controls:
            z = remaining.pop(0)
        else:
            def d2(q):
                a = np.array([float(q[k]) for k in ["J1_side_nm", "J2_length_nm", "J2_width_nm", "D_nm", "Psi_deg"]])
                vals = []
                for c in controls + selected:
                    b = np.array([float(c[k]) for k in ["J1_side_nm", "J2_length_nm", "J2_width_nm", "D_nm", "Psi_deg"]])
                    vals.append(float(np.linalg.norm((a - b) / np.array([4, 4, 4, 8, 1]))))
                return min(vals)
            z = max(remaining, key=lambda q: (d2(q), -q["disagreement_score"], q["candidate_id"]))
            remaining.remove(z)
            z["category"] = "LOW_DISAGREEMENT_MAXIMIN_CONTROL"; controls.append(z); used.add(z["exact_geometry_hash_sha256"]); used_canon.add(z["canonical_relative_geometry_hash_sha256"]); used_sym.add(z["symmetry_equivalence_geometry_hash_sha256"])
    if len(controls) != 4:
        raise SystemExit("CONTROL_QUOTA_GATE")
    selected.extend(controls)
    selected.sort(key=lambda z: (z["category"], int(float(z.get("target_bin", -1))), z["candidate_id"]))
    # Stable IDs and plan fields.
    for i, z in enumerate(selected, 1):
        z["candidate_id"] = f"LPML_R3_{i:03d}"
        z["candidate_order"] = i
        z["solver_status"] = "PLANNED_NOT_RUN"
        z["physics_status"] = "ABSENT_NOT_SIMULATED"
        z["prediction_status"] = "MODEL_PREDICTION_NOT_PHYSICS_LABEL"
        z["physics_origin"] = "ROUND3_PRE_RETRAIN_PROSPECTIVE_EVIDENCE"
        z["round3_identity"] = "ROUND3_TARGETED_ACTIVE_LEARNING_GEOMETRY"
        z["wavelength_authorization"] = "450.0-454.0_nm_step_0.5_nm"
        z["run_polarizations"] = "x,y"
        z["geometry_054_excluded"] = True
        z["no_replacement"] = True
        z["material"] = "APCD_TIO2_NATIVE_M1"
    if len(selected) != 64 or len({z["exact_geometry_hash_sha256"] for z in selected}) != 64 or len({z["canonical_relative_geometry_hash_sha256"] for z in selected}) != 64 or len({z["symmetry_equivalence_geometry_hash_sha256"] for z in selected}) != 64:
        raise SystemExit("ROUND3_IDENTITY_GATE")
    mod = model_import()
    # Reuse the exact clean train-only normalization and model loader from the
    # existing search implementation.
    old_norm = json.loads((A / "lp_ml_dataset_v1_round1_train_only_normalization_v1.json").read_text(encoding="utf-8"))
    clean_norm = json.loads(NORM.read_text(encoding="utf-8"))
    old_mu = old_norm["mean"]; old_sd = old_norm["std"]
    clean_mu = clean_norm["mean"]; clean_sd = clean_norm["std"]
    packs = {k: load_model_pack(mod, k, old_mu, old_sd, clean_mu, clean_sd) for k in ["C0", "C1", "C2", "C3", "C4"]}
    u = torch.tensor([[float(z["J1_side_nm"]), float(z["J2_length_nm"]), float(z["J2_width_nm"]), float(z["D_nm"]), float(z["Psi_deg"])] for z in selected], dtype=torch.float32, device="cuda")
    waves = torch.tensor(WAVES, dtype=torch.float32, device="cuda")
    means = {}; stacks = {}; checkpoint_hashes = {}
    for k, pack in packs.items():
        mean, stack = predict(pack, u, waves)
        means[k] = mean.detach().cpu().numpy(); stacks[k] = stack.detach().cpu().numpy()
        checkpoint_hashes[k] = [sha(p) for p in pack[3]]
    blend = 0.95 * means["C0"] + 0.05 * means["C1"]
    pred_rows = []
    for i, z in enumerate(selected):
        z["model_risk_class"] = str(z.get("risk_class", "MODEL_DISAGREEMENT_HIGH_RISK"))
        z["five_seed_dispersion"] = float(np.std(stacks["C1"][..., i, :, :], axis=0).mean())
        z["C0_blend_disagreement"] = float(np.sqrt(np.mean((means["C0"][i] - blend[i]) ** 2)))
        z["C0_prediction"] = means["C0"][i].tolist()
        z["selected_blend_prediction"] = blend[i].tolist()
        z["C1_prediction"] = means["C1"][i].tolist(); z["C2_prediction"] = means["C2"][i].tolist(); z["C3_prediction"] = means["C3"][i].tolist(); z["C4_prediction"] = means["C4"][i].tolist()
        z["C0_metrics"] = phase_and_metrics(means["C0"][i])
        z["selected_blend_metrics"] = phase_and_metrics(blend[i])
        z["C1_to_C4_seed_dispersion"] = float(np.std(stacks["C1"][..., i, :, :], axis=0).mean())
        for k in ["C0", "C1", "C2", "C3", "C4"]:
            z[f"{k}_checkpoint_sha256"] = checkpoint_hashes[k]
        for widx, wl in enumerate(WAVES):
            q = {"candidate_id": z["candidate_id"], "candidate_order": z["candidate_order"], "target_bin": z.get("target_bin"), "category": z["category"], "wavelength_nm": wl, "physics_origin": "ROUND3_PRE_RETRAIN_PROSPECTIVE_EVIDENCE", "prediction_status": "MODEL_PREDICTION_NOT_PHYSICS_LABEL"}
            for k in ["C0", "C1", "C2", "C3", "C4"]:
                q[k] = means[k][i, widx].tolist()
            q["selected_blend"] = blend[i, widx].tolist(); pred_rows.append(q)
    source_hashes = {str(p.relative_to(ROOT)).replace("\\", "/"): sha(p) for p in required + [SPLIT, NORM, MODEL_FREEZE] if p.exists()}
    plan_rows = []
    for z in selected:
        row = {k: v for k, v in z.items() if not isinstance(v, (list, dict))}
        plan_rows.append(row)
    write_csv(OUT_PLAN, plan_rows)
    plan_hash = sha(OUT_PLAN)
    contract = {"version": "LP_ML_ROUND3_EXECUTION_V1", "attempt_id": "LP_ML_ROUND3_TARGETED_ACTIVE_LEARNING_ATTEMPT1_V1", "plan_path": str(OUT_PLAN.relative_to(ROOT)).replace("\\", "/"), "plan_sha256": plan_hash, "candidate_count": 64, "max_solver_subruns": 128, "wavelengths_nm": WAVES, "only_input_polarizations": ["x", "y"], "physics_contract": "formal broadband Native-M1 weighted-G0; transmission field monitor z=1000 nm; endpoint deduplication; periodic reclosure; sqrt(T)/norm(weighted Ex,Ey)", "material": "APCD_TIO2_NATIVE_M1", "H_nm": 500.0, "period_nm": 432.0, "geometry_054_excluded": True, "failure_policy": "ISOLATED_ENTERED_FAILURE_QUARANTINE_AND_CONTINUE_V1", "no_replacement": True, "no_round4": True, "no_inverse_fdtd": True, "pre_retrain_prediction_path": str(OUT_PRED.relative_to(ROOT)).replace("\\", "/"), "selection_frozen_before_solver": True, "solver_calls_at_freeze": 0}
    dump(OUT_CONTRACT, contract)
    pred_obj = {"version": "LP_ML_ROUND3_PRE_RETRAIN_PROSPECTIVE_EVIDENCE_V1", "prediction_status": "ROUND3_PRE_RETRAIN_PROSPECTIVE_EVIDENCE", "candidate_count": 64, "wavelengths_nm": WAVES, "model_roles": ["C0", "SELECTED_BLEND_ALPHA_0P95", "C1", "C2", "C3", "C4"], "selected_blend_alpha": 0.95, "checkpoint_hashes": checkpoint_hashes, "source_hashes": source_hashes, "plan_sha256": plan_hash, "rows": pred_rows}
    dump(OUT_PRED, pred_obj); write_csv(OUT_PRED_CSV, pred_rows)
    dump(OUT_AUDIT, {"candidate_count": 64, "quotas": {"B0": 8, "B1": 8, "B2": 8, "B3": 12, "B4": 12, "B5": 12, "controls": 4}, "category_counts": {k: sum(z["category"] == k for z in selected) for k in sorted({z["category"] for z in selected})}, "unique_exact": 64, "unique_canonical": 64, "unique_symmetry": 64, "existing_geometry_count": 319, "geometry_054_excluded": True, "solver_calls": 0, "selection_frozen_before_solver": True, "source_hashes": source_hashes, "plan_sha256": plan_hash, "pre_retrain_predictions_sha256": sha(OUT_PRED), "tuple_front_sha256": sha(TUPLE), "candidate_pool_sha256": sha(POOL), "status": "PLANNED_AND_PREDICTIONS_FROZEN"})
    print(json.dumps({"selected": 64, "plan_sha256": plan_hash, "predictions_sha256": sha(OUT_PRED), "contract_sha256": sha(OUT_CONTRACT), "device": torch.cuda.get_device_name(0)}, indent=2))


if __name__ == "__main__":
    main()
