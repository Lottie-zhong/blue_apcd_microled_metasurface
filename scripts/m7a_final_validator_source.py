from __future__ import annotations

import csv
import hashlib
import json
import math
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(r"D:/project/worktrees/blue_apcd_np_k6_mdc_v1")
OUT = ROOT / r"outputs/np_k6_m7a_primary4_targeted_hf_acquisition_closeout_v1"
ACQ = ROOT / r"outputs/np_k6_m7a_primary4_hf_acquisition_v1"
DESIGN = ROOT / r"outputs/np_k6_m7a_targeted_development_acquisition_design_v1"
M6 = ROOT / r"outputs/np_k6_m6_formal_development_merge_v1"
ORDERS = [-3, -2, -1, 0, 1, 2, 3]
WLS = set(range(445, 456))
EXPECTED = {
    "G01": "K6X_D135_D155_D190_D220_D225_D230",
    "G02": "K6X_D110_D125_D135_D150_D175_D195",
    "G03": "K6X_D100_D105_D115_D165_D225_D230",
    "G04": "K6X_D100_D105_D110_D115_D190_D230",
}


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def read_csv(path: Path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def check(checks, name, passed, detail=None):
    checks.append({"name": name, "pass": bool(passed), "detail": detail})


def main() -> int:
    checks = []
    prereg = DESIGN / "NP_K6_M7A_TARGETED_ACQUISITION_PREREG_V1.json"
    check(checks, "output_exists", OUT.exists(), str(OUT))
    check(checks, "exact_prereg_hash", prereg.exists() and sha(prereg) == "bd221dfe8d15475cb5c0f9d5959a6595fed2238ff58f7ca1befbdc421bf65951", sha(prereg) if prereg.exists() else None)
    reg = read_csv(ACQ / "primary4_case_registry.csv")
    case_ids = [r["case_id"] for r in reg]
    check(checks, "exact_eight_case_registry", len(case_ids) == 8 and len(set(case_ids)) == 8, case_ids)
    check(checks, "primary4_geometry_identity", all(r["geometry_id"] == EXPECTED[f"G{int(r['slot']):02d}"] for r in reg), {r["case_id"]: r["geometry_id"] for r in reg})
    checks_by_case = {}
    for r in reg:
        p = ACQ / "cases" / r["case_id"] / "attempt_ledger.json"
        if not p.exists():
            checks_by_case[r["case_id"]] = False
            continue
        l = read_json(p)
        checks_by_case[r["case_id"]] = all([l.get("entered") is True, int(l.get("run_invocation_count", 0)) == 1, l.get("engine_completed") is True, l.get("post_saved") is True, l.get("controller_returned") is True, l.get("quality_gate_pass") is True, l.get("training_label") is True, l.get("diagnostic_only") is False])
    check(checks, "all_case_ledgers_quality_adjudicated", all(checks_by_case.values()), checks_by_case)
    check(checks, "no_attempt_002", not any("attempt_002" in str(p) for p in ACQ.rglob("*")), None)
    new = read_csv(OUT / "m7a_hf_observations_88rows.csv")
    old = read_csv(M6 / "formal_development_hf_observations_352rows.csv")
    merged = read_csv(OUT / "m7a_formal_development_hf_observations_440rows.csv")
    check(checks, "exact_new_88_rows", len(new) == 88, len(new))
    check(checks, "exact_existing_352_rows", len(old) == 352, len(old))
    check(checks, "exact_merged_440_rows", len(merged) == 440, len(merged))
    keys = [(r.get("case_id"), int(float(r.get("wavelength_nm", "nan")))) for r in merged]
    check(checks, "duplicate_case_wavelength_zero", len(keys) == len(set(keys)), len(keys) - len(set(keys)))
    geos = {r.get("geometry_id") for r in merged}
    pairs = {(r.get("geometry_id"), r.get("polarization", "").lower()) for r in merged}
    check(checks, "exact_20_geometries", len(geos) == 20, len(geos))
    check(checks, "exact_40_paired_cases", len(pairs) == 40, len(pairs))
    check(checks, "all_exact_wavelengths", all({int(float(r["wavelength_nm"])) for r in merged if r["geometry_id"] == g and r["polarization"].lower() == p} == WLS for g, p in pairs), None)
    check(checks, "new_quality_flags", all(r.get("quality_gate_pass") == "true" and r.get("training_label") == "true" and r.get("diagnostic_only") == "false" for r in new), None)
    check(checks, "new_candidate_label", all(r.get("candidate_performance_label") == "true" for r in new), None)
    old_ids = {r.get("geometry_id") for r in old}
    new_ids = {r.get("geometry_id") for r in new}
    check(checks, "new_vs_existing_geometry_overlap_zero", not old_ids & new_ids, sorted(old_ids & new_ids))
    quarantine = "K6X_D110_D125_D130_D135_D140_D175"
    check(checks, "quarantined_m6_g01_absent", quarantine not in geos, quarantine)
    prov = read_json(OUT / "m7a_provenance_external_sealed_audit.json")
    check(checks, "provenance_conflict_zero", prov.get("duplicate_or_conflicting_provenance") == 0, prov.get("duplicate_or_conflicting_provenance"))
    check(checks, "external_sealed_reads_zero", prov.get("external_target_reads") == 0 and prov.get("sealed_target_reads") == 0, prov)
    check(checks, "external_overlap_zero", prov.get("new_external_overlap") == [], prov.get("new_external_overlap"))
    check(checks, "quarantine_overlap_zero", prov.get("quarantined_overlap") is False, prov.get("quarantined_overlap"))
    lf = read_csv(OUT / "m7a_lf_baseline_88rows.csv")
    lf440 = read_csv(OUT / "m7a_formal_development_lf_baseline_440rows.csv")
    lfkeys = {(r["geometry_id"], r["polarization"].lower(), int(float(r["wavelength_nm"]))) for r in lf}
    hfkeys = {(r["geometry_id"], r["polarization"].lower(), int(float(r["wavelength_nm"]))) for r in new}
    check(checks, "lf_new_exact_88_rows", len(lf) == 88, len(lf))
    check(checks, "lf_new_key_identity", lfkeys == hfkeys, len(hfkeys - lfkeys))
    check(checks, "lf_merged_exact_440_rows", len(lf440) == 440, len(lf440))
    lf_manifest = read_json(OUT / "m7a_dataset_manifest.json")
    check(checks, "normal_incidence_scope", lf_manifest.get("u_x") == 0.0 and lf_manifest.get("k_y") == 0.0, lf_manifest)
    budget = read_json(OUT / "m7a_solver_budget_audit.json")
    check(checks, "solver_budget_exactly_eight", budget.get("m7a_entered_solver") == 8 and budget.get("m7a_run_invocations") == 8, budget)
    check(checks, "no_replacements_or_replays", budget.get("replacements") == 0 and budget.get("replays") == 0 and budget.get("attempt_002_count") == 0, budget)
    trial = read_json(OUT / "m7a_concurrency3_trial_observation.json")
    check(checks, "temporary_trial_only", trial.get("trial_id") == "APCD_PRODUCTION_CONCURRENCY3_TRIAL_V1" and trial.get("global_cap") == 3 and trial.get("fourth_fdtd_authorized") is False, trial)
    check(checks, "no_m8_or_inverse", not any(x in p.name.lower() for p in OUT.iterdir() for x in ["m8", "inverse"]), None)
    forbidden = [str(p.relative_to(OUT)) for p in OUT.rglob("*") if p.is_file() and p.suffix.lower() in {".fsp", ".npz", ".log"}]
    check(checks, "closeout_no_large_runtime_artifacts", not forbidden, forbidden)
    failed = [c for c in checks if not c["pass"]]
    report = {"validator_id": "NP_K6_M7A_PRIMARY4_TARGETED_HF_ACQUISITION_CLOSEOUT_VALIDATOR_V1", "generated_utc": datetime.now(timezone.utc).isoformat(), "status": "PASS" if not failed else "FAIL", "checks": checks, "error_count": len(failed), "solver_calls_during_validation": 0, "sealed_target_reads": 0, "external_target_reads": 0}
    (OUT / "m7a_final_validator_report.json").write_text(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
