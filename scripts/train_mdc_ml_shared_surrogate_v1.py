from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import random
import time
from pathlib import Path
from typing import Any, Callable

import joblib
import numpy as np
import pandas as pd
import torch
from scipy.stats import pearsonr, spearmanr
from sklearn.calibration import calibration_curve
from sklearn.dummy import DummyClassifier, DummyRegressor
from sklearn.ensemble import ExtraTreesClassifier, ExtraTreesRegressor, HistGradientBoostingClassifier, HistGradientBoostingRegressor
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import (average_precision_score, balanced_accuracy_score, brier_score_loss,
                             confusion_matrix, f1_score, mean_absolute_error, mean_squared_error,
                             median_absolute_error, precision_score, r2_score, recall_score, roc_auc_score)
from sklearn.preprocessing import StandardScaler


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "configs" / "mdc_ml_shared_surrogate_v1.yaml"


def load_json(path: Path) -> Any: return json.loads(path.read_text(encoding="utf-8"))
def canonical_json(v: Any) -> str: return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
def sha_bytes(v: bytes) -> str: return hashlib.sha256(v).hexdigest()
def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True); tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False), encoding="utf-8", newline="\n"); os.replace(tmp, path)
def safe_float(v: float) -> float | None: return float(v) if np.isfinite(v) else None


def set_seed(seed: int) -> None:
    os.environ["PYTHONHASHSEED"] = str(seed); random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
    torch.use_deterministic_algorithms(True); torch.set_num_threads(int(os.environ.get("OMP_NUM_THREADS", "8")))


