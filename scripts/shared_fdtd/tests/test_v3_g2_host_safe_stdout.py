import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HOST = ROOT / "tools" / "v3_g2_host.py"
sys.path.insert(0, str(ROOT.parent))


spec = importlib.util.spec_from_file_location("shared_v3_g2_host_under_test", HOST)
host = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = host
spec.loader.exec_module(host)


def test_safe_stdout_ignores_closed_stdout(monkeypatch):
    class ClosedStdout:
        def write(self, _value):
            raise OSError(22, "Invalid argument")

        def flush(self):
            raise OSError(22, "Invalid argument")

    monkeypatch.setattr(host.sys, "stdout", ClosedStdout())
    assert host.safe_stdout({"status": "PASS"}) is False


def test_safe_stdout_returns_true_for_normal_capture(capsys):
    assert host.safe_stdout({"status": "PASS"}) is True
    assert '"status": "PASS"' in capsys.readouterr().out
