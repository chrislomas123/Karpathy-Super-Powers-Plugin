# Desktop Contact Database & Operating Platform — Phase 1

Phase 1 creates a local-first desktop database application for construction/demolition contacts, companies, projects, bid opportunities, email activity, attachments, and follow-ups. It uses SQLite as the source of truth, provides a PySide6 desktop UI, and keeps the existing workbook workflow through Excel import/export.

Estimating/proposal workbook integration is intentionally **not** included yet. The schema and app structure are designed so future phases can add Outlook import automation and later estimating/proposal integration without replacing the Phase 1 database.

## Features delivered

- SQLite backend with SQLAlchemy models.
- Tables for:
  - `companies`
  - `contacts`
  - `projects`
  - `bid_opportunities`
  - `project_contacts`
  - `email_activity`
  - `attachments`
  - `follow_ups`
  - `stage_definitions`
  - `import_batches`
  - `settings`
- Desktop UI sections:
  - Dashboard
  - Global Search
  - Companies
  - Contacts
  - Projects
  - Bid Opportunities
  - Email Activity
  - Attachments
  - Follow-Ups
  - Review Queue
  - Settings
- Manual record creation, editing, deletion, searching, filtering by search text, and manual linking through ID fields.
- Global Search screen and CLI workflow across core record tables.
- Review Queue screen and CLI workflow for incomplete records needing cleanup.
- Dashboard cards for:
  - Active bids
  - Bids due this week
  - Follow-ups due
  - Overdue follow-ups
  - Emails needing project assignment
  - Attachments needing analysis
- Excel import/export for all Phase 1 tables.
- One row per email in `email_activity`, with `conversation_id` preserved.
- Full original email body storage in `full_message_body`, plus optional cleaned body storage in `cleaned_message_body`.
- Seeded construction/project stage definitions.
- Seeded `settings` rows for future Outlook sender defaults, lookback months, and Excel workflow preferences.

## Requirements

- Python 3.11+
- Windows, macOS, or Linux desktop environment for the PySide6 UI
- Python packages listed in `requirements.txt`

## Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Run the app

```bash
python app.py
```

By default the app creates/uses this SQLite database:

```text
~/.construction_contact_platform/construction_platform.sqlite3
```

To use a different database file:

```bash
python app.py --db ./construction_platform.sqlite3
```


## Headless command-line workflows

The app can also manage the database without launching the PySide6 UI. This is useful for servers, automation, or environments that do not have desktop GUI libraries installed. The help screen and parser load without importing pandas, SQLAlchemy, or PySide6, so `python app.py --help` remains available before dependencies are installed.

```bash
python app.py --db ./construction_platform.sqlite3 init-db
python app.py create-template ./construction_platform_template.xlsx
python app.py --db ./construction_platform.sqlite3 import-excel ./existing_workbook.xlsx
python app.py --db ./construction_platform.sqlite3 export-excel ./construction_platform_export.xlsx
python app.py --db ./construction_platform.sqlite3 review-queue --limit 10
python app.py --db ./construction_platform.sqlite3 search "45 Main" --limit 5
python app.py --db ./construction_platform.sqlite3 generate-followups
python app.py --db ./construction_platform.sqlite3 seed-demo
python app.py --db ./construction_platform.sqlite3 backup-db ./construction_platform_backup.sqlite3
python app.py --db ./construction_platform.sqlite3 doctor
python app.py --db ./construction_platform.sqlite3 settings list
python app.py --db ./construction_platform.sqlite3 settings set outlook.default_lookback_months 12 --type integer
python app.py schema-sql ./construction_platform_schema.sql
python app.py --db ./construction_platform.sqlite3 run
```

The `review-queue` command reports records needing cleanup, including emails missing project assignment, attachments not analyzed, projects missing job address, contacts missing phone/cell, and overdue follow-ups.

The `search` command performs a global search across companies, contacts, projects, bid opportunities, email activity, attachments, and follow-ups.

The `schema-sql` command prints or writes the SQLite schema DDL for review, backup documentation, or handoff.

The `generate-followups` command creates missing default bid reminders from bid due dates and proposal sent dates.

The `seed-demo` command inserts a coherent demo company/contact/project/bid/email/attachment set for first-run exploration.

The `backup-db` command creates a consistent SQLite backup using SQLite's online backup API.

The `settings` command lists, reads, or updates app settings such as future Outlook import defaults.

The `doctor` command reports dependency, schema, seed-data, database path, and Linux GUI runtime status.

On Linux, the `run` command checks for the OpenGL runtime (`libGL`) before importing PySide6. If desktop system libraries are missing, it now falls back to a text dashboard and exits successfully instead of failing.

Workbook imports are idempotent for the core matching fields: contact `email`, email `outlook_message_id`, company `source_domain`, project `job_address`, bid `project_id + gc_company_id`, and attachment `email_activity_id + file_name`.

## Excel workflow

The dashboard includes three workbook actions:

