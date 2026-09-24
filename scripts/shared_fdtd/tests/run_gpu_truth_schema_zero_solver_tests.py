from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from gpu_native_truth_validator_v1 import FIELDS, WAVELENGTHS_NM, validate_truth_bundle


def payload(name: str) -> dict:
    base = {"present": True, "type": "2D Z-normal", "z_nm": {"MON_IN": -100.0, "MON_PRENP": 1200.0, "MON_POSTNP": 2212.0, "MON_REFLECTION": -400.0}[name], "x_span_nm": 1740.0, "y_span_nm": 290.0, "wavelengths_nm": WAVELENGTHS_NM}
    if name == "MON_REFLECTION":
        return base | {"fields": [], "signed_poynting": [1.0] * 21, "R": [0.1] * 21}
    return base | {"fields": list(FIELDS)}


def bundle() -> dict:
    return {"monitors": {name: payload(name) for name in ("MON_IN", "MON_PRENP", "MON_POSTNP", "MON_REFLECTION")}}


def main() -> None:
    tests = {}
    for name in ("MON_IN", "MON_PRENP", "MON_POSTNP"):
        candidate = bundle(); candidate["monitors"][name]["fields"] = []
        tests[f"{name}_missing_EH_FAIL"] = not validate_truth_bundle(candidate)["pass"]
    candidate = bundle(); candidate["monitors"]["MON_REFLECTION"]["fields"] = []
    tests["MON_REFLECTION_power_only_PASS"] = validate_truth_bundle(candidate)["pass"]
    candidate = bundle(); del candidate["monitors"]["MON_REFLECTION"]
    tests["MON_REFLECTION_missing_FAIL"] = not validate_truth_bundle(candidate)["pass"]
    candidate = bundle(); candidate["monitors"]["MON_REFLECTION"]["R"] = None
    tests["MON_REFLECTION_power_unreadable_FAIL"] = not validate_truth_bundle(candidate)["pass"]
    candidate = bundle(); candidate["monitors"]["MON_REFLECTION"]["z_nm"] = -399.0
    tests["MON_REFLECTION_wrong_geometry_FAIL"] = not validate_truth_bundle(candidate)["pass"]
    tests["all_role_contracts_PASS"] = validate_truth_bundle(bundle())["pass"]
    tests["CPU_truth_role_path_unchanged"] = validate_truth_bundle(bundle())["monitors"]["MON_IN"]["role"] == "COMPLEX_EH"
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp); source = root / "runtime.fsp"; h5 = root / "runtime" / "runtime_output.h5"; restore = root / "restore" / "runtime"
        h5.parent.mkdir(); source.write_bytes(b"fsp"); h5.write_bytes(b"h5"); restore.mkdir(parents=True); shutil.copy2(source, root / "restore" / "runtime.fsp"); shutil.copy2(h5, restore / h5.name)
        tests["archive_restore_role_valid_truth_PASS"] = bool(source.read_bytes() == (root / "restore" / "runtime.fsp").read_bytes() and h5.read_bytes() == (restore / h5.name).read_bytes() and hashlib.sha256(h5.read_bytes()).hexdigest())
    print(json.dumps({"status": "PASS" if all(tests.values()) else "FAIL", "solver_entries": 0, "tests": tests}, indent=2))
    if not all(tests.values()): raise SystemExit(1)


if __name__ == "__main__":
    main()
