from __future__ import annotations

import csv
import importlib.util
import json
import math
import sys
import traceback
from datetime import datetime
from pathlib import Path

ROOT = Path(r"D:\project\worktrees\blue_apcd_rcled_mdc")
INPUT_FSP = Path(r"F:\wc_312\MDC_blue_oujizi.fsp")
RUNTIME_DIR = ROOT / "runtime" / "r2_4h1j_rcled_mdc_derived_fsp_DO_NOT_COMMIT"
DERIVED_FSP = RUNTIME_DIR / "MDC_blue_oujizi_RCLED_QWexact10pair_H1J.fsp"
OUT = ROOT / "outputs" / "r2_4h1j_create_derived_rcled_mdc_fsp_no_run"
LUMAPI = Path(r"N:\Program Files\ANSYS Inc\v251\Lumerical\api\python\lumapi.py")

OUT.mkdir(parents=True, exist_ok=True)
RUNTIME_DIR.mkdir(parents=True, exist_ok=True)

GITIGNORE = """*.fsp
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
"""
(RUNTIME_DIR / ".gitignore").write_text(GITIGNORE, encoding="utf-8")

TIO2_NM = 44.37
SIO2_NM = 78.89
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
SOURCE_Y_NM = -800.0


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


def safe_call(label: str, func, default="unknown", errors: list[dict] | None = None):
    try:
        return func()
    except Exception as exc:
        if errors is not None:
            errors.append({"operation": label, "status": "failed", "error": str(exc)})
        return default


def safe_get(fdtd, obj: str, prop: str, errors: list[dict] | None = None):
    return safe_call(f"getnamed {obj}.{prop}", lambda: fdtd.getnamed(obj, prop), "unknown", errors)


def safe_set(fdtd, obj: str, prop: str, value, errors: list[dict] | None = None) -> str:
    try:
        fdtd.setnamed(obj, prop, value)
        return "set"
    except Exception as exc:
        if errors is not None:
            errors.append({"operation": f"setnamed {obj}.{prop}", "status": "failed", "error": str(exc)})
        return f"failed: {exc}"


def safe_set_current(fdtd, prop: str, value, errors: list[dict] | None = None) -> str:
    try:
        fdtd.set(prop, value)
        return "set"
    except Exception as exc:
        if errors is not None:
            errors.append({"operation": f"set current {prop}", "status": "failed", "error": str(exc)})
        return f"failed: {exc}"


def stringify(v):
    try:
        if hasattr(v, "tolist"):
            return json.dumps(v.tolist())
        return str(v)
    except Exception:
        return repr(v)

creation_rows: list[dict] = []
layer_rows: list[dict] = []
fdtd_rows: list[dict] = []
source_rows: list[dict] = []
safety_rows: list[dict] = []
errors: list[dict] = []
h1j_decision = "derived_fsp_creation_failed_no_run"
derived_exists = False
load_succeeded = False
save_succeeded = False
layoutmode_before = "unknown"
layoutmode_after = "unknown"
layer_count = 0
fdtd_y_min_after = "unknown"
fdtd_y_max_after = "unknown"
source_1_y_after = "unknown"
source_1_enabled_after = "unknown"
plane_source_enabled_after = "unknown"

