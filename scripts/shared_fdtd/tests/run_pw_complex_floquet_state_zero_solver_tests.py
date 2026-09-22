"""Zero-solver A-J checks for the canonical PW complex-state comparator."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from shared_fdtd.tools.pw_complex_floquet_state_v1 import synthetic_regression_tests  # noqa: E402


EXPECTED = {
    "same_data_different_spatial_sampling": "A",
    "known_single_floquet_mode": "B",
    "multimode_superposition": "C",
    "global_representation_phase": "D",
    "relative_phase_perturbation": "E",
    "order_indexing_positive_x": "F",
    "reference_plane_deembedding": "G",
    "local_medium_basis": "H",
    "wavelength_order": "I",
    "no_power_only_collapse": "J",
}


def main() -> None:
    result = synthetic_regression_tests()
    assert result["status"] == "PASS"
    assert set(result["tests"]) == set(EXPECTED)
    assert all(row["pass"] for row in result["tests"].values())
    print(json.dumps({"schema_version": "PW_COMPLEX_FLOQUET_STATE_ZERO_SOLVER_TESTS_V1", "status": "PASS", "checks": EXPECTED, "solver_invocations": 0}, indent=2))


if __name__ == "__main__":
    main()
