import argparse
import json
from pathlib import Path

from .config import Request, load_config
from .ledger import Ledger
from .worker import FakeBackend, run_offline


def main():
    p = argparse.ArgumentParser(
        description="Independent V2 OFFLINE ONLY; no native solver dispatch"
    )
    p.add_argument("command", choices=["audit", "run-fixture"])
    p.add_argument("--config", required=True)
    p.add_argument("--request")
    args = p.parse_args()
    cfg = load_config(args.config)
    ledger = Ledger(Path(cfg.runtime_root) / "ledger.sqlite3")
    if args.command == "run-fixture":
        request = Request.model_validate_json(Path(args.request).read_text())
        ledger.register(request, cfg)
        run_offline(cfg, request, ledger, FakeBackend())
    print(json.dumps(ledger.audit(), indent=2))


if __name__ == "__main__":
    main()
