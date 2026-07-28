import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def test_existing_27point_evidence_contract():
 p=ROOT/'outputs/np_k6_p1d2_sixbin_exhaustive_ranking_27point_v1'; m=json.loads((p/'exhaustive_search_manifest.json').read_text()); a=json.loads((p/'d180_participation_audit.json').read_text())
 assert m['diameter_count']==27 and m['real_row_count']==297 and m['enumerated_combination_count']==296010
 assert m['missing_diameters']==[] and a['d180_total_combination_count']==65780 and a['d180_passing_combination_count']==2
