import json,csv
from pathlib import Path
O=Path(__file__).resolve().parents[1]/'outputs/np_k6_p1d4b_k6x_run3c_loss_poynting_recovery_v1'
r=list(csv.DictReader((O/'tr_three_path_power_audit.csv').open()))
assert len(r)==44 and max(abs(float(x['C_minus_A_T'])) for x in r)<.002
d=json.loads((O/'diagnostic_prefsp_checksum.json').read_text());assert d['source_unchanged'] and d['reload_passed']
print('PASS loss-poynting validator')
