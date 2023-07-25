import datetime
from unittest import mock
from unittest.mock import MagicMock
from uuid import UUID

import pytest
from structlog.testing import capture_logs

from ctms import acoustic_service
from ctms.acoustic_service import transform_field_for_acoustic
from ctms.crud import get_contact_by_email_id, get_newsletters_by_email_id
from ctms.schemas.contact import ContactSchema

CTMS_ACOUSTIC_MAIN_TABLE_ID = "1"
CTMS_ACOUSTIC_NEWSLETTER_TABLE_ID = "9"
CTMS_ACOUSTIC_PRODUCT_TABLE_ID = "10"
CTMS_ACOUSTIC_WAITLIST_TABLE_ID = "11"


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
            timeout=1.0,
        )


@pytest.fixture
def base_ctms_acoustic_service(acoustic_client):
    with mock.patch("ctms.acoustic_service.Acoustic"):
        yield acoustic_service.CTMSToAcousticService(
            acoustic_client=acoustic_client,
            acoustic_main_table_id=CTMS_ACOUSTIC_MAIN_TABLE_ID,
            acoustic_newsletter_table_id=CTMS_ACOUSTIC_NEWSLETTER_TABLE_ID,
            acoustic_waitlist_table_id=CTMS_ACOUSTIC_WAITLIST_TABLE_ID,
            acoustic_product_table_id=CTMS_ACOUSTIC_PRODUCT_TABLE_ID,
        )


@pytest.fixture
def metrics_ctms_acoustic_service(acoustic_client, background_metric_service):
    with mock.patch("ctms.acoustic_service.Acoustic"):
        yield acoustic_service.CTMSToAcousticService(
            acoustic_client=acoustic_client,
            acoustic_main_table_id=CTMS_ACOUSTIC_MAIN_TABLE_ID,
            acoustic_newsletter_table_id=CTMS_ACOUSTIC_NEWSLETTER_TABLE_ID,
            acoustic_waitlist_table_id=CTMS_ACOUSTIC_WAITLIST_TABLE_ID,
            acoustic_product_table_id=CTMS_ACOUSTIC_PRODUCT_TABLE_ID,
            metric_service=background_metric_service,
        )


def test_base_service_creation(base_ctms_acoustic_service):
    assert base_ctms_acoustic_service is not None


def test_ctms_to_acoustic_no_product(
    base_ctms_acoustic_service,
    minimal_contact,
    maximal_contact,
    example_contact,
    main_acoustic_fields,
    waitlist_acoustic_fields,
    acoustic_newsletters_mapping,
):
    for i, contact in enumerate([minimal_contact, maximal_contact, example_contact]):
        assert len(contact.products) == 0
        _, _, _, products = base_ctms_acoustic_service.convert_ctms_to_acoustic(
            contact,
            main_acoustic_fields,
            waitlist_acoustic_fields,
            acoustic_newsletters_mapping,
        )
        assert len(products) == 0, f"{i + 1}/3: no products in contact."


def test_ctms_to_acoustic_newsletters(
    dbsession,
    base_ctms_acoustic_service,
    email_factory,
    main_acoustic_fields,
    waitlist_acoustic_fields,
):
    email = email_factory(newsletters=5)
    email.newsletters[2].subscribed = False
    email.newsletters[2].unsub_reason = "not interested"
    dbsession.commit()

    contact = ContactSchema.from_email(email)

    acoustic_newsletters_mapping = {
        contact.newsletters[0].name: "sub_column_1",
        contact.newsletters[1].name: "sub_column_2",
        contact.newsletters[2].name: "sub_column_3",
    }

    (main, newsletter_rows, _, _) = base_ctms_acoustic_service.convert_ctms_to_acoustic(
        contact,
        main_acoustic_fields,
        waitlist_acoustic_fields,
        acoustic_newsletters_mapping,
    )

    # As many records in the newsletters relation table as in contact
    assert len(newsletter_rows) == len(contact.newsletters)
    # `newsletter_name` for all names
    assert sorted(nl["newsletter_name"] for nl in newsletter_rows) == sorted(
        nl.name for nl in contact.newsletters
    )
    # `email_id` column
    assert all(nl["email_id"] == str(contact.email.email_id) for nl in newsletter_rows)
    # `source` column
    assert sorted(nl["newsletter_source"] for nl in newsletter_rows) == sorted(
        nl.source for nl in contact.newsletters
    )
    # `subscribed` column
    assert newsletter_rows[1]["subscribed"] == "Yes"
    assert newsletter_rows[2]["subscribed"] == "No"
    assert newsletter_rows[3]["subscribed"] == "Yes"
    # Newsletters in mapping are marked as subscribed in main table
    assert main["sub_column_1"] == "1"
    assert main["sub_column_2"] == "1"
    assert main["sub_column_3"] == "0"
    # Newsletters not in mapping are listed as skipped
    assert sorted(base_ctms_acoustic_service.context["newsletters_skipped"]) == sorted(
        [
            contact.newsletters[3].name,
            contact.newsletters[4].name,
        ]
    )


