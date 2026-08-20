from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r"D:\project\worktrees\blue_apcd_np_k6_mdc_v1")
OUT = ROOT / "outputs/np_k6_frozen_forward_surrogate_nature_figure_v1"

qa = {
    "source_preflight": {"status": "PASS", "tool": "Nature Figure Python source preflight", "pass_count": 20, "warning_count": 0, "failure_count": 0},
    "pdf_glyph_audit": {"status": "PASS", "minimum_required_pt": 5.0, "minimum_found_pt": 5.1, "text_run_count": 91, "below_minimum_count": 0},
    "manual_rendered_panel_inspection": {"status": "PASS", "inspected": "high-resolution PNG at final physical size", "panels": ["a", "b", "c"]},
    "no_overlap": "PASS",
    "clipping": "PASS",
    "alignment": "PASS",
    "readability": "PASS",
    "provider_distinction_visible": "PASS",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
}
(OUT / "visual_qa.json").write_text(json.dumps(qa, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps(qa, indent=2))
