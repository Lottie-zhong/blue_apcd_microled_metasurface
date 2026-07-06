from __future__ import annotations
import csv, json, math, re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXT_ROOT = Path(r"D:\project\blue_apcd_microled_metasurface")
EXT_DIRS = [EXT_ROOT / "outputs", EXT_ROOT / "scripts", EXT_ROOT / "reports"]
ML0 = ROOT / "outputs" / "lp_ml0_existing_data_audit"
ML1A = ROOT / "outputs" / "lp_ml1a_seed_manifest_dryrun"
ML1A2 = ROOT / "outputs" / "lp_ml1a2_geometry_provenance_recovery"
ML1A3 = ROOT / "outputs" / "lp_ml1a3_git_history_geometry_reconstruction"
OUT = ROOT / "outputs" / "lp_ml1a3b_external_outputs_geometry_recovery"
REPORT = ROOT / "reports" / "lp_ml1a3b_external_outputs_geometry_recovery.md"
DECISION = ROOT / "reports" / "lp_ml1a3b_next_action_decision.md"
MAX_BYTES = 50 * 1024 * 1024
ALLOWED = {".csv", ".json", ".yaml", ".yml", ".md", ".txt", ".py", ".lsf", ".log"}
HEAVY = {".fsp", ".ldf", ".h5", ".mat", ".npz", ".npy", ".zbf", ".raw"}
GEOM = ["H_nm", "L1_nm", "W1_nm", "theta1_deg", "L2_nm", "W2_nm", "theta2_deg", "gap_or_dx_nm"]
INDEX_COLS = ["external_path", "relative_path", "file_size_bytes", "mtime", "file_type", "contains_lp_keywords", "contains_candidate_stem", "scan_status"]
REC_COLS = ["candidate_id", *GEOM, "period_x_nm", "period_y_nm", "pitch_nm", "pairing_rule", "J1_id", "J2_id", "center_dx_nm", "center_dy_nm", "generator_name", "stage_name", "evidence_label", "confidence_level", "external_source_path", "source_line_or_record", "all_evidence_paths", "run_ready_geometry", "notes"]
RUN_COLS = ["candidate_id", "source_candidate_id", "target_bin_deg", "source_diagnosis_category", *GEOM, "period_x_nm", "period_y_nm", "pitch_nm", "pairing_rule", "J1_id", "J2_id", "center_dx_nm", "center_dy_nm", "evidence_label", "confidence_level", "external_source_path", "source_line_or_record", "all_evidence_paths", "priority_score", "run_ready_geometry", "notes"]
VALID = {"exact_external_csv_json", "exact_external_script_dict", "exact_external_lsf_assignment", "external_generator_rule_candidate_specific", "external_candidate_name_plus_table_match"}
KEYWORDS = ["L1", "W1", "theta1", "theta_1", "rot1", "angle1", "L2", "W2", "theta2", "theta_2", "rot2", "angle2", "gap", "dx", "dy", "center_dx", "offset", "H_nm", "height_nm", "H500", "H600", "H650", "H700", "J1", "J2", "pair", "dimer", "B240", "B300", "Hnew", "stage11", "stage11_4"]


def read_csv(p: Path) -> list[dict]:
    try:
        with p.open("r", encoding="utf-8-sig", newline="") as f: return list(csv.DictReader(f))
    except Exception: return []

def write_csv(p: Path, rows: list[dict], fields: list[str]) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore"); w.writeheader(); w.writerows(rows)

def ensure_inputs() -> None:
    import subprocess
    py = r"N:\anaconda_envs\RCP_LCP\python.exe"
    if not (ML0 / "lp_hnew_all_candidates_unified.csv").exists(): subprocess.run([py, str(ROOT / "scripts/lp_ml0/lp_ml0_existing_data_audit.py")], cwd=ROOT, check=True)
    if not (ML1A / "lp_ml1a_seed_manifest.csv").exists(): subprocess.run([py, str(ROOT / "scripts/lp_ml1/lp_ml1a_seed_manifest_dryrun.py")], cwd=ROOT, check=True)
    if not (ML1A2 / "lp_ml1a2_unresolved_sources.csv").exists(): subprocess.run([py, str(ROOT / "scripts/lp_ml1/lp_ml1a2_geometry_provenance_recovery.py")], cwd=ROOT, check=True)
    if not (ML1A3 / "lp_ml1a3_unresolved_sources.csv").exists(): subprocess.run([py, str(ROOT / "scripts/lp_ml1/lp_ml1a3_git_history_geometry_reconstruction.py")], cwd=ROOT, check=True)

