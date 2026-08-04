import csv, hashlib, json, math
from pathlib import Path
ROOT=Path(r"D:/project/worktrees/blue_apcd_np_k6_mdc_v1")
EV=ROOT/'outputs/np_k6_p0_simtime_3ps_control_v1'
CASE='RUN3C_P_PILOT_HF_SIMTIME_3PS_CONTROL_V1'
EXPECTED_POST='c14fd3a2464e11c3ba667e4b513bd76a1828c918f80df54511fec7862e2705ca'
def readj(name): return json.loads((EV/name).read_text(encoding='utf-8-sig'))
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for c in iter(lambda:f.read(1<<20),b''): h.update(c)
    return h.hexdigest()
def main():
    errors=[]
    ledger=readj('entered_ledger.json'); checksum=readj('post_fsp_checksum.json'); cls=readj('classification.json'); prov=readj('provenance_audit.json')
    rows=list(csv.DictReader((EV/'spectral_metrics_11points.csv').open(encoding='utf-8')))
    wavelengths=[int(float(r['wavelength_nm'])) for r in rows]
    if ledger.get('case_id')!=CASE or ledger.get('attempt_id')!='attempt_001': errors.append('case_or_attempt')
    if not (ledger.get('entered') is True and ledger.get('run_invocation_count')==1 and ledger.get('engine_completed') is True and ledger.get('post_saved') is True and ledger.get('controller_returned') is True): errors.append('lifecycle')
    if checksum.get('sha256')!=EXPECTED_POST or not checksum.get('stable') or not checksum.get('readonly_reload'): errors.append('post_checksum')
    if not (len(rows)==11 and wavelengths==list(range(445,456))): errors.append('wavelengths')
    if any(not math.isfinite(float(r[k])) for r in rows for k in ('T_total','R_total','signed_closure_residual','eta_plus1','eta_0','eta_minus1')): errors.append('nonfinite')
    if cls.get('C3_pass') is not True or cls.get('G3_pass') is not True: errors.append('closure_or_structure_gate')
    if cls.get('A3_threshold_termination_detected') is not False or cls.get('classification')!='SIMULATION_TIME_3PS_CLOSURE_PASS_DECAY_UNRESOLVED': errors.append('fixed_time_classification')
    if cls.get('formal_hf_label_authorized') or cls.get('training_label') or cls.get('candidate_performance_label'): errors.append('label_promotion')
    raw=readj('raw_power_and_grid_audit.json')
    if raw.get('max_transmission_normalization_mismatch',1)>1e-8 or raw.get('max_reflection_normalization_mismatch',1)>1e-8: errors.append('power_normalization')
    if cls.get('order_mismatch_max',1)>1e-8: errors.append('order_normalization')
    if prov.get('single_variable')!='simulation time 2 ps -> 3 ps' or prov.get('unexpected_physical_differences')!=[]: errors.append('single_variable_provenance')
    result={'validator':'np_k6_p0_simtime_3ps_control_v1','case_id':CASE,'errors':errors,'pass':not errors,'classification':cls.get('classification'),'entered':ledger.get('entered'),'run_invocation_count':ledger.get('run_invocation_count'),'engine_completed':ledger.get('engine_completed'),'post_saved':ledger.get('post_saved'),'controller_returned':ledger.get('controller_returned'),'post_fsp_sha256':checksum.get('sha256'),'exact_11_points':len(rows)==11,'max_abs_closure_residual':cls.get('C3_max_abs_closure_residual'),'structure_448_abs':cls.get('G3_448_structure_abs'),'final_auto_shutoff':cls.get('A3_final_auto_shutoff_observed'),'threshold_termination_detected':cls.get('A3_threshold_termination_detected'),'formal_hf_labels':0,'training_labels':0,'candidate_performance_label':False,'no_rerun':ledger.get('run_invocation_count')==1}
    (EV/'standalone_validator_report.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2,sort_keys=True))
    raise SystemExit(0 if not errors else 1)
if __name__=='__main__': main()
