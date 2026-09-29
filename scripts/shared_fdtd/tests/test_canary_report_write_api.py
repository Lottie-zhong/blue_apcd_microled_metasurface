from pathlib import Path


HOST = Path(__file__).parents[3] / "scripts" / "shared_fdtd" / "tools" / "run_entered_exception_real_canary_v1.py"


def test_final_report_write_uses_supported_path_api():
    text = HOST.read_text(encoding="utf-8")
    assert "write_text(write_final,encoding='utf-8',newline=" not in text