def target_ids() -> tuple[set[str], list[dict]]:
    files = [ML0 / "lp_hnew_all_candidates_unified.csv", ML0 / "lp_hnew_b240_b300_diagnosis.csv", ML1A / "lp_ml1a_seed_manifest.csv", ML1A2 / "lp_ml1a2_unresolved_sources.csv", ML1A3 / "lp_ml1a3_unresolved_sources.csv"]
    rows = []
    for p in files:
        if p.exists(): rows += read_csv(p)
    seeds = {"H500DIMER2D_006", "H500DIMER12D_001", "H500DIMER12D_004", "H500DIMER2C_029", "H500DIMER2B_006", "H500DIMER2C_004", "H500DIMER2C_026", "H500DIMER2D_018"}
    ids = set(seeds)
    for r in rows:
        for k in ["candidate_id", "source_candidate_id"]:
            v = r.get(k, "")
            if v and "DIMER" in v.upper(): ids.add(v)
    return ids, rows

def stems(ids: set[str]) -> set[str]:
    out = set(ids)
    for cid in ids:
        parts = cid.split("_")
        if len(parts) >= 2: out.add("_".join(parts[:2]))
    return out

def safe_text(path: Path) -> str:
    try: return path.read_text(encoding="utf-8", errors="ignore")
    except Exception: return ""

def index_files(stemset: set[str]) -> tuple[list[dict], int]:
    rows = []; heavy = 0
    for root in EXT_DIRS:
        if not root.exists(): continue
        for p in root.rglob("*"):
            if not p.is_file(): continue
            suffix = p.suffix.lower(); size = p.stat().st_size
            rel = str(p.relative_to(EXT_ROOT)).replace("\\", "/")
            if suffix in HEAVY or size > MAX_BYTES or any(x in str(p).lower() for x in ["monitor", "farfield", "fielddump"]):
                heavy += 1
                rows.append({"external_path": str(p), "relative_path": rel, "file_size_bytes": size, "mtime": p.stat().st_mtime, "file_type": suffix, "contains_lp_keywords": "", "contains_candidate_stem": "", "scan_status": "skipped_heavy_or_runtime"})
                continue
            if suffix not in ALLOWED: continue
            text = safe_text(p)
            rows.append({"external_path": str(p), "relative_path": rel, "file_size_bytes": size, "mtime": p.stat().st_mtime, "file_type": suffix, "contains_lp_keywords": str(any(k.lower() in text.lower() for k in KEYWORDS)).lower(), "contains_candidate_stem": str(any(s in text for s in stemset)).lower(), "scan_status": "indexed_text"})
    return rows, heavy

def numeric(v: str) -> bool:
    try:
        x = float(v); return math.isfinite(x)
    except Exception: return False

def complete(vals: dict) -> bool:
    return all(numeric(str(vals.get(k, ""))) for k in GEOM)

def parse_line(line: str) -> dict:
    aliases = {"H_nm": ["H_nm", "height_nm", "height"], "L1_nm": ["L1_nm", "j1_length_nm", "L1"], "W1_nm": ["W1_nm", "j1_width_nm", "W1"], "theta1_deg": ["theta1_deg", "theta_1", "rot1", "angle1", "j1_rotation_deg", "theta1"], "L2_nm": ["L2_nm", "j2_length_nm", "L2"], "W2_nm": ["W2_nm", "j2_width_nm", "W2"], "theta2_deg": ["theta2_deg", "theta_2", "rot2", "angle2", "j2_rotation_deg", "theta2"], "gap_or_dx_nm": ["gap_or_dx_nm", "gap_nm", "dimer_gap_nm", "center_dx_nm", "dx_nm", "gap"]}
    vals = {}
    for k, names in aliases.items():
        vals[k] = ""
        for name in names:
            m = re.search(rf"['\"]?{re.escape(name)}['\"]?\s*[:=,]\s*['\"]?(-?\d+(?:\.\d+)?)", line)
            if m: vals[k] = m.group(1); break
    return vals

