"""Global search helpers across Phase 1 database tables."""

from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from construction_db.database import primary_key_name, row_to_dict
from construction_db.models import MODEL_REGISTRY

DEFAULT_SEARCH_TABLES = [
    "companies",
    "contacts",
    "projects",
    "bid_opportunities",
    "email_activity",
    "attachments",
    "follow_ups",
]

DISPLAY_FIELDS = {
    "companies": ["company_name", "company_type", "source_domain", "status"],
    "contacts": ["full_name", "email", "company_name", "title"],
    "projects": ["project_name", "job_address", "municipality", "project_stage"],
    "bid_opportunities": ["project_name", "gc_company_name", "bid_stage", "result"],
    "email_activity": ["subject", "from_email", "received_date", "conversation_id"],
    "attachments": ["file_name", "file_type", "saved_location"],
    "follow_ups": ["follow_up_type", "due_date", "status", "notes"],
}


def global_search(session: Session, query_text: str, limit_per_table: int = 10) -> dict[str, list[dict[str, object]]]:
    """Search important text columns across all primary Phase 1 record tables."""
    query_text = query_text.strip()
    if not query_text:
        return {table_name: [] for table_name in DEFAULT_SEARCH_TABLES}

    results: dict[str, list[dict[str, object]]] = {}
    pattern = f"%{query_text}%"
    for table_name in DEFAULT_SEARCH_TABLES:
        model = MODEL_REGISTRY[table_name]
        text_columns = [
            column for column in model.__table__.columns if str(column.type).upper().startswith(("VARCHAR", "TEXT"))
        ]
        if not text_columns:
            results[table_name] = []
            continue
        statement = select(model).where(or_(*[column.ilike(pattern) for column in text_columns])).limit(limit_per_table)
        results[table_name] = [row_to_dict(record) for record in session.scalars(statement)]
    return results


def format_global_search(session: Session, query_text: str, limit_per_table: int = 5) -> str:
    """Format global search results for CLI/headless output."""
    results = global_search(session, query_text=query_text, limit_per_table=limit_per_table)
    lines = [f"Global Search: {query_text}"]
    total = 0
    for table_name, rows in results.items():
        total += len(rows)
        lines.append(f"{table_name}: {len(rows)}")
        pk = primary_key_name(table_name)
        for row in rows:
            summary = _display_summary(table_name, row)
            lines.append(f"  - {row.get(pk)} | {summary}")
    lines.append(f"Total matches shown: {total}")
    return "\n".join(lines)


def _display_summary(table_name: str, row: dict[str, object]) -> str:
    values = [str(row.get(field) or "") for field in DISPLAY_FIELDS.get(table_name, [])]
    return " | ".join(value for value in values if value)
