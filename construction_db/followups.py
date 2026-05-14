"""Default follow-up generation rules for Phase 1 bid workflows."""

from __future__ import annotations

from datetime import date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from construction_db.database import new_id
from construction_db.models import BidOpportunity, FollowUp

DATE_FORMAT = "%Y-%m-%d"


def add_business_days(start_date: date, business_days: int) -> date:
    """Add or subtract business days, skipping Saturday and Sunday."""
    if business_days == 0:
        return start_date
    step = 1 if business_days > 0 else -1
    remaining = abs(business_days)
    current = start_date
    while remaining:
        current += timedelta(days=step)
        if current.weekday() < 5:
            remaining -= 1
    return current


def generate_followups_for_bid(session: Session, bid: BidOpportunity) -> list[FollowUp]:
    """Generate missing default follow-ups for a single bid opportunity."""
    created: list[FollowUp] = []
    if bid.bid_due_date:
        due_date = _parse_date(bid.bid_due_date)
        if due_date:
            reminder_date = add_business_days(due_date, -1)
            created.extend(
                _create_if_missing(
                    session=session,
                    bid=bid,
                    follow_up_type="Bid Due Reminder",
                    due_date=reminder_date,
                    notes="Automatically generated 1 business day before bid due date.",
                )
            )
            award_followup_date = due_date + timedelta(days=7)
            created.extend(
                _create_if_missing(
                    session=session,
                    bid=bid,
                    follow_up_type="Award Status Follow-Up",
                    due_date=award_followup_date,
                    notes="Automatically generated 7 days after bid due date.",
                )
            )
    if bid.proposal_sent_date:
        proposal_date = _parse_date(bid.proposal_sent_date)
        if proposal_date:
            created.extend(
                _create_if_missing(
                    session=session,
                    bid=bid,
                    follow_up_type="Proposal Follow-Up",
                    due_date=add_business_days(proposal_date, 3),
                    notes="Automatically generated 3 business days after proposal sent date.",
                )
            )
    return created


def generate_default_followups(session: Session) -> list[FollowUp]:
    """Generate missing default follow-ups for all bid opportunities."""
    created: list[FollowUp] = []
    for bid in session.scalars(select(BidOpportunity)).all():
        created.extend(generate_followups_for_bid(session, bid))
    session.commit()
    return created


def _create_if_missing(
    session: Session,
    bid: BidOpportunity,
    follow_up_type: str,
    due_date: date,
    notes: str,
) -> list[FollowUp]:
    due_date_text = due_date.strftime(DATE_FORMAT)
    existing = session.scalars(
        select(FollowUp).where(
            FollowUp.bid_id == bid.bid_id,
            FollowUp.follow_up_type == follow_up_type,
            FollowUp.due_date == due_date_text,
        )
    ).first()
    if existing:
        return []
    followup = FollowUp(
        follow_up_id=new_id("FU"),
        project_id=bid.project_id,
        bid_id=bid.bid_id,
        contact_id=bid.primary_contact_id,
        company_id=bid.gc_company_id,
        follow_up_type=follow_up_type,
        due_date=due_date_text,
        status="Open",
        notes=notes,
    )
    session.add(followup)
    return [followup]


def _parse_date(value: str) -> date | None:
    try:
        return datetime.strptime(value[:10], DATE_FORMAT).date()
    except ValueError:
        return None
