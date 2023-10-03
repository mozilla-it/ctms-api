import logging
import os
from uuid import uuid4

import backoff
import pytest
import requests
from pydantic import BaseSettings

from tests.conftest import FuzzyAssert

TEST_FOLDER = os.path.dirname(os.path.realpath(__file__))


class Settings(BaseSettings):
    basket_server_url: str = "http://127.0.0.1:9000"
    ctms_server_url: str = "http://127.0.0.1:8000"
    # We initialize CTMS api client id/secret in `ctms-db-init.sql`
    ctms_client_id: str = "id_integration-test"
    ctms_client_secret: str

    class Config:
        env_file = os.path.join(TEST_FOLDER, "basket.env")


settings = Settings()

retry_until_pass = backoff.on_exception(backoff.expo, AssertionError)

# Show the failing retried assertions in console.
backoff_logger = logging.getLogger("backoff")
backoff_logger.addHandler(logging.StreamHandler())


@pytest.fixture(scope="session", autouse=True)
def adjust_backoff_logger(pytestconfig):
    # Detect whether pytest was run using `-v` or `-vv` and logging.
    backoff_logger.setLevel(
        logging.INFO if pytestconfig.getoption("verbose") > 0 else logging.ERROR
    )


@pytest.fixture(scope="session")
def ctms_headers():
    """
    Trade the cliend id + secret for a bearer access token, and
    build the headers to be used on the server.

    TODO: use context manager with a requests session
    """
    resp = requests.post(
        f"{settings.ctms_server_url}/token",
        files={
            "grant_type": (None, "client_credentials"),
        },
        auth=(settings.ctms_client_id, settings.ctms_client_secret),
    )
    resp.raise_for_status()
    token = resp.json()
    return {
        "Authorization": f'{token["token_type"]} {token["access_token"]}',
    }


def basket_subscribe(email, waitlist, **kwargs):
    subscribe_url = f"{settings.basket_server_url}/news/subscribe/"
    form_data = {
        "email": email,
        "newsletters": waitlist,
        "format": "html",
        "country": "us",
        "lang": "en",
        "source_url": "https://www.mozilla.org/es-ES/products/vpn/invite/",
        **kwargs,
    }
    resp = requests.post(subscribe_url, data=form_data)
    resp.raise_for_status()
    assert resp.json()["status"] == "ok", resp.text
    return resp


def basket_unsubscribe(basket_token, waitlist):
    unsubscribe_url = f"{settings.basket_server_url}/news/unsubscribe/{basket_token}/"
    resp = requests.post(unsubscribe_url, data={"newsletters": waitlist})
    resp.raise_for_status()
    return resp


def ctms_fetch(email, ctms_headers):
    resp = requests.get(
        f"{settings.ctms_server_url}/ctms",
        params={"primary_email": email},
        headers=ctms_headers,
    )
    resp.raise_for_status()
    results = resp.json()
    assert len(results) == 1, f"Contact {email} does not exist in CTMS"
    contact_details = results[0]
    return contact_details


@pytest.mark.parametrize(
    "url",
    (
        f"{settings.basket_server_url}/readiness/",
        f"{settings.basket_server_url}/healthz/",
        f"{settings.ctms_server_url}/__heartbeat__",
    ),
)
def test_connectivity(url):
    resp = requests.get(url)
    resp.raise_for_status()


def test_vpn_waitlist(ctms_headers):
    # 1. Subscribe a certain email to the `vpn` waitlist
    email = f"integration-test-{uuid4()}@restmail.net"
    vpn_waitlist_slug = "guardian-vpn-waitlist"

    basket_subscribe(
        email, vpn_waitlist_slug, fpn_country="us", fpn_platform="ios,android"
    )

    # 2. Basket should have set the `vpn_waitlist` field/data.
    # Wait for the worker to have processed the request.
    @retry_until_pass
    def fetch_created():
        return ctms_fetch(email, ctms_headers)

    contact_details = fetch_created()
    assert contact_details["newsletters"] == []
    assert contact_details["waitlists"] == [
        {
            "name": "vpn",
            "source": "https://www.mozilla.org/es-ES/products/vpn/invite/",
            "fields": {
                "geo": "us",
                "platform": "ios,android",
            },
            "subscribed": True,
            "unsub_reason": None,
            "create_timestamp": FuzzyAssert.iso8601(),
            "update_timestamp": FuzzyAssert.iso8601(),
        }
    ]
    # Legacy (read-only) fields.
    assert contact_details["vpn_waitlist"] == {
        "geo": "us",
        "platform": "ios,android",
    }

    # 3. Patch an attribute (eg. change country)
    email_id = contact_details["email"]["email_id"]
    resp = requests.patch(
        f"{settings.ctms_server_url}/ctms/{email_id}",
        headers=ctms_headers,
        json={
            "waitlists": [
                {
                    "name": "vpn",
                    "fields": {"geo": "fr", "platform": "linux"},
                }
            ],
        },
    )
    resp.raise_for_status()
    # Request the full contact details again.
    contact_details = ctms_fetch(email, ctms_headers)
    assert contact_details["newsletters"] == []
    assert contact_details["waitlists"] == [
        {
            "name": "vpn",
            "source": "https://www.mozilla.org/es-ES/products/vpn/invite/",
            "fields": {
                "geo": "fr",
                "platform": "linux",
            },
            "subscribed": True,
            "unsub_reason": None,
            "create_timestamp": FuzzyAssert.iso8601(),
            "update_timestamp": FuzzyAssert.iso8601(),
        }
    ]
    # Legacy (read-only) fields.
    assert contact_details["vpn_waitlist"] == {
        "geo": "fr",
        "platform": "linux",
    }

    # 4. Unsubscribe via Basket
    basket_token = contact_details["email"]["basket_token"]
    basket_unsubscribe(basket_token, vpn_waitlist_slug)

    # Request the full contact details again.
    # Wait for the worker to have processed the request.
    @retry_until_pass
    def check_updated():
        contact_details = ctms_fetch(email, ctms_headers)
        assert contact_details["newsletters"] == []
        assert not contact_details["waitlists"][0]["subscribed"]
        # Legacy (read-only) fields.
        assert contact_details["vpn_waitlist"] == {
            "geo": None,
            "platform": None,
        }

    check_updated()


