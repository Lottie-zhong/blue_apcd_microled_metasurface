#!/usr/bin/env python3
"""R2-4H1A inventory existing Wan MDC server files.

Python-only file inventory. Does not open FSP/LDF/MAT/H5 or launch Lumerical.
"""
from __future__ import annotations

import csv
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(r"D:\project\worktrees\blue_apcd_rcled_mdc")
SOURCE = Path(r"F:\wc_312")
OUT = ROOT / "outputs" / "r2_4h1a_inventory_existing_wan_mdc_server_files"
MAX_DEPTH = 2
TEXT_EXTS = {".txt", ".lsf", ".json", ".csv", ".md"}
HEAVY_EXTS = {".fsp", ".ldf", ".mat", ".h5"}
PRIORITY_KEYWORDS = [
    "MDC_blue_qujizi", "MDC_blue_oujizi", "MDC", "MDC_sweep", "MDC_m",
    "MDC_red_453", "MDC_red_angle", "MDC_red_D1", "MDC_red_m",
    "MDC_blue_qujizi_source", "MDC_green_qujizi_source1",
]


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def rel_depth(path: Path) -> int:
    try:
        return len(path.relative_to(SOURCE).parts)
    except ValueError:
        return 999


def safe_mtime(ts: float) -> str:
    return datetime.fromtimestamp(ts).isoformat(timespec="seconds")


def row_for_path(p: Path, is_dir: bool) -> dict[str, Any]:
    st = p.stat()
    ext = "" if is_dir else p.suffix.lower()
    name_l = p.name.lower()
    category = "directory" if is_dir else "file"
    if ext in HEAVY_EXTS:
        category = "heavy_binary_not_opened"
    elif ext in TEXT_EXTS:
        category = "lightweight_text"
    elif not ext and not is_dir and ("mdc" in name_l or "fsp" in name_l):
        category = "possible_fsp_no_extension_not_opened"
    return {
        "full_path": str(p),
        "relative_path": str(p.relative_to(SOURCE)) if SOURCE in p.parents or p == SOURCE else str(p),
        "name": p.name,
        "extension": ext if ext else "none",
        "is_directory": is_dir,
        "size_bytes": "" if is_dir else st.st_size,
        "last_modified": safe_mtime(st.st_mtime),
        "depth": rel_depth(p),
        "category": category,
        "priority_name_match": any(k.lower() in name_l for k in PRIORITY_KEYWORDS),
    }


def inventory() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not SOURCE.exists():
        return rows
    for dirpath, dirnames, filenames in os.walk(SOURCE):
        dpath = Path(dirpath)
        depth = rel_depth(dpath)
        if depth > MAX_DEPTH:
            dirnames[:] = []
            continue
        if depth >= MAX_DEPTH:
            dirnames[:] = []
        for name in sorted(dirnames):
            p = dpath / name
            try:
                rows.append(row_for_path(p, True))
            except OSError:
                pass
        for name in sorted(filenames):
            p = dpath / name
            try:
                rows.append(row_for_path(p, False))
            except OSError:
                pass
    return rows


def read_text_snippets(rows: list[dict[str, Any]]) -> tuple[list[str], dict[str, list[str]]]:
    snippets: list[str] = []
    signals: dict[str, list[str]] = {}
    for row in rows:
        if row["category"] != "lightweight_text":
            continue
        p = Path(row["full_path"])
        sig: list[str] = []
        try:
            text = p.read_bytes()[:16384].decode("utf-8", errors="replace")
        except Exception as exc:
            snippets.append(f"## {p}\nREAD_ERROR: {exc}\n")
            continue
        joined = "\n".join(text.splitlines()[:40])
        low = joined.lower()
        for key in ["453", "blue", "sio2", "tio2", "100", "52", "m=8", "m = 8", "source", "monitor", "wavelength"]:
            if key in low:
                sig.append(key)
        if sig:
            signals[str(p)] = sig
        snippets.append(f"## {p}\nSignals: {', '.join(sig) if sig else 'none'}\n```text\n{joined}\n```\n")
    return snippets, signals


def baseline_role(name_l: str, rel_l: str) -> str:
    if "blue" in name_l or "blue" in rel_l or "453" in name_l or "453" in rel_l:
        return "preferred_blue_or_453nm_MDC_baseline"
    if "sweep" in name_l or "sweep" in rel_l:
        return "parameter_sweep_reference"
    if "_m" in name_l or "mdc_m" in rel_l:
        return "m_pair_count_reference"
    if "source" in name_l or "source" in rel_l:
        return "source_variant_reference"
    return "MDC_related_reference"


