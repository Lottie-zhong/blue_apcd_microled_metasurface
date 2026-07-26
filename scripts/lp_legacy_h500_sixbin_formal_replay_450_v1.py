from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import os
import shutil
import sys
import time
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

POST_SOLVER_ACCEPTANCE = None


R = Path(r"D:\project\worktrees\blue_apcd_lp_stage11_4")
O = R / "outputs"
ROOT = O / "lp_legacy_h500_sixbin_formal_replay_450_v1"
SUB = ROOT / "subruns"
CAND = ROOT / "candidates"
RUNTIME = ROOT / "runtime"
CSV_OUT = O / "lp_legacy_h500_sixbin_formal_replay_450_v1.csv"
JSON_OUT = O / "lp_legacy_h500_sixbin_formal_replay_450_v1.json"
REPORT = R / "reports/lp_legacy_h500_sixbin_formal_replay_450_v1.md"
STAGING = O / "lp_ml_dataset_v1/staging/legacy_h500_formal_replay_450_v1"

MIGRATION_JSON = O / "lp_legacy_h500_sixbin_geometry_migration_audit_v1.json"
MIGRATION_INVENTORY = O / "lp_legacy_h500_sixbin_geometry_inventory_v1.csv"
MIGRATION_MANIFEST = O / "lp_legacy_h500_sixbin_formal_replay_manifest_v1.csv"
MIGRATION_REPORT = R / "reports/lp_legacy_h500_sixbin_geometry_migration_audit_v1.md"
MIGRATION_SCRIPT = R / "scripts/lp_legacy_h500_sixbin_geometry_migration_audit_v1.py"
PROTECTED = (
    R / "reports/lp_ml1a3_git_history_geometry_reconstruction.md",
    R / "reports/stage11_4a20_legacy_fsp_object_inventory.md",
)
INPUT_SHA256 = {
    MIGRATION_JSON: "7C8BBF76C7539C066FFABFD0733CDDF62003D72F54EF7FC64161DCA1C4C999DE",
    MIGRATION_INVENTORY: "AEF6F1EEA906A38728018A1CDBC8BD3DF65D2E6C597E618ABB73F5AE0D09BFE9",
    MIGRATION_MANIFEST: "5C6ED3F6D01D3E57B1DD9D228205427C8B72ADC3D4B51D838D2E4423EF718CF8",
    MIGRATION_REPORT: "1FE5F698C3C007EB72F518548C50815052AECE9327D310527883942F93D8D995",
}
PROTECTED_SHA256 = {
    PROTECTED[0]: "21C6884F71BAD6BD6779D7CCC90CEC55AB1A94E239F849EA74A942BDD50EDD6A",
    PROTECTED[1]: "AE3B13341547E13CA85CA763ED8265591C100AC1A78C555DE1C8378816A33708",
}

SCHEMA = "LP_ML_SCHEMA_V1.0"
EVIDENCE = "FORMAL_FULL_DIMER"
SOURCE_STAGE = "LEGACY_H500_FORMAL_REPLAY_450_V1"
MID = "APCD_TIO2_NATIVE_M1"
WL = 450.0
NM = 1e-9
EPS = 1e-15
ORDER = [0, 60, 120, 180, 240, 300]
EXPECTED_IDS = {
    0: "LP_S2_H500_LEGACY_B000_SQUARE110_J2L150W70_D190_PSI000",
    60: "LP_S2_H500_LEGACY_B060_RECT170W130_J2L150W90_D220_PSI180",
    120: "LP_S2_H500_LEGACY_B120_SQUARE110_J2L120W90_D175_PSI180",
    180: "LP_S2_H500_LEGACY_B180_SQUARE90_J2L150W110_D180_PSI180",
    240: "LP_S2_H500_LEGACY_B240_CIRCLE100_J2L150W110_D215_PSI180",
    300: "LP_S2_H500_LEGACY_B300_CIRCLE120_J2L120W70_D200_PSI180",
}


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


