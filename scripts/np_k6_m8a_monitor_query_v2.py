from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from np_k6_m8a_durable_monitor_v2 import TASK_ID, monitor_query


def main() -> int:
    parser = argparse.ArgumentParser(description="fast read-only durable monitor query")
    parser.add_argument("--monitor-dir", required=True)
    args = parser.parse_args()
    result = monitor_query(Path(args.monitor_dir))
    result["task_id"] = TASK_ID
    print(json.dumps(result, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
