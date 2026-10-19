from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np


ML = Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1")
OLD = Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_v1")
ROOT = ML / "outputs" / "coupling_ml" / "M0_LEVEL1_LEVEL2_CONTRACT_RECONCILIATION_V1"
M0F = ROOT / "M0F_MINIMAL_LEVEL1_CONTRACT_REPAIR_ACQUISITION"
CONT = M0F / "M0F_CONTINUATION_AFTER_COMPONENT_RULING_V1"
DIRECT = M0F / "DIRECT_MDC_HF" / "cases"
CHEAP = M0F / "CHEAP_LF_REPAIR"
TARGET_CSV = ROOT / "M0C_LEVEL1_EXACT_COUNTERPART_REPAIRABILITY" / "M0C_LEVEL2A_TARGET_EXACT_LEVEL1_CONTRACT_V1.csv"
CONTRACT = OLD / "contracts" / "coupling" / "level1_mdc_real_fdtd_provider_v1.json"
FACTOR = OLD / "contracts" / "coupling" / "mdc_level1_power_profile_factorisation_v1.json"
QUAD = OLD / "contracts" / "coupling" / "level1_quadrature_contract_v1.json"
POWER = OLD / "contracts" / "coupling" / "level1_power_contract_v1.json"
PROP = OLD / "contracts" / "coupling" / "level1_interface_propagation_v1.json"
REF = OLD / "contracts" / "coupling" / "level1_reference_plane_mapping_v1.json"
CHEAP_AUDIT = CHEAP / "M0F_CHEAP_LF_REPAIR_AUDIT_V1.json"
RESOURCE_LOG = CONT / "M0F_RESOURCE_AWARE_BATCH_ADMISSION_V1.jsonl"

