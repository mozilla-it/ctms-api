import datetime
from unittest import mock
from unittest.mock import MagicMock

import pytest

from ctms import acoustic_service
from ctms.acoustic_service import CTMSToAcousticService

CTMS_ACOUSTIC_MAIN_TABLE_ID = "1"
CTMS_ACOUSTIC_NEWSLETTER_TABLE_ID = "9"
CTMS_ACOUSTIC_PRODUCT_TABLE_ID = "10"


@pytest.fixture
def acoustic_client():
    ctms_acoustic_client_id = "CLIENT"
    ctms_acoustic_client_secret = "SECRET"
    ctms_acoustic_refresh_token = "REFRESH"
    with mock.patch("ctms.acoustic_service.Acoustic"):
        yield acoustic_service.Acoustic(
            client_id=ctms_acoustic_client_id,
            client_secret=ctms_acoustic_client_secret,
            refresh_token=ctms_acoustic_refresh_token,
            server_number=6,
        )


@pytest.fixture
def base_ctms_acoustic_service(acoustic_client):
    with mock.patch("ctms.acoustic_service.Acoustic"):
        yield acoustic_service.CTMSToAcousticService(
            acoustic_client=acoustic_client,
            acoustic_main_table_id=CTMS_ACOUSTIC_MAIN_TABLE_ID,
            acoustic_newsletter_table_id=CTMS_ACOUSTIC_NEWSLETTER_TABLE_ID,
            acoustic_product_table_id=CTMS_ACOUSTIC_PRODUCT_TABLE_ID,
        )


@pytest.fixture
def metrics_ctms_acoustic_service(acoustic_client, background_metric_service):
    with mock.patch("ctms.acoustic_service.Acoustic"):
        yield acoustic_service.CTMSToAcousticService(
            acoustic_client=acoustic_client,
            acoustic_main_table_id=CTMS_ACOUSTIC_MAIN_TABLE_ID,
            acoustic_newsletter_table_id=CTMS_ACOUSTIC_NEWSLETTER_TABLE_ID,
            acoustic_product_table_id=CTMS_ACOUSTIC_PRODUCT_TABLE_ID,
            metric_service=background_metric_service,
        )


def test_base_service_creation(base_ctms_acoustic_service):
    assert base_ctms_acoustic_service is not None


def test_ctms_to_acoustic(
    base_ctms_acoustic_service, example_contact, maximal_contact, minimal_contact
):
    contact_list = [example_contact, maximal_contact, minimal_contact]
    example_contact_expected = [49, len(example_contact.newsletters) - 2]
    maximal_contact_expected = [49, len(maximal_contact.newsletters) - 2]
    minimal_contact_expected = [31, len(minimal_contact.newsletters) - 2]
    expected_results = {
        example_contact.email.email_id: example_contact_expected,
        maximal_contact.email.email_id: maximal_contact_expected,
        minimal_contact.email.email_id: minimal_contact_expected,
    }

    for contact in contact_list:
        expected = expected_results.get(contact.email.email_id)
        (
            _main,
            _newsletter,
            _product,
        ) = base_ctms_acoustic_service.convert_ctms_to_acoustic(contact)
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
            assert row["email_id"] == str(contact.email.email_id)
            assert row["newsletter_name"] is not None
        assert len(_product) == 0


def test_ctms_to_acoustic_mocked(
    base_ctms_acoustic_service,
    maximal_contact,
):
    acoustic_mock: MagicMock = MagicMock()
    base_ctms_acoustic_service.acoustic = acoustic_mock
    _main, _newsletter, _product = base_ctms_acoustic_service.convert_ctms_to_acoustic(
        maximal_contact
    )  # To be used as in testing, for expected inputs to downstream methods
    assert _main is not None
    assert _newsletter is not None
    assert len(_product) == 0
    results = base_ctms_acoustic_service.attempt_to_upload_ctms_contact(maximal_contact)
    assert results  # success
    acoustic_mock.add_recipient.assert_called()
    acoustic_mock.insert_update_relational_table.assert_called()

    acoustic_mock.add_recipient.assert_called_with(
        list_id=CTMS_ACOUSTIC_MAIN_TABLE_ID,
        created_from=3,
        update_if_found="TRUE",
        allow_html=False,
        sync_fields={"email_id": _main["email_id"]},
        columns=_main,
    )

    acoustic_mock.insert_update_relational_table.assert_called_with(
        table_id=CTMS_ACOUSTIC_NEWSLETTER_TABLE_ID, rows=_newsletter
    )

    acoustic_mock.insert_update_product_table.assert_not_called()


def test_ctms_to_acoustic_with_subscription(
    base_ctms_acoustic_service, contact_with_stripe_subscription
):
    acoustic_mock = MagicMock()
    base_ctms_acoustic_service.acoustic = acoustic_mock
    _main, _newsletter, _product = base_ctms_acoustic_service.convert_ctms_to_acoustic(
        contact_with_stripe_subscription
    )  # To be used as in testing, for expected inputs to downstream methods
    assert _main is not None
    assert len(_newsletter) == 0  # None in Main Table Subscriber flags
    assert len(_product) == 1
    results = base_ctms_acoustic_service.attempt_to_upload_ctms_contact(
        contact_with_stripe_subscription
    )
    assert results  # success

    acoustic_mock.insert_update_relational_table.assert_called_with(
        table_id=CTMS_ACOUSTIC_PRODUCT_TABLE_ID, rows=_product
    )
    for name, value in _product[0].items():
        assert isinstance(value, str), name


