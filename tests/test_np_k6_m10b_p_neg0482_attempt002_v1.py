from pathlib import Path
import csv,json,math
ROOT=Path(r"D:\project\worktrees\blue_apcd_np_k6_mdc_v1")
OUT=ROOT/"outputs/np_k6_m10b_p_neg0482_controlled_numerical_convergence_attempt002_v1"
RUN=ROOT/"outputs/np_k6_m10b_serial_execution_v1/runtime_runs/NP_K6_M10B_ALT1_UX_M0d482758620690_P_XLIKE/attempt_002"
def load(p): return json.loads(p.read_text(encoding="utf-8"))
def test_attempt002_completed_without_replay():
 l=load(RUN/"attempt_ledger.json"); assert l["entered"] is True and l["run_invocation_count"]==1 and l["engine_completed"] and l["post_saved"] and l["controller_returned"]
 assert not (ROOT/"outputs/np_k6_m10b_serial_execution_v1/runtime_runs/NP_K6_M10B_ALT1_UX_M0d482758620690_S_YLIKE/attempt_001").exists()
def test_frozen_gate_and_exact_wavelengths():
 q=load(OUT/"attempt002_quality_gate.json"); assert q["quality_gate_pass"] is False and q["max_closure_residual"]>0.01 and q["max_order_sum_T_mismatch"]<=1e-8 and q["max_normalization_mismatch"]<=1e-8
 with (OUT/"attempt002_spectral_metrics.csv").open(newline="",encoding="utf-8-sig") as f: rows=list(csv.DictReader(f))
 assert len(rows)==11 and [round(float(r["wavelength_nm"])) for r in rows]==list(range(445,456))
 assert all(math.isfinite(float(r["T_total"])) and math.isfinite(float(r["R_total"])) for r in rows)
def test_readonly_reload_provenance_and_hash():
 a=load(OUT/"attempt002_post_reload_readonly_audit.json"); assert a["reload_pass"] and a["independent_readonly_session"] and a["no_run_or_save"] and a["post_sha_unchanged"]
 assert load(OUT/"attempt002_solver_call_reconciliation.json")["recovery_stage_solver_calls"]==0
def test_classification_stops_s():
 d=load(OUT/"decision.json"); assert d["classification"]=="TEMPORAL_UNDERCONVERGENCE_NOT_PRIMARY_CAUSE" and d["S_started"] is False and d["S_authorization_ready"] is False
