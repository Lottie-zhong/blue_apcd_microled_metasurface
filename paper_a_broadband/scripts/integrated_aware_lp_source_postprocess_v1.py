from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__import__("os").environ.get("PAPER_A_ROOT", r"D:/project/worktrees/blue_apcd_paper_a_lp_cp_broadband_v1"))
BASE = ROOT / "paper_a_broadband"
LEGACY_POST = BASE / "scripts/ic1_integrated_canary_postprocess_v1.py"


def load_legacy():
    spec = importlib.util.spec_from_file_location("integrated_source_postprocess_legacy_adapter", LEGACY_POST)
    if spec is None or spec.loader is None:
        raise RuntimeError("IC1_INTEGRATED_POSTPROCESS_IMPORT_FAILED")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def copy_required(source: Path, destination: Path) -> None:
    if not source.exists():
        raise RuntimeError(f"REQUIRED_POSTPROCESS_ARTIFACT_MISSING:{source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)


def run(args):
    provenance = json.loads(args.provenance.read_text(encoding="utf-8"))
    if provenance.get("case_id") != args.case_id or provenance.get("status") != "RETURNED":
        raise RuntimeError("SOURCE_PROVENANCE_NOT_RETURNED")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.runtime_dir.mkdir(parents=True, exist_ok=True)
    module = load_legacy()
    module.CASE_ID = args.case_id
    old_argv = sys.argv
    try:
        sys.argv = [str(LEGACY_POST), "--post-fsp", str(args.post_fsp), "--provenance", str(args.provenance), "--output-dir", str(args.output_dir), "--runtime-dir", str(args.runtime_dir)]
        module.main()
    finally:
        sys.argv = old_argv

    mapping = {
        "ic1_stokes.csv": "source_stokes.csv",
        "ic1_closed_flux.csv": "source_closed_flux.csv",
        "ic1_farfield_metrics.csv": "source_farfield_metrics.csv",
        "ic1_face_flux_long.csv": "source_face_flux_long.csv",
        "ic1_integrated_validity_gate_v2.json": "validity_gate_v2.json",
        "ic1_integrated_canary_summary.json": "source_summary.json",
    }
    for src_name, dst_name in mapping.items():
        copy_required(args.output_dir / src_name, args.output_dir / dst_name)
    convergence = args.runtime_dir / "ic1_convergence_evidence_v2.json"
    copy_required(convergence, args.output_dir / "convergence_evidence_v2.json")
    raw_ff = args.runtime_dir / "ic1_farfield_450nm_raw.npz"
    copy_required(raw_ff, args.runtime_dir / "farfield_450nm_raw.npz")

    validity_path = args.output_dir / "validity_gate_v2.json"
    validity = json.loads(validity_path.read_text(encoding="utf-8"))
    validity["case_id"] = args.case_id
    validity["candidate_id"] = args.candidate_id
    validity["polarization"] = args.polarization
    validity["paper_a_gate"] = "PAPER_A_FDTD_PHYSICS_VALIDITY_GATE_V2_INSTRUMENTED"
    validity["source_postprocess_adapter"] = "IC1 integrated canary postprocess reused without changing physics or normalization"
    validity["solver_accounting"]["postprocess_solver_run_called"] = False
    validity["solver_accounting"]["postprocess_solver_entered"] = 0
    validity_path.write_text(json.dumps(validity, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    summary_path = args.output_dir / "source_summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary.update({"case_id": args.case_id, "candidate_id": args.candidate_id, "polarization": args.polarization, "validity_gate": str(validity_path)})
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"status": "PASS" if validity.get("status") == "VALID_FOR_IC1_INTEGRATED_CANARY_TRUTH" else "HARD_GATE", "case_id": args.case_id, "candidate_id": args.candidate_id, "polarization": args.polarization, "validity_status": validity.get("status"), "validity_path": str(validity_path), "stokes": str(args.output_dir / "source_stokes.csv"), "flux": str(args.output_dir / "source_closed_flux.csv"), "farfield": str(args.output_dir / "source_farfield_metrics.csv"), "convergence": str(args.output_dir / "convergence_evidence_v2.json"), "solver_run_called": False, "solver_entered": 0}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--candidate-id", required=True)
    parser.add_argument("--polarization", choices=("x", "y"), required=True)
    parser.add_argument("--post-fsp", type=Path, required=True)
    parser.add_argument("--provenance", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--runtime-dir", type=Path, required=True)
    args = parser.parse_args()
    result = run(args)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
