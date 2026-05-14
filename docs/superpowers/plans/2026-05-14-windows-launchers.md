# Windows Launchers Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Windows double-click launchers for setup, workbook loading, and app startup.

**Architecture:** Keep launchers as thin `.bat` wrappers in the repo root. They call the existing `app.py` CLI through `.venv\Scripts\python.exe` and share a repo-local SQLite database path.

**Tech Stack:** Windows batch files, Python 3.12, pytest.

---

### Task 1: Launcher Files

**Files:**
- Create: `Setup Environment.bat`
- Create: `Load Planning Workbook.bat`
- Create: `Start App.bat`
- Modify: `README.md`
- Modify: `tests/test_phase1.py`

- [ ] **Step 1: Write failing launcher tests**

Add a test that checks each root-level `.bat` file exists and includes expected command snippets.

- [ ] **Step 2: Verify focused test fails**

Run: `.venv\Scripts\python.exe -m pytest tests/test_phase1.py::test_windows_launcher_files_are_present_and_point_to_app_workflows -v`

Expected: fail because the batch files do not exist.

- [ ] **Step 3: Create launchers**

Create the three batch files with repo-relative paths and friendly error messages.

- [ ] **Step 4: Update README**

Add a Windows double-click launchers section with the intended order: setup once, load workbook, start app.

- [ ] **Step 5: Verify focused test and full suite**

Run focused test, then `.venv\Scripts\python.exe -m pytest`.
