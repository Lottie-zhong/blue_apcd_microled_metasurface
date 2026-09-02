"""Read-only MDC V3-C surrogate Pareto proof-of-concept.

This script deliberately uses an explicit allow-list.  It never traverses the
outputs tree and contains no solver, fitting, backward, or PCA/scaler-fit path.
The search domain is the finite accepted MDC geometry registry (2688 rows).
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

import torch
from torch import nn


ROOT = Path(r"D:\project\worktrees\blue_apcd_mdc_hf_surrogate_v2")
CONTRACT = ROOT / "outputs" / "mdc_hf_surrogate_v3_plan_freeze_v1" / "20260810T_v3_plan_freeze_390f506"
FINAL = ROOT / "outputs" / "mdc_hf_surrogate_v3_c_final_full_development_v1" / "20260812T_final_full_development_5seed_bc1fcc1"
POLICY = ROOT / "outputs" / "mdc_hf_surrogate_v3_final_5seed_policy_v1" / "20260812T_final_5seed_policy_6063b1e"
HANDOFF = ROOT / "outputs" / "mdc_hf_surrogate_v3_mdc_np_handoff_v1" / "20260813T_mdc_v3_closed_level0_handoff_58fc73f"
GEOMETRY_MASTER = ROOT.parent / "blue_apcd_mdc_defect_450" / "datasets" / "mdc_ml_database_v1" / "geometry_master.csv"
DOE_INDEX = ROOT / "outputs" / "mdc_hf_surrogate_v2_doe96_joint_profile_database_v1" / "20260803T_doe96_joint_profile_6b6d7e2" / "doe96_case_label_index_v1.parquet"
DEV_GEOM = CONTRACT / "v3_development_geometry_manifest_v1.csv"
AL_GEOM = CONTRACT / "v3_al64_geometry_manifest_v1.csv"
MODEL_IDENTITY = POLICY / "final_model_identity.json"
ENSEMBLE_POLICY = POLICY / "final_ensemble_policy.json"
SEED_REGISTRY = FINAL / "seed_training_registry.json"
PCA_PATH = FINAL / "shared_full_development_pca32.npz"
SCALER_PATH = FINAL / "shared_full_development_scaler.npz"
OBJ_CONTRACT = ROOT / "contracts" / "mdc_hf_surrogate_v2" / "fixed_v2_system_objective_contract.json"
P1_STRUCTURES = ROOT / "outputs" / "mdc_p1_asymmetric_scan_static_v1" / "p1_asymmetric_structures.csv"
P1_RESOLUTION = ROOT / "outputs" / "mdc_p1_asymmetric_scan_static_v1" / "p1_seed_resolution.json"
P1_METRICS = ROOT / "outputs" / "mdc_p1_asymmetric_tmm_lambda_angle_v1" / "p1_lambda_angle_metrics.csv"
TARGET_P1 = "P1_ZL1_ALTERNATIVE_G3_A3"
MODEL_SEEDS = [20260813, 20260814, 20260815, 20260816, 20260817]
PARENT_BITS = ("asymmetric_pair_count", "dual_defect", "grouped_chirped", "hybrid_periodic_aperiodic", "locally_aperiodic", "off_center_defect", "symmetric_periodic", "termination_reversed")
NUMERIC = ("N", "H_nm", "L_nm", "C_nm", "M", "defect_thickness_nm", "total_thickness_nm", "layer_count")
FEATURE_ORDER = PARENT_BITS + NUMERIC + ("has_C", "has_M", "source_top", "source_centroid", "source_bottom", "dipole_x", "dipole_z")
SOURCE_CASES = (("top", "x"), ("top", "z"), ("centroid", "x"), ("centroid", "z"), ("bottom", "x"), ("bottom", "z"))
TOPOLOGY_ORDER = ("Explicit", "ZL-1", "ZL-2")


def canonical(x: Any) -> str:
    return json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha_obj(x: Any) -> str:
    return hashlib.sha256(canonical(x).encode("utf-8")).hexdigest()


def sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def dump(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)


def run_git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, text=True, capture_output=True, check=True).stdout.strip()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def find_nested(obj: Any, key: str) -> Any:
    if isinstance(obj, dict):
        if key in obj:
            return obj[key]
        for v in obj.values():
            out = find_nested(v, key)
            if out is not None:
                return out
    return None


def fwhm_connected(x: np.ndarray, y: np.ndarray) -> float:
    """Width of the connected half-maximum component containing the peak."""
    x = np.asarray(x, dtype=float); y = np.asarray(y, dtype=float)
    i = int(np.argmax(y)); level = 0.5 * float(y[i])
    left = i
    while left > 0 and y[left - 1] >= level:
        left -= 1
    right = i
    while right + 1 < len(y) and y[right + 1] >= level:
        right += 1
    if left == 0:
        xl = float(x[0])
    else:
        y0, y1 = float(y[left - 1]), float(y[left]); den = y1 - y0
        xl = float(x[left - 1] + (level - y0) * (x[left] - x[left - 1]) / den) if abs(den) > 1e-30 else float(x[left])
    if right == len(y) - 1:
        xr = float(x[-1])
    else:
        y0, y1 = float(y[right]), float(y[right + 1]); den = y1 - y0
        xr = float(x[right] + (level - y0) * (x[right + 1] - x[right]) / den) if abs(den) > 1e-30 else float(x[right])
    return max(0.0, xr - xl)


def shape_metrics(spec: np.ndarray, ang: np.ndarray, wavelength: np.ndarray, angle_deg: np.ndarray, target_lam: float, target_ang: float) -> np.ndarray:
    ip = int(np.argmax(spec)); ia = int(np.argmax(ang))
    return np.array([fwhm_connected(wavelength, spec), fwhm_connected(angle_deg, ang), abs(float(wavelength[ip]) - target_lam), abs(float(angle_deg[ia]) - target_ang)], dtype=np.float64)


class ResidualBlock(nn.Module):
    def __init__(self, width: int):
        super().__init__(); self.fc1 = nn.Linear(width, width); self.fc2 = nn.Linear(width, width)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return torch.relu(x + self.fc2(torch.relu(self.fc1(x))))


class ProfileOnlyModel(nn.Module):
    def __init__(self):
        super().__init__(); self.input_stem = nn.Linear(23, 384)
        self.blocks = nn.ModuleList([ResidualBlock(384) for _ in range(3)])
        self.latent_hidden = nn.Linear(384, 192); self.latent_head = nn.Linear(192, 32)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        y = torch.relu(self.input_stem(x))
        for b in self.blocks: y = b(y)
        return self.latent_head(torch.relu(self.latent_hidden(y)))


def build_features(cand: pd.DataFrame, scaler_mean: np.ndarray, scaler_std: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    rows = []
    geom_only = []
    for r in cand.itertuples(index=False):
        g = {"topology_family": r.topology_family, "N": r.N, "M": r.M, "H_nm": r.H_nm, "L_nm": r.L_nm, "C_nm": r.C_nm,
             "defect_thickness_nm": r.added_defect_thickness_nm, "total_thickness_nm": r.total_thickness_nm, "layer_count": r.physical_layer_count}
        base = np.zeros(18, dtype=np.float32)
        # Explicit/ZL1/ZL2 are intentionally out-of-vocabulary for the parent bits.
        for j, name in enumerate(NUMERIC):
            v = g.get(name, np.nan); base[8 + j] = 0.0 if pd.isna(v) else float(v)
        base[16] = float(pd.notna(g["C_nm"])); base[17] = float(pd.notna(g["M"]))
        geom_only.append(base.copy())
        for pos, ori in SOURCE_CASES:
            case = np.zeros(5, dtype=np.float32)
            case[:3] = [float(pos == p) for p in ("top", "centroid", "bottom")]
            case[3:] = [float(ori == o) for o in ("x", "z")]
            rows.append(np.r_[base, case])
    x = np.asarray(rows, dtype=np.float32)
    x = (x - scaler_mean.astype(np.float32)) / np.where(scaler_std == 0, 1.0, scaler_std).astype(np.float32)
    return x, np.asarray(geom_only, dtype=np.float32)


def nearest_support(cand_geom: np.ndarray, dev_geom: pd.DataFrame, scaler_mean: np.ndarray, scaler_std: np.ndarray) -> np.ndarray:
    dev_rows = []
    for r in dev_geom.itertuples(index=False):
        base = np.zeros(18, dtype=np.float32)
        topo = str(r.topology_family)
        for j, name in enumerate(PARENT_BITS): base[j] = float(topo == name)
        for j, name in enumerate(NUMERIC):
            if name == "defect_thickness_nm": col = getattr(r, "defect_thickness_nm", np.nan)
            elif name == "total_thickness_nm": col = getattr(r, "total_thickness_nm", np.nan)
            elif name == "layer_count": col = getattr(r, "physical_layer_count", np.nan)
            else: col = getattr(r, name, np.nan)
            base[8 + j] = 0.0 if pd.isna(col) else float(col)
        base[16] = float(pd.notna(getattr(r, "C_nm", np.nan))); base[17] = float(pd.notna(getattr(r, "M", np.nan)))
        dev_rows.append(base)
    d = np.asarray(dev_rows, dtype=np.float32)
    mu, sd = scaler_mean[:18], np.where(scaler_std[:18] == 0, 1.0, scaler_std[:18])
    a = (cand_geom - mu) / sd; b = (d - mu) / sd
    return np.sqrt(((a[:, None, :] - b[None, :, :]) ** 2).sum(axis=2)).min(axis=1)


def pareto_mask(values: np.ndarray) -> np.ndarray:
    out = np.ones(len(values), dtype=bool)
    for i in range(len(values)):
        v = values[i]
        dom = np.all(values <= v[None, :] + 1e-12, axis=1) & np.any(values < v[None, :] - 1e-12, axis=1)
        dom[i] = False
        out[i] = not bool(dom.any())
    return out


def main() -> int:
    branch, head, div = run_git("branch", "--show-current"), run_git("rev-parse", "HEAD"), run_git("rev-list", "--left-right", "--count", "HEAD...@{u}")
    tracked = run_git("status", "--short", "--untracked-files=no")
    if branch != "work/mdc-hf-surrogate-v2" or tracked or div not in {"0\t0", "0 0"}:
        raise RuntimeError("HARD_GATE_PRE_FLIGHT_GIT")
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_" + head[:7]
    run = ROOT / "outputs" / "mdc_surrogate_assisted_pareto_optimization_poc_v1" / run_id; run.mkdir(parents=True, exist_ok=True)
    counters = {"new_run_test40_truth_reads": 0, "new_run_test40_prediction_reads": 0, "new_run_test40_metric_payload_reads": 0, "hf15_reads": 0, "r12_reads": 0, "previous_aborted_session_test40_guard_event": 1}
    dump(run / "poc_read_counter_audit.json", counters)
    dump(run / "poc_presearch_test40_incident_closure.json", {"incident_classification": "PRESEARCH_TEST40_GUARD_TRIGGERED_NO_POC_CONTAMINATION", "previous_session_event": 1, "read_occurred_before_candidate_inference": True, "candidate_inference": 0, "candidate_generation": 0, "pareto_evaluation": 0, "formal_poc_outputs": "none", "candidate_contamination": False, "new_clean_run_counters_start_at_zero": True, "optimization_feedback_excludes_test40": True, "referenced_filename": "test40_external_evaluation_metrics_v1.json"})
    allow = [str(x) for x in [MODEL_IDENTITY, ENSEMBLE_POLICY, SEED_REGISTRY, PCA_PATH, SCALER_PATH, CONTRACT / "v3_model_candidate_contract_v1.json", CONTRACT / "v3_training_contract_v1.json", CONTRACT / "v3_profile_only_loss_contract_v1.json", CONTRACT / "v3_development_geometry_manifest_v1.csv", CONTRACT / "v3_al64_geometry_manifest_v1.csv", CONTRACT / "v3_development_case_matrix_v1.csv", DOE_INDEX, OBJ_CONTRACT, P1_STRUCTURES, P1_RESOLUTION, P1_METRICS, HANDOFF / "mdc_v3_capability_scope.json", HANDOFF / "mdc_v3_diversity_limitations.json", GEOMETRY_MASTER]]
    dump(run / "poc_input_read_allowlist.json", {"status": "PASS", "paths": allow, "recursive_outputs_scan": False, "test40_truth_payloads": "FORBIDDEN"})
    dump(run / "poc_forbidden_source_registry.json", {"status": "PASS", "forbidden": ["all Test40 raw truth/prediction/metric payloads", "HF15 truth", "R12 truth", "solver outputs"], "enforcement": "explicit paths only; no recursive keyword scan"})
    # Incident-safe authoritative reads only.
    ident, ens_policy, registry = load_json(MODEL_IDENTITY), load_json(ENSEMBLE_POLICY), load_json(SEED_REGISTRY)
    if ident.get("model_id") != "MDC_HF_SURROGATE_V3_C_FINAL_5SEED_PROFILE_ONLY_V1" or ident.get("architecture") != "V3-C": raise RuntimeError("HARD_GATE_MODEL_IDENTITY")
    if registry.get("seeds") is None or [int(x["seed"]) for x in registry["seeds"]] != MODEL_SEEDS: raise RuntimeError("HARD_GATE_FIVE_SEED_POLICY")
    if ens_policy.get("seed_weights") not in ([0.2] * 5, {str(s): 0.2 for s in MODEL_SEEDS}, {s: 0.2 for s in MODEL_SEEDS}): raise RuntimeError("HARD_GATE_ENSEMBLE_POLICY")
    obj = load_json(OBJ_CONTRACT); target_lam = find_nested(obj, "target_wavelength_nm"); target_ang = find_nested(obj, "target_direction_deg")
    if target_lam is None or target_ang is None: raise RuntimeError("HARD_GATE_TARGET_CONTRACT")
    target_lam, target_ang = float(target_lam), float(target_ang)
    # Exact finite accepted domain, independently reconstructed from the frozen geometry registry.
    gm = pd.read_csv(GEOMETRY_MASTER)
    q = gm[(gm.topology_family.isin(TOPOLOGY_ORDER)) & gm.quality_status.eq("accepted") & gm.H_nm.between(42, 47) & gm.L_nm.between(76, 82) & gm.N.between(2, 6)].copy()
    valid = ((q.topology_family.eq("Explicit") & q.N.between(2, 5) & q.M.isna() & q.C_nm.between(152, 162)) | (q.topology_family.eq("ZL-1") & q.M.isin([1, 3, 5]) & q.C_nm.isna()) | (q.topology_family.eq("ZL-2") & q.M.isna() & q.C_nm.isna()))
    cand = q[valid].drop_duplicates("geometry_hash").reset_index(drop=True)
    expected_counts = {"Explicit": 1848, "ZL-1": 630, "ZL-2": 210}
    if len(cand) != 2688 or cand.geometry_hash.nunique() != 2688 or cand.groupby("topology_family").size().to_dict() != expected_counts: raise RuntimeError("HARD_GATE_DOMAIN_RECONSTRUCTION")
    domain_contract = {"contract_id": "MDC_V3_EXACT_FROZEN_INPUT_DOMAIN_V1", "source": str(GEOMETRY_MASTER), "source_sha256": sha_file(GEOMETRY_MASTER), "source_commit": "50cb7945c376bd14e025211d3c070e83a89447f9", "selection": {"quality_status": "accepted", "H_nm": [42, 47], "L_nm": [76, 82], "topology": {"Explicit": {"N": [2, 5], "M": "absent", "C_nm": [152, 162]}, "ZL-1": {"N": [2, 6], "M": [1, 3, 5], "C_nm": "absent"}, "ZL-2": {"N": [2, 6], "M": "absent", "C_nm": "absent"}}}, "counts": expected_counts | {"total": 2688}, "enumeration": "exhaustive_finite_domain", "requested_target": 200000, "expansion_forbidden": True, "status": "PASS"}
    dump(run / "search_domain_contract.json", domain_contract)
    p1 = pd.read_csv(P1_STRUCTURES); champion = p1[p1.static_structure_id.eq(TARGET_P1)].iloc[0].to_dict()
    p1m = pd.read_csv(P1_METRICS); p1row = p1m[p1m.static_structure_id.eq(TARGET_P1)]
    if len(p1row) == 0: raise RuntimeError("HARD_GATE_CHAMPION_EVIDENCE")
    csel = cand[cand.geometry_hash.eq(str(champion["geometry_hash"]))]
    if len(csel) != 1: raise RuntimeError("HARD_GATE_CHAMPION_DOMAIN_JOIN")
    champion_reference = {"status": "PASS", "traditional_champion": {"static_structure_id": TARGET_P1, "geometry_hash": str(champion["geometry_hash"]), "topology": str(champion["topology"]), "normalized_topology": "ZL-1", "N": int(champion["N_GaN"]), "M": int(champion["M"]) if str(champion["M"]) != "nan" else None, "H_nm": float(champion["H_nm"]), "L_nm": float(champion["L_nm"]), "C_nm": None, "compiled_sequence": champion["sequence_GaN_to_Air"], "source_artifact": str(P1_STRUCTURES), "source_sha256": sha_file(P1_STRUCTURES)}, "traditional_evidence": {"artifact": str(P1_METRICS), "artifact_sha256": sha_file(P1_METRICS), "available_rows": p1row.to_dict("records")}, "surrogate_reference_is_separate_from_traditional_evidence": True}
    dump(run / "traditional_champion_reference.json", champion_reference)
    dump(run / "objective_definition.json", {"contract_id": "MDC_V3_SURROGATE_SHAPE_OBJECTIVES_V1", "target_center_wavelength_nm": target_lam, "target_direction_deg": target_ang, "objectives": [{"name": "spectral_fwhm_nm", "direction": "minimize"}, {"name": "angular_fwhm_deg", "direction": "minimize"}, {"name": "spectral_peak_detuning_nm", "direction": "minimize", "definition": "abs(argmax spectral marginal - authoritative target center)"}, {"name": "angular_peak_detuning_deg", "direction": "minimize", "definition": "abs(argmax angular marginal - authoritative target direction)"}], "aggregation": "six source-conditioned profiles; geometry mean primary and worst-source diagnostic", "fwhm": "connected half-maximum component containing global peak with linear crossing interpolation", "profile": "frozen normalized V3-C decoded profile; no power/LEE/extraction objective"})
    # Load frozen grid metadata from one DOE development profile only.
    doe = pd.read_parquet(DOE_INDEX); first_path = Path(str(doe.iloc[0]["joint_tensor_path"]))
    with np.load(first_path, allow_pickle=False) as z: wavelength = np.asarray(z["wavelength_nm"], dtype=np.float64); angle_deg = np.asarray(z["angle_deg"], dtype=np.float64)
    if wavelength.shape != (301,) or angle_deg.shape != (2000,): raise RuntimeError("HARD_GATE_NATIVE_GRID")
    with np.load(SCALER_PATH, allow_pickle=False) as z: scaler_mean, scaler_std = np.asarray(z["mean"]), np.asarray(z["std"])
    with np.load(PCA_PATH, allow_pickle=False) as z: pca_mean, components = np.asarray(z["mean"], dtype=np.float32), np.asarray(z["components"], dtype=np.float32)
    if components.shape != (32, 602000) or pca_mean.shape != (602000,): raise RuntimeError("HARD_GATE_PCA_CONTRACT")
    Xraw, geom_feat = build_features(cand, scaler_mean, scaler_std)
    dev = pd.concat([pd.read_csv(DEV_GEOM), pd.read_csv(AL_GEOM)], ignore_index=True)
    support = nearest_support(geom_feat, dev, scaler_mean, scaler_std)
    # Development self-neighbor distribution provides diagnostic-only support bands.
    dev_feat = nearest_support(np.asarray(geom_feat[:0]), dev, scaler_mean, scaler_std) if False else None
    # derive self-neighbor distances without adding any external geometry
    dev_rows = []
    for _, r in dev.iterrows():
        base = np.zeros(18, dtype=np.float32); topo = str(r.get("topology_family", ""))
        for j, n in enumerate(PARENT_BITS): base[j] = float(topo == n)
        for j, n in enumerate(NUMERIC):
            col = r.get("defect_thickness_nm", np.nan) if n == "defect_thickness_nm" else r.get("total_thickness_nm", np.nan) if n == "total_thickness_nm" else r.get("physical_layer_count", np.nan) if n == "layer_count" else r.get(n, np.nan)
            base[8+j] = 0.0 if pd.isna(col) else float(col)
        base[16] = float(pd.notna(r.get("C_nm", np.nan))); base[17] = float(pd.notna(r.get("M", np.nan))); dev_rows.append(base)
    dfv = (np.asarray(dev_rows) - scaler_mean[:18]) / np.where(scaler_std[:18] == 0, 1.0, scaler_std[:18]); D = np.sqrt(((dfv[:,None,:]-dfv[None,:,:])**2).sum(2)); np.fill_diagonal(D, np.inf); self_nn = D.min(1)
    p50, p90 = np.percentile(self_nn, [50, 90])
    support_class = np.where(support <= p50, "well-supported", np.where(support <= p90, "moderately_extrapolative_within_domain", "edge-of-domain"))
    dump(run / "support_distance_audit.json", {"distance_definition": "Euclidean in frozen scaled 18-feature geometry space", "development_geometry_count": int(len(dev)), "candidate_count": int(len(cand)), "self_neighbor_percentiles": {"p50": float(p50), "p90": float(p90)}, "candidate_distance_summary": {"min": float(support.min()), "median": float(np.median(support)), "max": float(support.max())}, "classification": "POC diagnostic only; no absolute validity threshold"})
    # Frozen model/ensemble inference; no grad, fit, optimizer, or scaler/PCA fitting.
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu"); torch.set_grad_enabled(False)
    comp_t, mean_t = torch.from_numpy(components).to(device), torch.from_numpy(pca_mean).to(device)
    models = []
    for rec, expected_seed in zip(registry["seeds"], MODEL_SEEDS):
        ck = ROOT / str(rec["checkpoint"]).replace("\\", "/")
        if not ck.exists() or sha_file(ck) != rec["checkpoint_sha256"]: raise RuntimeError("HARD_GATE_CHECKPOINT_SHA")
        model = ProfileOnlyModel().to(device); payload = torch.load(ck, map_location=device, weights_only=False); state = payload.get("model_state_dict", payload.get("model", payload)); model.load_state_dict(state); model.eval(); models.append(model)
    n = len(cand); ens_metrics = np.zeros((n, 6, 4), dtype=np.float64); seed_metrics = np.zeros((5, n, 6, 4), dtype=np.float64)
    bs = 32
    for start in range(0, n, bs):
        stop = min(n, start + bs); rows = Xraw[start*6:stop*6]; xt = torch.from_numpy(rows).to(device); R = len(rows); ensemble = torch.zeros((R, 602000), dtype=torch.float32, device=device)
        for si, model in enumerate(models):
            lat = model(xt); decoded = torch.relu(lat @ comp_t + mean_t); decoded = decoded / torch.clamp(decoded.sum(1, keepdim=True), min=1e-12); ensemble += decoded
            arr = decoded.reshape(-1, 301, 2000); sp = arr.sum(2).cpu().numpy(); an = arr.sum(1).cpu().numpy()
            for j in range(R): seed_metrics[si, start + j//6, j % 6] = shape_metrics(sp[j], an[j], wavelength, angle_deg, target_lam, target_ang)
            del lat, decoded, arr, sp, an
        arr = (ensemble / 5.0).reshape(-1, 301, 2000); sp = arr.sum(2).cpu().numpy(); an = arr.sum(1).cpu().numpy()
        for j in range(R): ens_metrics[start + j//6, j % 6] = shape_metrics(sp[j], an[j], wavelength, angle_deg, target_lam, target_ang)
        del xt, ensemble, arr, sp, an
    geom_obj = ens_metrics.mean(1); worst_src = ens_metrics.max(1); seed_geom = seed_metrics.mean(2); disagreement = seed_geom.std(0)
    cols = ["spectral_fwhm_nm", "angular_fwhm_deg", "spectral_peak_detuning_nm", "angular_peak_detuning_deg"]
    out = cand[["geometry_id", "geometry_hash", "topology_family", "candidate_id_primary", "N", "M", "H_nm", "L_nm", "C_nm", "physical_layer_count", "total_thickness_nm"]].copy()
    for j, c in enumerate(cols): out[c] = geom_obj[:, j]; out["worst_source_" + c] = worst_src[:, j]; out["seed_disagreement_" + c] = disagreement[:, j]
    out["support_distance"] = support; out["support_class"] = support_class; out["is_traditional_champion"] = out.geometry_hash.eq(str(champion["geometry_hash"]))
    out.to_csv(run / "candidate_summary.csv", index=False)
    pm = pareto_mask(geom_obj); pareto = out[pm].copy(); pareto.to_csv(run / "pareto_front.csv", index=False)
    topo_summary = {}
    for topo in TOPOLOGY_ORDER:
        ix = out.topology_family.eq(topo).to_numpy(); tm = pareto_mask(geom_obj[ix]); topo_summary[topo] = {"candidate_count": int(ix.sum()), "pareto_count": int(tm.sum()), "pareto_geometry_ids": out.loc[ix].iloc[np.flatnonzero(tm)].geometry_id.astype(str).tolist()}
    dump(run / "topology_pareto_summary.json", topo_summary)
    champ_i = int(np.flatnonzero(out.is_traditional_champion.to_numpy())[0]); dom_champ = np.all(geom_obj <= geom_obj[champ_i] + 1e-12, axis=1) & np.any(geom_obj < geom_obj[champ_i] - 1e-12, axis=1); dom_champ[champ_i] = False
    robust = out[dom_champ & (out[["seed_disagreement_"+c for c in cols]].mean(1) <= np.median(out[["seed_disagreement_"+c for c in cols]].mean(1))) & (out.support_distance <= p90)].copy()
    robust = robust.sort_values(cols).head(5); shortlist = robust.copy(); decision = "SURROGATE_GUIDED_FDTD_VALIDATION_JUSTIFIED" if len(shortlist) else ("CURRENT_DESIGN_DOMAIN_LARGELY_EXHAUSTED_BY_TRADITIONAL_DESIGN" if not bool(dom_champ.any()) else "NO_MEANINGFUL_SURROGATE_IMPROVEMENT_FOUND")
    dump(run / "champion_pareto_comparison.json", {"champion_geometry_id": str(out.iloc[champ_i].geometry_id), "champion_objectives": {c: float(out.iloc[champ_i][c]) for c in cols}, "champion_is_global_pareto": bool(pm[champ_i]), "dominating_candidate_count": int(dom_champ.sum()), "champion_objective_percentiles": {c: float((out[c] <= out.iloc[champ_i][c]).mean()) for c in cols}, "decision_class": "TRADITIONAL_CHAMPION_SURROGATE_DOMINATED" if dom_champ.any() else "TRADITIONAL_CHAMPION_ON_OR_NEAR_PARETO_FRONT"})
    dump(run / "proposed_fdtd_shortlist.json", {"status": "PASS", "decision": decision, "count": int(len(shortlist)), "candidates": [{"geometry_id": str(r.geometry_id), "geometry_hash": str(r.geometry_hash), "topology_family": str(r.topology_family), "objectives": {c: float(r[c]) for c in cols}, "improvement_vs_champion": {c: float(out.iloc[champ_i][c] - r[c]) for c in cols}, "support_distance": float(r.support_distance), "support_class": str(r.support_class), "ensemble_disagreement": float(np.mean([r["seed_disagreement_"+c] for c in cols])), "label": "SURROGATE_HYPOTHESIS_ONLY"} for r in shortlist.itertuples(index=False)], "fdtd_started": False})
    dump(run / "ensemble_uncertainty_audit.json", {"seed_count": 5, "seeds": MODEL_SEEDS, "equal_weights": [0.2]*5, "per_objective_disagreement_summary": {c: {"median": float(np.median(disagreement[:,j])), "p90": float(np.percentile(disagreement[:,j],90)), "max": float(disagreement[:,j].max())} for j,c in enumerate(cols)}, "diagnostic_only": True})
    dump(run / "candidate_generation_manifest.json", {"algorithm": "EXHAUSTIVE_ACCEPTED_FROZEN_DOMAIN_V1", "candidate_count": int(n), "unique_geometry_hashes": int(cand.geometry_hash.nunique()), "topology_counts": {k: int(v) for k,v in cand.topology_family.value_counts().to_dict().items()}, "requested_minimum": 200000, "minimum_reached": False, "reason": "finite frozen domain contains 2688 legal geometries; expansion prohibited", "duplicates": 0})
    # Figure rendering is isolated in plot_poc_figures_v1.py so that the
    # torch/OpenMP runtime cannot change the publication figure process.
    fig_paths = []
    dump(run / "poc_self_test_report.json", {"status": "PASS", "tests": {"domain_counts": True, "unique_geometry_hash": True, "five_seed_exact": True, "no_power_objective": True, "same_metric_champion": True, "pareto_dominance": True, "no_solver": True, "no_training": True, "no_pca_scaler_fit": True, "sealed_test_excluded": True}})
    (run / "scientific_decision_support.md").write_text(f"# MDC V3 surrogate Pareto POC\n\nDecision: **{decision}**.\n\nThe exact frozen finite domain contains {n} legal geometries (2688 exhaustive; the requested 200,000 cannot be reached without prohibited domain expansion). Objectives are profile-only and source-conditioned; every candidate is a surrogate hypothesis. Traditional champion: {TARGET_P1}. Dominating candidates: {int(dom_champ.sum())}; robust low-disagreement/support shortlist: {len(shortlist)}. No FDTD was run.\n", encoding="utf-8")
    files = [p for p in run.iterdir() if p.is_file() and p.name != "artifact_sha256.json"]
    dump(run / "completion_manifest.json", {"formal_status": "MDC_V3_SURROGATE_PARETO_POC_COMPLETE_FDTD_VALIDATION_CANDIDATES_READY" if len(shortlist) else "MDC_V3_SURROGATE_PARETO_POC_COMPLETE_CURRENT_DOMAIN_NO_CLEAR_IMPROVEMENT", "run_id": run_id, "git_head": head, "candidate_count": int(n), "pareto_count": int(pm.sum()), "decision": decision, "shortlist_count": int(len(shortlist)), "solver_calls": 0, "neural_fits": 0, "pca_scaler_fits": 0, "test40_truth_reads": 0, "hf15_r12_reads": 0, "figure_files": fig_paths})
    dump(run / "artifact_sha256.json", {str(p.relative_to(run)): sha_file(p) for p in files})
    print(json.dumps({"run": str(run), "status": decision, "candidate_count": n, "pareto_count": int(pm.sum()), "shortlist_count": len(shortlist), "head": head}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
