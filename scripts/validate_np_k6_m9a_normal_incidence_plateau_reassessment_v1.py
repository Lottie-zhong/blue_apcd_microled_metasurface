from __future__ import annotations
import csv, hashlib, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "np_k6_m9a_normal_incidence_plateau_reassessment_v1"
M9 = ROOT / "outputs" / "np_k6_m9_22g_forward_retraining_v1"
HF22 = ROOT / "outputs" / "np_k6_m8a_primary2_closeout_v1" / "hf22_formal_development_484rows.csv"

def sha(p):
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()
def j(n): return json.loads((OUT / n).read_text(encoding="utf-8"))
def main():
    checks = {}
    p = OUT / "NP_K6_M9A_PLATEAU_REASSESSMENT_PREREG_V1.json"
    expected = j("preregistration_sha256.json")["sha256"]
    checks["m9a_prereg_hash"] = sha(p) == expected
    checks["m9_authority_hash_unchanged"] = j("authority_snapshot.json")["m9_prereg_sha256"] == sha(M9 / "NP_K6_M9_22G_FORWARD_RETRAINING_PREREG_V1.json")
    with HF22.open(newline="", encoding="utf-8") as f: rows = list(csv.DictReader(f))
    checks["hf22_exact_484"] = len(rows) == 484
    checks["hf22_22_geometries"] = len({r["geometry_id"] for r in rows}) == 22
    checks["hf22_ps_pairs"] = len({(r["geometry_id"], r["polarization"]) for r in rows}) == 44
    checks["hf22_11_wavelengths"] = sorted({int(float(r["wavelength_nm"])) for r in rows}) == list(range(445,456))
    checks["hf22_flags"] = all(r.get("quality_gate_pass") == "true" and r.get("diagnostic_only") == "false" and r.get("bulk_mdc_compatible") == "false" and r.get("accepted_execution") in ("true", "") for r in rows)
    z = j("solver_zero_audit.json")
    checks["solver_zero"] = all(z.get(k, 0) == 0 for k in ["fdtd_run_calls","rcwa_run_calls","lumapi_solver_run_calls","new_development_hf","external_hf","sealed_hf_target_reads","inverse_design"])
    checks["external_metadata_only"] = j("external_hf_disposition.json").get("target_reads") == 0 and j("external_hf_disposition.json").get("status") == "HOLD"
    checks["historical_m9_status_preserved"] = j("provenance_audit.json").get("historical_m9_status_preserved") == "NP_K6_M9_22G_FORWARD_MODEL_PLATEAU_REASSESSMENT_REQUIRED"
    checks["capability_matrix_complete"] = len(j("capability_matrix.json").get("rows", [])) == 99
    checks["angular_not_supported"] = all(r["status"] == "NOT_SUPPORTED" for r in j("capability_matrix.json")["rows"] if r["dimension"] == "K_angular_generalization")
    checks["coupling_untouched"] = j("provenance_audit.json").get("coupling_worktree_modified") is False
    checks["decision_status"] = j("decision.json").get("status") == "NP_K6_M9A_NORMAL_INCIDENCE_SCREENING_FROZEN_WAIT_COUPLING_ANGULAR_HANDOFF"
    report = {"validator_id":"NP_K6_M9A_NORMAL_INCIDENCE_PLATEAU_REASSESSMENT_VALIDATOR_V1","checks":checks,"pass":all(checks.values()),"solver_calls":0}
    (OUT / "m9a_validator_report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False))
    return 0 if report["pass"] else 1
if __name__ == "__main__": sys.exit(main())
