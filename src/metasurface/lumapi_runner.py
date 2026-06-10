from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Optional, Union

from metasurface.config import PlaneWaveSweepConfig, RuntimeConfig, load_runtime_config
from metasurface.h_sweep import build_dry_run_rows


@dataclass(frozen=True)
class SweepRunner:
    config: PlaneWaveSweepConfig
    dry_run: bool = False
    runtime: Optional[RuntimeConfig] = None

    @classmethod
    def from_runtime_file(
        cls,
        config: PlaneWaveSweepConfig,
        runtime_path: Optional[Union[str, Path]],
        dry_run: bool,
    ) -> "SweepRunner":
        runtime = None if dry_run or runtime_path is None else load_runtime_config(runtime_path)
        return cls(config=config, dry_run=dry_run, runtime=runtime)

    def run(self) -> list[dict[str, object]]:
        if self.dry_run:
            return build_dry_run_rows(self.config)

        if self.runtime is None:
            raise ValueError("A runtime config is required when dry_run is False")
        if not self.runtime.enable_lumerical:
            raise RuntimeError("runtime.enable_lumerical is false; use --dry-run or update runtime.yaml")

        lumapi = import_lumapi(self.runtime)
        return self._run_lumerical_sweep(lumapi)

    def _run_lumerical_sweep(self, lumapi: ModuleType) -> list[dict[str, object]]:
        raise NotImplementedError(
            "Real Lumerical h-sweep is planned for P1/P2. P0 supports --dry-run only."
        )


def import_lumapi(runtime: RuntimeConfig) -> ModuleType:
    api_dir = runtime.lumapi_python_api_dir
    if not api_dir:
        raise ValueError("lumapi.python_api_dir is empty in runtime config")

    api_path = str(Path(api_dir))
    if api_path not in sys.path:
        sys.path.insert(0, api_path)

    import lumapi  # type: ignore[import-not-found]

    return lumapi
