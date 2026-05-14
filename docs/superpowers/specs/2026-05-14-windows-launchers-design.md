# Windows Launchers Design

## Goal

Make the app usable from Windows Explorer without remembering Python commands.

## Launchers

Add three root-level batch files:

- `Setup Environment.bat` creates `.venv` with the Windows Python launcher or `python`, installs `requirements.txt`, and pauses so the user can see the result.
- `Load Planning Workbook.bat` uses `.venv\Scripts\python.exe` to run `bootstrap-workbook` against `N:\Chris M\AI\Desktop Contact Database & Operating Platform..xlsx` and stores data in `construction_platform.sqlite3` next to the repo.
- `Start App.bat` uses `.venv\Scripts\python.exe` to launch the desktop app against the same repo-local `construction_platform.sqlite3`.

## Behavior

The launchers should:

- work when double-clicked from File Explorer,
- use paths relative to the batch file so moving the repo folder does not break them,
- show a friendly message if `.venv` has not been created yet,
- avoid changing the Python app's internal behavior.

## Testing

Automated tests will assert that the batch files exist and contain the expected commands, path handling, and friendly missing-environment guidance. The full Python test suite will still verify the app behavior underneath the launchers.
