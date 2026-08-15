from pathlib import Path
import csv,json,hashlib,datetime
ROOT=Path(r"D:/project/worktrees/blue_apcd_np_k6_mdc_v1")
OUT=ROOT/"outputs/np_k6_m7a_targeted_development_acquisition_design_v1"
def read(name): return json.loads((OUT/name).read_text(encoding="utf-8"))
def rows(name):
    with (OUT/name).open(encoding="utf-8",newline="") as f:return list(csv.DictReader(f))
def main():
    checks=[]
    def c(name,ok,detail=None): checks.append({"name":name,"pass":bool(ok),"detail":detail})
    pre=read("NP_K6_M7A_TARGETED_ACQUISITION_PREREG_V1.json"); ph=read("preregistration_sha256.json"); sel=read("selection_manifest.json"); uni=read("candidate_universe_audit.json"); zero=read("solver_zero_audit.json")
    actual=hashlib.sha256((OUT/"NP_K6_M7A_TARGETED_ACQUISITION_PREREG_V1.json").read_bytes()).hexdigest()
    c("prereg_hash",actual==ph["sha256"],{"actual":actual,"recorded":ph["sha256"]})
    c("prereg_precedes_selection",ph["fit_or_identity_selection_started_after_preregistration"] is True)
    feats=rows("candidate_acquisition_features.csv"); ids=[r["geometry_id"] for r in feats]; hashes=[r["geometry_hash"] for r in feats]
    c("candidate_count_matches",len(ids)==sel["candidate_universe_size"],len(ids)); c("candidate_ids_unique",len(ids)==len(set(ids))); c("candidate_hashes_unique",len(hashes)==len(set(hashes)))
    c("G01_quarantine_absent",not any(r["geometry_id"]=="K6X_D110_D125_D130_D135_D140_D175" for r in feats)); c("formal_HF16_overlap_zero",not set(ids)&{r["geometry_id"] for r in csv.DictReader((ROOT/"outputs/np_k6_m6_formal_development_merge_v1/formal_development_hf_observations_352rows.csv").open(encoding="utf-8"))}); c("external_overlap_zero",uni["external_overlap"]==[])
    c("ordered_D1_D6",all([float(r[f"D{i}"])<=float(r[f"D{i+1}"]) for r in feats for i in range(1,6)]))
    p4=sel["Primary4"]; roles={x["acquisition_role"] for x in p4}; c("primary4_exact",len(p4)==4 and len({x["geometry_id"] for x in p4})==4); c("primary4_role_quota",roles=={"RESIDUAL-TAIL","RANKING-CHAMPION-STRESS","POLARIZATION-STRESS","COVERAGE-CONTROL"},sorted(roles)); c("backups_at_least_8",len(sel["backups"])>=8); c("first6_exact",len(sel["first6"])==6); c("first8_exact",len(sel["first8"])==8)
    required=["calibrated_eta_plus1","ridge_eta_plus1","residual_mlp_eta_plus1","cnn_eta_plus1","ranking_ambiguity_score","residual_tail_role_score","polarization_stress_role_score","coverage_control_role_score"]
    c("required_acquisition_features",all(x in feats[0] for x in required),required)
    c("solver_zero",all(int(zero.get(k,0))==0 for k in ("fdtd_run_calls","lumapi_solver_run_calls","new_hf_acquisition","external_hf_calls","sealed_hf_target_reads","inverse_design","checkpoint_count")),zero)
    c("external_and_sealed_zero",uni["external_target_reads"]==0 and uni["sealed_target_reads"]==0)
    forbidden=[]
    for p in OUT.rglob("*"):
        if p.is_file() and (p.suffix.lower() in {".fsp",".npz"} or "runtime" in p.name.lower() or "checkpoint" in p.name.lower()): forbidden.append(str(p.relative_to(OUT)))
    c("no_solver_artifacts",not forbidden,forbidden)
    status="PASS" if all(x["pass"] for x in checks) else "FAIL"
    report={"validator":"NP_K6_M7A_TARGETED_ACQUISITION_VALIDATOR_V1","generated_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"status":status,"checks":checks,"candidate_universe_size":len(ids),"solver_calls":0,"external_target_reads":0,"sealed_target_reads":0}
    (OUT/"m7a_validator_report.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2,sort_keys=True)); raise SystemExit(0 if status=="PASS" else 1)
if __name__=="__main__": main()
