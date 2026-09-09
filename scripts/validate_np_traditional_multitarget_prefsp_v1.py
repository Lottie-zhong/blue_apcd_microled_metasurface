"""Read-only validator for setup-only K4/K9 manifests."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/np_traditional_multitarget_baseline_extension_v1"


def main():
    for k in (4, 9):
        m = json.loads((OUT / f"k{k}_fullsupercell_setup_manifest.json").read_text(encoding="utf-8"))
        assert m["status"] == "SETUP_ONLY_SAVED_RELOADED" and m["solver_entered"] == 0
        assert len(m["cases"]) == 3 and all(c["reload_pass"] for c in m["cases"])
        c = json.loads((OUT / f"k{k}_setup_checksums.json").read_text(encoding="utf-8"))
        assert c["status"] == "PASS" and c["solver_entered"] == 0
    z = json.loads((OUT / "solver_zero_audit.json").read_text(encoding="utf-8"))
    assert z["solver_entered"] == 0 and z["fdtd_run_called"] is False
    print("TRADITIONAL_MULTITARGET_PREFSP_VALIDATION_PASS")


if __name__ == "__main__":
    main()
