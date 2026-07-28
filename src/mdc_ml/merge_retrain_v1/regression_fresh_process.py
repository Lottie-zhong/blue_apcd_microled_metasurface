from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import tempfile
from pathlib import Path

import joblib
import numpy as np

from .regression import SEEDS, _predict, _signature

def signature(value: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(np.round(value, 12)).tobytes()).hexdigest()

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture-root", type=Path, required=True)
    parser.add_argument("--input-npz", type=Path, required=True)
    parser.add_argument("--expected-json", type=Path, required=True)
    parser.add_argument("--result-json", type=Path, required=True)
    args = parser.parse_args()
    root = args.fixture_root.resolve(); temp = Path(tempfile.gettempdir()).resolve()
    if os.path.commonpath([str(root).lower(), str(temp).lower()]) != str(temp).lower(): raise ValueError("FRESH_PROCESS_ROOT_MUST_BE_SYSTEM_TEMP")
    if "worktrees" in str(root).lower(): raise ValueError("FRESH_PROCESS_FORBIDDEN_ROOT")
    expected = json.loads(args.expected_json.read_text(encoding="utf8")); arrays = np.load(args.input_npz); held, calibration = arrays["held"], arrays["calibration"]
    bundles = [joblib.load(root / "folds" / "fold_0" / f"seed_{seed}.joblib") for seed in SEEDS]
    held_seed = np.stack([_predict(bundle, held) for bundle in bundles]); cal_seed = np.stack([_predict(bundle, calibration) for bundle in bundles])
    # The synthetic fixture stores no target payload in the child.  It rebuilds the
    # same artifact-dependent ensemble and interval shape; exact calibration
    # quantiles are read from the fold conformal artifact.
    conformal = json.loads((root / "folds" / "fold_0" / "conformal.json").read_text(encoding="utf8")); quantiles = np.asarray(conformal["quantiles"])
    mean = held_seed.mean(axis=0); interval = np.stack((mean - quantiles, mean + quantiles))
    with (root / "regression_oof_sample_predictions.csv").open(newline="", encoding="utf8") as handle:
        eligible_ids = [row["candidate_id"] for row in csv.DictReader(handle)]
    with (root / "regression_ineligible_registry.csv").open(newline="", encoding="utf8") as handle:
        ineligible_ids = [row["candidate_id"] for row in csv.DictReader(handle)]
    actual = {"seed_signatures": [signature(held_seed[index]) for index in range(3)], "ensemble_signature": signature(mean), "interval_signature": signature(interval), "eligibility_signature": _signature(eligible_ids), "ineligibility_signature": _signature(ineligible_ids)}
    result = {"worker_pid": os.getpid(), "parent_pid": expected["parent_pid"], "distinct_process": os.getpid() != expected["parent_pid"], **actual}
    result["all_match"] = result["distinct_process"] and all(result[key] == expected[key] for key in actual)
    result["status"] = "PASS" if result["all_match"] else "FAIL"
    temp_path = args.result_json.with_suffix(".tmp"); temp_path.write_text(json.dumps(result, sort_keys=True, indent=2), encoding="utf8"); os.replace(temp_path, args.result_json)
    print(json.dumps(result, sort_keys=True)); raise SystemExit(0 if result["status"] == "PASS" else 1)

if __name__ == "__main__": main()
