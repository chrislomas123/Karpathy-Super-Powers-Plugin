# Excel Header Alias Import Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Excel import understand the human-friendly headers used by the existing planning workbook.

**Architecture:** Keep SQLAlchemy models and export format unchanged. Add a small header-normalization layer inside `construction_db/excel_io.py` before row dictionaries reach `upsert_row`.

**Tech Stack:** Python 3.12, pandas, openpyxl, SQLAlchemy, pytest.

---

### Task 1: Add Friendly Header Import Coverage

**Files:**
- Modify: `tests/test_phase1.py`
- Modify: `construction_db/excel_io.py`

- [ ] **Step 1: Write the failing test**

Add a test that writes a workbook with friendly headers like `Company ID`, `Bid Due Date`, and `Analyzed?`, imports it, and asserts mapped database fields.

- [ ] **Step 2: Run the focused test to verify it fails**

Run: `.venv\Scripts\python.exe -m pytest tests/test_phase1.py::test_import_accepts_planning_workbook_headers -v`

Expected: fail because friendly headers are ignored.

- [ ] **Step 3: Implement header normalization**

Add `_normalize_header`, `_normalize_row`, `_sheet_candidates`, and small alias dictionaries in `construction_db/excel_io.py`. Call `_normalize_row(table_name, row)` before `upsert_row`. Include the planning workbook's `Import Log` sheet and stage-definition field names.

- [ ] **Step 4: Run the focused test to verify it passes**

Run: `.venv\Scripts\python.exe -m pytest tests/test_phase1.py::test_import_accepts_planning_workbook_headers -v`

Expected: pass.

- [ ] **Step 5: Run the full suite**

Run: `.venv\Scripts\python.exe -m pytest`

Expected: all tests pass.

- [ ] **Step 6: Update docs**

Mention that Excel import accepts both database-style and planning-workbook-style headers, including `Import Log` and stage-definition aliases.
