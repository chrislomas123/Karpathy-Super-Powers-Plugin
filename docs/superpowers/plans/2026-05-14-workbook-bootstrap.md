# Workbook Bootstrap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `bootstrap-workbook` CLI command that safely imports a planning workbook into the app database and prints next steps.

**Architecture:** Create a focused `construction_db/bootstrap.py` module that orchestrates backup detection, workbook import, follow-up generation, dashboard counts, and summary formatting. Keep `app.py` responsible only for parsing and command dispatch.

**Tech Stack:** Python 3.12, SQLAlchemy, pandas/openpyxl, pytest.

---

### Task 1: Bootstrap Workflow

**Files:**
- Create: `construction_db/bootstrap.py`
- Modify: `app.py`
- Modify: `README.md`
- Modify: `tests/test_phase1.py`

- [ ] **Step 1: Write failing tests**

Add tests that call `bootstrap_workbook` against empty and non-empty temp databases.

- [ ] **Step 2: Verify focused tests fail**

Run: `.venv\Scripts\python.exe -m pytest tests/test_phase1.py::test_bootstrap_workbook_imports_and_reports_next_steps tests/test_phase1.py::test_bootstrap_workbook_backs_up_existing_user_data -v`

Expected: fail because `construction_db.bootstrap` does not exist yet.

- [ ] **Step 3: Implement bootstrap module**

Create `bootstrap_workbook`, `format_bootstrap_summary`, and user-data detection helpers.

- [ ] **Step 4: Add CLI command**

Add `bootstrap-workbook` to `app.py`, with one required `workbook` path argument.

- [ ] **Step 5: Verify focused tests pass**

Run the focused pytest command from Step 2.

- [ ] **Step 6: Verify real workbook command**

Run the command against `N:\Chris M\AI\Desktop Contact Database & Operating Platform..xlsx` with a temporary database.

- [ ] **Step 7: Run full tests**

Run: `.venv\Scripts\python.exe -m pytest`

Expected: all tests pass.
