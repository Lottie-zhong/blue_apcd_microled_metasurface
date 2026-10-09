import hashlib
import json
import os
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

CONTRACT_SHA = "32e60a7830a449f2268356db5ffd41f4f22b297be9a1d82ebe97f97be995dea5"


def digest(value):
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ).encode()
    ).hexdigest()


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


class Config(StrictModel):
    schema_version: Literal["APCD_GPU_PLATFORM_V2_OFFLINE_V1"]
    mode: Literal["offline"]
    scientific_enabled: Literal[False]
    runtime_root: str
    python_executable: str
    lumerical_version: Literal["2025 R1"]
    fdtd_executable: str
    lumapi_path: str
    gpu_resource: str = Field(min_length=1)
    native_h5_name: Literal["run_output.h5", "run.h5"]
    physical_contract_sha256: Literal[CONTRACT_SHA]
    slots: Literal[1]
    per_attempt_entry_limit: Literal[1]
    automatic_replays: Literal[0]

    @field_validator("gpu_resource")
    @classmethod
    def resource(cls, value):
        if value.strip() != value or any(ord(c) < 32 for c in value):
            raise ValueError("invalid GPU resource")
        return value

    @model_validator(mode="after")
    def isolated(self):
        root = Path(self.runtime_root).resolve()
        if not Path(self.runtime_root).is_absolute():
            raise ValueError("absolute offline runtime required")
        forbidden = [
            Path(r"D:\apcd_runtime\gpu_production_runner_v1"),
            Path(r"D:\project\blue_apcd_microled_metasurface"),
            Path(r"D:\project\worktrees\blue_apcd_gpu_production_runner_v1"),
            Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1"),
        ]
        if any(root == p.resolve() or p.resolve() in root.parents for p in forbidden):
            raise ValueError("production runtime forbidden")
        return self

    @property
    def sha256(self):
        return digest(self.model_dump())


def load_config(path, env=None):
    def unique(pairs):
        result = {}
        for k, v in pairs:
            if k in result:
                raise ValueError("duplicate config key: " + k)
            result[k] = v
        return result

    cfg = Config.model_validate(
        json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=unique)
    )
    env = os.environ if env is None else env
    for key in env:
        if key.startswith("APCD_V2_"):
            raise ValueError("environment override forbidden: " + key)
    if env.get("APCD_GPU_RESOURCE_NAME", cfg.gpu_resource) != cfg.gpu_resource:
        raise ValueError("legacy GPU resource conflict")
    return cfg


class Request(StrictModel):
    schema_version: Literal["APCD_GPU_PLATFORM_V2_OFFLINE_REQUEST_V1"]
    case_id: str = Field(pattern=r"^OFFLINE_[A-Za-z0-9_-]{1,50}$")
    attempt_id: Literal["attempt_001"]
    role: Literal["OFFLINE_FIXTURE"]
    pre_fsp: str
    pre_fsp_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    config_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    physical_contract_sha256: Literal[CONTRACT_SHA]
    ordered_d_nm: tuple[int, int, int, int, int, int]

    @field_validator("ordered_d_nm")
    @classmethod
    def geometry(cls, values):
        if any(v < 100 or v > 230 or v % 5 for v in values):
            raise ValueError("geometry outside frozen grid")
        return values

    @property
    def request_sha256(self):
        return digest(self.model_dump())
