from __future__ import annotations
import argparse, csv, hashlib, json, subprocess
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "datasets" / "mdc_ml_database_v1"
PREP = ROOT / "datasets" / "mdc_ml_database_v1_prepared"
REPORT = ROOT / "reports" / "mdc_ml_database_label_views_v1.md"
VERSION = "1.0.0"
HEAD_EXPECTED = "16ff883"

def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))

def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(dict.fromkeys(k for row in rows for k in row)) if rows else []
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader(); w.writerows(rows)

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()

def finite(value: object) -> bool:
    try:
        x = float(value)
        return x == x and abs(x) != float("inf")
    except (TypeError, ValueError):
        return False

def fnum(value: object) -> float | None:
    return float(value) if finite(value) else None

def fmt(value: object) -> str:
    return "" if value is None else str(value)

def git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()

def source_paths() -> list[str]:
    return [
        "database_manifest.json", "schema.json", "README.md", "geometry_master.csv",
        "tmm_nominal_metrics.csv", "tolerance_samples.csv", "fdtd_validation.csv",
        "split_assignments.csv", "label_dictionary.csv", "quality_audit.json", "split_audit.json",
    ]

def check_sources() -> dict:
    manifest = json.loads((DB / "database_manifest.json").read_text(encoding="utf-8"))
    if manifest.get("database_version") != "1.0.0" or manifest.get("schema_version") != "1.0.0":
        raise RuntimeError("unexpected database/schema version")
    head = git_head()
    if not head.startswith(HEAD_EXPECTED):
        raise RuntimeError(f"expected HEAD {HEAD_EXPECTED}, got {head}")
    hashes = {}
    for rel in source_paths():
        p = DB / rel
        if not p.exists() or p.stat().st_size == 0:
            raise RuntimeError(f"missing/empty source: {rel}")
        hashes[rel] = {"path": f"datasets/mdc_ml_database_v1/{rel}", "sha256": sha256(p), "bytes": p.stat().st_size}
    return {"manifest": manifest, "head": head, "hashes": hashes}

