"""SQLAlchemy models for the Phase 1 desktop construction database."""

from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Company(Base):
    __tablename__ = "companies"

    company_id: Mapped[str] = mapped_column(String, primary_key=True)
    company_name: Mapped[str] = mapped_column(String, nullable=False)
    company_type: Mapped[str | None] = mapped_column(String)
    address: Mapped[str | None] = mapped_column(Text)
    website: Mapped[str | None] = mapped_column(String)
    main_office_phone: Mapped[str | None] = mapped_column(String)
    estimating_email: Mapped[str | None] = mapped_column(String)
    main_contact_id: Mapped[str | None] = mapped_column(String)
    ap_billing_email: Mapped[str | None] = mapped_column(String)
    bid_submission_email: Mapped[str | None] = mapped_column(String)
    prequalification_requirements: Mapped[str | None] = mapped_column(Text)
    insurance_requirements: Mapped[str | None] = mapped_column(Text)
    safety_requirements: Mapped[str | None] = mapped_column(Text)
    preferred_delivery_method: Mapped[str | None] = mapped_column(String)
    portal_name: Mapped[str | None] = mapped_column(String)
    portal_url: Mapped[str | None] = mapped_column(String)
    estimating_department_phone: Mapped[str | None] = mapped_column(String)
    accounts_payable_contact: Mapped[str | None] = mapped_column(String)
    source_domain: Mapped[str | None] = mapped_column(String, index=True)
    notes: Mapped[str | None] = mapped_column(Text)
    created_date: Mapped[str | None] = mapped_column(String)
    last_email_date: Mapped[str | None] = mapped_column(String)
    status: Mapped[str | None] = mapped_column(String)
    last_bid_invite_date: Mapped[str | None] = mapped_column(String)
    last_award_date: Mapped[str | None] = mapped_column(String)
    last_active_project_date: Mapped[str | None] = mapped_column(String)

    contacts: Mapped[list["Contact"]] = relationship(back_populates="company")


class Contact(Base):
    __tablename__ = "contacts"

    contact_id: Mapped[str] = mapped_column(String, primary_key=True)
    company_id: Mapped[str | None] = mapped_column(ForeignKey("companies.company_id"), index=True)
    company_name: Mapped[str | None] = mapped_column(String)
    first_name: Mapped[str | None] = mapped_column(String)
    last_name: Mapped[str | None] = mapped_column(String)
    full_name: Mapped[str | None] = mapped_column(String, index=True)
    email: Mapped[str | None] = mapped_column(String, unique=True, index=True)
    phone: Mapped[str | None] = mapped_column(String)
    cell: Mapped[str | None] = mapped_column(String)
    title: Mapped[str | None] = mapped_column(String)
    default_role: Mapped[str | None] = mapped_column(String)
    company_address: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    source_email_id: Mapped[str | None] = mapped_column(String)
    source_email_subject: Mapped[str | None] = mapped_column(Text)
    source_email_date: Mapped[str | None] = mapped_column(String)
    last_email_date: Mapped[str | None] = mapped_column(String)
    contact_status: Mapped[str | None] = mapped_column(String)

    company: Mapped[Company | None] = relationship(back_populates="contacts")


class Project(Base):
    __tablename__ = "projects"

    project_id: Mapped[str] = mapped_column(String, primary_key=True)
    project_name: Mapped[str | None] = mapped_column(String, index=True)
    job_address: Mapped[str | None] = mapped_column(Text, index=True)
    city: Mapped[str | None] = mapped_column(String)
    state: Mapped[str | None] = mapped_column(String)
    zip: Mapped[str | None] = mapped_column(String)
    owner_company_id: Mapped[str | None] = mapped_column(ForeignKey("companies.company_id"))
    municipality: Mapped[str | None] = mapped_column(String)
    scope_summary: Mapped[str | None] = mapped_column(Text)
    project_stage: Mapped[str | None] = mapped_column(String, index=True)
    lead_source: Mapped[str | None] = mapped_column(String)
    first_email_date: Mapped[str | None] = mapped_column(String)
    last_activity_date: Mapped[str | None] = mapped_column(String)
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str | None] = mapped_column(Text)


