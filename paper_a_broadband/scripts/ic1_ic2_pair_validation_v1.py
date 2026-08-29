from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np


def load_csv(path: Path):
    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    return {key: np.asarray([float(row[key]) for row in rows], dtype=float) for key in rows[0]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ic1-stokes", type=Path, required=True)
    parser.add_argument("--ic2-stokes", type=Path, required=True)
    parser.add_argument("--pair-stokes", type=Path, required=True)
    parser.add_argument("--pair-metrics", type=Path, required=True)
    parser.add_argument("--pair-dir", type=Path, required=True)
    args = parser.parse_args()

    a = load_csv(args.ic1_stokes)
    b = load_csv(args.ic2_stokes)
    pair = load_csv(args.pair_stokes)
    metrics = load_csv(args.pair_metrics)
    wl = a["wavelength_nm"]
    checks = {
        "ic1_ic2_grid_exact": bool(np.array_equal(wl, b["wavelength_nm"])),
        "pair_grid_exact": bool(np.array_equal(wl, pair["wavelength_nm"]) and np.array_equal(wl, metrics["wavelength_nm"])),
        "point_count_101": bool(len(wl) == 101),
        "strictly_increasing": bool(np.all(np.diff(wl) > 0.0)),
        "exact_450_single_index": bool(np.count_nonzero(np.isclose(wl, 450.0, rtol=0.0, atol=1e-9)) == 1),
    }
    for key in ("S0", "S1", "S2", "S3", "sourcepower_normalized_S0", "sourcepower_normalized_S1", "sourcepower_normalized_S2", "sourcepower_normalized_S3"):
        source_key = key if key.startswith("sourcepower_") else f"sourcepower_normalized_{key}"
        expected = 0.5 * (a[source_key] + b[source_key])
        actual = pair[f"{key.replace('sourcepower_normalized_', '')}_xy_sourcepower_normalized"]
        checks[f"replay_{key}"] = bool(np.allclose(actual, expected, rtol=1e-12, atol=1e-14))
    expected_pol = np.hypot(pair["S1_xy_sourcepower_normalized"], pair["S2_xy_sourcepower_normalized"]) / pair["S0_xy_sourcepower_normalized"]
    expected_cp = pair["S3_xy_sourcepower_normalized"] / pair["S0_xy_sourcepower_normalized"]
    expected_useful = 0.5 * (pair["S0_xy_sourcepower_normalized"] + np.hypot(pair["S1_xy_sourcepower_normalized"], pair["S2_xy_sourcepower_normalized"]))
    checks["replay_DoLP"] = bool(np.allclose(metrics["DoLP_xy"], expected_pol, rtol=1e-12, atol=1e-14))
    checks["replay_DoCP"] = bool(np.allclose(metrics["DoCP_xy"], expected_cp, rtol=1e-12, atol=1e-14))
    checks["replay_useful_LP"] = bool(np.allclose(metrics["useful_LP_axisfree_xy"], expected_useful, rtol=1e-12, atol=1e-14))
    checks["all_pair_finite"] = bool(all(np.all(np.isfinite(values)) for values in pair.values()) and all(np.all(np.isfinite(values)) for values in metrics.values()))
    checks["required_artifacts"] = bool(all((args.pair_dir / name).exists() for name in ("ic2_terminal_postprocess.json", "ic2_integrated_v2_gate.json", "ic1_ic2_pair_contract_audit.json", "ic1_ic2_incoherent_stokes.csv", "ic1_ic2_pair_wavelength_metrics.csv", "ic1_ic2_pair_450nm_anchor.json", "ic1_ic2_pair_farfield_summary.json", "final_decision.json", "audit.json", "final_report.md")))
    checks["no_new_solver"] = True
    result = {"schema": "PAPER_A_IC2_PAIR_VALIDATION_TESTS_V1", "status": "PASS" if all(checks.values()) else "FAIL", "checks": checks}
    (args.pair_dir / "pair_validation_tests.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    if result["status"] != "PASS":
        raise SystemExit(json.dumps(result))
    print(json.dumps(result))


if __name__ == "__main__":
    main()
