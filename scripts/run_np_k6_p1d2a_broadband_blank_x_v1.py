from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_np_k6_unitcell_setup_v1 as base

CASE_ID = "NP_P1D2_BROADBAND_FIXED_REFERENCE_BLANK_X"
TARGET_NM = tuple(range(445, 456))
SOURCE_START_NM, SOURCE_STOP_NM = 440, 460
BACKEND = "eleven_single_wavelength_monitor_families_v1"
RUNTIME = ROOT / "runtime_fsp" / "np_k6_p1d2_broadband_v1"
OUTPUT = ROOT / "outputs" / "np_k6_p1d2a_broadband_blank_x_v1"
PRE_FSP = RUNTIME / f"{CASE_ID}_pre.fsp"
POST_FSP = RUNTIME / f"{CASE_ID}_post.fsp"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fingerprint(path: Path) -> dict[str, Any]:
    stat = path.stat()
    return {
        "path": str(path.relative_to(ROOT)),
        "sha256": sha256(path),
        "size": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
    }


def monitor_names(wavelength_nm: int) -> tuple[str, str, str]:
    suffix = f"L{wavelength_nm}"
    return (f"T_POWER_{suffix}", f"R_POWER_{suffix}", f"T_FIELDS_{suffix}")


def target_axis() -> list[int]:
    return list(TARGET_NM)


def validate_request(case_id: str, polarization: str = "x") -> None:
    if case_id != CASE_ID:
        raise ValueError(f"only {CASE_ID} is authorized")
    if polarization != "x":
        raise ValueError("only x polarization is authorized")


def build_spec(case_id: str = CASE_ID, polarization: str = "x") -> dict[str, Any]:
    validate_request(case_id, polarization)
    # The old builder remains the canonical geometry/material creator. Diameter is
    # accepted only by its legacy validation and is irrelevant to a blank setup.
    inherited = base.build_spec("blank", 450, "x", 500, 160)
    return {
        "case_id": CASE_ID,
        "geometry_type": "blank",
        "polarization": "x",
        "selected_height_nm_context": 500,
        "target_wavelength_grid_nm": target_axis(),
        "source_wavelength_start_nm": SOURCE_START_NM,
        "source_wavelength_stop_nm": SOURCE_STOP_NM,
        "spectral_sampling_backend": BACKEND,
        "monitor_count": len(TARGET_NM) * 3,
        "monitor_mapping": {
            str(w): {"T_power": monitor_names(w)[0], "R_power": monitor_names(w)[1], "T_fields": monitor_names(w)[2]}
            for w in TARGET_NM
        },
        "inherited_builder_spec": inherited,
    }


def physical_contract(spec: dict[str, Any], audit: dict[str, Any] | None = None) -> dict[str, Any]:
    layout = spec["inherited_builder_spec"]["layout_nm"]
    contract = {
        "case_id": CASE_ID,
        "geometry_type": "blank",
        "pillar_present": False,
        "pillar_object_count": 0,
        "polarization": "x",
        "normal_incidence": True,
        "selected_height_nm_context": 500,
        "pitch_x_nm": base.PITCH_NM,
        "pitch_y_nm": base.PITCH_NM,
        "fdtd_z_min_nm": layout["fdtd_z_min_nm"],
        "fdtd_z_max_nm": layout["fdtd_z_max_nm"],
        "source_z_nm": layout["source_z_nm"],
        "source_wavelength_start_nm": SOURCE_START_NM,
        "source_wavelength_stop_nm": SOURCE_STOP_NM,
        "reflection_monitor_z_nm": layout["reflection_monitor_z_nm"],
        "transmission_monitor_z_nm": layout["transmission_monitor_z_nm"],
        "pillar_base_reference_z_nm": 0,
        "native_materials": {"substrate": "APCD_SIO2_NATIVE_M1", "pillar": None},
        "boundary_conditions": {"x": "Periodic", "y": "Periodic", "z": "PML"},
        "spectral_sampling_backend": BACKEND,
        "target_wavelength_grid_nm": target_axis(),
        "monitor_mapping": spec["monitor_mapping"],
        "interpolation_used": False,
        "nearest_neighbor_used": False,
    }
    if audit is not None:
        contract["setup_readback"] = audit
    return contract


