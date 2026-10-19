import importlib.util
from pathlib import Path


SCRIPT = Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1\scripts\coupling_ml\finite_k6_23um_domain_19um_monitor_singlecase_convergence_probe_v1.py")
spec = importlib.util.spec_from_file_location("probe", SCRIPT)
assert spec is not None and spec.loader is not None
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


def test_singlecase_authority_and_mesh_gate():
    assert probe.CASE == "CONTROL0"
    assert probe.FDTD_NEW_UM == 23.0
    assert probe.MONITOR_NEW_UM == 19.0
    assert probe.case_selection()["selected_case"] == "CONTROL0"
    audit = probe.mesh_audit()
    assert audit["fine_mesh_volume_change"] == 0.0
    assert audit["pass"] is True


def test_zero_solver_offline_derivation():
    assert probe.offline_test() == 0
