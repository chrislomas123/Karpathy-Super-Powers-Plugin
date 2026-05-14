"""Application settings helpers for Phase 1 and future automation defaults."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from construction_db.models import AppSetting


def list_settings(session: Session) -> list[AppSetting]:
    """Return app settings ordered by key."""
    return list(session.scalars(select(AppSetting).order_by(AppSetting.setting_key)))


def get_setting(session: Session, key: str) -> AppSetting | None:
    """Return a setting by key, if it exists."""
    return session.get(AppSetting, key)


def set_setting(
    session: Session,
    key: str,
    value: str,
    setting_type: str | None = None,
    description: str | None = None,
) -> AppSetting:
    """Create or update an app setting."""
    setting = session.get(AppSetting, key)
    if setting is None:
        setting = AppSetting(setting_key=key)
        session.add(setting)
    setting.setting_value = value
    if setting_type is not None:
        setting.setting_type = setting_type
    elif setting.setting_type is None:
        setting.setting_type = "text"
    if description is not None:
        setting.description = description
    session.commit()
    return setting


def format_settings(settings: list[AppSetting]) -> str:
    """Format settings for CLI output."""
    if not settings:
        return "No settings found."
    lines = ["Settings"]
    for setting in settings:
        value = setting.setting_value or ""
        value = value.replace("\n", ", ")
        lines.append(f"{setting.setting_key} [{setting.setting_type or 'text'}] = {value}")
        if setting.description:
            lines.append(f"  {setting.description}")
    return "\n".join(lines)
