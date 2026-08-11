from pathlib import Path
import sys
import numpy as np
import torch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import run_mdc_hf_surrogate_v3_oof_formal_v1 as r

def test_schema_and_registry():
    assert len(r.FEATURE_ORDER) == 23
    assert r.FEATURE_ORDER[-5:] == ("source_top", "source_centroid", "source_bottom", "dipole_x", "dipole_z")
    assert sum(r.PROFILE_WEIGHTS.values()) == 1.0
    assert all(x["input_width"] == 23 for x in r.load_candidates())

def test_structural_model_has_profile_only_output():
    m = r.ProfileOnlyModel(r.load_candidates()[0])
    out = m(torch.zeros(2, 23))
    assert tuple(out["latent"].shape) == (2, 32)
    assert m.power_head is None and m.auxiliary_head is None

def test_synthetic_loss_finite_and_differentiable_definition():
    pred = torch.rand(2, 301, 2000, requires_grad=True)
    truth = torch.rand(2, 301, 2000)
    vals = r.profile_loss_torch(pred, truth)
    assert all(torch.isfinite(v).item() for v in vals.values())
    assert vals["total"].requires_grad

def test_outer_inner_geometry_grouping():
    import pandas as pd
    g = pd.DataFrame({"geometry_hash":[f"g{i}" for i in range(20)], "topology_family":["Explicit"]*20})
    folds = r.geometry_folds(g)
    for f, held in folds.items():
        fit, stop = r.inner_split(g, set(held))
        assert not set(held) & set(fit)
        assert not set(held) & set(stop)

def test_no_power_or_auxiliary_target():
    assert "power" not in r.PROFILE_WEIGHTS and "auxiliary" not in r.PROFILE_WEIGHTS
