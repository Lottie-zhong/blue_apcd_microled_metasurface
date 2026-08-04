from __future__ import annotations
import hashlib
import importlib.util
import subprocess
import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))
from lp_protected_artifact_guard_v1 import (
    ProtectedArtifactWriteError, assert_not_protected_write_target,
    guarded_replace, guarded_write_text, load_manifest, protected_artifact_paths,
)

def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def load_script(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module

def test_manifest_declares_exact_immutable_paths():
    manifest = load_manifest(ROOT)
    paths = [item["path"] for item in manifest["artifacts"]]
    assert paths == [
        "reports/lp_ml1a3_git_history_geometry_reconstruction.md",
        "reports/stage11_4a20_legacy_fsp_object_inventory.md",
    ]
    assert all(item["write_authorized"] is False for item in manifest["artifacts"])

def test_guard_blocks_case_traversal_and_replace_targets(tmp_path):
    protected = protected_artifact_paths(ROOT)[0]
    variants = [protected, Path(str(protected).swapcase()), ROOT / "reports" / ".." / "reports" / protected.name]
    for variant in variants:
        with pytest.raises(ProtectedArtifactWriteError):
            assert_not_protected_write_target(variant, "write", "test", ROOT)
    with pytest.raises(ProtectedArtifactWriteError):
        assert_not_protected_write_target(protected, "replace", "test", ROOT)
    assert_not_protected_write_target(protected, "hash", "test", ROOT)
    safe = tmp_path / "derived.md"
    guarded_write_text(safe, "ok", caller="test", root=ROOT)
    assert safe.read_text() == "ok"
    source = tmp_path / "source.md"
    source.write_text("source")
    with pytest.raises(ProtectedArtifactWriteError):
        guarded_replace(source, protected, caller="test", root=ROOT)

def test_import_and_dry_run_do_not_change_protected_hashes():
    protected = protected_artifact_paths(ROOT)
    before = [digest(p) for p in protected]
    load_script(SCRIPTS / "lp_ml1" / "lp_ml1a3_git_history_geometry_reconstruction.py", "lp_ml1a3_import")
    load_script(SCRIPTS / "stage11_4a20_legacy_fsp_object_inventory.py", "stage11_4a20_import")
    assert [digest(p) for p in protected] == before
    for script in (SCRIPTS / "lp_ml1" / "lp_ml1a3_git_history_geometry_reconstruction.py", SCRIPTS / "stage11_4a20_legacy_fsp_object_inventory.py"):
        cp = subprocess.run([sys.executable, str(script), "--dry-run"], cwd=ROOT, text=True, capture_output=True)
        assert cp.returncode == 0, cp.stderr
    assert [digest(p) for p in protected] == before

def test_explicit_protected_targets_fail_before_write():
    protected = protected_artifact_paths(ROOT)
    for script in (SCRIPTS / "lp_ml1" / "lp_ml1a3_git_history_geometry_reconstruction.py", SCRIPTS / "stage11_4a20_legacy_fsp_object_inventory.py"):
        cp = subprocess.run([sys.executable, str(script), "--dry-run", "--report-output", str(protected[0])], cwd=ROOT, text=True, capture_output=True)
        assert cp.returncode != 0
        assert "protected artifact write blocked" in (cp.stdout + cp.stderr)

def test_remediated_scripts_have_no_protected_writer_literal():
    names = [Path(item["path"]).name for item in load_manifest(ROOT)["artifacts"]]
    for path in (SCRIPTS / "lp_ml1" / "lp_ml1a3_git_history_geometry_reconstruction.py", SCRIPTS / "stage11_4a20_legacy_fsp_object_inventory.py"):
        text = path.read_text(encoding="utf-8-sig").lower()
        assert not any(name.lower() in text for name in names)
        assert "assert_not_protected_write_target" in text

def test_static_scan_has_no_unguarded_source_writer():
    scan_mod = load_script(SCRIPTS / "lp_protected_artifact_static_scan_v1.py", "protected_scan")
    result = scan_mod.scan(ROOT)
    assert result["unguarded_writer_count"] == 0, result["unguarded_writers"]
