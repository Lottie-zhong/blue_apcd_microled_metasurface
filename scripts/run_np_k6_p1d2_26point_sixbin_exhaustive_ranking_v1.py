"""Deterministic, solver-free exhaustive six-bin ranking for frozen P1-D2 data."""
from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "outputs" / "np_k6_p1d2_broadband_library_26point_v1" / "library_long.csv"
OUTPUT_NAME = "np_k6_p1d2_sixbin_exhaustive_ranking_v1"
DIAMETERS = tuple(d for d in range(100, 231, 5) if d != 180)
WAVELENGTHS = tuple(range(445, 456))
TARGET = np.arange(6, dtype=float) * 60.0
GATES = {
    "phase_fit_RMS_band_max_deg": {"op": "<=", "value": 10.0, "source": "task_frozen_engineering_contract_v1"},
    "maximum_phase_error_over_band_deg": {"op": "<=", "value": 15.0, "source": "task_frozen_engineering_contract_v1"},
    "amplitude_CV_band_max": {"op": "<=", "value": 0.10, "source": "task_frozen_engineering_contract_v1"},
    "minimum_txx_amplitude_over_band": {"op": ">=", "value": 0.80, "source": "formal_library_engineering_usable_gate"},
    "minimum_T_over_band": {"op": ">=", "value": 0.70, "source": "formal_library_engineering_usable_gate"},
    "maximum_cross_pol_over_band": {"op": "<=", "value": 1.0e-6, "source": "task_frozen_cross_pol_gate_v1"},
    "minimum_physical_gap_nm": {"op": ">=", "value": 60.0, "source": "task_frozen_manufacturing_gate_v1"},
}
GATE_ORDER = tuple(GATES) + ("finite_data_gate", "contract_gate", "formal_quality_gate")


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def dump(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def wrap180(values: np.ndarray | float) -> np.ndarray | float:
    return (np.asarray(values) + 180.0) % 360.0 - 180.0


def circular_fit(phases: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Exact branch search for circular least squares.

    ``phases`` has shape (..., 6).  The circular mean is evaluated first;
    all six deterministic cut branches are then evaluated, which is the
    analytic equivalent of a fine angular search for squared geodesic error.
    """
    delta = wrap180(phases - TARGET)
    initial = np.degrees(np.angle(np.mean(np.exp(1j * np.radians(delta)), axis=-1)))
    best_common = initial
    best_error = wrap180(delta - initial[..., None])
    best_sse = np.sum(best_error * best_error, axis=-1)
    for anchor in range(6):
        cut = delta[..., anchor, None]
        unwrapped = cut + wrap180(delta - cut)
        common = np.mean(unwrapped, axis=-1)
        error = wrap180(delta - common[..., None])
        sse = np.sum(error * error, axis=-1)
        take = sse < best_sse - 1.0e-12
        best_common = np.where(take, common, best_common)
        best_error = np.where(take[..., None], error, best_error)
        best_sse = np.where(take, sse, best_sse)
    return wrap180(best_common), best_error


def load_library(path: Path) -> tuple[np.ndarray, dict[str, np.ndarray], dict[int, str]]:
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    if len(rows) != 286:
        raise RuntimeError(f"expected 286 library rows, got {len(rows)}")
    ds = sorted({int(row["diameter_nm"]) for row in rows})
    if tuple(ds) != DIAMETERS:
        raise RuntimeError(f"frozen diameter allowlist mismatch: {ds}")
    data = {name: np.empty((26, 11), dtype=float) for name in ("phase", "T", "R", "amp", "cross", "energy", "recon")}
    index = {d: i for i, d in enumerate(DIAMETERS)}
    seen = set()
    for row in rows:
        d, w = int(row["diameter_nm"]), int(row["wavelength_nm"])
        if w not in WAVELENGTHS or (d, w) in seen:
            raise RuntimeError("library axis is not an exact unique 26 x 11 grid")
        seen.add((d, w)); i, j = index[d], w - 445
        data["phase"][i, j] = float(row["txx_wrapped_phase_deg"])
        data["T"][i, j] = float(row["T"])
        data["R"][i, j] = float(row["R"])
        data["amp"][i, j] = float(row["txx_amplitude"])
        data["cross"][i, j] = float(row["cross_pol"])
        data["energy"][i, j] = float(row["energy_residual"])
        data["recon"][i, j] = float(row["reconstruction_residual"])
    if len(seen) != 286 or not all(np.isfinite(a).all() for a in data.values()):
        raise RuntimeError("library finite/grid gate failed")
    qualities: dict[int, str] = {}
    for d in DIAMETERS:
        matches = list((ROOT / "outputs").glob(f"np_k6_p1d2b*_broadband_d{d}_x_v1/verification_summary.json"))
        if len(matches) != 1:
            raise RuntimeError(f"expected one verification summary for D{d}")
        qualities[d] = json.loads(matches[0].read_text(encoding="utf-8")).get("individual_pillar_spectral_quality", "missing")
    return np.asarray(DIAMETERS, dtype=np.int16), data, qualities


def defect_audit() -> dict[str, Any]:
    source = ROOT / "scripts" / "synthesize_np_k6_p1d2_broadband_library_x_v1.py"
    text = source.read_text(encoding="utf-8")
    old = json.loads((ROOT / "outputs" / "np_k6_p1d2_broadband_library_26point_v1" / "candidate_sextet_ranking.json").read_text(encoding="utf-8"))
    return {
        "audit_version": "sixbin_ranking_defect_audit_v1",
        "source_script": str(source.relative_to(ROOT)).replace("\\", "/"),
        "source_sha256": digest(source),
        "broadband_reuses_phase_branch": 'if kind=="amplitude_uniformity_optimal"' in text and 'else:' in text,
        "engineering_gate_boolean_is_constant": '"all_engineering_gates_passing_sextet_exists":False' in text,
        "exhaustive_combination_enumeration_present": "itertools.combinations" in text,
        "only_five_linear_steps_present": "np.diff(p[:,j])" in text,
        "D5_to_D0_closure_present": False,
        "depends_on_global_unwrap": "np.unwrap" in text,
        "unrecorded_high_transmission_prescreen": False,
        "old_champions_reproduced": {
            name: value["diameters_nm"] for name, value in old.items() if isinstance(value, dict) and "diameters_nm" in value
        },
        "conclusion": "repair_required",
    }


def evaluate_all(ds: np.ndarray, data: dict[str, np.ndarray], qualities: dict[int, str]) -> dict[str, np.ndarray]:
    combos = np.asarray(list(itertools.combinations(range(26), 6)), dtype=np.int16)
    n = len(combos)
    if n != math.comb(26, 6):
        raise RuntimeError("combination count mismatch")
    result: dict[str, np.ndarray] = {
        "indices": combos,
        "common": np.empty((n, 11), np.float32),
        "errors": np.empty((n, 11, 6), np.float32),
        "phase_rms": np.empty((n, 11), np.float32),
        "phase_abs": np.empty((n, 11), np.float32),
        "steps": np.empty((n, 11, 6), np.float32),
        "cyclic_rms": np.empty((n, 11), np.float32),
        "amp_cv": np.empty((n, 11), np.float32),
        "phase_rms_mean": np.empty(n, np.float32), "phase_rms_max": np.empty(n, np.float32),
        "phase_abs_max": np.empty(n, np.float32), "cyclic_rms_mean": np.empty(n, np.float32),
        "cyclic_rms_max": np.empty(n, np.float32), "step_abs_max": np.empty(n, np.float32),
        "step_drift_max": np.empty(n, np.float32), "closure_drift": np.empty(n, np.float32),
        "amp_cv_mean": np.empty(n, np.float32), "amp_cv_max": np.empty(n, np.float32),
        "min_amp": np.empty(n, np.float32), "min_T": np.empty(n, np.float32),
        "max_R": np.empty(n, np.float32), "max_cross": np.empty(n, np.float32),
        "min_gap": np.empty(n, np.float32), "warning_count": np.empty(n, np.int8),
        "formal_quality": np.empty(n, bool),
    }
    warning_by_d = np.asarray([qualities[int(d)] == "warning_valid" for d in ds])
    formal_by_d = np.asarray([qualities[int(d)] in {"pass", "warning_valid"} for d in ds])
    for start in range(0, n, 5000):
        end = min(start + 5000, n); ix = combos[start:end]
        phase = np.moveaxis(data["phase"][ix], 2, 1)  # batch, wavelength, six
        common, errors = circular_fit(phase)
        steps = wrap180(np.roll(phase, -1, axis=2) - phase - 60.0)
        rms = np.sqrt(np.mean(errors * errors, axis=2)); cyc = np.sqrt(np.mean(steps * steps, axis=2))
        amp = np.moveaxis(data["amp"][ix], 2, 1)
        cv = np.std(amp, axis=2) / np.mean(amp, axis=2)
        result["common"][start:end] = common; result["errors"][start:end] = errors
        result["phase_rms"][start:end] = rms; result["phase_abs"][start:end] = np.max(np.abs(errors), axis=2)
        result["steps"][start:end] = steps; result["cyclic_rms"][start:end] = cyc; result["amp_cv"][start:end] = cv
        result["phase_rms_mean"][start:end] = np.mean(rms, axis=1); result["phase_rms_max"][start:end] = np.max(rms, axis=1)
        result["phase_abs_max"][start:end] = np.max(np.abs(errors), axis=(1, 2)); result["cyclic_rms_mean"][start:end] = np.mean(cyc, axis=1); result["cyclic_rms_max"][start:end] = np.max(cyc, axis=1)
        result["step_abs_max"][start:end] = np.max(np.abs(steps), axis=(1, 2)); result["step_drift_max"][start:end] = np.max(np.ptp(steps, axis=1), axis=1); result["closure_drift"][start:end] = np.ptp(steps[:, :, 5], axis=1)
        result["amp_cv_mean"][start:end] = np.mean(cv, axis=1); result["amp_cv_max"][start:end] = np.max(cv, axis=1)
        result["min_amp"][start:end] = np.min(data["amp"][ix], axis=(1, 2)); result["min_T"][start:end] = np.min(data["T"][ix], axis=(1, 2)); result["max_R"][start:end] = np.max(data["R"][ix], axis=(1, 2)); result["max_cross"][start:end] = np.max(data["cross"][ix], axis=(1, 2))
        result["min_gap"][start:end] = 290 - np.max(ds[ix], axis=1); result["warning_count"][start:end] = np.sum(warning_by_d[ix], axis=1); result["formal_quality"][start:end] = np.all(formal_by_d[ix], axis=1)
    return result


def gate_table(r: dict[str, np.ndarray]) -> tuple[dict[str, np.ndarray], np.ndarray, list[str]]:
    table = {
        "phase_fit_RMS_band_max_deg": r["phase_rms_max"] <= GATES["phase_fit_RMS_band_max_deg"]["value"],
        "maximum_phase_error_over_band_deg": r["phase_abs_max"] <= GATES["maximum_phase_error_over_band_deg"]["value"],
        "amplitude_CV_band_max": r["amp_cv_max"] <= GATES["amplitude_CV_band_max"]["value"],
        "minimum_txx_amplitude_over_band": r["min_amp"] >= GATES["minimum_txx_amplitude_over_band"]["value"],
        "minimum_T_over_band": r["min_T"] >= GATES["minimum_T_over_band"]["value"],
        "maximum_cross_pol_over_band": r["max_cross"] <= GATES["maximum_cross_pol_over_band"]["value"],
        "minimum_physical_gap_nm": r["min_gap"] >= GATES["minimum_physical_gap_nm"]["value"],
        "finite_data_gate": np.ones(len(r["indices"]), bool),
        "contract_gate": np.ones(len(r["indices"]), bool),
        "formal_quality_gate": r["formal_quality"],
    }
    all_pass = np.logical_and.reduce([table[name] for name in GATE_ORDER])
    return table, all_pass, list(GATE_ORDER)


def phase_order(r: dict[str, np.ndarray], ds: np.ndarray) -> np.ndarray:
    d = ds[r["indices"]]
    return np.lexsort((d[:,5], d[:,4], d[:,3], d[:,2], d[:,1], d[:,0], -r["min_T"], r["amp_cv_max"], r["cyclic_rms_max"], r["phase_abs_max"], r["phase_rms_max"]))


def amplitude_order(r: dict[str, np.ndarray], ds: np.ndarray) -> np.ndarray:
    d = ds[r["indices"]]
    return np.lexsort((d[:,5], d[:,4], d[:,3], d[:,2], d[:,1], d[:,0], r["cyclic_rms_max"], r["phase_rms_max"], -r["min_T"], -r["min_amp"], r["amp_cv_mean"], r["amp_cv_max"]))


def broadband_order(r: dict[str, np.ndarray], ds: np.ndarray) -> np.ndarray:
    d = ds[r["indices"]]
    return np.lexsort((d[:,5], d[:,4], d[:,3], d[:,2], d[:,1], d[:,0], -r["min_T"], r["amp_cv_max"], r["phase_abs_max"], r["phase_rms_max"], r["cyclic_rms_max"], r["closure_drift"], r["step_drift_max"]))


def record(index: int, ds: np.ndarray, data: dict[str, np.ndarray], r: dict[str, np.ndarray], gates: dict[str, np.ndarray], names: list[str]) -> dict[str, Any]:
    d = ds[r["indices"][index]]; phase = data["phase"][r["indices"][index]]
    values = {"phase_fit_RMS_band_max_deg": float(r["phase_rms_max"][index]), "maximum_phase_error_over_band_deg": float(r["phase_abs_max"][index]), "amplitude_CV_band_max": float(r["amp_cv_max"][index]), "minimum_txx_amplitude_over_band": float(r["min_amp"][index]), "minimum_T_over_band": float(r["min_T"][index]), "maximum_cross_pol_over_band": float(r["max_cross"][index]), "minimum_physical_gap_nm": float(r["min_gap"][index])}
    passes = {name: bool(gates[name][index]) for name in names}; failed = [name for name in names if not passes[name]]
    margins = {name: (GATES[name]["value"] - values[name] if GATES[name]["op"] == "<=" else values[name] - GATES[name]["value"]) for name in GATES}
    return {"diameters_nm": [int(x) for x in d], "wrapped_phases_deg_by_wavelength": {str(w): [float(x) for x in phase[:, j]] for j, w in enumerate(WAVELENGTHS)}, "fitted_common_phase_deg_by_wavelength": [float(x) for x in r["common"][index]], "phase_errors_deg_by_wavelength": [[float(x) for x in row] for row in r["errors"][index]], "phase_fit_RMS_deg_by_wavelength": [float(x) for x in r["phase_rms"][index]], "phase_fit_RMS_band_mean": float(r["phase_rms_mean"][index]), "phase_fit_RMS_band_max": float(r["phase_rms_max"][index]), "maximum_phase_error_over_band": float(r["phase_abs_max"][index]), "six_cyclic_step_errors_deg_by_wavelength": [[float(x) for x in row] for row in r["steps"][index]], "cyclic_step_RMS_band_mean": float(r["cyclic_rms_mean"][index]), "cyclic_step_RMS_band_max": float(r["cyclic_rms_max"][index]), "cyclic_step_abs_error_band_max": float(r["step_abs_max"][index]), "maximum_step_drift_peak_to_peak": float(r["step_drift_max"][index]), "cyclic_closure_step_error_445": float(r["steps"][index,0,5]), "cyclic_closure_step_error_450": float(r["steps"][index,5,5]), "cyclic_closure_step_error_455": float(r["steps"][index,10,5]), "cyclic_closure_step_drift_peak_to_peak": float(r["closure_drift"][index]), "amplitude_CV_band_mean": float(r["amp_cv_mean"][index]), "amplitude_CV_band_max": float(r["amp_cv_max"][index]), "minimum_txx_amplitude_over_band": float(r["min_amp"][index]), "minimum_T_over_band": float(r["min_T"][index]), "maximum_R_over_band": float(r["max_R"][index]), "maximum_cross_pol_over_band": float(r["max_cross"][index]), "warning_valid_candidate_count": int(r["warning_count"][index]), "minimum_physical_gap_nm": float(r["min_gap"][index]), "each_gate_value": values, "each_gate_threshold": GATES, "each_gate_margin": margins, "each_gate_pass": passes, "failed_gate_names": failed, "first_failed_gate": failed[0] if failed else None, "all_legacy_engineering_gates_pass": not failed, "legacy_engineering_gate_pass": not failed, "K6_SUPERCELL_VALIDATION_STATUS": "not_run", "x_only": True}


def pareto_mask(r: dict[str, np.ndarray]) -> np.ndarray:
    # Sorting by the first minimization objective permits a compact exact frontier sweep.
    vals = np.column_stack((r["phase_rms_max"], r["phase_abs_max"], r["step_drift_max"], r["amp_cv_max"], -r["min_T"]))
    order = np.lexsort((vals[:,4], vals[:,3], vals[:,2], vals[:,1], vals[:,0])); front: list[int] = []
    for idx in order:
        point = vals[idx]
        if front and np.any(np.all(vals[np.asarray(front)] <= point, axis=1)):
            continue
        if front:
            keep = ~np.all(point <= vals[np.asarray(front)], axis=1)
            front = [v for v, yes in zip(front, keep) if yes]
        front.append(int(idx))
    mask = np.zeros(len(vals), bool); mask[front] = True
    return mask


def csv_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0]) if rows else ["diameters_nm"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader(); writer.writerows(rows)


def run(output: Path) -> dict[str, Any]:
    ds, data, qualities = load_library(INPUT); output.mkdir(parents=True, exist_ok=True)
    dump(output / "sixbin_ranking_defect_audit_v1.json", defect_audit())
    r = evaluate_all(ds, data, qualities); gates, all_pass, names = gate_table(r)
    phase, amplitude, broadband = phase_order(r, ds), amplitude_order(r, ds), broadband_order(r, ds)
    pareto = pareto_mask(r)
    n = len(r["indices"]); digits = np.asarray(ds[r["indices"]])
    failed_names = ["|".join(name for name in names if not gates[name][i]) for i in range(n)]
    first = [next((name for name in names if not gates[name][i]), "") for i in range(n)]
    summary_rows = [{"diameters_nm": ",".join(map(str, digits[i])), "all_legacy_engineering_gates_pass": bool(all_pass[i]), "first_failed_gate": first[i], "failed_gate_names": failed_names[i], "phase_fit_RMS_band_max": float(r["phase_rms_max"][i]), "maximum_phase_error_over_band": float(r["phase_abs_max"][i]), "maximum_step_drift_peak_to_peak": float(r["step_drift_max"][i]), "amplitude_CV_band_max": float(r["amp_cv_max"][i]), "minimum_txx_amplitude_over_band": float(r["min_amp"][i]), "minimum_T_over_band": float(r["min_T"][i])} for i in range(n)]
    csv_rows(output / "all_combinations_gate_summary.csv", summary_rows)
    npz = output / "all_combinations_metrics.npz"; np.savez_compressed(npz, **r, **{f"gate_{name}": value for name, value in gates.items()}, all_legacy_engineering_gates_pass=all_pass, pareto=pareto)
    def compact(ix: int, rank: int) -> dict[str, Any]:
        x = record(int(ix), ds, data, r, gates, names)
        return {"rank": rank, "diameters_nm": ",".join(map(str, x["diameters_nm"])), "phase_fit_RMS_band_max": x["phase_fit_RMS_band_max"], "maximum_phase_error_over_band": x["maximum_phase_error_over_band"], "maximum_step_drift_peak_to_peak": x["maximum_step_drift_peak_to_peak"], "amplitude_CV_band_max": x["amplitude_CV_band_max"], "minimum_T_over_band": x["minimum_T_over_band"], "all_legacy_engineering_gates_pass": x["all_legacy_engineering_gates_pass"]}
    for file, order in (("phase_error_top100.csv", phase), ("amplitude_uniformity_top100.csv", amplitude), ("broadband_dispersion_top100.csv", broadband)):
        csv_rows(output / file, [compact(int(ix), rank + 1) for rank, ix in enumerate(order[:100])])
    passing_indices = np.flatnonzero(all_pass); csv_rows(output / "passing_combinations.csv", [compact(int(ix), rank + 1) for rank, ix in enumerate(passing_indices)])
    passing_phase_order = [int(ix) for ix in phase if all_pass[ix]]
    top5_passing = [record(ix, ds, data, r, gates, names) for ix in passing_phase_order[:5]]
    first_second_margin = None if len(passing_phase_order) < 2 else {"ranking": "phase_error_optimal", "phase_fit_RMS_band_max_deg": float(r["phase_rms_max"][passing_phase_order[1]] - r["phase_rms_max"][passing_phase_order[0]]), "maximum_phase_error_over_band_deg": float(r["phase_abs_max"][passing_phase_order[1]] - r["phase_abs_max"][passing_phase_order[0]])}
    dump(output / "top_5_passing_sextets_detailed.json", {"top_5": top5_passing, "first_second_margin": first_second_margin})
    champions = {"phase_error_optimal": record(int(phase[0]), ds, data, r, gates, names), "amplitude_uniformity_optimal": record(int(amplitude[0]), ds, data, r, gates, names), "broadband_dispersion_optimal": record(int(broadband[0]), ds, data, r, gates, names)}
    top20 = {name: [record(int(ix), ds, data, r, gates, names) for ix in order[:20]] for name, order in (("phase_error", phase), ("amplitude_uniformity", amplitude), ("broadband_dispersion", broadband))}
    dump(output / "candidate_top20_detailed.json", top20)
    pareto_indices = np.flatnonzero(pareto); pareto_rows = [compact(int(ix), rank + 1) for rank, ix in enumerate(pareto_indices)]
    csv_rows(output / "pareto_front.csv", pareto_rows); dump(output / "pareto_front_detailed.json", [record(int(ix), ds, data, r, gates, names) for ix in pareto_indices])
    failed = {name: int(np.count_nonzero(~gates[name])) for name in names}
    multi = int(np.count_nonzero(np.sum(np.column_stack([~gates[name] for name in names]), axis=1) > 1))
    failure = {"phase_RMS_failure_count": failed["phase_fit_RMS_band_max_deg"], "max_phase_error_failure_count": failed["maximum_phase_error_over_band_deg"], "amplitude_CV_failure_count": failed["amplitude_CV_band_max"], "txx_amplitude_failure_count": failed["minimum_txx_amplitude_over_band"], "transmission_failure_count": failed["minimum_T_over_band"], "crosspol_failure_count": failed["maximum_cross_pol_over_band"], "manufacturing_failure_count": failed["minimum_physical_gap_nm"], "formal_quality_failure_count": failed["formal_quality_gate"], "multi_gate_failure_count": multi}
    dump(output / "failure_gate_statistics.json", failure)
    raw_values = {"phase_fit_RMS_band_max_deg": r["phase_rms_max"], "maximum_phase_error_over_band_deg": r["phase_abs_max"], "amplitude_CV_band_max": r["amp_cv_max"], "minimum_txx_amplitude_over_band": r["min_amp"], "minimum_T_over_band": r["min_T"], "maximum_cross_pol_over_band": r["max_cross"], "minimum_physical_gap_nm": r["min_gap"]}
    relax = np.zeros(n)
    for name, config in GATES.items():
        margin = config["value"] - raw_values[name] if config["op"] == "<=" else raw_values[name] - config["value"]
        relax += np.maximum(0.0, -margin) / max(abs(config["value"]), 1.0e-12)
    failed_count = np.sum(np.column_stack([~gates[name] for name in names]), axis=1)
    closest = np.lexsort((relax, failed_count))[:10]
    closest_detail = [record(i, ds, data, r, gates, names) for i in closest]
    cyclic = {"cyclic_step_count": 6, "D5_to_D0_closure_included": True, "cyclic_closure_threshold_status": "threshold_not_frozen", "champion_closure_audit": {name: {"445": value["cyclic_closure_step_error_445"], "450": value["cyclic_closure_step_error_450"], "455": value["cyclic_closure_step_error_455"]} for name, value in champions.items()}}
    dump(output / "cyclic_closure_audit.json", cyclic)
    best = champions["phase_error_optimal"]; best_ds = best["diameters_nm"]; d180 = {"D180_RERUN_RECOMMENDATION": "not_required_for_initial_sextet" if bool(all_pass.any()) else "useful_for_library_completeness", "measured_only_passing_exists": bool(all_pass.any()), "best_measured_only_sextet": best_ds, "best_crosses_D175_D185_gap": 175 in best_ds and 185 in best_ds, "missing_bin_near_D180": False, "ranking_sensitivity_to_gap": "low_without_global_unwrap", "expected_information_gain_of_D180": "local_forward_surrogate_uncertainty_reduction_only", "may_replace_current_candidate": False, "D180_formal_optical_label_used": False, "reason": "all rankings use wrapped phases only and no D180 interpolation"}
    dump(output / "d180_rerun_necessity_recomputed.json", d180)
    gate_contract = {"contract_version": "engineering_gate_contract_snapshot_v1", "gates": GATES, "non_numeric_gates": {"finite_data_gate": "all library values finite", "contract_gate": "exact 26 x 11 x-only frozen input", "formal_quality_gate": "each included source summary is pass or warning_valid"}, "cyclic_closure_threshold_status": "threshold_not_frozen", "legacy_only": True, "K6_SUPERCELL_VALIDATION_STATUS": "not_run"}
    dump(output / "engineering_gate_contract_snapshot.json", gate_contract)
    objective = {"phase_error_optimal": ["phase_fit_RMS_band_max asc", "maximum_phase_error_over_band asc", "cyclic_step_RMS_band_max asc", "amplitude_CV_band_max asc", "minimum_T desc", "diameters lexicographic"], "amplitude_uniformity_optimal": ["amplitude_CV_band_max asc", "amplitude_CV_band_mean asc", "minimum_txx_amplitude_over_band desc", "minimum_T desc", "phase_fit_RMS_band_max asc", "cyclic_step_RMS_band_max asc", "diameters lexicographic"], "broadband_dispersion_optimal": ["maximum_step_drift_peak_to_peak asc", "cyclic_closure_step_drift_peak_to_peak asc", "cyclic_step_RMS_band_max asc", "phase_fit_RMS_band_max asc", "maximum_phase_error_over_band asc", "amplitude_CV_band_max asc", "minimum_T desc", "diameters lexicographic"], "functions_independent": True, "uses_wrapped_circular_phase_only": True}
    dump(output / "ranking_objective_contract.json", objective)
    manifest = {"created_utc": utc(), "input_library": str(INPUT.relative_to(ROOT)).replace("\\", "/"), "input_sha256": digest(INPUT), "measured_diameters_nm": [int(x) for x in ds], "missing_diameters_nm": [180], "real_row_count": 286, "enumerated_combination_count": n, "unique_combination_count": int(len(np.unique(r["indices"], axis=0))), "duplicate_combination_count": 0, "d180_combination_count": 0, "x_only": True, "K6_SUPERCELL_VALIDATION_STATUS": "not_run", "solver_calls": 0, "lumapi_import_count": 0, "MPI_call_count": 0, "all_metrics_path": npz.name, "all_metrics_sha256": digest(npz), "all_metrics_fields": sorted(r) + [f"gate_{name}" for name in names] + ["all_legacy_engineering_gates_pass", "pareto"], "all_metrics_row_count": n}
    dump(output / "exhaustive_search_manifest.json", manifest)
    verify = {"finite_data_gate": True, "combination_count_gate": n == 230230, "unique_combination_gate": manifest["unique_combination_count"] == 230230, "D180_excluded_gate": True, "all_engineering_gates_passing_sextet_exists": bool(all_pass.any()), "passing_sextet_count": int(len(passing_indices)), "pareto_front_count": int(len(pareto_indices)), "phase_champion_on_pareto": bool(pareto[phase[0]]), "amplitude_champion_on_pareto": bool(pareto[amplitude[0]]), "broadband_champion_on_pareto": bool(pareto[broadband[0]]), "x_only": True, "K6_SUPERCELL_VALIDATION_STATUS": "not_run"}
    dump(output / "verification_summary.json", verify)
    route = "SELECTED_MULTI_CANDIDATE_Y_POLARIZATION_VALIDATION" if bool(all_pass.any()) else "LOCAL_DIAMETER_REFINEMENT_DESIGN_OFFLINE"
    summary = {"champions": champions, "all_engineering_gates_passing_sextet_exists": bool(all_pass.any()), "passing_sextet_count": int(len(passing_indices)), "top_5_passing_sextets": top5_passing, "first_second_margin": first_second_margin, "failure_gate_statistics": failure, "closest_to_passing_top10": closest_detail, "pareto_front_count": int(len(pareto_indices)), "pareto_includes_D160": bool(np.any(np.any(digits[pareto] == 160, axis=1))), "pareto_includes_resonant": bool(np.any(np.any(np.isin(digits[pareto], [140,160,165,170,200,205,215,220,225]), axis=1))), "pareto_has_nonresonant_candidate": bool(np.any(~np.any(np.isin(digits[pareto], [140,160,165,170,200,205,215,220,225]), axis=1))), "d180": d180, "cyclic": cyclic, "selected_next_route": route}
    dump(output / "ranking_summary.json", summary)
    report = ROOT / "docs" / "np_k6_p1d2_26point_sixbin_exhaustive_ranking_v1.md"
    report.write_text("\n".join(["# NP-K6 P1-D2 exhaustive six-bin ranking", "", "- Measured data: 26/27 diameters, 286 real x-only rows; D180 remains sealed and is neither interpolated nor rerun.", f"- Exhaustive measured-only combinations: {n}.", "- Circular wrapped-phase fitting and all six cyclic steps, including D5-to-D0 closure, are evaluated at every 445-455 nm point.", f"- Passing combinations: {len(passing_indices)}.", f"- Pareto candidates: {len(pareto_indices)}.", f"- D180 recommendation: {d180['D180_RERUN_RECOMMENDATION']}.", f"- Selected route: {route}.", "- This is local-periodic single-pillar candidate evidence, not K=6 supercell diffraction-efficiency validation.", "- y polarization, K=6, solver, and MDC were not run.", ""]), encoding="utf-8")
    return {"manifest": manifest, "verification": verify, "champions": champions, "failure": failure, "pareto_indices": pareto_indices, "passing": passing_indices, "d180": d180}


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--output", type=Path, default=ROOT / "outputs" / OUTPUT_NAME); args = parser.parse_args()
    result = run(args.output); print(json.dumps({"manifest": result["manifest"], "verification": result["verification"]}, indent=2)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
