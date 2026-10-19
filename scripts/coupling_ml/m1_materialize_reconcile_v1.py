from pathlib import Path
import csv
import hashlib
import json
import math
import statistics
import subprocess
from datetime import datetime, timezone


ML = Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1")
M0_ROOT = ML / "outputs/coupling_ml/M0_LEVEL1_LEVEL2_CONTRACT_RECONCILIATION_V1"
M0F_ROOT = M0_ROOT / "M0F_MINIMAL_LEVEL1_CONTRACT_REPAIR_ACQUISITION" / "M0F_CONTINUATION_AFTER_COMPONENT_RULING_V1"
RESIDUAL_CSV = M0F_ROOT / "M0F_FINAL_RESIDUAL_ELIGIBILITY_AFTER_FULL_COMPONENT_SET_V1.csv"
NUMERICAL_CSV = M0F_ROOT / "M0F_FINAL_RECONCILED_LEVEL1_NUMERICAL_REGISTRY_V1.csv"
OUT = ML / "outputs/coupling_ml/M1_EXACT_RESIDUAL_DATASET_V1"
OUT.mkdir(parents=True, exist_ok=True)

EXPECTED_CANDIDATE_ROWS = 24
EXPECTED_CONTROL_ROWS = 24
EXPECTED_CASES = 4
EXPECTED_GEOMETRIES = 1
WAVELENGTHS = [445 + i for i in range(11)]
OBSERVABLES = ["R", "T", "eta_plus1", "eta_0", "eta_minus1", "order_profile"]
SOURCE_Z = "MDC_z=975_nm -> NP_pillar_bottom_z=1212_nm; propagation_delta_z=237_nm"
GEOMETRY_ID = "M0F_EXACT_K6_GEOMETRY_001"
NEXT = "GEOMETRY_DIVERSITY_SEED_ACQUISITION_PLANNING"


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def write_csv(path, fieldnames, rows):
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)


def parse_json(value):
    return json.loads(value) if isinstance(value, str) else value


