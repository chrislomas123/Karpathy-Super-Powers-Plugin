"""First-run workbook bootstrap workflow for the local database app."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from construction_db.backup import backup_database
from construction_db.database import dashboard_counts
from construction_db.excel_io import import_from_excel
from construction_db.followups import generate_default_followups
from construction_db.models import MODEL_REGISTRY

USER_DATA_TABLES = [
    "companies",
    "contacts",
    "projects",
    "bid_opportunities",
    "project_contacts",
    "email_activity",
    "attachments",
    "follow_ups",
    "import_batches",
]


@dataclass(frozen=True)
class BootstrapSummary:
    workbook_path: Path
    db_path: Path
    backup_path: Path | None
    imported_rows: dict[str, int]
    generated_followups: int
    dashboard_counts: dict[str, int]


def bootstrap_workbook(session: Session, db_path: str | Path, workbook_path: str | Path) -> BootstrapSummary:
    """Safely import a workbook, generate follow-ups, and return a readable summary payload."""
    database = Path(db_path).expanduser()
    workbook = Path(workbook_path).expanduser()
    backup_path = backup_database(database) if database.exists() and has_user_data(session) else None

    imported_rows = import_from_excel(session, workbook)
    generated_followups = generate_default_followups(session)
    counts = dashboard_counts(session)

    return BootstrapSummary(
        workbook_path=workbook,
        db_path=database,
        backup_path=backup_path,
        imported_rows=imported_rows,
        generated_followups=len(generated_followups),
        dashboard_counts=counts,
    )


def has_user_data(session: Session) -> bool:
    """Return whether user-facing records exist beyond seeded settings/lookups."""
    return any(count_user_rows(session).values())


def count_user_rows(session: Session) -> dict[str, int]:
    """Count rows in user-facing tables that should trigger a backup before bootstrap."""
    counts: dict[str, int] = {}
    for table_name in USER_DATA_TABLES:
        model = MODEL_REGISTRY[table_name]
        counts[table_name] = session.scalar(select(func.count()).select_from(model)) or 0
    return counts


def format_bootstrap_summary(summary: BootstrapSummary) -> str:
    """Format bootstrap results for CLI output."""
    lines = [
        "Workbook bootstrap complete",
        f"Workbook: {summary.workbook_path}",
        f"Database: {summary.db_path}",
    ]
    if summary.backup_path:
        lines.append(f"Backup created: {summary.backup_path}")
    else:
        lines.append("Backup created: not needed; no existing user data was found")

    lines.append("Imported rows:")
    if summary.imported_rows:
        lines.extend(f"  {table_name}: {count}" for table_name, count in summary.imported_rows.items())
    else:
        lines.append("  no matching sheets found")

    lines.append(f"Generated follow-ups: {summary.generated_followups}")
    lines.append("Dashboard:")
    lines.extend(f"  {label}: {count}" for label, count in summary.dashboard_counts.items())
    lines.append("Open the desktop app next:")
    lines.append(f"  python app.py --db \"{summary.db_path}\" run")
    return "\n".join(lines)
