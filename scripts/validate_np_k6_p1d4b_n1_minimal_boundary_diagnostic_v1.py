from __future__ import annotations
import csv,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; E=ROOT/'outputs'/'np_k6_p1d4b_k6x_run3c_n1_minimal_boundary_diagnostic_v1'
def j(n): return json.loads((E/n).read_text(encoding='utf-8'))
def main():
 p=j('boundary_diagnostic_preflight.json'); assert p['preflight_pass'] and p['source_prefsp_sha256']=='982057c2d0112644bcf22c5927a53858328fbf1f3b6c23b5ae251aa9c772b63c'
 l=j('entered_ledger.json'); s=j('controller_status.json'); assert l['entered'] and l['engine_completed'] and l['post_saved'] and l['controller_returned'] and s['controller_returned']
 assert j('post_fsp_checksum.json')['sha256']=='92624a63a13b321015274c3ef8ceeaddcaee5bb80afceb65f649444178e58b83'
 rows=list(csv.DictReader((E/'formal_vs_boundary_power_balance_spectrum.csv').open())); assert len(rows)==11
 tr=list(csv.DictReader((E/'boundary_power_three_path_audit.csv').open())); assert max(abs(float(r['path_AB_diff'])) for r in tr)<1e-12
 assert j('boundary_root_cause_classification.json')['classification']=='BOUNDARY_FLUX_BALANCE_CLEAN_FORMAL_CLOSURE_CONFLICT'
 n=j('next_diagnostic_prefsp_checksum.json'); assert n['sha256'] and j('next_diagnostic_setup_diff.json')['changed_numeric_variables']==[]
 assert j('solver_budget_audit.json')['solver_entered']==1 and not j('solver_budget_audit.json')['attempt_002']
 print('PASS boundary diagnostic validator')
if __name__=='__main__': main()
