#!/usr/bin/env python3
"""Read-only GaN response extraction and blank-session material roundtrip audit."""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "mdc_gan_native_m1_extraction_audit_v1"
REPORT = ROOT / "reports" / "mdc_gan_native_m1_extraction_audit_v1.md"
FSP = Path(r"F:\wc_312\MDC_blue_oujizi_m\m_1.fsp")
EXPECTED_SHA = "d7511bb92154152d5050d7ae664cb5b281ad3794a280129008359353b357e26f"
EXPECTED_BYTES = 34_241_853
MATERIAL = "GaN"
C = 299_792_458.0
WAVELENGTHS = np.round(np.arange(420.0, 480.0 + 0.05, 0.1), 1)
CRITICAL = (420.0, 448.0, 450.0, 453.0, 480.0)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def json_safe(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return {"kind": "ndarray", "shape": list(value.shape), "dtype": str(value.dtype), "sha256": hashlib.sha256(value.tobytes()).hexdigest()}
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def check_source() -> dict[str, Any]:
    present = FSP.is_file()
    actual_bytes = FSP.stat().st_size if present else None
    actual_sha = sha256(FSP) if present else ""
    state = {"path": str(FSP), "expected_bytes": EXPECTED_BYTES, "actual_bytes": actual_bytes, "expected_sha256": EXPECTED_SHA, "actual_sha256": actual_sha, "size_matches": actual_bytes == EXPECTED_BYTES, "sha256_matches": actual_sha == EXPECTED_SHA}
    if not present or not state["size_matches"] or not state["sha256_matches"]:
        raise RuntimeError(f"fixed FSP source gate failed: {state}")
    return state


def delayed_lumapi() -> Any:
    api = Path(r"N:\Program Files\ANSYS Inc\v251\Lumerical\api\python\lumapi.py")
    spec = importlib.util.spec_from_file_location("lumapi", api)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load lumapi from {api}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def material_metadata(fdtd: Any, material: str) -> tuple[dict[str, Any], list[dict[str, str]]]:
    properties: dict[str, Any] = {}
    limitations: list[dict[str, str]] = []
    for prop in ("type", "material type", "reference", "frequency min", "frequency max", "sampled data", "tolerance", "fit tolerance", "fit range", "material database"):
        try:
            properties[prop] = json_safe(fdtd.getmaterial(material, prop))
        except Exception as exc:
            limitations.append({"property": prop, "reason": str(exc)})
    return properties, limitations


def index_response(fdtd: Any, material: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    frequency = C / (WAVELENGTHS * 1e-9)
    index = np.asarray(fdtd.getfdtdindex(material, frequency, float(frequency.min()), float(frequency.max()))).reshape(-1)
    if index.size != WAVELENGTHS.size:
        raise RuntimeError(f"index query length {index.size}, expected {WAVELENGTHS.size}")
    epsilon = index ** 2
    if not np.isfinite(index.real).all() or not np.isfinite(index.imag).all() or not np.isfinite(epsilon.real).all() or not np.isfinite(epsilon.imag).all():
        raise RuntimeError("non-finite source material response")
    return frequency, index, epsilon


def source_extract() -> dict[str, Any]:
    source = check_source()
    prior_sessions: list[dict[str, Any]] = []
    prior = OUT / "gan_source_material_metadata.json"
    if prior.is_file():
        try:
            prior_sessions = json.loads(prior.read_text(encoding="utf-8")).get("sessions", [])
        except Exception:
            prior_sessions = []
    state: dict[str, Any] = {"sessions": prior_sessions + [{"purpose": "source_FSP_metadata_and_601_point_index_query", "started": False, "closed": False}], "source": source, "object_material_assignment": {}, "metadata": {}, "metadata_api_limitations": [], "error": ""}
    fdtd = None
    try:
        lumapi = delayed_lumapi()
        fdtd = lumapi.FDTD(hide=True)
        state["sessions"][-1]["started"] = True
        fdtd.load(str(FSP))
        fdtd.select(MATERIAL)
        obj = fdtd.getObjectBySelection()
        assigned = str(obj["material"])
        state["object_material_assignment"] = {"geometry_object": str(obj["name"]), "assigned_material": assigned}
        if assigned != MATERIAL:
            raise RuntimeError(f"GaN object assignment mismatch: {assigned}")
        metadata, limitations = material_metadata(fdtd, MATERIAL)
        state["metadata"] = metadata
        state["metadata_api_limitations"] = limitations
        frequency, index, epsilon = index_response(fdtd, MATERIAL)
        rows: list[dict[str, Any]] = []
        for wavelength, freq, value, eps in zip(WAVELENGTHS, frequency, index, epsilon):
            rows.append({"wavelength_nm": f"{wavelength:.1f}", "frequency_hz": f"{freq:.12g}", "n_real": f"{value.real:.12g}", "k_imag": f"{value.imag:.12g}", "epsilon_real": f"{eps.real:.12g}", "epsilon_imag": f"{eps.imag:.12g}", "source_fsp_sha256": EXPECTED_SHA, "extraction_method": "getfdtdindex queried fitted/effective response from source FSP"})
        write_csv(OUT / "gan_complex_index_420_480.csv", rows, list(rows[0]))
        critical_rows = [row for row in rows if float(row["wavelength_nm"]) in CRITICAL]
        write_csv(OUT / "gan_critical_wavelengths.csv", critical_rows, list(rows[0]))
        roundtrip_payload = {"frequency_hz": frequency.tolist(), "epsilon_real": epsilon.real.tolist(), "epsilon_imag": epsilon.imag.tolist()}
        dump_json(OUT / "_roundtrip_payload.json", roundtrip_payload)
        state["response"] = {"point_count": len(rows), "wavelength_start_nm": 420.0, "wavelength_stop_nm": 480.0, "wavelength_step_nm": 0.1, "frequency_order_for_ascending_wavelength": "strictly descending", "extraction_method": "getfdtdindex queried fitted/effective response from source FSP", "critical_values": [{"wavelength_nm": row["wavelength_nm"], "n_real": row["n_real"], "k_imag": row["k_imag"]} for row in critical_rows]}
    except Exception as exc:
        state["error"] = str(exc)
        raise
    finally:
        if fdtd is not None:
            try:
                fdtd.close()
                state["sessions"][-1]["closed"] = True
            except Exception as exc:
                state["sessions"][-1]["close_error"] = str(exc)
        dump_json(OUT / "gan_source_material_metadata.json", state)
    return state


def read_response() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    path = OUT / "gan_complex_index_420_480.csv"
    if not path.is_file():
        raise RuntimeError("extract response first with --extract")
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    wavelength = np.asarray([float(row["wavelength_nm"]) for row in rows])
    frequency = np.asarray([float(row["frequency_hz"]) for row in rows])
    epsilon = np.asarray([float(row["epsilon_real"]) + 1j * float(row["epsilon_imag"]) for row in rows])
    if wavelength.size != 601 or not np.allclose(wavelength, WAVELENGTHS):
        raise RuntimeError("response grid is not the required 601-point 420-480 nm grid")
    return wavelength, frequency, epsilon


def roundtrip_register() -> dict[str, Any]:
    source = check_source()
    wavelength, frequency, epsilon = read_response()
    state: dict[str, Any] = {"sessions": [{"purpose": "blank_session_sampled_data_candidate_registration_and_index_query", "started": False, "closed": False}], "candidate_material_name": "APCD_GAN_FSP_M1_CANDIDATE", "registration_api": ["addmaterial('Sampled data')", "setmaterial(name, 'sampled data', frequency_epsilon_matrix)", "getfdtdindex"], "error": "", "status": "portable_registration_failed"}
    fdtd = None
    try:
        lumapi = delayed_lumapi()
        fdtd = lumapi.FDTD(hide=True)
        state["sessions"][0]["started"] = True
        created = fdtd.addmaterial("Sampled data")
        fdtd.setmaterial(created, "name", state["candidate_material_name"])
        payload = np.column_stack((frequency, epsilon))
        fdtd.setmaterial(state["candidate_material_name"], "sampled data", payload)
        cloned = np.asarray(fdtd.getfdtdindex(state["candidate_material_name"], frequency, float(frequency.min()), float(frequency.max()))).reshape(-1)
        original = np.sqrt(epsilon)
        original = np.where(original.imag < 0, -original, original)
        delta_n = np.abs(cloned.real - original.real)
        delta_k = np.abs(cloned.imag - original.imag)
        rows = [{"wavelength_nm": f"{wl:.1f}", "source_n": f"{n0.real:.12g}", "source_k": f"{n0.imag:.12g}", "candidate_n": f"{n1.real:.12g}", "candidate_k": f"{n1.imag:.12g}", "delta_n": f"{dn:.12g}", "delta_k": f"{dk:.12g}"} for wl, n0, n1, dn, dk in zip(wavelength, original, cloned, delta_n, delta_k)]
        write_csv(OUT / "gan_blank_session_roundtrip.csv", rows, list(rows[0]))
        critical = [row for row in rows if float(row["wavelength_nm"]) in CRITICAL]
        state.update({"status": "portable_response_roundtrip_pass", "max_abs_delta_n": float(delta_n.max()), "max_abs_delta_k": float(delta_k.max()), "rms_delta": float(np.sqrt(np.mean(delta_n**2 + delta_k**2))), "critical_wavelength_delta": critical, "source_sha256": source["actual_sha256"], "reproducible": bool(delta_n.max() <= 1e-9 and delta_k.max() <= 1e-9)})
    except Exception as exc:
        state["error"] = str(exc)
    finally:
        if fdtd is not None:
            try:
                fdtd.close()
                state["sessions"][0]["closed"] = True
            except Exception as exc:
                state["sessions"][0]["close_error"] = str(exc)
        dump_json(OUT / "_roundtrip_state.json", state)
    return state


def absorption_rows() -> list[dict[str, Any]]:
    rows = list(csv.DictReader((OUT / "gan_complex_index_420_480.csv").open(encoding="utf-8")))
    out: list[dict[str, Any]] = []
    for row in rows:
        wavelength_m = float(row["wavelength_nm"]) * 1e-9
        alpha = 4.0 * math.pi * float(row["k_imag"]) / wavelength_m
        out.append({"wavelength_nm": row["wavelength_nm"], "k_imag": row["k_imag"], "absorption_coefficient_m_inv": f"{alpha:.12g}", "absorption_coefficient_cm_inv": f"{alpha / 100.0:.12g}", "intensity_remaining_100nm": f"{math.exp(-alpha * 100e-9):.12g}", "intensity_remaining_400nm": f"{math.exp(-alpha * 400e-9):.12g}", "intensity_remaining_1um": f"{math.exp(-alpha * 1e-6):.12g}"})
    write_csv(OUT / "gan_absorption_sanity.csv", out, list(out[0]))
    return out


def deembedding_spec() -> dict[str, Any]:
    return {"scope": "rule only; no runner/configuration mutation", "sourcepower_definition": "injected power at the source plane only", "canonical_transmission": "stack-relative flux de-embedded at the stack entrance plane", "required_matched_homogeneous_gan_reference": {"same_source_position": True, "same_monitor_position": True, "same_GaN_material": True, "same_boundaries": True, "same_mesh": True, "same_polarization": True, "same_angle": True}, "requirements": ["Do not attribute source-to-stack GaN propagation loss to MDC transmission.", "Record reference-plane placement and propagation-loss treatment for reflection.", "Keep bare GaN/Air as an independent control.", "Do not substitute T_stack/T_bare for the full physical definition.", "If TMM retains lossless n=2.41, label the comparison material_model_mismatch_present.", "For formal cross-method comparison, either update TMM to the same dispersive complex GaN or compare only de-embedded stack-relative quantities."], "formal_comparison_gate": "one of the two declared comparison branches must be selected explicitly"}


def finalise() -> None:
    source = check_source()
    metadata = json.loads((OUT / "gan_source_material_metadata.json").read_text(encoding="utf-8"))
    roundtrip_path = OUT / "_roundtrip_state.json"
    roundtrip = json.loads(roundtrip_path.read_text(encoding="utf-8")) if roundtrip_path.is_file() else {"status": "not_attempted"}
    absorption = absorption_rows()
    critical_absorption = [row for row in absorption if float(row["wavelength_nm"]) in CRITICAL]
    response = list(csv.DictReader((OUT / "gan_complex_index_420_480.csv").open(encoding="utf-8")))
    values = {float(row["wavelength_nm"]): row for row in response}
    comparison = []
    for wavelength in (448.0, 450.0, 453.0):
        row = values[wavelength]
        comparison.append({"wavelength_nm": f"{wavelength:.1f}", "legacy_tmm_n": "2.41", "legacy_tmm_k": "0", "legacy_rcled_n": "2.56", "legacy_rcled_k": "0", "fsp_gan_n": row["n_real"], "fsp_gan_k": row["k_imag"], "delta_n_vs_tmm": f"{float(row['n_real']) - 2.41:.12g}", "delta_k_vs_tmm": row["k_imag"], "implication": "Fresnel/Bloch/sourcepower/propagation-loss differ; no equivalence claimed"})
    write_csv(OUT / "gan_policy_comparison.csv", comparison, list(comparison[0]))
    dump_json(OUT / "fdtd_gan_deembedding_spec.json", deembedding_spec())
    response_ok = metadata.get("response", {}).get("point_count") == 601 and not metadata.get("error")
    source_session_ok = all(item["started"] and item["closed"] for item in metadata["sessions"])
    roundtrip_ok = roundtrip.get("status") == "portable_response_roundtrip_pass" and roundtrip.get("reproducible")
    status = "portable_registration_failed"
    if response_ok and roundtrip_ok:
        status = "portable_response_found_but_bulk_substrate_physics_unconfirmed"
    policy = None
    if status == "portable_formal_candidate_ready_for_physical_approval":
        policy = {"policy_status": "proposed_not_frozen", "canonical_material_id": "APCD_GAN_FSP_M1_CANDIDATE"}
    validation = {"status": status, "source_gate": source, "response_601_points": response_ok, "source_session_closed": source_session_ok, "roundtrip": roundtrip, "no_solver_execution": True, "no_project_save": True, "high_k_warning_450nm": float(values[450.0]["k_imag"]) >= 0.084153, "policy_is_not_frozen": True, "deembedding_spec_present": True}
    dump_json(OUT / "gan_candidate_policy.json", policy)
    dump_json(OUT / "validation.json", validation)
    manifest = {"task": "MDC_GAN_NATIVE_M1_EXTRACTION_AND_DEEMBED_AUDIT_V1", "source_fsp": source, "material_object": MATERIAL, "outputs": sorted(p.name for p in OUT.iterdir() if not p.name.startswith("_")), "session_count": len(metadata.get("sessions", [])) + len(roundtrip.get("sessions", [])), "session_purposes": metadata.get("sessions", []) + roundtrip.get("sessions", [])}
    dump_json(OUT / "manifest.json", manifest)
    report = ["# MDC GaN Native-M1 extraction and deembedding audit v1", "", "## Answers", "", "1. Response is queried from the fixed Native-M1 source FSP, not newly fitted.", "2. Measurement provenance cannot be proven from the available material metadata.", f"3. Blank-session response reproduction: `{roundtrip.get('status')}`.", "4. Bulk-GaN suitability remains unconfirmed: the object is named GaN but its physical role/provenance is not established.", f"5. At 450 nm, k={values[450.0]['k_imag']}; this implies strong propagation loss, not a lossless bulk-substrate assumption.", "6. Phase A/B/C remain blocked.", "7. User approval/provenance clarification is required before a policy can be frozen.", "8. No solver execution occurred.", "", "## Source", "", f"- `{FSP}`", f"- SHA256 `{source['actual_sha256']}`, bytes `{source['actual_bytes']}`.", "", "## Material metadata", "", f"- Geometry object/material assignment: `{metadata.get('object_material_assignment')}`.", f"- Available metadata: `{metadata.get('metadata')}`.", f"- API limitations: `{metadata.get('metadata_api_limitations')}`.", "", "## Response and absorption", "", f"- 601 queried fitted/effective response points, 420-480 nm, 0.1 nm step.", f"- Critical n/k: 448 nm ({values[448.0]['n_real']}, {values[448.0]['k_imag']}), 450 nm ({values[450.0]['n_real']}, {values[450.0]['k_imag']}), 453 nm ({values[453.0]['n_real']}, {values[453.0]['k_imag']}).", f"- 450 nm absorption: `{next(row for row in critical_absorption if row['wavelength_nm'] == '450.0')}`.", "", "## Decision", "", f"- Status: `{status}`.", "- Candidate response is not declared measured, bulk-correct, or frozen.", "- `gan_candidate_policy.json` is null.", "", "## Deembedding", "", "- Formal comparison requires matched homogeneous-GaN reference-plane deembedding; bare GaN/Air remains an independent control.", "- A lossless n=2.41 TMM comparison must carry `material_model_mismatch_present`.", "", "## Safety", "", "- Only material metadata/index queries and blank-session sampled-data registration were used; no solver execution or project save.", ""]
    REPORT.write_text("\n".join(report), encoding="utf-8")


def audit() -> None:
    required = ["gan_source_material_metadata.json", "gan_complex_index_420_480.csv", "gan_critical_wavelengths.csv", "gan_blank_session_roundtrip.csv", "gan_absorption_sanity.csv", "gan_policy_comparison.csv", "fdtd_gan_deembedding_spec.json", "gan_candidate_policy.json", "validation.json", "manifest.json"]
    missing = [name for name in required if not (OUT / name).is_file()]
    if missing or not REPORT.is_file():
        raise RuntimeError(f"audit outputs missing: {missing}")
    validation = json.loads((OUT / "validation.json").read_text(encoding="utf-8"))
    if validation["no_solver_execution"] is not True or validation["no_project_save"] is not True:
        raise RuntimeError("unsafe action recorded")
    if validation["status"] == "portable_formal_candidate_ready_for_physical_approval":
        raise RuntimeError("formal approval cannot be automatic in this audit")
    print(f"GaN Native-M1 extraction audit PASS: status={validation['status']}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit-only", action="store_true")
    parser.add_argument("--extract", action="store_true")
    parser.add_argument("--roundtrip-register", action="store_true")
    args = parser.parse_args()
    if sum((args.audit_only, args.extract, args.roundtrip_register)) != 1:
        parser.error("choose exactly one mode")
    OUT.mkdir(parents=True, exist_ok=True)
    if args.extract:
        source_extract()
        if (OUT / "_roundtrip_state.json").is_file():
            finalise()
        return
    if args.roundtrip_register:
        roundtrip_register()
        finalise()
        return
    audit()


if __name__ == "__main__":
    main()
