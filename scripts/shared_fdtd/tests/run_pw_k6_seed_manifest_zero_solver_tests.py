from __future__ import annotations
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
from shared_fdtd.tools.build_pw_k6_seed_db_v1_manifest import build

def main():
    manifest = build()
    entries = manifest["entries"]
    audit = manifest["audit"]
    assert len(entries) == 20
    assert [e["manifest_index"] for e in entries] == list(range(1, 21))
    assert [e["case_id"] for e in entries[:4]] == ["W2H_15294", "W2H_06824", "W2H_19451", "W2H_10588"]
    assert [e["case_id"] for e in entries[4:]] == [f"K6V1_S{i:02d}" for i in range(1, 17)]
    assert len({e["geometry_hash_sha256"] for e in entries}) == 20
    assert audit["solver_invocations"] == 0
    assert audit["queue_entries_created"] == 0
    assert audit["selected_identity_conflict_count"] == 0
    assert audit["physical_order_preserved"] is True
    assert audit["integrated_pw_labels_used_for_selection"] is False
    print(json.dumps({"status": "PASS", "test": "PW_K6_SEED_DB_V1_ZERO_SOLVER_MANIFEST", "solver_invocations": 0}))

if __name__ == "__main__":
    main()
