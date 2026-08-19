from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.django_db


def _make_complaint(user, unit, subject="Bad road conditions"):
    from apps.complaints.documents import Complaint

    return Complaint.objects.create(
        submitted_by=user,
        submitting_unit=unit,
        target_unit=unit,
        complaint_type="COMPLAINT",
        subject=subject,
        description="The main road to the branch office has been unusable for months.",
    )


def test_ground_intelligence_returns_real_complaint_data(
    chairman_client, member_user, branch_unit, national_unit
):
    _make_complaint(member_user, branch_unit)

    response = chairman_client.get(
        f"/api/v1/analytics/ground-intelligence/{national_unit.id}/"
    )
    assert response.status_code == 200
    body = response.json()
    assert body["counts"]["pending_complaints"] == 1
    assert body["recent_complaints"][0]["subject"] == "Bad road conditions"
    assert "unusable for months" in body["recent_complaints"][0]["description"]


def test_ground_intelligence_forbidden_for_ordinary_member(auth_client, national_unit):
    response = auth_client.get(
        f"/api/v1/analytics/ground-intelligence/{national_unit.id}/"
    )
    assert response.status_code == 403


def test_regular_executive_gets_scoped_ground_intelligence_within_their_own_jurisdiction(
    national_unit, regional_unit
):
    """The new tiered behavior: any real executive (hierarchy.manage),
    not just top leadership, can now use Ground Intelligence - but only
    for a unit within their own jurisdiction. A Regional Chairman over
    regional_unit can access it (and national_unit is not tested here
    since it's an ancestor, not their own jurisdiction - see the
    denial test below for a genuinely out-of-jurisdiction unit)."""
    from apps.accounts.authentication import issue_token_pair
    from apps.accounts.documents import Role, User
    from rest_framework.test import APIClient

    role = Role.objects.create(
        name="Regional Chairman",
        code="regional_chairman_scoped_test",
        scope="REGIONAL",
        is_executive=True,
        permissions=["hierarchy.manage", "finance.manage"],
    )
    user = User(
        email="regional-scoped@example.com",
        phone_number="0244000099",
        first_name="Test",
        last_name="Regional",
        membership_id="NDC-TEST-000099",
        organizational_unit=regional_unit,
        role=role,
    )
    user.set_password("StrongPass123!")
    user.save()

    client = APIClient()
    tokens = issue_token_pair(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

    response = client.get(f"/api/v1/analytics/ground-intelligence/{regional_unit.id}/")
    assert response.status_code == 200


def test_regular_executive_still_blocked_from_a_unit_outside_their_own_jurisdiction(
    national_unit, regional_unit
):
    """The other half of the tiered design: scoped access is a real
    boundary, not just a label - a Regional Chairman over one region
    must not reach a sibling region they have no authority over."""
    from apps.accounts.authentication import issue_token_pair
    from apps.accounts.documents import Role, User
    from apps.hierarchy.documents import OrganizationalUnit
    from rest_framework.test import APIClient

    other_region = OrganizationalUnit.objects.create(
        name="Other Region",
        code="ndc-other-region",
        unit_type="REGIONAL",
        parent=national_unit,
    )

    role = Role.objects.create(
        name="Regional Chairman",
        code="regional_chairman_outside_test",
        scope="REGIONAL",
        is_executive=True,
        permissions=["hierarchy.manage", "finance.manage"],
    )
    user = User(
        email="regional-outside@example.com",
        phone_number="0244000098",
        first_name="Test",
        last_name="Outside",
        membership_id="NDC-TEST-000098",
        organizational_unit=regional_unit,
        role=role,
    )
    user.set_password("StrongPass123!")
    user.save()

    client = APIClient()
    tokens = issue_token_pair(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

    response = client.get(f"/api/v1/analytics/ground-intelligence/{other_region.id}/")
    assert response.status_code == 403


def test_ordinary_member_still_forbidden_from_ground_intelligence_entirely(
    auth_client, national_unit
):
    """The floor of the tiered design: someone with no hierarchy.manage
    at all still gets nothing, regardless of unit."""
    response = auth_client.get(
        f"/api/v1/analytics/ground-intelligence/{national_unit.id}/"
    )
    assert response.status_code == 403


@patch("requests.post")
def test_ground_briefing_uses_real_server_side_data_not_client_input(
    mock_post, settings, chairman_client, member_user, branch_unit, national_unit
):
    """The briefing endpoint must fetch real data itself - confirmed here
    by creating a real complaint and checking its actual content reaches
    the AI call, without the client ever sending it."""
    settings.ANTHROPIC_API_KEY = "sk-ant-test"
    _make_complaint(member_user, branch_unit, subject="Water shortage in the district")

    mock_response = MagicMock()
    mock_response.raise_for_status = lambda: None
    mock_response.json.return_value = {
        "content": [{"type": "text", "text": "Water shortage needs urgent attention."}]
    }
    mock_post.return_value = mock_response

    response = chairman_client.post(
        f"/api/v1/executive-ai/ground-briefing/{national_unit.id}/"
    )
    assert response.status_code == 200
    assert "Water shortage" in response.json()["briefing"]

    # Confirm the real complaint text was actually sent to the model,
    # not fabricated or omitted.
    sent_payload = mock_post.call_args.kwargs["json"]
    sent_text = str(sent_payload)
    assert "unusable for months" in sent_text


def test_ground_briefing_forbidden_for_ordinary_member(
    settings, auth_client, national_unit
):
    settings.ANTHROPIC_API_KEY = "sk-ant-test"
    response = auth_client.post(
        f"/api/v1/executive-ai/ground-briefing/{national_unit.id}/"
    )
    assert response.status_code == 403


@patch("requests.post")
def test_official_report_without_names_never_sends_reporter_identity_to_the_model(
    mock_post, settings, chairman_client, member_user, branch_unit, national_unit
):
    """The core safety property: with include_names=false, the reporter's
    real name must never appear in what is actually sent to the AI
    provider - not just asked to be omitted from the output."""
    settings.ANTHROPIC_API_KEY = "sk-ant-test"
    _make_complaint(member_user, branch_unit, subject="Sensitive matter")

    mock_response = MagicMock()
    mock_response.raise_for_status = lambda: None
    mock_response.json.return_value = {
        "content": [{"type": "text", "text": "Official report body."}]
    }
    mock_post.return_value = mock_response

    response = chairman_client.post(
        f"/api/v1/executive-ai/official-report/{national_unit.id}/?include_names=false"
    )
    assert response.status_code == 200
    sent_payload = str(mock_post.call_args.kwargs["json"])
    assert member_user.full_name not in sent_payload


@patch("requests.post")
def test_top_leadership_tier_gets_the_names_included_report(
    mock_post, settings, national_unit
):
    """can_view_ground_intelligence and can_reveal_reporter_identity are
    deliberately the same authority tier by design (see both functions'
    docstrings) - this confirms a user holding it gets the
    include_names=true variant, not blocked by a second, redundant
    check."""
    from apps.accounts.authentication import issue_token_pair
    from apps.accounts.documents import Role, User
    from rest_framework.test import APIClient

    settings.ANTHROPIC_API_KEY = "sk-ant-test"
    role = Role.objects.create(
        name="Ground Intelligence Tier",
        code="ground_intel_tier_test",
        scope="NATIONAL",
        is_executive=True,
        permissions=["analytics.ground_intelligence"],
    )
    user = User(
        email="gi-only@example.com",
        phone_number="0244000091",
        first_name="Gi",
        last_name="Only",
        membership_id="NDC-TEST-000091",
        organizational_unit=national_unit,
        role=role,
    )
    user.set_password("StrongPass123!")
    user.save()
    tokens = issue_token_pair(user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

    mock_response = MagicMock()
    mock_response.raise_for_status = lambda: None
    mock_response.json.return_value = {"content": [{"type": "text", "text": "Report."}]}
    mock_post.return_value = mock_response

    response = client.post(
        f"/api/v1/executive-ai/official-report/{national_unit.id}/?include_names=true"
    )
    assert response.status_code == 200
    assert response.json()["include_names"] is True


def test_official_report_forbidden_for_ordinary_member(
    settings, auth_client, national_unit
):
    settings.ANTHROPIC_API_KEY = "sk-ant-test"
    response = auth_client.post(
        f"/api/v1/executive-ai/official-report/{national_unit.id}/?include_names=false"
    )
    assert response.status_code == 403


@patch("requests.post")
def test_speech_never_includes_reporter_names_regardless_of_style(
    mock_post, settings, chairman_client, member_user, branch_unit, national_unit
):
    settings.ANTHROPIC_API_KEY = "sk-ant-test"
    _make_complaint(member_user, branch_unit, subject="Road repair needed")

    mock_response = MagicMock()
    mock_response.raise_for_status = lambda: None
    mock_response.json.return_value = {
        "content": [{"type": "text", "text": "Speech text."}]
    }
    mock_post.return_value = mock_response

    response = chairman_client.post(
        f"/api/v1/executive-ai/speech/{national_unit.id}/",
        {"style_instructions": "Bold and energetic, rally style."},
        format="json",
    )
    assert response.status_code == 200
    sent_payload = str(mock_post.call_args.kwargs["json"])
    assert member_user.full_name not in sent_payload
    assert "Bold and energetic" in sent_payload
