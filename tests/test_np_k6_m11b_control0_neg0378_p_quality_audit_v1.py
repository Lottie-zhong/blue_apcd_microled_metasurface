from pathlib import Path
import subprocess, sys
def test_m11b_control0_postfsp_quality_audit():
    root=Path(__file__).resolve().parents[1]
    script=root/'scripts/np_k6_m11b_control0_neg0378_p_quality_audit_validator_v1.py'
    r=subprocess.run([sys.executable,str(script)],cwd=root,text=True,capture_output=True)
    assert r.returncode==0, r.stdout+'\n'+r.stderr
