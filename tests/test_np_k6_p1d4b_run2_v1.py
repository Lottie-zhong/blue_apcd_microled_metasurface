import csv,json
from pathlib import Path
def test_run2_evidence_contract():
 o=Path(__file__).resolve().parents[1]/'outputs/np_k6_p1d4b_k6x_corrected_blank_run2_freeze_v1'
 l=json.loads((o/'entered_ledger.json').read_text());e=json.loads((o/'energy_closure_audit.json').read_text());n=json.loads((o/'blank_n0_dominance_audit.json').read_text())
 assert all(l[x] for x in ('entered','engine_completed','controller_returned','post_saved'))
 assert e['pass'] and n['pass']
 assert len(list(csv.DictReader((o/'spectral_tr_metrics.csv').open())))==11