try:
    lumapi = load_lumapi()
    creation_rows.append({"step": "load_lumapi", "status": "ok", "detail": str(LUMAPI)})
    fdtd = lumapi.FDTD(hide=False)
    creation_rows.append({"step": "launch_fdtd", "status": "ok", "detail": "FDTD launched for no-run setup save"})
    fdtd.load(str(INPUT_FSP))
    load_succeeded = True
    creation_rows.append({"step": "load_input_fsp", "status": "ok", "detail": str(INPUT_FSP)})

    layoutmode_before = safe_call("layoutmode before", lambda: fdtd.layoutmode(), "unknown", errors)
    creation_rows.append({"step": "layoutmode_before", "status": "recorded", "detail": stringify(layoutmode_before)})
    switch_status = safe_call("switchtolayout", lambda: fdtd.switchtolayout(), "unknown", errors)
    creation_rows.append({"step": "switchtolayout", "status": "attempted", "detail": stringify(switch_status)})
    layoutmode_after = safe_call("layoutmode after", lambda: fdtd.layoutmode(), "unknown", errors)
    creation_rows.append({"step": "layoutmode_after", "status": "recorded", "detail": stringify(layoutmode_after)})

    # FDTD expansion. Use center/span so target y-min/y-max are explicit.
    fdtd_before = {
        "y": safe_get(fdtd, "FDTD", "y", errors),
        "y span": safe_get(fdtd, "FDTD", "y span", errors),
        "x span": safe_get(fdtd, "FDTD", "x span", errors),
        "z span": safe_get(fdtd, "FDTD", "z span", errors),
    }
    y_set = safe_set(fdtd, "FDTD", "y", nm(FDTD_Y_CENTER_NM), errors)
    yspan_set = safe_set(fdtd, "FDTD", "y span", nm(FDTD_Y_SPAN_NM), errors)
    fdtd_after = {
        "y": safe_get(fdtd, "FDTD", "y", errors),
        "y span": safe_get(fdtd, "FDTD", "y span", errors),
        "x span": safe_get(fdtd, "FDTD", "x span", errors),
        "z span": safe_get(fdtd, "FDTD", "z span", errors),
    }
    fdtd_y_min_after = FDTD_Y_MIN_NM
    fdtd_y_max_after = FDTD_Y_MAX_NM
    fdtd_rows.append({
        "object": "FDTD",
        "property": "y/y span",
        "before": json.dumps({k: stringify(v) for k, v in fdtd_before.items()}),
        "target_y_min_nm": FDTD_Y_MIN_NM,
        "target_y_max_nm": FDTD_Y_MAX_NM,
        "target_y_center_nm": FDTD_Y_CENTER_NM,
        "target_y_span_nm": FDTD_Y_SPAN_NM,
        "set_y_status": y_set,
        "set_y_span_status": yspan_set,
        "after": json.dumps({k: stringify(v) for k, v in fdtd_after.items()}),
        "note": "x span, z span, boundary, and mesh settings intentionally left unchanged unless Lumerical internals adjust them",
    })

    # Source isolation settings for future dipole validation.
    source_rows.append({
        "object": "source",
        "role": "PlaneSource; present but disabled for future dipole validation",
        "enabled_before": stringify(safe_get(fdtd, "source", "enabled", errors)),
        "set_enabled_status": safe_set(fdtd, "source", "enabled", 0, errors),
        "enabled_after": stringify(safe_get(fdtd, "source", "enabled", errors)),
        "y_m": stringify(safe_get(fdtd, "source", "y", errors)),
        "note": "If enabled is unknown in GUI, user must mark PlaneSource as not used for dipole validation",
    })
    source_rows.append({
        "object": "source_1",
        "role": "DipoleSource x-dipole; keep enabled for x-only validation",
        "enabled_before": stringify(safe_get(fdtd, "source_1", "enabled", errors)),
        "set_enabled_status": safe_set(fdtd, "source_1", "enabled", 1, errors),
        "enabled_after": stringify(safe_get(fdtd, "source_1", "enabled", errors)),
        "x_m": stringify(safe_get(fdtd, "source_1", "x", errors)),
        "y_m": stringify(safe_get(fdtd, "source_1", "y", errors)),
        "theta_deg": stringify(safe_get(fdtd, "source_1", "theta", errors)),
        "phi_deg": stringify(safe_get(fdtd, "source_1", "phi", errors)),
        "wavelength_start_m": stringify(safe_get(fdtd, "source_1", "wavelength start", errors)),
        "wavelength_stop_m": stringify(safe_get(fdtd, "source_1", "wavelength stop", errors)),
        "note": "No y/z dipole or broadband created in H1J",
    })
    source_1_y_after = source_rows[-1]["y_m"]
    source_1_enabled_after = source_rows[-1]["enabled_after"]
    plane_source_enabled_after = source_rows[0]["enabled_after"]
    source_rows.append({
        "object": "monitor",
        "role": "existing monitor kept unchanged initially",
        "enabled_before": stringify(safe_get(fdtd, "monitor", "enabled", errors)),
        "set_enabled_status": "unchanged",
        "enabled_after": stringify(safe_get(fdtd, "monitor", "enabled", errors)),
        "x_m": stringify(safe_get(fdtd, "monitor", "x", errors)),
        "y_m": stringify(safe_get(fdtd, "monitor", "y", errors)),
        "note": "Manual GUI audit must confirm monitor remains reasonable for top output/farfield",
    })

    # Add bottom DBR layers from cavity side downward: TiO2 then SiO2 repeated.
    current_y_top = DBR_Y_MAX_NM
    index = 1
    for pair in range(1, PAIR_COUNT + 1):
        for material_label, material_name, thickness_nm in [
            ("TiO2", "tio22", TIO2_NM),
            ("SiO2", "sio222", SIO2_NM),
        ]:
            y_max = current_y_top
            y_min = y_max - thickness_nm
            y_center = 0.5 * (y_min + y_max)
            name = f"H1J_bottom_DBR_QWexact10pair_{index:02d}_{material_label}"
            fdtd.addrect()
            name_status = safe_set_current(fdtd, "name", name, errors)
            mat_status = safe_set_current(fdtd, "material", material_name, errors)
            x_status = safe_set_current(fdtd, "x", 0.0, errors)
            xspan_status = safe_set_current(fdtd, "x span", nm(X_SPAN_NM), errors)
            y_status = safe_set_current(fdtd, "y", nm(y_center), errors)
            yspan_status_layer = safe_set_current(fdtd, "y span", nm(thickness_nm), errors)
            z_status = safe_set_current(fdtd, "z", 0.0, errors)
            zspan_status = safe_set_current(fdtd, "z span", nm(Z_SPAN_NM), errors)
            layer_rows.append({
                "layer_index_top_to_bottom": index,
                "pair_index": pair,
                "name": name,
                "material_label": material_label,
                "material_name": material_name,
                "thickness_nm": thickness_nm,
                "y_min_nm": y_min,
                "y_max_nm": y_max,
                "y_center_nm": y_center,
                "x_span_nm": X_SPAN_NM,
                "z_span_nm": Z_SPAN_NM,
                "set_name_status": name_status,
                "set_material_status": mat_status,
                "set_x_status": x_status,
                "set_x_span_status": xspan_status,
                "set_y_status": y_status,
                "set_y_span_status": yspan_status_layer,
                "set_z_status": z_status,
                "set_z_span_status": zspan_status,
            })
            current_y_top = y_min
            index += 1
    layer_count = len(layer_rows)

    # Save derived only. Never save original.
    fdtd.save(str(DERIVED_FSP))
    save_succeeded = DERIVED_FSP.exists()
    derived_exists = save_succeeded
    creation_rows.append({"step": "save_derived_fsp", "status": "ok" if save_succeeded else "failed", "detail": str(DERIVED_FSP)})
    h1j_decision = "derived_runtime_fsp_created_for_manual_gui_audit" if save_succeeded else "derived_fsp_creation_failed_no_run"

    # Re-open/inspect derived file without run if possible.
    safe_call("close first fdtd", lambda: fdtd.close(), None, errors)
    if save_succeeded:
        fdtd2 = lumapi.FDTD(hide=False)
        fdtd2.load(str(DERIVED_FSP))
        creation_rows.append({"step": "reopen_derived_fsp_no_run", "status": "ok", "detail": str(DERIVED_FSP)})
        # quick object check for first and last DBR layer.
        first_layer_y = safe_get(fdtd2, layer_rows[0]["name"], "y", errors) if layer_rows else "missing"
        last_layer_y = safe_get(fdtd2, layer_rows[-1]["name"], "y", errors) if layer_rows else "missing"
        creation_rows.append({"step": "inspect_derived_first_last_layer", "status": "recorded", "detail": f"first_y={stringify(first_layer_y)}; last_y={stringify(last_layer_y)}"})
        safe_call("close derived fdtd", lambda: fdtd2.close(), None, errors)