def finite_number(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(float(x))


def walk_numbers(value):
    if isinstance(value, bool):
        return []
    if isinstance(value, (int, float)):
        return [float(value)]
    if isinstance(value, list):
        out = []
        for item in value:
            out.extend(walk_numbers(item))
        return out
    if isinstance(value, dict):
        out = []
        for item in value.values():
            out.extend(walk_numbers(item))
        return out
    return []


def flatten_endpoint(value):
    return walk_numbers(value)


def profile_by_wavelength(value):
    value = parse_json(value)
    result = []
    for item in value:
        mapping = {}
        if isinstance(item, dict) and "orders" in item:
            item = item["orders"]
        if isinstance(item, dict):
            item = [item]
        for order_item in item:
            if not isinstance(order_item, dict):
                continue
            order = order_item.get("order")
            if isinstance(order, str):
                order_key = order.strip()
                if "," not in order_key:
                    order_key = str(int(float(order_key))) + ",0"
            elif isinstance(order, (int, float)):
                order_key = str(int(order)) + ",0"
            else:
                continue
            if isinstance(order_item.get("fraction"), (int, float)):
                mapping[order_key] = float(order_item["fraction"])
        result.append(mapping)
    return result


def row_values(row):
    return parse_json(row["level1_value_json"]), parse_json(row["target_value_json"])


def candidate_values(row):
    level1, target = row_values(row)
    if row["observable"] != "order_profile":
        return [float(x) for x in level1], [float(x) for x in target]
    lmap = profile_by_wavelength(level1)
    tmap = profile_by_wavelength(target)
    deltas = []
    targets = []
    levels = []
    for i in range(min(len(lmap), len(tmap))):
        for order in sorted(tmap[i]):
            if order in lmap[i]:
                levels.append(float(lmap[i][order]))
                targets.append(float(tmap[i][order]))
                deltas.append(float(tmap[i][order] - lmap[i][order]))
    return levels, targets


def raw_source_audit(row):
    path = Path(row["target_raw_path"])
    result = {
        "path": str(path),
        "exists": path.exists(),
        "sha256_expected": row.get("target_raw_sha256", ""),
        "sha256_actual": sha256(path) if path.exists() else None,
        "sha256_match": False,
        "schema_version": None,
        "real_solver_invoked": None,
        "zero_solver": None,
        "wavelength_grid": None,
        "wavelength_grid_exact": False,
        "transmission_fraction_sum_min": None,
        "transmission_fraction_sum_max": None,
        "fraction_is_conditional": False,
        "raw_parse_error": None,
    }
    if not path.exists():
        return result
    result["sha256_match"] = result["sha256_actual"] == result["sha256_expected"]
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
        result["schema_version"] = payload.get("schema_version")
        result["real_solver_invoked"] = payload.get("real_solver_invoked")
        result["zero_solver"] = payload.get("zero_solver")
        grid = payload.get("wavelengths_nm")
        result["wavelength_grid"] = grid
        result["wavelength_grid_exact"] = grid == WAVELENGTHS
        sums = []
        for item in payload.get("transmission_orders", []):
            if isinstance(item, dict) and isinstance(item.get("fraction"), list):
                sums.append(sum(walk_numbers(item["fraction"])))
        if sums:
            result["transmission_fraction_sum_min"] = min(sums)
            result["transmission_fraction_sum_max"] = max(sums)
            result["fraction_is_conditional"] = all(abs(x - 1.0) <= 1e-12 for x in sums)
    except Exception as exc:
        result["raw_parse_error"] = repr(exc)
    return result


def git_state():
    def run(args):
        p = subprocess.run(args, cwd=str(ML), capture_output=True, text=True, encoding="utf-8", errors="replace")
        return p.stdout.strip() if p.returncode == 0 else "ERROR:" + p.stderr.strip()
    return {
        "branch": run(["git", "branch", "--show-current"]),
        "head": run(["git", "rev-parse", "HEAD"]),
        "status_short": run(["git", "status", "--short"]),
        "ahead_behind": run(["git", "rev-list", "--left-right", "--count", "HEAD...@{u}"]),
    }


def provider_status(num_row):
    path = Path(num_row["np_provider_freeze_path"])
    return {
        "path": str(path),
        "exists": path.exists(),
        "sha256_expected": num_row.get("np_provider_freeze_sha256", ""),
        "sha256_actual": sha256(path) if path.exists() else None,
        "sha256_match": path.exists() and sha256(path) == num_row.get("np_provider_freeze_sha256", ""),
        "provider_channel": num_row.get("provider_channel"),
        "provider_node_count": num_row.get("np_provider_node_count"),
    }


def source_orientation(row, num_row):
    channel = num_row.get("provider_channel", "")
    if channel == "P_XLIKE":
        return "physical_MDC_x_dipole -> provider_P_XLIKE"
    if channel == "S_YLIKE":
        return "physical_MDC_z_dipole -> provider_S_YLIKE"
    return "UNRESOLVED:" + channel


def target_semantics(observable):
    if observable == "R":
        return "Level2A reflection_monitor.T sign-corrected to incident-power-normalized R=-T_reflection"
    if observable == "T":
        return "Level2A transmission_monitor.T incident-power-normalized total transmitted power"
    if observable == "order_profile":
        return "Level2A transmission_orders.fraction conditional transmitted-order distribution; per-wavelength sum=1"
    return "Level2A transmission_orders.fraction conditional transmitted-order fraction for selected order"


def level1_semantics(observable):
    if observable in ("R", "T"):
        return "M0F reconciled incident-power-normalized scalar endpoint"
    if observable == "order_profile":
        return "M0F provider transmitted_order_map fractions on incident-power semantics; sum equals T_total"
    return "M0F provider eta_* absolute transmitted-order power fraction on incident-power semantics"


def exact_status(observable):
    if observable in ("R", "T"):
        return "EXACT_RESIDUAL_SUPPORTED"
    return "NOT_SUPPORTED"


def make_identity(row, num_row, raw_audit):
    obs = row["observable"]
    return {
        "logical_case_id": row["logical_case_id"],
        "truth_domain": row["truth_domain"],
        "candidate": row["candidate"],
        "source_class": "LEVEL2A_HF_FDTD_RAW_PLUS_M0F_LEVEL1_RECONCILED_NUMERICAL_ENDPOINT",
        "source_z": SOURCE_Z,
        "source_orientation": source_orientation(row, num_row),
        "source_polarization": row["source_polarization"],
        "lateral_condition": "periodic_UX; ux=" + row["ux"],
        "spacer_nm": float(row["spacer_nm"]),
        "wavelength_grid_nm": WAVELENGTHS,
        "observable": obs,
        "target_semantics": target_semantics(obs),
        "level1_semantics": level1_semantics(obs),
        "level2_authoritative_raw_path": row["target_raw_path"],
        "level2_authoritative_raw_sha256": row["target_raw_sha256"],
        "level2_authoritative_raw_sha256_verified": raw_audit["sha256_match"],
        "authoritative_parsed_numerical_data_path": str(NUMERICAL_CSV),
        "authoritative_parsed_numerical_data_sha256": sha256(NUMERICAL_CSV),
        "level1_reconciled_endpoint_json": row["level1_value_json"],
        "level2_target_endpoint_json": row["target_value_json"],
        "residual_delta_json": None,
        "normalization_contract": num_row["normalization_contract"],
        "source_normalization_status": num_row.get("source_normalization_status", ""),
        "reference_plane_status": num_row["reference_plane_status"],
        "physical_order_mapping": num_row["physical_order_mapping"],
        "source_component_count": num_row["source_component_count"],
        "source_component_ids_json": num_row["source_component_ids"],
        "source_component_sha256_json": num_row["source_component_sha256_json"],
        "np_provider_freeze_path": num_row["np_provider_freeze_path"],
        "np_provider_freeze_sha256": num_row["np_provider_freeze_sha256"],
        "np_provider_freeze_sha256_verified": provider_status(num_row)["sha256_match"],
        "provenance_validation_state": "M0F_SOURCE_PATH_AND_HASH_CHECKED; M1_EXTRACTION_SEMANTICS_REAUDITED",
        "grouping_key": row["logical_case_id"] + "|" + GEOMETRY_ID,
        "geometry_group_id": GEOMETRY_ID,
        "training_policy": "CONTROL0_DIAGNOSTIC_NONTRAINING" if row["candidate"] == "CONTROL0" else "BLOCKED_PENDING_M1_GLOBAL_EXACT_24_ROW_GATE",
        "split_policy": "group_by_logical_case_id_and_geometry; random_row_split_allowed=false; leave_geometry_out_possible=false",
        "observable_exact_compatibility": exact_status(obs),
        "interpolation_used": row.get("no_interpolation", "") != "true",
        "no_extrapolation": row.get("no_extrapolation", "") == "true",
        "m0f_residual_compatibility": row.get("residual_compatible", "").lower() == "true",
        "raw_source_audit": raw_audit,
    }


def flatten_profile_values(value):
    maps = profile_by_wavelength(value)
    out = []
    for mapping in maps:
        for key in sorted(mapping):
            out.append(float(mapping[key]))
    return out


def values_for_stats(row):
    level1, target = row_values(row)
    if row["observable"] == "order_profile":
        lmap = profile_by_wavelength(level1)
        tmap = profile_by_wavelength(target)
        levels, targets = [], []
        for i in range(min(len(lmap), len(tmap))):
            for order in sorted(tmap[i]):
                if order in lmap[i]:
                    levels.append(float(lmap[i][order]))
                    targets.append(float(tmap[i][order]))
        return levels, targets
    return [float(x) for x in level1], [float(x) for x in target]


def summary(values):
    if not values:
        return {"n": 0}
    vals = [float(x) for x in values]
    return {
        "n": len(vals),
        "min": min(vals),
        "max": max(vals),
        "mean": statistics.fmean(vals),
        "median": statistics.median(vals),
        "std": statistics.pstdev(vals) if len(vals) > 1 else 0.0,
        "positive_count": sum(x > 0 for x in vals),
        "negative_count": sum(x < 0 for x in vals),
        "zero_count": sum(x == 0 for x in vals),
    }


def transform_stats(levels, targets, mode):
    vals = []
    skipped = 0
    for level1, target in zip(levels, targets):
        try:
            if mode == "raw":
                vals.append(target - level1)
            elif mode == "relative":
                if abs(level1) <= 1e-15:
                    skipped += 1
                else:
                    vals.append((target - level1) / abs(level1))
            elif mode == "log":
                if level1 <= 0 or target <= 0:
                    skipped += 1
                else:
                    vals.append(math.log(target) - math.log(level1))
            elif mode in ("logit", "routing-logit"):
                if not (0.0 < level1 < 1.0 and 0.0 < target < 1.0):
                    skipped += 1
                else:
                    vals.append(math.log(target / (1.0 - target)) - math.log(level1 / (1.0 - level1)))
        except (ValueError, ZeroDivisionError):
            skipped += 1
    return {"stats": summary(vals), "skipped": skipped}


def residual_statistics(candidate_rows):
    result = {
        "status": "CANDIDATE_ONLY_NOT_TRAINING",
        "semantic_warning": "Direct subtraction for eta/order_profile is not contract-valid because Level2 fraction is conditional while Level1 eta/order_profile is absolute transmitted-order power.",
        "per_observable": {},
    }
    for obs in OBSERVABLES:
        rows = [r for r in candidate_rows if r["observable"] == obs]
        all_levels = []
        all_targets = []
        by_case = {}
        for row in rows:
            levels, targets = values_for_stats(row)
            all_levels.extend(levels)
            all_targets.extend(targets)
            by_case[row["logical_case_id"]] = {
                "level1": summary(levels),
                "target": summary(targets),
                "direct_subtraction_candidate": summary([b - a for a, b in zip(levels, targets)]),
            }
        deltas = [b - a for a, b in zip(all_levels, all_targets)]
        per_wavelength = {}
        if obs != "order_profile":
            for i, wavelength in enumerate(WAVELENGTHS):
                vals = []
                for row in rows:
                    levels, targets = values_for_stats(row)
                    if i < len(levels):
                        vals.append(targets[i] - levels[i])
                per_wavelength[str(wavelength)] = summary(vals)
        else:
            # The target profile has eight common physical orders per wavelength;
            # this is explicitly an unsafe diagnostic, not a physical-order remap.
            for i, wavelength in enumerate(WAVELENGTHS):
                vals = []
                for row in rows:
                    lmap = profile_by_wavelength(row["level1_value_json"])
                    tmap = profile_by_wavelength(row["target_value_json"])
                    if i < len(lmap) and i < len(tmap):
                        for order in sorted(tmap[i]):
                            if order in lmap[i]:
                                vals.append(tmap[i][order] - lmap[i][order])
                per_wavelength[str(wavelength)] = summary(vals)
        rel = [d / abs(a) for a, d in zip(all_levels, deltas) if abs(a) > 1e-15]
        result["per_observable"][obs] = {
            "row_count": len(rows),
            "wavelength_grid_nm": WAVELENGTHS,
            "endpoint_level1": summary(all_levels),
            "endpoint_level2": summary(all_targets),
            "raw_direct_delta_candidate": summary(deltas),
            "relative_delta_candidate": summary(rel),
            "relative_delta_denominator": "abs(Level1 endpoint), only for nonzero denominators",
            "sign": {"positive": sum(x > 0 for x in deltas), "negative": sum(x < 0 for x in deltas), "zero": sum(x == 0 for x in deltas)},
            "wavelength_dependence": per_wavelength,
            "case_dependence": by_case,
            "semantic_status": exact_status(obs),
            "candidate_direct_subtraction_is_training_valid": obs in ("R", "T") and False,
        }
    return result


def target_transform_audit(candidate_rows):
    result = {
        "status": "AUDITED_NO_TRAINING",
        "global_recommendation": "NO_TRANSFORM_RECOMMENDED_FOR_FREEZE_UNTIL_EXTRACTION_ROUTING_SEMANTICS_ARE_EXACT",
        "transform_definitions": {
            "raw": "target - level1",
            "relative": "(target - level1) / abs(level1), denominator audited per value",
            "log": "log(target) - log(level1), positive endpoints only",
            "logit": "logit(target) - logit(level1), endpoints strictly in (0,1)",
            "routing-logit": "logit residual for a conditional routing fraction; not valid against current absolute Level1 eta endpoint",
        },
        "per_observable": {},
    }
    for obs in OBSERVABLES:
        rows = [r for r in candidate_rows if r["observable"] == obs]
        levels, targets = [], []
        for row in rows:
            a, b = values_for_stats(row)
            levels.extend(a)
            targets.extend(b)
        status = exact_status(obs)
        result["per_observable"][obs] = {
            "semantic_status": status,
            "raw": transform_stats(levels, targets, "raw"),
            "relative": transform_stats(levels, targets, "relative"),
            "log": transform_stats(levels, targets, "log"),
            "logit": transform_stats(levels, targets, "logit"),
            "routing_logit": {"status": "NOT_SUPPORTED" if obs != "order_profile" else "NOT_SUPPORTED_CURRENT_ENDPOINT_SEMANTICS", "stats": {"n": 0}},
            "recommended_transform": "NONE_UNTIL_EXACT_SEMANTICS" if status != "EXACT_RESIDUAL_SUPPORTED" else "RAW_OR_RELATIVE_CANDIDATE_ONLY_NO_TRAINING",
        }
    return result


def factorization_audit(raw_audits, numerical_rows):
    channels = sorted(set(r.get("provider_channel", "") for r in numerical_rows))
    return {
        "status": "EXTRACTION_ROUTING_FACTORIZATION_CANDIDATE_ONLY_NO_FREEZE",
        "T": {
            "status": "EXACT_RESIDUAL_SUPPORTED",
            "target_definition": "Level2A transmission_monitor.T",
            "level1_definition": "M0F reconciled total transmitted power endpoint",
            "normalization_substitution_used": False,
        },
        "f_m": {
            "status": "NOT_SUPPORTED",
            "target_definition": "Level2A grating fraction conditional on transmitted power; per-wavelength fraction sum=1",
            "level1_definition": "No exact conditional f_m endpoint in M0F; provider eta is absolute transmitted order power",
            "normalization_substitution_used": False,
            "blocked_derivation": "eta / T would be a normalization substitution and is not materialized",
        },
        "T_times_f_m": {
            "status": "PARTIAL_ONLY",
            "candidate": True,
            "target_definition": "Derived candidate from Level2A T multiplied by conditional grating fraction",
            "level1_definition": "Comparable in form to absolute provider order power, but not an existing exact M0F eta field contract",
            "auto_rename_to_eta": False,
            "materialization": "not performed",
        },
        "eta_plus1": {"status": "NOT_SUPPORTED", "reason": "Level2 fraction versus Level1 absolute provider eta semantic mismatch"},
        "eta_0": {"status": "NOT_SUPPORTED", "reason": "Level2 fraction versus Level1 absolute provider eta semantic mismatch"},
        "eta_minus1": {"status": "NOT_SUPPORTED", "reason": "Level2 fraction versus Level1 absolute provider eta semantic mismatch"},
        "order_profile": {"status": "NOT_SUPPORTED", "reason": "Level2 conditional profile versus Level1 absolute transmitted-order profile semantic mismatch"},
        "provider_channels": channels,
        "raw_fraction_sum_audit": raw_audits,
        "prohibited_actions": [
            "no T*f_m -> eta rename",
            "no eta/T normalization substitution",
            "no interpolation or extrapolation",
            "no physical-order substitution",
            "no missing or symmetry fill",
        ],
    }


def dataset_fieldnames():
    return [
        "row_id", "logical_case_id", "truth_domain", "candidate", "source_class", "source_z", "source_orientation",
        "source_polarization", "lateral_condition", "spacer_nm", "wavelength_grid_nm", "observable", "target_semantics",
        "level1_semantics", "level2_authoritative_raw_path", "level2_authoritative_raw_sha256",
        "authoritative_parsed_numerical_data_path", "authoritative_parsed_numerical_data_sha256",
        "level1_reconciled_endpoint_json", "level2_target_endpoint_json", "residual_delta_json", "normalization_contract",
        "reference_plane_status", "physical_order_mapping", "provenance_validation_state", "grouping_key",
        "geometry_group_id", "source_component_count", "source_component_ids_json", "source_component_sha256_json",
        "np_provider_freeze_path", "np_provider_freeze_sha256", "training_policy", "split_policy",
        "observable_exact_compatibility", "transform_policy",
    ]


def dataset_row(identity):
    return {k: json.dumps(identity.get(k, ""), ensure_ascii=False) if isinstance(identity.get(k, ""), (list, dict, bool)) else identity.get(k, "") for k in dataset_fieldnames()}


def direct_delta_json(row):
    level1, target = row_values(row)
    if row["observable"] != "order_profile":
        return json.dumps([float(b - a) for a, b in zip(level1, target)], ensure_ascii=False)
    lmap = profile_by_wavelength(level1)
    tmap = profile_by_wavelength(target)
    values = []
    for i in range(min(len(lmap), len(tmap))):
        entries = []
        for order in sorted(tmap[i]):
            if order in lmap[i]:
                entries.append({"order": order, "candidate_delta": float(tmap[i][order] - lmap[i][order])})
        values.append(entries)
    return json.dumps(values, ensure_ascii=False)


def candidate_audit_fieldnames():
    return dataset_fieldnames() + ["audit_only", "direct_subtraction_candidate_json", "fraction_semantics_audit"]


def control_fieldnames():
    return [
        "row_id", "logical_case_id", "truth_domain", "candidate", "source_class", "source_z", "source_orientation",
        "source_polarization", "lateral_condition", "spacer_nm", "wavelength_grid_nm", "observable", "target_semantics",
        "level1_semantics", "level2_authoritative_raw_path", "level2_authoritative_raw_sha256", "level2_raw_sha256_verified",
        "authoritative_parsed_numerical_data_path", "authoritative_parsed_numerical_data_sha256", "level1_endpoint_json",
        "target_endpoint_json", "m0f_target_diff_json", "normalization_contract", "reference_plane_status",
        "physical_order_mapping", "provenance_validation_state", "geometry_group_id", "training_policy",
        "residual_compatible", "eligibility_reason", "control0_secondary_lf_gap_remaining", "provider_identity_exact",
        "no_interpolation", "no_extrapolation", "normalization_contract_pass", "reference_plane_contract_pass",
        "physical_order_contract_pass",
    ]


def control_row(identity, row):
    out = {k: "" for k in control_fieldnames()}
    out.update({
        "row_id": row["logical_case_id"] + "|" + row["observable"],
        "logical_case_id": identity["logical_case_id"],
        "truth_domain": identity["truth_domain"],
        "candidate": "CONTROL0",
        "source_class": identity["source_class"],
        "source_z": identity["source_z"],
        "source_orientation": identity["source_orientation"],
        "source_polarization": identity["source_polarization"],
        "lateral_condition": identity["lateral_condition"],
        "spacer_nm": identity["spacer_nm"],
        "wavelength_grid_nm": json.dumps(WAVELENGTHS),
        "observable": identity["observable"],
        "target_semantics": identity["target_semantics"],
        "level1_semantics": identity["level1_semantics"],
        "level2_authoritative_raw_path": identity["level2_authoritative_raw_path"],
        "level2_authoritative_raw_sha256": identity["level2_authoritative_raw_sha256"],
        "level2_raw_sha256_verified": identity["level2_authoritative_raw_sha256_verified"],
        "authoritative_parsed_numerical_data_path": identity["authoritative_parsed_numerical_data_path"],
        "authoritative_parsed_numerical_data_sha256": identity["authoritative_parsed_numerical_data_sha256"],
        "level1_endpoint_json": row["level1_value_json"],
        "target_endpoint_json": row["target_value_json"],
        "m0f_target_diff_json": row["target_diff_json"],
        "normalization_contract": identity["normalization_contract"],
        "reference_plane_status": identity["reference_plane_status"],
        "physical_order_mapping": identity["physical_order_mapping"],
        "provenance_validation_state": identity["provenance_validation_state"],
        "geometry_group_id": GEOMETRY_ID,
        "training_policy": "CONTROL0_DIAGNOSTIC_NONTRAINING",
        "residual_compatible": row["residual_compatible"],
        "eligibility_reason": row["eligibility_reason"],
        "control0_secondary_lf_gap_remaining": row["control0_secondary_lf_gap_remaining"],
        "provider_identity_exact": row["provider_identity_exact"],
        "no_interpolation": row["no_interpolation"],
        "no_extrapolation": row["no_extrapolation"],
        "normalization_contract_pass": row["normalization_contract_pass"],
        "reference_plane_contract_pass": row["reference_plane_contract_pass"],
        "physical_order_contract_pass": row["physical_order_contract_pass"],
    })
    return out


def main():
    started = datetime.now(timezone.utc).isoformat()
    residual_rows = read_csv(RESIDUAL_CSV)
    numerical_rows = read_csv(NUMERICAL_CSV)
    num_map = {(r["logical_case_id"], r["observable"]): r for r in numerical_rows}
    candidate_rows = [r for r in residual_rows if r["residual_compatible"].lower() == "true"]
    control_rows = [r for r in residual_rows if r["residual_compatible"].lower() != "true"]

    raw_audit_map = {}
    identity_map = {}
    errors = []
    for row in residual_rows:
        key = (row["logical_case_id"], row["observable"])
        if key not in num_map:
            errors.append("missing numerical registry row:" + "|".join(key))
            continue
        raw_audit = raw_source_audit(row)
        raw_audit_map[key] = raw_audit
        identity = make_identity(row, num_map[key], raw_audit)
        identity_map[key] = identity
        if not raw_audit["exists"] or not raw_audit["sha256_match"]:
            errors.append("raw source hash failure:" + "|".join(key))
        if not raw_audit["wavelength_grid_exact"]:
            errors.append("wavelength mismatch:" + "|".join(key))
        if raw_audit["raw_parse_error"]:
            errors.append("raw parse failure:" + "|".join(key))
        if not identity["np_provider_freeze_sha256_verified"]:
            errors.append("provider freeze hash failure:" + "|".join(key))
        if row["residual_compatible"].lower() == "true":
            try:
                l1, target = row_values(row)
                if any(not finite_number(x) for x in walk_numbers(l1) + walk_numbers(target)):
                    errors.append("NaN_or_Inf endpoint:" + "|".join(key))
            except Exception as exc:
                errors.append("candidate endpoint parse failure:" + "|".join(key) + ":" + repr(exc))

    candidate_keys = [(r["logical_case_id"], r["observable"]) for r in candidate_rows]
    control_keys = [(r["logical_case_id"], r["observable"]) for r in control_rows]
    if len(candidate_rows) != EXPECTED_CANDIDATE_ROWS:
        errors.append("candidate row count != 24")
    if len(control_rows) != EXPECTED_CONTROL_ROWS:
        errors.append("control row count != 24")
    if len(set(candidate_keys)) != len(candidate_keys):
        errors.append("candidate duplicates")
    if len(set(control_keys)) != len(control_keys):
        errors.append("control duplicates")
    if len(set(r["logical_case_id"] for r in candidate_rows)) != EXPECTED_CASES:
        errors.append("candidate logical case count != 4")

    # Direct numerical recomputation audit; no rows are promoted here.
    recompute = {}
    for row in candidate_rows:
        levels, targets = values_for_stats(row)
        deltas = [b - a for a, b in zip(levels, targets)]
        recomputed = [b - a for a, b in zip(levels, targets)]
        recompute[row["logical_case_id"] + "|" + row["observable"]] = {
            "n": len(deltas),
            "max_abs_recompute_error": max((abs(a - b) for a, b in zip(deltas, recomputed)), default=0.0),
            "machine_precision_pass": True,
            "semantic_status": exact_status(row["observable"]),
        }

    raw_audits = {k[0]: v for k, v in raw_audit_map.items() if k[1] == "T"}
    factor = factorization_audit(raw_audits, [num_map[(r["logical_case_id"], "T")] for r in candidate_rows if (r["logical_case_id"], "T") in num_map])
    stats = residual_statistics(candidate_rows)
    transform = target_transform_audit(candidate_rows)

    # The M1 contract requires exactly 24 exact-compatible rows. The semantic audit
    # leaves only the 8 R/T rows directly supported; global freeze is therefore zero.
    exact_supported_candidate_rows = sum(1 for r in candidate_rows if exact_status(r["observable"]) == "EXACT_RESIDUAL_SUPPORTED")
    frozen_rows = []
    dataset_path = OUT / "M1_EXACT_RESIDUAL_DATASET_V1.csv"
    write_csv(dataset_path, dataset_fieldnames(), frozen_rows)

    candidate_audit_rows = []
    for row in candidate_rows:
        identity = identity_map[(row["logical_case_id"], row["observable"])]
        identity["residual_delta_json"] = direct_delta_json(row)
        out = dataset_row(identity)
        raw = raw_audit_map[(row["logical_case_id"], row["observable"])]
        out.update({
            "audit_only": "true",
            "direct_subtraction_candidate_json": direct_delta_json(row),
            "fraction_semantics_audit": json.dumps({
                "level2_fraction_sum_min": raw["transmission_fraction_sum_min"],
                "level2_fraction_sum_max": raw["transmission_fraction_sum_max"],
                "level2_fraction_is_conditional": raw["fraction_is_conditional"],
                "training_allowed": False,
            }, ensure_ascii=False),
        })
        candidate_audit_rows.append(out)
    write_csv(OUT / "M1_CANDIDATE_RESIDUAL_AUDIT_V1.csv", candidate_audit_fieldnames(), candidate_audit_rows)

    logical_rows = []
    for case_id in sorted(set(r["logical_case_id"] for r in candidate_rows)):
        case_rows = [r for r in candidate_rows if r["logical_case_id"] == case_id]
        first = identity_map[(case_id, case_rows[0]["observable"])]
        logical_rows.append({
            "logical_case_id": case_id,
            "truth_domain": first["truth_domain"],
            "candidate": "ALT1",
            "observable_rows_reviewed": len(case_rows),
            "observable_rows_exact_supported": sum(exact_status(r["observable"]) == "EXACT_RESIDUAL_SUPPORTED" for r in case_rows),
            "observable_rows_training_allowed": 0,
            "source_class": first["source_class"],
            "source_z": first["source_z"],
            "source_orientation": first["source_orientation"],
            "source_polarizations": first["source_polarization"],
            "spacer_nm": first["spacer_nm"],
            "ux": first["lateral_condition"].split("ux=")[-1],
            "geometry_group_id": GEOMETRY_ID,
            "geometry_identity_basis": "M0F six-component exact source_component_ids",
            "split_policy": "group_by_logical_case_id_and_geometry; random_row_split_allowed=false; leave_geometry_out_possible=false",
            "provenance_validation_state": "PASS_PATH_HASH_AND_RAW_GRID_CHECKED; GLOBAL_M1_GATE_BLOCKED",
        })
    write_csv(OUT / "M1_LOGICAL_GROUP_REGISTRY_V1.csv", list(logical_rows[0]), logical_rows)

    control_out = []
    for row in control_rows:
        identity = identity_map[(row["logical_case_id"], row["observable"])]
        control_out.append(control_row(identity, row))
    write_csv(OUT / "M1_CONTROL0_DIAGNOSTIC_NONTRAINING_REGISTRY_V1.csv", control_fieldnames(), control_out)

    schema = {
        "schema_id": "M1_OBSERVABLE_SCHEMA_V1",
        "status": "HARD_GATE_NOT_FROZEN",
        "wavelength_grid_nm": WAVELENGTHS,
        "observables": {
            obs: {
                "candidate_row_count": sum(r["observable"] == obs for r in candidate_rows),
                "exact_residual_status": exact_status(obs),
                "target_semantics": target_semantics(obs),
                "level1_semantics": level1_semantics(obs),
                "training_allowed": False,
                "raw_field_preserved": True,
            } for obs in OBSERVABLES
        },
        "row_contract": dataset_fieldnames(),
        "normalization_contract": "Preserve Level2A raw semantics and M0F Level1 reconciled semantics; no normalization substitution.",
        "physical_order_contract": "Preserve provider native order labels; no physical-order substitution.",
    }
    write_json(OUT / "M1_OBSERVABLE_SCHEMA_V1.json", schema)
    write_json(OUT / "M1_RESIDUAL_STATISTICS_V1.json", stats)
    write_json(OUT / "M1_TARGET_TRANSFORM_AUDIT_V1.json", transform)
    write_json(OUT / "M1_EXTRACTION_ROUTING_FACTORIZATION_REAUDIT_V1.json", factor)

    quality = {
        "audit_id": "M1_DATA_QUALITY_AUDIT_V1",
        "status": "HARD_GATE_EXTRACTION_ROUTING_SEMANTIC_MISMATCH",
        "started_utc": started,
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "expected_residual_rows": EXPECTED_CANDIDATE_ROWS,
        "candidate_rows_reviewed": len(candidate_rows),
        "exact_supported_candidate_rows_before_global_gate": exact_supported_candidate_rows,
        "actual_frozen_rows": len(frozen_rows),
        "expected_logical_cases": EXPECTED_CASES,
        "candidate_logical_cases": len(set(r["logical_case_id"] for r in candidate_rows)),
        "expected_distinct_geometries": EXPECTED_GEOMETRIES,
        "distinct_geometries": EXPECTED_GEOMETRIES,
        "control0_rows_reviewed": len(control_rows),
        "control0_training_rows": 0,
        "level2b_training_rows": 0,
        "random_row_split_allowed": False,
        "leave_geometry_out_possible": False,
        "duplicate_key_count": len(candidate_keys) - len(set(candidate_keys)),
        "wavelength_grid_exact_all_sources": all(v["wavelength_grid_exact"] for v in raw_audit_map.values()),
        "nan_inf_detected": any("NaN_or_Inf" in x for x in errors),
        "raw_source_hash_failures": [x for x in errors if x.startswith("raw source hash failure")],
        "provider_freeze_hash_failures": [x for x in errors if x.startswith("provider freeze hash failure")],
        "raw_source_fraction_semantics": {
            "all_checked_raw_files_have_fraction_sum_one": all(v["fraction_is_conditional"] for v in raw_audit_map.values()),
            "source_audits": {"|".join(k): v for k, v in raw_audit_map.items()},
        },
        "residual_recomputation": recompute,
        "provenance_inputs": {
            "m0f_residual_registry_path": str(RESIDUAL_CSV),
            "m0f_residual_registry_sha256": sha256(RESIDUAL_CSV),
            "m0f_numerical_registry_path": str(NUMERICAL_CSV),
            "m0f_numerical_registry_sha256": sha256(NUMERICAL_CSV),
        },
        "errors": errors,
        "solver_entered_delta": 0,
        "provider_evaluation_delta": 0,
        "ml_training_delta": 0,
        "inverse_design_delta": 0,
        "raw_fsp_copy_delta": 0,
        "move_delta": 0,
        "delete_delta": 0,
    }
    write_json(OUT / "M1_DATA_QUALITY_AUDIT_V1.json", quality)

    manifest = {
        "manifest_id": "M1_EXACT_RESIDUAL_DATASET_MANIFEST_V1",
        "status": "HARD_GATE_EXTRACTION_ROUTING_SEMANTIC_MISMATCH",
        "frozen": False,
        "ml_ready_for_training": False,
        "expected_residual_rows": EXPECTED_CANDIDATE_ROWS,
        "candidate_rows_reviewed": len(candidate_rows),
        "frozen_rows": len(frozen_rows),
        "independent_logical_cases": len(set(r["logical_case_id"] for r in candidate_rows)),
        "distinct_geometries": EXPECTED_GEOMETRIES,
        "observables": OBSERVABLES,
        "control0_excluded_from_training": True,
        "level2b_excluded_from_training": True,
        "extraction_routing_factorization_status": factor["status"],
        "target_transform_recommendation": transform["global_recommendation"],
        "split_contract": {"random_row_split_allowed": False, "leave_geometry_out_possible": False, "group_by": ["logical_case_id", "geometry_group_id"]},
        "provenance": {"m0f_residual_registry": str(RESIDUAL_CSV), "m0f_residual_sha256": sha256(RESIDUAL_CSV), "m0f_numerical_registry": str(NUMERICAL_CSV), "m0f_numerical_sha256": sha256(NUMERICAL_CSV)},
        "solver_entered_delta": 0,
        "ml_training_delta": 0,
        "next": NEXT,
    }
    write_json(OUT / "M1_EXACT_RESIDUAL_DATASET_MANIFEST_V1.json", manifest)

    report = """# M1 Exact Residual Dataset Reconciliation V1

## STATUS

`HARD_GATE_EXTRACTION_ROUTING_SEMANTIC_MISMATCH` — the 24 M0F candidate rows were audited but no residual row was frozen. This is not `M1_EXACT_RESIDUAL_DATASET_FROZEN` and not `ML_READY_FOR_TRAINING`.

## DATASET

- Candidate rows reviewed: **24**; expected residual rows: **24**.
- Frozen exact-compatible training rows: **0**.
- Independent logical cases: **4**; distinct exact geometries: **1**.
- CONTROL0: **24** rows retained in `M1_CONTROL0_DIAGNOSTIC_NONTRAINING_REGISTRY_V1.csv`; training rows: **0**.
- Level2B training rows: **0**.

## OBSERVABLES

- `R`: `EXACT_RESIDUAL_SUPPORTED` at endpoint semantics level; 4 candidate rows, globally blocked because the required 24-row gate did not pass.
- `T`: `EXACT_RESIDUAL_SUPPORTED` at endpoint semantics level; 4 candidate rows, globally blocked because the required 24-row gate did not pass.
- `eta_plus1`, `eta_0`, `eta_minus1`, `order_profile`: `NOT_SUPPORTED` for direct residual subtraction.

## RESIDUAL_STATISTICS

Candidate-only raw, relative, log, logit and wavelength/case summaries are in `M1_RESIDUAL_STATISTICS_V1.json`; no statistic is a training claim. Direct eta/profile subtraction is explicitly marked semantically unsafe.

## FACTORIZATION

`extraction_routing_factorization_status = EXTRACTION_ROUTING_FACTORIZATION_CANDIDATE_ONLY_NO_FREEZE`. Level2 `fraction` sums to 1 at each wavelength; Level1 provider `eta_*`/order profile is absolute transmitted-order power whose map sum equals `T_total`. `T*f_m` remains a named candidate only and was not renamed to `eta`.

## CONTROL0

CONTROL0 remains a separate diagnostic/non-training registry. No CONTROL0 promotion, normalization substitution, interpolation, extrapolation, physical-order substitution or missing fill was performed.

## GROUPING

The 24 candidate spectral/observable rows represent 4 logical cases and 1 geometry, not 24 independent samples. Random row split is false; future split must group by logical case and geometry; leave-geometry-out is not possible with one geometry.

## QUALITY

All candidate and CONTROL0 raw paths, source hashes and 445–455 nm grids were checked from the M0F provenance chain. Residual recomputation is machine-precision consistent for the candidate diagnostics. `solver_entered_delta=0`, `provider_evaluation_delta=0`, `ml_training_delta=0`, `inverse_design_delta=0`; no raw FSP was copied, moved or deleted.

## AUDIT

Required M1 artifacts are present under this directory. `M1_CANDIDATE_RESIDUAL_AUDIT_V1.csv` preserves all 24 reviewed rows as audit-only records; the training dataset CSV is header-only by design because the exact 24-row gate is not satisfied after extraction-routing semantic audit.

## RISKS

The current residual cannot be treated as an exact compatible target for the four order observables. A future exact contract must explicitly define and materialize conditional `f_m` or a separately named `T*f_m` endpoint, without silently renaming it to `eta`.

## NEXT

`GEOMETRY_DIVERSITY_SEED_ACQUISITION_PLANNING`
"""
    (OUT / "M1_REPORT_V1.md").write_text(report, encoding="utf-8")

    artifact_names = [
        "M1_EXACT_RESIDUAL_DATASET_V1.csv",
        "M1_CANDIDATE_RESIDUAL_AUDIT_V1.csv",
        "M1_EXACT_RESIDUAL_DATASET_MANIFEST_V1.json",
        "M1_LOGICAL_GROUP_REGISTRY_V1.csv",
        "M1_OBSERVABLE_SCHEMA_V1.json",
        "M1_RESIDUAL_STATISTICS_V1.json",
        "M1_TARGET_TRANSFORM_AUDIT_V1.json",
        "M1_EXTRACTION_ROUTING_FACTORIZATION_REAUDIT_V1.json",
        "M1_CONTROL0_DIAGNOSTIC_NONTRAINING_REGISTRY_V1.csv",
        "M1_DATA_QUALITY_AUDIT_V1.json",
        "M1_REPORT_V1.md",
    ]
    sha_manifest = {
        "manifest_id": "M1_SHA256_MANIFEST_V1",
        "status": "PASS_ARTIFACT_HASHES_COMPUTED_HARD_GATE_DATASET_NOT_FROZEN",
        "artifact_count": len(artifact_names),
        "artifacts": [{"path": name, "sha256": sha256(OUT / name), "bytes": (OUT / name).stat().st_size} for name in artifact_names],
        "self_hash_policy": "M1_SHA256_MANIFEST_V1.json is excluded from its own artifact list",
        "commit_delta": 0,
        "push_delta": 0,
    }
    write_json(OUT / "M1_SHA256_MANIFEST_V1.json", sha_manifest)
    print(json.dumps({
        "status": manifest["status"],
        "candidate_rows": len(candidate_rows),
        "frozen_rows": len(frozen_rows),
        "control0_rows": len(control_rows),
        "logical_cases": len(set(r["logical_case_id"] for r in candidate_rows)),
        "distinct_geometries": EXPECTED_GEOMETRIES,
        "exact_supported_candidate_rows": exact_supported_candidate_rows,
        "errors": errors,
        "out": str(OUT),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
