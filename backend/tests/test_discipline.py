import pytest

pytestmark = pytest.mark.django_db


def _default_role():
    from apps.accounts.documents import Role

    role = Role.objects(code="discipline_test_ordinary_member").first()
    if role is None:
        role = Role.objects.create(
            name="Ordinary Member (discipline tests)",
            code="discipline_test_ordinary_member",
            scope="BRANCH",
            is_executive=False,
            permissions=["profile.manage_own"],
        )
    return role


def _make_member(email, membership_id, unit, role_override=None):
    from apps.accounts.documents import User

    # 0209 prefix avoids colliding with conftest's own fixture phone
    # numbers (member_user/national_chairman_user use 0244000001/000002).
    digits = "".join(ch for ch in membership_id if ch.isdigit())[-6:]
    user = User(
        email=email,
        phone_number="0209" + digits.zfill(6),
        first_name="Test",
        last_name=email.split("@")[0],
        membership_id=membership_id,
        organizational_unit=unit,
        role=role_override or _default_role(),
    )
    user.set_password("StrongPass123!")
    user.save()
    return user


def _client_for(user):
    from apps.accounts.authentication import issue_token_pair
    from rest_framework.test import APIClient

    client = APIClient()
    tokens = issue_token_pair(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    return client


def test_chairman_can_elect_a_three_member_committee(chairman_client, national_unit):
    from apps.discipline.documents import DisciplinaryCommittee

    m1 = _make_member("dc1@example.com", "NDC-DC-000001", national_unit)
    m2 = _make_member("dc2@example.com", "NDC-DC-000002", national_unit)
    m3 = _make_member("dc3@example.com", "NDC-DC-000003", national_unit)

    response = chairman_client.post(
        "/api/v1/discipline/committees/",
        {
            "organizational_unit_id": str(national_unit.id),
            "member_ids": [str(m1.id), str(m2.id), str(m3.id)],
        },
        format="json",
    )
    assert response.status_code == 201
    assert len(response.data["members"]) == 3
    assert DisciplinaryCommittee.objects.count() == 1


def test_committee_rejects_wrong_member_count(chairman_client, national_unit):
    m1 = _make_member("dc4@example.com", "NDC-DC-000004", national_unit)
    response = chairman_client.post(
        "/api/v1/discipline/committees/",
        {"organizational_unit_id": str(national_unit.id), "member_ids": [str(m1.id)]},
        format="json",
    )
    assert response.status_code == 400
    assert response.data["error"]["code"] == "invalid_input"


def test_committee_rejects_an_executive_of_that_unit(
    chairman_client, national_unit, national_chairman_role
):
    executive = _make_member(
        "exec@example.com",
        "NDC-DC-000005",
        national_unit,
        role_override=national_chairman_role,
    )
    m2 = _make_member("dc6@example.com", "NDC-DC-000006", national_unit)
    m3 = _make_member("dc7@example.com", "NDC-DC-000007", national_unit)

    response = chairman_client.post(
        "/api/v1/discipline/committees/",
        {
            "organizational_unit_id": str(national_unit.id),
            "member_ids": [str(executive.id), str(m2.id), str(m3.id)],
        },
        format="json",
    )
    assert response.status_code == 400
    assert "executive position" in response.data["error"]["message"]


def test_committee_cannot_be_elected_at_a_district_coordinating_committee(
    chairman_client,
):
    from apps.hierarchy.documents import OrganizationalUnit

    district = OrganizationalUnit.objects.create(
        name="Test District",
        code="ndc-test-district",
        unit_type="DISTRICT_COORDINATING_COMMITTEE",
    )
    m1 = _make_member("dc8@example.com", "NDC-DC-000008", district)
    m2 = _make_member("dc9@example.com", "NDC-DC-000009", district)
    m3 = _make_member("dc10@example.com", "NDC-DC-000010", district)

    response = chairman_client.post(
        "/api/v1/discipline/committees/",
        {
            "organizational_unit_id": str(district.id),
            "member_ids": [str(m1.id), str(m2.id), str(m3.id)],
        },
        format="json",
    )
    assert response.status_code == 400
    assert response.data["error"]["code"] == "invalid_level"


def test_ordinary_member_cannot_elect_a_committee(auth_client, national_unit):
    m1 = _make_member("dc11@example.com", "NDC-DC-000011", national_unit)
    m2 = _make_member("dc12@example.com", "NDC-DC-000012", national_unit)
    m3 = _make_member("dc13@example.com", "NDC-DC-000013", national_unit)

    response = auth_client.post(
        "/api/v1/discipline/committees/",
        {
            "organizational_unit_id": str(national_unit.id),
            "member_ids": [str(m1.id), str(m2.id), str(m3.id)],
        },
        format="json",
    )
    assert response.status_code == 403


@pytest.fixture
def elected_committee(chairman_client, national_unit):
    m1 = _make_member("comm1@example.com", "NDC-CM-100001", national_unit)
    m2 = _make_member("comm2@example.com", "NDC-CM-100002", national_unit)
    m3 = _make_member("comm3@example.com", "NDC-CM-100003", national_unit)
    chairman_client.post(
        "/api/v1/discipline/committees/",
        {
            "organizational_unit_id": str(national_unit.id),
            "member_ids": [str(m1.id), str(m2.id), str(m3.id)],
        },
        format="json",
    )
    return [m1, m2, m3]


def test_any_member_can_report_a_case_and_it_attaches_the_active_committee(
    auth_client, national_unit, member_user, elected_committee
):
    response = auth_client.post(
        "/api/v1/discipline/cases/",
        {
            "respondent_id": str(member_user.id),
            "organizational_unit_id": str(national_unit.id),
            "grounds": "ANTI_PARTY_CONDUCT",
            "description": "Public statements against the Party leadership.",
        },
        format="json",
    )
    assert response.status_code == 201
    assert response.data["status"] == "REPORTED"
    assert response.data["committee_id"] is not None


def test_full_case_lifecycle_convene_recommend_decide(
    national_unit, member_user, elected_committee
):
    from apps.discipline.documents import DisciplinaryCase

    reporter_client = _client_for(elected_committee[0])
    create_response = reporter_client.post(
        "/api/v1/discipline/cases/",
        {
            "respondent_id": str(member_user.id),
            "organizational_unit_id": str(national_unit.id),
            "grounds": "INSUBORDINATION",
            "description": "Refused to implement a lawful Party directive.",
        },
        format="json",
    )
    case_id = create_response.data["id"]

    outsider = _make_member("outsider@example.com", "NDC-OUT-000001", national_unit)
    outsider_client = _client_for(outsider)
    forbidden = outsider_client.post(f"/api/v1/discipline/cases/{case_id}/convene/")
    assert forbidden.status_code == 403

    committee_client = _client_for(elected_committee[1])
    convene_response = committee_client.post(
        f"/api/v1/discipline/cases/{case_id}/convene/"
    )
    assert convene_response.status_code == 200
    assert convene_response.data["status"] == "CONVENED"

    second_convene = committee_client.post(
        f"/api/v1/discipline/cases/{case_id}/convene/"
    )
    assert second_convene.status_code == 400

    recommend_response = committee_client.post(
        f"/api/v1/discipline/cases/{case_id}/recommend/",
        {
            "recommendation": "A reprimand is sufficient given the circumstances.",
            "recommended_measure": "REPRIMAND",
        },
        format="json",
    )
    assert recommend_response.status_code == 200
    assert recommend_response.data["status"] == "RECOMMENDED"

    case = DisciplinaryCase.objects.get(id=case_id)
    assert case.recommended_measure == "REPRIMAND"


def test_decide_requires_confirmation_to_vary_from_recommendation(
    chairman_client, national_unit, member_user, elected_committee
):
    reporter_client = _client_for(elected_committee[0])
    create_response = reporter_client.post(
        "/api/v1/discipline/cases/",
        {
            "respondent_id": str(member_user.id),
            "organizational_unit_id": str(national_unit.id),
            "grounds": "CONFIDENTIALITY_BREACH",
            "description": "Leaked internal NEC minutes to the press.",
        },
        format="json",
    )
    case_id = create_response.data["id"]
    committee_client = _client_for(elected_committee[1])
    committee_client.post(f"/api/v1/discipline/cases/{case_id}/convene/")
    committee_client.post(
        f"/api/v1/discipline/cases/{case_id}/recommend/",
        {"recommendation": "Reprimand only.", "recommended_measure": "REPRIMAND"},
        format="json",
    )

    unconfirmed = chairman_client.post(
        f"/api/v1/discipline/cases/{case_id}/decide/",
        {
            "final_decision": "The Executive Committee considers a suspension more appropriate.",
            "final_measure": "SUSPENSION",
        },
        format="json",
    )
    assert unconfirmed.status_code == 400
    assert unconfirmed.data["error"]["code"] == "confirmation_required"

    confirmed = chairman_client.post(
        f"/api/v1/discipline/cases/{case_id}/decide/",
        {
            "final_decision": "The Executive Committee considers a suspension more appropriate.",
            "final_measure": "SUSPENSION",
            "confirmed_two_thirds_majority": True,
        },
        format="json",
    )
    assert confirmed.status_code == 200
    assert confirmed.data["varied_from_recommendation"] is True
    assert confirmed.data["status"] == "DECIDED"


def test_appeal_creates_a_case_at_the_parent_unit(
    chairman_client, regional_unit, national_unit, elected_committee
):
    from apps.discipline.documents import DisciplinaryCase

    respondent = _make_member(
        "respondent@example.com", "NDC-RESP-000001", regional_unit
    )
    reporter_client = _client_for(elected_committee[0])

    r1 = _make_member("rcomm1@example.com", "NDC-RC-200001", regional_unit)
    r2 = _make_member("rcomm2@example.com", "NDC-RC-200002", regional_unit)
    r3 = _make_member("rcomm3@example.com", "NDC-RC-200003", regional_unit)
    chairman_client.post(
        "/api/v1/discipline/committees/",
        {
            "organizational_unit_id": str(regional_unit.id),
            "member_ids": [str(r1.id), str(r2.id), str(r3.id)],
        },
        format="json",
    )

    create_response = reporter_client.post(
        "/api/v1/discipline/cases/",
        {
            "respondent_id": str(respondent.id),
            "organizational_unit_id": str(regional_unit.id),
            "grounds": "OTHER",
            "description": "Conduct adversely affecting regional campaign strategy.",
        },
        format="json",
    )
    case_id = create_response.data["id"]

    r_committee_client = _client_for(r1)
    r_committee_client.post(f"/api/v1/discipline/cases/{case_id}/convene/")
    r_committee_client.post(
        f"/api/v1/discipline/cases/{case_id}/recommend/",
        {"recommendation": "Fine recommended.", "recommended_measure": "FINE"},
        format="json",
    )
    chairman_client.post(
        f"/api/v1/discipline/cases/{case_id}/decide/",
        {"final_decision": "Fine upheld.", "final_measure": "FINE"},
        format="json",
    )

    respondent_client = _client_for(respondent)
    appeal_response = respondent_client.post(
        f"/api/v1/discipline/cases/{case_id}/appeal/",
        {"grounds_for_appeal": "The fine is disproportionate to the conduct."},
        format="json",
    )
    assert appeal_response.status_code == 201
    assert appeal_response.data["organizational_unit"]["id"] == str(national_unit.id)
    assert appeal_response.data["parent_case_id"] == case_id

    original = DisciplinaryCase.objects.get(id=case_id)
    assert original.status == "APPEALED"


def test_appeal_blocked_at_national_level(
    chairman_client, national_unit, elected_committee
):
    reporter_client = _client_for(elected_committee[0])
    respondent = _make_member("resp2@example.com", "NDC-RESP-000002", national_unit)
    create_response = reporter_client.post(
        "/api/v1/discipline/cases/",
        {
            "respondent_id": str(respondent.id),
            "organizational_unit_id": str(national_unit.id),
            "grounds": "OTHER",
            "description": "Test case at national level.",
        },
        format="json",
    )
    case_id = create_response.data["id"]
    committee_client = _client_for(elected_committee[1])
    committee_client.post(f"/api/v1/discipline/cases/{case_id}/convene/")
    committee_client.post(
        f"/api/v1/discipline/cases/{case_id}/recommend/",
        {"recommendation": "Reprimand.", "recommended_measure": "REPRIMAND"},
        format="json",
    )
    chairman_client.post(
        f"/api/v1/discipline/cases/{case_id}/decide/",
        {"final_decision": "Upheld.", "final_measure": "REPRIMAND"},
        format="json",
    )

    respondent_client = _client_for(respondent)
    appeal_response = respondent_client.post(
        f"/api/v1/discipline/cases/{case_id}/appeal/"
    )
    assert appeal_response.status_code == 400
    assert appeal_response.data["error"]["code"] == "invalid_state"


def test_only_respondent_may_appeal(chairman_client, national_unit, elected_committee):
    reporter_client = _client_for(elected_committee[0])
    respondent = _make_member("resp3@example.com", "NDC-RESP-000003", national_unit)
    create_response = reporter_client.post(
        "/api/v1/discipline/cases/",
        {
            "respondent_id": str(respondent.id),
            "organizational_unit_id": str(national_unit.id),
            "grounds": "OTHER",
            "description": "Test case.",
        },
        format="json",
    )
    case_id = create_response.data["id"]
    committee_client = _client_for(elected_committee[1])
    committee_client.post(f"/api/v1/discipline/cases/{case_id}/convene/")
    committee_client.post(
        f"/api/v1/discipline/cases/{case_id}/recommend/",
        {"recommendation": "Reprimand.", "recommended_measure": "REPRIMAND"},
        format="json",
    )
    chairman_client.post(
        f"/api/v1/discipline/cases/{case_id}/decide/",
        {"final_decision": "Upheld.", "final_measure": "REPRIMAND"},
        format="json",
    )

    response = reporter_client.post(f"/api/v1/discipline/cases/{case_id}/appeal/")
    assert response.status_code == 403


def test_case_view_permission_denies_unrelated_member(
    chairman_client, national_unit, elected_committee
):
    reporter_client = _client_for(elected_committee[0])
    respondent = _make_member("resp4@example.com", "NDC-RESP-000004", national_unit)
    create_response = reporter_client.post(
        "/api/v1/discipline/cases/",
        {
            "respondent_id": str(respondent.id),
            "organizational_unit_id": str(national_unit.id),
            "grounds": "OTHER",
            "description": "Test case.",
        },
        format="json",
    )
    case_id = create_response.data["id"]

    unrelated = _make_member("unrelated@example.com", "NDC-UNREL-000001", national_unit)
    unrelated_client = _client_for(unrelated)
    response = unrelated_client.get(f"/api/v1/discipline/cases/{case_id}/")
    assert response.status_code == 403


def test_chairman_can_impose_and_refer_a_suspension(
    chairman_client, national_unit, member_user, elected_committee
):
    reporter_client = _client_for(elected_committee[0])
    case_response = reporter_client.post(
        "/api/v1/discipline/cases/",
        {
            "respondent_id": str(member_user.id),
            "organizational_unit_id": str(national_unit.id),
            "grounds": "ANTI_PARTY_CONDUCT",
            "description": "Serious anti-Party conduct requiring precautionary suspension.",
        },
        format="json",
    )
    case_id = case_response.data["id"]

    suspend_response = chairman_client.post(
        "/api/v1/discipline/suspensions/",
        {"user_id": str(member_user.id), "reason": "Pending disciplinary proceedings."},
        format="json",
    )
    assert suspend_response.status_code == 201
    suspension_id = suspend_response.data["id"]
    assert suspend_response.data["status"] == "ACTIVE"
    assert suspend_response.data["referral_overdue"] is False

    refer_response = chairman_client.post(
        f"/api/v1/discipline/suspensions/{suspension_id}/refer/",
        {"case_id": case_id},
        format="json",
    )
    assert refer_response.status_code == 200
    assert refer_response.data["status"] == "REFERRED"
    assert refer_response.data["related_case_id"] == case_id


def test_suspension_can_only_be_renewed_once(
    chairman_client, national_unit, member_user
):
    suspend_response = chairman_client.post(
        "/api/v1/discipline/suspensions/",
        {"user_id": str(member_user.id), "reason": "Interim suspension."},
        format="json",
    )
    suspension_id = suspend_response.data["id"]

    first_renewal = chairman_client.post(
        f"/api/v1/discipline/suspensions/{suspension_id}/renew/"
    )
    assert first_renewal.status_code == 200
    assert first_renewal.data["renewal_count"] == 1

    second_renewal = chairman_client.post(
        f"/api/v1/discipline/suspensions/{suspension_id}/renew/"
    )
    assert second_renewal.status_code == 400
    assert second_renewal.data["error"]["code"] == "invalid_state"


def test_ordinary_member_cannot_impose_a_suspension(auth_client, member_user):
    response = auth_client.post(
        "/api/v1/discipline/suspensions/",
        {"user_id": str(member_user.id), "reason": "Attempting self-suspension."},
        format="json",
    )
    assert response.status_code == 403


def test_end_suspension(chairman_client, member_user):
    suspend_response = chairman_client.post(
        "/api/v1/discipline/suspensions/",
        {"user_id": str(member_user.id), "reason": "Interim suspension."},
        format="json",
    )
    suspension_id = suspend_response.data["id"]
    end_response = chairman_client.post(
        f"/api/v1/discipline/suspensions/{suspension_id}/end/"
    )
    assert end_response.status_code == 200
    assert end_response.data["status"] == "ENDED"
