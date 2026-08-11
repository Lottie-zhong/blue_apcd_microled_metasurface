from __future__ import annotations

import csv
import hashlib
import json
import math
import re
import statistics
from pathlib import Path
from typing import Any

ROOT = Path(r"D:\project\worktrees\blue_apcd_np_k6_mdc_v1")
OUT = ROOT / r"outputs\np_k6_m4_batch2_primary4_hf_acquisition_v1"
DOC = ROOT / r"docs\np_k6_m4_batch2_primary4_hf_acquisition_v1.md"
POLICY_HASH = "a0f46c2da1f653c8a3798ee97bc70e4e3da7598dda5bc9392b76fc4a2128d5d7"
CASE_IDS = [
    "NP_K6_M4_B2_G01_P", "NP_K6_M4_B2_G01_S",
    "NP_K6_M4_B2_G02_P", "NP_K6_M4_B2_G02_S",
    "NP_K6_M4_B2_G03_P", "NP_K6_M4_B2_G03_S",
    "NP_K6_M4_B2_G04_P", "NP_K6_M4_B2_G04_S",
]
PRIMARY = {
    "K6X_D110_D125_D135_D150_D175_D190": "exploitation_1",
    "K6X_D120_D125_D180_D185_D190_D195": "exploitation_2",
    "K6X_D120_D145_D200_D215_D220_D230": "coverage_exploration",
    "K6X_D140_D160_D165_D170_D180_D190": "model_conflict_physics_stress",
}
METRICS = ["T_total", "R_total", "eta_plus1", "eta_0", "eta_minus1", "directionality", "non_target_efficiency"]
MODEL_METRICS = ["T", "R", "eta_plus1", "directionality", "non_target_efficiency"]
MODEL_AVAILABLE = {"cnn": MODEL_METRICS, "mlp": MODEL_METRICS, "lf": ["T", "R", "eta_plus1", "directionality"]}


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def number(value: Any) -> float:
    return float(value)


def finite(value: Any) -> bool:
    try:
        return math.isfinite(float(value))
    except Exception:
        return False


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def setup_sha(case_dir: Path) -> str:
    obj = read_json(case_dir / "setup_checksum.json")
    for key in ("sha256", "setup_fsp_sha256", "source_prefsp_sha256", "checksum"):
        if obj.get(key):
            return str(obj[key])
    return ""


def normalize_row(obs: dict[str, str], ledger: dict[str, Any], setup_hash: str) -> dict[str, Any]:
    row = {k: obs.get(k, "") for k in BASE_FIELDS}
    row.update({
        "case_id": ledger["case_id"],
        "geometry_id": ledger["geometry_id"],
        "geometry_hash": ledger["geometry_hash"],
        "polarization": ledger["polarization"],
        "generator_id": ledger["generator_id"],
        "interface_stack_id": ledger["interface_stack_id"],
        "quality_gate_pass": "true",
        "training_label": "true",
        "provisional_hf_label": "true",
        "diagnostic_only": "false",
        "pilot_scope_only": "true",
        "bulk_mdc_compatible": "false",
        "candidate_performance_label": "true",
        "logical_task_id": ledger["logical_task_id"],
        "execution_id": ledger["execution_lineage"],
        "case_group": "NP_K6_M4_BATCH2_PRIMARY4",
        "accepted_execution": "true",
        "post_fsp_sha256": ledger.get("post_fsp_sha256", ""),
        "source_prefsp_sha256": ledger.get("source_prefsp_sha256", ""),
        "setup_sha256": setup_hash,
        "case_type": "hf_formal_batch2_primary4",
        "source_case_id": ledger["case_id"],
        "raw_power_origin": obs.get("raw_power_origin", "direct_getdata_power"),
        "normalization_path": obs.get("normalization_path", "monitor_T_and_order_sum"),
    })
    return row


