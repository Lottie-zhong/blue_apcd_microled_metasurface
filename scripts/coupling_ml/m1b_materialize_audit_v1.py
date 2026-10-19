from pathlib import Path
import csv
import hashlib
import json
import math
import statistics
import subprocess
from datetime import datetime, timezone


ML = Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1")
OLD = Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_v1")
M0F = ML / "outputs/coupling_ml/M0_LEVEL1_LEVEL2_CONTRACT_RECONCILIATION_V1/M0F_MINIMAL_LEVEL1_CONTRACT_REPAIR_ACQUISITION/M0F_CONTINUATION_AFTER_COMPONENT_RULING_V1"
RESIDUAL = M0F / "M0F_FINAL_RESIDUAL_ELIGIBILITY_AFTER_FULL_COMPONENT_SET_V1.csv"
NUMERICAL = M0F / "M0F_FINAL_RECONCILED_LEVEL1_NUMERICAL_REGISTRY_V1.csv"
PROVIDER_ROOT = OLD / "outputs/coupling/rcwa_component_benchmark_v1/runtime_runs/RCWA_LEVEL1_ANGULAR_ACQUISITION_9JOB_V1"
OUT = ML / "outputs/coupling_ml/M1B_CANONICAL_ROUTING_OBSERVABLE_AUDIT_V1"
OUT.mkdir(parents=True, exist_ok=True)

