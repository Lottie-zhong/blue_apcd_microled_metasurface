from pathlib import Path
import re

ROOT = Path(r"D:\project\worktrees\blue_apcd_np_k6_mdc_v1")

def test_forensic_script_has_no_solver_or_save_call():
    p = ROOT / "scripts/np_k6_m10b_p_neg0482_closure_forensic_v1.py"
    s = p.read_text(encoding="utf-8")
    assert not re.search(r"\.run\s*\(|\.save\s*\(", s)

def test_forensic_evidence_is_zero_solver_and_failure_preserving():
    out = ROOT / "outputs/np_k6_m10b_p_neg0482_closure_forensic_v1"
    gov = (out / "governance_audit.json").read_text(encoding="utf-8")
    cls = (out / "final_classification.json").read_text(encoding="utf-8")
    assert '"forensic_solver_calls": 0' in gov
    assert '"S_entry": 0' in gov
    assert "MULTIPLE_CAUSES_POSSIBLE_INSUFFICIENT_SAVED_EVIDENCE" in cls