1. **Import Excel Workbook** — reads matching sheets and upserts rows into SQLite.
2. **Export Excel Workbook** — writes every Phase 1 table to an `.xlsx` workbook.
3. **Create Blank Workbook Template** — creates an Excel template with the correct sheets and column headers.

Supported sheet names match title-cased table names, for example:

- `Companies`
- `Contacts`
- `Projects`
- `Bid Opportunities`
- `Project Contacts`
- `Email Activity`
- `Attachments`
- `Follow Ups`
- `Stage Definitions`
- `Import Batches`

## Demo data

Seed a small coherent sample pipeline with:

```bash
python app.py --db ./construction_platform.sqlite3 seed-demo
```

The demo seed is idempotent and creates one general contractor, contact, project, bid opportunity, project contact relationship, email activity record, and attachment record.

## System doctor

Check the local environment and database health with:

```bash
python app.py --db ./construction_platform.sqlite3 doctor
```

The report verifies required tables, seeded settings/stages, important Python dependencies, and Linux `libGL` GUI availability.

## Settings CLI

List and update application settings with:

```bash
python app.py --db ./construction_platform.sqlite3 settings list
python app.py --db ./construction_platform.sqlite3 settings get outlook.default_selected_senders
python app.py --db ./construction_platform.sqlite3 settings set outlook.default_lookback_months 12 --type integer
```

Settings are stored in the `settings` table and are included in Excel import/export.

## Database backups

Create a safe copy of the SQLite database with:

```bash
python app.py --db ./construction_platform.sqlite3 backup-db ./construction_platform_backup.sqlite3
```

If the output path is omitted, the app creates a timestamped backup next to the source database.

## Schema SQL export

Export the current Phase 1 SQLite schema as SQL with:

```bash
python app.py schema-sql ./construction_platform_schema.sql
```

Omit the output path to print the schema to the terminal.

## Database schema overview

The SQLAlchemy models are defined in `construction_db/models.py`. Important Phase 1 design choices:

- `companies` stores company-level information separately from people.
- `contacts` stores sender/contact information and links to `companies` through `company_id`.
- `projects` represents the physical job/lead.
- `bid_opportunities` represents a GC-specific bid for a project, allowing multiple GCs for the same project/job address.
- `project_contacts` stores project-specific contact roles and stage involvement.
- `email_activity` stores one row per email, including `outlook_message_id`, `conversation_id`, `full_message_body`, assignment fields, detected project clues, and review status.
- `attachments` stores attachment metadata and analysis-ready extraction fields.
- `follow_ups` stores due dates, statuses, and links back to projects, bids, contacts, companies, and source emails.
- `stage_definitions` centralizes project and bid stage lists.
- `import_batches` logs workbook imports now and can log Outlook imports in a future phase.
- `settings` stores editable app defaults such as the future Outlook sender list and lookback window.

## Manual linking in Phase 1

Phase 1 keeps linking simple and transparent. Use ID fields to connect records:

- Link a contact to a company with `contacts.company_id`.
- Link a bid to a project with `bid_opportunities.project_id`.
- Link a bid to a GC with `bid_opportunities.gc_company_id`.
- Link an email to a project or bid with `email_activity.project_id` and `email_activity.bid_id`.
- Link an attachment to an email with `attachments.email_activity_id`.
- Link a follow-up to the relevant records with `project_id`, `bid_id`, `contact_id`, and `company_id`.

Future phases can replace raw ID entry with lookup dialogs and Outlook-driven suggestions.

## Global search

Phase 1 includes a Global Search desktop section and CLI global search across the core record tables:

```bash
python app.py --db ./construction_platform.sqlite3 search "ABC Construction" --limit 5
```

The search scans important text fields across companies, contacts, projects, bid opportunities, email activity, attachments, and follow-ups.

## Default follow-up generation

Generate missing default follow-ups from bid dates with:

```bash
python app.py --db ./construction_platform.sqlite3 generate-followups
```

Current Phase 1 rules create:

- Bid Due Reminder: 1 business day before `bid_due_date`
- Award Status Follow-Up: 7 days after `bid_due_date`
- Proposal Follow-Up: 3 business days after `proposal_sent_date`

Existing follow-ups with the same bid, type, and due date are not duplicated.

## Review queue

Phase 1 includes a Review Queue desktop section and a CLI helper for uncertain or incomplete records. Use it from the CLI with:

```bash
python app.py --db ./construction_platform.sqlite3 review-queue --limit 10
```

The queue currently highlights:

- Emails missing project assignment
- Attachments not analyzed
- Projects missing job address
- Contacts missing phone/cell
- Overdue follow-ups

## Future-ready Outlook automation

Phase 1 does not connect to Outlook yet. The database is prepared for future automation by including:

- `outlook_message_id` for email deduplication.
- `conversation_id` for thread grouping.
- `from_name` and `from_email` for sender-only contact extraction.
- `full_message_body` and `cleaned_message_body` fields.
- attachment metadata and extraction fields.
- `import_batches` for import summaries.
- seeded settings for the default selected senders and the 12-month lookback window from the design brief.

## Tests

Run the automated checks with:

```bash
pytest
```
