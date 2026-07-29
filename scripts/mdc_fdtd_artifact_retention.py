"""No-overwrite artifact retention primitives for Lumerical FSPs."""
from __future__ import annotations
import hashlib, shutil, uuid
from pathlib import Path
RUNTIME_ROOT=Path(r'D:\apcd_runtime\mdc_fdtd_validation_v1')
def sha256(path:Path)->str:return hashlib.sha256(path.read_bytes()).hexdigest()
def unique_runtime_fsp(run_id:str,case_id:str)->Path:
 p=RUNTIME_ROOT/run_id/case_id/(uuid.uuid4().hex+'__post.fsp');p.parent.mkdir(parents=True,exist_ok=True)
 if p.exists():raise FileExistsError(p)
 return p
def canonical_copy(runtime:Path,canonical:Path)->dict:
 if canonical.exists():raise FileExistsError(canonical)
 canonical.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(runtime,canonical);a,b=sha256(runtime),sha256(canonical)
 if a!=b:raise RuntimeError('canonical_copy_sha_mismatch')
 return {'runtime_fsp_path':str(runtime),'canonical_fsp_path':str(canonical),'runtime_sha256':a,'canonical_sha256':b}
