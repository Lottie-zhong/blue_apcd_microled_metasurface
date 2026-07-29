import json
from pathlib import Path
o=Path(__file__).resolve().parents[1]/'outputs/np_k6_p1d4b_k6x_phase_candidate_run3a_freeze_v1';l=json.loads((o/'entered_ledger.json').read_text());assert all(l[x] for x in ('entered','engine_completed','controller_returned','post_saved'));assert json.loads((o/'energy_closure_audit.json').read_text())['pass'];print('RUN3A_PASS')
