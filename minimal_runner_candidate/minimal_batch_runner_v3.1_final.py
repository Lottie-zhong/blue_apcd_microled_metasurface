"""
Minimal Batch Runner V3.1 Final - Production GPU FDTD Runner

Safety Enhancements:
- FAIL-CLOSED Resource Gate: Unknown state = HOLD, not proceed
- Cross-process GPU Mutex: Windows file lock
- Atomic No Replay: Transaction-protected solver_entries
- Single GPU serial execution
"""

import os
import sys
import json
import sqlite3
import argparse
import logging
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, Tuple

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)

class ResourceGateError(Exception):
    """Resource gate check failed - cannot proceed"""
    pass

class MinimalBatchRunner:
    """GPU FDTD Batch Runner with Fail-Closed Safety"""
    
    def __init__(self, db_path: str = "runner.db"):
        self.db_path = db_path
        self.gpu_lock_file = Path("gpu_runner.lock")
        self.gpu_lock_handle = None
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS batches (
                id INTEGER PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                description TEXT,
                status TEXT DEFAULT 'PENDING',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY,
                batch_id INTEGER NOT NULL,
                input_fsp_path TEXT NOT NULL,
                input_fsp_sha256 TEXT NOT NULL,
                status TEXT DEFAULT 'PENDING',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                started_at TEXT,
                completed_at TEXT,
                output_fsp_path TEXT,
                error_message TEXT,
                FOREIGN KEY(batch_id) REFERENCES batches(id)
            )
        """)
        
        # No Replay protection
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS solver_entries (
                id INTEGER PRIMARY KEY,
                job_id INTEGER NOT NULL UNIQUE,
                attempt_id TEXT NOT NULL,
                entered_at TEXT NOT NULL,
                FOREIGN KEY(job_id) REFERENCES jobs(id)
            )
        """)
        
        conn.commit()
        conn.close()
    
    def _acquire_gpu_lock(self, timeout: int = 30) -> bool:
        """
        Acquire cross-process GPU lock - FAIL-CLOSED
        Returns True if acquired, raises ResourceGateError if failed
        """
        try:
            import msvcrt
            
            # Try to acquire exclusive lock
            if self.gpu_lock_handle is None:
                self.gpu_lock_file.touch(exist_ok=True)
                self.gpu_lock_handle = open(str(self.gpu_lock_file), 'r+')
            
            try:
                msvcrt.locking(self.gpu_lock_handle.fileno(), msvcrt.LK_NBLCK, 1)
                logger.info("GPU lock acquired")
                return True
            except IOError:
                # Lock held by another process
                logger.error("GPU lock held by another runner instance")
                raise ResourceGateError("GPU already in use by another runner")
                
        except ImportError:
            # msvcrt not available - FAIL-CLOSED
            logger.error("Cannot verify GPU exclusivity (msvcrt unavailable)")
            raise ResourceGateError("Resource gate check unavailable - cannot proceed")
        except Exception as e:
            # Any other error - FAIL-CLOSED
            logger.error(f"GPU lock acquisition failed: {e}")
            raise ResourceGateError(f"Resource gate error: {e}")
    
    def _release_gpu_lock(self):
        """Release GPU lock"""
        if self.gpu_lock_handle:
            try:
                import msvcrt
                msvcrt.locking(self.gpu_lock_handle.fileno(), msvcrt.LK_UNLCK, 1)
                self.gpu_lock_handle.close()
                self.gpu_lock_handle = None
                logger.info("GPU lock released")
            except Exception as e:
                logger.warning(f"GPU lock release warning: {e}")
    
    def _check_no_replay(self, job_id: int) -> Tuple[bool, Optional[str]]:
        """Check if job already entered solver"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT attempt_id, entered_at FROM solver_entries WHERE job_id = ?",
            (job_id,)
        )
        entry = cursor.fetchone()
        conn.close()
        
        if entry:
            msg = f"No Replay: Job {job_id} already entered solver at {entry[1]} (attempt {entry[0]})"
            logger.error(msg)
            return False, msg
        
        return True, None
    
    def _record_solver_entry(self, job_id: int, attempt_id: str):
        """Atomically record solver entry BEFORE GPU call"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("BEGIN EXCLUSIVE TRANSACTION")
            
            # Re-check (防竞争)
            cursor.execute(
                "SELECT id FROM solver_entries WHERE job_id = ?",
                (job_id,)
            )
            if cursor.fetchone():
                raise RuntimeError(f"Job {job_id} already has solver entry (race)")
            
            # Insert entry record
            cursor.execute(
                """INSERT INTO solver_entries 
                   (job_id, attempt_id, entered_at) 
                   VALUES (?, ?, ?)""",
                (job_id, attempt_id, datetime.now().isoformat())
            )
            
            # Update job status
            cursor.execute(
                "UPDATE jobs SET status = ?, started_at = ? WHERE id = ?",
                ('RUNNING', datetime.now().isoformat(), job_id)
            )
            
            conn.commit()
            logger.info(f"Solver entry recorded atomically for job {job_id} (attempt {attempt_id})")
            
        except Exception as e:
            conn.rollback()
            raise RuntimeError(f"Failed to record solver entry: {e}")
        finally:
            conn.close()
    
    def run_job(self, job_id: int, input_fsp: str, 
                output_fsp: str, fake_solver: bool = False) -> Tuple[bool, Optional[str]]:
        """Execute GPU FDTD job with full safety gates"""
        
        logger.info(f"Starting job {job_id}")
        
        # Safety Gate 1: No Replay
        ok, msg = self._check_no_replay(job_id)
        if not ok:
            return False, msg
        
        # Safety Gate 2: GPU Resource (FAIL-CLOSED)
        try:
            self._acquire_gpu_lock()
        except ResourceGateError as e:
            return False, str(e)
        
        try:
            # Safety Gate 3: Atomic Entry Record
            attempt_id = f"attempt_{job_id}_{int(time.time() % 100000):03d}"
            try:
                self._record_solver_entry(job_id, attempt_id)
            except RuntimeError as e:
                return False, str(e)
            
            # Execute solver
            if fake_solver:
                # Fake: Copy input as output
                Path(output_fsp).parent.mkdir(parents=True, exist_ok=True)
                Path(output_fsp).write_bytes(Path(input_fsp).read_bytes())
                time.sleep(0.5)
            else:
                # Real GPU solver
                import lumapi
                
                logger.info(f"Loading FSP: {input_fsp}")
                fdtd = lumapi.FDTD()
                fdtd.load(input_fsp)
                
                logger.info("Running FDTD with GPU backend")
                fdtd.run('FDTD', 'GPU')
                
                logger.info(f"Saving output: {output_fsp}")
                Path(output_fsp).parent.mkdir(parents=True, exist_ok=True)
                fdtd.save(output_fsp)
                fdtd.close()
            
            # Mark complete
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE jobs SET status = ?, completed_at = ?, output_fsp_path = ? WHERE id = ?",
                ('COMPLETED', datetime.now().isoformat(), output_fsp, job_id)
            )
            conn.commit()
            conn.close()
            
            # Verify output
            if not Path(output_fsp).exists():
                return False, "Output FSP not created"
            
            output_size = Path(output_fsp).stat().st_size
            logger.info(f"Job {job_id} completed. Output: {output_size} bytes")
            return True, None
            
        except Exception as e:
            logger.error(f"Solver failed: {e}")
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE jobs SET status = ?, error_message = ?, completed_at = ? WHERE id = ?",
                ('FAILED', str(e), datetime.now().isoformat(), job_id)
            )
            conn.commit()
            conn.close()
            
            return False, str(e)
        
        finally:
            # Always release lock
            self._release_gpu_lock()
    
    def submit_batch(self, manifest_path: str) -> Tuple[bool, Optional[str]]:
        """Submit batch manifest"""
        manifest = json.loads(Path(manifest_path).read_text())
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "INSERT INTO batches (name, description) VALUES (?, ?)",
                (manifest['batch_name'], manifest.get('description', ''))
            )
            batch_id = cursor.lastrowid
            
            for job in manifest.get('jobs', []):
                cursor.execute(
                    """INSERT INTO jobs 
                       (batch_id, input_fsp_path, input_fsp_sha256)
                       VALUES (?, ?, ?)""",
                    (batch_id, job['input_fsp'], job.get('sha256', ''))
                )
            
            conn.commit()
            logger.info(f"Batch {manifest['batch_name']} submitted (ID {batch_id})")
            return True, None
            
        except Exception as e:
            conn.rollback()
            return False, str(e)
        finally:
            conn.close()
    
    def run_batch(self, batch_name: str, fake_solver: bool = False) -> Tuple[int, int]:
        """Run all pending jobs in batch"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM batches WHERE name = ?", (batch_name,))
        batch = cursor.fetchone()
        if not batch:
            logger.error(f"Batch {batch_name} not found")
            return 0, 0
        
        batch_id = batch[0]
        
        cursor.execute(
            """SELECT id, input_fsp_path FROM jobs 
               WHERE batch_id = ? AND status = 'PENDING'
               ORDER BY id""",
            (batch_id,)
        )
        jobs = cursor.fetchall()
        conn.close()
        
        completed = 0
        failed = 0
        
        for job_id, input_fsp in jobs:
            output_dir = Path('outputs') / f'batch_{batch_id}'
            output_fsp = str(output_dir / f'job_{job_id}_output.fsp')
            
            ok, msg = self.run_job(job_id, input_fsp, output_fsp, fake_solver=fake_solver)
            
            if ok:
                completed += 1
            else:
                logger.error(f"Job {job_id} failed: {msg}")
                failed += 1
        
        return completed, failed
    
    def status_batch(self, batch_name: str) -> Dict:
        """Get batch status"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                b.name,
                COUNT(j.id) as total,
                SUM(CASE WHEN j.status = 'COMPLETED' THEN 1 ELSE 0 END) as completed,
                SUM(CASE WHEN j.status = 'PENDING' THEN 1 ELSE 0 END) as pending,
                SUM(CASE WHEN j.status = 'FAILED' THEN 1 ELSE 0 END) as failed
            FROM batches b
            LEFT JOIN jobs j ON b.id = j.batch_id
            WHERE b.name = ?
            GROUP BY b.id
        """, (batch_name,))
        
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return {}
        
        return {
            'batch_name': result[0],
            'total': result[1] or 0,
            'completed': result[2] or 0,
            'pending': result[3] or 0,
            'failed': result[4] or 0
        }

def main():
    parser = argparse.ArgumentParser(description='Minimal GPU FDTD Batch Runner V3.1 Final')
    parser.add_argument('command', choices=['submit', 'run', 'status'],
                        help='Command to execute')
    parser.add_argument('batch_name', help='Batch name')
    parser.add_argument('--manifest', help='Manifest file path (for submit)')
    parser.add_argument('--fake-solver', action='store_true',
                        help='Use fake solver for testing')
    parser.add_argument('--db', default='runner.db', help='Database path')
    
    args = parser.parse_args()
    
    runner = MinimalBatchRunner(db_path=args.db)
    
    if args.command == 'submit':
        if not args.manifest:
            print("Error: --manifest required for submit")
            sys.exit(1)
        ok, msg = runner.submit_batch(args.manifest)
        if not ok:
            print(f"Submit failed: {msg}")
            sys.exit(1)
        print(f"Batch {args.batch_name} submitted")
    
    elif args.command == 'run':
        print(f"Running batch {args.batch_name}")
        try:
            completed, failed = runner.run_batch(args.batch_name, fake_solver=args.fake_solver)
            print(f"Completed: {completed}, Failed: {failed}")
        except ResourceGateError as e:
            print(f"Resource gate blocked: {e}")
            sys.exit(2)
    
    elif args.command == 'status':
        status = runner.status_batch(args.batch_name)
        if status:
            print(f"Batch: {status['batch_name']}")
            print(f"  Total: {status['total']}")
            print(f"  Completed: {status['completed']}")
            print(f"  Pending: {status['pending']}")
            print(f"  Failed: {status['failed']}")
        else:
            print(f"Batch {args.batch_name} not found")

if __name__ == '__main__':
    main()
