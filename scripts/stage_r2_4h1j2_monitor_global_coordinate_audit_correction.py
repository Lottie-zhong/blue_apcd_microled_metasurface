from __future__ import annotations

import csv
import importlib.util
import json
import sys
import traceback
from datetime import datetime
from pathlib import Path

ROOT = Path(r"D:\project\worktrees\blue_apcd_rcled_mdc")
DERIVED_FSP = ROOT / "runtime" / "r2_4h1j_rcled_mdc_derived_fsp_DO_NOT_COMMIT" / "MDC_blue_oujizi_RCLED_QWexact10pair_H1J.fsp"
OUT = ROOT / "outputs" / "r2_4h1j2_monitor_global_coordinate_audit_correction"
LUMAPI = Path(r"N:\Program Files\ANSYS Inc\v251\Lumerical\api\python\lumapi.py")
OUT.mkdir(parents=True, exist_ok=True)


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


def get_prop(fdtd, name: str, prop: str, errors: list[dict]):
    try:
        value = fdtd.getnamed(name, prop)
        return stringify(value), "ok"
    except Exception as exc:
        errors.append({"operation": f"getnamed {name}.{prop}", "status": "failed", "error": str(exc)})
        return "unknown", f"failed: {exc}"


def set_prop(fdtd, name: str, prop: str, value, errors: list[dict]):
    try:
        fdtd.setnamed(name, prop, value)
        return "set"
    except Exception as exc:
        errors.append({"operation": f"setnamed {name}.{prop}", "status": "failed", "error": str(exc)})
        return f"failed: {exc}"


def nm_value(text: str):
    try:
        if text in ("unknown", "", None):
            return None
        return float(text) * 1e9
    except Exception:
        return None


def audit_object(fdtd, name: str, role: str, errors: list[dict]) -> dict:
    props = ["x", "x span", "y", "y span", "z", "z span", "enabled", "monitor type", "projection direction", "material index", "far field filter", "2D resolution", "3D resolution", "Assume structure is periodic", "override near field mesh"]
    row = {"object_name": name, "role": role}
    ok_count = 0
    for prop in props:
        value, status = get_prop(fdtd, name, prop, errors)
        row[prop.replace(" ", "_")] = value
        row[prop.replace(" ", "_") + "_status"] = status
        if status == "ok":
            ok_count += 1
    row["coordinate_scope"] = "global_or_effective_if_object_is_top_level; local_if_child_of_group"
    row["readback_quality"] = "partial" if ok_count else "unavailable"
    return row

errors: list[dict] = []
coordinate_rows: list[dict] = []
monitor_rows: list[dict] = []
decision_rows: list[dict] = []
action_rows: list[dict] = []
h1j2_decision = "monitor_global_safety_requires_manual_gui_audit"
monitor_global_safety = "requires_manual_gui_audit"
monitor_action = "unchanged"
load_succeeded = False
run_called = False
save_called = False
monitor_y_nm = None
fdtd_y_min_nm = None
fdtd_y_max_nm = None
unsafe_confirmed = False
unsafe_reason = "not_confirmed"

