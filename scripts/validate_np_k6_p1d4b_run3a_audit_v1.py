import json
from pathlib import Path
o=Path(__file__).resolve().parents[1]/'outputs/np_k6_p1d4b_k6x_phase_candidate_run3a_audit_v1';x=json.loads((o/'canonical_hash_identity_audit.json').read_text());assert x['pre_fsp_recomputed_hash']==x['post_fsp_recomputed_hash'];print('RUN3A_AUDIT_PASS')
