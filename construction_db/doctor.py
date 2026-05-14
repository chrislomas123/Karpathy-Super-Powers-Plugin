"""Environment and database health checks for Phase 1 deployments."""

from __future__ import annotations

import importlib.util
import sys
from ctypes.util import find_library
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from construction_db.database import database_tables
from construction_db.models import MODEL_REGISTRY, AppSetting, StageDefinition

DEPENDENCIES = ["sqlalchemy", "pandas", "openpyxl", "PySide6"]


def dependency_status() -> dict[str, bool]:
    """Return whether important runtime dependencies are importable."""
    return {name: importlib.util.find_spec(name) is not None for name in DEPENDENCIES}


def doctor_report(engine: Engine, session: Session, db_path: str | Path) -> str:
    """Return a human-readable system/database health report."""
    path = Path(db_path).expanduser()
    tables = set(database_tables(engine))
    required_tables = set(MODEL_REGISTRY)
    missing_tables = sorted(required_tables - tables)
    settings_count = session.scalar(select(func.count()).select_from(AppSetting)) or 0
    stage_count = session.scalar(select(func.count()).select_from(StageDefinition)) or 0

    lines = ["System Check"]
    lines.append(f"Database path: {path}")
    lines.append(f"Database exists: {'yes' if path.exists() else 'no'}")
    lines.append(f"Tables present: {len(tables)}")
    lines.append(f"Missing required tables: {', '.join(missing_tables) if missing_tables else 'none'}")
    lines.append(f"Seeded settings: {settings_count}")
    lines.append(f"Seeded stage definitions: {stage_count}")
    lines.append("Dependencies:")
    for name, installed in dependency_status().items():
        lines.append(f"  {name}: {'ok' if installed else 'missing'}")
    if sys.platform.startswith("linux"):
        lines.append(f"Linux libGL available: {'yes' if find_library('GL') else 'no'}")
    return "\n".join(lines)
