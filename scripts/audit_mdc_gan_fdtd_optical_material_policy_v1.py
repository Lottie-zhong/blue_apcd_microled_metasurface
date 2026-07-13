#!/usr/bin/env python3
"""Audit only: determine whether a traceable dispersive GaN FDTD material exists."""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "mdc_gan_fdtd_optical_material_policy_audit_v1"
REPORT = ROOT / "reports" / "mdc_gan_fdtd_optical_material_policy_audit_v1.md"
FSP = Path(r"F:\wc_312\MDC_blue_oujizi_m\m_1.fsp")
WAVELENGTHS = (420, 448, 450, 453, 480)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader(); writer.writerows(rows)


def static_inventory() -> list[dict[str, Any]]:
    return [
        {"candidate_material_id": "N_GAN=2.41", "source_type": "legacy_TMM_constant", "source_path": "scripts/mdc_tmm_core.py:12", "source_sha256": "", "material_object_name": "", "geometry_objects": "", "model_type": "constant_index", "provenance": "existing TMM constant", "wavelength_range_nm": "not_dispersive", "sample_count": "", "interpolation_policy": "none", "extrapolation_policy": "not_applicable", "formal_fdtd": False, "reproducible": True, "status": "legacy_constant_index_reference", "reason": "not_allowed_for_formal_fdtd"},
        {"candidate_material_id": "GaN_n2p41", "source_type": "legacy_MDC_FDTD_script", "source_path": "scripts/stage_mdc1d1_native_m1_bare_fab_2d_smoke.py", "source_sha256": "", "material_object_name": "GaN_n2p41", "geometry_objects": "GaN substrate rectangle", "model_type": "constant_index", "provenance": "existing dipole-FDTD helper", "wavelength_range_nm": "not_dispersive", "sample_count": "", "interpolation_policy": "none", "extrapolation_policy": "not_applicable", "formal_fdtd": False, "reproducible": True, "status": "legacy_constant_index_reference", "reason": "not_allowed_for_formal_fdtd"},
        {"candidate_material_id": "GaN_450nm_n2p56_custom", "source_type": "legacy_RCLED_FDTD_script", "source_path": "scripts/stage_r1c4_rcled_c2_cav230_source_y_robustness.py:27,98", "source_sha256": "", "material_object_name": "GaN_450nm_n2p56_custom", "geometry_objects": "RCLED GaN cavity", "model_type": "constant_index", "provenance": "RCLED single-index helper", "wavelength_range_nm": "450 nm only / not dispersive", "sample_count": "", "interpolation_policy": "none", "extrapolation_policy": "not_applicable", "formal_fdtd": False, "reproducible": True, "status": "legacy_constant_index_reference", "reason": "not_allowed_for_formal_fdtd"},
        {"candidate_material_id": "FSP_PENDING_M1", "source_type": "targeted_FSP", "source_path": str(FSP), "source_sha256": digest(FSP) if FSP.is_file() else "", "source_bytes": FSP.stat().st_size if FSP.is_file() else "", "material_object_name": "", "geometry_objects": "", "model_type": "unresolved", "provenance": "explicitly cited Native-M1 source FSP", "wavelength_range_nm": "", "sample_count": "", "interpolation_policy": "", "extrapolation_policy": "", "formal_fdtd": False, "reproducible": FSP.is_file(), "status": "requires_readonly_lumapi_inspection", "reason": "static text cannot determine GaN object/material model"},
    ]


