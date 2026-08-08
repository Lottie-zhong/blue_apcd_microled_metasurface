from pathlib import Path
import json
import sys
ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
from apcd_coupling.provenance import load_source_lock, validate_source_lock

def main():
    lock = load_source_lock(ROOT/"contracts/coupling/source_branch_lock_v1.json")
    validate_source_lock(lock)
    for path in sorted((ROOT/"contracts/coupling").glob("*.json")):
        json.loads(path.read_text(encoding="utf-8"))
    print("interface contracts: valid")
    print("formal status:", lock["status"])
    print("offline screening authorized:", lock["joint_scope"]["offline_screening_authorized"])

if __name__ == "__main__":
    main()
