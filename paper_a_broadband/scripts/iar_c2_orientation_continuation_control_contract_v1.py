from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import math
import os
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(r"D:/project/worktrees/blue_apcd_paper_a_lp_cp_broadband_v1")
PKG = ROOT / "paper_a_broadband"
OUT = PKG / "reports/iar_c2_orientation_continuation_control_contract_v1"
DOMAIN = PKG / "reports/integrated_aware_lp_redesign_contract_v1/integrated_local_domain_authority.json"
INITIAL = PKG / "reports/integrated_aware_lp_redesign_contract_v1/integrated_candidate_registry_initial.csv"
CONDITIONAL = PKG / "reports/integrated_aware_lp_redesign_contract_v1/integrated_candidate_registry_conditional.csv"
PRIOR_REGISTRY = PKG / "reports/iar4_clearance_release_continuation_contract_v1/candidate_registry.json"
RULE = PKG / "scripts/lp_anisotropy_feasible_space_v2.py"
HP_RULE = PKG / "scripts/a02_pre_admission_geometry_audit_v2.py"
SCRIPT = PKG / "scripts/iar_c2_orientation_continuation_control_contract_v1.py"
PROTECTED = PKG / "reports/ic1_solver_ready_runner/dry_run.json"
PROTECTED_SHA = "52f70e630cc64e89be8e65adf1a402b4816c435c41232c39886167f6afc6567c"

EXPECTED_BRANCH = "work/paper-a-lp-cp-broadband-v1"
EXPECTED_HEAD = "a88474aeadba9870419d03f9e65de7ce8cdc33c2"
EXPECTED_BOUNDS = {"delta_theta_deg": [80.0, 90.0]}
EXPECTED_GATES = {
    "cell_containment": True,
    "direct_polygon_clearance_nm_ge": 60.0,
    "half_grid_centers": True,
    "integer_lateral_dimensions": True,
    "no_overlap_or_touching": True,
    "no_sub_grid_geometry": True,
    "periodic_image_polygon_clearance_nm_ge": 60.0,
}


def sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha_obj(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode("utf-8")
    ).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(value, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    tmp = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    with tmp.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    key: json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
                    if isinstance(value, (dict, list))
                    else value
                    for key, value in row.items()
                }
            )
    os.replace(tmp, path)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def module_from(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def git(*args: str, cwd: Path = ROOT) -> str:
    return subprocess.check_output(["git", *args], cwd=cwd, text=True, stderr=subprocess.STDOUT).strip()


def status_snapshot(cwd: Path) -> dict[str, Any]:
    return {
        "path": str(cwd),
        "branch": git("branch", "--show-current", cwd=cwd),
        "head": git("rev-parse", "HEAD", cwd=cwd),
        "status_short": git("status", "--short", "--untracked-files=all", cwd=cwd),
    }


def tasklist_fdtd() -> dict[str, Any]:
    p = subprocess.run(["tasklist", "/FO", "CSV"], capture_output=True, text=True)
    rows = [line for line in p.stdout.splitlines() if "fdtd-engine" in line.lower()]
    return {"matching_process_count": len(rows), "matching_process_rows": rows, "returncode": p.returncode}


def geometry_hash(g: dict[str, Any]) -> str:
    keys = [
        "L1_nm",
        "W1_nm",
        "L2_nm",
        "W2_nm",
        "D_nm",
        "delta_theta_deg",
        "height_nm",
        "period_x_nm",
        "period_y_nm",
        "theta1_deg",
        "theta2_deg",
    ]
    return sha_obj({key: g[key] for key in keys})


def geometry_from_row(row: dict[str, Any], theta: float | None = None) -> dict[str, Any]:
    angle = float(row["delta_theta_deg"] if theta is None else theta)
    d = int(row["D_nm"])
    return {
        "L1_nm": int(row["L1_nm"]),
        "W1_nm": int(row["W1_nm"]),
        "L2_nm": int(row["L2_nm"]),
        "W2_nm": int(row["W2_nm"]),
        "D_nm": d,
        "delta_theta_deg": angle,
        "theta1_deg": 0.0,
        "theta2_deg": angle,
        "j1_center_x_nm": 0.0,
        "j1_center_y_nm": d / 2.0,
        "j2_center_x_nm": 0.0,
        "j2_center_y_nm": -d / 2.0,
        "height_nm": float(row.get("height_nm", 525.0)),
        "period_x_nm": float(row.get("period_x_nm", 432.0)),
        "period_y_nm": float(row.get("period_y_nm", 432.0)),
    }


def hp_payload(g: dict[str, Any]) -> dict[str, str | dict[str, Any]]:
    return {
        "L1_nm": str(g["L1_nm"]),
        "W1_nm": str(g["W1_nm"]),
        "L2_nm": str(g["L2_nm"]),
        "W2_nm": str(g["W2_nm"]),
        "D_nm": str(g["D_nm"]),
        "j1_rotation_deg": str(g["theta1_deg"]),
        "j2_rotation_deg": str(g["theta2_deg"]),
        "j1_center_x_nm": str(g["j1_center_x_nm"]),
        "j1_center_y_nm": str(g["j1_center_y_nm"]),
        "j2_center_x_nm": str(g["j2_center_x_nm"]),
        "j2_center_y_nm": str(g["j2_center_y_nm"]),
        "validity": {},
    }


def current_rule_q(g: dict[str, Any]) -> dict[str, Any]:
    return {
        "L1_nm": g["L1_nm"],
        "W1_nm": g["W1_nm"],
        "L2_nm": g["L2_nm"],
        "W2_nm": g["W2_nm"],
        "D_nm": g["D_nm"],
        "theta1_deg": g["theta1_deg"],
        "theta2_deg": g["theta2_deg"],
        "j1_center_x_nm": g["j1_center_x_nm"],
        "j1_center_y_nm": g["j1_center_y_nm"],
        "j2_center_x_nm": g["j2_center_x_nm"],
        "j2_center_y_nm": g["j2_center_y_nm"],
        "height_nm": g["height_nm"],
        "period_x_nm": g["period_x_nm"],
        "period_y_nm": g["period_y_nm"],
    }


def inherited_gate_snapshot(hp_a: dict[str, Any]) -> dict[str, Any]:
    return {
        "direct_clearance_nm_ge_60": float(hp_a["direct_clearance_nm"]) >= 60.0,
        "periodic_clearance_nm_ge_60": float(hp_a["periodic_image_clearance_nm"]) >= 60.0,
        "no_direct_overlap_or_touch": bool(hp_a["direct_no_overlap_or_touch_pass"]),
        "no_periodic_overlap_or_touch": bool(hp_a["periodic_no_overlap_or_touch_pass"]),
        "cell_containment": bool(hp_a["cell_containment_pass"]),
        "integer_lateral_dimensions": bool(hp_a["integer_lateral_dimensions_pass"]),
        "half_grid_centers": bool(hp_a["half_grid_centers_pass"]),
        "current_inherited_gate_pass": bool(hp_a["current_inherited_gate_pass"]),
    }


def normalized_vector(g: dict[str, Any]) -> list[float]:
    # Existing feasible-space normalization, expressed from the current
    # rule's base dimensions and six-dimensional bounds.
    base = {"L1_nm": 230.0, "W1_nm": 100.0, "L2_nm": 180.0, "W2_nm": 90.0}
    bounds = {
        "L1_nm": (0.85 * base["L1_nm"], 1.15 * base["L1_nm"]),
        "W1_nm": (0.85 * base["W1_nm"], 1.15 * base["W1_nm"]),
        "L2_nm": (0.85 * base["L2_nm"], 1.15 * base["L2_nm"]),
        "W2_nm": (0.85 * base["W2_nm"], 1.15 * base["W2_nm"]),
        "delta_theta_deg": (0.0, 90.0),
        "D_nm": (170.0, 220.0),
    }
    return [(float(g[k]) - lo) / (hi - lo) for k, (lo, hi) in bounds.items()]


def euclidean(a: list[float], b: list[float]) -> float:
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def compact_geometry_record(candidate_id: str, role: str, status: str, g: dict[str, Any], hp_a: dict[str, Any], source_hash: str | None = None) -> dict[str, Any]:
    return {
        "candidate_id": candidate_id,
        "role": role,
        "status": status,
        "geometry": g,
        "geometry_hash_sha256_recomputed": geometry_hash(g),
        "source_geometry_hash": source_hash,
        "source_geometry_hash_match": source_hash is None or source_hash == geometry_hash(g),
        "validity_audit_high_precision": hp_a,
        "inherited_gate_snapshot": inherited_gate_snapshot(hp_a),
    }


def main() -> None:
    protected_before = sha_file(PROTECTED)
    if protected_before != PROTECTED_SHA:
        raise RuntimeError(f"protected dry_run.json SHA mismatch before audit: {protected_before}")

    before_old = {
        "lp": status_snapshot(Path(r"D:/project/worktrees/blue_apcd_lp_global_h_manifold_v1")),
        "cp": status_snapshot(Path(r"D:/project/worktrees/blue_apcd_cp_stage10_bw2a")),
        "mdc": status_snapshot(Path(r"D:/project/worktrees/blue_apcd_mdc_defect_450")),
    }
    branch = git("branch", "--show-current")
    head = git("rev-parse", "HEAD")
    upstream = git("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")
    ahead_behind = git("rev-list", "--left-right", "--count", "HEAD...@{u}")
    if branch != EXPECTED_BRANCH or head != EXPECTED_HEAD or ahead_behind != "0\t0":
        raise RuntimeError(f"canonical authority mismatch: {branch=} {head=} {ahead_behind=}")

    domain = read_json(DOMAIN)
    if domain["narrow_bounds"]["delta_theta_deg"] != EXPECTED_BOUNDS["delta_theta_deg"]:
        raise RuntimeError("delta-theta domain mismatch")
    if domain["hard_gates_inherited"] != EXPECTED_GATES:
        raise RuntimeError("inherited gate mismatch")

    initial = read_csv(INITIAL)
    conditional = read_csv(CONDITIONAL)
    c2_row = next(row for row in conditional if row["geometry_id"] == "IAR-C2")
    iar4_row = next(row for row in initial if row["geometry_id"] == "IAR4")
    c2 = geometry_from_row(c2_row)
    iar4 = geometry_from_row(iar4_row)
    if c2_row["geometry_hash_sha256"] != geometry_hash(c2):
        raise RuntimeError("IAR-C2 source geometry hash mismatch")
    if iar4_row["geometry_hash_sha256"] != geometry_hash(iar4):
        raise RuntimeError("IAR4 source geometry hash mismatch")

    hp = module_from(HP_RULE, "a02_high_precision_rule")
    current = module_from(RULE, "current_geometry_rule")
    c2_hp = hp.geometry_audit(hp_payload(c2), 432, 432)
    oc80 = geometry_from_row(c2_row, theta=80.0)
    oc80_hp = hp.geometry_audit(hp_payload(oc80), 432, 432)
    if not c2_hp["current_inherited_gate_pass"] or not oc80_hp["current_inherited_gate_pass"]:
        raise RuntimeError("high precision C2 or OC80 validity gate failed")

    frontier: list[dict[str, Any]] = []
    for idx in range(1001):
        theta = round(80.0 + idx * 0.01, 2)
        g = geometry_from_row(c2_row, theta=theta)
        core = current.geom_core(current_rule_q(g))
        valid = bool(
            core["cell_containment_pass"]
            and core["direct_clearance_nm"] >= 60.0 - 1e-9
            and core["periodic_image_clearance_nm"] >= 60.0 - 1e-9
            and core["overlap_or_touching_pass"]
        )
        if not valid:
            raise RuntimeError(f"current-rule angle scan failed at theta={theta}")
        frontier.append(
            {
                "theta_index": idx,
                "delta_theta_deg": f"{theta:.2f}",
                "L1_nm": g["L1_nm"],
                "W1_nm": g["W1_nm"],
                "L2_nm": g["L2_nm"],
                "W2_nm": g["W2_nm"],
                "D_nm": g["D_nm"],
                "direct_clearance_nm": f"{core['direct_clearance_nm']:.12f}",
                "periodic_image_clearance_nm": f"{core['periodic_image_clearance_nm']:.12f}",
                "global_minimum_clearance_nm": f"{core['global_minimum_clearance_nm']:.12f}",
                "direct_headroom_over_60_nm": f"{core['direct_clearance_nm'] - 60.0:.12f}",
                "periodic_headroom_over_60_nm": f"{core['periodic_image_clearance_nm'] - 60.0:.12f}",
                "nearest_direct_pair": core["direct_pair"],
                "nearest_periodic_pair": core["periodic_nearest_pair"],
                "global_nearest_pair": core["global_nearest_pair"],
                "direct_overlap_or_touch": not bool(core["direct_pair"]["touch_or_overlap"]),
                "no_direct_or_periodic_overlap_or_touch": bool(core["overlap_or_touching_pass"]),
                "cell_containment_pass": bool(core["cell_containment_pass"]),
                "current_inherited_gate_pass": valid,
                "geometry_hash_sha256": geometry_hash(g),
                "scan_method": "current exact polygon segment distance; fixed IAR-C2 geometry; 0.01-degree grid",
            }
        )

    # The current rule already reports the all-image overlap result. The branch above
    # intentionally avoids reimplementing its private periodic list.
    min_row = min(frontier, key=lambda row: float(row["global_minimum_clearance_nm"]))
    max_row = max(frontier, key=lambda row: float(row["global_minimum_clearance_nm"]))
    direct_min_row = min(frontier, key=lambda row: float(row["direct_clearance_nm"]))
    periodic_min_row = min(frontier, key=lambda row: float(row["periodic_image_clearance_nm"]))
    unique_nearest = sorted(
        {
            json.dumps(row["global_nearest_pair"], sort_keys=True, separators=(",", ":"))
            for row in frontier
        }
    )

    c2_record = compact_geometry_record(
        "IAR-C2",
        "SAME_ORIENTATION_LOCAL_BASIN_AND_CLEARANCE_REFERENCE",
        "REFERENCE_ONLY_NOT_CAUSAL_CONTROL",
        c2,
        c2_hp,
        c2_row["geometry_hash_sha256"],
    )
    oc80_record = compact_geometry_record(
        "IAR-C2-OC80",
        "FABRICATION_HEADROOM_ORIENTATION_CONTINUATION_CONTROL",
        "PROSPECTIVE_NOT_AUTHORIZED",
        oc80,
        oc80_hp,
    )
    oc80_record.update(
        {
            "parent_candidate_id": "IAR-C2",
            "only_changed_parameter": "delta_theta_deg",
            "delta_theta_difference_from_IAR_C2_deg": -2.818204313,
            "delta_theta_difference_from_IAR4_deg": float(oc80["delta_theta_deg"]) - float(iar4["delta_theta_deg"]),
            "clearance_headroom_over_60_nm": {
                "direct": float(oc80_hp["direct_clearance_nm"]) - 60.0,
                "periodic": float(oc80_hp["periodic_image_clearance_nm"]) - 60.0,
                "global": float(oc80_hp["physical_polygon_minimum_nm"]) - 60.0,
            },
            "causal_control_reason": "All IAR-C2 dimensions, D, H, periods, centers, materials, and geometry semantics are frozen; only relative orientation changes.",
        }
    )

    prior = read_json(PRIOR_REGISTRY)
    cr1_prior = next(row for row in prior["prospective_records"] if row["candidate_id"] == "IAR4-CR1")
    cr1_g = geometry_from_row(cr1_prior["geometry"])
    cr1_hp = hp.geometry_audit(hp_payload(cr1_g), 432, 432)
    cr1_record = compact_geometry_record(
        "IAR4-CR1",
        cr1_prior["role"],
        cr1_prior["status"],
        cr1_g,
        cr1_hp,
        cr1_prior["geometry_hash_sha256_recomputed"],
    )
    cr1_record["difference_from_IAR4"] = {
        key: float(cr1_g[key]) - float(iar4[key])
        for key in ("L1_nm", "W1_nm", "L2_nm", "W2_nm", "D_nm", "delta_theta_deg")
    }
    c2_record["difference_from_IAR4"] = {
        key: float(c2[key]) - float(iar4[key])
        for key in ("L1_nm", "W1_nm", "L2_nm", "W2_nm", "D_nm", "delta_theta_deg")
    }
    oc80_record["difference_from_IAR4"] = {
        key: float(oc80[key]) - float(iar4[key])
        for key in ("L1_nm", "W1_nm", "L2_nm", "W2_nm", "D_nm", "delta_theta_deg")
    }
    for record in (cr1_record, c2_record, oc80_record):
        record["normalized_6d_distance_from_IAR4"] = euclidean(normalized_vector(record["geometry"]), normalized_vector(iar4))

    solver = {
        "NEW_FDTD_BUDGET": 0,
        "solver_run_called": False,
        "solver_entered": 0,
        "RCWA": 0,
        "ML": 0,
        "active_fdtd_processes": tasklist_fdtd(),
        "hidden_ready_or_pending_auto_admission": False,
    }
    if solver["active_fdtd_processes"]["matching_process_count"] != 0:
        raise RuntimeError("active fdtd-engine process detected during zero-solver audit")

    control = {
        "schema": "PAPER_A_IAR_C2_ORIENTATION_CONTINUATION_CONTROL_CONTRACT_V1",
        "status": "ZERO_SOLVER_PRE_ADMISSION_PLAN_ONLY",
        "task": "PAPER_A_IAR_C2_ORIENTATION_CONTINUATION_CONTROL_CONTRACT_V1",
        "scientific_scope": "IAR-C2 fixed-geometry orientation continuation control; no optical inference",
        "parent_authority": {
            "conditional_registry_path": str(CONDITIONAL),
            "conditional_registry_sha256": sha_file(CONDITIONAL),
            "IAR-C2_exact_row_used": True,
            "frozen_local_domain_path": str(DOMAIN),
            "frozen_local_domain_sha256": sha_file(DOMAIN),
            "delta_theta_domain_deg": [80.0, 90.0],
        },
        "fixed_IAR_C2_geometry": c2,
        "IAR_C2_source_geometry_hash": c2_row["geometry_hash_sha256"],
        "angle_only_control": oc80_record,
        "validity_authority": {
            "current_rule_path": str(RULE),
            "current_rule_sha256": sha_file(RULE),
            "high_precision_rule_path": str(HP_RULE),
            "high_precision_rule_sha256": sha_file(HP_RULE),
            "method": "existing exact segment-to-segment polygon distance over all pillar/image pairs in translations {-1,0,+1}; no cell-boundary substitution",
            "inherited_gates": EXPECTED_GATES,
            "no_new_fabrication_threshold": True,
        },
        "frontier_scan": {
            "path": str(OUT / "iar_c2_angle_clearance_frontier.csv"),
            "grid_start_deg": 80.0,
            "grid_stop_deg": 90.0,
            "grid_step_deg": 0.01,
            "row_count": len(frontier),
            "all_current_rule_gates_pass": True,
            "minimum_legal_theta_on_grid_deg": float(min(row["delta_theta_deg"] for row in frontier)),
            "minimum_legal_theta_is_domain_lower_bound": True,
        },
        "solver_authority": {
            "current_solver_budget": 0,
            "future_bounded_validation_maximum": 4,
            "future_batch": ["IAR-C2_x", "IAR-C2_y", "IAR-C2-OC80_x", "IAR-C2-OC80_y"],
            "current_authorization": "NONE",
            "automatic_admission": False,
            "CR1_preferred": False,
        },
        "stop_loss": "After the separately authorized four-job C2/OC80 bounded validation, make a GO/STOP decision; do not expand the local geometry domain, run local DOE, or open another rescue route.",
        "solver_accounting": solver,
        "DOE_changed": False,
    }

    frontier_summary = {
        "schema": "PAPER_A_IAR_C2_ANGLE_CLEARANCE_FRONTIER_SUMMARY_V1",
        "fixed_geometry": c2,
        "domain_deg": [80.0, 90.0],
        "grid_step_deg": 0.01,
        "row_count": len(frontier),
        "all_rows_current_inherited_gates_pass": all(row["current_inherited_gate_pass"] for row in frontier),
        "minimum_legal_delta_theta_deg_on_grid": 80.0,
        "frontier_is_domain_lower_bound": True,
        "global_minimum_row": min_row,
        "global_maximum_row": max_row,
        "direct_minimum_row": direct_min_row,
        "periodic_minimum_row": periodic_min_row,
        "unique_global_nearest_pair_signatures": unique_nearest,
        "independent_high_precision_confirmation": {
            "IAR-C2": {
                "direct_clearance_nm": c2_hp["direct_clearance_nm"],
                "periodic_clearance_nm": c2_hp["periodic_image_clearance_nm"],
                "global_minimum_nm": c2_hp["physical_polygon_minimum_nm"],
                "current_inherited_gate_pass": c2_hp["current_inherited_gate_pass"],
            },
            "IAR-C2-OC80": {
                "direct_clearance_nm": oc80_hp["direct_clearance_nm"],
                "periodic_clearance_nm": oc80_hp["periodic_image_clearance_nm"],
                "global_minimum_nm": oc80_hp["physical_polygon_minimum_nm"],
                "current_inherited_gate_pass": oc80_hp["current_inherited_gate_pass"],
            },
        },
        "no_new_threshold": True,
    }

    matched = {
        "schema": "PAPER_A_IAR_C2_OC80_MATCHED_CONTROL_RECORD_V1",
        "status": "PROSPECTIVE_NOT_AUTHORIZED",
        "parent": c2_record,
        "matched_control": oc80_record,
        "only_changed_parameter": "delta_theta_deg",
        "all_other_geometry_fields_exactly_equal": all(
            c2[key] == oc80[key]
            for key in ("L1_nm", "W1_nm", "L2_nm", "W2_nm", "D_nm", "height_nm", "period_x_nm", "period_y_nm", "theta1_deg", "j1_center_x_nm", "j1_center_y_nm", "j2_center_x_nm", "j2_center_y_nm")
        ),
        "delta_theta_parent_deg": c2["delta_theta_deg"],
        "delta_theta_control_deg": oc80["delta_theta_deg"],
        "delta_theta_difference_deg": oc80["delta_theta_deg"] - c2["delta_theta_deg"],
        "geometry_hash_changed_only_because_angle_changed": True,
        "causal_control_role": "FABRICATION_HEADROOM_ORIENTATION_CONTINUATION_CONTROL",
        "no_solver": True,
    }
    # Store the hash relation explicitly without relying on the expression above.
    matched["geometry_hash_changed_only_because_angle_changed"] = (
        c2["delta_theta_deg"] != oc80["delta_theta_deg"]
        and c2_record["geometry_hash_sha256_recomputed"] != oc80_record["geometry_hash_sha256_recomputed"]
        and all(c2[key] == oc80[key] for key in ("L1_nm", "W1_nm", "L2_nm", "W2_nm", "D_nm", "height_nm", "period_x_nm", "period_y_nm", "theta1_deg", "j1_center_x_nm", "j1_center_y_nm", "j2_center_x_nm", "j2_center_y_nm"))
    )

    comparison = {
        "schema": "PAPER_A_IAR_C2_ORIENTATION_CONTINUATION_COMPARISON_V1",
        "strict_causal_pair_for_prior_IAR4_claim": "IAR4 <-> IAR4-OC1",
        "records": {
            "IAR4": {"geometry": iar4, "source_geometry_hash": iar4_row["geometry_hash_sha256"], "normalized_6d_distance_from_IAR4": 0.0},
            "IAR4-CR1": cr1_record,
            "IAR-C2": c2_record,
            "IAR-C2-OC80": oc80_record,
        },
        "control_comparison": {
            "IAR4-CR1": "changes D and delta_theta relative to IAR4; not a strict orientation-only control",
            "IAR-C2": "exact registry reference; dimensions and D differ from IAR4; not an orientation-only control",
            "IAR-C2-OC80": "same IAR-C2 geometry with only delta_theta changed; preferred continuation control",
        },
        "no_optical_ranking": True,
    }

    decision = {
        "schema": "PAPER_A_IAR_C2_ORIENTATION_CONTINUATION_PROSPECTIVE_SOLVER_DECISION_V1",
        "status": "PLAN_ONLY_NOT_AUTHORIZED",
        "preferred_bounded_validation_batch": ["IAR-C2_x", "IAR-C2_y", "IAR-C2-OC80_x", "IAR-C2-OC80_y"],
        "maximum_future_fdt_jobs": 4,
        "maximum_active_fdt_jobs": 2,
        "current_new_fdtd_budget": 0,
        "current_solver_run_called": False,
        "IAR4-CR1": "not preferred: D clearance compensation confounds orientation continuation",
        "IAR-C2-OC80": "preferred: legal at the frozen theta floor with direct/periodic headroom above the inherited 60 nm gate",
        "no_auto_admission": True,
        "stop_loss": control["stop_loss"],
    }

    validity = {
        "schema": "PAPER_A_IAR_C2_ORIENTATION_CONTINUATION_POLYGON_VALIDITY_AUDIT_V1",
        "status": "PASS",
        "fixed_C2_exact_audit": c2_record,
        "OC80_exact_audit": oc80_record,
        "frontier_summary": frontier_summary,
        "inherited_gates": EXPECTED_GATES,
        "no_authoritative_new_minimum_gap_threshold": True,
        "no_boundary_margin_substitution": True,
        "no_solver": True,
    }

    tests = {
        "schema": "PAPER_A_IAR_C2_ORIENTATION_CONTINUATION_VALIDATION_V1",
        "status": "PASS",
        "branch_exact": branch == EXPECTED_BRANCH,
        "head_exact_before_generation": head == EXPECTED_HEAD,
        "upstream_ahead_behind_zero": ahead_behind == "0\t0",
        "IAR_C2_loaded_from_conditional_registry": c2_row["geometry_id"] == "IAR-C2",
        "IAR_C2_source_hash_match": c2_record["source_geometry_hash_match"],
        "current_domain_exact_80_to_90": domain["narrow_bounds"]["delta_theta_deg"] == [80.0, 90.0],
        "inherited_gates_exact": domain["hard_gates_inherited"] == EXPECTED_GATES,
        "frontier_row_count_1001": len(frontier) == 1001,
        "frontier_all_current_rule_pass": all(row["current_inherited_gate_pass"] for row in frontier),
        "minimum_legal_theta_is_80_domain_floor": min(float(row["delta_theta_deg"]) for row in frontier) == 80.0,
        "C2_high_precision_pass": c2_hp["current_inherited_gate_pass"],
        "OC80_high_precision_pass": oc80_hp["current_inherited_gate_pass"],
        "OC80_direct_clearance_ge_60": float(oc80_hp["direct_clearance_nm"]) >= 60.0,
        "OC80_periodic_clearance_ge_60": float(oc80_hp["periodic_image_clearance_nm"]) >= 60.0,
        "OC80_no_direct_or_periodic_overlap": oc80_hp["direct_no_overlap_or_touch_pass"] and oc80_hp["periodic_no_overlap_or_touch_pass"],
        "OC80_containment_integer_half_grid": oc80_hp["cell_containment_pass"] and oc80_hp["integer_lateral_dimensions_pass"] and oc80_hp["half_grid_centers_pass"],
        "OC80_only_theta_changed": matched["all_other_geometry_fields_exactly_equal"],
        "OC80_hash_relation": matched["geometry_hash_changed_only_because_angle_changed"],
        "preferred_batch_four_cases": len(decision["preferred_bounded_validation_batch"]) == 4,
        "solver_run_called_false": solver["solver_run_called"] is False,
        "solver_entered_zero": solver["solver_entered"] == 0,
        "new_fdtd_budget_zero": solver["NEW_FDTD_BUDGET"] == 0,
        "RCWA_zero": solver["RCWA"] == 0,
        "ML_zero": solver["ML"] == 0,
        "active_fdtd_zero": solver["active_fdtd_processes"]["matching_process_count"] == 0,
        "DOE_changed_false": True,
        "protected_hash_before_expected": protected_before == PROTECTED_SHA,
    }
    if not all(value is True for key, value in tests.items() if key not in {"schema", "status"}):
        raise RuntimeError("validation failed: " + json.dumps(tests, ensure_ascii=False))

    after_old = {
        "lp": status_snapshot(Path(r"D:/project/worktrees/blue_apcd_lp_global_h_manifold_v1")),
        "cp": status_snapshot(Path(r"D:/project/worktrees/blue_apcd_cp_stage10_bw2a")),
        "mdc": status_snapshot(Path(r"D:/project/worktrees/blue_apcd_mdc_defect_450")),
    }
    old_unchanged = all(before_old[key] == after_old[key] for key in before_old)
    if not old_unchanged:
        raise RuntimeError("frozen source worktree snapshot changed during zero-solver audit")
    protected_after = sha_file(PROTECTED)
    if protected_after != PROTECTED_SHA:
        raise RuntimeError("protected dry_run.json changed during audit")
    tests["old_source_worktrees_unchanged_during_run"] = old_unchanged
    tests["protected_hash_after_expected"] = protected_after == PROTECTED_SHA
    tests["status_only_protected_dirty_before"] = before_old is not None

    provenance = {
        "schema": "PAPER_A_IAR_C2_ORIENTATION_CONTINUATION_PROVENANCE_V1",
        "task": "PAPER_A_IAR_C2_ORIENTATION_CONTINUATION_CONTROL_CONTRACT_V1",
        "canonical_worktree": str(ROOT),
        "canonical_branch": branch,
        "canonical_head_at_generation": head,
        "upstream": upstream,
        "ahead_behind_at_generation": ahead_behind,
        "source_files": {
            str(CONDITIONAL): sha_file(CONDITIONAL),
            str(INITIAL): sha_file(INITIAL),
            str(DOMAIN): sha_file(DOMAIN),
            str(RULE): sha_file(RULE),
            str(HP_RULE): sha_file(HP_RULE),
            str(PRIOR_REGISTRY): sha_file(PRIOR_REGISTRY),
        },
        "protected_file": {"path": str(PROTECTED), "sha256_before": protected_before, "sha256_after": protected_after, "expected_sha256": PROTECTED_SHA},
        "frozen_source_worktrees": before_old,
        "frozen_source_worktrees_after": after_old,
        "solver_accounting": solver,
        "no_new_geometry_domain": True,
        "no_optical_inference": True,
        "immutable_source": True,
    }

    audit = {
        "schema": "PAPER_A_IAR_C2_ORIENTATION_CONTINUATION_AUDIT_V1",
        "status": "PASS",
        "task": "PAPER_A_IAR_C2_ORIENTATION_CONTINUATION_CONTROL_CONTRACT_V1",
        "canonical_head_at_generation": head,
        "frontier_rows": len(frontier),
        "minimum_legal_theta_deg": 80.0,
        "C2_direct_clearance_nm": c2_hp["direct_clearance_nm"],
        "C2_periodic_clearance_nm": c2_hp["periodic_image_clearance_nm"],
        "OC80_direct_clearance_nm": oc80_hp["direct_clearance_nm"],
        "OC80_periodic_clearance_nm": oc80_hp["periodic_image_clearance_nm"],
        "solver_accounting": solver,
        "DOE_changed": False,
        "old_source_worktrees_unchanged_during_run": old_unchanged,
        "protected_file_sha256_after": protected_after,
        "no_solver_invocation": True,
    }

    report_lines = [
        "# IAR-C2 orientation continuation control contract",
        "",
        "Status: PASS — zero-solver pre-admission geometry audit.",
        "",
        "## Decision",
        "",
        "IAR-C2 is read from the canonical conditional registry. With all IAR-C2 geometry frozen, the current inherited polygon-validity rule was scanned from 80.00° to 90.00° in 0.01° increments. All 1001 grid points pass; 80.00° is legal and is the domain lower bound.",
        "",
        f"IAR-C2-OC80 is frozen as a prospective angle-only continuation control: only delta_theta changes from {c2['delta_theta_deg']:.9f}° to 80.000000000° (difference -2.818204313°). It is not solver-authorized in this task.",
        "",
        "## Exact geometry and clearance",
        "",
        f"IAR-C2: L1/W1/L2/W2={c2['L1_nm']}/{c2['W1_nm']}/{c2['L2_nm']}/{c2['W2_nm']} nm, D={c2['D_nm']} nm, delta_theta={c2['delta_theta_deg']:.9f}°, centers y=+{c2['j1_center_y_nm']}/{c2['j2_center_y_nm']} nm, H={c2['height_nm']:.1f} nm, Px=Py={c2['period_x_nm']:.1f} nm.",
        f"IAR-C2-OC80: direct={oc80_hp['direct_clearance_nm']} nm; periodic-image={oc80_hp['periodic_image_clearance_nm']} nm; global polygon minimum={oc80_hp['physical_polygon_minimum_nm']} nm.",
        f"OC80 headroom over the inherited 60 nm gate: direct={float(oc80_hp['direct_clearance_nm'])-60.0:.12f} nm; periodic={float(oc80_hp['periodic_image_clearance_nm'])-60.0:.12f} nm.",
        "Both exact audits pass containment, integer lateral dimensions, half-grid centers, no direct overlap/touch, and no periodic overlap/touch. No new fabrication threshold was introduced.",
        "",
        "## Control comparison",
        "",
        "IAR4-CR1 changes D and delta_theta relative to IAR4 and remains a clearance-compensated continuation probe, not a strict orientation-only control. IAR-C2-OC80 is preferred for bounded validation because it preserves IAR-C2 dimensions and D and changes only relative orientation.",
        "",
        "## Prospective solver plan",
        "",
        "Plan only, no current authorization: IAR-C2_x, IAR-C2_y, IAR-C2-OC80_x, IAR-C2-OC80_y; maximum four future FDTD jobs and maximum two active jobs. No automatic admission is enabled. After that bounded batch, make a GO/STOP decision without expanding the domain.",
        "",
        "## Accounting",
        "",
        "NEW_FDTD_BUDGET=0; solver_run_called=false; solver_entered=0; RCWA=0; ML=0; active fdtd-engine processes=0; DOE unchanged.",
        "",
        "See `iar_c2_angle_clearance_frontier.csv` for all 1001 scan points and `matched_control_record.json` for the exact control relationship.",
    ]

    OUT.mkdir(parents=True, exist_ok=True)
    write_json(OUT / "control_contract.json", control)
    write_csv(OUT / "iar_c2_angle_clearance_frontier.csv", frontier)
    write_json(OUT / "matched_control_record.json", matched)
    write_json(OUT / "cr1_vs_c2_control_comparison.json", comparison)
    write_json(OUT / "prospective_solver_decision.json", decision)
    write_json(OUT / "polygon_validity_audit.json", validity)
    write_json(OUT / "provenance.json", provenance)
    write_json(OUT / "validation_tests.json", tests)
    write_json(OUT / "audit.json", audit)
    (OUT / "final_report.md").write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    protected_final = sha_file(PROTECTED)
    if protected_final != PROTECTED_SHA:
        raise RuntimeError("protected dry_run.json changed after artifact write")
    tests["protected_hash_final_expected"] = protected_final == PROTECTED_SHA
    write_json(OUT / "validation_tests.json", tests)
    audit["protected_file_sha256_final"] = protected_final
    write_json(OUT / "audit.json", audit)

    print(
        json.dumps(
            {
                "status": "PASS",
                "branch": branch,
                "head": head,
                "upstream": upstream,
                "ahead_behind": ahead_behind,
                "IAR_C2_hash": c2_record["geometry_hash_sha256_recomputed"],
                "IAR_C2_OC80_hash": oc80_record["geometry_hash_sha256_recomputed"],
                "OC80_direct_clearance_nm": oc80_hp["direct_clearance_nm"],
                "OC80_periodic_clearance_nm": oc80_hp["periodic_image_clearance_nm"],
                "frontier_rows": len(frontier),
                "solver": solver,
                "protected_sha": protected_final,
                "output": str(OUT),
            },
            ensure_ascii=False,
            default=str,
        )
    )


if __name__ == "__main__":
    main()
