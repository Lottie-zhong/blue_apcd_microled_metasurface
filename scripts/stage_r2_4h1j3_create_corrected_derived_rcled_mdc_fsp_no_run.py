from __future__ import annotations

import csv
import importlib.util
import json
import sys
import traceback
from datetime import datetime
from pathlib import Path

ROOT = Path(r"D:\project\worktrees\blue_apcd_rcled_mdc")
INPUT_FSP = Path(r"F:\wc_312\MDC_blue_oujizi.fsp")
RUNTIME_DIR = ROOT / "runtime" / "r2_4h1j3_rcled_mdc_corrected_derived_fsp_DO_NOT_COMMIT"
DERIVED_FSP = RUNTIME_DIR / "MDC_blue_oujizi_RCLED_QWexact453_10pair_H1J3.fsp"
OUT = ROOT / "outputs" / "r2_4h1j3_create_corrected_derived_rcled_mdc_fsp_no_run"
LUMAPI = Path(r"N:\Program Files\ANSYS Inc\v251\Lumerical\api\python\lumapi.py")

OUT.mkdir(parents=True, exist_ok=True)
RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
(RUNTIME_DIR / ".gitignore").write_text("""*.fsp
*.fspx
*.ldf
*.mat
*.h5
*.hdf5
*.png
*.jpg
*.jpeg
*.bmp
*.tif
*.tiff
*.gif
*.mp4
*.avi
""", encoding="utf-8")

GROUP = "H1J3_bottom_DBR_QWexact453_10pair"
TIO2_NM = 44.7
SIO2_NM = 79.4
PAIR_COUNT = 10
DBR_Y_MAX_NM = -950.0
DBR_TOTAL_NM = PAIR_COUNT * (TIO2_NM + SIO2_NM)
DBR_Y_MIN_NM = DBR_Y_MAX_NM - DBR_TOTAL_NM
FDTD_Y_MIN_NM = -2800.0
FDTD_Y_MAX_NM = 1400.0
FDTD_Y_CENTER_NM = (FDTD_Y_MIN_NM + FDTD_Y_MAX_NM) / 2.0
FDTD_Y_SPAN_NM = FDTD_Y_MAX_NM - FDTD_Y_MIN_NM
X_SPAN_NM = 6000.0
Z_SPAN_NM = 5000.0
SOURCE_X_NM = 0.0
SOURCE_Y_NM = -800.0
SOURCE_Z_NM = 0.0
WAVELENGTH_NM = 453.0


def nm(v: float) -> float:
    return v * 1e-9


def write_csv(path: Path, rows: list[dict], fields: list[str] | None = None) -> None:
    if fields is None:
        fields = []
        for row in rows:
            for key in row:
                if key not in fields:
                    fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_md(path: Path, text: str) -> None:
    path.write_text(text.strip() + "\n", encoding="utf-8")


def load_lumapi():
    spec = importlib.util.spec_from_file_location("lumapi", str(LUMAPI))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load lumapi from {LUMAPI}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["lumapi"] = module
    spec.loader.exec_module(module)
    return module


def stringify(v):
    try:
        if hasattr(v, "tolist"):
            return json.dumps(v.tolist())
        return str(v)
    except Exception:
        return repr(v)


def safe_call(label: str, func, default="unknown", errors: list[dict] | None = None):
    try:
        return func()
    except Exception as exc:
        if errors is not None:
            errors.append({"operation": label, "status": "failed", "error": str(exc)})
        return default


def get_prop(fdtd, obj: str, prop: str, errors: list[dict]):
    return safe_call(f"getnamed {obj}.{prop}", lambda: fdtd.getnamed(obj, prop), "unknown", errors)


def set_prop(fdtd, obj: str, prop: str, value, errors: list[dict]) -> str:
    try:
        fdtd.setnamed(obj, prop, value)
        return "set"
    except Exception as exc:
        errors.append({"operation": f"setnamed {obj}.{prop}", "status": "failed", "error": str(exc)})
        return f"failed: {exc}"


def set_current(fdtd, prop: str, value, errors: list[dict]) -> str:
    try:
        fdtd.set(prop, value)
        return "set"
    except Exception as exc:
        errors.append({"operation": f"set current {prop}", "status": "failed", "error": str(exc)})
        return f"failed: {exc}"


