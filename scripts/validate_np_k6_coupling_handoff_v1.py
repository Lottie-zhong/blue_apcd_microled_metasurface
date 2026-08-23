from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(r"D:\project\worktrees\blue_apcd_np_k6_mdc_v1")
OUT = ROOT / "outputs/np_k6_final_freeze_closeout_v1"
handoff = json.loads((OUT / "coupling_handoff.json").read_text(encoding="utf-8"))
with (ROOT / "outputs/np_k6_m10c_alt1_neg0378_ps_quantitative_anchor_v1/m10c_angular_calibration_5case_55row_registry.csv").open(encoding="utf-8-sig", newline="") as f:
    rows = list(csv.DictReader(f))
groups = {(r["polarization"], float(r["u_x_exact"])) for r in rows}
expected = {("S_YLIKE", 0.22413793103448276), ("P_XLIKE", 0.37868939998860307), ("S_YLIKE", 0.37868939998860307), ("P_XLIKE", -0.3786893999886029), ("S_YLIKE", -0.3786893999886029)}
errors = []
if handoff["contract_id"] != "NP_K6_COUPLING_HANDOFF_CONTRACT_V1": errors.append("contract id")
if handoff["geometry_schema"] != ["D1", "D2", "D3", "D4", "D5", "D6"]: errors.append("geometry schema")
if handoff["phase_order_convention"]["m_plus_1"] != "physical +x": errors.append("phase convention")
if len(rows) != 55 or groups != expected: errors.append("55-row logical cases")
if handoff["angular_data_availability"]["unresolved"][0]["status"] != "UNRESOLVED_NOT_TRUTH_NO_ATTEMPT_003": errors.append("unresolved +0.224 P boundary")
if handoff["angular_data_availability"]["stress_only"][0]["status"] != "RAYLEIGH_STRESS_TEST_ONLY_NOT_QUANTITATIVE_ANCHOR": errors.append("-0.482 stress boundary")
if handoff["recommended_usage"] != ["RCWA baseline", "sparse FDTD calibration", "coupling residual learning"]: errors.append("recommended usage")
print(json.dumps({"status": "PASS" if not errors else "FAIL", "errors": errors, "row_count": len(rows), "logical_case_count": len(groups)}, indent=2))
raise SystemExit(0 if not errors else 1)
