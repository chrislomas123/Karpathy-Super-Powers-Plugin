from pathlib import Path

import pandas as pd
from sqlalchemy import inspect, select

from construction_db.database import create_session_factory, dashboard_counts, initialize_database, make_engine
from construction_db.excel_io import create_blank_workbook, export_to_excel, import_from_excel
from construction_db.models import AppSetting, Company, Contact, EmailActivity, MODEL_REGISTRY, StageDefinition


REQUIRED_TABLES = {
    "companies",
    "contacts",
    "projects",
    "bid_opportunities",
    "project_contacts",
    "email_activity",
    "attachments",
    "follow_ups",
    "stage_definitions",
    "import_batches",
    "settings",
}


def test_schema_and_stage_seed(tmp_path: Path) -> None:
    engine = make_engine(tmp_path / "phase1.sqlite3")
    initialize_database(engine)
    assert REQUIRED_TABLES.issubset(set(inspect(engine).get_table_names()))

    SessionLocal = create_session_factory(engine)
    with SessionLocal() as session:
        seeded = session.scalars(select(StageDefinition)).all()
        assert seeded
        assert {stage.stage_type for stage in seeded} == {"project_stage", "bid_stage"}
        default_senders = session.get(AppSetting, "outlook.default_selected_senders")
        assert default_senders is not None
        assert "kbean@keiter.com" in (default_senders.setting_value or "")


def test_excel_template_export_import_round_trip(tmp_path: Path) -> None:
    engine = make_engine(tmp_path / "phase1.sqlite3")
    initialize_database(engine)
    SessionLocal = create_session_factory(engine)

    template_path = create_blank_workbook(tmp_path / "template.xlsx")
    sheets = pd.read_excel(template_path, sheet_name=None)
    assert {name.replace(" ", "_").lower() for name in sheets}.issuperset(MODEL_REGISTRY.keys())

    with SessionLocal() as session:
        session.add(Company(company_id="CO-TEST", company_name="ABC Construction", company_type="General Contractor"))
        session.add(Contact(contact_id="CT-TEST", company_id="CO-TEST", full_name="Jane Estimator", email="jane@example.com"))
        session.add(
            EmailActivity(
                email_activity_id="EM-TEST",
                outlook_message_id="MSG-1",
                conversation_id="CONV-1",
                from_email="jane@example.com",
                subject="Invitation to bid 45 Main Street",
                full_message_body="Full original body is preserved.",
            )
        )
        session.commit()
        export_path = export_to_excel(session, tmp_path / "export.xlsx")

    second_engine = make_engine(tmp_path / "imported.sqlite3")
    initialize_database(second_engine)
    SecondSession = create_session_factory(second_engine)
    with SecondSession() as session:
        summary = import_from_excel(session, export_path)
        assert summary["companies"] >= 1
        assert session.get(Company, "CO-TEST").company_name == "ABC Construction"
        assert session.get(EmailActivity, "EM-TEST").conversation_id == "CONV-1"
        counts = dashboard_counts(session)
        assert "Emails needing project assignment" in counts


def test_natural_key_upsert_preserves_existing_email_and_contact_ids(tmp_path: Path) -> None:
    engine = make_engine(tmp_path / "dedupe.sqlite3")
    initialize_database(engine)
    SessionLocal = create_session_factory(engine)

    with SessionLocal() as session:
        session.add(Contact(contact_id="CT-ORIGINAL", full_name="Jane One", email="jane@example.com"))
        session.add(
            EmailActivity(
                email_activity_id="EM-ORIGINAL",
                outlook_message_id="MSG-DEDUP",
                conversation_id="CONV-OLD",
                from_email="jane@example.com",
                subject="Old subject",
                full_message_body="Old body",
            )
        )
        session.commit()

        from construction_db.database import upsert_row

        updated_contact = upsert_row(
            session,
            "contacts",
            {"full_name": "Jane Two", "email": "JANE@EXAMPLE.COM", "phone": "555-0100"},
        )
        updated_email = upsert_row(
            session,
            "email_activity",
            {
                "outlook_message_id": "MSG-DEDUP",
                "conversation_id": "CONV-NEW",
                "from_email": "JANE@EXAMPLE.COM",
                "subject": "Updated subject",
                "full_message_body": "Updated full body",
            },
        )
        session.commit()

        assert updated_contact.contact_id == "CT-ORIGINAL"
        assert session.get(Contact, "CT-ORIGINAL").full_name == "Jane Two"
        assert updated_email.email_activity_id == "EM-ORIGINAL"
        assert session.get(EmailActivity, "EM-ORIGINAL").conversation_id == "CONV-NEW"