try:
    lumapi = load_lumapi()
    fdtd = lumapi.FDTD(hide=False)
    fdtd.load(str(DERIVED_FSP))
    load_succeeded = True

    # No switch/save/run is needed for audit-only stage unless unsafe is clearly confirmed.
    for name, role in [
        ("FDTD", "simulation_region"),
        ("dbr", "top_MDC_structure_group_possible_parent"),
        ("monitor", "DFTMonitor_top_output_or_farfield"),
        ("monitor_1", "secondary_monitor_if_present"),
        ("source", "PlaneSource_should_remain_disabled"),
        ("source_1", "DipoleSource_x_validation_source"),
        ("H1J_bottom_DBR_QWexact10pair_01_TiO2", "bottom_DBR_first_layer_global_top_level"),
        ("H1J_bottom_DBR_QWexact10pair_20_SiO2", "bottom_DBR_last_layer_global_top_level"),
    ]:
        coordinate_rows.append(audit_object(fdtd, name, role, errors))

    # Attempt possible top MDC child-layer readbacks. Names are not trusted; failures are expected and recorded.
    child_candidates = [
        "dbr::tio22", "dbr::sio222", "dbr::TiO2", "dbr::SiO2", "dbr::rect", "dbr::rect_1",
        "dbr::layer", "dbr::layer_1", "dbr::MDC", "dbr::DBR",
    ]
    for name in child_candidates:
        row = audit_object(fdtd, name, "attempted_top_MDC_child_layer_coordinate_readback", errors)
        coordinate_rows.append(row)

    fdtd_y = next((r for r in coordinate_rows if r["object_name"] == "FDTD"), {})
    mon = next((r for r in coordinate_rows if r["object_name"] == "monitor"), {})
    monitor_y_nm = nm_value(mon.get("y"))
    fdtd_center_nm = nm_value(fdtd_y.get("y"))
    fdtd_span_nm = nm_value(fdtd_y.get("y_span"))
    if fdtd_center_nm is not None and fdtd_span_nm is not None:
        fdtd_y_min_nm = fdtd_center_nm - 0.5 * fdtd_span_nm
        fdtd_y_max_nm = fdtd_center_nm + 0.5 * fdtd_span_nm

    top_group = next((r for r in coordinate_rows if r["object_name"] == "dbr"), {})
    top_group_y_nm = nm_value(top_group.get("y"))
    top_group_span_nm = nm_value(top_group.get("y_span"))
    top_group_y_min_nm = None
    top_group_y_max_nm = None
    if top_group_y_nm is not None and top_group_span_nm is not None:
        top_group_y_min_nm = top_group_y_nm - 0.5 * top_group_span_nm
        top_group_y_max_nm = top_group_y_nm + 0.5 * top_group_span_nm

    # Safety logic: only move monitor if global unsafe condition is clearly confirmed.
    reasons = []
    if monitor_y_nm is None or fdtd_y_min_nm is None or fdtd_y_max_nm is None:
        monitor_global_safety = "requires_manual_gui_audit"
        reasons.append("monitor or FDTD global coordinate readback incomplete")
    else:
        pml_margin_nm = fdtd_y_max_nm - monitor_y_nm
        if pml_margin_nm < 100.0:
            unsafe_confirmed = True
            unsafe_reason = "monitor_too_close_to_upper_fdtd_boundary_or_pml_proxy"
            reasons.append(f"monitor y to y max margin {pml_margin_nm:.2f} nm < 100 nm")
        # We deliberately do NOT compare monitor y to local child layer coordinates.
        if top_group_y_min_nm is not None and top_group_y_max_nm is not None:
            if top_group_y_min_nm <= monitor_y_nm <= top_group_y_max_nm:
                # Group coordinates may be effective/global but still ambiguous for child-layer occupancy.
                monitor_global_safety = "requires_manual_gui_audit"
                reasons.append("monitor y lies inside dbr group bounding/effective range if readback is global; child-layer occupancy still requires GUI audit")
            elif monitor_y_nm < top_group_y_max_nm:
                monitor_global_safety = "requires_manual_gui_audit"
                reasons.append("monitor may be below output side of dbr group if dbr readback is global; requires GUI confirmation")
        else:
            monitor_global_safety = "requires_manual_gui_audit"
            reasons.append("top MDC/dbr effective global bounds unavailable")

    if unsafe_confirmed:
        # If this branch ever triggers, move monitor to a conservative output-side location and save a revised runtime FSP.
        # It is intentionally not expected for H1J2 unless global unsafe is clear.
        try:
            fdtd.switchtolayout()
            new_y_max_nm = max(fdtd_y_max_nm or 1400.0, 1800.0)
            new_monitor_y_nm = new_y_max_nm - 250.0
            set_prop(fdtd, "FDTD", "y", (fdtd_y_min_nm + new_y_max_nm) * 0.5e-9, errors)
            set_prop(fdtd, "FDTD", "y span", (new_y_max_nm - fdtd_y_min_nm) * 1e-9, errors)
            set_prop(fdtd, "monitor", "y", new_monitor_y_nm * 1e-9, errors)
            revised = DERIVED_FSP.with_name("MDC_blue_oujizi_RCLED_QWexact10pair_H1J2_monitor_corrected.fsp")
            fdtd.save(str(revised))
            save_called = True
            monitor_action = f"moved_and_saved_revised_runtime_fsp:{revised}"
            h1j2_decision = "monitor_moved_after_confirmed_global_unsafe"
            monitor_global_safety = "corrected_after_confirmed_unsafe"
        except Exception as exc:
            errors.append({"operation": "confirmed_unsafe_monitor_move", "status": "failed", "error": str(exc), "traceback": traceback.format_exc()})
            h1j2_decision = "monitor_correction_failed_requires_manual_gui_audit"
    else:
        monitor_action = "unchanged_no_global_unsafe_confirmed"
        h1j2_decision = "monitor_unchanged_requires_manual_gui_audit"

    monitor_rows.append({
        "monitor_name": "monitor",
        "monitor_y_nm": monitor_y_nm if monitor_y_nm is not None else "unknown",
        "fdtd_y_min_nm": fdtd_y_min_nm if fdtd_y_min_nm is not None else "unknown",
        "fdtd_y_max_nm": fdtd_y_max_nm if fdtd_y_max_nm is not None else "unknown",
        "dbr_group_y_min_nm": top_group_y_min_nm if top_group_y_min_nm is not None else "unknown",
        "dbr_group_y_max_nm": top_group_y_max_nm if top_group_y_max_nm is not None else "unknown",
        "monitor_global_safety": monitor_global_safety,
        "unsafe_confirmed": unsafe_confirmed,
        "unsafe_reason": unsafe_reason,
        "action": monitor_action,
        "reasoning": "; ".join(reasons) if reasons else "no clear global unsafe condition confirmed",
    })

    fdtd.close()
