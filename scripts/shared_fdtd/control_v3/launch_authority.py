from __future__ import annotations

import hashlib
import json
import os
import socket
import sys
import uuid
from typing import Callable

from .allocator import Allocator, AdmissionGateBlocked
from .db import utc_now


class LaunchAlreadyClaimed(RuntimeError):
    pass


class ScientificLaunchAuthority:
    """Durable, one-shot permission; a claim is never automatically retried.

    Commit the claim before any external side effect. A crash between commit
    and invocation is deliberately ambiguous and requires forensic recovery.
    This class is the control-plane API; callers must not write its table.
    """

    def __init__(self, db):
        self.db = db

    @staticmethod
    def _ensure(con):
        con.execute("""CREATE TABLE IF NOT EXISTS scientific_launch_claims (
            branch_id TEXT NOT NULL, logical_case_id TEXT NOT NULL,
            attempt_id TEXT NOT NULL, launch_id TEXT NOT NULL UNIQUE,
            lease_token_hash TEXT NOT NULL, fencing_generation INTEGER NOT NULL,
            claimed_at TEXT NOT NULL, identity_json TEXT NOT NULL,
            PRIMARY KEY(branch_id,logical_case_id,attempt_id))""")
        con.execute("""CREATE TRIGGER IF NOT EXISTS scientific_launch_no_update
            BEFORE UPDATE ON scientific_launch_claims BEGIN
            SELECT RAISE(ABORT,'scientific launch claims are immutable'); END""")
        con.execute("""CREATE TRIGGER IF NOT EXISTS scientific_launch_no_delete
            BEFORE DELETE ON scientific_launch_claims BEGIN
            SELECT RAISE(ABORT,'scientific launch claims are immutable'); END""")

    def claim(self, lease, *, pre_fsp_hash, physical_contract_hash,
              command, executable, resource_request=None, resource_snapshot=None,
              resource_policy=None, backend_type=None, exact_permit_id=None):
        for label, value in [('pre_fsp_hash', pre_fsp_hash),
                             ('physical_contract_hash', physical_contract_hash)]:
            if not isinstance(value, str) or len(value) != 64 or any(c not in '0123456789abcdefABCDEF' for c in value):
                raise ValueError('INVALID_' + label.upper())
        if not isinstance(command, list) or not command or not all(isinstance(x, str) and x for x in command):
            raise ValueError('COMMAND_ARRAY_REQUIRED')
        if not isinstance(executable, str) or not executable.strip():
            raise ValueError('EXECUTABLE_REQUIRED')
        from .resources import ResourceRequest
        if resource_request is not None and not isinstance(resource_request, ResourceRequest):
            resource_request = ResourceRequest.from_payload(resource_request)
        allocator = Allocator(self.db)
        key = (lease.owner_branch, lease.logical_case_id, lease.attempt_id)
        with self.db.immediate() as con:
            self._ensure(con)
            if con.execute('SELECT 1 FROM scientific_launch_claims WHERE branch_id=? AND logical_case_id=? AND attempt_id=?', key).fetchone():
                raise LaunchAlreadyClaimed('SCIENTIFIC_LAUNCH_ALREADY_CLAIMED')
            if con.execute("SELECT 1 FROM lease_events WHERE branch_id=? AND logical_case_id=? AND attempt_id=? AND event_type IN ('SCIENTIFIC_SOLVER_ENTERED','GPU_ENGINE_ENTRY_CONFIRMED')", key).fetchone():
                raise LaunchAlreadyClaimed('HISTORICAL_SCIENTIFIC_ENTRY_NO_REPLAY')
            decision = allocator._admission_decision(
                con, lease.owner_branch, logical_case_id=lease.logical_case_id,
                attempt_id=lease.attempt_id, lease=lease, final=True,
                resource_request=resource_request, resource_snapshot=resource_snapshot,
                resource_policy=resource_policy, backend_type=backend_type,
                exact_permit_id=exact_permit_id)
            if lease.control_generation is None or not decision['eligible']:
                raise AdmissionGateBlocked('SCIENTIFIC_LAUNCH_ADMISSION_BLOCKED:' + ','.join(decision['reasons']))
            if exact_permit_id:
                permit = allocator._consume_exact_launch_permit_in_con(con, exact_permit_id, lease)
                if not permit['valid']:
                    raise AdmissionGateBlocked(permit['reason'])
            identity = {
                'launch_id': uuid.uuid4().hex,
                'branch_id': key[0], 'case_id': key[1], 'attempt_id': key[2],
                'lease_token_hash': lease.token_hash,
                'fencing_generation': lease.fencing_generation,
                'host': socket.gethostname(), 'host_pid': os.getpid(),
                'host_executable': sys.executable, 'claimed_at': utc_now(),
                'pre_fsp_hash': pre_fsp_hash.lower(),
                'physical_contract_hash': physical_contract_hash.lower(),
                'command': command, 'executable': executable,
                'command_hash': hashlib.sha256(json.dumps(command, separators=(',', ':')).encode()).hexdigest(),
                'solver_entered': True,
                'entry_semantics': 'CONSERVATIVE_BUDGET_CONSUMED_BEFORE_INVOCATION',
                'physical_process_confirmed': False,
                'automatic_retry_allowed': False,
            }
            con.execute('INSERT INTO scientific_launch_claims VALUES(?,?,?,?,?,?,?,?)',
                        (*key, identity['launch_id'], lease.token_hash,
                         lease.fencing_generation, identity['claimed_at'], json.dumps(identity, sort_keys=True)))
            allocator._event(con, lease, 'SCIENTIFIC_LAUNCH_CLAIMED', identity)
            # Publish conservative entry and resource ownership in the same
            # commit as the claim: legacy reconciliation must never see a
            # retryable pre-entry owner after launch permission is consumed.
            now = identity['claimed_at']
            con.execute("UPDATE slots SET state='LIVE',solver_entered_at=?,heartbeat_at=?,updated_at=?,version=version+1 WHERE slot_id=?",
                        (now, now, now, lease.slot_id))
            from .resources import ensure_resource_tables
            ensure_resource_tables(con)
            con.execute("UPDATE resource_reservations SET state='LIVE',updated_at=? WHERE slot_id=? AND branch_id=? AND logical_case_id=? AND attempt_id=?",
                        (now, lease.slot_id, *key))
            from .gpu_capacity import mutate_gpu_capacity
            mutate_gpu_capacity(con, lease, 'LIVE')
            semantic_key = Allocator.semantic_event_key(
                lease, 'SCIENTIFIC_SOLVER_ENTERED', identity
            )
            allocator._event(
                con, lease, 'SCIENTIFIC_SOLVER_ENTERED',
                {'semantic_event_key': semantic_key, 'launch_identity': identity},
            )
        return identity

    def invoke(self, lease, callback: Callable, **identity):
        claim = self.claim(lease, **identity)
        # Never put this call inside the transaction or retry it on exceptions.
        Allocator(self.db).mark_entered(lease, launch_identity=claim)
        return claim, callback(claim)

    def record_process(self, lease, launch_id, *, pid, created_at, executable):
        if isinstance(pid, bool) or not isinstance(pid, int) or pid <= 0 or not created_at or not executable:
            raise ValueError('PROCESS_IDENTITY_REQUIRED')
        with self.db.immediate() as con:
            self._ensure(con)
            row = con.execute('SELECT * FROM scientific_launch_claims WHERE launch_id=?', (launch_id,)).fetchone()
            if row is None or (row['branch_id'],row['logical_case_id'],row['attempt_id'],row['lease_token_hash'],row['fencing_generation']) != (lease.owner_branch,lease.logical_case_id,lease.attempt_id,lease.token_hash,lease.fencing_generation):
                raise ValueError('PROCESS_LAUNCH_AUTHORITY_MISMATCH')
            evidence = {'launch_id':launch_id,'pid':pid,'created_at':created_at,'executable':executable}
            previous = con.execute("SELECT metadata_json FROM lease_events WHERE branch_id=? AND logical_case_id=? AND attempt_id=? AND event_type='SCIENTIFIC_PROCESS_BOUND'", (lease.owner_branch,lease.logical_case_id,lease.attempt_id)).fetchall()
            if previous:
                if any(json.loads(r['metadata_json']) != evidence for r in previous):
                    raise ValueError('PROCESS_LINEAGE_CONFLICT')
                return 'IDEMPOTENT_REPLAY_OF_EVENT'
            Allocator._event(con, lease, 'SCIENTIFIC_PROCESS_BOUND', evidence)
            return 'RECORDED'
