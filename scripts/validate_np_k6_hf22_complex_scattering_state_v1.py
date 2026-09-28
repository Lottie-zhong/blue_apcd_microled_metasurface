import json, csv, pathlib, math, sys
ROOT=pathlib.Path(r"D:\\project\\worktrees\\blue_apcd_np_k6_mdc_v1")
OUT=ROOT/"outputs/np_k6_hf22_complex_scattering_state_extraction_v1"
def fail(msg): print("FAIL",msg); raise SystemExit(1)
manifest=json.loads((OUT/"complex_extraction_manifest.json").read_text(encoding="utf-8"))
if manifest.get("solver_run_calls")!=0 or manifest.get("save_calls")!=0 or not manifest.get("load_only"): fail("solver/save/load-only contract")
if manifest.get("case_count")!=44 or manifest.get("spectral_rows")!=484: fail("HF22 counts")
if manifest.get("external_MDC_accessed") or manifest.get("sealed_target_accessed"): fail("scope contamination")
av=json.loads((OUT/"complex_availability_matrix.json").read_text(encoding="utf-8"))
items=av.get("availability",[])
if len(items)!=44 or not all(a.get("load_ok") and a.get("complex_eh_complete") and a.get("gratingvector_ok") and a.get("wavelength_count")==11 for a in items): fail("availability")
with (OUT/"complex_scattering_state_long.csv").open(encoding="utf-8-sig",newline="") as f:
 st=list(csv.DictReader(f))
with (OUT/"complex_power_closure_long.csv").open(encoding="utf-8-sig",newline="") as f:
 cl=list(csv.DictReader(f))
if len(cl)!=968 or len(st)<44*11*7: fail("row counts")
if any(not math.isfinite(float(r["absolute_efficiency"])) for r in st): fail("nonfinite efficiency")
errs=[abs(float(r["modal_minus_formal"])) for r in cl]
trans=[abs(float(r["raw_positive_flux_over_sourcepower"])-float(r["formal_total"])) for r in cl if r["raw_flux_isolated"]=="True"]
if max(errs)>1e-6 or max(trans)>0.05: fail("closure")
if (ROOT/"reports/NP_K6_HF22_COMPLEX_SCATTERING_STATE_EXTRACTION_V1.md").exists() is False: fail("report")
print(json.dumps({"status":"PASS","cases":44,"closure_rows":len(cl),"state_rows":len(st),"modal_max_abs_error":max(errs),"transmission_raw_max_abs_error":max(trans)},indent=2))
