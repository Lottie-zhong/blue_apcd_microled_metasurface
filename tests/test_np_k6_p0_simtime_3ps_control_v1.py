import csv, json, math
from pathlib import Path
ROOT=Path(r"D:/project/worktrees/blue_apcd_np_k6_mdc_v1")
EV=ROOT/'outputs/np_k6_p0_simtime_3ps_control_v1'
def j(n): return json.loads((EV/n).read_text(encoding='utf-8-sig'))
def test_3ps_closed_single_run_evidence():
    l=j('entered_ledger.json'); c=j('classification.json'); p=j('post_fsp_checksum.json')
    rows=list(csv.DictReader((EV/'spectral_metrics_11points.csv').open(encoding='utf-8')))
    assert l['entered'] is True and l['run_invocation_count']==1 and l['engine_completed'] and l['post_saved'] and l['controller_returned']
    assert [int(float(r['wavelength_nm'])) for r in rows]==list(range(445,456))
    assert all(math.isfinite(float(r['T_total'])) and math.isfinite(float(r['R_total'])) for r in rows)
    assert c['classification']=='SIMULATION_TIME_3PS_CLOSURE_PASS_DECAY_UNRESOLVED'
    assert c['C3_pass'] and c['G3_pass'] and not c['A3_threshold_termination_detected']
    assert not c['formal_hf_label_authorized'] and not c['training_label'] and not c['candidate_performance_label']
    assert p['sha256']=='c14fd3a2464e11c3ba667e4b513bd76a1828c918f80df54511fec7862e2705ca' and p['stable']
