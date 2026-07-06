from __future__ import annotations

import csv
import datetime as dt
import importlib.util
import json
from pathlib import Path
from typing import Any

ROOT = Path(r"D:\project\worktrees\blue_apcd_rcled_mdc")
OUT = ROOT / "outputs" / "r2_4h1d_lumerical_internal_no_run_fsp_audit"
FSP = Path(r"F:\wc_312\MDC_blue_oujizi.fsp")
LUMAPI_PATH = Path(r"N:\Program Files\ANSYS Inc\v251\Lumerical\api\python\lumapi.py")

SOURCE_TOKENS = ["source", "dipole", "plane", "planewave", "gaussian", "import", "mode", "mqw", "qujizi", "oujizi"]
MONITOR_TOKENS = ["monitor", "farfield", "far field", "power", "field", "frequency", "movie"]
FDTD_TOKENS = ["fdtd", "simulation region"]
MATERIAL_TOKENS = ["sio2", "ti o2", "tio2", "gan", "ito", "air", "substrate", "dbr", "mdc"]
PROPS = [
    "name", "type", "x", "y", "z", "x span", "y span", "z span", "radius", "thickness", "material",
    "wavelength", "wavelength start", "wavelength stop", "center wavelength", "frequency points",
    "dipole orientation", "theta", "phi", "polarization", "polarization angle",
    "x min bc", "x max bc", "y min bc", "y max bc", "z min bc", "z max bc", "mesh accuracy",
]


def safe_str(value: Any) -> str:
    try:
        if value is None:
            return ""
        if isinstance(value, (str, int, float, bool)):
            return str(value)
        if hasattr(value, "tolist"):
            value = value.tolist()
        return json.dumps(value, ensure_ascii=False, default=str)
    except Exception:
        return str(value)


def flatten(value: Any) -> list[str]:
    if value is None:
        return []
    if hasattr(value, "tolist"):
        value = value.tolist()
    if isinstance(value, str):
        return [value]
    if isinstance(value, bytes):
        return [value.decode(errors="replace")]
    if isinstance(value, (list, tuple)):
        out: list[str] = []
        for item in value:
            out.extend(flatten(item))
        return [x for x in out if x]
    return [str(value)]


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_md(path: Path, text: str) -> None:
    path.write_text(text.strip() + "\n", encoding="utf-8")


def import_lumapi() -> tuple[Any | None, str]:
    if not LUMAPI_PATH.exists():
        return None, f"missing lumapi.py: {LUMAPI_PATH}"
    try:
        spec = importlib.util.spec_from_file_location("lumapi", str(LUMAPI_PATH))
        if spec is None or spec.loader is None:
            return None, "could not create lumapi spec"
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)  # type: ignore[union-attr]
        return module, ""
    except Exception as exc:
        return None, f"lumapi import failed: {type(exc).__name__}: {exc}"


def record_attempt(rows: list[dict[str, Any]], name: str, category: str, command: str, ok: bool, result: Any = "", error: str = "") -> None:
    rows.append({
        "attempt_name": name,
        "category": category,
        "command_or_api": command,
        "succeeded": str(ok).lower(),
        "result_preview": safe_str(result)[:600],
        "error": error[:1000],
    })


def call_api(fdtd: Any, rows: list[dict[str, Any]], name: str, method: str, *args: Any) -> tuple[bool, Any]:
    try:
        result = getattr(fdtd, method)(*args)
        record_attempt(rows, name, "lumapi_method", f"{method}({', '.join(map(repr, args))})", True, result, "")
        return True, result
    except Exception as exc:
        record_attempt(rows, name, "lumapi_method", f"{method}({', '.join(map(repr, args))})", False, "", f"{type(exc).__name__}: {exc}")
        return False, None


def eval_script(fdtd: Any, rows: list[dict[str, Any]], name: str, script: str, variables: list[str] | None = None) -> tuple[bool, dict[str, Any]]:
    values: dict[str, Any] = {}
    try:
        result = fdtd.eval(script)
        record_attempt(rows, name, "lumerical_script", script, True, result, "")
        for var in variables or []:
            ok, val = call_api(fdtd, rows, f"getv_{name}_{var}", "getv", var)
            if ok:
                values[var] = val
        return True, values
    except Exception as exc:
        record_attempt(rows, name, "lumerical_script", script, False, "", f"{type(exc).__name__}: {exc}")
        return False, values


def classify(name: str, obj_type: str, props_json: str = "") -> str:
    text = f"{name} {obj_type} {props_json}".lower()
    if any(t in text for t in SOURCE_TOKENS):
        return "source_candidate"
    if any(t in text for t in MONITOR_TOKENS):
        return "monitor_candidate"
    if any(t in text for t in FDTD_TOKENS):
        return "fdtd_region_candidate"
    if any(t in text for t in MATERIAL_TOKENS):
        return "material_geometry_candidate"
    return "other_or_unknown"