def cls_metrics(y: np.ndarray, p: np.ndarray, threshold: float = .5) -> dict[str, Any]:
    y = y.astype(int); p = np.clip(p, 1e-8, 1 - 1e-8); pred = (p >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel(); both = len(np.unique(y)) == 2
    frac_pos, mean_pred = calibration_curve(y, p, n_bins=min(10, max(2, len(y) // 20)), strategy="quantile")
    bins = np.linspace(0, 1, 11); ids = np.minimum(np.digitize(p, bins) - 1, 9)
    ece = sum(np.mean(ids == b) * abs(np.mean(y[ids == b]) - np.mean(p[ids == b])) for b in range(10) if np.any(ids == b))
    return {"n": len(y), "prevalence": float(y.mean()), "roc_auc": safe_float(roc_auc_score(y, p)) if both else None,
            "pr_auc": safe_float(average_precision_score(y, p)) if both else None, "balanced_accuracy": float(balanced_accuracy_score(y, pred)),
            "precision": float(precision_score(y, pred, zero_division=0)), "recall": float(recall_score(y, pred, zero_division=0)),
            "f1": float(f1_score(y, pred, zero_division=0)), "specificity": float(tn / max(tn + fp, 1)),
            "confusion_matrix": [[int(tn), int(fp)], [int(fn), int(tp)]], "brier": float(brier_score_loss(y, p)),
            "ece": float(ece), "reliability": [{"mean_prediction": float(a), "fraction_positive": float(b)} for a, b in zip(mean_pred, frac_pos)]}


def reg_metrics(y: np.ndarray, p: np.ndarray, train_y: np.ndarray) -> dict[str, Any]:
    err = p - y; iqr = float(np.quantile(train_y, .75) - np.quantile(train_y, .25)); iqr = max(iqr, 1e-12)
    return {"n": len(y), "mae": float(mean_absolute_error(y, p)), "rmse": float(mean_squared_error(y, p) ** .5),
            "r2": safe_float(r2_score(y, p)), "spearman": safe_float(spearmanr(y, p).statistic),
            "pearson": safe_float(pearsonr(y, p).statistic), "median_absolute_error": float(median_absolute_error(y, p)),
            "iqr_normalized_mae": float(mean_absolute_error(y, p) / iqr), "prediction_bias": float(np.mean(err)),
            "p90_absolute_error": float(np.quantile(np.abs(err), .9)), "train_iqr": iqr}


def best_threshold(y: np.ndarray, p: np.ndarray) -> float:
    candidates = np.unique(np.quantile(p, np.linspace(.02, .98, 97)))
    return float(max(candidates, key=lambda t: (balanced_accuracy_score(y, p >= t), f1_score(y, p >= t, zero_division=0), -abs(t - .5))))

def bootstrap_pr_auc_ci(y: np.ndarray, p: np.ndarray, seed: int, repeats: int = 1000) -> list[float]:
    rng=np.random.default_rng(seed); values=[]
    for _ in range(repeats):
        ix=rng.integers(0,len(y),len(y)); yy=y[ix]
        if len(np.unique(yy))==2: values.append(float(average_precision_score(yy,p[ix])))
    return [float(np.quantile(values,.025)),float(np.quantile(values,.975))]


class ClassificationBundle:
    def __init__(self, family: str, params: dict[str, Any], seed: int): self.family, self.params, self.seed, self.models = family, params, seed, []
    def fit(self, X: np.ndarray, Y: np.ndarray) -> "ClassificationBundle":
        for j in range(Y.shape[1]):
            y = Y[:, j].astype(int)
            if self.family == "dummy_prevalence": model = DummyClassifier(strategy="prior")
            elif self.family == "dummy_stratified": model = DummyClassifier(strategy="stratified", random_state=self.seed + j)
            elif self.family == "linear": model = LogisticRegression(C=self.params["C"], class_weight="balanced", max_iter=3000, random_state=self.seed)
            elif self.family == "extra_trees": model = ExtraTreesClassifier(**self.params, class_weight="balanced", n_jobs=8, random_state=self.seed + j)
            elif self.family == "hist_gradient_boosting":
                model = HistGradientBoostingClassifier(**self.params, random_state=self.seed + j)
                counts = np.bincount(y, minlength=2); weights = np.where(y == 1, len(y) / max(2 * counts[1], 1), len(y) / max(2 * counts[0], 1)); model.fit(X, y, sample_weight=weights); self.models.append(model); continue
            else: raise ValueError(self.family)
            model.fit(X, y); self.models.append(model)
        return self
    def predict(self, X: np.ndarray) -> np.ndarray: return np.column_stack([m.predict_proba(X)[:, list(m.classes_).index(1)] if 1 in m.classes_ else np.zeros(len(X)) for m in self.models])


class RegressionBundle:
    def __init__(self, family: str, params: dict[str, Any], seed: int): self.family, self.params, self.seed, self.models = family, params, seed, []
    def fit(self, X: np.ndarray, Y: np.ndarray) -> "RegressionBundle":
        for j in range(Y.shape[1]):
            if self.family == "dummy_mean": model = DummyRegressor(strategy="mean")
            elif self.family == "dummy_median": model = DummyRegressor(strategy="median")
            elif self.family == "linear": model = Ridge(alpha=self.params["alpha"])
            elif self.family == "extra_trees": model = ExtraTreesRegressor(**self.params, n_jobs=8, random_state=self.seed + j)
            elif self.family == "hist_gradient_boosting": model = HistGradientBoostingRegressor(**self.params, random_state=self.seed + j)
            else: raise ValueError(self.family)
            model.fit(X, Y[:, j]); self.models.append(model)
        return self
    def predict(self, X: np.ndarray) -> np.ndarray: return np.column_stack([m.predict(X) for m in self.models])
    def dispersion(self, X: np.ndarray) -> np.ndarray | None:
        if self.family != "extra_trees": return None
        return np.column_stack([np.std(np.column_stack([tree.predict(X) for tree in m.estimators_]), axis=1) for m in self.models])


class SharedMLP(torch.nn.Module):
    def __init__(self, input_dim: int, hidden: list[int], dropout: float):
        super().__init__(); self.material_indices = list(range(0, 125, 5)); self.embedding = torch.nn.Embedding(3, 4, padding_idx=0)
        numeric_dim = input_dim - len(self.material_indices); layers: list[torch.nn.Module] = []; last = numeric_dim + 25 * 4
        for h in hidden: layers += [torch.nn.Linear(last, h), torch.nn.ReLU(), torch.nn.Dropout(dropout)]; last = h
        self.trunk = torch.nn.Sequential(*layers); self.cls_head = torch.nn.Linear(last, 4); self.reg_head = torch.nn.Linear(last, 4)
    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        material = x[:, self.material_indices].long(); keep = [i for i in range(x.shape[1]) if i not in self.material_indices]
        z = torch.cat([self.embedding(material).flatten(1), x[:, keep]], dim=1); h = self.trunk(z); return self.cls_head(h), self.reg_head(h)


class MLPBundle:
    def __init__(self, cfg: dict[str, Any], seed: int):
        self.cfg = cfg; self.seed = seed; self.model = None; self.x_scaler = StandardScaler(); self.y_mean = None; self.y_std = None; self.epochs = 0
    def fit(self, X: np.ndarray, YC: np.ndarray, YR: np.ndarray, mask: np.ndarray, validation: tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]) -> "MLPBundle":
        set_seed(self.seed); material_indices = list(range(0, 125, 5)); Xs = self.x_scaler.fit_transform(X); Xs[:, material_indices] = X[:, material_indices]
        self.y_mean = np.nanmean(YR[mask], axis=0); self.y_std = np.nanstd(YR[mask], axis=0); self.y_std[self.y_std < 1e-12] = 1
        yr = np.nan_to_num((YR - self.y_mean) / self.y_std); vx, vyc, vyr, vm = validation; vxs = self.x_scaler.transform(vx); vxs[:, material_indices] = vx[:, material_indices]; vyr = np.nan_to_num((vyr - self.y_mean) / self.y_std)
        self.model = SharedMLP(X.shape[1], self.cfg["hidden"], self.cfg["dropout"]); opt = torch.optim.AdamW(self.model.parameters(), lr=self.cfg["learning_rate"], weight_decay=self.cfg["weight_decay"])
        pos = YC.sum(axis=0); pos_weight = torch.tensor((len(YC) - pos) / np.maximum(pos, 1), dtype=torch.float32); bce = torch.nn.BCEWithLogitsLoss(pos_weight=pos_weight); huber = torch.nn.SmoothL1Loss()
        rng = np.random.default_rng(self.seed); best = math.inf; best_state = None; patience = 0
        for epoch in range(self.cfg["max_epochs"]):
            self.model.train(); order = rng.permutation(len(Xs))
            for start in range(0, len(order), self.cfg["batch_size"]):
                ix = order[start:start + self.cfg["batch_size"]]; tx = torch.tensor(Xs[ix], dtype=torch.float32); tc = torch.tensor(YC[ix], dtype=torch.float32)
                tr = torch.tensor(yr[ix], dtype=torch.float32); tm = torch.tensor(mask[ix], dtype=torch.bool); logits, pred = self.model(tx); loss = bce(logits, tc)
                if tm.any(): loss = loss + huber(pred[tm], tr[tm])
                opt.zero_grad(); loss.backward(); opt.step()
            self.model.eval()
            with torch.no_grad():
                lc, pr = self.model(torch.tensor(vxs, dtype=torch.float32)); vloss = bce(lc, torch.tensor(vyc, dtype=torch.float32)).item()
                if vm.any(): vloss += huber(pr[torch.tensor(vm)], torch.tensor(vyr[vm], dtype=torch.float32)).item()
            if vloss < best - 1e-7: best = vloss; best_state = {k: v.detach().clone() for k, v in self.model.state_dict().items()}; patience = 0
            else: patience += 1
            self.epochs = epoch + 1
            if patience >= self.cfg["patience"]: break
        assert best_state is not None; self.model.load_state_dict(best_state); return self
    def predict(self, X: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        self.model.eval(); xs = self.x_scaler.transform(X); material_indices = list(range(0, 125, 5)); xs[:, material_indices] = X[:, material_indices]
        with torch.no_grad(): logits, reg = self.model(torch.tensor(xs, dtype=torch.float32))
        return torch.sigmoid(logits).numpy(), reg.numpy() * self.y_std + self.y_mean


def load_data(cfg: dict[str, Any]) -> dict[str, Any]:
    root = ROOT / cfg["output_root"]; z = np.load(root / "dataset" / "dataset_v1.npz")
    split_df = pd.read_csv(root / "splits" / "split_records_v1.csv"); split_by_hash = dict(zip(split_df.canonical_geometry_hash, split_df.split))
    splits = np.asarray([split_by_hash[h] for h in z["canonical_hashes"]])
    return {k: z[k] for k in z.files} | {"splits": splits, "split_df": split_df}


def indices(data: dict[str, Any], split: str, regression: bool = False) -> np.ndarray:
    mask = data["splits"] == split
    if regression: mask &= data["regression_mask"]
    return np.where(mask)[0]


def evaluate_classification(Y: np.ndarray, P: np.ndarray, targets: list[str], thresholds: list[float] | None = None) -> dict[str, Any]:
    return {t: cls_metrics(Y[:, j], P[:, j], .5 if thresholds is None else thresholds[j]) for j, t in enumerate(targets)}


def evaluate_regression(Y: np.ndarray, P: np.ndarray, train_y: np.ndarray, targets: list[str]) -> dict[str, Any]:
    return {t: reg_metrics(Y[:, j], P[:, j], train_y[:, j]) for j, t in enumerate(targets)}


def classification_rank(metrics: dict[str, Any]) -> tuple[float, ...]:
    four = metrics["nominal_4d_objective_eligible"]; short = metrics["shortlist_quality_eligible"]
    return (four["pr_auc"] or -1, four["roc_auc"] or -1, -(four["brier"] or 1), short["pr_auc"] or -1)


def regression_rank(metrics: dict[str, Any]) -> tuple[float, ...]:
    vals = list(metrics.values()); return (-float(np.mean([m["iqr_normalized_mae"] for m in vals])), float(np.mean([m["spearman"] or -1 for m in vals])), -max(m["iqr_normalized_mae"] for m in vals))


def pareto_mask(values: np.ndarray) -> np.ndarray:
    transformed = values.copy(); transformed[:, 0:2] *= -1  # minimize widths, maximize proxies
    keep = np.ones(len(values), dtype=bool)
    for i in range(len(values)):
        if np.any(np.all(transformed >= transformed[i], axis=1) & np.any(transformed > transformed[i], axis=1)): keep[i] = False
    return keep


def pareto_metrics(y: np.ndarray, p: np.ndarray, uncertainty: np.ndarray) -> dict[str, Any]:
    true = pareto_mask(y); pred = pareto_mask(p); tp = int(np.sum(true & pred)); true_n = int(true.sum()); pred_n = int(pred.sum())
    rng = np.random.default_rng(20260720); pairs = rng.integers(0, len(y), size=(min(20000, len(y) ** 2), 2)); pairs = pairs[pairs[:, 0] != pairs[:, 1]]
    def dominates(a: np.ndarray, b: np.ndarray) -> bool:
        aa = a.copy(); bb = b.copy(); aa[:2] *= -1; bb[:2] *= -1; return bool(np.all(aa >= bb) and np.any(aa > bb))
    acc = np.mean([dominates(y[a], y[b]) == dominates(p[a], p[b]) for a, b in pairs])
    score = (-p[:, 0] - p[:, 1] + p[:, 2] + p[:, 3]); order = np.argsort(-score)
    k = max(true_n, 1); return {"test_eligible_count": len(y), "true_pareto_size": true_n, "predicted_pareto_size": pred_n,
        "precision": tp / max(pred_n, 1), "recall": tp / max(true_n, 1), "f1": 2 * tp / max(pred_n + true_n, 1),
        "pairwise_domination_accuracy": float(acc), "true_pareto_recall_at_k": float(true[order[:k]].sum() / max(true_n, 1)),
        "true_pareto_recall_at_2k": float(true[order[:min(2*k, len(y))]].sum() / max(true_n, 1)),
        "top_uncertainty_overlap": float(np.mean(pred[np.argsort(-np.mean(uncertainty, axis=1))[:max(pred_n, 1)]]))}


def fit_selected_classifier(spec: dict[str, Any], X: np.ndarray, Y: np.ndarray, seed: int) -> ClassificationBundle:
    return ClassificationBundle(spec["family"], spec["params"], seed).fit(X, Y)
def fit_selected_regressor(spec: dict[str, Any], X: np.ndarray, Y: np.ndarray, seed: int) -> RegressionBundle:
    return RegressionBundle(spec["family"], spec["params"], seed).fit(X, Y)


def calibrate(y: np.ndarray, p: np.ndarray) -> tuple[Any, str, np.ndarray]:
    eps = 1e-6; logit = np.log(np.clip(p, eps, 1-eps) / np.clip(1-p, eps, 1-eps)).reshape(-1, 1)
    sigmoid = LogisticRegression(C=1e6, max_iter=2000).fit(logit, y); ps = sigmoid.predict_proba(logit)[:, 1]
    candidates: list[tuple[float, Any, str, np.ndarray]] = [(brier_score_loss(y, ps), sigmoid, "sigmoid", ps)]
    if min(int(y.sum()), int(len(y)-y.sum())) >= 10:
        iso = IsotonicRegression(out_of_bounds="clip").fit(p, y); pi = iso.predict(p); candidates.append((brier_score_loss(y, pi), iso, "isotonic", pi))
    _, model, method, calibrated = min(candidates, key=lambda x: x[0]); return model, method, calibrated
def apply_calibrator(model: Any, method: str, p: np.ndarray) -> np.ndarray:
    if method == "isotonic": return model.predict(p)
    eps = 1e-6; logit = np.log(np.clip(p, eps, 1-eps) / np.clip(1-p, eps, 1-eps)).reshape(-1,1); return model.predict_proba(logit)[:,1]


def train(config_path: Path = DEFAULT_CONFIG) -> dict[str, Any]:
    cfg = load_json(config_path); set_seed(cfg["training_seeds"][0]); data = load_data(cfg); X = data["X"]; YC = data["y_classification"]; YR = data["y_regression"]; mask = data["regression_mask"]
    out = ROOT / cfg["output_root"]; model_dir = out / "models"; pred_dir = out / "predictions"; metric_dir = out / "metrics"; diag_dir = out / "diagnostics"; unc_dir = out / "uncertainty"
    tr, va, ca, te = [indices(data, s) for s in ("train", "validation", "calibration", "test")]; trr, var, car, ter = [indices(data, s, True) for s in ("train", "validation", "calibration", "test")]
    scaler = StandardScaler().fit(X[tr]); Xs = scaler.transform(X)
    cls_specs = [{"name":"dummy_prevalence","family":"dummy_prevalence","params":{}},{"name":"dummy_stratified","family":"dummy_stratified","params":{}}]
    cls_specs += [{"name":f"linear_C_{c}","family":"linear","params":{"C":c}} for c in cfg["linear"]["classification_C"]]
    cls_specs += [{"name":f"extra_trees_{i}","family":"extra_trees","params":p} for i,p in enumerate(cfg["extra_trees"]["configs"])]
    cls_specs += [{"name":f"hgb_{i}","family":"hist_gradient_boosting","params":p} for i,p in enumerate(cfg["hist_gradient_boosting"]["configs"])]
    reg_specs = [{"name":"dummy_mean","family":"dummy_mean","params":{}},{"name":"dummy_median","family":"dummy_median","params":{}}]
    reg_specs += [{"name":f"ridge_{a}","family":"linear","params":{"alpha":a}} for a in cfg["linear"]["ridge_alpha"]]
    reg_specs += [{"name":f"extra_trees_{i}","family":"extra_trees","params":p} for i,p in enumerate(cfg["extra_trees"]["configs"])]
    reg_specs += [{"name":f"hgb_{i}","family":"hist_gradient_boosting","params":p} for i,p in enumerate(cfg["hist_gradient_boosting"]["configs"])]
    cls_runs={}; reg_runs={}; cls_models={}; reg_models={}; timings={}
    for spec in cls_specs:
        start=time.perf_counter(); m=fit_selected_classifier(spec,Xs[tr],YC[tr],cfg["training_seeds"][0]); p=m.predict(Xs[va]); timings["classification:"+spec["name"]]=time.perf_counter()-start; cls_runs[spec["name"]]=evaluate_classification(YC[va],p,cfg["classification_targets"]); cls_models[spec["name"]]=m
    for spec in reg_specs:
        start=time.perf_counter(); m=fit_selected_regressor(spec,Xs[trr],YR[trr],cfg["training_seeds"][0]); p=m.predict(Xs[var]); timings["regression:"+spec["name"]]=time.perf_counter()-start; reg_runs[spec["name"]]=evaluate_regression(YR[var],p,YR[trr],cfg["regression_targets"]); reg_models[spec["name"]]=m
    mlp_runs=[]; mlp_models=[]; start=time.perf_counter()
    for seed in cfg["training_seeds"]:
        m=MLPBundle(cfg["mlp"],seed).fit(X[tr],YC[tr],YR[tr],mask[tr],(X[va],YC[va],YR[va],mask[va])); pc,pr=m.predict(X[va]); mlp_models.append(m); mlp_runs.append((pc,pr,m.epochs))
    timings["multitask_mlp_3seed"]=time.perf_counter()-start; mlp_pc=np.mean([x[0] for x in mlp_runs],axis=0); mlp_pr=np.mean([x[1] for x in mlp_runs],axis=0)
    cls_runs["multitask_mlp_3seed"]=evaluate_classification(YC[va],mlp_pc,cfg["classification_targets"]); reg_runs["multitask_mlp_3seed"]=evaluate_regression(YR[var],mlp_pr[mask[va]],YR[trr],cfg["regression_targets"])
    cls_best=max(cls_runs,key=lambda k:classification_rank(cls_runs[k])); reg_best=max(reg_runs,key=lambda k:regression_rank(reg_runs[k]))
    cls_spec=next((s for s in cls_specs if s["name"]==cls_best),{"name":cls_best,"family":"multitask_mlp","params":cfg["mlp"]}); reg_spec=next((s for s in reg_specs if s["name"]==reg_best),{"name":reg_best,"family":"multitask_mlp","params":cfg["mlp"]})
    def pred_cls(ix: np.ndarray) -> np.ndarray:
        return np.mean([m.predict(X[ix])[0] for m in mlp_models],axis=0) if cls_spec["family"]=="multitask_mlp" else cls_models[cls_best].predict(Xs[ix])
    def pred_reg(ix: np.ndarray) -> np.ndarray:
        return np.mean([m.predict(X[ix])[1] for m in mlp_models],axis=0) if reg_spec["family"]=="multitask_mlp" else reg_models[reg_best].predict(Xs[ix])
    pva=pred_cls(va); pca=pred_cls(ca); pte_raw=pred_cls(te); calibrators=[]; methods=[]; pca_cal=np.zeros_like(pca); pva_cal=np.zeros_like(pva); pte=np.zeros_like(pte_raw); thresholds=[]
    for j in range(YC.shape[1]):
        cal,method,pcal=calibrate(YC[ca,j].astype(int),pca[:,j]); calibrators.append(cal); methods.append(method); pca_cal[:,j]=pcal; pva_cal[:,j]=apply_calibrator(cal,method,pva[:,j]); pte[:,j]=apply_calibrator(cal,method,pte_raw[:,j]); thresholds.append(best_threshold(YC[va,j],pva_cal[:,j]))
    test_cls=evaluate_classification(YC[te],pte,cfg["classification_targets"],thresholds)
    for j,target in enumerate(cfg["classification_targets"]): test_cls[target]["pr_auc_bootstrap_95_ci"]=bootstrap_pr_auc_ci(YC[te,j],pte[:,j],cfg["split_seed"]+j)
    pcal_reg=pred_reg(car); ptest_reg=pred_reg(ter); pval_reg=pred_reg(var); uncertainty=None
    if reg_spec["family"]=="extra_trees": uncertainty=reg_models[reg_best].dispersion(Xs[ter])
    else:
        boot=[]; rng=np.random.default_rng(cfg["split_seed"])
        if reg_spec["family"]=="multitask_mlp": boot=[m.predict(X[ter])[1] for m in mlp_models]
        else:
            for seed in cfg["training_seeds"]:
                pick=rng.choice(trr,size=len(trr),replace=True); bm=fit_selected_regressor(reg_spec,Xs[pick],YR[pick],seed); boot.append(bm.predict(Xs[ter]))
        uncertainty=np.std(np.stack(boot),axis=0)
    test_reg=evaluate_regression(YR[ter],ptest_reg,YR[trr],cfg["regression_targets"])
    conformal={}; intervals={}
    for coverage in cfg["conformal_coverages"]:
        qs=[]; target_stats={}
        for j,t in enumerate(cfg["regression_targets"]):
            residual=np.abs(YR[car,j]-pcal_reg[:,j]); q=float(np.quantile(residual,min(1,math.ceil((len(residual)+1)*coverage)/len(residual)),method="higher")); qs.append(q)
            covered=np.abs(YR[ter,j]-ptest_reg[:,j])<=q; fam={f:float(np.mean(covered[data["families"][ter]==f])) for f in cfg["families"]}
            target_stats[t]={"quantile":q,"coverage":float(np.mean(covered)),"mean_interval_width":2*q,"family_coverage":fam}
        conformal[str(coverage)]=target_stats; intervals[str(coverage)]=qs
    pareto=pareto_metrics(YR[ter],ptest_reg,uncertainty)
    family_metrics=[]
    for f in cfg["families"]:
        take=data["families"][ter]==f
        for j,t in enumerate(cfg["regression_targets"]): family_metrics.append({"family":f,"target":t,**reg_metrics(YR[ter][take,j],ptest_reg[take,j],YR[trr,j])})
    learning=[]
    for frac in (.25,.5,.75,1.0):
        rng=np.random.default_rng(cfg["split_seed"]+int(frac*100)); n=max(20,int(len(tr)*frac)); sub=np.sort(rng.choice(tr,size=n,replace=False)); subr=sub[mask[sub]]
        shared = MLPBundle(cfg["mlp"],cfg["training_seeds"][0]).fit(X[sub],YC[sub],YR[sub],mask[sub],(X[va],YC[va],YR[va],mask[va])) if "multitask_mlp" in (cls_spec["family"],reg_spec["family"]) else None
        cp = shared.predict(X[va])[0] if cls_spec["family"]=="multitask_mlp" else fit_selected_classifier(cls_spec,Xs[sub],YC[sub],cfg["training_seeds"][0]).predict(Xs[va])
        rp = shared.predict(X[va])[1][mask[va]] if reg_spec["family"]=="multitask_mlp" else fit_selected_regressor(reg_spec,Xs[subr],YR[subr],cfg["training_seeds"][0]).predict(Xs[var])
        cmx=evaluate_classification(YC[va],cp,cfg["classification_targets"])["nominal_4d_objective_eligible"]; rmx=evaluate_regression(YR[var],rp,YR[subr],cfg["regression_targets"])
        learning.append({"fraction":frac,"train_total":len(sub),"train_regression":len(subr),"pr_auc_4d":cmx["pr_auc"],"mean_iqr_nmae":float(np.mean([v["iqr_normalized_mae"] for v in rmx.values()])),"mean_spearman":float(np.mean([v["spearman"] for v in rmx.values()]))})
    # Champion-family OOD diagnostics; test labels never affect fitting or selection.
    ood=[]
    def diagnostic(name:str, train_mask:np.ndarray, test_mask:np.ndarray) -> None:
        tri=np.where(train_mask)[0]; tei=np.where(test_mask)[0]; trri=tri[mask[tri]]; teri=tei[mask[tei]]
        if len(tri)<20 or len(teri)<4 or len(np.unique(YC[tei,2]))<2: return
        shared = MLPBundle(cfg["mlp"],cfg["training_seeds"][0]).fit(X[tri],YC[tri],YR[tri],mask[tri],(X[va],YC[va],YR[va],mask[va])) if "multitask_mlp" in (cls_spec["family"],reg_spec["family"]) else None
        cp = shared.predict(X[tei])[0] if cls_spec["family"]=="multitask_mlp" else fit_selected_classifier(cls_spec,Xs[tri],YC[tri],cfg["training_seeds"][0]).predict(Xs[tei])
        rp = shared.predict(X[tei])[1][mask[tei]] if reg_spec["family"]=="multitask_mlp" else fit_selected_regressor(reg_spec,Xs[trri],YR[trri],cfg["training_seeds"][0]).predict(Xs[teri])
        cm=cls_metrics(YC[tei,2],cp[:,2]); rm=evaluate_regression(YR[teri],rp,YR[trri],cfg["regression_targets"]); ood.append({"diagnostic":name,"train_n":len(tri),"test_n":len(tei),"regression_test_n":len(teri),"eligibility_pr_auc":cm["pr_auc"],"eligibility_roc_auc":cm["roc_auc"],"mean_iqr_nmae":float(np.mean([v["iqr_normalized_mae"] for v in rm.values()])),"mean_spearman":float(np.mean([v["spearman"] for v in rm.values()]))})
    all_idx=np.arange(len(X))
    for f in cfg["families"]: diagnostic("lofo:"+f,data["families"]!=f,data["families"]==f)
    parents=sorted(p for p in np.unique(data["anchor_parents"]) if p)
    for p in parents: diagnostic("anchor_holdout:"+p,data["anchor_parents"]!=p,data["anchor_parents"]==p)
    diagnostic("origin_transfer:FORMAL_2000_to_PRE1",data["origins"]=="FORMAL_2000",data["origins"]=="PRE1")
    diagnostic("origin_transfer:PRE1_to_FORMAL_2000",data["origins"]=="PRE1",data["origins"]=="FORMAL_2000")
    test_four=test_cls["nominal_4d_objective_eligible"]; avg_spear=float(np.mean([v["spearman"] for v in test_reg.values()])); min_spear=min(v["spearman"] for v in test_reg.values()); avg_nmae=float(np.mean([v["iqr_normalized_mae"] for v in test_reg.values()])); cov90=float(np.mean([v["coverage"] for v in conformal["0.9"].values()]))
    gates={"pr_auc_above_prevalence_by_0.15":test_four["pr_auc"]>=test_four["prevalence"]+.15,"roc_auc_at_least_0.75":test_four["roc_auc"]>=.75,"mean_spearman_at_least_0.60":avg_spear>=.60,"minimum_spearman_at_least_0.40":min_spear>=.40,"mean_iqr_nmae_at_most_0.45":avg_nmae<=.45,"pareto_recall_at_2k_at_least_0.50":pareto["true_pareto_recall_at_2k"]>=.50,"conformal_90_coverage_in_0.85_0.95":.85<=cov90<=.95}
    if all(gates.values()): decision="READY_ACTIVE_LEARNING_V1"
    elif learning[-1]["mean_iqr_nmae"] < learning[0]["mean_iqr_nmae"]*.8 and avg_spear>0.35: decision="NEED_MORE_TMM_5000"
    elif any(x.get("mean_spearman",1)<0 for x in ood): decision="NEED_SAMPLER_REVISION"
    else: decision="NEED_MODEL_FEATURE_REVISION"
    selection={"classification_champion":cls_spec,"regression_champion":reg_spec,"mlp_won_classification":cls_spec["family"]=="multitask_mlp","mlp_won_regression":reg_spec["family"]=="multitask_mlp","selection_split":"validation","test_evaluated_once":True,"classification_validation_ranking":sorted(cls_runs,key=lambda k:classification_rank(cls_runs[k]),reverse=True),"regression_validation_ranking":sorted(reg_runs,key=lambda k:regression_rank(reg_runs[k]),reverse=True)}
    (model_dir/"champion").mkdir(parents=True,exist_ok=True)
    cls_payload={"scaler":scaler,"models":cls_models[cls_best].models if cls_spec["family"]!="multitask_mlp" else None,"calibrators":calibrators,"methods":methods,"thresholds":thresholds,"spec":cls_spec}
    reg_payload={"scaler":scaler,"models":reg_models[reg_best].models if reg_spec["family"]!="multitask_mlp" else None,"mlp_states":[{"state_dict":{k:v.detach().cpu().numpy() for k,v in m.model.state_dict().items()},"x_mean":m.x_scaler.mean_,"x_scale":m.x_scaler.scale_,"y_mean":m.y_mean,"y_std":m.y_std,"epochs":m.epochs,"seed":m.seed} for m in mlp_models] if reg_spec["family"]=="multitask_mlp" else None,"mlp_config":cfg["mlp"] if reg_spec["family"]=="multitask_mlp" else None,"spec":reg_spec}
    joblib.dump(cls_payload,model_dir/"champion"/"classification_champion_v1.joblib",compress=3)
    joblib.dump(reg_payload,model_dir/"champion"/"regression_champion_v1.joblib",compress=3)
    atomic_json(metric_dir/"classification_metrics_v1.json",{"validation":cls_runs,"test_champion":test_cls,"calibration_methods":dict(zip(cfg["classification_targets"],methods)),"thresholds":dict(zip(cfg["classification_targets"],thresholds))})
    atomic_json(metric_dir/"regression_metrics_v1.json",{"validation":reg_runs,"test_champion":test_reg}); atomic_json(metric_dir/"calibration_metrics_v1.json",{"classification_methods":dict(zip(cfg["classification_targets"],methods)),"conformal":conformal})
    atomic_json(metric_dir/"pareto_retrieval_v1.json",pareto); metric_dir.mkdir(parents=True,exist_ok=True); pd.DataFrame(family_metrics).to_csv(metric_dir/"family_metrics_v1.csv",index=False); pd.DataFrame(learning).to_csv(metric_dir/"learning_curve_v1.csv",index=False); pd.DataFrame(ood).to_csv(metric_dir/"ood_metrics_v1.csv",index=False)
    unc_dir.mkdir(parents=True,exist_ok=True); atomic_json(unc_dir/"conformal_intervals_v1.json",{"coverages":conformal}); pd.DataFrame({"sample_id":data["sample_ids"][ter],**{f"uncertainty_{t}":uncertainty[:,j] for j,t in enumerate(cfg["regression_targets"])}}).to_csv(unc_dir/"uncertainty_calibration_v1.csv",index=False)
    for name,ix,pc,pr in (("validation",va,pva_cal,pval_reg),("calibration",ca,pca_cal,pcal_reg),("test",te,pte,ptest_reg)):
        pred_dir.mkdir(parents=True,exist_ok=True); frame=pd.DataFrame({"sample_id":data["sample_ids"][ix]})
        for j,t in enumerate(cfg["classification_targets"]): frame[f"prob_{t}"]=pc[:,j]
        reg_lookup={idx:k for k,idx in enumerate(indices(data,name,True))}
        for j,t in enumerate(cfg["regression_targets"]): frame[f"pred_{t}"]=[pr[reg_lookup[idx],j] if idx in reg_lookup else np.nan for idx in ix]
        frame.to_csv(pred_dir/f"{name}_predictions_v1.csv",index=False)
    atomic_json(diag_dir/"model_selection_v1.json",selection); atomic_json(diag_dir/"training_readiness_v1.json",{"decision":decision,"gates":gates,"test_metrics":{"four_d":test_four,"mean_spearman":avg_spear,"minimum_spearman":min_spear,"mean_iqr_nmae":avg_nmae,"coverage_90":cov90,"pareto_recall_at_2k":pareto["true_pareto_recall_at_2k"]},"five_thousand_justified":decision=="NEED_MORE_TMM_5000","recommended_next_stage":decision})
    artifacts=[p for p in out.rglob("*") if p.is_file()]; signature=sha_bytes(canonical_json([(p.relative_to(out).as_posix(),sha_bytes(p.read_bytes())) for p in sorted(artifacts)]).encode()); manifest={"contract_id":cfg["contract_id"],"device":"cpu","threads":int(os.environ.get("OMP_NUM_THREADS","8")),"deterministic":True,"seeds":cfg["training_seeds"],"model_configuration_counts":{"classification":len(cls_specs)+1,"regression":len(reg_specs)+1,"mlp_seeds":len(cfg["training_seeds"])},"training_seconds":timings,"classification_champion":cls_spec,"regression_champion":reg_spec,"test_evaluated_once":True,"decision":decision,"artifact_count":len(artifacts),"output_bytes_before_manifest":sum(p.stat().st_size for p in artifacts),"output_content_signature_before_manifest":signature,"prediction_signatures":{p.name:sha_bytes(p.read_bytes()) for p in pred_dir.glob("*.csv")}}
    atomic_json(out/"manifest_v1.json",manifest); assert sum(p.stat().st_size for p in out.rglob("*") if p.is_file())<=cfg["output_soft_limit_bytes"]
    result={"status":"PASS","manifest":manifest,"selection":selection,"test_classification":test_cls,"test_regression":test_reg,"uncertainty":conformal,"pareto":pareto,"learning_curve":learning,"ood":ood,"decision":decision,"gates":gates}; print(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)); return result


def validate(config_path: Path=DEFAULT_CONFIG) -> dict[str,Any]:
    cfg=load_json(config_path); out=ROOT/cfg["output_root"]; manifest=load_json(out/"manifest_v1.json"); selection=load_json(out/"diagnostics"/"model_selection_v1.json"); readiness=load_json(out/"diagnostics"/"training_readiness_v1.json")
    assert manifest["device"]=="cpu" and manifest["test_evaluated_once"] and selection["selection_split"]=="validation" and selection["test_evaluated_once"]
    assert (out/"models"/"champion"/"classification_champion_v1.joblib").is_file() and (out/"models"/"champion"/"regression_champion_v1.joblib").is_file()
    assert readiness["decision"] in {"READY_ACTIVE_LEARNING_V1","NEED_MODEL_FEATURE_REVISION","NEED_MORE_TMM_5000","NEED_SAMPLER_REVISION"}
    result={"status":"PASS","manifest":manifest,"selection":selection,"readiness":readiness}; print(json.dumps(result,indent=2,sort_keys=True)); return result

def finalize_existing(config_path: Path=DEFAULT_CONFIG) -> dict[str,Any]:
    cfg=load_json(config_path); out=ROOT/cfg["output_root"]; data=load_data(cfg); ter=indices(data,"test",True)
    unc_path=out/"uncertainty"/"uncertainty_calibration_v1.csv"; frame=pd.read_csv(unc_path); test=pd.read_csv(out/"predictions"/"test_predictions_v1.csv").set_index("sample_id")
    correlations={}
    for j,target in enumerate(cfg["regression_targets"]):
        pred=np.asarray([test.loc[s,f"pred_{target}"] for s in data["sample_ids"][ter]],dtype=float); err=np.abs(Y:=data["y_regression"][ter,j]-pred); u=frame[f"uncertainty_{target}"].to_numpy()
        frame[f"absolute_error_{target}"]=err; correlations[target]={"spearman_uncertainty_vs_absolute_error":safe_float(spearmanr(u,err).statistic),"pearson_uncertainty_vs_absolute_error":safe_float(pearsonr(u,err).statistic)}
    frame.to_csv(unc_path,index=False); atomic_json(out/"uncertainty"/"uncertainty_summary_v1.json",{"correlations":correlations,"semantics":"ensemble dispersion is an uncertainty score; only calibration-split conformal intervals are calibrated intervals"})
    te=indices(data,"test"); pred_test=pd.read_csv(out/"predictions"/"test_predictions_v1.csv"); cls_path_metrics=out/"metrics"/"classification_metrics_v1.json"; cls_payload=load_json(cls_path_metrics)
    for j,target in enumerate(cfg["classification_targets"]): cls_payload["test_champion"][target]["pr_auc_bootstrap_95_ci"]=bootstrap_pr_auc_ci(data["y_classification"][te,j],pred_test[f"prob_{target}"].to_numpy(),cfg["split_seed"]+j)
    atomic_json(cls_path_metrics,cls_payload)
    cls_path=out/"models"/"champion"/"classification_champion_v1.joblib"; cls_payload=joblib.load(cls_path)
    if "model" in cls_payload:
        bundle=cls_payload.pop("model"); cls_payload.pop("mlp_models",None); cls_payload["models"]=bundle.models; joblib.dump(cls_payload,cls_path,compress=3)
    reg_path=out/"models"/"champion"/"regression_champion_v1.joblib"; reg_payload=joblib.load(reg_path)
    if "mlp_models" in reg_payload:
        bundles=reg_payload.pop("mlp_models") or []; reg_payload.pop("model",None); reg_payload["models"]=None
        reg_payload["mlp_states"]=[{"state_dict":{k:v.detach().cpu().numpy() for k,v in m.model.state_dict().items()},"x_mean":m.x_scaler.mean_,"x_scale":m.x_scaler.scale_,"y_mean":m.y_mean,"y_std":m.y_std,"epochs":m.epochs,"seed":m.seed} for m in bundles]; reg_payload["mlp_config"]=cfg["mlp"]; joblib.dump(reg_payload,reg_path,compress=3)
    manifest=load_json(out/"manifest_v1.json"); artifacts=[p for p in out.rglob("*") if p.is_file() and p.name!="manifest_v1.json"]
    manifest["artifact_count_excluding_manifest"]=len(artifacts); manifest["output_bytes_excluding_manifest"]=sum(p.stat().st_size for p in artifacts); manifest["output_content_signature_excluding_manifest"]=sha_bytes(canonical_json([(p.relative_to(out).as_posix(),sha_bytes(p.read_bytes())) for p in sorted(artifacts)]).encode()); manifest["uncertainty_error_correlations"]=correlations
    atomic_json(out/"manifest_v1.json",manifest); result={"status":"PASS","correlations":correlations,"manifest":manifest}; print(json.dumps(result,indent=2,sort_keys=True)); return result


def validate_existing_contract_only(config_path=DEFAULT_CONFIG):
    cfg=load_json(config_path); out=ROOT/cfg["output_root"]; c=cfg["champion_artifact_contract"]
    assert cfg["test_seal_contract"]["test_evaluation_count"]==1 and cfg["test_seal_contract"]["test_sealed"]
    assert sha_bytes((out/c["classification"]["artifact_relative_path"]).read_bytes())==c["classification"]["artifact_sha256"]
    assert sha_bytes((out/c["regression"]["artifact_relative_path"]).read_bytes())==c["regression"]["artifact_sha256"]
    return {"status":"PASS"}

def main()->None:
    p=argparse.ArgumentParser(); p.add_argument("--config",type=Path,default=DEFAULT_CONFIG); p.add_argument("--validate-existing-only",action="store_true"); p.add_argument("--finalize-existing-only",action="store_true"); p.add_argument("--fresh-process-read-only",action="store_true"); a=p.parse_args()
    if a.fresh_process_read_only: print(json.dumps(validate_existing_contract_only(a.config)))
    elif a.validate_existing_only: validate(a.config)
    elif a.finalize_existing_only: finalize_existing(a.config)
    else: train(a.config)
if __name__=="__main__": main()
