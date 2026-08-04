from pathlib import Path
import json
import csv
import math

ROOT = Path(r'D:\project\worktrees\blue_apcd_np_k6_mdc_v1')
OUT = ROOT / 'outputs/np_k6_p0_observable_convergence_adjudication_v1'

def test_required_evidence_and_classification():
    required = ['stopped_10ps_attempt_audit.json','label_fidelity_contract_v2.json','convergence_2ps_3ps_spectral_comparison.csv','transmitted_order_convergence.csv','convergence_gate_results.json','convergence_trend_1ps_2ps_3ps.json','generator_v2_contract.json','remaining_anchor_authorization_manifest.json','checksum_manifest.json','provenance_audit.json']
    assert all((OUT / x).is_file() for x in required)
    assert json.loads((OUT/'convergence_gate_results.json').read_text())['all_gates_pass'] is True

def test_11_point_and_order_completeness():
    with (OUT/'convergence_2ps_3ps_spectral_comparison.csv').open(newline='') as f:
        rows=list(csv.DictReader(f))
    assert len(rows)==11
    assert [int(r['wavelength_nm']) for r in rows]==list(range(445,456))
    with (OUT/'transmitted_order_convergence.csv').open(newline='') as f:
        orders=list(csv.DictReader(f))
    assert len(orders)==77
    assert all(math.isfinite(float(r['absolute_efficiency_3ps'])) for r in orders)

def test_no_rerun_and_data_gates():
    stop=json.loads((OUT/'stopped_10ps_attempt_audit.json').read_text())
    assert stop['entered'] is True
    assert stop['run_invocation_count']==1
    assert stop['rerun_forbidden'] is True
    assert stop['recovery_forbidden'] is True
    assert json.loads((OUT/'provenance_audit.json').read_text())['solver_calls_this_round']==0
    rem=json.loads((OUT/'remaining_anchor_authorization_manifest.json').read_text())
    assert rem['all_untouched'] is True
    assert rem['formal_hf_labels']==0

def test_generator_v2_contract():
    d=json.loads((OUT/'generator_v2_contract.json').read_text())
    assert d['generator_id']=='NP_K6_PILOT_FDTD_GENERATOR_FIXED_GRID_3PS_V2'
    assert d['maximum_simulation_time_s']==3e-12
    assert d['auto_shutoff_threshold']==1e-5
    assert d['early_stop_enabled'] is True