def delayed_lumapi() -> Any:
    path = Path(r"N:\Program Files\ANSYS Inc\v251\Lumerical\api\python\lumapi.py")
    spec = importlib.util.spec_from_file_location("lumapi", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load lumapi from {path}")
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def fsp_inspection() -> dict[str, Any]:
    """Read object/material metadata only; no solver methods or save methods exist here."""
    record: dict[str, Any] = {"fsp_path": str(FSP), "source_sha256": digest(FSP), "session_started": False, "session_closed": False, "error": "", "objects": [], "gan_materials": [], "spectral_samples": []}
    fdtd = None
    try:
        lumapi = delayed_lumapi()
        fdtd = lumapi.FDTD(hide=True); record["session_started"] = True
        fdtd.load(str(FSP))
        fdtd.selectall()
        objects = fdtd.getAllSelectedObjects()
        for obj in objects:
            try:
                name = str(obj["name"])
                material = str(obj["material"])
            except Exception:
                continue
            text = f"{name} {material}".lower()
            if "gan" in text or "gallium nitride" in text:
                record["objects"].append({"object_name": str(name), "material": str(material)})
        candidates = sorted({x["material"] for x in record["objects"] if x["material"]})
        for material in candidates:
            entry = {"material_object_name": material, "model_type": "unresolved", "sample_count": "", "interpolation_policy": "unavailable_from_readonly_query", "extrapolation_policy": "unavailable_from_readonly_query", "n_k": {}}
            try:
                frequencies = np.asarray([299792458.0 / (w * 1e-9) for w in WAVELENGTHS], dtype=float)
                values = fdtd.getfdtdindex(material, frequencies, float(frequencies.min()), float(frequencies.max()))
                flat = list(values)
                for wavelength, value in zip(WAVELENGTHS, flat):
                    entry["n_k"][str(wavelength)] = {"n": float(complex(value).real), "k": float(complex(value).imag)}
                entry["model_type"] = "index_query_only_model_type_unresolved"
                entry["coverage_420_480_nm"] = True
            except Exception as exc:
                entry["getindex_error"] = str(exc); entry["coverage_420_480_nm"] = False
            record["gan_materials"].append(entry)
    except Exception as exc:
        record["error"] = f"readonly inspection failed: {exc}"
    finally:
        if fdtd is not None:
            try:
                fdtd.close(); record["session_closed"] = True
            except Exception as exc:
                record["close_error"] = str(exc)
    return record


def decide(inventory: list[dict[str, Any]], inspection: dict[str, Any] | None) -> tuple[str, dict[str, Any] | None]:
    if not inspection or not inspection.get("gan_materials"):
        return "no_formal_candidate_found", None
    usable = [m for m in inspection["gan_materials"] if m.get("coverage_420_480_nm") and m.get("model_type") != "constant_index" and m.get("extrapolation_policy") != "unauthorized_extrapolation"]
    if len(usable) == 1:
        return "formal_candidate_incomplete", None
    if len(usable) > 1:
        return "multiple_conflicting_formal_candidates", None
    return "formal_candidate_incomplete", None


def material_candidates(inventory: list[dict[str, Any]], inspection: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not inspection or not inspection.get("gan_materials"):
        return inventory
    completed = [row for row in inventory if row["candidate_material_id"] != "FSP_PENDING_M1"]
    objects = inspection.get("objects", [])
    for material in inspection["gan_materials"]:
        material_name = material["material_object_name"]
        geometry = "; ".join(x["object_name"] for x in objects if x["material"] == material_name)
        completed.append({"candidate_material_id": f"FSP_GaN::{material_name}", "source_type": "targeted_FSP_readonly_metadata", "source_path": str(FSP), "source_sha256": inspection["source_sha256"], "source_bytes": FSP.stat().st_size, "material_object_name": material_name, "geometry_objects": geometry, "model_type": material["model_type"], "provenance": "object/material reference queried from targeted FSP", "wavelength_range_nm": "420-480 covered at five queried points" if material.get("coverage_420_480_nm") else "unconfirmed", "sample_count": material.get("sample_count", ""), "interpolation_policy": material.get("interpolation_policy", ""), "extrapolation_policy": material.get("extrapolation_policy", ""), "formal_fdtd": False, "reproducible": True, "status": "formal_candidate_incomplete", "reason": "single FSP candidate exists, but material-model metadata and deterministic blank-session registration are not established"})
    for row in completed:
        is_fsp = row["source_type"] == "targeted_FSP_readonly_metadata"
        row.setdefault("usage_stage", "targeted_material_audit" if is_fsp else "historical_reference")
        row.setdefault("existing_formal_fdtd", "unverified" if is_fsp else "no")
        row.setdefault("blank_session_registration", "unproven" if is_fsp else "not_applicable")
        row.setdefault("substrate_role_consistent", "yes; FSP object named GaN" if is_fsp else "not a formal FDTD substrate mapping")
        row.setdefault("missing_evidence", "material model/type, interpolation/extrapolation, deterministic registration" if is_fsp else "dispersive optical material provenance")
    return completed


def build(inspect: bool) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    inventory = static_inventory()
    previous = OUT / "gan_material_source_inventory.json"
    inspection = fsp_inspection() if inspect else (json.loads(previous.read_text(encoding="utf-8")).get("fsp_inspection") if previous.is_file() else None)
    candidates = material_candidates(inventory, inspection)
    status, policy = decide(candidates, inspection)
    fields = list(dict.fromkeys(key for row in candidates for key in row)); write_csv(OUT / "gan_material_candidates.csv", candidates, fields)
    samples: list[dict[str, Any]] = []
    if inspection:
        for material in inspection.get("gan_materials", []):
            for wavelength, nk in material.get("n_k", {}).items(): samples.append({"material_object_name": material["material_object_name"], "wavelength_nm": wavelength, "n": nk["n"], "k": nk["k"]})
    write_csv(OUT / "gan_material_spectral_samples.csv", samples, ["material_object_name", "wavelength_nm", "n", "k"])
    write_json(OUT / "gan_material_source_inventory.json", {"static_inventory": inventory, "fsp_inspection": inspection})
    write_json(OUT / "gan_material_policy_candidate.json", policy)
    validation = {"status": status, "legacy_n_2p41": "legacy_constant_index_reference; not_allowed_for_formal_fdtd", "fsp_inspected": bool(inspection), "solver_execution": False, "analysis_execution": False, "project_save": False, "formal_candidate": policy is not None, "phase_A_B_C": "blocked unless unique_formal_candidate_found"}
    write_json(OUT / "gan_material_validation.json", validation)
    write_json(OUT / "manifest.json", {"task": "MDC_GAN_FDTD_OPTICAL_MATERIAL_POLICY_AUDIT_V1", "fsp_target": str(FSP), "fsp_sha256": digest(FSP) if FSP.is_file() else "", "inspection_requested_this_invocation": inspect, "readonly_inspection_evidence_retained": bool(inspection), "outputs": sorted(p.name for p in OUT.iterdir())})
    fsp_lines = ["- No readable GaN material metadata was retained."]
    if inspection and inspection.get("gan_materials"):
        material = inspection["gan_materials"][0]
        points = ", ".join(f"{w} nm: n={v['n']:.6f}, k={v['k']:.6f}" for w, v in material.get("n_k", {}).items())
        delta = material["n_k"]["450"]["n"] - 2.41
        fsp_lines = [f"- Read-only FSP object/material mapping: `GaN` object -> `{material['material_object_name']}` material.", f"- Five queried points (not exported material data): {points}.", f"- n(450 nm)={material['n_k']['450']['n']:.6f}; delta versus historical n=2.41 is {delta:+.6f}.", "- 420-480 nm query coverage is PASS; material-model type, sample count, interpolation/extrapolation policy, and deterministic blank-session registration remain unresolved."]
    REPORT.write_text("\n".join(["# MDC GaN FDTD optical material policy audit v1", "", "## Search scope", "", "- Read-only repository search: configs, scripts, reports, frozen manifests/JSON/CSV, MDC/RCLED/dipole-FDTD helpers, and Native-M1 material helpers.", "- No static repository source established a formal dispersive GaN FDTD registration; the traceable values found were legacy constants.", "", "## Decision", "", f"- Status: `{status}`.", "- `is_nominal` or a single FSP material name is insufficient to freeze a formal FDTD GaN mapping.", "- `gan_material_policy_candidate.json` is `null`: only a unique formal candidate may produce a proposed-not-frozen policy record.", "- Legacy `n=2.41` is `legacy_constant_index_reference` and `not_allowed_for_formal_fdtd`.", "- No candidate is written into plane-wave global configuration.", "", "## Sources", "", "- `scripts/mdc_tmm_core.py:12`: legacy constant n=2.41.", "- Existing MDC/RCLED helpers use constant custom GaN names; they are not dispersive formal candidates.", f"- Targeted FSP: `{FSP}`; SHA256 and byte size recorded in candidate CSV.", "", "## Read-only FSP inspection", "", *fsp_lines, "", "## Legacy comparison boundary", "", "- The n(450) difference is recorded only as a data comparison. It can affect sourcepower normalization, Bloch kx, Fresnel boundaries, and TMM-FDTD disagreement; this audit neither changes TMM nor asserts equivalence.", "", "## Inspection safety", "", f"- Read-only inspection evidence retained: `{bool(inspection)}`; this invocation started a session: `{inspect}`.", "- Solver execution, analysis execution, and project save: false/false/false.", "", "## Impact", "", "- Phase A/B/C remain blocked unless a future audit returns `unique_formal_candidate_found`.", "- Minimal next step: obtain an approved, versioned material registration/provenance record for this FSP's `GaN` material; do not fit or import external n,k data.", "" ]), encoding="utf-8")


def audit() -> None:
    required = ["gan_material_candidates.csv", "gan_material_spectral_samples.csv", "gan_material_source_inventory.json", "gan_material_policy_candidate.json", "gan_material_validation.json", "manifest.json"]
    if any(not (OUT / n).is_file() for n in required) or not REPORT.is_file(): raise RuntimeError("audit outputs missing")
    validation = json.loads((OUT / "gan_material_validation.json").read_text(encoding="utf-8"))
    if validation["solver_execution"] or validation["analysis_execution"] or validation["project_save"]: raise RuntimeError("unsafe action recorded")
    print(f"GaN policy audit PASS: status={validation['status']} inspect_fsp={validation['fsp_inspected']} solver_execution=false")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--audit-only", action="store_true"); parser.add_argument("--inspect-fsp-materials", action="store_true")
    args = parser.parse_args()
    if args.audit_only: audit()
    else: build(args.inspect_fsp_materials); audit()
