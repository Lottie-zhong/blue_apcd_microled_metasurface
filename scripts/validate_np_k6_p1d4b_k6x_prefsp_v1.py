from __future__ import annotations
import json
from pathlib import Path
R=Path(__file__).resolve().parents[1];O=R/'outputs/np_k6_p1d4b_k6x_prefsp_freeze_v1'
def main():
 a=json.loads((O/'case_allowlist.json').read_text());i=json.loads((O/'prefsp_inventory.json').read_text());w=json.loads((O/'wavelength_readback.json').read_text());g=json.loads((O/'cyclic_gap_and_aspect_ratio_audit.json').read_text());s=json.loads((O/'solver_zero_audit.json').read_text())
 assert len(a['cases'])==4 and len(i)==4 and [x['case_id'] for x in i]==a['cases']; assert all(x['exact_wavelength_axis_nm']==list(range(445,456)) and x['exact_integer_wavelength_sampling'] for x in w); assert all(x['gap_pass'] and x['aspect_pass'] for x in g); assert s['solver_entered']==0 and not s['solver_run_called']; print('PREFSP_VALIDATION_PASS')
if __name__=='__main__':main()