except Exception as exc:
    errors.append({"operation": "main", "status": "failed", "error": str(exc), "traceback": traceback.format_exc()})
    h1j_decision = "derived_fsp_creation_failed_no_run"

# Safety audit from planned coordinates and file status.
safety_rows.extend([
    {"check": "derived_fsp_exists", "status": bool(DERIVED_FSP.exists()), "detail": str(DERIVED_FSP)},
    {"check": "derived_fsp_under_runtime_do_not_commit", "status": str(DERIVED_FSP).startswith(str(RUNTIME_DIR)), "detail": str(RUNTIME_DIR)},
    {"check": "bottom_dbr_layer_count", "status": layer_count == 20, "detail": layer_count},
    {"check": "bottom_dbr_y_range_nm", "status": abs(DBR_Y_MIN_NM + 2182.6) < 1.0 and abs(DBR_Y_MAX_NM + 950.0) < 1e-6, "detail": f"{DBR_Y_MIN_NM:.2f} to {DBR_Y_MAX_NM:.2f} nm"},
    {"check": "source_1_not_inside_bottom_dbr_by_plan", "status": SOURCE_Y_NM > DBR_Y_MAX_NM, "detail": f"source_1 y {SOURCE_Y_NM:.1f} nm; DBR top {DBR_Y_MAX_NM:.1f} nm; gap {SOURCE_Y_NM - DBR_Y_MAX_NM:.1f} nm"},
    {"check": "fdtd_y_min_includes_bottom_dbr_and_margin", "status": FDTD_Y_MIN_NM < DBR_Y_MIN_NM, "detail": f"FDTD y min {FDTD_Y_MIN_NM:.1f} nm; DBR bottom {DBR_Y_MIN_NM:.1f} nm; margin {DBR_Y_MIN_NM - FDTD_Y_MIN_NM:.1f} nm"},
    {"check": "no_run_called", "status": True, "detail": "script contains no run/runanalysis/mesh/optimize/sweep calls"},
    {"check": "manual_gui_audit_required", "status": True, "detail": "user must inspect geometry before any FDTD"},
])

