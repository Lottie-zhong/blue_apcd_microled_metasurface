from __future__ import annotations

import csv
import datetime as dt
import json
import os
import re
from pathlib import Path
from typing import Any

ROOT = Path(r"D:\project\worktrees\blue_apcd_rcled_mdc")
SOURCE = Path(r"F:\wc_312")
OUT = ROOT / "outputs" / "r2_4h1c_wan_mdc_path_resolution_and_gui_audit_pack"
SCREENSHOT_DIR = OUT / "manual_gui_screenshots_DO_NOT_COMMIT"
H1A_DIR = ROOT / "outputs" / "r2_4h1a_inventory_existing_wan_mdc_server_files"
H1B_DIR = ROOT / "outputs" / "r2_4h1b_readonly_fsp_audit_existing_wan_mdc"

TOKENS = ["mdc", "blue", "qujizi", "oujizi", "source", "dipole", "453", "450"]
SPECIFIC_PATTERNS = [
    "mdc_blue_oujizi",
    "mdc_blue_qujizi",
    "mdc_blue_",
    "blue_oujizi",
    "blue_qujizi",
]
HEAVY_EXTS = {".fsp", ".fspx", ".ldf", ".mat", ".h5"}
TEXT_EXTS = {".txt", ".md", ".csv", ".json", ".lsf", ".log", ".ini", ".xml"}
SEARCH_TERMS = [
    "SiO2", "sio2", "TiO2", "tio2", "GaN", "ITO", "MDC", "DBR",
    "453", "450", "100", "52", "m=8", "m = 8", "dipole", "source",
    "qujizi", "oujizi", "plane wave", "planewave",
]
MAX_TEXT_BYTES = 131072


def now_iso() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


def norm(s: str) -> str:
    return s.lower().replace("\\", "/")


def safe_rel(path: Path) -> str:
    try:
        return str(path.relative_to(SOURCE))
    except Exception:
        return str(path)


def file_time(path: Path) -> str:
    try:
        return dt.datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds")
    except Exception:
        return ""


def file_size(path: Path) -> str:
    try:
        return str(path.stat().st_size)
    except Exception:
        return ""


