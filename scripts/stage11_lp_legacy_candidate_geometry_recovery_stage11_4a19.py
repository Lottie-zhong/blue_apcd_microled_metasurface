from __future__ import annotations

import csv
import json
import os
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

WORKTREE = Path(__file__).resolve().parents[1]
REPORTS = WORKTREE / "reports"
ALLOWED_ROOTS = [
    WORKTREE,
    Path(r"D:\project\blue_apcd_microled_metasurface"),
    Path(r"D:\project\blue_apcd_microled_metasurface_wt_stage11_4a0"),
    Path(r"D:\project\blue_plane_wave_metasurface"),
]
LIGHT_EXT = {".py", ".csv", ".json", ".md", ".txt", ".yaml", ".yml", ".lsf", ".ini", ".toml"}
HEAVY_EXT = {".fsp", ".ldf", ".mat", ".h5", ".hdf5", ".npy", ".npz", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".mp4", ".avi", ".zip", ".7z", ".rar"}
PRIORITY_FULL = [
    "H500DIMER2D_006_B240_x_pair_swap_G80_O-30",
    "H500DIMER12D_001_B300_x_pair_swap_G70_O-30",
    "H500DIMER12D_004_B300_x_pair_swap_G80_O-40",
]
PRIORITY_BASE = [
    "H500DIMER2C_029",
    "H500DIMER2B_006",
    "H500DIMER2C_004",
    "H500DIMER2C_026",
    "H500DIMER2D_018",
    "H500DIMER2D_006",
    "H500DIMER12D_001",
    "H500DIMER12D_004",
]
H500_SIX_SEED = ["H500DIMER2C_029", "H500DIMER2B_006", "H500DIMER2C_004", "H500DIMER2C_026", "H500DIMER2D_018", "H500DIMER2D_006"]
FAMILY_STEMS = ["DIMER2B", "DIMER2C", "DIMER2D", "DIMER12D", "H500DIMER", "H600DIMER", "H650DIMER", "H700DIMER"]
SUFFIX_RE = re.compile(r"(?P<target>B\d+)_(?P<axis>[xy])_pair_(?P<order>noswap|swap)_G(?P<G>-?\d+)_O(?P<O>[+-]?\d+)")
FULL_SUFFIX_RE = re.compile(r"(?P<base>H\d+DIMER\d+[A-Z]?_\d+)_(?P<target>B\d+)_(?P<axis>[xy])_pair_(?P<order>noswap|swap)_G(?P<G>-?\d+)_O(?P<O>[+-]?\d+)")
GEOM_ALIASES = {
    "H_nm": ["H_nm", "height_nm", "height", "h_nm"],
    "L1_nm": ["L1_nm", "j1_length_nm", "j1_L_nm", "L1", "length1_nm", "length_nm"],
    "W1_nm": ["W1_nm", "j1_width_nm", "j1_W_nm", "W1", "width1_nm", "width_nm"],
    "theta1_deg": ["theta1_deg", "j1_rotation_deg", "rot1", "angle1", "rotation1_deg"],
    "L2_nm": ["L2_nm", "j2_length_nm", "j2_L_nm", "L2", "length2_nm"],
    "W2_nm": ["W2_nm", "j2_width_nm", "j2_W_nm", "W2", "width2_nm"],
    "theta2_deg": ["theta2_deg", "j2_rotation_deg", "rot2", "angle2", "rotation2_deg"],
    "gap_or_dx_nm": ["gap_or_dx_nm", "gap_nm", "dimer_gap_nm", "dx_nm", "center_dx_nm", "gap"],
    "center_dx_nm": ["center_dx_nm", "j2_center_x_nm", "dx_center_nm"],
    "center_dy_nm": ["center_dy_nm", "j2_center_y_nm", "dy_center_nm"],
    "period_x_nm": ["period_x_nm", "p_x_nm", "px_nm"],
    "period_y_nm": ["period_y_nm", "p_y_nm", "py_nm"],
}
RECOVERY_COLUMNS = ["candidate_id", "base_candidate_id", "H_nm", "L1_nm", "W1_nm", "theta1_deg", "L2_nm", "W2_nm", "theta2_deg", "gap_or_dx_nm", "center_dx_nm", "center_dy_nm", "period_x_nm", "period_y_nm", "pair_swap", "axis", "G_nm", "O_nm", "transform_rule", "evidence_file", "evidence_type", "confidence", "status"]

@dataclass
class Evidence:
    candidate_id: str
    base_candidate_id: str
    source_file: str
    evidence_type: str
    line: str = ""
    geometry: dict | None = None


