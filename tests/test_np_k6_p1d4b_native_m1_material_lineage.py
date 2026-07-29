from __future__ import annotations
import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from metasurface.apcd_material_library import MaterialRangeError, get_epsilon, get_native_samples, get_nk, load_material_library, validate_wavelength_range
from metasurface.lumerical_native_materials import get_lumerical_material_name

def test_np_native_m1_material_lineage_contract() -> None:
    library = load_material_library()
    assert set(library) == {"APCD_TIO2_NATIVE_M1", "APCD_SIO2_NATIVE_M1"}
    for material_id in library:
        samples = get_native_samples(material_id)
        freq = [float(row["frequency_hz"]) for row in samples]
        assert samples and len(freq) == len(set(freq))
        assert all(b > a for a, b in zip(sorted(freq), sorted(freq)[1:]))
        assert all(isinstance(get_epsilon(material_id, w), complex) for w in range(445, 456))
        assert get_lumerical_material_name(material_id) == material_id
    assert get_nk("APCD_TIO2_NATIVE_M1", 450).real == pytest.approx(2.5372955063)
    assert get_nk("APCD_SIO2_NATIVE_M1", 450).real == pytest.approx(1.4261792901)
    with pytest.raises(MaterialRangeError): validate_wavelength_range("APCD_TIO2_NATIVE_M1", 150)
    with pytest.raises(KeyError): get_lumerical_material_name("APCD_GAN_NATIVE_M1")
