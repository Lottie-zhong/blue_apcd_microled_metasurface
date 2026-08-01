from __future__ import annotations
import csv,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"outputs"/"np_k6_p1d4b_k6x_m2_index_diagnostic_run_v1"
def main():
 ledger=json.loads((OUT/"entered_ledger.json").read_text())
 status=json.loads((OUT/"controller_status.json").read_text())
 non=json.loads((OUT/"m2_diagnostic_noninvasiveness_audit.json").read_text())
 grid=json.loads((OUT/"m1_m2_actual_grid_comparison.json").read_text())
 cls=json.loads((OUT/"m1_m2_index_attribution_classification.json").read_text())
 rows=list(csv.DictReader((OUT/"m2_formal_vs_index_diagnostic_11points.csv").open()))
 assert ledger["entered"] and ledger["authorized_solver_entered"]==1
 assert status["engine_completed"] and status["post_fsp_saved"] and status["controller_returned"]
 assert len(rows)==11 and non["classification"]=="DIAGNOSTIC_MONITORS_NONINVASIVE"
 assert grid["nesting"]["classification"]=="NON_NESTED"
 assert cls["classification"]=="M1_M2_DISCRETIZATION_SENSITIVITY_CONFIRMED_ROOT_CAUSE_NOT_UNIQUE"
 assert not any(p.suffix.lower() in {".fsp",".npz"} for p in OUT.rglob("*"))
 print("PASS m2 index diagnostic validator")
if __name__=="__main__":main()
