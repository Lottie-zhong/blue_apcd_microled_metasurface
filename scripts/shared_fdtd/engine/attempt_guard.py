from contextlib import contextmanager
from pathlib import Path
import os

from shared_fdtd.control_v3.db import ControlDB
from shared_fdtd.control_v3.launch_authority import LaunchAlreadyClaimed


@contextmanager
def exclusive_attempt(cfg):
    """Prevent concurrent host writes and reject historical entry before setup.

    OS locks die with the host; a durable launch claim does not. Retrying a
    genuinely pre-entry host remains possible, but any prior entry fails closed.
    """
    root = Path(cfg['attempt_root'])
    root.mkdir(parents=True, exist_ok=True)
    lock = (root / '.scientific_host.lock').open('a+b')
    locked = False
    try:
        lock.seek(0, 2)
        if lock.tell() == 0:
            lock.write(b'0'); lock.flush(); os.fsync(lock.fileno())
        lock.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            locked = True
        except OSError as exc:
            raise LaunchAlreadyClaimed('SCIENTIFIC_HOST_ALREADY_ACTIVE') from exc
        with ControlDB(cfg['db']).connect(readonly=True) as con:
            key = (cfg['branch'], cfg['case'], cfg['attempt'])
            if con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='scientific_launch_claims'").fetchone():
                if con.execute('SELECT 1 FROM scientific_launch_claims WHERE branch_id=? AND logical_case_id=? AND attempt_id=?', key).fetchone():
                    raise LaunchAlreadyClaimed('SCIENTIFIC_LAUNCH_ALREADY_CLAIMED')
            if con.execute("SELECT 1 FROM lease_events WHERE branch_id=? AND logical_case_id=? AND attempt_id=? AND event_type IN ('SCIENTIFIC_SOLVER_ENTERED','GPU_ENGINE_ENTRY_CONFIRMED')", key).fetchone():
                raise LaunchAlreadyClaimed('HISTORICAL_SCIENTIFIC_ENTRY_NO_REPLAY')
            row = con.execute('SELECT * FROM slots WHERE slot_id=?', (cfg['slot_id'],)).fetchone()
            if row is None or row['state'] != 'RESERVED' or (
                row['owner_branch'], row['logical_case_id'], row['attempt_id'],
                row['lease_token'], row['fencing_generation']
            ) != (*key, cfg['lease_token'], int(cfg['fencing_generation'])):
                raise LaunchAlreadyClaimed('HOST_OWNER_AUTHORITY_MISMATCH')
        yield
    finally:
        if locked:
            lock.seek(0)
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
        lock.close()
