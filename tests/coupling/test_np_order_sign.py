import pytest
from apcd_coupling import adapt_np_order_response
def record():
    return {"np_geometry_hash":"geom","wavelength_nm":450,"kx_over_k0":0,"polarization":"x","eta_t_order":{"+1":0.7,"0":0.1,"-1":0.02},"eta_r_order":{"+1":0.01},"T_total":0.82,"R_total":0.03,"theta_out_plus1":5.0,"interface_stack_id":"stack","model_scope":"synthetic"}
def test_positive_one_order_is_read_from_transmitted_order_map():
    assert adapt_np_order_response(record(), order=1)["eta_plus1"] == 0.7
def test_missing_positive_one_order_is_not_silently_relabelled():
    data = record(); data["eta_t_order"] = {"-1":0.7}
    with pytest.raises(ValueError, match="missing diffraction order 1"):
        adapt_np_order_response(data, order=1)
