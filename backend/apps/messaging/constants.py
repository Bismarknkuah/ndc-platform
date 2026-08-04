BROADCAST_KIND_CHOICES = [
    ("DIRECTIVE", "Directive (action required)"),
    ("ANNOUNCEMENT", "Announcement (informational)"),
]

PRIORITY_CHOICES = [
    ("LOW", "Low"),
    ("NORMAL", "Normal"),
    ("HIGH", "High"),
    ("URGENT", "Urgent"),
]

REPORT_STATUS_CHOICES = [
    ("SUBMITTED", "Submitted"),
    ("ACKNOWLEDGED", "Acknowledged"),
    ("RESOLVED", "Resolved"),
]

MEETING_TYPE_CHOICES = [
    ("MEETING", "Meeting"),
    ("WORKSHOP", "Training Workshop"),
]

MEETING_STATUS_CHOICES = [
    ("SCHEDULED", "Scheduled"),
    ("LIVE", "Live"),
    ("COMPLETED", "Completed"),
    ("CANCELLED", "Cancelled"),
]

RSVP_STATUS_CHOICES = [
    ("ATTENDING", "Attending"),
    ("DECLINED", "Declined"),
]

NOTIFICATION_TYPE_CHOICES = [
    ("BROADCAST", "Broadcast / Directive"),
    ("REPORT", "Upward Report"),
    ("DIRECT_MESSAGE", "Direct Message"),
    ("GROUP_MESSAGE", "Discussion Group Message"),
    ("TASK", "Department Task Assignment"),
    ("MEETING", "Meeting / Workshop"),
    ("ELECTION_ELIGIBILITY", "Election Voter Eligibility"),
    ("EVENT", "Event / Campaign"),
]
