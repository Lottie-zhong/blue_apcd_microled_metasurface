#!/usr/bin/env python3
"""Promote the project-native GaN sampled table without running a solver."""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "apcd_gan_native_m1_promotion_v1"
REPORT = ROOT / "reports" / "apcd_gan_native_m1_promotion_v1.md"
POLICY_PATH = ROOT / "configs" / "mdc_defect_450_material_policy.json"
OLD_LIBRARY = ROOT / "outputs" / "material_reference" / "mdc_blue_oujizi_m" / "material_ref_native_sampled.csv"
NEW_LIBRARY = ROOT / "outputs" / "material_reference" / "mdc_blue_oujizi_m" / "material_ref_native_sampled_mdc_native_m1.csv"
FSP = Path(r"F:\wc_312\MDC_blue_oujizi_m\m_1.fsp")
EXPECTED_SHA = "d7511bb92154152d5050d7ae664cb5b281ad3794a280129008359353b357e26f"
EXPECTED_BYTES = 34_241_853
API_PATH = Path(r"N:\Program Files\ANSYS Inc\v251\Lumerical\api\python\lumapi.py")
CANONICAL_ID = "APCD_GAN_NATIVE_M1"
C = 299_792_458.0
WAVELENGTHS = np.round(np.arange(420.0, 480.0 + 0.05, 0.1), 1)
CRITICAL = {420.0, 448.0, 450.0, 453.0, 480.0}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def csv_write(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader(); writer.writerows(rows)


def lumapi_module():
    spec = importlib.util.spec_from_file_location("lumapi", API_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load lumapi from {API_PATH}")
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def source_gate() -> dict[str, Any]:
    actual_bytes = FSP.stat().st_size if FSP.is_file() else None
    actual_sha = sha(FSP) if FSP.is_file() else ""
    result = {"path": str(FSP), "expected_bytes": EXPECTED_BYTES, "actual_bytes": actual_bytes, "expected_sha256": EXPECTED_SHA, "actual_sha256": actual_sha, "size_matches": actual_bytes == EXPECTED_BYTES, "sha256_matches": actual_sha == EXPECTED_SHA}
    if not (result["size_matches"] and result["sha256_matches"]):
        raise RuntimeError(f"source FSP identity gate failed: {result}")
    return result


def physical_index(epsilon: np.ndarray) -> np.ndarray:
    nk = np.sqrt(np.asarray(epsilon, dtype=np.complex128))
    nk = np.where(nk.real < 0, -nk, nk)
    if not np.isfinite(nk.real).all() or not np.isfinite(nk.imag).all() or np.any(nk.imag < -1e-12):
        raise RuntimeError("epsilon does not yield passive physical principal n+ik")
    return nk


def source_extract() -> dict[str, Any]:
    OUT.mkdir(parents=True, exist_ok=True)
    gate = source_gate(); session = {"purpose": "readonly_source_fsp_raw_sampled_data_and_601_point_query", "started": False, "closed": False}
    fdtd = None
    try:
        fdtd = lumapi_module().FDTD(hide=True); session["started"] = True
        fdtd.load(str(FSP)); fdtd.select("GaN"); obj = fdtd.getObjectBySelection()
        assignment = {"geometry_object": str(obj["name"]), "assigned_material": str(obj["material"])}
        if assignment != {"geometry_object": "GaN", "assigned_material": "GaN"}:
            raise RuntimeError(f"unexpected GaN object identity: {assignment}")
        raw = np.asarray(fdtd.getmaterial("GaN", "sampled data"), dtype=np.complex128)
        if raw.shape != (500, 2):
            raise RuntimeError(f"expected raw 500x2 complex sampled table, got {raw.shape}")
        frequency = raw[:, 0].real.astype(float); epsilon = raw[:, 1]
        if not np.isfinite(frequency).all() or not np.isfinite(epsilon.real).all() or not np.isfinite(epsilon.imag).all() or np.any(np.diff(frequency) <= 0):
            raise RuntimeError("invalid GaN raw sampled table")
        raw_hash = hashlib.sha256(raw.tobytes()).hexdigest(); raw_nk = physical_index(epsilon)
        raw_rows = [{"canonical_id": CANONICAL_ID, "frequency_hz": f"{f:.16g}", "wavelength_nm": f"{C/f*1e9:.16g}", "epsilon_real": f"{e.real:.16g}", "epsilon_imag": f"{e.imag:.16g}", "n_real": f"{n.real:.16g}", "k_imag": f"{n.imag:.16g}", "source_fsp_sha256": EXPECTED_SHA, "data_kind": "raw_sampled_3d_data", "interpolation_method": "none"} for f,e,n in zip(frequency, epsilon, raw_nk)]
        csv_write(OUT / "gan_raw_frequency_epsilon.csv", raw_rows, list(raw_rows[0]))
        query_frequency = C / (WAVELENGTHS * 1e-9)
        query_nk = np.asarray(fdtd.getfdtdindex("GaN", query_frequency, float(query_frequency.min()), float(query_frequency.max()))).reshape(-1)
        if query_nk.size != 601 or not np.isfinite(query_nk.real).all() or not np.isfinite(query_nk.imag).all():
            raise RuntimeError("source 601-point response invalid")
        query_eps = query_nk**2
        query_rows = [{"canonical_id": CANONICAL_ID, "wavelength_nm": f"{wl:.1f}", "frequency_hz": f"{f:.16g}", "epsilon_real": f"{e.real:.16g}", "epsilon_imag": f"{e.imag:.16g}", "n_real": f"{n.real:.16g}", "k_imag": f"{n.imag:.16g}", "query_method": "getfdtdindex source_FSP_validation_only", "source_fsp_sha256": EXPECTED_SHA} for wl,f,e,n in zip(WAVELENGTHS,query_frequency,query_eps,query_nk)]
        csv_write(OUT / "gan_complex_index_420_480.csv", query_rows, list(query_rows[0]))
        metadata = {"source_gate": gate, "object_material_assignment": assignment, "material_type": "Sampled 3D data", "tolerance": 0.1, "raw_shape": [500, 2], "raw_table_sha256": raw_hash, "query_response_sha256": sha(OUT / "gan_complex_index_420_480.csv"), "extraction_api": ["FDTD.load(read-only)", "getObjectBySelection", "getmaterial('GaN','sampled data')", "getfdtdindex"], "raw_frequency_range_hz": [float(frequency.min()), float(frequency.max())], "raw_wavelength_range_nm": [float((C/frequency*1e9).min()), float((C/frequency*1e9).max())], "query_points": 601, "session": session}
        dump(OUT / "source_extraction_metadata.json", metadata)
        return metadata
    finally:
        if fdtd is not None:
            fdtd.close(); session["closed"] = True
            if (OUT / "source_extraction_metadata.json").is_file():
                state = json.loads((OUT / "source_extraction_metadata.json").read_text(encoding="utf-8")); state["session"] = session; dump(OUT / "source_extraction_metadata.json", state)


def rows(path: Path) -> list[dict[str, str]]:
    return list(csv.DictReader(path.open(encoding="utf-8", newline="")))


def roundtrip() -> dict[str, Any]:
    raw = rows(OUT / "gan_raw_frequency_epsilon.csv")
    frequency = np.asarray([float(x["frequency_hz"]) for x in raw]); epsilon = np.asarray([complex(float(x["epsilon_real"]), float(x["epsilon_imag"])) for x in raw])
    query_frequency = C / (WAVELENGTHS * 1e-9)
    source = np.asarray([complex(float(x["n_real"]), float(x["k_imag"])) for x in rows(OUT / "gan_complex_index_420_480.csv")])
    session = {"purpose": "blank_session_APCD_GAN_NATIVE_M1_raw_table_registration_roundtrip", "started": False, "closed": False}; fdtd = None
    state: dict[str, Any] = {"status": "promotion_failed", "session": session, "registration_api": ["addmaterial('Sampled data')", "setmaterial('sampled data', raw_frequency_epsilon)", "getfdtdindex"]}
    try:
        fdtd = lumapi_module().FDTD(hide=True); session["started"] = True
        created = fdtd.addmaterial("Sampled data"); fdtd.setmaterial(created, "name", CANONICAL_ID)
        fdtd.setmaterial(CANONICAL_ID, "sampled data", np.column_stack((frequency, epsilon)))
        cloned = np.asarray(fdtd.getfdtdindex(CANONICAL_ID, query_frequency, float(query_frequency.min()), float(query_frequency.max()))).reshape(-1)
        if cloned.size != 601 or not np.isfinite(cloned.real).all() or not np.isfinite(cloned.imag).all():
            raise RuntimeError("roundtrip returned invalid response")
        dn = np.abs(cloned.real-source.real); dk = np.abs(cloned.imag-source.imag)
        table = [{"wavelength_nm": f"{wl:.1f}", "source_n": f"{a.real:.16g}", "source_k": f"{a.imag:.16g}", "registered_n": f"{b.real:.16g}", "registered_k": f"{b.imag:.16g}", "delta_n": f"{d1:.16g}", "delta_k": f"{d2:.16g}"} for wl,a,b,d1,d2 in zip(WAVELENGTHS,source,cloned,dn,dk)]
        csv_write(OUT / "gan_roundtrip_validation.csv", table, list(table[0]))
        state.update({"status": "promotion_roundtrip_pass" if dn.max() <= 1e-9 and dk.max() <= 1e-9 else "promotion_failed", "max_abs_delta_n": float(dn.max()), "max_abs_delta_k": float(dk.max()), "finite_points": int(cloned.size), "coverage_nm": [420.0,480.0]})
    except Exception as exc:
        state["error"] = str(exc)
    finally:
        if fdtd is not None:
            fdtd.close(); session["closed"] = True
        dump(OUT / "roundtrip_state.json", state)
    return state


def update_library_and_policy(metadata: dict[str, Any], rt: dict[str, Any]) -> None:
    if rt.get("status") != "promotion_roundtrip_pass":
        raise RuntimeError(f"promotion failed; config intentionally unchanged: {rt}")
    current = json.loads(POLICY_PATH.read_text(encoding="utf-8-sig"))
    old_rows = rows(OLD_LIBRARY); gan_rows = rows(OUT / "gan_raw_frequency_epsilon.csv")
    combined = []
    for row in old_rows:
        combined.append({"frequency_hz": row["frequency_hz"], "wavelength_nm": row["wavelength_nm"], "epsilon_real": row["epsilon_real"], "epsilon_imag": row["epsilon_imag"], "n_real": row["n_real"], "k_imag": row["k_imag"], "material_name": row["material_name"]})
    for row in gan_rows:
        combined.append({key: row[key] for key in ("frequency_hz","wavelength_nm","epsilon_real","epsilon_imag","n_real","k_imag") } | {"material_name": CANONICAL_ID})
    csv_write(NEW_LIBRARY, combined, ["frequency_hz","wavelength_nm","epsilon_real","epsilon_imag","n_real","k_imag","material_name"])
    updated = json.loads(json.dumps(current)); updated["material_policy_version"] = int(current.get("material_policy_version", 1)) + 1
    updated["materials"][CANONICAL_ID] = {"source_material_name": "GaN", "sample_count": 500, "material_class": "project_native_sampled_engineering_reference", "roles": ["tmm_gan_incident_medium","fdtd_gan_substrate","plane_wave_source_background","bloch_bfast_kx","sourcepower_reference_normalization","mdc_rcled_source_module_gan_background"], "limitations": ["optical_measurement_provenance_not_exposed","not_user_measured","high_loss_warning_retained","k450_approximately_0.084153","matched_reference_plane_deembedding_required_for_fdtd"]}
    updated["reference"]["native_sampled_csv"] = str(NEW_LIBRARY.relative_to(ROOT)).replace("\\","/")
    updated["reference"]["gan_native_m1"] = {"source_fsp": str(FSP), "source_fsp_sha256": EXPECTED_SHA, "object_name": "GaN", "material_name": "GaN", "raw_table_sha256": metadata["raw_table_sha256"], "source_commit": "752cc517c2c6dd2a53a27f7cc47f467635e37ff5", "promotion_date": "2026-07-13"}
    updated["legacy"]["gan_legacy"] = {"canonical_id": "APCD_GAN_LEGACY_N241", "n": 2.41, "k": 0.0, "status": "historical_only"}
    updated["legacy"]["gan_constant_fallback_allowed"] = False
    POLICY_PATH.write_text(json.dumps(updated, indent=2) + "\n", encoding="utf-8")
    policy = {"canonical_id": CANONICAL_ID, "policy_status": "active_engineering_default", "material_class": "project_native_sampled_engineering_reference", "source": updated["reference"]["gan_native_m1"], "registration": {"sampled_complex_epsilon": True, "interpolation_axis": "frequency_hz", "index_reconstruction": "physical_principal_square_root", "constant_fallback": "prohibited", "extrapolation": "forbidden"}, "deembedding_requirements": json.loads((ROOT / "outputs" / "mdc_gan_native_m1_extraction_audit_v1" / "fdtd_gan_deembedding_spec.json").read_text(encoding="utf-8")), "legacy_isolation": updated["legacy"]["gan_legacy"]}
    dump(OUT / "gan_material_policy.json", policy)
    dump(OUT / "material_library_update_summary.json", {"policy_path": str(POLICY_PATH), "new_library": str(NEW_LIBRARY), "policy_version": updated["material_policy_version"], "unchanged_native_material_ids": ["APCD_TIO2_NATIVE_M1","APCD_SIO2_NATIVE_M1"], "gan_sample_count": 500, "roundtrip": rt})


def validate_and_report() -> None:
    metadata=json.loads((OUT/"source_extraction_metadata.json").read_text(encoding="utf-8")); rt=json.loads((OUT/"roundtrip_state.json").read_text(encoding="utf-8")); policy=json.loads((OUT/"gan_material_policy.json").read_text(encoding="utf-8"))
    response=rows(OUT/"gan_complex_index_420_480.csv"); values={float(x["wavelength_nm"]):x for x in response}; config=json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    sys.path.insert(0, str(ROOT / "scripts")); import apcd_native_materials as native
    loader_nk = native.get_complex_index(CANONICAL_ID, np.asarray([float(x["wavelength_nm"]) for x in response]))
    source_nk = np.asarray([complex(float(x["n_real"]), float(x["k_imag"])) for x in response]); delta = np.abs(loader_nk-source_nk)
    loader = {"method": "raw_frequency_epsilon_linear_interpolation_then_physical_principal_sqrt", "query_reference": "source_FSP_getfdtdindex", "max_abs_nk_delta_vs_source_query": float(delta.max()), "rms_abs_nk_delta_vs_source_query": float(np.sqrt(np.mean(delta**2))), "critical": {str(w): {"loader_n": float(loader_nk[int(round((w-420.0)/0.1))].real), "loader_k": float(loader_nk[int(round((w-420.0)/0.1))].imag), "source_n": float(source_nk[int(round((w-420.0)/0.1))].real), "source_k": float(source_nk[int(round((w-420.0)/0.1))].imag), "abs_delta": float(delta[int(round((w-420.0)/0.1))])} for w in (420.0,448.0,450.0,453.0,480.0)}}
    dump(OUT / "tmm_loader_consistency.json", loader)
    checks={"source_sha_gate": metadata["source_gate"]["sha256_matches"], "raw_shape_500x2": metadata["raw_shape"]==[500,2], "query_601": len(response)==601, "roundtrip": rt["status"]=="promotion_roundtrip_pass", "roundtrip_finite": rt.get("finite_points")==601, "canonical_unique": list(config["materials"]).count(CANONICAL_ID)==1, "tio2_sio2_preserved": set(["APCD_TIO2_NATIVE_M1","APCD_SIO2_NATIVE_M1"]).issubset(config["materials"]), "no_constant_gan_fallback": config["legacy"].get("gan_constant_fallback_allowed") is False, "loader_finite_passive": bool(np.isfinite(loader_nk.real).all() and np.isfinite(loader_nk.imag).all() and np.all(loader_nk.imag >= 0)), "loss_retained": float(values[450.0]["k_imag"]) > 0 and loader_nk[int(round((450.0-420.0)/0.1))].imag > 0, "deembedding_present": "matched_reference_plane_deembedding_required_for_fdtd" in config["materials"][CANONICAL_ID]["limitations"], "no_solver_run": True, "no_project_save": True}
    checks = {key: bool(value) for key, value in checks.items()}
    if not all(checks.values()): raise RuntimeError(f"promotion validation failed: {checks}")
    manifest={"task":"PROMOTE_APCD_GAN_NATIVE_M1_FROM_PROJECT_FSP_V1","head":"752cc517c2c6dd2a53a27f7cc47f467635e37ff5","source":metadata["source_gate"],"raw_table_sha256":metadata["raw_table_sha256"],"query_response_sha256":metadata["query_response_sha256"],"sessions":[metadata["session"],rt["session"]],"outputs":sorted(x.name for x in OUT.iterdir())}
    dump(OUT/"validation.json",checks); dump(OUT/"manifest.json",manifest)
    report=["# APCD GaN Native-M1 promotion v1","",f"- Canonical material: `{CANONICAL_ID}` (`project_native_sampled_engineering_reference`).",f"- Source: `{FSP}`; SHA256 `{EXPECTED_SHA}`; object/material `GaN`/`GaN`.",f"- Raw table: 500x2 complex, SHA256 `{metadata['raw_table_sha256']}`. Query response: 601 points, SHA256 `{metadata['query_response_sha256']}`.",f"- 450 nm source query: n={values[450.0]['n_real']}, k={values[450.0]['k_imag']}; high-loss warning retained.",f"- Blank-session raw-table roundtrip: max |dn|={rt['max_abs_delta_n']:.3e}, max |dk|={rt['max_abs_delta_k']:.3e}.",f"- TMM loader uses original raw epsilon, not a fit of the 601-point query: max |n+ik difference| to the source query={loader['max_abs_nk_delta_vs_source_query']:.3e}; at 450 nm loader/source delta={loader['critical']['450.0']['abs_delta']:.3e}.","- Formal FDTD use requires matched reference-plane de-embedding: do not attribute source-to-stack GaN propagation loss to MDC loss; device/reference use the same GaN; bare GaN/Air remains an independent control.","- Legacy `APCD_GAN_LEGACY_N241` (n=2.41,k=0) is historical-only; no constant fallback is permitted.","- No solver run or source-FSP save/modification occurred.",""]
    REPORT.write_text("\n".join(report),encoding="utf-8")


def audit() -> None:
    required=["gan_raw_frequency_epsilon.csv","gan_complex_index_420_480.csv","gan_roundtrip_validation.csv","gan_material_policy.json","material_library_update_summary.json","validation.json","manifest.json"]
    missing=[x for x in required if not (OUT/x).is_file()]
    if missing: raise RuntimeError(f"missing promotion outputs: {missing}")
    validation=json.loads((OUT/"validation.json").read_text(encoding="utf-8"))
    if not all(validation.values()): raise RuntimeError(f"audit failed: {validation}")
    print("APCD_GAN_NATIVE_M1 promotion audit PASS")


def main() -> None:
    parser=argparse.ArgumentParser(); parser.add_argument("--audit-only",action="store_true"); parser.add_argument("--extract-and-register",action="store_true"); args=parser.parse_args()
    if args.audit_only == args.extract_and_register: parser.error("choose exactly one mode")
    if args.extract_and_register:
        metadata=source_extract(); rt=roundtrip(); update_library_and_policy(metadata,rt); validate_and_report()
    else: audit()


if __name__ == "__main__": main()