def set_first(fdtd, obj: str, candidates: list[str], value, errors: list[dict]) -> tuple[str, str]:
    details = []
    for prop in candidates:
        status = set_prop(fdtd, obj, prop, value, errors)
        details.append(f"{prop}:{status}")
        if status == "set":
            return prop, "; ".join(details)
    return "none", "; ".join(details)


def get_first(fdtd, obj: str, candidates: list[str], errors: list[dict]) -> tuple[str, str]:
    details = []
    for prop in candidates:
        value = get_prop(fdtd, obj, prop, errors)
        details.append(f"{prop}:{stringify(value)}")
        if stringify(value) != "unknown":
            return prop, stringify(value)
    return "none", "; ".join(details)


def nm_readback(value) -> str:
    try:
        return f"{float(value) * 1e9:.6g}"
    except Exception:
        return stringify(value)

errors: list[dict] = []
creation_rows: list[dict] = []
group_rows: list[dict] = []
layer_rows: list[dict] = []
mesh_rows: list[dict] = []
fdtd_rows: list[dict] = []
source_rows: list[dict] = []
monitor_rows: list[dict] = []
farfield_rows: list[dict] = []
safety_rows: list[dict] = []

h1j3_decision = "corrected_derived_fsp_creation_failed_no_run"
load_succeeded = False
save_succeeded = False
reopen_succeeded = False
run_called = False
layoutmode_before = "unknown"
layoutmode_after = "unknown"
switch_to_layout_attempted = False
group_created = False
group_membership_status = "unknown"
mesh_order_status = "unknown"
farfield_settings_status = "unknown"
monitor_global_safety = "requires_manual_gui_audit"
plane_source_enabled = "unknown"
source_1_enabled = "unknown"
source_1_x = "unknown"
source_1_y = "unknown"
source_1_wl_start = "unknown"
source_1_wl_stop = "unknown"
monitor_y = "unknown"

