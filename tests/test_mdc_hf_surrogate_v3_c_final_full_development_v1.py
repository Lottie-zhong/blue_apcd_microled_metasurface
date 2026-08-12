import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import torch
import run_mdc_hf_surrogate_v3_c_final_full_development_5seed_v1 as t

def test_fixed_identity_and_loss():
    assert t.MODEL_ID == "MDC_HF_SURROGATE_V3_C_FINAL_5SEED_PROFILE_ONLY_V1"
    assert t.FINAL_EPOCHS == 117
    assert t.SEEDS == (20260813, 20260814, 20260815, 20260816, 20260817)
    assert len(t.oof.FEATURE_ORDER) == 23
    assert abs(sum(t.WEIGHTS.values()) - 1.0) < 1e-12
    assert t.V3C["residual_width"] == 384 and t.V3C["latent_width"] == 192
    assert t.V3C["weight_decay"] == 0.0

def test_profile_only_model_has_no_load_bearing_power_aux():
    model = t.oof.ProfileOnlyModel(t.V3C)
    assert model.power_head is None and model.auxiliary_head is None
    assert model(torch.zeros((2, 23)))["latent"].shape == (2, 32)

def test_loss_components_and_no_power_component():
    a = torch.rand((2, 3, 4)); b = torch.rand((2, 3, 4))
    values = t.oof.profile_loss_torch(a, b)
    assert set(values) == {"profile", "JS", "spectral_CDF", "angular_CDF", "total"}
    assert all(torch.isfinite(v) for v in values.values())
    expected = sum(t.WEIGHTS[k] * values[k] for k in t.WEIGHTS)
    assert torch.allclose(values["total"], expected)

def test_scheduler_and_epoch_are_not_fixed_v2_epoch3():
    assert t.scheduler_factor(117) > t.scheduler_factor(118)
    assert t.scheduler_factor(3) != 1.0