def object_rows_from_names(fdtd: Any, attempts: list[dict[str, Any]], names: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in names:
        name = str(raw).strip()
        if not name or name in seen:
            continue
        seen.add(name)
        props: dict[str, str] = {}
        for prop in PROPS:
            ok, val = call_api(fdtd, attempts, f"getnamed_{name}_{prop}", "getnamed", name, prop)
            if ok:
                props[prop] = safe_str(val)
        obj_type = props.get("type", "")
        cls = classify(name, obj_type, json.dumps(props, ensure_ascii=False))
        rows.append({
            "object_name": name,
            "object_type": obj_type or cls,
            "object_class": cls,
            "parent_or_group": "unknown",
            "units": "Lumerical SI units unless otherwise shown; raw units unknown where not provided",
            "properties_json": json.dumps(props, ensure_ascii=False, sort_keys=True),
        })
    return rows


def names_from_values(values: dict[str, Any]) -> list[str]:
    names: list[str] = []
    for val in values.values():
        names.extend(flatten(val))
    return names


def detect_parameter_support(object_rows: list[dict[str, Any]], raw_log: str) -> dict[str, bool]:
    text = (raw_log + " " + " ".join(json.dumps(r, ensure_ascii=False) for r in object_rows)).lower()
    return {
        "source_dipole_or_mqw": ("dipole" in text or "mqw" in text),
        "plane_wave_only": ("plane wave" in text or "planewave" in text) and not ("dipole" in text or "mqw" in text),
        "blue_450_453": ("453" in text or "450" in text or "4.53e-7" in text or "4.5e-7" in text),
        "sio2_tio2": (("sio2" in text or "si o2" in text) and ("tio2" in text or "ti o2" in text)),
        "thickness_100_52": ("100" in text and "52" in text),
        "m8": ("m=8" in text or "m = 8" in text or "m8" in text),
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    attempts: list[dict[str, Any]] = []
    raw_lines: list[str] = []
    load_rows: list[dict[str, Any]] = []
    object_rows: list[dict[str, Any]] = []

    exists = FSP.exists()
    stat = FSP.stat() if exists else None
    lumapi, lumapi_error = import_lumapi()
    fdtd = None
    load_ok = False
    load_error = ""
    version = ""

    if lumapi is None:
        load_error = lumapi_error
        record_attempt(attempts, "import_lumapi", "python_import", str(LUMAPI_PATH), False, "", lumapi_error)
    elif not exists:
        load_error = "FSP missing"
        record_attempt(attempts, "file_exists", "filesystem", str(FSP), False, "", load_error)
    else:
        try:
            fdtd = lumapi.FDTD(hide=True)
            record_attempt(attempts, "open_fdtd_hide_true", "lumapi_constructor", "lumapi.FDTD(hide=True)", True, "", "")
            fdtd.load(str(FSP))
            load_ok = True
            record_attempt(attempts, "load_fsp", "lumapi_method", f"load({FSP})", True, "", "")
            ok, val = call_api(fdtd, attempts, "version_method", "version")
            if ok:
                version = safe_str(val)
        except Exception as exc:
            load_error = f"{type(exc).__name__}: {exc}"
            record_attempt(attempts, "load_fsp", "lumapi_method", f"load({FSP})", False, "", load_error)

    if fdtd is not None and load_ok:
        # Safe layout/introspection attempts only. No run/runanalysis/mesh/optimize/sweep/save calls appear here.
        eval_script(fdtd, attempts, "switch_to_layout_if_needed", "switchtolayout;")
        scripts = [
            ("script_version", "__h1d_version=version;", ["__h1d_version"]),
            ("script_selectall_names", 'selectall; __h1d_names=get("name");', ["__h1d_names"]),
            ("script_selectall_types", 'selectall; __h1d_types=get("type");', ["__h1d_types"]),
            ("script_getobjectnames", "__h1d_names=getobjectnames;", ["__h1d_names"]),
            ("script_getobjects", "__h1d_names=getobjects;", ["__h1d_names"]),
            ("script_getnumber", "__h1d_number=getnumber;", ["__h1d_number"]),
            ("script_model_selectall", 'groupscope("::model"); selectall; __h1d_names=get("name");', ["__h1d_names"]),
            ("script_material_db", "__h1d_materials=getmaterial;", ["__h1d_materials"]),
        ]
        collected_names: list[str] = []
        for name, script, vars_ in scripts:
            ok, values = eval_script(fdtd, attempts, name, script, vars_)
            raw_lines.append(f"## {name}\ncommand: {script}\nsucceeded: {ok}\nvalues: {safe_str(values)}\n")
            collected_names.extend(names_from_values(values))
        # Try direct dynamic APIs too; unsupported methods are logged and ignored.
        for method in ["getobjects", "getobjectnames", "getchildren"]:
            ok, val = call_api(fdtd, attempts, f"api_{method}", method)
            if ok:
                collected_names.extend(flatten(val))
                raw_lines.append(f"## api_{method}\nsucceeded: true\nvalues: {safe_str(val)}\n")
        object_rows = object_rows_from_names(fdtd, attempts, collected_names)
        try:
            fdtd.close()
        except Exception as exc:
            record_attempt(attempts, "close_fdtd", "lumapi_method", "close()", False, "", f"{type(exc).__name__}: {exc}")

    raw_log = "\n".join(raw_lines)
    support = detect_parameter_support(object_rows, raw_log)
    source_rows = [r for r in object_rows if r["object_class"] == "source_candidate"]
    monitor_rows = [r for r in object_rows if r["object_class"] == "monitor_candidate"]
    fdtd_rows = [r for r in object_rows if r["object_class"] == "fdtd_region_candidate"]
    material_rows = [r for r in object_rows if r["object_class"] == "material_geometry_candidate"]

    if support["plane_wave_only"]:
        baseline_status = "plane_wave_only_not_dipole_baseline"
    elif all([support["source_dipole_or_mqw"], support["blue_450_453"], support["sio2_tio2"], support["thickness_100_52"], support["m8"]]):
        baseline_status = "metadata_supported_primary_baseline"
    elif any(support.values()) or object_rows:
        baseline_status = "partial_metadata_supported_primary_gui_target"
    else:
        baseline_status = "still_requires_manual_gui_screenshot_audit"
    immediate_fdtd_allowed = baseline_status == "metadata_supported_primary_baseline"
    next_stage = "H1E no-run simulation plan" if immediate_fdtd_allowed else "manual GUI screenshot audit"

    load_rows.append({
        "fsp_path": str(FSP),
        "exists": str(exists).lower(),
        "size_bytes": stat.st_size if stat else "",
        "modified_time": dt.datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds") if stat else "",
        "lumapi_available": str(lumapi is not None).lower(),
        "load_succeeded": str(load_ok).lower(),
        "load_error": load_error,
        "lumerical_version": version,
        "baseline_status": baseline_status,
    })

    write_csv(OUT / "r2_4h1d_fsp_load_status.csv", load_rows, [
        "fsp_path", "exists", "size_bytes", "modified_time", "lumapi_available", "load_succeeded", "load_error", "lumerical_version", "baseline_status",
    ])
    write_csv(OUT / "r2_4h1d_lumerical_command_attempts.csv", attempts, [
        "attempt_name", "category", "command_or_api", "succeeded", "result_preview", "error",
    ])
    (OUT / "r2_4h1d_raw_introspection_log.txt").write_text(raw_log + "\n", encoding="utf-8")
    write_csv(OUT / "r2_4h1d_object_tree.csv", object_rows, [
        "object_name", "object_type", "object_class", "parent_or_group", "units", "properties_json",
    ])
    write_csv(OUT / "r2_4h1d_source_candidates.csv", source_rows, [
        "object_name", "object_type", "object_class", "parent_or_group", "units", "properties_json",
    ])
    write_csv(OUT / "r2_4h1d_monitor_candidates.csv", monitor_rows, [
        "object_name", "object_type", "object_class", "parent_or_group", "units", "properties_json",
    ])
    write_csv(OUT / "r2_4h1d_fdtd_region_candidates.csv", fdtd_rows, [
        "object_name", "object_type", "object_class", "parent_or_group", "units", "properties_json",
    ])
    write_csv(OUT / "r2_4h1d_material_geometry_candidates.csv", material_rows, [
        "object_name", "object_type", "object_class", "parent_or_group", "units", "properties_json",
    ])
    parameter_rows = [{
        "check": "source_dipole_or_mqw", "confirmed": str(support["source_dipole_or_mqw"]).lower(), "evidence": "object/raw introspection text token scan",
    }, {
        "check": "plane_wave_only", "confirmed": str(support["plane_wave_only"]).lower(), "evidence": "object/raw introspection text token scan",
    }, {
        "check": "blue_450_453", "confirmed": str(support["blue_450_453"]).lower(), "evidence": "object/raw introspection text token scan",
    }, {
        "check": "sio2_tio2", "confirmed": str(support["sio2_tio2"]).lower(), "evidence": "object/raw introspection text token scan",
    }, {
        "check": "thickness_100_52", "confirmed": str(support["thickness_100_52"]).lower(), "evidence": "object/raw introspection text token scan",
    }, {
        "check": "m8", "confirmed": str(support["m8"]).lower(), "evidence": "object/raw introspection text token scan",
    }]
    write_csv(OUT / "r2_4h1d_wan_mdc_parameter_check.csv", parameter_rows, ["check", "confirmed", "evidence"])

    succeeded = [r["attempt_name"] for r in attempts if r["succeeded"] == "true"]
    failed = [r["attempt_name"] for r in attempts if r["succeeded"] == "false"]
    object_tree_extracted = bool(object_rows)
    summary = f"""
# R2-4H1D Lumerical Internal No-run FSP Audit

Target FSP: `{FSP}`

Load succeeded: `{load_ok}`
Lumerical version: `{version or 'unavailable'}`
Object tree extracted: `{object_tree_extracted}`
Source type confirmed: `{support['source_dipole_or_mqw'] or support['plane_wave_only']}`
SiO2/TiO2 confirmed: `{support['sio2_tio2']}`
450/453 nm confirmed: `{support['blue_450_453']}`
100/52 nm confirmed: `{support['thickness_100_52']}`
m about 8 confirmed: `{support['m8']}`

Baseline status: `{baseline_status}`
Immediate FDTD allowed: `{str(immediate_fdtd_allowed).lower()}`
Next stage: `{next_stage}`

Command attempts:
- Succeeded: {len(succeeded)}
- Failed/unsupported: {len(failed)}

H1D did not run, mesh, analyze, optimize, sweep, save, or copy the original FSP.
"""
    write_md(OUT / "r2_4h1d_summary.md", summary)
    decision = summary + """

## Conservative Freeze Decision

Do not freeze an executable simulation baseline from H1D unless the GUI confirms source type, source wavelength, monitor layout, FDTD boundaries, and SiO2/TiO2 stack details. H1D metadata alone is not optical validation.
"""
    write_md(OUT / "r2_4h1d_baseline_freeze_decision.md", decision)
    manual_update = "" if baseline_status != "still_requires_manual_gui_screenshot_audit" else """

Because H1D still cannot confirm object/source/material metadata, the human GUI audit must capture:
- full object tree
- source object property panel
- source type and orientation
- source wavelength/frequency settings
- monitor list and far-field settings
- FDTD span/boundaries/mesh
- all material/layer names
- z-stack order and thickness estimates
- SiO2/TiO2 and m/pair-count evidence
"""
    next_md = f"""
# R2-4H1D Next Stage Recommendation

Recommended next stage: `{next_stage}`

If H1D status is `still_requires_manual_gui_screenshot_audit`, do manual GUI screenshot review first. If all metadata checks pass later, prepare H1E as a no-run simulation plan. Do not proceed directly to FDTD from H1D.
{manual_update}
"""
    write_md(OUT / "r2_4h1d_next_stage_recommendation.md", next_md)
    stop_allow = """
# R2-4H1D Stop / Allow Rules

Stop:
- Do not run FDTD from H1D.
- Do not call run, runanalysis, mesh, optimize, sweep, or save.
- Do not submit FSP/LDF/MAT/H5 or screenshots/heavy binaries.
- Do not claim optical success from metadata.

Allow:
- Manual GUI screenshot audit if metadata remains incomplete.
- H1E no-run simulation plan only after metadata checks pass.
- Commit lightweight script, CSV, JSON, TXT, and Markdown reports.
"""
    write_md(OUT / "r2_4h1d_stop_allow_rules.md", stop_allow)
    manifest = {
        "stage": "R2-4H1D Lumerical internal no-run FSP audit",
        "created_at": dt.datetime.now().isoformat(timespec="seconds"),
        "target_fsp": str(FSP),
        "exists": exists,
        "load_succeeded": load_ok,
        "lumerical_version": version,
        "no_fdtd_run": True,
        "no_runanalysis": True,
        "no_mesh": True,
        "no_save": True,
        "object_tree_extracted": object_tree_extracted,
        "source_type_confirmed": bool(support["source_dipole_or_mqw"] or support["plane_wave_only"]),
        "sio2_tio2_confirmed": support["sio2_tio2"],
        "blue_450_453_confirmed": support["blue_450_453"],
        "thickness_100_52_confirmed": support["thickness_100_52"],
        "m8_confirmed": support["m8"],
        "baseline_status": baseline_status,
        "immediate_fdtd_allowed": immediate_fdtd_allowed,
        "command_success_count": len(succeeded),
        "command_failure_count": len(failed),
        "outputs": [p.name for p in OUT.iterdir() if p.is_file()],
    }
    (OUT / "r2_4h1d_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(OUT),
        "load_succeeded": load_ok,
        "object_tree_extracted": object_tree_extracted,
        "support": support,
        "baseline_status": baseline_status,
        "immediate_fdtd_allowed": immediate_fdtd_allowed,
        "command_success_count": len(succeeded),
        "command_failure_count": len(failed),
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
