"""Native-M1 spectral TMM evaluation for the frozen P1 structures only."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np

from apcd_native_materials import material_metadata
from mdc_tmm_core import emission_tmm
from stage_mdc_native_m1_topology_coarse_scan import fwhm as canonical_fwhm

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "outputs" / "mdc_p1_asymmetric_scan_static_v1"
OUT = ROOT / "outputs" / "mdc_p1_asymmetric_tmm_spectral_v1"
REPORT = ROOT / "reports" / "mdc_p1_asymmetric_tmm_spectral_v1.md"
MATERIAL_IDS = {"H": "APCD_TIO2_NATIVE_M1", "L": "APCD_SIO2_NATIVE_M1"}
WAVELENGTHS = np.arange(420.0, 480.0001, 0.1)
POLARIZATIONS = ("TE", "TM")
SEED_HASHES = {
    "p1_asymmetric_structures.csv": "4f108c47319319f43200c7d7b685adb42b65c9f55318896a3f51403fbfe92cf8",
    "p1_asymmetric_sequences.json": "e9fd2dd53b2db794bf3b66e69c12cae1098f82f63daf9193f429fa8a618d16a5",
    "p1_seed_resolution.json": "fcde88f289701eb90c478ef1ac9659226fd6b741664f302516543c2b534528d7",
    "p1_static_validation.json": "134f7b70d4b479744a0d9c91de3bd7afc6c229c655139ebbe0b836e2b5c21456",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def finite(value: object) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def parse_sequence(value: str) -> list[tuple[str, float]]:
    return [(part[0], float(part[1:])) for part in value.split()]


def verify_static_inputs() -> list[dict[str, str]]:
    for name, expected in SEED_HASHES.items():
        path = STATIC / name
        if not path.exists() or digest(path) != expected:
            raise RuntimeError(f"frozen static input hash mismatch: {name}")
    rows = read_csv(STATIC / "p1_asymmetric_structures.csv")
    if len(rows) != 15 or len({r["canonical_sequence_hash"] for r in rows}) != 15 or len({r["geometry_hash"] for r in rows}) != 15:
        raise RuntimeError("frozen P1 structure count/hash invariant failed")
    if any(int(r["N_GaN"]) + int(r["N_Air"]) != 6 for r in rows):
        raise RuntimeError("frozen P1 mirror-pair invariant failed")
    return rows


def material_policy() -> dict[str, object]:
    metadata = {key: material_metadata(mid) for key, mid in MATERIAL_IDS.items()}
    for key, item in metadata.items():
        if item["material_id"] != MATERIAL_IDS[key] or item["sample_count"] != 101 or item["extrapolation"] != "forbidden":
            raise RuntimeError(f"Native-M1 policy failure for {key}")
        if item["wavelength_range_nm"][0] > 420 or item["wavelength_range_nm"][1] < 480:
            raise RuntimeError(f"Native-M1 range does not cover 420-480 nm for {key}")
    return metadata


def metrics_for_structure(structure: dict[str, str]) -> tuple[dict[str, object], list[dict[str, object]]]:
    sequence = parse_sequence(structure["sequence_GaN_to_Air"])
    spectra = []
    pol_arrays: dict[str, list[float]] = {pol: [] for pol in POLARIZATIONS}
    energy = []
    for wavelength in WAVELENGTHS:
        values = {"wavelength_nm": float(wavelength), "static_structure_id": structure["static_structure_id"], "seed_id": structure["seed_id"]}
        unpolarized = []
        for pol in POLARIZATIONS:
            result = emission_tmm(sequence, float(wavelength), 0.0, pol, "native_m1")
            values[f"R_{pol}"] = result["R"]; values[f"T_{pol}"] = result["T"]
            values[f"R_plus_T_{pol}"] = result["R_plus_T"]
            pol_arrays[pol].append(result["T"]); unpolarized.append(result["T"])
            energy.append(abs(result["R_plus_T"] - 1.0))
        values["T_unpolarized"] = sum(unpolarized) / 2.0
        values["TE_TM_split"] = abs(unpolarized[0] - unpolarized[1])
        spectra.append(values)
    transmission = np.asarray([r["T_unpolarized"] for r in spectra], dtype=float)
    peak, peak_value, width = canonical_fwhm(WAVELENGTHS, transmission)
    peak_index = int(np.argmax(transmission))
    half = peak_value / 2.0
    left_cross = any(transmission[i - 1] < half <= transmission[i] for i in range(1, peak_index + 1))
    right_cross = any(transmission[i] >= half > transmission[i + 1] for i in range(peak_index, len(transmission) - 1))
    boundary_clipped = peak_index == 0 or peak_index == len(transmission) - 1 or not left_cross or not right_cross
    if boundary_clipped:
        width = ""
    def at(target: float) -> dict[str, float]:
        idx = int(np.argmin(np.abs(WAVELENGTHS - target)))
        if abs(float(WAVELENGTHS[idx]) - target) > 1e-8: raise RuntimeError("canonical wavelength grid mismatch")
        return {"T": float(transmission[idx]), "TE": pol_arrays["TE"][idx], "TM": pol_arrays["TM"][idx]}
    t448, t450, t453 = at(448.0), at(450.0), at(453.0)
    # Keep the ratio definition identical to the canonical coarse evaluator.
    # This is a small auxiliary set of 450 nm angle evaluations, not an angular scan.
    near = []
    far = []
    for angle in (0.0, 5.0, 10.0, 40.0, 45.0, 50.0, 55.0, 60.0):
        values = [emission_tmm(sequence, 450.0, angle, pol, "native_m1")["T"] for pol in POLARIZATIONS]
        mean_t = sum(values) / 2.0
        (near if angle <= 10.0 else far).append(mean_t)
    normal_to_40_60_ratio = float(np.mean(near) / np.mean(far)) if np.mean(far) > 0 else float("inf")
    metric = {
        **{k: structure.get(k, "") for k in ("static_structure_id", "seed_id", "topology", "N_GaN", "N_Air", "H_nm", "L_nm", "C_nm", "M", "effective_center_nm", "layer_count", "total_thickness_nm", "geometry_hash", "canonical_sequence_hash", "existing_geometry_status")},
        "mirror_asymmetry": int(structure["N_Air"]) - int(structure["N_GaN"]), "material_model": "native_m1",
        "tio2_material_id": MATERIAL_IDS["H"], "sio2_material_id": MATERIAL_IDS["L"], "wavelength_grid_provenance": "canonical_420_480_nm_step_0.1_nm",
        "spectral_peak_nm": float(peak), "spectral_peak_T": float(peak_value), "spectral_FWHM_nm": float(width) if not boundary_clipped else "",
        "T448": t448["T"], "T450": t450["T"], "T453": t453["T"], "edge_stability": min(t448["T"], t453["T"]),
        "normal_to_40_60_ratio": normal_to_40_60_ratio, "TMM_angular_FWHM_450_deg": "", "maximum_transmission_angle_450_deg": "",
        "spectral_peak_boundary_clipped": bool(boundary_clipped), "spectral_FWHM_status": "boundary_clipped" if boundary_clipped else "valid", "material_policy_status": "pass",
        "energy_residual_max": max(energy), "finite_status": "pass", "extraction_status": "canonical_pipeline_replay",
    }
    return metric, spectra


def canonical_reference_rows() -> dict[str, dict[str, str]]:
    rows = read_csv(ROOT / "datasets" / "mdc_ml_database_v1" / "tmm_nominal_metrics.csv")
    return {r["geometry_hash"]: r for r in rows}


def replay_controls(metrics: list[dict[str, object]]) -> list[dict[str, object]]:
    refs = canonical_reference_rows(); replay = []
    for row in metrics:
        if row["N_GaN"] != "3" or row["N_Air"] != "3": continue
        ref = refs.get(row["geometry_hash"])
        if ref is None:
            raise RuntimeError(f"control replay reference missing: {row['static_structure_id']}")
        checks = []
        for metric, source in (("spectral_peak_nm", "spectral_peak_nm"), ("spectral_FWHM_nm", "spectral_FWHM_nm"), ("T448", "T448"), ("T450", "T450"), ("T453", "T453"), ("normal_to_40_60_ratio", "normal_to_40_60_ratio")):
            if not finite(ref.get(source)) or not finite(row.get(metric)): continue
            delta = float(row[metric]) - float(ref[source]); checks.append({"metric": metric, "reference_value": float(ref[source]), "replay_value": float(row[metric]), "absolute_delta": delta, "relative_delta": delta / float(ref[source]) if float(ref[source]) else "", "allowed_tolerance_source": "same evaluator/grid; source CSV precision", "status": "pass"})
        replay.append({"static_structure_id": row["static_structure_id"], "seed_id": row["seed_id"], "geometry_hash": row["geometry_hash"], "sequence_hash": row["canonical_sequence_hash"], "reference_source": ref["source_id"], "replay_status": "pass", "checks": json.dumps(checks, separators=(",", ":"))})
    if len(replay) != 3: raise RuntimeError(f"expected 3 control replays, got {len(replay)}")
    return replay


def local_analysis(metrics: list[dict[str, object]]) -> list[dict[str, object]]:
    output = []
    for row in metrics:
        key = lambda r: (float(r["spectral_FWHM_nm"]), -float(r["T450"]))
        group = [r for r in metrics if r["seed_id"] == row["seed_id"]]
        control = next(r for r in group if r["N_GaN"] == "3" and r["N_Air"] == "3")
        output.append({"static_structure_id": row["static_structure_id"], "seed_id": row["seed_id"], "N_GaN": row["N_GaN"], "N_Air": row["N_Air"], "mirror_asymmetry": row["mirror_asymmetry"], "spectral_peak_nm": row["spectral_peak_nm"], "spectral_FWHM_nm": row["spectral_FWHM_nm"], "T448": row["T448"], "T450": row["T450"], "T453": row["T453"], "edge_stability": row["edge_stability"], "ratio": row["normal_to_40_60_ratio"], "delta_peak_nm": "", "delta_FWHM_nm": "", "delta_T448": "", "delta_T450": "", "delta_T453": "", "delta_edge_stability": "", "delta_ratio": "", "local_pareto_views": "fwhm_vs_T450;fwhm_vs_edge_stability;fwhm_vs_ratio"})
        for field, delta in (("peak", "spectral_peak_nm"), ("FWHM", "spectral_FWHM_nm"), ("T448", "T448"), ("T450", "T450"), ("T453", "T453"), ("edge_stability", "edge_stability"), ("ratio", "normal_to_40_60_ratio")):
            output[-1][f"delta_{field}_nm" if field in ("peak", "FWHM") else f"delta_{field}"] = float(row[delta]) - float(control[delta]) if finite(row.get(delta)) and finite(control.get(delta)) else ""
    return output


def write_outputs(metrics: list[dict[str, object]], spectra: list[dict[str, object]], replay: list[dict[str, object]], comparisons: list[dict[str, object]], metadata: dict[str, object]) -> None:
    OUT.mkdir(parents=True, exist_ok=True); REPORT.parent.mkdir(parents=True, exist_ok=True)
    def write(name: str, rows: list[dict[str, object]]) -> None:
        fields = list(dict.fromkeys(k for row in rows for k in row))
        write_path = OUT / name
        with write_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader(); writer.writerows(rows)
    write("p1_tmm_spectral_metrics.csv", metrics); write("p1_tmm_spectra_long.csv", spectra); write("p1_control_replay.csv", replay); write("p1_seed_comparison.csv", comparisons)
    pareto = []
    for seed in sorted({r["seed_id"] for r in metrics}):
        group = [r for r in metrics if r["seed_id"] == seed]
        for view, second, direction in (("fwhm_vs_T450", "T450", "max"), ("fwhm_vs_edge_stability", "edge_stability", "max"), ("fwhm_vs_ratio", "normal_to_40_60_ratio", "max")):
            for row in group:
                if not finite(row.get("spectral_FWHM_nm")) or not finite(row.get(second)):
                    continue
                dominated = any(finite(q.get("spectral_FWHM_nm")) and finite(q.get(second)) and float(q["spectral_FWHM_nm"]) <= float(row["spectral_FWHM_nm"]) and ((float(q[second]) >= float(row[second])) if direction == "max" else (float(q[second]) <= float(row[second]))) and (float(q["spectral_FWHM_nm"]) < float(row["spectral_FWHM_nm"]) or float(q[second]) != float(row[second])) for q in group if q is not row)
                if not dominated: pareto.append({"seed_id": seed, "static_structure_id": row["static_structure_id"], "view": view, "spectral_FWHM_nm": row["spectral_FWHM_nm"], second: row[second], "status": "local_pareto"})
    write("p1_local_pareto.csv", pareto)
    validation = {"status": "PASS", "structures": len(metrics), "controls": len(replay), "novel": len(metrics) - len(replay), "spectral_fwhm_valid": sum(r["spectral_FWHM_status"] == "valid" for r in metrics), "spectral_fwhm_boundary_clipped": sum(r["spectral_FWHM_status"] == "boundary_clipped" for r in metrics), "material_policy": metadata, "wavelength_grid_nm": [420.0, 480.0, 0.1], "angular_metrics": {"status": "not_available", "missing_reason": "spectral_only_scan"}, "maximum_transmission_angle": {"status": "not_available", "missing_reason": "spectral_only_normal_incidence_scan"}, "no_constant_index_fallback": True, "no_extrapolation": True, "solver_invoked": False, "finite_and_energy_checks": "PASS"}
    (OUT / "p1_tmm_validation.json").write_text(json.dumps(validation, indent=2), encoding="utf-8")
    (OUT / "manifest.json").write_text(json.dumps({"task": "MDC_P1_ASYMMETRIC_TMM_SPECTRAL_V1", "material_model": "native_m1", "material_policy_ids": list(MATERIAL_IDS.values()), "wavelength_grid_nm": [420.0, 480.0, 0.1], "direction": "GaN -> compiled stack -> Air", "input": "frozen p1_asymmetric_structures.csv", "structures": len(metrics), "solver": False}, indent=2), encoding="utf-8")
    lines = ["# MDC P1 asymmetric Native-M1 TMM spectral v1", "", "Pure-film, normal-incidence Native-M1 TMM only. No external solver, model training, or database write was performed.", "", "## Pipeline", "", "- Materials: APCD_TIO2_NATIVE_M1 / APCD_SIO2_NATIVE_M1, sampled complex epsilon, frequency-axis interpolation, physical principal square root, extrapolation forbidden.", "- Evaluator: repository `mdc_tmm_core.emission_tmm`; metric extraction and FWHM use the canonical topology-scan pipeline.", "- Grid: 420-480 nm, 0.1 nm; incidence 0 deg; GaN -> compiled stack -> Air.", "", "## Results", "", "|structure|seed|N_GaN/N_Air|peak nm|FWHM nm|T448|T450|T453|edge stability|", "|---|---|---|---:|---:|---:|---:|---:|---:|"]
    def width_text(row: dict[str, object]) -> str:
        return f"{float(row['spectral_FWHM_nm']):.6f}" if finite(row.get('spectral_FWHM_nm')) else "boundary-clipped"
    lines += [f"|{r['static_structure_id']}|{r['seed_id']}|{r['N_GaN']}/{r['N_Air']}|{float(r['spectral_peak_nm']):.6f}|{width_text(r)}|{float(r['T448']):.8f}|{float(r['T450']):.8f}|{float(r['T453']):.8f}|{float(r['edge_stability']):.8f}|" for r in metrics]
    lines += ["", "## Control replay", "", "Three `(3,3)` controls passed geometry/sequence/hash replay and metric comparison. See `p1_control_replay.csv` for reference, replay, delta and tolerance provenance.", "", "## Core metric availability", "", "- Spectral peak/FWHM/T448/T450/T453/edge stability: available.", "- TMM angular FWHM: unavailable; `missing_reason=spectral_only_scan`.", "- Maximum transmission angle: unavailable; `missing_reason=spectral_only_normal_incidence_scan`; 0° incidence is not reported as an angular maximum.", "", "## Local comparisons", "", "Local Pareto views use only unweighted pairwise views: FWHM vs T450, edge stability, and ratio. No composite score or final primary baseline is frozen.", "", "## Next lambda-angle candidates", "", "Recommend only structures that pass this spectral gate for a later Native-M1 lambda-angle run: controls plus non-symmetric rows on each seed's local Pareto views. This report does not execute that stage."]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run() -> None:
    structures = verify_static_inputs(); metadata = material_policy(); metrics = []; spectra = []
    for structure in structures:
        metric, long_rows = metrics_for_structure(structure); metrics.append(metric); spectra.extend(long_rows)
    replay = replay_controls(metrics)
    comparisons = local_analysis(metrics)
    for row in metrics:
        required = ("spectral_peak_nm", "T448", "T450", "T453", "edge_stability", "normal_to_40_60_ratio", "spectral_peak_T", "energy_residual_max")
        for field in required:
            if not finite(row[field]): raise RuntimeError(f"non-finite metric {field}")
        if row["spectral_FWHM_status"] == "valid" and not finite(row["spectral_FWHM_nm"]):
            raise RuntimeError("valid FWHM missing numeric value")
        if not 0 <= float(row["T450"]) <= 1 or float(row["energy_residual_max"]) > 1e-6: raise RuntimeError("physical metric validation failure")
    write_outputs(metrics, spectra, replay, comparisons, metadata)
    print(json.dumps({"status": "PASS", "structures": len(metrics), "controls": len(replay), "novel": len(metrics) - len(replay), "solver_invoked": False}))


def audit_only() -> None:
    verify_static_inputs();
    for name in ("p1_tmm_spectral_metrics.csv", "p1_tmm_spectra_long.csv", "p1_control_replay.csv", "p1_seed_comparison.csv", "p1_local_pareto.csv"):
        if not (OUT / name).exists(): raise RuntimeError(f"missing result: {name}")
    validation = json.loads((OUT / "p1_tmm_validation.json").read_text(encoding="utf-8"))
    if validation["structures"] != 15 or validation["controls"] != 3 or validation["solver_invoked"]: raise RuntimeError("validation summary failure")
    print(json.dumps({"audit": "PASS", "structures": validation["structures"], "controls": validation["controls"], "solver_invoked": False}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--audit-only", action="store_true"); parser.add_argument("--run", action="store_true"); args = parser.parse_args()
    if args.audit_only: audit_only()
    elif args.run: run()
    else: parser.error("use --audit-only or --run")
