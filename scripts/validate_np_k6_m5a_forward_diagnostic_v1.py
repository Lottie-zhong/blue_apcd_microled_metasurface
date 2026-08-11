"""Standalone validator for the zero-solver NP K6 M5A diagnostic."""
from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if not (ROOT / "outputs" / "np_k6_m5a_forward_development_promotion_diagnostic_v1").exists():
    ROOT = Path(r"D:\project\worktrees\blue_apcd_np_k6_mdc_v1")
OUT = ROOT / "outputs" / "np_k6_m5a_forward_development_promotion_diagnostic_v1"
M5 = ROOT / "outputs" / "np_k6_m5_fullk6_forward_v0"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def read_json(name: str) -> dict:
    return json.loads((OUT / name).read_text(encoding="utf-8"))


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def validate(root: Path | None = None) -> dict:
    global ROOT, OUT, M5
    if root is not None:
        ROOT = Path(root)
        OUT = ROOT / "outputs" / "np_k6_m5a_forward_development_promotion_diagnostic_v1"
        M5 = ROOT / "outputs" / "np_k6_m5_fullk6_forward_v0"
    checks: dict[str, object] = {}
    errors: list[str] = []

    prereg_path = OUT / "NP_K6_M5A_FORWARD_DIAGNOSTIC_PREREG_V1.json"
    prereg_sha = read_json("preregistration_sha256.json")
    checks["preregistration_hash"] = sha256(prereg_path)
    if checks["preregistration_hash"] != prereg_sha["sha256"]:
        errors.append("M5A preregistration hash mismatch")
    prereg = json.loads(prereg_path.read_text(encoding="utf-8"))
    if not prereg.get("m5_frozen_inputs"):
        errors.append("M5 frozen-input hashes absent")
    else:
        m5_prereg_sha = json.loads((M5 / "preregistration_sha256.json").read_text(encoding="utf-8"))["sha256"]
        if prereg["m5_frozen_inputs"].get("m5_prereg_sha256") != m5_prereg_sha:
            errors.append("M5 preregistration identity changed")
        if prereg["m5_frozen_inputs"].get("m5_oof_sha256") != sha256(M5 / "oof_predictions.csv"):
            errors.append("M5 OOF identity changed")
    manifest = read_json("m5a_run_manifest.json")
    fit_time = manifest.get("fit_started_utc", "")
    checks["prereg_precedes_fit"] = bool(prereg.get("created_utc", "") < fit_time)
    if not checks["prereg_precedes_fit"]:
        errors.append("fit did not follow preregistration")

    view = read_rows(M5 / "m5_training_view_286rows.csv")
    geos = {r["geometry_id"] for r in view}
    cases = {(r["geometry_id"], r["polarization"]) for r in view}
    wls = {int(float(r["wavelength_nm"])) for r in view}
    checks.update({"rows": len(view), "geometry_count": len(geos), "paired_case_count": len(cases), "wavelength_count": len(wls)})
    if (len(view), len(geos), len(cases), len(wls)) != (286, 13, 26, 11):
        errors.append("286-row authority membership mismatch")
    if {r["polarization"] for r in view} != {"p", "s"}:
        errors.append("P/S identity mismatch")
    if not all(r.get("m5_training_label") == "true" and r.get("quality_gate_pass") == "true" and r.get("diagnostic_only") == "false" for r in view):
        errors.append("formal quality flags are not all valid")

    for name in [
        "m3_m5_common_subset_comparison.csv", "batch2_primary4_error_audit.csv",
        "m5a_2x2_ablation_metrics.csv", "lf_residual_summary.csv", "promotion_gate.csv",
    ]:
        if not (OUT / name).exists():
            errors.append(f"missing output: {name}")
    checks["common_rows"] = len(read_rows(OUT / "m3_m5_common_subset_comparison.csv"))
    checks["batch2_rows"] = len(read_rows(OUT / "batch2_primary4_error_audit.csv"))
    checks["ablation_rows"] = len(read_rows(OUT / "m5a_2x2_ablation_metrics.csv"))
    if checks["common_rows"] != 3 or checks["batch2_rows"] != 12 or checks["ablation_rows"] != 4:
        errors.append("forensic comparison row count mismatch")

    residual = read_json("m5_residual_reconstruction_audit.json")
    checks["residual_bug_confirmed"] = residual.get("classification") == "IMPLEMENTATION_RECONSTRUCTION_BUG_CONFIRMED"
    checks["correct_residual_formula"] = residual.get("correct_formula") == "eta_hat=LF_eta+delta_hat"
    if not checks["residual_bug_confirmed"] or not checks["correct_residual_formula"]:
        errors.append("residual reconstruction audit incomplete")
    rank = read_json("m5_ranking_contract_audit.json")
    checks["ranking_mixup_confirmed"] = rank.get("classification") == "M5_FROZEN_RANKING_INDEX_MIXUP_CONFIRMED"
    checks["eta_plus1_index"] = rank.get("canonical_eta_plus1_index_in_full_vector")
    if not checks["ranking_mixup_confirmed"] or checks["eta_plus1_index"] != 5 or not rank.get("m5_frozen_evidence_modified") is False:
        errors.append("ranking contract audit incomplete")

    promotion = read_json("promotion_decision.json")
    checks["learned_full_response_pass"] = promotion.get("learned_full_response_pass")
    checks["external_authorization"] = promotion.get("external_authorization")
    if promotion.get("learned_full_response_pass") is not False or promotion.get("external_authorization") is not False:
        errors.append("promotion/external gate is not closed")
    solver = read_json("solver_zero_audit.json")
    checks["solver_zero"] = all(solver.get(k) == 0 for k in ["solver_calls", "fdtd_run_calls", "lumapi_solver_run_calls", "external_hf_calls", "sealed_target_reads", "inverse_design_artifacts"])
    if not checks["solver_zero"]:
        errors.append("nonzero solver or sealed access count")
    registry = M5 / "external_set_registry.json"
    if registry.exists():
        reg = json.loads(registry.read_text(encoding="utf-8"))
        checks["external_geometry_count"] = len(reg.get("geometries", reg.get("geometry_ids", [])))
        if reg.get("target_read_count", reg.get("sealed_target_reads", 0)) != 0:
            errors.append("sealed target metadata gate violated")
    else:
        errors.append("external registry missing")

    checks["errors"] = errors
    checks["status"] = "PASS" if not errors else "FAIL"
    report = OUT / "m5a_validator_report.json"
    report.write_text(json.dumps(checks, indent=2, sort_keys=True, allow_nan=False), encoding="utf-8")
    if errors:
        raise AssertionError("; ".join(errors))
    return checks


if __name__ == "__main__":
    print(json.dumps(validate(), indent=2, sort_keys=True))
