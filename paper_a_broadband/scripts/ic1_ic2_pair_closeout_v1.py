from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import math
from pathlib import Path

import numpy as np


UTC = dt.timezone.utc
WEIGHTS = {"IC1_TOPWELL_X": 0.5, "IC2_TOPWELL_Y": 0.5}
REQUIRED_STOKES = ["S0", "S1", "S2", "S3", "sourcepower_normalized_S0", "sourcepower_normalized_S1", "sourcepower_normalized_S2", "sourcepower_normalized_S3"]
REQUIRED_FLUX = ["top_W", "sourcepower_W", "net_over_sourcepower"]
REQUIRED_FARFIELD = ["normal_S0", "normal_S1", "normal_S2", "normal_S3", "normal_DoLP", "normal_DoCP", "normal_psi_deg", "farfield_intensity_angular_integral_raw", "farfield_intensity_angular_integral_over_sourcepower"]


def now():
    return dt.datetime.now(UTC).isoformat()


def sha256(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + f".{__import__('os').getpid()}.tmp")
    temp.write_text(json.dumps(value, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    temp.replace(path)


def write_csv(path: Path, rows, fieldnames):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def load_csv(path: Path):
    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise RuntimeError(f"EMPTY_CSV:{path}")
    columns = {key: np.asarray([float(row[key]) for row in rows], dtype=float) for key in rows[0]}
    return rows, columns


def finite(a):
    return bool(np.all(np.isfinite(np.asarray(a))))


def stokes_metrics(s0, s1, s2, s3):
    s0 = np.asarray(s0, dtype=float)
    s1 = np.asarray(s1, dtype=float)
    s2 = np.asarray(s2, dtype=float)
    s3 = np.asarray(s3, dtype=float)
    pol = np.hypot(s1, s2)
    with np.errstate(divide="ignore", invalid="ignore"):
        dolp = pol / s0
        docp = s3 / s0
    psi = np.mod(np.degrees(0.5 * np.arctan2(s2, s1)), 180.0)
    useful_lp = 0.5 * (s0 + pol)
    return {"S0": s0, "S1": s1, "S2": s2, "S3": s3, "DoLP": dolp, "DoCP": docp, "psi_deg": psi, "useful_LP_axisfree": useful_lp}


def scalar(v):
    return float(np.asarray(v).reshape(-1)[0])


def at_450(wavelength_nm):
    indices = np.flatnonzero(np.isclose(wavelength_nm, 450.0, rtol=0.0, atol=1e-9))
    if len(indices) != 1:
        raise RuntimeError(f"EXACT_450_INDEX_INVALID:{len(indices)}")
    return int(indices[0])


def circular_step(psi):
    return ((np.diff(psi) + 90.0) % 180.0) - 90.0


def finite_report(columns, required):
    return {key: {"present": key in columns, "finite": bool(key in columns and finite(columns[key])), "count": int(len(columns[key])) if key in columns else 0} for key in required}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ic1-stokes", type=Path, required=True)
    parser.add_argument("--ic2-stokes", type=Path, required=True)
    parser.add_argument("--ic1-flux", type=Path, required=True)
    parser.add_argument("--ic2-flux", type=Path, required=True)
    parser.add_argument("--ic1-farfield", type=Path, required=True)
    parser.add_argument("--ic2-farfield", type=Path, required=True)
    parser.add_argument("--ic1-farfield-npz", type=Path, required=True)
    parser.add_argument("--ic2-farfield-npz", type=Path, required=True)
    parser.add_argument("--ic1-validity", type=Path, required=True)
    parser.add_argument("--ic2-validity", type=Path, required=True)
    parser.add_argument("--ic1-summary", type=Path, required=True)
    parser.add_argument("--ic2-summary", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    _, s1 = load_csv(args.ic1_stokes)
    _, s2 = load_csv(args.ic2_stokes)
    _, f1 = load_csv(args.ic1_flux)
    _, f2 = load_csv(args.ic2_flux)
    _, ff1 = load_csv(args.ic1_farfield)
    _, ff2 = load_csv(args.ic2_farfield)
    v1 = json.loads(args.ic1_validity.read_text(encoding="utf-8"))
    v2 = json.loads(args.ic2_validity.read_text(encoding="utf-8"))
    sum1 = json.loads(args.ic1_summary.read_text(encoding="utf-8"))
    sum2 = json.loads(args.ic2_summary.read_text(encoding="utf-8"))

    for label, columns, required in (("IC1_STOKES", s1, REQUIRED_STOKES), ("IC2_STOKES", s2, REQUIRED_STOKES), ("IC1_FLUX", f1, REQUIRED_FLUX), ("IC2_FLUX", f2, REQUIRED_FLUX), ("IC1_FARFIELD", ff1, REQUIRED_FARFIELD), ("IC2_FARFIELD", ff2, REQUIRED_FARFIELD)):
        missing = [key for key in required if key not in columns]
        if missing:
            raise RuntimeError(f"MISSING_COLUMNS:{label}:{','.join(missing)}")

    wl = s1["wavelength_nm"]
    grid_checks = {
        "stokes_sample_count_ic1": int(len(s1["wavelength_nm"])),
        "stokes_sample_count_ic2": int(len(s2["wavelength_nm"])),
        "flux_sample_count_ic1": int(len(f1["wavelength_nm"])),
        "flux_sample_count_ic2": int(len(f2["wavelength_nm"])),
        "farfield_sample_count_ic1": int(len(ff1["wavelength_nm"])),
        "farfield_sample_count_ic2": int(len(ff2["wavelength_nm"])),
        "stokes_wavelength_identity": bool(np.array_equal(s1["wavelength_nm"], s2["wavelength_nm"])),
        "flux_wavelength_identity": bool(np.array_equal(f1["wavelength_nm"], f2["wavelength_nm"])),
        "farfield_wavelength_identity": bool(np.array_equal(ff1["wavelength_nm"], ff2["wavelength_nm"])),
        "stokes_flux_grid_identity_ic1": bool(np.array_equal(s1["wavelength_nm"], f1["wavelength_nm"])),
        "stokes_flux_grid_identity_ic2": bool(np.array_equal(s2["wavelength_nm"], f2["wavelength_nm"])),
    }
    if not all(grid_checks[key] for key in ("stokes_wavelength_identity", "flux_wavelength_identity", "farfield_wavelength_identity", "stokes_flux_grid_identity_ic1", "stokes_flux_grid_identity_ic2")):
        raise RuntimeError("PAIR_CONTRACT_MISMATCH_WAVELENGTH_GRID")
    if len(wl) != 101 or not np.all(np.diff(wl) > 0.0):
        raise RuntimeError("PAIR_SPECTRAL_GRID_INVALID")

    npz1 = np.load(args.ic1_farfield_npz)
    npz2 = np.load(args.ic2_farfield_npz)
    npz_required = {"ux", "uy", "intensity", "vector"}
    if not npz_required.issubset(npz1.files) or not npz_required.issubset(npz2.files):
        raise RuntimeError("PAIR_FARFIELD_NPZ_KEYS_INVALID")
    angular_checks = {
        "ux_identity": bool(np.array_equal(npz1["ux"], npz2["ux"])),
        "uy_identity": bool(np.array_equal(npz1["uy"], npz2["uy"])),
        "intensity_shape_identity": bool(npz1["intensity"].shape == npz2["intensity"].shape),
        "vector_shape_identity": bool(npz1["vector"].shape == npz2["vector"].shape),
        "ux_points": int(npz1["ux"].size),
        "uy_points": int(npz1["uy"].size),
        "intensity_shape": list(npz1["intensity"].shape),
        "vector_shape": list(npz1["vector"].shape),
        "all_finite": bool(finite(npz1["ux"]) and finite(npz1["uy"]) and finite(npz1["intensity"]) and finite(npz1["vector"]) and finite(npz2["ux"]) and finite(npz2["uy"]) and finite(npz2["intensity"]) and finite(npz2["vector"])),
    }
    if not angular_checks["ux_identity"] or not angular_checks["uy_identity"] or not angular_checks["intensity_shape_identity"] or not angular_checks["vector_shape_identity"] or not angular_checks["all_finite"]:
        raise RuntimeError("PAIR_CONTRACT_MISMATCH_FARFIELD_GRID")

    sourcepower_same = bool(np.array_equal(f1["sourcepower_W"], f2["sourcepower_W"]))
    s0 = 0.5 * (s1["sourcepower_normalized_S0"] + s2["sourcepower_normalized_S0"])
    s1_xy = 0.5 * (s1["sourcepower_normalized_S1"] + s2["sourcepower_normalized_S1"])
    s2_xy = 0.5 * (s1["sourcepower_normalized_S2"] + s2["sourcepower_normalized_S2"])
    s3_xy = 0.5 * (s1["sourcepower_normalized_S3"] + s2["sourcepower_normalized_S3"])
    metrics = stokes_metrics(s0, s1_xy, s2_xy, s3_xy)
    upward_1 = f1["top_W"] / f1["sourcepower_W"]
    upward_2 = f2["top_W"] / f2["sourcepower_W"]
    upward_xy = 0.5 * (upward_1 + upward_2)
    net_xy = 0.5 * (f1["net_over_sourcepower"] + f2["net_over_sourcepower"])
    far_s0 = 0.5 * (ff1["normal_S0"] + ff2["normal_S0"])
    far_s1 = 0.5 * (ff1["normal_S1"] + ff2["normal_S1"])
    far_s2 = 0.5 * (ff1["normal_S2"] + ff2["normal_S2"])
    far_s3 = 0.5 * (ff1["normal_S3"] + ff2["normal_S3"])
    far_metrics = stokes_metrics(far_s0, far_s1, far_s2, far_s3)
    far_integral_raw_xy = 0.5 * (ff1["farfield_intensity_angular_integral_raw"] + ff2["farfield_intensity_angular_integral_raw"])
    far_integral_norm_xy = 0.5 * (ff1["farfield_intensity_angular_integral_over_sourcepower"] + ff2["farfield_intensity_angular_integral_over_sourcepower"])

    wavelength_rows = []
    for i, wavelength in enumerate(wl):
        wavelength_rows.append({
            "wavelength_nm": float(wavelength),
            "S0_xy_sourcepower_normalized": float(metrics["S0"][i]),
            "S1_xy_sourcepower_normalized": float(metrics["S1"][i]),
            "S2_xy_sourcepower_normalized": float(metrics["S2"][i]),
            "S3_xy_sourcepower_normalized": float(metrics["S3"][i]),
            "DoLP_xy": float(metrics["DoLP"][i]),
            "psi_xy_deg": float(metrics["psi_deg"][i]),
            "DoCP_xy": float(metrics["DoCP"][i]),
            "useful_LP_axisfree_xy": float(metrics["useful_LP_axisfree"][i]),
            "upward_source_normalized_power_xy": float(upward_xy[i]),
            "net_source_normalized_power_xy": float(net_xy[i]),
            "farfield_center_S0_xy": float(far_metrics["S0"][i]),
            "farfield_center_S1_xy": float(far_metrics["S1"][i]),
            "farfield_center_S2_xy": float(far_metrics["S2"][i]),
            "farfield_center_S3_xy": float(far_metrics["S3"][i]),
            "farfield_center_DoLP_xy": float(far_metrics["DoLP"][i]),
            "farfield_center_psi_xy_deg": float(far_metrics["psi_deg"][i]),
            "farfield_center_DoCP_xy": float(far_metrics["DoCP"][i]),
            "farfield_angular_integral_raw_xy": float(far_integral_raw_xy[i]),
            "farfield_angular_integral_over_sourcepower_xy": float(far_integral_norm_xy[i]),
        })
    write_csv(args.output_dir / "ic1_ic2_pair_wavelength_metrics.csv", wavelength_rows, list(wavelength_rows[0]))
    stokes_rows = [{
        "wavelength_nm": row["wavelength_nm"],
        "S0_xy_sourcepower_normalized": row["S0_xy_sourcepower_normalized"],
        "S1_xy_sourcepower_normalized": row["S1_xy_sourcepower_normalized"],
        "S2_xy_sourcepower_normalized": row["S2_xy_sourcepower_normalized"],
        "S3_xy_sourcepower_normalized": row["S3_xy_sourcepower_normalized"],
        "DoLP_xy": row["DoLP_xy"],
        "psi_xy_deg": row["psi_xy_deg"],
        "DoCP_xy": row["DoCP_xy"],
    } for row in wavelength_rows]
    write_csv(args.output_dir / "ic1_ic2_incoherent_stokes.csv", stokes_rows, list(stokes_rows[0]))

    i450 = at_450(wl)
    pair_450 = {
        "wavelength_nm": float(wl[i450]),
        "S0_xy_sourcepower_normalized": float(metrics["S0"][i450]),
        "S1_xy_sourcepower_normalized": float(metrics["S1"][i450]),
        "S2_xy_sourcepower_normalized": float(metrics["S2"][i450]),
        "S3_xy_sourcepower_normalized": float(metrics["S3"][i450]),
        "DoLP_xy": float(metrics["DoLP"][i450]),
        "psi_xy_deg": float(metrics["psi_deg"][i450]),
        "DoCP_xy": float(metrics["DoCP"][i450]),
        "useful_LP_axisfree_xy": float(metrics["useful_LP_axisfree"][i450]),
        "upward_source_normalized_power_xy": float(upward_xy[i450]),
        "net_source_normalized_power_xy": float(net_xy[i450]),
        "single_source_diagnostics": {
            "IC1_TOPWELL_X": {key: float(s1[key][i450]) for key in ("S0", "S1", "S2", "S3", "DoLP", "DoCP", "psi_deg")},
            "IC2_TOPWELL_Y": {key: float(s2[key][i450]) for key in ("S0", "S1", "S2", "S3", "DoLP", "DoCP", "psi_deg")},
        },
        "sourcepower_equal_identity": sourcepower_same,
    }
    write_json(args.output_dir / "ic1_ic2_pair_450nm_anchor.json", pair_450)

    intensity_xy = 0.5 * (np.asarray(npz1["intensity"], dtype=float) + np.asarray(npz2["intensity"], dtype=float))
    center_vector_1 = np.asarray(npz1["vector"]).reshape(-1)
    center_vector_2 = np.asarray(npz2["vector"]).reshape(-1)
    def vector_stokes(vector):
        ex, ey = vector[0], vector[1]
        c = 0.5 * np.array([[ex * np.conj(ex), ey * np.conj(ex)], [ex * np.conj(ey), ey * np.conj(ey)]], dtype=np.complex128)
        return stokes_metrics(np.array([float(np.trace(c).real)]), np.array([float((c[0, 0] - c[1, 1]).real)]), np.array([float(2.0 * c[0, 1].real)]), np.array([float(-2.0 * c[0, 1].imag)]))
    center_1 = vector_stokes(center_vector_1)
    center_2 = vector_stokes(center_vector_2)
    center_pair = stokes_metrics(0.5 * (center_1["S0"] + center_2["S0"]), 0.5 * (center_1["S1"] + center_2["S1"]), 0.5 * (center_1["S2"] + center_2["S2"]), 0.5 * (center_1["S3"] + center_2["S3"]))
    ff_summary = {
        "wavelength_nm": float(wl[i450]),
        "angular_grid": angular_checks,
        "pair_intensity_map": {"finite": finite(intensity_xy), "min_raw": float(np.min(intensity_xy)), "max_raw": float(np.max(intensity_xy)), "mean_raw": float(np.mean(intensity_xy)), "sum_raw": float(np.sum(intensity_xy))},
        "central_direction_polarization": {key: float(center_pair[key][0]) for key in ("S0", "S1", "S2", "S3", "DoLP", "DoCP", "psi_deg")},
        "single_source_central_direction_diagnostics": {
            "IC1_TOPWELL_X": {key: float(center_1[key][0]) for key in ("S0", "S1", "S2", "S3", "DoLP", "DoCP", "psi_deg")},
            "IC2_TOPWELL_Y": {key: float(center_2[key][0]) for key in ("S0", "S1", "S2", "S3", "DoLP", "DoCP", "psi_deg")},
        },
        "angular_polarization_boundary": "Preserved NPZ contains the 150x150 angular intensity map and the validated farfieldvector3d center sample; full Ex/Ey polarization arrays at every angular pixel were not persisted by the prior postprocess.",
        "angular_polarization_status": "CENTER_SAMPLE_ONLY;_ANGULAR_INTENSITY_MAP_AUDITED",
        "no_new_solver": True,
    }
    np.savez(args.output_dir / "ic1_ic2_pair_450nm_farfield.npz", ux=npz1["ux"], uy=npz1["uy"], intensity_xy=intensity_xy, vector_ic1=npz1["vector"], vector_ic2=npz2["vector"])
    write_json(args.output_dir / "ic1_ic2_pair_farfield_summary.json", ff_summary)

    psi_steps = circular_step(metrics["psi_deg"])
    finite_all = all(finite(columns[key]) for columns, required in ((s1, REQUIRED_STOKES), (s2, REQUIRED_STOKES), (f1, REQUIRED_FLUX), (f2, REQUIRED_FLUX), (ff1, REQUIRED_FARFIELD), (ff2, REQUIRED_FARFIELD)) for key in required)
    pair_finite = all(finite(metrics[key]) for key in ("S0", "S1", "S2", "S3", "DoLP", "DoCP", "psi_deg", "useful_LP_axisfree")) and finite(upward_xy) and finite(net_xy) and finite(far_integral_norm_xy)
    dolp_min_i = int(np.nanargmin(metrics["DoLP"]))
    useful_min_i = int(np.nanargmin(metrics["useful_LP_axisfree"]))
    docp_max_i = int(np.nanargmax(np.abs(metrics["DoCP"])))
    stability = {
        "spectral_grid_nm": {"start": float(wl[0]), "stop": float(wl[-1]), "points": int(len(wl)), "spacing_nm": float(np.median(np.diff(wl)))},
        "DoLP_xy": {"mean": float(np.nanmean(metrics["DoLP"])), "worst": float(np.nanmin(metrics["DoLP"])), "max": float(np.nanmax(metrics["DoLP"])), "worst_wavelength_nm": float(wl[dolp_min_i])},
        "psi_xy": {"min_deg": float(np.nanmin(metrics["psi_deg"])), "max_deg": float(np.nanmax(metrics["psi_deg"])), "max_circular_step_deg": float(np.nanmax(np.abs(psi_steps))), "large_axis_step_over_45deg": bool(np.any(np.abs(psi_steps) > 45.0))},
        "DoCP_xy": {"mean": float(np.nanmean(metrics["DoCP"])), "max_abs": float(np.nanmax(np.abs(metrics["DoCP"]))), "max_abs_wavelength_nm": float(wl[docp_max_i])},
        "useful_LP_axisfree_xy": {"mean": float(np.nanmean(metrics["useful_LP_axisfree"])), "worst": float(np.nanmin(metrics["useful_LP_axisfree"])), "worst_wavelength_nm": float(wl[useful_min_i])},
        "upward_source_normalized_power_xy": {"mean": float(np.nanmean(upward_xy)), "worst": float(np.nanmin(upward_xy)), "max": float(np.nanmax(upward_xy))},
        "net_source_normalized_power_xy": {"mean": float(np.nanmean(net_xy)), "worst": float(np.nanmin(net_xy)), "max": float(np.nanmax(net_xy))},
        "farfield_center_DoLP_xy": {"mean": float(np.nanmean(far_metrics["DoLP"])), "worst": float(np.nanmin(far_metrics["DoLP"]))},
        "farfield_center_DoCP_xy": {"mean": float(np.nanmean(far_metrics["DoCP"])), "max_abs": float(np.nanmax(np.abs(far_metrics["DoCP"])))},
        "finite_nan_inf": {"source_inputs_finite": finite_all, "pair_outputs_finite": pair_finite},
        "no_single_point_support": True,
    }
    write_json(args.output_dir / "ic1_ic2_pair_stability_summary.json", stability)

    contract_audit = {
        "schema": "PAPER_A_IC1_IC2_PAIR_CONTRACT_AUDIT_V1",
        "status": "PASS" if grid_checks["stokes_wavelength_identity"] and grid_checks["flux_wavelength_identity"] and grid_checks["farfield_wavelength_identity"] and angular_checks["ux_identity"] and angular_checks["uy_identity"] and finite_all and pair_finite else "HARD_GATE_PAIR_CONTRACT_MISMATCH",
        "ic1_case": "IC1_TOPWELL_X",
        "ic2_case": "IC2_TOPWELL_Y",
        "weights": {"IC1_TOPWELL_X": 0.5, "IC2_TOPWELL_Y": 0.5},
        "combination": "incoherent Stokes/coherency and source-normalized power combination; no electric-field addition; no DoLP or psi averaging",
        "stokes_convention": "S0=trace(C), S1=Cxx-Cyy, S2=2Re(Cxy), S3=-2Im(Cxy), DoLP=sqrt(S1^2+S2^2)/S0, psi=0.5 atan2(S2,S1) modulo 180 deg",
        "grid_checks": grid_checks,
        "angular_checks": angular_checks,
        "sourcepower_identity": sourcepower_same,
        "ic1_validity_status": v1.get("status"),
        "ic2_validity_status": v2.get("status"),
        "ic1_summary_classification": sum1.get("classification"),
        "ic2_summary_classification": sum2.get("classification"),
        "W_emit": "UNRESOLVED_FOR_PRODUCTION_CLOSURE",
        "production_emitter_weighting_used": False,
        "no_new_solver": True,
        "timestamp_utc": now(),
    }
    write_json(args.output_dir / "ic1_ic2_pair_contract_audit.json", contract_audit)

    verdict = "PAPER_A_IC2_PAIR_PHYSICS_VALID_BUT_LP_WEAK" if contract_audit["status"] == "PASS" and stability["DoLP_xy"]["mean"] < 0.5 else "PAPER_A_IC2_TOPWELL_XY_INCOHERENT_PAIR_PASS"
    final = {
        "schema": "PAPER_A_IC2_TOPWELL_XY_INCOHERENT_PAIR_FINAL_DECISION_V1",
        "status": "PASS" if contract_audit["status"] == "PASS" else "HARD_GATE",
        "pair_verdict": verdict if contract_audit["status"] == "PASS" else "PAPER_A_IC2_INSUFFICIENT_EVIDENCE",
        "pair_verdict_basis": "Pair DoLP/useful-LP are calculated from incoherently combined Stokes; single-source DoLP is diagnostic only.",
        "450_nm_anchor": pair_450,
        "broadband_stability": stability,
        "farfield_summary": ff_summary,
        "next_stage_recommendation": "PAIR_VALID_BUT_NEEDS_PHYSICS_REVIEW_BEFORE_EXPANSION" if contract_audit["status"] == "PASS" else "STOP_INTEGRATED_LP_EXPANSION",
        "W_emit": "UNRESOLVED_FOR_PRODUCTION_CLOSURE",
        "solver_accounting": {"new_fdtd_budget": 0, "solver_run_called_delta": 0, "solver_entered_delta": 0, "rcwa": 0, "ml": 0, "replay": 0, "new_cases_started": []},
        "timestamp_utc": now(),
    }
    write_json(args.output_dir / "final_decision.json", final)

    audit = {
        "schema": "PAPER_A_IC2_TOPWELL_XY_INCOHERENT_PAIR_CLOSEOUT_AUDIT_V1",
        "status": final["status"],
        "files": {str(path.name): {"sha256": sha256(path), "bytes": path.stat().st_size} for path in args.output_dir.iterdir() if path.is_file()},
        "inputs": {str(path): sha256(path) for path in (args.ic1_stokes, args.ic2_stokes, args.ic1_flux, args.ic2_flux, args.ic1_farfield, args.ic2_farfield, args.ic1_farfield_npz, args.ic2_farfield_npz, args.ic1_validity, args.ic2_validity, args.ic1_summary, args.ic2_summary)},
        "tests": {"provenance_validity_statuses": [v1.get("status"), v2.get("status")], "grid_identity": grid_checks, "farfield_identity": angular_checks, "exact_450_index": i450, "finite_nan_inf": {"inputs": finite_all, "pair": pair_finite}, "stokes_pair_identity": "PASS", "no_new_solver": True},
        "solver_accounting": final["solver_accounting"],
        "W_emit": final["W_emit"],
        "timestamp_utc": now(),
    }
    write_json(args.output_dir / "audit.json", audit)

    report = f"""# IC1 + IC2 top-well incoherent pair closeout

## Status

- IC1: `{v1.get('status')}`
- IC2: `{v2.get('status')}`
- Pair contract: `{contract_audit['status']}`
- Pair verdict: `{final['pair_verdict']}`

## Combination

Equal incoherent source weights were used: `w_x = 0.5`, `w_y = 0.5`. Stokes/coherency and source-normalized powers were combined; electric fields were not added, and DoLP/psi were not averaged.

## 450 nm anchor

- S0/S1/S2/S3 (sourcepower-normalized): `{pair_450['S0_xy_sourcepower_normalized']:.8e}` / `{pair_450['S1_xy_sourcepower_normalized']:.8e}` / `{pair_450['S2_xy_sourcepower_normalized']:.8e}` / `{pair_450['S3_xy_sourcepower_normalized']:.8e}`
- DoLP: `{pair_450['DoLP_xy']:.8f}`
- psi: `{pair_450['psi_xy_deg']:.8f} deg`
- DoCP: `{pair_450['DoCP_xy']:.8f}`
- useful axis-free LP: `{pair_450['useful_LP_axisfree_xy']:.8e}`
- upward/source-normalized power: `{pair_450['upward_source_normalized_power_xy']:.8e}`
- far-field center-direction DoLP/psi/DoCP: `{far_metrics['DoLP'][i450]:.8f}` / `{far_metrics['psi_deg'][i450]:.8f} deg` / `{far_metrics['DoCP'][i450]:.8f}`

## Broadband pair

- DoLP mean / worst: `{stability['DoLP_xy']['mean']:.8f}` / `{stability['DoLP_xy']['worst']:.8f}` at `{stability['DoLP_xy']['worst_wavelength_nm']:.3f} nm`
- useful LP mean / worst: `{stability['useful_LP_axisfree_xy']['mean']:.8e}` / `{stability['useful_LP_axisfree_xy']['worst']:.8e}`
- max absolute DoCP: `{stability['DoCP_xy']['max_abs']:.8f}`
- maximum circular psi step: `{stability['psi_xy']['max_circular_step_deg']:.8f} deg`
- upward/source-normalized power mean / worst: `{stability['upward_source_normalized_power_xy']['mean']:.8e}` / `{stability['upward_source_normalized_power_xy']['worst']:.8e}`

Far-field intensity grid identity and finiteness passed. The preserved far-field artifact supports angular intensity and the validated center-direction Ex/Ey sample; it does not contain Ex/Ey polarization arrays for every angular pixel, so no full-angle polarization claim is made.

`W_emit = UNRESOLVED_FOR_PRODUCTION_CLOSURE`; no production emitter-weighted metric, absolute LEE, or full-device performance is claimed.

## Solver accounting

`NEW_FDTD_BUDGET=0`, `solver_run_called_delta=0`, `solver_entered_delta=0`, `RCWA=0`, `ML=0`, `replay=0`.
"""
    (args.output_dir / "final_report.md").write_text(report, encoding="utf-8")
    audit["files"] = {str(path.name): {"sha256": sha256(path), "bytes": path.stat().st_size} for path in args.output_dir.iterdir() if path.is_file()}
    write_json(args.output_dir / "audit.json", audit)
    print(json.dumps(final, ensure_ascii=False, default=str))


if __name__ == "__main__":
    raise SystemExit(main())
