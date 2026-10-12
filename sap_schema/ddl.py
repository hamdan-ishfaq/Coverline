"""DDL for the three SQLite databases (TRD Section 4.1/4.2).

- po_triage.db     read-only BUILD artifact: SAP-shaped tables, case_files,
                   vendor_messages, options, extracted signals, predictions.
- state.db         runtime state: decisions, audit_log (append-only via
                   triggers), policy_config.
- eval_truth.db    eval ground truth: planted_rules, vendor_message_gold.

Every statement in this file must execute with sqlite3 (SQLAlchemy is used for
queries at runtime, but the schema activity is plain SQL). Tests build all three
in-memory and assert the append-only triggers reject UPDATE/DELETE.
"""

from __future__ import annotations

import sqlite3

# ---------------------------------------------------------------------------
# po_triage.db
# ---------------------------------------------------------------------------

PO_TRIAGE_DDL: list[str] = [
    """
    CREATE TABLE IF NOT EXISTS lfb1 (
        vendor_id    TEXT NOT NULL,
        company_code TEXT NOT NULL,
        vendor_name  TEXT NOT NULL,
        vendor_group TEXT,
        abc_class    TEXT,
        PRIMARY KEY (vendor_id, company_code)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS mara (
        material_id    TEXT NOT NULL PRIMARY KEY,
        material_type  TEXT,
        material_text  TEXT,
        procurement_type TEXT,   -- foreign/standard, in-house, consignment
        replenishment   TEXT,
        abc_class       TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS marc (
        plant        TEXT NOT NULL,
        material_id  TEXT NOT NULL,
        repl_qty     REAL,
        safety_stock REAL,
        lead_time_days INTEGER,
        PRIMARY KEY (plant, material_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS ekpo (
        po_number    TEXT NOT NULL,
        po_item      INTEGER NOT NULL,
        doc_type     TEXT,       -- NB, NB2 (blanket)
        material_id  TEXT,
        plant        TEXT,
        order_qty    REAL,
        order_val    REAL,
        confirms_qty REAL,
        scheduled_delivery_date TEXT,   -- ISO date
        po_condition TEXT,
        PRIMARY KEY (po_number, po_item)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS ekbe (
        po_number    TEXT NOT NULL,
        po_item      INTEGER NOT NULL,
        movement_type TEXT,
        quantity     REAL,
        base_quantity REAL,
        movement_date TEXT,       -- ISO date
        bwart_code   TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS ekko (
        po_number   TEXT NOT NULL PRIMARY KEY,
        vendor_id   TEXT,
        company_code TEXT,
        currency    TEXT,
        document_date TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS maarap (
        vendor_id        TEXT NOT NULL,
        company_code     TEXT NOT NULL,
        material_id      TEXT,
        credit_limit_amt REAL,
        utilization_pct  REAL,
        PRIMARY KEY (vendor_id, company_code, material_id)
    )
    """,
    # Forecast of open load, per vendor, used for the capacity feature.
    """
    CREATE TABLE IF NOT EXISTS forecast (
        vendor_id         TEXT NOT NULL,
        as_of             TEXT NOT NULL,
        forecast_qty      REAL,
        forecast_value    REAL,
        PRIMARY KEY (vendor_id, as_of)
    )
    """,
    # Model outputs (M4) + projections (M5). Label h per line (TRD 5.1/5.2).
    """
    CREATE TABLE IF NOT EXISTS predictions (
        line_id            TEXT NOT NULL PRIMARY KEY,
        po_number          TEXT NOT NULL,
        po_item            INTEGER NOT NULL,
        feature_days_to_due INTEGER,
        pred_on_time_conf   REAL,
        pred_late_conf      REAL,
        pred_recovery_conf  REAL,
        planted_rule_id    TEXT,      -- links to eval_truth.planted_rules
        label_confirmed_in_time INTEGER,   -- 1/0, tolerance_days from prereg
        snapshot_h         INTEGER
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS case_files (
        line_id      TEXT NOT NULL PRIMARY KEY,
        po_number    TEXT NOT NULL,
        po_item      INTEGER NOT NULL,
        opened_at    TEXT,
        trigger      TEXT,
        severity     TEXT,
        lineage      TEXT            -- OFF-PLAN / LATE / COST-INFLATION / DROPPED
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS options (
        option_id    TEXT NOT NULL PRIMARY KEY,
        line_id      TEXT NOT NULL,
        option_type  TEXT,           -- expedite / split / transfer / accept
        vendor_id    TEXT,
        delta_value  REAL,
        pl_cost_k    REAL,
        p95_cost_k   REAL,
        pl_recovery  REAL,
        etr_days     INTEGER
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS vendor_messages (
        message_id  TEXT NOT NULL PRIMARY KEY,
        line_id     TEXT NOT NULL,
        provider    TEXT,            -- vendor / system
        direction   TEXT,            -- inbound / outbound
        sent_at     TEXT,
        body        TEXT,            -- BODY; address stored separately (TRD 4.1)
        deliverable TEXT            -- confirmation / asn / query
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS extracted_signals (
        signal_id   TEXT NOT NULL PRIMARY KEY,
        message_id  TEXT NOT NULL,
        line_id     TEXT NOT NULL,
        cq          TEXT,            -- confirmed quantity
        cd          TEXT,            -- confirmed date
        etr         TEXT,            -- estimated time of recovery
        confidence  REAL,
        extracted_at TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS eval_runs (
        run_id       TEXT NOT NULL PRIMARY KEY,
        stamps       TEXT,
        llm_mode     TEXT,
        provider     TEXT,
        duration_s   REAL,
        policy_hash  TEXT
    )
    """,
]

