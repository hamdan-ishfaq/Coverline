"""Schema builds end-to-end and the audit_log append-only triggers really block."""

import sqlite3

import pytest

from sap_schema.ddl import DATABASES, create


@pytest.fixture(scope="module")
def conns():
    conns = {name: sqlite3.connect(":memory:") for name in DATABASES}
    for name, conn in conns.items():
        create(name, conn)
    yield conns
    for conn in conns.values():
        conn.close()


@pytest.mark.parametrize("db_name", sorted(DATABASES))
def test_all_databases_build(conns, db_name):
    tables = conns[db_name].execute(
        "SELECT name FROM sqlite_master WHERE type = 'table'"
    ).fetchall()
    assert len(tables) >= 1


def test_audit_log_accepts_insert(conns):
    conn = conns["state"]
    with conn:
        conn.execute(
            "INSERT INTO audit_log (ts, stream, action, actor, row_hash, prev_hash)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            ("2026-10-13T00:00:00", "policy", "update", "user", "h1", ""),
        )
    assert conn.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0] == 1


def test_audit_log_rejects_update(conns):
    conn = conns["state"]
    with pytest.raises(sqlite3.IntegrityError):
        with conn:
            conn.execute("UPDATE audit_log SET payload = 'tampered' WHERE entry_id = 1")


def test_audit_log_rejects_delete(conns):
    conn = conns["state"]
    with pytest.raises(sqlite3.IntegrityError):
        with conn:
            conn.execute("DELETE FROM audit_log WHERE entry_id = 1")