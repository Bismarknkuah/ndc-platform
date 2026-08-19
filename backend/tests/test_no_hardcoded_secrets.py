"""
Regression guard for a mistake that has genuinely happened three times in
this project's history: real database credentials (two different Atlas
clusters' passwords, and a Railway Redis password) each got hardcoded as
fallback defaults directly into tracked source/config files - twice into
config/settings.py, once (persisting even after settings.py was fixed)
into backend/.env.example. All three were caught and removed, but only
after already being committed to git history.

This test exists so that a fourth occurrence gets caught by the test
suite itself, regardless of who or what makes the edit (this exact
mistake has come from both a "helpful" direct commit and, separately,
direct edits made through GitHub's own web interface - the test suite
doesn't care which).
"""

import re
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent

# Real infrastructure hostnames that should never appear as a *fallback
# default* in tracked source/config - these are fine in an actual,
# untracked .env, but a committed file should only ever show generic
# placeholders (localhost, mongo, redis, docker-compose service names).
# Deliberately narrow: "redis.railway.internal" or "*.up.railway.app"
# are Railway's own generic naming *conventions* (not tied to any one
# project), safe to keep as a fallback default - only a specific
# Atlas cluster address is unambiguously always project-specific.
SUSPICIOUS_HOST_PATTERNS = [
    r"cluster\d+\.[a-z0-9]+\.mongodb\.net",
]

FILES_TO_CHECK = [
    BACKEND_DIR / "config" / "settings.py",
    BACKEND_DIR / ".env.example",
]


def test_no_real_infrastructure_hostnames_in_tracked_config():
    for path in FILES_TO_CHECK:
        content = path.read_text()
        for pattern in SUSPICIOUS_HOST_PATTERNS:
            matches = re.findall(pattern, content)
            assert not matches, (
                f"{path} contains a real-looking infrastructure hostname "
                f"matching {pattern!r} - this file is git-tracked and "
                "must only ever contain generic placeholders, never a "
                "specific deployment's real domain/cluster address."
            )


def test_no_known_previously_leaked_credentials_in_tracked_config():
    """Specific, concrete check for the exact three credentials that have
    actually leaked in this project's history - belt-and-suspenders on
    top of the more general hostname check above."""
    known_leaked_fragments = [
        "baristernkuah",  # first Atlas cluster's username
        "Desward8080",  # second Atlas cluster's password
        "IpZAEjyRWucjYEoPSXdmsUHAyKHRUgMp",  # Railway Redis password
    ]
    for path in FILES_TO_CHECK:
        content = path.read_text()
        for fragment in known_leaked_fragments:
            assert fragment not in content, (
                f"{path} contains a credential fragment ({fragment!r}) "
                "that has already leaked once before in this project's "
                "git history - must never reappear in a tracked file."
            )


def test_env_example_has_no_password_looking_values():
    """.env.example specifically should read as an obvious template - no
    value should look like a real generated password (long, high-entropy,
    mixed-case-and-digits) rather than an placeholder word."""
    env_example = BACKEND_DIR / ".env.example"
    content = env_example.read_text()

    for line in content.splitlines():
        if "=" not in line or line.strip().startswith("#"):
            continue
        key, _, value = line.partition("=")
        value = value.strip()
        if not value:
            continue
        # A real generated secret is long, mixes case and digits, and
        # has no separators - placeholders in this file are either
        # empty, an explanatory phrase ("change-this-to-..."), or a
        # generic example value.
        looks_like_real_secret = (
            len(value) >= 20
            and re.search(r"[a-z]", value)
            and re.search(r"[A-Z]", value)
            and re.search(r"[0-9]", value)
            and "-" not in value
            and "_" not in value
            and " " not in value
            and "://" not in value  # connection strings checked separately above
        )
        assert not looks_like_real_secret, (
            f"{env_example} line for {key!r} looks like a real generated "
            f"secret rather than a placeholder: {value!r}"
        )