# ---------------------------------------------------------------------------
# state.db (runtime, per-session on Streamlit Cloud)
# ---------------------------------------------------------------------------

STATE_DDL: list[str] = [
    """
    CREATE TABLE IF NOT EXISTS decisions (
        decision_id     TEXT NOT NULL PRIMARY KEY,
        line_id         TEXT NOT NULL,
        option_id       TEXT,
        action          TEXT,        -- approved / rejected / deferred / auto_close
        rationale       TEXT,
        decided_by      TEXT,        -- agent / user
        decided_at      TEXT,
        approval_tier   TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS audit_log (
        entry_id   INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
        ts         TEXT NOT NULL,
        stream     TEXT NOT NULL,    -- intake / policy / decision / admin / config
        action     TEXT NOT NULL,
        actor      TEXT,
        line_ids   TEXT,             -- JSON list
        payload    TEXT,             -- JSON snapshot of what happened
        row_hash   TEXT NOT NULL,
        prev_hash  TEXT NOT NULL DEFAULT ''
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS policy_config (
        key        TEXT NOT NULL PRIMARY KEY,
        value      TEXT,             -- JSON-encoded
        changed_at TEXT,
        changed_by TEXT
    )
    """,
]

# Append-only every row, chained by prev_hash (TRD 4.1/9.2). A trigger on the
# table, not app logic, is what makes it structural.
STATE_TRIGGERS: list[str] = [
    """
    CREATE TRIGGER IF NOT EXISTS audit_log_append_only_update
    BEFORE UPDATE ON audit_log
    BEGIN
        SELECT RAISE(ABORT, 'audit_log is append-only (UPDATE blocked)');
    END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS audit_log_append_only_delete
    BEFORE DELETE ON audit_log
    BEGIN
        SELECT RAISE(ABORT, 'audit_log is append-only (DELETE blocked)');
    END
    """,
]

# ---------------------------------------------------------------------------
# eval_truth.db
# ---------------------------------------------------------------------------

EVAL_TRUTH_DDL: list[str] = [
    """
    CREATE TABLE IF NOT EXISTS planted_rules (
        rule_id       TEXT NOT NULL PRIMARY KEY,
        rule_desc     TEXT NOT NULL,
        rule_params   TEXT NOT NULL     -- JSON map, e.g. {"quarter": "Q3"}
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS vendor_message_gold (
        message_id  TEXT NOT NULL PRIMARY KEY,
        line_id     TEXT NOT NULL,
        cq_gold     TEXT,
        cd_gold     TEXT,
        etr_gold    TEXT,
        source      TEXT,               -- template variant that produced it
        grade       TEXT                -- set by the extraction evaluator
    )
    """,
]

# ---------------------------------------------------------------------------
# Per-database registry + helpers
# ---------------------------------------------------------------------------

DATABASES: dict[str, tuple[list[str], list[str]]] = {
    "po_triage": (PO_TRIAGE_DDL, []),
    "state": (STATE_DDL, STATE_TRIGGERS),
    "eval_truth": (EVAL_TRUTH_DDL, []),
}


def create(db_name: str, conn: sqlite3.Connection) -> None:
    """Create tables (and triggers if any) for one database on an existing connection."""
    if db_name not in DATABASES:
        raise KeyError(f"unknown database: {db_name}")
    ddl, triggers = DATABASES[db_name]
    with conn:
        for statement in (*ddl, *triggers):
            conn.execute(statement)


def create_all(conns: dict[str, sqlite3.Connection]) -> None:
    """Create every database on the given connection map (used by tests and ingester)."""
    for db_name, conn in conns.items():
        create(db_name, conn)