def test_ctms_to_acoustic_newsletter_timestamps(
    dbsession,
    base_ctms_acoustic_service,
    minimal_contact,
    main_acoustic_fields,
    waitlist_acoustic_fields,
    acoustic_newsletters_mapping,
):
    # Set timestamps on DB objects.
    newsletters = get_newsletters_by_email_id(dbsession, minimal_contact.email.email_id)
    app_dev_nl = [nl for nl in newsletters if nl.name == "app-dev"][0]
    app_dev_nl.create_timestamp = "1982-05-08T13:20"
    app_dev_nl.update_timestamp = "2023-06-19T12:17"
    dbsession.add(app_dev_nl)
    dbsession.commit()
    # Reload contact from DB.
    minimal_contact = get_contact_by_email_id(dbsession, minimal_contact.email.email_id)

    (_, newsletters_rows, _, _) = base_ctms_acoustic_service.convert_ctms_to_acoustic(
        minimal_contact,
        main_acoustic_fields,
        waitlist_acoustic_fields,
        acoustic_newsletters_mapping,
    )

    app_dev_row = [r for r in newsletters_rows if r["newsletter_name"] == "app-dev"][0]
    assert app_dev_row["create_timestamp"] == "1982-05-08"
    assert app_dev_row["update_timestamp"] == "2023-06-19"


def test_ctms_to_acoustic_waitlists_minimal(
    base_ctms_acoustic_service,
    minimal_contact,
    main_acoustic_fields,
    waitlist_acoustic_fields,
    acoustic_newsletters_mapping,
):
    main, _, _, _ = base_ctms_acoustic_service.convert_ctms_to_acoustic(
        minimal_contact,
        main_acoustic_fields,
        waitlist_acoustic_fields,
        acoustic_newsletters_mapping,
    )
    assert len(minimal_contact.waitlists) == 0
    assert main["vpn_waitlist_geo"] == ""
    assert main["vpn_waitlist_platform"] == ""
    assert main["relay_waitlist_geo"] == ""


def test_ctms_to_acoustic_waitlists_maximal(
    base_ctms_acoustic_service,
    maximal_contact,
    main_acoustic_fields,
    waitlist_acoustic_fields,
    acoustic_newsletters_mapping,
):
    main, _, waitlist_records, _ = base_ctms_acoustic_service.convert_ctms_to_acoustic(
        maximal_contact,
        main_acoustic_fields,
        waitlist_acoustic_fields,
        acoustic_newsletters_mapping,
    )
    assert len(maximal_contact.waitlists) == 4
    assert main["vpn_waitlist_geo"] == "ca"
    assert main["vpn_waitlist_platform"] == "windows,android"
    assert main["relay_waitlist_geo"] == "cn"

    assert [sorted(wl.keys()) for wl in waitlist_records] == (
        len(maximal_contact.waitlists)
        * [
            [
                "create_timestamp",
                "email_id",
                "subscribed",
                "unsub_reason",
                "update_timestamp",
                "waitlist_geo",  # from `waitlist_acoustic_fields`
                "waitlist_name",
                "waitlist_platform",  # ditto
                "waitlist_source",
            ]
        ]
    )

    waitlist_records_by_name = {wl["waitlist_name"]: wl for wl in waitlist_records}
    assert waitlist_records_by_name["vpn"]["email_id"] == str(
        maximal_contact.email.email_id
    )
    assert waitlist_records_by_name["vpn"]["subscribed"]
    assert waitlist_records_by_name["vpn"]["unsub_reason"] == ""
    assert waitlist_records_by_name["vpn"]["waitlist_geo"] == "ca"
    assert waitlist_records_by_name["vpn"]["waitlist_platform"] == "windows,android"
    assert waitlist_records_by_name["a-software"]["waitlist_geo"] == "fr"
    assert waitlist_records_by_name["a-software"]["waitlist_platform"] == ""


