from __future__ import annotations

import csv
import datetime as dt
import importlib.util
import json
import os
from pathlib import Path
from typing import Any

ROOT = Path(r"D:\project\worktrees\blue_apcd_rcled_mdc")
OUT = ROOT / "outputs" / "r2_4h1b_readonly_fsp_audit_existing_wan_mdc"
LUMAPI_PATH = Path(r"N:\Program Files\ANSYS Inc\v251\Lumerical\api\python\lumapi.py")
FSP_FILES = [
    Path(r"F:\wc_312\MDC_blue_oujizi.fsp"),
    Path(r"F:\wc_312\MDC_blue_qujizi.fsp"),
]

TARGET_PROPS = [
    "name", "type", "x", "y", "z", "x span", "y span", "z span", "material",
    "index", "monitor type", "source type", "injection axis", "direction",
    "wavelength", "wavelength start", "wavelength stop", "center wavelength",
    "frequency points", "theta", "phi", "polarization angle", "amplitude",
    "mesh accuracy", "x min bc", "x max bc", "y min bc", "y max bc", "z min bc", "z max bc",
]
MATERIAL_HINTS = ["sio2", "si o2", "tio2", "ti o2", "gan", "ito", "air", "substrate", "mdc", "dbr"]
SOURCE_HINTS = ["source", "dipole", "mqw", "plane", "gaussian", "mode"]
MONITOR_HINTS = ["monitor", "power", "field", "far", "frequency", "profile"]


def now_iso() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


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


def file_meta(path: Path) -> dict[str, Any]:
    exists = path.exists()
    stat = path.stat() if exists else None
    return {
        "file_path": str(path),
        "exists": exists,
        "size_bytes": stat.st_size if stat else "",
        "modified_time": dt.datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds") if stat else "",
        "load_succeeded": False,
        "load_error": "not attempted" if exists else "missing file",
        "lumerical_version": "",
    }


def import_lumapi() -> tuple[Any | None, str]:
    if not LUMAPI_PATH.exists():
        return None, f"lumapi.py missing: {LUMAPI_PATH}"
    try:
        spec = importlib.util.spec_from_file_location("lumapi", str(LUMAPI_PATH))
        if spec is None or spec.loader is None:
            return None, "could not create lumapi import spec"
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)  # type: ignore[union-attr]
        return module, ""
    except Exception as exc:
        return None, f"lumapi import failed: {type(exc).__name__}: {exc}"


def flatten_names(value: Any) -> list[str]:
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
            out.extend(flatten_names(item))
        return [x for x in out if x]
    return [str(value)]


def call(obj: Any, method: str, *args: Any) -> tuple[bool, Any, str]:
    try:
        return True, getattr(obj, method)(*args), ""
    except Exception as exc:
        return False, None, f"{method} failed: {type(exc).__name__}: {exc}"


def get_version(fdtd: Any) -> str:
    for method in ("version", "getversion"):
        ok, val, _ = call(fdtd, method)
        if ok:
            return safe_str(val)
    ok, _, _ = call(fdtd, "eval", "__h1b_version = version;")
    if ok:
        ok2, val, _ = call(fdtd, "getv", "__h1b_version")
        if ok2:
            return safe_str(val)
    return "unavailable"


def get_names_in_scope(fdtd: Any, scope: str | None = None) -> tuple[list[str], str]:
    errors: list[str] = []
    if scope:
        ok, _, err = call(fdtd, "groupscope", scope)
        if not ok:
            errors.append(err)
    for method in ("getobjects", "getchildren"):
        ok, val, err = call(fdtd, method)
        if ok:
            names = flatten_names(val)
            if names:
                return names, ""
        else:
            errors.append(err)
    # Last attempt through script variable. This is still read-only introspection.
    ok, _, err = call(fdtd, "eval", "__h1b_objs = getobjects;")
    if ok:
        ok2, val, err2 = call(fdtd, "getv", "__h1b_objs")
        if ok2:
            names = flatten_names(val)
            if names:
                return names, ""
        else:
            errors.append(err2)
    else:
        errors.append(err)
    return [], "; ".join(errors[:4])


