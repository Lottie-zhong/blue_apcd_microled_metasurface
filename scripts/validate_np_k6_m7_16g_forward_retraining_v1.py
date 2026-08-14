from __future__ import annotations
import csv, hashlib, json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(r"D:/project/worktrees/blue_apcd_np_k6_mdc_v1")
OUT=ROOT/"outputs/np_k6_m7_16g_forward_retraining_v1"
DATA=ROOT/"outputs/np_k6_m6_formal_development_merge_v1/formal_development_hf_observations_352rows.csv"
ORDERS=[-3,-2,-1,0,1,2,3]; WLS=list(range(445,456))

def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()
def j(p): return json.loads(p.read_text(encoding="utf-8-sig"))
def rows(p):
 with p.open(encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))
def check(name, passed, detail): return {"check":name,"pass":bool(passed),"detail":detail}
def main():
 checks=[]; errors=[]
 checks.append(check("output_exists",OUT.exists(),str(OUT)))
 data=rows(DATA); geos=sorted({r["geometry_id"] for r in data}); keys=[(r["case_id"],int(float(r["wavelength_nm"]))) for r in data]
 checks += [check("exact_352_rows",len(data)==352,len(data)),check("exact_16_geometries",len(geos)==16,len(geos)),check("32_paired_PS_cases",len({(r["geometry_id"],r["polarization"]) for r in data})==32,len({(r["geometry_id"],r["polarization"]) for r in data})),check("row_duplicate_zero",len(keys)==len(set(keys)),len(keys)-len(set(keys))),check("exact_wavelengths",all({int(float(r["wavelength_nm"])) for r in data}==set(WLS) for g in geos for p in ["p","s"]),WLS),check("M6_G01_quarantine_absent",not any("NP_K6_M6_PRIMARY4_G01" in r["case_id"] for r in data),True)]
 checks.append(check("formal_flags",all(r.get("quality_gate_pass")=="true" and r.get("diagnostic_only")=="false" for r in data),"quality_gate_pass=true, diagnostic_only=false"))
 lf=rows(OUT/"lf_baseline_352rows.csv"); lfkeys=[(r["geometry_id"],r["polarization"],int(float(r["wavelength_nm"]))) for r in lf]; datakeys=[(r["geometry_id"],r["polarization"].lower(),int(float(r["wavelength_nm"]))) for r in data]
 checks += [check("LF_exact_352_rows",len(lf)==352,len(lf)),check("LF_key_identity",set(lfkeys)==set(datakeys),len(set(datakeys)-set(lfkeys))),check("LF_16G_coverage",len({r["geometry_id"] for r in lf})==16,len({r["geometry_id"] for r in lf})),check("LF_authority_complete",j(OUT/"lf_authority_completion.json").get("coverage_complete") is True,True)]
 pre=OUT/"NP_K6_M7_16G_FORWARD_RETRAINING_PREREG_V1.json"; pre_sha=j(OUT/"preregistration_sha256.json"); run=j(OUT/"m7_training_run_manifest.json")
 checks += [check("prereg_hash",sha(pre)==pre_sha.get("sha256"),{"actual":sha(pre),"recorded":pre_sha.get("sha256")}),check("prereg_before_fit",pre.stat().st_mtime_ns < (OUT/"model_metrics_raw.csv").stat().st_mtime_ns,True),check("fit_after_prereg",run.get("fit_started_after_preregistration") is True,run.get("fit_started_after_preregistration")),check("cv_16_LOGO",len(rows(OUT/"fold_manifest.csv"))==16 and len({r["held_out_geometry"] for r in rows(OUT/"fold_manifest.csv")})==16,len(rows(OUT/"fold_manifest.csv"))),check("fold_local_normalization",all(int(r["normalization_train_rows"])==330 for r in rows(OUT/"fold_manifest.csv")),True)]
 expected={"LF_only","LF_global_bias","LF_affine","LF_ridge_residual","LF_paired_shared_contrast","corrected_residual_mlp","direct_mlp","resmlp","circular_cnn"}; mm=rows(OUT/"model_metrics_raw.csv"); checks += [check("model_family_identity",{r["model"] for r in mm}==expected,sorted({r["model"] for r in mm})),check("raw_constrained_metrics",(OUT/"model_metrics_constrained.csv").exists(),True),check("OOF_complete",len(rows(OUT/"oof_predictions_16g.csv"))==352*len(expected),len(rows(OUT/"oof_predictions_16g.csv")))]
 ext=j(OUT/"external_set_readiness.json"); sol=j(OUT/"solver_zero_audit.json"); checks += [check("external_metadata_only",ext.get("geometry_count")==12 and ext.get("sealed_target_reads")==0 and ext.get("external_target_reads")==0,ext),check("solver_zero",all(sol.get(k)==0 for k in ("fdtd_run_calls","lumapi_solver_run_calls","new_hf_acquisition","external_hf_calls","sealed_hf_target_reads","inverse_design")),sol),check("no_inverse_artifacts",not any("inverse" in p.name.lower() for p in OUT.iterdir()),[p.name for p in OUT.iterdir() if "inverse" in p.name.lower()])]
 checks.append(check("symbolic_output_contract",j(pre).get("output_contract",{}).get("eta_plus1_symbolic_key")=="eta_m+1",j(pre).get("output_contract")))
 for c in checks:
  if not c["pass"]: errors.append(c)
 report={"validator_id":"NP_K6_M7_16G_FORWARD_RETRAINING_VALIDATOR_V1","generated_utc":datetime.now(timezone.utc).isoformat(),"status":"PASS" if not errors else "FAIL","checks":checks,"error_count":len(errors),"solver_calls":0,"sealed_target_reads":0,"external_target_reads":0}
 (OUT/"m7_validator_report.json").write_text(json.dumps(report,indent=2,sort_keys=True,ensure_ascii=False)+"\n",encoding="utf-8")
 print(json.dumps(report,indent=2,ensure_ascii=False))
 raise SystemExit(0 if not errors else 1)
if __name__=="__main__": main()
