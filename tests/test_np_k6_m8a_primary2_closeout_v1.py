from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from np_k6_m8a_primary2_closeout_validator_v1 import validate
def test_primary2_closeout():
    result=validate()
    assert result['status']=='PASS'
    assert result['solver_calls']==0
