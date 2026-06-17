from __future__ import annotations
import sys
from pathlib import Path
REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
from metasurface.stage12_11a_phase_origin_search import OUTPUT_DIR_NAME, Stage12_11APaths, run_stage12_11a

def main() -> int:
    result = run_stage12_11a(REPO_ROOT, Stage12_11APaths(REPO_ROOT / "outputs" / OUTPUT_DIR_NAME))
    for key, value in result.items():
        print(f"{key}={value}")
    print("boundary=read_only_no_fdtd_no_k6_no_dipoles_no_cp_no_ygradient_no_h600_h700")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())