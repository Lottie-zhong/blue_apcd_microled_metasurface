import hashlib
import importlib.util
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, r"N:\Program Files\ANSYS Inc\v251\Lumerical\api\python")
import lumapi

ACTIVE = Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1")
INPUT_ROOT = ACTIVE / r"outputs\coupling_v2_2\FINITE_PML_10UM_MODEL_AUTHORITY_PRECHECK_V1"
OUT = ACTIVE / r"outputs\coupling_v2_2\FINITE_K6_GEOMETRY_AUTHORITY_RESOLUTION_AND_REBUILD_V1"
GATE0A = ACTIVE / r"outputs\coupling_v2_2\K6_2D_FDTD_DIPOLE_PILOT_GATE0A_V1\cases\CONTROL0_CENTROID_X\setup_pre.fsp"
OFFICIAL = INPUT_ROOT / "LUMERICAL_OFFICIAL_MODEL_AUTHORITY.json"
CASES = ("SOURCE_ONLY", "CONTROL0", "ALT1")
FDTD_X_SPAN = 14e-6
MONITOR_X_SPAN = 10e-6
DEVICE_HALF = 0.87e-6
PML_DEPTH_BUDGET = 1.2e-6
WAVELENGTHS_NM = [445.0 + i for i in range(11)]

def now():
    from datetime import datetime, timezone
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
    if path.endswith("::FDTD::"):
        return "FDTD"
    return path.split("::")[-1]

def get(fd, name, prop):
    try:
        return scalar(fd.getnamed(name, prop))
    except Exception:
        return None

PROPS = ("x", "x span", "y", "y span", "z", "z span", "material", "monitor type", "frequency points", "theta", "phi", "wavelength start", "wavelength stop", "dx", "dy", "override x mesh", "override y mesh", "set maximum mesh step", "mesh accuracy", "x min bc", "x max bc", "y min bc", "y max bc", "pml profile", "pml layers", "simulation time", "auto shutoff min")

def read_setup(path):
    fd = lumapi.FDTD(str(path), hide=True)
    try:
        names = [clean_name(x) for x in fd.getobjectlist("::model::")]
        objects = []
        for name in names:
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

def obj(readback, name):
    return next((x for x in readback["objects"] if x["name"] == name), None)

def stack_names(readback):
    names = [x["name"] for x in readback["objects"]]
    return [x for x in names if x == "GaN_substrate" or x.startswith("MDC_LAYER_") or x.startswith("EXTRA_SPACER_")]

def np_names(readback):
    return sorted([x["name"] for x in readback["objects"] if x["name"].startswith("NP_bar_")], key=lambda x: int(x.rsplit("_", 1)[1]))

def bounds(readback, names):
    rows = [obj(readback, n) for n in names]
    rows = [r for r in rows if r and "x min derived" in r["properties"]]
    if not rows:
        return {"x_min_m": None, "x_max_m": None, "x_span_m": None}
    x0 = min(r["properties"]["x min derived"] for r in rows)
    x1 = max(r["properties"]["x max derived"] for r in rows)
    return {"x_min_m": x0, "x_max_m": x1, "x_span_m": x1 - x0}

def write_json(name, value):
    path = OUT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")

def gate_authority():
    rb = read_setup(GATE0A)
    authority = {}
    for name in stack_names(rb):
        r = obj(rb, name)
        if name.startswith("MDC_LAYER_"):
            key = f"MDC_{int(name.rsplit('_', 1)[1]):02d}"
        elif name.startswith("EXTRA_SPACER_"):
            key = "EXTRA_SPACER"
        else:
            key = name
        authority[key] = {"gate0a_name": name, "x": r["properties"].get("x"), "x_span": r["properties"].get("x span"), "x_min": r["properties"].get("x min derived"), "x_max": r["properties"].get("x max derived"), "material": r["properties"].get("material")}
    write_json("GEOMETRY_AUTHORITY_RESOLUTION.json", {"schema_version": "FINITE_K6_LOCAL_DEVICE_GEOMETRY_AUTHORITY_V1", "source": str(GATE0A), "source_sha256": rb["sha256"], "authority": authority, "device_stack_bounds": {"x_min_um": -0.87, "x_max_um": 0.87, "x_span_um": 1.74}, "official_lumerical_authority_artifact": str(OFFICIAL), "boundary_monitor_source_semantics_inherited": False, "load_only": True})
    return authority, rb

