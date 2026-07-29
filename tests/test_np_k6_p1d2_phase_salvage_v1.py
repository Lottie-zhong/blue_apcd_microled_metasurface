import csv
from pathlib import Path
R=Path(__file__).resolve().parents[1];O=R/'outputs/np_k6_p1d2_corrected_direction_spotcheck_v1'
def test_rows():assert len(list(csv.DictReader((O/'corrected_complex_txx_77rows.csv').open())))==77
