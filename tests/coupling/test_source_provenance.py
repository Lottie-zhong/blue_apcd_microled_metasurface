import json
import os
import subprocess
import sys
from pathlib import Path

from apcd_coupling.provenance import canonical_sha256, load_source_lock, validate_source_lock

ROOT = Path(__file__).resolve().parents[2]

def test_source_lock_is_exact_and_read_only():
    lock = load_source_lock(ROOT/"contracts/coupling/source_branch_lock_v1.json")
    validate_source_lock(lock)
    assert lock["sources"]["mdc"]["commit"] == "489b54e43bbf2c08ce030a945b9d4b70ee7550f2"
    assert lock["sources"]["np"]["commit"] == "6493fae1f9acc636722ae1705c58b208c5cbdbe6"
    assert lock["sources"]["mdc"]["observed_clean"] is True
    assert lock["sources"]["np"]["pre_existing_dirty_changes_preserved"] is True

def test_canonical_provenance_replay_is_stable():
    lock = load_source_lock(ROOT/"contracts/coupling/source_branch_lock_v1.json")
    assert canonical_sha256(lock) == canonical_sha256(json.loads(json.dumps(lock, sort_keys=True)))

def test_fresh_process_provenance_replay_is_identical():
    code = (
        "from pathlib import Path; "
        "from apcd_coupling.provenance import canonical_sha256, load_source_lock; "
        "p=Path('contracts/coupling/source_branch_lock_v1.json'); "
        "print(canonical_sha256(load_source_lock(p)))"
    )
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT/"src")
    first = subprocess.check_output([sys.executable, "-c", code], cwd=str(ROOT), env=env, text=True).strip()
    second = subprocess.check_output([sys.executable, "-c", code], cwd=str(ROOT), env=env, text=True).strip()
    assert first == second