def parse_csv_json(path: Path, ids: set[str]) -> dict[str, list[dict]]:
    found = defaultdict(list)
    rows = []
    if path.suffix.lower() == ".csv": rows = read_csv(path)
    elif path.suffix.lower() == ".json":
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            rows = data if isinstance(data, list) else ([data] if isinstance(data, dict) else [])
        except Exception: rows = []
    for i, r in enumerate(rows, 2):
        cid = r.get("candidate_id") or r.get("case_id") or r.get("dimer_case_id") or r.get("source_candidate_id")
        if cid not in ids: continue
        vals = {k: r.get(k, "") for k in GEOM}
        alias = {"H_nm": ["height_nm"], "gap_or_dx_nm": ["gap_nm", "dimer_gap_nm", "center_dx_nm"], "L1_nm": ["j1_length_nm"], "W1_nm": ["j1_width_nm"], "theta1_deg": ["j1_rotation_deg"], "L2_nm": ["j2_length_nm"], "W2_nm": ["j2_width_nm"], "theta2_deg": ["j2_rotation_deg"]}
        for k, names in alias.items():
            if not vals[k]:
                for n in names:
                    if r.get(n): vals[k] = r.get(n); break
        if complete(vals):
            found[cid].append(record(cid, vals, "exact_external_csv_json", path, str(i)))
    return found

def record(cid: str, vals: dict, label: str, path: Path, loc: str) -> dict:
    return {"candidate_id": cid, **{k: vals.get(k, "") for k in GEOM}, "period_x_nm": "", "period_y_nm": "", "pitch_nm": "", "pairing_rule": "", "J1_id": "", "J2_id": "", "center_dx_nm": vals.get("gap_or_dx_nm", ""), "center_dy_nm": "0", "generator_name": "", "stage_name": "", "evidence_label": label, "confidence_level": label, "external_source_path": str(path), "source_line_or_record": loc, "all_evidence_paths": str(path), "run_ready_geometry": "false", "notes": "candidate-specific external numeric geometry"}

def parse_text(path: Path, ids: set[str]) -> dict[str, list[dict]]:
    found = defaultdict(list)
    if path.suffix.lower() in {".csv", ".json"}: return found
    lines = safe_text(path).splitlines()
    label = "exact_external_lsf_assignment" if path.suffix.lower() == ".lsf" else "exact_external_script_dict" if path.suffix.lower() in {".py", ".yaml", ".yml"} else "partial_external_match_needs_manual_review"
    for n, line in enumerate(lines, 1):
        for cid in ids:
            if cid in line:
                vals = parse_line(line)
                if label != "partial_external_match_needs_manual_review" and complete(vals):
                    found[cid].append(record(cid, vals, label, path, str(n)))
                elif any(vals.values()):
                    found[cid].append(record(cid, vals, "partial_external_match_needs_manual_review", path, str(n)))
    return found

def merge_evidence(ids: set[str], index: list[dict]) -> tuple[list[dict], list[dict], int, int]:
    evidence = defaultdict(list); exact_matches = partial_matches = 0
    for item in index:
        if item["scan_status"] != "indexed_text" or item["contains_candidate_stem"] != "true": continue
        p = Path(item["external_path"])
        found = parse_csv_json(p, ids) if p.suffix.lower() in {".csv", ".json"} else parse_text(p, ids)
        for cid, rows in found.items():
            evidence[cid].extend(rows)
            exact_matches += sum(1 for r in rows if r["evidence_label"] in VALID)
            partial_matches += sum(1 for r in rows if r["evidence_label"] not in VALID)
    recovered = []; unresolved = []
    for cid in sorted(ids):
        goods = [r for r in evidence[cid] if r["evidence_label"] in VALID and complete(r)]
        sigs = {tuple(g[k] for k in GEOM) for g in goods}
        if len(sigs) == 1 and goods:
            row = goods[0]; row["run_ready_geometry"] = "true"; row["all_evidence_paths"] = ";".join(sorted({g["external_source_path"] for g in goods})); recovered.append(row)
        elif len(sigs) > 1:
            unresolved.append(unresolved_row(cid, "conflicting_external_evidence"))
        elif evidence[cid]:
            unresolved.append(unresolved_row(cid, "partial_match_only"))
        else:
            unresolved.append(unresolved_row(cid, "candidate_id_not_found_in_external_outputs"))
    return recovered, unresolved, exact_matches, partial_matches

