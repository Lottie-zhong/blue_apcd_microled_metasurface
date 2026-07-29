import csv,json
from pathlib import Path
R=Path(__file__).resolve().parents[1];O=R/'outputs/np_k6_p1d2_corrected_direction_spotcheck_v1'
def main():
 assert len(list(csv.DictReader((O/'corrected_complex_txx_77rows.csv').open())))==77
 assert len(list(csv.DictReader((O/'corrected_complex_txx_66rows.csv').open())))==66
 p=json.loads((O/'phase_residual_audit.json').read_text());a=json.loads((O/'amplitude_transfer_audit.json').read_text());assert p['direct_rms_deg']<=8 and p['direct_max_deg']<=15 and a['max_common_scale_relative_residual']<=.05;print('PHASE_SALVAGE_METRICS_PASS')
if __name__=='__main__':main()
