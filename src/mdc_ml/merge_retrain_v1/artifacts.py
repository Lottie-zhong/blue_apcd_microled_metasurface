from __future__ import annotations

"""Atomic, policy-bound artifact writes for future authorized trainer stages."""

import csv
import io
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import joblib

from .contracts import SignatureBundle, canonical_json, sha256_bytes, sha256_file


ARTIFACT_SCHEMA_VERSION = "mdc_ml_artifact_record_v1"
MANIFEST_SCHEMA_VERSION = "mdc_ml_artifact_manifest_v1"


def _same_path(left: Path, right: Path) -> bool:
    return os.path.normcase(str(left.resolve())) == os.path.normcase(str(right.resolve()))


def _within(path: Path, root: Path) -> bool:
    try:
        return os.path.commonpath(
            [os.path.normcase(str(path.resolve())), os.path.normcase(str(root.resolve()))]
        ) == os.path.normcase(str(root.resolve()))
    except ValueError:
        return False


@dataclass(frozen=True)
class ArtifactPolicy:
    root: Path
    mode: str
    worktree_root: Path
    formal_output_root: Path
    formal_authorized: bool = False

    @classmethod
    def fixture(
        cls,
        root: Path,
        *,
        worktree_root: Path,
        formal_output_root: Path,
    ) -> "ArtifactPolicy":
        return cls(
            root=root,
            mode="fixture",
            worktree_root=worktree_root,
            formal_output_root=formal_output_root,
            formal_authorized=False,
        )

    @classmethod
    def formal(
        cls,
        root: Path,
        *,
        worktree_root: Path,
        formal_output_root: Path,
        authorized: bool,
    ) -> "ArtifactPolicy":
        return cls(
            root=root,
            mode="formal",
            worktree_root=worktree_root,
            formal_output_root=formal_output_root,
            formal_authorized=authorized,
        )

    @classmethod
    def formal_run(
        cls, root: Path, *, worktree_root: Path, formal_output_root: Path,
        authorized: bool,
    ) -> "ArtifactPolicy":
        """Authorized formal artifacts live in the allocated run, never inputs."""
        return cls(root=root, mode="formal_run", worktree_root=worktree_root,
                   formal_output_root=formal_output_root,
                   formal_authorized=authorized)

    def validate(self) -> None:
        root = self.root.resolve()
        if self.mode == "fixture":
            temp_root = Path(tempfile.gettempdir()).resolve()
            if not _within(root, temp_root):
                raise ValueError("FIXTURE_ROOT_MUST_BE_SYSTEM_TEMP")
            if _within(root, self.worktree_root.resolve()):
                raise ValueError("FIXTURE_ROOT_INSIDE_WORKTREE")
            if _within(root, self.formal_output_root.resolve()):
                raise ValueError("FIXTURE_ROOT_INSIDE_FORMAL_OUTPUT")
        elif self.mode == "formal":
            if not _same_path(root, self.formal_output_root):
                raise ValueError("FORMAL_ARTIFACT_ROOT_MISMATCH")
            if not self.formal_authorized:
                raise PermissionError("FORMAL_ARTIFACT_WRITE_NOT_AUTHORIZED")
        elif self.mode == "formal_run":
            if _within(root, self.worktree_root.resolve()) or _within(root, self.formal_output_root.resolve()):
                raise ValueError("FORMAL_RUN_ARTIFACT_ROOT_INVALID")
            if not self.formal_authorized:
                raise PermissionError("FORMAL_ARTIFACT_WRITE_NOT_AUTHORIZED")
        else:
            raise ValueError("UNKNOWN_ARTIFACT_MODE:" + self.mode)


@dataclass(frozen=True)
class ArtifactRecord:
    relative_path: str
    size_bytes: int
    sha256: str
    artifact_type: str
    producer_stage: str
    producer_unit: str
    created_at: str
    schema_version: str = ARTIFACT_SCHEMA_VERSION

    def as_dict(self) -> dict[str, Any]:
        return {
            "relative_path": self.relative_path,
            "size_bytes": self.size_bytes,
            "sha256": self.sha256,
            "artifact_type": self.artifact_type,
            "producer_stage": self.producer_stage,
            "producer_unit": self.producer_unit,
            "created_at": self.created_at,
            "schema_version": self.schema_version,
        }