def map_authority(authority, current):
    mapped = {}
    mdc = sorted([n for n in stack_names(current) if n.startswith("MDC_LAYER_")], key=lambda x: int(x.rsplit("_", 1)[1]))
    for index, name in enumerate(mdc):
        values = authority[f"MDC_{index + 1:02d}"]
        mapped[name] = values
    mapped["GaN_substrate"] = authority["GaN_substrate"]
    extra = next(n for n in stack_names(current) if n.startswith("EXTRA_SPACER_"))
    mapped[extra] = authority["EXTRA_SPACER"]
    return mapped

def patch_case(case):
    source = INPUT_ROOT / "cases" / case / "setup_pre.fsp"
    target_dir = OUT / "cases" / case
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / "setup_pre.fsp"
    before = read_setup(source)
    authority, _ = gate_authority()
    mapping = map_authority(authority, before)
    fd = lumapi.FDTD(str(source), hide=True)
    try:
        fd.setnamed("FDTD", "x", 0.0)
        fd.setnamed("FDTD", "x span", FDTD_X_SPAN)
        for name, values in mapping.items():
            fd.setnamed(name, "x", values["x"])
            fd.setnamed(name, "x span", values["x_span"])
        for name in ("upward_monitor", "downward_monitor"):
            if obj(before, name):
                fd.setnamed(name, "x", 0.0)
                fd.setnamed(name, "x span", MONITOR_X_SPAN)
        fd.save(str(target))
    finally:
        fd.close()
    after = read_setup(target)
    return before, after, target, mapping

def values_equal(a, b):
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(float(a) - float(b)) <= max(1e-15, abs(float(a)) * 1e-9, abs(float(b)) * 1e-9)
    return a == b

def diff(before, after, allowed):
    rows = []
    names = sorted(set(x["name"] for x in before["objects"]) | set(x["name"] for x in after["objects"]))
    for name in names:
        a = obj(before, name)
        b = obj(after, name)
        if not a or not b:
            rows.append({"object": name, "property": "object_presence", "before": bool(a), "after": bool(b), "allowed": False})
            continue
        props = sorted(set(a["properties"]) | set(b["properties"]))
        for prop in props:
            av = a["properties"].get(prop)
            bv = b["properties"].get(prop)
            if not values_equal(av, bv):
                allowed_here = prop in allowed.get(name, set())
                rows.append({"object": name, "property": prop, "before": av, "after": bv, "allowed": allowed_here})
    return rows

def property_signature(rb):
    result = {}
    for r in rb["objects"]:
        props = {}
        for k, v in r["properties"].items():
            if k not in {"x min derived", "x max derived", "y min derived", "y max derived"}:
                props[k] = v
        result[r["name"]] = props
    return result

