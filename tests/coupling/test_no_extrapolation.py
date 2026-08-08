import pytest
from apcd_coupling import interpolate_no_extrapolation
def test_interpolation_is_deterministic_and_endpoint_inclusive():
    assert interpolate_no_extrapolation(1.5,[1,2,3],[10,20,40]) == 15
    assert interpolate_no_extrapolation(3,[1,2,3],[10,20,40]) == 40
@pytest.mark.parametrize("x",[0,4])
def test_extrapolation_is_rejected(x):
    with pytest.raises(ValueError, match="extrapolation"):
        interpolate_no_extrapolation(x,[1,2,3],[10,20,40])
def test_non_monotonic_grid_is_rejected():
    with pytest.raises(ValueError, match="strictly increasing"):
        interpolate_no_extrapolation(1.5,[1,1,2],[1,2,3])
