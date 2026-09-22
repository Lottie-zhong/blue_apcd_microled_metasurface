"""Load-only saved-truth recomputation for the canonical PW state."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

LUMERICAL_API = r"N:\Program Files\ANSYS Inc\v251\Lumerical\api\python"
REPO_SCRIPTS = Path(__file__).resolve().parents[2]
if str(REPO_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(REPO_SCRIPTS))
if LUMERICAL_API not in sys.path:
    sys.path.insert(0, LUMERICAL_API)

from shared_fdtd.tools.pw_complex_floquet_state_v1 import (  # noqa: E402
    canonical_state_from_fdtd,
    compare_states,
    save_state_npz,
    state_metadata,
)

PW_CONTRACT = {
    "monitors": {"input": "MON_IN", "pre": "MON_PRENP", "output": "MON_POSTNP"},
    "samples_nm": {"MON_IN": -100.0, "MON_PRENP": 1150.0, "MON_POSTNP": 1800.0},
    "references_nm": {"MON_IN": -50.0, "MON_PRENP": 1202.0, "MON_POSTNP": 1722.0},
    "materials": {"substrate": "APCD_GAN_NATIVE_M1", "mdc_sio2": "APCD_SIO2_NATIVE_M1", "superstrate": "Air"},
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_state(path: Path):
    import lumapi

    fd = lumapi.FDTD(str(path), hide=True)
    try:
        return canonical_state_from_fdtd(fd, PW_CONTRACT)
    finally:
        try:
            fd.close()
        except Exception:
            pass


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(json.dumps(value, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    temp.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if not args.reference.is_file() or not args.candidate.is_file():
        raise SystemExit("saved_truth_fsp_missing")
    reference = load_state(args.reference)
    candidate = load_state(args.candidate)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    reference_npz = args.output_dir / "reference_pw_complex_floquet_state.npz"
    candidate_npz = args.output_dir / "candidate_pw_complex_floquet_state.npz"
    save_state_npz(reference_npz, reference)
    save_state_npz(candidate_npz, candidate)
    reference_meta = state_metadata(reference, str(reference_npz)) | {"sha256": sha256(reference_npz), "source_fsp": str(args.reference)}
    candidate_meta = state_metadata(candidate, str(candidate_npz)) | {"sha256": sha256(candidate_npz), "source_fsp": str(args.candidate)}
    write_json(args.output_dir / "reference_pw_complex_floquet_state.json", reference_meta)
    write_json(args.output_dir / "candidate_pw_complex_floquet_state.json", candidate_meta)
    comparison = compare_states(reference, candidate)
    report = {
        "schema_version": "PW_COMPLEX_FLOQUET_STATE_OFFLINE_RECOMPUTE_V1",
        "status": "PASS",
        "solver_invocations": 0,
        "load_only": True,
        "run_calls": 0,
        "reference": reference_meta,
        "candidate": candidate_meta,
        "comparison": comparison,
        "fast_admission": "REJECTED_BY_FROZEN_R_AND_ORDER_GATES; complex-state_metric_does_not_override",
    }
    write_json(args.output_dir / "canonical_complex_state_comparison.json", report)
    print(json.dumps({"status": "PASS", "solver_invocations": 0, "aggregate": comparison["aggregate"], "output_dir": str(args.output_dir)}, indent=2))


if __name__ == "__main__":
    main()
