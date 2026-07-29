import json
from pathlib import Path
o=Path(__file__).resolve().parents[1]/'outputs/np_k6_p1d4b_geometry_hash_reconciliation_v1';b=json.loads((o/'legacy_to_canonical_hash_bridge.json').read_text());assert b['classification']=='HASH_DOMAIN_MISMATCH_ONLY';assert json.loads((o/'solver_zero_audit.json').read_text())['solver_calls']==0;print('HASH_RECONCILIATION_PASS')
