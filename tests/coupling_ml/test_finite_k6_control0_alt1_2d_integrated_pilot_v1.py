import ast
from pathlib import Path


_candidates = [
    Path(__file__).with_name("finite_k6_control0_alt1_2d_integrated_pilot_v1.py"),
    Path(__file__).parents[2] / "scripts" / "coupling_ml" / "finite_k6_control0_alt1_2d_integrated_pilot_v1.py",
]
SOURCE = next(path for path in _candidates if path.is_file())


def test_integrated_pilot_contract_is_two_case_and_non_mutating():
    text = SOURCE.read_text(encoding="utf-8")
    tree = ast.parse(text)
    assert 'CASES = ("CONTROL0", "ALT1")' in text
    assert "--preflight" in text and "--run-case" in text and "--aggregate" in text
    assert "CONTROL0_ALT1_2D_INTEGRATED_PILOT_V1" in text
    assert "SOURCE_ONLY rerun" not in text
    assert "addfdtd" not in text.lower()
    assert "adddipole" not in text.lower()
    assert not any(isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in {"reset", "restore", "clean", "stash"} for node in ast.walk(tree))