write_csv(OUT / "r2_4h1j_derived_fsp_creation_status.csv", creation_rows + errors)
write_csv(OUT / "r2_4h1j_bottom_dbr_layer_table.csv", layer_rows)
write_csv(OUT / "r2_4h1j_fdtd_region_change_record.csv", fdtd_rows)
write_csv(OUT / "r2_4h1j_source_monitor_status_record.csv", source_rows)
write_csv(OUT / "r2_4h1j_geometry_safety_audit.csv", safety_rows)

write_md(OUT / "r2_4h1j_manual_gui_audit_checklist.md", f"""
# R2-4H1J manual GUI audit checklist

Open the derived FSP manually:

`{DERIVED_FSP}`

Confirm before any FDTD:

- bottom DBR exists and has 20 layers
- layer prefix is `H1J_bottom_DBR_QWexact10pair`
- materials alternate `tio22` / `sio222`
- TiO2 layers are 44.37 nm
- SiO2 layers are 78.89 nm
- bottom DBR y range is about -2182.55 nm to -950 nm
- `source_1` remains at about y=-800 nm and is not inside DBR
- there is no overlap between bottom DBR and existing MDC
- FDTD y min/y max are expanded to about -2800 nm to +1400 nm
- PML margin below bottom DBR is reasonable
- PlaneSource `source` is disabled or clearly marked not to use for dipole validation
- DipoleSource `source_1` remains enabled for x-dipole validation
- monitor remains in a reasonable top-output/far-field position
- no simulation was run
""")

write_md(OUT / "r2_4h1j_do_not_commit_runtime_fsp_note.md", f"""
# Do not commit runtime FSP

The derived FSP is a runtime artifact only:

`{DERIVED_FSP}`

The runtime directory contains a `.gitignore` that blocks `.fsp`, `.fspx`, `.ldf`, `.mat`, `.h5`, image, and video files. Commit only lightweight audit files and the `.gitignore`, never the derived FSP.
""")

