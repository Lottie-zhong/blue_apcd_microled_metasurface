from __future__ import annotations
import argparse, csv, json, re, subprocess, sys
from collections import Counter
from pathlib import Path

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))
from lp_protected_artifact_guard_v1 import assert_not_protected_write_target, guarded_write_text

ROOT = Path(__file__).resolve().parents[2]
ML0 = ROOT / "outputs" / "lp_ml0_existing_data_audit"
ML1A = ROOT / "outputs" / "lp_ml1a_seed_manifest_dryrun"
ML1A2 = ROOT / "outputs" / "lp_ml1a2_geometry_provenance_recovery"
OUT = ROOT / "outputs" / "lp_ml1a3_git_history_geometry_reconstruction"
DERIVED_REPORT_DIR = OUT / "derived_reports"
REPORT = DERIVED_REPORT_DIR / "git_history_geometry_reconstruction.md"
DECISION = DERIVED_REPORT_DIR / "next_action_decision.md"
GEOM = ["H_nm","L1_nm","W1_nm","theta1_deg","L2_nm","W2_nm","theta2_deg","gap_or_dx_nm"]
REC_COLS = ["candidate_id",*GEOM,"pitch_nm","period_nm","pairing_rule","J1_id","J2_id","evidence_label","confidence_level","source_commit","source_file","source_line_or_record","run_ready_geometry","notes"]
RUN_COLS = ["candidate_id","source_candidate_id","target_bin_deg","sampling_group","source_diagnosis_category",*GEOM,"pitch_nm","period_nm","evidence_label","confidence_level","source_commit","source_file","source_line_or_record","priority_score","notes"]
INDEX_COLS = ["commit","path","matched_reason"]
VALID_LABELS = {"exact_candidate_csv_json","exact_candidate_script_dict","exact_candidate_lsf_assignment","generator_rule_candidate_specific"}


