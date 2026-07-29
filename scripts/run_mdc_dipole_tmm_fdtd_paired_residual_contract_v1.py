"""Build a read-only, 18-case Dipole-TMM to 2D-FDTD residual evidence set.

This script never imports lumapi and never modifies either frozen source run.
It records model discrepancy, not an absolute-power or Purcell residual.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import mdc_dipole_tmm as tmm
import run_mdc_native_m1_2d_dipole_device_comparison_v1 as frozen

CONFIG = json.loads((ROOT / "configs" / "mdc_dipole_tmm_fdtd_paired_residual_contract_v1.json").read_text())
FDTD_ROOT = ROOT / CONFIG["frozen_fdtd_root"]


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def fingerprint(values: np.ndarray) -> str:
    return hashlib.sha256(np.asarray(values, dtype=np.float64).tobytes()).hexdigest()


def dump(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False), encoding="utf-8")


def area_normalize(grid: np.ndarray, values: np.ndarray) -> np.ndarray:
    area = float(np.trapezoid(values, grid))
    if not np.isfinite(area) or area <= 0:
        raise ValueError("nonpositive curve integral")
    return values / area


def fwhm(grid: np.ndarray, values: np.ndarray) -> float:
    peak = float(np.max(values))
    if not np.isfinite(peak) or peak <= 0:
        raise ValueError("nonpositive curve peak")
    idx = np.flatnonzero(values >= peak / 2.0)
    if not len(idx):
        raise ValueError("fwhm undefined")
    return float(grid[idx[-1]] - grid[idx[0]])


def cone(angles: np.ndarray, normalized: np.ndarray, degrees: float) -> float:
    mask = np.abs(angles) <= degrees
    return float(np.trapezoid(normalized[mask], np.deg2rad(angles[mask])))


def curve_stats(reference: np.ndarray, prediction: np.ndarray, grid: np.ndarray) -> dict[str, float]:
    delta = prediction - reference
    corr = float(np.corrcoef(reference, prediction)[0, 1]) if np.std(reference) > 0 and np.std(prediction) > 0 else float("nan")
    return {"mae": float(np.mean(np.abs(delta))), "rmse": float(np.sqrt(np.mean(delta**2))),
            "max_abs_error": float(np.max(np.abs(delta))), "correlation": corr,
            "integrated_absolute_difference": float(np.trapezoid(np.abs(delta), grid))}


def candidate_map(case_index: pd.DataFrame) -> dict[str, tmm.Candidate]:
    records = {x["structure_key"]: x for x in frozen.structures()}
    mapping: dict[str, tmm.Candidate] = {}
    for key, group in case_index.groupby("candidate_key"):
        record = records.get(key)
        if record is None:
            raise RuntimeError(f"FDTD candidate key missing from frozen builder: {key}")
        if set(group.candidate_id) != ({"BARE_GAN_AIR_REFERENCE"} if key == "bare" else {record["structure_id"]}):
            raise RuntimeError(f"candidate ID drift for {key}")
        if set(group.geometry_hash) != {record["geometry_hash"]}:
            raise RuntimeError(f"geometry hash drift for {key}")
        layers = tuple(("APCD_TIO2_NATIVE_M1" if name == "H" else "APCD_SIO2_NATIVE_M1", float(thickness)) for name, thickness in record["sequence"])
        mapping[key] = tmm.Candidate(group.candidate_id.iloc[0], record["geometry_hash"], layers)
    if set(mapping) != {"bare", "zl1_nominal", "zl1_alternative"}:
        raise RuntimeError("exactly the frozen Bare/nominal/alternative candidates are required")
    return mapping


def tmm_curves(candidate: tmm.Candidate, depth: float, orientation: str, wavelengths: np.ndarray, angles: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    spectrum = np.array([tmm.dipole_channel(candidate, float(w), 0.0, depth, orientation)["I_air_relative"] for w in wavelengths], dtype=float)
    angular = np.array([tmm.dipole_channel(candidate, 450.0, float(a), depth, orientation)["I_air_relative"] for a in angles], dtype=float)
    if not (np.isfinite(spectrum).all() and np.isfinite(angular).all() and (spectrum > 0).all() and (angular > 0).all()):
        raise ValueError("nonpositive or nonfinite Dipole-TMM channel")
    return spectrum, angular


def run(output: Path) -> None:
    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True)
    case = pd.read_parquet(FDTD_ROOT / "case_manifest.parquet").copy()
    spectral = pd.read_parquet(FDTD_ROOT / "spectral_normalized.parquet")
    angular_formal = pd.read_parquet(FDTD_ROOT / "angular_filter_0p2.parquet")
    angular_audit = pd.read_parquet(FDTD_ROOT / "angular_filter_0.parquet")
    sub = pd.read_parquet(FDTD_ROOT / "subrun_metrics.parquet")
    manifest = json.loads((FDTD_ROOT / "manifest.json").read_text())
    provenance = json.loads((FDTD_ROOT / "provenance.json").read_text())
    if not (len(case) == 18 and case.case_id.is_unique and (case.status == "COMPLETE").all()):
        raise RuntimeError("FDTD exact-once closure not established")
    keys = ["candidate_id", "geometry_hash", "source_position_nm", "source_role", "orientation"]
    wavelengths = np.sort(spectral.wavelength_nm.unique())
    angles = np.sort(angular_formal.air_angle_deg.unique())
    # The FDTD far-field exporter retained a strictly finer monotone angular
    # grid than the nominal 1-degree minimum.  Directly evaluating TMM at its
    # retained points is lossless and avoids any angular interpolation.
    if not (len(wavelengths) == 301 and np.allclose(wavelengths, np.linspace(420, 480, 301), rtol=0, atol=1e-9) and len(angles) >= 121 and angles.min() >= -60 and angles.max() <= 60):
        raise RuntimeError("frozen FDTD grid mismatch")
    cmap = candidate_map(case)
    tmm_code_sha = sha(ROOT / "scripts" / "mdc_dipole_tmm.py")
    fdtd_manifest_sha = sha(FDTD_ROOT / "manifest.json")
    pairs, scalars, spectra, angulars, residuals, curves, power_rows = [], [], [], [], [], [], []
    for _, row in case.sort_values("case_id").iterrows():
        selector = {k: row[k] for k in keys}
        fs = spectral.loc[np.logical_and.reduce([spectral[k].eq(v) for k, v in selector.items()])].sort_values("wavelength_nm")
        angular_selector = {k: selector[k] for k in ("candidate_id", "source_position_nm", "orientation")}
        fa = angular_formal.loc[np.logical_and.reduce([angular_formal[k].eq(v) for k, v in angular_selector.items()])].sort_values("air_angle_deg")
        f0 = angular_audit.loc[np.logical_and.reduce([angular_audit[k].eq(v) for k, v in angular_selector.items()])].sort_values("air_angle_deg")
        if len(fs) != 301 or len(fa) < 121 or len(f0) != len(fa):
            raise RuntimeError(f"missing FDTD curve rows for {row.case_id}")
        pair_angles = fa.air_angle_deg.to_numpy(float)
        if not (np.all(np.diff(pair_angles) > 0) and len(pair_angles) >= 121 and pair_angles.min() >= -60 and pair_angles.max() <= 60):
            raise RuntimeError(f"invalid retained FDTD angular grid for {row.case_id}")
        ts, ta = tmm_curves(cmap[row.candidate_key], float(row.source_position_nm), row.orientation, wavelengths, pair_angles)
        fs_raw, fs_norm = fs.P_top_raw.to_numpy(float), fs.spectral_normalized.to_numpy(float)
        fa_raw, fa_norm = fa.raw_intensity.to_numpy(float), fa.normalized_intensity.to_numpy(float)
        f0_norm = f0.normalized_intensity.to_numpy(float)
        ts_norm = area_normalize(wavelengths, ts)
        ta_norm = area_normalize(np.deg2rad(pair_angles), ta)
        pair_id = f"{row.case_id}__dtmm"
        common = {"pair_id": pair_id, **selector, "candidate_key": row.candidate_key,
                  "fdtd_case_id": row.case_id, "fdtd_post_fsp_sha256": row.post_fsp_sha256,
                  "fdtd_manifest_sha256": fdtd_manifest_sha, "dipole_tmm_code_sha256": tmm_code_sha,
                  "wavelength_grid_fingerprint": fingerprint(wavelengths), "angle_grid_fingerprint": fingerprint(pair_angles),
                  "normalization_contract": CONFIG["normalization_contract"], "formal_filter": "0.2", "audit_filter": "0"}
        pairs.append(common)
        sm = {**common, "fdtd_spectral_peak_wavelength_nm": float(fs.wavelength_nm.iloc[np.argmax(fs_raw)]),
              "dtmm_spectral_peak_wavelength_nm": float(wavelengths[np.argmax(ts)]),
              "fdtd_spectral_fwhm_nm": fwhm(wavelengths, fs_raw), "dtmm_spectral_fwhm_nm": fwhm(wavelengths, ts),
              "fdtd_angular_fwhm_deg": fwhm(pair_angles, fa_raw), "dtmm_angular_fwhm_deg": fwhm(pair_angles, ta),
              "fdtd_peak_angle_deg": float(pair_angles[np.argmax(fa_raw)]), "dtmm_peak_angle_deg": float(pair_angles[np.argmax(ta)]),
              "fdtd_eta_up_r12_450": float(sub.loc[sub.case_id.eq(row.case_id), "eta_up_r12_450"].iloc[0]),
              "dtmm_I_air_raw_relative_450": float(ts[int(np.argmin(np.abs(wavelengths - 450.0)))]),
              "fdtd_filter0_cone10": cone(pair_angles, f0_norm, 10), "fdtd_filter02_cone10": cone(pair_angles, fa_norm, 10)}
        for degree in (5, 10, 20):
            sm[f"fdtd_cone{degree}"] = cone(pair_angles, fa_norm, degree)
            sm[f"dtmm_cone{degree}"] = cone(pair_angles, ta_norm, degree)
        scalars.append(sm)
        for wl, fr, fn, tr, tn in zip(wavelengths, fs_raw, fs_norm, ts, ts_norm):
            spectra.append({**common, "wavelength_nm": float(wl), "fdtd_raw": float(fr), "fdtd_normalized": float(fn), "dtmm_raw_relative": float(tr), "dtmm_normalized": float(tn), "spectral_pointwise_residual": float(tn - fn)})
        for angle, fr, fn, tr, tn in zip(pair_angles, fa_raw, fa_norm, ta, ta_norm):
            angulars.append({**common, "air_angle_deg": float(angle), "fdtd_raw_filter_0p2": float(fr), "fdtd_normalized_filter_0p2": float(fn), "dtmm_raw_relative": float(tr), "dtmm_normalized": float(tn), "angular_pointwise_residual_filter_0p2": float(tn - fn)})
        residuals.append({**common, "delta_peak_wavelength_nm": sm["dtmm_spectral_peak_wavelength_nm"] - sm["fdtd_spectral_peak_wavelength_nm"], "delta_spectral_fwhm_nm": sm["dtmm_spectral_fwhm_nm"] - sm["fdtd_spectral_fwhm_nm"], "delta_angular_fwhm_deg": sm["dtmm_angular_fwhm_deg"] - sm["fdtd_angular_fwhm_deg"], "delta_cone5": sm["dtmm_cone5"] - sm["fdtd_cone5"], "delta_cone10": sm["dtmm_cone10"] - sm["fdtd_cone10"], "delta_cone20": sm["dtmm_cone20"] - sm["fdtd_cone20"]})
        for kind, g, a, b in (("spectral", wavelengths, fs_norm, ts_norm), ("angular_filter_0p2", np.deg2rad(pair_angles), fa_norm, ta_norm)):
            curves.append({**common, "curve_kind": kind, **curve_stats(a, b, g)})
    scalar = pd.DataFrame(scalars)
    for _, r in scalar.iterrows():
        bare = scalar.loc[(scalar.candidate_key == "bare") & (scalar.source_position_nm == r.source_position_nm) & (scalar.orientation == r.orientation)]
        if len(bare) != 1:
            raise RuntimeError("Bare reference pairing ambiguity")
        b = bare.iloc[0]
        fdtd_ratio = r.fdtd_eta_up_r12_450 / b.fdtd_eta_up_r12_450
        dtmm_ratio = r.dtmm_I_air_raw_relative_450 / b.dtmm_I_air_raw_relative_450
        residual = 0.0 if r.candidate_key == "bare" else float(math.log(fdtd_ratio) - math.log(dtmm_ratio))
        power_rows.append({"pair_id": r.pair_id, "candidate_id": r.candidate_id, "candidate_key": r.candidate_key, "source_position_nm": r.source_position_nm, "orientation": r.orientation, "fdtd_eta_up_r12_450": r.fdtd_eta_up_r12_450, "dtmm_I_air_raw_relative_450": r.dtmm_I_air_raw_relative_450, "fdtd_candidate_to_bare_ratio": fdtd_ratio, "dtmm_candidate_to_bare_ratio": dtmm_ratio, "power_log_ratio_residual": residual})
    power = pd.DataFrame(power_rows)
    residual = pd.DataFrame(residuals).merge(power[["pair_id", "power_log_ratio_residual"]], on="pair_id", validate="one_to_one")
    # Position and polarization are model-specific diagnostics, never new independent geometries.
    pos_rows, pol_rows = [], []
    for model, value in (("FDTD", "fdtd_eta_up_r12_450"), ("Dipole-TMM", "dtmm_I_air_raw_relative_450")):
        for cid, g in scalar.groupby("candidate_id"):
            avg = g.groupby("source_position_nm")[value].mean()
            pos_rows.append({"model": model, "candidate_id": cid, "three_position_mean": float(avg.mean()), "three_position_min": float(avg.min()), "three_position_max": float(avg.max()), "three_position_relative_span": float((avg.max()-avg.min())/avg.max())})
        for (cid, depth), g in scalar.groupby(["candidate_id", "source_position_nm"]):
            x, z = float(g.loc[g.orientation.eq("x"), value].iloc[0]), float(g.loc[g.orientation.eq("z"), value].iloc[0])
            pol_rows.append({"model": model, "candidate_id": cid, "source_position_nm": depth, "x_value": x, "z_value": z, "xz_relative_difference": abs(x-z)/((x+z)/2)})
    pos, pol = pd.DataFrame(pos_rows), pd.DataFrame(pol_rows)
    # Ranking is separated by metric, with a diagnostic composite that is explicitly not a champion decision.
    rank_rows = []
    rank_specs = [("relative_upward_power", "fdtd_eta_up_r12_450", "dtmm_I_air_raw_relative_450", False), ("spectral_fwhm", "fdtd_spectral_fwhm_nm", "dtmm_spectral_fwhm_nm", False), ("angular_fwhm", "fdtd_angular_fwhm_deg", "dtmm_angular_fwhm_deg", False), ("cone5", "fdtd_cone5", "dtmm_cone5", True), ("cone10", "fdtd_cone10", "dtmm_cone10", True)]
    for label, fcol, tcol, desc in rank_specs:
        for model, col in (("FDTD", fcol), ("Dipole-TMM", tcol)):
            scores = scalar.groupby("candidate_id")[col].mean().sort_values(ascending=not desc)
            for order, (cid, score) in enumerate(scores.items(), 1): rank_rows.append({"ranking_metric": label, "model": model, "candidate_id": cid, "score": float(score), "rank": order, "diagnostic_only": True})
    composite = scalar.groupby("candidate_id")[["fdtd_eta_up_r12_450", "fdtd_cone10", "dtmm_I_air_raw_relative_450", "dtmm_cone10"]].mean()
    for model, p, c in (("FDTD", "fdtd_eta_up_r12_450", "fdtd_cone10"), ("Dipole-TMM", "dtmm_I_air_raw_relative_450", "dtmm_cone10")):
        score = (composite[p] / composite[p].max()) * (composite[c] / composite[c].max())
        for rank, (cid, val) in enumerate(score.sort_values(ascending=False).items(), 1): rank_rows.append({"ranking_metric": "composite_angle_power_tradeoff", "model": model, "candidate_id": cid, "score": float(val), "rank": rank, "diagnostic_only": True})
    ranking = pd.DataFrame(rank_rows)
    filter_audit = scalar[["pair_id", "candidate_id", "source_position_nm", "orientation", "fdtd_filter0_cone10", "fdtd_filter02_cone10"]].copy()
    filter_audit["cone10_delta_filter02_minus_filter0"] = filter_audit.fdtd_filter02_cone10 - filter_audit.fdtd_filter0_cone10
    # Required residuals derived from scalar paired metrics.
    avg_pol = pol.groupby("candidate_id").xz_relative_difference.mean().rename("xz_relative_difference")
    avg_pos = pos.pivot(index="candidate_id", columns="model", values="three_position_relative_span")
    residual["delta_polarization_difference"] = residual.candidate_id.map(avg_pol) - residual.candidate_id.map(avg_pol)  # populated separately below
    residual["delta_polarization_difference"] = residual.candidate_id.map(pol[pol.model.eq("Dipole-TMM")].groupby("candidate_id").xz_relative_difference.mean()) - residual.candidate_id.map(pol[pol.model.eq("FDTD")].groupby("candidate_id").xz_relative_difference.mean())
    residual["delta_source_position_span"] = residual.candidate_id.map(avg_pos["Dipole-TMM"]) - residual.candidate_id.map(avg_pos["FDTD"])
    # Strict finite audit after all calculations.
    frames = {"paired_case_index.parquet": pd.DataFrame(pairs), "paired_scalar_metrics.parquet": scalar, "paired_spectral_curves.parquet": pd.DataFrame(spectra), "paired_angular_curves.parquet": pd.DataFrame(angulars), "scalar_residuals.parquet": residual, "curve_residuals.parquet": pd.DataFrame(curves), "power_reference_ratios.parquet": power, "ranking_comparison.parquet": ranking, "source_position_comparison.parquet": pos, "polarization_comparison.parquet": pol, "filter_audit.parquet": filter_audit}
    for name, frame in frames.items():
        numeric = frame.select_dtypes(include=[np.number]).to_numpy()
        if not np.isfinite(numeric).all():
            raise ValueError(f"NaN/Inf prohibited in {name}")
        frame.to_parquet(output / name, index=False)
    sufficiency = {"independent_geometry_count": 3, "paired_rows": 18, "source_positions_per_geometry": 3, "orientations_per_position": 2, "geometry_effective_sample_size": 3, "residual_model_training_allowed": False, "high_capacity_ml_residual_surrogate_supported": False, "global_or_targetwise_low_parameter_calibration_only_evaluable": True, "leave_one_candidate_out_identifiable": False, "overfit_risk": "severe", "minimum_recommended_new_geometries": 12, "recommended_next_fdtd_budget_range": "72-96 unique cases (12-16 geometries x 3 positions x 2 orientations)"}
    contract = {"version": "v1", "physical_scope": "2D line-dipole relative channel; homogeneous_GaN_optical_approximation; GaN->MDC->Air", "residual_interpretation": "model_discrepancy + numerical/device-domain_difference", "absolute_power_claim": False, "purcell_claim": False, "formal_filter": "0.2", "audit_filter": "0", "power_formula": "log(FDTD_candidate/Bare)-log(DTMM_candidate/Bare)", "formal_residual_model_trained": False, "safety_counters": CONFIG["safety_counters"]}
    dump(output / "sample_sufficiency_audit.json", sufficiency)
    dump(output / "residual_contract.json", contract)
    prov = {"frozen_fdtd_root": str(FDTD_ROOT), "fdtd_manifest_sha256": fdtd_manifest_sha, "fdtd_provenance_sha256": sha(FDTD_ROOT / "provenance.json"), "dipole_tmm_code_sha256": tmm_code_sha, "source_manifest": manifest, "source_provenance": provenance, "solver_calls_this_task": 0}
    dump(output / "provenance.json", prov)
    manifest_out = {"run_id": output.name, "files": {p.name: sha(p) for p in output.iterdir() if p.is_file()}, "pair_count": 18, "all_finite": True, "deterministic_inputs": True, "solver_calls": 0}
    dump(output / "manifest.json", manifest_out)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--output-root", required=True)
    args = parser.parse_args(); run(Path(args.output_root))
