import math
from apcd_coupling import normalize_power
def test_normalization_closes_to_one():
    normalized = normalize_power([2,3,5])
    assert math.isclose(sum(normalized), 1.0, rel_tol=0, abs_tol=1e-12)
    assert normalized == [0.2,0.3,0.5]