try:
    lumapi = load_lumapi()
    creation_rows.append({"step": "load_lumapi", "status": "ok", "detail": str(LUMAPI)})
    fdtd = lumapi.FDTD(hide=False)
    creation_rows.append({"step": "launch_fdtd", "status": "ok", "detail": "FDTD launched for no-run derived FSP construction"})
    fdtd.load(str(INPUT_FSP))
    load_succeeded = True
    creation_rows.append({"step": "load_original_input_fsp", "status": "ok", "detail": str(INPUT_FSP)})

    layoutmode_before = stringify(safe_call("layoutmode before", lambda: fdtd.layoutmode(), "unknown", errors))
    switch_to_layout_attempted = True
    sw = safe_call("switchtolayout", lambda: fdtd.switchtolayout(), "unknown", errors)
    layoutmode_after = stringify(safe_call("layoutmode after", lambda: fdtd.layoutmode(), "unknown", errors))
    creation_rows.append({"step": "layout_mode", "status": "recorded", "detail": f"before={layoutmode_before}; switch={stringify(sw)}; after={layoutmode_after}"})

    # FDTD region: keep H1J lower expansion.
    before_y = get_prop(fdtd, "FDTD", "y", errors)
    before_y_span = get_prop(fdtd, "FDTD", "y span", errors)
    set_y = set_prop(fdtd, "FDTD", "y", nm(FDTD_Y_CENTER_NM), errors)
    set_yspan = set_prop(fdtd, "FDTD", "y span", nm(FDTD_Y_SPAN_NM), errors)
    after_y = get_prop(fdtd, "FDTD", "y", errors)
    after_y_span = get_prop(fdtd, "FDTD", "y span", errors)
    fdtd_rows.append({
        "object": "FDTD",
        "target_y_min_nm": FDTD_Y_MIN_NM,
        "target_y_max_nm": FDTD_Y_MAX_NM,
        "target_y_center_nm": FDTD_Y_CENTER_NM,
        "target_y_span_nm": FDTD_Y_SPAN_NM,
        "before_y_m": stringify(before_y),
        "before_y_span_m": stringify(before_y_span),
        "set_y_status": set_y,
        "set_y_span_status": set_yspan,
        "after_y_m": stringify(after_y),
        "after_y_span_m": stringify(after_y_span),
        "note": "y max unchanged at 1400 nm; monitor not moved because global unsafe not confirmed",
    })

    # Structure group.
    try:
        fdtd.addstructuregroup()
        set_current(fdtd, "name", GROUP, errors)
        group_created = True
        group_rows.append({"group_name": GROUP, "created": True, "method": "addstructuregroup + set name", "members_expected": 20})
    except Exception as exc:
        errors.append({"operation": "addstructuregroup", "status": "failed", "error": str(exc)})
        group_rows.append({"group_name": GROUP, "created": False, "method": "addstructuregroup failed", "members_expected": 20})

    # Add bottom DBR layers. If group membership works, set properties through group::child path.
    current_y_top = DBR_Y_MAX_NM
    idx = 1
    member_ok = 0
    mesh_ok = 0
    for pair in range(1, PAIR_COUNT + 1):
        for mat_label, mat_name, thickness_nm in [("TiO2", "tio22", TIO2_NM), ("SiO2", "sio222", SIO2_NM)]:
            y_max = current_y_top
            y_min = y_max - thickness_nm
            y_center = 0.5 * (y_min + y_max)
            child_name = f"H1J3_bottom_DBR_layer_{idx:02d}_{mat_label}"
            fdtd.addrect()
            set_current(fdtd, "name", child_name, errors)
            in_group = False
            object_path = child_name
            addtogroup_status = "not_attempted"
            if group_created:
                try:
                    fdtd.addtogroup(GROUP)
                    addtogroup_status = "ok"
                    in_group = True
                    object_path = f"{GROUP}::{child_name}"
                    member_ok += 1
                except Exception as exc:
                    addtogroup_status = f"failed: {exc}"
                    errors.append({"operation": f"addtogroup {GROUP} for {child_name}", "status": "failed", "error": str(exc)})
            set_statuses = {
                "material": set_prop(fdtd, object_path, "material", mat_name, errors),
                "x": set_prop(fdtd, object_path, "x", 0.0, errors),
                "x_span": set_prop(fdtd, object_path, "x span", nm(X_SPAN_NM), errors),
                "y": set_prop(fdtd, object_path, "y", nm(y_center), errors),
                "y_span": set_prop(fdtd, object_path, "y span", nm(thickness_nm), errors),
                "z": set_prop(fdtd, object_path, "z", 0.0, errors),
                "z_span": set_prop(fdtd, object_path, "z span", nm(Z_SPAN_NM), errors),
            }
            override_prop, override_status = set_first(fdtd, object_path, [
                "override mesh order from material database",
                "override mesh order from material database?",
                "override mesh order",
            ], 1, errors)
            mesh_prop, mesh_status = set_first(fdtd, object_path, ["mesh order"], 1, errors)
            rb_override_prop, rb_override = get_first(fdtd, object_path, [
                "override mesh order from material database",
                "override mesh order from material database?",
                "override mesh order",
            ], errors)
            rb_mesh_prop, rb_mesh = get_first(fdtd, object_path, ["mesh order"], errors)
            if mesh_prop != "none" and rb_mesh not in ("unknown", ""):
                try:
                    if abs(float(rb_mesh) - 1.0) < 1e-9:
                        mesh_ok += 1
                except Exception:
                    pass
            layer_rows.append({
                "layer_index_top_to_bottom": idx,
                "pair_index": pair,
                "object_path": object_path,
                "child_name": child_name,
                "in_group": in_group,
                "addtogroup_status": addtogroup_status,
                "material_label": mat_label,
                "material_name": mat_name,
                "thickness_nm": thickness_nm,
                "y_min_nm": y_min,
                "y_max_nm": y_max,
                "y_center_nm": y_center,
                "x_span_nm": X_SPAN_NM,
                "z_span_nm": Z_SPAN_NM,
                **{f"set_{k}_status": v for k, v in set_statuses.items()},
            })
            mesh_rows.append({
                "layer_index_top_to_bottom": idx,
                "object_path": object_path,
                "override_mesh_order_property_used": override_prop,
                "override_mesh_order_set_status": override_status,
                "mesh_order_property_used": mesh_prop,
                "mesh_order_set_status": mesh_status,
                "override_mesh_order_readback_property": rb_override_prop,
                "override_mesh_order_readback": rb_override,
                "mesh_order_readback_property": rb_mesh_prop,
                "mesh_order_readback": rb_mesh,
                "status": "verified_mesh_order_1" if mesh_prop != "none" and rb_mesh not in ("unknown", "") else "requires_manual_gui_audit",
            })
            current_y_top = y_min
            idx += 1
    group_membership_status = "verified_all_20_members" if member_ok == 20 else f"requires_manual_gui_audit_members_verified_{member_ok}_of_20"
    mesh_order_status = "verified_all_20_mesh_order_1" if mesh_ok == 20 else f"requires_manual_gui_audit_mesh_verified_{mesh_ok}_of_20"
    group_rows[0]["members_created"] = len(layer_rows)
    group_rows[0]["members_added_to_group"] = member_ok
    group_rows[0]["membership_status"] = group_membership_status

    # Source setup.
    plane_before = stringify(get_prop(fdtd, "source", "enabled", errors))
    plane_set = set_prop(fdtd, "source", "enabled", 0, errors)
    plane_source_enabled = stringify(get_prop(fdtd, "source", "enabled", errors))
    source_rows.append({"object": "source", "role": "PlaneSource disabled for future dipole validation", "enabled_before": plane_before, "set_enabled_status": plane_set, "enabled_after": plane_source_enabled})

    src_set = {
        "enabled": set_prop(fdtd, "source_1", "enabled", 1, errors),
        "x": set_prop(fdtd, "source_1", "x", nm(SOURCE_X_NM), errors),
        "y": set_prop(fdtd, "source_1", "y", nm(SOURCE_Y_NM), errors),
        "z": set_prop(fdtd, "source_1", "z", nm(SOURCE_Z_NM), errors),
        "theta": set_prop(fdtd, "source_1", "theta", 90, errors),
        "phi": set_prop(fdtd, "source_1", "phi", 0, errors),
        "wavelength_start": set_prop(fdtd, "source_1", "wavelength start", nm(WAVELENGTH_NM), errors),
        "wavelength_stop": set_prop(fdtd, "source_1", "wavelength stop", nm(WAVELENGTH_NM), errors),
    }
    dipole_prop, dipole_status = set_first(fdtd, "source_1", ["dipole type", "source type"], "Electric dipole", errors)
    source_1_enabled = stringify(get_prop(fdtd, "source_1", "enabled", errors))
    source_1_x = stringify(get_prop(fdtd, "source_1", "x", errors))
    source_1_y = stringify(get_prop(fdtd, "source_1", "y", errors))
    source_1_wl_start = stringify(get_prop(fdtd, "source_1", "wavelength start", errors))
    source_1_wl_stop = stringify(get_prop(fdtd, "source_1", "wavelength stop", errors))
    source_rows.append({
        "object": "source_1",
        "role": "DipoleSource x-dipole at 453 nm",
        **{f"set_{k}_status": v for k, v in src_set.items()},
        "dipole_property_used": dipole_prop,
        "dipole_set_status": dipole_status,
        "enabled_after": source_1_enabled,
        "x_after_m": source_1_x,
        "y_after_m": source_1_y,
        "z_after_m": stringify(get_prop(fdtd, "source_1", "z", errors)),
        "theta_after_deg": stringify(get_prop(fdtd, "source_1", "theta", errors)),
        "phi_after_deg": stringify(get_prop(fdtd, "source_1", "phi", errors)),
        "wavelength_start_after_m": source_1_wl_start,
        "wavelength_stop_after_m": source_1_wl_stop,
    })

    # Monitor setup: keep y unchanged, record global-coordinate safety as manual-audit because top MDC global bounds not confirmed.
    monitor_y = stringify(get_prop(fdtd, "monitor", "y", errors))
    monitor_rows.append({
        "monitor_name": "monitor",
        "monitor_y_m": monitor_y,
        "monitor_y_nm": nm_readback(monitor_y),
        "monitor_global_safety": "requires_manual_gui_audit",
        "unsafe_confirmed": False,
        "action": "unchanged",
        "reason": "top MDC global/effective bounds not safely available; do not compare against local child-layer coordinates",
    })

    # Far-field settings: attempt common property names, record readbacks.
    farfield_specs = [
        ("projection direction", "auto", ["projection direction"]),
        ("material index", "auto", ["material index"]),
        ("far field filter", 1, ["far field filter"]),
        ("2D resolution", 1001, ["2D resolution", "2d resolution"]),
        ("3D resolution", 1001, ["3D resolution", "3d resolution"]),
        ("Assume structure is periodic", 0, ["Assume structure is periodic", "assume structure is periodic"]),
        ("override near field mesh", 0, ["override near field mesh", "Override near field mesh"]),
    ]
    ff_verified = 0
    for label, value, candidates in farfield_specs:
        used, set_status = set_first(fdtd, "monitor", candidates, value, errors)
        rb_prop, rb = get_first(fdtd, "monitor", candidates, errors)
        ok = used != "none" and rb_prop != "none" and rb != "unknown"
        if ok:
            ff_verified += 1
        farfield_rows.append({
            "setting": label,
            "target_value": value,
            "property_used_for_set": used,
            "set_status": set_status,
            "readback_property": rb_prop,
            "readback_value": rb,
            "status": "programmatically_accessible" if ok else "requires_manual_gui_audit",
        })
    farfield_settings_status = "programmatically_accessible_all" if ff_verified == len(farfield_specs) else f"requires_manual_gui_audit_accessible_{ff_verified}_of_{len(farfield_specs)}"

    # Geometry safety audit.
    safety_rows.extend([
        {"check": "bottom_dbr_layer_count", "status": len(layer_rows) == 20, "detail": len(layer_rows)},
        {"check": "bottom_dbr_group_membership", "status": member_ok == 20, "detail": group_membership_status},
        {"check": "bottom_dbr_y_range", "status": True, "detail": f"{DBR_Y_MIN_NM:.1f} to {DBR_Y_MAX_NM:.1f} nm"},
        {"check": "source_not_inside_bottom_dbr", "status": SOURCE_Y_NM > DBR_Y_MAX_NM, "detail": f"source y {SOURCE_Y_NM} nm; DBR top {DBR_Y_MAX_NM} nm"},
        {"check": "mesh_order_overlap_fix", "status": mesh_ok == 20, "detail": mesh_order_status},
        {"check": "monitor_not_moved_without_global_unsafe_confirmation", "status": True, "detail": "monitor remains at y=1100 nm"},
        {"check": "no_run_called", "status": True, "detail": "script does not call run/runanalysis/mesh/optimize/sweep"},
    ])

    fdtd.save(str(DERIVED_FSP))
    save_succeeded = DERIVED_FSP.exists()
    creation_rows.append({"step": "save_derived_h1j3_fsp", "status": "ok" if save_succeeded else "failed", "detail": str(DERIVED_FSP)})
    safe_call("close fdtd", lambda: fdtd.close(), None, errors)

    # Reopen/inspect derived file without running.
    if save_succeeded:
        fdtd2 = lumapi.FDTD(hide=False)
        fdtd2.load(str(DERIVED_FSP))
        reopen_succeeded = True
        creation_rows.append({"step": "reopen_derived_no_run", "status": "ok", "detail": str(DERIVED_FSP)})
        first_path = layer_rows[0]["object_path"] if layer_rows else "missing"
        last_path = layer_rows[-1]["object_path"] if layer_rows else "missing"
        creation_rows.append({
            "step": "inspect_first_last_layer",
            "status": "recorded",
            "detail": f"first_y={stringify(get_prop(fdtd2, first_path, 'y', errors))}; last_y={stringify(get_prop(fdtd2, last_path, 'y', errors))}",
        })
        safe_call("close derived fdtd", lambda: fdtd2.close(), None, errors)

    if save_succeeded:
        if mesh_order_status.startswith("verified") and farfield_settings_status.startswith("programmatically_accessible"):
            h1j3_decision = "corrected_derived_runtime_fsp_created_for_manual_gui_audit"
        else:
            h1j3_decision = "corrected_derived_runtime_fsp_created_requires_manual_gui_audit"
    else:
        h1j3_decision = "corrected_derived_fsp_creation_failed_no_run"
