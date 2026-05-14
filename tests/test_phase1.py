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
        lost_stage = session.scalars(select(StageDefinition).where(StageDefinition.stage_name == "Lost")).first()
        assert lost_stage is not None
        assert lost_stage.stage_status == "closed"
        counts = dashboard_counts(session)
        assert "Emails needing project assignment" in counts


def test_import_accepts_planning_workbook_headers(tmp_path: Path) -> None:
    from construction_db.models import Attachment, BidOpportunity, FollowUp, ImportBatch, Project

    workbook_path = tmp_path / "planning_headers.xlsx"
    with pd.ExcelWriter(workbook_path, engine="openpyxl") as writer:
        pd.DataFrame(
            [
                {
                    "Import Batch ID": "IMPORT-PLAN",
                    "Import Date": "2026-05-13",
                    "Selected Senders": "pat@planning.example",
                    "Emails Found": 1,
                    "Emails Imported": 1,
                    "Warnings / Notes": "Planning workbook import",
                }
            ]
        ).to_excel(writer, sheet_name="Import Log", index=False)
        pd.DataFrame(
            [
                {
                    "Company ID": "CO-PLAN",
                    "Company Name": "Planning GC",
                    "Company Type": "General Contractor",
                    "Estimating Department Email": "estimating@planning.example",
                    "Source Domain": "planning.example",
                }
            ]
        ).to_excel(writer, sheet_name="Companies", index=False)
        pd.DataFrame(
            [
                {
                    "Contact ID": "CT-PLAN",
                    "Company ID": "CO-PLAN",
                    "Company Name": "Planning GC",
                    "Full Name": "Pat Planner",
                    "Email": "pat@planning.example",
                    "Phone": "555-0200",
                }
            ]
        ).to_excel(writer, sheet_name="Contacts", index=False)
        pd.DataFrame(
            [
                {
                    "Project ID": "PR-PLAN",
                    "Project Name": "Planning Project",
                    "Job Address": "100 Planning Way",
                    "ZIP": "06118",
                    "Project Stage": "Estimating",
                }
            ]
        ).to_excel(writer, sheet_name="Projects", index=False)
        pd.DataFrame(
            [
                {
                    "Bid ID": "BD-PLAN",
                    "Project ID": "PR-PLAN",
                    "GC Company ID": "CO-PLAN",
                    "Primary Contact ID": "CT-PLAN",
                    "Bid Due Date": "2026-05-20",
                    "Follow-Up Date": "2026-05-19",
                }
            ]
        ).to_excel(writer, sheet_name="Bid Opportunities", index=False)
        pd.DataFrame(
            [
                {
                    "Email Activity ID": "EM-PLAN",
                    "Outlook Message ID": "MSG-PLAN",
                    "Conversation ID": "CONV-PLAN",
                    "From Email": "pat@planning.example",
                    "Subject": "Planning bid invite",
                    "Full Message Body": "Full planning body",
                    "Project ID": "PR-PLAN",
                    "Bid ID": "BD-PLAN",
                    "Import Batch ID": "IMPORT-PLAN",
                    "Has Attachments": "True",
                    "Attachment Count": 1,
                }
            ]
        ).to_excel(writer, sheet_name="Email Activity", index=False)
        pd.DataFrame(
            [
                {
                    "Attachment ID": "AT-PLAN",
                    "Email Activity ID": "EM-PLAN",
                    "File Name": "planning.pdf",
                    "File Type": "pdf",
                    "Analyzed?": "True",
                    "Extracted Job Address": "100 Planning Way",
                }
            ]
        ).to_excel(writer, sheet_name="Attachments", index=False)
        pd.DataFrame(
            [
                {
                    "Follow Up ID": "FU-PLAN",
                    "Project ID": "PR-PLAN",
                    "Bid ID": "BD-PLAN",
                    "Contact ID": "CT-PLAN",
                    "Company ID": "CO-PLAN",
                    "Follow Up Type": "Bid due reminder",
                    "Due Date": "2026-05-19",
                    "Status": "Open",
                    "Created From Email ID": "EM-PLAN",
                }
            ]
        ).to_excel(writer, sheet_name="Follow Ups", index=False)
        pd.DataFrame(
            [
                {
                    "Stage Name": "Planning Closed",
                    "Applies To": "Bid",
                    "Stage Order": 99,
                    "Is Closed Stage": "True",
                }
            ]
        ).to_excel(writer, sheet_name="Stage Definitions", index=False)

    engine = make_engine(tmp_path / "planning_headers.sqlite3")
    initialize_database(engine)
    SessionLocal = create_session_factory(engine)

    with SessionLocal() as session:
        summary = import_from_excel(session, workbook_path)

        assert summary["companies"] == 1
        assert summary["import_batches"] == 1
        assert summary["stage_definitions"] == 1
        assert session.get(ImportBatch, "IMPORT-PLAN").errors_warnings == "Planning workbook import"
        assert session.get(Company, "CO-PLAN").estimating_email == "estimating@planning.example"
        assert session.get(Contact, "CT-PLAN").company_id == "CO-PLAN"
        assert session.get(Project, "PR-PLAN").zip == "06118"
        assert session.get(BidOpportunity, "BD-PLAN").follow_up_date == "2026-05-19"
        assert session.get(EmailActivity, "EM-PLAN").has_attachments is True
        assert session.get(Attachment, "AT-PLAN").analyzed is True
        assert session.get(FollowUp, "FU-PLAN").created_from_email_id == "EM-PLAN"
        imported_stage = session.scalars(select(StageDefinition).where(StageDefinition.stage_name == "Planning Closed")).one()
        assert imported_stage.stage_type == "bid_stage"
        assert imported_stage.stage_status == "closed"
        assert imported_stage.sort_order == 99