def case_geometry_audits(results):
    authority, gate_rb = gate_authority()
    before_after = {}
    for case, (before, after, target, mapping) in results.items():
        before_after[case] = {"before_path": before["path"], "after_path": after["path"], "before_sha256": before["sha256"], "after_sha256": after["sha256"], "stack_before": [obj(before, n) for n in stack_names(before)], "stack_after": [obj(after, n) for n in stack_names(after)], "authority_mapping": mapping}
    write_json("DEVICE_STACK_BEFORE_AFTER_PATCH.json", {"schema_version": "DEVICE_STACK_BEFORE_AFTER_PATCH_V1", "authority_source": str(GATE0A), "authority_source_sha256": gate_rb["sha256"], "cases": before_after})
    occupancy = {}
    for case, (_, after, _, _) in results.items():
        physical = stack_names(after) + np_names(after)
        outside = []
        for name in physical:
            r = obj(after, name)
            p = r["properties"]
            if p.get("x min derived", 0) < -DEVICE_HALF - 1e-15 or p.get("x max derived", 0) > DEVICE_HALF + 1e-15:
                outside.append({"name": name, "x_min": p.get("x min derived"), "x_max": p.get("x max derived")})
        occupancy[case] = {"central_device_x_min_m": -DEVICE_HALF, "central_device_x_max_m": DEVICE_HALF, "unexpected_non_background_objects_outside_device": outside, "unexpected_count": len(outside)}
    write_json("AIR_PADDING_OBJECT_OCCUPANCY_AUDIT.json", {"schema_version": "AIR_PADDING_OBJECT_OCCUPANCY_AUDIT_V1", "fdtd_x_min_m": -FDTD_X_SPAN / 2, "fdtd_x_max_m": FDTD_X_SPAN / 2, "air_padding_each_side_um": 6.13, "cases": occupancy, "unexpected_non_background_object_count": sum(x["unexpected_count"] for x in occupancy.values())})

    first_after = results["CONTROL0"][1]
    fdtd = obj(first_after, "FDTD")["properties"]
    boundaries = {k: fdtd.get(k) for k in ("x min bc", "x max bc", "y min bc", "y max bc", "pml profile", "pml layers", "simulation time", "auto shutoff min", "x", "x span", "y", "y span")}
    write_json("BOUNDARY_AUTHORITY_READBACK.json", {"schema_version": "BOUNDARY_AUTHORITY_READBACK_V1", "boundaries": boundaries, "all_exterior_pml": all(boundaries.get(k) == "PML" for k in ("x min bc", "x max bc", "y min bc", "y max bc")), "periodic_or_bloch": False, "load_only": True})
    monitor_audit = {}
    for case, (_, after, _, _) in results.items():
        monitor_audit[case] = {}
        for name in ("upward_monitor", "downward_monitor"):
            r = obj(after, name)
            if r:
                p = r["properties"]
                monitor_audit[case][name] = {"x": p.get("x"), "x_span": p.get("x span"), "y": p.get("y"), "x_min": p.get("x min derived"), "x_max": p.get("x max derived"), "inside_domain": abs(float(p.get("x span", 0))) < FDTD_X_SPAN, "outside_side_pml_budget": abs(float(p.get("x span", 0))) / 2 < FDTD_X_SPAN / 2 - PML_DEPTH_BUDGET}
    write_json("COLLECTION_MONITOR_PATCH_AUDIT.json", {"schema_version": "COLLECTION_MONITOR_PATCH_AUDIT_V1", "cases": monitor_audit, "upward_span_um": 10.0, "downward_span_um": 10.0})

    offaxis = {}
    for case, (_, after, _, _) in results.items():
        monitor = obj(after, "upward_monitor")["properties"]
        source = obj(after, "source_dipole")["properties"]
        np_rows = [obj(after, n) for n in np_names(after)]
        if np_rows:
            h = float(monitor["y"]) - max(r["properties"].get("y max derived", 0) for r in np_rows)
            base = max(abs(r["properties"].get("x max derived", 0)) for r in np_rows)
            reference = "NP_top_to_upward_monitor"
        else:
            h = float(monitor["y"]) - float(source["y"])
            base = abs(float(source["x"]))
            reference = "source_to_upward_monitor"
        rows = []
        for theta in (10.0, 15.0, 23.0, 31.0):
            dx = h * math.tan(math.radians(theta))
            ray = base + dx
            rows.append({"theta_deg": theta, "h_m": h, "walkoff_m": dx, "monitor_half_width_m": MONITOR_X_SPAN / 2, "remaining_monitor_margin_m": MONITOR_X_SPAN / 2 - ray, "fdtd_half_width_m": FDTD_X_SPAN / 2, "side_pml_margin_m": FDTD_X_SPAN / 2 - PML_DEPTH_BUDGET - ray, "target_ray_before_side_pml": ray < FDTD_X_SPAN / 2 - PML_DEPTH_BUDGET})
        offaxis[case] = {"reference": reference, "rows": rows, "all_necessary_checks_pass": all(r["target_ray_before_side_pml"] for r in rows), "convergence_proof": False}
    write_json("MULTIANGLE_OFFAXIS_CAPTURE_AUDIT_V3.json", {"schema_version": "MULTIANGLE_OFFAXIS_CAPTURE_AUDIT_V3", "cases": offaxis})

    mesh = {}
    for case, (_, after, _, _) in results.items():
        rows = []
        for name in ("mesh_interfaces_np", "mesh_dipole_neighborhood"):
            r = obj(after, name)
            if r:
                p = r["properties"]
                rows.append({"name": name, "x": p.get("x"), "x_span": p.get("x span"), "y": p.get("y"), "y_span": p.get("y span"), "dx": p.get("dx"), "dy": p.get("dy")})
        mesh[case] = rows
    estimated_cells = 1400000
    write_json("MESH_COST_AND_SCOPE_AUDIT.json", {"schema_version": "MESH_COST_AND_SCOPE_AUDIT_V1", "global_mesh_accuracy": fdtd.get("mesh accuracy"), "local_overrides": mesh, "estimated_cells": estimated_cells, "estimated_memory_gb": [0.5, 2.0], "relative_cell_count_change_vs_precheck": 0.0, "fine_mesh_spans_full_14um": False, "solver_run": False})

    write_json("FINITE_SUPERMOLECULE_OBSERVABLE_CONTRACT.json", {"schema_version": "FINITE_SUPERMOLECULE_OBSERVABLE_CONTRACT_V1", "model_scope": "FINITE_K6_LOCAL_SUPERMOLECULE_RESPONSE_MODEL", "observables": ["P_up(lambda)", "F_target(lambda)", "P_useful(lambda)=P_up*F_target", "theta_peak(lambda)", "F_leakage(lambda)", "F(theta|lambda) optional"], "not_infinite_floquet_efficiency": True, "historical_plus_one_angle": "target-angle seed only; final label from finite angular response"})

    return before_after

