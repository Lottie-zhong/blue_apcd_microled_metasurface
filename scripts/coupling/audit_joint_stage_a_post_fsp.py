from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
from build_joint_stage_a_case import readback, validate_readback

OUTPUT = ROOT / "outputs/coupling/stage_a_450nm_xpol_normal_textra0_golden_fixture_v1"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=OUTPUT)
    args = parser.parse_args()
    setup = json.loads((args.output_dir / "setup_manifest.json").read_text(encoding="utf-8"))
    runtime = json.loads((args.output_dir / "runtime/attempt_001/run_state.json").read_text(encoding="utf-8"))
    case = json.loads((args.output_dir / "joint_case.json").read_text(encoding="utf-8"))
    rb = readback(case, Path(runtime["post_fsp_path"]), Path(r"D:\project\worktrees\blue_apcd_mdc_hf_surrogate_v2"))
    gate = validate_readback(case, rb)
    pre = setup["readback"]
    identity_checks = {
        "material_identity_unchanged": rb["materials"] == pre["materials"],
        "mdc_layer_identity_unchanged": rb["mdc_layers"] == pre["mdc_layers"],
        "np_geometry_identity_unchanged": rb["np_pillars"] == pre["np_pillars"],
        "source_identity_unchanged": rb["source"] == pre["source"],
        "monitor_identity_unchanged": rb["monitors"] == pre["monitors"],
        "solver_identity_gate": gate["pass"],
    }
    audit = {"schema_version":"stage_a_post_fsp_identity_audit_v1","post_fsp_path":runtime["post_fsp_path"],"post_fsp_sha256":runtime["post_fsp_sha256"],"readback":rb,"setup_gate_replay":gate,"identity_checks":identity_checks,"pass":all(identity_checks.values())}
    (args.output_dir / "post_fsp_readback.json").write_text(json.dumps(rb, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.output_dir / "post_fsp_identity_audit.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"post_fsp_sha256":runtime["post_fsp_sha256"],"pass":audit["pass"],"identity_checks":identity_checks}, indent=2))
    if not audit["pass"]:
        raise SystemExit("POST_FSP_IDENTITY_FAIL")

if __name__ == "__main__":
    main()
