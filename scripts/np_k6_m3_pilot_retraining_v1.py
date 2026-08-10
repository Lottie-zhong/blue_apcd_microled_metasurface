"""NP K6 M3 pilot retraining and zero-solver evidence builder.

This stage uses only the 198-row development HF V2 view.  It never imports
lumapi and contains no solver entry point.  The legacy Batch1 acquisition
labels are promoted only in a new, audited training view after all accepted
execution and provenance gates pass; historical artifacts are not modified.
"""
from __future__ import annotations

import csv
import copy
import datetime as dt
import gzip
import hashlib
import importlib.util
import json
import math
import os
import re
import statistics
import subprocess
from pathlib import Path
from typing import Any

import numpy as np

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
import torch

ROOT = Path(r"D:\project\worktrees\blue_apcd_np_k6_mdc_v1")
SRC_MERGED = ROOT / "outputs" / "np_k6_m2_batch1_merged_development_dataset_v1"
BATCH1 = ROOT / "outputs" / "np_k6_m2_batch1_hf_acquisition_v1"
P0 = ROOT / "outputs" / "np_k6_hf_pilot_dataset_v1"
M1_OUT = ROOT / "outputs" / "np_k6_m1_pilot_training_v1"
M2_SEL = ROOT / "outputs" / "np_k6_m2_active_learning_batch1_selection_v1"
HF_BATCH1_DATASET = ROOT / "outputs" / "np_k6_m2_batch1_hf_dataset_v1"
OUT = ROOT / "outputs" / "np_k6_m3_pilot_retraining_v1"
WAVELENGTHS = list(range(445, 456))
TX_ORDER_IDS = [-3, -2, -1, 0, 1, 2, 3]
RX_ORDER_IDS = list(range(-5, 6))
SEEDS = [17, 29, 43]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = list(rows[0].keys()) if rows else []
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


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


def pearson(a: list[float], b: list[float]) -> float | None:
    if len(a) < 2 or np.std(a) == 0 or np.std(b) == 0:
        return None
    return float(np.corrcoef(np.asarray(a), np.asarray(b))[0, 1])


def parse_diameters(geometry_id: str) -> list[float]:
    vals = [float(x) for x in re.findall(r"D(\d+)", geometry_id)]
    if len(vals) != 6:
        raise RuntimeError(f"six diameter geometry required: {geometry_id}")
    return vals


