MESSAGE_ROLE_CHOICES = [
    ("USER", "User"),
    ("ASSISTANT", "Assistant"),
]

# How many of the most recent messages in a conversation get sent to the
# model as context - bounds token cost/latency on long-running threads
# rather than replaying an ever-growing history forever.
MAX_HISTORY_MESSAGES = 20