def parse_suffix(candidate_id: str) -> dict[str, str]:
    m = SUFFIX_RE.search(candidate_id)
    if not m:
        return {"target_bin": "", "axis": "", "pair_swap": "", "G_nm": "", "O_nm": ""}
    return {"target_bin": m.group("target"), "axis": m.group("axis"), "pair_swap": str(m.group("order") == "swap").lower(), "G_nm": m.group("G"), "O_nm": m.group("O")}


def base_id(candidate_id: str) -> str:
    m = FULL_SUFFIX_RE.search(candidate_id)
    return m.group("base") if m else candidate_id


def light_files(root: Path) -> Iterable[Path]:
    if not root.exists():
        return []
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in {".git", "__pycache__", ".pytest_cache"}]
        for name in filenames:
            p = Path(dirpath) / name
            ext = p.suffix.lower()
            if ext in HEAVY_EXT or ext not in LIGHT_EXT:
                continue
            try:
                if p.stat().st_size <= 8_000_000:
                    out.append(p)
            except OSError:
                pass
    return out


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def row_value(row: dict, aliases: list[str]) -> str:
    lower = {str(k).lower(): v for k, v in row.items()}
    for a in aliases:
        v = row.get(a, lower.get(a.lower(), ""))
        if v not in (None, ""):
            return str(v)
    return ""


def geometry_from_row(row: dict) -> dict[str, str]:
    return {field: row_value(row, aliases) for field, aliases in GEOM_ALIASES.items()}


def row_has_geometry(geom: dict[str, str]) -> bool:
    return all(geom.get(k) for k in ["H_nm", "L1_nm", "W1_nm", "theta1_deg", "L2_nm", "W2_nm", "theta2_deg", "gap_or_dx_nm"])


def scan_csv(path: Path, wanted: list[str]) -> list[Evidence]:
    out = []
    try:
        with path.open(newline="", encoding="utf-8-sig", errors="ignore") as f:
            for row in csv.DictReader(f):
                blob = " ".join(str(v) for v in row.values())
                for hit in [w for w in wanted if w in blob]:
                    cid = row_value(row, ["candidate_id", "dimer_case_id", "source_pair_id", "base_candidate_id"]) or hit
                    if not cid.startswith("H"):
                        cid = hit
                    out.append(Evidence(cid, base_id(cid), str(path), "exact_candidate_csv" if cid in PRIORITY_FULL else "base_candidate_csv", geometry=geometry_from_row(row)))
    except Exception:
        return []
    return out


def scan_textish(path: Path, wanted: list[str]) -> list[Evidence]:
    text = read_text(path)
    if not text:
        return []
    out = []
    ext = path.suffix.lower()
    etype = "exact_candidate_json" if ext == ".json" else "manifest" if ext in {".md", ".yaml", ".yml", ".toml", ".ini"} else "python_generator" if ext == ".py" else "lsf_assignment" if ext == ".lsf" else "git_grep_only"
    for n, line in enumerate(text.splitlines(), 1):
        for hit in [w for w in wanted if w in line]:
            out.append(Evidence(hit, base_id(hit), f"{path}:{n}", etype, line.strip()[:300]))
    return out


def collect_evidence() -> list[Evidence]:
    wanted = PRIORITY_FULL + PRIORITY_BASE + FAMILY_STEMS
    evidence = []
    for root in ALLOWED_ROOTS:
        for path in light_files(root):
            evidence.extend(scan_csv(path, wanted) if path.suffix.lower() == ".csv" else scan_textish(path, wanted))
    return evidence


def best_base_geometry(evidence: list[Evidence]) -> dict[str, dict[str, str]]:
    best = {}
    for ev in evidence:
        if ev.geometry and row_has_geometry(ev.geometry):
            best.setdefault(ev.base_candidate_id, ev.geometry)
            best.setdefault(ev.candidate_id, ev.geometry)
    return best


def explicit_transform_source(evidence: list[Evidence]) -> str:
    needles = ["center_dx", "center_dy", "j1_center", "j2_center", "local_offset", "gap_nm", "dimer_gap", "placement_type"]
    for ev in evidence:
        line = ev.line.lower()
        if any(n in line for n in needles) and ("_g" in line or "gap" in line):
            return ev.source_file
    return ""


