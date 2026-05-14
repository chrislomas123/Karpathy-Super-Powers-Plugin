"""Application entry point and headless utilities for the desktop database app."""

from __future__ import annotations

import argparse
import sys
from ctypes.util import find_library
from pathlib import Path


DEFAULT_DB_PATH = Path.home() / ".construction_contact_platform" / "construction_platform.sqlite3"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run or manage the Construction Contact Database app.")
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH), help="SQLite database path")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("init-db", help="Create/upgrade the SQLite schema and seed lookup data")

    template = subparsers.add_parser("create-template", help="Create a blank Excel workbook template")
    template.add_argument("output", help="Output .xlsx path")

    import_cmd = subparsers.add_parser("import-excel", help="Import records from an Excel workbook")
    import_cmd.add_argument("workbook", help="Input .xlsx path")

    bootstrap_cmd = subparsers.add_parser(
        "bootstrap-workbook",
        help="Import a planning workbook, back up existing data if needed, and print next steps",
    )
    bootstrap_cmd.add_argument("workbook", help="Input .xlsx planning workbook path")

    export_cmd = subparsers.add_parser("export-excel", help="Export all tables to an Excel workbook")
    export_cmd.add_argument("output", help="Output .xlsx path")

    review_cmd = subparsers.add_parser("review-queue", help="Show records needing manual review or cleanup")
    review_cmd.add_argument("--limit", type=int, default=5, help="Maximum sample rows per review bucket")

    search_cmd = subparsers.add_parser("search", help="Search companies, contacts, projects, bids, emails, attachments, and follow-ups")
    search_cmd.add_argument("query", help="Text to search for")
    search_cmd.add_argument("--limit", type=int, default=5, help="Maximum matches to show per table")

    schema_cmd = subparsers.add_parser("schema-sql", help="Print or write the SQLite schema DDL")
    schema_cmd.add_argument("output", nargs="?", help="Optional output .sql path. Prints to stdout when omitted")

    subparsers.add_parser("generate-followups", help="Generate missing default follow-ups from bid dates")
    subparsers.add_parser("seed-demo", help="Seed a small demo company/project/bid/email dataset")
    subparsers.add_parser("doctor", help="Run environment and database health checks")

    backup_cmd = subparsers.add_parser("backup-db", help="Create a consistent SQLite database backup")
    backup_cmd.add_argument("output", nargs="?", help="Optional backup .sqlite3 path. Defaults to a timestamped file next to the database")

    settings_cmd = subparsers.add_parser("settings", help="List, get, or set application settings")
    settings_subcommands = settings_cmd.add_subparsers(dest="settings_command")
    settings_subcommands.add_parser("list", help="List all application settings")
    settings_get = settings_subcommands.add_parser("get", help="Show one application setting")
    settings_get.add_argument("key", help="Setting key")
    settings_set = settings_subcommands.add_parser("set", help="Create or update one application setting")
    settings_set.add_argument("key", help="Setting key")
    settings_set.add_argument("value", help="Setting value")
    settings_set.add_argument("--type", dest="setting_type", help="Optional setting type")
    settings_set.add_argument("--description", help="Optional setting description")

    subparsers.add_parser(
        "run",
        help="Launch the PySide6 desktop UI, or show a headless dashboard if GUI libraries are unavailable",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    command = args.command or "run"

    if command == "create-template":
        from construction_db.excel_io import create_blank_workbook

        output = create_blank_workbook(args.output)
        print(f"Created blank workbook template: {output}")
        return 0
    if command == "schema-sql":
        from construction_db.schema import schema_sql, write_schema_sql

        if args.output:
            output = write_schema_sql(args.output)
            print(f"Wrote schema SQL: {output}")
        else:
            print(schema_sql(), end="")
        return 0

    from construction_db.database import create_session_factory, database_tables, initialize_database, make_engine

    db_path = Path(args.db).expanduser()
    engine = make_engine(db_path)
    initialize_database(engine)
    session_factory = create_session_factory(engine)

    if command == "init-db":
        print(f"Initialized database: {db_path}")
        print("Tables: " + ", ".join(database_tables(engine)))
        return 0
    if command == "import-excel":
        from construction_db.excel_io import import_from_excel

        with session_factory() as session:
            summary = import_from_excel(session, args.workbook)
        print("Imported rows:")
        for table_name, count in summary.items():
            print(f"  {table_name}: {count}")
        return 0
    if command == "bootstrap-workbook":
        from construction_db.bootstrap import bootstrap_workbook, format_bootstrap_summary

        with session_factory() as session:
            summary = bootstrap_workbook(session, db_path, args.workbook)
        print(format_bootstrap_summary(summary))
        return 0
    if command == "export-excel":
        from construction_db.excel_io import export_to_excel

        with session_factory() as session:
            output = export_to_excel(session, args.output)
        print(f"Exported workbook: {output}")
        return 0
    if command == "review-queue":
        from construction_db.review import format_review_queue

        with session_factory() as session:
            print(format_review_queue(session, limit=args.limit))
        return 0
    if command == "search":
        from construction_db.search import format_global_search

        with session_factory() as session:
            print(format_global_search(session, args.query, limit_per_table=args.limit))
        return 0
    if command == "generate-followups":
        from construction_db.followups import generate_default_followups

        with session_factory() as session:
            created = generate_default_followups(session)
        print(f"Generated follow-ups: {len(created)}")
        return 0
    if command == "seed-demo":
        from construction_db.demo import format_demo_summary, seed_demo_data

        with session_factory() as session:
            summary = seed_demo_data(session)
        print(format_demo_summary(summary))
        return 0
    if command == "backup-db":
        from construction_db.backup import backup_database

        output = backup_database(db_path, args.output)
        print(f"Created database backup: {output}")
        return 0
    if command == "doctor":
        from construction_db.doctor import doctor_report

        with session_factory() as session:
            print(doctor_report(engine, session, db_path))
        return 0
    if command == "settings":
        return _handle_settings_command(args, session_factory)

    if sys.platform.startswith("linux") and find_library("GL") is None:
        return _run_headless_dashboard(
            session_factory,
            db_path,
            "PySide6 desktop UI unavailable: libGL was not found.",
        )

    from construction_db.ui import run_app

    return run_app(session_factory, db_path)


def _handle_settings_command(args, session_factory) -> int:
    from construction_db.settings import format_settings, get_setting, list_settings, set_setting

    settings_command = args.settings_command or "list"
    with session_factory() as session:
        if settings_command == "list":
            print(format_settings(list_settings(session)))
            return 0
        if settings_command == "get":
            setting = get_setting(session, args.key)
            if setting is None:
                print(f"Setting not found: {args.key}")
                return 1
            print(format_settings([setting]))
            return 0
        if settings_command == "set":
            setting = set_setting(
                session,
                args.key,
                args.value,
                setting_type=args.setting_type,
                description=args.description,
            )
            print(format_settings([setting]))
            return 0
    print(f"Unknown settings command: {settings_command}")
    return 1


def _run_headless_dashboard(session_factory, db_path: Path, reason: str) -> int:
    from construction_db.database import dashboard_counts

    print(reason)
    print("Running headless dashboard fallback instead.")
    print(f"SQLite database: {db_path}")
    with session_factory() as session:
        counts = dashboard_counts(session)
    for label, count in counts.items():
        print(f"{label}: {count}")
    print("Use init-db, import-excel, export-excel, or create-template for headless workflows.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
