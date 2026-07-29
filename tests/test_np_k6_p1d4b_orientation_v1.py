import json
from pathlib import Path
R=Path(__file__).resolve().parents[1];E=R/'outputs/np_k6_p1d4b_source_monitor_orientation_v1'
def test_orientation():
 x=json.loads((E/'corrected_prefsp_inventory.json').read_text());assert len(x)==4
 for a in x:
  assert a['source']['z_nm']<0 and a['source']['direction']=='Forward'
  m={v['name']:v['z_nm'] for v in a['monitors']};assert m['transmission_monitor']==900 and m['reflection_monitor']<0
