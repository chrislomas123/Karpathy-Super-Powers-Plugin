"""Review queue helpers for records that need manual cleanup or assignment."""

from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from construction_db.database import row_to_dict
from construction_db.models import Attachment, Contact, EmailActivity, FollowUp, Project

REVIEW_QUEUE_LABELS = {
    "emails_missing_project": "Emails missing project assignment",
    "attachments_not_analyzed": "Attachments not analyzed",
    "projects_missing_address": "Projects missing job address",
    "contacts_missing_phone": "Contacts missing phone/cell",
    "overdue_followups": "Overdue follow-ups",
}


def review_queue_counts(session: Session) -> dict[str, int]:
    """Return high-signal cleanup counts for Phase 1 review workflows."""
    emails_missing_project = session.scalar(
        select(func.count()).select_from(EmailActivity).where(EmailActivity.project_id.is_(None))
    )
    attachments_not_analyzed = session.scalar(
        select(func.count()).select_from(Attachment).where(Attachment.analyzed.is_(False))
    )
    projects_missing_address = session.scalar(
        select(func.count()).select_from(Project).where(or_(Project.job_address.is_(None), Project.job_address == ""))
    )
    contacts_missing_phone = session.scalar(
        select(func.count()).select_from(Contact).where(
            or_(Contact.phone.is_(None), Contact.phone == ""),
            or_(Contact.cell.is_(None), Contact.cell == ""),
        )
    )
    overdue_followups = session.scalar(
        select(func.count()).select_from(FollowUp).where(
            FollowUp.status.in_(["Open", "Overdue"]),
            FollowUp.due_date < func.date("now"),
        )
    )
    return {
        "emails_missing_project": emails_missing_project or 0,
        "attachments_not_analyzed": attachments_not_analyzed or 0,
        "projects_missing_address": projects_missing_address or 0,
        "contacts_missing_phone": contacts_missing_phone or 0,
        "overdue_followups": overdue_followups or 0,
    }


def review_queue_details(session: Session, limit: int = 10) -> dict[str, list[dict[str, object]]]:
    """Return sample rows for each review queue bucket."""
    queries = {
        "emails_missing_project": select(EmailActivity).where(EmailActivity.project_id.is_(None)).limit(limit),
        "attachments_not_analyzed": select(Attachment).where(Attachment.analyzed.is_(False)).limit(limit),
        "projects_missing_address": select(Project).where(or_(Project.job_address.is_(None), Project.job_address == "")).limit(limit),
        "contacts_missing_phone": select(Contact).where(
            or_(Contact.phone.is_(None), Contact.phone == ""),
            or_(Contact.cell.is_(None), Contact.cell == ""),
        ).limit(limit),
        "overdue_followups": select(FollowUp).where(
            FollowUp.status.in_(["Open", "Overdue"]),
            FollowUp.due_date < func.date("now"),
        ).limit(limit),
    }
    return {key: [row_to_dict(record) for record in session.scalars(statement)] for key, statement in queries.items()}


def format_review_queue(session: Session, limit: int = 5) -> str:
    """Format review queue counts and sample identifiers for CLI output."""
    counts = review_queue_counts(session)
    details = review_queue_details(session, limit=limit)
    lines = ["Review Queue"]
    for key, label in REVIEW_QUEUE_LABELS.items():
        lines.append(f"{label}: {counts[key]}")
        for row in details[key][:limit]:
            identifier = _row_identifier(key, row)
            if identifier:
                lines.append(f"  - {identifier}")
    return "\n".join(lines)


def _row_identifier(queue_key: str, row: dict[str, object]) -> str:
    if queue_key == "emails_missing_project":
        return f"{row.get('email_activity_id')} | {row.get('from_email') or ''} | {row.get('subject') or ''}"
    if queue_key == "attachments_not_analyzed":
        return f"{row.get('attachment_id')} | {row.get('file_name') or ''}"
    if queue_key == "projects_missing_address":
        return f"{row.get('project_id')} | {row.get('project_name') or ''}"
    if queue_key == "contacts_missing_phone":
        return f"{row.get('contact_id')} | {row.get('full_name') or ''} | {row.get('email') or ''}"
    if queue_key == "overdue_followups":
        return f"{row.get('follow_up_id')} | due {row.get('due_date') or ''} | {row.get('follow_up_type') or ''}"
    return ""