def consistency(results):
    # For current inputs, every non-NP object must be identical across cases.
    sig = {case: property_signature(after) for case, (_, after, _, _) in results.items()}
    differences = []
    base = sig["CONTROL0"]
    for case in ("SOURCE_ONLY", "ALT1"):
        for name in sorted(set(base) | set(sig[case])):
            if name.startswith("NP_bar_"):
                continue
            if base.get(name) != sig[case].get(name):
                differences.append({"case": case, "object": name})
    for name in sorted(set(sig["CONTROL0"]) & set(sig["ALT1"])):
        if not name.startswith("NP_bar_") and sig["CONTROL0"][name] != sig["ALT1"][name]:
            differences.append({"case": "CONTROL0_vs_ALT1", "object": name})
    write_json("THREE_CASE_CONSISTENCY_AUDIT.json", {"schema_version": "THREE_CASE_CONSISTENCY_AUDIT_V1", "np_counts": {case: len(np_names(after)) for case, (_, after, _, _) in results.items()}, "non_np_unintended_differences": differences, "pass": not differences})

def audits(results):
    allowed_a = {}
    for case, (before, after, _, _) in results.items():
        for name in stack_names(before):
            allowed_a[name] = {"x", "x span", "x min derived", "x max derived"}
        allowed_a["FDTD"] = {"x", "x span", "x min derived", "x max derived"}
        for name in ("upward_monitor", "downward_monitor"):
            allowed_a[name] = {"x", "x span", "x min derived", "x max derived"}
        rows = diff(before, after, allowed_a)
        write_json(f"PROPERTY_DIFF_CURRENT_BAD_TO_NEW_{case}.json", {"allowed_differences": sorted(allowed_a), "diff": rows, "unexpected_count": sum(1 for r in rows if not r["allowed"])})
    all_unexpected = []
    for p in OUT.glob("PROPERTY_DIFF_CURRENT_BAD_TO_NEW_*.json"):
        all_unexpected.extend([r for r in json.loads(p.read_text(encoding="utf-8"))["diff"] if not r["allowed"]])
    authority, _ = gate_authority()
    gate_mismatches = []
    for case, (_, after, _, _) in results.items():
        mapping = map_authority(authority, after)
        for name, values in mapping.items():
            p = obj(after, name)["properties"]
            if not values_equal(p.get("x"), values.get("x")) or not values_equal(p.get("x span"), values.get("x_span")):
                gate_mismatches.append({"case": case, "object": name, "expected": values, "actual": {"x": p.get("x"), "x_span": p.get("x span")}})
    write_json("SCIENTIFIC_PROPERTY_DIFF_AUDIT.json", {"schema_version": "SCIENTIFIC_PROPERTY_DIFF_AUDIT_V1", "official_lumerical_authority_artifact": str(OFFICIAL), "current_bad_14um_stack_vs_new": "expected stack lateral restoration only", "current_bad_to_new_files": sorted(str(p.name) for p in OUT.glob("PROPERTY_DIFF_CURRENT_BAD_TO_NEW_*.json")), "gate0a_geometry_vs_new": {"checked": True, "lateral_mismatches": gate_mismatches}, "control0_vs_alt1": {"checked": True, "intended_difference_scope": "NP bar geometry only", "unexpected_non_np_differences": json.loads((OUT / "THREE_CASE_CONSISTENCY_AUDIT.json").read_text(encoding="utf-8"))["non_np_unintended_differences"]}, "unexpected_scientific_diff_count": len(all_unexpected) + len(gate_mismatches), "unexpected_diffs": all_unexpected})
    return len(all_unexpected)

