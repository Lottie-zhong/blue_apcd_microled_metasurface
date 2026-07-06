from __future__ import annotations
import csv, json, re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ML0 = ROOT / "outputs" / "lp_ml0_existing_data_audit"
ML1A = ROOT / "outputs" / "lp_ml1a_seed_manifest_dryrun"
OUT = ROOT / "outputs" / "lp_ml1a2_geometry_provenance_recovery"
REPORT = ROOT / "reports" / "lp_ml1a2_geometry_provenance_recovery.md"
DECISION = ROOT / "reports" / "lp_ml1a2_run_ready_decision.md"
GEOM = ["H_nm","L1_nm","W1_nm","theta1_deg","L2_nm","W2_nm","theta2_deg","gap_or_dx_nm"]
LOOKUP_COLS = ["candidate_id", *GEOM, "pitch_or_period_nm", "source_file", "source_line_or_record", "evidence_type", "confidence_level", "recovery_notes"]
RUN_READY_COLS = ["candidate_id","source_candidate_id","target_bin_deg","sampling_group","source_diagnosis_category",*GEOM,"confidence_level","source_file","priority_score","notes"]


def read_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as f: return list(csv.DictReader(f))

def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w=csv.DictWriter(f, fieldnames=fields, extrasaction="ignore"); w.writeheader(); w.writerows(rows)

def ensure_inputs() -> None:
    import subprocess
    py = r"N:\anaconda_envs\RCP_LCP\python.exe"
    if not (ML0 / "lp_hnew_all_candidates_unified.csv").exists(): subprocess.run([py, str(ROOT / "scripts/lp_ml0/lp_ml0_existing_data_audit.py")], cwd=ROOT, check=True)
    if not (ML1A / "lp_ml1a_seed_manifest.csv").exists(): subprocess.run([py, str(ROOT / "scripts/lp_ml1/lp_ml1a_seed_manifest_dryrun.py")], cwd=ROOT, check=True)

def candidates(unified, diag, manifest, sampling) -> set[str]:
    ids = {r.get("candidate_id","") for r in unified+diag+manifest+sampling}
    ids |= {r.get("source_candidate_id","") for r in manifest+sampling}
    return {x for x in ids if x and "DIMER" in x.upper()}

def explicit_from_csv_json(path: Path, wanted: set[str]) -> dict[str, dict]:
    out = {}
    rows = []
    try:
        if path.suffix.lower() == ".csv": rows = read_csv(path)
        elif path.suffix.lower() == ".json":
            data=json.loads(path.read_text(encoding="utf-8")); rows = data if isinstance(data,list) else ([data] if isinstance(data,dict) else [])
    except Exception: return out
    for i,r in enumerate(rows, 2):
        cid = r.get("candidate_id") or r.get("case_id") or r.get("dimer_case_id") or r.get("source_candidate_id")
        if cid not in wanted: continue
        vals = {k: r.get(k, "") for k in GEOM}
        aliases = {"H_nm":["height_nm"], "gap_or_dx_nm":["gap_nm","gap","dimer_gap_nm"], "L1_nm":["j1_length_nm"], "W1_nm":["j1_width_nm"], "L2_nm":["j2_length_nm"], "W2_nm":["j2_width_nm"]}
        for k,names in aliases.items():
            if not vals[k]:
                for n in names:
                    if r.get(n): vals[k]=r.get(n); break
        if all(str(vals[k]).strip() for k in GEOM):
            out[cid] = {"candidate_id":cid, **vals, "pitch_or_period_nm": r.get("p_x_nm") or r.get("period_nm") or "", "source_file": str(path.relative_to(ROOT)).replace('\\','/'), "source_line_or_record": str(i), "evidence_type":"explicit_csv_json_fields", "confidence_level":"exact_numeric_match", "recovery_notes":"matched exact candidate_id with explicit numeric geometry fields"}
    return out

