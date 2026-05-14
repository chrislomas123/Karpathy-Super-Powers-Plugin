# Workbook Bootstrap Design

## Goal

Add one simple command that loads the real planning workbook into the app database and prints a clear summary of what happened.

## Command

```bash
python app.py --db ./construction_platform.sqlite3 bootstrap-workbook "N:\Chris M\AI\Desktop Contact Database & Operating Platform..xlsx"
```

The command works with any workbook path. If `--db` is omitted, it uses the app's normal default database path.

## Behavior

The command will:

- initialize the database schema and lookup seed data through the existing startup flow,
- create a SQLite backup before import when the database already contains user data,
- import workbook rows using the existing Excel importer,
- generate default follow-ups from bid due and proposal sent dates,
- print a plain-English summary with the database path, optional backup path, imported row counts, generated follow-up count, dashboard counts, and next command to launch the app.

Lookup-only seed data such as settings and stage definitions should not force a backup. A backup is only needed when user-facing data already exists in tables such as companies, contacts, projects, bids, emails, attachments, follow-ups, project contacts, or import batches.

## Scope

This slice does not change the desktop UI and does not connect to Outlook. It only turns the already-working workbook import path into a safer, simpler first-run command.

## Testing

Add tests for:

- bootstrapping into an empty database without creating a backup,
- bootstrapping into a database with existing user data and creating a readable backup,
- summary formatting including next-step guidance.
