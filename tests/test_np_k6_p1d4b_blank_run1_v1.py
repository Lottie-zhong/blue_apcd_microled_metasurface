import csv,json
from pathlib import Path
R=Path(__file__).resolve().parents[1];E=R/'outputs/np_k6_p1d4b_k6x_blank_run1_freeze_v1'
def test_run1_blank_evidence():
 rows=list(csv.DictReader((E/'spectral_tr_metrics.csv').open()));l=json.loads((E/'entered_ledger.json').read_text());assert len(rows)==11 and l['entered'] and l['engine_completed'] and l['post_saved']