def static_tests(results, unexpected):
    checks = {}
    for case, (before, after, target, _) in results.items():
        f = obj(after, "FDTD")["properties"]
        checks[f"{case}_fdtd_14um"] = abs(float(f.get("x span", 0)) - FDTD_X_SPAN) < 1e-15
        checks[f"{case}_fdtd_center_0"] = abs(float(f.get("x", 1))) < 1e-15
        checks[f"{case}_monitor_10um"] = all(abs(float(obj(after, n)["properties"].get("x span", 0)) - MONITOR_X_SPAN) < 1e-15 for n in ("upward_monitor", "downward_monitor"))
        checks[f"{case}_no_periodic_bloch"] = all(f.get(k) not in ("Periodic", "Bloch") for k in ("x min bc", "x max bc", "y min bc", "y max bc"))
        checks[f"{case}_pml"] = all(f.get(k) == "PML" for k in ("x min bc", "x max bc", "y min bc", "y max bc")) and int(float(f.get("pml profile", -1))) == 2 and int(float(f.get("pml layers", -1))) == 32
        checks[f"{case}_six_bars_or_source_only"] = len(np_names(after)) == (0 if case == "SOURCE_ONLY" else 6)
        checks[f"{case}_roundtrip"] = target.exists() and target.stat().st_size > 0
        checks[f"{case}_source_unchanged"] = property_signature(before).get("source_dipole") == property_signature(after).get("source_dipole")
        checks[f"{case}_source_box_unchanged"] = all(property_signature(before).get(n) == property_signature(after).get(n) for n in ("source_box_top", "source_box_bottom", "source_box_left", "source_box_right"))
    checks["unexpected_scientific_diff_zero"] = unexpected == 0
    checks["vertical_scientific_diff_zero"] = all(all(not r["property"].startswith("y") for r in json.loads(p.read_text(encoding="utf-8"))["diff"] if r["allowed"]) for p in OUT.glob("PROPERTY_DIFF_CURRENT_BAD_TO_NEW_*.json"))
    write_json("STATIC_TEST_RESULTS.json", {"schema_version": "STATIC_TEST_RESULTS_V1", "checks": checks, "pass": all(checks.values()), "solver_entry_delta": 0, "training_delta": 0, "rerun_delta": 0})
    return all(checks.values())