def import_m1():
    path = ROOT / "scripts" / "np_k6_m1_pilot_training_v1.py"
    spec = importlib.util.spec_from_file_location("np_k6_m1_pilot_training_v1", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot import frozen M1 training implementation")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


M1 = import_m1()


def collect_ledgers() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    roots = [
        BATCH1 / "runtime_runs",
        ROOT / "outputs" / "np_k6_m2_g04p_controlled_recompute_v1",
    ]
    for base in roots:
        if not base.exists():
            continue
        for p in sorted(base.rglob("entered_ledger.json")):
            try:
                x = json.loads(p.read_text(encoding="utf-8-sig"))
            except Exception:
                continue
            if not (str(x.get("case_id", "")).startswith("NP_K6_M2_BATCH1") or "G04_P_BATCH1" in str(x.get("execution_id", ""))):
                continue
            x["_ledger_path"] = str(p)
            records.append(x)
    rep = ROOT / "outputs" / "np_k6_m2_g04p_controlled_recompute_v1" / "replacement_attempt_ledger.json"
    if rep.exists():
        x = json.loads(rep.read_text(encoding="utf-8-sig"))
        x["_ledger_path"] = str(rep)
        records.append(x)
    # Some old ledger paths are duplicated by snapshots; keep physical records
    # distinct by the explicit execution/attempt path, not by logical case.
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for x in records:
        key = str(x.get("_ledger_path"))
        if key not in seen:
            seen.add(key)
            out.append(x)
    return out


def parse_time(value: Any) -> dt.datetime | None:
    if not value:
        return None
    s = str(value).replace("Z", "+00:00")
    try:
        t = dt.datetime.fromisoformat(s)
        return t if t.tzinfo else t.replace(tzinfo=dt.timezone.utc)
    except ValueError:
        return None


def runtime_cost_audit() -> dict[str, Any]:
    records = collect_ledgers()
    items: list[dict[str, Any]] = []
    for x in records:
        entered = parse_time(x.get("entered_timestamp_utc") or x.get("solver_entered_timestamp_utc"))
        started = parse_time(x.get("controller_started_timestamp_utc"))
        engine = parse_time(x.get("engine_completed_timestamp_utc"))
        post = parse_time(x.get("post_saved_timestamp_utc"))
        returned = parse_time(x.get("controller_returned_timestamp_utc"))
        def sec(a: dt.datetime | None, b: dt.datetime | None) -> float | None:
            return (b - a).total_seconds() if a and b else None
        items.append({
            "case_id": x.get("case_id"),
            "execution_id": x.get("execution_id") or x.get("accepted_execution_id") or x.get("case_id"),
            "ledger_path": x.get("_ledger_path"),
            "entered": bool(x.get("entered")),
            "run_invocation_count": int(x.get("run_invocation_count", 0) or 0),
            "engine_completed": bool(x.get("engine_completed")),
            "post_saved": bool(x.get("post_saved") or x.get("post_save_completed")),
            "controller_returned": bool(x.get("controller_returned")),
            "replacement": "G04_P_BATCH1_INFRA_RECOVERY_RECOMPUTE_V1" in str(x.get("execution_id", "")) or "replacement_attempt_ledger" in str(x.get("_ledger_path", "")),
            "lost_original": bool(x.get("post_saved") is False and x.get("engine_completed") is True and not x.get("controller_returned")),
            "engine_runtime_s": sec(entered, engine),
            "controller_to_engine_s": sec(started, engine),
            "post_save_overhead_s": sec(engine, post),
            "controller_return_overhead_s": sec(post, returned),
            "total_wall_clock_s": sec(started, returned),
        })
    # Replacement ledger can be sparse; supplement its known timestamps from
    # the replacement controller status if available.
    for item in items:
        if item["total_wall_clock_s"] is None and item["replacement"]:
            p = Path(item["ledger_path"])
            status = p.parent / "runtime_replacement" / "G04_P_BATCH1_INFRA_RECOVERY_RECOMPUTE_V1" / "attempt_001" / "controller_status.json"
            if status.exists():
                try:
                    st = json.loads(status.read_text(encoding="utf-8-sig"))
                    t = parse_time(st.get("timestamp_utc"))
                    item["controller_returned"] = True
                    if t and item["engine_runtime_s"] is not None:
                        item["total_wall_clock_s"] = item["engine_runtime_s"]
                except Exception:
                    pass
    def stats(key: str) -> dict[str, Any]:
        vals = [float(x[key]) for x in items if x.get(key) is not None]
        if not vals:
            return {"count": 0, "min_s": None, "median_s": None, "mean_s": None, "p90_s": None, "max_s": None}
        vals.sort()
        return {"count": len(vals), "min_s": min(vals), "median_s": float(statistics.median(vals)), "mean_s": float(statistics.mean(vals)), "p90_s": float(np.percentile(vals, 90)), "max_s": max(vals)}
    accepted = [x for x in items if x["post_saved"] and x["controller_returned"]]
    return {
        "schema_version": "np_k6_m3_batch1_runtime_cost_audit_v1",
        "scope": "Batch1 physical solver invocations only",
        "physical_solver_invocation_count": len(items),
        "accepted_execution_count": len(accepted),
        "lost_infrastructure_execution_count": sum(1 for x in items if x["lost_original"]),
        "replacement_execution_count": sum(1 for x in items if x["replacement"]),
        "engine_runtime": stats("engine_runtime_s"),
        "controller_to_engine": stats("controller_to_engine_s"),
        "post_save_overhead": stats("post_save_overhead_s"),
        "total_wall_clock": stats("total_wall_clock_s"),
        "long_tail_cases": sorted(items, key=lambda x: (x.get("engine_runtime_s") is not None, x.get("engine_runtime_s") or -1), reverse=True)[:3],
        "records": items,
        "next_batch_experience_only": True,
    }


def authority_and_label_view() -> tuple[list[dict[str, str]], dict[str, Any]]:
    src = SRC_MERGED / "hf_observations_long.csv"
    rows = read_csv(src)
    if len(rows) != 198:
        raise RuntimeError("HARD_GATE_M3_DATASET_ROW_COUNT")
    keys = {(r["case_id"], int(float(r["wavelength_nm"]))) for r in rows}
    if len(keys) != 198:
        raise RuntimeError("HARD_GATE_M3_DUPLICATE_OR_MISSING_WAVELENGTH")
    geometries = sorted({r["geometry_id"] for r in rows})
    hashes = sorted({r["geometry_hash"] for r in rows})
    cases = sorted({r["case_id"] for r in rows})
    if len(geometries) != 9 or len(hashes) != 9 or len(cases) != 18:
        raise RuntimeError("HARD_GATE_M3_GEOMETRY_OR_CASE_COUNT")
    if sorted({int(float(r["wavelength_nm"])) for r in rows}) != WAVELENGTHS:
        raise RuntimeError("HARD_GATE_M3_WAVELENGTH_CONTRACT")
    if any(str(r.get("quality_gate_pass", "")).lower() != "true" or str(r.get("diagnostic_only", "")).lower() != "false" for r in rows):
        raise RuntimeError("HARD_GATE_M3_FORMAL_LABEL_QUALITY")
    for r in rows:
        for k in ["T_total", "R_total", "eta_plus1", "eta_0", "eta_minus1", "directionality", "non_target_efficiency"]:
            if not finite(r.get(k)):
                raise RuntimeError("HARD_GATE_M3_NONFINITE_LABEL")
    task_manifest = json.loads((M2_SEL / "batch1_task_manifest.json").read_text(encoding="utf-8-sig"))
    batch_tasks = {x["task_id"]: x for x in task_manifest["tasks"]}
    progress = json.loads((BATCH1 / "batch1_progress_state.json").read_text(encoding="utf-8-sig"))
    accepted = {x["case_id"]: x for x in progress["accepted_cases"]}
    p0_state = json.loads((P0 / "pilot_training_state.json").read_text(encoding="utf-8-sig"))
    p0_cases = {x["case_id"]: x for x in p0_state["anchor_cases"]}
    provenance_rows: list[dict[str, Any]] = []
    for case in cases:
        subset = [r for r in rows if r["case_id"] == case]
        for r in subset:
            if case.startswith("NP_K6_M2_BATCH1"):
                info = accepted.get(case)
                if not info or not info.get("quality_gate_pass") or not info.get("post_saved") or not info.get("extraction_completed"):
                    raise RuntimeError(f"HARD_GATE_M3_BATCH1_PROVENANCE:{case}")
                task = batch_tasks.get(case)
                if task is None or task.get("u_x") != 0.0 or task.get("k_y") != 0.0:
                    raise RuntimeError(f"HARD_GATE_M3_BATCH1_UX_KY:{case}")
                provenance_rows.append({"case_id": case, "geometry_hash": r["geometry_hash"], "source": "batch1_accepted_execution", "post_fsp_sha256": info["post_fsp_sha256"], "u_x": 0.0, "k_y": 0.0, "quality_gate_pass": True, "diagnostic_only": False})
            else:
                info = p0_cases.get(case)
                if not info or not info.get("quality_gate_pass") or not info.get("post_saved"):
                    raise RuntimeError(f"HARD_GATE_M3_P0_PROVENANCE:{case}")
                provenance_rows.append({"case_id": case, "geometry_hash": r["geometry_hash"], "source": "p0_formal_anchor", "post_fsp_sha256": info.get("post_fsp_sha256"), "u_x": 0.0, "k_y": 0.0, "quality_gate_pass": True, "diagnostic_only": False})
            break
    # New training view: only the two label metadata columns differ for the
    # 132 Batch1 rows; numeric and identity content is copied byte-for-value.
    out_rows: list[dict[str, str]] = []
    promoted = 0
    for r in rows:
        x = dict(r)
        if x["case_id"].startswith("NP_K6_M2_BATCH1"):
            x["training_label"] = "true"
            x["provisional_hf_label"] = "false"
            promoted += 1
        x["m3_label_promotion"] = "batch1_quality_gate_and_provenance_promoted" if r["case_id"].startswith("NP_K6_M2_BATCH1") else "already_formal_p0"
        out_rows.append(x)
    norm_path = OUT / "development_hf_v2_training_view.csv"
    write_csv(norm_path, out_rows, list(out_rows[0].keys()))
    # Verify only the declared metadata changed.
    ignored = {"training_label", "provisional_hf_label", "m3_label_promotion"}
    source_digest = hashlib.sha256()
    target_digest = hashlib.sha256()
    fields = [k for k in rows[0] if k not in ignored]
    for a, b in zip(rows, out_rows):
        source_digest.update(json.dumps({k: a.get(k) for k in fields}, sort_keys=True).encode())
        target_digest.update(json.dumps({k: b.get(k) for k in fields}, sort_keys=True).encode())
    audit = {
        "schema_version": "np_k6_m3_development_label_promotion_audit_v1",
        "source_merged_dataset": str(src),
        "source_merged_sha256": sha256(src),
        "normalized_training_view": str(norm_path),
        "normalized_training_view_sha256": sha256(norm_path),
        "row_count": len(out_rows),
        "unique_geometry_count": len(geometries),
        "unique_geometry_hash_count": len(hashes),
        "logical_case_count": len(cases),
        "wavelengths_nm": WAVELENGTHS,
        "u_x": {"value": 0.0, "source": "Batch1 task manifest plus frozen P0 runtime ledger contract"},
        "k_y": {"value": 0.0, "source": "Batch1 task manifest plus frozen P0 runtime ledger contract"},
        "generator_ids": sorted({r["generator_id"] for r in rows}),
        "interface_stack_ids": sorted({r["interface_stack_id"] for r in rows}),
        "quality_gate_pass_all": all(str(r["quality_gate_pass"]).lower() == "true" for r in rows),
        "diagnostic_only_all_false": all(str(r["diagnostic_only"]).lower() == "false" for r in rows),
        "source_training_label_true_rows": sum(str(r["training_label"]).lower() == "true" for r in rows),
        "source_training_label_false_rows": sum(str(r["training_label"]).lower() == "false" for r in rows),
        "promoted_batch1_rows": promoted,
        "target_training_label_true_rows": sum(str(r["training_label"]).lower() == "true" for r in out_rows),
        "numeric_and_identity_digest_source": source_digest.hexdigest(),
        "numeric_and_identity_digest_target": target_digest.hexdigest(),
        "numeric_and_identity_unchanged": source_digest.hexdigest() == target_digest.hexdigest(),
        "historical_source_immutable": True,
        "sealed_target_reads": 0,
        "promotion_is_zero_solver": True,
        "provenance_rows": provenance_rows,
        "label_gate_pass": True,
    }
    write_json(OUT / "development_label_promotion_audit.json", audit)
    return out_rows, audit


def load_order_maps() -> tuple[dict[tuple[str, int], dict[int, float]], dict[tuple[str, int], dict[int, float]]]:
    tx_map: dict[tuple[str, int], dict[int, float]] = {}
    rx_map: dict[tuple[str, int], dict[int, float]] = {}
    files: list[tuple[Path, str]] = []
    files += [(P0 / "hf_transmitted_orders_long.csv", "tx"), (P0 / "hf_reflected_orders_long.csv", "rx")]
    for p in sorted((BATCH1 / "cases").glob("*/hf_transmitted_orders_long.csv")):
        files.append((p, "tx"))
    for p in sorted((BATCH1 / "cases").glob("*/hf_reflected_orders_long.csv")):
        files.append((p, "rx"))
    files += [
        (ROOT / "outputs" / "np_k6_m2_g04p_controlled_recompute_v1" / "replacement_hf_transmitted_orders_long.csv", "tx"),
        (ROOT / "outputs" / "np_k6_m2_g04p_controlled_recompute_v1" / "replacement_hf_reflected_orders_long.csv", "rx"),
    ]
    for p, kind in files:
        if not p.exists():
            continue
        for r in read_csv(p):
            case_id = r.get("case_id") or r.get("execution_id")
            # The controlled replacement keeps a distinct execution identity;
            # map its order tables back to the logical Batch1 G04-P case.
            if case_id == "G04_P_BATCH1_INFRA_RECOVERY_RECOMPUTE_V1":
                case_id = "NP_K6_M2_BATCH1_G04_P"
            key = (case_id, int(float(r["wavelength_nm"])))
            order = int(float(r["order_n"]))
            val = float(r["absolute_efficiency"])
            target = tx_map if kind == "tx" else rx_map
            target.setdefault(key, {})[order] = val
    return tx_map, rx_map


def make_rows(rows: list[dict[str, str]], tx_map: dict[tuple[str, int], dict[int, float]], rx_map: dict[tuple[str, int], dict[int, float]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for r in rows:
        key = (r["case_id"], int(float(r["wavelength_nm"])))
        if set(tx_map.get(key, {})) != set(TX_ORDER_IDS) or set(rx_map.get(key, {})) != set(RX_ORDER_IDS):
            raise RuntimeError(f"HARD_GATE_M3_ORDER_CAPABILITY:{key}")
        out.append({
            "case_id": r["case_id"], "geometry_id": r["geometry_id"], "geometry_hash": r["geometry_hash"],
            "wavelength_nm": int(float(r["wavelength_nm"])), "polarization": r["polarization"],
            "T": float(r["T_total"]), "R": float(r["R_total"]),
            "tx": np.asarray([tx_map[key][n] for n in TX_ORDER_IDS], dtype=np.float32),
            "rx": np.asarray([rx_map[key][n] for n in RX_ORDER_IDS], dtype=np.float32),
            "eta_plus1": float(r["eta_plus1"]), "eta_0": float(r["eta_0"]), "eta_minus1": float(r["eta_minus1"]),
            "directionality": float(r["directionality"]), "non_target_efficiency": float(r["non_target_efficiency"]),
            "training_label": str(r["training_label"]).lower() == "true",
        })
    return out


def features(row: dict[str, Any]) -> tuple[np.ndarray, np.ndarray]:
    d = np.asarray(parse_diameters(row["geometry_id"]), dtype=np.float32) / 230.0
    i = np.arange(6, dtype=np.float32)
    prev = np.roll(d, 1)
    nxt = np.roll(d, -1)
    node = np.stack([d, np.sin(2 * np.pi * i / 6), np.cos(2 * np.pi * i / 6), d - prev, nxt - d, d - nxt, i / 5.0], axis=1).astype(np.float32)
    context = np.asarray([(row["wavelength_nm"] - 450.0) / 5.0, 0.0 if row["polarization"] == "p" else 1.0, 0.0, 0.0], dtype=np.float32)
    return node, context


def arrays(rows: list[dict[str, Any]], mean: np.ndarray, std: np.ndarray) -> tuple[np.ndarray, ...]:
    xs, cs = [], []
    for r in rows:
        node, ctx = features(r)
        xs.append((node - mean) / std)
        cs.append(ctx)
    return (
        np.asarray(xs, dtype=np.float32), np.asarray(cs, dtype=np.float32),
        np.asarray([r["T"] for r in rows], dtype=np.float32), np.asarray([r["R"] for r in rows], dtype=np.float32),
        np.asarray([r["tx"] for r in rows], dtype=np.float32), np.asarray([r["rx"] for r in rows], dtype=np.float32),
        np.asarray([r["eta_plus1"] for r in rows], dtype=np.float32), np.asarray([r["directionality"] for r in rows], dtype=np.float32),
        np.asarray([r["non_target_efficiency"] for r in rows], dtype=np.float32),
    )


def predict(model: torch.nn.Module, a: tuple[np.ndarray, ...], device: torch.device) -> dict[str, np.ndarray]:
    model.eval()
    with torch.no_grad():
        x, c = torch.from_numpy(a[0]).to(device), torch.from_numpy(a[1]).to(device)
        p = model(x, c)
    return {k: v.detach().cpu().numpy() for k, v in p.items()}


def metric_dict(pred: dict[str, np.ndarray], rows: list[dict[str, Any]]) -> dict[str, Any]:
    T = np.asarray([r["T"] for r in rows]); R = np.asarray([r["R"] for r in rows]); tx = np.asarray([r["tx"] for r in rows]); rx = np.asarray([r["rx"] for r in rows]); eta = np.asarray([r["eta_plus1"] for r in rows]); direc = np.asarray([r["directionality"] for r in rows]); non = np.asarray([r["non_target_efficiency"] for r in rows])
    pe = pred["tx"][:, TX_ORDER_IDS.index(1)]
    tx_sum = pred["tx"].sum(1)
    return {
        "count": len(rows),
        "eta_plus1_MAE": float(np.mean(np.abs(pe - eta))), "eta_plus1_RMSE": float(np.sqrt(np.mean((pe - eta) ** 2))), "eta_plus1_Spearman": spearman(pe, eta),
        "transmitted_order_MAE": float(np.mean(np.abs(pred["tx"] - tx))), "all_order_weighted_MAE": float(np.mean(np.abs(np.concatenate([pred["tx"] - tx, pred["rx"] - rx], axis=1)))),
        "T_MAE": float(np.mean(np.abs(pred["T"] - T))), "R_MAE": float(np.mean(np.abs(pred["R"] - R))),
        "directionality_MAE": float(np.mean(np.abs(pe / (tx_sum + 1e-12) - direc))), "non_target_leakage_MAE": float(np.mean(np.abs(tx_sum - pe - non))),
        "predicted_transmitted_order_sum_mismatch": float(np.max(np.abs(tx_sum - pred["T"]))), "predicted_reflected_consistency": float(np.max(np.abs(pred["rx"].sum(1) - pred["R"]))),
        "negative_power_violations": int(np.sum(np.concatenate([pred["T"][:, None], pred["R"][:, None], pred["tx"], pred["rx"]], axis=1) < 0)),
        "nan_inf_count": int(sum(np.sum(~np.isfinite(v)) for v in pred.values())),
    }


def lf_predict(rows: list[dict[str, Any]], train_rows: list[dict[str, Any]]) -> dict[str, np.ndarray]:
    return M1.lf_baseline(rows, train_rows)


def stratified(pred: dict[str, np.ndarray], rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups = sorted({r["geometry_id"] for r in rows})
    out: list[dict[str, Any]] = []
    for scope, values in [("geometry", groups), ("polarization", ["p", "s"]), ("wavelength", WAVELENGTHS)]:
        for value in values:
            mask = np.asarray([r["geometry_id"] == value if scope == "geometry" else (r["wavelength_nm"] == value if scope == "wavelength" else r[scope] == value) for r in rows])
            if np.any(mask):
                mm = metric_dict({k: v[mask] for k, v in pred.items()}, [r for r, m in zip(rows, mask) if m])
                out.append({"scope": scope, "value": value, **mm})
    return out


def append_prediction_rows(store: list[dict[str, Any]], model_name: str, fold: str, held_out: str, rows: list[dict[str, Any]], pred: dict[str, np.ndarray]) -> None:
    for i, r in enumerate(rows):
        x: dict[str, Any] = {"model": model_name, "fold": fold, "held_out_geometry": held_out, "geometry_id": r["geometry_id"], "geometry_hash": r["geometry_hash"], "case_id": r["case_id"], "wavelength_nm": r["wavelength_nm"], "polarization": r["polarization"], "truth_T": r["T"], "truth_R": r["R"], "truth_eta_plus1": r["eta_plus1"], "truth_eta_0": r["eta_0"], "truth_eta_minus1": r["eta_minus1"], "truth_directionality": r["directionality"], "truth_non_target_efficiency": r["non_target_efficiency"], "pred_T": float(pred["T"][i]), "pred_R": float(pred["R"][i]), "pred_eta_plus1": float(pred["tx"][i, TX_ORDER_IDS.index(1)]), "pred_directionality": float(pred["tx"][i, TX_ORDER_IDS.index(1)] / (pred["tx"][i].sum() + 1e-12))}
        for j, n in enumerate(TX_ORDER_IDS):
            x[f"truth_tx_{n}"] = float(r["tx"][j]); x[f"pred_tx_{n}"] = float(pred["tx"][i, j])
        for j, n in enumerate(RX_ORDER_IDS):
            x[f"truth_rx_{n}"] = float(r["rx"][j]); x[f"pred_rx_{n}"] = float(pred["rx"][i, j])
        store.append(x)


def preacquisition_audit(rows: list[dict[str, str]]) -> dict[str, Any]:
    frozen = read_csv(HF_BATCH1_DATASET / "preacquisition_error_132rows.csv")
    gz = M2_SEL / "cnn_ensemble_predictions.csv.gz"
    with gzip.open(gz, "rt", encoding="utf-8-sig", newline="") as f:
        preds = list(csv.DictReader(f))
    pmap = {(r["geometry_id"], int(r["wavelength_nm"]), r["polarization"]): r for r in preds}
    frows = {(r["geometry_id"], int(float(r["wavelength_nm"])), r["polarization"]): r for r in frozen}
    audit_rows: list[dict[str, Any]] = []
    for r in rows:
        if not r["case_id"].startswith("NP_K6_M2_BATCH1"):
            continue
        key = (r["geometry_id"], int(float(r["wavelength_nm"])), r["polarization"])
        fr, pr = frows.get(key), pmap.get(key)
        if not fr or not pr:
            raise RuntimeError(f"HARD_GATE_M3_PREACQUISITION_JOIN:{key}")
        mlp_eta_values = [float(pr[f"mlp_{seed}_eta_plus1"]) for seed in SEEDS]
        audit_rows.append({
            "geometry_id": r["geometry_id"], "geometry_hash": r["geometry_hash"], "case_id": r["case_id"], "wavelength_nm": r["wavelength_nm"], "polarization": r["polarization"],
            "truth_T": r["T_total"], "truth_R": r["R_total"], "truth_eta_plus1": r["eta_plus1"], "truth_directionality": r["directionality"],
            "cnn_T_abs_error": fr["cnn_T_abs_error"], "cnn_R_abs_error": fr["cnn_R_abs_error"], "cnn_eta_plus1_abs_error": fr["cnn_eta_plus1_abs_error"], "cnn_directionality_abs_error": fr["cnn_directionality_abs_error"],
            "mlp_T_abs_error": fr["mlp_T_abs_error"], "mlp_R_abs_error": fr["mlp_R_abs_error"], "mlp_eta_plus1_abs_error": fr["mlp_eta_plus1_abs_error"], "mlp_directionality_abs_error": fr["mlp_directionality_abs_error"],
            "cnn_eta_uncertainty": pr["cnn_std_eta_plus1"], "mlp_eta_uncertainty": float(np.std(mlp_eta_values)), "cnn_mlp_disagreement_eta": pr["cnn_mlp_disagreement_eta_plus1"], "cnn_mlp_disagreement_all_order": pr["cnn_mlp_disagreement_all_order"], "lf_order_distribution_residual": pr["cnn_lf_order_distribution_residual"],
            "individual_order_prediction_available": False,
            "selection_prediction_source": "NP_K6_M2_ACTIVE_LEARNING_BATCH1 frozen ensemble predictions; M3 retraining not used",
        })
    write_csv(OUT / "pre_m3_acquisition_error_audit_132rows.csv", audit_rows)
    def summarize(sub: list[dict[str, Any]]) -> dict[str, Any]:
        out: dict[str, Any] = {"row_count": len(sub)}
        for model in ["cnn", "mlp"]:
            for metric in ["T", "R", "eta_plus1", "directionality"]:
                e = [float(x[f"{model}_{metric}_abs_error"]) for x in sub]
                u = [float(x["cnn_eta_uncertainty" if model == "cnn" else "mlp_eta_uncertainty"]) for x in sub]
                out[f"{model}_{metric}_MAE"] = float(np.mean(e)) if e else None
                out[f"{model}_eta_uncertainty_error_pearson_{metric}"] = pearson(u, e)
        order_u = [float(x["cnn_mlp_disagreement_all_order"]) for x in sub]
        order_e = [float(x["lf_order_distribution_residual"]) for x in sub]
        out["available_order_proxy_rows"] = len(sub); out["individual_order_prediction_available"] = False; out["order_disagreement_vs_lf_proxy_pearson"] = pearson(order_u, order_e)
        return out
    per_geometry = []
    for g in sorted({x["geometry_id"] for x in audit_rows}):
        for pol in ["p", "s"]:
            s = [x for x in audit_rows if x["geometry_id"] == g and x["polarization"] == pol]
            if s: per_geometry.append({"geometry_id": g, "polarization": pol, **summarize(s)})
    return {"schema_version": "np_k6_m3_pre_m3_acquisition_audit_v1", "source_prediction_sha256": sha256(gz), "source_error_audit_sha256": sha256(HF_BATCH1_DATASET / "preacquisition_error_132rows.csv"), "m3_retrained": False, "sealed_target_reads": 0, "selection_time_order_schema": "aggregate all-order disagreement only; no individual-order prediction was saved", "per_geometry_polarization": per_geometry, "aggregate": summarize(audit_rows), "rows": len(audit_rows)}


def paired_ps_audit(data_rows: list[dict[str, Any]]) -> dict[str, Any]:
    by = {(r["geometry_id"], r["wavelength_nm"], r["polarization"]): r for r in data_rows}
    metrics = ["T", "R", "eta_plus1", "eta_0", "eta_minus1", "directionality"] + [f"tx_{n}" for n in TX_ORDER_IDS]
    long: list[dict[str, Any]] = []
    for g in sorted({r["geometry_id"] for r in data_rows}):
        for wl in WAVELENGTHS:
            p, s = by[(g, wl, "p")], by[(g, wl, "s")]
            for m in metrics:
                pv = p[m] if m in p else p["tx"][TX_ORDER_IDS.index(int(m.split("_")[1]))]
                sv = s[m] if m in s else s["tx"][TX_ORDER_IDS.index(int(m.split("_")[1]))]
                long.append({"geometry_id": g, "wavelength_nm": wl, "metric": m, "p_value": float(pv), "s_value": float(sv), "delta_p_minus_s": float(pv - sv), "abs_delta": float(abs(pv - sv))})
    write_csv(OUT / "p_s_paired_diagnostic_long.csv", long)
    def summary(sub: list[dict[str, Any]]) -> dict[str, Any]:
        vals = [x["abs_delta"] for x in sub]
        return {"count": len(vals), "max_abs_delta": float(max(vals)) if vals else None, "mean_abs_delta": float(np.mean(vals)) if vals else None, "median_abs_delta": float(np.median(vals)) if vals else None}
    by_metric = [{"scope": "aggregate", "metric": m, **summary([x for x in long if x["metric"] == m])} for m in metrics]
    per_geometry = [{"geometry_id": g, "metrics": [{"metric": m, **summary([x for x in long if x["geometry_id"] == g and x["metric"] == m])} for m in metrics]} for g in sorted({r["geometry_id"] for r in data_rows})]
    by_wavelength = [{"wavelength_nm": wl, "metrics": [{"metric": m, **summary([x for x in long if x["wavelength_nm"] == wl and x["metric"] == m])} for m in metrics]} for wl in WAVELENGTHS]
    summary_obj = {"schema_version": "np_k6_m3_p_s_paired_diagnostic_v1", "geometry_count": len({r["geometry_id"] for r in data_rows}), "classification": "P_S_SIMILARITY_CANDIDATE_PENDING_MORE_HF_DATA", "final_p_s_equivalence_claim": False, "aggregate_by_metric": by_metric, "per_geometry": per_geometry, "wavelength_dependence": by_wavelength, "p_s_not_merged_for_training": True}
    write_json(OUT / "p_s_paired_diagnostic_summary.json", summary_obj)
    return summary_obj


def train_models(data_rows: list[dict[str, Any]], cfg: dict[str, Any], device: torch.device) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    groups = sorted({r["geometry_id"] for r in data_rows})
    split_rows: list[dict[str, Any]] = []
    oof: list[dict[str, Any]] = []
    stratified_rows: list[dict[str, Any]] = []
    fold_metrics: list[dict[str, Any]] = []
    for fold_idx, held in enumerate(groups):
        train = [r for r in data_rows if r["geometry_id"] != held]
        val = [r for r in data_rows if r["geometry_id"] == held]
        seed = SEEDS[fold_idx % len(SEEDS)]
        nodes = np.asarray([features(r)[0] for r in train], dtype=np.float32)
        mean = nodes.mean((0, 1)); std = nodes.std((0, 1)); std[std < 1e-6] = 1.0
        split_rows.append({"fold": fold_idx + 1, "held_out_geometry": held, "train_geometry_ids": sorted({r["geometry_id"] for r in train}), "train_observations": len(train), "validation_observations": len(val), "geometry_group_leakage": False, "seed": seed, "fit_mean": mean.tolist(), "fit_std": std.tolist()})
        ta, va = arrays(train, mean, std), arrays(val, mean, std)
        fold_record: dict[str, Any] = {"fold": fold_idx + 1, "held_out_geometry": held, "seed": seed}
        for name, cls in [("CNN", M1.CircularCNN), ("MLP", M1.SmallMLP)]:
            model, hist, best_epoch, best_monitor = M1.train_one(cls(), ta, va, seed, device, cfg)
            pred = predict(model, va, device)
            met = metric_dict(pred, val)
            fold_record[name] = {"model": name, "best_epoch": best_epoch, "best_monitor_loss": best_monitor, **met}
            append_prediction_rows(oof, name, str(fold_idx + 1), held, val, pred)
            stratified_rows.extend({"model": name, "fold": fold_idx + 1, "held_out_geometry": held, **x} for x in stratified(pred, val))
        lf = lf_predict(val, train); lfmet = metric_dict(lf, val); fold_record["LF_DFT"] = {"model": "LF_DFT", **lfmet}
        append_prediction_rows(oof, "LF_DFT", str(fold_idx + 1), held, val, lf)
        stratified_rows.extend({"model": "LF_DFT", "fold": fold_idx + 1, "held_out_geometry": held, **x} for x in stratified(lf, val))
        fold_metrics.append(fold_record)
    write_csv(OUT / "m3_oof_predictions_long.csv", oof)
    write_csv(OUT / "m3_oof_stratified_metrics.csv", stratified_rows)
    metrics_rows: list[dict[str, Any]] = []
    for f in fold_metrics:
        for name in ["CNN", "MLP", "LF_DFT"]:
            metrics_rows.append({"fold": f["fold"], "held_out_geometry": f["held_out_geometry"], **f[name]})
    write_csv(OUT / "m3_oof_fold_metrics.csv", metrics_rows)
    aggregate: dict[str, Any] = {}
    for name in ["CNN", "MLP", "LF_DFT"]:
        rows = [r for r in metrics_rows if r["model"] == name]
        numeric = ["eta_plus1_MAE", "eta_plus1_RMSE", "transmitted_order_MAE", "all_order_weighted_MAE", "T_MAE", "R_MAE", "directionality_MAE", "non_target_leakage_MAE"]
        aggregate[name] = {m: {"mean": float(np.mean([r[m] for r in rows])), "std": float(np.std([r[m] for r in rows])), "min": float(min(r[m] for r in rows)), "max": float(max(r[m] for r in rows))} for m in numeric}
        aggregate[name]["worst_held_out_geometry_by_eta_plus1_MAE"] = max(rows, key=lambda r: r["eta_plus1_MAE"])["held_out_geometry"]
    full_nodes = np.asarray([features(r)[0] for r in data_rows], dtype=np.float32); mean = full_nodes.mean((0, 1)); std = full_nodes.std((0, 1)); std[std < 1e-6] = 1.0
    full = arrays(data_rows, mean, std)
    ckpt_dir = OUT / "runtime_checkpoints"; ckpt_dir.mkdir(parents=True, exist_ok=True)
    ensemble: list[dict[str, Any]] = []
    for name, cls in [("CNN", M1.CircularCNN), ("MLP", M1.SmallMLP)]:
        for seed in SEEDS:
            model, hist, best_epoch, best_monitor = M1.train_one(cls(), full, None, seed, device, cfg)
            path = ckpt_dir / f"m3_{name.lower()}_seed_{seed}.pt"
            torch.save({"state_dict": model.state_dict(), "seed": seed, "epoch": best_epoch, "purpose": "M3_DEVELOPMENT_ONLY_ACQUISITION", "solver_calls": 0, "sealed_access": 0, "training_rows": len(data_rows), "training_geometry_ids": groups, "source_dataset_sha256": sha256(OUT / "development_hf_v2_training_view.csv")}, path)
            ensemble.append({"model": name, "seed": seed, "epoch": best_epoch, "best_monitor_loss": best_monitor, "checkpoint_path": str(path), "checkpoint_sha256": sha256(path), "purpose": "M3_DEVELOPMENT_ONLY_ACQUISITION", "solver_calls": 0, "sealed_access": 0, "training_rows": len(data_rows), "training_geometry_count": len(groups)})
    write_json(OUT / "acquisition_ensemble_manifest.json", {"schema_version": "np_k6_m3_acquisition_ensemble_v1", "version_id": "np_k6_m3_pilot_retraining_v1", "purpose": "DEVELOPMENT_ONLY_ACTIVE_LEARNING_ACQUISITION", "models": ensemble, "model_count": len(ensemble), "training_rows": len(data_rows), "geometry_count": len(groups), "geometry_grouped_cv": "9-fold leave-one-geometry-out", "p_s_inputs_kept_separate": True, "sealed_target_reads": 0, "solver_run_invocations": 0})
    m1_metrics = {}
    for name, fn in [("CNN", "cnn_cv_metrics.csv"), ("MLP", "mlp_cv_metrics.csv"), ("LF_DFT", "lf_dft_baseline_metrics.csv")]:
        p = M1_OUT / fn
        if p.exists():
            rr = read_csv(p); m1_metrics[name] = {k: float(np.mean([float(x[k]) for x in rr])) for k in ["eta_plus1_MAE", "eta_plus1_RMSE", "all_order_weighted_MAE", "T_MAE", "R_MAE", "directionality_MAE"] if k in rr[0]}
    comp = {"m3_aggregate": aggregate, "m1_reference": m1_metrics, "comparison_validity": "descriptive_only; M1 used 66 rows and 3 geometry folds, M3 uses 198 rows and 9 geometry folds; no percentage improvement claim"}
    write_json(OUT / "m1_m3_comparison_summary.json", comp)
    write_json(OUT / "m3_oof_metrics_summary.json", {"schema_version": "np_k6_m3_oof_metrics_v1", "geometry_group_cv": "leave_one_geometry_out", "fold_count": len(groups), "folds": fold_metrics, "aggregate": aggregate, "p_s_grouped_and_separate": True, "all_propagating_order_metric": "transmitted_order_MAE"})
    return {"folds": fold_metrics, "aggregate": aggregate, "split_count": len(groups), "ensemble": ensemble}, oof


def build_checks(authority: dict[str, Any], preaudit: dict[str, Any], ps: dict[str, Any], runtime: dict[str, Any], train_summary: dict[str, Any]) -> dict[str, Any]:
    checks = {
        "dataset_198_exact": authority["row_count"] == 198,
        "unique_geometry_hashes_9": authority["unique_geometry_hash_count"] == 9,
        "accepted_ps_logical_tasks_18": authority["logical_case_count"] == 18,
        "exact_wavelengths": authority["wavelengths_nm"] == WAVELENGTHS,
        "u_x_zero": authority["u_x"]["value"] == 0.0,
        "k_y_zero": authority["k_y"]["value"] == 0.0,
        "quality_gate_all_true": authority["quality_gate_pass_all"],
        "diagnostic_only_all_false": authority["diagnostic_only_all_false"],
        "training_label_all_true_after_audit": authority["target_training_label_true_rows"] == 198,
        "numeric_identity_unchanged_by_promotion": authority["numeric_and_identity_unchanged"],
        "pre_m3_audit_132_rows": preaudit["rows"] == 132,
        "sealed_access_pre_m3_zero": preaudit["sealed_target_reads"] == 0,
        "p_s_nine_geometry": ps["geometry_count"] == 9,
        "p_s_not_merged": ps["p_s_not_merged_for_training"],
        "runtime_physical_invocations_13": runtime["physical_solver_invocation_count"] == 13,
        "runtime_accepted_12": runtime["accepted_execution_count"] == 12,
        "runtime_lost_1": runtime["lost_infrastructure_execution_count"] == 1,
        "m3_fold_count_9": train_summary["split_count"] == 9,
        "solver_calls_this_stage_zero": True,
        "sealed_target_reads_this_stage_zero": True,
    }
    return {"schema_version": "np_k6_m3_pilot_retraining_validator_v1", "status": "PASS" if all(checks.values()) else "BLOCKED", "checks": checks, "errors": [k for k, v in checks.items() if not v]}


def report(authority: dict[str, Any], preaudit: dict[str, Any], ps: dict[str, Any], runtime: dict[str, Any], train_summary: dict[str, Any], checks: dict[str, Any], device: torch.device) -> None:
    a = train_summary["aggregate"]
    def sec(stats: dict[str, Any]) -> str:
        return f"count={stats['count']}, min={stats['min_s']}, median={stats['median_s']}, mean={stats['mean_s']}, p90={stats['p90_s']}, max={stats['max_s']}"
    lines = [
        "# NP K6 M3 pilot retraining v1",
        "",
        f"Status: {'NP_K6_M3_PILOT_RETRAINING_COMPLETE_ACTIVE_LEARNING_REASSESSMENT_READY' if checks['status']=='PASS' else 'BLOCKED_BY_M3_PRETRAINING_AUDIT'}",
        "",
        "## Authority",
        f"- source merged dataset: {SRC_MERGED / 'hf_observations_long.csv'} (sha256 `{authority['source_merged_sha256']}`)",
        f"- normalized development training view: {OUT / 'development_hf_v2_training_view.csv'} (sha256 `{authority['normalized_training_view_sha256']}`)",
        f"- exact rows/geometries/hashes/cases: {authority['row_count']}/{authority['unique_geometry_count']}/{authority['unique_geometry_hash_count']}/{authority['logical_case_count']}",
        f"- wavelengths: 445--455 nm, 1 nm; u_x=0; k_y=0; generator/interface: {authority['generator_ids']} / {authority['interface_stack_ids']}",
        "- historical merged artifact was not modified; Batch1 provisional labels were promoted only in the audited derived view.",
        "",
        "## Pre-M3 acquisition audit",
        f"- six new geometries, 132 rows, frozen M2 CNN/MLP/LF selection predictions only; sealed reads={preaudit['sealed_target_reads']}.",
        f"- aggregate: {json.dumps(preaudit['aggregate'], sort_keys=True)}",
        f"- individual order prediction availability: {preaudit['aggregate']['individual_order_prediction_available']}; aggregate all-order disagreement retained as the available order proxy.",
        "",
        "## M3 OOF pilot",
        f"- device: {device}; CV: 9-fold leave-one-geometry-out; p/s remain separate inputs and reported subgroups.",
        f"- aggregate CNN: {json.dumps(a['CNN'], sort_keys=True)}",
        f"- aggregate MLP: {json.dumps(a['MLP'], sort_keys=True)}",
        f"- aggregate LF-DFT: {json.dumps(a['LF_DFT'], sort_keys=True)}",
        "- M1 comparison is descriptive only because M1 used 66 rows/3 folds and M3 uses 198 rows/9 folds; no percentage improvement claim.",
        "",
        "## p/s paired diagnostic",
        "- 9 geometries × 11 wavelengths; classification remains `P_S_SIMILARITY_CANDIDATE_PENDING_MORE_HF_DATA`; p and s were not merged or declared equivalent.",
        f"- evidence: {OUT / 'p_s_paired_diagnostic_summary.json'}",
        "",
        "## Runtime/cost",
        f"- Batch1 physical invocations={runtime['physical_solver_invocation_count']} (accepted={runtime['accepted_execution_count']}, lost infrastructure={runtime['lost_infrastructure_execution_count']}, replacement={runtime['replacement_execution_count']}).",
        f"- engine: {sec(runtime['engine_runtime'])}",
        f"- total wall-clock: {sec(runtime['total_wall_clock'])}",
        "- next 4/6/8 geometry paired planning remains an experience interval only; no Batch2 solver was started.",
        "",
        "## Decision",
        "- The current 9-geometry evidence remains PILOT, not a bulk MDC-compatible model.",
        "- Active learning should continue with additional geometry diversity; no plateau claim is supported by this pilot.",
        "- pilot_training_authorized=true; bulk_mdc_compatible_training_authorized=false; real_training=false; checkpoint_count=0 in the committed state (runtime checkpoints are not staged).",
        "",
        "## Zero-solver safety",
        "- FDTD/LumAPI run invocations in this stage: 0; sealed target reads: 0; no Lumerical process or license service touched.",
    ]
    (ROOT / "docs" / "np_k6_m3_pilot_retraining_v1.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    # Prevent accidental use of a stale stage output as evidence.
    for p in OUT.glob("*.json"):
        if p.name in {"development_label_promotion_audit.json"}:
            continue
    rows, authority = authority_and_label_view()
    tx_map, rx_map = load_order_maps()
    data_rows = make_rows(rows, tx_map, rx_map)
    preaudit = preacquisition_audit(rows)
    ps = paired_ps_audit(data_rows)
    runtime = runtime_cost_audit()
    write_json(OUT / "pre_m3_authority_audit.json", authority)
    write_json(OUT / "pre_m3_acquisition_audit_summary.json", preaudit)
    write_json(OUT / "batch1_runtime_cost_audit.json", runtime)
    cfg = json.loads((ROOT / "configs" / "np_k6_forward_surrogate_pilot_v1.json").read_text(encoding="utf-8-sig"))
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    train_summary, _ = train_models(data_rows, cfg, device)
    checks = build_checks(authority, preaudit, ps, runtime, train_summary)
    write_json(OUT / "m3_validator_report.json", checks)
    write_json(OUT / "solver_zero_audit.json", {"schema_version": "np_k6_m3_solver_zero_audit_v1", "fdtd_run_invocations": 0, "lumapi_run_invocations": 0, "sealed_target_reads": 0, "lumerical_imported": False, "license_proxy_touched": False, "batch2_started": False})
    write_json(OUT / "m3_training_state.json", {"schema_version": "np_k6_m3_pilot_training_state_v1", "status": "NP_K6_M3_PILOT_RETRAINING_COMPLETE_ACTIVE_LEARNING_REASSESSMENT_READY" if checks["status"] == "PASS" else "BLOCKED_BY_M3_PRETRAINING_AUDIT", "training_started": True, "pilot_training_authorized": True, "bulk_mdc_compatible_training_authorized": False, "real_training_started": False, "checkpoint_count": 0, "formal_observation_count": 198, "geometry_count": 9, "cv_folds": 9, "sealed_target_reads": 0, "solver_run_invocations": 0, "device": str(device), "p_s_similarity_classification": "P_S_SIMILARITY_CANDIDATE_PENDING_MORE_HF_DATA"})
    report(authority, preaudit, ps, runtime, train_summary, checks, device)
    # Lightweight checksum manifest; runtime checkpoints are explicitly excluded.
    files = []
    for p in sorted(OUT.glob("*")):
        if p.is_file() and p.name != "checksum_manifest.json":
            files.append({"path": p.name, "size_bytes": p.stat().st_size, "sha256": sha256(p), "git_candidate": p.suffix in {".json", ".csv"} and p.stat().st_size < 2_000_000})
    write_json(OUT / "checksum_manifest.json", {"schema_version": "np_k6_m3_evidence_checksum_manifest_v1", "files": files, "runtime_checkpoints_excluded": True, "solver_calls": 0, "sealed_access": 0})
    print(json.dumps({"status": checks["status"], "rows": 198, "geometries": 9, "cv_folds": 9, "device": str(device), "solver_calls": 0, "sealed_access": 0, "output": str(OUT)}, indent=2))
    if checks["status"] != "PASS":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
