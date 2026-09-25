from __future__ import annotations

import hashlib
import json
import shutil
import time
import uuid
from pathlib import Path
from typing import Any, Callable

from shared_fdtd.engine.persistence import sha256_equal

H5_SUFFIXES = {".h5", ".hdf5"}
SCHEMA = "APCD_GPU_NATIVE_BUNDLE_MANIFEST_V1"


class GpuBundleError(RuntimeError):
    pass


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _relative_files(root: Path) -> list[Path]:
    return sorted(
        path.relative_to(root)
        for path in root.rglob("*")
        if path.is_file() and path.name != "bundle_manifest.json"
    )


def _bundle_sidecar_paths(source: Path) -> list[Path]:
    root = source.parent
    paths: list[Path] = []
    sidecar_root = root / source.stem
    if sidecar_root.is_dir():
        paths.extend(path for path in sidecar_root.rglob("*") if path.is_file() and path.name != "bundle_manifest.json")
    paths.extend(path for path in root.iterdir() if path.is_file() and path.suffix.lower() in H5_SUFFIXES)
    return sorted(set(paths))

def wait_for_bundle_ready(source_fsp: str | Path, *, timeout_s: float = 120.0, poll_s: float = 0.5, stable_polls: int = 2, readiness_validator: Callable[[Path], Any] | None = None) -> dict[str, Any]:
    source = Path(source_fsp)
    deadline = time.monotonic() + max(float(timeout_s), 0.0)
    previous = None
    stable = 0
    last_validation_error = None
    while True:
        if source.is_file() and source.stat().st_size > 0:
            sidecars = _bundle_sidecar_paths(source)
            signature = tuple((str(path.relative_to(source.parent)), path.stat().st_size, path.stat().st_mtime_ns) for path in sidecars if path.is_file())
            if signature:
                if signature == previous:
                    stable += 1
                else:
                    previous = signature
                    stable = 1
                if stable >= max(int(stable_polls), 1):
                    manifest = discover_bundle(source)
                    if manifest["sidecar_paths"]:
                        if readiness_validator is not None:
                            try:
                                readiness_validator(source)
                            except Exception as exc:
                                last_validation_error = repr(exc)
                                if time.monotonic() >= deadline:
                                    detail = f":{last_validation_error}"
                                    raise GpuBundleError(f"NATIVE_SIDECAR_READINESS_TIMEOUT:{source}{detail}")
                                time.sleep(max(float(poll_s), 0.01))
                                continue
                        manifest["readiness"] = {"validated": readiness_validator is not None, "last_validation_error": last_validation_error}
                        return manifest
        if time.monotonic() >= deadline:
            detail = f":{last_validation_error}" if last_validation_error else ""
            raise GpuBundleError(f"NATIVE_SIDECAR_READINESS_TIMEOUT:{source}{detail}")
        time.sleep(max(float(poll_s), 0.01))

def discover_bundle(source_fsp: str | Path) -> dict[str, Any]:
    source = Path(source_fsp)
    if not source.is_file() or source.stat().st_size <= 0:
        raise GpuBundleError(f"GPU_BUNDLE_FSP_MISSING:{source}")
    root = source.parent
    relative = [Path(source.name)]
    sidecar_root = root / source.stem
    if sidecar_root.is_dir():
        relative.extend(Path(source.stem) / item for item in _relative_files(sidecar_root))
    for sibling in root.iterdir():
        if sibling.is_file() and sibling.suffix.lower() in H5_SUFFIXES:
            relative.append(sibling.relative_to(root))
    relative = sorted({item.as_posix() for item in relative})
    sidecars = [item for item in relative if item != source.name]
    files = []
    for item in relative:
        path = root / item
        if not path.is_file():
            raise GpuBundleError(f"GPU_BUNDLE_LAYOUT_MISSING:{item}")
        files.append({
            "relative_path": item,
            "file_size": path.stat().st_size,
            "sha256": sha256_file(path),
        })
    fsp_record = next(item for item in files if item["relative_path"] == source.name)
    return {
        "schema": SCHEMA,
        "fsp_path": source.name,
        "sidecar_paths": sidecars,
        "relative_layout": relative,
        "file_size": fsp_record["file_size"],
        "sha256": fsp_record["sha256"],
        "files": files,
    }


def verify_bundle(bundle_root: str | Path, manifest: dict[str, Any]) -> dict[str, Any]:
    root = Path(bundle_root)
    expected = {str(item) for item in manifest["relative_layout"]}
    actual = {item.as_posix() for item in _relative_files(root)}
    if actual != expected:
        raise GpuBundleError(
            f"GPU_BUNDLE_INVENTORY_MISMATCH:expected={sorted(expected)}:actual={sorted(actual)}"
        )
    for record in manifest["files"]:
        path = root / record["relative_path"]
        if path.stat().st_size != int(record["file_size"]):
            raise GpuBundleError(f"GPU_BUNDLE_SIZE_MISMATCH:{record['relative_path']}")
        if not sha256_equal(sha256_file(path), record["sha256"]):
            raise GpuBundleError(f"GPU_BUNDLE_SHA_MISMATCH:{record['relative_path']}")
    return {
        "status": "PASS",
        "file_count": len(manifest["files"]),
        "sidecar_count": len(manifest["sidecar_paths"]),
        "fsp_path": str(root / manifest["fsp_path"]),
        "manifest": manifest,
    }


