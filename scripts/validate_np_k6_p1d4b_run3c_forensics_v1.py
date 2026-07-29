import json
from pathlib import Path
o=Path(__file__).resolve().parents[1]/'outputs/np_k6_p1d4b_k6x_run3c_closure_forensics_v1';assert json.loads((o/'run3c_failure_layer_classification.json').read_text())['order_to_T_pass'];print('FORENSICS_PASS')