def read_csv_if_exists(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            return list(csv.DictReader(f))
    except Exception:
        return []


def scan_paths() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not SOURCE.exists():
        return rows
    for dirpath, dirnames, filenames in os.walk(SOURCE):
        base = Path(dirpath)
        entries = [(base / d, True) for d in dirnames] + [(base / f, False) for f in filenames]
        for path, is_dir in entries:
            text = norm(str(path))
            name_text = norm(path.name)
            token_hits = [t for t in TOKENS if t in text]
            pattern_hits = [p for p in SPECIFIC_PATTERNS if p in text]
            if not token_hits and not pattern_hits:
                continue
            ext = "" if is_dir else path.suffix.lower()
            rows.append({
                "path": str(path),
                "relative_path": safe_rel(path),
                "name": path.name,
                "is_directory": str(is_dir).lower(),
                "extension": ext or "none",
                "is_heavy": str(ext in HEAVY_EXTS).lower(),
                "is_text_like": str(ext in TEXT_EXTS).lower(),
                "size_bytes": "" if is_dir else file_size(path),
                "modified_time": file_time(path),
                "token_hits": ";".join(token_hits),
                "specific_pattern_hits": ";".join(pattern_hits),
                "exact_mdc_blue_oujizi": str("mdc_blue_oujizi" in name_text).lower(),
                "exact_mdc_blue_qujizi": str("mdc_blue_qujizi" in name_text).lower(),
                "candidate_role_hint": role_hint(path, is_dir, token_hits, pattern_hits),
            })
    rows.sort(key=lambda r: (role_sort(r), str(r["path"]).lower()))
    return rows


def role_hint(path: Path, is_dir: bool, token_hits: list[str], pattern_hits: list[str]) -> str:
    text = norm(str(path))
    ext = "" if is_dir else path.suffix.lower()
    if "mdc_blue_oujizi" in text and ext == ".fsp":
        return "primary_exact_oujizi_fsp"
    if "mdc_blue_qujizi" in text and ext == ".fsp":
        return "exact_qujizi_fsp_candidate"
    if "mdc_blue_oujizi" in text:
        return "oujizi_related"
    if "mdc_blue_qujizi" in text:
        return "qujizi_related"
    if "blue" in token_hits and ("qujizi" in token_hits or "oujizi" in token_hits):
        return "blue_qujizi_oujizi_related"
    if "source" in token_hits or "dipole" in token_hits:
        return "source_or_dipole_related"
    return "matched_token_inventory"


def role_sort(row: dict[str, Any]) -> int:
    order = {
        "primary_exact_oujizi_fsp": 0,
        "exact_qujizi_fsp_candidate": 1,
        "oujizi_related": 2,
        "qujizi_related": 3,
        "blue_qujizi_oujizi_related": 4,
        "source_or_dipole_related": 5,
    }
    return order.get(str(row.get("candidate_role_hint", "")), 9)


def text_hits(path_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in path_rows:
        if row.get("is_text_like") != "true" or row.get("is_directory") == "true":
            continue
        path = Path(str(row["path"]))
        try:
            data = path.read_bytes()[:MAX_TEXT_BYTES]
        except Exception as exc:
            rows.append({
                "path": str(path),
                "read_status": f"read_failed: {type(exc).__name__}: {exc}",
                "terms_hit": "",
                "line_numbers": "",
                "evidence_snippets": "",
                "supports_sio2_tio2": "false",
                "supports_453_or_450": "false",
                "supports_100_52_nm": "false",
                "supports_m8": "false",
                "supports_dipole_source": "false",
                "supports_planewave": "false",
            })
            continue
        text = data.decode("utf-8", errors="replace")
        terms: list[str] = []
        line_numbers: list[str] = []
        snippets: list[str] = []
        lines = text.splitlines()
        for idx, line in enumerate(lines[:500], start=1):
            lower = line.lower()
            hit_terms = [term for term in SEARCH_TERMS if term.lower() in lower]
            if hit_terms:
                terms.extend(hit_terms)
                line_numbers.append(str(idx))
                snippets.append(f"L{idx}: {line.strip()[:180]}")
            if len(snippets) >= 12:
                break
        terms_unique = sorted(set(terms), key=lambda x: x.lower())
        lower_all = text.lower()
        supports_sio2_tio2 = ("sio2" in lower_all or "si o2" in lower_all) and ("tio2" in lower_all or "ti o2" in lower_all)
        supports_453_or_450 = "453" in lower_all or "450" in lower_all
        supports_100_52 = ("100" in lower_all and "52" in lower_all)
        supports_m8 = bool(re.search(r"\bm\s*=\s*8\b", lower_all)) or "m8" in lower_all
        supports_dipole = "dipole" in lower_all or "mqw" in lower_all
        supports_planewave = "plane wave" in lower_all or "planewave" in lower_all
        rows.append({
            "path": str(path),
            "read_status": "ok",
            "terms_hit": ";".join(terms_unique),
            "line_numbers": ";".join(line_numbers),
            "evidence_snippets": " | ".join(snippets),
            "supports_sio2_tio2": str(supports_sio2_tio2).lower(),
            "supports_453_or_450": str(supports_453_or_450).lower(),
            "supports_100_52_nm": str(supports_100_52).lower(),
            "supports_m8": str(supports_m8).lower(),
            "supports_dipole_source": str(supports_dipole).lower(),
            "supports_planewave": str(supports_planewave).lower(),
        })
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_md(path: Path, text: str) -> None:
    path.write_text(text.strip() + "\n", encoding="utf-8")


def any_true(rows: list[dict[str, Any]], key: str) -> bool:
    return any(str(r.get(key, "")).lower() == "true" for r in rows)


def load_h1b_status() -> dict[str, str]:
    rows = read_csv_if_exists(H1B_DIR / "r2_4h1b_fsp_file_metadata.csv")
    out: dict[str, str] = {}
    for r in rows:
        out[str(r.get("file_path", ""))] = str(r.get("load_succeeded", ""))
    return out


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    (SCREENSHOT_DIR / ".gitignore").write_text("""
*.png
*.jpg
*.jpeg
*.bmp
*.tif
*.tiff
*.gif
*.mp4
*.avi
*.fsp
*.ldf
*.mat
*.h5
""".strip() + "\n", encoding="utf-8")

    path_rows = scan_paths()
    hit_rows = text_hits(path_rows)
    h1b_load = load_h1b_status()

    exact_oujizi = [r for r in path_rows if str(r.get("path", "")).lower() == r"f:\wc_312\mdc_blue_oujizi.fsp"]
    exact_qujizi_fsp = [r for r in path_rows if "mdc_blue_qujizi" in str(r.get("path", "")).lower() and str(r.get("extension")) == ".fsp"]
    oujizi_any = [r for r in path_rows if "mdc_blue_oujizi" in str(r.get("path", "")).lower()]
    qujizi_any = [r for r in path_rows if "mdc_blue_qujizi" in str(r.get("path", "")).lower()]

    text_support = {
        "sio2_tio2": any_true(hit_rows, "supports_sio2_tio2"),
        "453_or_450": any_true(hit_rows, "supports_453_or_450"),
        "100_52_nm": any_true(hit_rows, "supports_100_52_nm"),
        "m8": any_true(hit_rows, "supports_m8"),
        "dipole_source": any_true(hit_rows, "supports_dipole_source"),
        "planewave": any_true(hit_rows, "supports_planewave"),
    }
    primary_target = r"F:\wc_312\MDC_blue_oujizi.fsp" if exact_oujizi else "none"
    exact_qujizi_found = bool(exact_qujizi_fsp)
    competing = "; ".join(str(r["path"]) for r in exact_qujizi_fsp) if exact_qujizi_fsp else "none"

    write_csv(OUT / "r2_4h1c_candidate_path_resolution.csv", path_rows, [
        "path", "relative_path", "name", "is_directory", "extension", "is_heavy", "is_text_like",
        "size_bytes", "modified_time", "token_hits", "specific_pattern_hits", "exact_mdc_blue_oujizi",
        "exact_mdc_blue_qujizi", "candidate_role_hint",
    ])
    write_csv(OUT / "r2_4h1c_lightweight_text_parameter_hits.csv", hit_rows, [
        "path", "read_status", "terms_hit", "line_numbers", "evidence_snippets", "supports_sio2_tio2",
        "supports_453_or_450", "supports_100_52_nm", "supports_m8", "supports_dipole_source", "supports_planewave",
    ])
    form_rows = [
        {"audit_item": "full_object_tree_screenshot", "required": "yes", "operator_entry": "", "notes": "Capture whole tree without running simulation."},
        {"audit_item": "source_object_name_type", "required": "yes", "operator_entry": "", "notes": "dipole / plane wave / other."},
        {"audit_item": "source_position_orientation", "required": "yes", "operator_entry": "", "notes": "Record x/y/z and theta/phi or equivalent."},
        {"audit_item": "source_wavelength_frequency", "required": "yes", "operator_entry": "", "notes": "Confirm blue 453 nm or ambiguity."},
        {"audit_item": "monitor_list_farfield_settings", "required": "yes", "operator_entry": "", "notes": "Record monitor names and spans."},
        {"audit_item": "fdtd_region_boundaries_span", "required": "yes", "operator_entry": "", "notes": "Record span/boundary/mesh."},
        {"audit_item": "material_layer_stack_names", "required": "yes", "operator_entry": "", "notes": "Look for SiO2/TiO2/GaN/ITO/air/substrate."},
        {"audit_item": "z_stack_order_thickness", "required": "yes", "operator_entry": "", "notes": "Approximate layer order and thickness."},
        {"audit_item": "sio2_tio2_present", "required": "yes", "operator_entry": "", "notes": "yes/no/ambiguous."},
        {"audit_item": "m8_or_pair_count_visible", "required": "yes", "operator_entry": "", "notes": "Record visible pair count if available."},
        {"audit_item": "mqw_dipole_or_planewave_like", "required": "yes", "operator_entry": "", "notes": "Classify baseline usage."},
        {"audit_item": "safe_for_tri_point_xdipole_453_later", "required": "yes", "operator_entry": "", "notes": "Planning only; do not run."},
    ]
    write_csv(OUT / "r2_4h1c_manual_gui_audit_form.csv", form_rows, ["audit_item", "required", "operator_entry", "notes"])

    exact_report = f"""
# R2-4H1C Exact Path Report

Checked source folder: `{SOURCE}`

- Exact oujizi FSP requested: `F:\\wc_312\\MDC_blue_oujizi.fsp`
- Exact oujizi FSP found: `{bool(exact_oujizi)}`
- H1B load status for oujizi: `{h1b_load.get(str(Path(r'F:/wc_312/MDC_blue_oujizi.fsp')), 'unknown')}`

- Exact qujizi FSP requested: `F:\\wc_312\\MDC_blue_qujizi.fsp`
- Exact qujizi FSP found: `{exact_qujizi_found}`
- Competing qujizi FSP candidates: `{competing}`

Related path counts:
- `MDC_blue_oujizi*`: {len(oujizi_any)}
- `MDC_blue_qujizi*`: {len(qujizi_any)}
- All token-matched paths: {len(path_rows)}

H1C does not open or copy any FSP/LDf/MAT/H5 file.
"""
    write_md(OUT / "r2_4h1c_qujizi_oujizi_exact_path_report.md", exact_report)

    evidence_summary = f"""
# R2-4H1C Lightweight Text Evidence Summary

Text-like files scanned from token-matched paths: {len(hit_rows)}

Evidence support flags:
- SiO2/TiO2: `{text_support['sio2_tio2']}`
- 453 or 450 nm text: `{text_support['453_or_450']}`
- 100 and 52 text hints: `{text_support['100_52_nm']}`
- m about 8 text hint: `{text_support['m8']}`
- dipole/source text: `{text_support['dipole_source']}`
- plane-wave text: `{text_support['planewave']}`

These are text/path evidence only. They are not optical validation and not a substitute for GUI/FDTD object confirmation.
"""
    write_md(OUT / "r2_4h1c_text_evidence_summary.md", evidence_summary)

    gui_protocol = f"""
# R2-4H1C Manual GUI Audit Protocol

Open `F:\\wc_312\\MDC_blue_oujizi.fsp` in Lumerical/FDTD GUI without running simulation.

Do not click Run, Run Analysis, Mesh, Optimize, Sweep, Save, or Save As over the original file.

Capture or record:
1. Full object tree screenshot.
2. Source object screenshot/property panel.
3. Source type: dipole / plane wave / other.
4. Source position and orientation.
5. Wavelength/frequency settings.
6. Monitor list and far-field monitor settings.
7. FDTD region boundaries and span.
8. Material/layer stack names.
9. z-stack layer order and approximate thicknesses.
10. Whether SiO2/TiO2 layers are present.
11. Whether blue 453 nm target is visible in source/monitor/settings.
12. Whether the file appears MQW/dipole-like or plane-wave-like.
13. Whether it is safe to use for a future tri-point x-dipole 453 nm planning stage.

Optional screenshot intake folder, not for commit:
`{SCREENSHOT_DIR}`
"""
    write_md(OUT / "r2_4h1c_manual_gui_audit_protocol.md", gui_protocol)

    decision = f"""
# R2-4H1C Baseline Decision After Path Resolution

Primary GUI-audit target: `{primary_target}`

Reason:
- H1A found MDC blue qujizi/oujizi naming evidence.
- H1B loaded `F:\\wc_312\\MDC_blue_oujizi.fsp` successfully but could not introspect object/source/material metadata through the attempted API path.
- H1C confirms the exact oujizi FSP path remains available for manual GUI audit.
- Exact `F:\\wc_312\\MDC_blue_qujizi.fsp` found: `{exact_qujizi_found}`.

Text-supported Wan MDC baseline hints:
- SiO2/TiO2: `{text_support['sio2_tio2']}`
- blue 453/450 text: `{text_support['453_or_450']}`
- 100/52 nm text: `{text_support['100_52_nm']}`
- m about 8: `{text_support['m8']}`

Decision: keep `F:\\wc_312\\MDC_blue_oujizi.fsp` as the primary manual GUI-audit target. Do not freeze it for simulation until GUI evidence confirms object tree, source type, source settings, monitor settings, layer stack, and 453 nm target.

Immediate FDTD allowed: `false`
Next recommended stage: manual GUI screenshot review, then H1D no-run simulation plan only if the audit passes.
"""
    write_md(OUT / "r2_4h1c_baseline_decision_after_path_resolution.md", decision)

    stop_allow = """
# R2-4H1C Stop / Allow Rules

Stop:
- Do not run FDTD.
- Do not call run, runanalysis, mesh, optimize, or sweep.
- Do not open or copy heavy FSP/LDf/MAT/H5 files into git.
- Do not treat text/path evidence as optical success.
- Do not start tri-point FDTD from H1C alone.

Allow:
- Manual GUI screenshot audit of `F:\wc_312\MDC_blue_oujizi.fsp` without running or saving.
- Commit lightweight CSV/JSON/MD/script files and the screenshot intake `.gitignore`.
- Plan H1D only after human GUI evidence is reviewed.
"""
    write_md(OUT / "r2_4h1c_stop_allow_rules.md", stop_allow)

    summary = f"""
# R2-4H1C Wan MDC Path Resolution and GUI Audit Pack

H1C is a zero-FDTD, Python-only filesystem/text audit stage.

Results:
- Source folder exists: `{SOURCE.exists()}`
- Token-matched path count: `{len(path_rows)}`
- Exact oujizi FSP found: `{bool(exact_oujizi)}`
- Exact qujizi FSP found: `{exact_qujizi_found}`
- Primary GUI-audit target: `{primary_target}`
- Immediate FDTD allowed: `false`

Text evidence flags:
- SiO2/TiO2: `{text_support['sio2_tio2']}`
- 453/450: `{text_support['453_or_450']}`
- 100/52 nm: `{text_support['100_52_nm']}`
- m about 8: `{text_support['m8']}`

H1C conclusion: path resolution supports `F:\\wc_312\\MDC_blue_oujizi.fsp` as the primary manual GUI-audit target, but no simulation baseline is frozen until GUI screenshots confirm the source, monitors, stack, and 453 nm settings.
"""
    write_md(OUT / "r2_4h1c_summary.md", summary)

    manifest = {
        "stage": "R2-4H1C Wan MDC path resolution and GUI audit pack",
        "created_at": dt.datetime.now().isoformat(timespec="seconds"),
        "python_only": True,
        "no_lumerical": True,
        "no_lumapi": True,
        "no_fdtd": True,
        "source_folder": str(SOURCE),
        "source_exists": SOURCE.exists(),
        "path_count": len(path_rows),
        "text_hit_file_count": len(hit_rows),
        "exact_oujizi_fsp_found": bool(exact_oujizi),
        "exact_qujizi_fsp_found": exact_qujizi_found,
        "primary_gui_audit_target": primary_target,
        "competing_qujizi_fsp_candidates": [str(r["path"]) for r in exact_qujizi_fsp],
        "text_support": text_support,
        "immediate_fdtd_allowed": False,
        "next_stage": "manual GUI screenshot review or H1D no-run simulation plan after GUI pass",
        "screenshot_intake_folder": str(SCREENSHOT_DIR),
        "heavy_files_copied": False,
    }
    (OUT / "r2_4h1c_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(json.dumps({
        "output": str(OUT),
        "path_count": len(path_rows),
        "exact_oujizi_fsp_found": bool(exact_oujizi),
        "exact_qujizi_fsp_found": exact_qujizi_found,
        "primary_gui_audit_target": primary_target,
        "text_support": text_support,
        "immediate_fdtd_allowed": False,
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
