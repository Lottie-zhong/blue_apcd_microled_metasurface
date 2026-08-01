from __future__ import annotations
import csv,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/"outputs"/"np_k6_p1d4b_k6x_run3c_fixed_nested_mesh_n1_v1"
def main():
 l=json.loads((OUT/"entered_ledger.json").read_text());s=json.loads((OUT/"controller_status.json").read_text());c=json.loads((OUT/"n1_fixed_grid_classification.json").read_text());r=list(csv.DictReader((OUT/"n1_spectral_tr_metrics.csv").open()));a=json.loads((OUT/"n1_absolute_order_normalization_audit.json").read_text())
 assert l["entered"] and l["authorized_solver_entered"]==1 and s["controller_returned"]
 assert len(r)==11 and c["classification"]=="N1_FIXED_GRID_SEVERE_CLOSURE_DEFICIT"
 assert a["pass"] and not any(p.suffix.lower() in {".fsp",".npz"}for p in OUT.rglob("*"))
 print("PASS N1 validator")
if __name__=="__main__":main()