class BidOpportunity(Base):
    __tablename__ = "bid_opportunities"
    __table_args__ = (UniqueConstraint("project_id", "gc_company_id", name="uq_bid_project_gc"),)

    bid_id: Mapped[str] = mapped_column(String, primary_key=True)
    project_id: Mapped[str | None] = mapped_column(ForeignKey("projects.project_id"), index=True)
    project_name: Mapped[str | None] = mapped_column(String)
    job_address: Mapped[str | None] = mapped_column(Text)
    gc_company_id: Mapped[str | None] = mapped_column(ForeignKey("companies.company_id"), index=True)
    gc_company_name: Mapped[str | None] = mapped_column(String)
    primary_contact_id: Mapped[str | None] = mapped_column(ForeignKey("contacts.contact_id"))
    bid_due_date: Mapped[str | None] = mapped_column(String, index=True)
    site_walk_date: Mapped[str | None] = mapped_column(String)
    bid_stage: Mapped[str | None] = mapped_column(String, index=True)
    proposal_sent_date: Mapped[str | None] = mapped_column(String)
    follow_up_date: Mapped[str | None] = mapped_column(String)
    result: Mapped[str | None] = mapped_column(String, index=True)
    scope_summary: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)


class ProjectContact(Base):
    __tablename__ = "project_contacts"

    project_contact_id: Mapped[str] = mapped_column(String, primary_key=True)
    project_id: Mapped[str | None] = mapped_column(ForeignKey("projects.project_id"), index=True)
    bid_id: Mapped[str | None] = mapped_column(ForeignKey("bid_opportunities.bid_id"), index=True)
    contact_id: Mapped[str | None] = mapped_column(ForeignKey("contacts.contact_id"), index=True)
    company_id: Mapped[str | None] = mapped_column(ForeignKey("companies.company_id"), index=True)
    role_on_project: Mapped[str | None] = mapped_column(String)
    stage_involved: Mapped[str | None] = mapped_column(String)
    communication_role: Mapped[str | None] = mapped_column(String)
    start_date: Mapped[str | None] = mapped_column(String)
    last_activity_date: Mapped[str | None] = mapped_column(String)
    notes: Mapped[str | None] = mapped_column(Text)


class EmailActivity(Base):
    __tablename__ = "email_activity"
    __table_args__ = (
        UniqueConstraint("conversation_id", "from_email", "subject", "received_date", name="uq_email_secondary_match"),
    )

    email_activity_id: Mapped[str] = mapped_column(String, primary_key=True)
    outlook_message_id: Mapped[str | None] = mapped_column(String, unique=True, index=True)
    conversation_id: Mapped[str | None] = mapped_column(String, index=True)
    received_date: Mapped[str | None] = mapped_column(String, index=True)
    from_name: Mapped[str | None] = mapped_column(String)
    from_email: Mapped[str | None] = mapped_column(String, index=True)
    contact_id: Mapped[str | None] = mapped_column(ForeignKey("contacts.contact_id"), index=True)
    company_id: Mapped[str | None] = mapped_column(ForeignKey("companies.company_id"), index=True)
    subject: Mapped[str | None] = mapped_column(Text)
    full_message_body: Mapped[str | None] = mapped_column(Text)
    cleaned_message_body: Mapped[str | None] = mapped_column(Text)
    project_id: Mapped[str | None] = mapped_column(ForeignKey("projects.project_id"), index=True)
    bid_id: Mapped[str | None] = mapped_column(ForeignKey("bid_opportunities.bid_id"), index=True)
    detected_project_name: Mapped[str | None] = mapped_column(String)
    detected_job_address: Mapped[str | None] = mapped_column(Text)
    detected_bid_due_date: Mapped[str | None] = mapped_column(String)
    detected_stage: Mapped[str | None] = mapped_column(String)
    has_attachments: Mapped[bool] = mapped_column(Boolean, default=False)
    attachment_count: Mapped[int] = mapped_column(Integer, default=0)
    import_batch_id: Mapped[str | None] = mapped_column(ForeignKey("import_batches.import_batch_id"), index=True)
    reviewed: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str | None] = mapped_column(Text)