def script_mapping(path: Path, wanted: set[str]) -> dict[str, dict]:
    # ponytail: conservative regex for same-line dict-like records only; no broad inference.
    out = {}
    try: lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception: return out
    num = r"(-?\d+(?:\.\d+)?)"
    for n,line in enumerate(lines,1):
        for cid in wanted:
            if cid not in line: continue
            vals = {}
            patterns = {
                "H_nm": rf"(?:H_nm|height_nm|height)\D{{0,8}}{num}", "L1_nm": rf"(?:L1_nm|j1_length_nm|L1)\D{{0,8}}{num}", "W1_nm": rf"(?:W1_nm|j1_width_nm|W1)\D{{0,8}}{num}",
                "theta1_deg": rf"(?:theta1_deg|j1_rotation_deg|theta1)\D{{0,8}}{num}", "L2_nm": rf"(?:L2_nm|j2_length_nm|L2)\D{{0,8}}{num}", "W2_nm": rf"(?:W2_nm|j2_width_nm|W2)\D{{0,8}}{num}",
                "theta2_deg": rf"(?:theta2_deg|j2_rotation_deg|theta2)\D{{0,8}}{num}", "gap_or_dx_nm": rf"(?:gap_or_dx_nm|gap_nm|dimer_gap_nm|gap)\D{{0,8}}{num}",
            }
            for k,p in patterns.items():
                m = re.search(p, line)
                vals[k] = m.group(1) if m else ""
            if all(vals.values()):
                out[cid] = {"candidate_id":cid, **vals, "pitch_or_period_nm":"", "source_file": str(path.relative_to(ROOT)).replace('\\','/'), "source_line_or_record": str(n), "evidence_type":"script_mapping", "confidence_level":"script_mapping_match", "recovery_notes":"candidate_id and full numeric geometry found on one script line"}
    return out

def manifest_mapping(manifest: list[dict], wanted: set[str]) -> dict[str, dict]:
    # LP-ML1A manifest geometry is project_default, therefore never run-ready for source provenance.
    out = {}
    for i,r in enumerate(manifest,2):
        cid = r.get("source_candidate_id")
        if cid in wanted and all(r.get(k) for k in GEOM):
            out[cid] = {"candidate_id":cid, **{k:r.get(k,"") for k in GEOM}, "pitch_or_period_nm":"", "source_file":"outputs/lp_ml1a_seed_manifest_dryrun/lp_ml1a_seed_manifest.csv", "source_line_or_record":str(i), "evidence_type":"default_range_manifest_mapping", "confidence_level":"unresolved", "recovery_notes":"LP-ML1A default safe geometry; invalid as run-ready provenance"}
    return out

def build_lookup(ids:set[str], manifest:list[dict]) -> list[dict]:
    found = {}
    for root, globs in [(ROOT/"outputs", ["*.csv","*.json"]), (ROOT/"reports", ["*.csv","*.json","*.yaml","*.md"]), (ROOT/"scripts", ["*.py","*.lsf"] )]:
        if not root.exists(): continue
        for glob in globs:
            for p in root.rglob(glob):
                low=str(p).lower()
                if OUT in p.parents: continue
                if any(x in low for x in [".fsp",".ldf",".log","monitor","farfield","raw"]): continue
                if p.suffix.lower() in {".csv",".json"}: found.update({k:v for k,v in explicit_from_csv_json(p, ids).items() if k not in found})
                if p.suffix.lower() in {".py",".yaml",".md",".lsf"}: found.update({k:v for k,v in script_mapping(p, ids).items() if k not in found})
    default_map = manifest_mapping(manifest, ids)
    rows=[]
    for cid in sorted(ids):
        if cid in found: rows.append(found[cid])
        elif cid in default_map: rows.append(default_map[cid])
        else: rows.append({"candidate_id":cid, **{k:"" for k in GEOM}, "pitch_or_period_nm":"", "source_file":"", "source_line_or_record":"", "evidence_type":"none", "confidence_level":"unresolved", "recovery_notes":"missing_all_geometry"})
    return rows

def ready(row):
    return row.get("confidence_level") in {"exact_numeric_match","script_mapping_match","manifest_mapping_match"} and all(str(row.get(k,"")).strip() for k in GEOM)

