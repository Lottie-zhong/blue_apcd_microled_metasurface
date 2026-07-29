import json
from pathlib import Path
o=Path(__file__).resolve().parents[1]/'outputs/np_k6_p1d4b_k6x_transmission_candidate_run3b_freeze_v1';assert json.loads((o/'energy_closure_audit.json').read_text())['pass'];print('RUN3B_PASS')
