"""Central guard for immutable protected artifacts."""
from __future__ import annotations
import json
import os
from pathlib import Path

class ProtectedArtifactWriteError(PermissionError):
    """Raised before any write/replace targets a protected artifact."""

_READ_OPERATIONS = {"read", "hash", "stat", "inspect"}

def worktree_root(root=None) -> Path:
    if root is not None:
        return Path(root).resolve()
    return Path(__file__).resolve().parents[1]

def manifest_path(root=None) -> Path:
    return worktree_root(root) / "configs" / "lp_protected_artifact_manifest_v1.json"

def load_manifest(root=None) -> dict:
    with manifest_path(root).open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)

def _canonical(path, root: Path) -> str:
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = root / candidate
    return os.path.normcase(os.path.normpath(os.path.realpath(os.path.abspath(os.fspath(candidate)))))

def protected_artifact_paths(root=None) -> list[Path]:
    root_path = worktree_root(root)
    return [root_path / item["path"] for item in load_manifest(root_path)["artifacts"]]

def _matching_entry(path, root: Path):
    candidate = _canonical(path, root)
    for item in load_manifest(root)["artifacts"]:
        target = root / item["path"]
        if candidate == _canonical(target, root):
            return candidate, item
    return None

def assert_not_protected_write_target(path, operation: str, caller: str, root=None) -> Path:
    """Allow reads; fail before any mutation of an exact protected path."""
    root_path = worktree_root(root)
    match = _matching_entry(path, root_path)
    if match is not None and operation.lower() not in _READ_OPERATIONS:
        _, item = match
        raise ProtectedArtifactWriteError(
            f"protected artifact write blocked: path={_canonical(path, root_path)} "
            f"operation={operation!r} caller={caller!r} "
            f"manifest_path={item['path']!r} write_authorized={item['write_authorized']!r}"
        )
    return Path(path)

def guarded_write_text(path, text: str, *, encoding="utf-8", caller="unknown", root=None) -> Path:
    target = assert_not_protected_write_target(path, "write", caller, root)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding=encoding)
    return target

def guarded_write_bytes(path, data: bytes, *, caller="unknown", root=None) -> Path:
    target = assert_not_protected_write_target(path, "write", caller, root)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return target

def guarded_replace(source, target, *, caller="unknown", root=None) -> Path:
    assert_not_protected_write_target(source, "replace", caller, root)
    target_path = assert_not_protected_write_target(target, "replace", caller, root)
    os.replace(os.fspath(source), os.fspath(target_path))
    return target_path
