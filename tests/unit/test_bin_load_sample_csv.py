from os.path import dirname, join

import pytest

from ctms.bin.load_sample_csv import main
from ctms.crud import get_contact_by_email_id
from ctms.schemas import ContactSchema


@pytest.fixture
def test_data_dir(request):
    if not hasattr(request, "param"):
        raise BaseException(
            "Must provide param to test_data fixture specifying which data to use."
        )
    return join(dirname(dirname(__file__)), "data", request.param)


@pytest.mark.parametrize("test_data_dir", ["good_csvs"], indirect=True)
def test_create(connection, dbsession, settings, test_data_dir):
    """Most straightforward load works"""
    ret = main(
        connection,
        settings,
        [
            "-d",
            test_data_dir,
            "--dev",
            "--duplicates",
            f"{test_data_dir}/duplicates.txt",
        ],
    )
    assert ret == 0

    ctct = get_contact_by_email_id(dbsession, "e926425d-0189-4cc2-ac7c-b760659ac62f")
    contact = ContactSchema(**ctct)
    assert contact
    assert contact.email.mailing_country == "A country in the world"
    assert contact.amo.email_opt_in == 0
    assert (
        contact.fxa.created_date == "2019-05-28"
    )  # This is not our timestamp, but a fxa thing
    assert len(contact.waitlists) == 1
    assert len(contact.newsletters) == 4
    assert "firefox-accounts-journey" in [n.name for n in contact.newsletters]


@pytest.mark.parametrize("test_data_dir", ["good_csvs_no_amo"], indirect=True)
def test_create_no_amo(connection, dbsession, settings, test_data_dir):
    """If the amo file is empty, we don't make an amo for this record"""
    ret = main(
        connection,
        settings,
        [
            "-d",
            test_data_dir,
            "--dev",
            "--duplicates",
            f"{test_data_dir}/duplicates.txt",
        ],
    )
    assert ret == 0

    ctct = get_contact_by_email_id(dbsession, "e926425d-0189-4cc2-ac7c-b760659ac62f")
    contact = ContactSchema(**ctct)
    assert contact
    assert contact.email.mailing_country == "A country in the world"
    assert contact.amo is None
    assert (
        contact.fxa.created_date == "2019-05-28"
    )  # This is not our timestamp, but a fxa thing
    assert len(contact.waitlists) == 1
    assert len(contact.newsletters) == 4
    assert "firefox-accounts-journey" in [n.name for n in contact.newsletters]