def unresolved_row(cid: str, reason: str) -> dict:
    return {"candidate_id": cid, **{k: "" for k in GEOM}, "period_x_nm": "", "period_y_nm": "", "pitch_nm": "", "pairing_rule": "", "J1_id": "", "J2_id": "", "center_dx_nm": "", "center_dy_nm": "", "generator_name": "", "stage_name": "", "evidence_label": "unresolved", "confidence_level": "unresolved", "external_source_path": "", "source_line_or_record": "", "all_evidence_paths": "", "run_ready_geometry": "false", "notes": reason}

def run_ready_rows(recovered: list[dict], manifest_rows: list[dict]) -> list[dict]:
    rec = {r["candidate_id"]: r for r in recovered}; out = []
    for m in manifest_rows:
        src = m.get("source_candidate_id", "")
        if src not in rec: continue
        r = rec[src]; target = m.get("target_bin_deg", "")
        pri = 400 if target == "300" else 300 if target == "240" else 200
        if r["evidence_label"] in {"exact_external_csv_json", "exact_external_script_dict"}: pri += 50
        if r.get("H_nm") in {"500", "600", "650"}: pri += 10
        out.append({"candidate_id": m.get("candidate_id", ""), "source_candidate_id": src, "target_bin_deg": target, "source_diagnosis_category": m.get("source_diagnosis_category", ""), **{k: r.get(k, "") for k in GEOM}, "period_x_nm": r.get("period_x_nm", ""), "period_y_nm": r.get("period_y_nm", ""), "pitch_nm": r.get("pitch_nm", ""), "pairing_rule": r.get("pairing_rule", ""), "J1_id": r.get("J1_id", ""), "J2_id": r.get("J2_id", ""), "center_dx_nm": r.get("center_dx_nm", ""), "center_dy_nm": r.get("center_dy_nm", ""), "evidence_label": r["evidence_label"], "confidence_level": r["confidence_level"], "external_source_path": r["external_source_path"], "source_line_or_record": r["source_line_or_record"], "all_evidence_paths": r["all_evidence_paths"], "priority_score": pri, "run_ready_geometry": "true", "notes": "external output geometry recovered"})
    return sorted(out, key=lambda r: (-float(r["priority_score"]), r["candidate_id"]))

def table(rows: list[dict]) -> str:
    cols = ["candidate_id", "source_candidate_id", "target_bin_deg", "H_nm", "evidence_label", "priority_score"]
    if not rows: return "No rows."
    return "\n".join(["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"] + ["| " + " | ".join(str(r.get(c, "")) for c in cols) + " |" for r in rows[:10]])

