"""SQLite backup helpers for local-first Phase 1 databases."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path


def default_backup_path(db_path: str | Path) -> Path:
    """Return a timestamped backup path next to the source database."""
    source = Path(db_path).expanduser()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return source.with_name(f"{source.stem}_backup_{timestamp}{source.suffix or '.sqlite3'}")


def backup_database(db_path: str | Path, output_path: str | Path | None = None) -> Path:
    """Create a consistent SQLite backup using SQLite's online backup API."""
    source = Path(db_path).expanduser()
    if not source.exists():
        raise FileNotFoundError(f"Database does not exist: {source}")
    destination = Path(output_path).expanduser() if output_path else default_backup_path(source)
    destination.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(source) as source_connection:
        with sqlite3.connect(destination) as destination_connection:
            source_connection.backup(destination_connection)
    return destination
