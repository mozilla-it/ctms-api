import datetime
from unittest import mock

import pytest

from ctms import acoustic_service

CTMS_ACOUSTIC_CLIENT_ID = "CLIENT"
CTMS_ACOUSTIC_CLIENT_SECRET = "SECRET"
CTMS_ACOUSTIC_REFRESH_TOKEN = "REFRESH"
CTMS_ACOUSTIC_MAIN_TABLE_ID = "1"
CTMS_ACOUSTIC_NEWSLETTER_TABLE_ID = "9"


@pytest.fixture()
def no_acoustic():
    patcher = mock.patch("acoustic_service.Acoustic")
    patcher.start()
    yield patcher
    patcher.stop()


@pytest.fixture
def base_ctms_acoustic_service(no_acoustic):
    return acoustic_service.CTMSToAcousticService(
        client_id=CTMS_ACOUSTIC_CLIENT_ID,
        client_secret=CTMS_ACOUSTIC_CLIENT_SECRET,
        refresh_token=CTMS_ACOUSTIC_REFRESH_TOKEN,
        acoustic_main_table_id=CTMS_ACOUSTIC_MAIN_TABLE_ID,
        acoustic_newsletter_table_id=CTMS_ACOUSTIC_NEWSLETTER_TABLE_ID,
        server_number=6,
    )


def test_base_service_creation(base_ctms_acoustic_service):
    assert base_ctms_acoustic_service is not None


def test_ctms_to_acoustic(
    base_ctms_acoustic_service, example_contact, maximal_contact, minimal_contact
):
    contact_list = [example_contact, maximal_contact, minimal_contact]
    example_contact_expected = [54, len(example_contact.newsletters)]
    maximal_contact_expected = [54, len(maximal_contact.newsletters)]
    minimal_contact_expected = [36, len(minimal_contact.newsletters)]
    expected_results = {
        example_contact.email.email_id: example_contact_expected,
        maximal_contact.email.email_id: maximal_contact_expected,
        minimal_contact.email.email_id: minimal_contact_expected,
    }

    for contact in contact_list:
        expected = expected_results.get(contact.email.email_id)
        _main, _newsletter = base_ctms_acoustic_service.convert_ctms_to_acoustic(
            contact
        )
        assert _main is not None
        assert _newsletter is not None
        assert (
            len(_main) == expected[0]
        ), f"Expected {expected[0]} with id {contact.email.email_id}"
        assert (
            len(_newsletter) == expected[1]
        ), f"Expected {expected[1]} with id {contact.email.email_id}"
        assert _main["email"] == contact.email.primary_email
        if contact.fxa is not None:
            assert _main["fxa_id"] == contact.fxa.fxa_id
        for row in _newsletter:
            assert (
                row["email_id"] == contact.email.email_id
            )  # TODO: Should this be a str?
            assert row["newsletter_name"] is not None


def test_transform_field(base_ctms_acoustic_service):
    is_true = base_ctms_acoustic_service.transform_field_for_acoustic(True)
    assert is_true == "1"
    is_false = base_ctms_acoustic_service.transform_field_for_acoustic(False)
    assert is_false == "0"
    is_datetime = base_ctms_acoustic_service.transform_field_for_acoustic(
        datetime.datetime.now()
    )
    assert is_datetime is not None
    is_date = base_ctms_acoustic_service.transform_field_for_acoustic(
        datetime.date.today()
    )
    assert is_date is not None

    try:
        is_datetime = datetime.date.fromisoformat(is_datetime)
        assert isinstance(is_datetime, datetime.date)
        is_date = datetime.date.fromisoformat(is_date)
        assert isinstance(is_date, datetime.date)
    except:  # pylint: disable=W0702
        assert False, "Failure with timestamp validation"