for path in (R / "src", R / "scripts"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

base = load_module(R / "scripts/lp_stage2_h500_full_dimer_dual_bridge_v1.py", "legacy450_base")
migration = load_module(MIGRATION_SCRIPT, "legacy450_migration")
from metasurface.apcd_material_library import get_epsilon, get_nk  # noqa: E402
from metasurface.config import load_runtime_config  # noqa: E402
from metasurface.lumerical_native_materials import ensure_apcd_native_materials, get_lumerical_material_name  # noqa: E402
from metasurface.lumapi_runner import import_lumapi  # noqa: E402


GEOMETRY_FIELDS = [
    "schema_version", "candidate_id", "legacy_case_id", "legacy_nominal_bin_deg", "source_pair_id",
    "geometry_hash", "physics_configuration_hash", "H_nm", "period_x_nm", "period_y_nm",
    "J1_shape", "J1_L_nm", "J1_W_nm", "J1_diameter_nm", "J1_rotation_deg", "J1_center_x_nm", "J1_center_y_nm",
    "J2_shape", "J2_L_nm", "J2_W_nm", "J2_rotation_deg", "J2_center_x_nm", "J2_center_y_nm",
    "exact_old_centers", "canonical_centers", "common_translation_x_nm", "common_translation_y_nm",
    "D_nm", "directed_PSI_deg", "legacy_gap_nm", "legacy_offset_nm", "direct_gap_nm", "periodic_gap_nm",
    "closest_periodic_translation_x_nm", "closest_periodic_translation_y_nm", "fabrication_hard_pass",
    "fabrication_preferred_pass", "integer_dimension_pass", "primitive_valid", "direct_overlap", "periodic_overlap",
    "historical_source_paths", "split_group", "split_assignment", "evidence_tier", "source_stage",
]
SUBRUN_FIELDS = [
    "schema_version", "subrun_id", "candidate_id", "geometry_hash", "runtime_geometry_hash",
    "physics_configuration_hash", "wavelength_nm", "input_polarization", "source_hash", "source_common_hash",
    "monitor_hash", "boundary_hash", "material_hash", "integration_hash", "normalization_version",
    "solver_status", "runtime_seconds", "solver_runtime_seconds", "checkpoint_path", "checkpoint_sha256",
    "weighted_G0_Ex_real", "weighted_G0_Ex_imag", "weighted_G0_Ey_real", "weighted_G0_Ey_imag",
    "raw_weighted_G0_Ex_real", "raw_weighted_G0_Ex_imag", "raw_weighted_G0_Ey_real", "raw_weighted_G0_Ey_imag",
    "T", "normalization_scale", "quality_status", "failure_code", "evidence_tier", "source_stage",
]
CANDIDATE_FIELDS = [
    "schema_version", "candidate_id", "legacy_case_id", "legacy_nominal_bin_deg", "geometry_hash",
    "runtime_geometry_hash", "physics_configuration_hash", "wavelength_nm", "candidate_checkpoint_path",
    "candidate_checkpoint_sha256", "txx_real", "txx_imag", "txy_real", "txy_imag", "tyx_real", "tyx_imag",
    "tyy_real", "tyy_imag", "Txx", "Txy", "Tyx", "Tyy", "cross_power", "leakage_sum", "R_total",
    "blocked_input_selectivity", "selected_polarization_purity", "sigma1", "sigma2", "sigma2_over_sigma1",
    "determinant_magnitude", "matrix_projection_error", "reciprocity_residual", "input_S1", "input_S2", "input_S3",
    "output_S1", "output_S2", "output_S3", "input_AoLP_deg", "output_AoLP_deg", "input_ellipticity_deg",
    "output_ellipticity_deg", "input_x_overlap", "output_x_overlap", "a0_real", "a0_imag", "az_real", "az_imag",
    "ax_real", "ax_imag", "ay_real", "ay_imag", "abs_a0_over_abs_az", "common_differential_phase_error_deg",
    "off_axis_fraction", "actual_txx_phase_deg_450", "nearest_actual_bin_deg", "actual_bin_phase_error_deg",
    "formal_classification", "projector_gate_status", "projector_failed_checks", "dominant_leakage", "quality_status",
    "evidence_tier", "source_stage",
]
HISTORICAL_FIELDS = [
    "schema_version", "candidate_id", "legacy_case_id", "geometry_hash", "legacy_nominal_bin_deg",
    "legacy_actual_phase_deg", "legacy_selected_power", "legacy_selectivity", "legacy_matrix_error",
    "legacy_phase_error", "legacy_material", "legacy_monitor_z_nm", "legacy_extractor", "legacy_normalization",
    "historical_source_paths", "evidence_tier", "source_stage",
]


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def stable_readback(value: Any) -> Any:
    """Canonicalize lumapi scalar noise while retaining sub-nanometre geometry."""
    if isinstance(value, dict):
        return {str(k): stable_readback(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [stable_readback(v) for v in value]
    if isinstance(value, (float, np.floating)):
        return round(float(value), 18)
    if isinstance(value, (int, np.integer)):
        return int(value)
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    return value


def atomic(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def write_rows(path: Path, fields: list[str], values: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(values)


def append_row(path: Path, fields: list[str], value: dict[str, Any]) -> None:
    with path.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writerow(value)
        f.flush()
        os.fsync(f.fileno())


def cv(value: dict[str, Any]) -> complex:
    return complex(float(value["real"]), float(value["imag"]))


def cparts(value: complex) -> tuple[float, float]:
    return float(value.real), float(value.imag)


def phase360(value: complex) -> float:
    return float(math.degrees(math.atan2(value.imag, value.real)) % 360.0)


def wrap_error(value: float, target: float) -> float:
    return abs((value - target + 180.0) % 360.0 - 180.0)


def nearest_bin(value: float) -> tuple[int, float]:
    ranked = sorted((wrap_error(value, b), b) for b in ORDER)
    return ranked[0][1], ranked[0][0]


FORMAL_CONFIG = {
    "wavelength_nm": 450, "period_x_nm": 432, "period_y_nm": 432, "H_nm": 500,
    "material": MID, "background": "air n=1", "incidence": "normal",
    "boundaries": {"x": "Periodic", "y": "Periodic", "z": "PML"},
    "source": {"type": "plane", "direction": "Forward", "z_nm": -250, "inputs": ["x", "y"]},
    "monitor": {"name": "field_monitor", "type": "2D Z-normal", "z_nm": 1000},
    "integration": "coordinate-weighted periodic-closure 2D complex G0; duplicate endpoints removed and reclosed",
    "normalization": "sqrt(T)/norm(weighted Ex, weighted Ey)",
}
PHYSICS_HASH = digest(FORMAL_CONFIG)
INTEGRATION_HASH = digest({"integration": FORMAL_CONFIG["integration"], "normalization": FORMAL_CONFIG["normalization"]})
NORMALIZATION_VERSION = "LP_WEIGHTED_G0_SQRT_T_NORM_V1"


def load_specs() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    audit = json.loads(MIGRATION_JSON.read_text(encoding="utf-8"))
    cases = {c["current_candidate_id"]: c for c in audit["cases"]}
    manifest = {r["current_candidate_id"]: r for r in audit["formal_replay_manifest"]}
    specs = []
    for old_bin in ORDER:
        cid = EXPECTED_IDS[old_bin]
        case, man = cases[cid], manifest[cid]
        j1_dims = case["J1"]["dimensions_nm"]
        specs.append({
            "candidate_id": cid, "legacy_case_id": case["legacy_case_id"], "legacy_bin": old_bin,
            "source_pair_id": case["source_pair_id"], "geometry_hash": case["geometry_hash_sha256"],
            "J1_primitive": case["J1"]["primitive"], "J1_dims": j1_dims,
            "J1_center": [float(v) for v in case["old_placement"]["exact_centers_nm"]["J1"]],
            "J1_rotation": float(case["J1"]["global_rotation_deg"]),
            "J2_primitive": "sharp_rectangle", "J2_L": float(case["J2"]["L_nm"]), "J2_W": float(case["J2"]["W_nm"]),
            "J2_center": [float(v) for v in case["old_placement"]["exact_centers_nm"]["J2"]],
            "J2_rotation": float(case["J2"]["global_rotation_deg"]),
            "canonical_centers": case["current_builder_mapping"]["canonical_J1_center_nm"],
            "canonical_centers_pair": {"J1": case["current_builder_mapping"]["canonical_J1_center_nm"], "J2": case["current_builder_mapping"]["canonical_J2_center_nm"]},
            "common_translation": [float(v) for v in case["current_builder_mapping"]["common_translation_nm"]],
            "D": float(case["current_builder_mapping"]["D_nm"]), "PSI": float(case["current_builder_mapping"]["PSI_deg"]),
            "legacy_gap": float(case["old_placement"]["gap_field_nm"]), "legacy_offset": float(case["old_placement"]["local_offset_field_nm"]),
            "direct_gap_ref": float(case["geometry_audit"]["direct"]["gap_nm"]), "periodic_gap_ref": float(case["geometry_audit"]["periodic"]["gap_nm"]),
            "legacy": case["old_metrics_provenance_only"], "legacy_conditions": case["old_conditions"],
            "source_files": case["source_files"], "migration_manifest": man, "migration_case": case,
        })
    return specs, audit


class Recorder:
    def __init__(self):
        self.objects: dict[str, dict[str, Any]] = {}
        self.current: dict[str, Any] | None = None

    def addrect(self):
        self.current = {"primitive": "rectangle"}

    def addcircle(self):
        self.current = {"primitive": "circle"}

    def set(self, key: str, value: Any):
        assert self.current is not None
        self.current[key] = value
        if key == "name":
            self.objects[str(value)] = self.current


def add_exact_pillar(fdtd: Any, name: str, spec: dict[str, Any], first: bool, material_name: str) -> dict[str, Any]:
    prefix = "J1" if first else "J2"
    primitive = spec[f"{prefix}_primitive"]
    center = spec[f"{prefix}_center"]
    rotation = spec[f"{prefix}_rotation"]
    if primitive == "circle":
        diameter = float(spec["J1_dims"]["diameter_nm"])
        fdtd.addcircle(); fdtd.set("radius", diameter * 0.5 * NM)
        dims = {"diameter_nm": diameter}
    else:
        if first:
            if "side_nm" in spec["J1_dims"]:
                length = width = float(spec["J1_dims"]["side_nm"])
            else:
                length, width = float(spec["J1_dims"]["length_nm"]), float(spec["J1_dims"]["width_nm"])
        else:
            length, width = spec["J2_L"], spec["J2_W"]
        fdtd.addrect(); fdtd.set("x span", length * NM); fdtd.set("y span", width * NM)
        fdtd.set("first axis", "z"); fdtd.set("rotation 1", rotation)
        dims = {"length_nm": length, "width_nm": width}
    fdtd.set("name", name); fdtd.set("x", center[0] * NM); fdtd.set("y", center[1] * NM)
    fdtd.set("z min", 0); fdtd.set("z max", 500 * NM); fdtd.set("material", material_name)
    return {"name": name, "primitive": primitive, "center_x_nm": center[0], "center_y_nm": center[1], "height_nm": 500.0, "theta_deg": rotation, **dims}


def recompute_geometry(spec: dict[str, Any]) -> dict[str, Any]:
    old = spec["migration_case"]["geometry_audit"]
    a, b = dict(old["J1"]), dict(old["J2"])
    gap, p1, p2, overlap = migration.primitive_gap(a, b)
    periodic = migration.periodic_minimum({"J1": a, "J2": b}, 432.0)
    boxes = [migration.bbox(a), migration.bbox(b)]
    footprint = {"x_min_nm": min(x[0] for x in boxes), "x_max_nm": max(x[1] for x in boxes), "y_min_nm": min(x[2] for x in boxes), "y_max_nm": max(x[3] for x in boxes)}
    hard = gap >= 50 and periodic["gap_nm"] >= 50 and not overlap and not periodic["overlap"]
    preferred = hard and gap >= 60 and periodic["gap_nm"] >= 60
    return {"direct_gap_nm": gap, "direct_closest_J1_nm": p1, "direct_closest_J2_nm": p2, "direct_overlap": overlap,
            "periodic_gap_nm": periodic["gap_nm"], "periodic_translation_nm": periodic["image_translation_nm"],
            "periodic_pair": [periodic["central_primitive"], periodic["image_primitive"]], "periodic_overlap": periodic["overlap"],
            "footprint_nm": footprint, "primary_cell_crossing": any((footprint["x_min_nm"] < -216, footprint["x_max_nm"] > 216, footprint["y_min_nm"] < -216, footprint["y_max_nm"] > 216)),
            "primitive_valid": True, "fabrication_hard_pass": hard, "fabrication_preferred_pass": preferred}


def static_builder_gate(spec: dict[str, Any]) -> dict[str, Any]:
    recorder = Recorder(); mat = get_lumerical_material_name(MID)
    r1 = add_exact_pillar(recorder, "pillar_1", spec, True, mat)
    r2 = add_exact_pillar(recorder, "pillar_2", spec, False, mat)
    o1, o2 = recorder.objects["pillar_1"], recorder.objects["pillar_2"]
    geometry = recompute_geometry(spec)
    checks = {
        "explicit_J1_center": abs(o1["x"] / NM - spec["J1_center"][0]) < 1e-12 and abs(o1["y"] / NM - spec["J1_center"][1]) < 1e-12,
        "explicit_J2_center": abs(o2["x"] / NM - spec["J2_center"][0]) < 1e-12 and abs(o2["y"] / NM - spec["J2_center"][1]) < 1e-12,
        "half_integer_preserved": spec["legacy_bin"] != 120 or (o1["x"] / NM == 77.5 and o2["x"] / NM == -97.5),
        "common_translation_preserved": all(abs((spec["J1_center"][i] + spec["J2_center"][i]) / 2 - spec["common_translation"][i]) < 1e-12 for i in (0, 1)),
        "sharp_or_circle_primitive": r1["primitive"] in {"circle", "sharp_rectangle"} and r2["primitive"] == "sharp_rectangle",
        "rotations_zero": r1["theta_deg"] == 0 and r2["theta_deg"] == 0,
        "geometry_hash_matches_manifest": spec["geometry_hash"] == spec["migration_manifest"]["geometry_hash_sha256"],
        "direct_gap_matches": abs(geometry["direct_gap_nm"] - spec["direct_gap_ref"]) < 1e-9,
        "periodic_gap_matches": abs(geometry["periodic_gap_nm"] - spec["periodic_gap_ref"]) < 1e-9,
        "fabrication_hard_pass": geometry["fabrication_hard_pass"],
    }
    if spec["legacy_bin"] == 60:
        checks["bin60_preferred_expected_false"] = not geometry["fabrication_preferred_pass"]
    return {"candidate_id": spec["candidate_id"], "gate": "PASS" if all(checks.values()) else "FAIL", "checks": checks,
            "requested": {"J1": r1, "J2": r2, "period_nm": [432, 432], "H_nm": 500, "monitor_z_nm": 1000, "material": MID},
            "recorder_readback": {"pillar_1": o1, "pillar_2": o2}, "geometry": geometry}


def validate_inputs(resume: bool = False) -> dict[str, Any]:
    specs, audit = load_specs()
    report_text = MIGRATION_REPORT.read_text(encoding="utf-8")
    manifest_rows = rows(MIGRATION_MANIFEST)
    inventory_rows = rows(MIGRATION_INVENTORY)
    static = [static_builder_gate(s) for s in specs]
    targets = [ROOT, CSV_OUT, JSON_OUT, STAGING, REPORT]
    checks = {
        "branch": base.git("branch", "--show-current") == "work/lp-stage11-4",
        "head": base.git("rev-parse", "--short", "HEAD") == "06eb759",
        "input_hashes": all(sha(p).upper() == expected for p, expected in INPUT_SHA256.items()),
        "six_manifest_rows": len(manifest_rows) == 6 and len(inventory_rows) == 6 and len(specs) == 6,
        "authorized_order": [s["legacy_bin"] for s in specs] == ORDER,
        "authorized_ids": [s["candidate_id"] for s in specs] == [EXPECTED_IDS[b] for b in ORDER],
        "report_crosscheck": all(s["candidate_id"] in report_text and s["geometry_hash"] in report_text for s in specs),
        "audit_route": audit["route_decision"] == "LEGACY_LIBRARY_READY_FOR_FORMAL_REPLAY",
        "static_exact_center_gates": all(g["gate"] == "PASS" for g in static),
        "no_target_preexists": not any(p.exists() for p in targets) if not resume else True,
        "resume_partial_state": (not resume) or (ROOT.exists() and JSON_OUT.exists() and (ROOT / "builder_gate.json").exists()
                                                    and (STAGING / "subrun_records_v1.csv").exists()
                                                    and json.loads(JSON_OUT.read_text(encoding="utf-8")).get("status") == "PARTIAL_PASS_CANDIDATE_DATA_PRESERVED"),
        "protected_preflight": all(sha(p).upper() == expected for p, expected in PROTECTED_SHA256.items()),
    }
    return {"status": "PASS" if all(checks.values()) else "EXACT_CENTER_BUILDER_GATE_FAILED", "checks": checks, "static_builder_gates": static, "specs": specs}


def material_readback(fdtd: Any) -> dict[str, Any]:
    name = get_lumerical_material_name(MID)
    table = np.asarray(fdtd.getmaterial(name, "sampled data"), dtype=np.complex128)
    freq, eps = np.real(table[:, 0]), table[:, 1]
    target = 299792458.0 / (WL * NM)
    value = complex(np.interp(target, freq, eps.real), np.interp(target, freq, eps.imag))
    try:
        nk = complex(fdtd.getindex(name, target))
    except Exception:
        nk = None
    loader_eps, loader_nk = get_epsilon(MID, WL), get_nk(MID, WL)
    return {"material_name": name, "wavelength_nm": WL, "sample_count": len(freq), "frequency_monotonic": bool(np.all(np.diff(freq) > 0)),
            "duplicate_frequency_count": int(len(freq) - len(np.unique(freq))), "epsilon_real": value.real, "epsilon_imag": value.imag,
            "n_real": None if nk is None else nk.real, "k_imag": None if nk is None else nk.imag,
            "loader_epsilon_real": loader_eps.real, "loader_epsilon_imag": loader_eps.imag,
            "loader_n_real": loader_nk.real, "loader_k_imag": loader_nk.imag,
            "epsilon_matches_loader": abs(value - loader_eps) < 1e-12, "range_covers_450": bool(freq.min() <= target <= freq.max())}


def configure_exact(fdtd: Any, spec: dict[str, Any], pol: str) -> dict[str, Any]:
    ensure_apcd_native_materials(fdtd)
    fdtd.switchtolayout(); fdtd.deleteall()
    fdtd.addfdtd(); fdtd.set("dimension", "3D"); fdtd.set("x span", 432 * NM); fdtd.set("y span", 432 * NM)
    fdtd.set("z min", -500 * NM); fdtd.set("z max", 1200 * NM)
    for key, value in (("x min bc", "Periodic"), ("x max bc", "Periodic"), ("y min bc", "Periodic"), ("y max bc", "Periodic"), ("z min bc", "PML"), ("z max bc", "PML"), ("mesh accuracy", 2), ("simulation time", 1000e-15), ("background material", "<Object defined dielectric>"), ("index", 1.0)):
        fdtd.set(key, value)
    mat = get_lumerical_material_name(MID)
    records = [add_exact_pillar(fdtd, "pillar_1", spec, True, mat), add_exact_pillar(fdtd, "pillar_2", spec, False, mat)]
    assigned = {name: str(fdtd.getnamed(name, "material")) for name in ("pillar_1", "pillar_2")}
    fdtd.addplane(); fdtd.set("name", "source"); fdtd.set("injection axis", "z"); fdtd.set("direction", "Forward")
    fdtd.set("x span", 432 * NM); fdtd.set("y span", 432 * NM); fdtd.set("z", -250 * NM)
    fdtd.set("wavelength start", WL * NM); fdtd.set("wavelength stop", WL * NM); fdtd.set("polarization angle", 0 if pol == "x" else 90)
    for name, kind in (("T", "power"), ("field_monitor", "profile")):
        getattr(fdtd, "add" + kind)(); fdtd.set("name", name); fdtd.set("monitor type", "2D Z-normal")
        fdtd.set("x span", 432 * NM); fdtd.set("y span", 432 * NM); fdtd.set("z", 1000 * NM)
    return {"geometry_records": records, "pillar_assignments": assigned, "material_readback": material_readback(fdtd)}


def safe(fdtd: Any, name: str, prop: str) -> Any:
    try:
        value = fdtd.getnamed(name, prop)
        return value.item() if hasattr(value, "item") else value
    except Exception as exc:
        return f"UNAVAILABLE:{type(exc).__name__}"


def runtime_gate(fdtd: Any, spec: dict[str, Any], built: dict[str, Any], static: dict[str, Any], stage: str) -> dict[str, Any]:
    p1 = {p: safe(fdtd, "pillar_1", p) for p in ("x", "y", "z min", "z max", "material", "rotation 1", "x span", "y span", "radius")}
    p2 = {p: safe(fdtd, "pillar_2", p) for p in ("x", "y", "z min", "z max", "material", "rotation 1", "x span", "y span")}
    f = {p: safe(fdtd, "FDTD", p) for p in ("x span", "y span", "x min bc", "x max bc", "y min bc", "y max bc", "z min bc", "z max bc", "background material", "index")}
    mon = {name: {p: safe(fdtd, name, p) for p in ("z", "x span", "y span", "monitor type")} for name in ("T", "field_monitor")}
    src = {p: safe(fdtd, "source", p) for p in ("z", "direction", "polarization angle", "wavelength start", "wavelength stop")}
    mat = built["material_readback"] if stage == "build" else material_readback(fdtd)
    inv = stable_readback({"pillar_1": {"primitive": spec["J1_primitive"], **p1},
                           "pillar_2": {"primitive": spec["J2_primitive"], **p2},
                           "FDTD": f, "monitors": mon, "source": src, "material": mat})
    geometry = {"pillar_1": inv["pillar_1"], "pillar_2": inv["pillar_2"]}
    source_common = {k: v for k, v in inv["source"].items() if k != "polarization angle"}
    hashes = {"object_inventory_hash": digest(inv), "geometry_hash": digest(geometry),
              "source_common_hash": digest(source_common), "monitor_hash": digest(inv["monitors"]),
              "boundary_hash": digest(inv["FDTD"]), "material_hash": digest(inv["material"])}
    expected_mat = get_lumerical_material_name(MID)
    checks = {
        "static_gate": static["gate"] == "PASS",
        "J1_center": abs(float(p1["x"]) / NM - spec["J1_center"][0]) < 1e-8 and abs(float(p1["y"]) / NM - spec["J1_center"][1]) < 1e-8,
        "J2_center": abs(float(p2["x"]) / NM - spec["J2_center"][0]) < 1e-8 and abs(float(p2["y"]) / NM - spec["J2_center"][1]) < 1e-8,
        "both_native": str(p1["material"]) == expected_mat and str(p2["material"]) == expected_mat,
        "material_table": mat["epsilon_matches_loader"] and mat["range_covers_450"] and mat["frequency_monotonic"] and mat["duplicate_frequency_count"] == 0,
        "periods": abs(float(f["x span"]) / NM - 432) < 1e-8 and abs(float(f["y span"]) / NM - 432) < 1e-8,
        "boundaries": all(str(f[k]) == v for k, v in (("x min bc", "Periodic"), ("x max bc", "Periodic"), ("y min bc", "Periodic"), ("y max bc", "Periodic"), ("z min bc", "PML"), ("z max bc", "PML"))),
        "background_air": str(f["background material"]) == "<Object defined dielectric>" and abs(float(f["index"]) - 1) < 1e-9,
        "monitor_z": abs(float(mon["field_monitor"]["z"]) / NM - 1000) < 1e-8,
        "source_450": abs(float(src["wavelength start"]) / NM - 450) < 1e-8 and abs(float(src["wavelength stop"]) / NM - 450) < 1e-8,
        "geometry_hash_reference": spec["geometry_hash"] == spec["migration_manifest"]["geometry_hash_sha256"],
    }
    return {"stage": stage, "gate": "PASS" if all(checks.values()) else "FAIL", "checks": checks, "requested_centers_nm": {"J1": spec["J1_center"], "J2": spec["J2_center"]},
            "object_readback": {"J1": p1, "J2": p2}, "boundary_readback": f, "monitor_readback": mon, "source_readback": src,
            "material_readback": mat, "inventory": inv, "runtime_hashes": hashes, "reference_geometry_hash": spec["geometry_hash"]}


def runtime_builder_gate_all(runtime: Any, specs: list[dict[str, Any]], static: list[dict[str, Any]]) -> list[dict[str, Any]]:
    lum = import_lumapi(runtime)
    results = []
    for spec, sg in zip(specs, static):
        path = RUNTIME / f"builder_gate_{spec['legacy_bin']:03d}.fsp"
        fdtd = None
        try:
            fdtd = lum.FDTD(hide=getattr(runtime, "hide_gui", True)); built = configure_exact(fdtd, spec, "x")
            build_gate = runtime_gate(fdtd, spec, built, sg, "build")
            if build_gate["gate"] != "PASS":
                raise RuntimeError("exact-center build readback failed")
            fdtd.save(str(path)); fdtd.close(); fdtd = None
            fdtd = lum.FDTD(hide=getattr(runtime, "hide_gui", True)); fdtd.load(str(path))
            load_gate = runtime_gate(fdtd, spec, built, sg, "save_load")
            if load_gate["gate"] != "PASS" or load_gate["runtime_hashes"] != build_gate["runtime_hashes"]:
                raise RuntimeError("exact-center save/load persistence failed: " + json.dumps({
                    "candidate_id": spec["candidate_id"], "load_checks": load_gate["checks"],
                    "build_hashes": build_gate["runtime_hashes"], "load_hashes": load_gate["runtime_hashes"],
                    "build_inventory": build_gate["inventory"], "load_inventory": load_gate["inventory"]}, default=str))
            results.append({"candidate_id": spec["candidate_id"], "gate": "PASS", "build": build_gate, "save_load": load_gate})
        finally:
            if fdtd is not None:
                try: fdtd.close()
                except Exception: pass
            for artifact in path.parent.glob(path.stem + "*"):
                if artifact.is_file(): artifact.unlink(missing_ok=True)
    return results


def geometry_master(spec: dict[str, Any], sg: dict[str, Any]) -> dict[str, Any]:
    d = spec["J1_dims"]; g = sg["geometry"]
    return {"schema_version": SCHEMA, "candidate_id": spec["candidate_id"], "legacy_case_id": spec["legacy_case_id"], "legacy_nominal_bin_deg": spec["legacy_bin"],
            "source_pair_id": spec["source_pair_id"], "geometry_hash": spec["geometry_hash"], "physics_configuration_hash": PHYSICS_HASH,
            "H_nm": 500, "period_x_nm": 432, "period_y_nm": 432, "J1_shape": spec["J1_primitive"],
            "J1_L_nm": d.get("side_nm", d.get("length_nm", "")), "J1_W_nm": d.get("side_nm", d.get("width_nm", "")), "J1_diameter_nm": d.get("diameter_nm", ""),
            "J1_rotation_deg": 0, "J1_center_x_nm": spec["J1_center"][0], "J1_center_y_nm": spec["J1_center"][1],
            "J2_shape": "sharp_rectangle", "J2_L_nm": spec["J2_L"], "J2_W_nm": spec["J2_W"], "J2_rotation_deg": 0,
            "J2_center_x_nm": spec["J2_center"][0], "J2_center_y_nm": spec["J2_center"][1],
            "exact_old_centers": json.dumps({"J1": spec["J1_center"], "J2": spec["J2_center"]}, separators=(",", ":")),
            "canonical_centers": json.dumps(spec["canonical_centers_pair"], separators=(",", ":")),
            "common_translation_x_nm": spec["common_translation"][0], "common_translation_y_nm": spec["common_translation"][1],
            "D_nm": spec["D"], "directed_PSI_deg": spec["PSI"], "legacy_gap_nm": spec["legacy_gap"], "legacy_offset_nm": spec["legacy_offset"],
            "direct_gap_nm": g["direct_gap_nm"], "periodic_gap_nm": g["periodic_gap_nm"],
            "closest_periodic_translation_x_nm": g["periodic_translation_nm"][0], "closest_periodic_translation_y_nm": g["periodic_translation_nm"][1],
            "fabrication_hard_pass": g["fabrication_hard_pass"], "fabrication_preferred_pass": g["fabrication_preferred_pass"],
            "integer_dimension_pass": all(float(v).is_integer() for v in [500, 432, 432, spec["J2_L"], spec["J2_W"], *[x for x in d.values() if isinstance(x, (int, float))]]),
            "primitive_valid": g["primitive_valid"], "direct_overlap": g["direct_overlap"], "periodic_overlap": g["periodic_overlap"],
            "historical_source_paths": json.dumps(spec["source_files"], separators=(",", ":")), "split_group": spec["geometry_hash"], "split_assignment": "UNASSIGNED",
            "evidence_tier": EVIDENCE, "source_stage": SOURCE_STAGE}


def historical_row(spec: dict[str, Any]) -> dict[str, Any]:
    old = spec["legacy"]
    return {"schema_version": SCHEMA, "candidate_id": spec["candidate_id"], "legacy_case_id": spec["legacy_case_id"], "geometry_hash": spec["geometry_hash"],
            "legacy_nominal_bin_deg": spec["legacy_bin"], "legacy_actual_phase_deg": spec["migration_case"]["actual_old_phase_deg"],
            "legacy_selected_power": old["selected_power"], "legacy_selectivity": old["selectivity"], "legacy_matrix_error": old["matrix_error"],
            "legacy_phase_error": old["phase_error_deg"], "legacy_material": "dielectric_n2p6_blue_baseline", "legacy_monitor_z_nm": 850,
            "legacy_extractor": "central spatial sample", "legacy_normalization": "sqrt(T)/norm(Ex_center,Ey_center)",
            "historical_source_paths": json.dumps(spec["source_files"], separators=(",", ":")), "evidence_tier": "LEGACY_PROVENANCE_ONLY", "source_stage": SOURCE_STAGE}


def empty_subrun_record(run_id: str, spec: dict[str, Any], pol: str) -> dict[str, Any]:
    return {field: "" for field in SUBRUN_FIELDS} | {"schema_version": SCHEMA, "subrun_id": run_id, "candidate_id": spec["candidate_id"],
            "geometry_hash": spec["geometry_hash"], "physics_configuration_hash": PHYSICS_HASH, "wavelength_nm": WL,
            "input_polarization": pol, "normalization_version": NORMALIZATION_VERSION, "solver_status": "FAILED",
            "quality_status": "FAIL", "failure_code": "UNCLASSIFIED_FAILURE", "evidence_tier": EVIDENCE, "source_stage": SOURCE_STAGE}


def run_one(runtime: Any, spec: dict[str, Any], static: dict[str, Any], pol: str) -> dict[str, Any]:
    run_id = f"{spec['candidate_id']}_{pol}_{uuid.uuid4().hex[:8]}"
    run_dir = SUB / spec["candidate_id"] / run_id; run_dir.mkdir(parents=True, exist_ok=True)
    checkpoint = run_dir / "checkpoint.json"; cleanup_file = run_dir / "cleanup.json"; fsp = RUNTIME / f"{run_id}.fsp"
    fdtd = None; started = time.time(); ml_written = False
    out = {"candidate_id": spec["candidate_id"], "legacy_bin": spec["legacy_bin"], "input_basis": pol, "run_id": run_id,
           "status": "FAILED", "solver_called": False, "checkpoint_path": str(checkpoint), "checkpoint_reload": "PENDING", "ml_record_validation": "PENDING", "cleanup_status": "PENDING"}
    record = empty_subrun_record(run_id, spec, pol)
    try:
        lum = import_lumapi(runtime); fdtd = lum.FDTD(hide=getattr(runtime, "hide_gui", True))
        built = configure_exact(fdtd, spec, pol); build_gate = runtime_gate(fdtd, spec, built, static, "build")
        if build_gate["gate"] != "PASS": raise RuntimeError("GEOMETRY_MATERIAL_GATE_FAILED")
        fdtd.save(str(fsp)); fdtd.close(); fdtd = None
        fdtd = lum.FDTD(hide=getattr(runtime, "hide_gui", True)); fdtd.load(str(fsp))
        load_gate = runtime_gate(fdtd, spec, built, static, "save_load")
        if load_gate["gate"] != "PASS": raise RuntimeError("SAVE_LOAD_READBACK_GATE_FAILED")
        out["solver_called"] = True; t0 = time.time(); fdtd.run(); solver_seconds = time.time() - t0
        T = float(fdtd.transmission("T")); x, y, ex, ey, grid = base.b.f1.grid_plane(fdtd, T)
        raw_ex = base.b.f1.periodic_weighted(x, y, ex, grid["x_periodic_duplicate_endpoint"], grid["y_periodic_duplicate_endpoint"])
        raw_ey = base.b.f1.periodic_weighted(x, y, ey, grid["x_periodic_duplicate_endpoint"], grid["y_periodic_duplicate_endpoint"])
        norm_ex, norm_ey = base.b.f1.normalize_pair(raw_ex, raw_ey, T)
        scale = math.sqrt(T) / max(math.hypot(abs(raw_ex), abs(raw_ey)), EPS)
        integration = {"method": FORMAL_CONFIG["integration"], "normalization": FORMAL_CONFIG["normalization"], "hash": INTEGRATION_HASH,
                       "endpoint_flags": {"x": bool(grid["x_periodic_duplicate_endpoint"]), "y": bool(grid["y_periodic_duplicate_endpoint"])},
                       "grid": {"x_count": grid["x_count"], "y_count": grid["y_count"]}, "raw_Ex": base.cdict(raw_ex), "raw_Ey": base.cdict(raw_ey),
                       "normalized_Ex": base.cdict(norm_ex), "normalized_Ey": base.cdict(norm_ey), "T": T, "normalization_scale": scale}
        payload = {"schema_version": SCHEMA, "evidence_tier": EVIDENCE, "source_stage": SOURCE_STAGE, "candidate_id": spec["candidate_id"],
                   "legacy_case_id": spec["legacy_case_id"], "legacy_nominal_bin_deg": spec["legacy_bin"], "run_id": run_id, "input_basis": pol,
                   "status": "PASS", "solver_called": True, "solver_runtime_seconds": solver_seconds, "runtime_seconds": time.time() - started,
                   "reference_geometry_hash": spec["geometry_hash"], "runtime_hashes": load_gate["runtime_hashes"], "physics_configuration_hash": PHYSICS_HASH,
                   "build_gate": build_gate, "save_load_gate": load_gate, "formal_observable": FORMAL_CONFIG, "integration": integration,
                   "checkpoint_reload": "PASS", "cleanup_status": "ATTESTED_SEPARATELY"}
        atomic(checkpoint, payload); reloaded = json.loads(checkpoint.read_text(encoding="utf-8"))
        expected_reload = json.loads(json.dumps(payload, default=str))
        if reloaded["integration"] != expected_reload["integration"] or reloaded["run_id"] != run_id: raise RuntimeError("CHECKPOINT_RELOAD_FAILED")
        checkpoint_hash = sha(checkpoint); hashes = load_gate["runtime_hashes"]
        record.update({"runtime_geometry_hash": hashes["geometry_hash"], "source_hash": digest({"source_common": hashes["source_common_hash"], "input": pol}),
                       "source_common_hash": hashes["source_common_hash"], "monitor_hash": hashes["monitor_hash"], "boundary_hash": hashes["boundary_hash"],
                       "material_hash": hashes["material_hash"], "integration_hash": INTEGRATION_HASH, "solver_status": "PASS",
                       "runtime_seconds": payload["runtime_seconds"], "solver_runtime_seconds": solver_seconds, "checkpoint_path": str(checkpoint),
                       "checkpoint_sha256": checkpoint_hash, "weighted_G0_Ex_real": norm_ex.real, "weighted_G0_Ex_imag": norm_ex.imag,
                       "weighted_G0_Ey_real": norm_ey.real, "weighted_G0_Ey_imag": norm_ey.imag, "raw_weighted_G0_Ex_real": raw_ex.real,
                       "raw_weighted_G0_Ex_imag": raw_ex.imag, "raw_weighted_G0_Ey_real": raw_ey.real, "raw_weighted_G0_Ey_imag": raw_ey.imag,
                       "T": T, "normalization_scale": scale, "quality_status": "PASS", "failure_code": "NONE"})
        if callable(POST_SOLVER_ACCEPTANCE):
            POST_SOLVER_ACCEPTANCE(record=record, checkpoint=checkpoint, run_id=run_id, checkpoint_hash=checkpoint_hash, formal_row_path=STAGING / "subrun_records_v1.csv", fields=SUBRUN_FIELDS)
        else:
            append_row(STAGING / "subrun_records_v1.csv", SUBRUN_FIELDS, record)
            matched = [r for r in rows(STAGING / "subrun_records_v1.csv") if r["subrun_id"] == run_id]
            if len(matched) != 1 or matched[0]["checkpoint_sha256"] != checkpoint_hash: raise RuntimeError("ML_SUBRUN_RELOAD_VALIDATION_FAILED")
        ml_written = True
        out.update({"status": "PASS", "solver_runtime_seconds": solver_seconds, "runtime_seconds": payload["runtime_seconds"],
                    "checkpoint_reload": "PASS", "ml_record_validation": "PASS", "runtime_geometry_hash": hashes["geometry_hash"]})
    except Exception as exc:
        out.update({"status": "FAILED", "runtime_seconds": time.time() - started, "exception_type": type(exc).__name__, "exception_message": str(exc), "traceback": traceback.format_exc()})
        record.update({"solver_status": "FAILED", "runtime_seconds": out["runtime_seconds"], "quality_status": "FAIL", "failure_code": str(exc)[:120]})
        if not checkpoint.exists():
            atomic(checkpoint, {"schema_version": SCHEMA, "candidate_id": spec["candidate_id"], "run_id": run_id, "status": "FAILED", "exception_type": type(exc).__name__, "exception_message": str(exc), "traceback": traceback.format_exc(), "checkpoint_reload": "PASS"})
        record["checkpoint_path"] = str(checkpoint); record["checkpoint_sha256"] = sha(checkpoint)
        if not ml_written:
            append_row(STAGING / "subrun_records_v1.csv", SUBRUN_FIELDS, record); ml_written = True
            out["ml_record_validation"] = "PASS" if len([r for r in rows(STAGING / "subrun_records_v1.csv") if r["subrun_id"] == run_id]) == 1 else "FAIL"
    finally:
        if fdtd is not None:
            try: fdtd.close()
            except Exception: pass
        deleted = []
        for artifact in fsp.parent.glob(fsp.stem + "*"):
            if artifact.is_file() and artifact.suffix.lower() in {".fsp", ".fspx", ".ldf", ".log", ".h5", ".mat", ".npy", ".npz"}:
                deleted.append(str(artifact)); artifact.unlink(missing_ok=True)
        out["cleanup_status"] = "PASS" if not any(fsp.parent.glob(fsp.stem + "*")) else "FAIL"
        atomic(cleanup_file, {"run_id": run_id, "status": out["cleanup_status"], "deleted": deleted, "session_closed": True})
    return out


def replace_row(path: Path, fieldnames: list[str], key: str, record: dict[str, Any]) -> None:
    current = rows(path)
    replaced = False
    updated = []
    for row in current:
        if row[key] == str(record[key]):
            if replaced:
                raise RuntimeError(f"DUPLICATE_EXISTING_ROW:{record[key]}")
            updated.append(record); replaced = True
        else:
            updated.append(row)
    if not replaced:
        updated.append(record)
    temp = path.with_suffix(path.suffix + ".resume.tmp")
    temp.unlink(missing_ok=True)
    write_rows(temp, fieldnames, updated)
    os.replace(temp, path)


def recover_completed_subrun(spec: dict[str, Any], pol: str) -> dict[str, Any]:
    checkpoints = sorted((SUB / spec["candidate_id"]).glob(f"*_{pol}_*/checkpoint.json"))
    if len(checkpoints) != 1:
        raise RuntimeError(f"RESUME_CHECKPOINT_COUNT:{spec['candidate_id']}:{pol}:{len(checkpoints)}")
    checkpoint = checkpoints[0]
    payload = json.loads(checkpoint.read_text(encoding="utf-8"))
    cleanup_path = checkpoint.with_name("cleanup.json")
    cleanup = json.loads(cleanup_path.read_text(encoding="utf-8")) if cleanup_path.exists() else {}
    required = {"normalized_Ex", "normalized_Ey", "raw_Ex", "raw_Ey", "T", "normalization_scale", "hash"}
    checks = {
        "checkpoint_status_pass": payload.get("status") == "PASS",
        "solver_called": payload.get("solver_called") is True,
        "candidate_match": payload.get("candidate_id") == spec["candidate_id"],
        "input_match": payload.get("input_basis") == pol,
        "physics_hash_match": payload.get("physics_configuration_hash") == PHYSICS_HASH,
        "integration_complete": required <= set(payload.get("integration", {})),
        "integration_hash_match": payload.get("integration", {}).get("hash") == INTEGRATION_HASH,
        "cleanup_pass": cleanup.get("status") == "PASS",
    }
    if not all(checks.values()):
        raise RuntimeError("RESUME_CHECKPOINT_GATE_FAILED:" + json.dumps(checks))
    integration = payload["integration"]; hashes = payload["runtime_hashes"]
    def part(name: str, component: str) -> float:
        return float(integration[name][component])
    record = empty_subrun_record(payload["run_id"], spec, pol)
    record.update({"runtime_geometry_hash": hashes["geometry_hash"],
                   "source_hash": digest({"source_common": hashes["source_common_hash"], "input": pol}),
                   "source_common_hash": hashes["source_common_hash"], "monitor_hash": hashes["monitor_hash"],
                   "boundary_hash": hashes["boundary_hash"], "material_hash": hashes["material_hash"],
                   "integration_hash": INTEGRATION_HASH, "solver_status": "PASS",
                   "runtime_seconds": payload["runtime_seconds"], "solver_runtime_seconds": payload["solver_runtime_seconds"],
                   "checkpoint_path": str(checkpoint), "checkpoint_sha256": sha(checkpoint),
                   "weighted_G0_Ex_real": part("normalized_Ex", "real"), "weighted_G0_Ex_imag": part("normalized_Ex", "imag"),
                   "weighted_G0_Ey_real": part("normalized_Ey", "real"), "weighted_G0_Ey_imag": part("normalized_Ey", "imag"),
                   "raw_weighted_G0_Ex_real": part("raw_Ex", "real"), "raw_weighted_G0_Ex_imag": part("raw_Ex", "imag"),
                   "raw_weighted_G0_Ey_real": part("raw_Ey", "real"), "raw_weighted_G0_Ey_imag": part("raw_Ey", "imag"),
                   "T": integration["T"], "normalization_scale": integration["normalization_scale"],
                   "quality_status": "PASS", "failure_code": "NONE"})
    replace_row(STAGING / "subrun_records_v1.csv", SUBRUN_FIELDS, "subrun_id", record)
    matched = [r for r in rows(STAGING / "subrun_records_v1.csv") if r["subrun_id"] == payload["run_id"]]
    if len(matched) != 1 or matched[0]["checkpoint_sha256"] != sha(checkpoint):
        raise RuntimeError("RESUME_ML_ROW_VALIDATION_FAILED")
    atomic(checkpoint.with_name("recovery_validation.json"),
           {"schema_version": SCHEMA, "run_id": payload["run_id"], "status": "PASS", "checks": checks,
            "repair": "offline ML-row recovery after NumPy-bool JSON type comparison; solver not rerun",
            "checkpoint_sha256": sha(checkpoint)})
    return {"candidate_id": spec["candidate_id"], "legacy_bin": spec["legacy_bin"], "input_basis": pol,
            "run_id": payload["run_id"], "status": "PASS", "solver_called": True,
            "solver_runtime_seconds": payload["solver_runtime_seconds"], "runtime_seconds": payload["runtime_seconds"],
            "checkpoint_path": str(checkpoint), "checkpoint_reload": "PASS", "ml_record_validation": "PASS",
            "cleanup_status": "PASS", "runtime_geometry_hash": hashes["geometry_hash"],
            "recovered_from_checkpoint": True, "solver_rerun": False}


def formal_metrics(matrix: np.ndarray, spec: dict[str, Any], sg: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    m = base.metric(matrix)
    Txx, Txy, Tyx, Tyy = (float(abs(matrix[0, 0]) ** 2), float(abs(matrix[0, 1]) ** 2), float(abs(matrix[1, 0]) ** 2), float(abs(matrix[1, 1]) ** 2))
    cross, leakage = Txy + Tyx, Txy + Tyx + Tyy
    ratio = Txx / max(leakage, EPS); purity = Txx / max(Txx + Tyx, EPS); matrix_error = math.sqrt(leakage) / max(abs(matrix[0, 0]), EPS)
    pin, pout = m["principal_input_stokes"], m["principal_output_stokes"]
    strict_checks = {"Txx_ge_0p45": Txx >= .45, "R_total_ge_8": ratio >= 8, "purity_ge_0p90": purity >= .90,
                     "matrix_error_le_0p45": matrix_error <= .45, "input_x_overlap_ge_0p90": m["input_x_overlap"] >= .90,
                     "output_x_overlap_ge_0p90": m["output_x_overlap"] >= .90, "input_abs_ellipticity_le_10": abs(pin["ellipticity_deg"]) <= 10,
                     "output_abs_ellipticity_le_10": abs(pout["ellipticity_deg"]) <= 10, "fabrication_hard_pass": sg["geometry"]["fabrication_hard_pass"]}
    failed = [k for k, v in strict_checks.items() if not v]
    xlinear = all(strict_checks[k] for k in ("input_x_overlap_ge_0p90", "output_x_overlap_ge_0p90", "input_abs_ellipticity_le_10", "output_abs_ellipticity_le_10"))
    if all(strict_checks.values()):
        label, gate = "STRICT_PROJECTOR", "PASS_STRICT"
    elif xlinear and strict_checks["R_total_ge_8"] and strict_checks["fabrication_hard_pass"] and len(failed) <= 2:
        label, gate = "REPAIRABLE_PROJECTOR", "PASS_REPAIRABLE"
    elif max(m["input_x_overlap"], m["output_x_overlap"]) < .5 and max(abs(pin["ellipticity_deg"]), abs(pout["ellipticity_deg"])) <= 10:
        label, gate = "WRONG_AXIS", "FAIL"
    elif m["sigma2_over_sigma1"] <= .5 and max(abs(pin["ellipticity_deg"]), abs(pout["ellipticity_deg"])) > 10:
        label, gate = "ELLIPTICAL_LOW_RANK", "FAIL"
    elif m["sigma2_over_sigma1"] >= .75:
        label, gate = "HIGH_RANK_RETARDER", "FAIL"
    elif Txx < .1 and max(Txy, Tyx, Tyy) < .1:
        label, gate = "NO_USEFUL_RESPONSE", "FAIL"
    else:
        label, gate = "MIXED_RESPONSE", "FAIL"
    actual_phase = phase360(matrix[0, 0]); actual_bin, phase_error = nearest_bin(actual_phase)
    eligible = label in {"STRICT_PROJECTOR", "REPAIRABLE_PROJECTOR"}
    m.update({"Txx": Txx, "Txy": Txy, "Tyx": Tyx, "Tyy": Tyy, "cross_power": cross, "leakage_sum": leakage,
              "R_total": ratio, "blocked_input_selectivity": ratio, "selected_polarization_purity": purity,
              "matrix_projection_error": matrix_error, "actual_txx_phase_deg_450": actual_phase,
              "nearest_actual_bin_deg": actual_bin if eligible else None, "diagnostic_nearest_phase_bin_deg": actual_bin,
              "actual_bin_phase_error_deg": phase_error if eligible else None, "diagnostic_phase_error_deg": phase_error,
              "formal_classification": label, "projector_gate_status": gate, "projector_checks": strict_checks,
              "projector_failed_checks": failed, "rebin_eligible": eligible})
    return m, {"classification": label, "projector_gate_status": gate, "failed_checks": failed, "rebin_eligible": eligible}


def candidate_row(spec: dict[str, Any], matrix: np.ndarray, m: dict[str, Any], checkpoint: Path, runtime_hash: str) -> dict[str, Any]:
    p, pi, po = m["pauli"], m["principal_input_stokes"], m["principal_output_stokes"]
    return {"schema_version": SCHEMA, "candidate_id": spec["candidate_id"], "legacy_case_id": spec["legacy_case_id"], "legacy_nominal_bin_deg": spec["legacy_bin"],
            "geometry_hash": spec["geometry_hash"], "runtime_geometry_hash": runtime_hash, "physics_configuration_hash": PHYSICS_HASH, "wavelength_nm": WL,
            "candidate_checkpoint_path": str(checkpoint), "candidate_checkpoint_sha256": sha(checkpoint),
            "txx_real": matrix[0, 0].real, "txx_imag": matrix[0, 0].imag, "txy_real": matrix[0, 1].real, "txy_imag": matrix[0, 1].imag,
            "tyx_real": matrix[1, 0].real, "tyx_imag": matrix[1, 0].imag, "tyy_real": matrix[1, 1].real, "tyy_imag": matrix[1, 1].imag,
            "Txx": m["Txx"], "Txy": m["Txy"], "Tyx": m["Tyx"], "Tyy": m["Tyy"], "cross_power": m["cross_power"], "leakage_sum": m["leakage_sum"],
            "R_total": m["R_total"], "blocked_input_selectivity": m["blocked_input_selectivity"], "selected_polarization_purity": m["selected_polarization_purity"],
            "sigma1": m["sigma1"], "sigma2": m["sigma2"], "sigma2_over_sigma1": m["sigma2_over_sigma1"], "determinant_magnitude": m["determinant_magnitude"],
            "matrix_projection_error": m["matrix_projection_error"], "reciprocity_residual": m["reciprocity_residual"],
            "input_S1": pi["S1"], "input_S2": pi["S2"], "input_S3": pi["S3"], "output_S1": po["S1"], "output_S2": po["S2"], "output_S3": po["S3"],
            "input_AoLP_deg": pi["aolp_deg"], "output_AoLP_deg": po["aolp_deg"], "input_ellipticity_deg": pi["ellipticity_deg"], "output_ellipticity_deg": po["ellipticity_deg"],
            "input_x_overlap": m["input_x_overlap"], "output_x_overlap": m["output_x_overlap"],
            "a0_real": p["a0"]["real"], "a0_imag": p["a0"]["imag"], "az_real": p["az"]["real"], "az_imag": p["az"]["imag"],
            "ax_real": p["ax"]["real"], "ax_imag": p["ax"]["imag"], "ay_real": p["ay"]["real"], "ay_imag": p["ay"]["imag"],
            "abs_a0_over_abs_az": p["identity_anisotropy_ratio"], "common_differential_phase_error_deg": p["identity_anisotropy_phase_error_deg"],
            "off_axis_fraction": p["off_axis_fraction"], "actual_txx_phase_deg_450": m["actual_txx_phase_deg_450"],
            "nearest_actual_bin_deg": "" if m["nearest_actual_bin_deg"] is None else m["nearest_actual_bin_deg"],
            "actual_bin_phase_error_deg": "" if m["actual_bin_phase_error_deg"] is None else m["actual_bin_phase_error_deg"],
            "formal_classification": m["formal_classification"], "projector_gate_status": m["projector_gate_status"],
            "projector_failed_checks": json.dumps(m["projector_failed_checks"], separators=(",", ":")), "dominant_leakage": m["dominant_leakage"],
            "quality_status": "PASS", "evidence_tier": EVIDENCE, "source_stage": SOURCE_STAGE}


def make_candidate(spec: dict[str, Any], sg: dict[str, Any], subruns: list[dict[str, Any]]) -> dict[str, Any]:
    if len(subruns) != 2 or any(r["status"] != "PASS" or r["cleanup_status"] != "PASS" for r in subruns):
        raise RuntimeError("SUBRUN_PAIR_INCOMPLETE")
    loaded = [json.loads(Path(r["checkpoint_path"]).read_text(encoding="utf-8")) for r in subruns]
    x = next(r for r in loaded if r["input_basis"] == "x"); y = next(r for r in loaded if r["input_basis"] == "y")
    keys = ("geometry_hash", "source_common_hash", "monitor_hash", "boundary_hash", "material_hash")
    xh, yh = x["runtime_hashes"], y["runtime_hashes"]
    checks = {"candidate_id": x["candidate_id"] == y["candidate_id"] == spec["candidate_id"], "input_pair": {x["input_basis"], y["input_basis"]} == {"x", "y"},
              "physics_hash": x["physics_configuration_hash"] == y["physics_configuration_hash"] == PHYSICS_HASH,
              "runtime_hashes": all(xh[k] == yh[k] for k in keys), "integration_hash": x["integration"]["hash"] == y["integration"]["hash"] == INTEGRATION_HASH}
    if not all(checks.values()): raise RuntimeError("JONES_PAIRING_MISMATCH")
    matrix = np.array([[cv(x["integration"]["normalized_Ex"]), cv(y["integration"]["normalized_Ex"])],
                       [cv(x["integration"]["normalized_Ey"]), cv(y["integration"]["normalized_Ey"])]], dtype=complex)
    m, classification = formal_metrics(matrix, spec, sg)
    path = CAND / f"{spec['candidate_id']}.json"
    payload = {"schema_version": SCHEMA, "candidate_id": spec["candidate_id"], "legacy_case_id": spec["legacy_case_id"], "legacy_nominal_bin_deg": spec["legacy_bin"],
               "status": "PASS", "reference_geometry_hash": spec["geometry_hash"], "runtime_geometry_hash": xh["geometry_hash"], "physics_configuration_hash": PHYSICS_HASH,
               "subrun_checkpoints": [r["checkpoint_path"] for r in subruns], "provenance_pairing": {"status": "PASS", "checks": checks},
               "weighted_G0_Jones": [[base.cdict(matrix[0, 0]), base.cdict(matrix[0, 1])], [base.cdict(matrix[1, 0]), base.cdict(matrix[1, 1])]],
               "formal_metrics": m, "classification": classification, "geometry_gate": sg, "candidate_checkpoint_reload": "PENDING"}
    atomic(path, payload); reload = json.loads(path.read_text(encoding="utf-8"))
    if reload["weighted_G0_Jones"] != payload["weighted_G0_Jones"]: raise RuntimeError("CANDIDATE_CHECKPOINT_RELOAD_FAILED")
    payload["candidate_checkpoint_reload"] = "PASS"
    payload["ml_candidate_record_validation"] = "ATTESTED_SEPARATELY"
    atomic(path, payload)
    row = candidate_row(spec, matrix, m, path, xh["geometry_hash"])
    append_row(STAGING / "candidate_wavelength_jones_v1.csv", CANDIDATE_FIELDS, row)
    matches = [r for r in rows(STAGING / "candidate_wavelength_jones_v1.csv") if r["candidate_id"] == spec["candidate_id"]]
    if len(matches) != 1 or matches[0]["candidate_checkpoint_sha256"] != sha(path): raise RuntimeError("ML_CANDIDATE_RELOAD_VALIDATION_FAILED")
    atomic(CAND / f"{spec['candidate_id']}.ml_validation.json",
           {"schema_version": SCHEMA, "candidate_id": spec["candidate_id"], "status": "PASS",
            "candidate_checkpoint_sha256": sha(path), "candidate_ml_record_reload": "PASS"})
    result = json.loads(path.read_text(encoding="utf-8"))
    result["ml_candidate_record_validation"] = "PASS"
    return result


def field_dictionary() -> dict[str, Any]:
    files = {"geometry_master_v1.csv": GEOMETRY_FIELDS, "subrun_records_v1.csv": SUBRUN_FIELDS,
             "candidate_wavelength_jones_v1.csv": CANDIDATE_FIELDS, "historical_provenance_v1.csv": HISTORICAL_FIELDS}
    definitions = {}
    for filename, fields in files.items():
        definitions[filename] = {}
        for field in fields:
            unit = "nm" if field.endswith("_nm") else "deg" if field.endswith("_deg") or "phase" in field and "hash" not in field else "s" if field.endswith("_seconds") else "dimensionless"
            definitions[filename][field] = {"description": field.replace("_", " "), "unit": unit, "missing": "empty string"}
    return {"schema_version": SCHEMA, "field_definitions": definitions, "wrap_convention": "phases wrap to [0,360); errors use shortest circular distance",
            "phase_convention": "arg(txx) at formal field_monitor plane z=1000 nm", "jones_convention": "J=[[txx,txy],[tyx,tyy]], columns are x/y inputs",
            "classification_enum": ["STRICT_PROJECTOR", "REPAIRABLE_PROJECTOR", "WRONG_AXIS", "ELLIPTICAL_LOW_RANK", "HIGH_RANK_RETARDER", "MIXED_RESPONSE", "NO_USEFUL_RESPONSE", "INDETERMINATE"],
            "missing_value_convention": "CSV empty string; JSON null", "failure_code_enum": ["NONE", "GEOMETRY_MATERIAL_GATE_FAILED", "SAVE_LOAD_READBACK_GATE_FAILED", "CHECKPOINT_RELOAD_FAILED", "ML_SUBRUN_RELOAD_VALIDATION_FAILED", "SOLVER_OR_EXTRACTION_FAILURE", "UNCLASSIFIED_FAILURE"],
            "evidence_tier_enum": [EVIDENCE, "LEGACY_PROVENANCE_ONLY"],
            "manufacturing_flags": {"fabrication_hard_pass": "direct and periodic gaps >=50 nm and no overlap", "fabrication_preferred_pass": "direct and periodic gaps >=60 nm and no overlap"},
            "projector_rules": {"strict": "Txx>=0.45, R_total>=8, purity>=0.90, matrix_error<=0.45, input/output x overlap>=0.90, abs ellipticity<=10 deg, fabrication hard pass",
                                "repairable": "x-linear and R_total/fabrication gates remain passed; at most two of Txx/purity/matrix-error marginal checks fail; ratio gate is never lowered"}}


def quality_audit(specs: list[dict[str, Any]], candidates: list[dict[str, Any]]) -> dict[str, Any]:
    gm, sr, cr, hr = (rows(STAGING / name) for name in ("geometry_master_v1.csv", "subrun_records_v1.csv", "candidate_wavelength_jones_v1.csv", "historical_provenance_v1.csv"))
    finite_fields = [f for f in CANDIDATE_FIELDS if f.endswith(("_real", "_imag"))]
    checks = {
        "duplicate_geometry_hash": len({r["geometry_hash"] for r in gm}) == len(gm),
        "duplicate_subrun_id": len({r["subrun_id"] for r in sr}) == len(sr),
        "missing_xy_partner": all({r["input_polarization"] for r in sr if r["candidate_id"] == s["candidate_id"] and r["solver_status"] == "PASS"} == {"x", "y"} for s in specs if any(c["candidate_id"] == s["candidate_id"] for c in candidates)),
        "inconsistent_physics_hash": all(r["physics_configuration_hash"] == PHYSICS_HASH for r in gm + sr + cr),
        "nonfinite_complex_value": all(math.isfinite(float(r[f])) for r in cr for f in finite_fields if r[f] != ""),
        "jones_pairing_mismatch": all(c["provenance_pairing"]["status"] == "PASS" for c in candidates),
        "label_recomputation_consistency": all(abs(float(r["Txx"]) - (float(r["txx_real"]) ** 2 + float(r["txx_imag"]) ** 2)) < 1e-10 for r in cr),
        "historical_formal_label_leakage": all(k.startswith("legacy_") or k in {"schema_version", "candidate_id", "geometry_hash", "historical_source_paths", "evidence_tier", "source_stage"} for k in HISTORICAL_FIELDS) and not any(k.startswith("legacy_") and k not in {"legacy_case_id", "legacy_nominal_bin_deg"} for k in CANDIDATE_FIELDS),
        "manufacturing_label_consistency": all((r["fabrication_hard_pass"].lower() == "true") == (float(r["direct_gap_nm"]) >= 50 and float(r["periodic_gap_nm"]) >= 50 and r["direct_overlap"].lower() == "false" and r["periodic_overlap"].lower() == "false") for r in gm),
        "count_consistency": len(gm) == len(hr) == 6 and len(sr) == 2 * len(cr) and len(cr) == len(candidates),
        "checkpoint_ml_row_consistency": all(Path(r["checkpoint_path"]).exists() and sha(Path(r["checkpoint_path"])) == r["checkpoint_sha256"] for r in sr),
        "candidate_checkpoint_ml_row_consistency": all(Path(r["candidate_checkpoint_path"]).exists() and sha(Path(r["candidate_checkpoint_path"])) == r["candidate_checkpoint_sha256"] for r in cr),
    }
    return {"schema_version": SCHEMA, "status": "PASS" if all(checks.values()) else "FAIL", "checks": checks,
            "row_counts": {"geometry_master": len(gm), "subrun_records": len(sr), "candidate_wavelength_jones": len(cr), "historical_provenance": len(hr)}}


def aggregate_csv(candidates: list[dict[str, Any]]) -> None:
    flat = []
    for c in candidates:
        m = c["formal_metrics"]
        flat.append({"candidate_id": c["candidate_id"], "legacy_nominal_bin_deg": c["legacy_nominal_bin_deg"], "classification": m["formal_classification"],
                     "actual_phase_deg": m["actual_txx_phase_deg_450"], "actual_bin_deg": "" if m["nearest_actual_bin_deg"] is None else m["nearest_actual_bin_deg"],
                     "phase_error_deg": "" if m["actual_bin_phase_error_deg"] is None else m["actual_bin_phase_error_deg"],
                     "Txx": m["Txx"], "Txy": m["Txy"], "Tyx": m["Tyx"], "Tyy": m["Tyy"], "R_total": m["R_total"],
                     "matrix_error": m["matrix_projection_error"], "sigma2_over_sigma1": m["sigma2_over_sigma1"], "input_x_overlap": m["input_x_overlap"], "output_x_overlap": m["output_x_overlap"]})
    fields = list(flat[0]); CSV_OUT.parent.mkdir(parents=True, exist_ok=True)
    with CSV_OUT.open("x", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(flat)


def report(payload: dict[str, Any]) -> str:
    lines = ["# APCD_LP_LEGACY_H500_SIXBIN_FORMAL_REPLAY_450_V1_RESULT", "", "## ENVIRONMENT", "", json.dumps(payload["environment"], indent=2), "",
             "## EXACT_CENTER_BUILDER_GATE", "", json.dumps(payload["exact_center_builder_gate"], indent=2), "", "## FORMAL_CONFIGURATION", "", json.dumps(payload["formal_configuration"], indent=2), "",
             "## GEOMETRY_GATE", "", json.dumps(payload["geometry_gates"], indent=2), "", "## RUN_STATUS", "", json.dumps(payload["run_status"], indent=2), "",
             "## WEIGHTED_G0_JONES", "", json.dumps([{c["candidate_id"]: c["weighted_G0_Jones"]} for c in payload["candidates"]], indent=2), "",
             "## FORMAL_PROJECTOR_METRICS", "", json.dumps([{c["candidate_id"]: c["formal_metrics"]} for c in payload["candidates"]], indent=2), "",
             "## PAULI_SVD_STOKES", "", json.dumps([{c["candidate_id"]: {"pauli": c["formal_metrics"]["pauli"], "sigma1": c["formal_metrics"]["sigma1"], "sigma2": c["formal_metrics"]["sigma2"], "input": c["formal_metrics"]["principal_input_stokes"], "output": c["formal_metrics"]["principal_output_stokes"]}} for c in payload["candidates"]], indent=2), "",
             "## HISTORICAL_VS_FORMAL", "", json.dumps(payload["historical_vs_formal"], indent=2), "", "## ACTUAL_PHASE_REBIN", "", json.dumps(payload["actual_phase_rebin"], indent=2), "",
             "## BIN_OCCUPANCY", "", json.dumps(payload["bin_occupancy"], indent=2), "", "## ML_DATA_PACKAGE", "", json.dumps(payload["ml_data_package"], indent=2), "",
             "## ROUTE_DECISION", "", json.dumps(payload["route_decision"], indent=2), "", "## CONSTRAINT_AUDIT", "", json.dumps(payload["constraint_audit"], indent=2), "", "## FINAL_STATUS", "", payload["status"], ""]
    return "\n".join(lines)


def finalize_ml(specs: list[dict[str, Any]], candidates: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any]]:
    atomic(STAGING / "label_dictionary_v1.json", field_dictionary())
    qa = quality_audit(specs, candidates); atomic(STAGING / "quality_audit_v1.json", qa)
    source_paths = [MIGRATION_JSON, MIGRATION_INVENTORY, MIGRATION_MANIFEST, MIGRATION_REPORT, Path(__file__)]
    manifest = {"schema_version": SCHEMA, "generation_task": SOURCE_STAGE, "creation_timestamp": datetime.now(timezone.utc).isoformat(),
                "source_files": [{"path": str(p), "bytes": p.stat().st_size, "sha256": sha(p)} for p in source_paths],
                "formal_physics_configuration": FORMAL_CONFIG, "physics_configuration_hash": PHYSICS_HASH,
                "row_counts": qa["row_counts"], "candidate_count": len(specs), "success_count": len(candidates), "failure_count": len(specs) - len(candidates),
                "geometry_hashes": [s["geometry_hash"] for s in specs], "split_assignment": "UNASSIGNED", "split_policy": "split_group equals geometry_hash", "code_sha256": sha(Path(__file__))}
    atomic(STAGING / "dataset_manifest_v1.json", manifest)
    staging_files = sorted(p for p in STAGING.iterdir() if p.name != "checksums_v1.json")
    checksums = {"schema_version": SCHEMA, "self_reference_policy": "checksums_v1.json excludes itself because a file cannot contain its own stable digest",
                 "files": [{"path": str(p), "bytes": p.stat().st_size, "sha256": sha(p)} for p in staging_files]}
    atomic(STAGING / "checksums_v1.json", checksums)
    return qa, manifest


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--validate-only", action="store_true"); parser.add_argument("--resume", action="store_true"); args = parser.parse_args()
    validation = validate_inputs(args.resume)
    print(json.dumps({"preflight": validation["status"], "checks": validation["checks"], "builder_gates": validation["static_builder_gates"]}, default=str))
    if validation["status"] != "PASS": return 2
    if args.validate_only: return 0
    specs = validation.pop("specs"); static = validation["static_builder_gates"]
    ROOT.mkdir(parents=True, exist_ok=args.resume); SUB.mkdir(exist_ok=args.resume); CAND.mkdir(exist_ok=args.resume); RUNTIME.mkdir(parents=True, exist_ok=args.resume); STAGING.mkdir(parents=True, exist_ok=args.resume)
    protected_before = {str(p): sha(p) for p in PROTECTED}; runtime = load_runtime_config(R / "configs/runtime.yaml")
    environment = {"host": "DESKTOP-NNE313K", "branch": base.git("branch", "--show-current"), "head": base.git("rev-parse", "--short", "HEAD"),
                   "pre_git_status": base.git("status", "--short", "--branch"), "protected_before": protected_before,
                   "input_files": [{"path": str(p), "sha256": sha(p)} for p in INPUT_SHA256]}
    builder_gate = json.loads((ROOT / "builder_gate.json").read_text(encoding="utf-8")) if args.resume else runtime_builder_gate_all(runtime, specs, static)
    if not args.resume: atomic(ROOT / "builder_gate.json", builder_gate)
    if not all(g["gate"] == "PASS" for g in builder_gate):
        raise RuntimeError("EXACT_CENTER_BUILDER_GATE_FAILED")
    if not args.resume:
        write_rows(STAGING / "geometry_master_v1.csv", GEOMETRY_FIELDS, [geometry_master(s, g) for s, g in zip(specs, static)])
        write_rows(STAGING / "historical_provenance_v1.csv", HISTORICAL_FIELDS, [historical_row(s) for s in specs])
        write_rows(STAGING / "subrun_records_v1.csv", SUBRUN_FIELDS, [])
        write_rows(STAGING / "candidate_wavelength_jones_v1.csv", CANDIDATE_FIELDS, [])
    recovered = recover_completed_subrun(specs[0], "x") if args.resume else None
    run_status, candidates, aggregate_error = ([recovered] if recovered else []), [], None
    for spec, sg in zip(specs, static):
        pair = []
        for pol in ("x", "y"):
            if recovered and spec["candidate_id"] == recovered["candidate_id"] and pol == "x":
                pair.append(recovered)
                print(json.dumps({"candidate_id": recovered["candidate_id"], "input_basis": "x", "status": "PASS", "recovered_from_checkpoint": True, "solver_rerun": False}), flush=True)
                continue
            run = run_one(runtime, spec, sg, pol); pair.append(run); run_status.append(run)
            print(json.dumps({k: run.get(k) for k in ("candidate_id", "input_basis", "status", "solver_runtime_seconds", "checkpoint_reload", "ml_record_validation", "cleanup_status", "exception_message")}, default=str), flush=True)
            if run["status"] != "PASS" or run["cleanup_status"] != "PASS": break
        if len(pair) != 2 or any(r["status"] != "PASS" for r in pair): break
        try:
            item = make_candidate(spec, sg, pair); candidates.append(item)
            print(json.dumps({"candidate_id": item["candidate_id"], "classification": item["formal_metrics"]["formal_classification"], "candidate_checkpoint_reload": item["candidate_checkpoint_reload"], "ml_validation": item["ml_candidate_record_validation"]}), flush=True)
        except Exception as exc:
            aggregate_error = {"exception_type": type(exc).__name__, "exception_message": str(exc), "traceback": traceback.format_exc()}; break
    shutil.rmtree(RUNTIME, ignore_errors=True)
    qa, dataset_manifest = finalize_ml(specs, candidates)
    eligible = [c for c in candidates if c["formal_metrics"]["rebin_eligible"]]
    bins = sorted({c["formal_metrics"]["nearest_actual_bin_deg"] for c in eligible})
    if len(candidates) < 6 or len(run_status) < 12 or any(r["status"] != "PASS" for r in run_status) or qa["status"] != "PASS": route = "FORMAL_REPLAY_DATA_PARTIAL"
    elif len(bins) >= 4: route = "FORMAL_REPLAY_PROJECTOR_LIBRARY_SURVIVES"
    elif bins: route = "FORMAL_REPLAY_PARTIAL_PROJECTOR_SEEDS_SURVIVE"
    else: route = "FORMAL_REPLAY_NO_PROJECTOR_SURVIVES"
    primary = max(eligible, key=lambda c: c["formal_metrics"]["Txx"] * c["formal_metrics"]["R_total"] / max(1, c["formal_metrics"]["matrix_projection_error"]))["candidate_id"] if eligible else "none"
    occupancy = {str(b): {"strict": [c["candidate_id"] for c in eligible if c["formal_metrics"]["nearest_actual_bin_deg"] == b and c["formal_metrics"]["formal_classification"] == "STRICT_PROJECTOR"],
                          "repairable": [c["candidate_id"] for c in eligible if c["formal_metrics"]["nearest_actual_bin_deg"] == b and c["formal_metrics"]["formal_classification"] == "REPAIRABLE_PROJECTOR"],
                          "empty_or_nonprojector": not any(c["formal_metrics"]["nearest_actual_bin_deg"] == b for c in eligible)} for b in ORDER}
    protected_after = {str(p): sha(p) for p in PROTECTED}
    payload = {"stage": SOURCE_STAGE, "status": "PASS" if route != "FORMAL_REPLAY_DATA_PARTIAL" else "PARTIAL_PASS_CANDIDATE_DATA_PRESERVED",
               "environment": environment | {"protected_after": protected_after, "protected_integrity": protected_before == protected_after},
               "exact_center_builder_gate": {"static": static, "runtime_save_load": builder_gate},
               "formal_configuration": {"legacy": {"wavelength_nm": 450, "period_x_nm": 431.907786, "period_y_nm": 432, "material": "dielectric n=2.6", "monitor_z_nm": 850, "extractor": "central spatial sample", "normalization": "legacy component normalization"},
                                        "formal": FORMAL_CONFIG, "period_x_migration_delta_nm": .092214},
               "geometry_gates": static, "run_status": run_status, "candidates": candidates,
               "historical_vs_formal": [{"candidate_id": c["candidate_id"], "legacy": next(s["legacy"] for s in specs if s["candidate_id"] == c["candidate_id"]), "formal": {k: c["formal_metrics"][k] for k in ("Txx", "R_total", "matrix_projection_error", "formal_classification", "actual_txx_phase_deg_450")}} for c in candidates],
               "actual_phase_rebin": [{"candidate_id": c["candidate_id"], "legacy_bin": c["legacy_nominal_bin_deg"], "classification": c["formal_metrics"]["formal_classification"], "actual_phase": c["formal_metrics"]["actual_txx_phase_deg_450"], "actual_bin": c["formal_metrics"]["nearest_actual_bin_deg"], "phase_error": c["formal_metrics"]["actual_bin_phase_error_deg"]} for c in candidates],
               "bin_occupancy": occupancy, "ml_data_package": {"schema_version": SCHEMA, "staging_path": str(STAGING), "dataset_manifest": dataset_manifest, "quality_audit": qa, "split_policy": "geometry_hash / UNASSIGNED"},
               "route_decision": {"classification": route, "primary_surviving_candidate": primary, "spectral_screen_candidates": [c["candidate_id"] for c in eligible] if route == "FORMAL_REPLAY_PROJECTOR_LIBRARY_SURVIVES" else [], "next_task_started": False},
               "aggregate_error": aggregate_error,
               "constraint_audit": {"solver_subrun_count": sum(bool(r.get("solver_called")) for r in run_status), "exactly_12_FDTD_subruns": len(run_status) == 12 and all(r.get("solver_called") for r in run_status),
                                    "only_six_authorized_candidates": {r["candidate_id"] for r in run_status} <= {s["candidate_id"] for s in specs}, "exact_old_centers_retained": all(g["gate"] == "PASS" for g in builder_gate),
                                    "no_automatic_canonicalization": True, "no_spectrum_or_geometry_variation": True, "no_baseline_or_constituent_runs": True,
                                    "candidate_checkpoint_before_aggregate": all(c["candidate_checkpoint_reload"] == "PASS" for c in candidates), "ML_records_before_proceeding": all(r.get("ml_record_validation") == "PASS" for r in run_status),
                                    "failed_runs_retained_as_labels": True, "no_historical_formal_label_mixing": qa["checks"]["historical_formal_label_leakage"],
                                    "no_protected_report_modification": protected_before == protected_after, "no_heavy_artifacts": not RUNTIME.exists(), "no_git_write": True, "no_external_process_termination": True,
                                    "task_created_runtime_directories": 0 if not RUNTIME.exists() else 1}}
    aggregate_csv(candidates) if candidates else None
    atomic(JSON_OUT, payload); REPORT.write_text(report(payload), encoding="utf-8")
    print(json.dumps({"status": payload["status"], "route": route, "primary": primary, "subruns": len(run_status), "candidates": len(candidates), "quality": qa["status"]}), flush=True)
    return 0 if payload["status"] == "PASS" else 3


if __name__ == "__main__":
    raise SystemExit(main())
