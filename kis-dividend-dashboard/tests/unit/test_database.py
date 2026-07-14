from __future__ import annotations

from pathlib import Path
from typing import Final

from sqlalchemy.engine import make_url
from src.database import normalize_database_url

DASHBOARD_SCHEMA: Final = "kis_dashboard"


def test_postgres_url_preserves_connection_options_without_startup_search_path() -> None:
    # Given
    source = "postgresql://postgres:password@database.example:5432/postgres?sslmode=require"

    # When
    normalized = make_url(normalize_database_url(source))

    # Then
    assert normalized.drivername == "postgresql+psycopg"
    assert normalized.query["sslmode"] == "require"
    assert "options" not in normalized.query


def test_migration_creates_only_private_dashboard_tables() -> None:
    # Given
    migration = (Path(__file__).parents[2] / "migrations" / "001_initial_schema.sql").read_text(
        encoding="utf-8"
    )

    # When
    sql = migration.lower()

    # Then
    assert f"create schema if not exists {DASHBOARD_SCHEMA}" in sql
    assert f"{DASHBOARD_SCHEMA}.app_settings" in sql
    assert "public.app_settings" not in sql