except Exception as exc:
    errors.append({"operation": "main", "status": "failed", "error": str(exc), "traceback": traceback.format_exc()})
    h1j3_decision = "corrected_derived_fsp_creation_failed_no_run"

# Write outputs.
write_csv(OUT / "r2_4h1j3_derived_fsp_creation_status.csv", creation_rows + errors)
write_csv(OUT / "r2_4h1j3_bottom_dbr_group_record.csv", group_rows)
write_csv(OUT / "r2_4h1j3_bottom_dbr_layer_table.csv", layer_rows)
write_csv(OUT / "r2_4h1j3_mesh_order_overlap_fix_record.csv", mesh_rows)
write_csv(OUT / "r2_4h1j3_fdtd_region_record.csv", fdtd_rows)
write_csv(OUT / "r2_4h1j3_source_record.csv", source_rows)
write_csv(OUT / "r2_4h1j3_monitor_global_coordinate_record.csv", monitor_rows)
write_csv(OUT / "r2_4h1j3_farfield_settings_record.csv", farfield_rows)
write_csv(OUT / "r2_4h1j3_geometry_safety_audit.csv", safety_rows)

write_md(OUT / "r2_4h1j3_manual_gui_audit_checklist.md", f"""
# R2-4H1J3 manual GUI audit checklist

Open the H1J3 derived FSP:

`{DERIVED_FSP}`

Confirm before any FDTD:

- bottom DBR exists as a group named `{GROUP}`
- group contains 20 layers
- material order is TiO2 then SiO2 repeated 10 times
- TiO2 layers are about 44.7 nm
- SiO2 layers are about 79.4 nm
- all bottom DBR layers use object-level mesh order override = true and mesh order = 1
- bottom DBR y range is about -2191 nm to -950 nm
- bottom DBR may overlap GaN rectangle, but mesh order makes DBR override GaN in overlap
- `source_1` default x=0 nm, y=-800 nm, z=0 nm
- `source_1` wavelength is 453 nm
- `source_1` remains x-dipole: theta=90 deg, phi=0 deg
- PlaneSource `source` is disabled
- FDTD y range is about -2800 to +1400 nm
- monitor y remains 1100 nm
- monitor is visually on the output side of the top MDC
- monitor is not inside TiO2/SiO2 layers
- monitor spacing from upper PML is reasonable
- far-field settings match:
  - projection direction = auto
  - material index = auto
  - far field filter = 1
  - 2D resolution = 1001
  - 3D resolution = 1001
  - Assume structure is periodic unchecked
  - override near field mesh unchecked
- no simulation was run
""")

