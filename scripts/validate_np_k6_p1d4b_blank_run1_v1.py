import json
from pathlib import Path
R=Path(__file__).resolve().parents[1];E=R/'outputs/np_k6_p1d4b_k6x_blank_run1_freeze_v1'
def main():
 l=json.loads((E/'entered_ledger.json').read_text());e=json.loads((E/'energy_closure_audit.json').read_text());n=json.loads((E/'blank_n0_dominance_audit.json').read_text());x=json.loads((E/'extraction_manifest.json').read_text());assert l['entered'] and l['engine_completed'] and l['controller_returned'] and l['post_saved'];assert e['pass'] and n['pass'] and x['wavelength_count']==11 and x['finite'];print('RUN1_VALIDATION_PASS')
if __name__=='__main__':main()
