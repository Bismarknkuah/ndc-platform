import datetime

import pytest

pytestmark = pytest.mark.django_db


def _window():
    start = datetime.datetime.utcnow().isoformat() + "Z"
    end = (datetime.datetime.utcnow() + datetime.timedelta(days=30)).isoformat() + "Z"
    return start, end


def test_authorized_officer_can_create_campaign(chairman_client, national_unit):
    start, end = _window()
    response = chairman_client.post(
        "/api/v1/donations/campaigns/",
        {
            "title": "2028 Election Fund",
            "target_unit_id": str(national_unit.id),
            "goal_amount": "50000.00",
            "start_date": start,
            "end_date": end,
        },
        format="json",
    )
    assert response.status_code == 201
    assert response.json()["status"] == "PLANNING"


def test_ordinary_member_cannot_create_campaign(auth_client, national_unit):
    start, end = _window()
    response = auth_client.post(
        "/api/v1/donations/campaigns/",
        {
            "title": "Should fail",
            "target_unit_id": str(national_unit.id),
            "goal_amount": "1000.00",
            "start_date": start,
            "end_date": end,
        },
        format="json",
    )
    assert response.status_code == 403


@pytest.fixture
def campaign(chairman_client, national_unit):
    start, end = _window()
    return chairman_client.post(
        "/api/v1/donations/campaigns/",
        {
            "title": "2028 Election Fund",
            "target_unit_id": str(national_unit.id),
            "goal_amount": "1000.00",
            "start_date": start,
            "end_date": end,
        },
        format="json",
    ).json()


def test_member_can_self_pledge(auth_client, campaign):
    response = auth_client.post(
        "/api/v1/donations/pledges/",
        {"campaign_id": campaign["id"], "pledged_amount": "100.00"},
        format="json",
    )
    assert response.status_code == 201
    assert response.json()["status"] == "PLEDGED"
    assert response.json()["donor_display_name"]


def test_authority_can_record_external_donor_pledge(chairman_client, campaign):
    response = chairman_client.post(
        "/api/v1/donations/pledges/",
        {
            "campaign_id": campaign["id"],
            "donor_name": "Kofi Businessman",
            "donor_contact": "0244000000",
            "pledged_amount": "5000.00",
        },
        format="json",
    )
    assert response.status_code == 201
    assert response.json()["donor_display_name"] == "Kofi Businessman"


def test_member_cannot_record_pledge_on_behalf_of_another_member(
    auth_client, campaign, national_chairman_user
):
    response = auth_client.post(
        "/api/v1/donations/pledges/",
        {
            "campaign_id": campaign["id"],
            "donor_user_id": str(national_chairman_user.id),
            "pledged_amount": "50.00",
        },
        format="json",
    )
    assert response.status_code == 403


def test_pledge_requires_an_amount(chairman_client, campaign):
    response = chairman_client.post(
        "/api/v1/donations/pledges/",
        {"campaign_id": campaign["id"], "donor_name": "External Donor"},
        format="json",
    )
    assert response.status_code == 400


def test_omitting_donor_fields_defaults_to_self_pledge(
    auth_client, campaign, member_user
):
    response = auth_client.post(
        "/api/v1/donations/pledges/",
        {"campaign_id": campaign["id"], "pledged_amount": "25.00"},
        format="json",
    )
    assert response.status_code == 201
    assert response.json()["donor_user"]["id"] == str(member_user.id)


def test_authority_can_fulfill_pledge_and_creates_finance_record(
    chairman_client, campaign
):
    pledge = chairman_client.post(
        "/api/v1/donations/pledges/",
        {
            "campaign_id": campaign["id"],
            "donor_name": "External Donor",
            "pledged_amount": "1000.00",
        },
        format="json",
    ).json()

    response = chairman_client.post(
        f"/api/v1/donations/pledges/{pledge['id']}/fulfill/",
        {"amount": "400.00"},
        format="json",
    )
    assert response.status_code == 200
    assert response.json()["status"] == "PARTIALLY_FULFILLED"
    assert response.json()["fulfilled_amount"] == "400.00"
    assert len(response.json()["finance_record_ids"]) == 1

    from apps.finance.documents import FinanceRecord

    record = FinanceRecord.objects.get(id=response.json()["finance_record_ids"][0])
    assert record.record_type == "INCOME"
    assert str(record.amount) == "400.00"


def test_full_fulfillment_marks_pledge_fulfilled(chairman_client, campaign):
    pledge = chairman_client.post(
        "/api/v1/donations/pledges/",
        {
            "campaign_id": campaign["id"],
            "donor_name": "External Donor",
            "pledged_amount": "200.00",
        },
        format="json",
    ).json()
    response = chairman_client.post(
        f"/api/v1/donations/pledges/{pledge['id']}/fulfill/",
        {"amount": "200.00"},
        format="json",
    )
    assert response.json()["status"] == "FULFILLED"


def test_cannot_fulfill_beyond_pledged_amount(chairman_client, campaign):
    pledge = chairman_client.post(
        "/api/v1/donations/pledges/",
        {
            "campaign_id": campaign["id"],
            "donor_name": "External Donor",
            "pledged_amount": "100.00",
        },
        format="json",
    ).json()
    response = chairman_client.post(
        f"/api/v1/donations/pledges/{pledge['id']}/fulfill/",
        {"amount": "150.00"},
        format="json",
    )
    assert response.status_code == 400


def test_ordinary_member_cannot_fulfill_pledge(auth_client, chairman_client, campaign):
    pledge = chairman_client.post(
        "/api/v1/donations/pledges/",
        {
            "campaign_id": campaign["id"],
            "donor_name": "External Donor",
            "pledged_amount": "100.00",
        },
        format="json",
    ).json()
    response = auth_client.post(
        f"/api/v1/donations/pledges/{pledge['id']}/fulfill/",
        {"amount": "50.00"},
        format="json",
    )
    assert response.status_code == 403


def test_campaign_progress_aggregates_pledges(chairman_client, campaign):
    p1 = chairman_client.post(
        "/api/v1/donations/pledges/",
        {
            "campaign_id": campaign["id"],
            "donor_name": "Donor A",
            "pledged_amount": "300.00",
        },
        format="json",
    ).json()
    chairman_client.post(
        "/api/v1/donations/pledges/",
        {
            "campaign_id": campaign["id"],
            "donor_name": "Donor B",
            "pledged_amount": "200.00",
        },
        format="json",
    )
    chairman_client.post(
        f"/api/v1/donations/pledges/{p1['id']}/fulfill/",
        {"amount": "300.00"},
        format="json",
    )

    response = chairman_client.get(
        f"/api/v1/donations/campaigns/{campaign['id']}/progress/"
    )
    body = response.json()
    assert body["total_pledged"] == "500.00"
    assert body["total_fulfilled"] == "300.00"
    assert body["pledge_count"] == 2
    assert body["percentage_of_goal_fulfilled"] == 30.0