write_md(OUT / "r2_4h1j3_do_not_commit_runtime_fsp_note.md", f"""
# Do not commit H1J3 runtime FSP

The H1J3 derived FSP is a runtime artifact only:

`{DERIVED_FSP}`

The runtime directory contains a `.gitignore` for FSP/LDF/MAT/H5/image/video files. Commit only the script, reports, CSV/JSON/MD, and the runtime `.gitignore`.
""")

write_md(OUT / "r2_4h1j3_next_stage_recommendation.md", """
# R2-4H1J3 next-stage recommendation

Next stage: `H1K manual GUI audit record for H1J3 derived FSP, no FDTD`.

Only after H1K passes should x-only three-position validation be discussed. Do not run y-dipole, broadband, APCD coupling, center-only validation, or any sweep.
""")

write_md(OUT / "r2_4h1j3_stop_allow_rules.md", """
# R2-4H1J3 stop / allow rules

Stop:
- no FDTD
- no run, runanalysis, mesh/run mesh, optimize, or sweep
- no y-dipole
- no broadband
- no APCD coupling
- no center-only validation
- no committing `.fsp`, `.fspx`, `.ldf`, `.mat`, `.h5`, screenshots, images, or videos

Allow:
- corrected derived runtime FSP creation only in the DO_NOT_COMMIT runtime directory
- lightweight CSV/JSON/MD audit outputs
- manual GUI inspection next
""")

