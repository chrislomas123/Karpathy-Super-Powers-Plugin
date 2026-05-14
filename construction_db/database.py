"""Database setup, seeding, and lightweight repository helpers."""

from __future__ import annotations

import math
from pathlib import Path
from uuid import uuid4

from sqlalchemy import create_engine, event, func, inspect, or_, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from construction_db.lookups import DEFAULT_SELECTED_SENDERS, STAGE_SEEDS
from construction_db.models import AppSetting, Base, MODEL_REGISTRY, StageDefinition

APP_DIR = Path.home() / ".construction_contact_platform"
DEFAULT_DB_PATH = APP_DIR / "construction_platform.sqlite3"

# Natural keys keep workbook imports idempotent when a user does not provide the
# internal Phase 1 primary key columns. These mirror the matching rules from the
# product brief without attempting automatic fuzzy merges in Phase 1.
NATURAL_KEY_FIELDS: dict[str, tuple[str, ...]] = {
    "companies": ("source_domain",),
    "contacts": ("email",),
    "projects": ("job_address",),
    "bid_opportunities": ("project_id", "gc_company_id"),
    "email_activity": ("outlook_message_id",),
    "attachments": ("email_activity_id", "file_name"),
    "settings": ("setting_key",),
}

SECONDARY_NATURAL_KEY_FIELDS: dict[str, tuple[str, ...]] = {
    "companies": ("company_name",),
    "contacts": ("full_name", "company_id"),
    "projects": ("project_name", "municipality"),
    "email_activity": ("conversation_id", "from_email", "subject", "received_date"),
}

BOOLEAN_FIELDS: dict[str, set[str]] = {
    "projects": {"needs_review"},
    "email_activity": {"has_attachments", "reviewed"},
    "attachments": {"analyzed"},
}


def make_engine(db_path: str | Path = DEFAULT_DB_PATH) -> Engine:
    path = Path(db_path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{path}", future=True)

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragmas(dbapi_connection, _connection_record):  # type: ignore[no-untyped-def]
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()

    return engine


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, future=True, expire_on_commit=False)


def initialize_database(engine: Engine) -> None:
    Base.metadata.create_all(engine)
    SessionLocal = create_session_factory(engine)
    with SessionLocal() as session:
        seed_stage_definitions(session)
        seed_app_settings(session)
        session.commit()


def seed_stage_definitions(session: Session) -> None:
    existing = session.scalar(select(func.count()).select_from(StageDefinition))
    if existing:
        return
    for index, (stage_type, stage_name, stage_status) in enumerate(STAGE_SEEDS, start=1):
        session.add(
            StageDefinition(
                stage_type=stage_type,
                stage_name=stage_name,
                stage_status=stage_status,
                sort_order=index,
            )
        )


def seed_app_settings(session: Session) -> None:
    """Seed editable local settings used by Phase 1 and future Outlook import phases."""
    defaults = {
        "outlook.default_selected_senders": (
            "\n".join(DEFAULT_SELECTED_SENDERS),
            "text_list",
            "Default sender email list for future Outlook automation.",
        ),
        "outlook.default_lookback_months": (
            "12",
            "integer",
            "Default date range lookback for future Outlook imports.",
        ),
        "excel.last_export_path": (
            "",
            "path",
            "Optional reminder of the last Excel export location.",
        ),
    }
    for key, (value, value_type, description) in defaults.items():
        if session.get(AppSetting, key):
            continue
        session.add(
            AppSetting(
                setting_key=key,
                setting_value=value,
                setting_type=value_type,
                description=description,
            )
        )


def table_columns(table_name: str) -> list[str]:
    model = MODEL_REGISTRY[table_name]
    return [column.name for column in model.__table__.columns]


def primary_key_name(table_name: str) -> str:
    model = MODEL_REGISTRY[table_name]
    return next(column.name for column in model.__table__.primary_key.columns)


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:10].upper()}"


def default_prefix(table_name: str) -> str:
    return {
        "companies": "CO",
        "contacts": "CT",
        "projects": "PR",
        "bid_opportunities": "BD",
        "project_contacts": "PC",
        "email_activity": "EM",
        "attachments": "AT",
        "follow_ups": "FU",
        "import_batches": "IB",
        "stage_definitions": "SD",
        "settings": "SET",
    }.get(table_name, "ID")


def ensure_primary_key(table_name: str, values: dict[str, object]) -> dict[str, object]:
    pk = primary_key_name(table_name)
    if values.get(pk) in (None, "") and pk != "stage_definition_id":
        values[pk] = new_id(default_prefix(table_name))
    return values


