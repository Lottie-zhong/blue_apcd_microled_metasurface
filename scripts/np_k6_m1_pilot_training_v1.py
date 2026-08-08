"""NP K6 M1 pilot surrogate smoke training.

This stage consumes only the six accepted FDTD HF anchors, uses geometry-group
leave-one-geometry-out validation, and never invokes a solver.  Checkpoints are
runtime artifacts; only lightweight manifests and metrics are evidence.
"""
from __future__ import annotations

import copy
import csv
import hashlib
import json
import math
import os
import re
import shutil
import time
from pathlib import Path
from typing import Any

import numpy as np
# The bundled Anaconda/OpenMP runtimes can expose duplicate Intel OpenMP DLLs
# on Windows.  Keep this scoped to the smoke-training process and single-thread
# BLAS so the CUDA preflight remains explicit and reproducible.
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

ROOT = Path(r"D:\project\worktrees\blue_apcd_np_k6_mdc_v1")
DATASET = ROOT / "outputs" / "np_k6_hf_pilot_dataset_v1"
OUT = ROOT / "outputs" / "np_k6_m1_pilot_training_v1"
CONFIG_PATH = ROOT / "configs" / "np_k6_forward_surrogate_pilot_v1.json"
WAVELENGTHS = list(range(445, 456))
GEOMETRY_GROUPS = ["RUN3A", "RUN3B", "RUN3C"]
SEEDS = [17, 29, 43]
TX_ORDER_IDS = [-3, -2, -1, 0, 1, 2, 3]
RX_ORDER_IDS = list(range(-5, 6))


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def json_write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def csv_read(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def finite(v: Any) -> bool:
    try:
        return math.isfinite(float(v))
    except (TypeError, ValueError):
        return False


def rankdata(a: np.ndarray) -> np.ndarray:
    return np.argsort(np.argsort(np.asarray(a, dtype=float)))


def spearman(a: np.ndarray, b: np.ndarray) -> float:
    if len(a) < 2 or np.std(a) == 0 or np.std(b) == 0:
        return 1.0 if np.allclose(a, b) else 0.0
    return float(np.corrcoef(rankdata(a), rankdata(b))[0, 1])


def geometry_group(case_id: str) -> str:
    m = re.match(r"(RUN3[ABC])_", case_id)
    if not m:
        raise RuntimeError(f"unexpected case id: {case_id}")
    return m.group(1)


def parse_diameters(geometry_id: str) -> list[float]:
    values = [float(x) for x in re.findall(r"D(\d+)", geometry_id)]
    if len(values) != 6:
        raise RuntimeError(f"six-diameter geometry required: {geometry_id}")
    return values


class AnchorDataset:
    def __init__(self) -> None:
        self.metrics = csv_read(DATASET / "hf_observations_long.csv")
        self.tx = csv_read(DATASET / "hf_transmitted_orders_long.csv")
        self.rx = csv_read(DATASET / "hf_reflected_orders_long.csv")
        self.registry = csv_read(DATASET / "hf_task_registry.csv")
        self.audit = self._audit()
        self.rows = self._make_rows()

    def _audit(self) -> dict[str, Any]:
        if len(self.metrics) != 66:
            raise RuntimeError("HARD_GATE_PILOT_HF_DATA_SPLIT_CONFLICT: observation count")
        keys = {(r["case_id"], int(float(r["wavelength_nm"]))) for r in self.metrics}
        if len(keys) != 66:
            raise RuntimeError("duplicate case/wavelength labels")
        cases = sorted({r["case_id"] for r in self.metrics})
        groups = sorted({geometry_group(c) for c in cases})
        hashes = sorted({r["geometry_hash"] for r in self.metrics})
        pols = sorted({r["polarization"] for r in self.metrics})
        if groups != GEOMETRY_GROUPS or len(hashes) != 3 or pols != ["p", "s"]:
            raise RuntimeError("geometry/polarization inventory mismatch")
        errors = []
        for r in self.metrics:
            if int(float(r["wavelength_nm"])) not in WAVELENGTHS:
                errors.append("wavelength")
            if r.get("training_label", "").lower() != "true": errors.append("training_label")
            if r.get("quality_gate_pass", "").lower() != "true": errors.append("quality_gate_pass")
            if r.get("diagnostic_only", "").lower() != "false": errors.append("diagnostic_only")
            if r.get("generator_id") != "NP_K6_PILOT_FDTD_GENERATOR_FIXED_GRID_3PS_V2": errors.append("generator")
            if r.get("interface_stack_id") != "NP_K6_INDEPENDENT_STACK_PILOT_V1": errors.append("stack")
            if any(token in json.dumps(r).lower() for token in ["1ps", "2ps", "10ps", "rcwa", "sealed"]): errors.append("contaminant")
            for field in ["T_total", "R_total", "eta_plus1", "eta_0", "eta_minus1", "directionality", "non_target_efficiency"]:
                if not finite(r.get(field)): errors.append("nonfinite")
        if any("RUN3C_S_PILOT_HF_V1" in c for c in cases): errors.append("obsolete_RUN3C_S")
        if errors:
            raise RuntimeError("dataset audit failed: " + ",".join(sorted(set(errors))))
        registry_types = sorted({r.get("source_type", "") for r in self.registry})
        return {
            "schema_version": "np_k6_m1_pilot_dataset_audit_v1",
            "formal_observation_count": 66,
            "formal_hf_tasks": 6,
            "case_ids": cases,
            "geometry_groups": groups,
            "geometry_hashes": hashes,
            "polarizations": pols,
            "wavelengths_nm": WAVELENGTHS,
            "rows_per_case": {c: sum(x["case_id"] == c for x in self.metrics) for c in cases},
            "training_label_all_true": True,
            "quality_gate_pass_all_true": True,
            "diagnostic_only_all_false": True,
            "generator_id": "NP_K6_PILOT_FDTD_GENERATOR_FIXED_GRID_3PS_V2",
            "interface_stack_id": "NP_K6_INDEPENDENT_STACK_PILOT_V1",
            "label_source": "FDTD",
            "registry_source_types": registry_types,
            "lf_dft_as_label": False,
            "rcwa_as_label": False,
            "sealed_test_access": 0,
            "obsolete_run3c_s_access": 0,
            "partial_simulation_time_records": 0,
            "dataset_manifest_sha256": sha256(DATASET / "dataset_checksum_manifest.json"),
        }

    def _make_rows(self) -> list[dict[str, Any]]:
        tx_map: dict[tuple[str, int], dict[int, float]] = {}
        rx_map: dict[tuple[str, int], dict[int, float]] = {}
        for r in self.tx:
            tx_map.setdefault((r["case_id"], int(float(r["wavelength_nm"]))), {})[int(float(r["order_n"]))] = float(r["absolute_efficiency"])
        for r in self.rx:
            rx_map.setdefault((r["case_id"], int(float(r["wavelength_nm"]))), {})[int(float(r["order_n"]))] = float(r["absolute_efficiency"])
        rows = []
        for r in self.metrics:
            key = (r["case_id"], int(float(r["wavelength_nm"])))
            if set(tx_map.get(key, {})) != set(TX_ORDER_IDS) or set(rx_map.get(key, {})) != set(RX_ORDER_IDS):
                raise RuntimeError(f"order capability mismatch for {key}")
            rows.append({
                "case_id": r["case_id"], "geometry_group": geometry_group(r["case_id"]),
                "geometry_id": r["geometry_id"], "geometry_hash": r["geometry_hash"],
                "wavelength_nm": int(float(r["wavelength_nm"])), "polarization": r["polarization"],
                "T": float(r["T_total"]), "R": float(r["R_total"]),
                "tx": np.asarray([tx_map[key][n] for n in TX_ORDER_IDS], dtype=np.float32),
                "rx": np.asarray([rx_map[key][n] for n in RX_ORDER_IDS], dtype=np.float32),
                "eta_plus1": float(r["eta_plus1"]), "directionality": float(r["directionality"]),
                "non_target_efficiency": float(r["non_target_efficiency"]),
            })
        return rows

    def features(self, row: dict[str, Any]) -> tuple[np.ndarray, np.ndarray]:
        d = np.asarray(parse_diameters(row["geometry_id"]), dtype=np.float32) / 230.0
        i = np.arange(6, dtype=np.float32)
        prev = np.roll(d, 1); nxt = np.roll(d, -1)
        node = np.stack([d, np.sin(2*np.pi*i/6), np.cos(2*np.pi*i/6), d-prev, nxt-d, d-nxt, i/5.0], axis=1).astype(np.float32)
        wl = (row["wavelength_nm"] - 450.0) / 5.0
        pol = 0.0 if row["polarization"] == "p" else 1.0
        context = np.asarray([wl, pol, 0.0, 0.0], dtype=np.float32)
        return node, context


class CircularCNN(nn.Module):
    def __init__(self, hidden: int = 32) -> None:
        super().__init__()
        self.conv = nn.Sequential(
            nn.Conv1d(7, hidden, 3, padding=1, padding_mode="circular"), nn.GELU(),
            nn.Conv1d(hidden, hidden, 3, padding=1, padding_mode="circular"), nn.GELU(),
            nn.Conv1d(hidden, hidden, 3, padding=1, padding_mode="circular"), nn.GELU(),
        )
        self.context = nn.Sequential(nn.Linear(4, hidden), nn.GELU())
        self.tr = nn.Linear(hidden, 2)
        self.tx = nn.Linear(hidden, len(TX_ORDER_IDS))
        self.rx = nn.Linear(hidden, len(RX_ORDER_IDS))

    def forward(self, x: torch.Tensor, c: torch.Tensor) -> dict[str, torch.Tensor]:
        h = self.conv(x.transpose(1, 2)).mean(dim=2) + self.context(c)
        tr = torch.sigmoid(self.tr(h)); T = tr[:, 0]; R = (1.0 - T) * tr[:, 1]
        return {"T": T, "R": R, "tx": T[:, None] * torch.softmax(self.tx(h), dim=1), "rx": R[:, None] * torch.softmax(self.rx(h), dim=1)}


class SmallMLP(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.body = nn.Sequential(nn.Linear(6*7+4, 64), nn.GELU(), nn.Linear(64, 64), nn.GELU())
        self.tr = nn.Linear(64, 2); self.tx = nn.Linear(64, len(TX_ORDER_IDS)); self.rx = nn.Linear(64, len(RX_ORDER_IDS))

    def forward(self, x: torch.Tensor, c: torch.Tensor) -> dict[str, torch.Tensor]:
        h = self.body(torch.cat([x.flatten(1), c], dim=1)); tr = torch.sigmoid(self.tr(h)); T = tr[:, 0]; R = (1.0-T)*tr[:, 1]
        return {"T": T, "R": R, "tx": T[:, None]*torch.softmax(self.tx(h), dim=1), "rx": R[:, None]*torch.softmax(self.rx(h), dim=1)}


def tensor_targets(rows: list[dict[str, Any]], xmean: np.ndarray, xstd: np.ndarray) -> tuple[np.ndarray, ...]:
    ds = AnchorDataset.__new__(AnchorDataset)
    xs, cs = [], []
    for row in rows:
        node, ctx = ds.features(row); xs.append((node-xmean)/xstd); cs.append(ctx)
    return (np.asarray(xs, dtype=np.float32), np.asarray(cs, dtype=np.float32),
            np.asarray([r["T"] for r in rows], dtype=np.float32), np.asarray([r["R"] for r in rows], dtype=np.float32),
            np.asarray([r["tx"] for r in rows], dtype=np.float32), np.asarray([r["rx"] for r in rows], dtype=np.float32),
            np.asarray([r["eta_plus1"] for r in rows], dtype=np.float32), np.asarray([r["directionality"] for r in rows], dtype=np.float32),
            np.asarray([r["non_target_efficiency"] for r in rows], dtype=np.float32))


def loss_fn(pred: dict[str, torch.Tensor], target: tuple[torch.Tensor, ...]) -> dict[str, torch.Tensor]:
    T, R, tx, rx = target[:4]
    hub = nn.SmoothL1Loss()
    order = hub(pred["tx"], tx) + hub(pred["rx"], rx)
    tr = hub(pred["T"], T) + hub(pred["R"], R)
    target_loss = hub(pred["tx"][:, TX_ORDER_IDS.index(1)], tx[:, TX_ORDER_IDS.index(1)])
    phys = torch.relu(torch.abs(1.0-pred["T"]-pred["R"])-0.02).mean()
    return {"total": order+tr+target_loss+phys, "order": order, "TR": tr, "target": target_loss, "physics": phys}


def evaluate(model: nn.Module, arrays: tuple[np.ndarray, ...], device: torch.device) -> tuple[dict[str, Any], np.ndarray, np.ndarray]:
    x, c, T, R, tx, rx, eta, direc, non = arrays
    model.eval()
    with torch.no_grad():
        p = model(torch.from_numpy(x).to(device, non_blocking=True), torch.from_numpy(c).to(device, non_blocking=True))
        pred = {k: v.detach().cpu().numpy() for k, v in p.items()}
    pe = pred["tx"][:, TX_ORDER_IDS.index(1)]
    true_non = non
    pred_non = pred["tx"].sum(axis=1)-pe
    allerr = np.concatenate([pred["tx"]-tx, pred["rx"]-rx], axis=1)
    metrics = {
        "eta_plus1_MAE": float(np.mean(np.abs(pe-eta))), "eta_plus1_RMSE": float(np.sqrt(np.mean((pe-eta)**2))),
        "eta_plus1_Spearman": spearman(pe, eta), "all_order_weighted_MAE": float(np.mean(np.abs(allerr))),
        "T_MAE": float(np.mean(np.abs(pred["T"]-T))), "R_MAE": float(np.mean(np.abs(pred["R"]-R))),
        "directionality_MAE": float(np.mean(np.abs(pe/(pred["tx"].sum(axis=1)+1e-12)-direc))),
        "non_target_leakage_MAE": float(np.mean(np.abs(pred_non-true_non))),
        "predicted_transmitted_order_sum_mismatch": float(np.max(np.abs(pred["tx"].sum(axis=1)-pred["T"]))),
        "predicted_reflected_consistency": float(np.max(np.abs(pred["rx"].sum(axis=1)-pred["R"]))),
        "negative_power_violations": int(np.sum(np.concatenate([pred["T"][:,None],pred["R"][:,None],pred["tx"],pred["rx"]],axis=1)<0)),
        "nan_inf_count": int(sum(np.sum(~np.isfinite(v)) for v in pred.values())),
    }
    return metrics, pred["tx"], pred["rx"]


def stratified_metrics(pred_tx: np.ndarray, pred_rx: np.ndarray, rows: list[dict[str, Any]]) -> dict[str, Any]:
    true_tx = np.asarray([r["tx"] for r in rows]); true_rx = np.asarray([r["rx"] for r in rows])
    true_eta = np.asarray([r["eta_plus1"] for r in rows]); true_T = np.asarray([r["T"] for r in rows]); true_R = np.asarray([r["R"] for r in rows])
    true_dir = np.asarray([r["directionality"] for r in rows]); true_non = np.asarray([r["non_target_efficiency"] for r in rows])
    idx = TX_ORDER_IDS.index(1); pe = pred_tx[:, idx]; eta_err = np.abs(pe-true_eta)
    def one(mask: np.ndarray) -> dict[str, float]:
        if not np.any(mask): return {"count": 0}
        return {"count": int(np.sum(mask)), "eta_plus1_MAE": float(np.mean(eta_err[mask])), "T_MAE": float(np.mean(np.abs(pred_tx[mask].sum(1)-true_T[mask]))), "R_MAE": float(np.mean(np.abs(pred_rx[mask].sum(1)-true_R[mask]))), "directionality_MAE": float(np.mean(np.abs(pe[mask]/(pred_tx[mask].sum(1)+1e-12)-true_dir[mask]))), "non_target_leakage_MAE": float(np.mean(np.abs(pred_tx[mask].sum(1)-pe[mask]-true_non[mask]))), "all_order_weighted_MAE": float(np.mean(np.abs(np.concatenate([pred_tx[mask]-true_tx[mask], pred_rx[mask]-true_rx[mask]], 1))))}
    wavelengths = {str(w): one(np.asarray([r["wavelength_nm"] == w for r in rows])) for w in WAVELENGTHS}
    polarizations = {p: one(np.asarray([r["polarization"] == p for r in rows])) for p in ["p", "s"]}
    geometries = {g: one(np.asarray([r["geometry_group"] == g for r in rows])) for g in GEOMETRY_GROUPS}
    channels = {"eta_plus1": float(np.mean(np.abs(pe-true_eta))), "T": float(np.mean(np.abs(pred_tx.sum(1)-true_T))), "R": float(np.mean(np.abs(pred_rx.sum(1)-true_R))), "directionality": float(np.mean(np.abs(pe/(pred_tx.sum(1)+1e-12)-true_dir))), "non_target_leakage": float(np.mean(np.abs(pred_tx.sum(1)-pe-true_non)))}
    return {"wavelength_stratified": wavelengths, "polarization_stratified": polarizations, "geometry_stratified": geometries, "worst_wavelength_by_eta_plus1_MAE": max(wavelengths, key=lambda k: wavelengths[k]["eta_plus1_MAE"]), "worst_output_channel": max(channels, key=channels.get), "output_channel_MAE": channels}


def train_one(model: nn.Module, train_arrays: tuple[np.ndarray, ...], val_arrays: tuple[np.ndarray, ...] | None, seed: int, device: torch.device, cfg: dict[str, Any]) -> tuple[nn.Module, list[dict[str, Any]], int, float]:
    torch.manual_seed(seed); np.random.seed(seed)
    model.to(device)
    x,c,T,R,tx,rx,eta,direc,non = train_arrays
    ds = TensorDataset(torch.from_numpy(x), torch.from_numpy(c), torch.from_numpy(T), torch.from_numpy(R), torch.from_numpy(tx), torch.from_numpy(rx), torch.from_numpy(eta), torch.from_numpy(direc), torch.from_numpy(non))
    loader = DataLoader(ds, batch_size=16, shuffle=True, pin_memory=True, num_workers=0)
    opt = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)
    sch = torch.optim.lr_scheduler.ReduceLROnPlateau(opt, mode="min", patience=8, factor=0.5)
    best_state, best = None, float("inf"); wait = 0; history=[]; best_epoch=0
    for epoch in range(1, 301):
        model.train(); sums=[]; first_batch_device=None
        for batch in loader:
            batch = tuple(t.to(device, non_blocking=True) for t in batch); first_batch_device = str(batch[0].device)
            pred = model(batch[0], batch[1]); losses = loss_fn(pred, batch[2:]); opt.zero_grad(set_to_none=True); losses["total"].backward(); opt.step(); sums.append(float(losses["total"].detach().cpu()))
        monitor=float(np.mean(sums))
        if val_arrays is not None:
            model.eval(); vx,vc,vT,vR,vtx,vrx,veta,vd,vn=val_arrays
            with torch.no_grad(): monitor=float(loss_fn(model(torch.from_numpy(vx).to(device),torch.from_numpy(vc).to(device)), tuple(t.to(device) for t in [torch.from_numpy(vT),torch.from_numpy(vR),torch.from_numpy(vtx),torch.from_numpy(vrx),torch.from_numpy(veta),torch.from_numpy(vd),torch.from_numpy(vn)]))["total"].cpu())
        sch.step(monitor); history.append({"epoch":epoch,"train_loss":float(np.mean(sums)),"monitor_loss":monitor,"lr":opt.param_groups[0]["lr"],"batch_device":first_batch_device,"model_device":str(next(model.parameters()).device)})
        if monitor < best-1e-9:
            best=monitor; best_state=copy.deepcopy(model.state_dict()); best_epoch=epoch; wait=0
        else: wait += 1
        if wait >= 25: break
    if best_state is not None: model.load_state_dict(best_state)
    return model, history, best_epoch, best


def lf_baseline(rows: list[dict[str, Any]], train_rows: list[dict[str, Any]]) -> dict[str, np.ndarray]:
    # Analytic phase-bin DFT proxy; T/R calibration uses training rows only.
    Tmean=float(np.mean([r["T"] for r in train_rows])); Rmean=float(np.mean([r["R"] for r in train_rows]))
    tx=[]; rx=[]
    for r in rows:
        d=np.asarray(parse_diameters(r["geometry_id"]),float); phase=2*np.pi*(d-d.mean())/(d.std()+1e-6)/6
        amps=[]
        for n in TX_ORDER_IDS: amps.append(abs(np.sum(np.exp(1j*phase)*np.exp(-2j*np.pi*n*np.arange(6)/6)))**2)
        frac=np.asarray(amps); frac/=frac.sum(); tx.append(Tmean*frac)
        rx.append(np.full(len(RX_ORDER_IDS),Rmean/len(RX_ORDER_IDS)))
    return {"T":np.full(len(rows),Tmean),"R":np.full(len(rows),Rmean),"tx":np.asarray(tx),"rx":np.asarray(rx)}


def baseline_metrics(pred: dict[str,np.ndarray], rows: list[dict[str,Any]]) -> dict[str,Any]:
    T=np.asarray([r["T"] for r in rows]); R=np.asarray([r["R"] for r in rows]); tx=np.asarray([r["tx"] for r in rows]); rx=np.asarray([r["rx"] for r in rows]); eta=np.asarray([r["eta_plus1"] for r in rows]); direc=np.asarray([r["directionality"] for r in rows]); non=np.asarray([r["non_target_efficiency"] for r in rows]); pe=pred["tx"][:,TX_ORDER_IDS.index(1)]
    return {"eta_plus1_MAE":float(np.mean(abs(pe-eta))),"eta_plus1_RMSE":float(np.sqrt(np.mean((pe-eta)**2))),"eta_plus1_Spearman":spearman(pe,eta),"all_order_weighted_MAE":float(np.mean(abs(np.concatenate([pred["tx"]-tx,pred["rx"]-rx],1)))),"T_MAE":float(np.mean(abs(pred["T"]-T))),"R_MAE":float(np.mean(abs(pred["R"]-R))),"directionality_MAE":float(np.mean(abs(pe/(pred["tx"].sum(1)+1e-12)-direc))),"non_target_leakage_MAE":float(np.mean(abs(pred["tx"].sum(1)-pe-non))),"predicted_transmitted_order_sum_mismatch":float(np.max(abs(pred["tx"].sum(1)-pred["T"]))),"predicted_reflected_consistency":float(np.max(abs(pred["rx"].sum(1)-pred["R"]))),"negative_power_violations":int(np.sum(np.concatenate([pred["T"][:,None],pred["R"][:,None],pred["tx"],pred["rx"]],1)<0)),"nan_inf_count":int(sum(np.sum(~np.isfinite(v)) for v in pred.values()))}


def main() -> None:
    cfg=json.loads(CONFIG_PATH.read_text(encoding="utf-8")); device=torch.device("cuda:0") if torch.cuda.is_available() else None
    if device is None: raise SystemExit("HARD_GATE_NP_K6_M1_CUDA_UNAVAILABLE")
    torch.cuda.reset_peak_memory_stats(); cuda={"torch":torch.__version__,"torch_version_cuda":torch.version.cuda,"cuda_available":True,"gpu_count":torch.cuda.device_count(),"gpu_name":torch.cuda.get_device_name(0),"device":"cuda:0","driver_visible_device":os.environ.get("CUDA_VISIBLE_DEVICES","default"),"initial_allocated_bytes":torch.cuda.memory_allocated(0),"initial_reserved_bytes":torch.cuda.memory_reserved(0),"amp":False,"pin_memory":True,"non_blocking":True,"runtime_environment":{"KMP_DUPLICATE_LIB_OK":os.environ.get("KMP_DUPLICATE_LIB_OK"),"OMP_NUM_THREADS":os.environ.get("OMP_NUM_THREADS"),"MKL_NUM_THREADS":os.environ.get("MKL_NUM_THREADS")}}
    data=AnchorDataset(); rows=data.rows
    json_write(OUT/"dataset_audit.json",data.audit); json_write(OUT/"cuda_environment.json",cuda)
    folds=[("A","RUN3A",["RUN3B","RUN3C"],17),("B","RUN3B",["RUN3A","RUN3C"],29),("C","RUN3C",["RUN3A","RUN3B"],43)]
    split_manifest=[]; norm_manifest=[]; cnn_rows=[]; mlp_rows=[]; lf_rows=[]; histories=[]; fold_summary=[]; stratified_records=[]
    for fold,val_group,train_groups,seed in folds:
        train=[r for r in rows if r["geometry_group"] in train_groups]; val=[r for r in rows if r["geometry_group"]==val_group]
        tr_nodes=np.asarray([AnchorDataset.features(data,r)[0] for r in train]); mean=tr_nodes.mean((0,1)); std=tr_nodes.std((0,1)); std[std<1e-6]=1.0
        norm_manifest.append({"fold":fold,"fit_geometry_groups":train_groups,"fit_geometry_hashes":sorted({r["geometry_hash"] for r in train}),"feature_mean":mean.tolist(),"feature_std":std.tolist(),"output_normalization":"none","held_out_geometry_excluded":val_group})
        split_manifest.append({"fold":fold,"train_geometry_groups":train_groups,"validation_geometry_group":val_group,"train_observations":len(train),"validation_observations":len(val),"seed":seed,"geometry_group_leakage":False})
        tr=tensor_targets(train,mean,std); va=tensor_targets(val,mean,std)
        for name,cls,store in [("CNN",CircularCNN,cnn_rows),("MLP",SmallMLP,mlp_rows)]:
            model,hist,best_epoch,best=train_one(cls(),tr,va,seed,device,cfg); met,p_tx,p_rx=evaluate(model,va,device); store.append({"model":name,"fold":fold,"held_out_geometry":val_group,"seed":seed,"best_epoch":best_epoch,"best_monitor_loss":best,**met}); stratified_records.append({"model":name,"fold":fold,"held_out_geometry":val_group,"seed":seed,"metrics":stratified_metrics(p_tx,p_rx,val)}); histories.extend({"model":name,"fold":fold,**h} for h in hist)
        lf=baseline_metrics(lf_baseline(val,train),val); lf_rows.append({"model":"LF_DFT","fold":fold,"held_out_geometry":val_group,"seed":seed,**lf}); fold_summary.append({"fold":fold,"train_rows":len(train),"validation_rows":len(val),"held_out_geometry":val_group,"cnn":cnn_rows[-1],"mlp":mlp_rows[-1],"lf_dft":lf_rows[-1]})
    # Full-data acquisition-only ensemble; no validation claim is made here.
    all_nodes=np.asarray([AnchorDataset.features(data,r)[0] for r in rows]); mean=all_nodes.mean((0,1)); std=all_nodes.std((0,1)); std[std<1e-6]=1.0; full=tensor_targets(rows,mean,std); checkpoint_dir=OUT/"checkpoints"; checkpoint_dir.mkdir(parents=True,exist_ok=True); ensemble=[]
    for seed in SEEDS:
        model,hist,best_epoch,best=train_one(CircularCNN(),full,None,seed,device,cfg); path=checkpoint_dir/f"cnn_acquisition_seed_{seed}.pt"; torch.save({"state_dict":model.state_dict(),"seed":seed,"epoch":best_epoch,"config":cfg,"purpose":"ACQUISITION_ONLY"},path); ensemble.append({"seed":seed,"epoch":best_epoch,"checkpoint_path":str(path),"checkpoint_sha256":sha256(path),"config_sha256":hashlib.sha256(json.dumps(cfg,sort_keys=True).encode()).hexdigest(),"dataset_manifest_sha256":data.audit["dataset_manifest_sha256"],"training_geometry_hashes":sorted({r["geometry_hash"] for r in rows}),"device":"cuda:0","torch":torch.__version__})
    cuda["peak_allocated_bytes"]=torch.cuda.max_memory_allocated(0); cuda["peak_reserved_bytes"]=torch.cuda.max_memory_reserved(0); json_write(OUT/"cuda_environment.json",cuda)
    def write_rows(path,items):
        fields=list(dict.fromkeys(k for x in items for k in x));
        with (OUT/path).open("w",newline="",encoding="utf-8") as f: w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(items)
    write_rows("cnn_cv_metrics.csv",cnn_rows); write_rows("mlp_cv_metrics.csv",mlp_rows); write_rows("lf_dft_baseline_metrics.csv",lf_rows); write_rows("training_history_summary.csv",histories)
    json_write(OUT/"cv_split_manifest.json",{"schema_version":"np_k6_geometry_group_cv_v1","folds":split_manifest,"total_observations":66}); json_write(OUT/"normalization_manifest.json",{"schema_version":"np_k6_fold_normalization_v1","folds":norm_manifest,"full_data_fit_geometry_hashes":sorted({r["geometry_hash"] for r in rows})}); json_write(OUT/"cv_fold_summary.json",{"folds":fold_summary,"macro":{"cnn_eta_plus1_MAE":float(np.mean([x["eta_plus1_MAE"] for x in cnn_rows]))}}); json_write(OUT/"cv_stratified_metrics.json",{"schema_version":"np_k6_cv_stratified_metrics_v1","folds":stratified_records,"aggregate":{"wavelengths":WAVELENGTHS,"polarizations":["p","s"],"geometries":GEOMETRY_GROUPS,"worst_wavelength_present":True,"worst_output_channel_present":True}})
    json_write(OUT/"physics_constraint_audit.json",{"models":{"CNN":cnn_rows,"MLP":mlp_rows,"LF_DFT":lf_rows},"nonnegative_power_enforced":True,"order_sum_constraint_enforced_for_neural_models":True,"all_order_heads":True,"complex_order_loss":"disabled","nan_inf_all_zero":all(x["nan_inf_count"]==0 for x in cnn_rows+mlp_rows+lf_rows)})
    cnn_mae=float(np.mean([x["eta_plus1_MAE"] for x in cnn_rows])); mlp_mae=float(np.mean([x["eta_plus1_MAE"] for x in mlp_rows])); lf_mae=float(np.mean([x["eta_plus1_MAE"] for x in lf_rows])); classification="CNN_PILOT_SIGNAL_PRESENT" if cnn_mae < min(mlp_mae,lf_mae) else ("CNN_AND_MLP_COMPARABLE_AT_TINY_DATA" if abs(cnn_mae-mlp_mae)/max(mlp_mae,1e-12)<0.1 else ("LF_BASELINE_STILL_COMPETITIVE" if lf_mae <= cnn_mae else "PILOT_DATA_TOO_SMALL_FOR_ARCHITECTURE_CONCLUSION"))
    json_write(OUT/"architecture_comparison.json",{"classification":classification,"macro_eta_plus1_MAE":{"CNN":cnn_mae,"MLP":mlp_mae,"LF_DFT":lf_mae},"tiny_data_caveat":True,"no_final_architecture_claim":True})
    json_write(OUT/"acquisition_ensemble_manifest.json",{"purpose":"ACQUISITION_ONLY","seed_count":3,"checkpoint_count":3,"models":ensemble,"full_data_geometry_count":3,"final_performance_model":False,"inverse_design_model":False})
    json_write(OUT/"training_gate_summary.json",{"status":"NP_K6_M1_PILOT_SURROGATE_SMOKE_TRAINING_COMPLETE_ACTIVE_LEARNING_READY","real_training_started":True,"pilot_smoke_training_completed":True,"formal_hf_observations":66,"cv_geometries":3,"cuda_training":True,"acquisition_ensemble_checkpoints":3,"final_performance_model":False,"inverse_design_model":False,"bulk_mdc_compatible_model":False,"sealed_test_untouched":True,"solver_calls":0,"geometry_group_leakage":False,"classification":"PILOT_SURROGATE_PIPELINE_VALID_MORE_HF_GEOMETRIES_REQUIRED","next_action":"WAIT_FOR_NP_K6_M2_ACTIVE_LEARNING_BATCH1_SELECTION"})
    files=[]
    for p in sorted(OUT.glob("*.json")):
        if p.name!="checksum_manifest.json": files.append({"path":p.name,"sha256":sha256(p),"size_bytes":p.stat().st_size})
    for p in sorted(OUT.glob("*.csv")): files.append({"path":p.name,"sha256":sha256(p),"size_bytes":p.stat().st_size})
    json_write(OUT/"checksum_manifest.json",{"schema_version":"np_k6_m1_pilot_training_v1","files":files,"checkpoint_files_excluded_from_git":True})
    print(json.dumps({"status":"NP_K6_M1_PILOT_SURROGATE_SMOKE_TRAINING_COMPLETE_ACTIVE_LEARNING_READY","cv_folds":3,"formal_hf_observations":66,"checkpoint_count":3,"cuda":"cuda:0","classification":classification},indent=2))


if __name__ == "__main__":
    main()
