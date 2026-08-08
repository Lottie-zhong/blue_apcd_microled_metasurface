import hashlib
import json
from pathlib import Path

from apcd_coupling.result_schema import validate_result

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/coupling/stage_a_450nm_xpol_normal_textra0_golden_fixture_v1"

def test_completed_result_schema_and_hashes():
    result_path = OUT / "results/result.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    validate_result(result)
    assert result["solver_entered"] is True
    assert result["solver_completed"] is True
    ledger = json.loads((OUT / "runtime/attempt_001/entered_ledger.json").read_text(encoding="utf-8"))
    assert ledger["pre_fsp_sha256"] == result["pre_fsp_sha256"]
    assert result["pre_fsp_post_entry_mutation"]["detected"] is True
    assert result["pre_fsp_current_sha256"] == hashlib.sha256(Path(result["pre_fsp_path"]).read_bytes()).hexdigest()
    assert hashlib.sha256(Path(result["post_fsp_path"]).read_bytes()).hexdigest() == result["post_fsp_sha256"]
    assert result["sign_audit"]["pass"] is True
    assert result["order_closure"]["pass"] is True
    assert result["power_closure"]["pass"] is True

def test_post_fsp_identity_and_standalone_reference_provenance():
    audit = json.loads((OUT / "post_fsp_identity_audit.json").read_text(encoding="utf-8"))
    result = json.loads((OUT / "results/result.json").read_text(encoding="utf-8"))
    assert audit["pass"] is True
    assert all(audit["identity_checks"].values())
    ref = result["standalone_reference"]
    assert ref["source_commit"] == "7a8588f6b5a1c96d88813f60406d418b488135fd"
    assert ref["values"]["eta_plus1"] == 0.7459706928105845
    assert ref["values"]["eta_zero"] == 0.01047848951306206
    assert ref["values"]["eta_minus1"] == 0.005755124074191433
    assert ref["values"]["directionality"] == 0.9923441181014093