def main():
    ensure_inputs(); OUT.mkdir(parents=True, exist_ok=True)
    unified=read_csv(ML0/"lp_hnew_all_candidates_unified.csv"); diag=read_csv(ML0/"lp_hnew_b240_b300_diagnosis.csv"); manifest=read_csv(ML1A/"lp_ml1a_seed_manifest.csv")
    sampling=read_csv(ML1A/"lp_ml1a_sampling_sources.csv") if (ML1A/"lp_ml1a_sampling_sources.csv").exists() else []
    ids=candidates(unified, diag, manifest, sampling); lookup=build_lookup(ids, manifest)
    byid={r["candidate_id"]:r for r in lookup}
    joined=[]; run_ready=[]; unresolved=[]
    for m in manifest:
        src=m.get("source_candidate_id",""); rec=byid.get(src, {})
        row=dict(m)
        for k in GEOM: row[k]=rec.get(k, row.get(k,"")) if ready(rec) else row.get(k,"")
        row["recovered_confidence_level"]=rec.get("confidence_level","unresolved"); row["recovered_source_file"]=rec.get("source_file",""); row["run_ready_geometry"]="true" if ready(rec) else "false"; joined.append(row)
        rr={"candidate_id":m.get("candidate_id",""),"source_candidate_id":src,"target_bin_deg":m.get("target_bin_deg",""),"sampling_group":m.get("sampling_group",""),"source_diagnosis_category":m.get("source_diagnosis_category",""), **{k: rec.get(k,"") for k in GEOM}, "confidence_level":rec.get("confidence_level","unresolved"),"source_file":rec.get("source_file",""),"priority_score":m.get("priority_score",""),"notes":"run-ready only if recovered from non-default provenance"}
        if ready(rec): run_ready.append(rr)
        else:
            reason = rec.get("recovery_notes") or "missing_all_geometry"
            if rec.get("evidence_type") == "default_range_manifest_mapping": reason = "only_default_range_available"
            unresolved.append({**rr, "unresolved_reason": reason})
    write_csv(OUT/"lp_ml1a2_geometry_lookup.csv", lookup, LOOKUP_COLS)
    write_csv(OUT/"lp_ml1a2_manifest_with_recovered_geometry.csv", joined, list(joined[0].keys()) if joined else [])
    write_csv(OUT/"lp_ml1a2_run_ready_sources.csv", run_ready, RUN_READY_COLS)
    write_csv(OUT/"lp_ml1a2_unresolved_sources.csv", unresolved, RUN_READY_COLS+["unresolved_reason"])
    counts=Counter(r["confidence_level"] for r in lookup); recovered=[r for r in lookup if ready(r)]
    summary={"total_source_candidates_searched":len(ids),"exact_numeric_match":counts.get("exact_numeric_match",0),"script_mapping_match":counts.get("script_mapping_match",0),"manifest_mapping_match":counts.get("manifest_mapping_match",0),"name_inferred_low_confidence":counts.get("name_inferred_low_confidence",0),"unresolved":counts.get("unresolved",0),"run_ready_candidate_count":len(run_ready),"count_by_H_nm_recovered":dict(Counter(r.get("H_nm","") for r in recovered)),"count_by_target_bin_recovered":dict(Counter(r.get("target_bin_deg","") for r in run_ready)),"no_fdtd_run":True}
    (OUT/"lp_ml1a2_geometry_recovery_summary.json").write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    top_b300=[r for r in run_ready if r.get("target_bin_deg")=="300"][:10]; top_b240=[r for r in run_ready if r.get("target_bin_deg")=="240"][:10]
    def table(rows):
        cols=["candidate_id","source_candidate_id","target_bin_deg","sampling_group","H_nm","confidence_level","priority_score"]
        if not rows: return "No rows."
        return "\n".join(["| "+" | ".join(cols)+" |","| "+" | ".join(["---"]*len(cols))+" |"]+["| "+" | ".join(str(r.get(c,"")) for c in cols)+" |" for r in rows])
    REPORT.write_text("\n".join(["# LP-ML1A2 Geometry Provenance Recovery","","Purpose: recover numeric geometry provenance for LP candidate IDs before any full-wave LP-ML1B run.","","LP-ML1A is not directly FDTD-run-ready because its 600 rows used project-default geometry after LP-ML0 source rows lacked numeric L/W/theta provenance.","",f"Total source candidates searched: {summary['total_source_candidates_searched']}",f"Recovered exact count: {summary['exact_numeric_match']}",f"Recovered script-mapping count: {summary['script_mapping_match']}",f"Recovered manifest-mapping count: {summary['manifest_mapping_match']}",f"Low-confidence name-inferred count: {summary['name_inferred_low_confidence']}",f"Unresolved count: {summary['unresolved']}","","## Count by H_nm among recovered","```json\n"+json.dumps(summary['count_by_H_nm_recovered'],indent=2,sort_keys=True)+"\n```","## Count by target bin among recovered","```json\n"+json.dumps(summary['count_by_target_bin_recovered'],indent=2,sort_keys=True)+"\n```","## Count by source diagnosis among recovered","No run-ready recovered rows; source diagnosis counts are empty." if not run_ready else "See run-ready CSV.","","## Top recovered B300 sources",table(top_b300),"","## Top recovered B240 sources",table(top_b240),"","No FDTD was run.","No Lumerical GUI was opened.","No model was trained.","No K=6 was attempted."]),encoding="utf-8")
    decision="Go" if len(run_ready)>=20 else "No-Go"
    next_step="Recommend LP-ML1B pilot with 20-40 highest-priority run-ready candidates." if decision=="Go" else "Recommend LP-ML1A3 minimal geometry reconstruction from original generator scripts before any FDTD."
    DECISION.write_text(f"# LP-ML1A2 Run-Ready Decision\n\nDecision: {decision} for LP-ML1B pilot.\n\nRun-ready sources: {len(run_ready)}.\n\n{next_step}\n\nWarning: Do not run LP-ML1B from default-range-only manifest rows.\n",encoding="utf-8")
    print(json.dumps(summary,sort_keys=True)); return 0
if __name__ == "__main__": raise SystemExit(main())