def test_ctms_to_acoustic_minimal_fields(
    base_ctms_acoustic_service,
    minimal_contact,
    main_acoustic_fields,
    waitlist_acoustic_fields,
    acoustic_newsletters_mapping,
):
    main, _, _, _ = base_ctms_acoustic_service.convert_ctms_to_acoustic(
        minimal_contact,
        main_acoustic_fields,
        waitlist_acoustic_fields,
        acoustic_newsletters_mapping,
    )
    assert main["email"] == minimal_contact.email.primary_email
    assert main["basket_token"] == str(minimal_contact.email.basket_token)
    assert main["mailing_country"] == minimal_contact.email.mailing_country
    assert "skipped_fields" not in base_ctms_acoustic_service.context


def test_ctms_to_acoustic_maximal_fields(
    base_ctms_acoustic_service,
    maximal_contact,
    main_acoustic_fields,
    waitlist_acoustic_fields,
    acoustic_newsletters_mapping,
):
    skip_fields = main_acoustic_fields - {"mailing_country"}
    main, _, _, _ = base_ctms_acoustic_service.convert_ctms_to_acoustic(
        maximal_contact,
        skip_fields,
        waitlist_acoustic_fields,
        acoustic_newsletters_mapping,
    )

    assert main["email"] == maximal_contact.email.primary_email
    assert main["basket_token"] == str(maximal_contact.email.basket_token)
    assert main["fxa_id"] == maximal_contact.fxa.fxa_id
    assert base_ctms_acoustic_service.context["skipped_fields"] == [
        "email.mailing_country"
    ]


# Expected log context from successful .attempt_to_upload_ctms_contact()
EXPECTED_LOG = {
    "email_id": "CHANGE_ME",
    "event": "Successfully sync'd contact to acoustic...",
    "fxa_created_date_converted": "success",
    "log_level": "debug",
    "newsletter_count": 0,
    "product_count": 0,
    "success": True,
}


def test_ctms_to_acoustic_mocked(
    base_ctms_acoustic_service,
    maximal_contact,
    main_acoustic_fields,
    waitlist_acoustic_fields,
    acoustic_newsletters_mapping,
):
    acoustic_mock: MagicMock = MagicMock()
    base_ctms_acoustic_service.acoustic = acoustic_mock
    (
        main_row,
        newsletter_rows,
        waitlist_rows,
        product_rows,
    ) = base_ctms_acoustic_service.convert_ctms_to_acoustic(
        maximal_contact,
        main_acoustic_fields,
        waitlist_acoustic_fields,
        acoustic_newsletters_mapping,
    )  # To be used as in testing, for expected inputs to downstream methods
    assert main_row
    assert len(newsletter_rows) > 0
    assert len(waitlist_rows) > 0
    assert len(product_rows) == 0
    with capture_logs() as caplog:
        base_ctms_acoustic_service.attempt_to_upload_ctms_contact(
            maximal_contact,
            main_acoustic_fields,
            waitlist_acoustic_fields,
            acoustic_newsletters_mapping,
        )

    acoustic_mock.add_recipient.assert_called_with(
        list_id=CTMS_ACOUSTIC_MAIN_TABLE_ID,
        created_from=3,
        update_if_found="TRUE",
        allow_html=False,
        sync_fields={"email_id": main_row["email_id"]},
        columns=main_row,
    )

    acoustic_mock.insert_update_relational_table.assert_any_call(
        table_id=CTMS_ACOUSTIC_NEWSLETTER_TABLE_ID, rows=newsletter_rows
    )

    acoustic_mock.insert_update_relational_table.assert_any_call(
        table_id=CTMS_ACOUSTIC_WAITLIST_TABLE_ID, rows=waitlist_rows
    )

    acoustic_mock.insert_update_product_table.assert_not_called()

    assert len(caplog) == 1
    expected_log = EXPECTED_LOG.copy()
    expected_log.update(
        {
            "email_id": "67e52c77-950f-4f28-accb-bb3ea1a2c51a",
            "newsletter_count": len(newsletter_rows),
            "newsletters_skipped": ["ambassadors", "firefox-os"],
        }
    )
    assert caplog[0] == expected_log


