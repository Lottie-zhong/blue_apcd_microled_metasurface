PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS schema_meta (
  schema_version INTEGER NOT NULL,
  migration_version INTEGER NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS slots (
  slot_id TEXT PRIMARY KEY,
  state TEXT NOT NULL CHECK(state IN ('FREE','RESERVED','LIVE','RELEASE_PENDING','OWNER_QUARANTINED')),
  owner_branch TEXT,
  logical_case_id TEXT,
  attempt_id TEXT,
  lease_token TEXT,
  fencing_generation INTEGER NOT NULL DEFAULT 0,
  acquired_at TEXT,
  solver_entered_at TEXT,
  heartbeat_at TEXT,
  updated_at TEXT NOT NULL,
  version INTEGER NOT NULL DEFAULT 0,
  CHECK ((state='FREE' AND owner_branch IS NULL AND lease_token IS NULL) OR state<>'FREE')
);

CREATE TABLE IF NOT EXISTS branch_limits (
  branch_id TEXT PRIMARY KEY,
  cap INTEGER NOT NULL CHECK(cap >= 0),
  enabled INTEGER NOT NULL CHECK(enabled IN (0,1)),
  preferred_slot_order TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS lease_events (
  event_id INTEGER PRIMARY KEY AUTOINCREMENT,
  timestamp TEXT NOT NULL,
  slot_id TEXT NOT NULL,
  branch_id TEXT,
  logical_case_id TEXT,
  attempt_id TEXT,
  event_type TEXT NOT NULL,
  lease_token_hash TEXT,
  fencing_generation INTEGER,
  metadata_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS branch_queue (
  queue_id INTEGER PRIMARY KEY AUTOINCREMENT,
  branch_id TEXT NOT NULL,
  logical_case_id TEXT NOT NULL,
  attempt_id TEXT NOT NULL,
  state TEXT NOT NULL,
  payload_json TEXT NOT NULL DEFAULT '{}',
  slot_id TEXT,
  lease_token_hash TEXT,
  fencing_generation INTEGER,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE(branch_id, logical_case_id, attempt_id)
);

CREATE TABLE IF NOT EXISTS health_metrics (
  metric_name TEXT PRIMARY KEY,
  metric_value INTEGER NOT NULL DEFAULT 0,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS resource_reservations (
  reservation_id INTEGER PRIMARY KEY AUTOINCREMENT,
  branch_id TEXT NOT NULL,
  logical_case_id TEXT NOT NULL,
  attempt_id TEXT NOT NULL,
  slot_id TEXT NOT NULL,
  resource_class TEXT NOT NULL,
  backend_type TEXT NOT NULL DEFAULT 'CPU',
  estimated_peak_ram_bytes INTEGER,
  estimated_commit_bytes INTEGER,
  mpi_ranks INTEGER NOT NULL,
  threads INTEGER NOT NULL,
  integrated_pw INTEGER NOT NULL DEFAULT 0,
  safety_margin_ratio REAL NOT NULL,
  state TEXT NOT NULL CHECK(state IN ('RESERVED','LIVE','RELEASE_PENDING','OWNER_QUARANTINED','RELEASED')),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  released_at TEXT,
  UNIQUE(branch_id, logical_case_id, attempt_id)
);

CREATE INDEX IF NOT EXISTS idx_resource_reservations_active
  ON resource_reservations(state, branch_id, integrated_pw);

CREATE TABLE IF NOT EXISTS backend_capacity (
  backend_type TEXT PRIMARY KEY,
  physical_cap INTEGER NOT NULL CHECK(physical_cap BETWEEN 1 AND 3),
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS gpu_capacity_leases (
  capacity_lease_id INTEGER PRIMARY KEY AUTOINCREMENT,
  branch_id TEXT NOT NULL,
  logical_case_id TEXT NOT NULL,
  attempt_id TEXT NOT NULL,
  slot_id TEXT NOT NULL,
  lease_token_hash TEXT NOT NULL,
  fencing_generation INTEGER NOT NULL,
  state TEXT NOT NULL CHECK(state IN ('RESERVED','LIVE','RELEASE_PENDING','OWNER_QUARANTINED','RELEASED')),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  released_at TEXT,
  UNIQUE(branch_id, logical_case_id, attempt_id)
);

CREATE INDEX IF NOT EXISTS idx_gpu_capacity_leases_active
  ON gpu_capacity_leases(state);

CREATE TRIGGER IF NOT EXISTS lease_events_no_update
BEFORE UPDATE ON lease_events BEGIN SELECT RAISE(ABORT, 'lease_events are append-only'); END;
CREATE TRIGGER IF NOT EXISTS lease_events_no_delete
BEFORE DELETE ON lease_events BEGIN SELECT RAISE(ABORT, 'lease_events are append-only'); END;