def main() -> int:
    ensure_inputs(); OUT.mkdir(parents=True, exist_ok=True)
    ids, _ = target_ids(); stemset = stems(ids)
    index, heavy = index_files(stemset); write_csv(OUT / "lp_ml1a3b_external_file_index.csv", index, INDEX_COLS)
    recovered, unresolved, exact_match_count, partial_match_count = merge_evidence(ids, index)
    write_csv(OUT / "lp_ml1a3b_candidate_geometry_recovered.csv", recovered + unresolved, REC_COLS)
    manifest = read_csv(ML1A / "lp_ml1a_seed_manifest.csv")
    ready = run_ready_rows(recovered, manifest); write_csv(OUT / "lp_ml1a3b_run_ready_sources.csv", ready, RUN_COLS)
    write_csv(OUT / "lp_ml1a3b_unresolved_sources.csv", [{"candidate_id": u["candidate_id"], "source_candidate_id": u["candidate_id"], "unresolved_reason": u["notes"], **u} for u in unresolved], ["candidate_id", "source_candidate_id", "unresolved_reason", *REC_COLS])
    label_counts = Counter(r["evidence_label"] for r in recovered); conflict = sum(1 for u in unresolved if u["notes"] == "conflicting_external_evidence")
    summary = {"external_files_indexed": sum(1 for r in index if r["scan_status"] == "indexed_text"), "heavy_files_skipped": heavy, "unique_candidate_ids_searched": len(ids), "exact_match_count": exact_match_count, "partial_match_count": partial_match_count, "recovered_by_evidence_label": dict(label_counts), "unresolved_count": len(unresolved), "conflicting_evidence_count": conflict, "run_ready_count": len(ready), "recovered_count_by_H_nm": dict(Counter(r.get("H_nm", "") for r in recovered)), "recovered_count_by_target_bin_deg": dict(Counter(r.get("target_bin_deg", "") for r in ready)), "no_fdtd_run": True}
    (OUT / "lp_ml1a3b_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    b300 = [r for r in ready if r.get("target_bin_deg") == "300"]; b240 = [r for r in ready if r.get("target_bin_deg") == "240"]
    examples = [r["external_source_path"] for r in recovered[:5]] or ["No exact numeric evidence paths recovered."]
    REPORT.write_text("\n".join(["# LP-ML1A3B External Outputs Geometry Recovery", "", "Purpose: recover numeric LP dimer geometry from the original project output folder before any LP-ML1B run.", "", "A3 searched only the current worktree and git history. A3B additionally reads D:\\project\\blue_apcd_microled_metasurface\\outputs plus scripts/reports as read-only external provenance.", "", "External roots searched:", "- D:\\project\\blue_apcd_microled_metasurface\\outputs", "- D:\\project\\blue_apcd_microled_metasurface\\scripts", "- D:\\project\\blue_apcd_microled_metasurface\\reports", "", f"File count indexed: {summary['external_files_indexed']}", f"Skipped heavy file count: {summary['heavy_files_skipped']}", f"Unique candidate IDs searched: {summary['unique_candidate_ids_searched']}", f"Exact match count: {summary['exact_match_count']}", f"Partial match count: {summary['partial_match_count']}", "Recovered count by evidence label:", "```json\n" + json.dumps(summary['recovered_by_evidence_label'], indent=2, sort_keys=True) + "\n```", f"Unresolved count: {summary['unresolved_count']}", f"Conflicting evidence count: {summary['conflicting_evidence_count']}", f"Run-ready candidate count: {summary['run_ready_count']}", "", "## Recovered count by H_nm", "```json\n" + json.dumps(summary['recovered_count_by_H_nm'], indent=2, sort_keys=True) + "\n```", "## Recovered count by target_bin_deg", "```json\n" + json.dumps(summary['recovered_count_by_target_bin_deg'], indent=2, sort_keys=True) + "\n```", "## Top recovered B300 sources", table(b300), "", "## Top recovered B240 sources", table(b240), "", "## Evidence path examples", "\n".join(f"- {p}" for p in examples), "", "No FDTD was run.", "No Lumerical GUI was opened.", "No model was trained.", "No K=6 was attempted."]) + "\n", encoding="utf-8")
    decision = "Go" if len(ready) >= 20 else "No-Go"
    if len(ready) >= 20: next_step = "Recommend LP-ML1B 20-40 case pilot using highest-priority run-ready rows."
    elif len(ready) > 0: next_step = "Recommend manual review plus optional small FDTD pilot only after geometry confirmation."
    else: next_step = "Recommend LP-ML1A4 explicit new geometry seed generator."
    DECISION.write_text(f"# LP-ML1A3B Next Action Decision\n\nDecision: {decision} for LP-ML1B pilot.\n\nRun-ready count: {len(ready)}.\n\n{next_step}\n\nWarning: Do not run LP-ML1B from default-range-only manifest rows.\n", encoding="utf-8")
    print(json.dumps(summary, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
