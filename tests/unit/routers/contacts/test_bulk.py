"""pytest tests for API functionality"""

import urllib.parse
from datetime import timedelta

import pytest

from ctms.schemas import BulkRequestSchema, ContactSchema, CTMSResponse


@pytest.mark.parametrize(
    "path",
    [
        "/updates?start=2020-01-22T03%3A24%3A00%2B00%3A00&end=2021-01-29T09%3A26%3A57.511000%2B00%3A00&limit=-11&after=OTNkYjgzZDQtNDExOS00ZTBjLWFmODctYTcxMzc4NmZhODFkLDIwMjAtMDEtMjIgMTU6MjQ6MDArMDA6MDA=",
        "/updates?start=2020-01-22T03%3A24%3A00%2B00%3A00&end=&limit=1001&after=&mofo_relevant=",
        "/updates?start=2020-01-22T03%3A24%3A00%2B00%3A00&end=&limit=-3&after=&mofo_relevant=",
        "/updates?start=2020-01-22T03%3A24%3A00%2B00%3A00&after=null",
        "/updates?start=2020-01-22T03%3A24%3A00%2B00%3A00&limit=null",
        "/updates?start=2020-01-22T03%3A24%3A00%2B00%3A00&after=hello",
        "/updates?start=2020-01-22T03%3A24%3A00%2B00%3A00&mofo_relevant=nah",
    ],
)
def test_authorized_bulk_call_errs_on_validation(client, path):
    """Calling the API with invlaid query parameters fails"""

    resp = client.get(path)
    assert resp.status_code == 422


BULK_TEST_CASES = (
    "/updates?start=2020-01-22T03%3A24%3A00%2B00%3A00&end=2021-01-29T09%3A26%3A57.511000%2B00%3A00&limit=1&after=OTNkYjgzZDQtNDExOS00ZTBjLWFmODctYTcxMzc4NmZhODFkLDIwMjAtMDEtMjIgMTU6MjQ6MDArMDA6MDA=",
    "/updates?start=2020-01-22T03%3A24%3A00%2B00%3A00&end=&limit=100&after=&mofo_relevant=",
    "/updates?start=2020-01-22T03%3A24%3A00%2B00%3A00",
    "/updates?start=2020-01-22T03%3A24%3A00%2B00%3A00&mofo_relevant=yes",
)


@pytest.mark.parametrize("path", BULK_TEST_CASES)
def test_authorized_bulk_call_succeeds(client, path):
    """Calling the API with credentials succeeds."""
    resp = client.get(path)
    assert resp.status_code == 200


@pytest.mark.parametrize("path", BULK_TEST_CASES)
def test_unauthorized_api_call_fails(anon_client, path):
    """Calling the API without credentials fails."""
    resp = anon_client.get(path)
    assert resp.status_code == 401
    assert resp.json() == {"detail": "Not authenticated"}


def test_get_ctms_bulk_by_timerange(client, dbsession, email_factory):
    first_email = email_factory()
    target_email = email_factory(
        newsletters=1,
        waitlists=1,
        mofo=True,
        amo=True,
        fxa=True,
    )
    last_email = email_factory()
    dbsession.commit()

    after = BulkRequestSchema.compressor_for_bulk_encoded_details(
        first_email.email_id, first_email.update_timestamp
    )
    limit = 1
    start = first_email.update_timestamp - timedelta(hours=12)
    start_time = urllib.parse.quote_plus(start.isoformat())
    end = last_email.update_timestamp + timedelta(hours=12)
    end_time = urllib.parse.quote_plus(end.isoformat())
    url = f"/updates?start={start_time}&end={end_time}&limit={limit}&after={after}"
    resp = client.get(url)
    assert resp.status_code == 200
    results = resp.json()
    assert "start" in results
    assert "end" in results
    assert "after" in results
    assert "limit" in results
    assert "next" in results
    assert "items" in results
    assert len(results["items"]) > 0

    dict_contact_expected = ContactSchema.from_email(target_email).model_dump()
    dict_contact_actual = CTMSResponse(**results["items"][0]).model_dump()

    # The response shows computed fields for retro-compat. Contact schema
    # does not have them.
    del dict_contact_actual["vpn_waitlist"]
    del dict_contact_actual["relay_waitlist"]
    # The reponse does not show `email_id` and timestamp fields.
    for newsletter in dict_contact_expected["newsletters"]:
        del newsletter["email_id"]
    for waitlist in dict_contact_expected["waitlists"]:
        del waitlist["email_id"]

    assert dict_contact_expected == dict_contact_actual
    assert results["next"] is not None


def test_get_ctms_bulk_by_timerange_no_results(dbsession, client, email_factory):
    emails = email_factory.create_batch(3)
    dbsession.commit()

    sorted_list = sorted(
        emails,
        key=lambda email: (email.update_timestamp, email.email_id),
    )
    first_email = sorted_list[0]
    last_email = sorted_list[-1]
    after = BulkRequestSchema.compressor_for_bulk_encoded_details(
        last_email.email_id, last_email.update_timestamp
    )
    limit = 1
    start = first_email.update_timestamp - timedelta(hours=12)
    start_time = urllib.parse.quote_plus(start.isoformat())
    end = last_email.update_timestamp + timedelta(hours=12)
    end_time = urllib.parse.quote_plus(end.isoformat())
    url = f"/updates?start={start_time}&end={end_time}&limit={limit}&after={after}"
    resp = client.get(url)
    assert resp.status_code == 200
    results = resp.json()
    assert "start" in results
    assert "end" in results
    assert "after" in results
    assert "limit" in results
    assert "next" in results
    assert "items" in results
    assert len(results["items"]) == 0
    assert results["next"] is None
