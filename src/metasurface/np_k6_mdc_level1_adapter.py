import numpy as np
class MDCInterfaceError(ValueError): pass
def couple_level1(mdc_profile,np_result,expected_stack_id=None,expected_normalization_id=None):
    p=dict(mdc_profile); w=np.asarray(p["joint_weight"],float)
    if np.any(w<0) or not np.isclose(w.sum(),1,atol=1e-10): raise MDCInterfaceError("JOINT_WEIGHT_INVALID")
    if expected_stack_id is not None and p.get("interface_stack_id")!=expected_stack_id: raise MDCInterfaceError("STACK_ID_MISMATCH")
    if expected_normalization_id is not None and p.get("normalization_id")!=expected_normalization_id: raise MDCInterfaceError("NORMALIZATION_ID_MISMATCH")
    if p.get("wavelength_nm") not in np_result.get("wavelength_nm",[p.get("wavelength_nm")]): raise MDCInterfaceError("WAVELENGTH_EXTRAPOLATION")
    if p.get("u_x") not in np_result.get("u_x",[p.get("u_x")]): raise MDCInterfaceError("U_X_EXTRAPOLATION")
    eta=np.asarray(np_result["eta_plus1"],float); up=float(p["relative_upward_power"])
    return {"relative_power_plus1":up*float(np.sum(w*eta)),"relative_upward_power":up,"coverage_fraction":1.0,"extrapolation_fraction":0.0,"compatibility_pass":True,"complex_feedback":"NOT_SUPPORTED_IN_V1"}

