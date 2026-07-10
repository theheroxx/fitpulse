# migrate_to_postgres.py
"""
Migrate SQLite database to PostgreSQL.
Run once to transfer all data.

Usage:
    python migrate_to_postgres.py
"""

import sqlite3
import psycopg2
from psycopg2 import sql
import os
import sys

# ─── PostgreSQL configuration ───────────────────────────────────────
PG_HOST = os.getenv("PG_HOST", "localhost")
PG_PORT = os.getenv("PG_PORT", "5432")
PG_DB = os.getenv("PG_DB", "fitpulse")
PG_USER = os.getenv("PG_USER", "admin")
PG_PASS = os.getenv("PG_PASS", "hossein100")

# ─── SQLite database path ──────────────────────────────────────────
SQLITE_PATH = "D:/ED/database/ed_database.db"   # adjust if needed

def get_sqlite_connection():
    return sqlite3.connect(SQLITE_PATH)

def get_pg_connection():
    return psycopg2.connect(
        host=PG_HOST,
        port=PG_PORT,
        dbname=PG_DB,
        user=PG_USER,
        password=PG_PASS
    )

def table_exists(conn, table_name):
    cur = conn.cursor()
    cur.execute(
        "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = %s)",
        (table_name,)
    )
    exists = cur.fetchone()[0]
    cur.close()
    return exists

def drop_table_if_exists(conn, table_name):
    cur = conn.cursor()
    cur.execute(sql.SQL("DROP TABLE IF EXISTS {} CASCADE").format(sql.Identifier(table_name)))
    conn.commit()
    cur.close()
    print(f"  Dropped existing table {table_name} (if any)")

def get_sqlite_schema(sqlite_conn, table_name):
    """Extract column info from SQLite PRAGMA."""
    cursor = sqlite_conn.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    # columns: (cid, name, type, notnull, dflt_value, pk)
    return columns

def sqlite_type_to_pg(sqlite_type, is_pk=False):
    """Map SQLite types to PostgreSQL types."""
    sqlite_type = sqlite_type.upper()
    if is_pk and sqlite_type == "INTEGER":
        return "SERIAL PRIMARY KEY"
    if sqlite_type.startswith("INT"):
        return "INTEGER"
    if sqlite_type.startswith("TEXT") or "VARCHAR" in sqlite_type:
        return "TEXT"
    if sqlite_type.startswith("REAL") or sqlite_type.startswith("FLOAT") or sqlite_type.startswith("DOUBLE"):
        return "DOUBLE PRECISION"
    if sqlite_type.startswith("BOOLEAN"):
        return "BOOLEAN"
    if sqlite_type.startswith("TIMESTAMP") or sqlite_type.startswith("DATETIME"):
        return "TIMESTAMP"
    if sqlite_type.startswith("BLOB"):
        return "BYTEA"
    # default
    return "TEXT"

def build_create_table_sql(columns, table_name):
    """Generate CREATE TABLE SQL from column info."""
    col_defs = []
    for col in columns:
        cid, name, col_type, notnull, dflt_value, pk = col
        pg_type = sqlite_type_to_pg(col_type, pk and not (pk == 0))
        if pk and col_type.upper() == "INTEGER":
            # Already handled by sqlite_type_to_pg for SERIAL
            pass

        # Build column definition
        col_def = f'"{name}" {pg_type}'

        if notnull and not (pk and col_type.upper() == "INTEGER"):
            col_def += " NOT NULL"

        # Handle default values: convert boolean literals
        if dflt_value is not None:
            if pg_type == "BOOLEAN":
                if dflt_value in ("0", "1"):
                    dflt_value = "TRUE" if dflt_value == "1" else "FALSE"
            col_def += f" DEFAULT {dflt_value}"

        col_defs.append(col_def)

    create_stmt = f'CREATE TABLE "{table_name}" (\n  ' + ',\n  '.join(col_defs) + '\n);'
    return create_stmt

