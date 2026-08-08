import math
from apcd_coupling import integrate_power
def test_weighted_power_integration_is_conservative():
    assert math.isclose(integrate_power([0.2,0.3,0.5],[2.0,1.0,1.0]), 1.2, rel_tol=0, abs_tol=1e-12)