def geometry_fields(g: dict[str, str]) -> dict[str, str]:
    names = ["geometry_id", "geometry_hash", "candidate_id_primary", "candidate_aliases", "topology_family",
             "N", "M", "H_nm", "L_nm", "C_nm", "effective_central_L_thickness_nm",
             "physical_layer_count", "total_thickness_nm", "compiled_sequence", "material_model",
             "propagation_direction"]
    return {x: g.get(x, "") for x in names}

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--audit-only", action="store_true")
    args = ap.parse_args()
    src = check_sources()
    geo = read_csv(DB / "geometry_master.csv")
    tmm = read_csv(DB / "tmm_nominal_metrics.csv")
    tol = read_csv(DB / "tolerance_samples.csv")
    fdtd = read_csv(DB / "fdtd_validation.csv")
    splits = read_csv(DB / "split_assignments.csv")
    labels = read_csv(DB / "label_dictionary.csv")
    geo_by_hash = {r["geometry_hash"]: r for r in geo}
    tmm_by_hash = {r["geometry_hash"]: r for r in tmm}
    if len(geo_by_hash) != len(geo): raise RuntimeError("geometry_hash is not unique in geometry_master")
    if len(tmm_by_hash) != len(tmm): raise RuntimeError("geometry_hash is not unique in tmm_nominal_metrics")
    if len({r["record_id"] for r in tmm}) != len(tmm): raise RuntimeError("TMM record_id is not unique")
    if len({r["sample_id"] for r in tol}) != len(tol): raise RuntimeError("tolerance sample_id is not unique")
    if len({r["record_id"] for r in fdtd}) != len(fdtd): raise RuntimeError("FDTD record_id is not unique")
    split_by_id = {r["record_id"]: r for r in splits}
    if any(r["record_id"] not in split_by_id for r in tmm): raise RuntimeError("canonical TMM missing split")
    if any(r.get("simulation_method") != "TMM" or r.get("usable_for_training", "").lower() != "true" or r.get("source_id") not in {"tmm_coarse", "tmm_refined"} for r in tmm):
        raise RuntimeError("canonical TMM role predicate failed")
    if any(r.get("usable_for_training", "").lower() == "true" for r in tol): raise RuntimeError("tolerance training leakage")
    if any(r.get("source_id", "").startswith("fdtd_") for r in tmm): raise RuntimeError("FDTD row in canonical TMM")
    if any(r.get("source_id", "").startswith("tmm_") for r in fdtd): raise RuntimeError("TMM row in FDTD reference")
    # A: one canonical row per nominal TMM fact, with geometry join only for traceable features.
    spectral = []
    for r in tmm:
        g = geo_by_hash.get(r["geometry_hash"])
        if g is None: raise RuntimeError("TMM geometry hash join missing")
        row = {"sample_role": "canonical_tmm_sweep", "future_training_role": "supervised_forward_target",
               **geometry_fields(g), "record_id": r["record_id"], "source_id": r["source_id"],
               "fidelity_level": r["fidelity_level"], "simulation_method": r["simulation_method"],
               "usable_for_training": r["usable_for_training"], "quality_status": r["quality_status"],
               "spectral_peak_nm": r["spectral_peak_nm"], "spectral_peak_T": r["spectral_peak_T"],
               "spectral_FWHM_nm": r["spectral_FWHM_nm"], "T448": r["T448"], "T450": r["T450"], "T453": r["T453"],
               "normal_to_40_60_ratio": r["normal_to_40_60_ratio"], "FAB_pass": r["FAB_pass"],
               "PERF_pass": r["PERF_pass"], "combined_pass": r["combined_pass"],
               "spectral_label_status": "valid" if all(finite(r[x]) for x in ["spectral_peak_nm", "spectral_FWHM_nm", "T448", "T450", "T453"]) else "partial"}
        spectral.append(row)
    # B: preserve all canonical rows, never fill sparse angular labels.
    angular = []
    for r in tmm:
        g = geo_by_hash[r["geometry_hash"]]
        fwhm = finite(r["tmm_angular_FWHM_450_deg"]); angle = finite(r["tmm_max_transmission_angle_450_deg"])
        status = "valid" if fwhm and angle else ("partial" if fwhm or angle else "missing")
        reason = "" if status != "missing" else "not_computed"
        angular.append({"sample_role": "canonical_tmm_sweep", "future_training_role": "sparse_angular_analysis",
                        **geometry_fields(g), "record_id": r["record_id"], "source_id": r["source_id"],
                        "fidelity_level": r["fidelity_level"], "simulation_method": r["simulation_method"],
                        "tmm_angular_FWHM_450_deg": r["tmm_angular_FWHM_450_deg"],
                        "tmm_max_transmission_angle_450_deg": r["tmm_max_transmission_angle_450_deg"],
                        "strict_normal_450": r["strict_normal_450"], "near_normal_450": r["near_normal_450"],
                        "normal_to_40_60_ratio": r["normal_to_40_60_ratio"],
                        "angular_FWHM_valid": r["angular_FWHM_valid"], "quality_status": r["quality_status"],
                        "has_angular_fwhm_label": str(fwhm).lower(), "has_max_angle_label": str(angle).lower(),
                        "angular_label_status": status, "angular_missing_reason": reason})
    # C: parent joins are hash-based and cardinality-checked; paired deltas are computed only when finite.
    tol_view = []
    for r in tol:
        parent = geo_by_hash.get(r["parent_nominal_geometry_hash"])
        nominal = tmm_by_hash.get(r["parent_nominal_geometry_hash"])
        if parent is None: raise RuntimeError("tolerance parent geometry hash join missing")
        row = {"sample_role": "tolerance_perturbation", "future_training_role": "robustness_or_paired_learning",
               **geometry_fields(parent), "sample_id": r["sample_id"], "sample_hash": r["sample_hash"],
               "perturbed_geometry_id": r["geometry_id"], "perturbed_geometry_hash": r["geometry_hash"],
               "parent_nominal_geometry_id": r["parent_nominal_geometry_id"], "parent_nominal_geometry_hash": r["parent_nominal_geometry_hash"],
               "source_id": r["source_id"], "scan_mode": r["scan_mode"], "error_bound_nm": r["error_bound_nm"],
               "random_seed": r["random_seed"], "sample_index": r["sample_index"], "delta_H_nm": r["delta_H_nm"],
               "delta_L_nm": r["delta_L_nm"], "delta_defect_nm": r["delta_defect_nm"],
               "layer_error_vector_json": r["layer_error_vector_json"], "perturbed_compiled_sequence": r["perturbed_compiled_sequence"],
               "parent_join_status": "unique_matched" if nominal is not None else "geometry_matched_canonical_missing", "usable_for_training": r["usable_for_training"],
               "usable_for_validation": r["usable_for_validation"], "quality_status": r["quality_status"]}
        for x in ["spectral_peak_nm", "spectral_FWHM_nm", "T450", "normal_to_40_60_ratio"]:
            pv, qv = (fnum(nominal.get(x, "")), fnum(r.get(x, ""))) if nominal is not None else (None, None)
            row[f"perturbed_{x}"] = r.get(x, "")
            row[f"nominal_{x}"] = nominal.get(x, "") if nominal is not None else ""
            row[f"delta_{x}"] = "" if pv is None or qv is None else qv - pv
            row[f"delta_{x}_missing_reason"] = "" if pv is not None and qv is not None else ("parent_not_in_canonical_tmm" if nominal is None else "label_missing")
        tol_view.append(row)
    # D: FDTD remains external reference; single-wavelength cases retain unavailable spectral labels.
    fdtd_view = []
    for r in fdtd:
        g = geo_by_hash.get(r["geometry_hash"])
        if g is None: raise RuntimeError("FDTD geometry hash join missing")
        spectral_status = "not_available"; spectral_reason = "single_wavelength_simulation"
        angular_status = "valid" if finite(r["farfield_angular_FWHM_deg"]) else "missing"
        fdtd_view.append({"sample_role": "fdtd_external_high_fidelity_reference", "future_training_role": "external_validation_or_multifidelity_reference",
                          **geometry_fields(g), **r, "spectral_FWHM_label_status": spectral_status,
                          "spectral_FWHM_missing_reason": spectral_reason, "angular_label_status": angular_status})
    PREP.mkdir(parents=True, exist_ok=True)
    outputs = {
        "tmm_canonical_spectral_labels.csv": spectral,
        "tmm_angular_sparse_labels.csv": angular,
        "tolerance_robustness_labels.csv": tol_view,
        "fdtd_external_reference_labels.csv": fdtd_view,
    }
    for name, data in outputs.items(): write_csv(PREP / name, data)
    dictionary = []
    definitions = [
        ("spectral_peak_nm", "spectral peak wavelength", "nm", "tmm_nominal_metrics.csv", "source field preserved", "resolved_source_field"),
        ("spectral_FWHM_nm", "normal-incidence pure-film spectral FWHM", "nm", "tmm_nominal_metrics.csv", "source field preserved; no boundary-clipped values imputed", "resolved_source_field"),
        ("T448", "TMM transmission at 448 nm", "fraction", "tmm_nominal_metrics.csv", "source field preserved", "resolved_source_field"),
        ("T450", "TMM transmission at 450 nm", "fraction", "tmm_nominal_metrics.csv", "source field preserved", "resolved_source_field"),
        ("T453", "TMM transmission at 453 nm", "fraction", "tmm_nominal_metrics.csv", "source field preserved", "resolved_source_field"),
        ("normal_to_40_60_ratio", "source TMM normal-to-large-angle ratio", "ratio", "tmm_nominal_metrics.csv", "threshold/formula not redefined in this view", "source_field_preserved"),
        ("FAB_pass", "source FAB gate label", "bool", "tmm_nominal_metrics.csv", "threshold not redefined in this view", "source_field_preserved"),
        ("PERF_pass", "source PERF gate label", "bool", "tmm_nominal_metrics.csv", "threshold not redefined in this view", "source_field_preserved"),
        ("combined_pass", "source combined gate label", "bool", "tmm_nominal_metrics.csv", "source field preserved", "resolved_source_field"),
        ("tmm_angular_FWHM_450_deg", "TMM plane-wave angular half-power width at 450 nm", "deg", "tmm_nominal_metrics.csv", "blank means not computed; 15 valid", "resolved_source_field_sparse"),
        ("tmm_max_transmission_angle_450_deg", "TMM plane-wave maximum transmission angle", "deg", "tmm_nominal_metrics.csv", "blank means not computed; 2 valid; not dipole far field", "resolved_source_field_sparse"),
        ("strict_normal_450", "stored strict-normal TMM flag", "bool", "tmm_nominal_metrics.csv", "not derived here from sparse max-angle rows", "preserved_not_derived"),
        ("near_normal_450", "stored near-normal TMM flag", "bool", "tmm_nominal_metrics.csv", "not derived here from sparse max-angle rows", "preserved_not_derived"),
        ("farfield_peak_angle_deg", "FDTD dipole far-field peak angle", "deg", "fdtd_validation.csv", "blank means unavailable", "resolved_external_reference"),
        ("farfield_angular_FWHM_deg", "FDTD dipole far-field angular FWHM", "deg", "fdtd_validation.csv", "blank means unavailable", "resolved_external_reference"),
        ("eta10", "FDTD angular fraction within 10 degrees", "fraction", "fdtd_validation.csv", "blank means unavailable", "resolved_external_reference"),
        ("eta20", "FDTD angular fraction within 20 degrees", "fraction", "fdtd_validation.csv", "blank means unavailable", "resolved_external_reference"),
        ("leakage20_40", "FDTD angular leakage fraction 20-40 degrees", "fraction", "fdtd_validation.csv", "blank means unavailable", "resolved_external_reference"),
        ("leakage40_60", "FDTD angular leakage fraction 40-60 degrees", "fraction", "fdtd_validation.csv", "blank means unavailable", "resolved_external_reference"),
        ("residual60_plus", "FDTD residual fraction beyond 60 degrees", "fraction", "fdtd_validation.csv", "blank means unavailable", "resolved_external_reference"),
        ("raw_upward_monitor_power", "FDTD raw upward monitor power", "arb.", "fdtd_validation.csv", "not extraction efficiency; blank means unavailable", "resolved_external_reference"),
        ("spectral_FWHM_label_status", "FDTD spectral FWHM availability status", "category", "fdtd_validation.csv", "single-wavelength cases are not available", "resolved_status"),
    ]
    for name, meaning, unit, table, missing, status in definitions:
        dictionary.append({"canonical_label_name": name, "original_field_name": name, "physical_meaning": meaning, "unit": unit,
                           "source_table": table, "source_script_or_report": "scripts/build_mdc_ml_database_v1.py; datasets/mdc_ml_database_v1/schema.json; reports/mdc_defect_450/mdc_ml_database_v1.md", "extraction_or_derivation": "copy of existing source field; no simulation or imputation", "valid_when": "source field is nonblank and quality policy permits", "missing_value_meaning": missing, "fidelity_level": "TMM" if "tmm" in table else "FDTD", "sample_role": "canonical_tmm_sweep" if "tmm" in table else "fdtd_external_high_fidelity_reference", "future_training_role": "label view only; role-specific", "definition_status": status, "notes": "TMM plane-wave labels must not be called dipole far-field labels."})
    write_csv(PREP / "label_dictionary_extended.csv", dictionary)
    topology = dict(Counter(r["topology_family"] for r in spectral))
    output_info = {}
    for name in [*outputs.keys(), "label_dictionary_extended.csv"]:
        p = PREP / name; output_info[f"datasets/mdc_ml_database_v1_prepared/{name}"] = {"sha256": sha256(p), "bytes": p.stat().st_size}
    manifest = {"prepared_schema_version": VERSION, "source_database_version": src["manifest"]["database_version"], "source_schema_version": src["manifest"]["schema_version"], "source_git_head": src["head"], "input_files": src["hashes"], "output_files": output_info, "sample_roles": {"canonical_tmm_sweep": "tmm_nominal_metrics fact table; no tolerance perturbation", "tolerance_perturbation": "tolerance_samples validation/robustness", "fdtd_external_high_fidelity_reference": "fdtd_validation external reference"}, "view_counts": {"tmm_canonical_spectral_labels": len(spectral), "tmm_angular_sparse_labels": len(angular), "tolerance_robustness_labels": len(tol_view), "fdtd_external_reference_labels": len(fdtd_view), "label_dictionary_extended": len(dictionary)}, "topology_distribution": topology, "coarse_refined_distribution": dict(Counter(r["source_id"] for r in spectral)), "label_coverage": {"spectral_peak": sum(finite(r["spectral_peak_nm"]) for r in tmm), "spectral_FWHM": sum(finite(r["spectral_FWHM_nm"]) for r in tmm), "angular_FWHM": sum(finite(r["tmm_angular_FWHM_450_deg"]) for r in tmm), "maximum_angle": sum(finite(r["tmm_max_transmission_angle_450_deg"]) for r in tmm), "tolerance": len(tol_view), "fdtd": len(fdtd_view)}, "tolerance_parent_join_counts": dict(Counter(r["parent_join_status"] for r in tol_view)), "known_limitations": ["angular FWHM is valid for 15 TMM rows; maximum angle is valid for 2", "strict/near-normal are not extrapolated from two max-angle rows", "FDTD single-wavelength rows have no spectral FWHM label", "FAB/PERF/ratio thresholds are preserved, not redefined", "6 tolerance parent hashes exist in geometry_master but not in canonical TMM; their paired deltas remain blank with explicit missing reason"], "generator": "scripts/build_mdc_ml_label_views_v1.py"}
    (PREP / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    report_lines = ["# MDC ML database label views v1", "", f"Source HEAD: `{src['head']}`; database/schema `{src['manifest']['database_version']}/{src['manifest']['schema_version']}`.", "", "## Source files", "", *[f"- {x}: {v['bytes']} bytes; SHA256 `{v['sha256']}`" for x, v in src["hashes"].items()], "", "## Sample roles", "", "- `canonical_tmm_sweep`: 2,688 TMM facts (coarse 2,673 + refined 15).", "- `tolerance_perturbation`: 8,400 robustness rows; not training rows.", "- `fdtd_external_high_fidelity_reference`: 11 external rows; never mixed into canonical TMM.", "- `geometry_master.is_nominal_geometry`: legacy reference-candidate marker only; never used as a canonical filter.", "", "## Views", "", f"- spectral view: {len(spectral)} rows; topology {topology}; geometry_hash unique.", f"- angular sparse view: {len(angular)} rows; angular FWHM valid {sum(finite(r['tmm_angular_FWHM_450_deg']) for r in tmm)}; maximum angle valid {sum(finite(r['tmm_max_transmission_angle_450_deg']) for r in tmm)}; missing values remain blank with `not_computed`.", f"- tolerance view: {len(tol_view)} rows; parent join status {dict(Counter(r['parent_join_status'] for r in tol_view))}; non-canonical parents retain blank deltas with explicit missing reason.", f"- FDTD reference view: {len(fdtd_view)} rows; single-wavelength spectral FWHM status `not_available`.", "", "## Semantics and limitations", "", "- No missing label was filled with zero and no strict/near-normal threshold was invented.", "- TMM angular transmission metrics are plane-wave metrics, not dipole far-field metrics.", "- FAB/PERF/ratio labels are preserved source fields; this task does not redefine their thresholds.", "- No model, checkpoint, prediction, loss curve, or new simulation data was created.", "", "## Validation", "", "- Cardinality checks pass for geometry and parent hash joins; tolerance parent hashes not present in canonical TMM are explicitly marked.", "- Canonical TMM excludes tolerance and FDTD rows by source role.", "- Outputs are deterministic byte-stable for identical frozen inputs."]
    REPORT.parent.mkdir(parents=True, exist_ok=True); REPORT.write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    for p in [REPORT, ROOT / "scripts" / "build_mdc_ml_label_views_v1.py", ROOT / "tests" / "test_mdc_ml_label_views_v1.py"]:
        if p.exists():
            output_info[str(p.relative_to(ROOT)).replace("\\", "/")] = {"sha256": sha256(p), "bytes": p.stat().st_size}
    manifest["output_files"] = output_info
    (PREP / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    if args.audit_only:
        print(json.dumps({"audit": "PASS", "views": manifest["view_counts"], "output_files": len(output_info)}, indent=2))
    else:
        print(json.dumps({"status": "PASS", "views": manifest["view_counts"], "output_files": len(output_info)}, indent=2))

if __name__ == "__main__":
    main()
