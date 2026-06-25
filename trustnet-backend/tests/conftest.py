"""
TrustNet Integration Test Configuration
Creates SQLite-compatible tables via raw SQL and overrides the DB dependency.
"""

import asyncio
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Test DB engine (SQLite)
# ---------------------------------------------------------------------------
TEST_DB_URL = "sqlite+aiosqlite:///./test_integration.db"

test_engine = create_async_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)

TestSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def override_get_db():
    async with TestSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


# ---------------------------------------------------------------------------
# Create tables via raw SQL (avoids Postgres-only type conflicts)
# ---------------------------------------------------------------------------
CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    phone_hash TEXT,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    investigation_count INTEGER DEFAULT 0,
    is_trusted_reporter BOOLEAN DEFAULT 0
);

CREATE TABLE IF NOT EXISTS investigations (
    id TEXT PRIMARY KEY,
    user_id TEXT REFERENCES users(id),
    raw_input TEXT NOT NULL,
    input_type TEXT NOT NULL,
    entities_json TEXT NOT NULL DEFAULT '{}',
    trust_score INTEGER,
    confidence_score INTEGER,
    verdict TEXT NOT NULL,
    category_scores_json TEXT NOT NULL DEFAULT '{}',
    evidence_json TEXT NOT NULL DEFAULT '[]',
    hindi_explanation TEXT,
    blockchain_tx_hash TEXT,
    neo4j_connections_json TEXT,
    processing_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fee_amount_inr INTEGER,
    language_detected TEXT
);

CREATE TABLE IF NOT EXISTS entities (
    id TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL,
    entity_value TEXT NOT NULL,
    entity_hash TEXT UNIQUE NOT NULL,
    first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    investigation_count INTEGER DEFAULT 1,
    aggregate_score INTEGER,
    on_chain BOOLEAN DEFAULT 0,
    ring_name TEXT,
    last_refreshed_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS community_reports (
    id TEXT PRIMARY KEY,
    entity_id TEXT NOT NULL REFERENCES entities(id),
    reporter_user_id TEXT REFERENCES users(id),
    report_type TEXT NOT NULL,
    loss_amount_inr INTEGER,
    description TEXT,
    verified_by_admin BOOLEAN DEFAULT 0,
    reporter_weight REAL DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS company_master (
    cin TEXT PRIMARY KEY,
    company_name TEXT NOT NULL,
    registration_date TIMESTAMP,
    status TEXT,
    authorized_capital REAL,
    paid_up_capital REAL,
    state TEXT,
    directors_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS stats_counters (
    id TEXT PRIMARY KEY,
    total_investigations INTEGER DEFAULT 0,
    total_entities_flagged INTEGER DEFAULT 0,
    total_inr_protected INTEGER DEFAULT 0,
    total_on_chain_records INTEGER DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


async def create_test_tables():
    """Create all tables in the test SQLite DB using raw SQL."""
    async with test_engine.begin() as conn:
        for statement in CREATE_TABLES_SQL.strip().split(";"):
            stmt = statement.strip()
            if stmt:
                await conn.exec_driver_sql(stmt)


async def drop_test_tables():
    """Drop all tables after tests."""
    drop_sql = """
    DROP TABLE IF EXISTS community_reports;
    DROP TABLE IF EXISTS investigations;
    DROP TABLE IF EXISTS entities;
    DROP TABLE IF EXISTS company_master;
    DROP TABLE IF EXISTS stats_counters;
    DROP TABLE IF EXISTS users;
    """
    async with test_engine.begin() as conn:
        for statement in drop_sql.strip().split(";"):
            stmt = statement.strip()
            if stmt:
                await conn.exec_driver_sql(stmt)


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Session-scoped fixture: creates tables, overrides DB dep, runs tests, tears down."""
    # Override DB dependency on the app
    from main import app
    from app.models.database import get_db
    app.dependency_overrides[get_db] = override_get_db

    # Use a dedicated event loop for session-scoped async setup
    loop = asyncio.new_event_loop()
    loop.run_until_complete(create_test_tables())

    yield

    loop.run_until_complete(drop_test_tables())
    loop.close()