def contract_hash(contract: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(contract, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _set(fdtd: Any, key: str, value: Any) -> None:
    fdtd.set(key, value)


def _delete_named(fdtd: Any, name: str) -> None:
    if int(fdtd.getnamednumber(name)):
        fdtd.select(name)
        fdtd.delete()


def _configure_monitor(fdtd: Any, name: str, wavelength_nm: int, z_nm: int, field: bool) -> None:
    (fdtd.addprofile if field else fdtd.addpower)()
    _set(fdtd, "name", name)
    _set(fdtd, "monitor type", "2D Z-normal")
    _set(fdtd, "x span", base.PITCH_NM * base.NM)
    _set(fdtd, "y span", base.PITCH_NM * base.NM)
    _set(fdtd, "z", z_nm * base.NM)
    _set(fdtd, "override global monitor settings", True)
    _set(fdtd, "use source limits", False)
    _set(fdtd, "frequency points", 1)
    _set(fdtd, "use wavelength spacing", True)
    # In this Lumapi version, a monitor created with an initial zero span can
    # quantize its center onto the legacy frequency grid. A nonzero priming span
    # followed by the requested center produces a saved readback of exactly one
    # wavelength; the audited final span is zero.
    _set(fdtd, "wavelength span", 1e-12)
    _set(fdtd, "wavelength center", wavelength_nm * base.NM)


def create_pre_fsp(spec: dict[str, Any], output_fsp: Path = PRE_FSP) -> dict[str, Any]:
    output_fsp.parent.mkdir(parents=True, exist_ok=True)
    # Reuse the frozen P1-D1 builder for FDTD, material registration, stack,
    # source plane and all spatial/boundary conventions.
    base.create_setup(spec["inherited_builder_spec"], output_fsp)
    fdtd = base._import_lumapi().FDTD(hide=True)
    try:
        fdtd.load(str(output_fsp))
        _delete_named(fdtd, "R_fields")
        _delete_named(fdtd, "T_fields")
        fdtd.select("source")
        _set(fdtd, "wavelength start", SOURCE_START_NM * base.NM)
        _set(fdtd, "wavelength stop", SOURCE_STOP_NM * base.NM)
        _set(fdtd, "polarization angle", 0)
        for wavelength_nm in TARGET_NM:
            t_power, r_power, t_fields = monitor_names(wavelength_nm)
            _configure_monitor(fdtd, t_power, wavelength_nm, base.LAYOUT_NM["transmission_monitor_z_nm"], False)
            _configure_monitor(fdtd, r_power, wavelength_nm, base.LAYOUT_NM["reflection_monitor_z_nm"], False)
            _configure_monitor(fdtd, t_fields, wavelength_nm, base.LAYOUT_NM["transmission_monitor_z_nm"], True)
        fdtd.save(str(output_fsp))
    finally:
        fdtd.close()
    return read_only_audit(output_fsp, spec)


def _get(fdtd: Any, name: str, prop: str) -> Any:
    return fdtd.getnamed(name, prop)


def _as_float(value: Any) -> float:
    return float(np.squeeze(value))


def read_only_audit(path: Path, spec: dict[str, Any]) -> dict[str, Any]:
    before = fingerprint(path)
    fdtd = base._import_lumapi().FDTD(hide=True)
    try:
        fdtd.load(str(path))
        pillar_count = int(fdtd.getnamednumber("TiO2 pillar"))
        if pillar_count:
            raise RuntimeError("blank pre-FSP contains a TiO2 pillar")
        configured: list[float] = []
        monitor_inventory: list[dict[str, Any]] = []
        spatial_signatures: list[tuple[float, float, float]] = []
        for wavelength_nm in TARGET_NM:
            for name in monitor_names(wavelength_nm):
                center_nm = _as_float(_get(fdtd, name, "wavelength center")) / base.NM
                span_nm = _as_float(_get(fdtd, name, "wavelength span")) / base.NM
                points = int(_as_float(_get(fdtd, name, "frequency points")))
                use_limits = bool(_get(fdtd, name, "use source limits"))
                wavelength_spacing = bool(_get(fdtd, name, "use wavelength spacing"))
                x_span = _as_float(_get(fdtd, name, "x span"))
                y_span = _as_float(_get(fdtd, name, "y span"))
                z = _as_float(_get(fdtd, name, "z"))
                expected_z = base.LAYOUT_NM["reflection_monitor_z_nm"] if name.startswith("R_POWER") else base.LAYOUT_NM["transmission_monitor_z_nm"]
                if use_limits or not wavelength_spacing or points != 1 or abs(span_nm) > 1e-9 or not math.isclose(center_nm, wavelength_nm, abs_tol=1e-6):
                    raise RuntimeError(f"single-wavelength monitor readback failed: {name}")
                if not math.isclose(z / base.NM, expected_z, abs_tol=1e-6):
                    raise RuntimeError(f"monitor z mismatch: {name}")
                if not (math.isclose(x_span / base.NM, base.PITCH_NM, abs_tol=1e-6) and math.isclose(y_span / base.NM, base.PITCH_NM, abs_tol=1e-6)):
                    raise RuntimeError(f"monitor span mismatch: {name}")
                if name.startswith("T_FIELDS"):
                    configured.append(center_nm)
                monitor_inventory.append({"name": name, "wavelength_nm": center_nm, "wavelength_span_nm": span_nm, "frequency_points": points, "use_source_limits": use_limits, "use_wavelength_spacing": wavelength_spacing, "z_nm": z / base.NM})
                spatial_signatures.append((x_span, y_span, z))
        if len(monitor_inventory) != 33 or not np.allclose(configured, target_axis(), atol=1e-6, rtol=0):
            raise RuntimeError("configured wavelength axis is not exactly the target eleven-point axis")
        source_start_nm = _as_float(_get(fdtd, "source", "wavelength start")) / base.NM
        source_stop_nm = _as_float(_get(fdtd, "source", "wavelength stop")) / base.NM
        source_angle = _as_float(_get(fdtd, "source", "polarization angle"))
        if not (source_start_nm <= min(TARGET_NM) and source_stop_nm >= max(TARGET_NM) and abs(source_angle) < 1e-12):
            raise RuntimeError("source readback does not cover target x-polarized band")
        audit = {
            "fdt": {
                "x_span_nm": _as_float(_get(fdtd, "FDTD", "x span")) / base.NM,
                "y_span_nm": _as_float(_get(fdtd, "FDTD", "y span")) / base.NM,
                "z_min_nm": _as_float(_get(fdtd, "FDTD", "z min")) / base.NM,
                "z_max_nm": _as_float(_get(fdtd, "FDTD", "z max")) / base.NM,
                "x_min_bc": str(_get(fdtd, "FDTD", "x min bc")),
                "y_min_bc": str(_get(fdtd, "FDTD", "y min bc")),
                "z_min_bc": str(_get(fdtd, "FDTD", "z min bc")),
                "simulation_time_s": _as_float(_get(fdtd, "FDTD", "simulation time")),
                "auto_shutoff_min": _as_float(_get(fdtd, "FDTD", "auto shutoff min")),
            },
            "source": {"wavelength_start_nm": source_start_nm, "wavelength_stop_nm": source_stop_nm, "polarization_angle_deg": source_angle, "z_nm": _as_float(_get(fdtd, "source", "z")) / base.NM, "direction": str(_get(fdtd, "source", "direction"))},
            "pillar_count": pillar_count,
            "monitor_count": len(monitor_inventory),
            "monitor_inventory": monitor_inventory,
            "configured_wavelength_grid_nm": configured,
            "sampling_backend": BACKEND,
            "exact_axis_gate": True,
            "all_monitor_spatial_properties_verified": True,
        }
    finally:
        fdtd.close()
    after = fingerprint(path)
    if before != after:
        raise RuntimeError("read-only pre-FSP audit changed the file")
    audit["pre_fsp_fingerprint"] = after
    return audit


def _complex_dict(value: complex) -> dict[str, float]:
    value = complex(value)
    return {"real": value.real, "imag": value.imag, "amplitude": abs(value), "phase_deg_wrapped": float(np.degrees(np.angle(value)))}


def _area_average(component: np.ndarray, x: Any, y: Any) -> complex:
    arr = np.asarray(component)
    xv, yv = np.squeeze(np.asarray(x)), np.squeeze(np.asarray(y))
    if arr.ndim != 2 or xv.ndim != 1 or yv.ndim != 1 or len(xv) < 2 or len(yv) < 2:
        raise RuntimeError(f"unsafe field grid for area average: {arr.shape}, {xv.shape}, {yv.shape}")
    numerator = np.trapezoid(np.trapezoid(arr, yv, axis=1), xv, axis=0)
    area = float((xv[-1] - xv[0]) * (yv[-1] - yv[0]))
    if not np.isfinite(area) or abs(area) < 1e-30:
        raise RuntimeError("unsafe area denominator")
    return complex(numerator / area)


def extract_post_fsp(path: Path, spec: dict[str, Any]) -> dict[str, Any]:
    before = fingerprint(path)
    fdtd = base._import_lumapi().FDTD(hide=True)
    rows: list[dict[str, Any]] = []
    try:
        fdtd.load(str(path))
        if int(fdtd.getnamednumber("TiO2 pillar")):
            raise RuntimeError("post-FSP contains a TiO2 pillar")
        for wavelength_nm in TARGET_NM:
            t_power, r_power, t_fields = monitor_names(wavelength_nm)
            t = _as_float(fdtd.transmission(t_power))
            r_raw = _as_float(fdtd.transmission(r_power))
            fields = fdtd.getresult(t_fields, "E")
            e = np.squeeze(np.asarray(fields["E"]))
            if e.ndim != 3 or e.shape[-1] != 3:
                raise RuntimeError(f"unexpected E data shape for {t_fields}: {e.shape}")
            extracted_nm = _as_float(fields["lambda"]) / base.NM
            ax, ay = _area_average(e[..., 0], fields["x"], fields["y"]), _area_average(e[..., 1], fields["x"], fields["y"])
            values = [t, r_raw, ax.real, ax.imag, ay.real, ay.imag, extracted_nm]
            if not np.isfinite(values).all() or not math.isclose(extracted_nm, wavelength_nm, abs_tol=1e-6):
                raise RuntimeError(f"non-finite or wrong wavelength result for {wavelength_nm} nm")
            r_total = -r_raw
            rows.append({"wavelength_nm": extracted_nm, "frequency_hz": 299792458.0 / (extracted_nm * base.NM), "T": t, "R_raw": r_raw, "R_total": r_total, "energy_residual": abs(1 - t - r_total), "ax": _complex_dict(ax), "ay": _complex_dict(ay)})
    finally:
        fdtd.close()
    after = fingerprint(path)
    if before != after:
        raise RuntimeError("read-only post-FSP extraction changed the file")
    axis = [row["wavelength_nm"] for row in rows]
    if not np.allclose(axis, target_axis(), atol=1e-6, rtol=0):
        raise RuntimeError("extracted axis is not exactly the target grid")
    return {"rows": rows, "extracted_wavelength_grid_nm": axis, "post_fsp_fingerprint": after}


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_outputs(spec: dict[str, Any], pre_audit: dict[str, Any], extracted: dict[str, Any]) -> dict[str, Any]:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    contract = physical_contract(spec, pre_audit)
    contract_digest = contract_hash(contract)
    rows = extracted["rows"]
    metrics = {
        "T_min_over_band": min(r["T"] for r in rows), "T_max_over_band": max(r["T"] for r in rows),
        "T_peak_to_peak": max(r["T"] for r in rows) - min(r["T"] for r in rows),
        "R_total_min_over_band": min(r["R_total"] for r in rows), "R_total_max_over_band": max(r["R_total"] for r in rows),
        "energy_residual_mean_over_band": float(np.mean([r["energy_residual"] for r in rows])),
        "energy_residual_max_over_band": max(r["energy_residual"] for r in rows),
        "blank_ax_amplitude_min": min(r["ax"]["amplitude"] for r in rows), "blank_ax_amplitude_max": max(r["ax"]["amplitude"] for r in rows),
        "blank_ax_phase_span_deg": max(r["ax"]["phase_deg_wrapped"] for r in rows) - min(r["ax"]["phase_deg_wrapped"] for r in rows),
        "blank_ay_amplitude_max": max(r["ay"]["amplitude"] for r in rows),
        "cross_pol_reference_max": max(r["ay"]["amplitude"] for r in rows),
    }
    formal = metrics["energy_residual_max_over_band"] <= 0.08 and metrics["blank_ax_amplitude_min"] > 1e-12
    axis_audit = {
        "target_axis": target_axis(), "configured_axis": pre_audit["configured_wavelength_grid_nm"],
        "extracted_axis": extracted["extracted_wavelength_grid_nm"], "sampling_backend": BACKEND,
        "per_monitor_mapping": spec["monitor_mapping"], "exact_axis_gate": True,
        "interpolation_used": False, "nearest_neighbor_used": False, "frequency_uniform_axis_misrepresented": False,
    }
    verification = {"P1D2A_FORMAL_STATUS": "pass" if formal else "fail", "P1D2_BROADBAND_BLANK_READY": formal, "finite_data_gate": True, "denominator_safety_gate": metrics["blank_ax_amplitude_min"] > 1e-12, "common_11point_axis_gate": True, "metrics": metrics}
    manifest = {"case_id": CASE_ID, "mode": "run", "created_utc": datetime.now(timezone.utc).isoformat(), "pre_fsp": pre_audit["pre_fsp_fingerprint"], "post_fsp": extracted["post_fsp_fingerprint"], "physical_contract_hash": contract_digest, "new_solver_run_entered": 1, "new_solver_run_completed": 1}
    _write_json(OUTPUT / "blank_spectrum.json", {"case_id": CASE_ID, "rows": rows})
    with (OUTPUT / "blank_spectrum.csv").open("w", newline="", encoding="utf-8") as f:
        fieldnames = ["wavelength_nm", "frequency_hz", "T", "R_raw", "R_total", "energy_residual", "ax_real", "ax_imag", "ax_amplitude", "ax_phase_deg", "ay_real", "ay_imag", "ay_amplitude", "ay_phase_deg"]
        writer = csv.DictWriter(f, fieldnames=fieldnames); writer.writeheader()
        for r in rows:
            writer.writerow({"wavelength_nm": r["wavelength_nm"], "frequency_hz": r["frequency_hz"], "T": r["T"], "R_raw": r["R_raw"], "R_total": r["R_total"], "energy_residual": r["energy_residual"], "ax_real": r["ax"]["real"], "ax_imag": r["ax"]["imag"], "ax_amplitude": r["ax"]["amplitude"], "ax_phase_deg": r["ax"]["phase_deg_wrapped"], "ay_real": r["ay"]["real"], "ay_imag": r["ay"]["imag"], "ay_amplitude": r["ay"]["amplitude"], "ay_phase_deg": r["ay"]["phase_deg_wrapped"]})
    _write_json(OUTPUT / "wavelength_axis_audit.json", axis_audit)
    _write_json(OUTPUT / "monitor_mapping.json", spec["monitor_mapping"])
    _write_json(OUTPUT / "physical_contract.json", contract)
    _write_json(OUTPUT / "run_manifest.json", manifest)
    _write_json(OUTPUT / "verification_summary.json", verification)
    report = ROOT / "docs" / "np_k6_p1d2a_broadband_blank_x_report_v1.md"
    report.write_text(
        ("# NP-K6 P1-D2A broadband fixed-reference blank (x)\n\n"
         "- Case: %s\n"
         "- Sampling backend: %s\n"
         "- Exact wavelength axis (nm): %s\n"
         "- Pre-FSP SHA256: %s\n"
         "- Post-FSP SHA256: %s\n"
         "- T range: %.9g to %.9g\n"
         "- R_total range: %.9g to %.9g\n"
         "- Maximum energy residual: %.9g\n"
         "- Formal status: %s\n"
         "\nNo interpolation or nearest-neighbour substitution was used. a_x_blank and "
         "a_y_blank are field-plane area averages.\n")
        % (CASE_ID, BACKEND, target_axis(), pre_audit["pre_fsp_fingerprint"]["sha256"],
           extracted["post_fsp_fingerprint"]["sha256"], metrics["T_min_over_band"],
           metrics["T_max_over_band"], metrics["R_total_min_over_band"],
           metrics["R_total_max_over_band"], metrics["energy_residual_max_over_band"],
           "pass" if formal else "fail"),
        encoding="utf-8",
    )
    return {"contract_hash": contract_digest, "metrics": metrics, "formal": formal, "verification": verification}


def update_release(summary: dict[str, Any], post_fingerprint: dict[str, Any]) -> None:
    path = ROOT / "outputs" / "np_k6_p1d2_broadband_contract_v1" / "broadband_library_contract.json"
    contract = json.loads(path.read_text(encoding="utf-8"))
    contract.update({"broadband_blank_id": CASE_ID, "broadband_blank_status": "trusted_completed" if summary["formal"] else "failed", "broadband_blank_fsp_path": post_fingerprint["path"], "broadband_blank_sha256": post_fingerprint["sha256"], "broadband_blank_physical_contract_hash": summary["contract_hash"], "broadband_blank_wavelength_axis_hash": hashlib.sha256(json.dumps(target_axis()).encode()).hexdigest(), "broadband_blank_result_hash": sha256(OUTPUT / "blank_spectrum.json"), "spectral_sampling_backend": BACKEND, "P1D2A_FORMAL_STATUS": "pass" if summary["formal"] else "fail", "P1D2_BROADBAND_BLANK_READY": summary["formal"], "P1D2_NEXT_AUTHORIZED_ACTION": "BROADBAND_PILLAR_D100_X_ONLY" if summary["formal"] else None})
    _write_json(path, contract)
    _write_json(path.parent / "run_manifest.json", json.loads((OUTPUT / "run_manifest.json").read_text(encoding="utf-8")))
    _write_json(path.parent / "verification_summary.json", summary["verification"])


def main() -> int:
    parser = argparse.ArgumentParser(description="P1-D2 exact eleven-wavelength x-polarized blank only.")
    parser.add_argument("--mode", choices=("build", "audit", "run"), required=True)
    parser.add_argument("--case-id", default=CASE_ID)
    args = parser.parse_args()
    spec = build_spec(args.case_id)
    if args.mode == "build":
        audit = create_pre_fsp(spec)
        print(json.dumps({"mode": "build", "pre_fsp": fingerprint(PRE_FSP), "audit": audit, "physical_contract_hash": contract_hash(physical_contract(spec, audit))}, indent=2, sort_keys=True))
        return 0
    if args.mode == "audit":
        print(json.dumps(read_only_audit(PRE_FSP, spec), indent=2, sort_keys=True)); return 0
    if not PRE_FSP.exists():
        raise RuntimeError("pre-FSP is required before the one authorized solver run")
    pre_audit = read_only_audit(PRE_FSP, spec)
    fdtd = base._import_lumapi().FDTD(hide=True)
    try:
        fdtd.load(str(PRE_FSP))
        print("SOLVER_RUN_CALL_ENTERING", flush=True)
        fdtd.run()
        print("SOLVER_RUN_CALL_RETURNED", flush=True)
        fdtd.save(str(POST_FSP))
    finally:
        fdtd.close()
    extracted = extract_post_fsp(POST_FSP, spec)
    summary = write_outputs(spec, pre_audit, extracted)
    update_release(summary, extracted["post_fsp_fingerprint"])
    print(json.dumps({"mode": "run", "formal": summary["formal"], "metrics": summary["metrics"], "post_fsp": extracted["post_fsp_fingerprint"]}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
