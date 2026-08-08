"""Build the six-case NP K6 pilot HF dataset transactionally.

This script is intentionally conservative: it refuses to write the formal
dataset unless all six canonical cases have complete, quality-gated, exact
11-point read-only extraction evidence.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import shutil
import tempfile
from pathlib import Path

ROOT = Path(r"D:\project\worktrees\blue_apcd_np_k6_mdc_v1")
STAGE = ROOT / "outputs" / "np_k6_p0_remaining_five_anchors_execution_v1"
OUT = ROOT / "outputs" / "np_k6_hf_pilot_dataset_v1"
WAVELENGTHS = list(range(445, 456))
CANONICAL = [
    "RUN3C_P_PILOT_HF_V1",
    "RUN3C_S_PILOT_HF_V2",
    "RUN3A_P_PILOT_HF_V1",
    "RUN3A_S_PILOT_HF_V1",
    "RUN3B_P_PILOT_HF_V1",
    "RUN3B_S_PILOT_HF_V1",
]
THREE_PS = ROOT / "outputs" / "np_k6_p0_simtime_3ps_control_v1"
CASE_INFO = {
    "RUN3C_P_PILOT_HF_V1": {
        "source_case_id": "RUN3C_P_PILOT_HF_SIMTIME_3PS_CONTROL_V1",
        "geometry_id": "K6X_D130_D145_D155_D180_D195_D230",
        "geometry_hash": "4591fc0d081506b1251fb74edd24b3b6fc950b99072ca0f3172b5d50f5951fc1",
        "polarization": "p",
        "post_sha256": "c14fd3a2464e11c3ba667e4b513bd76a1828c918f80df54511fec7862e2705ca",
        "generator_id": "NP_K6_PILOT_FDTD_GENERATOR_FIXED_GRID_3PS_V2",
        "interface_stack_id": "NP_K6_INDEPENDENT_STACK_PILOT_V1",
    },
    "RUN3C_S_PILOT_HF_V2": {
        "geometry_id": "K6X_D130_D145_D155_D180_D195_D230",
        "geometry_hash": "4591fc0d081506b1251fb74edd24b3b6fc950b99072ca0f3172b5d50f5951fc1",
        "polarization": "s",
    },
    "RUN3A_P_PILOT_HF_V1": {
        "geometry_id": "K6X_D125_D135_D150_D175_D190_D210",
        "geometry_hash": "06f49f63b580719dd1345d98f28881538154de46899e4d633dbf6dacce51c0f9",
        "polarization": "p",
    },
    "RUN3A_S_PILOT_HF_V1": {
        "geometry_id": "K6X_D125_D135_D150_D175_D190_D210",
        "geometry_hash": "06f49f63b580719dd1345d98f28881538154de46899e4d633dbf6dacce51c0f9",
        "polarization": "s",
    },
    "RUN3B_P_PILOT_HF_V1": {
        "geometry_id": "K6X_D100_D115_D130_D145_D155_D185",
        "geometry_hash": "42d96454a34a0ccbde1bba64746f5920389e2a2924569a69ee7f2aac08a6bcde",
        "polarization": "p",
    },
    "RUN3B_S_PILOT_HF_V1": {
        "geometry_id": "K6X_D100_D115_D130_D145_D155_D185",
        "geometry_hash": "42d96454a34a0ccbde1bba64746f5920389e2a2924569a69ee7f2aac08a6bcde",
        "polarization": "s",
    },
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def finite(value: str) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def load_case(case: str) -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, str]], dict]:
    info = dict(CASE_INFO[case])
    if case == "RUN3C_P_PILOT_HF_V1":
        metric_path = THREE_PS / "spectral_metrics_11points.csv"
        tx_path = THREE_PS / "transmitted_orders_11points.csv"
        rx_path = THREE_PS / "reflected_orders_11points.csv"
        if not all(p.exists() for p in (metric_path, tx_path, rx_path)):
            raise RuntimeError(f"missing accepted 3ps source for {case}")
        metrics = read_csv(metric_path)
        tx = read_csv(tx_path)
        rx = read_csv(rx_path)
        for row in metrics:
            row["source_case_id"] = row.get("case_id", "")
            row["case_id"] = case
            row["frequency_hz"] = str(299792458.0 / (float(row["wavelength_nm"]) * 1e-9))
        for row in tx + rx:
            row["case_id"] = case
        info["source_metrics"] = str(metric_path)
        info["source_post_sha256"] = info["post_sha256"]
        info["quality_gate_pass"] = True
        info["source_type"] = "accepted_3ps_correction_v2_bridge"
        return metrics, tx, rx, info

    cdir = STAGE / "cases" / case
    manifest_path = cdir / "extraction_manifest.json"
    metric_path = cdir / "hf_observations_long.csv"
    tx_path = cdir / "hf_transmitted_orders_long.csv"
    rx_path = cdir / "hf_reflected_orders_long.csv"
    if not all(p.exists() for p in (manifest_path, metric_path, tx_path, rx_path)):
        raise RuntimeError(f"incomplete evidence for {case}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    ledger = json.loads((cdir / "attempt_ledger.json").read_text(encoding="utf-8-sig"))
    if not manifest.get("quality_gate_pass"):
        raise RuntimeError(f"quality gate failed for {case}")
    if not (manifest.get("readonly_reload") and manifest.get("exact_11_points")):
        raise RuntimeError(f"read-only/exact wavelength gate failed for {case}")
    if ledger.get("run_invocation_count") != 1 or not ledger.get("entered"):
        raise RuntimeError(f"solver ledger identity failed for {case}")
    metrics, tx, rx = read_csv(metric_path), read_csv(tx_path), read_csv(rx_path)
    for row in metrics + tx + rx:
        row["case_id"] = case
    info.update({
        "source_metrics": str(metric_path),
        "source_post_sha256": manifest.get("post_fsp_sha256"),
        "post_sha256": manifest.get("post_fsp_sha256"),
        "quality_gate_pass": True,
        "source_type": "remaining_five_v2_anchor",
        "generator_id": "NP_K6_PILOT_FDTD_GENERATOR_FIXED_GRID_3PS_V2",
        "interface_stack_id": "NP_K6_INDEPENDENT_STACK_PILOT_V1",
    })
    return metrics, tx, rx, info


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise RuntimeError(f"refusing empty CSV: {path}")
    fields = list(dict.fromkeys(k for row in rows for k in row))
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def write_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def main() -> None:
    if OUT.exists():
        raise RuntimeError(f"dataset output already exists; refusing overwrite: {OUT}")
    cases, all_metrics, all_tx, all_rx, case_info = [], [], [], [], {}
    for case in CANONICAL:
        metrics, tx, rx, info = load_case(case)
        wavelengths = [int(float(r["wavelength_nm"])) for r in metrics]
        if wavelengths != WAVELENGTHS:
            raise RuntimeError(f"exact wavelength failure for {case}: {wavelengths}")
        if len(metrics) != 11 or any(not finite(r.get("T_total")) or not finite(r.get("R_total")) for r in metrics):
            raise RuntimeError(f"finite/row-count failure for {case}")
        for row in metrics:
            row.update({"geometry_id": info["geometry_id"], "geometry_hash": info["geometry_hash"], "polarization": info["polarization"], "generator_id": info["generator_id"], "interface_stack_id": info["interface_stack_id"], "quality_gate_pass": "true", "training_label": "true", "provisional_hf_label": "false", "diagnostic_only": "false", "pilot_scope_only": "true", "bulk_mdc_compatible": "false", "candidate_performance_label": "true"})
        for row in tx + rx:
            row.update({"geometry_id": info["geometry_id"], "geometry_hash": info["geometry_hash"], "polarization": info["polarization"]})
        cases.append(case)
        all_metrics.extend(metrics); all_tx.extend(tx); all_rx.extend(rx)
        case_info[case] = info

    if len(all_metrics) != 66 or len(set((r["case_id"], int(float(r["wavelength_nm"]))) for r in all_metrics)) != 66:
        raise RuntimeError("formal observations are not exactly 66 unique case/wavelength rows")
    tmp = Path(tempfile.mkdtemp(prefix="np_k6_hf_dataset_", dir=str(ROOT / "outputs")))
    try:
        write_csv(tmp / "hf_observations_long.csv", all_metrics)
        write_csv(tmp / "hf_transmitted_orders_long.csv", all_tx)
        write_csv(tmp / "hf_reflected_orders_long.csv", all_rx)
        registry = [{"case_id": c, **{k: v for k, v in case_info[c].items() if k in {"geometry_id", "geometry_hash", "polarization", "post_sha256", "source_post_sha256", "source_type", "generator_id", "interface_stack_id", "quality_gate_pass"}}} for c in cases]
        write_csv(tmp / "hf_task_registry.csv", registry)
        write_csv(tmp / "label_quality_registry.csv", [{"case_id": c, "quality_gate_pass": "true", "training_label": "true", "provisional_hf_label": "false", "diagnostic_only": "false", "pilot_scope_only": "true", "bulk_mdc_compatible": "false"} for c in cases])
        geometries = {}
        for c in cases:
            i = case_info[c]; geometries[i["geometry_id"]] = {"geometry_id": i["geometry_id"], "geometry_hash": i["geometry_hash"]}
        write_csv(tmp / "hf_geometry_registry.csv", list(geometries.values()))
        write_json(tmp / "pilot_generator_manifest.json", {"generator_id": "NP_K6_PILOT_FDTD_GENERATOR_FIXED_GRID_3PS_V2", "interface_stack_id": "NP_K6_INDEPENDENT_STACK_PILOT_V1", "canonical_cases": cases, "formal_observation_count": 66, "sealed_test_touched": False, "training_started": False})
        pairs = [("RUN3C", "RUN3C_P_PILOT_HF_V1", "RUN3C_S_PILOT_HF_V2"), ("RUN3A", "RUN3A_P_PILOT_HF_V1", "RUN3A_S_PILOT_HF_V1"), ("RUN3B", "RUN3B_P_PILOT_HF_V1", "RUN3B_S_PILOT_HF_V1")]
        ps_rows = []
        for name, p, s in pairs:
            pm = {int(float(r["wavelength_nm"])): r for r in all_metrics if r["case_id"] == p}
            sm = {int(float(r["wavelength_nm"])): r for r in all_metrics if r["case_id"] == s}
            d_eta = [abs(float(pm[w]["eta_plus1"]) - float(sm[w]["eta_plus1"])) for w in WAVELENGTHS]
            d_t = [abs(float(pm[w]["T_total"]) - float(sm[w]["T_total"])) for w in WAVELENGTHS]
            ps_rows.append({"geometry_family": name, "p_case_id": p, "s_case_id": s, "max_abs_delta_eta_plus1": max(d_eta), "mean_abs_delta_eta_plus1": sum(d_eta)/len(d_eta), "max_abs_delta_T": max(d_t), "classification": "P_S_SIMILARITY_CANDIDATE_PENDING_MORE_HF_DATA"})
        write_csv(tmp / "p_s_preliminary_audit.csv", ps_rows)
        write_json(tmp / "p_s_preliminary_audit.json", {"classification_set": [r["classification"] for r in ps_rows], "rows": ps_rows, "final_p_s_equivalence_claim": False})
        checks = []
        for p in sorted(tmp.rglob("*")):
            if p.is_file(): checks.append({"path": str(p.relative_to(tmp)).replace("\\", "/"), "sha256": sha256(p), "size_bytes": p.stat().st_size})
        write_json(tmp / "dataset_checksum_manifest.json", {"schema_version": "np_k6_hf_pilot_dataset_v1", "formal_observation_count": 66, "files": checks})
        write_json(tmp / "dataset_decision.json", {"status": "NP_K6_HF_P0_ANCHOR_DATASET_COMPLETE_PILOT_TRAINING_READY", "formal_observation_count": 66, "training_started": False, "sealed_test_touched": False})
        os.replace(str(tmp), str(OUT))
    except Exception:
        shutil.rmtree(tmp, ignore_errors=True)
        raise


if __name__ == "__main__":
    main()
