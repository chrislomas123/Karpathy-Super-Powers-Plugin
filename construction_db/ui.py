"""PySide6 desktop UI for the Phase 1 local database app."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from construction_db.database import dashboard_counts, ensure_primary_key, row_to_dict, search_rows, table_columns
from construction_db.excel_io import create_blank_workbook, export_to_excel, import_from_excel
from construction_db.models import MODEL_REGISTRY
from construction_db.review import REVIEW_QUEUE_LABELS, review_queue_counts, review_queue_details
from construction_db.search import DISPLAY_FIELDS, global_search

SECTION_TABLES = {
    "Companies": "companies",
    "Contacts": "contacts",
    "Projects": "projects",
    "Bid Opportunities": "bid_opportunities",
    "Email Activity": "email_activity",
    "Attachments": "attachments",
    "Follow-Ups": "follow_ups",
}

NAV_ITEMS = [
    "Dashboard",
    "Global Search",
    "Companies",
    "Contacts",
    "Projects",
    "Bid Opportunities",
    "Email Activity",
    "Attachments",
    "Follow-Ups",
    "Review Queue",
    "Settings",
]

MULTILINE_FIELDS = {
    "address",
    "notes",
    "scope_summary",
    "subject",
    "full_message_body",
    "cleaned_message_body",
    "detected_job_address",
    "saved_location",
    "extracted_scope",
    "extracted_contacts",
    "errors_warnings",
    "selected_senders",
    "prequalification_requirements",
    "insurance_requirements",
    "safety_requirements",
}


class MainWindow(QMainWindow):
    def __init__(self, session_factory: sessionmaker[Session], db_path: Path):
        super().__init__()
        self.session_factory = session_factory
        self.db_path = db_path
        self.pages: dict[str, QWidget] = {}
        self.setWindowTitle("Construction Contact Database & Operating Platform")
        self.resize(1320, 820)
        self._build_shell()
        self.refresh_dashboard()

    def _build_shell(self) -> None:
        splitter = QSplitter(Qt.Horizontal)
        self.nav = QListWidget()
        self.nav.setMaximumWidth(230)
        self.nav.setStyleSheet("font-size: 15px; padding: 6px;")
        for item in NAV_ITEMS:
            QListWidgetItem(item, self.nav)
        self.stack = QStackedWidget()
        splitter.addWidget(self.nav)
        splitter.addWidget(self.stack)
        splitter.setStretchFactor(1, 1)
        self.setCentralWidget(splitter)

        self.dashboard = DashboardPage(self)
        self.pages["Dashboard"] = self.dashboard
        self.stack.addWidget(self.dashboard)

        self.global_search = GlobalSearchPage(self)
        self.pages["Global Search"] = self.global_search
        self.stack.addWidget(self.global_search)

        for section, table_name in SECTION_TABLES.items():
            page = TablePage(self, table_name, section)
            self.pages[section] = page
            self.stack.addWidget(page)

        self.review_queue = ReviewQueuePage(self)
        self.pages["Review Queue"] = self.review_queue
        self.stack.addWidget(self.review_queue)

        self.settings = SettingsPage(self)
        self.pages["Settings"] = self.settings
        self.stack.addWidget(self.settings)
        self.nav.currentRowChanged.connect(self._change_page)
        self.nav.setCurrentRow(0)

    def _change_page(self, row: int) -> None:
        self.stack.setCurrentIndex(row)
        section = NAV_ITEMS[row]
        page = self.pages[section]
        if isinstance(page, TablePage):
            page.refresh()
        if section == "Dashboard":
            self.refresh_dashboard()
        if section == "Global Search":
            self.global_search.run_search()
        if section == "Review Queue":
            self.review_queue.refresh()
        if section == "Settings":
            self.settings.refresh()

    def refresh_dashboard(self) -> None:
        with self.session_factory() as session:
            self.dashboard.set_counts(dashboard_counts(session))

    def import_workbook(self, path: str) -> None:
        with self.session_factory() as session:
            summary = import_from_excel(session, path)
        self.refresh_all_tables()
        QMessageBox.information(self, "Import complete", _summary_text("Imported rows", summary))

    def export_workbook(self, path: str) -> None:
        with self.session_factory() as session:
            export_to_excel(session, path)
        QMessageBox.information(self, "Export complete", f"Exported database to:\n{path}")

    def create_template(self, path: str) -> None:
        create_blank_workbook(path)
        QMessageBox.information(self, "Template created", f"Blank workbook template created at:\n{path}")

    def refresh_all_tables(self) -> None:
        for page in self.pages.values():
            if isinstance(page, TablePage):
                page.refresh()
        self.review_queue.refresh()
        self.settings.refresh()
        self.refresh_dashboard()


class DashboardPage(QWidget):
    def __init__(self, window: MainWindow):
        super().__init__()
        self.window = window
        self.cards: dict[str, QLabel] = {}
        layout = QVBoxLayout(self)
        title = QLabel("Dashboard")
        title.setStyleSheet("font-size: 28px; font-weight: 700;")
        subtitle = QLabel("Pipeline, follow-up, email assignment, and attachment analysis overview.")
        subtitle.setStyleSheet("color: #53606f; font-size: 14px;")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        grid = QGridLayout()
        for index, label in enumerate(
            [
                "Active bids",
                "Bids due this week",
                "Follow-ups due",
                "Overdue follow-ups",
                "Emails needing project assignment",
                "Attachments needing analysis",
            ]
        ):
            card = self._card(label)
            grid.addWidget(card, index // 3, index % 3)
        layout.addLayout(grid)

        actions = QHBoxLayout()
        for text, handler in [
            ("Import Excel Workbook", self._choose_import),
            ("Export Excel Workbook", self._choose_export),
            ("Create Blank Workbook Template", self._choose_template),
        ]:
            button = QPushButton(text)
            button.clicked.connect(handler)
            actions.addWidget(button)
        actions.addStretch(1)
        layout.addLayout(actions)

        note = QLabel(
            "Phase 1 is local-first: SQLite stores the working database, Excel import/export keeps the workbook workflow, "
            "and future Outlook automation can be added without changing the main UI sections."
        )
        note.setWordWrap(True)
        note.setStyleSheet("background: #eef5ff; border: 1px solid #c8dbf8; padding: 12px; border-radius: 8px;")
        layout.addWidget(note)
        layout.addStretch(1)

    def _card(self, label: str) -> QFrame:
        frame = QFrame()
        frame.setFrameShape(QFrame.StyledPanel)
        frame.setStyleSheet("QFrame { border: 1px solid #d8dee9; border-radius: 10px; background: #ffffff; }")
        layout = QVBoxLayout(frame)
        count = QLabel("0")
        count.setStyleSheet("font-size: 34px; font-weight: 700; color: #172033;")
        caption = QLabel(label)
        caption.setWordWrap(True)
        caption.setStyleSheet("font-size: 14px; color: #53606f;")
        layout.addWidget(count)
        layout.addWidget(caption)
        self.cards[label] = count
        return frame

    def set_counts(self, counts: dict[str, int]) -> None:
        for label, count in counts.items():
            self.cards[label].setText(str(count))

    def _choose_import(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Import Excel workbook", str(Path.home()), "Excel Files (*.xlsx)")
        if path:
            self.window.import_workbook(path)

    def _choose_export(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Export Excel workbook", str(Path.home() / "construction_platform_export.xlsx"), "Excel Files (*.xlsx)")
        if path:
            self.window.export_workbook(path)

    def _choose_template(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Create blank workbook template", str(Path.home() / "construction_platform_template.xlsx"), "Excel Files (*.xlsx)")
        if path:
            self.window.create_template(path)


class TablePage(QWidget):
    def __init__(self, window: MainWindow, table_name: str, title: str):
        super().__init__()
        self.window = window
        self.table_name = table_name
        self.title = title
        self.columns = table_columns(table_name)
        self.current_pk: object | None = None
        self.editors: dict[str, QLineEdit | QTextEdit] = {}
        self.rows: list[dict[str, object]] = []
        self._build()
        self.refresh()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        header = QHBoxLayout()
        title = QLabel(self.title)
        title.setStyleSheet("font-size: 24px; font-weight: 700;")
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search all text fields...")
        self.search.textChanged.connect(self.refresh)
        add = QPushButton("New")
        add.clicked.connect(self.new_record)
        save = QPushButton("Save")
        save.clicked.connect(self.save_record)
        delete = QPushButton("Delete")
        delete.clicked.connect(self.delete_record)
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(self.search, 2)
        header.addWidget(add)
        header.addWidget(save)
        header.addWidget(delete)
        layout.addLayout(header)

        splitter = QSplitter(Qt.Vertical)
        self.table = QTableWidget()
        self.table.setColumnCount(len(self.columns))
        self.table.setHorizontalHeaderLabels(self.columns)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.itemSelectionChanged.connect(self.load_selected_row)
        splitter.addWidget(self.table)

        form_widget = QWidget()
        self.form = QFormLayout(form_widget)
        for column in self.columns:
            if column in MULTILINE_FIELDS or column.endswith("body") or column.endswith("notes"):
                editor = QTextEdit()
                editor.setMaximumHeight(90)
            else:
                editor = QLineEdit()
            self.editors[column] = editor
            self.form.addRow(column, editor)
        splitter.addWidget(form_widget)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter)

    def refresh(self) -> None:
        with self.window.session_factory() as session:
            records = search_rows(session, self.table_name, self.search.text())
            self.rows = [row_to_dict(record) for record in records]
        self.table.setRowCount(len(self.rows))
        for row_index, row in enumerate(self.rows):
            for col_index, column in enumerate(self.columns):
                value = row.get(column)
                item = QTableWidgetItem("" if value is None else str(value))
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(row_index, col_index, item)

    def load_selected_row(self) -> None:
        selected = self.table.selectionModel().selectedRows()
        if not selected:
            return
        row = self.rows[selected[0].row()]
        self.current_pk = row.get(self.columns[0])
        self._set_form(row)

    def new_record(self) -> None:
        self.current_pk = None
        self._set_form({column: "" for column in self.columns})

    def save_record(self) -> None:
        values = self._form_values()
        values = ensure_primary_key(self.table_name, values)
        with self.window.session_factory() as session:
            from construction_db.database import upsert_row

            upsert_row(session, self.table_name, values)
            session.commit()
        self.refresh()
        self.window.refresh_dashboard()

    def delete_record(self) -> None:
        if self.current_pk in (None, ""):
            return
        model = MODEL_REGISTRY[self.table_name]
        with self.window.session_factory() as session:
            record = session.get(model, self.current_pk)
            if record:
                session.delete(record)
                session.commit()
        self.new_record()
        self.refresh()
        self.window.refresh_dashboard()

    def _set_form(self, values: dict[str, object]) -> None:
        for column, editor in self.editors.items():
            value = values.get(column)
            text = "" if value is None else str(value)
            if isinstance(editor, QTextEdit):
                editor.setPlainText(text)
            else:
                editor.setText(text)

    def _form_values(self) -> dict[str, object]:
        values: dict[str, object] = {}
        for column, editor in self.editors.items():
            text = editor.toPlainText() if isinstance(editor, QTextEdit) else editor.text()
            values[column] = None if text == "" else text
        return values


class GlobalSearchPage(QWidget):
    def __init__(self, window: MainWindow):
        super().__init__()
        self.window = window
        layout = QVBoxLayout(self)
        title = QLabel("Global Search")
        title.setStyleSheet("font-size: 24px; font-weight: 700;")
        layout.addWidget(title)
        subtitle = QLabel("Search companies, contacts, projects, bid opportunities, emails, attachments, and follow-ups.")
        subtitle.setStyleSheet("color: #53606f; font-size: 14px;")
        layout.addWidget(subtitle)

        search_bar = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search company names, contacts, addresses, email subjects/bodies, attachment names...")
        self.search_input.returnPressed.connect(self.run_search)
        search_button = QPushButton("Search")
        search_button.clicked.connect(self.run_search)
        search_bar.addWidget(self.search_input, 1)
        search_bar.addWidget(search_button)
        layout.addLayout(search_bar)

        self.results = QTableWidget()
        self.results.setColumnCount(4)
        self.results.setHorizontalHeaderLabels(["Table", "Record ID", "Summary", "Matched Fields"])
        self.results.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        layout.addWidget(self.results)

    def run_search(self) -> None:
        query_text = self.search_input.text().strip()
        if not query_text:
            self.results.setRowCount(0)
            return
        with self.window.session_factory() as session:
            results = global_search(session, query_text, limit_per_table=25)
        rows: list[tuple[str, str, str, str]] = []
        for table_name, records in results.items():
            pk = table_columns(table_name)[0]
            for record in records:
                rows.append(
                    (
                        table_name,
                        str(record.get(pk) or ""),
                        _search_summary(table_name, record),
                        _matched_fields(record, query_text),
                    )
                )
        self.results.setRowCount(len(rows))
        for row_index, row_values in enumerate(rows):
            for col_index, value in enumerate(row_values):
                item = QTableWidgetItem(value)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.results.setItem(row_index, col_index, item)


def _search_summary(table_name: str, record: dict[str, object]) -> str:
    values = [str(record.get(field) or "") for field in DISPLAY_FIELDS.get(table_name, [])]
    return " | ".join(value for value in values if value)


def _matched_fields(record: dict[str, object], query_text: str) -> str:
    query = query_text.lower()
    matches = []
    for field, value in record.items():
        if value is not None and query in str(value).lower():
            matches.append(field)
    return ", ".join(matches[:8])


class ReviewQueuePage(QWidget):
    def __init__(self, window: MainWindow):
        super().__init__()
        self.window = window
        layout = QVBoxLayout(self)
        title = QLabel("Review Queue")
        title.setStyleSheet("font-size: 24px; font-weight: 700;")
        layout.addWidget(title)
        subtitle = QLabel("Records needing assignment, analysis, missing-data cleanup, or follow-up attention.")
        subtitle.setStyleSheet("color: #53606f; font-size: 14px;")
        layout.addWidget(subtitle)

        self.summary_table = QTableWidget()
        self.summary_table.setColumnCount(2)
        self.summary_table.setHorizontalHeaderLabels(["Review bucket", "Count"])
        self.summary_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        layout.addWidget(self.summary_table)

        self.details = QTextEdit()
        self.details.setReadOnly(True)
        self.details.setPlaceholderText("Review queue detail samples will appear here.")
        layout.addWidget(self.details)
        self.refresh()

    def refresh(self) -> None:
        with self.window.session_factory() as session:
            counts = review_queue_counts(session)
            details = review_queue_details(session, limit=5)
        self.summary_table.setRowCount(len(REVIEW_QUEUE_LABELS))
        detail_lines: list[str] = []
        for row_index, (key, label) in enumerate(REVIEW_QUEUE_LABELS.items()):
            self.summary_table.setItem(row_index, 0, QTableWidgetItem(label))
            self.summary_table.setItem(row_index, 1, QTableWidgetItem(str(counts[key])))
            detail_lines.append(f"{label} ({counts[key]})")
            for row in details[key]:
                detail_lines.append(f"  - {_review_row_summary(key, row)}")
            detail_lines.append("")
        self.details.setPlainText("\n".join(detail_lines).strip())


def _review_row_summary(queue_key: str, row: dict[str, object]) -> str:
    if queue_key == "emails_missing_project":
        return f"{row.get('email_activity_id')} | {row.get('from_email') or ''} | {row.get('subject') or ''}"
    if queue_key == "attachments_not_analyzed":
        return f"{row.get('attachment_id')} | {row.get('file_name') or ''}"
    if queue_key == "projects_missing_address":
        return f"{row.get('project_id')} | {row.get('project_name') or ''}"
    if queue_key == "contacts_missing_phone":
        return f"{row.get('contact_id')} | {row.get('full_name') or ''} | {row.get('email') or ''}"
    if queue_key == "overdue_followups":
        return f"{row.get('follow_up_id')} | due {row.get('due_date') or ''} | {row.get('follow_up_type') or ''}"
    return ""


class SettingsPage(QWidget):
    def __init__(self, window: MainWindow):
        super().__init__()
        self.window = window
        layout = QVBoxLayout(self)
        title = QLabel("Settings")
        title.setStyleSheet("font-size: 24px; font-weight: 700;")
        layout.addWidget(title)
        db_label = QLabel(f"SQLite database: {window.db_path}")
        db_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(db_label)
        instructions = QLabel(
            "Use Dashboard import/export actions to move data between SQLite and Excel. "
            "Future phases can add Outlook sender/date-range automation while writing into the same email_activity, attachments, contacts, companies, projects, and bid tables."
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)

        self.settings_table = QTableWidget()
        self.settings_table.setColumnCount(4)
        self.settings_table.setHorizontalHeaderLabels(["Key", "Value", "Type", "Description"])
        self.settings_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        layout.addWidget(self.settings_table)
        self.refresh()

    def refresh(self) -> None:
        model = MODEL_REGISTRY["settings"]
        with self.window.session_factory() as session:
            rows = [row_to_dict(record) for record in session.scalars(select(model)).all()]
        self.settings_table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            for col_index, column in enumerate(["setting_key", "setting_value", "setting_type", "description"]):
                value = row.get(column)
                item = QTableWidgetItem("" if value is None else str(value))
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.settings_table.setItem(row_index, col_index, item)


def _summary_text(prefix: str, summary: dict[str, int]) -> str:
    if not summary:
        return f"{prefix}: no matching sheets found."
    lines = [prefix]
    lines.extend(f"{table}: {count}" for table, count in summary.items())
    return "\n".join(lines)


def run_app(session_factory: sessionmaker[Session], db_path: Path) -> int:
    app = QApplication([])
    window = MainWindow(session_factory, db_path)
    window.show()
    return app.exec()