def _write_manifest(path: Path, manifest: dict[str, Any]) -> None:
    temporary = path.with_name(path.name + f".{uuid.uuid4().hex}.tmp")
    temporary.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def persist_gpu_bundle(
    source_fsp: str | Path,
    destination_fsp: str | Path,
    *,
    staging_root: str | Path | None = None,
    require_sidecars: bool = True,
    validator: Callable[[Path], Any] | None = None,
    failure_after_files: int | None = None,
) -> dict[str, Any]:
    source = Path(source_fsp)
    destination = Path(destination_fsp)
    if destination.name != source.name:
        raise GpuBundleError(
            f"GPU_BUNDLE_BASENAME_MISMATCH:{source.name}!={destination.name}"
        )
    source_manifest = discover_bundle(source)
    if require_sidecars and not source_manifest["sidecar_paths"]:
        raise GpuBundleError("GPU_BUNDLE_REQUIRED_SIDECAR_MISSING")
    final_dir = destination.parent
    final_fsp = final_dir / source.name
    manifest_path = final_dir / "bundle_manifest.json"
    if final_dir.exists():
        if manifest_path.is_file():
            existing = json.loads(manifest_path.read_text(encoding="utf-8"))
            if existing.get("files") != source_manifest["files"]:
                raise GpuBundleError(f"GPU_BUNDLE_FINAL_CONFLICT:{final_dir}")
            verify_bundle(final_dir, existing)
            validation = validator(final_fsp) if validator is not None else {"passed": True, "mode": "INVENTORY_ONLY"}
            return {
                "status": "ALREADY_DURABLE",
                "path": str(final_fsp),
                "fsp_path": str(final_fsp),
                "sha256": source_manifest["sha256"],
                "size_bytes": source_manifest["file_size"],
                "manifest_path": str(manifest_path),
                "manifest": existing,
                "validation": validation,
            }
        if _relative_files(final_dir):
            raise GpuBundleError(f"GPU_BUNDLE_PARTIAL_FINAL_EXISTS:{final_dir}")
    if staging_root is None:
        staging_root = final_dir.parent.parent / "native_staging" / final_dir.name
    staging_parent = Path(staging_root)
    staging_parent.mkdir(parents=True, exist_ok=True)
    stage_dir = staging_parent / (uuid.uuid4().hex + ".staging")
    stage_dir.mkdir(parents=True, exist_ok=False)
    try:
        for index, record in enumerate(source_manifest["files"], start=1):
            source_path = source.parent / record["relative_path"]
            target_path = stage_dir / record["relative_path"]
            target_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, target_path)
            if failure_after_files is not None and index >= failure_after_files:
                raise GpuBundleError("GPU_BUNDLE_COPY_INTERRUPTED")
        verify_bundle(stage_dir, source_manifest)
        _write_manifest(stage_dir / "bundle_manifest.json", source_manifest)
        validation = validator(stage_dir / source.name) if validator is not None else {"passed": True, "mode": "INVENTORY_ONLY"}
        if isinstance(validation, dict) and validation.get("passed") is False:
            raise GpuBundleError(f"GPU_BUNDLE_LOAD_ONLY_FAILED:{validation}")
        final_dir.parent.mkdir(parents=True, exist_ok=True)
        created = []
        try:
            for record in source_manifest["files"]:
                staged_path = stage_dir / record["relative_path"]
                final_path = final_dir / record["relative_path"]
                if final_path.exists():
                    raise GpuBundleError(f"GPU_BUNDLE_FINAL_CONFLICT:{final_path}")
                final_path.parent.mkdir(parents=True, exist_ok=True)
                staged_path.replace(final_path)
                created.append(final_path)
            _write_manifest(manifest_path, source_manifest)
            shutil.rmtree(stage_dir, ignore_errors=True)
        except Exception:
            for path in reversed(created):
                try:
                    path.unlink()
                except FileNotFoundError:
                    pass
            if stage_dir.exists():
                shutil.rmtree(stage_dir, ignore_errors=True)
            raise
        return {
            "status": "DURABLE",
            "path": str(final_fsp),
            "fsp_path": str(final_fsp),
            "sha256": source_manifest["sha256"],
            "size_bytes": source_manifest["file_size"],
            "manifest_path": str(manifest_path),
            "manifest": source_manifest,
            "validation": validation,
        }
    except Exception:
        if stage_dir.exists():
            shutil.rmtree(stage_dir, ignore_errors=True)
        raise
