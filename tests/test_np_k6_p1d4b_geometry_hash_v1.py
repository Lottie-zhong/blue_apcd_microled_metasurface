def test_hash_contract():
 from pathlib import Path
 import json
 o=Path(__file__).resolve().parents[1]/'outputs/np_k6_p1d4b_geometry_hash_reconciliation_v1'
 assert json.loads((o/'legacy_to_canonical_hash_bridge.json').read_text())['rebuild_prefsp'] is False
