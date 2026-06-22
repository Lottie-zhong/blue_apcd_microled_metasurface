from __future__ import annotations

import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from metasurface.stage13_7a_coordinate_sign_bridge import run_audit


def main() -> int:
    result = run_audit(REPO_ROOT, REPO_ROOT / "outputs/stage13_7a_lp_coordinate_sign_bridge")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
