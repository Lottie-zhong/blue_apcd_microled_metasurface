import hashlib,importlib.util,inspect,sys
from pathlib import Path
import pytest
from apcd_gpu_v2.science import postprocess
from apcd_gpu_v2.science import mdc_tmm_complex_incident_power_v1 as bundled

def test_helper_has_frozen_source_bytes_and_numerical_parity():
    source=Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1\scripts\mdc_tmm_complex_incident_power_v1.py")
    expected="12d2d95bd99fc6e18fec9ac17ab066a5a1fc4a3ddf1a6e5a8c0a625da959ff4b"
    assert hashlib.sha256(Path(bundled.__file__).read_bytes()).hexdigest()==expected
    assert hashlib.sha256(source.read_bytes()).hexdigest()==expected
    spec=importlib.util.spec_from_file_location("frozen_source_helper",source)
    old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
    for wl in (440.0,450.0,460.0):
        args=(2.45+0.01j,1+0j,[(2.4+0.002j,44.0),(1.46+0j,79.0)],wl)
        assert bundled.normal_stack_power(*args)==old.normal_stack_power(*args)

def test_analyze_imports_packaged_helper_without_ambient_scripts(monkeypatch):
    monkeypatch.delitem(sys.modules,"mdc_tmm_complex_incident_power_v1",raising=False)
    class ReachedFrequency(RuntimeError):pass
    def stop(*args):raise ReachedFrequency()
    monkeypatch.setattr(postprocess,"_contract",lambda cfg:dict(monitors={"output":"MON_POSTNP"},samples_nm={},references_nm={},materials={}))
    monkeypatch.setattr(postprocess,"_freq",stop)
    with pytest.raises(ReachedFrequency):postprocess.analyze(None,{})
    assert "mdc_tmm_complex_incident_power_v1" not in sys.modules

def test_missing_helper_pin_refused_before_native_session(tmp_path):
    from types import SimpleNamespace
    from apcd_gpu_v2.serial import NativeTruthValidator
    from apcd_gpu_v2.ledger import Refused
    cfg=SimpleNamespace(truth_toolchain={},coupling_root=str(tmp_path))
    with pytest.raises(Refused,match="INCIDENT_POWER_HELPER_PIN_REQUIRED"):
        NativeTruthValidator(cfg)(None,None,None)

def test_identical_helper_at_unbound_path_refused(tmp_path):
    from types import SimpleNamespace
    from apcd_gpu_v2.serial import NativeTruthValidator,Pin
    from apcd_gpu_v2.artifacts import sha256
    from apcd_gpu_v2.ledger import Refused
    p=tmp_path/"helper.py";p.write_bytes(Path(bundled.__file__).read_bytes())
    cfg=SimpleNamespace(truth_toolchain={"incident_power_helper":Pin(path=str(p),sha256=sha256(p))},coupling_root=str(tmp_path))
    with pytest.raises(Refused,match="INCIDENT_POWER_HELPER_PIN_CHANGED"):
        NativeTruthValidator(cfg)(None,None,None)
