import json,csv
from pathlib import Path
R=Path(__file__).resolve().parents[1];O=R/'outputs/np_k6_p1d4b_k6x_corrected_blank_run2_freeze_v1'
def main():
 l=json.loads((O/'entered_ledger.json').read_text());e=json.loads((O/'energy_closure_audit.json').read_text());n=json.loads((O/'blank_n0_dominance_audit.json').read_text());assert l['entered'] and l['engine_completed'] and l['controller_returned'] and l['post_saved'];assert e['pass'] and n['pass'];assert len(list(csv.DictReader((O/'spectral_tr_metrics.csv').open())))==11;print('RUN2_PASS')
if __name__=='__main__':main()