def git(args, check=True):
    cp = subprocess.run(["git", *args], cwd=ROOT, text=True, encoding="utf-8", errors="replace", stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if check and cp.returncode: raise RuntimeError(cp.stderr)
    return cp.stdout

def read_csv(p):
    with p.open("r", encoding="utf-8-sig", newline="") as f: return list(csv.DictReader(f))

def write_csv(p, rows, fields):
    assert_not_protected_write_target(p, "write", __file__)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8", newline="") as f:
        w=csv.DictWriter(f, fieldnames=fields, extrasaction="ignore"); w.writeheader(); w.writerows(rows)

def ensure_inputs():
    py = r"N:\anaconda_envs\RCP_LCP\python.exe"
    if not (ML0/"lp_hnew_all_candidates_unified.csv").exists(): subprocess.run([py, str(ROOT/"scripts/lp_ml0/lp_ml0_existing_data_audit.py")], cwd=ROOT, check=True)
    if not (ML1A/"lp_ml1a_seed_manifest.csv").exists(): subprocess.run([py, str(ROOT/"scripts/lp_ml1/lp_ml1a_seed_manifest_dryrun.py")], cwd=ROOT, check=True)
    if not (ML1A2/"lp_ml1a2_unresolved_sources.csv").exists(): subprocess.run([py, str(ROOT/"scripts/lp_ml1/lp_ml1a2_geometry_provenance_recovery.py")], cwd=ROOT, check=True)

def target_ids():
    rows=[]
    for p in [ML1A2/"lp_ml1a2_unresolved_sources.csv", ML1A2/"lp_ml1a2_manifest_with_recovered_geometry.csv", ML1A/"lp_ml1a_seed_manifest.csv", ML0/"lp_hnew_all_candidates_unified.csv", ML0/"lp_hnew_b240_b300_diagnosis.csv"]:
        if p.exists(): rows += read_csv(p)
    ids=set()
    for r in rows:
        for k in ["candidate_id","source_candidate_id"]:
            v=r.get(k,"")
            if v and "DIMER" in v.upper(): ids.add(v)
    return ids

def history_index():
    text = git(["log","--all","--name-only","--pretty=format:%H"])
    exts={".py",".lsf",".json",".csv",".yaml",".yml",".md",".txt"}; roots=("scripts/","reports/","outputs/","configs/")
    rows=[]; commit=""
    for line in text.splitlines():
        line=line.strip()
        if not line: continue
        if re.fullmatch(r"[0-9a-f]{40}", line): commit=line; continue
        p=line.replace("\\","/")
        if commit and p.startswith(roots) and Path(p).suffix.lower() in exts and not any(x in p.lower() for x in [".fsp",".ldf",".log","monitor","farfield","raw"]):
            rows.append({"commit":commit,"path":p,"matched_reason":"history_lightweight_file"})
    return rows

def parse_geom(text):
    aliases={"H_nm":["H_nm","height_nm","height"],"L1_nm":["L1_nm","j1_length_nm","L1"],"W1_nm":["W1_nm","j1_width_nm","W1"],"theta1_deg":["theta1_deg","j1_rotation_deg","theta1"],"L2_nm":["L2_nm","j2_length_nm","L2"],"W2_nm":["W2_nm","j2_width_nm","W2"],"theta2_deg":["theta2_deg","j2_rotation_deg","theta2"],"gap_or_dx_nm":["gap_or_dx_nm","gap_nm","dimer_gap_nm","dx_nm","gap"]}
    vals={}
    for k,names in aliases.items():
        vals[k]=""
        for name in names:
            m=re.search(rf"['\"]?{re.escape(name)}['\"]?\s*[:=]\s*['\"]?(-?\d+(?:\.\d+)?)", text)
            if m: vals[k]=m.group(1); break
    return vals

def complete(vals):
    try: return all(vals.get(k)!="" and float(vals[k])==float(vals[k]) for k in GEOM)
    except Exception: return False

def classify(path):
    ext=Path(path).suffix.lower()
    if ext in {".csv",".json"}: return "exact_candidate_csv_json"
    if ext==".lsf": return "exact_candidate_lsf_assignment"
    if ext in {".py",".yaml",".yml"}: return "exact_candidate_script_dict"
    return "partial_match_needs_manual_review"

def current_tree_hits(ids):
    pats=sorted(ids)
    hits=[]
    for i in range(0,len(pats),30):
        args=["grep","-n","-F"]
        for p in pats[i:i+30]: args += ["-e", p]
        args += ["--","scripts","reports","outputs","configs"]
        out=git(args, check=False)
        for line in out.splitlines():
            m=re.match(r"([^:]+):(\d+):(.*)", line)
            if m: hits.append(("HEAD",m.group(1),m.group(2),m.group(3)))
    return hits

def recover(ids, hits):
    found={cid:[] for cid in ids}
    for commit,path,line_no,line in hits:
        if any(x in path.lower() for x in ["lp_ml1a_seed_manifest", "lp_ml1a2_geometry_provenance_recovery", "lp_ml1a3_git_history_geometry_reconstruction"]):
            continue
        for cid in ids:
            if cid in line:
                vals=parse_geom(line); label=classify(path) if complete(vals) else "partial_match_needs_manual_review"
                found[cid].append({"candidate_id":cid,**vals,"pitch_nm":"","period_nm":"","pairing_rule":"","J1_id":"","J2_id":"","evidence_label":label,"confidence_level":label if label in VALID_LABELS else "partial_match_needs_manual_review","source_commit":commit,"source_file":path,"source_line_or_record":line_no,"run_ready_geometry":"false","notes":"candidate-specific current tree/history-index line match"})
    recovered=[]; unresolved=[]
    for cid in sorted(ids):
        goods=[r for r in found[cid] if r["evidence_label"] in VALID_LABELS and complete(r)]
        sigs={tuple(g[k] for k in GEOM) for g in goods}
        if len(sigs)==1 and goods:
            g=goods[0]; g["run_ready_geometry"]="true"; recovered.append(g)
        elif len(sigs)>1:
            unresolved.append(empty(cid,"conflicting_evidence"))
        else:
            unresolved.append(empty(cid,"partial_match_only" if found[cid] else "candidate_id_not_found_in_history"))
    return recovered, unresolved

def empty(cid, reason):
    return {"candidate_id":cid, **{k:"" for k in GEOM}, "pitch_nm":"","period_nm":"","pairing_rule":"","J1_id":"","J2_id":"","evidence_label":"unresolved","confidence_level":"unresolved","source_commit":"","source_file":"","source_line_or_record":"","run_ready_geometry":"false","notes":reason}

def join_ready(recovered, manifest):
    rec={r["candidate_id"]:r for r in recovered}; out=[]
    for m in manifest:
        src=m.get("source_candidate_id","")
        if src in rec:
            r=rec[src]
            out.append({"candidate_id":m.get("candidate_id",""),"source_candidate_id":src,"target_bin_deg":m.get("target_bin_deg",""),"sampling_group":m.get("sampling_group",""),"source_diagnosis_category":m.get("source_diagnosis_category",""),**{k:r.get(k,"") for k in GEOM},"pitch_nm":"","period_nm":"","evidence_label":r["evidence_label"],"confidence_level":r["confidence_level"],"source_commit":r["source_commit"],"source_file":r["source_file"],"source_line_or_record":r["source_line_or_record"],"priority_score":m.get("priority_score",""),"notes":"run-ready geometry recovered from git/current indexed evidence"})
    return out

def table(rows):
    cols=["candidate_id","source_candidate_id","target_bin_deg","sampling_group","H_nm","evidence_label","priority_score"]
    if not rows: return "No rows."
    return "\n".join(["| "+" | ".join(cols)+" |","| "+" | ".join(["---"]*len(cols))+" |"]+["| "+" | ".join(str(r.get(c,"")) for c in cols)+" |" for r in rows[:10]])

def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--report-output", default=str(REPORT))
    parser.add_argument("--decision-output", default=str(DECISION))
    args = parser.parse_args(argv)
    report_path = Path(args.report_output)
    decision_path = Path(args.decision_output)
    assert_not_protected_write_target(report_path, "write", __file__)
    assert_not_protected_write_target(decision_path, "write", __file__)
    if args.dry_run:
        print(json.dumps({"dry_run": True, "report_output": str(report_path), "decision_output": str(decision_path)}, sort_keys=True))
        return 0
    ensure_inputs(); OUT.mkdir(parents=True, exist_ok=True)
    ids=target_ids(); manifest=read_csv(ML1A/"lp_ml1a_seed_manifest.csv")
    idx=history_index(); write_csv(OUT/"lp_ml1a3_history_file_index.csv", idx, INDEX_COLS)
    hits=current_tree_hits(ids); recovered, unresolved=recover(ids,hits)
    write_csv(OUT/"lp_ml1a3_candidate_geometry_recovered.csv", recovered+unresolved, REC_COLS)
    ready=join_ready(recovered, manifest); write_csv(OUT/"lp_ml1a3_run_ready_sources.csv", ready, RUN_COLS)
    write_csv(OUT/"lp_ml1a3_unresolved_sources.csv", [{"candidate_id":u["candidate_id"],"source_candidate_id":u["candidate_id"],"unresolved_reason":u["notes"],**u} for u in unresolved], ["candidate_id","source_candidate_id","unresolved_reason",*REC_COLS])
    labels=Counter(r["evidence_label"] for r in recovered); conflict=sum(1 for u in unresolved if u["notes"]=="conflicting_evidence")
    summary={"unique_target_ids_searched":len(ids),"commits_scanned":len({r['commit'] for r in idx}),"files_scanned":len(idx),"recovered_by_evidence_label":dict(labels),"exact_candidate_csv_json":labels.get("exact_candidate_csv_json",0),"exact_candidate_script_dict":labels.get("exact_candidate_script_dict",0),"exact_candidate_lsf_assignment":labels.get("exact_candidate_lsf_assignment",0),"generator_rule_candidate_specific":labels.get("generator_rule_candidate_specific",0),"unresolved_count":len(unresolved),"conflicting_evidence_count":conflict,"run_ready_count":len(ready),"recovered_count_by_H_nm":dict(Counter(r.get("H_nm","") for r in recovered)),"recovered_count_by_target_bin_deg":dict(Counter(r.get("target_bin_deg","") for r in ready)),"no_fdtd_run":True}
    guarded_write_text(OUT/"lp_ml1a3_summary.json", json.dumps(summary,indent=2,sort_keys=True)+"\n", encoding="utf-8", caller=__file__)
    b300=[r for r in ready if r.get("target_bin_deg")=="300"]; b240=[r for r in ready if r.get("target_bin_deg")=="240"]
    guarded_write_text(report_path, "\n".join(["# LP-ML1A3 Git History Geometry Reconstruction","","Purpose: recover LP dimer numeric geometry from git history and original generator scripts before any LP-ML1B full-wave run.","","LP-ML1B is blocked because LP-ML1A2 found zero run-ready source candidates and LP-ML1A rows are default-range-only scaffold rows.","","Git-history search method: git log --all --name-only indexed lightweight historical files; current indexed files were grepped for exact candidate IDs and accepted only if the same line contained complete numeric geometry. No checkout was performed.","",f"Unique target IDs searched: {summary['unique_target_ids_searched']}",f"Commits scanned: {summary['commits_scanned']}",f"Files scanned: {summary['files_scanned']}",f"Recovered exact_candidate_csv_json count: {summary['exact_candidate_csv_json']}",f"Recovered exact_candidate_script_dict count: {summary['exact_candidate_script_dict']}",f"Recovered exact_candidate_lsf_assignment count: {summary['exact_candidate_lsf_assignment']}",f"Recovered generator_rule_candidate_specific count: {summary['generator_rule_candidate_specific']}",f"Unresolved count: {summary['unresolved_count']}",f"Conflicting evidence count: {summary['conflicting_evidence_count']}",f"Run-ready count: {summary['run_ready_count']}","","## Recovered count by H_nm","```json\n"+json.dumps(summary['recovered_count_by_H_nm'],indent=2,sort_keys=True)+"\n```","## Recovered count by target_bin_deg","```json\n"+json.dumps(summary['recovered_count_by_target_bin_deg'],indent=2,sort_keys=True)+"\n```","## Top recovered B300 sources",table(b300),"","## Top recovered B240 sources",table(b240),"","No FDTD was run.","No Lumerical GUI was opened.","No model was trained.","No K=6 was attempted."]),encoding="utf-8")
    decision="Go" if len(ready)>=20 else "No-Go"; nxt="Recommend LP-ML1B pilot with 20-40 highest-priority run-ready rows." if decision=="Go" else "Recommend LP-ML1A4 explicit new geometry seed generator."
    guarded_write_text(decision_path, f"# LP-ML1A3 Next Action Decision\n\nDecision: {decision} for LP-ML1B pilot.\n\nRun-ready count: {len(ready)}.\n\n{nxt}\n\nWarning: Do not run LP-ML1B from default-range-only manifest rows.\n",encoding="utf-8")
    print(json.dumps(summary,sort_keys=True)); return 0
if __name__ == "__main__": raise SystemExit(main())
