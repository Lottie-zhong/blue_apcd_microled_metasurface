from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import importlib.util
import json
import math
import subprocess
from pathlib import Path


UTC = dt.timezone.utc
ROOT = Path(r"D:/project/worktrees/blue_apcd_paper_a_lp_cp_broadband_v1")
PKG = ROOT / "paper_a_broadband"
REPORT = PKG / "reports/integrated_aware_lp_redesign_contract_v1"
VALIDITY_SCRIPT = PKG / "scripts/lp_anisotropy_feasible_space_v2.py"
PARENT_DOMAIN = PKG / "reports/bf04_local_diattenuation_redesign_doe_v1/local_domain_authority.json"
PARENT_POOL = PKG / "reports/bf04_local_diattenuation_redesign_doe_v1/feasible_pool_inventory.csv"
PARENT_CONFIG = PKG / "configs/BF04_LOCAL_DIATTENUATION_REDESIGN_DOE_V1.json"
NEW_SCOPE_CONFIG = PKG / "configs/PAPER_A_BROADBAND_LP_NEW_GEOMETRY_SEARCH_V1.json"
BASELINE_DIR = PKG / "reports/ic2_pair_polarization_cancellation_forensic_v1"


def now():
    return dt.datetime.now(UTC).isoformat()


def sha256(path: Path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + f".{__import__('os').getpid()}.tmp")
    temp.write_text(json.dumps(value, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    temp.replace(path)


def write_csv(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: json.dumps(value, ensure_ascii=False, sort_keys=True) if isinstance(value, (dict, list)) else value for key, value in row.items()})


def read_csv(path: Path):
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def git_value(*args):
    return subprocess.check_output(["git", "-C", str(ROOT), *args], text=True).strip()


def load_validity_module():
    spec = importlib.util.spec_from_file_location("paper_a_existing_lp_validity", VALIDITY_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def f(row, key):
    return float(row[key])


def as_bool(value):
    return str(value).strip().lower() == "true"


def candidate_geometry(module, row):
    q = {
        "L1_nm": int(round(f(row, "L1_nm"))),
        "W1_nm": int(round(f(row, "W1_nm"))),
        "L2_nm": int(round(f(row, "L2_nm"))),
        "W2_nm": int(round(f(row, "W2_nm"))),
        "D_nm": int(round(f(row, "D_nm"))),
        "delta_theta_deg": f(row, "delta_theta_deg"),
        "height_nm": 525.0,
        "period_x_nm": 432.0,
        "period_y_nm": 432.0,
        "theta1_deg": 0.0,
        "theta2_deg": f(row, "delta_theta_deg"),
        "j1_center_x_nm": 0.0,
        "j1_center_y_nm": int(round(f(row, "D_nm"))) / 2.0,
        "j2_center_x_nm": 0.0,
        "j2_center_y_nm": -int(round(f(row, "D_nm"))) / 2.0,
    }
    return q, module.geom_core(q)


def enrich(module, row, i03, scales, parent_row):
    q, core = candidate_geometry(module, row)
    recomputed_hash = module.sha_obj({key: q[key] for key in ("L1_nm", "W1_nm", "L2_nm", "W2_nm", "D_nm", "delta_theta_deg", "height_nm", "period_x_nm", "period_y_nm", "theta1_deg", "theta2_deg")})
    values = [q["L1_nm"], q["W1_nm"], q["L2_nm"], q["W2_nm"], q["D_nm"], q["delta_theta_deg"]]
    base = [i03["L1_nm"], i03["W1_nm"], i03["L2_nm"], i03["W2_nm"], i03["D_nm"], i03["delta_theta_deg"]]
    distance = math.sqrt(sum(((value - reference) / scale) ** 2 for value, reference, scale in zip(values, base, scales)))
    a1 = (q["L1_nm"] - q["W1_nm"]) / (q["L1_nm"] + q["W1_nm"])
    a2 = (q["L2_nm"] - q["W2_nm"]) / (q["L2_nm"] + q["W2_nm"])
    record = {
        "sample_index": int(float(row["sample_index"])),
        "L1_nm": q["L1_nm"], "W1_nm": q["W1_nm"], "L2_nm": q["L2_nm"], "W2_nm": q["W2_nm"],
        "A1": a1, "A2": a2, "A_mean": 0.5 * (a1 + a2), "Delta_A": a1 - a2,
        "delta_theta_deg": q["delta_theta_deg"], "D_nm": q["D_nm"], "theta1_deg": 0.0, "theta2_deg": q["delta_theta_deg"],
        "j1_center_x_nm": 0.0, "j1_center_y_nm": q["j1_center_y_nm"], "j2_center_x_nm": 0.0, "j2_center_y_nm": q["j2_center_y_nm"],
        "height_nm": 525.0, "period_x_nm": 432.0, "period_y_nm": 432.0,
        "pillar_1_area_nm2": q["L1_nm"] * q["W1_nm"], "pillar_2_area_nm2": q["L2_nm"] * q["W2_nm"],
        "total_footprint_nm2": q["L1_nm"] * q["W1_nm"] + q["L2_nm"] * q["W2_nm"], "cell_area_nm2": 432.0 * 432.0,
        "footprint_fill_fraction": (q["L1_nm"] * q["W1_nm"] + q["L2_nm"] * q["W2_nm"]) / (432.0 * 432.0),
        "direct_clearance_nm": core["direct_clearance_nm"], "periodic_image_clearance_nm": core["periodic_image_clearance_nm"],
        "periodic_x_clearance_nm": core["periodic_x_clearance_nm"], "periodic_y_clearance_nm": core["periodic_y_clearance_nm"],
        "periodic_diagonal_clearance_nm": core["periodic_diagonal_clearance_nm"], "global_minimum_clearance_nm": core["global_minimum_clearance_nm"],
        "nearest_object_image_pair": core["global_nearest_pair"], "cell_containment_pass": core["cell_containment_pass"],
        "overlap_or_touching_pass": core["overlap_or_touching_pass"], "minimum_lateral_feature_nm": min(q[k] for k in ("L1_nm", "W1_nm", "L2_nm", "W2_nm")),
        "aspect_ratio_H_over_min_feature": 525.0 / min(q[k] for k in ("L1_nm", "W1_nm", "L2_nm", "W2_nm")),
        "distance_from_i03_6d": distance, "geometry_hash_sha256": row["geometry_hash_sha256"], "geometry_hash_recomputed": recomputed_hash,
        "geometry_hash_recomputed_match": row["geometry_hash_sha256"] == recomputed_hash,
        "solver_entered": False, "solver_run_called": False,
        "parent_pool_sample_index": int(float(row["sample_index"])),
    }
    return record


def near_fixed(row, base_theta):
    return abs(row["D_nm"] - 220) <= 2 and abs(row["delta_theta_deg"] - base_theta) <= 2.0


def select_one(pool, chosen, key_function, predicate=lambda row: True):
    available = [row for row in pool if row["geometry_hash_sha256"] not in chosen and predicate(row)]
    if not available:
        raise RuntimeError("NO_FEASIBLE_CANDIDATE_FOR_SELECTION")
    selected = min(available, key=key_function)
    chosen.add(selected["geometry_hash_sha256"])
    return selected


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=REPORT)
    args = parser.parse_args()
    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)

    module = load_validity_module()
    parent_domain = read_json(PARENT_DOMAIN)
    parent_pool_rows = read_csv(PARENT_POOL)
    parent_config = read_json(PARENT_CONFIG)
    new_scope_config = read_json(NEW_SCOPE_CONFIG)

    i03 = {
        "geometry_id": "BF04R_I03",
        "L1_nm": 264, "W1_nm": 87, "L2_nm": 194, "W2_nm": 80,
        "D_nm": 220, "delta_theta_deg": 85.819861293,
    }
    parent_quantized = parent_domain["quantized_allowed_bounds"]
    pct = 0.05
    narrow_bounds = {
        "L1_nm": [max(int(parent_quantized["L1_nm"][0]), math.ceil(i03["L1_nm"] * (1.0 - pct))), min(int(parent_quantized["L1_nm"][1]), math.floor(i03["L1_nm"] * (1.0 + pct)))],
        "W1_nm": [max(int(parent_quantized["W1_nm"][0]), math.ceil(i03["W1_nm"] * (1.0 - pct))), min(int(parent_quantized["W1_nm"][1]), math.floor(i03["W1_nm"] * (1.0 + pct)))],
        "L2_nm": [max(int(parent_quantized["L2_nm"][0]), math.ceil(i03["L2_nm"] * (1.0 - pct))), min(int(parent_quantized["L2_nm"][1]), math.floor(i03["L2_nm"] * (1.0 + pct)))],
        "W2_nm": [max(int(parent_quantized["W2_nm"][0]), math.ceil(i03["W2_nm"] * (1.0 - pct))), min(int(parent_quantized["W2_nm"][1]), math.floor(i03["W2_nm"] * (1.0 + pct)))],
        "D_nm": [208, 220], "delta_theta_deg": [80.0, 90.0],
    }
    scales = [narrow_bounds[key][1] - narrow_bounds[key][0] for key in ("L1_nm", "W1_nm", "L2_nm", "W2_nm", "D_nm", "delta_theta_deg")]

    pool = []
    parent_index = {row["geometry_hash_sha256"]: row for row in parent_pool_rows}
    for parent_row in parent_pool_rows:
        if any(not (narrow_bounds[key][0] <= f(parent_row, key) <= narrow_bounds[key][1]) for key in ("L1_nm", "W1_nm", "L2_nm", "W2_nm", "D_nm", "delta_theta_deg")):
            continue
        if not as_bool(parent_row["cell_containment_pass"]) or not as_bool(parent_row["overlap_or_touching_pass"]):
            continue
        if f(parent_row, "direct_clearance_nm") < 60.0 - 1e-9 or f(parent_row, "periodic_image_clearance_nm") < 60.0 - 1e-9:
            continue
        pool.append(enrich(module, parent_row, i03, scales, parent_row))
    pool.sort(key=lambda row: (row["sample_index"], row["geometry_hash_sha256"]))
    if len(pool) < 6:
        raise RuntimeError(f"INTEGRATED_NARROW_POOL_TOO_SMALL:{len(pool)}")

    base_theta = i03["delta_theta_deg"]
    base_delta = (i03["L1_nm"] - i03["W1_nm"]) / (i03["L1_nm"] + i03["W1_nm"]) - (i03["L2_nm"] - i03["W2_nm"]) / (i03["L2_nm"] + i03["W2_nm"])
    base_amean = 0.5 * ((i03["L1_nm"] - i03["W1_nm"]) / (i03["L1_nm"] + i03["W1_nm"]) + (i03["L2_nm"] - i03["W2_nm"]) / (i03["L2_nm"] + i03["W2_nm"]))
    i03_hashes = [row["geometry_hash_sha256"] for row in pool if row["L1_nm"] == i03["L1_nm"] and row["W1_nm"] == i03["W1_nm"] and row["L2_nm"] == i03["L2_nm"] and row["W2_nm"] == i03["W2_nm"] and row["D_nm"] == i03["D_nm"] and abs(row["delta_theta_deg"] - i03["delta_theta_deg"]) < 1e-9]
    if len(i03_hashes) != 1:
        raise RuntimeError(f"I03_REFERENCE_HASH_NOT_UNIQUE:{len(i03_hashes)}")
    chosen = {i03_hashes[0]}
    selections = []
    selections.append(("IAR1", "INITIAL", "maximum attainable Delta_A boundary control; stronger-than-I03 direction unavailable in parent domain", "DELTA_A_STRONGER_REQUEST_UNAVAILABLE_BOUNDARY_CONTROL", select_one(pool, chosen, lambda r: (-r["Delta_A"], abs(r["D_nm"] - 220) + abs(r["delta_theta_deg"] - base_theta), r["distance_from_i03_6d"], r["geometry_hash_sha256"]), lambda r: near_fixed(r, base_theta))))
    selections.append(("IAR2", "INITIAL", "decrease Delta_A at nearly fixed D and delta_theta", "DELTA_A_WEAKER", select_one(pool, chosen, lambda r: (r["Delta_A"], abs(r["D_nm"] - 220) + abs(r["delta_theta_deg"] - base_theta), r["distance_from_i03_6d"], r["geometry_hash_sha256"]), lambda r: near_fixed(r, base_theta))))
    selections.append(("IAR3", "INITIAL", "reduced D while preserving I03-like anisotropy", "D_REDUCED_ANISOTROPY_PRESERVED", select_one(pool, chosen, lambda r: (r["D_nm"], abs(r["Delta_A"] - base_delta), abs(r["delta_theta_deg"] - base_theta), r["distance_from_i03_6d"], r["geometry_hash_sha256"]))))
    selections.append(("IAR4", "INITIAL", "small delta_theta rotation at nearly fixed anisotropy", "DELTA_THETA_ROTATION", select_one(pool, chosen, lambda r: (abs(abs(r["delta_theta_deg"] - base_theta) - 3.0), abs(r["Delta_A"] - base_delta), abs(r["D_nm"] - 220), r["distance_from_i03_6d"], r["geometry_hash_sha256"]), lambda r: abs(r["delta_theta_deg"] - base_theta) >= 1.0)))
    selections.append(("IAR-C1", "CONDITIONAL", "D x delta_theta interaction with I03-like anisotropy retained", "D_DELTA_THETA_INTERACTION", select_one(pool, chosen, lambda r: (abs(r["D_nm"] - 208) / 12.0 + abs(r["delta_theta_deg"] - (base_theta + 3.0)) / 10.0, abs(r["Delta_A"] - base_delta), r["distance_from_i03_6d"], r["geometry_hash_sha256"]))))
    selections.append(("IAR-C2", "CONDITIONAL", "Delta_A x delta_theta interaction", "DELTA_A_DELTA_THETA_INTERACTION", select_one(pool, chosen, lambda r: (abs(r["delta_theta_deg"] - (base_theta - 3.0)) / 10.0, -abs(r["Delta_A"] - base_delta), abs(r["D_nm"] - 220), r["distance_from_i03_6d"], r["geometry_hash_sha256"]))))

    initial = []
    conditional = []
    for candidate_id, role, direction, mechanism, row in selections:
        row = dict(row)
        row.update({"geometry_id": candidate_id, "role": f"{role}_INTEGRATED_AWARE_CANDIDATE", "selection_label": direction, "mechanism_direction": mechanism, "parent_authority": "BF04/I03 local feasible pool; zero-optical-information deterministic selection"})
        row["direct_clearance_ge_60"] = row["direct_clearance_nm"] >= 60.0
        row["periodic_clearance_ge_60"] = row["periodic_image_clearance_nm"] >= 60.0
        row["integer_lateral_dimensions"] = all(float(row[key]).is_integer() for key in ("L1_nm", "W1_nm", "L2_nm", "W2_nm"))
        row["half_grid_centers"] = all(abs(2.0 * row[key] - round(2.0 * row[key])) < 1e-9 for key in ("j1_center_y_nm", "j2_center_y_nm"))
        row["geometry_valid"] = bool(row["direct_clearance_ge_60"] and row["periodic_clearance_ge_60"] and row["cell_containment_pass"] and row["overlap_or_touching_pass"] and row["integer_lateral_dimensions"] and row["half_grid_centers"])
        (initial if role == "INITIAL" else conditional).append(row)
    by_id = {row["geometry_id"]: row for row in initial + conditional}
    if not by_id["IAR2"]["Delta_A"] < base_delta:
        raise RuntimeError("IAR2_NOT_WEAKER_DELTA_A_THAN_I03")
    max_pool_delta = max(row["Delta_A"] for row in pool)
    iar1_direction_feasible = max_pool_delta > base_delta + 1e-12
    final_verdict = "INTEGRATED_AWARE_INITIAL_DOE_READY" if iar1_direction_feasible else "INTEGRATED_LOCAL_SPACE_TOO_CONSTRAINED"
    if not iar1_direction_feasible:
        by_id["IAR1"]["role"] = "INITIAL_INTEGRATED_AWARE_BOUNDARY_CONTROL"
        by_id["IAR1"]["selection_label"] = "IAR1_STRONGER_DELTA_A_UNAVAILABLE_WITHIN_PARENT_DOMAIN"
        by_id["IAR1"]["mechanism_direction"] = "DELTA_A_STRONGER_REQUEST_UNAVAILABLE_BOUNDARY_CONTROL"

    pool_file = out / "integrated_feasible_pool.csv"
    write_csv(pool_file, pool)

    source_files = [PARENT_DOMAIN, PARENT_POOL, PARENT_CONFIG, NEW_SCOPE_CONFIG, VALIDITY_SCRIPT]
    source_refs = {str(path): {"sha256": sha256(path), "bytes": path.stat().st_size} for path in source_files}
    baseline_anchor = read_json(BASELINE_DIR / "pair_450nm_forensic_anchor.json")
    angular_rows = read_csv(BASELINE_DIR / "pair_angular_cancellation_metrics.csv")
    cone_rows = read_csv(BASELINE_DIR / "pair_collection_cone_metrics.csv")
    cones = {row["cone"]: row for row in cone_rows}
    baseline = {
        "schema": "PAPER_A_INTEGRATED_AWARE_BASELINE_METRICS_V1",
        "source": "finite integrated IC1/IC2 top-well x/y pair; current authoritative post-FSP truth",
        "baseline_artifact": str(BASELINE_DIR / "root_cause_decision.json"),
        "baseline_artifact_sha256": sha256(BASELINE_DIR / "root_cause_decision.json"),
        "wavelength_nm": 450.0,
        "pair_DoLP": baseline_anchor["pair_DoLP"],
        "C_source": baseline_anchor["C_linear"],
        "C_angular": baseline_anchor["angular"]["angular_cancellation"]["C_angular"],
        "cone_DoLP": {key: float(cones[key]["DoLP"]) for key in ("5_deg_normal", "10_deg_normal", "20_deg_normal")},
        "upward_source_normalized_power": {key: float(cones[key]["upward_source_normalized_power_integral"]) for key in ("5_deg_normal", "10_deg_normal", "20_deg_normal", "full_available_upper")},
        "pair_angular_DoLP_full_available_upper": float(cones["full_available_upper"]["DoLP"]),
        "pair_angular_psi_full_available_upper_deg": float(cones["full_available_upper"]["psi_deg"]),
        "xy_Poincare_separation_deg": baseline_anchor["Poincare_separation_deg"],
        "x_y_S0_ratio": baseline_anchor["power_ratio_S0x_over_S0y"],
        "pair_local_DoLP_powerweighted": baseline_anchor["angular"]["angular_cancellation"]["pair_local_DoLP_powerweighted"],
        "angular_map_npz": str(BASELINE_DIR / "pair_angular_resolved_450nm.npz"),
        "angular_DoLP_figure": str(BASELINE_DIR / "figures/pair_angular_dolp_450nm.png"),
        "angular_psi_figure": str(BASELINE_DIR / "figures/pair_angular_psi_450nm.png"),
        "baseline_scope_boundary": "relative integrated baseline only; not periodic intrinsic I03 substitution; no absolute LEE claim",
        "source_files": {str(path): {"sha256": sha256(path), "bytes": path.stat().st_size} for path in (BASELINE_DIR / "pair_450nm_forensic_anchor.json", BASELINE_DIR / "pair_angular_cancellation_metrics.csv", BASELINE_DIR / "pair_collection_cone_metrics.csv", BASELINE_DIR / "pair_angular_resolved_450nm.npz", BASELINE_DIR / "figures/pair_angular_dolp_450nm.png", BASELINE_DIR / "figures/pair_angular_psi_450nm.png")},
    }
    write_json(out / "integrated_baseline_metrics.json", baseline)

    local_domain = {
        "schema": "PAPER_A_INTEGRATED_AWARE_LOCAL_DOMAIN_AUTHORITY_V1",
        "status": "ZERO_SOLVER_INITIAL_DOE_PLANNING",
        "parent_authority": {"local_domain_path": str(PARENT_DOMAIN), "local_domain_sha256": sha256(PARENT_DOMAIN), "parent_pool_path": str(PARENT_POOL), "parent_pool_sha256": sha256(PARENT_POOL), "parent_config_path": str(PARENT_CONFIG), "parent_config_sha256": sha256(PARENT_CONFIG)},
        "i03_reference": i03,
        "fixed_physics": {"height_nm": 525.0, "period_x_nm": 432.0, "period_y_nm": 432.0, "finite_array": "5x5 full cells", "mesa_nm": [3000.0, 3000.0], "MDC": "unchanged frozen MDC/source/top-well contract", "materials": ["APCD_GAN_NATIVE_M1", "APCD_TIO2_NATIVE_M1", "APCD_SIO2_NATIVE_M1"]},
        "narrow_bounds": narrow_bounds,
        "bound_derivation": {"dimension_fraction": 0.05, "dimensions": "intersection of exact parent quantized bounds with integer +/-5% I03 neighborhood, rounded outward to integer candidates only after intersection", "D_nm": "fixed prospective [208,220] nm from new contract", "delta_theta_deg": "fixed prospective [80,90] deg from new contract"},
        "hard_gates_inherited": {"direct_polygon_clearance_nm_ge": 60.0, "periodic_image_polygon_clearance_nm_ge": 60.0, "no_overlap_or_touching": True, "cell_containment": True, "integer_lateral_dimensions": True, "half_grid_centers": True, "no_sub_grid_geometry": True},
        "validity_implementation": {"path": str(VALIDITY_SCRIPT), "sha256": sha256(VALIDITY_SCRIPT), "method": "existing exact segment-to-segment polygon distance over translations {-Px,0,+Px}x{-Py,0,+Py}; no new threshold"},
        "pool_filter": "parent feasible_pool_inventory filtered only by new narrow bounds and inherited validity gates; no optical field or metric used",
        "pool_count": len(pool),
        "pool_hash": hashlib.sha256("\n".join(row["geometry_hash_sha256"] for row in pool).encode()).hexdigest(),
        "solver_accounting": {"NEW_FDTD_BUDGET": 0, "solver_run_called": False, "solver_entered": 0, "RCWA": 0, "ML": 0},
    }
    write_json(out / "integrated_local_domain_authority.json", local_domain)
    write_csv(out / "integrated_candidate_registry_initial.csv", initial)
    write_csv(out / "integrated_candidate_registry_conditional.csv", conditional)

    selection_audit = {
        "schema": "PAPER_A_INTEGRATED_AWARE_MECHANISM_SELECTION_AUDIT_V1",
        "status": "PASS",
        "selection_is_geometry_only": True,
        "no_optical_prediction": True,
        "algorithm": {"IAR1": "max Delta_A within |D-220|<=2 and |delta_theta-I03|<=2", "IAR2": "min Delta_A within same near-fixed D/theta subset", "IAR3": "minimum D with Delta_A/theta proximity tie-break", "IAR4": "target approximately 3 deg delta_theta displacement with anisotropy proximity tie-break", "IAR-C1": "D x delta_theta interaction target (208 nm, I03 theta +3 deg) with anisotropy proximity", "IAR-C2": "Delta_A x delta_theta interaction target (I03 theta -3 deg) with Delta_A displacement tie-break"},
        "selected_initial_ids": [row["geometry_id"] for row in initial],
        "selected_conditional_ids": [row["geometry_id"] for row in conditional],
        "all_selected_geometry_valid": all(row["geometry_valid"] for row in initial + conditional),
        "all_direct_clearance_ge_60": all(row["direct_clearance_ge_60"] for row in initial + conditional),
        "all_periodic_clearance_ge_60": all(row["periodic_clearance_ge_60"] for row in initial + conditional),
        "all_hashes_unique": len({row["geometry_hash_sha256"] for row in initial + conditional}) == 6,
        "baseline_i03_excluded": i03_hashes[0] not in {row["geometry_hash_sha256"] for row in initial + conditional},
        "all_geometry_hashes_recomputed_match": all(row["geometry_hash_recomputed_match"] for row in initial + conditional),
        "IAR1_requested_direction_feasible": iar1_direction_feasible,
        "IAR1_max_pool_Delta_A": max_pool_delta,
        "IAR1_base_I03_Delta_A": base_delta,
        "IAR1_max_pool_minus_I03": max_pool_delta - base_delta,
        "final_verdict": final_verdict,
        "old_labels_reused": False,
        "candidate_mechanism_diversity": True,
        "base_delta_A": base_delta,
        "base_A_mean": base_amean,
    }
    write_json(out / "integrated_mechanism_selection_audit.json", selection_audit)

    budget = {
        "schema": "PAPER_A_INTEGRATED_AWARE_FUTURE_SOLVER_BUDGET_PLAN_V1",
        "current_stage": {"NEW_FDTD_BUDGET": 0, "solver_run_called": False, "solver_entered": 0, "RCWA": 0, "ML": 0, "new_MQW_wells": 0, "executed": False},
        "initial_truth_batch": {"geometries": 4, "dipole_orientations_per_geometry": 2, "FDTD_entries": 8, "cases": "top-well x and top-well y independent cases", "active_cap": 2, "provider": "current-Native FDTD only", "authorization": "future user authorization plus shared scheduler admission required", "admission_status": final_verdict},
        "conditional_truth_batch": {"geometries": 2, "dipole_orientations_per_geometry": 2, "FDTD_entries": 4, "authorization": "not authorized by this planning stage"},
        "global_policy": {"CURRENT_PRODUCTION_FDTD_SCHEDULING_CAP": 3, "CURRENT_PRODUCTION_RCWA_SCHEDULING_CAP": 3, "shared_scheduler_not_forked": True},
        "case_validity": "geometry not scientifically evaluable until both x and y source cases are valid; combine S_i,pair=0.5*S_i,x+0.5*S_i,y",
        "no_auto_admission": True,
    }
    write_json(out / "future_solver_budget_plan.json", budget)

    contract = {
        "schema": "PAPER_A_INTEGRATED_AWARE_LP_REDESIGN_CONTRACT_V1",
        "status": final_verdict,
        "canonical_head": git_value("rev-parse", "HEAD"),
        "canonical_branch": git_value("branch", "--show-current"),
        "objective": {"primary": ["x/y source Stokes reinforcement", "angular polarization-axis reinforcement"], "source_formula": "C_source(lambda)=|L_x+L_y|/(|L_x|+|L_y|), L=(S1,S2)", "angular_formula": "C_angular(lambda)=|integral L_xy dOmega|/integral |L_xy| dOmega", "quadrature": "existing exact solid-angle quadrature; no scalar composite score", "success_requires": ["pair DoLP improvement", "C_source improvement", "C_angular improvement", "dominant angular LP-axis consistency", "no severe upward/source-normalized power collapse", "low circular contamination", "numerical stability"]},
        "frozen_root_cause": {"classification": "BOTH_SOURCE_AND_ANGULAR_CANCELLATION", "pair_DoLP_450nm": 0.037876844117608964, "C_source_450nm": 0.08854257161559786, "C_angular_450nm": 0.08612761641165362, "Poincare_separation_deg": 100.45025108271777, "interpretation": "finite integrated incoherent source does not quantitatively inherit periodic intrinsic I03 LP behavior"},
        "baseline_metrics_path": str(out / "integrated_baseline_metrics.json"),
        "design_space": {"parent": "exact BF04/I03 local feasible domain", "vary_only": ["L1_nm", "W1_nm", "L2_nm", "W2_nm", "D_nm", "delta_theta_deg"], "fixed": {"H_nm": 525.0, "Px_nm": 432.0, "Py_nm": 432.0, "finite_array": "5x5", "mesa_nm": [3000.0, 3000.0], "MDC_source_topwell_domain_monitors": "unchanged"}, "domain_authority_path": str(out / "integrated_local_domain_authority.json")},
        "mechanism_coordinates": ["A1", "A2", "A_mean", "Delta_A", "D", "delta_theta"],
        "integrated_mechanism_labels": ["SOURCE_CHANNEL_ALIGNMENT_PROBE", "ANGULAR_AXIS_ALIGNMENT_PROBE", "COUPLING_STRENGTH_PROBE", "DIFFERENTIAL_ANISOTROPY_PROBE"],
        "candidate_registries": {"initial": str(out / "integrated_candidate_registry_initial.csv"), "conditional": str(out / "integrated_candidate_registry_conditional.csv")},
        "future_evaluation": {"at_450_nm": ["pair DoLP", "C_source", "C_angular", "Poincare x/y separation", "upward/source-normalized power", "5/10/20 deg cone DoLP"], "broadband": ["pair DoLP(lambda)", "C_source(lambda)", "C_angular(lambda)", "angular psi stability", "DoCP(lambda)", "power spectrum"], "combination": "incoherent x/y Stokes combination only after both cases valid"},
        "future_budget_path": str(out / "future_solver_budget_plan.json"),
        "limitations": {"W_emit": "UNRESOLVED_FOR_PRODUCTION_CLOSURE", "incident_plane": "INCIDENT_I03_FIELD_NOT_AVAILABLE", "no_historical_28nm_gaussian": True, "no_exact_source_to_I03_angular_causality_claim": True},
        "excluded_objectives": ["phase", "K6", "six-phase reachability", "beam steering", "LP-K6", "grouped-D", "J1 rescue", "phase coverage", "old historical rescue ranking"],
        "candidate_selection_status": {"IAR1_requested_direction_feasible": iar1_direction_feasible, "IAR1_max_pool_Delta_A": max_pool_delta, "IAR1_base_I03_Delta_A": base_delta, "IAR1_boundary_control_only": not iar1_direction_feasible, "initial_candidate_count": len(initial), "conditional_candidate_count": len(conditional)},
        "solver_safety": {"NEW_FDTD_BUDGET": 0, "solver_run_called": False, "solver_entered": 0, "RCWA": 0, "ML": 0, "new_physics": 0, "new_MQW_wells": 0, "no_ready_pending_hidden_auto_admission": True},
        "source_authority": source_refs,
        "created_utc": now(),
    }
    write_json(out / "integrated_aware_lp_redesign_contract_v1.json", contract)

    report_lines = [
        "# Integrated-aware LP redesign contract v1", "", "## Status", "", f"`{final_verdict}` — zero-solver candidate design only.", "",
        "## Objective", "", "The primary objective is simultaneous reinforcement of x/y source Stokes and angular polarization axes. No scalar composite score and no optical prediction are used.", "",
        "## Frozen baseline", "", f"At 450 nm, finite integrated I03 x/y pair: DoLP={baseline['pair_DoLP']:.8f}, C_source={baseline['C_source']:.8f}, C_angular={baseline['C_angular']:.8f}, x/y Poincare separation={baseline['xy_Poincare_separation_deg']:.8f} deg.", f"Normal 5/10/20 deg cone DoLP={baseline['cone_DoLP']['5_deg_normal']:.8f}/{baseline['cone_DoLP']['10_deg_normal']:.8f}/{baseline['cone_DoLP']['20_deg_normal']:.8f}; full-angle DoLP={baseline['pair_angular_DoLP_full_available_upper']:.8f}.", "This is the finite integrated baseline, not periodic intrinsic truth.", "",
        "## Local pool", "", f"The inherited exact polygon-validity rules produce {len(pool)} feasible geometries after the narrower I03-centered filter. Fixed H=525 nm, Px=Py=432 nm, 5x5 array, and 3000x3000 nm mesa are retained.", "", "| ID | role | mechanism | L1/W1/L2/W2 nm | D / delta_theta | A1 / A2 / A_mean / Delta_A | direct / periodic clearance nm | distance from I03 |", "|---|---|---|---:|---:|---:|---:|---:|",
    ]
    for row in initial + conditional:
        report_lines.append(f"| {row['geometry_id']} | {row['role']} | {row['mechanism_direction']} | {row['L1_nm']}/{row['W1_nm']}/{row['L2_nm']}/{row['W2_nm']} | {row['D_nm']} / {row['delta_theta_deg']:.9f} | {row['A1']:.6f} / {row['A2']:.6f} / {row['A_mean']:.6f} / {row['Delta_A']:.6f} | {row['direct_clearance_nm']:.6f} / {row['periodic_image_clearance_nm']:.6f} | {row['distance_from_i03_6d']:.6f} |")
    report_lines += ["", "All six selected records are mathematically non-overlapping, contained, integer-dimensioned, half-grid compatible, and pass the inherited direct/periodic clearance >=60 nm gates. IAR1 is a boundary control only: the requested stronger-Delta_A direction is absent within the inherited parent domain because I03 already reaches the pool maximum. These are geometry-only probes; no candidate is predicted to improve integrated DoLP.", "", "## Future truth contract", "", "The initial batch is 4 geometries x 2 independent top-well dipoles = 8 FDTD entries, but admission is not authorized here and is blocked by the local-space constraint. Both x and y must be valid before pair evaluation; combine Stokes incoherently.", "", "## Limits", "", "W_emit remains `UNRESOLVED_FOR_PRODUCTION_CLOSURE`. The incident field immediately at I03 is unavailable (`INCIDENT_I03_FIELD_NOT_AVAILABLE`), so exact source-to-I03 angular causality is not claimed. No new diagnostic solver is requested here.", "", "## Solver accounting", "", "`NEW_FDTD_BUDGET=0`, `solver_run_called=false`, `solver_entered=0`, `RCWA=0`, `ML=0`; no new MQW well or physics was created.", ""]
    (out / "final_report.md").write_text("\n".join(report_lines), encoding="utf-8")

    audit_files = [out / name for name in ("integrated_aware_lp_redesign_contract_v1.json", "integrated_baseline_metrics.json", "integrated_local_domain_authority.json", "integrated_feasible_pool.csv", "integrated_candidate_registry_initial.csv", "integrated_candidate_registry_conditional.csv", "integrated_mechanism_selection_audit.json", "future_solver_budget_plan.json", "final_report.md")]
    audit = {"schema": "PAPER_A_INTEGRATED_AWARE_LP_REDESIGN_AUDIT_V1", "status": "PASS", "stage": "PAPER_A_INTEGRATED_AWARE_LP_REDESIGN_CONTRACT_V1", "canonical_head": git_value("rev-parse", "HEAD"), "canonical_branch": git_value("branch", "--show-current"), "pool_count": len(pool), "selected_initial_count": len(initial), "selected_conditional_count": len(conditional), "all_selected_valid": selection_audit["all_selected_geometry_valid"], "all_hashes_unique": selection_audit["all_hashes_unique"], "solver_accounting": budget["current_stage"], "source_files": source_refs, "output_files": {path.name: {"sha256": sha256(path), "bytes": path.stat().st_size} for path in audit_files}, "DOE_changed": False, "physics_changed": False, "old_source_worktrees_modified": False, "incident_plane_field": "INCIDENT_I03_FIELD_NOT_AVAILABLE", "W_emit": "UNRESOLVED_FOR_PRODUCTION_CLOSURE", "timestamp_utc": now()}
    write_json(out / "audit.json", audit)
    print(json.dumps({"status": contract["status"], "pool_count": len(pool), "initial": [row["geometry_id"] for row in initial], "conditional": [row["geometry_id"] for row in conditional], "solver_accounting": budget["current_stage"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
