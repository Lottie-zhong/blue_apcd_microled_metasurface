from apcd_coupling import adapt_mdc_profile

def test_mdc_profile_preserves_joint_coordinates_and_power_fields():
    record = {
        "mdc_geometry_hash": "geom",
        "wavelength_nm": 450,
        "kx_over_k0": 0.125,
        "theta_air_deg": 7.0,
        "joint_weight": 0.25,
        "relative_upward_power": 0.8,
        "profile_sha": "profile",
        "model_scope": "synthetic",
        "source_aggregation_id": "agg",
    }
    adapted = adapt_mdc_profile(record)
    assert adapted["wavelength_nm"] == 450.0
    assert adapted["kx_over_k0"] == 0.125
    assert adapted["relative_upward_power"] == 0.8
