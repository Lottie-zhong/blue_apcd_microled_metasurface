import csv
from pathlib import Path
R=Path(__file__).resolve().parents[1];O=R/'outputs/np_k6_p1d2_corrected_direction_spotcheck_v1'
def test_spot():assert len(list(csv.DictReader((O/'corrected_spotcheck_long.csv').open())))==77