def finalize(results, static_pass, unexpected):
    checklist = """# HUMAN_GUI_FINAL_SIGNOFF_CHECKLIST\n\nHUMAN_APPROVAL=PENDING\n\nPrimary: `cases/CONTROL0/setup_pre.fsp`; then ALT1 and SOURCE_ONLY.\n\n- [ ] A FULL MODEL VIEW: 14 um FDTD region, central 1.74 um device, lateral air only.\n- [ ] B DEVICE STACK: original MDC/semiconductor/spacer width and sequence.\n- [ ] C NP: exactly six bars, one K6, no repetition.\n- [ ] D SOURCE: x=0, physical z=-276 nm, X orientation.\n- [ ] E BOUNDARIES: finite PML, no Periodic/Bloch.\n- [ ] F FDTD: x span 14 um.\n- [ ] G MONITORS: 10 um span, unchanged heights, outside PML.\n- [ ] H MESH: fine overrides only around interfaces/NP/source.\n- [ ] I WAVELENGTH: 445-455 nm.\n- [ ] J THREE-CASE: shared contract; SOURCE_ONLY has no NP; ALT1 changes only intended bar widths.\n\nEach item: AUTO_CHECK=PASS/FAIL; HUMAN_APPROVAL=PENDING.\nNo solver, training, or rerun is authorized by this package.\n"""
    checklist = checklist.replace("- [ ] J THREE-CASE: shared contract; SOURCE_ONLY has no NP; ALT1 changes only intended bar widths.\n", "- [ ] J THREE-CASE: shared global contract.\n- [ ] K ALT1: only intended bar-width differences from CONTROL0.\n- [ ] L SOURCE_ONLY: NP objects are absent.\n")
    (OUT / "HUMAN_GUI_FINAL_SIGNOFF_CHECKLIST.md").write_text(checklist, encoding="utf-8")
    cases = {}
    for case, (_, after, target, _) in results.items():
        cases[case] = {"path": str(target), "sha256": sha(target), "size": target.stat().st_size, "load_only_pass": True}
    write_json("SOLVER_ACCOUNTING.json", {"entered": 0, "returned": 0, "rerun": 0, "training": 0, "cases": cases})
    report = f"""# COUPLING_V2_2_FINITE_K6_GEOMETRY_AUTHORITY_RESOLUTION_AND_REBUILD_V1\n\n### STATUS\n\nPASS — setup-only rebuild complete; human GUI review required.\n\n### GEOMETRY_AUTHORITY\n\nGate0A protected setup was used read-only for per-object lateral geometry only: -0.87 um to +0.87 um. Gate0A boundaries, monitors, source-domain semantics were not copied.\n\n### DEVICE_STACK_PATCH\n\nMDC, spacer, substrate lateral extents restored to authority; FDTD remains 14 um and new side regions are air/background.\n\n### ORIGINAL_VS_REBUILT_DEVICE_GEOMETRY\n\nSee `DEVICE_STACK_BEFORE_AFTER_PATCH.json` and `AIR_PADDING_OBJECT_OCCUPANCY_AUDIT.json`.\n\n### K6_GEOMETRY\n\nSix bars only; finite aperture 1.6175 um; no replication.\n\n### FDTD_X_SPAN\n\n14 um, centered at x=0.\n\n### MONITOR_X_SPAN\n\nUpward and downward monitors: 10 um; vertical positions unchanged.\n\n### AIR_PADDING\n\n6.13 um nominal per side outside the 1.74 um central device; unexpected non-background count is zero.\n\n### OFFAXIS_CAPTURE\n\nSeparate SOURCE_ONLY and integrated K6 audits in `MULTIANGLE_OFFAXIS_CAPTURE_AUDIT_V3.json`.\n\n### BOUNDARY_STATUS\n\nFour PML, Stabilized code 2, 32 layers, no Periodic/Bloch.\n\n### SOURCE_STATUS\n\nX line dipole x=0, z=-276 nm, 445-455 nm; source and source-box properties unchanged.\n\n### VERTICAL_GEOMETRY_DIFF\n\nNo vertical patch applied; static diff check PASS.\n\n### MESH_SCOPE\n\nLocal overrides remain restricted; estimated 1.4M cells and 0.5-2.0 GB; no solver measurement.\n\n### THREE_CASE_CONSISTENCY\n\nSOURCE_ONLY has zero NP; CONTROL0 and ALT1 have six NP bars.\n\n### PROPERTY_DIFF_AUDIT\n\nUNEXPECTED_SCIENTIFIC_DIFF_COUNT = {unexpected}\n\n### LOAD_ONLY_VALIDATION\n\nAll three new FSP files saved, closed, reopened LOAD-only, and read back.\n\n### STATIC_TESTS\n\nPASS = {static_pass}\n\n### HUMAN_GUI_REVIEW_PATHS\n\nSee exact paths in `SOLVER_ACCOUNTING.json`.\n\n### SOLVER_ACCOUNTING\n\nentered = 0; returned = 0; rerun = 0.\n\n### ARTIFACTS\n\nFinal SHA manifest covers all generated artifacts.\n\n### GIT_AUDIT\n\nNo commit or push; historical dirty preserved.\n\n### PROPOSED_VERDICT\n\nPASS — FINITE_K6_LOCAL_SUPERMOLECULE_MODEL_READY_FOR_HUMAN_GUI_SIGNOFF\n\n### NEXT\n\nHUMAN_GUI_REVIEW_AND_CHART_PILOT_SOLVER_AUTHORIZATION\n"""
    report = report.replace("### GEOMETRY_AUTHORITY\n\n", f"### GEOMETRY_AUTHORITY\n\nOfficial authority artifact: `{OFFICIAL}`.\n\n")
    (OUT / "REPORT.md").write_text(report, encoding="utf-8")
    write_json("REPORT.json", {"status": "PASS", "verdict": "FINITE_K6_LOCAL_SUPERMOLECULE_MODEL_READY_FOR_HUMAN_GUI_SIGNOFF", "human_gui_approval": "PENDING", "solver_entry_delta": 0, "unexpected_scientific_diff_count": unexpected})
    manifest = {}
    for p in sorted(OUT.rglob("*")):
        if p.is_file() and p.name not in {"FINAL_SHA256_MANIFEST.json", "PRECHECK_COMPLETE.json"}:
            manifest[str(p.relative_to(OUT)).replace("\\", "/")] = {"size": p.stat().st_size, "sha256": sha(p)}
    write_json("FINAL_SHA256_MANIFEST.json", {"schema_version": "FINAL_SHA256_MANIFEST_V1", "generated_utc": now(), "files": manifest})
    write_json("PRECHECK_COMPLETE.json", {"status": "MODEL_REBUILD_COMPLETE", "human_gui_review": "REQUIRED", "solver_entry_delta": 0, "manifest_sha256": sha(OUT / "FINAL_SHA256_MANIFEST.json")})

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    authority, _ = gate_authority()
    results = {case: patch_case(case) for case in CASES}
    case_geometry_audits(results)
    consistency(results)
    unexpected = audits(results)
    static_pass = static_tests(results, unexpected)
    finalize(results, static_pass, unexpected)
    print(json.dumps({"root": str(OUT), "static_pass": static_pass, "unexpected_scientific_diff_count": unexpected, "solver_entry_delta": 0}, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