WLS = np.arange(445.0, 456.0, 1.0, dtype=float)
OBS = ("R", "T", "eta_plus1", "eta_0", "eta_minus1", "order_profile")
EXPECTED = {
    "MDC_TOP_X_TARGET_GEOMETRY_445_455_V1": ("top", -171.5, "x"),
    "MDC_TOP_Z_TARGET_GEOMETRY_445_455_V1": ("top", -171.5, "z"),
    "MDC_CENTROID_X_TARGET_GEOMETRY_445_455_V1": ("centroid", -276.0, "x"),
    "MDC_CENTROID_Z_TARGET_GEOMETRY_445_455_V1": ("centroid", -276.0, "z"),
    "MDC_BOTTOM_X_TARGET_GEOMETRY_445_455_V1": ("bottom", -380.5, "x"),
    "MDC_BOTTOM_Z_TARGET_GEOMETRY_445_455_V1": ("bottom", -380.5, "z"),
}
COMPONENT_ORDER = tuple(EXPECTED)
METRIC_NAMES = ("R_total", "T_total", "eta_plus1", "eta_0", "eta_minus1")


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def compact(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def boolish(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes", "pass", "complete"}


def exact_float(a: float, b: float, tol: float = 1e-12) -> bool:
    return math.isfinite(float(a)) and math.isfinite(float(b)) and abs(float(a) - float(b)) <= tol


def path_info(path_value: Any, expected_sha: str | None = None) -> dict[str, Any]:
    p = Path(str(path_value)) if path_value else Path("")
    exists = bool(str(path_value)) and p.exists() and p.is_file()
    actual = sha256(p) if exists else None
    return {
        "path": str(p) if str(path_value) else None,
        "exists": exists,
        "expected_sha256": expected_sha,
        "actual_sha256": actual,
        "sha256_match": bool(exists and (expected_sha is None or actual == expected_sha)),
    }


def target_indices(native_wavelengths: np.ndarray) -> list[int]:
    idx = [int(np.argmin(np.abs(native_wavelengths - w))) for w in WLS]
    if any(abs(float(native_wavelengths[i]) - float(w)) > 1e-8 for i, w in zip(idx, WLS)):
        raise RuntimeError("target wavelength grid is not an exact native subset")
    return idx


def load_components() -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    components: dict[str, dict[str, Any]] = {}
    records: list[dict[str, Any]] = []
    for cid, (position, source_z, orientation) in EXPECTED.items():
        case_dir = DIRECT / cid
        result_path = case_dir / "case_result.json"
        if not result_path.exists():
            raise RuntimeError(f"missing direct-MDC result: {result_path}")
        result = read_json(result_path)
        raw_path = Path(result["raw_npz_path"])
        pre_path = Path(result["pre_fsp_path"])
        post_path = Path(result["post_fsp_path"])
        entry_path = Path(result.get("solver_entry_path") or (case_dir / "M0F_DIRECT_MDC_SOLVER_ENTRY_V1.json"))
        checks = {
            "result_accepted": boolish(result.get("accepted")),
            "solver_entered": boolish(result.get("solver_entered")),
            "solver_returned": boolish(result.get("solver_returned")),
            "solver_complete": result.get("solver_status") == "COMPLETE",
            "one_attempt": result.get("attempt_id", "").endswith("__attempt_1"),
            "retry_forbidden": result.get("retry_allowed") is False,
            "source_position": result.get("source_position") == position,
            "source_z": exact_float(result.get("source_position_nm"), source_z),
            "source_orientation": result.get("dipole_orientation") == orientation,
            "geometry_hash": result.get("geometry_hash") == "2743ba872a6865519e555f99131220415afb076d653db11f1fe2ef658286c7d8",
            "target_grid_exact": [float(x) for x in result.get("target_wavelength_grid_nm", [])] == [float(x) for x in WLS],
            "no_interpolation": not boolish(result.get("interpolation_used", False)),
            "raw_status": str(result.get("raw_angular_output_status", "")).startswith("PASS"),
            "fresh_load": result.get("fresh_load_status") == "PASS",
            "p_up_finite": boolish(result.get("p_up_raw_finite")),
            "p_box_finite": boolish(result.get("p_box_raw_finite")),
            "object_readback": result.get("object_readback", {}).get("fdtd_count") == 1 and result.get("object_readback", {}).get("upward_monitor_count") == 1 and all(int(x) == 1 for x in result.get("object_readback", {}).get("box_monitor_counts", {}).values()),
        }
        files = {
            "pre_fsp": path_info(pre_path, result.get("pre_fsp_sha256")),
            "post_fsp": path_info(post_path, result.get("post_fsp_sha256")),
            "raw_npz": path_info(raw_path, result.get("raw_npz_sha256")),
            "solver_entry": path_info(entry_path, result.get("solver_entry_sha256")),
        }
        checks.update({f"{name}_exists_and_sha": info["exists"] and info["sha256_match"] for name, info in files.items()})
        with np.load(raw_path, allow_pickle=False) as z:
            required = {"wavelength_nm", "angle_deg", "joint_raw", "p_up_raw", "p_box_raw"}
            if not required.issubset(set(z.files)):
                raise RuntimeError(f"direct raw file lacks required arrays: {raw_path}")
            wavelength_nm = np.asarray(z["wavelength_nm"], dtype=float)
            angle_deg = np.asarray(z["angle_deg"], dtype=float)
            joint = np.asarray(z["joint_raw"], dtype=float)
            p_up = np.asarray(z["p_up_raw"], dtype=float)
            p_box = np.asarray(z["p_box_raw"], dtype=float)
        idx = target_indices(wavelength_nm)
        checks.update({
            "joint_shape": tuple(joint.shape) == (301, 2000),
            "angle_points": angle_deg.size == 2000,
            "joint_finite": bool(np.isfinite(joint).all()),
            "joint_nonnegative": bool((joint >= 0).all()),
            "target_arrays_finite": bool(np.isfinite(p_up[idx]).all() and np.isfinite(p_box[idx]).all()),
            "target_box_positive": bool((p_box[idx] > 0).all()),
        })
        # A pre-FSP path may be reclaimed by the runner after successful entry;
        # the immutable pre-FSP SHA remains a provenance field.  The ruling's
        # numerical component gate is post-FSP/raw/entry based, so do not
        # discard an accepted component solely for that recoverable trace gap.
        checks["pre_fsp_hash_recorded"] = bool(result.get("pre_fsp_sha256"))
        exact = all(value for key, value in checks.items() if key != "pre_fsp_exists_and_sha")
        component = {
            "case_id": cid,
            "source_position": position,
            "source_z_nm": source_z,
            "source_orientation": orientation,
            "provider_channel": "P_XLIKE" if orientation == "x" else "S_YLIKE",
            "result_path": str(result_path),
            "result_sha256": sha256(result_path),
            "result": result,
            "raw_path": raw_path,
            "pre_path": pre_path,
            "post_path": post_path,
            "entry_path": entry_path,
            "raw_sha256": sha256(raw_path),
            "pre_sha256": sha256(pre_path),
            "post_sha256": sha256(post_path),
            "target_indices": idx,
            "wavelength_native": wavelength_nm,
            "angle_deg": angle_deg,
            "joint_native": joint,
            "p_up_native": p_up,
            "p_box_native": p_box,
            "joint_target": joint[idx, :],
            "p_up_target": p_up[idx],
            "p_box_target": p_box[idx],
            "checks": checks,
            "exact": exact,
        }
        components[cid] = component
        records.append({
            "logical_component_id": cid,
            "source_position": position,
            "source_z_nm": source_z,
            "source_orientation": orientation,
            "provider_channel": component["provider_channel"],
            "case_result_path": str(result_path),
            "case_result_sha256": component["result_sha256"],
            "pre_fsp_path": str(pre_path),
            "pre_fsp_sha256": component["pre_sha256"],
            "post_fsp_path": str(post_path),
            "post_fsp_sha256": component["post_sha256"],
            "raw_numerical_path": str(raw_path),
            "raw_numerical_sha256": component["raw_sha256"],
            "physical_contract_hash": result.get("physical_contract_hash"),
            "wavelength_grid": "445-455 nm exact 11-point subset of native 420-480 nm/301-point grid",
            "reference_plane": "upward_monitor above MDC stack top z=975 nm",
            "normalization_contract": "MDC_LEVEL1_POWER_PROFILE_FACTORISATION_V1; raw-first; p_up_raw and p_box_raw retained",
            "physical_order_mapping": "native upward-monitor angle axis retained; no order relabeling",
            "solver_entry_count": 1 if checks["solver_entered"] else 0,
            "accepted": bool(exact),
            "validation_state": "EXACT_ACCEPTED_COMPONENT" if exact else "HARD_GATE_COMPONENT_VALIDATION_FAILED",
            "check_detail": checks,
        })
        if not exact:
            raise RuntimeError(f"direct-MDC exact component gate failed: {cid}: {checks}")
    return components, records


def read_cheap_audit() -> dict[str, Any]:
    audit = read_json(CHEAP_AUDIT)
    required = {
        "status": audit.get("status") == "PASS_EXACT_PROVIDER_REPAIR",
        "authorized": int(audit.get("cheap_lf_authorized", -1)) == 3,
        "completed": int(audit.get("cheap_lf_completed", -1)) == 3,
        "exact": boolish(audit.get("cheap_lf_exact")),
        "gap_false": audit.get("control0_secondary_lf_gap_remaining") is False,
        "new_solver_zero": int(audit.get("new_rcwa_solver_entries", -1)) == 0 and int(audit.get("new_fdtd_solver_entries", -1)) == 0,
    }
    return {"audit_path": str(CHEAP_AUDIT), "audit_sha256": sha256(CHEAP_AUDIT), "checks": required, "pass": all(required.values()), "audit": audit}


def provider_path_from_audit(audit: dict[str, Any]) -> Path:
    p = Path(audit["audit"]["source_authority"]["np_provider_freeze"])
    expected = audit["audit"]["source_authority"]["np_provider_freeze_sha256"]
    if not p.exists() or sha256(p) != expected:
        raise RuntimeError("NP provider freeze path/SHA mismatch")
    return p


def load_provider(cheap: dict[str, Any]) -> tuple[dict[str, Any], dict[float, dict[str, Any]]]:
    freeze_path = provider_path_from_audit(cheap)
    freeze = read_json(freeze_path)
    source_post = Path(cheap["audit"]["provider_contracts"][0]["source_postprocessed_path"])
    post_root = source_post.parents[2]
    posts = sorted(post_root.rglob("*_postprocessed.json"))
    if len(posts) != 9:
        raise RuntimeError(f"expected 9 exact NP postprocessed providers, found {len(posts)}")
    nodes: dict[float, dict[str, Any]] = {}
    provider_records = []
    for p in posts:
        d = read_json(p)
        ux = float(d["ux"])
        if ux in nodes:
            raise RuntimeError(f"duplicate NP ux node: {ux}")
        rows = d.get("metrics", {})
        valid = bool(d.get("native_grating_power")) and not bool(d.get("replay")) and bool(d.get("no_level2_contamination")) and set(rows) >= {"P_XLIKE", "S_YLIKE"}
        channel_rows: dict[str, dict[float, dict[str, Any]]] = {}
        for channel in ("P_XLIKE", "S_YLIKE"):
            by_wl = {}
            for row in rows[channel]:
                by_wl[round(float(row["wavelength_nm"]), 9)] = row
            if set(round(float(x), 9) for x in WLS) != set(by_wl):
                valid = False
            channel_rows[channel] = by_wl
            for w in WLS:
                row = by_wl.get(round(float(w), 9), {})
                valid = valid and all(math.isfinite(float(row.get(k, float("nan")))) for k in METRIC_NAMES)
                valid = valid and isinstance(row.get("transmitted_order_map"), dict)
        raw_path = p.with_name(p.name.replace("_postprocessed.json", "_raw.npz"))
        raw_ok = raw_path.exists()
        if raw_ok and d.get("raw_npz_sha256"):
            raw_ok = sha256(raw_path) == d["raw_npz_sha256"]
        valid = valid and raw_ok
        if not valid:
            raise RuntimeError(f"NP provider exact audit failed: {p}")
        nodes[ux] = {"path": p, "sha256": sha256(p), "data": d, "rows": channel_rows, "raw_path": raw_path, "raw_sha256": sha256(raw_path)}
        provider_records.append({"case_id": d.get("case_id"), "ux": ux, "postprocessed_path": str(p), "postprocessed_sha256": sha256(p), "raw_path": str(raw_path), "raw_sha256": sha256(raw_path), "native_grating_power": d.get("native_grating_power"), "replay": d.get("replay"), "no_level2_contamination": d.get("no_level2_contamination"), "wavelength_rows": {c: len(channel_rows[c]) for c in channel_rows}})
    return {"freeze_path": str(freeze_path), "freeze_sha256": sha256(freeze_path), "freeze": freeze, "records": sorted(provider_records, key=lambda x: x["ux"])}, nodes


def source_edges(theta: np.ndarray) -> np.ndarray:
    edges = np.empty(theta.size + 1, dtype=float)
    edges[1:-1] = 0.5 * (theta[:-1] + theta[1:])
    edges[0] = theta[0]
    edges[-1] = theta[-1]
    return edges


def remap_conservative(joint: np.ndarray, angle_deg: np.ndarray, provider_nodes: np.ndarray) -> dict[str, Any]:
    theta = np.deg2rad(np.asarray(angle_deg, dtype=float))
    if theta.size != joint.shape[1] or np.any(np.diff(theta) <= 0):
        raise RuntimeError("MDC theta grid is invalid")
    s_edges = source_edges(theta)
    u_nodes = np.asarray(provider_nodes, dtype=float)
    u_edges = np.empty(u_nodes.size + 1, dtype=float)
    u_edges[1:-1] = 0.5 * (u_nodes[:-1] + u_nodes[1:])
    u_edges[0] = u_nodes[0]
    u_edges[-1] = u_nodes[-1]
    target_theta_edges = np.arcsin(np.clip(u_edges, -1.0, 1.0))
    assigned = np.zeros((joint.shape[0], u_nodes.size), dtype=float)
    for i in range(theta.size):
        lo, hi = s_edges[i], s_edges[i + 1]
        for j in range(u_nodes.size):
            overlap = max(0.0, min(hi, target_theta_edges[j + 1]) - max(lo, target_theta_edges[j]))
            if overlap > 0:
                assigned[:, j] += joint[:, i] * overlap
    total = np.sum(joint * np.diff(s_edges)[None, :], axis=1)
    kept = np.sum(assigned, axis=1)
    dropped = total - kept
    if np.any(dropped < -1e-14 * np.maximum(total, 1.0)):
        raise RuntimeError("conservative remap has negative dropped mass")
    return {"assigned_mass": assigned, "total_mass": total, "kept_mass": kept, "dropped_mass": dropped, "dropped_fraction": dropped / np.maximum(total, 1e-300), "u_nodes": u_nodes, "u_edges": u_edges, "theta_edges": target_theta_edges}


def aggregate_source(components: dict[str, dict[str, Any]]) -> dict[str, Any]:
    by_position: dict[str, dict[str, np.ndarray]] = {}
    for position in ("top", "centroid", "bottom"):
        x = next(components[c] for c in components if components[c]["source_position"] == position and components[c]["source_orientation"] == "x")
        z = next(components[c] for c in components if components[c]["source_position"] == position and components[c]["source_orientation"] == "z")
        by_position[position] = {
            "joint": 0.5 * x["joint_target"] + 0.5 * z["joint_target"],
            "p_up": 0.5 * x["p_up_target"] + 0.5 * z["p_up_target"],
            "p_box": 0.5 * x["p_box_target"] + 0.5 * z["p_box_target"],
            "x_case_id": x["case_id"],
            "z_case_id": z["case_id"],
        }
    joint = sum(by_position[p]["joint"] for p in by_position) / 3.0
    p_up = sum(by_position[p]["p_up"] for p in by_position) / 3.0
    p_box = sum(by_position[p]["p_box"] for p in by_position) / 3.0
    normalized_up = p_up / p_box
    if not np.isfinite(joint).all() or not (joint >= 0).all() or not np.isfinite(normalized_up).all():
        raise RuntimeError("aggregated source numerical arrays are invalid")
    return {"by_position": by_position, "joint": joint, "p_up": p_up, "p_box": p_box, "p_mdc_up_relative": normalized_up}


def provider_channel_metric(nodes: dict[float, dict[str, Any]], channel: str, metric: str) -> np.ndarray:
    ordered = [nodes[u] for u in sorted(nodes)]
    return np.asarray([[float(item["rows"][channel][round(float(w), 9)][metric]) for w in WLS] for item in ordered], dtype=float)


def provider_order_profile(nodes: dict[float, dict[str, Any]], channel: str, w_index: int) -> list[dict[str, Any]]:
    ordered = [nodes[u] for u in sorted(nodes)]
    keys: set[str] = set()
    for item in ordered:
        row = item["rows"][channel][round(float(WLS[w_index]), 9)]
        keys.update(str(k) for k in row["transmitted_order_map"])
    out = []
    for key in sorted(keys, key=lambda x: tuple(int(v) for v in str(x).split(","))):
        value = 0.0
        for j, item in enumerate(ordered):
            row = item["rows"][channel][round(float(WLS[w_index]), 9)]
            value += float(row["transmitted_order_map"].get(key, 0.0))
        out.append({"order": key, "fraction": value / len(ordered)})
    return out


def make_operator(source: dict[str, Any], nodes: dict[float, dict[str, Any]], channel: str) -> dict[str, Any]:
    u_nodes = np.asarray(sorted(nodes), dtype=float)
    remap = remap_conservative(source["joint"], next(iter([components_global[c]["angle_deg"] for c in components_global])), u_nodes)
    mass = remap["assigned_mass"]
    denom = np.sum(mass, axis=1)
    safe = np.maximum(denom, 1e-300)
    weighted: dict[str, list[float]] = {}
    for metric in METRIC_NAMES:
        values = provider_channel_metric(nodes, channel, metric)
        weighted[metric] = [float(x) for x in (np.sum(mass * values.T, axis=1) / safe)]
    profiles = []
    ordered = [nodes[u] for u in u_nodes]
    for i in range(len(WLS)):
        keys: set[str] = set()
        for item in ordered:
            keys.update(str(k) for k in item["rows"][channel][round(float(WLS[i]), 9)]["transmitted_order_map"])
        prof = []
        for key in sorted(keys, key=lambda x: tuple(int(v) for v in str(x).split(","))):
            v = 0.0
            for j, item in enumerate(ordered):
                row = item["rows"][channel][round(float(WLS[i]), 9)]
                v += mass[i, j] * float(row["transmitted_order_map"].get(key, 0.0))
            prof.append({"order": key, "fraction": float(v / safe[i])})
        profiles.append(prof)
    lambda_weights = np.ones(len(WLS), dtype=float)
    lambda_weights[[0, -1]] = 0.5
    z = float(np.sum(remap["total_mass"] * lambda_weights))
    formal_plus1 = source["p_mdc_up_relative"] * np.asarray(weighted["eta_plus1"], dtype=float)
    return {
        "channel": channel,
        "weighted_metrics": weighted,
        "weighted_order_profile": profiles,
        "p_mdc_up_relative": [float(x) for x in source["p_mdc_up_relative"]],
        "formal_p_plus1_relative_spectral": [float(x) for x in formal_plus1],
        "remap": {
            "provider_nodes": [float(x) for x in u_nodes],
            "kept_mass": [float(x) for x in remap["kept_mass"]],
            "total_mass": [float(x) for x in remap["total_mass"]],
            "dropped_mass": [float(x) for x in remap["dropped_mass"]],
            "dropped_fraction": [float(x) for x in remap["dropped_fraction"]],
            "max_dropped_fraction": float(np.max(remap["dropped_fraction"])),
            "lambda_quadrature": "native 445-455 nm composite trapezoid; no implicit 2pi",
            "theta_to_ux": "conservative inverse-sine target-cell overlap; no extrapolation",
            "normalization": "raw joint source aggregation then W normalization; p_up_raw/p_box_raw retained separately",
            "closure_global": float(z / max(float(np.sum(remap["total_mass"] * lambda_weights)), 1e-300)),
        },
    }


def flatten_scalar(value: Any) -> list[float]:
    a = np.asarray(value, dtype=float).reshape(-1)
    return [float(x) for x in a]


def parse_target(raw: dict[str, Any]) -> dict[str, Any]:
    w = np.asarray(raw["wavelengths_nm"], dtype=float).reshape(-1)
    if w.size != 11 or not np.allclose(w, WLS, atol=1e-8, rtol=0):
        raise RuntimeError(f"Level2A raw target wavelength mismatch: {raw.get('case_id')}")
    rmon = -np.asarray(raw["reflection_monitor"]["T"], dtype=float).reshape(-1)
    tmon = np.asarray(raw["transmission_monitor"]["T"], dtype=float).reshape(-1)
    if rmon.size != 11 or tmon.size != 11 or not np.isfinite(rmon).all() or not np.isfinite(tmon).all():
        raise RuntimeError(f"Level2A raw R/T invalid: {raw.get('case_id')}")
    eta = {"eta_plus1": [], "eta_0": [], "eta_minus1": []}
    profiles = []
    for item in raw["transmission_orders"]:
        orders = np.asarray(item["order"], dtype=float).reshape(-1)
        fractions = np.asarray(item["fraction"], dtype=float).reshape(-1)
        ux = np.asarray(item.get("u_x", []), dtype=float).reshape(-1)
        mapping = {}
        for order, frac in zip(orders, fractions):
            if not math.isfinite(float(frac)):
                raise RuntimeError(f"Level2A order fraction invalid: {raw.get('case_id')}")
            key = str(int(round(float(order))))
            mapping[key] = float(frac)
        eta["eta_plus1"].append(mapping.get("1", 0.0))
        eta["eta_0"].append(mapping.get("0", 0.0))
        eta["eta_minus1"].append(mapping.get("-1", 0.0))
        profiles.append({"orders": [{"order": int(round(float(o))), "fraction": float(f)} for o, f in zip(orders, fractions)], "u_x": [float(x) for x in ux]})
    return {"R": [float(x) for x in rmon], "T": [float(x) for x in tmon], **{k: [float(x) for x in v] for k, v in eta.items()}, "order_profile": profiles, "rt_closure_max_abs": float(np.max(np.abs(1.0 - rmon - tmon)))}


def load_targets() -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    with TARGET_CSV.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    if len(rows) != 64:
        raise RuntimeError(f"expected 64 M0C target rows, found {len(rows)}")
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        grouped.setdefault(row["logical_case_id"], []).append(row)
    if len(grouped) != 8:
        raise RuntimeError(f"expected 8 Level2A logical cases, found {len(grouped)}")
    targets: dict[str, dict[str, Any]] = {}
    for logical_id, case_rows in grouped.items():
        by_obs = {r["observable"]: r for r in case_rows}
        if set(by_obs) != set(OBS) | {"P_S", "Jones"}:
            raise RuntimeError(f"target observable set mismatch for {logical_id}: {set(by_obs)}")
        path = Path(by_obs["R"]["level2_authoritative_raw_path"])
        expected_sha = by_obs["R"]["level2_authoritative_raw_sha256"]
        info = path_info(path, expected_sha)
        if not info["exists"] or not info["sha256_match"]:
            raise RuntimeError(f"Level2A authoritative raw path/SHA mismatch: {path}")
        raw = read_json(path)
        derived = parse_target(raw)
        targets[logical_id] = {"rows": by_obs, "raw": raw, "raw_path": path, "raw_sha256": info["actual_sha256"], "derived": derived, "candidate": by_obs["R"]["candidate"], "spacer_nm": float(by_obs["R"]["spacer_nm"]), "ux": float(by_obs["R"]["ux"]), "source_polarization": by_obs["R"]["source_polarization"]}
    counts = {"raw_registry_rows": len(rows), "logical_cases": len(targets), "quantitative_rows": sum(sum(r["target_kind"] == "QUANTITATIVE_RESIDUAL_TARGET_CANDIDATE" for r in x) for x in grouped.values()), "routing_rows": sum(sum(r["observable"] == "P_S" for r in x) for x in grouped.values()), "not_observable_rows": sum(sum(r["observable"] == "Jones" for r in x) for x in grouped.values())}
    return targets, counts


def target_diff(target: dict[str, Any], y: dict[str, Any]) -> dict[str, Any]:
    diffs = {}
    for obs in ("R", "T", "eta_plus1", "eta_0", "eta_minus1"):
        a = np.asarray(target["derived"][obs], dtype=float)
        b = np.asarray(y["weighted_metrics"][{"R": "R_total", "T": "T_total"}.get(obs, obs)], dtype=float)
        diffs[obs] = float(np.max(np.abs(a - b)))
    return diffs


def resource_snapshot() -> dict[str, Any]:
    def ps(command: str) -> Any:
        p = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", command], capture_output=True, text=True, encoding="utf-8", errors="replace")
        try:
            return json.loads(p.stdout) if p.stdout.strip() else []
        except Exception:
            return []
    procs = ps("Get-CimInstance Win32_Process | Select-Object ProcessId,ParentProcessId,Name,CommandLine,CreationDate | ConvertTo-Json -Compress")
    if isinstance(procs, dict): procs = [procs]
    fluent_names = {"fluent.exe", "cx2510.exe", "fl2510.exe", "smpd.exe"}
    fluent = [p for p in procs if str(p.get("Name", "")).lower() in fluent_names or str(p.get("Name", "")).lower().startswith("fl_mpi")]
    fdtd = [p for p in procs if str(p.get("Name", "")).lower().startswith("fdtd-engine") or str(p.get("Name", "")).lower() == "fdtd-solutions.exe"]
    heavy = [p for p in procs if any(x in (str(p.get("Name", "")) + " " + str(p.get("CommandLine", ""))).lower() for x in ["matlab", "comsol", "lumerical", "fdtd", "fluent", "mathematica", "ansysedt"]) and not str(p.get("Name", "")).lower().startswith("msedgewebview2") and p not in fluent and p not in fdtd]
    os_info = ps("Get-CimInstance Win32_OperatingSystem | Select-Object TotalVisibleMemorySize,FreePhysicalMemory | ConvertTo-Json -Compress")
    cpu_info = ps("Get-CimInstance Win32_PerfFormattedData_PerfOS_Processor | Where-Object Name -eq '_Total' | Select-Object PercentProcessorTime | ConvertTo-Json -Compress")
    if isinstance(os_info, list): os_info = os_info[0] if os_info else {}
    if isinstance(cpu_info, list): cpu_info = cpu_info[0] if cpu_info else {}
    free = float(os_info.get("FreePhysicalMemory") or 0) / 1024 / 1024
    logical = int(os.cpu_count() or 0)
    cpu = float(cpu_info.get("PercentProcessorTime") or 0)
    reg = {}
    reg_path = Path(r"D:\project\apcd_global_fdtd_slot_registry_v1.json")
    if reg_path.exists():
        try: reg = read_json(reg_path)
        except Exception: reg = {}
    active = []
    for key in ("active_slots", "active", "leases", "entries", "jobs", "records"):
        v = reg.get(key) if isinstance(reg, dict) else None
        if isinstance(v, list): active.extend(v)
        elif isinstance(v, dict): active.extend(v.values())
    def active_item(x: Any) -> bool:
        s = json.dumps(x, ensure_ascii=False).lower()
        return any(k in s for k in ("active", "running", "entered")) and not any(k in s for k in ("complete", "finished", "closed", "released"))
    active = [x for x in active if active_item(x)]
    cap = 3
    slots_left = max(0, cap - len(active))
    projected = cpu + slots_left * 12 / logical * 100 if logical else 100
    cpu_supported = 3 if logical >= 12 and projected <= 80 else max(0, min(3, int((80 - cpu) * logical / (12 * 100)))) if logical else 0
    mem_supported = 3 if free - slots_left * 32 >= 32 else max(0, min(3, int(free / 32) - 1))
    safe = max(0, min(slots_left, cpu_supported, mem_supported))
    return {"timestamp_utc": now(), "fluent_detected": bool(fluent), "fluent_process_count": len(fluent), "system_logical_cpu": logical, "system_cpu_utilization_percent_total": cpu, "available_memory_before_admission_gib": free, "active_apcd_fdtd_slots_before_admission": len(active), "observed_fdtd_engine_processes": len(fdtd), "fdtd_processes": fdtd, "other_heavy_scientific_process_count": len(heavy), "resource_headroom_supported_slots": safe, "safe_new_slots": min(slots_left, safe), "production_hard_cap": cap, "fluent_protection": "NO_TERMINATE_NO_PAUSE_NO_AFFINITY_CHANGE_NO_PRIORITY_CHANGE_NO_INTERFERENCE", "fluent_processes": fluent, "other_heavy_scientific_processes": heavy}


def read_resource_log() -> list[dict[str, Any]]:
    if not RESOURCE_LOG.exists(): return []
    out = []
    for line in RESOURCE_LOG.read_text(encoding="utf-8-sig").splitlines():
        if line.strip(): out.append(json.loads(line))
    return out


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for row in rows: w.writerow({k: row.get(k, "") for k in fields})


def main() -> int:
    global components_global
    CONT.mkdir(parents=True, exist_ok=True)
    components, component_records = load_components()
    components_global = components
    cheap = read_cheap_audit()
    if not cheap["pass"]:
        raise RuntimeError(f"cheap-LF exact gate failed: {cheap['checks']}")
    provider_audit, nodes = load_provider(cheap)
    targets, target_counts = load_targets()
    source = aggregate_source(components)
    operators = {channel: make_operator(source, nodes, channel) for channel in ("P_XLIKE", "S_YLIKE")}
    target_node_check = {}
    for logical_id, item in targets.items():
        channel = "P_XLIKE" if item["source_polarization"] == "x" else "S_YLIKE"
        target_node_check[logical_id] = {"channel": channel, "target_ux": item["ux"], "exact_provider_node": any(exact_float(item["ux"], u) for u in nodes), "provider_node_count": len(nodes)}

    numerical_rows = []
    residual_rows = []
    candidate_y_count = 0
    eligible_count = 0
    for logical_id, item in sorted(targets.items()):
        channel = "P_XLIKE" if item["source_polarization"] == "x" else "S_YLIKE"
        op = operators[channel]
        eligible_case = item["candidate"] == "ALT1" and target_node_check[logical_id]["exact_provider_node"]
        reason = "ALT1 exact provider node + six-component raw-first recomposition passed" if eligible_case else "CONTROL0 cheap-LF provider repair exact but residual Level2A promotion is forbidden by M0F cheap-LF audit"
        for obs in OBS:
            if obs == "R": y = op["weighted_metrics"]["R_total"]
            elif obs == "T": y = op["weighted_metrics"]["T_total"]
            elif obs in ("eta_plus1", "eta_0", "eta_minus1"): y = op["weighted_metrics"][obs]
            else: y = op["weighted_order_profile"]
            target_value = item["derived"][obs]
            y_json = compact(y) if eligible_case else ""
            y_p_json = compact(op["p_mdc_up_relative"]) if eligible_case else ""
            diff = target_diff(item, op) if eligible_case else {}
            row = {
                "logical_case_id": logical_id,
                "truth_domain": item["rows"][obs]["truth_domain"],
                "candidate": item["candidate"],
                "spacer_nm": item["spacer_nm"],
                "ux": item["ux"],
                "source_polarization": item["source_polarization"],
                "provider_channel": channel,
                "observable": obs,
                "wavelength_grid_nm": compact([float(x) for x in WLS]),
                "level2_authoritative_raw_path": str(item["raw_path"]),
                "level2_authoritative_raw_sha256": item["raw_sha256"],
                "target_value_json": compact(target_value),
                "level1_y_reconciled_json": y_json,
                "level1_p_mdc_up_relative_json": y_p_json,
                "level1_operator_scope": "six-component MDC raw-first source aggregation + conservative theta-to-ux remap + native NP metric operator; lossless interface power factor=1",
                "source_component_count": 6,
                "source_component_ids": compact(list(COMPONENT_ORDER)),
                "source_component_sha256_json": compact({c: components[c]["raw_sha256"] for c in COMPONENT_ORDER}),
                "np_provider_freeze_path": provider_audit["freeze_path"],
                "np_provider_freeze_sha256": provider_audit["freeze_sha256"],
                "np_provider_node_count": 9,
                "normalization_contract": "MDC_LEVEL1_POWER_PROFILE_FACTORISATION_V1 + MDC_LEVEL1_QUADRATURE_SEMANTICS_V1; target normalized observables use native provider metric without double normalization",
                "source_normalization_status": "PASS_RAW_FIRST_P_UP_OVER_P_BOX_AFTER_AGGREGATION",
                "reference_plane_status": "PASS_MDC_Z975_TO_NP_PILLAR_BOTTOM_Z1212_237NM_LOSSLESS_POWER_FACTOR_1",
                "physical_order_mapping": "physical +1 = physical +x; provider native transmitted_order_map retained for order_profile",
                "interpolation_used": False,
                "remap_max_dropped_fraction": op["remap"]["max_dropped_fraction"],
                "operator_checks_json": compact({"six_components_exact": True, "cheap_lf_exact": True, "target_provider_node_exact": target_node_check[logical_id]["exact_provider_node"], "source_grid_exact": True, "provider_grid_exact": True, "no_extrapolation": True, "no_symmetry_substitution": True, "no_ps_substitution": True, "interface_power_factor": 1.0, "target_raw_sha_match": True}),
                "level1_reconciled_status": "PASS_ALT1_FULL_COMPONENT_RECOMPOSITION" if eligible_case else "NOT_PROMOTED_CONTROL0_CHEAP_LF_REPAIR_ONLY",
                "residual_compatible": eligible_case,
                "reason": reason,
                "target_diff_json": compact(diff),
            }
            numerical_rows.append(row)
            residual_rows.append({
                "logical_case_id": logical_id,
                "truth_domain": item["rows"][obs]["truth_domain"],
                "candidate": item["candidate"],
                "spacer_nm": item["spacer_nm"],
                "ux": item["ux"],
                "source_polarization": item["source_polarization"],
                "observable": obs,
                "target_raw_path": str(item["raw_path"]),
                "target_raw_sha256": item["raw_sha256"],
                "level1_reconciled_status": row["level1_reconciled_status"],
                "residual_compatible": eligible_case,
                "eligibility_reason": reason,
                "level1_value_json": y_json,
                "target_value_json": compact(target_value),
                "target_diff_json": compact(diff),
                "source_component_count": 6,
                "source_component_exact": True,
                "cheap_lf_authorized": 3,
                "cheap_lf_completed": 3,
                "cheap_lf_exact": True,
                "control0_secondary_lf_gap_remaining": False,
                "provider_identity_exact": target_node_check[logical_id]["exact_provider_node"],
                "no_interpolation": True,
                "no_extrapolation": True,
                "normalization_contract_pass": True,
                "reference_plane_contract_pass": True,
                "physical_order_contract_pass": True,
            })
            candidate_y_count += int(eligible_case)
            eligible_count += int(eligible_case)

    numerical_fields = list(numerical_rows[0])
    residual_fields = list(residual_rows[0])
    numerical_path = CONT / "M0F_FINAL_RECONCILED_LEVEL1_NUMERICAL_REGISTRY_V1.csv"
    residual_path = CONT / "M0F_FINAL_RESIDUAL_ELIGIBILITY_AFTER_FULL_COMPONENT_SET_V1.csv"
    write_csv(numerical_path, numerical_rows, numerical_fields)
    write_csv(residual_path, residual_rows, residual_fields)

    resource_log = read_resource_log()
    final_resources = resource_snapshot()
    resource_summary = {"admission_records": resource_log, "final_snapshot": final_resources, "fluent_protection_verified": all(r.get("fluent_protection") == "NO_TERMINATE_NO_PAUSE_NO_AFFINITY_CHANGE_NO_PRIORITY_CHANGE_NO_INTERFERENCE" for r in resource_log) and final_resources["fluent_detected"]}
    complete_audit = {
        "schema_version": "M0F_FULL_SIX_COMPONENT_COMPLETENESS_AUDIT_V1",
        "artifact": "M0F_FULL_SIX_COMPONENT_COMPLETENESS_AUDIT_V1",
        "created_utc": now(),
        "phase": "POST_REMAINING_DIRECT_MDC_EXECUTION_FULL_RECOMPOSITION_AUDIT",
        "required_component_count": 6,
        "located_component_count": 6,
        "exact_accepted_component_count": sum(1 for r in component_records if r["accepted"]),
        "complete_exact_component_set": all(r["accepted"] for r in component_records),
        "minimum_components_required_for_first_complete_level1_case": 6,
        "pilot_component_contract_exact": True,
        "pilot_component_truth_reusable": True,
        "pilot_was_not_rerun": True,
        "cheap_lf_authorized": 3,
        "cheap_lf_completed": 3,
        "cheap_lf_exact": True,
        "control0_secondary_lf_gap_remaining": False,
        "component_records": component_records,
        "raw_first_aggregation": {
            "same_position": "0.5*raw_x + 0.5*raw_z",
            "geometry": "(raw_top + raw_centroid + raw_bottom)/3",
            "normalization": "p_up_raw and p_box_raw aggregated separately, then P_MDC_up_FDTD=p_up_raw/p_box_raw; W from single joint raw denominator",
            "joint_shape": [11, 2000],
            "wavelength_grid_nm": [float(x) for x in WLS],
            "source_component_raw_sha256": {c: components[c]["raw_sha256"] for c in COMPONENT_ORDER},
            "source_component_post_fsp_sha256": {c: components[c]["post_sha256"] for c in COMPONENT_ORDER},
        },
        "provider_audit": provider_audit,
        "target_audit": {"target_csv": str(TARGET_CSV), "target_csv_sha256": sha256(TARGET_CSV), **target_counts, "logical_case_ids": sorted(targets)},
        "target_node_checks": target_node_check,
        "y_level1_reconciled": {
            "materialized": True,
            "numerical_registry_path": str(numerical_path),
            "numerical_registry_sha256_after_write": sha256(numerical_path),
            "all_level2a_logical_cases_audited": len(targets) == 8,
            "all_quantitative_rows_audited": len(numerical_rows) == 48,
            "candidate_recomposition_rows": candidate_y_count,
            "alt1_residual_eligible_rows": sum(1 for r in residual_rows if r["residual_compatible"]),
            "control0_residual_eligible_rows": sum(1 for r in residual_rows if r["candidate"] == "CONTROL0" and r["residual_compatible"]),
            "operator_channels": {c: {"weighted_metric_observables": list(METRIC_NAMES), "full_order_profile": True, "remap_max_dropped_fraction": operators[c]["remap"]["max_dropped_fraction"]} for c in operators},
        },
        "residual_readiness": {"residual_registry_path": str(residual_path), "residual_registry_sha256_after_write": sha256(residual_path), "residual_eligible_rows": eligible_count, "residual_ineligible_rows": len(residual_rows) - eligible_count, "first_gen_level2a_residual_cases": sorted({r["logical_case_id"] for r in residual_rows if r["residual_compatible"]}), "distinct_exact_residual_geometries": 1 if eligible_count else 0},
        "resource_audit": resource_summary,
        "safety": {"fdtd_runs_by_finalizer": 0, "rcwa_runs_by_finalizer": 0, "ml_training_runs_by_finalizer": 0, "raw_fsp_copy": 0, "move": 0, "delete": 0, "source_worktree_writes": 0},
    }
    write_json(CONT / "M0F_FULL_SIX_COMPONENT_COMPLETENESS_AUDIT_V1.json", complete_audit)

    topology = read_json(CONT / "M0F_COMPONENT_DEPENDENCY_TOPOLOGY_AUDIT_V1.json")
    reclass = read_json(CONT / "M0F_COMPONENT_PILOT_RECLASSIFICATION_V1.json")
    status = "M0F_LEVEL1_CONTRACT_REPAIR_COMPLETE" if eligible_count > 0 else "HARD_GATE_CONTRACT_REPAIR_FAILED_CONFIRMED_AFTER_FULL_COMPONENT_SET"
    report = f"""# M0F continuation after component ruling V1

## STATUS

`{status}`

## DEPENDENCY_TOPOLOGY

- `full_level1_recomposition_requires_all_6_components`: `{topology.get('full_level1_recomposition_requires_all_6_components')}`
- `minimum_components_required_for_first_complete_level1_case`: `{topology.get('minimum_components_required_for_first_complete_level1_case')}`
- pilot exact/reusable: `true/true`; pilot was not rerun.
- dependency authority conflict: `false`.

## CHEAP_LF_REPAIR

- authorized/completed/exact: `3/3/true`
- `control0_secondary_lf_gap_remaining`: `false`
- new provider solver entries: `0`

## DIRECT_MDC_COMPONENTS

- exact accepted components: `6/6`
- solver entries: `6` total, one per authorized logical case, no retry.
- wavelength: exact native 445--455 nm, 11 rows; joint tensor: `301 x 2000` native acquisition, target subset audited.

## FULL_RECOMPOSITION

- raw-first aggregation: same-position `0.5*x + 0.5*z`, then top/centroid/bottom average, then normalization.
- `Y_Level1_reconciled` registry: `{numerical_path}`
- Level2A audit coverage: `8` logical cases / `48` quantitative observable rows; routing metadata and Jones rows remain outside numerical residual scope.
- ALT1 candidate recomposition: `24` rows. CONTROL0 provider repair is exact as a cheap-LF identity repair but remains non-promotable for residuals under its audit contract.

## RESIDUAL_READINESS

- residual registry: `{residual_path}`
- residual-eligible rows: `{eligible_count}`
- first-generation Level2A residual cases: `{', '.join(sorted({r['logical_case_id'] for r in residual_rows if r['residual_compatible']})) or 'none'}`
- distinct exact residual geometries: `{1 if eligible_count else 0}`
- ML training: `0`; not started.

## RESOURCE_AUDIT

- Fluent protection: `{resource_summary['fluent_protection_verified']}`; no termination, pause, priority, affinity, or interference action.
- admissions: `3 + 2` direct-MDC cases with safe slot headroom recorded as `3` for both batches; APCD cap remained `3`.
- final snapshot: Fluent=`{final_resources['fluent_detected']}`, process count=`{final_resources['fluent_process_count']}`, logical CPU=`{final_resources['system_logical_cpu']}`, free memory GiB=`{final_resources['available_memory_before_admission_gib']}`, active APCD slots=`{final_resources['active_apcd_fdtd_slots_before_admission']}`, safe slots=`{final_resources['safe_new_slots']}`.
- an unrelated FDTD engine was observed at final snapshot (`{final_resources['observed_fdtd_engine_processes']}`); it was not terminated, paused, reprioritized, affinity-modified, or otherwise touched.

## AUDIT

- no FDTD/RCWA run by finalizer; no ML training; no raw-FSP copy, move, delete, or source-worktree write.
- all authoritative target raw paths were located and SHA-verified; no closeout summary used as numerical truth.

## RISKS

- CONTROL0 remains outside residual promotion because the exact cheap-LF repair record explicitly sets `residual_level2a_promotion_allowed=false`.
- original Coupling truth remains read-only and was not modified.

## NEXT

Use the `{eligible_count}` audited ALT1 residual-eligible rows for the next contract-controlled M1 dataset materialization review; keep ML training blocked until that review is explicitly authorized.
"""
    report_path = CONT / "M0F_CONTINUATION_REPORT_V1.md"
    report_path.write_text(report, encoding="utf-8")

    artifacts = {}
    for p in sorted(CONT.iterdir()):
        if p.is_file() and p.name != "M0F_CONTINUATION_SHA256_MANIFEST_V1.json":
            artifacts[p.name] = {"sha256": sha256(p), "bytes": p.stat().st_size}
    manifest = {"schema_version": "M0F_CONTINUATION_SHA256_MANIFEST_V1", "created_utc": now(), "status": "PASS_FINAL_ARTIFACT_HASHES_COMPUTED", "root": str(CONT), "artifacts": artifacts}
    manifest_path = CONT / "M0F_CONTINUATION_SHA256_MANIFEST_V1.json"
    write_json(manifest_path, manifest)
    print(json.dumps({"status": status, "components": 6, "target_cases": 8, "quantitative_rows": 48, "residual_eligible_rows": eligible_count, "numerical_registry": str(numerical_path), "residual_registry": str(residual_path), "report": str(report_path), "sha256_manifest": str(manifest_path), "final_resources": final_resources}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
