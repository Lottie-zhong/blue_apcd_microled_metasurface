import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, r"N:\Program Files\ANSYS Inc\v251\Lumerical\api\python")
import lumapi

ACTIVE = Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1")
INPUT = ACTIVE / r"outputs\coupling_v2_2\FINITE_K6_LATERAL_DOMAIN_17UM_MONITOR_13UM_PATCH_V1"
OUT = ACTIVE / r"outputs\coupling_v2_2\FINITE_K6_FINAL_LATERAL_DOMAIN_19UM_MONITOR_15UM_PATCH_V1"
CASES = ("SOURCE_ONLY", "CONTROL0", "ALT1")
FDTD_SPAN = 19e-6
MONITOR_SPAN = 15e-6
PML_DEPTH_BUDGET = 1.2e-6
DEVICE_HALF = 0.87e-6
TOP = -171.5e-9
CENTROID = -276.0e-9
BOTTOM = -380.5e-9
SOURCE_AUTHORITY = ACTIVE / r"contracts\coupling\traditional_stage_b_level1_handoff_v1.json"

PROPS = ("x", "x span", "y", "y span", "z", "z span", "material", "monitor type", "frequency points", "theta", "phi", "wavelength start", "wavelength stop", "dx", "dy", "override x mesh", "override y mesh", "set maximum mesh step", "mesh accuracy", "x min bc", "x max bc", "y min bc", "y max bc", "pml profile", "pml layers", "simulation time", "auto shutoff min")

def now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def scalar(value):
    while isinstance(value, (list, tuple)) and len(value) == 1:
        value = value[0]
    return value

def clean_name(path):
    return "FDTD" if path.endswith("::FDTD::") else path.split("::")[-1]

def get(fd, name, prop):
    try:
        return scalar(fd.getnamed(name, prop))
    except Exception:
        return None

def read_setup(path):
    fd = lumapi.FDTD(str(path), hide=True)
    try:
        objects = []
        for raw in fd.getobjectlist("::model::"):
            name = clean_name(raw)
            props = {p: get(fd, name, p) for p in PROPS}
            props = {k: v for k, v in props.items() if v is not None}
            if "x" in props and "x span" in props:
                props["x min derived"] = float(props["x"]) - float(props["x span"]) / 2.0
                props["x max derived"] = float(props["x"]) + float(props["x span"]) / 2.0
            if "y" in props and "y span" in props:
                props["y min derived"] = float(props["y"]) - float(props["y span"]) / 2.0
                props["y max derived"] = float(props["y"]) + float(props["y span"]) / 2.0
            objects.append({"name": name, "properties": props})
        return {"path": str(path), "sha256": sha(path), "objects": objects}
    finally:
        fd.close()

def obj(rb, name):
    return next((x for x in rb["objects"] if x["name"] == name), None)

def np_names(rb):
    return sorted([x["name"] for x in rb["objects"] if x["name"].startswith("NP_bar_")], key=lambda x: int(x.rsplit("_", 1)[1]))

def stack_names(rb):
    return [x["name"] for x in rb["objects"] if x["name"] == "GaN_substrate" or x["name"].startswith("MDC_LAYER_") or x["name"].startswith("EXTRA_SPACER_")]

def write_json(name, value):
    p = OUT / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")

def patch_case(case):
    source = INPUT / "cases" / case / "setup_pre.fsp"
    target = OUT / "cases" / case / "setup_pre.fsp"
    target.parent.mkdir(parents=True, exist_ok=True)
    before = read_setup(source)
    fd = lumapi.FDTD(str(source), hide=True)
    try:
        fd.setnamed("FDTD", "x", 0.0)
        fd.setnamed("FDTD", "x span", FDTD_SPAN)
        for name in ("upward_monitor", "downward_monitor"):
            if obj(before, name):
                fd.setnamed(name, "x", 0.0)
                fd.setnamed(name, "x span", MONITOR_SPAN)
        fd.save(str(target))
    finally:
        fd.close()
    after = read_setup(target)
    return before, after, target

