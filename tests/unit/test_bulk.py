"""pytest tests for API functionality"""
import urllib.parse
from datetime import timedelta
from typing import Tuple

import pytest

from ctms.schemas import BulkRequestSchema, CTMSResponse

INVALID_BULK_TEST_CASES: Tuple[Tuple[str, str], ...] = (
    (
        "GET",
        "/updates?start=2020-01-22T03%3A24%3A00%2B00%3A00&end=2021-01-29T09%3A26%3A57.511000%2B00%3A00&limit=-11&after=OTNkYjgzZDQtNDExOS00ZTBjLWFmODctYTcxMzc4NmZhODFkLDIwMjAtMDEtMjIgMTU6MjQ6MDArMDA6MDA=",
    ),
    (
        "GET",
        "/updates?start=2020-01-22T03%3A24%3A00%2B00%3A00&end=&limit=1001&after=&mofo_relevant=",
    ),
    (
        "GET",
        "/updates?start=2020-01-22T03%3A24%3A00%2B00%3A00&end=&limit=-3&after=&mofo_relevant=",
    ),
    (
        "GET",
        "/updates?start=2020-01-22T03%3A24%3A00%2B00%3A00&after=null",
    ),
    (
        "GET",
        "/updates?start=2020-01-22T03%3A24%3A00%2B00%3A00&limit=null",
    ),
    (
        "GET",
        "/updates?start=2020-01-22T03%3A24%3A00%2B00%3A00&after=hello",
    ),
    (
        "GET",
        "/updates?start=2020-01-22T03%3A24%3A00%2B00%3A00&mofo_relevant=nah",
    ),
)
BULK_TEST_CASES: Tuple[Tuple[str, str], ...] = (
    (
        "GET",
        "/updates?start=2020-01-22T03%3A24%3A00%2B00%3A00&end=2021-01-29T09%3A26%3A57.511000%2B00%3A00&limit=1&after=OTNkYjgzZDQtNDExOS00ZTBjLWFmODctYTcxMzc4NmZhODFkLDIwMjAtMDEtMjIgMTU6MjQ6MDArMDA6MDA=",
    ),
    (
        "GET",
        "/updates?start=2020-01-22T03%3A24%3A00%2B00%3A00&end=&limit=100&after=&mofo_relevant=",
    ),
    (
        "GET",
        "/updates?start=2020-01-22T03%3A24%3A00%2B00%3A00",
    ),
    (
        "GET",
        "/updates?start=2020-01-22T03%3A24%3A00%2B00%3A00&mofo_relevant=yes",
    ),
)


@pytest.mark.parametrize("method,path", INVALID_BULK_TEST_CASES)
def test_authorized_bulk_call_errs_on_validation(client, example_contact, method, path):
    """Calling the API without credentials fails."""
    resp = client.get(path)
    assert resp.status_code == 422


@pytest.mark.parametrize("method,path", BULK_TEST_CASES)
def test_authorized_bulk_call_succeeds(client, example_contact, method, path):
    """Calling the API without credentials fails."""
    resp = client.get(path)
    assert resp.status_code == 200


@pytest.mark.parametrize("method,path", BULK_TEST_CASES)
def test_unauthorized_api_call_fails(anon_client, example_contact, method, path):
    """Calling the API without credentials fails."""
    resp = anon_client.get(path)
    assert resp.status_code == 401
    assert resp.json() == {"detail": "Not authenticated"}


def test_get_ctms_bulk_by_timerange(
    client, example_contact, maximal_contact, minimal_contact
):
    contact_list = [example_contact, maximal_contact, minimal_contact]
    sorted_list = sorted(
        contact_list,
        key=lambda contact: (contact.email.update_timestamp, contact.email.email_id),
    )
    first_contact = sorted_list[0]
    last_contact = sorted_list[-1]
    after = BulkRequestSchema.compressor_for_bulk_encoded_details(
        first_contact.email.email_id, first_contact.email.update_timestamp
    )
    limit = 1
    start = first_contact.email.update_timestamp - timedelta(hours=12)
    start_time = urllib.parse.quote_plus(start.isoformat())
    end = last_contact.email.update_timestamp + timedelta(hours=12)
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
    dict_contact_expected = sorted_list[1].dict()
    # Since the contact data contains more info than the response, let's strip fields
    # to be able to compare dict down the line (sic).
    omit_fields = ("email_id", "create_timestamp", "update_timestamp")
    dict_contact_expected["newsletters"] = [
        {k: v for k, v in nl.items() if k not in omit_fields}
        for nl in dict_contact_expected["newsletters"]
    ]
    dict_contact_expected["waitlists"] = [
        {k: v for k, v in wl.items() if k not in omit_fields}
        for wl in dict_contact_expected["waitlists"]
    ]

    dict_contact_actual = CTMSResponse.parse_obj(results["items"][0]).dict()
    # products list is not (yet) in output schema
    assert dict_contact_expected["products"] == []
    assert "products" not in dict_contact_actual
    dict_contact_actual["products"] = []
    # The response shows computed fields for retro-compat. Contact schema
    # does not have them.
    del dict_contact_actual["vpn_waitlist"]
    del dict_contact_actual["relay_waitlist"]

    assert dict_contact_expected == dict_contact_actual
    assert results["next"] is not None


def test_get_ctms_bulk_by_timerange_no_results(
    client, example_contact, maximal_contact, minimal_contact
):
    contact_list = [example_contact, maximal_contact, minimal_contact]
    sorted_list = sorted(
        contact_list,
        key=lambda contact: (contact.email.update_timestamp, contact.email.email_id),
    )
    first_contact = sorted_list[0]
    last_contact = sorted_list[-1]
    after = BulkRequestSchema.compressor_for_bulk_encoded_details(
        last_contact.email.email_id, last_contact.email.update_timestamp
    )
    limit = 1
    start = first_contact.email.update_timestamp - timedelta(hours=12)
    start_time = urllib.parse.quote_plus(start.isoformat())
    end = last_contact.email.update_timestamp + timedelta(hours=12)
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
