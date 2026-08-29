from __future__ import annotations

import argparse
import copy
import datetime as dt
import hashlib
import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(os.environ.get("PAPER_A_ROOT", r"D:/project/worktrees/blue_apcd_paper_a_lp_cp_broadband_v1"))
BASE = ROOT / "paper_a_broadband"
AUTH = BASE / "authority"
RUNTIME = BASE / "runtime/ic2_solver_ready"
REPORT = BASE / "reports/ic2_solver_ready_prefsp"
IC1_BUILDER_PATH = BASE / "scripts/ic1_solver_ready_prefsp_builder_v1.py"
IC1_AUTHORITY_PATH = AUTH / "ic1_solver_ready_prefsp_authority_v1.json"
CASE_ID = "IC2_TOPWELL_Y"
IC1_CASE_ID = "IC1_MDC_I03_TOPWELL_X"
V2_TIME_PROBE = "ic1_v2_time_probe"
CANONICAL_PREFSP = RUNTIME / f"{CASE_ID}_attempt_001_pre.fsp"
LUMERICAL_API = r"N:/Program Files/ANSYS Inc/v251/Lumerical/api/python"
if LUMERICAL_API not in sys.path:
    sys.path.insert(0, LUMERICAL_API)


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def canon(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode("utf-8")


def sha_obj(value: Any) -> str:
    return hashlib.sha256(canon(value)).hexdigest()


def sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(value, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def load_base_builder():
    if not IC1_BUILDER_PATH.exists():
        raise RuntimeError(f"IC1_BUILDER_MISSING:{IC1_BUILDER_PATH}")
    spec = importlib.util.spec_from_file_location("ic1_prefsp_builder_for_ic2", IC1_BUILDER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("IC1_BUILDER_IMPORT_FAILED")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_ic1_authority() -> dict[str, Any]:
    authority = load_json(IC1_AUTHORITY_PATH)
    if authority.get("status") != "PASS_SOLVER_READY_PREFSP" or authority.get("case_id") != IC1_CASE_ID:
        raise RuntimeError("IC1_AUTHORITY_NOT_PASS")
    return authority


def add_y_source(fdtd: Any, authorities: dict[str, Any]) -> None:
    """Reuse the IC1 source contract; only change x-oriented azimuth to y."""
    c, source = authorities["monitor"]["source_grid"], authorities["z"]["ic1_source"]
    fdtd.setglobalmonitor("frequency points", int(c["points"]))
    fdtd.setglobalmonitor("use wavelength spacing", True)
    fdtd.adddipole()
    fdtd.set("name", CASE_ID)
    for key, value in (
        ("x", float(source["position_nm"][0]) * 1e-9),
        ("y", float(source["position_nm"][1]) * 1e-9),
        ("z", float(source["position_nm"][2]) * 1e-9),
        ("theta", 90.0),
        ("phi", 90.0),
        ("wavelength start", float(c["start_nm"]) * 1e-9),
        ("wavelength stop", float(c["stop_nm"]) * 1e-9),
        ("amplitude", 1.0),
        ("phase", 0.0),
    ):
        fdtd.setnamed(CASE_ID, key, value)


def configure_ic2_builder(module: Any) -> None:
    module.CASE_ID = CASE_ID
    # Keep all monitor names identical to IC1 so the instrumentation contract
    # is byte/semantic comparable; only the source object is case-specific.
    module.V2_TIME_PROBE = V2_TIME_PROBE
    module.add_source = add_y_source


def normalize_physics(value: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(value)
    result["case_id"] = "CASE_ID_IGNORED_FOR_ORIENTATION_COMPARISON"
    result["source"]["phi"] = "ORIENTATION_IGNORED"
    return result


def validate_ic2(module: Any, readback: dict[str, Any], ic1_authority: dict[str, Any]) -> dict[str, Any]:
    checks = {key: value for key, value in module.validate_readback(readback).items() if key != "all"}
    source = readback["physics_semantic"]["source"]
    checks["source"] = (
        abs(float(source["x"]) * 1e9) < 1e-6
        and abs(float(source["y"]) * 1e9) < 1e-6
        and abs(float(source["z"]) * 1e9 + 171.5) < 1e-6
        and abs(float(source["theta"]) - 90.0) < 1e-6
        and abs(float(source["phi"]) - 90.0) < 1e-6
    )
    ic1_readback = ic1_authority["full_readback"]
    checks["geometry_domain_monitor_semantic_match"] = (
        normalize_physics(ic1_readback["physics_semantic"])
        == normalize_physics(readback["physics_semantic"])
        and ic1_readback["instrumentation_semantic"] == readback["instrumentation_semantic"]
    )
    checks["orientation_only_physics_delta"] = (
        normalize_physics(ic1_readback["physics_semantic"])
        == normalize_physics(readback["physics_semantic"])
        and float(ic1_readback["physics_semantic"]["source"]["phi"]) == 0.0
        and float(readback["physics_semantic"]["source"]["phi"]) == 90.0
    )
    checks["all"] = all(bool(item) for item in checks.values())
    return checks


def readback(path: Path) -> dict[str, Any]:
    module = load_base_builder()
    configure_ic2_builder(module)
    return module.readback(path)


def validate_readback(value: dict[str, Any]) -> dict[str, Any]:
    module = load_base_builder()
    configure_ic2_builder(module)
    return validate_ic2(module, value, load_ic1_authority())


def build(output: Path) -> dict[str, Any]:
    if output.exists():
        raise RuntimeError(f"REFUSE_OVERWRITE_IC2_PREFSP:{output}")
    ic1_authority = load_ic1_authority()
    module = load_base_builder()
    configure_ic2_builder(module)
    result = module.build_from_authority(output)
    readback = module.readback(output)
    validation = validate_ic2(module, readback, ic1_authority)
    if not validation["all"]:
        raise RuntimeError(f"IC2_SETUP_VALIDATION_FAILED:{json.dumps(validation, sort_keys=True)}")

    normalized_geometry = normalize_physics(readback["physics_semantic"])
    ic1_contract = copy.deepcopy(ic1_authority["physics_contract"])
    ic2_contract = copy.deepcopy(ic1_contract)
    ic2_contract["source"]["orientation"] = "y"
    authority_files = {
        "ic1_authority": IC1_AUTHORITY_PATH,
        "finite_mesa": AUTH / "ic1_finite_mesa_authority.json",
        "domain_pml": AUTH / "ic1_domain_pml_authority.json",
        "absolute_z_layout": AUTH / "ic1_absolute_z_layout.json",
        "i03_replication": AUTH / "ic1_i03_5x5_replication_authority.json",
        "monitor_contract": AUTH / "ic1_monitor_contract.json",
        "integrated_adapter": AUTH / "ic1_integrated_validity_adapter.json",
        "v2_validity": AUTH / "paper_a_fdtd_physics_validity_gate_v2_instrumented.json",
        "material_config": ROOT / "configs/material_reference_apcd_blue.json",
    }
    source_provenance = {key: {"path": str(path), "sha256": sha_file(path)} for key, path in authority_files.items()}
    counters = {"solver_run_called": False, "solver_entered": 0, "active_fdtd": 0, "rcwa": 0, "ml": 0, "hidden_auto_admission": False}
    authority = {
        "schema": "PAPER_A_IC2_SOLVER_READY_PREFSP_AUTHORITY_V1",
        "status": "PASS_SOLVER_READY_PREFSP",
        "task_id": "PAPER_A_IC2_TOPWELL_Y_SINGLE_FDTD_V1",
        "case_id": CASE_ID,
        "scope": "setup_only_pre_fsp; exact IC1 integrated authority with x-to-y source orientation only",
        "canonical_prefsp": {"path": str(output), "sha256": sha_file(output), "size_bytes": output.stat().st_size},
        "source_ic1_authority": {
            "path": str(IC1_AUTHORITY_PATH),
            "sha256": sha_file(IC1_AUTHORITY_PATH),
            "canonical_ic1_prefsp_sha256": ic1_authority["canonical_prefsp"]["sha256"],
            "canonical_ic1_truth": "PAPER_A_IC1_FINITE_INTEGRATED_CANARY_PASS",
            "current_runtime_ic1_prefsp_not_used": True,
        },
        "source_authority_provenance": source_provenance,
        "physics_contract": ic2_contract,
        "monitor_contract": ic1_authority["monitor_contract"],
        "source_orientation": {
            "ic1": {"theta_deg": 90.0, "phi_deg": 0.0, "position_nm": [0.0, 0.0, -171.5]},
            "ic2": {"theta_deg": 90.0, "phi_deg": 90.0, "position_nm": [0.0, 0.0, -171.5]},
            "only_physics_change": "electric-dipole azimuth x to y",
        },
        "geometry_semantic_sha256": sha_obj(normalized_geometry),
        "physics_semantic_fingerprint": readback["physics_semantic_fingerprint"],
        "integrated_instrumentation_fingerprint": readback["integrated_instrumentation_fingerprint"],
        "comparison_to_ic1": {
            "geometry_domain_monitor_semantic_match": validation["geometry_domain_monitor_semantic_match"],
            "orientation_only_physics_delta": validation["orientation_only_physics_delta"],
            "ic1_physics_fingerprint": ic1_authority["physics_semantic_fingerprint"],
            "ic2_physics_fingerprint": readback["physics_semantic_fingerprint"],
            "ic1_instrumentation_fingerprint": ic1_authority["integrated_instrumentation_fingerprint"],
            "ic2_instrumentation_fingerprint": readback["integrated_instrumentation_fingerprint"],
        },
        "full_readback": readback,
        "v2_integration": {
            "parent_authority_path": str(AUTH / "paper_a_fdtd_physics_validity_gate_v2_instrumented.json"),
            "adapter_path": str(AUTH / "ic1_integrated_validity_adapter.json"),
            "time_probe": {"name": V2_TIME_PROBE, "position_nm": [0.0, 0.0, -100.0], "solver_run_called": False},
            "thresholds_preserved": True,
        },
        "production_runner": {
            "case_id": CASE_ID,
            "runner": "paper_a_broadband/scripts/ic2_production_runner_v1.py",
            "mpi_processes": 12,
            "threads_per_process": 1,
            "max_new_fdtd_entries": 1,
            "paper_a_max_active_fdtd": 1,
            "entered_true_no_auto_replay": True,
            "execute_requires_explicit_confirmation": True,
        },
        "authorization": {"ic2_authorized": True, "authorization_used": False, "new_fdtd_entries": 0},
        "solver_counters": counters,
        "timestamp_utc": now(),
    }
    write_json(AUTH / "ic2_solver_ready_prefsp_authority_v1.json", authority)
    write_json(AUTH / "ic2_solver_ready_prefsp_readback_v1.json", readback)
    audit = {
        "schema": "PAPER_A_IC2_SETUP_ONLY_AUDIT_V1",
        "status": "PASS_SOLVER_READY_PREFSP",
        "case_id": CASE_ID,
        "canonical_prefsp_sha256": sha_file(output),
        "canonical_prefsp_readback_valid": validation["all"],
        "validation": validation,
        "source_ic1_authority_sha256": sha_file(IC1_AUTHORITY_PATH),
        "source_ic1_prefsp_authority_sha256": ic1_authority["canonical_prefsp"]["sha256"],
        "actual_current_ic1_prefsp_not_used": True,
        "source_orientation_readback": readback["physics_semantic"]["source"],
        "geometry_semantic_sha256": sha_obj(normalized_geometry),
        "solver_counters": counters,
        "timestamp_utc": now(),
    }
    write_json(AUTH / "ic2_solver_ready_prefsp_audit_v1.json", audit)
    report = [
        "# IC2 setup-only pre-FSP audit",
        "",
        "Status: PASS_SOLVER_READY_PREFSP",
        f"Case: {CASE_ID}",
        "No FDTD/RCWA/ML solver was run; run() was not called and solver entry remains zero.",
        "",
        f"Canonical pre-FSP: {output}",
        f"Canonical SHA256: {sha_file(output)}",
        f"Physics semantic fingerprint: {readback['physics_semantic_fingerprint']}",
        f"Integrated instrumentation fingerprint: {readback['integrated_instrumentation_fingerprint']}",
        f"Geometry semantic SHA256: {sha_obj(normalized_geometry)}",
        "",
        "## IC1-to-IC2 comparison",
        "- Geometry, domain, materials, mesh, boundaries, z layout, and monitors match IC1 semantic authority.",
        "- Only source azimuth changes: theta=90 deg, phi=0 deg (IC1 x) to phi=90 deg (IC2 y).",
        "- Source position remains (0, 0, -171.5) nm; source grid remains 400-500 nm with 101 points.",
        "- The runtime IC1 pre-FSP observed after the completed run was not used as a parent.",
        "",
        "## Gate",
        "- Setup-only readback: PASS.",
        "- Native-M1 materials: PASS.",
        "- Solver counters: run_called=false, entered=0, active_fdtd=0, RCWA=0, ML=0.",
        "- New FDTD entry is authorized but remains unused until the separate production runner executes with explicit confirmation.",
        "",
    ]
    (REPORT / "ic2_solver_ready_prefsp_report.md").parent.mkdir(parents=True, exist_ok=True)
    (REPORT / "ic2_solver_ready_prefsp_report.md").write_text("\n".join(report), encoding="utf-8")
    return {"status": "PASS_SOLVER_READY_PREFSP", "case_id": CASE_ID, "validation": validation,
            "pre_fsp": str(output), "pre_fsp_sha256": sha_file(output), "solver_run_called": False, "solver_entered": 0}


def dry_run() -> dict[str, Any]:
    ic1 = load_ic1_authority()
    return {
        "status": "PASS_DRY_RUN",
        "case_id": CASE_ID,
        "source_ic1_authority": str(IC1_AUTHORITY_PATH),
        "source_ic1_prefsp_authority_sha256": ic1["canonical_prefsp"]["sha256"],
        "planned_source_orientation": {"theta_deg": 90.0, "phi_deg": 90.0},
        "planned_difference": "source azimuth only",
        "solver_run_called": False,
        "solver_entered": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("dry-run", "build"), required=True)
    parser.add_argument("--output", type=Path, default=CANONICAL_PREFSP)
    args = parser.parse_args()
    result = dry_run() if args.mode == "dry-run" else build(args.output)
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
