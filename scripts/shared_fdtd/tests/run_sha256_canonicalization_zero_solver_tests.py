from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1")
sys.path.insert(0, str(ROOT / "scripts"))
from shared_fdtd.engine.persistence import canonical_sha256, sha256_equal


def must_raise(value):
    try:
        canonical_sha256(value)
    except ValueError:
        return True
    return False


def main():
    base = hashlib.sha256(b"APCD-S14-SHA256-FIX").hexdigest()
    upper = base.upper()
    mixed = "".join(ch.upper() if i % 3 == 0 else ch for i, ch in enumerate(base))
    different = ("0" if base[0] != "0" else "1") + base[1:]
    tests = {
        "A_lower_lower": sha256_equal(base, base),
        "B_upper_lower": sha256_equal(upper, base),
        "C_mixed_lower": sha256_equal(mixed, base),
        "D_different_digest_FAIL": not sha256_equal(different, base),
        "E_63_chars_FAIL": not sha256_equal(base[:-1], base),
        "F_65_chars_FAIL": not sha256_equal(base + "0", base),
        "G_non_hex_FAIL": not sha256_equal("g" + base[1:], base),
        "H_empty_null_missing_FAIL": not sha256_equal("", base) and not sha256_equal(None, base) and must_raise(None),
        "I_whitespace_strict_FAIL": not sha256_equal(" " + base, base) and not sha256_equal(base + " ", base),
    }
    attempt = Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1\outputs\coupling_ml\PW_K6_SEED_DB_V1_PRODUCTION_V1\K6V1_S14\attempt_002")
    manifest_path = attempt / "pre_entry_manifest.json"
    ledger_path = attempt / "attempt_ledger.json"
    manifest_bytes_before = manifest_path.read_bytes()
    ledger_bytes_before = ledger_path.read_bytes()
    manifest = json.loads(manifest_bytes_before)
    ledger = json.loads(ledger_bytes_before)
    pre = Path(ledger["pre_fsp"])
    actual = hashlib.sha256(pre.read_bytes()).hexdigest()
    tests["J_exact_S14_upper_manifest_lower_ledger_PASS"] = sha256_equal(manifest["pre_fsp_sha256"], ledger["pre_fsp_sha256"]) and sha256_equal(actual, manifest["pre_fsp_sha256"])
    tests["K_actual_mismatch_still_FAIL"] = not sha256_equal(actual[:-1] + ("0" if actual[-1] != "0" else "1"), ledger["pre_fsp_sha256"])
    tests["L_source_artifacts_unchanged"] = manifest_path.read_bytes() == manifest_bytes_before and ledger_path.read_bytes() == ledger_bytes_before
    tests["M_repeated_validator_idempotent"] = all(sha256_equal(upper, base) for _ in range(25)) and all(canonical_sha256(upper) == base for _ in range(25))
    assert all(tests.values()), tests
    print(json.dumps({"status": "PASS", "solver_invocations": 0, "scientific_solver_entries": 0, "tests": tests, "canonical_digest": base}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
