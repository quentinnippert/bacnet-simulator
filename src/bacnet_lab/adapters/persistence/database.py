from contextlib import asynccontextmanager

import aiosqlite


@asynccontextmanager
async def connect(path: str):
    async with aiosqlite.connect(path, timeout=10) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA foreign_keys = ON")
        yield db