except Exception as exc:
    errors.append({"operation": "main", "status": "failed", "error": str(exc), "traceback": traceback.format_exc()})
    h1j2_decision = "monitor_global_audit_failed_requires_manual_gui_audit"

# Filter child coordinate rows into separate table too.
child_rows = [r for r in coordinate_rows if r.get("role") == "attempted_top_MDC_child_layer_coordinate_readback"]
summary_rows = [
    {"item": "h1j2_decision", "value": h1j2_decision},
    {"item": "monitor_global_safety", "value": monitor_global_safety},
    {"item": "monitor_action", "value": monitor_action},
    {"item": "load_succeeded", "value": load_succeeded},
    {"item": "run_called", "value": run_called},
    {"item": "save_called", "value": save_called},
    {"item": "manual_gui_audit_required", "value": True},
]

write_csv(OUT / "r2_4h1j2_global_coordinate_readback.csv", coordinate_rows)
write_csv(OUT / "r2_4h1j2_top_mdc_child_coordinate_attempts.csv", child_rows)
write_csv(OUT / "r2_4h1j2_monitor_global_safety_decision.csv", monitor_rows)
write_csv(OUT / "r2_4h1j2_action_record.csv", summary_rows)
write_csv(OUT / "r2_4h1j2_error_log.csv", errors)

write_md(OUT / "r2_4h1j2_manual_gui_audit_checklist.md", """
# R2-4H1J2 manual GUI audit checklist

This stage does not blindly move the DFT monitor based on child-layer local coordinates.

Manual GUI audit must confirm:

- monitor is on the output side of the top MDC;
- monitor is not inside TiO2/SiO2 layers;
- monitor has reasonable spacing from the upper PML;
- far-field settings match the user-approved settings:
  - projection direction = auto
  - material index = auto
  - far field filter = 1
  - 2D resolution = 1001
  - 3D resolution = 1001
  - Assume structure is periodic unchecked
  - override near field mesh unchecked

If GUI confirms the monitor is unsafe, a later explicit correction stage may move the monitor and save a revised runtime FSP. H1J2 does not run FDTD.
""")

write_md(OUT / "r2_4h1j2_monitor_correction_policy.md", """
# R2-4H1J2 monitor correction policy

Do not compare monitor y directly against top MDC child-layer local coordinates. Many objects use relative coordinates, so local child values such as y=1216-1316 nm are not automatically global coordinates.

H1J2 keeps the monitor unchanged unless one of these is clearly confirmed in global/effective coordinates:

1. the monitor is inside the top MDC stack;
2. the monitor is too close to the top PML;
3. the monitor is below the output-side structure.

If only local coordinates are accessible, monitor safety is `requires_manual_gui_audit`.
""")

write_md(OUT / "r2_4h1j2_summary.md", f"""
# R2-4H1J2 summary

Decision: `{h1j2_decision}`.

Monitor global safety: `{monitor_global_safety}`.

Monitor action: `{monitor_action}`.

H1J2 loaded the H1J derived FSP for no-run coordinate audit. It did not call run/runanalysis/mesh/optimize/sweep. It did not blindly move the monitor based on local child-layer coordinates.

Manual GUI audit is still required before any FDTD.
""")

write_md(OUT / "r2_4h1j2_stop_allow_rules.md", """
# R2-4H1J2 stop / allow rules

Stop:
- no FDTD
- no y-dipole
- no broadband
- no APCD coupling
- no center-only validation
- no monitor move based only on local child-layer coordinates
- no committing runtime FSPs or heavy files

Allow:
- lightweight coordinate audit reports
- manual GUI audit next
- future monitor correction only if global unsafe condition is explicitly confirmed
""")

manifest = {
    "stage": "R2-4H1J2 monitor global-coordinate audit correction",
    "created_at": datetime.now().isoformat(timespec="seconds"),
    "input_derived_fsp": str(DERIVED_FSP),
    "load_succeeded": load_succeeded,
    "run_called": run_called,
    "save_called": save_called,
    "h1j2_decision": h1j2_decision,
    "monitor_global_safety": monitor_global_safety,
    "monitor_action": monitor_action,
    "manual_gui_audit_required": True,
    "error_count": len(errors),
    "outputs": sorted(set([p.name for p in OUT.iterdir() if p.is_file()] + ["r2_4h1j2_manifest.json"])),
}
(OUT / "r2_4h1j2_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

print(json.dumps({
    "h1j2_decision": h1j2_decision,
    "monitor_global_safety": monitor_global_safety,
    "monitor_action": monitor_action,
    "load_succeeded": load_succeeded,
    "run_called": run_called,
    "save_called": save_called,
    "error_count": len(errors),
}, indent=2))