def make_recovery_rows(evidence: list[Evidence]) -> list[dict[str, str]]:
    geom_by_base = best_base_geometry(evidence)
    transform_source = explicit_transform_source(evidence)
    rows = []
    for cid in PRIORITY_FULL + PRIORITY_BASE:
        base = base_id(cid)
        suffix = parse_suffix(cid)
        geom = geom_by_base.get(base) or geom_by_base.get(cid) or {}
        hits = [ev for ev in evidence if ev.candidate_id in {cid, base} or ev.base_candidate_id in {cid, base}]
        has_base = row_has_geometry(geom)
        has_suffix = bool(suffix["G_nm"])
        if has_base and has_suffix and transform_source:
            status, confidence, rule = "reconstructed", "high", f"explicit:{transform_source}"
        elif has_base:
            status, confidence, rule = "partial_base_only", "medium", "suffix_only" if has_suffix else "base_only"
        elif has_suffix:
            status, confidence, rule = "suffix_only", "low", "suffix_only"
        else:
            status, confidence, rule = "unresolved", "none", "none"
        row = {c: "" for c in RECOVERY_COLUMNS}
        row.update({"candidate_id": cid, "base_candidate_id": base, "pair_swap": suffix["pair_swap"], "axis": suffix["axis"], "G_nm": suffix["G_nm"], "O_nm": suffix["O_nm"], "transform_rule": rule, "evidence_file": hits[0].source_file if hits else "", "evidence_type": hits[0].evidence_type if hits else ("suffix_only" if has_suffix else "git_grep_only"), "confidence": confidence, "status": status})
        for k in GEOM_ALIASES:
            row[k] = geom.get(k, "")
        rows.append(row)
    return rows


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows([{k: r.get(k, "") for k in fields} for r in rows])


def main() -> None:
    REPORTS.mkdir(exist_ok=True)
    evidence = collect_evidence()
    rows = make_recovery_rows(evidence)
    recovered = [r for r in rows if r["status"] == "reconstructed"]
    partial = [r for r in rows if r["status"] in {"partial_base_only", "suffix_only"}]
    unresolved = [r for r in rows if r["status"] == "unresolved"]
    transform_rows = [{k: r[k] for k in ["candidate_id", "axis", "pair_swap", "G_nm", "O_nm", "transform_rule", "confidence", "status"]} for r in rows if r["G_nm"]]
    source_counter = Counter(re.sub(r":\\d+$", "", ev.source_file) for ev in evidence)
    sources = [{"source_file": k, "match_count": v} for k, v in source_counter.most_common(50)]
    summary = {
        "recovered_count": len(recovered),
        "partial_count": len(partial),
        "unresolved_count": len(unresolved),
        "priority_candidates_recovered": [r["candidate_id"] for r in recovered if r["candidate_id"] in PRIORITY_FULL],
        "h500_six_seed_recovery": {r["candidate_id"]: r["status"] for r in rows if r["candidate_id"] in H500_SIX_SEED},
        "b240_b300_base_transform_recovery": {r["candidate_id"]: r["status"] for r in rows if "_B240_" in r["candidate_id"] or "_B300_" in r["candidate_id"]},
        "evidence_type_counts": dict(Counter(ev.evidence_type for ev in evidence)),
        "top_evidence_files": sources[:10],
        "run_ready_geometry_table_exists": bool(recovered),
        "no_fdtd_lumerical_run": True,
    }
    write_csv(REPORTS / "stage11_4a19_legacy_candidate_geometry_recovery_table.csv", rows, RECOVERY_COLUMNS)
    write_csv(REPORTS / "stage11_4a19_legacy_candidate_geometry_transform_rules.csv", transform_rows, ["candidate_id", "axis", "pair_swap", "G_nm", "O_nm", "transform_rule", "confidence", "status"])
    write_csv(REPORTS / "stage11_4a19_legacy_candidate_geometry_unresolved.csv", unresolved, RECOVERY_COLUMNS)
    write_csv(REPORTS / "stage11_4a19_legacy_candidate_geometry_sources.csv", sources, ["source_file", "match_count"])
    (REPORTS / "stage11_4a19_legacy_candidate_geometry_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    report = ["# Stage11-4A19 LP legacy candidate geometry recovery", "", "No FDTD or Lumerical execution was run. This audit only scanned lightweight files in the allowed roots.", "", f"Recovered count: {len(recovered)}", f"Partial count: {len(partial)}", f"Unresolved count: {len(unresolved)}", "", "## Priority and seed candidates"]
    report += [f"- {r['candidate_id']}: {r['status']} ({r['confidence']}); evidence={r['evidence_file'] or 'none'}" for r in rows]
    report += ["", "## Transform rules", "Suffixes such as `_B300_x_pair_swap_G80_O-40` are parsed. G/O semantics are explicit only when a matching layout rule is found; otherwise transform_rule is suffix_only.", "", "## Top evidence files"]
    report += [f"- {s['source_file']}: {s['match_count']}" for s in sources[:10]]
    (REPORTS / "stage11_4a19_legacy_candidate_geometry_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    next_line = "run-ready reuse is possible for reconstructed rows." if recovered else "no run-ready legacy geometry table exists; use manual inspection or explicit new geometry seed generator."
    (REPORTS / "stage11_4a19_legacy_candidate_geometry_recommended_next.md").write_text(f"# Stage11-4A19 recommended next\n\n{next_line}\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))

if __name__ == "__main__":
    main()