class Attachment(Base):
    __tablename__ = "attachments"

    attachment_id: Mapped[str] = mapped_column(String, primary_key=True)
    outlook_message_id: Mapped[str | None] = mapped_column(String, index=True)
    email_activity_id: Mapped[str | None] = mapped_column(ForeignKey("email_activity.email_activity_id"), index=True)
    file_name: Mapped[str | None] = mapped_column(String, index=True)
    file_type: Mapped[str | None] = mapped_column(String)
    file_size: Mapped[int | None] = mapped_column(Integer)
    saved_location: Mapped[str | None] = mapped_column(Text)
    analyzed: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    extracted_project_name: Mapped[str | None] = mapped_column(String)
    extracted_job_address: Mapped[str | None] = mapped_column(Text)
    extracted_bid_due_date: Mapped[str | None] = mapped_column(String)
    extracted_scope: Mapped[str | None] = mapped_column(Text)
    extracted_contacts: Mapped[str | None] = mapped_column(Text)
    extracted_gc_project_number: Mapped[str | None] = mapped_column(String)
    extracted_site_walk_date: Mapped[str | None] = mapped_column(String)
    extracted_start_date: Mapped[str | None] = mapped_column(String)
    extracted_completion_deadline: Mapped[str | None] = mapped_column(String)
    notes: Mapped[str | None] = mapped_column(Text)


class FollowUp(Base):
    __tablename__ = "follow_ups"

    follow_up_id: Mapped[str] = mapped_column(String, primary_key=True)
    project_id: Mapped[str | None] = mapped_column(ForeignKey("projects.project_id"), index=True)
    bid_id: Mapped[str | None] = mapped_column(ForeignKey("bid_opportunities.bid_id"), index=True)
    contact_id: Mapped[str | None] = mapped_column(ForeignKey("contacts.contact_id"), index=True)
    company_id: Mapped[str | None] = mapped_column(ForeignKey("companies.company_id"), index=True)
    follow_up_type: Mapped[str | None] = mapped_column(String)
    due_date: Mapped[str | None] = mapped_column(String, index=True)
    status: Mapped[str | None] = mapped_column(String, index=True)
    notes: Mapped[str | None] = mapped_column(Text)
    created_from_email_id: Mapped[str | None] = mapped_column(ForeignKey("email_activity.email_activity_id"))
    completed_date: Mapped[str | None] = mapped_column(String)


class StageDefinition(Base):
    __tablename__ = "stage_definitions"

    stage_definition_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stage_type: Mapped[str] = mapped_column(String, index=True)
    stage_name: Mapped[str] = mapped_column(String, index=True)
    stage_status: Mapped[str] = mapped_column(String)
    sort_order: Mapped[int] = mapped_column(Integer)


class ImportBatch(Base):
    __tablename__ = "import_batches"

    import_batch_id: Mapped[str] = mapped_column(String, primary_key=True)
    import_date: Mapped[str | None] = mapped_column(String)
    selected_senders: Mapped[str | None] = mapped_column(Text)
    date_range_start: Mapped[str | None] = mapped_column(String)
    date_range_end: Mapped[str | None] = mapped_column(String)
    import_mode: Mapped[str | None] = mapped_column(String)
    emails_found: Mapped[int] = mapped_column(Integer, default=0)
    emails_imported: Mapped[int] = mapped_column(Integer, default=0)
    emails_skipped: Mapped[int] = mapped_column(Integer, default=0)
    contacts_created: Mapped[int] = mapped_column(Integer, default=0)
    contacts_updated: Mapped[int] = mapped_column(Integer, default=0)
    companies_created: Mapped[int] = mapped_column(Integer, default=0)
    projects_created: Mapped[int] = mapped_column(Integer, default=0)
    bid_opportunities_created: Mapped[int] = mapped_column(Integer, default=0)
    attachments_found: Mapped[int] = mapped_column(Integer, default=0)
    attachments_analyzed: Mapped[int] = mapped_column(Integer, default=0)
    possible_duplicates_found: Mapped[int] = mapped_column(Integer, default=0)
    errors_warnings: Mapped[str | None] = mapped_column(Text)


class AppSetting(Base):
    __tablename__ = "settings"

    setting_key: Mapped[str] = mapped_column(String, primary_key=True)
    setting_value: Mapped[str | None] = mapped_column(Text)
    setting_type: Mapped[str | None] = mapped_column(String)
    description: Mapped[str | None] = mapped_column(Text)


MODEL_REGISTRY = {
    "companies": Company,
    "contacts": Contact,
    "projects": Project,
    "bid_opportunities": BidOpportunity,
    "project_contacts": ProjectContact,
    "email_activity": EmailActivity,
    "attachments": Attachment,
    "follow_ups": FollowUp,
    "stage_definitions": StageDefinition,
    "import_batches": ImportBatch,
    "settings": AppSetting,
}
