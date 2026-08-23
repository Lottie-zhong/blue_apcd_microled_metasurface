from pathlib import Path
import json

ROOT = Path(r"D:\project\worktrees\blue_apcd_np_k6_mdc_v1")
OUT = ROOT / "outputs/np_k6_final_freeze_closeout_v1"

def test_freeze_status_and_zero_compute():
    x = json.loads((OUT / "freeze_manifest.json").read_text(encoding="utf-8"))
    assert x["status"] == "NP_K6_FROZEN_FORWARD_PROVIDER_COUPLING_HANDOFF_READY"
    assert all(v == 0 for k, v in x["zero_solver_audit"].items() if k != "basis")

def test_provider_scope_and_distinct_components():
    x = json.loads((OUT / "provider_manifest.json").read_text(encoding="utf-8"))
    assert x["scope"]["u_x"] == [0.0]
    assert x["hf_authority"] == {"geometries": 22, "logical_ps_cases": 44, "spectral_rows": 484}
    assert x["components_are_distinct"] is True

def test_angular_handoff_boundaries():
    x = json.loads((OUT / "coupling_handoff.json").read_text(encoding="utf-8"))
    assert x["angular_data_availability"]["row_count"] == 55
    assert x["angular_data_availability"]["unresolved"][0]["u_x"] == 0.22413793103448276
    assert x["angular_data_availability"]["stress_only"][0]["u_x"] == -0.482758620690

def test_expected_lightweight_inventory_exists():
    for name in ("freeze_manifest.json", "provider_manifest.json", "coupling_handoff.json", "capability_boundary.md", "artifact_index.json", "git_state.txt"):
        assert (OUT / name).exists()
