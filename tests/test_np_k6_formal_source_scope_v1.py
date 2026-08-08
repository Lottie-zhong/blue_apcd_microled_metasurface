from pathlib import Path
from scripts.validate_np_k6_formal_source_scope_v1 import validate

def test_formal_source_scope_v1_replays_cleanly():
    assert validate(Path(__file__).resolve().parents[1]) == []
