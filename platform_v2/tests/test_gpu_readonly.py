from copy import deepcopy

import pytest

from apcd_gpu_v2.gpu_readonly import EDT, LICENSE, evaluate_idle_edt, wddm_exclusivity
from apcd_gpu_v2 import gpu_readonly, serial
from apcd_gpu_v2.ledger import Refused


def evidence():
    record=dict(pid=123,creation_time=1.,executable=str(EDT))
    return [record,[str(EDT),'N:/other/project.aedt'],[dict(executable=str(LICENSE))],[[dict(name='pid_123_luid_0_engtype_Compute',utilization=0)] for _ in range(3)]]


def test_positive_idle_gui():
    args=evidence()
    args[0].update(classification='SCIENCE_OR_UNATTRIBUTED',command=args[1],reported_memory='[N/A]')
    result=evaluate_idle_edt(*args)
    assert result['classification']=='VERIFIED_IDLE_EDT_GUI'
    assert result['reported_memory']=='[N/A]'


@pytest.mark.parametrize('fault',['compute','render','pid','sample','child','command','image','malformed'])
def test_idle_exception_requires_complete_evidence(fault):
    args=deepcopy(evidence())
    if fault in ['compute','render']:args[3][1][0].update(name='pid_123_luid_0_engtype_'+('Compute' if fault=='compute' else '3D'),utilization=1)
    if fault=='pid':args[3][0][0]['name']='pid_999_luid_0_engtype_Compute'
    if fault=='sample':args[3].pop()
    if fault=='child':args[2][0]['executable']='N:/solver.exe'
    if fault=='command':args[1].append('-BatchSolve')
    if fault=='image':args[0]['executable']='N:/untrusted/ansysedt.exe'
    if fault=='malformed':args[3][1][0]['utilization']=None
    with pytest.raises(Refused):evaluate_idle_edt(*args)

def _wddm_row(pid, engine, utilization):
    return {"name": f"pid_{pid}_luid_0x00000000_0x00000000_phys_0_eng_0_engtype_{engine}",
            "utilization": utilization}


def _reader_for(image, executable, create_time=10.0):
    return lambda pid: {"pid": pid, "creation_time": create_time, "image": image, "executable": executable}


def test_wddm_allows_only_core_windows_display_engines():
    samples = [[_wddm_row(4, "3D", 2.0)], [_wddm_row(4, "Copy", 1.0)], [_wddm_row(4, "3D", 0.5)]]
    reader = _reader_for("dwm.exe", r"C:/Windows/System32/dwm.exe")
    result = wddm_exclusivity(samples, process_reader=reader)
    assert result["verdict"] == "PASS_NO_NON_SYSTEM_GPU_ACTIVITY"
    assert result["active_system_display"][0]["pid"] == 4


@pytest.mark.parametrize("engine", ["3D", "VideoEncode"])
def test_wddm_non_system_activity_blocks_even_when_nvidia_memory_is_na(engine):
    samples = [[_wddm_row(10484, engine, 61.0)], [_wddm_row(10484, engine, 7.0)], [_wddm_row(10484, engine, 1.0)]]
    reader = _reader_for("GameViewerServer.exe", r"C:/Program Files/RemoteViewer/GameViewerServer.exe")
    with pytest.raises(Refused, match="WDDM_NON_SYSTEM_GPU_ACTIVITY_PRESENT"):
        wddm_exclusivity(samples, process_reader=reader)


def test_wddm_compute_activity_always_blocks():
    samples = [[_wddm_row(4, "Compute_0", 1.0)]] * 3
    reader = _reader_for("dwm.exe", r"C:/Windows/System32/dwm.exe")
    with pytest.raises(Refused, match="WDDM_COMPUTE_ACTIVITY_PRESENT"):
        wddm_exclusivity(samples, process_reader=reader)


def test_wddm_pid_reuse_or_identity_loss_fails_closed():
    samples = [[_wddm_row(10484, "3D", 1.0)]] * 3
    calls = iter([10.0, 11.0, 11.0])
    def reused(pid):
        return {"pid": pid, "creation_time": next(calls), "image": "GameViewerServer.exe",
                "executable": r"C:/Program Files/RemoteViewer/GameViewerServer.exe"}
    with pytest.raises(Refused, match="WDDM_GPU_PID_REUSED_DURING_SAMPLE"):
        wddm_exclusivity(samples, process_reader=reused)


@pytest.mark.parametrize("samples", [[], [[], [], []], [[{"name": "unknown", "utilization": 0}]] * 3])
def test_wddm_missing_or_unattributable_counters_fail_closed(samples):
    with pytest.raises(Refused):
        wddm_exclusivity(samples, process_reader=lambda pid: {})


def test_gpu_inventory_gate_rejects_wddm_activity_when_nvidia_reports_na(monkeypatch):
    from types import SimpleNamespace
    rows = [
        "NVIDIA GeForce RTX 3080, 6000" + chr(10),
        "10484, C:/Program Files/RemoteViewer/GameViewerServer.exe, [N/A]" + chr(10),
    ]
    def run(*args, **kwargs):
        return SimpleNamespace(stdout=rows.pop(0), returncode=0)
    monkeypatch.setattr(serial.subprocess, "run", run)
    monkeypatch.setattr(serial.time, "sleep", lambda _: None)
    record = dict(pid=10484, creation_time=10.0,
                  executable=r"C:/Program Files/RemoteViewer/GameViewerServer.exe",
                  command=[])
    monkeypatch.setattr(serial, "identity", lambda pid: record)
    monkeypatch.setattr(gpu_readonly, "snapshot", lambda: [_wddm_row(10484, "3D", 61.0)])
    monkeypatch.setattr(gpu_readonly, "_wddm_process_identity",
                        _reader_for("GameViewerServer.exe", record["executable"], 10.0))
    with pytest.raises(Refused, match="WDDM_NON_SYSTEM_GPU_ACTIVITY_PRESENT"):
        serial.gpu_inventory_gate(SimpleNamespace(gpu_device="NVIDIA GeForce RTX 3080"))