def test_ctms_to_acoustic_with_subscription(
    dbsession,
    stripe_subscription_factory,
    base_ctms_acoustic_service,
    main_acoustic_fields,
    waitlist_acoustic_fields,
    acoustic_newsletters_mapping,
):
    subscription = stripe_subscription_factory()
    dbsession.commit()

    contact = get_contact_by_email_id(dbsession, email_id=subscription.get_email_id())
    contact = ContactSchema.parse_obj(contact)

    acoustic_mock = MagicMock()
    base_ctms_acoustic_service.acoustic = acoustic_mock
    (
        main_row,
        newsletter_rows,
        waitlist_rows,
        product_rows,
    ) = base_ctms_acoustic_service.convert_ctms_to_acoustic(
        contact,
        main_acoustic_fields,
        waitlist_acoustic_fields,
        acoustic_newsletters_mapping,
    )  # To be used as in testing, for expected inputs to downstream methods
    assert main_row
    assert len(newsletter_rows) == 0  # None in Main Table Subscriber flags
    assert len(waitlist_rows) == 0
    assert len(product_rows) == 1
    assert all(
        isinstance(value, str) for value in product_rows[0].values()
    ), product_rows[0]

    with capture_logs() as caplog:
        base_ctms_acoustic_service.attempt_to_upload_ctms_contact(
            contact,
            main_acoustic_fields,
            waitlist_acoustic_fields,
            acoustic_newsletters_mapping,
        )

    acoustic_mock.insert_update_relational_table.assert_called_with(
        table_id=CTMS_ACOUSTIC_PRODUCT_TABLE_ID, rows=product_rows
    )

    assert len(caplog) == 1
    expected_log = EXPECTED_LOG.copy()
    expected_log.update(
        {
            "email_id": str(contact.email.email_id),
            "product_count": 1,
        }
    )
    assert caplog[0] == expected_log