def test_relay_waitlists(ctms_headers):
    email = f"stage-test-{uuid4()}@restmail.net"
    relay_waitlist_slug = "relay-waitlist"

    # 1. Subscribe a certain email to the `relay` waitlist
    basket_subscribe(
        email,
        relay_waitlist_slug,
        relay_country="es",
        source_url="https://relay.firefox.com/",
    )

    # 2. Basket should have set the `relay_waitlist` field/data.
    # Wait for the worker to have processed the request.
    @retry_until_pass
    def fetch_created():
        return ctms_fetch(email, ctms_headers)

    contact_details = fetch_created()

    # 3. CTMS should show both formats (legacy `relay_waitlist` field, and entry in `waitlists` list)
    assert contact_details["waitlists"] == [
        {
            "name": "relay",
            "source": "https://relay.firefox.com/",
            "fields": {
                "geo": "es",
            },
            "subscribed": True,
            "unsub_reason": None,
            "create_timestamp": FuzzyAssert.iso8601(),
            "update_timestamp": FuzzyAssert.iso8601(),
        }
    ]
    # Legacy (read-only) fields.
    assert contact_details["relay_waitlist"] == {
        "geo": "es",
    }

    # 4. Subscribe to another relay waitlist, from another country.
    relay_vpn_bundle_waitlist_slug = "relay-vpn-bundle-waitlist"
    basket_subscribe(
        email,
        relay_vpn_bundle_waitlist_slug,
        relay_country="fr",
        source_url="https://relay.firefox.com/vpn-relay/waitlist/",
    )

    @retry_until_pass
    def check_subscribed():
        details = ctms_fetch(email, ctms_headers)
        # CTMS has both waitlists.
        assert len(details["waitlists"]) == 2
        return details

    contact_details = check_subscribed()
    assert contact_details["newsletters"] == []
    assert contact_details["waitlists"] == [
        {
            "name": "relay",
            "source": "https://relay.firefox.com/",
            "fields": {
                "geo": "es",
            },
            "subscribed": True,
            "unsub_reason": None,
            "create_timestamp": FuzzyAssert.iso8601(),
            "update_timestamp": FuzzyAssert.iso8601(),
        },
        {
            "name": "relay-vpn-bundle",
            "source": "https://relay.firefox.com/vpn-relay/waitlist/",
            "fields": {
                "geo": "fr",
            },
            "subscribed": True,
            "unsub_reason": None,
            "create_timestamp": FuzzyAssert.iso8601(),
            "update_timestamp": FuzzyAssert.iso8601(),
        },
    ]
    # Legacy (read-only) fields.
    # If multiple `relay-` waitlists are present, the `geo` field of the
    # first waitlist is set as the value of `relay_waitlist["geo"]`.
    assert contact_details["relay_waitlist"] == {
        "geo": "es",
    }

    # 5. Unsubscribe from one Relay waitlist.
    basket_token = contact_details["email"]["basket_token"]
    basket_unsubscribe(basket_token, relay_waitlist_slug)

    # Wait for the worker to have processed the request.
    @retry_until_pass
    def check_unsubscribed():
        details = ctms_fetch(email, ctms_headers)
        # CTMS has now one subscribed waitlist.
        assert len([wl for wl in details["waitlists"] if wl["subscribed"]]) == 1
        return details

    contact_details = check_unsubscribed()
    # And only one newsletter subscribed.
    assert contact_details["newsletters"] == []
    assert contact_details["waitlists"] == [
        {
            "fields": {"geo": "es"},
            "name": "relay",
            "source": "https://relay.firefox.com/",
            "subscribed": False,
            "unsub_reason": None,
            "create_timestamp": FuzzyAssert.iso8601(),
            "update_timestamp": FuzzyAssert.iso8601(),
        },
        {
            "name": "relay-vpn-bundle",
            "source": "https://relay.firefox.com/vpn-relay/waitlist/",
            "fields": {
                "geo": "fr",
            },
            "subscribed": True,
            "unsub_reason": None,
            "create_timestamp": FuzzyAssert.iso8601(),
            "update_timestamp": FuzzyAssert.iso8601(),
        },
    ]
    # Legacy (read-only) fields.
    # relay_waitlist geo is pulled from the remaining waitlist.
    assert contact_details["relay_waitlist"] == {
        "geo": "fr",
    }

    # 6. Unsubscribe from the last Relay waitlist.
    basket_unsubscribe(basket_token, relay_vpn_bundle_waitlist_slug)

    # Wait for the worker to have processed the request.
    @retry_until_pass
    def check_unsubscribed_last():
        details = ctms_fetch(email, ctms_headers)
        # CTMS has no more subscribed waitlist or newsletter.
        assert not any(wl["subscribed"] for wl in details["waitlists"])
        return details

    contact_details = check_unsubscribed_last()
    assert contact_details["newsletters"] == []
    # Legacy (read-only) fields.
    # Relay attribute is now empty
    assert contact_details["relay_waitlist"] == {"geo": None}