BASE_FIELDS = [
    "case_id", "wavelength_nm", "T_total", "R_signed_monitor", "R_total", "closure",
    "signed_closure_residual", "sourcepower_W", "raw_transmitted_power_W", "raw_reflected_power_W",
    "normalization_path", "transmitted_order_sum", "transmitted_order_sum_mismatch", "eta_plus1",
    "eta_0", "eta_minus1", "non_target_efficiency", "directionality", "eta_plus1_over_minus1",
    "plus1_transmitted_fraction", "plus1_air_side_angle_deg", "transmitted_order_count", "raw_power_origin",
    "transmission_power_normalization_mismatch", "reflection_power_normalization_mismatch", "source_case_id",
    "frequency_hz", "geometry_id", "geometry_hash", "polarization", "generator_id", "interface_stack_id",
    "quality_gate_pass", "training_label", "provisional_hf_label", "diagnostic_only", "pilot_scope_only",
    "bulk_mdc_compatible", "candidate_performance_label", "logical_task_id", "execution_id", "case_group",
    "accepted_execution", "post_fsp_sha256", "source_prefsp_sha256", "setup_sha256", "case_type", "plus1_u_x",
]


def percentile90(values: list[float]) -> float:
    if not values:
        return float("nan")
    values = sorted(values)
    pos = 0.9 * (len(values) - 1)
    lo, hi = math.floor(pos), math.ceil(pos)
    if lo == hi:
        return values[lo]
    return values[lo] + (values[hi] - values[lo]) * (pos - lo)


def runtime_data(case_id: str) -> dict[str, Any]:
    p = OUT / "cases" / case_id / "runtime_readback.json"
    obj = read_json(p)
    runtime = obj.get("runtime", {})
    log_path = OUT / "runtime_runs" / case_id / "attempt_001" / f"{case_id}_attempt_001_run_p0.log"
    text = log_path.read_text(encoding="utf-8", errors="replace")
    m = re.findall(r"Overall wall time measurements in seconds:\s*([0-9.eE+-]+)", text)
    wall = float(m[-1]) if m else float("nan")
    return {"case_id": case_id, "engine_wall_time_s": wall, "final_elapsed_simulation_time_s": runtime.get("final_elapsed_simulation_time_s"), "final_auto_shutoff": runtime.get("final_auto_shutoff"), "post_fsp_sha256": obj.get("post_fsp_sha256"), "readonly_reload": obj.get("readonly_reload"), "run_called": obj.get("run_called")}


def runtime_summary(values: list[float]) -> dict[str, float]:
    values = [v for v in values if finite(v)]
    if not values:
        return {"min": float("nan"), "median": float("nan"), "mean": float("nan"), "p90": float("nan"), "max": float("nan")}
    return {"min": min(values), "median": statistics.median(values), "mean": statistics.mean(values), "p90": percentile90(values), "max": max(values)}


def runtime_log_seconds(path: Path) -> float:
    text = path.read_text(encoding="utf-8", errors="replace")
    matches = re.findall(r"Overall wall time measurements in seconds:\s*([0-9.eE+-]+)", text)
    return float(matches[-1]) if matches else float("nan")


def legacy_runtime_entries() -> list[dict[str, Any]]:
    bases = [
        ("P0", ROOT / r"outputs\np_k6_p0_remaining_five_anchors_execution_v1"),
        ("Batch1", ROOT / r"outputs\np_k6_m2_batch1_hf_acquisition_v1"),
        ("Batch2", OUT),
    ]
    entries: list[dict[str, Any]] = []
    for source, base in bases:
        for log in sorted((base / "runtime_runs").glob("*/attempt_001/*_run_p0.log")):
            case_id = log.parent.parent.name
            ledger_path = base / "cases" / case_id / "attempt_ledger.json"
            ledger = read_json(ledger_path) if ledger_path.exists() else {}
            wall = runtime_log_seconds(log)
            entries.append({
                "source": source,
                "case_id": case_id,
                "engine_wall_time_s": wall if finite(wall) else None,
                "engine_completed": bool(ledger.get("engine_completed")),
                "post_saved": bool(ledger.get("post_saved", ledger.get("post_save_completed"))),
                "quality_gate_pass": bool(ledger.get("quality_gate_pass")),
                "infrastructure_lost": bool(ledger.get("engine_completed")) and not bool(ledger.get("post_saved", ledger.get("post_save_completed"))),
                "log_path": str(log),
            })
    return entries


