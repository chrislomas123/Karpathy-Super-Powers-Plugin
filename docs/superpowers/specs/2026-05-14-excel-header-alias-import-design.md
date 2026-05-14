# Excel Header Alias Import Design

## Goal

Allow the Phase 1 app to import the existing planning workbook at `N:\Chris M\AI\Desktop Contact Database & Operating Platform..xlsx` without changing the internal database schema or the current exported workbook format.

## Current Problem

The app importer currently passes workbook row dictionaries directly to `upsert_row`. That works when columns are named like database fields, for example `company_id` and `bid_due_date`. The planning workbook uses user-facing headers such as `Company ID`, `Bid Due Date`, `Estimating Department Email`, and `Analyzed?`. Those names are currently ignored because they do not match model column names.

## Design

Import will normalize every incoming worksheet header before rows are upserted. The normalizer will:

- strip whitespace,
- lowercase text,
- remove punctuation such as `?`,
- replace spaces, slashes, and hyphens with underscores,
- map known workbook aliases to model columns where generic normalization is not enough.

The app will keep exporting database-style headers for now, preserving existing round-trip behavior and avoiding a broader workbook-format change.

## Alias Scope

The alias layer must support headers already present in the planning workbook, including:

- `Company ID` to `company_id`
- `Estimating Department Email` to `estimating_email`
- `Bid ID` to `bid_id`
- `Follow-Up Date` to `follow_up_date`
- `Follow Up ID` to `follow_up_id`
- `Analyzed?` to `analyzed`
- `ZIP` to `zip`
- `Import Log` sheet to `import_batches`
- `Warnings / Notes` to `errors_warnings`
- stage-definition fields such as `Applies To`, `Stage Order`, and `Is Closed Stage`

Unknown columns should still be ignored by the existing database cleanup path.

The stage-definition compatibility layer converts `Applies To` values into app stage types and converts `Is Closed Stage` values into `active` or `closed` status values.

## Testing

Add a focused test that creates a workbook with friendly headers, imports it, and verifies that company, contact, project, bid, email, attachment, and follow-up values land in the correct database columns.

Then run the full existing test suite.