@dataclass(frozen=True)
class ArtifactManifest:
    manifest_schema_version: str
    run_id: str
    signature_bundle: Mapping[str, str]
    artifact_count: int
    total_bytes: int
    records: tuple[ArtifactRecord, ...]
    canonical_manifest_sha256: str

    def unsigned_dict(self) -> dict[str, Any]:
        return {
            "manifest_schema_version": self.manifest_schema_version,
            "run_id": self.run_id,
            "signature_bundle": dict(self.signature_bundle),
            "artifact_count": self.artifact_count,
            "total_bytes": self.total_bytes,
            "records": [record.as_dict() for record in self.records],
        }

    def as_dict(self) -> dict[str, Any]:
        return {
            **self.unsigned_dict(),
            "canonical_manifest_sha256": self.canonical_manifest_sha256,
        }


class AtomicArtifactStore:
    def __init__(
        self,
        policy: ArtifactPolicy,
        *,
        run_id: str,
        signature_bundle: SignatureBundle | Mapping[str, str],
        created_at: str = "1970-01-01T00:00:00+00:00",
    ):
        policy.validate()
        self.policy = policy
        self.root = policy.root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.run_id = run_id
        self.signature_bundle = (
            signature_bundle.as_dict()
            if isinstance(signature_bundle, SignatureBundle)
            else dict(signature_bundle)
        )
        self.created_at = created_at
        self._records: dict[str, ArtifactRecord] = {}

    def _target(self, relative_path: str | Path) -> tuple[str, Path]:
        child = Path(relative_path)
        if child.is_absolute() or ".." in child.parts:
            raise ValueError("ARTIFACT_PATH_TRAVERSAL")
        relative = child.as_posix()
        if relative in {"", "."}:
            raise ValueError("ARTIFACT_PATH_EMPTY")
        target = (self.root / child).resolve()
        if not _within(target, self.root):
            raise ValueError("ARTIFACT_PATH_ESCAPE")
        return relative, target

    def _record(
        self,
        relative: str,
        target: Path,
        artifact_type: str,
        producer_stage: str,
        producer_unit: str,
    ) -> ArtifactRecord:
        record = ArtifactRecord(
            relative_path=relative,
            size_bytes=target.stat().st_size,
            sha256=sha256_file(target),
            artifact_type=artifact_type,
            producer_stage=producer_stage,
            producer_unit=producer_unit,
            created_at=self.created_at,
        )
        self._records[relative] = record
        return record

    def _atomic_payload(
        self,
        relative_path: str | Path,
        payload: bytes,
        *,
        artifact_type: str,
        producer_stage: str,
        producer_unit: str,
    ) -> ArtifactRecord:
        relative, target = self._target(relative_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        expected_sha = sha256_bytes(payload)
        if target.exists():
            if target.is_dir() or sha256_file(target) != expected_sha:
                raise FileExistsError("ARTIFACT_OVERWRITE_SHA_MISMATCH:" + relative)
            return self._record(
                relative, target, artifact_type, producer_stage, producer_unit
            )
        temporary: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                dir=target.parent,
                prefix=f".{target.name}.",
                suffix=".tmp",
                delete=False,
            ) as handle:
                temporary = Path(handle.name)
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, target)
            temporary = None
        finally:
            if temporary is not None and temporary.exists():
                temporary.unlink()
        return self._record(relative, target, artifact_type, producer_stage, producer_unit)

    def write_bytes(
        self,
        relative_path: str | Path,
        value: bytes,
        *,
        artifact_type: str,
        producer_stage: str,
        producer_unit: str,
    ) -> ArtifactRecord:
        return self._atomic_payload(
            relative_path,
            value,
            artifact_type=artifact_type,
            producer_stage=producer_stage,
            producer_unit=producer_unit,
        )

    def write_text(
        self,
        relative_path: str | Path,
        value: str,
        *,
        artifact_type: str,
        producer_stage: str,
        producer_unit: str,
    ) -> ArtifactRecord:
        return self.write_bytes(
            relative_path,
            value.encode("utf-8"),
            artifact_type=artifact_type,
            producer_stage=producer_stage,
            producer_unit=producer_unit,
        )

    def write_json(
        self,
        relative_path: str | Path,
        value: Any,
        *,
        artifact_type: str,
        producer_stage: str,
        producer_unit: str,
    ) -> ArtifactRecord:
        payload = (
            json.dumps(
                value,
                indent=2,
                sort_keys=True,
                ensure_ascii=False,
                allow_nan=False,
            )
            + "\n"
        ).encode("utf-8")
        return self.write_bytes(
            relative_path,
            payload,
            artifact_type=artifact_type,
            producer_stage=producer_stage,
            producer_unit=producer_unit,
        )

    def write_jsonl(
        self,
        relative_path: str | Path,
        rows: Iterable[Any],
        *,
        artifact_type: str,
        producer_stage: str,
        producer_unit: str,
    ) -> ArtifactRecord:
        payload = "".join(canonical_json(row) + "\n" for row in rows).encode("utf-8")
        return self.write_bytes(
            relative_path,
            payload,
            artifact_type=artifact_type,
            producer_stage=producer_stage,
            producer_unit=producer_unit,
        )

    def write_csv(
        self,
        relative_path: str | Path,
        rows: Sequence[Mapping[str, Any]],
        *,
        artifact_type: str,
        producer_stage: str,
        producer_unit: str,
        fieldnames: Sequence[str] | None = None,
    ) -> ArtifactRecord:
        names = list(fieldnames or (list(rows[0]) if rows else []))
        stream = io.StringIO(newline="")
        writer = csv.DictWriter(stream, fieldnames=names, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
        return self.write_text(
            relative_path,
            stream.getvalue(),
            artifact_type=artifact_type,
            producer_stage=producer_stage,
            producer_unit=producer_unit,
        )

    def write_joblib(
        self,
        relative_path: str | Path,
        value: Any,
        *,
        artifact_type: str,
        producer_stage: str,
        producer_unit: str,
    ) -> ArtifactRecord:
        stream = io.BytesIO()
        joblib.dump(value, stream, compress=3)
        return self.write_bytes(
            relative_path,
            stream.getvalue(),
            artifact_type=artifact_type,
            producer_stage=producer_stage,
            producer_unit=producer_unit,
        )

    def manifest(self) -> ArtifactManifest:
        records = tuple(self._records[key] for key in sorted(self._records))
        unsigned = {
            "manifest_schema_version": MANIFEST_SCHEMA_VERSION,
            "run_id": self.run_id,
            "signature_bundle": dict(sorted(self.signature_bundle.items())),
            "artifact_count": len(records),
            "total_bytes": sum(record.size_bytes for record in records),
            "records": [record.as_dict() for record in records],
        }
        return ArtifactManifest(
            manifest_schema_version=MANIFEST_SCHEMA_VERSION,
            run_id=self.run_id,
            signature_bundle=unsigned["signature_bundle"],
            artifact_count=len(records),
            total_bytes=unsigned["total_bytes"],
            records=records,
            canonical_manifest_sha256=sha256_bytes(
                canonical_json(unsigned).encode("utf-8")
            ),
        )

    def validate_manifest(self, manifest: ArtifactManifest) -> None:
        expected_sha = sha256_bytes(
            canonical_json(manifest.unsigned_dict()).encode("utf-8")
        )
        if expected_sha != manifest.canonical_manifest_sha256:
            raise RuntimeError("ARTIFACT_MANIFEST_DRIFT")
        for record in manifest.records:
            relative, target = self._target(record.relative_path)
            if relative != record.relative_path or not target.is_file():
                raise RuntimeError("ARTIFACT_MISSING:" + record.relative_path)
            if (
                target.stat().st_size != record.size_bytes
                or sha256_file(target) != record.sha256
            ):
                raise RuntimeError("ARTIFACT_DRIFT:" + record.relative_path)

    def audit_unregistered(self, *, ignore: Iterable[str] = ()) -> tuple[str, ...]:
        ignored = set(ignore)
        actual = {
            path.relative_to(self.root).as_posix()
            for path in self.root.rglob("*")
            if path.is_file() and path.suffix != ".tmp"
        }
        return tuple(sorted(actual - set(self._records) - ignored))

    def write_manifest(
        self,
        relative_path: str | Path = "artifact_manifest_v1.json",
    ) -> ArtifactManifest:
        manifest = self.manifest()
        relative, target = self._target(relative_path)
        payload = (
            json.dumps(
                manifest.as_dict(),
                indent=2,
                sort_keys=True,
                ensure_ascii=False,
                allow_nan=False,
            )
            + "\n"
        ).encode("utf-8")
        if target.exists() and sha256_file(target) != sha256_bytes(payload):
            raise FileExistsError("ARTIFACT_OVERWRITE_SHA_MISMATCH:" + relative)
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            temporary: Path | None = None
            try:
                with tempfile.NamedTemporaryFile(
                    mode="wb",
                    dir=target.parent,
                    prefix=f".{target.name}.",
                    suffix=".tmp",
                    delete=False,
                ) as handle:
                    temporary = Path(handle.name)
                    handle.write(payload)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temporary, target)
                temporary = None
            finally:
                if temporary is not None and temporary.exists():
                    temporary.unlink()
        return manifest