def test_bootstrap_workbook_imports_and_reports_next_steps(tmp_path: Path) -> None:
    from construction_db.bootstrap import bootstrap_workbook, format_bootstrap_summary
    from construction_db.models import BidOpportunity, FollowUp, Project

    workbook_path = _write_bootstrap_workbook(tmp_path / "bootstrap.xlsx")
    db_path = tmp_path / "bootstrap.sqlite3"
    engine = make_engine(db_path)
    initialize_database(engine)
    SessionLocal = create_session_factory(engine)

    with SessionLocal() as session:
        summary = bootstrap_workbook(session, db_path, workbook_path)
        output = format_bootstrap_summary(summary)

        assert summary.backup_path is None
        assert summary.imported_rows["companies"] == 1
        assert summary.imported_rows["bid_opportunities"] == 1
        assert summary.generated_followups == 2
        assert session.get(Project, "PR-BOOT").project_name == "Bootstrap Project"
        assert session.get(BidOpportunity, "BD-BOOT").bid_due_date == "2026-05-20"
        assert len(session.scalars(select(FollowUp).where(FollowUp.bid_id == "BD-BOOT")).all()) == 2
        assert "Workbook bootstrap complete" in output
        assert "Open the desktop app next:" in output


def test_bootstrap_workbook_backs_up_existing_user_data(tmp_path: Path) -> None:
    from construction_db.bootstrap import bootstrap_workbook

    workbook_path = _write_bootstrap_workbook(tmp_path / "bootstrap.xlsx")
    db_path = tmp_path / "existing.sqlite3"
    engine = make_engine(db_path)
    initialize_database(engine)
    SessionLocal = create_session_factory(engine)

    with SessionLocal() as session:
        session.add(Company(company_id="CO-EXISTING", company_name="Existing GC"))
        session.commit()

        summary = bootstrap_workbook(session, db_path, workbook_path)

    assert summary.backup_path is not None
    assert summary.backup_path.exists()
    backup_engine = make_engine(summary.backup_path)
    BackupSession = create_session_factory(backup_engine)
    with BackupSession() as session:
        assert session.get(Company, "CO-EXISTING").company_name == "Existing GC"
        assert session.get(Company, "CO-BOOT") is None


def test_windows_launcher_files_are_present_and_point_to_app_workflows() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    launchers = {
        "Setup Environment.bat": [
            "python -m venv .venv",
            "py -3 -m venv .venv",
            "pip install -r requirements.txt",
        ],
        "Load Planning Workbook.bat": [
            ".venv\\Scripts\\python.exe",
            "bootstrap-workbook",
            "Desktop Contact Database & Operating Platform..xlsx",
            "construction_platform.sqlite3",
            "echo \"%APP_DB%\"",
            "echo \"%WORKBOOK%\"",
        ],
        "Start App.bat": [
            ".venv\\Scripts\\python.exe",
            "app.py",
            "construction_platform.sqlite3",
            " run",
            "echo \"%APP_DB%\"",
        ],
    }

    for launcher_name, expected_snippets in launchers.items():
        text = (repo_root / launcher_name).read_text(encoding="utf-8")
        assert "cd /d \"%~dp0\"" in text
        assert "Setup Environment.bat" in text or launcher_name == "Setup Environment.bat"
        for snippet in expected_snippets:
            assert snippet in text


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


def _write_bootstrap_workbook(workbook_path: Path) -> Path:
    with pd.ExcelWriter(workbook_path, engine="openpyxl") as writer:
        pd.DataFrame(
            [
                {
                    "Company ID": "CO-BOOT",
                    "Company Name": "Bootstrap GC",
                    "Company Type": "General Contractor",
                    "Source Domain": "bootstrap.example",
                }
            ]
        ).to_excel(writer, sheet_name="Companies", index=False)
        pd.DataFrame(
            [
                {
                    "Project ID": "PR-BOOT",
                    "Project Name": "Bootstrap Project",
                    "Job Address": "200 Bootstrap Lane",
                    "Project Stage": "Estimating",
                }
            ]
        ).to_excel(writer, sheet_name="Projects", index=False)
        pd.DataFrame(
            [
                {
                    "Bid ID": "BD-BOOT",
                    "Project ID": "PR-BOOT",
                    "Project Name": "Bootstrap Project",
                    "GC Company ID": "CO-BOOT",
                    "GC Company Name": "Bootstrap GC",
                    "Bid Due Date": "2026-05-20",
                    "Bid Stage": "Estimating",
                    "Result": "Pending",
                }
            ]
        ).to_excel(writer, sheet_name="Bid Opportunities", index=False)
    return workbook_path
