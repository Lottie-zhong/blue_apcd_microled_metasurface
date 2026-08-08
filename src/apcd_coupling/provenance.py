# Read-only provenance checks for coupling source locks.
import hashlib
import json
from pathlib import Path

_FORBIDDEN_IDENTITY_TOKENS = {"latest", "current", "newest", "best_model_latest", "recent_output"}
_IDENTITY_FIELDS = ("worktree", "branch", "commit", "completion_manifest", "package_manifest", "model_manifest", "artifact_registry", "model_id", "package_id")

def load_source_lock(path):
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)

def _walk_strings(value):
    if isinstance(value, dict):
        for key, item in value.items():
            yield from _walk_strings(key)
            yield from _walk_strings(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _walk_strings(item)
    elif isinstance(value, str):
        yield value

def validate_source_lock(lock):
    if lock.get("read_only") is not True or not lock.get("base_commit"):
        raise ValueError("source lock must be read_only=true and include base_commit")
    for source_name in ("mdc", "np"):
        source = lock.get("sources", {}).get(source_name)
        if not source:
            raise ValueError(f"missing source lock: {source_name}")
        for key in ("worktree", "branch", "commit", "completion_manifest", "package_manifest_sha256", "scope_decision"):
            if key not in source:
                raise ValueError(f"{source_name} source lock missing {key}")
        if len(source["commit"]) != 40:
            raise ValueError(f"{source_name} commit must be a full SHA-1")
        if not source["worktree"].startswith("D:"):
            raise ValueError(f"{source_name} worktree must be an absolute Windows path")
        identity_values = [source.get(key) for key in _IDENTITY_FIELDS if source.get(key) is not None]
        for forbidden in _FORBIDDEN_IDENTITY_TOKENS:
            if any(forbidden in str(value).lower() for value in identity_values):
                raise ValueError(f"mutable identity token is forbidden in {source_name} identity: {forbidden}")

def canonical_sha256(value):
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
