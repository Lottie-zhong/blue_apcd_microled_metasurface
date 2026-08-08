"""Standalone validator for the transactional NP K6 HF pilot dataset."""
from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(r"D:\project\worktrees\blue_apcd_np_k6_mdc_v1")
DATASET = ROOT / "outputs" / "np_k6_hf_pilot_dataset_v1"
WAVELENGTHS = list(range(445, 456))
CASES = [
    "RUN3C_P_PILOT_HF_V1", "RUN3C_S_PILOT_HF_V2",
    "RUN3A_P_PILOT_HF_V1", "RUN3A_S_PILOT_HF_V1",
    "RUN3B_P_PILOT_HF_V1", "RUN3B_S_PILOT_HF_V1",
]


def read_csv(name: str) -> list[dict[str, str]]:
    with (DATASET / name).open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def finite(value: str) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def validate() -> dict:
    decision = json.loads((DATASET / "dataset_decision.json").read_text(encoding="utf-8"))
    manifest = json.loads((DATASET / "pilot_generator_manifest.json").read_text(encoding="utf-8"))
    state = json.loads((DATASET / "pilot_training_state.json").read_text(encoding="utf-8"))
    rows = read_csv("hf_observations_long.csv")
    keys = [(r.get("case_id"), int(float(r["wavelength_nm"]))) for r in rows]
    checks = {
        "dataset_exists": DATASET.is_dir(),
        "formal_observation_count": len(rows) == 66,
        "unique_case_wavelength_rows": len(set(keys)) == 66,
        "canonical_cases": sorted(set(r.get("case_id") for r in rows)) == sorted(CASES),
        "exact_wavelengths_per_case": all(
            sorted(w for c, w in keys if c == case) == WAVELENGTHS for case in CASES
        ),
        "finite_T_R": all(finite(r.get("T_total")) and finite(r.get("R_total")) for r in rows),
        "status": decision.get("status") == "NP_K6_HF_P0_ANCHOR_DATASET_COMPLETE_PILOT_TRAINING_READY",
        "sealed_test_untouched": decision.get("sealed_test_touched") is False and manifest.get("sealed_test_touched") is False,
        "training_not_started": decision.get("training_started") is False and manifest.get("training_started") is False,
        "pilot_training_authorized": decision.get("pilot_training_authorized") is True and state.get("pilot_training_authorized") is True,
        "bulk_training_blocked": decision.get("bulk_mdc_compatible_training_authorized") is False and state.get("bulk_mdc_compatible_training_authorized") is False,
        "checkpoint_zero": decision.get("checkpoint_count") == 0 and state.get("checkpoint_count") == 0,
        "six_anchor_transaction": decision.get("six_anchor_transaction_committed") is True and state.get("anchor_case_count") == 6,
        "generator": manifest.get("generator_id") == "NP_K6_PILOT_FDTD_GENERATOR_FIXED_GRID_3PS_V2",
        "interface_stack": manifest.get("interface_stack_id") == "NP_K6_INDEPENDENT_STACK_PILOT_V1",
    }
    if not all(checks.values()):
        raise SystemExit(json.dumps({"pass": False, "checks": checks}, indent=2))
    return {"pass": True, "checks": checks, "formal_observation_count": len(rows), "case_count": len(CASES)}


if __name__ == "__main__":
    print(json.dumps(validate(), indent=2, sort_keys=True))
