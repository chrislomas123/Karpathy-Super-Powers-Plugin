"""Centralized lookup lists and seed data for the construction CRM app."""

COMPANY_TYPES = [
    "General Contractor",
    "Owner",
    "Municipality",
    "Vendor",
    "Disposal / Recycling Facility",
]

CONTACT_ROLES = [
    "Estimator",
    "Project Manager",
    "Assistant Project Manager",
    "Superintendent",
    "Owner",
    "Municipality Contact",
    "Vendor",
    "Disposal Facility Contact",
    "Billing / AP",
    "Unknown",
]

PROJECT_STAGES = [
    "New Lead",
    "Qualification",
    "Site Walk Scheduled",
    "Estimating",
    "RFI / Clarification",
    "Proposal Sent",
    "Follow-up",
    "Negotiation",
    "Awarded",
    "Lost",
    "Active",
    "Completed",
    "Invoiced",
    "Paid / Closed",
]

BID_STAGES = [
    "New Lead",
    "Qualification",
    "Site Walk Scheduled",
    "Estimating",
    "RFI / Clarification",
    "Proposal Sent",
    "Follow-up",
    "Negotiation",
    "Awarded",
    "Lost",
    "No Bid",
]

FOLLOW_UP_STATUSES = ["Open", "Completed", "Overdue", "Canceled", "Deferred"]

FOLLOW_UP_TYPES = [
    "Review New Bid Invite",
    "Bid Due Reminder",
    "Proposal Follow-Up",
    "RFI Follow-Up",
    "Award Status Follow-Up",
    "Active Project Check-In",
    "Invoice Follow-Up",
    "Manual Follow-Up",
]

BID_RESULTS = ["Pending", "Awarded", "Lost", "No Bid", "Canceled", "Unknown"]
CONTACT_STATUSES = ["Active", "Inactive", "Unknown"]

CLOSED_STAGES = ["Lost", "No Bid", "Canceled", "Paid / Closed"]
ACTIVE_STAGES = [
    "New Lead",
    "Qualification",
    "Site Walk Scheduled",
    "Estimating",
    "RFI / Clarification",
    "Proposal Sent",
    "Follow-up",
    "Negotiation",
    "Awarded",
    "Active",
    "Completed",
    "Invoiced",
]

DEFAULT_SELECTED_SENDERS = [
    "kbean@keiter.com",
    "aaron@annulli.com",
    "dtynan@teagnoconstruction.com",
    "cindy@witchenterprises.com",
    "dowling.phil@gmail.com",
    "rkberg@ingledc.com",
    "brian@gcscontractors.com",
    "james@camporacc.com",
]

STAGE_SEEDS = [
    ("project_stage", stage, "closed" if stage in CLOSED_STAGES else "active")
    for stage in PROJECT_STAGES
] + [
    ("bid_stage", stage, "closed" if stage in CLOSED_STAGES else "active")
    for stage in BID_STAGES
]
