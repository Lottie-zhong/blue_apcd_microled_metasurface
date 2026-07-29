from __future__ import annotations
import csv, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/np_k6_p1d4b_k6x_run3c_provenance_recovery_v1'
def main():
 rows=list(csv.DictReader((OUT/'tr_three_path_power_audit.csv').open(encoding='utf-8')))
 assert len(rows)==88
 assert max(abs(float(r['path_a_monitor_T'])-float(r['path_c_eh_poynting_over_source'])) for r in rows)<2e-3
 mat=list(csv.DictReader((OUT/'native_m1_formal_loss_readback_445_455nm.csv').open(encoding='utf-8')))
 assert len(mat)==11 and all(float(r['TiO2_k'])==0 and float(r['SiO2_k'])==0 for r in mat)
 z=json.loads((OUT/'solver_zero_audit.json').read_text(encoding='utf-8'))
 assert z['solver_entered_this_task']==0 and z['run_called'] is False
 print('PASS provenance recovery validator')
if __name__=='__main__':main()
