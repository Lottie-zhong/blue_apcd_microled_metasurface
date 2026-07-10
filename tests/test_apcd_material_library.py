from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from metasurface.apcd_material_library import (  # noqa: E402
    MaterialRangeError,
    get_epsilon,
    get_native_samples,
    get_nk,
    load_material_library,
    validate_wavelength_range,
)


def test_two_native_materials_and_sample_counts() -> None:
    library = load_material_library()
    assert set(library) == {"APCD_TIO2_NATIVE_M1", "APCD_SIO2_NATIVE_M1"}
    assert len(get_native_samples("APCD_TIO2_NATIVE_M1")) == 101
    assert len(get_native_samples("APCD_SIO2_NATIVE_M1")) == 101


def test_native_range_and_450_nm_values() -> None:
    library = load_material_library()
    for entry in library.values():
        assert entry["native_lambda_min_nm"] == pytest.approx(199.9745)
        assert entry["native_lambda_max_nm"] == pytest.approx(1033.2015)
    assert get_nk("APCD_TIO2_NATIVE_M1", 450.0).real == pytest.approx(2.5372955063)
    assert get_nk("APCD_SIO2_NATIVE_M1", 450.0).real == pytest.approx(1.4261792901)


def test_range_rejection_and_epsilon_consistency() -> None:
    with pytest.raises(MaterialRangeError):
        validate_wavelength_range("APCD_TIO2_NATIVE_M1", 199.9744)
    with pytest.raises(MaterialRangeError):
        validate_wavelength_range("APCD_TIO2_NATIVE_M1", 1033.2016)
    nk = get_nk("APCD_TIO2_NATIVE_M1", 450.0)
    assert nk * nk == pytest.approx(get_epsilon("APCD_TIO2_NATIVE_M1", 450.0))


def test_interpolation_is_on_frequency_axis() -> None:
    material_id = "APCD_TIO2_NATIVE_M1"
    library = load_material_library()[material_id]
    wavelength_nm = 450.0
    frequency = 299792458.0 / (wavelength_nm * 1e-9)
    expected = complex(
        np.interp(frequency, library["frequency_hz"], library["epsilon"].real),
        np.interp(frequency, library["frequency_hz"], library["epsilon"].imag),
    )
    assert get_epsilon(material_id, wavelength_nm) == pytest.approx(expected)