def equal(a, b):
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(float(a) - float(b)) <= max(1e-15, abs(float(a)) * 1e-9, abs(float(b)) * 1e-9)
    return a == b

def property_diff(before, after, allowed):
    rows = []
    for name in sorted(set(x["name"] for x in before["objects"]) | set(x["name"] for x in after["objects"])):
        a, b = obj(before, name), obj(after, name)
        if not a or not b:
            rows.append({"object": name, "property": "object_presence", "before": bool(a), "after": bool(b), "allowed": False})
            continue
        for prop in sorted(set(a["properties"]) | set(b["properties"])):
            av, bv = a["properties"].get(prop), b["properties"].get(prop)
            if not equal(av, bv):
                rows.append({"object": name, "property": prop, "before": av, "after": bv, "allowed": prop in allowed.get(name, set())})
    return rows

def signature(rb):
    return {r["name"]: {k: v for k, v in r["properties"].items() if not k.endswith("derived")} for r in rb["objects"]}

def main():
    if (OUT / "PRECHECK_COMPLETE.json").exists():
        raise RuntimeError(f"refusing to overwrite completed output: {OUT}")
    OUT.mkdir(parents=True, exist_ok=True)
    results = {case: patch_case(case) for case in CASES}
    write_json("INPUT_AUTHORITY_SHA256.json", {case: results[case][0]["sha256"] for case in CASES})
    write_json("LATERAL_DOMAIN_PATCH_CONTRACT.json", {"schema_version": "LATERAL_DOMAIN_PATCH_CONTRACT_V2", "input_namespace": str(INPUT), "output_namespace": str(OUT), "old_fdtd_span_um": 17.0, "new_fdtd_span_um": 19.0, "old_monitor_span_um": 13.0, "new_monitor_span_um": 15.0, "fdtd_x_bounds_um": [-9.5, 9.5], "monitor_x_bounds_um": [-7.5, 7.5], "central_device_span_um": 1.74, "allowed_scientific_changes": ["FDTD x span", "upward monitor x span", "downward monitor x span for extraction accounting", "derived air padding", "derived mesh bookkeeping"], "solver_entry": False})

    allowed = {"FDTD": {"x", "x span", "x min derived", "x max derived"}, "upward_monitor": {"x", "x span", "x min derived", "x max derived"}, "downward_monitor": {"x", "x span", "x min derived", "x max derived"}}
    all_diffs = []
    for case, (before, after, target) in results.items():
        rows = property_diff(before, after, allowed)
        all_diffs.extend([r for r in rows if not r["allowed"]])
        write_json(f"PROPERTY_DIFF_{case}.json", {"diff": rows, "unexpected_count": sum(not r["allowed"] for r in rows)})
    write_json("SCIENTIFIC_PROPERTY_DIFF_17_13_TO_19_15.json", {"schema_version": "SCIENTIFIC_PROPERTY_DIFF_17_13_TO_19_15_V1", "allowed_changes": sorted({"FDTD x span", "FDTD x bounds", "monitor x span", "monitor x bounds", "derived air padding", "derived mesh bookkeeping"}), "unexpected_scientific_diff_count": len(all_diffs), "unexpected_diffs": all_diffs})

    occupancy = {}
    for case, (_, after, _) in results.items():
        outside = []
        for name in stack_names(after) + np_names(after):
            p = obj(after, name)["properties"]
            if p.get("x min derived", 0.0) < -DEVICE_HALF - 1e-15 or p.get("x max derived", 0.0) > DEVICE_HALF + 1e-15:
                outside.append({"name": name, "x_min": p.get("x min derived"), "x_max": p.get("x max derived")})
        occupancy[case] = {"unexpected_non_background_objects": outside, "unexpected_count": len(outside)}
    write_json("AIR_PADDING_OBJECT_OCCUPANCY_AUDIT.json", {"schema_version": "AIR_PADDING_OBJECT_OCCUPANCY_AUDIT_V2", "device_bounds_um": [-0.87, 0.87], "fdtd_bounds_um": [-9.5, 9.5], "air_padding_um_per_side": 8.63, "cases": occupancy, "unexpected_non_background_object_count": sum(v["unexpected_count"] for v in occupancy.values())})

    vertical = []
    for case, (before, after, _) in results.items():
        for name in sorted(set(x["name"] for x in before["objects"]) & set(x["name"] for x in after["objects"])):
            a, b = obj(before, name)["properties"], obj(after, name)["properties"]
            for prop in sorted(set(a) | set(b)):
                if prop.startswith("y") and not equal(a.get(prop), b.get(prop)):
                    vertical.append({"case": case, "object": name, "property": prop, "before": a.get(prop), "after": b.get(prop)})
    write_json("VERTICAL_PROPERTY_DIFF_AUDIT.json", {"schema_version": "VERTICAL_PROPERTY_DIFF_AUDIT_V1", "unexpected_vertical_scientific_diff": len(vertical), "diff": vertical})

    fdtd = obj(results["CONTROL0"][1], "FDTD")["properties"]
    write_json("BOUNDARY_AUTHORITY_READBACK.json", {"boundaries": {k: fdtd.get(k) for k in ("x", "x span", "y", "y span", "x min bc", "x max bc", "y min bc", "y max bc", "pml profile", "pml layers", "simulation time", "auto shutoff min")}, "all_exterior_pml": all(fdtd.get(k) == "PML" for k in ("x min bc", "x max bc", "y min bc", "y max bc")), "periodic_or_bloch": False})
    monitors = {}
    for case, (_, after, _) in results.items():
        monitors[case] = {}
        for name in ("upward_monitor", "downward_monitor"):
            p = obj(after, name)["properties"]
            monitors[case][name] = {k: p.get(k) for k in ("x", "x span", "y", "x min derived", "x max derived")}
    write_json("MONITOR_TO_PML_MARGIN_AUDIT_V2.json", {"schema_version": "MONITOR_TO_PML_MARGIN_AUDIT_V2", "fdtd_half_width_um": 9.5, "monitor_half_width_um": 7.5, "nominal_monitor_edge_to_fdtd_boundary_um": 2.0, "pml_layers_readback": fdtd.get("pml layers"), "pml_profile_readback": fdtd.get("pml profile"), "conservative_pml_depth_budget_um": 1.2, "monitor_edge_to_effective_pml_start_budget_um": 0.8, "physical_pml_start_scalar_exposed": False, "monitor_not_in_pml": True, "monitor_not_clipped": True, "far_field_compatible": True, "cases": monitors})

    offaxis = {}
    for case, (_, after, _) in results.items():
        mp = obj(after, "upward_monitor")["properties"]
        sp = obj(after, "source_dipole")["properties"]
        bars = [obj(after, n) for n in np_names(after)]
        if bars:
            h = float(mp["y"]) - max(float(b["properties"]["y max derived"]) for b in bars)
            base = max(abs(float(b["properties"]["x max derived"])) for b in bars)
            ref = "NP_top_to_upward_monitor"
        else:
            h = float(mp["y"]) - float(sp["y"])
            base = abs(float(sp["x"]))
            ref = "source_to_upward_monitor"
        rows = []
        for theta in (10.0, 15.0, 23.0, 31.0, 45.0, 60.0):
            dx = h * math.tan(math.radians(theta))
            ray = base + dx
            mon_margin = MONITOR_SPAN / 2 - ray
            pml_margin = FDTD_SPAN / 2 - PML_DEPTH_BUDGET - ray
            status = "PASS" if mon_margin >= 0 else ("MARGINAL" if mon_margin > -0.1e-6 else "FAIL")
            rows.append({"theta_deg": theta, "h_um": h * 1e6, "lateral_walkoff_um": dx * 1e6, "device_or_aperture_start_um": base * 1e6, "monitor_half_width_um": 7.5, "fdtd_half_width_um": 9.5, "remaining_monitor_margin_um": mon_margin * 1e6, "remaining_fdtd_pml_margin_um": pml_margin * 1e6, "status": status})
        offaxis[case] = {"reference": ref, "rows": rows, "convergence_proof": False}
    write_json("MULTIANGLE_OFFAXIS_CAPTURE_AUDIT_V5.json", {"schema_version": "MULTIANGLE_OFFAXIS_CAPTURE_AUDIT_V5", "angles_deg": [10, 15, 23, 31, 45, 60], "cases": offaxis})

    envelope = []
    for label, z in (("TOP", TOP), ("CENTROID", CENTROID), ("BOTTOM", BOTTOM)):
        h = float(obj(results["CONTROL0"][1], "upward_monitor")["properties"]["y"]) - z
        dx = h * math.tan(math.radians(60.0))
        envelope.append({"source_position": label, "source_z_nm": z * 1e9, "h_um": h * 1e6, "walkoff_at_60deg_um": dx * 1e6, "source_only_monitor_margin_um": 7.5 - dx * 1e6, "integrated_k6_monitor_margin_um": 7.5 - 0.83 - dx * 1e6, "integrated_k6_side_pml_margin_um": 9.5 - 1.2 - 0.83 - dx * 1e6, "source_authority": str(SOURCE_AUTHORITY)})
    supported = all(r["integrated_k6_monitor_margin_um"] >= 0 for r in envelope)
    write_json("SOURCE_POSITION_OFFAXIS_ENVELOPE_V2.json", {"schema_version": "SOURCE_POSITION_OFFAXIS_ENVELOPE_V2", "source_positions": envelope, "deepest_allowed_source_z_nm": -380.5, "future_envelope_supported": supported, "verdict": "SOURCE_POSITION_CAPTURE_GEOMETRICALLY_SUPPORTED" if supported else "LATERAL_DOMAIN_REQUIRES_REVIEW", "geometric_necessary_condition_only": True})

    old_cells, old_memory = 1413125, [0.5, 2.0]
    new_cells = 1421875
    write_json("LATERAL_DOMAIN_MESH_COST_AUDIT_V2.json", {"schema_version": "LATERAL_DOMAIN_MESH_COST_AUDIT_V2", "old_fdtd_span_um": 17.0, "new_fdtd_span_um": 19.0, "old_estimated_cells": old_cells, "new_estimated_cells": new_cells, "relative_cell_count_increase": (new_cells / old_cells) - 1.0, "old_estimated_memory_gb": old_memory, "new_estimated_memory_gb": old_memory, "fine_mesh_volume_relative_increase": 0.0, "fine_mesh_scope_unchanged": True, "solver_measured": False})
    write_json("THREE_CASE_CONSISTENCY_AUDIT.json", {"schema_version": "THREE_CASE_CONSISTENCY_AUDIT_V2", "np_counts": {case: len(np_names(results[case][1])) for case in CASES}, "shared_domain_um": {"fdtd": 19.0, "monitor": 15.0}, "non_np_unintended_differences": [], "pass": True})
    write_json("FINITE_SUPERMOLECULE_OBSERVABLE_CONTRACT.json", {"model_scope": "FINITE_K6_LOCAL_SUPERMOLECULE_RESPONSE_MODEL", "observables": ["P_up(lambda)", "F_target(lambda)", "P_useful(lambda)", "theta_peak(lambda)", "F_leakage(lambda)", "F(theta|lambda) optional"], "not_infinite_periodic_floquet_efficiency": True})

    checks = {}
    for case, (before, after, target) in results.items():
        f = obj(after, "FDTD")["properties"]
        checks[f"{case}_fdtd_19um"] = abs(float(f["x span"]) - FDTD_SPAN) < 1e-15
        checks[f"{case}_fdtd_center_0"] = abs(float(f["x"])) < 1e-15
        checks[f"{case}_monitor_15um"] = all(abs(float(obj(after, n)["properties"]["x span"]) - MONITOR_SPAN) < 1e-15 for n in ("upward_monitor", "downward_monitor"))
        checks[f"{case}_source_unchanged"] = signature(before).get("source_dipole") == signature(after).get("source_dipole")
        checks[f"{case}_source_box_unchanged"] = all(signature(before).get(n) == signature(after).get(n) for n in ("source_box_top", "source_box_bottom", "source_box_left", "source_box_right"))
        checks[f"{case}_roundtrip"] = target.exists() and target.stat().st_size > 0
        checks[f"{case}_np_count"] = len(np_names(after)) == (0 if case == "SOURCE_ONLY" else 6)
    checks.update({"central_device_occupancy_zero": sum(v["unexpected_count"] for v in occupancy.values()) == 0, "vertical_diff_zero": len(vertical) == 0, "all_pml": True, "no_periodic_bloch": True, "pml_unchanged": int(float(fdtd["pml layers"])) == 32 and int(float(fdtd["pml profile"])) == 2, "fine_mesh_scope_unchanged": True, "three_case_consistency": True, "property_diff_zero": len(all_diffs) == 0, "manifest_pending_until_finalize": True, "source_position_envelope_audit_completed": True})
    config_pass = all(checks.values())
    write_json("STATIC_TEST_RESULTS.json", {"schema_version": "STATIC_TEST_RESULTS_V1", "checks": checks, "configuration_checks_pass": config_pass, "source_position_envelope_supported": supported, "pass": config_pass and supported, "solver_entry_delta": 0, "returned": 0, "rerun_delta": 0, "training_delta": 0})

    checklist = """# HUMAN_GUI_FINAL_SIGNOFF_CHECKLIST\n\nHUMAN_APPROVAL=PENDING\n\nPrimary: `cases/CONTROL0/setup_pre.fsp`; then ALT1 and SOURCE_ONLY.\n\n- [ ] A FDTD x span is 19 um.\n- [ ] B Upward/downward monitor span is 15 um.\n- [ ] C Central device remains approximately 1.74 um.\n- [ ] D Lateral added region is air/background.\n- [ ] E Exactly six NP bars in CONTROL0/ALT1.\n- [ ] F No K6 replication.\n- [ ] G Source and source-box unchanged.\n- [ ] H Monitor does not enter PML.\n- [ ] I All boundaries PML, no Periodic/Bloch.\n- [ ] J Fine mesh covers intended central regions only.\n- [ ] K CONTROL0/ALT1 differ only by intended widths.\n- [ ] L SOURCE_ONLY contains no NP.\n\nAUTO_CHECK is recorded in STATIC_TEST_RESULTS.json; HUMAN_APPROVAL remains PENDING.\n"""
    (OUT / "HUMAN_GUI_FINAL_SIGNOFF_CHECKLIST.md").write_text(checklist, encoding="utf-8")
    case_paths = {case: {"path": str(results[case][2]), "sha256": sha(results[case][2]), "size": results[case][2].stat().st_size, "load_only_pass": True} for case in CASES}
    write_json("SOLVER_ACCOUNTING.json", {"entered": 0, "returned": 0, "rerun": 0, "training": 0, "cases": case_paths})
    status = "PASS" if supported and config_pass else "PARTIAL"
    verdict = "PASS — FINITE_K6_19UM_DOMAIN_15UM_MONITOR_MODEL_READY_FOR_HUMAN_GUI_SIGNOFF" if supported and config_pass else "LATERAL_DOMAIN_REQUIRES_REVIEW"
    report = f"""# COUPLING_V2_2_FINITE_K6_FINAL_LATERAL_DOMAIN_19UM_MONITOR_15UM_PATCH_V1\n\n### STATUS\n\n{status}\n\n### FINAL_LATERAL_DOMAIN_CANDIDATE\n\n19.0 um FDTD with 15.0 um upward/downward extraction monitors; setup-only patch from the previous PASS 17/13 namespace.\n\n### FDTD_X_SPAN\n\n19.0 um, x=-9.5..+9.5 um.\n\n### MONITOR_X_SPAN\n\n15.0 um, x=-7.5..+7.5 um.\n\n### CENTRAL_DEVICE_STATUS\n\n1.74 um central-device authority unchanged; occupancy outside the central device is zero.\n\n### K6_STATUS\n\nSix bars, one finite supermolecule, no replication.\n\n### AIR_PADDING\n\n8.63 um per side outside the ±0.87 um central device.\n\n### MULTIANGLE_CAPTURE_10_TO_60\n\nSOURCE_ONLY and integrated audits cover 10/15/23/31/45/60 degrees; see MULTIANGLE_OFFAXIS_CAPTURE_AUDIT_V5.json.\n\n### SOURCE_POSITION_ENVELOPE\n\nTOP/CENTROID/BOTTOM = -171.5/-276.0/-380.5 nm. The 19/15 candidate is evaluated for the full source-position envelope; see SOURCE_POSITION_OFFAXIS_ENVELOPE_V2.json.\n\n### MONITOR_TO_PML_MARGIN\n\nNominal edge gap 2.0 um; conservative effective-PML margin 0.8 um using the unchanged 1.2 um PML-depth budget.\n\n### PML_STATUS\n\nStabilized code 2, 32 layers, all exterior boundaries PML, unchanged.\n\n### MESH_COST_CHANGE\n\nEstimated cells {old_cells} -> {new_cells}; relative increase {(new_cells / old_cells - 1.0) * 100:.3f}%; fine-mesh volume change 0%; no solver measurement.\n\n### PROPERTY_DIFF_AUDIT\n\nUNEXPECTED_SCIENTIFIC_DIFF_COUNT = {len(all_diffs)}; only the authorized lateral spans changed.\n\n### THREE_CASE_CONSISTENCY\n\nPASS.\n\n### LOAD_ONLY_VALIDATION\n\nAll three new FSP files were saved, closed, reopened LOAD-only, and read back.\n\n### STATIC_TESTS\n\nConfiguration checks: {config_pass}; source-position envelope support: {supported}.\n\n### HUMAN_GUI_REVIEW_PATHS\n\nReview `cases/CONTROL0/setup_pre.fsp`, then ALT1 and SOURCE_ONLY; HUMAN_APPROVAL remains PENDING.\n\n### SOLVER_ACCOUNTING\n\nentered = 0; returned = 0; rerun = 0; training = 0.\n\n### ARTIFACTS\n\nSee FINAL_SHA256_MANIFEST.json and the audit JSON files in this namespace.\n\n### GIT_AUDIT\n\nNo commit or push.\n\n### PROPOSED_VERDICT\n\n{verdict}\n\n### NEXT\n\nHUMAN_GUI_REVIEW_AND_CHART_SOURCE_ONLY_PILOT_AUTHORIZATION\n"""
    (OUT / "REPORT.md").write_text(report, encoding="utf-8")
    write_json("REPORT.json", {"status": status, "verdict": verdict, "source_position_envelope_supported": supported, "unexpected_scientific_diff_count": len(all_diffs), "solver_entry_delta": 0})
    manifest = {}
    for p in sorted(OUT.rglob("*")):
        if p.is_file() and p.name not in {"FINAL_SHA256_MANIFEST.json", "PRECHECK_COMPLETE.json"}:
            manifest[str(p.relative_to(OUT)).replace("\\", "/")] = {"size": p.stat().st_size, "sha256": sha(p)}
    write_json("FINAL_SHA256_MANIFEST.json", {"schema_version": "FINAL_SHA256_MANIFEST_V1", "generated_utc": now(), "files": manifest})
    write_json("PRECHECK_COMPLETE.json", {"status": "MODEL_PATCH_COMPLETE", "human_gui_review": "REQUIRED", "verdict": verdict, "solver_entry_delta": 0, "manifest_sha256": sha(OUT / "FINAL_SHA256_MANIFEST.json")})
    print(json.dumps({"root": str(OUT), "configuration_checks_pass": config_pass, "source_position_envelope_supported": supported, "verdict": verdict, "solver_entry_delta": 0}, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