def test_ctms_to_acoustic_with_subscription_and_metrics(
    metrics_ctms_acoustic_service, contact_with_stripe_subscription
):
    acoustic_mock = MagicMock()
    acoustic_svc = metrics_ctms_acoustic_service
    acoustic_svc.acoustic = acoustic_mock
    _main, _newsletter, _product = acoustic_svc.convert_ctms_to_acoustic(
        contact_with_stripe_subscription
    )  # To be used as in testing, for expected inputs to downstream methods
    assert _main is not None
    assert len(_newsletter) == 0  # None in Main Table Subscriber flags
    assert len(_product) == 1
    results = acoustic_svc.attempt_to_upload_ctms_contact(
        contact_with_stripe_subscription
    )
    assert results  # success

    acoustic_mock.insert_update_relational_table.assert_called_with(
        table_id=CTMS_ACOUSTIC_PRODUCT_TABLE_ID, rows=_product
    )

    registry = acoustic_svc.metric_service.registry
    main_labels = {
        "method": "add_recipient",
        "status": "success",
        "table": "main",
        "app_kubernetes_io_component": "background",
        "app_kubernetes_io_instance": "ctms",
        "app_kubernetes_io_name": "ctms",
    }
    rt_labels = main_labels.copy()
    rt_labels.update({"method": "insert_update_relational_table", "table": "product"})
    metrics = (
        "ctms_background_acoustic_request_total",
        "ctms_background_acoustic_requests_duration_count",
    )
    for metric in metrics:
        for labels in (main_labels, rt_labels):
            assert registry.get_sample_value(metric, labels) == 1, (metric, labels)


def test_transform_field(base_ctms_acoustic_service):
    is_true = base_ctms_acoustic_service.transform_field_for_acoustic(True)
    assert is_true == "1"
    is_false = base_ctms_acoustic_service.transform_field_for_acoustic(False)
    assert is_false == "0"
    transformed_from_datetime = base_ctms_acoustic_service.transform_field_for_acoustic(
        datetime.datetime.now()
    )
    assert (
        transformed_from_datetime is not None
    ), "Error when using method to transform datetime object"
    transformed_from_date = base_ctms_acoustic_service.transform_field_for_acoustic(
        datetime.date.today()
    )
    assert (
        transformed_from_date is not None
    ), "Error when using method to transform date object"

    assert transformed_from_datetime == transformed_from_date, (
        "The result of the transformation process of a "
        "date and datetime should be identical, "
        "when starting values are equivalent in date "
    )

    is_datetime_parsed = datetime.datetime.strptime(
        transformed_from_datetime, "%m/%d/%Y"
    )
    assert isinstance(
        is_datetime_parsed, datetime.date
    ), "The result should be in MM/DD/YYYY format, to be able to be processed to a date"
    is_date_parsed = datetime.datetime.strptime(transformed_from_date, "%m/%d/%Y")
    assert isinstance(
        is_date_parsed, datetime.date
    ), "The result should be in MM/DD/YYYY format, to be able to be processed to a date"


@pytest.mark.parametrize(
    "value,expected",
    (("true", "Yes"), (True, "Yes"), (False, "No"), ("false", "No"), ("", "No")),
)
def test_to_acoustic_bool(value, expected):
    """Python and JS booleans are converted to Acoustic Yes/No bools."""
    assert CTMSToAcousticService.to_acoustic_bool(value) == expected


def test_to_acoustic_timestamp():
    """Python datetimes are converted to Acoustic timestamps."""
    the_datetime = datetime.datetime(2021, 11, 8, 9, 6, tzinfo=datetime.timezone.utc)
    acoustic_ts = CTMSToAcousticService.to_acoustic_timestamp(the_datetime)
    assert acoustic_ts == "11/08/2021 09:06:00"


def test_to_acoustic_timestamp_null():
    """Null datetimes are converted to an empty string."""
    assert CTMSToAcousticService.to_acoustic_timestamp(None) == ""


def test_transform_fxa_created_date(base_ctms_acoustic_service):
    fxa_created_date = "2021-06-16T20:09:41.121000"
    fxa_datetime = base_ctms_acoustic_service.fxa_created_date_string_to_datetime(
        fxa_created_date
    )
    assert isinstance(fxa_datetime, datetime.datetime)
    # converted successfully and will be transformed by alternate method to acoustic-readable
    # later to be a noop/passthrough when fixed upstream.

    fxa_created_date = fxa_datetime  # now a datetime, still will be.
    fxa_unchanged = base_ctms_acoustic_service.fxa_created_date_string_to_datetime(
        fxa_created_date
    )
    assert isinstance(fxa_unchanged, datetime.datetime)
    assert fxa_created_date is fxa_unchanged

    fxa_created_date = 123  # Ok, data upstream must be weird.
    fxa_still_int = base_ctms_acoustic_service.fxa_created_date_string_to_datetime(
        fxa_created_date
    )
    assert isinstance(fxa_still_int, int)
    assert fxa_created_date is fxa_still_int
