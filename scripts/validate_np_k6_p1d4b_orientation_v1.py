import json
from pathlib import Path
R=Path(__file__).resolve().parents[1];E=R/'outputs/np_k6_p1d4b_source_monitor_orientation_v1'
def main():
 a=json.loads((E/'source_monitor_orientation_audit.json').read_text());i=json.loads((E/'corrected_prefsp_inventory.json').read_text());assert a['corrected_pass'] and len(i)==4 and all(x['source']['z_nm']<0 and x['source']['direction']=='Forward' for x in i);print('ORIENTATION_VALIDATION_PASS')
if __name__=='__main__':main()
