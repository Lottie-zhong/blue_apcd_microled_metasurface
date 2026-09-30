from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

SHARED_FDTD_ROOT = Path(__file__).resolve().parents[1]
SERVICE = SHARED_FDTD_ROOT / "tools" / "v3_reconciler_service.py"
SPEC = importlib.util.spec_from_file_location("versioned_reconciler_service_under_test", SERVICE)
SERVICE_MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = SERVICE_MODULE
SPEC.loader.exec_module(SERVICE_MODULE)


def test_reconciler_service_imports_its_own_versioned_backend_without_running_main():
    expected_backend = SERVICE.resolve().parents[3]
    assert SERVICE_MODULE.BACKEND_ROOT.resolve() == expected_backend
    assert Path(sys.path[0]).resolve() == expected_backend / "scripts"
    assert SERVICE_MODULE.DB_PATH == Path(r"D:\apcd_runtime\global_fdtd_control_v3\control.sqlite3")
    assert not (expected_backend / "global_fdtd_control_v3" / "control.sqlite3").exists()
