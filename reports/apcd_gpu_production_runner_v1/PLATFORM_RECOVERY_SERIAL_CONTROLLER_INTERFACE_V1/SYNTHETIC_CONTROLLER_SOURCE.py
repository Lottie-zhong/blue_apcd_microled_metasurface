import argparse, hashlib, json, os, sys, time
from datetime import datetime, timezone
from pathlib import Path
CONTROLLER_PROTOCOL = "APCD_GPU_RUNNER_V1_QUEUE_CONTROLLER_CLI_V1"
parser = argparse.ArgumentParser()
parser.add_argument("--runner-controller-manifest", required=True)
parser.add_argument("--runner-controller-manifest-sha256", required=True)
parser.add_argument("--runner-controller-request-id", required=True)
parser.add_argument("--runner-resume-receipt")
parser.add_argument("--runner-resume-receipt-sha256")
args = parser.parse_args()
manifest_path = Path(args.runner_controller_manifest)
manifest_raw = manifest_path.read_bytes()
manifest = json.loads(manifest_raw.decode("utf-8-sig"))
sha = lambda b: hashlib.sha256(b).hexdigest()
if sha(manifest_raw) != args.runner_controller_manifest_sha256:
    raise SystemExit(31)
if args.runner_controller_request_id != sha(manifest_raw)[:32]:
    raise SystemExit(32)
if sha(Path(manifest["controller_script_path"]).read_bytes()) != manifest["controller_script_sha256"]:
    raise SystemExit(33)
status_path = Path(manifest["status_path"])
events_path = status_path.with_name("controller_events.jsonl")
truth_dir = status_path.parent / "truth"
def now():
    return datetime.now(timezone.utc).isoformat()
def event(name, **details):
    with events_path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps({"event": name, "at_utc": now(), **details}, sort_keys=True) + "\n")
        stream.flush()
def write_status(state, **extra):
    value = {
        "schema": "APCD_GPU_RUNNER_V1_QUEUE_CONTROLLER_STATUS_V1",
        "request_id": args.runner_controller_request_id,
        "controller_manifest_sha256": args.runner_controller_manifest_sha256,
        "queue_id": manifest["queue_id"],
        "state": state,
        "current_case_id": None,
        "runner_request_ids": [],
        "unresolved_runner_request_ids": [],
        "post_entry_automatic_replays": 0,
        "controller_pid": os.getpid(),
        "controller_parent_pid": os.getppid(),
        "updated_utc": now(),
    }
    value.update(extra)
    tmp = status_path.with_suffix(".tmp")
    tmp.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, status_path)
if args.runner_resume_receipt is None:
    write_status("RUNNING", current_case_id="SYNTH_CASE_A", phase="pre-crash-checkpoint")
    event("INITIAL_TASK_STARTED", pid=os.getpid(), parent_pid=os.getppid())
    time.sleep(6)
    event("PROGRESS_AFTER_SSH_CLIENT_RETURN", pid=os.getpid(), parent_pid=os.getppid())
    os._exit(73)
receipt_raw = Path(args.runner_resume_receipt).read_bytes()
if sha(receipt_raw) != args.runner_resume_receipt_sha256:
    raise SystemExit(34)
receipt = json.loads(receipt_raw.decode("utf-8-sig"))
if receipt.get("request_id") != args.runner_controller_request_id:
    raise SystemExit(35)
event("RESUMED_AFTER_RECONCILIATION", pid=os.getpid(), parent_pid=os.getppid(),
      receipt_sha256=args.runner_resume_receipt_sha256)
truth_dir.mkdir(parents=True, exist_ok=True)
truth_index = {}
for case_id in ("SYNTH_CASE_A", "SYNTH_CASE_B"):
    if case_id == "SYNTH_CASE_B":
        prior = truth_dir / "SYNTH_CASE_A.json"
        prior_raw = prior.read_bytes()
        prior_value = json.loads(prior_raw.decode("utf-8"))
        if prior_value.get("case_id") != "SYNTH_CASE_A":
            raise SystemExit(36)
        event("TRUTH_BEFORE_NEXT_CONFIRMED", prior_sha256=sha(prior_raw))
    event("SYNTHETIC_CASE_STARTED", case_id=case_id)
    value = {"schema": "SYNTHETIC_TRUTH_V1", "case_id": case_id,
             "solver_invocations": 0, "solver_entered": False, "replay_count": 0}
    raw = (json.dumps(value, sort_keys=True) + "\n").encode("utf-8")
    path = truth_dir / (case_id + ".json")
    path.write_bytes(raw)
    truth_index[case_id] = {"path": str(path), "sha256": sha(raw)}
    event("SYNTHETIC_TRUTH_DURABLE", case_id=case_id, sha256=sha(raw))
write_status("DONE", current_case_id=None, completed_case_ids=["SYNTH_CASE_A", "SYNTH_CASE_B"],
             synthetic_truth_index=truth_index, fake_runner_requests=0, fake_solver_entries=0)
event("CONTROLLER_DONE", fake_runner_requests=0, fake_solver_entries=0)
