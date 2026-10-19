import hashlib
import json
from pathlib import Path


ROOT = Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1") / "outputs" / "coupling_v2_2" / "FINITE_K6_FINAL_LATERAL_DOMAIN_19UM_MONITOR_15UM_PATCH_V1"


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def test_final_19_15_patch_artifacts():
    assert ROOT.is_dir()
    report = load("REPORT.json")
    assert report["verdict"] == "PASS — FINITE_K6_19UM_DOMAIN_15UM_MONITOR_MODEL_READY_FOR_HUMAN_GUI_SIGNOFF"
    assert report["unexpected_scientific_diff_count"] == 0

    contract = load("LATERAL_DOMAIN_PATCH_CONTRACT.json")
    assert contract["old_fdtd_span_um"] == 17.0
    assert contract["new_fdtd_span_um"] == 19.0
    assert contract["old_monitor_span_um"] == 13.0
    assert contract["new_monitor_span_um"] == 15.0
    assert contract["solver_entry"] is False

    static = load("STATIC_TEST_RESULTS.json")
    assert static["pass"] is True
    assert static["solver_entry_delta"] == 0
    assert static["returned"] == 0
    assert static["rerun_delta"] == 0

    envelope = load("SOURCE_POSITION_OFFAXIS_ENVELOPE_V2.json")
    assert envelope["future_envelope_supported"] is True
    assert all(row["integrated_k6_monitor_margin_um"] >= 0 for row in envelope["source_positions"])

    margin = load("MONITOR_TO_PML_MARGIN_AUDIT_V2.json")
    assert margin["monitor_not_in_pml"] is True
    assert margin["monitor_edge_to_effective_pml_start_budget_um"] == 0.8

    mesh = load("LATERAL_DOMAIN_MESH_COST_AUDIT_V2.json")
    assert mesh["old_estimated_cells"] == 1413125
    assert mesh["new_estimated_cells"] == 1421875
    assert mesh["fine_mesh_volume_relative_increase"] == 0.0

    accounting = load("SOLVER_ACCOUNTING.json")
    assert accounting["entered"] == accounting["returned"] == accounting["rerun"] == accounting["training"] == 0
    for case in ("SOURCE_ONLY", "CONTROL0", "ALT1"):
        fsp = ROOT / "cases" / case / "setup_pre.fsp"
        assert fsp.is_file() and fsp.stat().st_size > 0

    manifest = load("FINAL_SHA256_MANIFEST.json")["files"]
    assert manifest
    for relative, record in manifest.items():
        path = ROOT / relative
        assert path.is_file()
        assert path.stat().st_size == record["size"]
        assert digest(path) == record["sha256"]
