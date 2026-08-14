
from __future__ import annotations
import argparse
import csv
import hashlib
import importlib.util
import json
import os
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports/stage_h1c1b_broadband_adaptive"
OUT = ROOT / "outputs/lp_global_h_h1c1b"
MANIFEST_PATH = REPORT / "h1c1b_candidate_manifest.json"
ACCOUNTING_PATH = REPORT / "h1c1b_solver_accounting.json"
GRID = [450.0 + 0.5 * i for i in range(9)]
POLARIZATIONS = ("x", "y")
MAX_SUBRUNS = 48
TARGET_BRANCH = "work/lp-global-h-manifold-v1"
SLOT_REGISTRY = Path(r"D:projectapcd_global_fdtd_slot_registry_v1.json")

def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module

h1a = load_module(ROOT / "scripts/lp_global_h_h1c1a_broadband_v1.py", "h1c1b_h1a_support")

def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))

def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, default=str) + chr(10), encoding="utf-8")
    os.replace(tmp, path)

def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields or ["status"], extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    os.replace(tmp, path)

def sha256_obj(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()

def configure_support() -> None:
    h1a.REPORT = REPORT
    h1a.OUT = OUT
    h1a.RUNTIME = OUT / "runtime"
    h1a.MANIFEST_PATH = MANIFEST_PATH
    h1a.ACCOUNTING_PATH = ACCOUNTING_PATH
    h1a.GRID = GRID
    h1a.H_GLOBAL_NM = 550.0
    h1a.PERIOD_NM = 432.0
    h1a.MATERIAL = "APCD_TIO2_NATIVE_M1"
    h1a.PROJECTOR = [[1, 0], [0, 0]]
    h1a.POLARIZATIONS = POLARIZATIONS
    h1a.MAX_SUBRUNS = MAX_SUBRUNS
    h1a.TARGET_BRANCH = TARGET_BRANCH
    h1a.SLOT_REGISTRY = SLOT_REGISTRY
    h1a.BUILDER_VERSION = "h1c1b_broadband_unified_h550_builder_v2"
    h1a.EXTRACTION_CONVENTION = "transmission_side_full_period_coordinate_weighted_complex_G0_endpoint_dedup_periodic_reclosure_sqrtT_over_norm_arg_txx"

def manifest() -> dict[str, Any]:
    data = read_json(MANIFEST_PATH)
    frozen = dict(data)
    freeze = frozen.pop("freeze_sha256", None)
    if freeze != sha256_obj(frozen):
        raise RuntimeError("HARD_GATE_H1C1B_MANIFEST_FREEZE_HASH")
    if data.get("status") != "FROZEN_READY":
        raise RuntimeError("HARD_GATE_H1C1B_MANIFEST_STATUS")
    return data

def validate_manifest(data: dict[str, Any]) -> None:
    rows = data["candidates"]
    if len(rows) != 24 or len({row["exact_hash"] for row in rows}) != 24:
        raise RuntimeError("HARD_GATE_H1C1B_EXACT_24_UNIQUE")
    frontier = rows[:12]
    exploration = rows[12:]
    counts = {}
    for row in frontier:
        parent = row["proposal_audit"]["parent_reference_geometry"]
        counts[parent] = counts.get(parent, 0) + 1
    if counts != {"GLOBAL_018": 3, "GLOBAL_002": 3, "C": 2, "GLOBAL_006": 2, "GLOBAL_015": 2}:
        raise RuntimeError(f"HARD_GATE_H1C1B_FRONTIER_COVERAGE:{counts}")
    if len(exploration) != 12 or not all(row["role"] == "PHASE_GAP_GLOBAL_EXPLORATION" for row in exploration):
        raise RuntimeError("HARD_GATE_H1C1B_EXPLORATION_ROLE")
    if not all(row["legality"]["pass"] for row in rows):
        raise RuntimeError("HARD_GATE_H1C1B_LEGALITY")
    if any(row.get("solver_entered") or row.get("solver_replay") for row in rows):
        raise RuntimeError("HARD_GATE_H1C1B_PRE_ENTRY_STATE")
    if data.get("solver_budget_planned") != 48 or data.get("max_global_fdtd_concurrency") != 2 or data.get("max_active_fdtd_per_branch") != 1:
        raise RuntimeError("HARD_GATE_H1C1B_RUNTIME_CONTRACT")
    if data.get("processes_per_job") != 4 or data.get("threads_per_job") != 1:
        raise RuntimeError("HARD_GATE_H1C1B_RESOURCE_CONTRACT")
    for row in rows:
        identities = row["broadband_case_identity"]
        if set(identities) != {"x", "y"}:
            raise RuntimeError("HARD_GATE_H1C1B_XY_IDENTITIES")
        if any(identity["wavelength_grid_nm"] != GRID for identity in identities.values()):
            raise RuntimeError("HARD_GATE_H1C1B_GRID")
        if any(identity["exact_geometry_hash_sha256"] != row["exact_hash"] for identity in identities.values()):
            raise RuntimeError("HARD_GATE_H1C1B_HASH_IDENTITY")

def initial_accounting(data: dict[str, Any]) -> dict[str, Any]:
    if ACCOUNTING_PATH.exists():
        old = read_json(ACCOUNTING_PATH)
        if old.get("manifest_freeze_sha256") != data["freeze_sha256"] and old.get("solver_subruns_entered", 0):
            raise RuntimeError("HARD_GATE_H1C1B_ACCOUNTING_MANIFEST_MISMATCH_AFTER_ENTRY")
        return old
    cases = []
    for candidate in data["candidates"]:
        for pol in POLARIZATIONS:
            cases.append({"case_id": candidate["broadband_case_identity"][pol]["case_uid"], "geometry_uid": candidate["geometry_uid"], "exact_hash": candidate["exact_hash"], "polarization": pol, "planned": True, "attempted": False, "solver_entered": False, "accepted": False, "recovered": False, "quarantined": False})
    payload = {"schema": "H1C1B_SOLVER_ACCOUNTING_V1", "stage": "H1C-1B", "manifest_freeze_sha256": data["freeze_sha256"], "solver_budget_planned": MAX_SUBRUNS, "solver_subruns_entered": 0, "solver_subruns_accepted": 0, "H_global_nm": 550.0, "wavelength_grid_nm": GRID, "max_global_fdtd_concurrency": 2, "max_active_fdtd_per_branch": 1, "processes_per_job": 4, "threads_per_job": 1, "rcwa_consumes_fdtd_slot": False, "cases": cases, "solver_entries": [], "status": "PLANNED"}
    write_json(ACCOUNTING_PATH, payload)
    return payload

def preflight() -> dict[str, Any]:
    configure_support()
    data = manifest()
    validate_manifest(data)
    accounting = initial_accounting(data)
    result = {"status": "H1C1B_PREFLIGHT_PASS", "manifest_freeze_sha256": data["freeze_sha256"], "candidate_count": 24, "frontier_count": 12, "exploration_count": 12, "planned_formal_subruns": MAX_SUBRUNS, "solver_entered": accounting.get("solver_subruns_entered", 0), "max_global_fdtd_concurrency": 2, "max_active_fdtd_per_branch": 1, "processes_per_job": 4, "threads_per_job": 1}
    write_json(REPORT / "h1c1b_preflight.json", result)
    return result

def setup_check() -> dict[str, Any]:
    configure_support()
    data = manifest()
    validate_manifest(data)
    initial_accounting(data)
    result = h1a.setup_check(data)
    result.update({"stage": "H1C-1B", "solver_entered": False, "solver_run_called": False})
    write_json(REPORT / "h1c1b_setup_check.json", result)
    return result

def execute() -> dict[str, Any]:
    configure_support()
    data = manifest()
    validate_manifest(data)
    initial_accounting(data)
    setup = read_json(REPORT / "h1c1b_setup_check.json")
    if setup.get("solver_entered") or setup.get("solver_run_called") or not setup.get("reload_gate", {}).get("pass"):
        raise RuntimeError("HARD_GATE_H1C1B_SETUP_CHECK")
    runtime = h1a.load_runtime()
    slot = load_module(ROOT / "scripts/apcd_global_fdtd_slot_v1.py", "h1c1b_slot")
    scheduler = slot.GlobalSlotScheduler(SLOT_REGISTRY)
    results = []
    for candidate in data["candidates"]:
        for pol in POLARIZATIONS:
            result = h1a.run_case(runtime, candidate, pol, data, scheduler)
            item = {"case_id": candidate["broadband_case_identity"][pol]["case_uid"], "geometry_uid": candidate["geometry_uid"], "polarization": pol, "status": result.get("status"), "solver_entered": result.get("solver_entered", False), "accepted": result.get("status") == "ACCEPTED"}
            results.append(item)
            print(json.dumps(item, ensure_ascii=False), flush=True)
    write_json(REPORT / "h1c1b_execution_results.json", {"stage": "H1C-1B", "results": results})
    return {"status": "H1C1B_EXECUTION_RETURNED", "results": results}

def build_registry(data: dict[str, Any], full_rows: list[dict[str, Any]]) -> dict[str, Any]:
    old = read_json(ROOT / "reports/stage_h1c1a_broadband_global/lp_hf_authoritative_label_registry_v1.json")
    before = list(old.get("rows", []))
    before_hashes = {row.get("exact_hash") for row in before}
    new = []
    for row in full_rows:
        item = dict(row)
        item.update({"ml_eligible": True, "ml_admitted": False, "split": "UNASSIGNED", "spectral_scope": "BROADBAND_9NM_GRID"})
        if item["exact_hash"] in before_hashes:
            raise RuntimeError(f"HARD_GATE_H1C1B_REGISTRY_DUPLICATE:{item['exact_hash']}")
        new.append(item)
    combined = before + new
    snapshot = {"schema": "LP_HF_AUTHORITATIVE_LABEL_REGISTRY_V1", "stage": "H1C-1B_APPEND_SNAPSHOT", "historical_row_count": len(before), "new_broadband_rows": len(new), "row_count": len(combined), "rows": combined, "ml_eligible_all": all(row.get("ml_eligible") for row in combined), "ml_admitted_false_all": all(not row.get("ml_admitted") for row in combined), "split_unassigned_all": all(row.get("split") == "UNASSIGNED" for row in combined)}
    write_json(REPORT / "h1c1b_authoritative_label_registry_v1.json", snapshot)
    write_csv(REPORT / "h1c1b_authoritative_label_registry_v1.csv", combined)
    audit = {"schema": "H1C1B_ML_REGISTRY_AUDIT_V1", "status": "PASS", "canonical_registry_before_rows": len(before), "new_formal_full_jones_rows": len(new), "canonical_registry_after_rows": len(combined), "new_formal_geometry_count": len({row["exact_hash"] for row in new}), "ml_eligible_all": snapshot["ml_eligible_all"], "ml_admitted_false_all": snapshot["ml_admitted_false_all"], "split_unassigned_all": snapshot["split_unassigned_all"], "registry_append_only": True, "new_rows_only_from_formal_accepted_full_jones": True, "expected_max_if_24_complete": 425}
    write_json(REPORT / "h1c1b_ml_registry_audit.json", audit)
    return audit

def postprocess() -> dict[str, Any]:
    configure_support()
    data = manifest()
    validate_manifest(data)
    accounting = read_json(ACCOUNTING_PATH)
    full_rows, summaries, result_by_uid = h1a.assemble_rows(data, accounting)
    for row in full_rows:
        row.update({"source_stage": "H1C1B_BROADBAND_ADAPTIVE", "ml_eligible": True, "ml_admitted": False, "split": "UNASSIGNED"})
    for row in summaries:
        row.update({"source_stage": "H1C1B_BROADBAND_ADAPTIVE", "strict_definition": "9/9 projector pass only", "near_miss_promoted_to_strict": False})
    write_csv(REPORT / "h1c1b_broadband_full_jones.csv", full_rows)
    write_csv(REPORT / "h1c1b_geometry_broadband_summary.csv", summaries)
    phase = h1a.phase_islands(summaries, result_by_uid)
    bins = h1a.six_bin_screening(summaries, result_by_uid)
    write_json(REPORT / "h1c1b_phase_islands.json", phase)
    write_json(REPORT / "h1c1b_six_bin_screening.json", bins)
    frontier = []
    exploration = []
    near_miss = []
    for summary in summaries:
        candidate = next(row for row in data["candidates"] if row["geometry_uid"] == summary["geometry_uid"])
        effect = {"geometry_uid": summary["geometry_uid"], "exact_hash": summary["exact_hash"], "subrole": candidate["subrole"], "parent_reference_geometry": candidate["proposal_audit"]["parent_reference_geometry"], "broadband_status": summary["broadband_status"], "projector_pass_count_9": summary["projector_pass_count"], "failed_wavelengths": summary["failed_wavelengths"], "phase_450_deg": (summary.get("phase_trajectory_deg") or [None])[0], "near_miss_promoted_to_strict": False}
        (frontier if candidate["role"] == "SELECTIVITY_FRONTIER" else exploration).append(effect)
        if summary["broadband_status"] != "BROADBAND_PROJECTOR_COMPATIBLE_STRICT":
            near_miss.append(effect)
    write_csv(REPORT / "h1c1b_frontier_effects.csv", frontier)
    write_csv(REPORT / "h1c1b_global_exploration_effects.csv", exploration)
    write_json(REPORT / "h1c1b_near_miss_bank.json", {"schema": "H1C1B_NEAR_MISS_BANK_V1", "strict_definition": "9/9 projector pass only", "near_miss_never_promoted": True, "rows": near_miss})
    registry = build_registry(data, full_rows)
    strict_before = read_json(ROOT / "reports/stage_h1c1a_broadband_global/h1c1a_final.json").get("strict_candidate_count", 2)
    strict_batch = sum(summary.get("broadband_status") == "BROADBAND_PROJECTOR_COMPATIBLE_STRICT" for summary in summaries); strict_after = strict_before + strict_batch
    category_counts = {key: sum(summary.get("broadband_status") == key for summary in summaries) for key in ("BROADBAND_PROJECTOR_COMPATIBLE_STRICT", "CENTER_ONLY_COMPATIBLE", "PARTIALLY_COMPATIBLE", "INCOMPATIBLE")}
    entered = accounting.get("solver_subruns_entered", 0)
    accepted = accounting.get("solver_subruns_accepted", 0)
    quarantined = sum(bool(row.get("quarantined")) for row in accounting.get("cases", []))
    if accepted == MAX_SUBRUNS:
        outcome = "H1C1B_STRICT_COUNT_INCREASED_SAME_PHASE_REGIONS" if strict_after > strict_before else "H1C1B_NO_NEW_STRICT_BROADBAND_CANDIDATES"
        status = "H1C1B_COMPLETE"
    else:
        outcome = "H1C1B_INCONCLUSIVE"
        status = "H1C1B_PARTIAL_DATA_PRESERVED"
    quarantine_cases = [{"case_id": case["case_id"], "geometry_uid": case["geometry_uid"], "polarization": case["polarization"], "status": case.get("status"), "solver_entered": case.get("solver_entered"), "solver_replay": False, "error": read_json(OUT / "runtime" / "cases" / case["case_id"] / "attempt_provenance.json").get("error")} for case in accounting.get("cases", []) if case.get("quarantined")] ; final = {"schema": "H1C1B_FINAL_V1", "status": status, "stage": "H1C-1B", "branch": TARGET_BRANCH, "manifest_freeze_sha256": data["freeze_sha256"], "planned_geometries": 24, "planned_frontier": 12, "planned_exploration": 12, "planned_formal_subruns": 48, "entered_formal_subruns": entered, "accepted_formal_subruns": accepted, "quarantined_entered_subruns": quarantined, "quarantine_cases": quarantine_cases, "max_global_fdtd_concurrency": 2, "max_active_fdtd_per_branch": 1, "processes_per_job": 4, "threads_per_job": 1, "strict_count_before": strict_before, "strict_count_h1c1b_batch": strict_batch, "strict_count_after_h1c1b": strict_after, "strict_count_delta": strict_after - strict_before, "category_counts_h1c1b": category_counts, "new_strict_geometry_uids": [summary["geometry_uid"] for summary in summaries if summary.get("broadband_status") == "BROADBAND_PROJECTOR_COMPATIBLE_STRICT"], "frontier_effects": frontier, "exploration_effects": exploration, "phase_islands": phase, "six_bin_screening": bins, "ml_registry_audit": registry, "solver_replay": False, "automatic_next_stage": False, "hard_gates": [], "expected_outcome": outcome}
    if entered > 48:
        final["hard_gates"].append("HARD_GATE_SOLVER_BUDGET_EXCEEDED")
    write_json(REPORT / "h1c1b_final.json", final)
    lines = ["# Stage H1C-1B H550 Broadband Adaptive Global Full-Dimer", "", f"- Status: {status}; outcome: {outcome}.", f"- Exact geometries: 24 (12 selectivity frontier + 12 phase-gap/global exploration).", f"- Frozen grid: {GRID} nm; one broadband solve per polarization returns all 9 points.", f"- Formal subruns planned/entered/accepted/quarantined: 48/{entered}/{accepted}/{quarantined}.", f"- Strict before / H1C-1B batch / cumulative after: {strict_before} / {strict_batch} / {strict_after}; near-miss is never promoted.", f"- Category counts: {category_counts}.", "- FDTD concurrency: global 2, LP branch 1; resources 4 MPI x 1 thread; RCWA excluded from FDTD count.", f"- ML registry: {registry['canonical_registry_before_rows']} + {registry['new_formal_full_jones_rows']} = {registry['canonical_registry_after_rows']}; ml_admitted=false for all.", "- No automatic H1C-1C, ML training, inverse design, K6, constituent solver, or domain expansion.", "", "Artifacts are listed in the H1C1B report directory."]
    (REPORT / "h1c1b_summary.md").write_text(chr(10).join(lines) + chr(10), encoding="utf-8")
    return final

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("preflight", "setup-check", "execute", "postprocess"))
    args = parser.parse_args()
    result = {"preflight": preflight, "setup-check": setup_check, "execute": execute, "postprocess": postprocess}[args.mode]()
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
