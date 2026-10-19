import hashlib
import json
from pathlib import Path

ROOT = Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1\outputs\coupling_v2_2\FINITE_K6_GEOMETRY_AUTHORITY_RESOLUTION_AND_REBUILD_V1")

def test_zero_solver_rebuild_artifacts():
    static = json.loads((ROOT / "STATIC_TEST_RESULTS.json").read_text(encoding="utf-8"))
    diff = json.loads((ROOT / "SCIENTIFIC_PROPERTY_DIFF_AUDIT.json").read_text(encoding="utf-8"))
    air = json.loads((ROOT / "AIR_PADDING_OBJECT_OCCUPANCY_AUDIT.json").read_text(encoding="utf-8"))
    consistency = json.loads((ROOT / "THREE_CASE_CONSISTENCY_AUDIT.json").read_text(encoding="utf-8"))
    accounting = json.loads((ROOT / "SOLVER_ACCOUNTING.json").read_text(encoding="utf-8"))
    assert static["pass"] is True
    assert diff["unexpected_scientific_diff_count"] == 0
    assert air["unexpected_non_background_object_count"] == 0
    assert consistency["pass"] is True
    assert accounting["entered"] == accounting["returned"] == accounting["rerun"] == accounting["training"] == 0

def test_fsp_sha_manifest_roundtrip():
    manifest = json.loads((ROOT / "FINAL_SHA256_MANIFEST.json").read_text(encoding="utf-8"))
    for rel, item in manifest["files"].items():
        assert hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() == item["sha256"]
