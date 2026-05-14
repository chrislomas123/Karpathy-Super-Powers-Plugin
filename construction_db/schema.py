"""Schema export helpers for the local SQLite database."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy.schema import CreateTable
from sqlalchemy.sql.ddl import CreateIndex
from sqlalchemy.dialects import sqlite

from construction_db.models import Base


def schema_sql() -> str:
    """Return SQLite DDL for all Phase 1 tables and indexes."""
    dialect = sqlite.dialect()
    statements: list[str] = []
    for table in Base.metadata.sorted_tables:
        statements.append(str(CreateTable(table).compile(dialect=dialect)).strip() + ";")
        for index in sorted(table.indexes, key=lambda item: item.name or ""):
            statements.append(str(CreateIndex(index).compile(dialect=dialect)).strip() + ";")
    return "\n\n".join(statements) + "\n"


def write_schema_sql(output_path: str | Path) -> Path:
    """Write SQLite DDL to a .sql file and return the output path."""
    output = Path(output_path).expanduser()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(schema_sql(), encoding="utf-8")
    return output
