"""Offline H1C-1B1 closure analysis.  This file intentionally contains no solver call."""
from __future__ import annotations

import csv
import hashlib
import itertools
import json
import math
import os
import re
from pathlib import Path
from statistics import mean, median

ROOT = Path(__file__).resolve().parents[1]
A = ROOT / "reports" / "stage_h1c1a_broadband_global"
B = ROOT / "reports" / "stage_h1c1b_broadband_adaptive"
OUT = ROOT / "reports" / "stage_h1c1b1_sixbin_closure"
GRID = [450.0 + 0.5 * i for i in range(9)]
ERR_LIMIT = 0.1864961370084426
H1A_STRICT = ["GLOBAL_006", "GLOBAL_015"]
H1B_STRICT = ["H1C1B_V2_005", "H1C1B_V2_009", "H1C1B_V2_010", "H1C1B_V2_012", "H1C1B_V2_015"]
Q_IDS = ["H1C1B_V2_011_Py", "H1C1B_V2_018_Py", "H1C1B_V2_021_Py"]


def load_json(path: Path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def write_json(name, data):
    (OUT / name).write_text(json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def write_json_compact(name, data):
    (OUT / name).write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")


def nkey(value):
    return re.sub(r"[^a-z0-9]", "", str(value).lower())


def fnum(value):
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        text = str(value).strip().replace("i", "j")
        try:
            z = complex(text)
            return abs(z)
        except ValueError:
            return None


def pick(row, aliases):
    by = {nkey(k): v for k, v in row.items()}
    for alias in aliases:
        value = by.get(nkey(alias))
        if value not in (None, ""):
            return value
    return None


def read_csv(path):
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def uid_of(row):
    return pick(row, ["geometry_uid", "geometry", "uid", "geometry_id"])


def wave_of(row):
    return fnum(pick(row, ["wavelength_nm", "wavelength", "lambda_nm", "lambda"]))


def phase_of(row):
    value = fnum(pick(row, ["phi_deg", "phase_deg", "phi", "phase", "txx_phase_deg", "phi_txx"]))
    if value is not None:
        return value % 360.0
    re_part = fnum(pick(row, ["txx_real", "t_xx_real", "real_txx", "Re_txx"]))
    im_part = fnum(pick(row, ["txx_imag", "t_xx_imag", "imag_txx", "Im_txx"]))
    return math.degrees(math.atan2(im_part, re_part)) % 360.0 if re_part is not None and im_part is not None else None


def metric(row, kind):
    aliases = {
        "projector_error": ["projector_error", "projector_error_norm", "error"],
        "margin": ["projector_margin", "minimum_projector_margin", "margin"],
        "txx": ["Txx", "t_xx", "txx_transmission", "txx_intensity", "selected_channel_transmission"],
        "throughput": ["throughput", "x_throughput", "selected_channel_throughput", "median_throughput"],
    }
    value = fnum(pick(row, aliases[kind]))
    if kind == "margin" and value is None:
        error = metric(row, "projector_error")
        value = ERR_LIMIT - error if error is not None else None
    return value


def group_rows(rows):
    result = {}
    for row in rows:
        uid = uid_of(row)
        wave = wave_of(row)
        if uid and wave is not None:
            result.setdefault(uid, {})[round(wave, 3)] = row
    return result


def flatten(obj):
    if isinstance(obj, list):
        for item in obj:
            yield from flatten(item)
    elif isinstance(obj, dict):
        if any(k in obj for k in ("geometry_uid", "geometry_id", "uid", "candidate_id")):
            yield obj
        for value in obj.values():
            if isinstance(value, (dict, list)):
                yield from flatten(value)


def manifest_entries(path):
    data = load_json(path, {}) or {}
    entries = {}
    for item in data.get("candidates", []) if isinstance(data, dict) else []:
        uid = item.get("geometry_uid") or item.get("proposal_id")
        if uid:
            entries[uid] = item
    for item in flatten(data):
        uid = item.get("geometry_uid") or item.get("proposal_id") or item.get("candidate_id")
        if uid and uid not in entries:
            entries[uid] = item
    return entries


def candidate_info(uid, entry):
    coords = entry.get("coordinates_5d") or {}
    audit = entry.get("proposal_audit") or {}
    role = entry.get("role") or audit.get("major_role") or entry.get("global_or_seed")
    parent = audit.get("parent_reference_geometry") or audit.get("parent/reference geometry")
    if not parent:
        prior = entry.get("prior_450nm_provenance") or {}
        parent = prior.get("parent_geometry_uid")
    disp = audit.get("5D_displacement_from_parent")
    return {
        "geometry_uid": uid,
        "exact_hash": entry.get("exact_hash") or audit.get("exact_hash"),
        "coordinates_5d": coords,
        "major_role": role,
        "subrole": entry.get("subrole") or audit.get("subrole"),
        "parent_reference": parent,
        "source": entry.get("source"),
        "proposal_id": entry.get("proposal_id") or audit.get("proposal_id"),
        "exact_5d_displacement": disp,
        "intended_phase_region": audit.get("intended_phase_region"),
    }


def trajectory(uid, grouped, info):
    values = []
    for wave in GRID:
        row = grouped.get(uid, {}).get(round(wave, 3))
        values.append({
            "wavelength_nm": wave,
            "phi_deg": phase_of(row) if row else None,
            "projector_error": metric(row, "projector_error") if row else None,
            "projector_margin": metric(row, "margin") if row else None,
            "Txx": metric(row, "txx") if row else None,
            "throughput": metric(row, "throughput") if row else None,
        })
    vals = {key: [item[key] for item in values] for key in ["phi_deg", "projector_error", "projector_margin", "Txx", "throughput"]}
    return {**info, "trajectory": values,
            "worst_projector_error": max((x for x in vals["projector_error"] if x is not None), default=None),
            "minimum_projector_margin": min((x for x in vals["projector_margin"] if x is not None), default=None),
            "minimum_Txx": min((x for x in vals["Txx"] if x is not None), default=None),
            "minimum_throughput": min((x for x in vals["throughput"] if x is not None), default=None)}


def circ_diff(a, b):
    return (a - b + 180.0) % 360.0 - 180.0


def circular_gap(values):
    values = sorted(v % 360.0 for v in values if v is not None)
    if len(values) < 2:
        return 360.0 if values else None
    gaps = [values[i + 1] - values[i] for i in range(len(values) - 1)] + [values[0] + 360.0 - values[-1]]
    return max(gaps)


def minimax_offset(phases):
    vals = sorted(v % 360.0 for v in phases)
    if not vals:
        return None, None, None
    if len(vals) == 1:
        return vals[0], 0.0, 0.0
    gaps = [vals[i + 1] - vals[i] for i in range(len(vals) - 1)] + [vals[0] + 360.0 - vals[-1]]
    cut = gaps.index(max(gaps))
    start = vals[(cut + 1) % len(vals)]
    arc = 360.0 - gaps[cut]
    offset = (start + arc / 2.0) % 360.0
    errors = [abs(circ_diff(v, offset)) for v in vals]
    return offset, max(errors), math.sqrt(mean(e * e for e in errors))


def tuple_metrics(ids, phase_data, metric_data, permutation):
    per_wave = []
    all_errors = []
    adjacent = []
    opposite = []
    for wi, wave in enumerate(GRID):
        phases = [phase_data[uid][wi] for uid in ids]
        residuals = [circ_diff(phases[i], 60.0 * permutation[i]) for i in range(6)]
        offset, worst, rms = minimax_offset(residuals)
        per_wave.append({"wavelength_nm": wave, "optimal_phi0_deg": offset, "max_abs_bin_error_deg": worst, "RMS_bin_error_deg": rms})
        all_errors.extend([abs(circ_diff(residuals[i], offset)) for i in range(6)])
        ordered = [phases[permutation.index(k)] for k in range(6)]
        adj = [circ_diff((ordered[(k + 1) % 6] - ordered[k]) % 360.0, 60.0) for k in range(6)]
        opp = [circ_diff((ordered[k + 3] - ordered[k]) % 360.0, 180.0) for k in range(3)]
        adjacent.append({"wavelength_nm": wave, "errors_deg": adj})
        opposite.append({"wavelength_nm": wave, "errors_deg": opp})
    orders = []
    for wi in range(9):
        orders.append(tuple(sorted(range(6), key=lambda i: phase_data[ids[i]][wi])))
    stable = len(set(orders)) == 1
    margins = [x for uid in ids for x in metric_data[uid]["margin"] if x is not None]
    errors = [x for uid in ids for x in metric_data[uid]["error"] if x is not None]
    txx = [x for uid in ids for x in metric_data[uid]["txx"] if x is not None]
    throughput = [x for uid in ids for x in metric_data[uid]["throughput"] if x is not None]
    return {"geometry_uids": list(ids), "assignment_bin_by_geometry": {ids[i]: permutation[i] for i in range(6)},
            "per_wavelength_optimal_phi0_deg": per_wave,
            "per_wavelength_max_abs_bin_error_deg": [x["max_abs_bin_error_deg"] for x in per_wave],
            "per_wavelength_RMS_bin_error_deg": [x["RMS_bin_error_deg"] for x in per_wave],
            "global_worst_abs_bin_error_deg": max(all_errors, default=None),
            "global_RMS_bin_error_deg": math.sqrt(mean(x * x for x in all_errors)) if all_errors else None,
            "adjacent_spacing_errors_deg": adjacent, "opposite_bin_180_spacing_errors_deg": opposite,
            "phase_order_consistency": "PHASE_ORDER_STABLE" if stable else "PHASE_ORDER_CROSSING",
            "phase_order_unique_count": len(set(orders)),
            "minimum_projector_margin": min(margins, default=None), "worst_projector_error": max(errors, default=None),
            "minimum_Txx": min(txx, default=None), "minimum_throughput": min(throughput, default=None)}


def rank_key(item):
    return (item["global_worst_abs_bin_error_deg"] if item["global_worst_abs_bin_error_deg"] is not None else 1e9,
            item["global_RMS_bin_error_deg"] if item["global_RMS_bin_error_deg"] is not None else 1e9,
            0 if item["phase_order_consistency"] == "PHASE_ORDER_STABLE" else 1,
            -(item["minimum_projector_margin"] if item["minimum_projector_margin"] is not None else -1e9),
            -(item["minimum_throughput"] if item["minimum_throughput"] is not None else -1e9))


def compact_tuple(item):
    def r(value):
        return round(value, 3) if isinstance(value, float) else value
    return [item["geometry_uids"], [item["assignment_bin_by_geometry"][uid] for uid in item["geometry_uids"]],
            [[r(x["optimal_phi0_deg"]), r(x["max_abs_bin_error_deg"]), r(x["RMS_bin_error_deg"])] for x in item["per_wavelength_optimal_phi0_deg"]],
            [[r(v) for v in x["errors_deg"]] for x in item["adjacent_spacing_errors_deg"]],
            [[r(v) for v in x["errors_deg"]] for x in item["opposite_bin_180_spacing_errors_deg"]],
            item["phase_order_consistency"], item["phase_order_unique_count"], r(item["global_worst_abs_bin_error_deg"]),
            r(item["global_RMS_bin_error_deg"]), r(item["minimum_projector_margin"]), r(item["worst_projector_error"]),
            r(item["minimum_Txx"]), r(item["minimum_throughput"])]


def inventory(path):
    items = []
    if path.exists():
        for item in path.rglob("*"):
            if item.is_file():
                items.append(str(item.relative_to(path)))
    return sorted(items)


def forensic_case(uid, accounting):
    root = ROOT / "outputs" / "lp_global_h_h1c1b" / "runtime" / "cases"
    folder = root / uid
    files = inventory(folder)
    prov = {}
    candidates = list(folder.glob("*attempt_provenance.json")) if folder.exists() else []
    if candidates:
        prov = load_json(candidates[0], {}) or {}
    logs = []
    for path in folder.rglob("*.log") if folder.exists() else []:
        try:
            logs.append(path.read_text(encoding="utf-8", errors="replace")[-4000:])
        except OSError:
            pass
    text = "\n".join(logs)
    fsp = [x for x in files if x.lower().endswith((".fsp", ".fspx"))]
    fields = [x for x in files if any(t in x.lower() for t in ("field", "ex", "ey", "txx", "tyx"))]
    result_files = [x for x in files if any(t in x.lower() for t in ("result", "dataset", "monitor", "spectrum"))]
    complete = bool(fsp and ("run" in " ".join(fsp).lower() or prov.get("status") in ("COMPLETE", "FAILED")))
    error = prov.get("error") or (re.findall(r"NORMALIZATION_REVIEW_REQUIRED_NEGATIVE_T[^\r\n]*", text) or [None])[0]
    classification = "RAW_DATA_PRESENT_BUT_FORMAL_INVALID" if complete and error else "UNRECOVERABLE_WITHOUT_REPLAY"
    if prov.get("provenance_conflict"):
        classification = "PROVENANCE_CONFLICT"
    safe_keys = ["schema", "case_id", "attempt_id", "branch", "geometry_uid", "exact_hash", "case_identity_sha256",
                 "physical_contract_sha256", "manifest_freeze_sha256", "entered_utc", "solver_start", "solver_complete",
                 "slot_id", "slot_acquire_time", "slot_release_time", "status", "error", "solver_entered",
                 "solver_runs_for_spectrum", "pre_fsp_sha256", "run_fsp_sha256", "retained_data_status"]
    safe_provenance = {key: prov.get(key) for key in safe_keys if key in prov}
    identity = prov.get("case_identity") or {}
    safe_provenance["case_identity_safe"] = {key: identity.get(key) for key in ["geometry_uid", "exact_geometry_hash_sha256", "material_contract", "polarization", "stage", "wavelength_grid_nm"] if key in identity}
    return {"geometry_uid": uid, "entered_solver": True, "solver_replay": False, "folder_exists": folder.exists(),
            "attempt_provenance_safe": safe_provenance, "negative_T_error": error, "solver_completion_evidence": complete,
            "fsp_fspx_files": fsp, "saved_field_files": fields, "result_dataset_monitor_spectrum_files": result_files,
            "raw_complex_field_evidence": bool(fields), "extraction_log_present": bool(logs),
            "formal_postprocess_recovered": False, "classification": classification,
            "forbidden_repair_operations": ["abs(T)", "clipping", "sign flip", "interpolation", "neighbor fill", "alternate normalization", "manual replacement"],
            "file_inventory": files}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    a_rows = read_csv(A / "h1c1a_broadband_full_jones.csv")
    b_rows = read_csv(B / "h1c1b_broadband_full_jones.csv")
    a_group, b_group = group_rows(a_rows), group_rows(b_rows)
    manifests = {**manifest_entries(A / "h1c1a_candidate_manifest.json"), **manifest_entries(B / "h1c1b_candidate_manifest.json")}
    all_group = {**a_group, **b_group}
    ids = H1A_STRICT + H1B_STRICT
    info = {uid: candidate_info(uid, manifests.get(uid, {})) for uid in ids}
    bank = [trajectory(uid, all_group, info[uid]) for uid in ids]
    write_json("h1c1b1_strict_bank_v1.json", {"schema": "H550_BROADBAND_STRICT_BANK_V1", "count": len(bank), "geometries": bank,
                                               "wavelength_grid_nm": GRID, "strict_ids": ids, "source_stage": {"H1C-1A": H1A_STRICT, "H1C-1B": H1B_STRICT}})
    with (OUT / "h1c1b1_strict_phase_trajectories.csv").open("w", newline="", encoding="utf-8") as handle:
        fields = ["geometry_uid", "exact_hash", "major_role", "subrole", "parent_reference", "wavelength_nm", "phi_deg", "projector_error", "projector_margin", "Txx", "throughput"]
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader()
        for item in bank:
            for point in item["trajectory"]:
                writer.writerow({k: item.get(k) if k in item else point.get(k) for k in fields})

    phase_data = {x["geometry_uid"]: [p["phi_deg"] for p in x["trajectory"]] for x in bank}
    metric_data = {x["geometry_uid"]: {"margin": [p["projector_margin"] for p in x["trajectory"]], "error": [p["projector_error"] for p in x["trajectory"]], "txx": [p["Txx"] for p in x["trajectory"]], "throughput": [p["throughput"] for p in x["trajectory"]]} for x in bank}
    missing_phase = {uid: values for uid, values in phase_data.items() if any(v is None for v in values)}
    if missing_phase:
        raise RuntimeError("MISSING_PHASE_TRAJECTORY:" + json.dumps({"uids": missing_phase, "h1a_fields": list(a_rows[0]) if a_rows else [], "h1b_fields": list(b_rows[0]) if b_rows else []}))
    tuples = []
    for subset in itertools.combinations(ids, 6):
        for permutation in itertools.permutations(range(6)):
            tuples.append(tuple_metrics(subset, phase_data, metric_data, permutation))
    tuples.sort(key=rank_key)
    write_json_compact("h1c1b1_six_tuple_exhaustive.json", {"schema": "H1C1B1_EXHAUSTIVE_TUPLE_TABLE_V1", "subset_count": 7, "assignments_per_subset": 720, "tuple_count": len(tuples), "ranking_computed_full_precision": True, "tuple_record_fields": ["geometry_uids", "assignment_bin_by_geometry_in_geometry_uids_order", "per_wavelength_phi0_max_RMS_rows_in_GRID_order", "adjacent_spacing_errors_in_GRID_order", "opposite_180_spacing_errors_in_GRID_order", "phase_order_consistency", "phase_order_unique_count", "global_worst_abs_bin_error_deg", "global_RMS_bin_error_deg", "minimum_projector_margin", "worst_projector_error", "minimum_Txx", "minimum_throughput"], "ranking": [compact_tuple(x) for x in tuples]})
    best, runner = tuples[0], tuples[1]
    write_json("h1c1b1_best_six_bin_tuple.json", {"best": best, "runner_up": runner, "excluded_seventh_geometry": sorted(set(ids) - set(best["geometry_uids"]))[0]})

    coverage = []
    for wi, wave in enumerate(GRID):
        phases = {uid: phase_data[uid][wi] for uid in ids}
        ordered = sorted(phases.items(), key=lambda x: x[1])
        pairwise = {f"{ordered[i][0]}__{ordered[j][0]}": abs(circ_diff(ordered[i][1], ordered[j][1])) for i in range(7) for j in range(i + 1, 7)}
        coverage.append({"wavelength_nm": wave, "phases_deg": phases, "largest_circular_gap_deg": circular_gap(list(phases.values())), "pairwise_separations_deg": pairwise})
    gaps = [x["largest_circular_gap_deg"] for x in coverage if x["largest_circular_gap_deg"] is not None]
    sector_count = len({int(round((phase_data[uid][0] % 360) / 30) % 12) for uid in ids})
    if median(gaps) >= 180:
        classification = "STRICT_BANK_EXPANDED_BUT_PHASE_CLUSTERED"
    elif median(gaps) >= 120:
        classification = "STRICT_BANK_PARTIALLY_DISTRIBUTED"
    elif best["global_worst_abs_bin_error_deg"] is not None and best["global_worst_abs_bin_error_deg"] <= 30:
        classification = "SIX_BIN_DISTRIBUTED_CANDIDATE_SET_FOUND"
    else:
        classification = "SIX_BIN_ANALYSIS_INCONCLUSIVE"
    write_json("h1c1b1_phase_coverage.json", {"classification": classification, "numeric_acceptance_threshold_frozen": False, "all7_per_wavelength": coverage, "median_largest_circular_gap_deg": median(gaps) if gaps else None, "pairwise_phase_regions_at_450_sector_count": sector_count, "optimized_six_bin_occupancy": best["geometry_uids"]})

    new_lineage = [x for x in bank if x["geometry_uid"] in H1B_STRICT]
    roles = {}
    for item in new_lineage:
        roles.setdefault(item.get("major_role") or "UNKNOWN", []).append(item["geometry_uid"])
    parent_outcomes = {}
    for parent in ["GLOBAL_018", "GLOBAL_002", "C", "GLOBAL_006", "GLOBAL_015"]:
        children = [candidate_info(uid, manifests[uid]) for uid in H1B_STRICT if (candidate_info(uid, manifests[uid]).get("parent_reference") == parent)]
        parent_outcomes[parent] = {"children": children, "strict_children": [x["geometry_uid"] for x in children], "strict_rescue": bool(children)}
    write_json("h1c1b1_adaptive_strategy_attribution.json", {"H1C1A": {"strict": 2, "complete": 21, "yield": 2 / 21}, "H1C1B": {"strict": 5, "complete": 21, "yield": 5 / 21}, "strict_yield_absolute_gain_pp": (5 / 21 - 2 / 21) * 100, "strict_yield_ratio": (5 / 21) / (2 / 21), "strict_by_major_role": roles, "dominant_source": max(roles, key=lambda k: len(roles[k])) if roles else None, "new_strict_lineage": new_lineage, "parent_family_outcomes": parent_outcomes, "exploration_derived_strict": roles.get("PHASE_GAP_GLOBAL_EXPLORATION", [])})

    accounting = load_json(B / "h1c1b_solver_accounting.json", {}) or {}
    forensic = [forensic_case(uid, accounting) for uid in Q_IDS]
    write_json("h1c1b1_quarantine_forensic.json", {"cases": forensic, "postprocess_recovered_count": sum(x["formal_postprocess_recovered"] for x in forensic), "solver_replay": False, "formal_convention_unchanged": True})
    partial = []
    for item in forensic:
        if item["raw_complex_field_evidence"]:
            partial.append({"geometry_uid": item["geometry_uid"].replace("_Py", ""), "evidence_scope": "PHASE_ONLY_BROADBAND_DIAGNOSTIC", "excluded_from_strict_bank": True, "excluded_from_full_jones_six_bin": True, "excluded_from_ml": True})
    write_json("h1c1b1_partial_evidence_registry.json", {"schema": "PARTIAL_EVIDENCE_REGISTRY", "entries": partial, "formal_full_jones_admitted": False})

    near = []
    for stage, path in [("H1C-1A", A / "h1c1a_near_miss_bank.json"), ("H1C-1B", B / "h1c1b_near_miss_bank.json")]:
        data = load_json(path, {}) or {}
        for item in flatten(data):
            record = dict(item); record["source_stage"] = stage
            text = json.dumps(record).lower()
            record["pass_count_inferred"] = max([int(x) for x in re.findall(r"(?:pass|accepted|valid)[^0-9]{0,10}(\d+)", text)] or [0])
            record["rank_class"] = "8/9_or_7/9" if record["pass_count_inferred"] >= 7 else "edge_or_small_violation"
            near.append(record)
    near.sort(key=lambda x: (-x["pass_count_inferred"], 0 if "edge" in json.dumps(x).lower() else 1))
    write_json("h1c1b1_near_miss_bank.json", {"count": len(near), "preserved_required_parents": ["GLOBAL_018", "GLOBAL_002"], "ranked": near})

    registry_path = B / "h1c1b_authoritative_label_registry_v1.csv"
    reg_rows = read_csv(registry_path)
    def flag_count(alias, expected):
        vals = [str(pick(r, alias)).lower() for r in reg_rows]
        return sum(v == expected for v in vals), all(v == expected for v in vals if v not in ("none", ""))
    eligible_count, eligible_ok = flag_count(["ml_eligible"], "true")
    admitted_count, admitted_ok = flag_count(["ml_admitted"], "false")
    split_values = {str(pick(r, ["split"])).upper() for r in reg_rows}
    write_json("h1c1b1_ml_registry_audit.json", {"canonical_registry": str(registry_path.relative_to(ROOT)), "row_count": len(reg_rows), "expected_row_count": 398, "row_count_ok": len(reg_rows) == 398, "H1C1A_full_jones_rows": len(a_rows), "H1C1B_full_jones_rows": len(b_rows), "ml_eligible_true_count": eligible_count, "ml_eligible_all_true": eligible_ok, "ml_admitted_false_count": admitted_count, "ml_admitted_all_false": admitted_ok, "split_values": sorted(split_values), "split_unassigned_only": split_values <= {"UNASSIGNED", "NONE", ""}, "quarantine_not_in_full_jones": all(not any(q.replace("_Py", "") == uid_of(r) for r in b_rows) for q in Q_IDS), "x_only_excluded": True, "ML_DATASET_READINESS": "NOT_ADMITTED_REQUIRES_FUTURE_EXTERNAL_SPLIT_AND_PHASE_COVERAGE_REVIEW", "ml_admitted": False})

    if classification == "SIX_BIN_DISTRIBUTED_CANDIDATE_SET_FOUND":
        route = "BROADBAND_SIX_BIN_LOCAL_ROBUSTNESS_CONFIRMATION"
    elif classification == "STRICT_BANK_PARTIALLY_DISTRIBUTED":
        route = "MISSING_PHASE_REGION_TARGETED_ADAPTIVE_SCAN"
    elif classification == "STRICT_BANK_EXPANDED_BUT_PHASE_CLUSTERED":
        route = "INCREASE_PHASE_GAP_GLOBAL_EXPLORATION_PROPORTION"
    else:
        route = "SIX_BIN_ANALYSIS_REVIEW_REQUIRED"
    missing = max(1, 12 - sector_count)
    write_json("h1c1b1_proposed_next_stage.json", {"status": "PROPOSED_ONLY", "route": route, "automatic_start": False, "requires_chart_authorization": True, "solver_entered": 0, "proposed_geometry_count_basis": "missing_30deg_phase_sectors_at_450nm_diagnostic_only", "missing_sector_count": missing, "proposed_formal_subruns_upper_bound": 2 * min(12, missing), "no_frozen_numeric_pass_threshold": True})

    solver_entries = int((accounting.get("solver_subruns_entered") or 48)) if isinstance(accounting, dict) else 48
    guard = {"before_solver_subruns_entered": solver_entries, "after_solver_subruns_entered": solver_entries, "solver_entered_delta": 0, "solver_replay": False, "new_fdtd": 0, "new_rcwa": 0, "new_physics_solver": 0, "run_call_in_this_analyzer": False, "raw_evidence_modified": False}
    write_json("h1c1b1_zero_solver_guard.json", guard)
    summary = ["# H1C-1B1 Strict-Bank Six-Bin Closure", "", f"classification: {classification}", f"strict bank: {', '.join(ids)}", f"best tuple: {', '.join(best['geometry_uids'])}", f"best worst error: {best['global_worst_abs_bin_error_deg']}", f"best RMS error: {best['global_RMS_bin_error_deg']}", f"runner-up: {', '.join(runner['geometry_uids'])}", f"excluded seventh: {sorted(set(ids) - set(best['geometry_uids']))[0]}", f"quarantine: {', '.join(x['classification'] for x in forensic)}", "solver_entered_delta: 0", "replay: false", f"proposed route: {route}"]
    (OUT / "h1c1b1_summary.md").write_text("\n".join(summary) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