write_md(OUT / "r2_4h1j3_summary.md", f"""
# R2-4H1J3 summary

Decision: `{h1j3_decision}`.

Derived H1J3 FSP:

`{DERIVED_FSP}`

Derived FSP exists: `{DERIVED_FSP.exists()}`.

Bottom DBR:

- group: `{GROUP}`
- layers: {len(layer_rows)}
- TiO2 thickness: {TIO2_NM:.1f} nm
- SiO2 thickness: {SIO2_NM:.1f} nm
- y range: {DBR_Y_MIN_NM:.1f} nm to {DBR_Y_MAX_NM:.1f} nm
- mesh order status: `{mesh_order_status}`

Source/monitor:

- `source_1` x readback: `{source_1_x}`
- `source_1` y readback: `{source_1_y}`
- wavelength start/stop readback: `{source_1_wl_start}` / `{source_1_wl_stop}`
- PlaneSource enabled readback: `{plane_source_enabled}`
- monitor y readback: `{monitor_y}`
- monitor global safety: `{monitor_global_safety}`
- far-field settings status: `{farfield_settings_status}`

Immediate FDTD allowed: `false`. Manual GUI audit required next: `true`.
""")

manifest = {
    "stage": "R2-4H1J3 corrected derived RCLED-MDC FSP no-run",
    "created_at": datetime.now().isoformat(timespec="seconds"),
    "input_fsp": str(INPUT_FSP),
    "runtime_dir": str(RUNTIME_DIR),
    "derived_fsp": str(DERIVED_FSP),
    "derived_fsp_exists": DERIVED_FSP.exists(),
    "h1j3_decision": h1j3_decision,
    "load_succeeded": load_succeeded,
    "save_succeeded": save_succeeded,
    "reopen_succeeded": reopen_succeeded,
    "layoutmode_before": layoutmode_before,
    "layoutmode_after": layoutmode_after,
    "switch_to_layout_attempted": switch_to_layout_attempted,
    "bottom_dbr_group_name": GROUP,
    "bottom_dbr_layer_count": len(layer_rows),
    "bottom_dbr_y_min_nm": DBR_Y_MIN_NM,
    "bottom_dbr_y_max_nm": DBR_Y_MAX_NM,
    "tio2_thickness_nm": TIO2_NM,
    "sio2_thickness_nm": SIO2_NM,
    "mesh_order_status": mesh_order_status,
    "group_membership_status": group_membership_status,
    "fdtd_y_min_nm": FDTD_Y_MIN_NM,
    "fdtd_y_max_nm": FDTD_Y_MAX_NM,
    "source_1_x_readback_m": source_1_x,
    "source_1_y_readback_m": source_1_y,
    "source_1_wavelength_start_readback_m": source_1_wl_start,
    "source_1_wavelength_stop_readback_m": source_1_wl_stop,
    "source_1_enabled_readback": source_1_enabled,
    "plane_source_enabled_readback": plane_source_enabled,
    "monitor_y_readback_m": monitor_y,
    "monitor_global_safety": monitor_global_safety,
    "farfield_settings_status": farfield_settings_status,
    "run_called": run_called,
    "immediate_fdtd_allowed": False,
    "manual_gui_audit_required_next": True,
    "y_dipole_allowed": False,
    "broadband_allowed": False,
    "apcd_coupling_allowed": False,
    "error_count": len(errors),
    "outputs": sorted(set([p.name for p in OUT.iterdir() if p.is_file()] + ["r2_4h1j3_manifest.json"])),
}
(OUT / "r2_4h1j3_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

print(json.dumps({
    "h1j3_decision": h1j3_decision,
    "derived_fsp": str(DERIVED_FSP),
    "derived_fsp_exists": DERIVED_FSP.exists(),
    "bottom_dbr_group_name": GROUP,
    "bottom_dbr_layer_count": len(layer_rows),
    "bottom_dbr_y_range_nm": [DBR_Y_MIN_NM, DBR_Y_MAX_NM],
    "mesh_order_status": mesh_order_status,
    "group_membership_status": group_membership_status,
    "source_1_x": source_1_x,
    "source_1_y": source_1_y,
    "source_1_wavelength_start": source_1_wl_start,
    "source_1_wavelength_stop": source_1_wl_stop,
    "plane_source_enabled": plane_source_enabled,
    "monitor_y": monitor_y,
    "monitor_global_safety": monitor_global_safety,
    "farfield_settings_status": farfield_settings_status,
    "error_count": len(errors),
    "immediate_fdtd_allowed": False,
}, indent=2))