write_md(OUT / "r2_4h1j_next_stage_recommendation.md", """
# R2-4H1J next-stage recommendation

Next stage: `H1K manual GUI audit record for derived FSP, no FDTD`.

Only after H1K passes should we discuss x-only three-position validation. Do not run y-dipole, broadband, APCD coupling, center-only validation, or any sweep.
""")

write_md(OUT / "r2_4h1j_stop_allow_rules.md", """
# R2-4H1J stop / allow rules

Stop:
- no FDTD
- no run, runanalysis, mesh/run mesh, optimize, or sweep
- no y-dipole
- no broadband
- no APCD coupling
- no center-only validation
- no committing `.fsp`, `.fspx`, `.ldf`, `.mat`, `.h5`, screenshots, images, or videos

Allow:
- derived runtime FSP creation only in the DO_NOT_COMMIT runtime directory
- lightweight CSV/JSON/MD audit outputs
- manual GUI inspection next
""")

write_md(OUT / "r2_4h1j_summary.md", f"""
# R2-4H1J summary

Decision: `{h1j_decision}`.

Derived FSP path:

`{DERIVED_FSP}`

Derived FSP exists: `{DERIVED_FSP.exists()}`.

Bottom DBR plan:

- candidate: `DBR_QW_exact_450_10pair`
- layers: {layer_count}
- order from cavity side downward: TiO2 then SiO2 repeated 10 times
- y range: {DBR_Y_MIN_NM:.2f} nm to {DBR_Y_MAX_NM:.2f} nm
- x span fallback: {X_SPAN_NM:.0f} nm
- z span fallback: {Z_SPAN_NM:.0f} nm

FDTD target y range: {FDTD_Y_MIN_NM:.0f} nm to {FDTD_Y_MAX_NM:.0f} nm.

Immediate FDTD allowed: `false`. Manual GUI audit required next: `true`.
""")

manifest = {
    "stage": "R2-4H1J create derived RCLED-MDC FSP no-run",
    "created_at": datetime.now().isoformat(timespec="seconds"),
    "input_fsp": str(INPUT_FSP),
    "runtime_dir": str(RUNTIME_DIR),
    "derived_fsp": str(DERIVED_FSP),
    "derived_fsp_exists": DERIVED_FSP.exists(),
    "h1j_decision": h1j_decision,
    "load_succeeded": load_succeeded,
    "save_succeeded": save_succeeded,
    "layoutmode_before": stringify(layoutmode_before),
    "layoutmode_after": stringify(layoutmode_after),
    "bottom_dbr_layer_count": layer_count,
    "bottom_dbr_y_min_nm": DBR_Y_MIN_NM,
    "bottom_dbr_y_max_nm": DBR_Y_MAX_NM,
    "fdtd_y_min_nm": FDTD_Y_MIN_NM,
    "fdtd_y_max_nm": FDTD_Y_MAX_NM,
    "source_1_y_position_readback": stringify(source_1_y_after),
    "source_1_enabled_status": stringify(source_1_enabled_after),
    "plane_source_enabled_status": stringify(plane_source_enabled_after),
    "run_called": False,
    "immediate_fdtd_allowed": False,
    "manual_gui_audit_required_next": True,
    "y_dipole_allowed": False,
    "broadband_allowed": False,
    "apcd_coupling_allowed": False,
    "error_count": len(errors),
    "outputs": sorted(set([p.name for p in OUT.iterdir() if p.is_file()] + ["r2_4h1j_manifest.json"])),
}
(OUT / "r2_4h1j_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

print(json.dumps({
    "h1j_decision": h1j_decision,
    "derived_fsp": str(DERIVED_FSP),
    "derived_fsp_exists": DERIVED_FSP.exists(),
    "bottom_dbr_layer_count": layer_count,
    "bottom_dbr_y_range_nm": [DBR_Y_MIN_NM, DBR_Y_MAX_NM],
    "fdtd_y_range_nm": [FDTD_Y_MIN_NM, FDTD_Y_MAX_NM],
    "source_1_y": stringify(source_1_y_after),
    "source_1_enabled": stringify(source_1_enabled_after),
    "plane_source_enabled": stringify(plane_source_enabled_after),
    "error_count": len(errors),
    "immediate_fdtd_allowed": False,
}, indent=2))
