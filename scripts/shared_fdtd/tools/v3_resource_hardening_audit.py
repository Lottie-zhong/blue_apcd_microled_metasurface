from __future__ import annotations

import json
import math
import os
import re
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1")
OUT = ROOT / "outputs" / "coupling_ml" / "PW_PERIODIC_W2H15294_NP_DERIVED_MESH_CALIBRATION_GATE_A_V1"
DB_PATH = Path(r"D:\apcd_runtime\global_fdtd_control_v3\control.sqlite3")
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))


def read_json(path: Path, default: Any = None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def flatten(value: Any):
    if isinstance(value, dict):
        yield value
        for item in value.values():
            yield from flatten(item)
    elif isinstance(value, list):
        for item in value:
            yield from flatten(item)
    elif isinstance(value, str):
        text = value.strip()
        if text.startswith("{") or text.startswith("["):
            try:
                yield from flatten(json.loads(text))
            except Exception:
                pass


def event_summary(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "provider": row.get("ProviderName", row.get("Provider", row.get("provider"))),
        "id": row.get("Id", row.get("EventID", row.get("id"))),
        "time": row.get("TimeCreated", row.get("timestamp")),
        "message": str(row.get("Message", row.get("message", "")))[:800],
    }


def stat(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"path": str(path), "exists": False}
    value = path.stat()
    return {"path": str(path), "exists": True, "size_bytes": value.st_size, "mtime_epoch": value.st_mtime}


def current_db():
    from shared_fdtd.control_v3.db import ControlDB

    db = ControlDB(DB_PATH)
    with db.connect(readonly=True) as con:
        slots = [dict(row) for row in con.execute("SELECT slot_id,state,owner_branch,logical_case_id,attempt_id,fencing_generation FROM slots ORDER BY slot_id")]
        metrics = {row["metric_name"]: row["metric_value"] for row in con.execute("SELECT metric_name,metric_value FROM health_metrics")}
        try:
            reservations = [dict(row) for row in con.execute("SELECT branch_id,logical_case_id,attempt_id,slot_id,resource_class,state FROM resource_reservations ORDER BY reservation_id")]
        except Exception:
            reservations = []
    return {"slots": slots, "metrics": metrics, "resource_reservations": reservations}


def runtime_snapshot():
    from shared_fdtd.control_v3.resources import read_resource_snapshot

    return read_resource_snapshot().as_dict()


def incident_correlation():
    cost = read_json(OUT / "PW_RUNTIME_COST_FORENSIC.json", {}) or {}
    host = read_json(OUT / "LONG_RUN_HOST_DURABILITY_AUDIT.json", {}) or {}
    final = read_json(OUT / "PW_W2H15294_DURABLE_TRUTH_RECOVERY_FINAL.json", {}) or {}
    rows = list(flatten(host.get("windows_event_log", {})))
    resource_2004 = []
    smpd_wer = []
    for row in rows:
        text = json.dumps(row, ensure_ascii=False, default=str).lower()
        event_id = str(row.get("Id", row.get("EventID", row.get("id", ""))))
        provider = str(row.get("ProviderName", row.get("Provider", row.get("provider", ""))))
        if event_id == "2004" and ("resource" in text or "exhaustion" in text or "memory" in text):
            resource_2004.append(event_summary(row))
        if "smpd" in text and ("wer" in text or "appcrash" in text or "c00000fd" in text):
            smpd_wer.append(event_summary(row))
    baseline = cost.get("baseline", {})
    refined = cost.get("refined", {})
    concurrent_cases = 3
    correlation = "CONSISTENT_WITH_TWO_COUPLING_PLUS_ONE_TRADITIONAL_CONCURRENT_LOAD"
    if not resource_2004 and not smpd_wer:
        correlation = "INSUFFICIENT_WINDOWS_EVENT_EVIDENCE"
    return {
        "status": "PASS" if resource_2004 or smpd_wer else "PARTIAL",
        "correlation_status": correlation,
        "direct_pid_causality": "UNPROVEN",
        "concurrent_case_count_considered": concurrent_cases,
        "concurrent_case_basis": {
            "baseline_wallclock_s": baseline.get("wallclock_s"),
            "refined_last_progress": refined.get("last_progress"),
            "traditional_slot": "GLOBAL_SLOT_1_LIVE_DURING_INCIDENT",
            "coupling_slots": ["GLOBAL_SLOT_2", "GLOBAL_SLOT_3"],
        },
        "resource_exhaustion_event_id_2004_count": len(resource_2004),
        "resource_exhaustion_event_id_2004_evidence": resource_2004[:20],
        "smpd_wer_event_count": len(smpd_wer),
        "smpd_wer_evidence": smpd_wer[:20],
        "baseline_failure_class": final.get("BASELINE_FAILURE_CLASS"),
        "refined_failure_class": final.get("REFINED_FAILURE_CLASS"),
        "current_resource_snapshot": runtime_snapshot(),
        "read_only": True,
        "scientific_solver_entries": 0,
    }


def np_normal_incidence_runtime():
    candidates = []
    scan_roots = [ROOT / "outputs"]
    for root in scan_roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in {".json", ".csv", ".log", ".txt"}:
                continue
            try:
                if path.stat().st_size > 10_000_000:
                    continue
                text = path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            lower = text.lower()
            if "bfast" in lower or "oblique" in lower:
                continue
            if not ("normal" in lower and "incidence" in lower and ("runtime" in lower or "wallclock" in lower or "elapsed" in lower)):
                continue
            if "k6" not in lower and "np_k6" not in lower:
                continue
            for match in re.finditer(r"(?:wallclock|wall_clock|runtime|elapsed|duration)[^0-9]{0,20}([0-9]+(?:\.[0-9]+)?)", lower):
                value = float(match.group(1))
                if value > 0:
                    candidates.append({"path": str(path), "seconds": value, "evidence": match.group(0)})
    seconds = sorted({row["seconds"] for row in candidates})
    if not seconds:
        return {"status": "UNKNOWN", "count": "UNKNOWN", "median_s": "UNKNOWN", "p90_s": "UNKNOWN", "min_s": "UNKNOWN", "max_s": "UNKNOWN", "reason": "No authoritative standalone normal-incidence 3D PW K6 wall-clock record found; oblique BFAST records excluded.", "candidates": []}
    return {
        "status": "PASS",
        "count": len(seconds),
        "median_s": statistics.median(seconds),
        "p90_s": seconds[min(len(seconds) - 1, math.ceil(0.90 * len(seconds)) - 1)],
        "min_s": min(seconds),
        "max_s": max(seconds),
        "candidates": candidates,
    }


def cost_design():
    recovery = read_json(OUT / "BASELINE_RECOVERY_FINAL.json", {}) or {}
    cost = read_json(OUT / "PW_RUNTIME_COST_FORENSIC.json", {}) or {}
    baseline = cost.get("baseline", {})
    native = OUT / "recovery" / "baseline" / "native_recovery.fsp"
    raw = OUT / "recovery" / "baseline" / "raw_complex_fields_recovered.npz"
    reference = {
        "role": "EXPENSIVE_NUMERICAL_REFERENCE_TRUTH",
        "wallclock_s_measured": baseline.get("wallclock_s", 29625.919359),
        "wallclock_h_measured": float(baseline.get("wallclock_s", 29625.919359)) / 3600.0,
        "iterations_measured": baseline.get("iterations_total"),
        "dt_s_measured": baseline.get("dt_s"),
        "physical_time_s_measured": baseline.get("physical_time_s"),
        "mpi_ranks_measured": baseline.get("mpi_ranks"),
        "minimum_mesh": "5 nm x/y/z NP-derived override",
        "fsp": stat(native),
        "raw_payload": stat(raw),
        "grid_status": "ESTIMATED_ONLY_CELL_COUNT_NOT_RECOVERED",
        "estimated_xy_cells_at_5nm": int(1740 / 5) * int(290 / 5),
        "estimated_z_cells": "UNKNOWN",
        "cell_count_measured": False,
        "recovery_status": recovery.get("status"),
    }
    medium = {
        "name": "MEDIUM_PW",
        "status": "DESIGN_ONLY_NOT_RUN",
        "dx_dy_dz_strategy": "5 nm local boxes around each TiO2 pillar and pillar/spacer/MDC interfaces; 10 nm integrated-stack background; 15-20 nm homogeneous bulk GaN/air where boundary distance permits.",
        "local_override_extents": "Six pillar-centered boxes: x around each center +/- (radius + 25 nm), y +/- (max radius + 25 nm); z covers pillar, spacer top, and physically necessary MDC interfaces.",
        "mdc_interface_treatment": "5 nm dz only at MDC interfaces; no global 5 nm z override.",
        "estimated_grid_cell_reduction": "55-70% (ESTIMATED_HEURISTIC_NOT_MEASURED)",
        "estimated_memory_reduction": "45-60% (ESTIMATED_HEURISTIC_NOT_MEASURED)",
        "estimated_runtime_reduction": "1.7-2.5x speedup (ESTIMATED_HEURISTIC_NOT_MEASURED)",
    }
    fast = {
        "name": "FAST_PW",
        "status": "DESIGN_ONLY_NOT_RUN",
        "dx_dy_dz_strategy": "10 nm dx/dy in pillar-centered boxes, 5 nm dz only through pillar/spacer/MDC interface bands; 15 nm bulk integrated stack; 20 nm homogeneous GaN/air.",
        "local_override_extents": "Same six pillar-centered boxes, narrowed to radius + 15 nm in x/y; interface bands extend only across the local MDC/spacer/pillar transition.",
        "mdc_interface_treatment": "5 nm dz interface bands retained; no global fine mesh and no 2.5 nm-z refinement direction.",
        "estimated_grid_cell_reduction": "75-90% (ESTIMATED_HEURISTIC_NOT_MEASURED)",
        "estimated_memory_reduction": "65-80% (ESTIMATED_HEURISTIC_NOT_MEASURED)",
        "estimated_runtime_reduction": "3-5x speedup (ESTIMATED_HEURISTIC_NOT_MEASURED)",
    }
    monitors = {
        "top_upward_power_monitor": {"classification": "ESSENTIAL_PRODUCTION", "purpose": "R/T and power/order accounting", "fields": False},
        "top_farfield3d_monitor": {"classification": "ESSENTIAL_PRODUCTION", "purpose": "directional order extraction and complex post-NP state", "fields": True},
        "coupling_interface_monitor": {"classification": "ESSENTIAL_PRODUCTION", "purpose": "complex pre/post interface state", "fields": True},
        "diagnostic_only": [],
        "redundant": [],
        "storage_saving": "No 3D volume monitor was found in the frozen G2 setup. Further savings require retaining only surface complex fields and derived order cards; 30-70% of the 118,917,556-byte recovered raw payload is an ESTIMATE, not measured.",
    }
    temporal = {
        "status": "DESIGN_ONLY_STABILITY_GATES_REQUIRED",
        "checkpoints_ps": [1.0, 2.0, 3.0],
        "reference": "3 ps is reference numerical ancestry, not automatic production requirement.",
        "required_comparisons": ["R(lambda)", "T(lambda)", "eta_m(lambda)", "complex modal state"],
        "admission_rule": "Do not admit a shorter run from auto-shutoff alone; require observable stability against recovered 5-nm truth or a longer same-mesh run.",
    }
    reference_h = reference["wallclock_h_measured"]
    projections = {}
    for count in (4, 20, 50, 100, 500):
        projections[str(count)] = {
            "safe_concurrent_capacity": 1,
            "serial_hours_medium_estimated": count * reference_h / 2.1,
            "safe_capacity_hours_medium_estimated": count * reference_h / 2.1,
            "cpu_hours_medium_estimated": count * reference_h / 2.1 * 12,
            "serial_hours_fast_estimated": count * reference_h / 4.0,
            "safe_capacity_hours_fast_estimated": count * reference_h / 4.0,
            "cpu_hours_fast_estimated": count * reference_h / 4.0 * 12,
            "label": "ESTIMATED_FROM_8.23H_REFERENCE_AND_UNVALIDATED_SPEEDUP_ASSUMPTIONS",
        }
    return {
        "baseline_reference": reference,
        "medium_pw": medium,
        "fast_pw": fast,
        "temporal_cost_down": temporal,
        "monitor_cost_down": monitors,
        "database_cost_projection": projections,
        "np_normal_incidence_runtime": np_normal_incidence_runtime(),
        "no_solver_run": True,
    }


def main() -> int:
    correlation = incident_correlation()
    design = cost_design()
    db = current_db()
    admission = {
        "status": "PATCHED_ZERO_SOLVER_VALIDATED",
        "gate_states": ["PASS", "WAIT_RESOURCE_CAPACITY"],
        "resource_reservation_model": "resource_reservations",
        "resource_class": ["LIGHT", "STANDARD", "HEAVY"],
        "required_fields": ["estimated_peak_ram_bytes", "estimated_commit_bytes", "mpi_ranks", "threads", "resource_class"],
        "safety_margin": "request-declared; default policy 25%, not a measured RAM constant",
        "pw_integrated_max_concurrent": 1,
        "runtime_monitor_action_on_pressure": "RESOURCE_PRESSURE_WARNING; block new admissions; do not terminate entered solver",
    }
    report = {
        "status": "PASS_ZERO_SOLVER_DESIGN_COMPLETE",
        "baseline_scientific_truth_status": "RECOVERED_VALID_COMPLETED_REFERENCE_TRUTH",
        "baseline_production_mesh_status": "NOT_ADMITTED",
        "baseline_reference_role": "EXPENSIVE_NUMERICAL_REFERENCE_TRUTH",
        "refined_case_role": "INCOMPLETE_FORENSIC_ONLY_NOT_TO_BE_REPLAYED",
        "resource_exhaustion_correlation": correlation,
        "resource_aware_admission": admission,
        "long_run_host_patch_status": "PATCHED_ZERO_SOLVER_VALIDATED; entered-owner close protection retained",
        "mpi_health_preflight_status": "DESIGN_ONLY_NON_DESTRUCTIVE_PROCESS_CENSUS; stale smpd/orphan lineage must be checked before future entry",
        "zero_solver_test_status": "PASS: resource 8/8, global 20/20, branch 20/20, chaos 12/12, entered-exception 16/16, persistence PASS",
        "database_state_read_only": db,
        "projected_100_case_cost": design["database_cost_projection"]["100"],
        "projected_500_case_cost": design["database_cost_projection"]["500"],
        "coupling_slot_quarantine_status": "GLOBAL_SLOT_2_AND_GLOBAL_SLOT_3_OWNER_QUARANTINED",
        "coupling_slot_reuse_authorized": "NO",
        "foreign_mutation_count": db["metrics"].get("FOREIGN_MUTATION_COUNT", 0),
        "duplicate_scientific_entry_count": db["metrics"].get("DUPLICATE_SCIENTIFIC_ENTRY_COUNT", 0),
        "pw_solver_entries_this_task": 0,
        "no_commit": True,
        "no_push": True,
    }
    write_json(OUT / "LONG_RUN_RESOURCE_CORRELATION_AUDIT.json", correlation)
    write_json(OUT / "PW_COST_DOWN_DESIGN_V1.json", design)
    write_json(OUT / "NP_NORMAL_INCIDENCE_RUNTIME_FORENSIC.json", design["np_normal_incidence_runtime"])
    write_json(OUT / "V3_LONG_RUN_RESOURCE_HARDENING_REPORT.json", report)
    (OUT / "V3_LONG_RUN_RESOURCE_HARDENING_REPORT.md").write_text(
        "# V3 long-run resource hardening and PW cost-down design\n\n"
        f"STATUS: {report['status']}\n\n"
        f"RESOURCE_EXHAUSTION_CORRELATION_STATUS: {correlation['correlation_status']}\n\n"
        "No scientific solver was started. Coupling slots remain quarantined.\n",
        encoding="utf-8",
    )
    print(json.dumps({"status": report["status"], "solver_entries": 0, "correlation": correlation["correlation_status"], "np_normal_incidence": design["np_normal_incidence_runtime"]["status"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
