from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "apcd_gan_native_m1_promotion_v1"
sys.path.insert(0, str(ROOT / "scripts"))
import apcd_native_materials as materials


def test_source_and_raw_contract():
    manifest = json.loads((OUT / "manifest.json").read_text())
    assert manifest["source"]["actual_sha256"] == "d7511bb92154152d5050d7ae664cb5b281ad3794a280129008359353b357e26f"
    raw = list(csv.DictReader((OUT / "gan_raw_frequency_epsilon.csv").open(encoding="utf-8")))
    assert len(raw) == 500
    assert all(float(x["epsilon_imag"]) >= 0 for x in raw)


def test_query_roundtrip_and_principal_index_contract():
    response = list(csv.DictReader((OUT / "gan_complex_index_420_480.csv").open(encoding="utf-8")))
    rt = list(csv.DictReader((OUT / "gan_roundtrip_validation.csv").open(encoding="utf-8")))
    assert len(response) == len(rt) == 601
    assert max(float(x["delta_n"]) for x in rt) <= 1e-9
    assert max(float(x["delta_k"]) for x in rt) <= 1e-9
    at450 = next(x for x in response if x["wavelength_nm"] == "450.0")
    assert abs(float(at450["n_real"]) - 2.41494647635) < 1e-6
    assert abs(float(at450["k_imag"]) - 0.0841534686933) < 1e-6


def test_loader_policy_and_legacy_separation():
    data = materials.load_material("APCD_GAN_NATIVE_M1")
    assert data["canonical_id"] == "APCD_GAN_NATIVE_M1"
    assert len(data["frequency_hz"]) == 500 and np.all(data["n_complex"].imag >= 0)
    assert data["loss_warning"] == "high_loss_warning_retained"
    policy = materials.load_mdc_material_policy()
    assert policy["materials"]["APCD_GAN_NATIVE_M1"]["sample_count"] == 500
    assert policy["legacy"]["gan_legacy"]["canonical_id"] == "APCD_GAN_LEGACY_N241"
    assert policy["legacy"]["gan_constant_fallback_allowed"] is False


def test_no_solver_or_project_save_contract():
    text = (ROOT / "scripts" / "promote_apcd_gan_native_m1_v1.py").read_text(encoding="utf-8")
    for forbidden in (".run(", "runanalysis", ".save(", "saveas"):
        assert forbidden not in text
    validation = json.loads((OUT / "validation.json").read_text())
    assert validation["no_solver_run"] and validation["no_project_save"] and validation["deembedding_present"]