def get_props(fdtd: Any, name: str) -> tuple[dict[str, str], list[str], str]:
    props: dict[str, str] = {}
    readable_props: list[str] = []
    prop_err = ""
    ok, val, err = call(fdtd, "getnamedproperties", name)
    if ok:
        readable_props = flatten_names(val)
    else:
        prop_err = err
    candidates = list(dict.fromkeys(TARGET_PROPS + readable_props[:80]))
    for prop in candidates:
        okp, valp, _ = call(fdtd, "getnamed", name, prop)
        if okp:
            props[prop] = safe_str(valp)
    return props, readable_props, prop_err


def classify_name(name: str, props: dict[str, str]) -> str:
    text = (name + " " + " ".join(f"{k} {v}" for k, v in props.items())).lower()
    if "fdtd" in text:
        return "fdtd_region_or_simulation"
    if any(h in text for h in SOURCE_HINTS):
        return "source_like"
    if any(h in text for h in MONITOR_HINTS):
        return "monitor_like"
    if any(h in text for h in MATERIAL_HINTS):
        return "material_or_layer_like"
    return "other_or_unknown"


def z_thickness_nm(props: dict[str, str]) -> str:
    raw = props.get("z span") or props.get("y span") or ""
    try:
        return f"{float(raw) * 1e9:.3f}"
    except Exception:
        return ""


def material_hit_text(name: str, props: dict[str, str]) -> str:
    text = (name + " " + " ".join(props.values())).lower()
    hits = [h for h in MATERIAL_HINTS if h in text]
    return ";".join(sorted(set(hits)))