def create_table_in_pg(pg_conn, sqlite_conn, table_name):
    """Create table in PostgreSQL (drop if exists)."""
    columns = get_sqlite_schema(sqlite_conn, table_name)
    if not columns:
        print(f"  Skipping {table_name} (no columns)")
        return

    if table_exists(pg_conn, table_name):
        drop_table_if_exists(pg_conn, table_name)

    create_sql = build_create_table_sql(columns, table_name)
    print(f"  CREATE SQL for {table_name}: {create_sql[:200]}...")  # debug
    cur = pg_conn.cursor()
    cur.execute(create_sql)
    pg_conn.commit()
    cur.close()
    print(f"  Created table {table_name}")


def get_pg_column_types(pg_conn, table_name):
    cur = pg_conn.cursor()
    cur.execute("""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = %s
    """, (table_name,))
    types = {row[0]: row[1] for row in cur.fetchall()}
    cur.close()
    return types

def copy_table_data(pg_conn, sqlite_conn, table_name):
    columns = get_sqlite_schema(sqlite_conn, table_name)
    col_names = [col[1] for col in columns]
    col_types = [col[2] for col in columns]  # SQLite type

    # Get PostgreSQL column data types
    pg_types = get_pg_column_types(pg_conn, table_name)

    sqlite_cursor = sqlite_conn.cursor()
    sqlite_cursor.execute(f"SELECT * FROM {table_name}")
    rows = sqlite_cursor.fetchall()
    sqlite_cursor.close()

    if not rows:
        print(f"  No data to copy for {table_name}")
        return

    pg_cursor = pg_conn.cursor()
    placeholders = ','.join(['%s'] * len(col_names))
    insert_sql = f'INSERT INTO "{table_name}" ({",".join(col_names)}) VALUES ({placeholders})'

    for row in rows:
        converted_row = list(row)
        for i, val in enumerate(converted_row):
            col_name = col_names[i]
            pg_type = pg_types.get(col_name, '').lower()
            # If PostgreSQL column is boolean, convert 0/1 to False/True
            if pg_type == 'boolean':
                # val should be 0 or 1 from SQLite; convert to Python bool
                converted_row[i] = bool(val) if val is not None else None
        pg_cursor.execute(insert_sql, converted_row)

    pg_conn.commit()
    pg_cursor.close()
    print(f"  Copied {len(rows)} rows to {table_name}")

def main():
    print("🔁 Starting migration from SQLite to PostgreSQL")
    if not os.path.exists(SQLITE_PATH):
        print(f"❌ SQLite database not found at {SQLITE_PATH}")
        sys.exit(1)

    print(f"📂 SQLite DB: {SQLITE_PATH}")
    print(f"🐘 PostgreSQL: {PG_USER}@{PG_HOST}:{PG_PORT}/{PG_DB}")

    sqlite_conn = get_sqlite_connection()
    pg_conn = get_pg_connection()
    pg_conn.autocommit = False

    # Get list of user tables
    sqlite_cursor = sqlite_conn.cursor()
    sqlite_cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    )
    tables = [row[0] for row in sqlite_cursor.fetchall()]
    sqlite_cursor.close()
    print(f"📋 Found tables: {', '.join(tables)}")

    # Grant superuser to admin if needed (we'll try to set replication role)
    # If it fails, we skip it and continue.
    pg_cursor = pg_conn.cursor()
    try:
        pg_cursor.execute("SET session_replication_role = 'replica';")
        pg_conn.commit()
        print("✅ Disabled foreign key checks (superuser mode).")
    except Exception as e:
        print(f"⚠️ Could not disable foreign key checks: {e}")
        print("   Continuing anyway (may fail if foreign keys conflict).")
    pg_cursor.close()

    # Create tables and copy data
    for table in tables:
        print(f"🔄 Processing {table}...")
        create_table_in_pg(pg_conn, sqlite_conn, table)
        copy_table_data(pg_conn, sqlite_conn, table)
        print()

    # Re-enable foreign key checks
    pg_cursor = pg_conn.cursor()
    try:
        pg_cursor.execute("SET session_replication_role = 'origin';")
        pg_conn.commit()
        print("✅ Re-enabled foreign key checks.")
    except Exception as e:
        print(f"⚠️ Could not re-enable foreign key checks: {e}")
    pg_cursor.close()

    sqlite_conn.close()
    pg_conn.close()

    print("✅ Migration completed successfully!")

if __name__ == "__main__":
    main()