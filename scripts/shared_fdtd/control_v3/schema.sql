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

CREATE TABLE IF NOT EXISTS admission_control (
  control_id INTEGER PRIMARY KEY CHECK(control_id = 1),
  new_entry_hold INTEGER NOT NULL CHECK(new_entry_hold IN (0,1)),
  temporary_runtime_cap INTEGER CHECK(temporary_runtime_cap IS NULL OR temporary_runtime_cap >= 1),
  health_status TEXT NOT NULL CHECK(health_status IN ('PASS','BLOCKED')),
  control_generation INTEGER NOT NULL CHECK(control_generation >= 0),
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

CREATE TABLE IF NOT EXISTS recovery_adoption_fences (
  fence_id TEXT PRIMARY KEY,
  branch_id TEXT NOT NULL,
  logical_case_id TEXT NOT NULL,
  attempt_id TEXT NOT NULL,
  expected_queue_state TEXT NOT NULL,
  expected_queue_updated_at TEXT NOT NULL,
  expected_slot_id TEXT NOT NULL,
  expected_lease_token_hash TEXT NOT NULL,
  expected_fencing_generation INTEGER NOT NULL,
  expected_control_generation INTEGER NOT NULL,
  evidence_manifest_sha256 TEXT NOT NULL,
  artifact_identity_sha256 TEXT NOT NULL,
  state TEXT NOT NULL CHECK(state IN ('ARMED','CONSUMED','ABORTED')),
  created_at TEXT NOT NULL,
  consumed_at TEXT,
  recovery_transaction_id TEXT,
  metadata_json TEXT NOT NULL DEFAULT '{}',
  UNIQUE(branch_id, logical_case_id, attempt_id)
);

CREATE TABLE IF NOT EXISTS exact_launch_permits (
  permit_id TEXT PRIMARY KEY,
  branch_id TEXT NOT NULL,
  logical_case_id TEXT NOT NULL,
  attempt_id TEXT NOT NULL,
  slot_id TEXT,
  lease_token_hash TEXT,
  fencing_generation INTEGER,
  authorization_generation INTEGER NOT NULL,
  state TEXT NOT NULL CHECK(state IN ('ARMED','CONSUMED','CANCELLED')),
  created_at TEXT NOT NULL,
  bound_at TEXT,
  consumed_at TEXT,
  cancelled_at TEXT,
  metadata_json TEXT NOT NULL DEFAULT '{}',
  UNIQUE(branch_id, logical_case_id, attempt_id)
);

CREATE TABLE IF NOT EXISTS hold_lifecycle (
  hold_id TEXT PRIMARY KEY,
  scope TEXT NOT NULL,
  status TEXT NOT NULL CHECK(status IN ('ACTIVE','RELEASED','CANCELLED')),
  reason_code TEXT NOT NULL,
  free_text_reason TEXT NOT NULL DEFAULT '',
  linked_incident_ids_json TEXT NOT NULL DEFAULT '[]',
  linked_case_ids_json TEXT NOT NULL DEFAULT '[]',
  release_requirements_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL,
  created_by TEXT NOT NULL,
  released_at TEXT,
  released_by TEXT,
  release_authority_hash TEXT,
  metadata_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS hold_events (
  event_id INTEGER PRIMARY KEY AUTOINCREMENT,
  hold_id TEXT NOT NULL,
  timestamp TEXT NOT NULL,
  event_type TEXT NOT NULL,
  actor TEXT NOT NULL,
  metadata_json TEXT NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_hold_lifecycle_active ON hold_lifecycle(status,scope);
CREATE TRIGGER IF NOT EXISTS hold_events_no_update BEFORE UPDATE ON hold_events BEGIN SELECT RAISE(ABORT, 'hold_events are append-only'); END;
CREATE TRIGGER IF NOT EXISTS hold_events_no_delete BEFORE DELETE ON hold_events BEGIN SELECT RAISE(ABORT, 'hold_events are append-only'); END;

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