def test_headless_dashboard_fallback_outputs_counts(tmp_path: Path, capsys) -> None:
    from app import _run_headless_dashboard

    engine = make_engine(tmp_path / "headless.sqlite3")
    initialize_database(engine)
    SessionLocal = create_session_factory(engine)

    exit_code = _run_headless_dashboard(SessionLocal, tmp_path / "headless.sqlite3", "GUI unavailable")

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Running headless dashboard fallback" in captured.out
    assert "Active bids:" in captured.out


def test_review_queue_counts_and_cli_format(tmp_path: Path) -> None:
    from construction_db.models import Attachment, FollowUp, Project
    from construction_db.review import format_review_queue, review_queue_counts

    engine = make_engine(tmp_path / "review.sqlite3")
    initialize_database(engine)
    SessionLocal = create_session_factory(engine)

    with SessionLocal() as session:
        session.add(EmailActivity(email_activity_id="EM-REVIEW", subject="Needs project"))
        session.add(Attachment(attachment_id="AT-REVIEW", file_name="plans.pdf", analyzed=False))
        session.add(Project(project_id="PR-REVIEW", project_name="Missing Address"))
        session.add(Contact(contact_id="CT-REVIEW", full_name="No Phone", email="nophone@example.com"))
        session.add(FollowUp(follow_up_id="FU-REVIEW", due_date="2000-01-01", status="Open"))
        session.commit()

        counts = review_queue_counts(session)
        output = format_review_queue(session, limit=2)

    assert counts["emails_missing_project"] >= 1
    assert counts["attachments_not_analyzed"] >= 1
    assert counts["projects_missing_address"] >= 1
    assert counts["contacts_missing_phone"] >= 1
    assert counts["overdue_followups"] >= 1
    assert "Review Queue" in output
    assert "EM-REVIEW" in output


def test_global_search_finds_records_across_tables(tmp_path: Path) -> None:
    from construction_db.models import Project
    from construction_db.search import format_global_search, global_search

    engine = make_engine(tmp_path / "search.sqlite3")
    initialize_database(engine)
    SessionLocal = create_session_factory(engine)

    with SessionLocal() as session:
        session.add(Company(company_id="CO-SEARCH", company_name="Searchable Construction"))
        session.add(Project(project_id="PR-SEARCH", project_name="Searchable Demo", job_address="45 Search Street"))
        session.add(EmailActivity(email_activity_id="EM-SEARCH", subject="Searchable bid invite"))
        session.commit()

        results = global_search(session, "Searchable", limit_per_table=5)
        output = format_global_search(session, "Searchable", limit_per_table=5)

    assert any(row["company_id"] == "CO-SEARCH" for row in results["companies"])
    assert any(row["project_id"] == "PR-SEARCH" for row in results["projects"])
    assert any(row["email_activity_id"] == "EM-SEARCH" for row in results["email_activity"])
    assert "Global Search: Searchable" in output
    assert "CO-SEARCH" in output


def test_schema_sql_export_contains_core_tables(tmp_path: Path) -> None:
    from construction_db.schema import schema_sql, write_schema_sql

    sql = schema_sql()
    output = write_schema_sql(tmp_path / "schema.sql")

    assert "CREATE TABLE companies" in sql
    assert "CREATE TABLE email_activity" in sql
    assert "CREATE TABLE settings" in sql
    assert output.read_text(encoding="utf-8") == sql


