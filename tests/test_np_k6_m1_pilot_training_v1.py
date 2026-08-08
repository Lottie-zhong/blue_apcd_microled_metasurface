from pathlib import Path
import importlib.util
import json
import torch


ROOT = Path(r"D:\project\worktrees\blue_apcd_np_k6_mdc_v1")


def _load(name, rel):
    path = ROOT / rel
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_m1_standalone_validator():
    validator = _load("m1_validator", "scripts/validate_np_k6_m1_pilot_training_v1.py")
    result = validator.validate()
    assert result["pass"] is True
    assert result["formal_hf_observations"] == 66


def test_m1_structured_cnn_gpu_forward_backward():
    assert torch.cuda.is_available()
    train = _load("m1_train", "scripts/np_k6_m1_pilot_training_v1.py")
    model = train.CircularCNN().to("cuda:0")
    x = torch.randn(4, 6, 7, device="cuda:0")
    c = torch.randn(4, 4, device="cuda:0")
    pred = model(x, c)
    target = (torch.full((4,), 0.5, device="cuda:0"), torch.full((4,), 0.4, device="cuda:0"),
              torch.full((4, 7), 0.5 / 7, device="cuda:0"), torch.full((4, 11), 0.4 / 11, device="cuda:0"),
              torch.full((4,), 0.1, device="cuda:0"), torch.full((4,), 0.8, device="cuda:0"), torch.full((4,), 0.1, device="cuda:0"))
    losses = train.loss_fn(pred, target)
    losses["total"].backward()
    assert all(v.device.type == "cuda" for v in pred.values() if torch.is_tensor(v))
    assert torch.max(torch.abs(pred["tx"].sum(1) - pred["T"])) < 1e-5
    assert torch.max(torch.abs(pred["rx"].sum(1) - pred["R"])) < 1e-5


def test_m1_gate_flags_and_no_solver():
    gate = json.loads((ROOT / "outputs/np_k6_m1_pilot_training_v1/training_gate_summary.json").read_text(encoding="utf-8"))
    assert gate["solver_calls"] == 0
    assert gate["sealed_test_untouched"] is True
    assert gate["acquisition_ensemble_checkpoints"] == 3
    assert gate["final_performance_model"] is False


def test_m1_mdc_level1_adapter_contract():
    audit = json.loads((ROOT / "outputs/np_k6_m1_pilot_training_v1/mdc_level1_adapter_audit.json").read_text(encoding="utf-8"))
    assert audit["compatibility_pass"] is True
    assert audit["extrapolation_fraction"] == 0.0
    assert audit["solver_calls"] == 0