def candidate_rows(rows: list[dict[str, Any]], signals: dict[str, list[str]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        name_l = str(row["name"]).lower()
        rel_l = str(row["relative_path"]).lower()
        if "mdc" not in name_l and "mdc" not in rel_l:
            continue
        score = 0
        reasons: list[str] = []
        if "blue" in name_l or "blue" in rel_l:
            score += 3; reasons.append("blue_name")
        if "453" in name_l or "453" in rel_l:
            score += 3; reasons.append("453_name")
        if "qujizi" in name_l or "oujizi" in name_l:
            score += 3; reasons.append("qujizi_oujizi_name")
        if row["extension"] == ".fsp" or row["category"] == "possible_fsp_no_extension_not_opened":
            score += 2; reasons.append("fsp_or_possible_fsp")
        if "source" in name_l or "source" in rel_l:
            score += 1; reasons.append("source_variant")
        sigs: list[str] = []
        for path, s in signals.items():
            path_l = path.lower()
            if rel_l in path_l or Path(path).parent.name.lower() in rel_l:
                sigs += s
        if any(x in sigs for x in ["453", "blue", "sio2", "tio2", "m=8", "m = 8"]):
            score += 2; reasons.append("lightweight_text_support")
        confidence = "high" if score >= 8 else "medium" if score >= 4 else "low"
        out.append({
            "candidate_path": row["full_path"],
            "name": row["name"],
            "extension": row["extension"],
            "category": row["category"],
            "size_bytes": row["size_bytes"],
            "last_modified": row["last_modified"],
            "baseline_role": baseline_role(name_l, rel_l),
            "confidence": confidence,
            "score": score,
            "evidence": ";".join(reasons) if reasons else "filename_only_mdc_related",
            "needs_gui_lumerical_audit": "yes" if confidence != "high" or row["category"] in {"heavy_binary_not_opened", "possible_fsp_no_extension_not_opened"} else "optional",
        })
    out.sort(key=lambda r: (-int(r["score"]), str(r["candidate_path"])))
    return out


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    rows = inventory()
    snippets, signals = read_text_snippets(rows)
    candidates = candidate_rows(rows, signals)
    recommended = candidates[0] if candidates else {}
    found_blue = any("mdc_blue_qujizi" in str(r["name"]).lower() or "mdc_blue_oujizi" in str(r["name"]).lower() for r in rows)

    write_csv(OUT / "r2_4h1a_file_inventory.csv", rows)
    write_csv(OUT / "r2_4h1a_mdc_baseline_candidates.csv", candidates)
    write_text(OUT / "r2_4h1a_lightweight_text_parameter_extract.md", "# R2-4H1A Lightweight Text Parameter Extract\n\n" + ("\n".join(snippets) if snippets else "No lightweight text files found/read within depth limit."))
    write_text(OUT / "r2_4h1a_wan_thesis_parameter_crosscheck.md", f"""
# R2-4H1A Wan Thesis Parameter Crosscheck

Expected Wan/MDC blue seed parameters from project context:
- SiO2/TiO2 MDC near blue 453 nm;
- approximate seed: SiO2 = 100 nm, TiO2 = 52 nm, m = 8;
- experimental spectrum narrowing context: about 28 nm to 18 nm;
- angular context: roughly 30 deg or within 60 deg depending measurement context.

Inventory result:
- source folder exists: {SOURCE.exists()}
- MDC_blue_qujizi or MDC_blue_oujizi found by filename: {found_blue}
- lightweight text signal files with parameter hints: {len(signals)}

This stage did not open FSP binaries. If baseline parameters cannot be confirmed from filenames/lightweight text, the next step is GUI/Lumerical audit only after explicit approval.
""")
    rec_path = recommended.get("candidate_path", "none")
    rec_conf = recommended.get("confidence", "low")
    write_text(OUT / "r2_4h1a_recommended_baseline_freeze_plan.md", f"""
# R2-4H1A Recommended Baseline Freeze Plan

Recommended baseline file/folder:
`{rec_path}`

Confidence: `{rec_conf}`

Plan:
1. Freeze the baseline decision as blue/453 nm MDC-first if `MDC_blue_qujizi` or nearest 453 nm MDC is confirmed.
2. Do not copy or commit original FSP/heavy files.
3. If confidence is medium/low, perform a later GUI/Lumerical audit to confirm layer order, wavelength, material names, m, source, and monitor setup.
4. After audit, encode only lightweight baseline parameters into repo documents/scripts.
5. Do not run FDTD in H1A.
""")
    write_text(OUT / "r2_4h1a_stop_allow_rules.md", """
# R2-4H1A Stop / Allow Rules

Stop:
- no FDTD;
- no Lumerical/lumapi;
- no opening FSP binaries;
- no copying heavy files to repo;
- no push.

Allow:
- Python standard-library inventory of F:\\wc_312;
- read first lines of lightweight .txt/.lsf/.json/.csv/.md files;
- commit lightweight inventory and planning outputs only.
""")
    write_text(OUT / "r2_4h1a_summary.md", f"""
# R2-4H1A Inventory Existing Wan MDC Server Files

Folder checked: `{SOURCE}`

Folder exists: {SOURCE.exists()}
Files/directories inventoried within depth <= {MAX_DEPTH}: {len(rows)}
MDC_blue_qujizi / MDC_blue_oujizi filename found: {found_blue}
Recommended baseline: `{rec_path}`
Confidence: `{rec_conf}`

One-line conclusion: H1A inventories existing server MDC files and recommends the blue/453 nm MDC-related item as the baseline freeze candidate, with GUI/Lumerical audit required if parameters remain filename-only.
""")
    write_json(OUT / "r2_4h1a_manifest.json", {
        "stage": "R2-4H1A inventory existing Wan MDC server files",
        "python_only": True,
        "no_lumerical": True,
        "no_lumapi": True,
        "no_fdtd": True,
        "source_folder": str(SOURCE),
        "source_folder_exists": SOURCE.exists(),
        "max_depth": MAX_DEPTH,
        "inventory_count": len(rows),
        "candidate_count": len(candidates),
        "found_MDC_blue_qujizi_or_oujizi": found_blue,
        "recommended_baseline": rec_path,
        "confidence": rec_conf,
        "needs_gui_lumerical_audit": recommended.get("needs_gui_lumerical_audit", "yes"),
        "heavy_files_not_opened": True,
    })
    print(json.dumps({"output": str(OUT), "source_exists": SOURCE.exists(), "inventory_count": len(rows), "found_blue": found_blue, "recommended": rec_path, "confidence": rec_conf}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
