from __future__ import annotations
import csv, json, hashlib, re, subprocess, datetime
from pathlib import Path

ROOT=Path(r"D:\\project\\worktrees\\blue_apcd_np_k6_mdc_v1")
M5=ROOT/"outputs"/"np_k6_m5_fullk6_forward_v0"
M5A=ROOT/"outputs"/"np_k6_m5a_forward_development_promotion_diagnostic_v1"
OUT=ROOT/"outputs"/"np_k6_m5b_forward_formulation_repair_v1"

def sha(p):
 h=hashlib.sha256();
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1<<20),b""): h.update(b)
 return h.hexdigest()
def load(p): return json.loads(p.read_text(encoding="utf-8"))
def check(name,ok,detail): return {"check":name,"pass":bool(ok),"detail":detail}

def main():
 checks=[]
 schema=load(OUT/"NP_K6_AUTHORITATIVE_OUTPUT_SCHEMA_V1.json")
 vector=schema["primary_vector"]; idx={n:i for i,n in enumerate(vector)}
 checks.append(check("authoritative_output_schema", vector==["R","eta_m-3","eta_m-2","eta_m-1","eta_m+0","eta_m+1","eta_m+2","eta_m+3"], vector))
 checks.append(check("eta_plus1_symbolic_index", idx[schema["eta_plus1_symbolic_key"]]==5, {"key":schema["eta_plus1_symbolic_key"],"index":idx[schema["eta_plus1_symbolic_key"]]}))
 pre=load(OUT/"NP_K6_M5B_FORMULATION_REPAIR_PREREG_V1.json"); pre_sha=load(OUT/"m5b_preregistration_sha256.json")["prereg_sha256"]
 checks.append(check("m5b_prereg_hash", sha(OUT/"NP_K6_M5B_FORMULATION_REPAIR_PREREG_V1.json")==pre_sha, pre_sha))
 add_sha=load(OUT/"m5b_refit_addendum_sha256.json")["sha256"]
 checks.append(check("m5b_addendum_hash", sha(OUT/"NP_K6_M5B_FORMULATION_REPAIR_REFIT_ADDENDUM_V1.json")==add_sha, add_sha))
 replay=load(OUT/"m5b_no_refit_replay_manifest.json")
 checks.append(check("no_refit_first", replay.get("refit_count")==0 and replay.get("solver_calls")==0, {"refit_count":replay.get("refit_count"),"solver_calls":replay.get("solver_calls")}))
 manifest=load(OUT/"m5b_refit_manifest.json")
 checks.append(check("refit_manifest_zero_solver", manifest.get("refit_count")==1 and manifest.get("solver_calls")==0 and manifest.get("external_hf_calls")==0 and manifest.get("sealed_target_reads")==0, manifest))
 created=datetime.datetime.fromisoformat(pre["created_utc"]); fit=datetime.datetime.fromisoformat(manifest["fit_started_utc"])
 checks.append(check("prereg_precedes_refit", fit>=created, {"prereg_created":pre["created_utc"],"fit_started":manifest["fit_started_utc"]}))
 rows=list(csv.DictReader((M5/"m5_training_view_286rows.csv").open(encoding="utf-8-sig",newline="")))
 geos={r["geometry_id"] for r in rows}; cases={(r["geometry_id"],r["polarization"]) for r in rows}; wls={int(r["wavelength_nm"]) for r in rows}
 checks.append(check("exact_development_membership", len(rows)==286 and len(geos)==13 and len(cases)==26 and wls==set(range(445,456)), {"rows":len(rows),"geometries":len(geos),"paired_cases":len(cases),"wavelengths":sorted(wls)}))
 checks.append(check("quality_flags", all(r.get("m5_training_label")=="true" and r.get("quality_gate_pass")=="true" and r.get("diagnostic_only")=="false" for r in rows), "all rows"))
 checks.append(check("no_duplicate_case_wavelength", len({(r["case_id"],r["wavelength_nm"]) for r in rows})==286, "286 unique keys"))
 checks.append(check("ux_scope", manifest.get("wavelengths")==list(range(445,456)) and manifest.get("sealed_metadata_only") is True, manifest.get("wavelengths")))
 m5pr=load(M5/"preregistration_sha256.json"); m5a=load(M5A/"preregistration_sha256.json"); m5as=load(M5A/"supplement_preregistration_sha256.json")
 checks.append(check("m5_frozen_prereg_unchanged", sha(M5/"NP_K6_FULLK6_FORWARD_V0_PREREG_V1.json")==m5pr["sha256"], m5pr["sha256"]))
 checks.append(check("m5_frozen_oof_unchanged", sha(M5/"oof_predictions.csv")=="17fb5d5f84b89565df18ee055020541794d682ba197c4193f36fdebcd9591f64", "read-only raw OOF"))
 checks.append(check("m5a_frozen_preregs_unchanged", sha(M5A/"NP_K6_M5A_FORWARD_DIAGNOSTIC_PREREG_V1.json")==m5a["sha256"] and sha(M5A/"NP_K6_M5A_FORWARD_DIAGNOSTIC_SUPPLEMENT_V1.json")==m5as["sha256"], {"m5a":m5a["sha256"],"supplement":m5as["sha256"]}))
 active=(ROOT/"scripts"/"np_k6_m5b_refit_v1.py").read_text(encoding="utf-8")
 forbidden=[pat for pat in [r"a\[ix,\s*4\]",r"a\[ix,\s*5\]",r"\[:,\s*4\]\s*#\s*eta",r"\[:,\s*5\]\s*#\s*eta"] if re.search(pat,active)]
 checks.append(check("no_hardcoded_eta_ranking_index", not forbidden, forbidden))
 checks.append(check("symbolic_residual_reconstruction", "lf[:, eta_i]" in active and "delta_target" in active and "eta_hat" not in active or "LF_eta+delta_hat" in (OUT/"m5b_residual_reconstruction_audit.json").read_text(encoding="utf-8"), "LF plus delta reconstruction"))
 oof=list(csv.DictReader((OUT/"m5b_refit_candidate_oof.csv").open(encoding="utf-8-sig",newline="")))
 checks.append(check("refit_oof_complete", len(oof)>=286*10 and len({(r["case_id"],r["wavelength_nm"]) for r in oof})==286, {"rows":len(oof),"models":sorted({r["model"] for r in oof}),"variants":sorted({r["variant"] for r in oof})}))
 gate=list(csv.DictReader((OUT/"m5b_promotion_gate.csv").open(encoding="utf-8-sig",newline="")))
 checks.append(check("promotion_gate_evaluated", len(gate)>=5 and all("promotion_pass" in r for r in gate), len(gate)))
 final=load(OUT/"m5b_final_decision.json")
 checks.append(check("external_target_zero", final.get("external_target_reads")==0 and final.get("sealed_target_reads")==0 and final.get("solver_calls")==0, final))
 checks.append(check("supersession_map", (OUT/"m5b_supersession_map.json").exists(), "historical artifacts retained"))
 checks.append(check("no_inverse_artifacts", manifest.get("inverse_design_artifacts")==0, manifest.get("inverse_design_artifacts")))
 status="PASS" if all(c["pass"] for c in checks) else "FAIL"
 report={"status":status,"validator_id":"NP_K6_M5B_FORMULATION_REPAIR_VALIDATOR_V1","checks":checks,"solver_calls":0,"external_hf_calls":0,"sealed_target_reads":0,"inverse_design_artifacts":0,"historical_artifacts_modified":False,"generated_utc":datetime.datetime.now(datetime.timezone.utc).isoformat()}
 (OUT/"m5b_validator_report.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
 print(json.dumps({"status":status,"failed":[c for c in checks if not c["pass"]]},indent=2))
 raise SystemExit(0 if status=="PASS" else 1)
if __name__=="__main__": main()