def test_ctms_to_acoustic_with_subscription_and_metrics(
    dbsession,
    metrics_ctms_acoustic_service,
    stripe_subscription_factory,
    stripe_price_factory,
    main_acoustic_fields,
    waitlist_acoustic_fields,
    acoustic_newsletters_mapping,
):
    price = stripe_price_factory(stripe_id="price_test", stripe_product_id="prod_test")
    subscription = stripe_subscription_factory(
        stripe_created=datetime.datetime(2021, 9, 27, 0, 0, 0),
        current_period_end=datetime.datetime(2021, 11, 27, 0, 0, 0),
        current_period_start=datetime.datetime(2021, 10, 27, 0, 0, 0),
        start_date=datetime.datetime(2021, 9, 27, 0, 0, 0),
        subscription_items__price=price,
    )
    dbsession.commit()

    contact = get_contact_by_email_id(dbsession, email_id=subscription.get_email_id())
    contact = ContactSchema.parse_obj(contact)

    acoustic_mock = MagicMock()
    acoustic_svc = metrics_ctms_acoustic_service
    acoustic_svc.acoustic = acoustic_mock
    (
        main_row,
        newsletter_rows,
        waitlist_rows,
        product_rows,
    ) = acoustic_svc.convert_ctms_to_acoustic(
        contact,
        main_acoustic_fields,
        waitlist_acoustic_fields,
        acoustic_newsletters_mapping,
    )  # To be used as in testing, for expected inputs to downstream methods
    assert main_row
    assert len(newsletter_rows) == 0  # None in Main Table Subscriber flags
    assert len(waitlist_rows) == 0
    assert len(product_rows) == 1

    # Alpha-sorted, to ease cross-check with Acoustic table displays
    expected_product = {
        "amount": "1000",
        "billing_country": "",
        "cancel_at_period_end": "No",
        "canceled_at": "",
        "card_brand": "",
        "card_last4": "",
        "changed": "09/27/2021 00:00:00",
        "created": "09/27/2021 00:00:00",
        "currency": "usd",
        "current_period_end": "11/27/2021 00:00:00",
        "current_period_start": "10/27/2021 00:00:00",
        "email_id": str(subscription.get_email_id()),
        "ended_at": "",
        "interval": "month",
        "interval_count": "1",
        "payment_service": "stripe",
        "payment_type": "",
        "price_id": "price_test",
        "product_id": "prod_test",
        "product_name": "",
        "segment": "active",
        "start": "09/27/2021 00:00:00",
        "status": "active",
        "sub_count": "1",
    }
    assert product_rows[0] == expected_product

    with capture_logs() as caplog:
        acoustic_svc.attempt_to_upload_ctms_contact(
            contact,
            main_acoustic_fields,
            waitlist_acoustic_fields,
            acoustic_newsletters_mapping,
        )

    acoustic_mock.insert_update_relational_table.assert_called_with(
        table_id=CTMS_ACOUSTIC_PRODUCT_TABLE_ID, rows=product_rows
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

    assert len(caplog) == 1
    log = caplog[0]
    expected_log = EXPECTED_LOG.copy()
    expected_log.update(
        {
            "email_id": str(contact.email.email_id),
            "product_count": 1,
            "main_status": "success",
            "product_status": "success",
            "main_duration_s": log["main_duration_s"],
            "product_duration_s": log["product_duration_s"],
        }
    )
    assert log == expected_log


def test_ctms_to_acoustic_traced_email(
    base_ctms_acoustic_service,
    example_contact,
    main_acoustic_fields,
    waitlist_acoustic_fields,
    acoustic_newsletters_mapping,
):
    """A contact requesting tracing is traced in the logs."""
    email = "tester+trace-me-mozilla-nov24@example.com"
    example_contact.email.primary_email = email
    acoustic_mock: MagicMock = MagicMock()
    base_ctms_acoustic_service.acoustic = acoustic_mock

    with capture_logs() as caplog:
        base_ctms_acoustic_service.attempt_to_upload_ctms_contact(
            example_contact,
            main_acoustic_fields,
            waitlist_acoustic_fields,
            acoustic_newsletters_mapping,
        )

    assert len(caplog) == 1
    assert caplog[0] == {
        **EXPECTED_LOG,
        "email_id": "332de237-cab7-4461-bcc3-48e68f42bd5c",
        "newsletter_count": 2,
        "newsletters_skipped": ["firefox-welcome", "mozilla-welcome"],
        "trace": email,
    }


@pytest.mark.parametrize(
    "value, expected",
    (
        ("string", "string"),
        (True, "Yes"),
        (False, "No"),
        (None, ""),
        (
            UUID("62d8d3c6-95f3-4ed6-b176-7f69acff22f6"),
            "62d8d3c6-95f3-4ed6-b176-7f69acff22f6",
        ),
        (
            datetime.datetime(2021, 11, 8, 9, 6, tzinfo=datetime.timezone.utc),
            "11/08/2021 09:06:00",
        ),
        (datetime.date(2021, 11, 8), "11/08/2021"),
    ),
)
def test_transform_field_for_acoustic(value, expected):
    assert transform_field_for_acoustic(value) == expected


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
