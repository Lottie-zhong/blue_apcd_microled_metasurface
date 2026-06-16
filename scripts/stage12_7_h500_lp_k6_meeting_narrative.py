from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from metasurface.stage12_7_meeting_narrative import OUTPUT_DIR_NAME, Stage12_7Paths, run_stage12_7

OUT = REPO_ROOT / "outputs" / OUTPUT_DIR_NAME
PATHS = Stage12_7Paths(
    stage12_6_dir=REPO_ROOT / "outputs/stage12_6_h500_lp_k6_official_result_package",
    output_dir=OUT,
)

def main() -> int:
    result = run_stage12_7(PATHS)
    print(f"output_dir={result['output_dir']}")
    print(f"qa_pass={result['qa_pass']}")
    print(f"figure_file_count={result['figure_file_count']}")
    print("text_files=" + ",".join(result["text_files"]))
    print("boundary=read_only_no_fdtd_no_optimization_no_new_fsp")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
