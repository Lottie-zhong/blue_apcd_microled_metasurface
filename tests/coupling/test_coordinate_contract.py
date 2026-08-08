import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
def test_coordinate_contract_freezes_physical_signs():
    data = json.loads((ROOT/"contracts/coupling/coordinate_convention_v1.json").read_text(encoding="utf-8"))
    assert data["plus_z"].startswith("LED/GaN")
    assert data["positive_kx"] == "physical +x"
    assert data["diffraction_order_m_plus_1"] == "physical +x"
    assert data["interface_primary_variables"] == ["wavelength_nm","kx_over_k0"]
    assert "theta_air_deg" in data["derived_variables"]
