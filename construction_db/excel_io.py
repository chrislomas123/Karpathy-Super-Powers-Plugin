"""Excel workbook import/export for Phase 1."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from construction_db.database import row_to_dict, table_columns, upsert_row
from construction_db.models import ImportBatch, MODEL_REGISTRY

IMPORT_ORDER = ["import_batches", *[name for name in MODEL_REGISTRY if name != "import_batches"]]


def export_to_excel(session: Session, workbook_path: str | Path) -> Path:
    output = Path(workbook_path).expanduser()
    output.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for table_name, model in MODEL_REGISTRY.items():
            rows = [row_to_dict(row) for row in session.scalars(select(model)).all()]
            pd.DataFrame(rows, columns=table_columns(table_name)).to_excel(
                writer,
                sheet_name=_sheet_name(table_name),
                index=False,
            )
    return output


def import_from_excel(session: Session, workbook_path: str | Path) -> dict[str, int]:
    workbook = Path(workbook_path).expanduser()
    sheets = pd.read_excel(workbook, sheet_name=None, dtype=object)
    summary: dict[str, int] = {}
    for table_name in IMPORT_ORDER:
        candidates = {_sheet_name(table_name), table_name, table_name.replace("_", " ").title()}
        sheet_name = next((name for name in sheets if name in candidates), None)
        if not sheet_name:
            continue
        imported = 0
        dataframe = sheets[sheet_name].where(pd.notna(sheets[sheet_name]), None)
        for row in dataframe.to_dict(orient="records"):
            if any(value not in (None, "") for value in row.values()):
                upsert_row(session, table_name, row)
                imported += 1
        summary[table_name] = imported
    session.add(
        ImportBatch(
            import_batch_id=f"XLSX-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}",
            import_date=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            import_mode="excel_import",
            emails_imported=summary.get("email_activity", 0),
            contacts_created=summary.get("contacts", 0),
            companies_created=summary.get("companies", 0),
            projects_created=summary.get("projects", 0),
            bid_opportunities_created=summary.get("bid_opportunities", 0),
            attachments_found=summary.get("attachments", 0),
            errors_warnings=f"Imported workbook: {workbook}",
        )
    )
    session.commit()
    return summary


def create_blank_workbook(workbook_path: str | Path) -> Path:
    output = Path(workbook_path).expanduser()
    output.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for table_name in MODEL_REGISTRY:
            pd.DataFrame(columns=table_columns(table_name)).to_excel(
                writer,
                sheet_name=_sheet_name(table_name),
                index=False,
            )
    return output


def _sheet_name(table_name: str) -> str:
    return table_name.replace("_", " ").title()[:31]
