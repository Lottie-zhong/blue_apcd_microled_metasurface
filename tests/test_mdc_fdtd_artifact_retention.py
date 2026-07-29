from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import mdc_fdtd_artifact_retention as r
def test_unique_runtime_name_and_no_overwrite(tmp_path,monkeypatch):
 monkeypatch.setattr(r,'RUNTIME_ROOT',tmp_path);a=r.unique_runtime_fsp('r','c');b=r.unique_runtime_fsp('r','c');assert a!=b and not a.exists()
def test_copy_sha_and_existing_rejection(tmp_path):
 src=tmp_path/'s';src.write_bytes(b'x');dst=tmp_path/'d';out=r.canonical_copy(src,dst);assert out['runtime_sha256']==out['canonical_sha256']
 try:r.canonical_copy(src,dst)
 except FileExistsError:pass
 else:assert False