def test_generate_default_followups_is_idempotent(tmp_path: Path) -> None:
    from construction_db.followups import generate_default_followups
    from construction_db.models import BidOpportunity, FollowUp, Project

    engine = make_engine(tmp_path / "followups.sqlite3")
    initialize_database(engine)
    SessionLocal = create_session_factory(engine)

    with SessionLocal() as session:
        session.add(Company(company_id="CO-FOLLOW", company_name="Follow GC"))
        session.add(Contact(contact_id="CT-FOLLOW", company_id="CO-FOLLOW", full_name="Follow Contact", email="follow@example.com"))
        session.add(Project(project_id="PR-FOLLOW", project_name="Follow Project"))
        session.commit()
        session.add(
            BidOpportunity(
                bid_id="BD-FOLLOW",
                project_id="PR-FOLLOW",
                gc_company_id="CO-FOLLOW",
                primary_contact_id="CT-FOLLOW",
                bid_due_date="2026-05-18",
                proposal_sent_date="2026-05-13",
            )
        )
        session.commit()

        created_once = generate_default_followups(session)
        created_twice = generate_default_followups(session)
        followups = session.scalars(select(FollowUp).where(FollowUp.bid_id == "BD-FOLLOW")).all()

    assert len(created_once) == 3
    assert len(created_twice) == 0
    assert {followup.follow_up_type for followup in followups} == {
        "Bid Due Reminder",
        "Award Status Follow-Up",
        "Proposal Follow-Up",
    }
    assert any(followup.due_date == "2026-05-15" for followup in followups)


def test_backup_database_creates_readable_copy(tmp_path: Path) -> None:
    import sqlite3

    from construction_db.backup import backup_database

    db_path = tmp_path / "source.sqlite3"
    backup_path = tmp_path / "backup.sqlite3"
    engine = make_engine(db_path)
    initialize_database(engine)

    output = backup_database(db_path, backup_path)

    assert output == backup_path
    with sqlite3.connect(output) as connection:
        table_names = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert "companies" in table_names
    assert "email_activity" in table_names


def test_settings_helpers_create_update_and_format(tmp_path: Path) -> None:
    from construction_db.settings import format_settings, get_setting, list_settings, set_setting

    engine = make_engine(tmp_path / "settings.sqlite3")
    initialize_database(engine)
    SessionLocal = create_session_factory(engine)

    with SessionLocal() as session:
        setting = set_setting(
            session,
            "outlook.default_lookback_months",
            "18",
            setting_type="integer",
            description="Updated lookback.",
        )
        fetched = get_setting(session, "outlook.default_lookback_months")
        output = format_settings(list_settings(session))

    assert setting.setting_value == "18"
    assert fetched is not None
    assert fetched.setting_value == "18"
    assert "outlook.default_lookback_months [integer] = 18" in output


def test_doctor_report_includes_database_health(tmp_path: Path) -> None:
    from construction_db.doctor import doctor_report

    db_path = tmp_path / "doctor.sqlite3"
    engine = make_engine(db_path)
    initialize_database(engine)
    SessionLocal = create_session_factory(engine)

    with SessionLocal() as session:
        report = doctor_report(engine, session, db_path)

    assert "System Check" in report
    assert "Missing required tables: none" in report
    assert "Seeded settings:" in report
    assert "sqlalchemy: ok" in report


def test_seed_demo_data_is_idempotent_and_searchable(tmp_path: Path) -> None:
    from sqlalchemy import func

    from construction_db.demo import format_demo_summary, seed_demo_data
    from construction_db.models import BidOpportunity, Project
    from construction_db.search import global_search

    engine = make_engine(tmp_path / "demo.sqlite3")
    initialize_database(engine)
    SessionLocal = create_session_factory(engine)

    with SessionLocal() as session:
        summary_once = seed_demo_data(session)
        summary_twice = seed_demo_data(session)
        project_count = session.scalar(select(func.count()).select_from(Project))
        bid_count = session.scalar(select(func.count()).select_from(BidOpportunity))
        search_results = global_search(session, "45 Main", limit_per_table=5)

    assert summary_once["projects"] == 1
    assert summary_twice["projects"] == 1
    assert project_count == 1
    assert bid_count == 1
    assert search_results["projects"]
    assert "Demo data seeded" in format_demo_summary(summary_once)
