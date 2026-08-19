from __future__ import annotations
import hashlib, json, re
from pathlib import Path

ROOT = Path(r"D:\project\worktrees\blue_apcd_np_k6_mdc_v1")
OUT = ROOT / "outputs/np_k6_m10b_p_neg0482_closure_forensic_v1"
POST = ROOT / "outputs/np_k6_m10b_serial_execution_v1/runtime_runs/NP_K6_M10B_ALT1_UX_M0d482758620690_P_XLIKE/attempt_001/NP_K6_M10B_ALT1_UX_M0d482758620690_P_XLIKE_attempt_001_post.fsp"
PLEDGER = POST.parent / "attempt_ledger.json"
QG = POST.parent / "quality_gate.json"
SCRIPT = ROOT / "scripts/np_k6_m10b_p_neg0482_closure_forensic_v1.py"
EXPECTED_SHA = "60c6f668b0f9fdc64b00b10fa00699314d4f377ac711ed6142290ac7020e67fc"

def sha(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1<<20),b""): h.update(b)
    return h.hexdigest()

def load(name): return json.loads((OUT/name).read_text(encoding="utf-8"))

def main():
    checks=[]
    def c(name, ok): checks.append({"name":name,"pass":bool(ok)})
    required=['per_wavelength_energy.json','per_wavelength_energy.csv','transmitted_orders.csv','material_loss_audit.json','extended_rta_audit.json','source_normalization_audit.json','fixed_ux_audit.json','fixed_ux_reconstruction.csv','boundary_bloch_audit.json','reference_plane_monitor_audit.json','structure_anomaly_audit.json','convergence_audit.json','angular_hf_comparison.json','rcwa_diagnostic_comparison.json','final_classification.json','next_action_recommendation.json','governance_audit.json','provenance_audit.json','extraction_manifest.json']
    c('required_evidence', all((OUT/x).exists() for x in required))
    prov=load('provenance_audit.json'); ext=load('extraction_manifest.json'); gov=load('governance_audit.json'); cls=load('final_classification.json'); mat=load('material_loss_audit.json'); ux=load('fixed_ux_audit.json'); norm=load('source_normalization_audit.json'); energy=load('per_wavelength_energy.json'); struct=load('structure_anomaly_audit.json')
    c('post_sha_unchanged', POST.exists() and sha(POST)==EXPECTED_SHA and prov['post_fsp_unchanged'] is True)
    c('independent_readonly_reload', prov['independent_readonly_reload'] is True and ext['readonly_reload'] is True)
    c('exact_11_finite', ext['exact_wavelengths_nm']==list(range(445,456)) and ext['exact_wavelengths_nm']==[int(round(float(x['wavelength_nm']))) for x in energy['rows']] and energy['all_finite'] is True)
    c('raw_failure_preserved', QG.exists() and json.loads(QG.read_text(encoding='utf-8'))['quality_gate_pass'] is False and abs(float(json.loads(QG.read_text(encoding='utf-8'))['max_closure_residual'])-0.02142121987216855)<1e-12)
    c('all_positive_residuals', all(float(x['closure_RT'])>0 for x in energy['rows']))
    c('order_sum_gate', max(float(x['order_sum_T_mismatch']) for x in energy['rows']) <= 1.1e-15)
    c('normalization_gate', max(max(float(x['normalization_T_mismatch']),float(x['normalization_R_mismatch'])) for x in energy['rows']) <= 2.3e-16)
    c('material_loss_explicit', mat['all_sampled_k_zero'] is True and mat['A_observable'] is False and mat['status']=='ABSORPTION_NOT_DIRECTLY_OBSERVABLE_FROM_SAVED_STATE')
    c('fixed_ux', ux['fixed_ux_drift'] is False and ux['max_abs_error'] <= 1e-15)
    c('structure_gap_explicit', struct['gate_evaluated'] is False and all(x['structure_anomaly'] is None for x in struct['per_wavelength']))
    c('governance_zero_solver', all(gov[k]==0 for k in ['forensic_solver_calls','fdtd_run_calls','fdtd_save_calls','rcwa_calls','replay','attempt_002','attempt_003','S_entry','external_hf','training','inverse']))
    c('S_not_entered', gov['S_state']=='PREPARED_NOT_ENTERED' and not (ROOT/'outputs/np_k6_m10b_serial_execution_v1/runtime_runs/NP_K6_M10B_ALT1_UX_M0d482758620690_S_YLIKE/attempt_001').exists())
    c('classification_allowed', cls['classification'] in {'PHYSICAL_ABSORPTION_NOT_INCLUDED_IN_OLD_RT_CLOSURE_GATE','OBLIQUE_P_NORMALIZATION_IMPLEMENTATION_DEFECT','FIXED_UX_IMPLEMENTATION_DRIFT_CONFIRMED','REFERENCE_PLANE_OR_MONITOR_CONTRACT_DEFECT','OBLIQUE_BOUNDARY_FLUX_ANOMALY','NUMERICAL_CONVERGENCE_RISK_CONFIRMED','TRUE_UNEXPLAINED_FDTD_ENERGY_CLOSURE_FAILURE','MULTIPLE_CAUSES_POSSIBLE_INSUFFICIENT_SAVED_EVIDENCE'})
    c('no_run_save_in_forensic_code', not re.search(r'\.run\s*\(|\.save\s*\(', SCRIPT.read_text(encoding='utf-8')))
    c('quality_threshold_unchanged', load('next_action_recommendation.json')['quality_threshold_changed'] is False)
    pld=json.loads(PLEDGER.read_text(encoding='utf-8')); c('original_attempt_count_one', pld['entered'] is True and pld['run_invocation_count']==1 and pld['engine_completed'] is True and pld['post_saved'] is True and pld['controller_returned'] is True)
    report={'validator':'np_k6_m10b_p_neg0482_closure_forensic_v1','checks':checks,'passed':all(x['pass'] for x in checks),'solver_calls_in_forensic':0,'classification':cls['classification']}
    (OUT/'forensic_validator_report.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2)); raise SystemExit(0 if report['passed'] else 1)

if __name__=='__main__': main()