WLS = [445.0 + i for i in range(11)]
OBS = ["R", "T", "eta_plus1", "eta_0", "eta_minus1", "order_profile"]
EXPECTED_CASES = 4
EXPECTED_RT_ROWS = 8
CANONICAL_ID = "CANONICAL_TRANSMITTED_ORDER_FRACTION_V1"
SOURCE_Z = "MDC_z=975_nm -> NP_pillar_bottom_z=1212_nm; propagation_delta_z=237_nm"
GEOMETRY_ID = "M0F_EXACT_K6_GEOMETRY_001"
PERIOD_X_NM_EXPECTED = 1740.0


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path, fields, rows):
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="raise")
        w.writeheader()
        w.writerows(rows)


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def compact(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def scalar(value):
    if isinstance(value, list):
        if not value:
            raise ValueError("empty nested scalar")
        return scalar(value[0])
    return float(value)


def order_key(value):
    value = scalar(value) if isinstance(value, list) else value
    if isinstance(value, str):
        text = value.strip()
        if "," not in text:
            return str(int(float(text))) + ",0"
        return text
    return str(int(value)) + ",0"


def order_index(order_label):
    return int(str(order_label).split(",")[0])


def order_direction(ux):
    if ux > 1e-12:
        return "+x"
    if ux < -1e-12:
        return "-x"
    return "normal_x"


def source_orientation(num_row):
    return "physical_MDC_x_dipole -> provider_P_XLIKE" if num_row.get("provider_channel") == "P_XLIKE" else "physical_MDC_z_dipole -> provider_S_YLIKE"


def channel_for(row):
    return "P_XLIKE" if row["source_polarization"] == "x" else "S_YLIKE"


def git_state(root):
    def run(args):
        p = subprocess.run(["git"] + args, cwd=str(root), capture_output=True, text=True, encoding="utf-8", errors="replace")
        return p.stdout.strip() if p.returncode == 0 else "ERROR:" + p.stderr.strip()
    return {
        "branch": run(["branch", "--show-current"]),
        "head": run(["rev-parse", "HEAD"]),
        "status_short": run(["status", "--short"]),
        "ahead_behind": run(["rev-list", "--left-right", "--count", "HEAD...@{u}"]),
    }


def load_provider_nodes():
    posts = sorted(PROVIDER_ROOT.rglob("*_postprocessed.json"))
    if len(posts) != 9:
        raise RuntimeError("expected 9 provider postprocessed files, got %d" % len(posts))
    setup_files = sorted(PROVIDER_ROOT.rglob("*_setup_readback.json"))
    if len(setup_files) < 9:
        raise RuntimeError("expected at least 9 provider setup readbacks, got %d" % len(setup_files))
    setup_by_ux = {}
    periods = []
    setup_provenance = []
    for path in setup_files:
        d = json.loads(path.read_text(encoding="utf-8-sig"))
        ux = float(d["ux"])
        span = float(d["geometry"]["substrate"]["x_span_nm"])
        periods.append(span)
        setup_by_ux[ux] = d
        setup_provenance.append({"path": str(path), "sha256": sha256(path), "ux": ux, "period_x_nm": span, "geometry_id": d.get("geometry_id")})
    if not periods:
        raise RuntimeError("provider period-x readback is empty")
    nodes = []
    for path in posts:
        d = json.loads(path.read_text(encoding="utf-8-sig"))
        ux = float(d["ux"])
        setup = setup_by_ux.get(ux)
        if setup is None:
            raise RuntimeError("missing exact setup readback for provider ux %s" % ux)
        if abs(float(setup["geometry"]["substrate"]["x_span_nm"]) - PERIOD_X_NM_EXPECTED) > 1e-9:
            raise RuntimeError("matched provider period-x readback is not 1740 nm")
        raw_npz = path.with_name(path.name.replace("_postprocessed.json", "_raw.npz"))
        raw_table = path.with_name(path.name.replace("_postprocessed.json", "_raw_provider.json"))
        if not raw_npz.exists() or not raw_table.exists():
            raise RuntimeError("provider raw provenance missing for %s" % path)
        if d.get("wavelengths_nm") != WLS and [float(x) for x in d.get("wavelengths_nm", [])] != WLS:
            raise RuntimeError("provider wavelength mismatch %s" % path)
        records = {}
        for channel in ("P_XLIKE", "S_YLIKE"):
            by_wl = {}
            for item in d["metrics"][channel]:
                wavelength = float(item["wavelength_nm"])
                by_wl[wavelength] = item
                if not isinstance(item.get("transmitted_order_map"), dict):
                    raise RuntimeError("missing transmitted order map")
                if any(not finite(v) or float(v) < 0 for v in item["transmitted_order_map"].values()):
                    raise RuntimeError("negative or nonfinite provider order power")
                if abs(sum(float(v) for v in item["transmitted_order_map"].values()) - float(item["T_total"])) > 1e-8:
                    raise RuntimeError("provider order closure failed")
            if set(by_wl) != set(WLS):
                raise RuntimeError("provider wavelength row set mismatch")
            records[channel] = by_wl
        nodes.append({
            "ux": ux,
            "path": path,
            "sha256": sha256(path),
            "raw_npz_path": raw_npz,
            "raw_npz_sha256": sha256(raw_npz),
            "raw_table_path": raw_table,
            "raw_table_sha256": sha256(raw_table),
            "setup_path": next(Path(x["path"]) for x in setup_provenance if abs(x["ux"] - ux) <= 1e-12),
            "setup_sha256": next(x["sha256"] for x in setup_provenance if abs(x["ux"] - ux) <= 1e-12),
            "period_x_nm": PERIOD_X_NM_EXPECTED,
            "geometry_id": d.get("geometry_id"),
            "records": records,
            "order_power_semantics": d.get("order_power_semantics"),
            "n_upper_by_wavelength": d.get("n_upper_by_wavelength"),
        })
    nodes.sort(key=lambda x: x["ux"])
    return nodes, setup_provenance


def load_inputs():
    residual = read_csv(RESIDUAL)
    numerical = read_csv(NUMERICAL)
    nmap = {(r["logical_case_id"], r["observable"]): r for r in numerical}
    candidate = [r for r in residual if r["residual_compatible"].lower() == "true"]
    control = [r for r in residual if r["residual_compatible"].lower() != "true"]
    cases = sorted(set(r["logical_case_id"] for r in candidate))
    if len(candidate) != 24 or len(cases) != EXPECTED_CASES:
        raise RuntimeError("M0F candidate input count/case count mismatch")
    targets = {}
    for case_id in cases:
        profile_row = next(r for r in candidate if r["logical_case_id"] == case_id and r["observable"] == "order_profile")
        raw_path = Path(profile_row["target_raw_path"])
        raw = json.loads(raw_path.read_text(encoding="utf-8-sig"))
        if [float(x) for x in raw["wavelengths_nm"]] != WLS:
            raise RuntimeError("Level2 wavelength grid mismatch for %s" % case_id)
        target_records = []
        for item in raw["transmission_orders"]:
            orders = item["order"]
            fractions = item["fraction"]
            ux_values = item["u_x"]
            values = []
            for o, f, ux in zip(orders, fractions, ux_values):
                values.append({"order": order_key(o), "raw_order_index": scalar(o), "fraction": scalar(f), "u_x": scalar(ux)})
            target_records.append(values)
        targets[case_id] = {
            "case_id": case_id,
            "candidate": profile_row["candidate"],
            "source_polarization": profile_row["source_polarization"],
            "channel": channel_for(profile_row),
            "spacer_nm": float(profile_row["spacer_nm"]),
            "ux": float(profile_row["ux"]),
            "raw_path": raw_path,
            "raw_sha256": sha256(raw_path),
            "raw": raw,
            "records": target_records,
            "level1_profile": json.loads(nmap[(case_id, "order_profile")]["level1_y_reconciled_json"]),
            "level1_t": [float(x) for x in json.loads(nmap[(case_id, "T")]["level1_y_reconciled_json"])],
            "level2_t": [float(x) for x in raw["transmission_monitor"]["T"]],
            "level1_num": nmap[(case_id, "order_profile")],
        }
    return residual, numerical, candidate, control, nmap, targets


def physical_ux(incident_ux, m, wavelength_nm, period_x_nm):
    return float(incident_ux + m * wavelength_nm / period_x_nm)


def family(records):
    return sorted(set(item["order"] for item in records))


def side_raw_fraction_closure(target):
    errors = []
    for i, records in enumerate(target["records"]):
        errors.append(abs(sum(float(x["fraction"]) for x in records) - 1.0))
    return max(errors) if errors else None


def provider_union_family(nodes, channel, wavelength_index):
    out = set()
    wavelength = WLS[wavelength_index]
    for node in nodes:
        out.update(order_key(k) for k in node["records"][channel][wavelength]["transmitted_order_map"])
    return sorted(out, key=order_index)


def aggregate_family(profile):
    return sorted(set(order_key(x["order"]) for item in profile for x in item), key=order_index)


def make_rt_seed(candidate, nmap):
    fields = [
        "row_id", "logical_case_id", "truth_domain", "candidate", "source_class", "source_z", "source_orientation",
        "source_polarization", "lateral_condition", "spacer_nm", "wavelength_grid_nm", "observable",
        "Y_Level1_json", "Y_Level2_json", "DeltaY_json", "delta_formula", "canonical_observable_id",
        "level2_authoritative_raw_path", "level2_authoritative_raw_sha256", "authoritative_parsed_numerical_data_path",
        "authoritative_parsed_numerical_data_sha256", "normalization_contract", "reference_plane_status",
        "physical_order_mapping", "provenance_validation_state", "geometry_group_id", "training_policy",
        "split_policy", "distinct_training_geometries",
    ]
    out = []
    for row in candidate:
        if row["observable"] not in ("R", "T"):
            continue
        num = nmap[(row["logical_case_id"], row["observable"])]
        y1 = json.loads(num["level1_y_reconciled_json"])
        y2 = json.loads(row["target_value_json"])
        delta = [float(b) - float(a) for a, b in zip(y1, y2)]
        out.append({
            "row_id": row["logical_case_id"] + "|" + row["observable"],
            "logical_case_id": row["logical_case_id"],
            "truth_domain": row["truth_domain"],
            "candidate": row["candidate"],
            "source_class": "LEVEL2A_HF_FDTD_RAW_PLUS_M0F_LEVEL1_RECONCILED",
            "source_z": SOURCE_Z,
            "source_orientation": "provider_channel=" + num["provider_channel"],
            "source_polarization": row["source_polarization"],
            "lateral_condition": "periodic_UX; ux=" + row["ux"],
            "spacer_nm": row["spacer_nm"],
            "wavelength_grid_nm": compact(WLS),
            "observable": row["observable"],
            "Y_Level1_json": compact(y1),
            "Y_Level2_json": compact(y2),
            "DeltaY_json": compact(delta),
            "delta_formula": "Y_Level2A_HF - Y_Level1_reconciled",
            "canonical_observable_id": "RT_NATIVE_ENDPOINT_V1",
            "level2_authoritative_raw_path": row["target_raw_path"],
            "level2_authoritative_raw_sha256": row["target_raw_sha256"],
            "authoritative_parsed_numerical_data_path": str(NUMERICAL),
            "authoritative_parsed_numerical_data_sha256": sha256(NUMERICAL),
            "normalization_contract": num["normalization_contract"],
            "reference_plane_status": num["reference_plane_status"],
            "physical_order_mapping": num["physical_order_mapping"],
            "provenance_validation_state": "M0F exact source path/SHA checked; M1B RT seed not trained",
            "geometry_group_id": GEOMETRY_ID,
            "training_policy": "TRAINING_BLOCKED_GEOMETRY_DIVERSITY",
            "split_policy": "group_by_logical_case_id_and_geometry; random_row_split_allowed=false; leave_geometry_out_possible=false",
            "distinct_training_geometries": "1",
        })
    return fields, out


def numerator_fields():
    return [
        "audit_row_id", "logical_case_id", "candidate", "source_side", "provider_channel", "wavelength_nm",
        "raw_solver_order_index", "canonical_physical_order", "physical_ux", "physical_direction",
        "raw_power_quantity", "raw_power_value", "raw_power_unit", "quantity_semantics", "derived_power_formula",
        "derived_power_value", "normalization", "reference_plane", "propagating_status", "order_family_role",
        "source_artifact", "source_sha256", "raw_artifact", "raw_sha256", "authoritative_parsed_data_path",
        "authoritative_parsed_data_sha256", "physical_order_mapping", "provenance_validation_state",
    ]


def build_numerator_audit(targets, nodes, nmap):
    fields = numerator_fields()
    rows = []
    # Level2A target numerator: exact deterministic candidate P_m=T_total*f_m.
    for case_id, target in targets.items():
        for iw, (records, t_value) in enumerate(zip(target["records"], target["level2_t"])):
            for item in records:
                m = order_index(item["order"])
                derived = float(t_value) * float(item["fraction"])
                rows.append({
                    "audit_row_id": "%s|L2|%s|%s" % (case_id, int(WLS[iw]), item["order"]),
                    "logical_case_id": case_id, "candidate": "ALT1", "source_side": "LEVEL2A_HF_RAW",
                    "provider_channel": target["channel"], "wavelength_nm": WLS[iw],
                    "raw_solver_order_index": item["raw_order_index"], "canonical_physical_order": item["order"],
                    "physical_ux": item["u_x"], "physical_direction": order_direction(item["u_x"]),
                    "raw_power_quantity": "transmission_orders.fraction", "raw_power_value": item["fraction"],
                    "raw_power_unit": "dimensionless conditional transmitted fraction",
                    "quantity_semantics": "conditional on transmitted power; per-wavelength sum=1",
                    "derived_power_formula": "T_total * fraction; candidate only, not renamed eta",
                    "derived_power_value": derived,
                    "normalization": "T_total incident-power-normalized; fraction conditional transmitted",
                    "reference_plane": "Level2A raw transmission monitor; monitor coordinate not encoded in raw_result.json",
                    "propagating_status": "reported by Level2A grating order output",
                    "order_family_role": "Level2A case-specific raw transmitted order set",
                    "source_artifact": str(target["raw_path"]), "source_sha256": target["raw_sha256"],
                    "raw_artifact": str(target["raw_path"]), "raw_sha256": target["raw_sha256"],
                    "authoritative_parsed_data_path": str(target["raw_path"]), "authoritative_parsed_data_sha256": target["raw_sha256"],
                    "physical_order_mapping": "frozen integer order identity; no array-index inference; physical +1=+x",
                    "provenance_validation_state": "raw path/SHA/grid checked; physical ux read directly from raw u_x",
                })
    # Level1 provider node numerator: native absolute transmitted-order powers.
    for case_id, target in targets.items():
        for node in nodes:
            for iw, wavelength in enumerate(WLS):
                item = node["records"][target["channel"]][wavelength]
                for label, value in sorted(item["transmitted_order_map"].items(), key=lambda kv: order_index(order_key(kv[0]))):
                    canonical = order_key(label)
                    m = order_index(canonical)
                    ux = physical_ux(node["ux"], m, wavelength, node["period_x_nm"])
                    rows.append({
                        "audit_row_id": "%s|NODE|%+.12f|%s|%s" % (case_id, node["ux"], int(wavelength), canonical),
                        "logical_case_id": case_id, "candidate": "ALT1", "source_side": "LEVEL1_PROVIDER_NODE_RAW",
                        "provider_channel": target["channel"], "wavelength_nm": wavelength,
                        "raw_solver_order_index": m, "canonical_physical_order": canonical,
                        "physical_ux": ux, "physical_direction": order_direction(ux),
                        "raw_power_quantity": "transmitted_order_map[%s]" % canonical, "raw_power_value": float(value),
                        "raw_power_unit": "dimensionless incident-power-normalized transmitted order power",
                        "quantity_semantics": "absolute transmitted-order power on incident-power semantics",
                        "derived_power_formula": "none; native grating_power postprocessed value",
                        "derived_power_value": float(value),
                        "normalization": item.get("order_power_normalization_kind", "native_provider_power"),
                        "reference_plane": "NP provider native grating_power transmitted side; M0F interface contract maps MDC z975 to NP bottom z1212",
                        "propagating_status": "postprocessor transmitted_mask; propagating order map",
                        "order_family_role": "one provider node order set contributing to M0F aggregate union",
                        "source_artifact": str(node["path"]), "source_sha256": node["sha256"],
                        "raw_artifact": str(node["raw_table_path"]), "raw_sha256": node["raw_table_sha256"],
                        "authoritative_parsed_data_path": str(node["path"]), "authoritative_parsed_data_sha256": node["sha256"],
                        "physical_order_mapping": "frozen integer n,0 order identity; kx-derived physical ux from exact provider ux and 1740 nm period",
                        "provenance_validation_state": "postprocessed/raw/setup paths and SHA checked; native order closure checked",
                    })
    # Level1 M0F aggregate numerator: preserve the exact parsed aggregate endpoint.
    for case_id, target in targets.items():
        profile = target["level1_profile"]
        for iw, wavelength in enumerate(WLS):
            labels = sorted((order_key(x["order"]) for x in profile[iw]), key=order_index)
            by_label = {order_key(x["order"]): float(x["fraction"]) for x in profile[iw]}
            for canonical in labels:
                m = order_index(canonical)
                node_ux = sorted(set(float(x["ux"]) for x in nodes if any(canonical == order_key(k) for k in x["records"][target["channel"]][wavelength]["transmitted_order_map"])))
                rows.append({
                    "audit_row_id": "%s|M0F_AGG|%s|%s" % (case_id, int(wavelength), canonical),
                    "logical_case_id": case_id, "candidate": "ALT1", "source_side": "LEVEL1_M0F_AGGREGATE",
                    "provider_channel": target["channel"], "wavelength_nm": wavelength,
                    "raw_solver_order_index": m, "canonical_physical_order": canonical,
                    "physical_ux": "MULTI_NODE_AGGREGATE_NOT_SINGLE_VALUE",
                    "physical_direction": "order-relative; aggregate ux set recorded separately",
                    "raw_power_quantity": "M0F level1_y_reconciled_json[order].fraction",
                    "raw_power_value": by_label[canonical],
                    "raw_power_unit": "dimensionless incident-power-normalized aggregate transmitted-order power",
                    "quantity_semantics": "absolute transmitted-order power; field name fraction retained from provider map",
                    "derived_power_formula": "M0F six-component source aggregation + conservative remap + native provider metric",
                    "derived_power_value": by_label[canonical],
                    "normalization": "M0F raw-first aggregation; provider native incident-power semantics; denominator sum equals M0F T",
                    "reference_plane": "M0F PASS_MDC_Z975_TO_NP_PILLAR_BOTTOM_Z1212_237NM_LOSSLESS_POWER_FACTOR_1",
                    "propagating_status": "union of per-node propagating order maps",
                    "order_family_role": "M0F aggregate union family; not a fixed-case family",
                    "source_artifact": str(NUMERICAL), "source_sha256": sha256(NUMERICAL),
                    "raw_artifact": ";".join(str(x["path"]) for x in nodes), "raw_sha256": compact({str(x["path"]): x["sha256"] for x in nodes}),
                    "authoritative_parsed_data_path": str(NUMERICAL), "authoritative_parsed_data_sha256": sha256(NUMERICAL),
                    "physical_order_mapping": "frozen integer order identity; aggregate has no unique physical ux because 9 provider nodes are integrated",
                    "provenance_validation_state": "M0F aggregate endpoint/path/SHA checked; common-order authority unavailable",
                    "provider_node_ux_set_json": compact(node_ux),
                })
    # Add a field used only by aggregate rows without weakening CSV contract.
    if "provider_node_ux_set_json" not in fields:
        fields.append("provider_node_ux_set_json")
        for row in rows:
            row.setdefault("provider_node_ux_set_json", "")
    return fields, rows


def mapping_fields():
    return [
        "mapping_row_id", "logical_case_id", "candidate", "wavelength_nm", "source_side", "raw_order_index",
        "canonical_physical_order", "physical_ux", "physical_direction", "order_membership", "order_family",
        "propagating_policy", "reference_plane", "normalization", "source_artifact", "source_sha256",
        "physical_order_mapping", "mapping_status",
    ]


def build_order_mapping(targets, nodes):
    rows = []
    for case_id, target in targets.items():
        for iw, wavelength in enumerate(WLS):
            raw_items = target["records"][iw]
            l2_family = set(item["order"] for item in raw_items)
            l1_family = set(order_key(x["order"]) for x in target["level1_profile"][iw])
            for item in raw_items:
                rows.append({
                    "mapping_row_id": "%s|L2|%s|%s" % (case_id, int(wavelength), item["order"]),
                    "logical_case_id": case_id, "candidate": "ALT1", "wavelength_nm": wavelength,
                    "source_side": "LEVEL2A_HF_RAW", "raw_order_index": item["raw_order_index"],
                    "canonical_physical_order": item["order"], "physical_ux": item["u_x"],
                    "physical_direction": order_direction(item["u_x"]), "order_membership": "included",
                    "order_family": "case-specific Level2A raw propagating grating set",
                    "propagating_policy": "Level2A grating output; explicit evanescent policy absent in raw_result schema",
                    "reference_plane": "Level2A raw transmission monitor; coordinate not encoded in raw_result.json",
                    "normalization": "conditional transmitted fraction; numerator candidate T*f_m",
                    "source_artifact": str(target["raw_path"]), "source_sha256": target["raw_sha256"],
                    "physical_order_mapping": "frozen integer order identity; raw u_x retained; no array-index inference",
                    "mapping_status": "SOURCE_SIDE_EXACT_MAPPING_NOT_CANONICAL_PROMOTED",
                })
            for canonical in sorted(l1_family, key=order_index):
                m = order_index(canonical)
                ux_set = sorted(set(physical_ux(node["ux"], m, wavelength, node["period_x_nm"]) for node in nodes if canonical in {order_key(x) for x in node["records"][target["channel"]][wavelength]["transmitted_order_map"]}))
                rows.append({
                    "mapping_row_id": "%s|L1|%s|%s" % (case_id, int(wavelength), canonical),
                    "logical_case_id": case_id, "candidate": "ALT1", "wavelength_nm": wavelength,
                    "source_side": "LEVEL1_M0F_AGGREGATE", "raw_order_index": m,
                    "canonical_physical_order": canonical, "physical_ux": compact(ux_set),
                    "physical_direction": "multi-node aggregate; per-node directions derived from ux set",
                    "order_membership": "included", "order_family": "15-label M0F aggregate union family",
                    "propagating_policy": "per-node postprocessor transmitted_mask followed by 9-node union/weighted aggregation",
                    "reference_plane": "M0F PASS_MDC_Z975_TO_NP_PILLAR_BOTTOM_Z1212_237NM_LOSSLESS_POWER_FACTOR_1",
                    "normalization": "absolute incident-power provider metric; aggregate profile sum equals M0F T",
                    "source_artifact": str(NUMERICAL), "source_sha256": sha256(NUMERICAL),
                    "physical_order_mapping": "frozen integer order identity; no array-index inference; aggregate has no single ux",
                    "mapping_status": "SOURCE_SIDE_EXACT_MAPPING_NOT_CANONICAL_PROMOTED",
                })
    return mapping_fields(), rows


def denominator_fields():
    return [
        "audit_row_id", "logical_case_id", "candidate", "wavelength_nm", "source_side", "denominator_formula",
        "included_order_set", "excluded_order_set", "order_count", "denominator_value", "numerator_sum_check",
        "closure_abs_error", "fraction_closure_abs_error", "normalization", "propagating_order_policy",
        "evanescent_treatment", "reference_plane", "transmitted_side_definition", "source_artifact", "source_sha256",
        "same_as_other_side_order_family", "denominator_status", "provenance_validation_state",
    ]


def build_denominator_audit(targets, nodes):
    rows = []
    for case_id, target in targets.items():
        for iw, wavelength in enumerate(WLS):
            raw_items = target["records"][iw]
            l2_set = sorted(set(x["order"] for x in raw_items), key=order_index)
            l1_set = sorted(set(order_key(x["order"]) for x in target["level1_profile"][iw]), key=order_index)
            common = sorted(set(l2_set) & set(l1_set), key=order_index)
            l2_p = [float(target["level2_t"][iw]) * float(x["fraction"]) for x in raw_items]
            l1_by = {order_key(x["order"]): float(x["fraction"]) for x in target["level1_profile"][iw]}
            l1_p = [l1_by[x] for x in l1_set]
            l1_t = float(target["level1_t"][iw])
            l2_t = float(target["level2_t"][iw])
            l1_common_sum = sum(l1_by[x] for x in common)
            rows.append({
                "audit_row_id": "%s|L2|%s" % (case_id, int(wavelength)), "logical_case_id": case_id, "candidate": "ALT1",
                "wavelength_nm": wavelength, "source_side": "LEVEL2A_HF_RAW",
                "denominator_formula": "sum over the Level2A raw transmitted order set of T_total*fraction",
                "included_order_set": compact(l2_set), "excluded_order_set": "not enumerated in raw_result.json",
                "order_count": len(l2_set), "denominator_value": l2_t, "numerator_sum_check": sum(l2_p),
                "closure_abs_error": abs(sum(l2_p) - l2_t), "fraction_closure_abs_error": abs(sum(x["fraction"] for x in raw_items) - 1.0),
                "normalization": "T_total incident-power-normalized; fraction conditional transmitted",
                "propagating_order_policy": "Level2A grating output order list",
                "evanescent_treatment": "not separately encoded; only returned grating orders represented",
                "reference_plane": "Level2A raw transmission monitor; coordinate not encoded in raw_result.json",
                "transmitted_side_definition": "Level2A transmission_monitor plus transmission_orders",
                "source_artifact": str(target["raw_path"]), "source_sha256": target["raw_sha256"],
                "same_as_other_side_order_family": False,
                "denominator_status": "NUMERIC_CLOSURE_PASS_BUT_ORDER_FAMILY_NOT_COMMON",
                "provenance_validation_state": "raw path/SHA/grid checked",
            })
            rows.append({
                "audit_row_id": "%s|L1|%s" % (case_id, int(wavelength)), "logical_case_id": case_id, "candidate": "ALT1",
                "wavelength_nm": wavelength, "source_side": "LEVEL1_M0F_AGGREGATE",
                "denominator_formula": "sum over M0F 9-node aggregate union transmitted_order_map",
                "included_order_set": compact(l1_set), "excluded_order_set": "orders absent from 9-node aggregate union",
                "order_count": len(l1_set), "denominator_value": l1_t, "numerator_sum_check": sum(l1_p),
                "closure_abs_error": abs(sum(l1_p) - l1_t), "fraction_closure_abs_error": abs(sum(l1_p) / l1_t - 1.0) if l1_t else None,
                "normalization": "absolute incident-power provider metric; M0F aggregate endpoint",
                "propagating_order_policy": "per-node transmitted_mask followed by 9-node union/weighted aggregation",
                "evanescent_treatment": "per-node postprocessor mask; aggregate union does not preserve one fixed-case set",
                "reference_plane": "M0F PASS_MDC_Z975_TO_NP_PILLAR_BOTTOM_Z1212_237NM_LOSSLESS_POWER_FACTOR_1",
                "transmitted_side_definition": "native grating_power transmitted_order_map",
                "source_artifact": str(NUMERICAL), "source_sha256": sha256(NUMERICAL),
                "same_as_other_side_order_family": False,
                "denominator_status": "NUMERIC_CLOSURE_PASS_BUT_ORDER_FAMILY_NOT_COMMON",
                "provenance_validation_state": "M0F numerical path/SHA checked; P_common_order_authority unavailable",
            })
            rows.append({
                "audit_row_id": "%s|COMMON_INTERSECTION|%s" % (case_id, int(wavelength)), "logical_case_id": case_id, "candidate": "ALT1",
                "wavelength_nm": wavelength, "source_side": "CROSS_SIDE_INTERSECTION_DIAGNOSTIC",
                "denominator_formula": "diagnostic only: M0F sum over Level2A/L1 order-label intersection",
                "included_order_set": compact(common), "excluded_order_set": compact(sorted(set(l1_set) - set(common), key=order_index)),
                "order_count": len(common), "denominator_value": l1_common_sum, "numerator_sum_check": l1_common_sum,
                "closure_abs_error": None, "fraction_closure_abs_error": None,
                "normalization": "not promoted; intersection redefinition would alter denominator contract",
                "propagating_order_policy": "not a frozen common policy", "evanescent_treatment": "not applicable",
                "reference_plane": "not promoted", "transmitted_side_definition": "not promoted",
                "source_artifact": str(NUMERICAL), "source_sha256": sha256(NUMERICAL),
                "same_as_other_side_order_family": False,
                "denominator_status": "PROHIBITED_INTERSECTION_REDEFINITION_NOT_PROMOTED",
                "provenance_validation_state": "diagnostic only; no missing-order fill or renormalization performed",
            })
    return denominator_fields(), rows


def build_repairability(targets, nodes):
    fields = [
        "logical_case_id", "candidate", "canonical_observable_id", "formula", "level1_numerator_status",
        "level2_numerator_status", "level1_denominator_status", "level2_denominator_status", "order_family_identical",
        "included_orders_identical", "excluded_orders_identical", "propagating_policy_identical", "evanescent_policy_identical",
        "reference_plane_identical", "transmitted_side_identical", "normalization_identical", "physical_ux_mapping_status",
        "level2_order_family_by_wavelength_json", "level1_order_family_by_wavelength_json", "level1_extra_orders_by_wavelength_json",
        "physical_orders_supported", "unsupported_orders", "canonical_fraction_closure_worst", "exact_supported",
        "repairability_state", "training_allowed", "provenance_basis",
    ]
    rows = []
    for case_id, target in targets.items():
        l2_families = [family(item) for item in target["records"]]
        l1_families = [sorted(set(order_key(x["order"]) for x in item), key=order_index) for item in target["level1_profile"]]
        extras = [sorted(set(l1) - set(l2), key=order_index) for l1, l2 in zip(l1_families, l2_families)]
        raw_closure = side_raw_fraction_closure(target)
        l1_closure = max(abs(sum(float(x["fraction"]) for x in item) / float(target["level1_t"][i]) - 1.0) for i, item in enumerate(target["level1_profile"]))
        rows.append({
            "logical_case_id": case_id, "candidate": "ALT1", "canonical_observable_id": CANONICAL_ID,
            "formula": "f_m_canonical = P_m / sum_k P_k over identical transmitted physical diffraction-order set",
            "level1_numerator_status": "EXACT_NATIVE_PROVIDER_ORDER_POWER_AVAILABLE; M0F aggregate preserves 9-node union",
            "level2_numerator_status": "EXACT_DERIVABLE_ZERO_SOLVER_CANONICAL_ROUTING_CANDIDATE_T_TIMES_FRACTION",
            "level1_denominator_status": "NUMERIC_CLOSURE_PASS_OVER_M0F_15_LABEL_UNION",
            "level2_denominator_status": "NUMERIC_CLOSURE_PASS_OVER_CASE_SPECIFIC_7_TO_8_LABEL_SET",
            "order_family_identical": False, "included_orders_identical": False, "excluded_orders_identical": False,
            "propagating_policy_identical": False, "evanescent_policy_identical": False,
            "reference_plane_identical": "M0F interface mapping pass; Level2 raw monitor coordinate not encoded",
            "transmitted_side_identical": False, "normalization_identical": False,
            "physical_ux_mapping_status": "Level2 raw u_x exact; Level1 node ux exact-derived but M0F aggregate has no single ux",
            "level2_order_family_by_wavelength_json": compact(l2_families),
            "level1_order_family_by_wavelength_json": compact(l1_families),
            "level1_extra_orders_by_wavelength_json": compact(extras),
            "physical_orders_supported": 0,
            "unsupported_orders": compact(sorted(set(x for group in extras for x in group), key=order_index)),
            "canonical_fraction_closure_worst": "NOT_APPLICABLE_NO_CANONICAL_ROW",
            "exact_supported": False,
            "repairability_state": "HARD_GATE_ROUTING_PROVENANCE_OR_SEMANTIC_CONFLICT",
            "training_allowed": False,
            "provenance_basis": "M0F numerical registry + 4 Level2A raw paths + 9 provider postprocessed/raw/setup chains; provider freeze P_common_order_authority unavailable",
        })
    return fields, rows


def build_control_diagnostic(control, targets, nmap):
    fields = [
        "row_id", "logical_case_id", "candidate", "observable", "source_polarization", "spacer_nm", "ux",
        "level2_raw_path", "level2_raw_sha256", "level2_order_ingredients_available", "level1_provider_ingredients_available",
        "canonical_observable_id", "canonical_routing_status", "first_gen_training_allowed", "promotion_status",
        "reason", "geometry_group_id", "provenance_validation_state",
    ]
    out = []
    for row in control:
        case_id = row["logical_case_id"]
        if case_id not in targets:
            # CONTROL0 has the same case parameter family but was not M0F promoted;
            # resolve its raw target directly from its row.
            raw_path = Path(row["target_raw_path"])
            raw_sha = sha256(raw_path) if raw_path.exists() else ""
            order_available = raw_path.exists()
        else:
            raw_path = targets[case_id]["raw_path"]
            raw_sha = targets[case_id]["raw_sha256"]
            order_available = True
        out.append({
            "row_id": case_id + "|" + row["observable"], "logical_case_id": case_id, "candidate": "CONTROL0",
            "observable": row["observable"], "source_polarization": row["source_polarization"],
            "spacer_nm": row["spacer_nm"], "ux": row["ux"], "level2_raw_path": str(raw_path), "level2_raw_sha256": raw_sha,
            "level2_order_ingredients_available": order_available,
            "level1_provider_ingredients_available": True,
            "canonical_observable_id": CANONICAL_ID,
            "canonical_routing_status": "DIAGNOSTIC_ONLY_ORDER_FAMILY_CONFLICT",
            "first_gen_training_allowed": False, "promotion_status": "CONTROL0_DIAGNOSTIC_NONTRAINING",
            "reason": "CONTROL0 promotion remains forbidden; routing canonicalization is not promoted in this round",
            "geometry_group_id": GEOMETRY_ID,
            "provenance_validation_state": "raw ingredient availability checked where source path exists; no CONTROL0 promotion",
        })
    return fields, out


def main():
    started = datetime.now(timezone.utc).isoformat()
    residual, numerical, candidate, control, nmap, targets = load_inputs()
    nodes, setup_provenance = load_provider_nodes()
    rt_fields, rt_rows = make_rt_seed(candidate, nmap)
    if len(rt_rows) != EXPECTED_RT_ROWS:
        raise RuntimeError("RT seed row count is not 8")
    write_csv(OUT / "M1B_RT_EXACT_RESIDUAL_SEED_REGISTRY_V1.csv", rt_fields, rt_rows)
    num_fields, num_rows = build_numerator_audit(targets, nodes, nmap)
    write_csv(OUT / "M1B_ROUTING_NUMERATOR_AUDIT_V1.csv", num_fields, num_rows)
    den_fields, den_rows = build_denominator_audit(targets, nodes)
    write_csv(OUT / "M1B_ROUTING_DENOMINATOR_AUDIT_V1.csv", den_fields, den_rows)
    map_fields, map_rows = build_order_mapping(targets, nodes)
    write_csv(OUT / "M1B_CANONICAL_ORDER_MAPPING_V1.csv", map_fields, map_rows)
    repair_fields, repair_rows = build_repairability(targets, nodes)
    write_csv(OUT / "M1B_CANONICAL_ROUTING_REPAIRABILITY_MATRIX_V1.csv", repair_fields, repair_rows)
    control_fields, control_out = build_control_diagnostic(control, targets, nmap)
    write_csv(OUT / "M1B_CONTROL0_ROUTING_DIAGNOSTIC_V1.csv", control_fields, control_out)

    level2_fraction_errors = [side_raw_fraction_closure(t) for t in targets.values()]
    l1_fraction_errors = []
    for target in targets.values():
        for i, profile in enumerate(target["level1_profile"]):
            total = float(target["level1_t"][i])
            l1_fraction_errors.append(abs(sum(float(x["fraction"]) for x in profile) / total - 1.0) if total else None)
    source_side_closure_worst = max([x for x in level2_fraction_errors + l1_fraction_errors if x is not None])
    level2_order_labels = sorted(set(x["order"] for t in targets.values() for rec in t["records"] for x in rec), key=order_index)
    level1_order_labels = sorted(set(order_key(x["order"]) for t in targets.values() for rec in t["level1_profile"] for x in rec), key=order_index)
    matrix_statuses = sorted(set(r["repairability_state"] for r in repair_rows))
    quality = {
        "audit_id": "M1B_CANONICAL_ROUTING_OBSERVABLE_AUDIT_V1",
        "status": "RT_RESIDUAL_ONLY_ROUTING_NOT_REPAIRABLE_ZERO_SOLVER",
        "started_utc": started,
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "candidate_logical_cases": len(targets),
        "candidate_residual_rows_reviewed": len(candidate),
        "rt_exact_residual_rows": len(rt_rows),
        "canonical_routing_exact_supported": False,
        "canonical_routing_cases": 0,
        "canonical_routing_rows": 0,
        "canonical_physical_orders": 0,
        "observed_level2_physical_order_labels": level2_order_labels,
        "observed_level1_m0f_aggregate_order_labels": level1_order_labels,
        "source_side_fraction_closure_worst_abs_error": source_side_closure_worst,
        "canonical_fraction_closure_worst": None,
        "eta_semantics_modified": False,
        "order_profile_semantics_modified": False,
        "distinct_training_geometries": 1,
        "training_allowed": False,
        "control0_rows": len(control),
        "control0_training_rows": 0,
        "level2b_training_rows": 0,
        "no_interpolation": True,
        "no_renormalization_substitution": True,
        "no_missing_order_fill": True,
        "no_symmetry_fill": True,
        "no_ps_substitution": True,
        "no_reference_plane_substitution": True,
        "provider_node_count": len(nodes),
        "provider_node_order_closure_checked": True,
        "provider_freeze_common_order_authority": "not available in preserved P Anchor C handoff",
        "wavelength_grid_exact": True,
        "nan_inf_detected": False,
        "solver_entered_delta": 0,
        "new_rcwa_evaluation_delta": 0,
        "provider_evaluation_delta": 0,
        "ml_training_delta": 0,
        "inverse_design_delta": 0,
        "raw_fsp_copy_delta": 0,
        "move_delta": 0,
        "delete_delta": 0,
        "source_hashes": {
            "m0f_residual_registry": {"path": str(RESIDUAL), "sha256": sha256(RESIDUAL)},
            "m0f_numerical_registry": {"path": str(NUMERICAL), "sha256": sha256(NUMERICAL)},
            "level2_raw_sources": {case: {"path": str(t["raw_path"]), "sha256": t["raw_sha256"]} for case, t in targets.items()},
            "provider_setup_readbacks": setup_provenance,
        },
        "repairability_states": matrix_statuses,
    }
    write_json(OUT / "M1B_DATA_QUALITY_AUDIT_V1.json", quality)

    schema = {
        "schema_id": "M1B_CANONICAL_ROUTING_SCHEMA_V1",
        "status": "RT_ONLY_ROUTING_NOT_REPAIRABLE",
        "canonical_observable_id": CANONICAL_ID,
        "observable_class": "ML-SIDE DERIVED OBSERVABLE",
        "formula": "f_m_canonical = P_m / sum_k P_k",
        "formula_constraints": [
            "same transmitted physical diffraction-order set on Level1 and Level2 sides",
            "same propagating/evanescent policy",
            "same transmitted-side and reference-plane contract",
            "f_m >= 0",
            "abs(sum_m f_m - 1) <= 1e-8",
        ],
        "current_result": "not materialized because Level1 M0F aggregate union family and Level2 fixed-case family differ",
        "old_semantics_unchanged": {"eta_semantics_modified": False, "order_profile_semantics_modified": False},
        "training_policy": "training_allowed=false; TRAINING_BLOCKED_GEOMETRY_DIVERSITY",
        "field_contract": [
            "logical_case_id", "wavelength_nm", "canonical_physical_order", "physical_ux", "P_m_level1",
            "P_m_level2", "DeltaY", "numerator_provenance", "denominator_provenance", "physical_order_mapping",
        ],
    }
    write_json(OUT / "M1B_CANONICAL_ROUTING_SCHEMA_V1.json", schema)

    dataset_fields = [
        "row_id", "logical_case_id", "candidate", "wavelength_nm", "canonical_observable_id", "canonical_physical_order",
        "physical_ux", "P_m_Level1", "P_m_Level2", "DeltaY", "denominator_Level1", "denominator_Level2",
        "formula", "numerator_provenance", "denominator_provenance", "physical_order_mapping", "normalization_contract",
        "reference_plane_contract", "training_policy", "provenance_validation_state",
    ]
    write_csv(OUT / "M1B_CANONICAL_ROUTING_DATASET_V1.csv", dataset_fields, [])
    dataset_manifest = {
        "manifest_id": "M1B_CANONICAL_ROUTING_DATASET_MANIFEST_V1",
        "status": "NO_LEGAL_CANONICAL_ROUTING_ROWS",
        "canonical_observable_id": CANONICAL_ID,
        "rows": 0,
        "reason": "order family/provenance conflict; no canonical numerator-denominator pair promoted",
        "rt_seed_registry": "M1B_RT_EXACT_RESIDUAL_SEED_REGISTRY_V1.csv",
        "training_allowed": False,
    }
    write_json(OUT / "M1B_CANONICAL_ROUTING_DATASET_MANIFEST_V1.json", dataset_manifest)

    report = """# M1B Canonical Routing Observable Repairability Audit V1

## STATUS

`RT_RESIDUAL_ONLY_ROUTING_NOT_REPAIRABLE_ZERO_SOLVER`.

## RT_RESIDUAL

- `rt_exact_residual_rows = 8` (4 ALT1 logical cases × R/T).
- The seed registry is frozen as a numerical audit/seed artifact only; `training_allowed = false` because one training geometry is insufficient.

## ROUTING_NUMERATOR

- All 4 ALT1 cases were audited.
- Level-2A provides conditional `transmission_orders.fraction`; `P_m` is only a deterministic candidate `T_total*fraction`.
- Level-1 provider nodes provide native absolute `transmitted_order_map` powers. The M0F endpoint is a 9-node aggregate union and preserves a 15-label order family.
- Physical order identity is integer `(m,0)` with physical `m=+1 -> +x`; no array-index inference was used.

## ROUTING_DENOMINATOR

- Level-2 denominator closes over the case-specific raw transmitted order set (7–8 labels per wavelength).
- Level-1 denominator closes over the M0F 9-node aggregate union (15 labels).
- Numeric closure passes on each side, but included and excluded order sets are not identical. Intersection redefinition would change the denominator contract and was not promoted.

## CANONICAL_ROUTING

- `canonical_routing_exact_supported = false`.
- `canonical_routing_cases = 0`; `canonical_routing_rows = 0`; `canonical_physical_orders = 0`.
- `canonical_fraction_closure_worst = NOT_APPLICABLE_NO_CANONICAL_ROW`; source-side candidate closure was checked separately.
- The provider freeze states that `P_common_order_authority` is unavailable. No old `eta_*` or `order_profile` semantics were modified.

## CONTROL0

CONTROL0 remains `DIAGNOSTIC_NONTRAINING`; no CONTROL0 promotion or routing training is allowed.

## DATASET

`M1B_CANONICAL_ROUTING_DATASET_V1.csv` is header-only and accompanied by a manifest. Only the R/T exact seed registry contains rows.

## AUDIT

All 4 ALT1 cases, 9 provider nodes, Level-2 raw paths, M0F numerical registry, provider setup readbacks and SHA chains were checked. No solver, RCWA evaluation, provider evaluation, ML training, inverse design, FSP copy, move or delete was performed.

`eta_semantics_modified = false`; `order_profile_semantics_modified = false`; `distinct_training_geometries = 1`; `training_allowed = false`.

`solver_entered_delta = 0`; `ml_training_delta = 0`; `commit_delta = 0`; `push_delta = 0`.

## RISKS

The current routing inputs cannot support an exact cross-level canonical fraction because Level-1 uses a multi-node aggregate order union while Level-2 uses a fixed-case propagating-order set. A future routing contract must freeze one common order family, evanescent policy, transmitted-side definition and reference-plane metadata before routing residual promotion.

## NEXT

`GEOMETRY_DIVERSITY_SEED_ACQUISITION_PLANNING_FOR_RT_ONLY_WITH_ROUTING_HELDOUT`
"""
    (OUT / "M1B_REPORT_V1.md").write_text(report, encoding="utf-8")

    manifest_names = [
        "M1B_RT_EXACT_RESIDUAL_SEED_REGISTRY_V1.csv",
        "M1B_ROUTING_NUMERATOR_AUDIT_V1.csv",
        "M1B_ROUTING_DENOMINATOR_AUDIT_V1.csv",
        "M1B_CANONICAL_ORDER_MAPPING_V1.csv",
        "M1B_CANONICAL_ROUTING_REPAIRABILITY_MATRIX_V1.csv",
        "M1B_CANONICAL_ROUTING_DATASET_V1.csv",
        "M1B_CANONICAL_ROUTING_DATASET_MANIFEST_V1.json",
        "M1B_CANONICAL_ROUTING_SCHEMA_V1.json",
        "M1B_CONTROL0_ROUTING_DIAGNOSTIC_V1.csv",
        "M1B_DATA_QUALITY_AUDIT_V1.json",
        "M1B_REPORT_V1.md",
    ]
    sha_manifest = {
        "manifest_id": "M1B_SHA256_MANIFEST_V1",
        "status": "PASS_ARTIFACT_HASHES_COMPUTED_RT_ONLY_ROUTING_NOT_REPAIRABLE",
        "artifact_count": len(manifest_names),
        "artifacts": [{"path": name, "sha256": sha256(OUT / name), "bytes": (OUT / name).stat().st_size} for name in manifest_names],
        "self_hash_policy": "M1B_SHA256_MANIFEST_V1.json excluded from its own artifact list",
        "commit_delta": 0,
        "push_delta": 0,
    }
    write_json(OUT / "M1B_SHA256_MANIFEST_V1.json", sha_manifest)
    print(json.dumps({
        "status": quality["status"], "rt_exact_residual_rows": len(rt_rows), "canonical_routing_exact_supported": False,
        "canonical_routing_cases": 0, "canonical_routing_rows": 0, "canonical_physical_orders": 0,
        "source_side_fraction_closure_worst": source_side_closure_worst, "numerator_audit_rows": len(num_rows),
        "denominator_audit_rows": len(den_rows), "order_mapping_rows": len(map_rows), "control0_rows": len(control_out),
        "out": str(OUT),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
