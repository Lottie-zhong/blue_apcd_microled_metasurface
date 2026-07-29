import json
from pathlib import Path
o=Path(__file__).resolve().parents[1]/'outputs/np_k6_p1d4b_k6x_broadband_candidate_run3c_freeze_v1';assert json.loads((o/'run3c_extraction_integrity_failure.json').read_text())['classification']=='FULLWAVE_EXTRACTION_INVALID';print('RUN3C_FAILURE_FROZEN')
