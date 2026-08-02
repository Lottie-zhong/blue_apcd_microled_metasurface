from __future__ import annotations
import json,csv
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; E=ROOT/'outputs'/'np_k6_p1d4b_k6x_run3c_n1_power_normalization_reassessment_v1'
def j(n): return json.loads((E/n).read_text(encoding='utf-8'))
def main():
 inv=j('sourcepower_diagnostic_attempt_inventory.json'); assert not inv['authorized_solver_entered'] and not inv['scheduler_exists'] and not inv['post_fsp_exists']
 f=j('sourcepower_redundancy_forensic.json'); assert f['sourcepower_diagnostic_entered'] is False and f['sourcepower_cannot_explain_structure_gain'] is True and f['max_monitor_T_vs_raw_sourcepower_difference']<1e-12
 assert j('sourcepower_normalization_final_classification.json')['classification']=='SOURCEPOWER_NORMALIZATION_EFFECTIVELY_RULED_OUT'
 assert j('structure_interval_nonconservation_classification.json')['classification']=='STRUCTURE_INTERVAL_NUMERICAL_NONCONSERVATION_CONFIRMED'
 c=j('conformal_diagnostic_prefsp_contract.json'); assert c['solver_entered']==0 and c['modified_field']['property']=='mesh refinement' and c['modified_field']['after']=='conformal variant 1'
 d=j('conformal_diagnostic_setup_diff.json'); assert d['diff_is_exactly_one_field'] and d['added_objects']==[] and d['deleted_objects']==[]
 assert j('solver_zero_audit.json')['additional_solver_entered']==0
 print('PASS reassessment validator')
if __name__=='__main__': main()