def row_to_dict(row: object) -> dict[str, object]:
    return {column.name: getattr(row, column.name) for column in row.__table__.columns}


def upsert_row(session: Session, table_name: str, values: dict[str, object]) -> object:
    model = MODEL_REGISTRY[table_name]
    clean_values = _clean_values(table_name, values)
    pk = primary_key_name(table_name)
    existing = _find_existing_row(session, table_name, clean_values)

    if existing:
        # Preserve the established primary key when a workbook row matched by a
        # stable natural key such as email address or Outlook message ID.
        clean_values[pk] = getattr(existing, pk)
        for key, value in clean_values.items():
            setattr(existing, key, value)
        return existing

    clean_values = ensure_primary_key(table_name, clean_values)
    record = model(**clean_values)
    session.add(record)
    return record


def _clean_values(table_name: str, values: dict[str, object]) -> dict[str, object]:
    cleaned: dict[str, object] = {}
    for key, value in values.items():
        if key not in table_columns(table_name):
            continue
        if _is_blank_value(value):
            value = None
        if isinstance(value, str):
            value = value.strip() or None
        if key in {"email", "from_email", "estimating_email", "ap_billing_email", "bid_submission_email"} and isinstance(value, str):
            value = value.lower()
        if key in BOOLEAN_FIELDS.get(table_name, set()):
            value = _coerce_bool(value)
        cleaned[key] = value
    return cleaned


def _is_blank_value(value: object) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    if isinstance(value, float):
        return math.isnan(value)
    try:
        return bool(value != value)
    except (TypeError, ValueError):
        return False


def _coerce_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "checked"}
    return bool(value)


def _find_existing_row(session: Session, table_name: str, values: dict[str, object]) -> object | None:
    model = MODEL_REGISTRY[table_name]
    pk = primary_key_name(table_name)
    if values.get(pk) is not None:
        existing = session.get(model, values[pk])
        if existing:
            return existing
    for fields in (NATURAL_KEY_FIELDS.get(table_name), SECONDARY_NATURAL_KEY_FIELDS.get(table_name)):
        if not fields or not all(values.get(field) not in (None, "") for field in fields):
            continue
        statement = select(model).where(*[getattr(model, field) == values[field] for field in fields])
        existing = session.scalars(statement).first()
        if existing:
            return existing
    return None


def search_rows(session: Session, table_name: str, query_text: str = "", limit: int = 500) -> list[object]:
    model = MODEL_REGISTRY[table_name]
    statement = select(model).limit(limit)
    text_columns = [column for column in model.__table__.columns if str(column.type).upper().startswith(("VARCHAR", "TEXT"))]
    if query_text and text_columns:
        pattern = f"%{query_text}%"
        statement = select(model).where(or_(*[column.ilike(pattern) for column in text_columns])).limit(limit)
    return list(session.scalars(statement))


def dashboard_counts(session: Session) -> dict[str, int]:
    from construction_db.lookups import ACTIVE_STAGES
    from construction_db.models import Attachment, BidOpportunity, EmailActivity, FollowUp

    active_bids = session.scalar(
        select(func.count()).select_from(BidOpportunity).where(BidOpportunity.bid_stage.in_(ACTIVE_STAGES))
    )
    bids_due_this_week = session.scalar(
        select(func.count()).select_from(BidOpportunity).where(
            BidOpportunity.bid_due_date >= func.date("now"),
            BidOpportunity.bid_due_date <= func.date("now", "+7 days"),
        )
    )
    followups_due = session.scalar(
        select(func.count()).select_from(FollowUp).where(
            FollowUp.status.in_(["Open", "Overdue", "Deferred"]),
            FollowUp.due_date <= func.date("now", "+7 days"),
        )
    )
    overdue_followups = session.scalar(
        select(func.count()).select_from(FollowUp).where(
            FollowUp.status.in_(["Open", "Overdue"]),
            FollowUp.due_date < func.date("now"),
        )
    )
    emails_needing_assignment = session.scalar(
        select(func.count()).select_from(EmailActivity).where(EmailActivity.project_id.is_(None))
    )
    attachments_needing_analysis = session.scalar(
        select(func.count()).select_from(Attachment).where(Attachment.analyzed.is_(False))
    )
    return {
        "Active bids": active_bids or 0,
        "Bids due this week": bids_due_this_week or 0,
        "Follow-ups due": followups_due or 0,
        "Overdue follow-ups": overdue_followups or 0,
        "Emails needing project assignment": emails_needing_assignment or 0,
        "Attachments needing analysis": attachments_needing_analysis or 0,
    }


def database_tables(engine: Engine) -> list[str]:
    return inspect(engine).get_table_names()
