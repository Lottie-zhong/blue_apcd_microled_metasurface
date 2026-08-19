from __future__ import annotations
import csv, hashlib, json, math
from pathlib import Path
ROOT=Path(r"D:\project\worktrees\blue_apcd_np_k6_mdc_v1")
OUT=ROOT/"outputs/np_k6_m10b_p_neg0482_controlled_numerical_convergence_attempt002_v1"
RUN=ROOT/"outputs/np_k6_m10b_serial_execution_v1/runtime_runs/NP_K6_M10B_ALT1_UX_M0d482758620690_P_XLIKE/attempt_002"
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1<<20),b""): h.update(b)
 return h.hexdigest()
def main():
 checks=[]
 def c(name,ok): checks.append({"name":name,"pass":bool(ok)})
 def load(n): return json.loads((OUT/n).read_text(encoding="utf-8"))
 led=load(RUN/"attempt_ledger.json"); q=load("attempt002_quality_gate.json"); dec=load("decision.json"); ra=load("attempt002_post_reload_readonly_audit.json"); recon=load("attempt002_solver_call_reconciliation.json"); prov=load("attempt002_provenance_reconciliation.json")
 post=next(RUN.glob("*_post.fsp")); pref=next((OUT/"runtime_prefsp").glob("*.fsp")); runfsp=next(RUN.glob("*_run.fsp"))
 with (OUT/"attempt002_spectral_metrics.csv").open(newline="",encoding="utf-8-sig") as f: rows=list(csv.DictReader(f))
 c("entered_once",led.get("entered") is True and led.get("run_invocation_count")==1 and recon.get("solver_entered_count")==1)
 c("engine_post_controller",led.get("engine_completed") is True and led.get("post_saved") is True and led.get("controller_returned") is True)
 c("exact_11_finite",len(rows)==11 and all(math.isfinite(float(r[k])) for r in rows for k in ("T_total","R_total","residual","eta_plus1","eta_0","eta_minus1")))
 c("closure_gate_recorded_fail",q.get("quality_gate_pass") is False and q.get("max_closure_residual",0)>0.01)
 c("order_sum_gate",q.get("order_sum_gate_pass") is True and q.get("max_order_sum_T_mismatch",1)<=1e-8)
 c("normalization_gate",q.get("normalization_gate_pass") is True and q.get("max_normalization_mismatch",1)<=1e-8)
 c("post_reload",ra.get("reload_pass") is True and ra.get("independent_readonly_session") is True and ra.get("no_run_or_save") is True)
 c("post_sha_stable",sha(post)==led.get("post_fsp_sha256")==ra.get("post_sha256_before")==ra.get("post_sha256_after"))
 c("run_copy_initial_setup_identity",prov.get("run_copy_initial_sha256")==sha(pref) and prov.get("run_copy_initial_matches_setup") is True)
 c("solver_budget",recon.get("run_invocation_count")==1 and recon.get("recovery_stage_solver_calls")==0 and recon.get("attempt_003") is False and recon.get("S_started") is False)
 c("provenance",prov.get("post_sha_matches_ledger") is True and prov.get("source_prefsp_unchanged") is True and prov.get("external_mdc_fsp_accessed") is False)
 c("classification",dec.get("classification")=="TEMPORAL_UNDERCONVERGENCE_NOT_PRIMARY_CAUSE" and dec.get("S_authorization_ready") is False)
 report={"validator":"validate_np_k6_m10b_p_neg0482_attempt002_v1","checks":checks,"passed":all(x["pass"] for x in checks),"solver_calls":1,"recovery_stage_solver_calls":0}
 (OUT/"attempt002_validator_report.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
 print(json.dumps(report,indent=2))
 raise SystemExit(0 if report["passed"] else 1)
if __name__=="__main__": main()
