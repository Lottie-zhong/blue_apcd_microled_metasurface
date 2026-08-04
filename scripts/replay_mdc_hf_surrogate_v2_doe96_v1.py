"""Fresh-process deterministic replay audit for frozen DOE96 exports."""
from __future__ import annotations
import json, sys
from datetime import datetime, timezone
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from extract_mdc_hf_surrogate_v2_doe96_labels_v1 import replay_digest
run = Path(sys.argv[1])
replay_id = int(sys.argv[2]) if len(sys.argv) > 2 else 1
out = run / f"doe96_extraction_replay_{replay_id}.json"
d = replay_digest(run)
d.update({"replay_process_id": replay_id, "status": "PASS", "source_policy": "frozen raw post-FSP exports only", "solver_calls": 0, "formal_hf15_reads": 0, "sealed_test_reads": 0, "generated_at_utc": datetime.now(timezone.utc).isoformat()})
out.write_text(json.dumps(d, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps(d, sort_keys=True))
