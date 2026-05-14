"""Demo data seeding for first-run exploration and screenshots."""

from __future__ import annotations

from sqlalchemy.orm import Session

from construction_db.database import upsert_row

DEMO_RECORDS: dict[str, list[dict[str, object]]] = {
    "companies": [
        {
            "company_id": "CO-DEMO-GC",
            "company_name": "Demo GC Construction",
            "company_type": "General Contractor",
            "main_office_phone": "555-0100",
            "estimating_email": "estimating@demogc.example",
            "source_domain": "demogc.example",
            "status": "Active",
        }
    ],
    "contacts": [
        {
            "contact_id": "CT-DEMO-EST",
            "company_id": "CO-DEMO-GC",
            "company_name": "Demo GC Construction",
            "first_name": "Dana",
            "last_name": "Estimator",
            "full_name": "Dana Estimator",
            "email": "dana.estimator@demogc.example",
            "phone": "555-0101",
            "title": "Estimator",
            "default_role": "Estimator",
            "contact_status": "Active",
        }
    ],
    "projects": [
        {
            "project_id": "PR-DEMO-45MAIN",
            "project_name": "45 Main Street Demolition",
            "job_address": "45 Main Street",
            "city": "Hartford",
            "state": "CT",
            "municipality": "Hartford",
            "scope_summary": "Selective demolition and debris removal demo record.",
            "project_stage": "Estimating",
            "lead_source": "Demo Seed",
        }
    ],
    "bid_opportunities": [
        {
            "bid_id": "BD-DEMO-GC-45MAIN",
            "project_id": "PR-DEMO-45MAIN",
            "project_name": "45 Main Street Demolition",
            "job_address": "45 Main Street",
            "gc_company_id": "CO-DEMO-GC",
            "gc_company_name": "Demo GC Construction",
            "primary_contact_id": "CT-DEMO-EST",
            "bid_due_date": "2026-05-20",
            "bid_stage": "Estimating",
            "result": "Pending",
            "scope_summary": "Bid opportunity for Demo GC on 45 Main Street.",
        }
    ],
    "project_contacts": [
        {
            "project_contact_id": "PC-DEMO-EST",
            "project_id": "PR-DEMO-45MAIN",
            "bid_id": "BD-DEMO-GC-45MAIN",
            "contact_id": "CT-DEMO-EST",
            "company_id": "CO-DEMO-GC",
            "role_on_project": "Estimator",
            "stage_involved": "Estimating",
            "communication_role": "Bid Invite Sender",
        }
    ],
    "email_activity": [
        {
            "email_activity_id": "EM-DEMO-INVITE",
            "outlook_message_id": "DEMO-MSG-001",
            "conversation_id": "DEMO-CONV-45MAIN",
            "received_date": "2026-05-13",
            "from_name": "Dana Estimator",
            "from_email": "dana.estimator@demogc.example",
            "contact_id": "CT-DEMO-EST",
            "company_id": "CO-DEMO-GC",
            "subject": "Invitation to bid - 45 Main Street Demolition",
            "full_message_body": "Demo full message body for the 45 Main Street demolition invitation to bid.",
            "cleaned_message_body": "Demo cleaned message body for the 45 Main Street demolition invitation to bid.",
            "project_id": "PR-DEMO-45MAIN",
            "bid_id": "BD-DEMO-GC-45MAIN",
            "detected_project_name": "45 Main Street Demolition",
            "detected_job_address": "45 Main Street",
            "detected_bid_due_date": "2026-05-20",
            "detected_stage": "Estimating",
            "has_attachments": True,
            "attachment_count": 1,
            "reviewed": True,
        }
    ],
    "attachments": [
        {
            "attachment_id": "AT-DEMO-PLANS",
            "outlook_message_id": "DEMO-MSG-001",
            "email_activity_id": "EM-DEMO-INVITE",
            "file_name": "45-main-demo-plans.pdf",
            "file_type": "pdf",
            "file_size": 123456,
            "analyzed": False,
            "extracted_project_name": "45 Main Street Demolition",
            "extracted_job_address": "45 Main Street",
            "extracted_bid_due_date": "2026-05-20",
        }
    ],
}


def seed_demo_data(session: Session) -> dict[str, int]:
    """Insert or update a small coherent demo pipeline and return row counts by table."""
    summary: dict[str, int] = {}
    for table_name, rows in DEMO_RECORDS.items():
        for row in rows:
            upsert_row(session, table_name, row)
        summary[table_name] = len(rows)
    session.commit()
    return summary


def format_demo_summary(summary: dict[str, int]) -> str:
    """Format demo seed results for CLI output."""
    lines = ["Demo data seeded"]
    lines.extend(f"{table_name}: {count}" for table_name, count in summary.items())
    return "\n".join(lines)
