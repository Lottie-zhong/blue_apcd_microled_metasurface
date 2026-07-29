import json
from pathlib import Path
o=Path(__file__).resolve().parents[1]/'outputs/np_k6_p1d4b_k6x_run3c_provenance_recovery_v1';assert json.loads((o/'solver_zero_audit.json').read_text())['new_solver_entered']==0;print('PROVENANCE_PASS')