def inspect_file(path: Path, lumapi: Any | None) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    meta = file_meta(path)
    object_rows: list[dict[str, Any]] = []
    source_monitor_rows: list[dict[str, Any]] = []
    material_rows: list[dict[str, Any]] = []
    if not path.exists() or lumapi is None:
        if lumapi is None and path.exists():
            meta["load_error"] = "lumapi unavailable"
        return meta, object_rows, source_monitor_rows, material_rows

    fdtd = None
    try:
        # Hide keeps this an introspection task; no run/mesh/save methods are called anywhere in this script.
        fdtd = lumapi.FDTD(hide=True)
        fdtd.load(str(path))
        meta["load_succeeded"] = True
        meta["load_error"] = ""
        meta["lumerical_version"] = get_version(fdtd)
        names, names_err = get_names_in_scope(fdtd)
        if not names:
            object_rows.append({
                "file_path": str(path), "object_name": "", "object_type_or_class": "object_tree_unavailable",
                "parent_or_group": "", "property_count": 0, "read_error": names_err, "properties_json": "{}",
            })
            return meta, object_rows, source_monitor_rows, material_rows
        seen: set[str] = set()
        queue: list[tuple[str, str]] = [(n, "::model") for n in names]
        while queue and len(seen) < 2000:
            name, parent = queue.pop(0)
            if name in seen:
                continue
            seen.add(name)
            props, readable_props, prop_err = get_props(fdtd, name)
            cls = classify_name(name, props)
            obj_type = props.get("type") or props.get("source type") or props.get("monitor type") or cls
            object_rows.append({
                "file_path": str(path),
                "object_name": name,
                "object_type_or_class": obj_type,
                "parent_or_group": parent,
                "property_count": len(readable_props),
                "read_error": prop_err,
                "properties_json": json.dumps(props, ensure_ascii=False, sort_keys=True),
            })
            if cls in {"source_like", "monitor_like", "fdtd_region_or_simulation"}:
                source_monitor_rows.append({
                    "file_path": str(path), "name": name, "class": cls, "type": obj_type,
                    "x": props.get("x", ""), "y": props.get("y", ""), "z": props.get("z", ""),
                    "x_span": props.get("x span", ""), "y_span": props.get("y span", ""), "z_span": props.get("z span", ""),
                    "wavelength_start": props.get("wavelength start", ""), "wavelength_stop": props.get("wavelength stop", ""),
                    "wavelength": props.get("wavelength", "") or props.get("center wavelength", ""),
                    "theta": props.get("theta", ""), "phi": props.get("phi", ""),
                    "polarization_angle": props.get("polarization angle", ""),
                    "boundary_or_mesh": "; ".join(f"{k}={props[k]}" for k in props if k.endswith("bc") or k == "mesh accuracy"),
                })
            hits = material_hit_text(name, props)
            if hits or props.get("material"):
                material_rows.append({
                    "file_path": str(path), "name": name, "class": cls, "material": props.get("material", ""),
                    "material_name_hits": hits, "x_span": props.get("x span", ""), "y_span": props.get("y span", ""),
                    "z_span": props.get("z span", ""), "estimated_thickness_nm_from_span": z_thickness_nm(props),
                    "x": props.get("x", ""), "y": props.get("y", ""), "z": props.get("z", ""),
                })
            # Optional one-level group introspection. Failure is harmless.
            if "group" in str(obj_type).lower() or "group" in name.lower():
                child_scope = name if name.startswith("::") else f"::model::{name}"
                child_names, _ = get_names_in_scope(fdtd, child_scope)
                for child in child_names:
                    if child not in seen:
                        queue.append((child, child_scope))
    except Exception as exc:
        meta["load_succeeded"] = False
        meta["load_error"] = f"{type(exc).__name__}: {exc}"
    finally:
        if fdtd is not None:
            try:
                fdtd.close()
            except Exception:
                pass
    return meta, object_rows, source_monitor_rows, material_rows


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def infer_candidate(meta: dict[str, Any], objects: list[dict[str, Any]], sm: list[dict[str, Any]], mat: list[dict[str, Any]]) -> dict[str, Any]:
    path = meta["file_path"]
    all_text = " ".join([
        path,
        " ".join(str(r.get("object_name", "")) for r in objects),
        " ".join(str(r.get("name", "")) for r in sm),
        " ".join(str(r.get("material", "")) + " " + str(r.get("material_name_hits", "")) for r in mat),
    ]).lower()
    source_text = " ".join(str(r.get("name", "")) + " " + str(r.get("type", "")) for r in sm if r.get("class") == "source_like").lower()
    blue_score = int("blue" in all_text) + int("453" in all_text) + int("0.453" in all_text) + int("4.53e-07" in all_text)
    dbr_score = int("sio2" in all_text or "si o2" in all_text) + int("tio2" in all_text or "ti o2" in all_text)
    dipole_like = any(w in source_text for w in ["dipole", "mqw"])
    plane_like = "plane" in source_text
    if dipole_like:
        source_kind = "dipole_or_mqw_like"
    elif plane_like:
        source_kind = "plane_wave_like"
    elif source_text:
        source_kind = "source_present_ambiguous"
    else:
        source_kind = "no_source_detected_or_unavailable"
    thickness_text = " ".join(str(r.get("estimated_thickness_nm_from_span", "")) for r in mat)
    wan_thickness_hint = any(s in thickness_text for s in ["100", "52", "99", "51"])
    confidence_score = int(bool(meta.get("load_succeeded"))) * 2 + int(dipole_like) * 3 + blue_score + dbr_score + int(wan_thickness_hint)
    if confidence_score >= 7:
        suitability = "strong_metadata_candidate"
    elif confidence_score >= 4:
        suitability = "partial_metadata_candidate"
    else:
        suitability = "ambiguous_or_failed_metadata"
    return {
        "file_path": path,
        "exists": meta.get("exists"),
        "load_succeeded": meta.get("load_succeeded"),
        "source_kind": source_kind,
        "object_count": len([r for r in objects if r.get("object_name")]),
        "source_monitor_count": len(sm),
        "material_geometry_count": len(mat),
        "blue_453_hint_score": blue_score,
        "sio2_tio2_hint_score": dbr_score,
        "wan_100_52_nm_hint": wan_thickness_hint,
        "suitability": suitability,
        "confidence_score": confidence_score,
        "load_error": meta.get("load_error", ""),
    }


