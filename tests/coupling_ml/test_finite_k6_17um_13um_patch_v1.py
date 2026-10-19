import hashlib
import json
from pathlib import Path

ROOT = Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1\outputs\coupling_v2_2\FINITE_K6_LATERAL_DOMAIN_17UM_MONITOR_13UM_PATCH_V1")

def test_patch_contract_and_zero_solver():
    contract = json.loads((ROOT / "LATERAL_DOMAIN_PATCH_CONTRACT.json").read_text(encoding="utf-8"))
    diff = json.loads((ROOT / "SCIENTIFIC_PROPERTY_DIFF_14_10_TO_17_13.json").read_text(encoding="utf-8"))
    vertical = json.loads((ROOT / "VERTICAL_PROPERTY_DIFF_AUDIT.json").read_text(encoding="utf-8"))
    air = json.loads((ROOT / "AIR_PADDING_OBJECT_OCCUPANCY_AUDIT.json").read_text(encoding="utf-8"))
    account = json.loads((ROOT / "SOLVER_ACCOUNTING.json").read_text(encoding="utf-8"))
    assert contract["new_fdtd_span_um"] == 17.0
    assert contract["new_monitor_span_um"] == 13.0
    assert diff["unexpected_scientific_diff_count"] == 0
    assert vertical["unexpected_vertical_scientific_diff"] == 0
    assert air["unexpected_non_background_object_count"] == 0
    assert account["entered"] == account["returned"] == account["rerun"] == account["training"] == 0

def test_manifest_and_case_files():
    manifest = json.loads((ROOT / "FINAL_SHA256_MANIFEST.json").read_text(encoding="utf-8"))
    for rel, item in manifest["files"].items():
        assert hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() == item["sha256"]
    for case in ("SOURCE_ONLY", "CONTROL0", "ALT1"):
        assert (ROOT / "cases" / case / "setup_pre.fsp").stat().st_size > 0
