import base64
import datetime

import pytest

pytestmark = pytest.mark.django_db

_FAKE_PHOTO = base64.b64encode(b"fake-collation-sheet-bytes").decode("ascii")


def _window():
    start = datetime.datetime.utcnow().isoformat() + "Z"
    end = (datetime.datetime.utcnow() + datetime.timedelta(days=7)).isoformat() + "Z"
    return start, end


def _make_branch_executive(
    branch_unit,
    email="branchexec@example.com",
    membership_id="NDC-TEST-000400",
    designated=True,
):
    """
    Creates a Branch-level executive. By default also grants them the
    Elections-department designation at this specific branch (the
    "district IT assigns one of the branch executives to submit results"
    workflow) so callers who just need "a valid results submitter" don't
    have to wire that up themselves. Pass designated=False to get a branch
    executive WITHOUT that designation, for negative tests.
    """
    from apps.accounts.authentication import issue_token_pair
    from apps.accounts.documents import Role, User
    from apps.departments.documents import Department, DepartmentAssignment
    from rest_framework.test import APIClient

    role = Role.objects.create(
        name="Branch Chairman",
        code=f"branch_chairman_election_test_{membership_id}",
        scope="BRANCH",
        is_executive=True,
        permissions=["messaging.report.upward", "membership.register"],
    )
    user = User(
        email=email,
        phone_number=f"0244{membership_id[-6:]}",
        first_name="Branch",
        last_name="Exec",
        membership_id=membership_id,
        organizational_unit=branch_unit,
        role=role,
    )
    user.set_password("StrongPass123!")
    user.save()

    if designated:
        elections_department = Department.objects(code="elections").first()
        if elections_department is None:
            elections_department = Department.objects.create(
                code="elections", name="Elections"
            )
        DepartmentAssignment.objects.create(
            user=user,
            department=elections_department,
            organizational_unit=branch_unit,
            position="MEMBER",
        )

    client = APIClient()
    tokens = issue_token_pair(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    return client, user


# ---------------------------------------------------------------------------
# Election organizing authority
# ---------------------------------------------------------------------------


def test_election_it_director_can_organize_national_election(
    election_it_director_client, national_unit
):
    start, end = _window()
    response = election_it_director_client.post(
        "/api/v1/elections/",
        {
            "title": "2028 National General Election",
            "election_type": "NATIONAL_GENERAL",
            "scope_unit_id": str(national_unit.id),
            "start_date": start,
            "end_date": end,
        },
        format="json",
    )
    assert response.status_code == 201
    assert response.json()["status"] == "DRAFT"


def test_election_it_director_can_organize_election_at_regional_level(
    election_it_director_client, regional_unit
):
    """'organize elections at all levels' - national authority reaches down to a regional-scoped election too."""
    start, end = _window()
    response = election_it_director_client.post(
        "/api/v1/elections/",
        {
            "title": "Ashanti Regional Executives Primary",
            "election_type": "PARTY_INTERNAL",
            "scope_unit_id": str(regional_unit.id),
            "start_date": start,
            "end_date": end,
        },
        format="json",
    )
    assert response.status_code == 201


def test_election_it_director_can_organize_a_poll(
    election_it_director_client, national_unit
):
    start, end = _window()
    response = election_it_director_client.post(
        "/api/v1/elections/",
        {
            "title": "Manifesto Priorities Poll",
            "election_type": "POLL",
            "scope_unit_id": str(national_unit.id),
            "start_date": start,
            "end_date": end,
        },
        format="json",
    )
    assert response.status_code == 201
    assert response.json()["election_type"] == "POLL"


def test_ordinary_member_cannot_organize_election(auth_client, national_unit):
    start, end = _window()
    response = auth_client.post(
        "/api/v1/elections/",
        {
            "title": "Should fail",
            "election_type": "POLL",
            "scope_unit_id": str(national_unit.id),
            "start_date": start,
            "end_date": end,
        },
        format="json",
    )
    assert response.status_code == 403


def test_end_date_must_be_after_start_date(election_it_director_client, national_unit):
    start, end = _window()
    response = election_it_director_client.post(
        "/api/v1/elections/",
        {
            "title": "Bad dates",
            "election_type": "POLL",
            "scope_unit_id": str(national_unit.id),
            "start_date": end,
            "end_date": start,
        },
        format="json",
    )
    assert response.status_code == 400


def test_director_can_progress_election_status(
    election_it_director_client, national_unit
):
    start, end = _window()
    created = election_it_director_client.post(
        "/api/v1/elections/",
        {
            "title": "Status Flow Test",
            "election_type": "POLL",
            "scope_unit_id": str(national_unit.id),
            "start_date": start,
            "end_date": end,
        },
        format="json",
    ).json()

    opened = election_it_director_client.patch(
        f"/api/v1/elections/{created['id']}/", {"status": "OPEN"}, format="json"
    )
    assert opened.json()["status"] == "OPEN"

    collating = election_it_director_client.patch(
        f"/api/v1/elections/{created['id']}/", {"status": "COLLATION"}, format="json"
    )
    assert collating.json()["status"] == "COLLATION"


# ---------------------------------------------------------------------------
# Candidates
# ---------------------------------------------------------------------------


@pytest.fixture
def election_with_candidates(election_it_director_client, national_unit):
    start, end = _window()
    election = election_it_director_client.post(
        "/api/v1/elections/",
        {
            "title": "2028 National General Election",
            "election_type": "NATIONAL_GENERAL",
            "scope_unit_id": str(national_unit.id),
            "start_date": start,
            "end_date": end,
        },
        format="json",
    ).json()

    candidate_a = election_it_director_client.post(
        f"/api/v1/elections/{election['id']}/candidates/",
        {"name": "Candidate A"},
        format="json",
    ).json()
    candidate_b = election_it_director_client.post(
        f"/api/v1/elections/{election['id']}/candidates/",
        {"name": "Candidate B"},
        format="json",
    ).json()
    return election, candidate_a, candidate_b


def test_candidates_can_be_added_to_election(election_with_candidates):
    election, candidate_a, candidate_b = election_with_candidates
    assert candidate_a["name"] == "Candidate A"
    assert candidate_b["name"] == "Candidate B"


def test_unauthorized_user_cannot_add_candidates(auth_client, election_with_candidates):
    election, _, _ = election_with_candidates
    response = auth_client.post(
        f"/api/v1/elections/{election['id']}/candidates/",
        {"name": "Sneaky Candidate"},
        format="json",
    )
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# Result submission (collation)
# ---------------------------------------------------------------------------


def test_branch_executive_can_submit_result(election_with_candidates, branch_unit):
    election, candidate_a, candidate_b = election_with_candidates
    client, _ = _make_branch_executive(branch_unit)

    response = client.post(
        "/api/v1/elections/results/",
        {
            "election_id": election["id"],
            "branch_unit_id": str(branch_unit.id),
            "collation_sheet_photo_base64": _FAKE_PHOTO,
            "tallies": [
                {"candidate_id": candidate_a["id"], "votes": 80},
                {"candidate_id": candidate_b["id"], "votes": 20},
            ],
            "total_registered_voters": 150,
            "total_valid_votes": 100,
            "total_rejected_votes": 5,
        },
        format="json",
    )
    assert response.status_code == 201
    assert response.json()["status"] == "SUBMITTED"
    assert response.json()["collation_sheet_photo_base64"] == _FAKE_PHOTO


def test_result_submission_requires_collation_sheet_photo(
    election_with_candidates, branch_unit
):
    election, candidate_a, _ = election_with_candidates
    client, _ = _make_branch_executive(branch_unit)
    response = client.post(
        "/api/v1/elections/results/",
        {
            "election_id": election["id"],
            "branch_unit_id": str(branch_unit.id),
            "tallies": [{"candidate_id": candidate_a["id"], "votes": 10}],
            # deliberately omit collation_sheet_photo_base64
        },
        format="json",
    )
    assert response.status_code == 400
    assert "collation_sheet_photo_base64" in response.json()["error"]["message"]


def test_oversized_collation_sheet_photo_rejected(
    election_with_candidates, branch_unit
):
    election, candidate_a, _ = election_with_candidates
    client, _ = _make_branch_executive(branch_unit)
    response = client.post(
        "/api/v1/elections/results/",
        {
            "election_id": election["id"],
            "branch_unit_id": str(branch_unit.id),
            "collation_sheet_photo_base64": "A" * 3_000_000,
            "tallies": [{"candidate_id": candidate_a["id"], "votes": 10}],
        },
        format="json",
    )
    assert response.status_code == 400


def test_submitter_can_amend_collation_sheet_photo(
    election_with_candidates, branch_unit
):
    election, candidate_a, _ = election_with_candidates
    client, _ = _make_branch_executive(branch_unit)
    created = client.post(
        "/api/v1/elections/results/",
        {
            "election_id": election["id"],
            "branch_unit_id": str(branch_unit.id),
            "collation_sheet_photo_base64": _FAKE_PHOTO,
            "tallies": [{"candidate_id": candidate_a["id"], "votes": 10}],
        },
        format="json",
    ).json()

    new_photo = base64.b64encode(b"a-clearer-retake").decode("ascii")
    amended = client.patch(
        f"/api/v1/elections/results/{created['id']}/",
        {"collation_sheet_photo_base64": new_photo},
        format="json",
    )
    assert amended.status_code == 200
    assert amended.json()["collation_sheet_photo_base64"] == new_photo


def test_non_branch_member_cannot_submit_result(
    election_with_candidates, branch_unit, auth_client
):
    election, candidate_a, _ = election_with_candidates
    response = auth_client.post(
        "/api/v1/elections/results/",
        {
            "election_id": election["id"],
            "branch_unit_id": str(branch_unit.id),
            "collation_sheet_photo_base64": _FAKE_PHOTO,
            "tallies": [{"candidate_id": candidate_a["id"], "votes": 10}],
        },
        format="json",
    )
    assert response.status_code == 403


def test_ordinary_member_at_branch_cannot_submit_result(
    election_with_candidates, branch_unit, member_user, api_client
):
    """member_user is an Ordinary Member (non-executive) at branch_unit - should still be blocked."""
    from apps.accounts.authentication import issue_token_pair

    election, candidate_a, _ = election_with_candidates
    tokens = issue_token_pair(member_user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

    response = api_client.post(
        "/api/v1/elections/results/",
        {
            "election_id": election["id"],
            "branch_unit_id": str(branch_unit.id),
            "collation_sheet_photo_base64": _FAKE_PHOTO,
            "tallies": [{"candidate_id": candidate_a["id"], "votes": 10}],
        },
        format="json",
    )
    assert response.status_code == 403


def test_duplicate_submission_rejected(election_with_candidates, branch_unit):
    election, candidate_a, _ = election_with_candidates
    client, _ = _make_branch_executive(branch_unit)
    payload = {
        "election_id": election["id"],
        "branch_unit_id": str(branch_unit.id),
        "collation_sheet_photo_base64": _FAKE_PHOTO,
        "tallies": [{"candidate_id": candidate_a["id"], "votes": 10}],
    }
    first = client.post("/api/v1/elections/results/", payload, format="json")
    assert first.status_code == 201
    second = client.post("/api/v1/elections/results/", payload, format="json")
    assert second.status_code == 409


def test_submitter_can_amend_own_result(election_with_candidates, branch_unit):
    election, candidate_a, candidate_b = election_with_candidates
    client, _ = _make_branch_executive(branch_unit)
    created = client.post(
        "/api/v1/elections/results/",
        {
            "election_id": election["id"],
            "branch_unit_id": str(branch_unit.id),
            "collation_sheet_photo_base64": _FAKE_PHOTO,
            "tallies": [{"candidate_id": candidate_a["id"], "votes": 10}],
        },
        format="json",
    ).json()

    amended = client.patch(
        f"/api/v1/elections/results/{created['id']}/",
        {
            "collation_sheet_photo_base64": _FAKE_PHOTO,
            "tallies": [
                {"candidate_id": candidate_a["id"], "votes": 55},
                {"candidate_id": candidate_b["id"], "votes": 45},
            ],
        },
        format="json",
    )
    assert amended.status_code == 200
    votes = {t["candidate_id"]: t["votes"] for t in amended.json()["tallies"]}
    assert votes[candidate_a["id"]] == 55


def test_director_can_verify_result(
    election_with_candidates, branch_unit, election_it_director_client
):
    election, candidate_a, _ = election_with_candidates
    client, _ = _make_branch_executive(branch_unit)
    created = client.post(
        "/api/v1/elections/results/",
        {
            "election_id": election["id"],
            "branch_unit_id": str(branch_unit.id),
            "collation_sheet_photo_base64": _FAKE_PHOTO,
            "tallies": [{"candidate_id": candidate_a["id"], "votes": 10}],
        },
        format="json",
    ).json()

    verified = election_it_director_client.patch(
        f"/api/v1/elections/results/{created['id']}/",
        {"status": "VERIFIED"},
        format="json",
    )
    assert verified.status_code == 200
    assert verified.json()["status"] == "VERIFIED"
    assert verified.json()["verified_by"] is not None


def test_unrelated_user_cannot_verify_result(
    election_with_candidates, branch_unit, auth_client
):
    election, candidate_a, _ = election_with_candidates
    client, _ = _make_branch_executive(branch_unit)
    created = client.post(
        "/api/v1/elections/results/",
        {
            "election_id": election["id"],
            "branch_unit_id": str(branch_unit.id),
            "collation_sheet_photo_base64": _FAKE_PHOTO,
            "tallies": [{"candidate_id": candidate_a["id"], "votes": 10}],
        },
        format="json",
    ).json()

    response = auth_client.patch(
        f"/api/v1/elections/results/{created['id']}/",
        {"status": "VERIFIED"},
        format="json",
    )
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# Automatic analysis / collation summary
# ---------------------------------------------------------------------------


def test_summary_aggregates_single_branch(
    election_with_candidates, branch_unit, national_unit, election_it_director_client
):
    election, candidate_a, candidate_b = election_with_candidates
    client, _ = _make_branch_executive(branch_unit)
    client.post(
        "/api/v1/elections/results/",
        {
            "election_id": election["id"],
            "branch_unit_id": str(branch_unit.id),
            "collation_sheet_photo_base64": _FAKE_PHOTO,
            "tallies": [
                {"candidate_id": candidate_a["id"], "votes": 80},
                {"candidate_id": candidate_b["id"], "votes": 20},
            ],
            "total_registered_voters": 150,
            "total_valid_votes": 100,
            "total_rejected_votes": 5,
        },
        format="json",
    )

    # Live, mid-collation results are only visible to a legitimate
    # viewer (organizer, or Chairman/Secretary of the level) now - not
    # to just anyone, including the branch executive who submitted this
    # one result. See can_view_election_progress.
    response = election_it_director_client.get(
        f"/api/v1/elections/{election['id']}/results/summary/?organizational_unit_id={national_unit.id}"
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total_votes_cast"] == 100
    assert body["leading_candidate"]["candidate_name"] == "Candidate A"
    assert body["leading_candidate"]["percentage"] == 80.0
    assert body["branches_expected"] == 1
    assert body["branches_reported"] == 1
    assert body["is_fully_reported"] is True
    assert body["turnout_percentage"] == 70.0  # (100+5)/150


def test_summary_reflects_partial_reporting_across_multiple_branches(
    election_with_candidates,
    branch_unit,
    constituency_unit,
    national_unit,
    election_it_director_client,
):
    from apps.hierarchy.documents import OrganizationalUnit

    election, candidate_a, candidate_b = election_with_candidates

    # A second branch under the same constituency that never reports.
    OrganizationalUnit.objects.create(
        name="Unreported Branch",
        code="ndc-unreported-branch",
        unit_type="BRANCH",
        parent=constituency_unit,
    )

    client, _ = _make_branch_executive(branch_unit)
    client.post(
        "/api/v1/elections/results/",
        {
            "election_id": election["id"],
            "branch_unit_id": str(branch_unit.id),
            "collation_sheet_photo_base64": _FAKE_PHOTO,
            "tallies": [
                {"candidate_id": candidate_a["id"], "votes": 30},
                {"candidate_id": candidate_b["id"], "votes": 10},
            ],
        },
        format="json",
    )

    response = election_it_director_client.get(
        f"/api/v1/elections/{election['id']}/results/summary/?organizational_unit_id={national_unit.id}"
    )
    body = response.json()
    assert body["branches_expected"] == 2
    assert body["branches_reported"] == 1
    assert body["reporting_percentage"] == 50.0
    assert body["is_fully_reported"] is False
    assert body["total_votes_cast"] == 40


def test_summary_at_regional_level_matches_national_when_single_region(
    election_with_candidates, branch_unit, regional_unit, election_it_director_client
):
    election, candidate_a, candidate_b = election_with_candidates
    client, _ = _make_branch_executive(branch_unit)
    client.post(
        "/api/v1/elections/results/",
        {
            "election_id": election["id"],
            "branch_unit_id": str(branch_unit.id),
            "collation_sheet_photo_base64": _FAKE_PHOTO,
            "tallies": [
                {"candidate_id": candidate_a["id"], "votes": 5},
                {"candidate_id": candidate_b["id"], "votes": 3},
            ],
        },
        format="json",
    )
    response = election_it_director_client.get(
        f"/api/v1/elections/{election['id']}/results/summary/?organizational_unit_id={regional_unit.id}"
    )
    assert response.status_code == 200
    assert response.json()["total_votes_cast"] == 8


def test_multi_position_election_tallies_are_independent(
    election_it_director_client, national_unit, branch_unit
):
    start, end = _window()
    election = election_it_director_client.post(
        "/api/v1/elections/",
        {
            "title": "2028 Internal Party Election",
            "election_type": "PARTY_INTERNAL",
            "scope_unit_id": str(national_unit.id),
            "start_date": start,
            "end_date": end,
        },
        format="json",
    ).json()

    chair_candidate = election_it_director_client.post(
        f"/api/v1/elections/{election['id']}/candidates/",
        {"name": "Chair Candidate", "position": "National Chairman"},
        format="json",
    ).json()
    treasurer_candidate = election_it_director_client.post(
        f"/api/v1/elections/{election['id']}/candidates/",
        {"name": "Treasurer Candidate", "position": "National Treasurer"},
        format="json",
    ).json()

    client, _ = _make_branch_executive(branch_unit)
    client.post(
        "/api/v1/elections/results/",
        {
            "election_id": election["id"],
            "branch_unit_id": str(branch_unit.id),
            "position": "National Chairman",
            "collation_sheet_photo_base64": _FAKE_PHOTO,
            "tallies": [{"candidate_id": chair_candidate["id"], "votes": 12}],
        },
        format="json",
    )
    client.post(
        "/api/v1/elections/results/",
        {
            "election_id": election["id"],
            "branch_unit_id": str(branch_unit.id),
            "position": "National Treasurer",
            "collation_sheet_photo_base64": _FAKE_PHOTO,
            "tallies": [{"candidate_id": treasurer_candidate["id"], "votes": 9}],
        },
        format="json",
    )

    chair_summary = election_it_director_client.get(
        f"/api/v1/elections/{election['id']}/results/summary/"
        f"?organizational_unit_id={national_unit.id}&position=National Chairman"
    ).json()
    treasurer_summary = election_it_director_client.get(
        f"/api/v1/elections/{election['id']}/results/summary/"
        f"?organizational_unit_id={national_unit.id}&position=National Treasurer"
    ).json()

    assert chair_summary["total_votes_cast"] == 12
    assert treasurer_summary["total_votes_cast"] == 9


# ---------------------------------------------------------------------------
# District/Regional IT directors via the department system
# ---------------------------------------------------------------------------


def _make_department_it_director(unit, elections_department, email, membership_id):
    from apps.accounts.authentication import issue_token_pair
    from apps.accounts.documents import Role, User
    from apps.departments.documents import DepartmentAssignment
    from rest_framework.test import APIClient

    role = Role.objects.create(
        name="Constituency Chairman",
        code=f"district_it_test_{membership_id}",
        scope=unit.unit_type,
        permissions=["hierarchy.manage"],
    )
    user = User(
        email=email,
        phone_number=f"0244{membership_id[-6:]}",
        first_name="District",
        last_name="IT",
        membership_id=membership_id,
        organizational_unit=unit,
        role=role,
    )
    user.set_password("StrongPass123!")
    user.save()
    DepartmentAssignment.objects.create(
        user=user,
        department=elections_department,
        organizational_unit=unit,
        position="HEAD",
    )

    client = APIClient()
    tokens = issue_token_pair(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    return client, user


def test_constituency_elections_department_head_can_organize_election_in_own_jurisdiction(
    elections_department, constituency_unit
):
    client, _ = _make_department_it_director(
        constituency_unit,
        elections_department,
        "district-it@example.com",
        "NDC-TEST-000500",
    )
    start, end = _window()
    response = client.post(
        "/api/v1/elections/",
        {
            "title": "Constituency Executive Primary",
            "election_type": "PARTY_INTERNAL",
            "scope_unit_id": str(constituency_unit.id),
            "start_date": start,
            "end_date": end,
        },
        format="json",
    )
    assert response.status_code == 201


def test_constituency_elections_head_cannot_organize_outside_jurisdiction(
    elections_department, constituency_unit, national_unit
):
    client, _ = _make_department_it_director(
        constituency_unit,
        elections_department,
        "district-it2@example.com",
        "NDC-TEST-000501",
    )
    start, end = _window()
    response = client.post(
        "/api/v1/elections/",
        {
            "title": "Should fail",
            "election_type": "NATIONAL_GENERAL",
            "scope_unit_id": str(national_unit.id),
            "start_date": start,
            "end_date": end,
        },
        format="json",
    )
    assert response.status_code == 403


def test_district_it_can_appoint_designated_branch_submitter(
    elections_department, constituency_unit, branch_unit, election_with_candidates
):
    """The actual workflow: a district IT director (Elections dept HEAD at
    the constituency) appoints ONE branch executive as the designated
    results submitter for a branch in their jurisdiction, via the
    existing department-assignment endpoint."""
    district_client, _ = _make_department_it_director(
        constituency_unit,
        elections_department,
        "district-it3@example.com",
        "NDC-TEST-000502",
    )
    election, candidate_a, _ = election_with_candidates

    # Two branch chairmen at the same branch; neither pre-designated.
    _, undesignated_user = _make_branch_executive(
        branch_unit,
        email="undesignated@example.com",
        membership_id="NDC-TEST-000503",
        designated=False,
    )

    appoint = district_client.post(
        "/api/v1/departments/assignments/",
        {
            "user_id": str(undesignated_user.id),
            "department_id": str(elections_department.id),
            "organizational_unit_id": str(branch_unit.id),
            "position": "MEMBER",
        },
        format="json",
    )
    assert appoint.status_code == 201

    from apps.accounts.authentication import issue_token_pair
    from rest_framework.test import APIClient

    now_designated_client = APIClient()
    tokens = issue_token_pair(undesignated_user)
    now_designated_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

    response = now_designated_client.post(
        "/api/v1/elections/results/",
        {
            "election_id": election["id"],
            "branch_unit_id": str(branch_unit.id),
            "collation_sheet_photo_base64": _FAKE_PHOTO,
            "tallies": [{"candidate_id": candidate_a["id"], "votes": 5}],
        },
        format="json",
    )
    assert response.status_code == 201


def test_undesignated_branch_executive_cannot_submit_result(
    branch_unit, election_with_candidates
):
    election, candidate_a, _ = election_with_candidates
    client, _ = _make_branch_executive(branch_unit, designated=False)
    response = client.post(
        "/api/v1/elections/results/",
        {
            "election_id": election["id"],
            "branch_unit_id": str(branch_unit.id),
            "collation_sheet_photo_base64": _FAKE_PHOTO,
            "tallies": [{"candidate_id": candidate_a["id"], "votes": 5}],
        },
        format="json",
    )
    assert response.status_code == 403


def test_district_it_can_see_results_in_their_jurisdiction(
    elections_department, constituency_unit, branch_unit, election_with_candidates
):
    election, candidate_a, _ = election_with_candidates
    client, _ = _make_branch_executive(branch_unit)
    client.post(
        "/api/v1/elections/results/",
        {
            "election_id": election["id"],
            "branch_unit_id": str(branch_unit.id),
            "collation_sheet_photo_base64": _FAKE_PHOTO,
            "tallies": [{"candidate_id": candidate_a["id"], "votes": 15}],
        },
        format="json",
    )

    district_client, _ = _make_department_it_director(
        constituency_unit,
        elections_department,
        "district-it4@example.com",
        "NDC-TEST-000504",
    )
    response = district_client.get(
        f"/api/v1/elections/results/?election_id={election['id']}&organizational_unit_id={constituency_unit.id}"
    )
    assert response.status_code == 200
    assert response.json()["count"] == 1


def test_unauthorized_user_cannot_list_results_by_jurisdiction(
    auth_client, constituency_unit, election_with_candidates
):
    election, _, _ = election_with_candidates
    response = auth_client.get(
        f"/api/v1/elections/results/?election_id={election['id']}&organizational_unit_id={constituency_unit.id}"
    )
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# Candidate photos and multi-party general elections
# ---------------------------------------------------------------------------


def test_candidate_can_have_photo_and_party(election_it_director_client, national_unit):
    start, end = _window()
    election = election_it_director_client.post(
        "/api/v1/elections/",
        {
            "title": "2028 Presidential Election",
            "election_type": "NATIONAL_GENERAL",
            "scope_unit_id": str(national_unit.id),
            "start_date": start,
            "end_date": end,
        },
        format="json",
    ).json()

    fake_png = base64.b64encode(b"fake-image-bytes").decode("ascii")
    response = election_it_director_client.post(
        f"/api/v1/elections/{election['id']}/candidates/",
        {
            "name": "Jane Doe",
            "position": "President",
            "party": "NDC",
            "photo_base64": fake_png,
        },
        format="json",
    )
    assert response.status_code == 201
    body = response.json()
    assert body["party"] == "NDC"
    assert body["photo_base64"] == fake_png


def test_oversized_photo_rejected(election_it_director_client, national_unit):
    start, end = _window()
    election = election_it_director_client.post(
        "/api/v1/elections/",
        {
            "title": "Photo size test",
            "election_type": "POLL",
            "scope_unit_id": str(national_unit.id),
            "start_date": start,
            "end_date": end,
        },
        format="json",
    ).json()
    huge = "A" * 3_000_000
    response = election_it_director_client.post(
        f"/api/v1/elections/{election['id']}/candidates/",
        {"name": "Too Big", "photo_base64": huge},
        format="json",
    )
    assert response.status_code == 400


def test_national_sees_party_breakdown_for_presidential_race(
    election_it_director_client, national_unit, branch_unit
):
    start, end = _window()
    election = election_it_director_client.post(
        "/api/v1/elections/",
        {
            "title": "2028 Presidential Election",
            "election_type": "NATIONAL_GENERAL",
            "scope_unit_id": str(national_unit.id),
            "start_date": start,
            "end_date": end,
        },
        format="json",
    ).json()

    ndc_candidate = election_it_director_client.post(
        f"/api/v1/elections/{election['id']}/candidates/",
        {"name": "NDC Flagbearer", "position": "President", "party": "NDC"},
        format="json",
    ).json()
    npp_candidate = election_it_director_client.post(
        f"/api/v1/elections/{election['id']}/candidates/",
        {"name": "NPP Flagbearer", "position": "President", "party": "NPP"},
        format="json",
    ).json()
    independent = election_it_director_client.post(
        f"/api/v1/elections/{election['id']}/candidates/",
        {
            "name": "Independent Candidate",
            "position": "President",
            "party": "Independent",
        },
        format="json",
    ).json()

    client, _ = _make_branch_executive(branch_unit)
    client.post(
        "/api/v1/elections/results/",
        {
            "election_id": election["id"],
            "branch_unit_id": str(branch_unit.id),
            "position": "President",
            "collation_sheet_photo_base64": _FAKE_PHOTO,
            "tallies": [
                {"candidate_id": ndc_candidate["id"], "votes": 60},
                {"candidate_id": npp_candidate["id"], "votes": 35},
                {"candidate_id": independent["id"], "votes": 5},
            ],
        },
        format="json",
    )

    response = election_it_director_client.get(
        f"/api/v1/elections/{election['id']}/results/summary/"
        f"?organizational_unit_id={national_unit.id}&position=President"
    )
    body = response.json()
    party_votes = {p["party"]: p["votes"] for p in body["party_results"]}
    assert party_votes == {"NDC": 60, "NPP": 35, "Independent": 5}
    assert body["leading_candidate"]["party"] == "NDC"


def test_parliamentary_race_is_independent_per_constituency(
    election_it_director_client, national_unit, branch_unit
):
    """Both presidential and parliamentary candidates: parliamentary races
    are scoped per-constituency via distinct `position` values."""
    start, end = _window()
    election = election_it_director_client.post(
        "/api/v1/elections/",
        {
            "title": "2028 General Election",
            "election_type": "NATIONAL_GENERAL",
            "scope_unit_id": str(national_unit.id),
            "start_date": start,
            "end_date": end,
        },
        format="json",
    ).json()

    mp_position = "MP - Kumasi Central"
    ndc_mp = election_it_director_client.post(
        f"/api/v1/elections/{election['id']}/candidates/",
        {"name": "NDC MP Candidate", "position": mp_position, "party": "NDC"},
        format="json",
    ).json()
    npp_mp = election_it_director_client.post(
        f"/api/v1/elections/{election['id']}/candidates/",
        {"name": "NPP MP Candidate", "position": mp_position, "party": "NPP"},
        format="json",
    ).json()

    client, _ = _make_branch_executive(branch_unit)
    client.post(
        "/api/v1/elections/results/",
        {
            "election_id": election["id"],
            "branch_unit_id": str(branch_unit.id),
            "position": mp_position,
            "collation_sheet_photo_base64": _FAKE_PHOTO,
            "tallies": [
                {"candidate_id": ndc_mp["id"], "votes": 40},
                {"candidate_id": npp_mp["id"], "votes": 38},
            ],
        },
        format="json",
    )

    response = election_it_director_client.get(
        f"/api/v1/elections/{election['id']}/results/summary/"
        f"?organizational_unit_id={national_unit.id}&position={mp_position}"
    )
    assert response.json()["leading_candidate"]["candidate_name"] == "NDC MP Candidate"


# ---------------------------------------------------------------------------
# Direct digital voting for internal party elections
# ---------------------------------------------------------------------------


def test_director_can_select_electorate_and_voters_are_notified(
    election_it_director_client, election_with_candidates, member_user
):
    election, _, _ = election_with_candidates
    response = election_it_director_client.post(
        f"/api/v1/elections/{election['id']}/voters/",
        {"user_ids": [str(member_user.id)]},
        format="json",
    )
    assert response.status_code == 201
    assert len(response.json()) == 1


def test_added_voter_receives_notification(
    election_it_director_client, auth_client, election_with_candidates, member_user
):
    election, _, _ = election_with_candidates
    election_it_director_client.post(
        f"/api/v1/elections/{election['id']}/voters/",
        {"user_ids": [str(member_user.id)]},
        format="json",
    )
    notifications = auth_client.get("/api/v1/messaging/notifications/")
    assert any(
        n["notification_type"] == "ELECTION_ELIGIBILITY"
        for n in notifications.json()["results"]
    )


def test_unauthorized_user_cannot_select_electorate(
    auth_client, election_with_candidates, member_user
):
    election, _, _ = election_with_candidates
    response = auth_client.post(
        f"/api/v1/elections/{election['id']}/voters/",
        {"user_ids": [str(member_user.id)]},
        format="json",
    )
    assert response.status_code == 403


def test_eligible_voter_can_check_own_status(
    election_it_director_client, auth_client, election_with_candidates, member_user
):
    election, _, _ = election_with_candidates
    election_it_director_client.post(
        f"/api/v1/elections/{election['id']}/voters/",
        {"user_ids": [str(member_user.id)]},
        format="json",
    )
    response = auth_client.get(f"/api/v1/elections/{election['id']}/my-eligibility/")
    assert response.status_code == 200
    assert response.json()["eligible"] is True


def test_ineligible_member_sees_not_eligible(auth_client, election_with_candidates):
    election, _, _ = election_with_candidates
    response = auth_client.get(f"/api/v1/elections/{election['id']}/my-eligibility/")
    assert response.json()["eligible"] is False


def test_eligible_voter_can_cast_vote_when_election_open(
    election_it_director_client, auth_client, election_with_candidates, member_user
):
    election, candidate_a, _ = election_with_candidates
    election_it_director_client.post(
        f"/api/v1/elections/{election['id']}/voters/",
        {"user_ids": [str(member_user.id)]},
        format="json",
    )
    election_it_director_client.patch(
        f"/api/v1/elections/{election['id']}/", {"status": "OPEN"}, format="json"
    )

    response = auth_client.post(
        f"/api/v1/elections/{election['id']}/vote/",
        {"candidate_id": candidate_a["id"]},
        format="json",
    )
    assert response.status_code == 201


def test_cannot_vote_when_election_not_open(
    election_it_director_client, auth_client, election_with_candidates, member_user
):
    election, candidate_a, _ = election_with_candidates
    election_it_director_client.post(
        f"/api/v1/elections/{election['id']}/voters/",
        {"user_ids": [str(member_user.id)]},
        format="json",
    )
    # Still DRAFT - never opened.
    response = auth_client.post(
        f"/api/v1/elections/{election['id']}/vote/",
        {"candidate_id": candidate_a["id"]},
        format="json",
    )
    assert response.status_code == 400


def test_ineligible_member_cannot_vote(auth_client, election_with_candidates):
    election, candidate_a, _ = election_with_candidates
    response = auth_client.post(
        f"/api/v1/elections/{election['id']}/vote/",
        {"candidate_id": candidate_a["id"]},
        format="json",
    )
    assert response.status_code == 403


def test_cannot_vote_twice_in_same_race(
    election_it_director_client, auth_client, election_with_candidates, member_user
):
    election, candidate_a, candidate_b = election_with_candidates
    election_it_director_client.post(
        f"/api/v1/elections/{election['id']}/voters/",
        {"user_ids": [str(member_user.id)]},
        format="json",
    )
    election_it_director_client.patch(
        f"/api/v1/elections/{election['id']}/", {"status": "OPEN"}, format="json"
    )

    first = auth_client.post(
        f"/api/v1/elections/{election['id']}/vote/",
        {"candidate_id": candidate_a["id"]},
        format="json",
    )
    assert first.status_code == 201
    second = auth_client.post(
        f"/api/v1/elections/{election['id']}/vote/",
        {"candidate_id": candidate_b["id"]},
        format="json",
    )
    assert second.status_code == 409


def test_direct_voting_results_show_in_summary(
    election_it_director_client,
    auth_client,
    election_with_candidates,
    member_user,
    national_unit,
):
    election, candidate_a, candidate_b = election_with_candidates
    election_it_director_client.post(
        f"/api/v1/elections/{election['id']}/voters/",
        {"user_ids": [str(member_user.id)]},
        format="json",
    )
    election_it_director_client.patch(
        f"/api/v1/elections/{election['id']}/", {"status": "OPEN"}, format="json"
    )
    auth_client.post(
        f"/api/v1/elections/{election['id']}/vote/",
        {"candidate_id": candidate_a["id"]},
        format="json",
    )

    response = election_it_director_client.get(
        f"/api/v1/elections/{election['id']}/results/summary/?organizational_unit_id={national_unit.id}"
    )
    body = response.json()
    assert body["mode"] == "DIRECT_VOTING"
    assert body["total_votes_cast"] == 1
    assert body["eligible_voters_count"] == 1
    assert body["turnout_percentage"] == 100.0


def test_director_can_revoke_eligibility(
    election_it_director_client, election_with_candidates, member_user
):
    election, _, _ = election_with_candidates
    election_it_director_client.post(
        f"/api/v1/elections/{election['id']}/voters/",
        {"user_ids": [str(member_user.id)]},
        format="json",
    )
    response = election_it_director_client.delete(
        f"/api/v1/elections/{election['id']}/voters/{member_user.id}/"
    )
    assert response.status_code == 204


# ---------------------------------------------------------------------------
# Centralized election authority: only Election/IT Director organizes,
# but Chairman/Secretary retain real transparency into live results.
# ---------------------------------------------------------------------------


def test_national_chairman_can_no_longer_organize_an_election(
    chairman_client, national_unit
):
    """The actual fix: election-organizing authority is now centralized
    exclusively to the Election/IT Director roles - not even the
    National Chairman can create an election anymore."""
    start, end = _window()
    response = chairman_client.post(
        "/api/v1/elections/",
        {
            "title": "Should Be Rejected",
            "election_type": "PARTY_INTERNAL",
            "scope_unit_id": str(national_unit.id),
            "start_date": start,
            "end_date": end,
        },
        format="json",
    )
    assert response.status_code == 403


def test_national_chairman_can_still_see_live_results_before_completion(
    election_with_candidates, branch_unit, national_unit, chairman_client
):
    """The transparency half of the fix: the Chairman lost organizing
    authority above, but must still be able to watch an election in
    progress - real oversight, not blindness."""
    election, candidate_a, _ = election_with_candidates
    client, _ = _make_branch_executive(branch_unit)
    client.post(
        "/api/v1/elections/results/",
        {
            "election_id": election["id"],
            "branch_unit_id": str(branch_unit.id),
            "collation_sheet_photo_base64": _FAKE_PHOTO,
            "tallies": [{"candidate_id": candidate_a["id"], "votes": 10}],
        },
        format="json",
    )

    response = chairman_client.get(
        f"/api/v1/elections/{election['id']}/results/summary/?organizational_unit_id={national_unit.id}"
    )
    assert response.status_code == 200


def test_ordinary_member_blocked_from_live_results_before_completion(
    election_with_candidates, branch_unit, national_unit, auth_client
):
    """The publication half of the fix: an ordinary member must not be
    able to see live, unverified, in-progress results - only once the
    election is actually completed."""
    election, candidate_a, _ = election_with_candidates
    client, _ = _make_branch_executive(branch_unit)
    client.post(
        "/api/v1/elections/results/",
        {
            "election_id": election["id"],
            "branch_unit_id": str(branch_unit.id),
            "collation_sheet_photo_base64": _FAKE_PHOTO,
            "tallies": [{"candidate_id": candidate_a["id"], "votes": 10}],
        },
        format="json",
    )

    response = auth_client.get(
        f"/api/v1/elections/{election['id']}/results/summary/?organizational_unit_id={national_unit.id}"
    )
    assert response.status_code == 403


def test_ordinary_member_can_see_results_once_election_is_completed(
    election_with_candidates,
    branch_unit,
    national_unit,
    auth_client,
    election_it_director_client,
):
    """Once the election is actually COMPLETED, results are published -
    any authenticated member can see them, not just organizers/oversight."""
    from apps.elections.documents import Election

    election, candidate_a, _ = election_with_candidates
    client, _ = _make_branch_executive(branch_unit)
    client.post(
        "/api/v1/elections/results/",
        {
            "election_id": election["id"],
            "branch_unit_id": str(branch_unit.id),
            "collation_sheet_photo_base64": _FAKE_PHOTO,
            "tallies": [{"candidate_id": candidate_a["id"], "votes": 10}],
        },
        format="json",
    )

    Election.objects.filter(id=election["id"]).update(status="COMPLETED")

    response = auth_client.get(
        f"/api/v1/elections/{election['id']}/results/summary/?organizational_unit_id={national_unit.id}"
    )
    assert response.status_code == 200


def test_secretary_without_hierarchy_manage_can_still_see_live_results(
    election_with_candidates, branch_unit, national_unit
):
    """Secretary deliberately does not carry hierarchy.manage (see
    apps/dashboard/role_insights.py), so without an explicit role-code
    carve-out in can_view_election_progress, the Secretary would have
    no way to watch an election either - confirms the carve-out
    actually works for a genuine Secretary account, not just Chairman."""
    from apps.accounts.authentication import issue_token_pair
    from apps.accounts.documents import Role, User
    from rest_framework.test import APIClient

    election, candidate_a, _ = election_with_candidates
    client, _ = _make_branch_executive(branch_unit)
    client.post(
        "/api/v1/elections/results/",
        {
            "election_id": election["id"],
            "branch_unit_id": str(branch_unit.id),
            "collation_sheet_photo_base64": _FAKE_PHOTO,
            "tallies": [{"candidate_id": candidate_a["id"], "votes": 10}],
        },
        format="json",
    )

    role = Role.objects.create(
        name="National General Secretary",
        code="national_general_secretary",
        scope="NATIONAL",
        is_executive=True,
        permissions=["hierarchy.manage", "messaging.broadcast.downward"],
    )
    role.permissions = ["messaging.broadcast.downward"]  # confirm no hierarchy.manage
    role.save()
    secretary = User(
        email="secretary-election-test@example.com",
        phone_number="0244000082",
        first_name="Test",
        last_name="Secretary",
        membership_id="NDC-TEST-000082",
        organizational_unit=national_unit,
        role=role,
    )
    secretary.set_password("StrongPass123!")
    secretary.save()

    tokens = issue_token_pair(secretary)
    secretary_client = APIClient()
    secretary_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

    response = secretary_client.get(
        f"/api/v1/elections/{election['id']}/results/summary/?organizational_unit_id={national_unit.id}"
    )
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# Supreme Court ruling: presidential/parliamentary primaries are open to
# every active member - no curated electorate involved.
# ---------------------------------------------------------------------------


def test_any_active_member_is_automatically_eligible_for_presidential_primary(
    election_it_director_client, national_unit, member_user
):
    """The actual ruling: no EligibleVoter selection needed at all - every
    active member is eligible the moment the election exists."""
    start, end = _window()
    election = election_it_director_client.post(
        "/api/v1/elections/",
        {
            "title": "2028 Presidential Primary",
            "election_type": "PRESIDENTIAL_PRIMARY",
            "scope_unit_id": str(national_unit.id),
            "start_date": start,
            "end_date": end,
        },
        format="json",
    ).json()

    from apps.accounts.authentication import issue_token_pair
    from rest_framework.test import APIClient

    tokens = issue_token_pair(member_user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

    response = client.get(f"/api/v1/elections/{election['id']}/my-eligibility/")
    assert response.status_code == 200
    assert response.json()["eligible"] is True


def test_inactive_member_is_not_eligible_for_presidential_primary(
    election_it_director_client, national_unit, member_user
):
    """Note: an inactive member actually can't even authenticate at all
    (the auth layer itself rejects them with 401 before any view logic
    runs), so this checks is_eligible_voter directly rather than via a
    real request - the is_active check inside it is still real defense
    in depth, not dead code, for any path that reaches it."""
    from apps.elections.documents import Election
    from apps.elections.permissions import is_eligible_voter

    member_user.is_active = False
    member_user.save()

    start, end = _window()
    election = election_it_director_client.post(
        "/api/v1/elections/",
        {
            "title": "2028 Presidential Primary",
            "election_type": "PRESIDENTIAL_PRIMARY",
            "scope_unit_id": str(national_unit.id),
            "start_date": start,
            "end_date": end,
        },
        format="json",
    ).json()

    election_doc = Election.objects.get(id=election["id"])
    assert is_eligible_voter(member_user, election_doc) is False


def test_member_outside_the_constituency_cannot_vote_in_its_parliamentary_primary(
    election_it_director_client, national_unit, constituency_unit, member_user
):
    """The scoping half of the ruling: a parliamentary primary is open
    to every active member of THAT constituency, not the whole party -
    a member registered elsewhere must not be eligible."""
    from apps.hierarchy.documents import OrganizationalUnit

    other_constituency = OrganizationalUnit.objects.create(
        name="Other Constituency",
        code="ndc-other-constituency-primary-test",
        unit_type="CONSTITUENCY",
        parent=constituency_unit.parent,
    )
    member_user.organizational_unit = other_constituency
    member_user.save()

    start, end = _window()
    election = election_it_director_client.post(
        "/api/v1/elections/",
        {
            "title": "Kumasi Central Parliamentary Primary",
            "election_type": "PARLIAMENTARY_PRIMARY",
            "scope_unit_id": str(constituency_unit.id),
            "start_date": start,
            "end_date": end,
        },
        format="json",
    ).json()

    from apps.accounts.authentication import issue_token_pair
    from rest_framework.test import APIClient

    tokens = issue_token_pair(member_user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

    response = client.get(f"/api/v1/elections/{election['id']}/my-eligibility/")
    assert response.status_code == 200
    assert response.json()["eligible"] is False


def test_it_director_cannot_curate_electorate_for_a_mandatory_open_primary(
    election_it_director_client, national_unit
):
    start, end = _window()
    election = election_it_director_client.post(
        "/api/v1/elections/",
        {
            "title": "2028 Presidential Primary",
            "election_type": "PRESIDENTIAL_PRIMARY",
            "scope_unit_id": str(national_unit.id),
            "start_date": start,
            "end_date": end,
        },
        format="json",
    ).json()

    response = election_it_director_client.post(
        f"/api/v1/elections/{election['id']}/voters/",
        {"user_ids": []},
        format="json",
    )
    assert response.status_code == 400


def test_presidential_primary_turnout_reflects_real_active_membership_not_zero(
    election_it_director_client, national_unit, member_user
):
    """Confirms the real fix in aggregate_results: eligible_voters_count
    for a mandatory-open primary comes from actual active membership,
    not the empty EligibleVoter table - otherwise turnout would always
    show as unavailable despite real votes being cast."""
    start, end = _window()
    election = election_it_director_client.post(
        "/api/v1/elections/",
        {
            "title": "2028 Presidential Primary",
            "election_type": "PRESIDENTIAL_PRIMARY",
            "scope_unit_id": str(national_unit.id),
            "start_date": start,
            "end_date": end,
        },
        format="json",
    ).json()
    candidate = election_it_director_client.post(
        f"/api/v1/elections/{election['id']}/candidates/",
        {"name": "Primary Candidate"},
        format="json",
    ).json()
    election_it_director_client.patch(
        f"/api/v1/elections/{election['id']}/", {"status": "OPEN"}, format="json"
    )

    from apps.accounts.authentication import issue_token_pair
    from rest_framework.test import APIClient

    tokens = issue_token_pair(member_user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    client.post(
        f"/api/v1/elections/{election['id']}/vote/",
        {"candidate_id": candidate["id"]},
        format="json",
    )

    response = election_it_director_client.get(
        f"/api/v1/elections/{election['id']}/results/summary/?organizational_unit_id={national_unit.id}"
    )
    body = response.json()
    assert body["eligible_voters_count"] >= 1
    assert body["total_votes_cast"] == 1
    assert body["turnout_percentage"] is not None


# ---------------------------------------------------------------------------
# Department-requests-an-election workflow
# ---------------------------------------------------------------------------


def test_chairman_can_request_an_election_but_not_organize_one(
    chairman_client, national_unit
):
    """The whole point of this workflow: the Chairman lost organizing
    authority, but must still have a real way to get an election
    organized - a formal request to the Election/IT Director."""
    response = chairman_client.post(
        "/api/v1/elections/requests/",
        {
            "target_unit_id": str(national_unit.id),
            "election_type": "PARTY_INTERNAL",
            "title": "NEC Officer Election",
            "reason": "Current term has expired.",
        },
        format="json",
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "PENDING"
    assert body["title"] == "NEC Officer Election"


def test_ordinary_member_cannot_request_an_election(auth_client, national_unit):
    """Deliberately not open to everyone - a genuine executive, not any
    member submitting requests on a whim."""
    response = auth_client.post(
        "/api/v1/elections/requests/",
        {
            "target_unit_id": str(national_unit.id),
            "election_type": "PARTY_INTERNAL",
            "title": "Should Be Rejected",
            "reason": "No real reason.",
        },
        format="json",
    )
    assert response.status_code == 403


def test_department_head_without_hierarchy_manage_can_request_an_election(
    national_unit, communications_department
):
    """Confirms the department-authority path works too, not just
    hierarchy.manage - a real Communications Director (no broad
    jurisdiction authority) can still ask."""
    from apps.accounts.authentication import issue_token_pair
    from apps.accounts.documents import Role, User
    from apps.departments.documents import DepartmentAssignment
    from rest_framework.test import APIClient

    role = Role.objects.create(
        name="Communications Director",
        code="communications_director_election_request_test",
        scope="NATIONAL",
        is_executive=True,
        permissions=["messaging.broadcast.downward"],
    )
    director = User(
        email="comms-election-request-test@example.com",
        phone_number="0244000081",
        first_name="Test",
        last_name="Director",
        membership_id="NDC-TEST-000081",
        organizational_unit=national_unit,
        role=role,
    )
    director.set_password("StrongPass123!")
    director.save()
    DepartmentAssignment.objects.create(
        user=director,
        department=communications_department,
        organizational_unit=national_unit,
        position="HEAD",
    )

    client = APIClient()
    tokens = issue_token_pair(director)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

    response = client.post(
        "/api/v1/elections/requests/",
        {
            "target_unit_id": str(national_unit.id),
            "election_type": "POLL",
            "title": "Membership Sentiment Poll",
            "reason": "Want direct member feedback before Congress.",
        },
        format="json",
    )
    assert response.status_code == 201


def test_election_it_director_sees_and_approves_pending_requests(
    election_it_director_client, chairman_client, national_unit
):
    request_response = chairman_client.post(
        "/api/v1/elections/requests/",
        {
            "target_unit_id": str(national_unit.id),
            "election_type": "PARTY_INTERNAL",
            "title": "NEC Officer Election",
            "reason": "Term expired.",
        },
        format="json",
    ).json()

    list_response = election_it_director_client.get(
        f"/api/v1/elections/requests/?target_unit_id={national_unit.id}"
    )
    assert list_response.status_code == 200
    assert any(
        r["id"] == request_response["id"] for r in list_response.json()["results"]
    )

    approve_response = election_it_director_client.patch(
        f"/api/v1/elections/requests/{request_response['id']}/",
        {"status": "APPROVED", "notes": "Approved - will schedule next week."},
        format="json",
    )
    assert approve_response.status_code == 200
    assert approve_response.json()["status"] == "APPROVED"


def test_chairman_cannot_approve_their_own_request(chairman_client, national_unit):
    """Confirms the review step is genuinely restricted to the
    Election/IT Director - the requester cannot self-approve."""
    request_response = chairman_client.post(
        "/api/v1/elections/requests/",
        {
            "target_unit_id": str(national_unit.id),
            "election_type": "PARTY_INTERNAL",
            "title": "NEC Officer Election",
            "reason": "Term expired.",
        },
        format="json",
    ).json()

    response = chairman_client.patch(
        f"/api/v1/elections/requests/{request_response['id']}/",
        {"status": "APPROVED"},
        format="json",
    )
    assert response.status_code == 403


def test_approved_request_is_fulfilled_when_the_election_is_actually_created(
    election_it_director_client, chairman_client, national_unit
):
    """The real end-to-end link: once approved, organizing the actual
    election with fulfills_request_id moves the request to FULFILLED
    and links it to the real election - the requester can see it
    actually happened, not just that it was approved in principle."""
    request_response = chairman_client.post(
        "/api/v1/elections/requests/",
        {
            "target_unit_id": str(national_unit.id),
            "election_type": "PARTY_INTERNAL",
            "title": "NEC Officer Election",
            "reason": "Term expired.",
        },
        format="json",
    ).json()
    election_it_director_client.patch(
        f"/api/v1/elections/requests/{request_response['id']}/",
        {"status": "APPROVED"},
        format="json",
    )

    start, end = _window()
    election = election_it_director_client.post(
        "/api/v1/elections/",
        {
            "title": "NEC Officer Election",
            "election_type": "PARTY_INTERNAL",
            "scope_unit_id": str(national_unit.id),
            "start_date": start,
            "end_date": end,
            "fulfills_request_id": request_response["id"],
        },
        format="json",
    ).json()

    detail_response = election_it_director_client.get(
        f"/api/v1/elections/requests/{request_response['id']}/"
    )
    body = detail_response.json()
    assert body["status"] == "FULFILLED"
    assert body["fulfilled_election_id"] == election["id"]


def test_cannot_fulfill_a_request_that_was_never_approved(
    election_it_director_client, chairman_client, national_unit
):
    request_response = chairman_client.post(
        "/api/v1/elections/requests/",
        {
            "target_unit_id": str(national_unit.id),
            "election_type": "PARTY_INTERNAL",
            "title": "NEC Officer Election",
            "reason": "Term expired.",
        },
        format="json",
    ).json()

    start, end = _window()
    response = election_it_director_client.post(
        "/api/v1/elections/",
        {
            "title": "NEC Officer Election",
            "election_type": "PARTY_INTERNAL",
            "scope_unit_id": str(national_unit.id),
            "start_date": start,
            "end_date": end,
            "fulfills_request_id": request_response["id"],
        },
        format="json",
    )
    assert response.status_code == 400