def write_md(path: Path, text: str) -> None:
    path.write_text(text.strip() + "\n", encoding="utf-8")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    lumapi, lumapi_error = import_lumapi()
    file_rows: list[dict[str, Any]] = []
    object_rows: list[dict[str, Any]] = []
    source_monitor_rows: list[dict[str, Any]] = []
    material_rows: list[dict[str, Any]] = []
    compare_rows: list[dict[str, Any]] = []

    by_file: dict[str, tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]] = {}
    for fsp in FSP_FILES:
        meta, objs, sms, mats = inspect_file(fsp, lumapi)
        if lumapi is None and meta.get("exists"):
            meta["load_error"] = lumapi_error
        file_rows.append(meta)
        object_rows.extend(objs)
        source_monitor_rows.extend(sms)
        material_rows.extend(mats)
        by_file[str(fsp)] = (meta, objs, sms, mats)
        compare_rows.append(infer_candidate(meta, objs, sms, mats))

    write_csv(OUT / "r2_4h1b_fsp_file_metadata.csv", file_rows, [
        "file_path", "exists", "size_bytes", "modified_time", "load_succeeded", "load_error", "lumerical_version",
    ])
    write_csv(OUT / "r2_4h1b_object_tree.csv", object_rows, [
        "file_path", "object_name", "object_type_or_class", "parent_or_group", "property_count", "read_error", "properties_json",
    ])
    write_csv(OUT / "r2_4h1b_source_monitor_summary.csv", source_monitor_rows, [
        "file_path", "name", "class", "type", "x", "y", "z", "x_span", "y_span", "z_span",
        "wavelength_start", "wavelength_stop", "wavelength", "theta", "phi", "polarization_angle", "boundary_or_mesh",
    ])
    write_csv(OUT / "r2_4h1b_material_geometry_summary.csv", material_rows, [
        "file_path", "name", "class", "material", "material_name_hits", "x_span", "y_span", "z_span",
        "estimated_thickness_nm_from_span", "x", "y", "z",
    ])
    write_csv(OUT / "r2_4h1b_candidate_compare.csv", compare_rows, [
        "file_path", "exists", "load_succeeded", "source_kind", "object_count", "source_monitor_count",
        "material_geometry_count", "blue_453_hint_score", "sio2_tio2_hint_score", "wan_100_52_nm_hint",
        "suitability", "confidence_score", "load_error",
    ])

    loaded = [r for r in compare_rows if str(r.get("load_succeeded")) == "True"]
    oujizi = next((r for r in compare_rows if "oujizi" in str(r.get("file_path", "")).lower()), None)
    qujizi = next((r for r in compare_rows if "qujizi" in str(r.get("file_path", "")).lower()), None)
    decision = "ambiguous_require_manual_gui_audit"
    recommended = "none"
    reason = "Metadata did not clearly prove a blue dipole/MQW-like MDC baseline."
    if oujizi and oujizi.get("suitability") == "strong_metadata_candidate" and "dipole" in str(oujizi.get("source_kind")):
        decision = "recommend_oujizi_for_baseline_audit_target"
        recommended = str(oujizi["file_path"])
        reason = "Oujizi loaded and metadata indicates a dipole/MQW-like blue MDC candidate."
    elif qujizi and qujizi.get("suitability") == "strong_metadata_candidate" and "dipole" in str(qujizi.get("source_kind")):
        decision = "recommend_qujizi_for_baseline_audit_target"
        recommended = str(qujizi["file_path"])
        reason = "Qujizi loaded and is more consistent than oujizi by metadata."
    elif oujizi and str(oujizi.get("exists")) == "True":
        recommended = str(oujizi["file_path"])
        reason = "Oujizi remains the conservative audit target from H1A, but H1B metadata is incomplete or ambiguous."

    immediate_fdtd_allowed = False
    summary = f"""
# R2-4H1B Read-only FSP Audit Existing Wan MDC

H1A found both MDC_blue_qujizi / MDC_blue_oujizi naming evidence under `F:\\wc_312` and recommended `F:\\wc_312\\MDC_blue_oujizi.fsp` as the high-confidence file-name baseline candidate.

H1B attempted read-only Lumerical metadata audit only. It did not call run, runanalysis, mesh, optimize, sweep, save, or copy FSP files into the git worktree.

Lumapi import status: `{('ok' if lumapi is not None else lumapi_error)}`

Files audited:

"""
    for row in compare_rows:
        summary += f"- `{row['file_path']}`: exists={row['exists']}, load_succeeded={row['load_succeeded']}, source_kind={row['source_kind']}, suitability={row['suitability']}\n"
    summary += f"""

Freeze decision: `{decision}`
Recommended audit target: `{recommended}`
Reason: {reason}

Immediate FDTD allowed: `{str(immediate_fdtd_allowed).lower()}`

What remains unknown before FDTD:
- Whether the loaded geometry visually matches the intended Wan blue MDC baseline.
- Whether source orientation and monitor placement are physically correct for the next RCLED-MDC stage.
- Whether layer thickness/order are exactly the thesis/Wan baseline if metadata extraction was incomplete.
- Optical performance remains unknown because H1B did not run or analyze simulation results.
"""
    write_md(OUT / "r2_4h1b_summary.md", summary)
    write_md(OUT / "r2_4h1b_baseline_freeze_decision.md", summary + "\n## Conservative stop/allow rules\n\n- Stop: do not run immediate FDTD from H1B alone.\n- Allow: manual GUI screenshot audit of the recommended target.\n- Allow: write a future setup-only plan if GUI audit confirms source, monitor, layer stack, and wavelength.\n- Never: overwrite or save original `F:\\wc_312` FSP files.\n")
    write_md(OUT / "r2_4h1b_manual_gui_audit_checklist.md", """
# R2-4H1B Manual GUI Audit Checklist

Use only if metadata is incomplete or to verify the freeze target before any FDTD planning.

- Open the original FSP read-only or via a disposable copy outside git.
- Confirm top MDC/DBR layer order and material names.
- Confirm SiO2 thickness near 100 nm and TiO2 thickness near 52 nm if present.
- Confirm pair count near m=8 if present.
- Confirm blue / 453 nm source or sweep settings.
- Confirm whether source is dipole/MQW-like or plane-wave-like.
- Confirm source orientation and position.
- Confirm monitor names, positions, and far-field monitor suitability.
- Confirm FDTD region, boundary conditions, and mesh settings.
- Do not run, mesh, runanalysis, sweep, optimize, or save over original files.
""")
    manifest = {
        "stage": "R2-4H1B read-only FSP audit existing Wan MDC",
        "created_at": now_iso(),
        "python_script": str(ROOT / "scripts" / "stage_r2_4h1b_readonly_fsp_audit_existing_wan_mdc.py"),
        "output_dir": str(OUT),
        "python_only": False,
        "read_only_lumerical_metadata": True,
        "no_fdtd_run": True,
        "no_runanalysis": True,
        "no_save_original_fsp": True,
        "lumapi_available": lumapi is not None,
        "lumapi_error": lumapi_error,
        "files": file_rows,
        "candidate_compare": compare_rows,
        "decision": decision,
        "recommended_baseline_audit_target": recommended,
        "immediate_fdtd_allowed": immediate_fdtd_allowed,
    }
    (OUT / "r2_4h1b_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(OUT),
        "lumapi_available": lumapi is not None,
        "file_results": [{"file": r["file_path"], "exists": r["exists"], "load_succeeded": r["load_succeeded"], "load_error": r["load_error"]} for r in file_rows],
        "decision": decision,
        "recommended": recommended,
        "immediate_fdtd_allowed": immediate_fdtd_allowed,
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
