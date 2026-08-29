from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np


EXPECTED_FILES = {
    "pair_single_source_stokes.csv",
    "pair_xy_source_cancellation.csv",
    "pair_poincare_relation.csv",
    "pair_useful_lp_normalized.csv",
    "pair_angular_resolved_450nm.npz",
    "pair_angular_resolved_relevant_wavelengths.npz",
    "pair_collection_cone_metrics.csv",
    "pair_angular_cancellation_metrics.csv",
    "pair_450nm_forensic_anchor.json",
    "root_cause_decision.json",
    "audit.json",
    "final_report.md",
}
EXPECTED_FIGURES = {
    "pair_single_source_stokes_spectra.png",
    "pair_poincare_relation.png",
    "pair_angular_dolp_450nm.png",
    "pair_angular_psi_450nm.png",
    "pair_normal_centered_cone_dolp.png",
    "pair_source_vs_angular_decomposition.png",
}


def sha256(path: Path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_csv(path: Path):
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def numeric_csv_check(path: Path):
    rows = read_csv(path)
    if not rows:
        return False, "empty"
    allowed_nan_fields = {"peak_theta_deg_450_only", "peak_phi_deg_450_only"}
    bad = []
    for row_index, row in enumerate(rows, start=2):
        for field, value in row.items():
            if field in allowed_nan_fields and value.strip().lower() == "nan":
                continue
            try:
                number = float(value)
            except (TypeError, ValueError):
                continue
            if not np.isfinite(number):
                bad.append(f"{path.name}:{row_index}:{field}={value}")
    return not bad, bad


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--monitor-state", type=Path)
    args = parser.parse_args()
    root = args.output_dir
    results = {"schema": "PAPER_A_IC2_PAIR_POLARIZATION_CANCELLATION_VALIDATION_V1", "status": "PASS", "checks": {}}
    missing = sorted(name for name in EXPECTED_FILES if not (root / name).is_file())
    results["checks"]["required_files"] = {"pass": not missing, "missing": missing}
    figure_dir = root / "figures"
    missing_figures = sorted(name for name in EXPECTED_FIGURES if not (figure_dir / name).is_file())
    results["checks"]["required_figures"] = {"pass": not missing_figures, "missing": missing_figures}

    csv_checks = {}
    for path in sorted(root.glob("*.csv")):
        passed, detail = numeric_csv_check(path)
        csv_checks[path.name] = {"pass": passed, "detail": detail}
    results["checks"]["finite_csv_values"] = {"pass": all(item["pass"] for item in csv_checks.values()), "files": csv_checks}

    decision = json.loads((root / "root_cause_decision.json").read_text(encoding="utf-8"))
    audit = json.loads((root / "audit.json").read_text(encoding="utf-8"))
    accounting = decision["solver_accounting"]
    zero_fields = {key: accounting.get(key) for key in ("new_fdtd_budget", "solver_run_called_delta", "solver_entered_delta", "fdtd", "rcwa", "ml", "replay")}
    results["checks"]["decision_and_zero_solver"] = {
        "pass": decision.get("status") == "PASS" and decision.get("root_cause_classification") == "BOTH_SOURCE_AND_ANGULAR_CANCELLATION" and all(value == 0 for value in zero_fields.values()) and accounting.get("new_cases_started") == [],
        "root_cause_classification": decision.get("root_cause_classification"),
        "zero_solver_fields": zero_fields,
        "new_cases_started": accounting.get("new_cases_started"),
    }
    results["checks"]["audit_no_new_solver"] = {"pass": audit.get("analysis_tests", {}).get("no_new_solver") is True and audit.get("solver_accounting") == accounting}

    cancellation_rows = read_csv(root / "pair_angular_cancellation_metrics.csv")
    c_values = [float(row["C_source_per_angle_powerweighted"]) for row in cancellation_rows]
    results["checks"]["angular_weighted_cancellation_finite"] = {"pass": bool(c_values) and bool(np.all(np.isfinite(c_values))), "values": c_values}

    useful_rows = read_csv(root / "pair_useful_lp_normalized.csv")
    identity_errors = []
    for row in useful_rows:
        identity_errors.append(abs(float(row["useful_LP_over_S0"]) - 0.5 * (1.0 + float(row["DoLP_xy"]))))
    results["checks"]["useful_lp_normalized_identity"] = {"pass": bool(identity_errors) and max(identity_errors) < 1e-12, "max_abs_error": max(identity_errors) if identity_errors else None}

    anchor = json.loads((root / "pair_450nm_forensic_anchor.json").read_text(encoding="utf-8"))
    results["checks"]["450_anchor"] = {
        "pass": abs(anchor["pair_DoLP"] - 0.037876844117608964) < 1e-12 and abs(anchor["C_linear"] - 0.08854257161559786) < 1e-12 and abs(anchor["angular"]["angular_cancellation"]["C_angular"] - 0.08612761641165362) < 1e-12,
        "pair_DoLP": anchor["pair_DoLP"],
        "C_linear": anchor["C_linear"],
        "C_angular": anchor["angular"]["angular_cancellation"]["C_angular"],
    }

    npz = np.load(root / "pair_angular_resolved_450nm.npz")
    propagating_checks = {}
    for wavelength in (440, 450, 460):
        mask = npz[f"propagating_{wavelength}nm"]
        checks = {}
        for key in ("S0", "S1", "S2", "S3", "DoLP", "DoCP", "psi_deg", "useful_LP_axisfree"):
            values = npz[f"{key}_xy_{wavelength}nm"][mask]
            checks[key] = bool(np.all(np.isfinite(values)))
        propagating_checks[str(wavelength)] = checks
    results["checks"]["angular_npz_finite_inside_propagating_disk"] = {"pass": all(all(item.values()) for item in propagating_checks.values()), "per_wavelength": propagating_checks}

    if args.monitor_state and args.monitor_state.is_file():
        monitor = json.loads(args.monitor_state.read_text(encoding="utf-8-sig"))
        results["checks"]["monitor_snapshot"] = {"pass": monitor.get("global_fdtd_slots") == 0 and monitor.get("running", 0) == 0 and monitor.get("entered_unresolved", False) is False, "global_fdtd_slots": monitor.get("global_fdtd_slots"), "running": monitor.get("running"), "entered_unresolved": monitor.get("entered_unresolved")}
    else:
        results["checks"]["monitor_snapshot"] = {"pass": False, "detail": "monitor state not supplied or unavailable"}

    results["checks"]["artifact_hashes"] = {name: {"sha256": sha256(root / name), "bytes": (root / name).stat().st_size} for name in sorted(EXPECTED_FILES) if (root / name).is_file()}
    boolean_checks = [check for check in results["checks"].values() if "pass" in check]
    results["status"] = "PASS" if all(check["pass"] for check in boolean_checks) else "FAIL"
    (root / "forensic_validation_tests.json").write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(results, ensure_ascii=False))
    raise SystemExit(0 if results["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
