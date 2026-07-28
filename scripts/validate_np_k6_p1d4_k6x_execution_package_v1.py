import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 f=ROOT/'outputs/np_k6_p1d4_k6x_candidate_freeze_v1';p=ROOT/'outputs/np_k6_p1d4_k6x_execution_package_v1'
 assert len(json.loads((f/'selected_k6x_candidates.json').read_text())['candidates'])==3
 assert json.loads((f/'orientation_sign_convention_contract.json').read_text())['status']=='HARD_GATE_ORIENTATION_AMBIGUOUS'
 assert json.loads((p/'preflight_manifest.json').read_text())['solver_entered']==0
if __name__=='__main__': main()