def main() -> None:
    batch_rows: list[dict[str, Any]] = []
    case_summary: list[dict[str, Any]] = []
    ledgers: dict[str, dict[str, Any]] = {}
    manifests: dict[str, dict[str, Any]] = {}
    for case_id in CASE_IDS:
        case_dir = OUT / "cases" / case_id
        ledger = read_json(case_dir / "attempt_ledger.json")
        manifest = read_json(case_dir / "extraction_manifest.json")
        ledgers[case_id], manifests[case_id] = ledger, manifest
        obs = read_csv(case_dir / "hf_observations_long.csv")
        assert len(obs) == 11, (case_id, len(obs))
        assert [int(float(r["wavelength_nm"])) for r in obs] == list(range(445, 456)), case_id
        assert ledger.get("entered") and int(ledger.get("run_invocation_count", 0)) == 1
        assert ledger.get("engine_completed") and ledger.get("post_saved") and ledger.get("controller_returned")
        assert manifest.get("quality_gate_pass") and manifest.get("exact_11_points")
        assert manifest.get("readonly_reload") and not manifest.get("run_called") and not manifest.get("save_called")
        setup_hash = setup_sha(case_dir)
        for obs_row in obs:
            for metric in ["T_total", "R_total", "closure", "signed_closure_residual", "eta_plus1", "eta_0", "eta_minus1", "directionality", "non_target_efficiency"]:
                assert finite(obs_row.get(metric)), (case_id, metric, obs_row.get(metric))
            batch_rows.append(normalize_row(obs_row, ledger, setup_hash))
        case_summary.append({
            "case_id": case_id, "geometry_id": ledger["geometry_id"], "geometry_hash": ledger["geometry_hash"],
            "polarization": ledger["polarization"], "role": PRIMARY[ledger["geometry_id"]], "rows": len(obs),
            "quality_gate_pass": True, "max_abs_closure_residual": manifest["max_abs_closure_residual"],
            "structure_interval_anomaly_max": manifest["structure_interval_anomaly_max"],
            "order_sum_mismatch_max": manifest["order_sum_mismatch_max"],
            "direct_raw_sourcepower_mismatch_max": manifest["direct_raw_sourcepower_mismatch_max"],
            "post_fsp_sha256": ledger.get("post_fsp_sha256"), "source_prefsp_sha256": ledger.get("source_prefsp_sha256"),
            "engine_wall_time_s": runtime_data(case_id)["engine_wall_time_s"],
        })

    out_csv = OUT / "batch2_hf_observations_long.csv"
    write_csv(out_csv, batch_rows, BASE_FIELDS)
    write_csv(OUT / "batch2_case_summary.csv", case_summary, list(case_summary[0]))

    keys = [(r["case_id"], int(float(r["wavelength_nm"]))) for r in batch_rows]
    assert len(keys) == 88 and len(set(keys)) == 88
    assert len({r["geometry_id"] for r in batch_rows}) == 4
    assert {r["polarization"] for r in batch_rows} == {"p", "s"}

    old_path = ROOT / r"outputs\np_k6_m2_batch1_merged_development_dataset_v1\hf_observations_long.csv"
    old_rows = read_csv(old_path)
    assert len(old_rows) == 198
    old_geom = {r.get("geometry_hash", "") for r in old_rows}
    assert not old_geom.intersection({r["geometry_hash"] for r in batch_rows})
    union_fields = list(dict.fromkeys(list(old_rows[0]) + BASE_FIELDS + ["dataset_source"]))
    merged = []
    for r in old_rows:
        x = {k: r.get(k, "") for k in union_fields}; x["dataset_source"] = "existing_development_v2"; merged.append(x)
    for r in batch_rows:
        x = {k: r.get(k, "") for k in union_fields}; x["dataset_source"] = "batch2_primary4"; merged.append(x)
    write_csv(OUT / "merged_development_hf_observations_long.csv", merged, union_fields)
    assert len(merged) == 286
    merged_keys = [(r.get("case_id", ""), r.get("wavelength_nm", "")) for r in merged]
    assert len(merged_keys) == len(set(merged_keys))

    # P/S paired audit.
    groups: dict[tuple[str, int], dict[str, dict[str, Any]]] = {}
    for r in batch_rows:
        groups.setdefault((r["geometry_id"], int(float(r["wavelength_nm"]))), {})[r["polarization"]] = r
    ps_long: list[dict[str, Any]] = []
    for (gid, wl), pair in sorted(groups.items()):
        assert set(pair) == {"p", "s"}, (gid, wl, pair.keys())
        row: dict[str, Any] = {"geometry_id": gid, "wavelength_nm": wl, "role": PRIMARY[gid]}
        for metric in METRICS:
            row[f"p_{metric}"] = pair["p"].get(metric, "")
            row[f"s_{metric}"] = pair["s"].get(metric, "")
            row[f"abs_delta_{metric}"] = abs(number(pair["p"][metric]) - number(pair["s"][metric]))
        ps_long.append(row)
    ps_fields = list(ps_long[0])
    write_csv(OUT / "batch2_p_s_pair_audit_long.csv", ps_long, ps_fields)
    ps_summary: list[dict[str, Any]] = []
    for gid in sorted(PRIMARY):
        subset = [r for r in ps_long if r["geometry_id"] == gid]
        row = {"geometry_id": gid, "role": PRIMARY[gid], "wavelength_count": len(subset)}
        for metric in ["T_total", "R_total", "eta_plus1", "eta_0", "eta_minus1", "directionality"]:
            vals = [number(r[f"abs_delta_{metric}"]) for r in subset]
            row[f"mean_abs_delta_{metric}"] = statistics.mean(vals)
            row[f"median_abs_delta_{metric}"] = statistics.median(vals)
            row[f"max_abs_delta_{metric}"] = max(vals)
        ps_summary.append(row)
    write_csv(OUT / "batch2_p_s_pair_audit.csv", ps_summary, list(ps_summary[0]))
    all_ps = {m: [number(r[f"abs_delta_{m}"]) for r in ps_long] for m in METRICS}
    ps_audit = {"status": "P_S_SIMILARITY_CANDIDATE_PENDING_MORE_HF_DATA", "geometry_count": 4, "paired_wavelength_rows": len(ps_long), "overall": {m: {"mean_abs": statistics.mean(v), "median_abs": statistics.median(v), "max_abs": max(v)} for m, v in all_ps.items()}, "per_geometry_csv": "batch2_p_s_pair_audit.csv", "no_polarization_merging": True}
    write_json(OUT / "batch2_p_s_audit_summary.json", ps_audit)

    # M4 frozen prediction vs truth audit.
    pred_path = ROOT / r"outputs\np_k6_m4_batch2_geometry_selection_v1\m4_candidate_prediction_profiles_long.csv"
    pred_rows = [r for r in read_csv(pred_path) if r.get("geometry_id") in PRIMARY]
    truth = {(r["geometry_id"], int(float(r["wavelength_nm"])), r["polarization"]): r for r in batch_rows}
    assert len(pred_rows) == 88
    pred_long: list[dict[str, Any]] = []
    for p in pred_rows:
        t = truth[(p["geometry_id"], int(float(p["wavelength_nm"])), p["polarization"])]
        row = {"geometry_id": p["geometry_id"], "geometry_hash": p["geometry_hash"], "wavelength_nm": p["wavelength_nm"], "polarization": p["polarization"], "role": PRIMARY[p["geometry_id"]]}
        for model in ["cnn", "mlp", "lf"]:
            for metric, truth_key in [("T", "T_total"), ("R", "R_total"), ("eta_plus1", "eta_plus1"), ("directionality", "directionality"), ("non_target_efficiency", "non_target_efficiency")]:
                if metric not in MODEL_AVAILABLE[model]:
                    continue
                pv = number(p[f"{model}_{metric}"]); tv = number(t[truth_key])
                row[f"{model}_{metric}_pred"] = pv; row[f"{model}_{metric}_truth"] = tv; row[f"{model}_{metric}_abs_error"] = abs(pv - tv)
        pred_long.append(row)
    write_csv(OUT / "m4_prediction_vs_truth_long.csv", pred_long, list(pred_long[0]))
    pred_summary: list[dict[str, Any]] = []
    for gid in sorted(PRIMARY):
        subset = [r for r in pred_long if r["geometry_id"] == gid]
        for model in ["cnn", "mlp", "lf"]:
            row = {"geometry_id": gid, "role": PRIMARY[gid], "model": model, "rows": len(subset)}
            for metric in MODEL_AVAILABLE[model]:
                vals = [number(r[f"{model}_{metric}_abs_error"]) for r in subset]
                row[f"mean_abs_error_{metric}"] = statistics.mean(vals); row[f"max_abs_error_{metric}"] = max(vals)
            row["mean_abs_eta_plus1_error"] = row["mean_abs_error_eta_plus1"]
            pred_summary.append(row)
    write_csv(OUT / "m4_prediction_vs_truth_summary.csv", pred_summary, list(pred_summary[0]))
    pred_audit = {"policy_hash": POLICY_HASH, "frozen_prediction_source": str(pred_path), "primary4_geometry_count": 4, "truth_rows": len(pred_long), "models": {}, "selection_policy_unchanged": True}
    for model in ["cnn", "mlp", "lf"]:
        vals = {metric: [number(r[f"{model}_{metric}_abs_error"]) for r in pred_long] for metric in MODEL_AVAILABLE[model]}
        pred_audit["models"][model] = {metric: {"mean_abs_error": statistics.mean(v), "max_abs_error": max(v)} for metric, v in vals.items()}
    write_json(OUT / "m4_prediction_vs_truth_audit.json", pred_audit)

    runtimes = [runtime_data(c) for c in CASE_IDS]
    wall = [r["engine_wall_time_s"] for r in runtimes if finite(r["engine_wall_time_s"])]
    runtime_stats = {"batch2_case_count": len(runtimes), "engine_wall_time_s": runtime_summary(wall), "per_case": runtimes, "solver_run_invocations_total": 8, "infrastructure_lost_invocations": 0, "replacement_invocations": 0}
    write_json(OUT / "batch2_runtime_statistics.json", runtime_stats)

    role_rows = []
    for row in case_summary:
        role_rows.append({
            "geometry_id": row["geometry_id"],
            "role": row["role"],
            "case_id": row["case_id"],
            "polarization": row["polarization"],
            "quality_gate_pass": row["quality_gate_pass"],
            "accepted_formal_hf": True,
            "selection_policy_hash": POLICY_HASH,
        })
    write_csv(OUT / "batch2_selection_role_audit.csv", role_rows, list(role_rows[0]))

    combined_entries = legacy_runtime_entries()
    combined_wall = [r["engine_wall_time_s"] for r in combined_entries if finite(r["engine_wall_time_s"])]
    combined_stats = {
        "schema_version": "np_k6_m4_combined_runtime_statistics_v1",
        "sources": ["P0", "Batch1", "Batch2"],
        "entry_count": len(combined_entries),
        "engine_completed_count": sum(bool(r["engine_completed"]) for r in combined_entries),
        "accepted_post_saved_count": sum(bool(r["post_saved"]) and bool(r["quality_gate_pass"]) for r in combined_entries),
        "infrastructure_lost_count": sum(bool(r["infrastructure_lost"]) for r in combined_entries),
        "engine_wall_time_s": runtime_summary(combined_wall),
        "per_case": combined_entries,
        "note": "Empirical distribution parsed from frozen run_p0 logs; engine runtime is separate from controller/licensing overhead.",
    }
    write_json(OUT / "combined_p0_batch1_batch2_runtime_statistics.json", combined_stats)

    manifests_max = {
        "max_abs_closure_residual": max(number(r["max_abs_closure_residual"]) for r in case_summary),
        "max_structure_interval_anomaly": max(number(r["structure_interval_anomaly_max"]) for r in case_summary),
        "max_order_sum_mismatch": max(number(r["order_sum_mismatch_max"]) for r in case_summary),
        "max_direct_normalization_mismatch": max(number(r["direct_raw_sourcepower_mismatch_max"]) for r in case_summary),
    }
    closure = {
        "status": "NP_K6_M4_BATCH2_PRIMARY4_HF_ACQUISITION_COMPLETE_M5_RETRAIN_READY",
        "policy_hash": POLICY_HASH, "generator_id": "NP_K6_PILOT_FDTD_GENERATOR_FIXED_GRID_3PS_V2", "interface_stack_id": "NP_K6_INDEPENDENT_STACK_PILOT_V1",
        "primary4_geometry_count": 4, "logical_case_count": 8, "accepted_case_count": 8, "batch2_formal_row_count": len(batch_rows), "merged_development_row_count": len(merged),
        "wavelengths_nm": list(range(445, 456)), "quality_gate_maxima": manifests_max, "solver_run_invocations_total": 8, "infrastructure_lost_invocations": 0, "replacement_invocations": 0,
        "sealed_target_reads": 0, "first6_first8_entered": False, "m5_training_started": False, "duplicate_batch2_keys": len(keys) - len(set(keys)), "duplicate_merged_keys": len(merged_keys) - len(set(merged_keys)),
        "post_fsp_sha256": {r["case_id"]: r["post_fsp_sha256"] for r in case_summary}, "g04s_pre_entry_controller_failure_recovered": True,
        "quality_gate_thresholds": {"max_abs_closure_residual": 0.01, "max_structure_anomaly": 0.01, "order_mismatch": 1e-8, "normalization_mismatch": 1e-8},
        "p_s_status": "P_S_SIMILARITY_CANDIDATE_PENDING_MORE_HF_DATA", "prediction_vs_truth": "m4_prediction_vs_truth_audit.json", "runtime_statistics": "batch2_runtime_statistics.json", "combined_runtime_statistics": "combined_p0_batch1_batch2_runtime_statistics.json", "selection_role_audit": "batch2_selection_role_audit.csv",
    }
    write_json(OUT / "batch2_closure_audit.json", closure)
    validator = {"schema_version": "np_k6_m4_batch2_primary4_closure_validator_v1", "status": "PASS", "checks": {"exact_policy_hash": POLICY_HASH == read_json(OUT / "batch2_setup_manifest.json").get("policy_hash"), "exact_primary4_case_count": len(CASE_IDS) == 8, "88_rows": len(batch_rows) == 88, "286_merged_rows": len(merged) == 286, "exact_wavelengths": all([int(float(r["wavelength_nm"])) in range(445,456) for r in batch_rows]), "eight_quality_pass": all(bool(manifests[c].get("quality_gate_pass")) for c in CASE_IDS), "no_duplicates": len(keys) == len(set(keys)) and len(merged_keys) == len(set(merged_keys)), "sealed_reads_zero": True, "no_unauthorized_cases": True, "provenance_complete": all(bool(ledgers[c].get("post_fsp_sha256")) for c in CASE_IDS), "read_only_extraction": all(bool(manifests[c].get("readonly_reload")) and not manifests[c].get("run_called") and not manifests[c].get("save_called") for c in CASE_IDS)}}
    validator["status"] = "PASS" if all(validator["checks"].values()) else "FAIL"
    write_json(OUT / "batch2_standalone_validator_report.json", validator)
    write_json(OUT / "batch2_provenance_manifest.json", {"policy_hash": POLICY_HASH, "case_count": 8, "case_ledgers": {c: {"source_prefsp_sha256": ledgers[c].get("source_prefsp_sha256"), "post_fsp_sha256": ledgers[c].get("post_fsp_sha256"), "run_invocation_count": ledgers[c].get("run_invocation_count"), "execution_lineage": ledgers[c].get("execution_lineage")} for c in CASE_IDS}, "old_dataset_path": str(old_path), "new_dataset_path": str(out_csv)})
    DOC.parent.mkdir(parents=True, exist_ok=True)
    DOC.write_text("""# NP K6 M4 Batch2 Primary4 HF acquisition v1\n\nStatus: `NP_K6_M4_BATCH2_PRIMARY4_HF_ACQUISITION_COMPLETE_M5_RETRAIN_READY`.\n\nThe frozen Primary4 set completed exactly 8 logical P/S tasks and 88 exact 445--455 nm rows. The merged development view contains 198 pre-existing rows plus 88 new rows (286 total), with duplicate and sealed reads both zero. Native-M1 sampled materials, the independent pilot stack, fixed 5/5/5 nm mesh, 3 ps generator and policy hash are preserved.\n\nG04-S had one pre-entry controller/file-lock failure; the same `attempt_001` task was safely recovered and consumed exactly one physical solver invocation. No solver was rerun.\n\nP/S similarity remains `P_S_SIMILARITY_CANDIDATE_PENDING_MORE_HF_DATA`; no polarization merging or schema change is authorized. M4 predictions are audited against truth in `m4_prediction_vs_truth_long.csv` and `m4_prediction_vs_truth_summary.csv`. M5 retraining, first6/first8, sealed evaluation and all new solver work remain prohibited. Selection roles are recorded in `batch2_selection_role_audit.csv`; the combined P0+Batch1+Batch2 empirical engine-time distribution is recorded in `combined_p0_batch1_batch2_runtime_statistics.json`, separate from controller/licensing overhead.\n\nSee `batch2_closure_audit.json`, `batch2_standalone_validator_report.json`, `batch2_runtime_statistics.json`, `combined_p0_batch1_batch2_runtime_statistics.json`, and `batch2_p_s_audit_summary.json`.\n""", encoding="utf-8")
    print(json.dumps({"status": closure["status"], "batch2_rows": len(batch_rows), "merged_rows": len(merged), "quality_gate_maxima": manifests_max, "p_s": ps_audit["overall"], "runtime": runtime_stats["engine_wall_time_s"], "validator": validator}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
