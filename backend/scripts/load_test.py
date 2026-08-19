"""
Load test focused on this platform's actual highest-risk scenario:
election-day result collation, where hundreds of branch executives
submit results in a compressed window while officers repeatedly poll the
live summary endpoint.

Usage:
    pip install locust  # already in requirements.txt's testing section
    locust -f scripts/load_test.py --host http://localhost:8000

Then open http://localhost:8089 to configure user count/spawn rate and
start the run, or run headless:
    locust -f scripts/load_test.py --host http://localhost:8000 \
        --users 200 --spawn-rate 20 --run-time 5m --headless

Before running against anything but a local/staging environment: this
generates real traffic, real writes, and real load - never point it at a
production database without a clear maintenance window and a fresh
backup (see docs/OPERATIONS.md).

This script does NOT seed its own test data - run
`python manage.py seed_platform` first, and see the environment variables
below for pointing it at real election/branch/candidate IDs from your
seeded (or staging) database.
"""

import os
import random

from locust import HttpUser, between, task

# Fill these in from your seeded/staging database - see the module
# docstring. Left blank, the collation tasks below simply skip (they check
# for a non-empty value first), so you can still load-test auth/dashboard
# in isolation without a fully configured election.
ELECTION_ID = os.getenv("LOAD_TEST_ELECTION_ID", "")
BRANCH_UNIT_ID = os.getenv("LOAD_TEST_BRANCH_UNIT_ID", "")
NATIONAL_UNIT_ID = os.getenv("LOAD_TEST_NATIONAL_UNIT_ID", "")
CANDIDATE_ID = os.getenv("LOAD_TEST_CANDIDATE_ID", "")

# A test member's credentials - create one via /api/v1/auth/register/ or
# the seed command's bootstrap admin, and grant it Elections/IT department
# membership at BRANCH_UNIT_ID if exercising the submission task.
TEST_EMAIL = os.getenv("LOAD_TEST_EMAIL", "admin@ndc.example")
TEST_PASSWORD = os.getenv("LOAD_TEST_PASSWORD", "ChangeMe123!")

_FAKE_COLLATION_PHOTO = "aGVsbG8="  # base64 for "hello" - a tiny placeholder image


class PartyMemberUser(HttpUser):
    """Simulates a logged-in member checking their dashboard and, if
    configured, a branch executive submitting/re-checking election
    results - the two dominant traffic patterns on election day."""

    wait_time = between(1, 3)

    def on_start(self):
        response = self.client.post(
            "/api/v1/auth/login/",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
            name="/api/v1/auth/login/",
        )
        if response.status_code == 200:
            token = response.json()["tokens"]["access"]
            self.client.headers.update({"Authorization": f"Bearer {token}"})
        else:
            self.environment.runner.quit()

    @task(5)
    def view_dashboard(self):
        self.client.get("/api/v1/dashboard/", name="/api/v1/dashboard/")

    @task(3)
    def view_notifications(self):
        self.client.get("/api/v1/messaging/notifications/", name="/api/v1/messaging/notifications/")

    @task(8)
    def view_election_summary(self):
        """The endpoint flagged in docs/OPERATIONS.md as the first place
        to add caching if this test shows it degrading under load - it
        aggregates every submission in a subtree on every call."""
        if not ELECTION_ID or not NATIONAL_UNIT_ID:
            return
        self.client.get(
            f"/api/v1/elections/{ELECTION_ID}/results/summary/?organizational_unit_id={NATIONAL_UNIT_ID}",
            name="/api/v1/elections/[id]/results/summary/",
        )

    @task(1)
    def submit_branch_result(self):
        """Only meaningful if TEST_EMAIL is a designated branch results
        submitter (an Elections/IT DepartmentAssignment at
        BRANCH_UNIT_ID) - see apps.elections.permissions.can_submit_result.
        Safe to leave unconfigured; skipped when IDs are blank."""
        if not (ELECTION_ID and BRANCH_UNIT_ID and CANDIDATE_ID):
            return
        self.client.post(
            "/api/v1/elections/results/",
            json={
                "election_id": ELECTION_ID,
                "branch_unit_id": BRANCH_UNIT_ID,
                "collation_sheet_photo_base64": _FAKE_COLLATION_PHOTO,
                "tallies": [{"candidate_id": CANDIDATE_ID, "votes": random.randint(0, 500)}],
                "total_registered_voters": random.randint(500, 1000),
                "total_valid_votes": random.randint(200, 500),
                "total_rejected_votes": random.randint(0, 10),
            },
            name="/api/v1/elections/results/ [POST]",
        )
