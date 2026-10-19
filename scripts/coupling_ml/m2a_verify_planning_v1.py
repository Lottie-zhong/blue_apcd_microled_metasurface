import csv
import hashlib
import json
import math
import os
import subprocess
from pathlib import Path

ML = Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1")
NP = Path(r"D:\project\worktrees\blue_apcd_np_k6_mdc_v1")
OUT = ML / r"outputs\coupling_ml\M2A_GEOMETRY_DIVERSITY_SEED_ACQUISITION_PLANNING_V1"
HF = NP / r"outputs\np_k6_m8a_primary2_closeout_v1\hf22_formal_development_484rows.csv"

required = [
    "M2A_NP22_GEOMETRY_CANDIDATE_POOL_V1.csv",
    "M2A_ORDERED_GEOMETRY_DISTANCE_MATRIX_V1.csv",
    "M2A_LEVEL1_RESPONSE_DIVERSITY_MATRIX_V1.csv",
    "M2A_PERFORMANCE_STRATA_V1.csv",
    "M2A_PROVIDER_FEASIBILITY_AUDIT_V1.csv",
    "M2A_SELECTED_GEOMETRY_SEED_SET_V1.json",
    "M2A_CONDITION_INFORMATION_VALUE_AUDIT_V1.csv",
    "M2A_CORE_MINIMAL_ACQUISITION_PLAN_V1.csv",
    "M2A_FULL_MATCHED_ACQUISITION_PLAN_V1.csv",
    "M2A_FUTURE_CANONICAL_ROUTING_CONTRACT_PREFLIGHT_V1.json",
    "M2A_ALT1_ROUTING_ANCHOR_INFORMATION_VALUE_V1.json",
    "M2A_REPORT_V1.md",
    "M2A_SHA256_MANIFEST_V1.json",
]


def sha(p):
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def rows(p):
    with p.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def finite_audit(p):
    if p.suffix.lower() != ".csv": return []
    bad=[]
    for i,r in enumerate(rows(p),2):
        for k,v in r.items():
            if v in {None,""}: continue
            try:
                x=float(v)
            except Exception:
                continue
            if not math.isfinite(x): bad.append({"row":i,"field":k,"value":v})
    return bad


def git(path, args):
    p=subprocess.run(["git",*args],cwd=str(path),capture_output=True,text=True,encoding="utf-8",errors="replace")
    return {"rc":p.returncode,"stdout":p.stdout.strip(),"stderr":p.stderr.strip()}


def main():
    exists={n:(OUT/n).exists() for n in required}
    csv_counts={n:len(rows(OUT/n)) for n in required if (OUT/n).exists() and n.endswith(".csv")}
    manifest=json.loads((OUT/"M2A_SHA256_MANIFEST_V1.json").read_text(encoding="utf-8"))
    sha_ok=[]
    for a in manifest.get("artifacts",[]):
        p=OUT/a["file"]
        sha_ok.append({"file":a["file"],"exists":p.exists(),"expected":a["sha256"],"actual":sha(p) if p.exists() else None,"match":p.exists() and sha(p)==a["sha256"]})
    selected=json.loads((OUT/"M2A_SELECTED_GEOMETRY_SEED_SET_V1.json").read_text(encoding="utf-8"))
    routing=json.loads((OUT/"M2A_FUTURE_CANONICAL_ROUTING_CONTRACT_PREFLIGHT_V1.json").read_text(encoding="utf-8"))
    bridge=json.loads((OUT/"M2A_ALT1_ROUTING_ANCHOR_INFORMATION_VALUE_V1.json").read_text(encoding="utf-8"))
    report=(OUT/"M2A_REPORT_V1.md").read_text(encoding="utf-8")
    with HF.open(encoding="utf-8-sig",newline="") as f: hf_rows=list(csv.DictReader(f))
    hf_geometries=sorted({r.get("geometry_id") for r in hf_rows})
    forbidden=[]
    for p in OUT.rglob("*"):
        if p.is_file() and p.suffix.lower() in {".fsp",".npz",".mat",".h5",".hdf5"}: forbidden.append(str(p))
    report_headings=[x for x in ["STATUS","CANDIDATE_POOL","SELECTED_GEOMETRIES","CONDITION_SELECTION","CORE_PLAN","FULL_PLAN","LEVEL1_FEASIBILITY","FUTURE_ROUTING_CONTRACT","ALT1_ROUTING_BRIDGE","AUDIT","RISKS","NEXT"] if f"## {x}" in report]
    out={
        "required_all_exist":all(exists.values()),"missing_required":[n for n,v in exists.items() if not v],"csv_counts":csv_counts,
        "sha_manifest_artifact_count":manifest.get("artifact_count"),"sha_manifest_all_match":all(x["match"] for x in sha_ok),"sha_checks":sha_ok,
        "selected_geometry_ids":selected.get("selected_geometry_ids"),"selected_count":len(selected.get("selected_geometry_ids",[])),"selected_unique":len(set(selected.get("selected_geometry_ids",[])))==3,
        "candidate_geometries":selected.get("candidate_geometries"),"current_exact_geometries":selected.get("current_exact_geometries"),"projected_exact_geometries_after_core":selected.get("projected_exact_geometries_after_core"),
        "core_jobs":len(rows(OUT/"M2A_CORE_MINIMAL_ACQUISITION_PLAN_V1.csv")),"full_jobs":len(rows(OUT/"M2A_FULL_MATCHED_ACQUISITION_PLAN_V1.csv")),
        "future_routing_contract_feasible":routing.get("future_routing_contract_feasible"),"future_routing_entry_cost":routing.get("future_routing_additional_solver_entry_cost"),
        "bridge_recommended":bridge.get("alt1_routing_anchor_replay_recommended"),"bridge_entries":bridge.get("additional_solver_entries"),
        "hf_rows":len(hf_rows),"hf_geometries":len(hf_geometries),"hf_geometry_hashes_unique":len({r.get("geometry_hash") for r in hf_rows})==22,
        "forbidden_scientific_artifacts_in_output":forbidden,"report_headings":report_headings,"report_headings_complete":len(report_headings)==12,
        "nonfinite_csv_values":{n:finite_audit(OUT/n) for n in required if n.endswith(".csv") and (OUT/n).exists()},
        "zero_compute_audit":manifest.get("zero_compute_audit"),
        "ml_git":{"branch":git(ML,["branch","--show-current"]),"head":git(ML,["rev-parse","HEAD"]),"status_no_untracked":git(ML,["status","--short","--untracked-files=no"]),"upstream":git(ML,["rev-list","--left-right","--count","HEAD...@{u}"])},
    }
    out["pass"] = out["required_all_exist"] and out["sha_manifest_all_match"] and out["selected_count"]==3 and out["selected_unique"] and out["candidate_geometries"]==22 and out["hf_rows"]==484 and out["hf_geometries"]==22 and out["core_jobs"]==9 and out["full_jobs"]==12 and out["future_routing_contract_feasible"] is True and out["future_routing_entry_cost"]==0 and not forbidden and out["report_headings_complete"] and all(not x for x in out["nonfinite_csv_values"].values())
    print(json.dumps(out,ensure_ascii=False,indent=2))


if __name__ == "__main__": main()
