from __future__ import annotations

import aiosqlite

TABLES = [
    """
    CREATE TABLE IF NOT EXISTS devices (
        device_id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT DEFAULT '',
        ip TEXT DEFAULT '',
        port INTEGER DEFAULT 0,
        status TEXT DEFAULT 'online'
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS points (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        device_id INTEGER NOT NULL,
        object_type TEXT NOT NULL,
        object_instance INTEGER NOT NULL,
        object_name TEXT NOT NULL,
        description TEXT DEFAULT '',
        present_value TEXT DEFAULT '0',
        units TEXT DEFAULT '',
        cov_increment REAL DEFAULT 0.0,
        FOREIGN KEY (device_id) REFERENCES devices(device_id),
        UNIQUE(device_id, object_type, object_instance)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS endpoints (
        id TEXT PRIMARY KEY,
        url TEXT NOT NULL,
        secret TEXT NOT NULL,
        enabled INTEGER DEFAULT 1,
        event_types TEXT DEFAULT '[]',
        created_at TEXT,
        last_delivery_at TEXT,
        failure_count INTEGER DEFAULT 0
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS events (
        id TEXT PRIMARY KEY,
        event_type TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        payload TEXT NOT NULL,
        delivered INTEGER DEFAULT 0
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS alarms (
        id TEXT PRIMARY KEY,
        device_id INTEGER NOT NULL,
        point_name TEXT NOT NULL,
        severity TEXT NOT NULL,
        message TEXT NOT NULL,
        raised_at TEXT NOT NULL,
        cleared_at TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS telemetry (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        device_id INTEGER NOT NULL,
        points TEXT NOT NULL
    )
    """,
]


async def run_migrations(db_path: str) -> None:
    """Migrate atomically; retain v1 data and reject unknown future schemas."""
    import json
    from pathlib import Path

    from bacnet_lab.adapters.persistence.sqlite_repos import _parse_value

    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(db_path) as db:
        await db.execute("PRAGMA journal_mode = WAL")
        version = (await (await db.execute("PRAGMA user_version")).fetchone())[0]
        if version > 2:
            raise RuntimeError(f"Unsupported database schema version: {version}")
        await db.execute("BEGIN IMMEDIATE")
        try:
            for table_sql in TABLES:
                await db.execute(table_sql)
            if version < 2:
                columns = {
                    row[1]
                    for row in await (await db.execute("PRAGMA table_info(points)")).fetchall()
                }
                if "state_text" not in columns:
                    await db.execute(
                        "ALTER TABLE points ADD COLUMN state_text TEXT NOT NULL DEFAULT '[]'"
                    )
                rows = await (await db.execute("SELECT id, present_value FROM points")).fetchall()
                for identifier, value in rows:
                    await db.execute(
                        "UPDATE points SET present_value=? WHERE id=?",
                        (json.dumps(_parse_value(value)), identifier),
                    )
                await db.execute("""CREATE TABLE deliveries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT NOT NULL REFERENCES events(id) ON DELETE CASCADE,
                    endpoint_id TEXT NOT NULL REFERENCES endpoints(id) ON DELETE CASCADE,
                    state TEXT NOT NULL DEFAULT 'pending',
                    attempts INTEGER NOT NULL DEFAULT 0,
                    next_attempt REAL NOT NULL DEFAULT 0,
                    last_error TEXT,
                    UNIQUE(event_id, endpoint_id)
                )""")
                await db.execute("CREATE INDEX events_timestamp ON events(timestamp)")
                await db.execute("CREATE INDEX alarms_raised_at ON alarms(raised_at)")
                await db.execute(
                    "CREATE INDEX deliveries_pending ON deliveries(state, next_attempt)"
                )
                await db.execute("PRAGMA user_version = 2")
            await db.commit()
        except BaseException:
            await db.rollback()
            raise
