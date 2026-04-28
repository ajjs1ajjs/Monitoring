#!/usr/bin/env python3
"""Migrate data from SQLite (pymon.db) to PostgreSQL (DSN via psycopg2).
This is a basic migration helper suitable for initial migrations. It will create
the target tables if they do not exist and copy over servers and metrics_history.
"""

import argparse
import sqlite3
import sys
from datetime import datetime

try:
    import psycopg2
except Exception:
    psycopg2 = None

def ensure_tables(pg_conn):
    with pg_conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS servers (
              id INTEGER PRIMARY KEY,
              name TEXT,
              host TEXT,
              os_type TEXT,
              agent_port INTEGER,
              last_status TEXT,
              created_at TIMESTAMP
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS metrics (
              id SERIAL PRIMARY KEY,
              server_id INTEGER,
              name TEXT,
              labels TEXT,
              value REAL,
              timestamp TIMESTAMP
            )
            """
        )
        pg_conn.commit()

def migrate(sqlite_path: str, pg_dsn: str, dry_run: bool = False) -> int:
    if psycopg2 is None:
        print("psycopg2 is not installed. Install psycopg2-binary to proceed.")
        return 2

    # Connect to SQLite
    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_conn.row_factory = sqlite3.Row
    cur = sqlite_conn.cursor()

    # Connect to PostgreSQL
    pg_conn = psycopg2.connect(pg_dsn)
    try:
        ensure_tables(pg_conn)
        pg_cur = pg_conn.cursor()
        # Migrate servers (best-effort upsert by id)
        cur.execute("SELECT id, name, host, os_type, agent_port, last_status, created_at FROM servers")
        servers = cur.fetchall()
        for s in servers:
            pg_cur.execute(
                "INSERT INTO servers (id, name, host, os_type, agent_port, last_status, created_at) VALUES (%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (id) DO NOTHING",
                (s[0], s[1], s[2], s[3], s[4], s[5], s[6] or datetime.now()),
            )
        # Migrate metrics
        cur.execute("SELECT server_id, name, labels, value, timestamp FROM metrics_history")
        for r in cur.fetchall():
            pg_cur.execute(
                "INSERT INTO metrics (server_id, name, labels, value, timestamp) VALUES (%s,%s,%s,%s,%s)",
                (r[0], r[1], r[2], r[3], r[4]),
            )
        if not dry_run:
            pg_conn.commit()
        print("Migration completed (dry_run=%s)." % dry_run)
        return 0
    except Exception as e:
        print("Migration error:", e)
        if not dry_run:
            pg_conn.rollback()
        return 1
    finally:
        sqlite_conn.close()
        pg_cur.close() if 'pg_cur' in locals() else None
        pg_conn.close() if 'pg_conn' in locals() else None

def main():
    ap = argparse.ArgumentParser(prog="migrate_sqlite_to_postgres", description="Migrate PyMon data from SQLite to PostgreSQL")
    ap.add_argument("--sqlite", required=True, help="Path to sqlite DB (pymon.db)")
    ap.add_argument("--pg-dsn", required=True, help="PostgreSQL DSN (postgresql://user:pass@host/db)")
    ap.add_argument("--dry-run", action="store_true", help="Dry run (no writes to PostgreSQL)")
    args = ap.parse_args()
    code = migrate(args.sqlite, args.pgdsn, dry_run=args.dry_run)
    sys.exit(code)

if __name__ == "__main__":
    main()
