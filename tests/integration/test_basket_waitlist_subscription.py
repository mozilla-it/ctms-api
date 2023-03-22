import os
import time
from uuid import uuid4

import pytest
import requests
from pydantic import BaseSettings

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


@pytest.fixture
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
    waitlist = "guardian-vpn-waitlist"

    print(f"Subscribe {email} to {waitlist}", end="...")
    subscribe_url = f"{settings.basket_server_url}/news/subscribe/"
    form_data = {
        "email": email,
        "newsletters": waitlist,
        "fpn_country": "us",
        "fpn_platform": "ios,android",
        "format": "html",
        "country": "us",
        "lang": "en",
        "source_url": "https://www.mozilla.org/es-ES/products/vpn/invite/",
    }
    resp = requests.post(subscribe_url, data=form_data)
    resp.raise_for_status()
    assert resp.json()["status"] == "ok", resp.text
    print("OK")

    # 2. Basket should have set the `vpn_waitlist` field/data.
    # Wait for the worker to have processed the request.
    time.sleep(1)
    print(f"Check CTMS for {email}", end="...")
    resp = requests.get(
        f"{settings.ctms_server_url}/ctms",
        params={"primary_email": email},
        headers=ctms_headers,
    )
    resp.raise_for_status()
    print("OK")
    results = resp.json()
    assert len(results) == 1, "Contact was saved in CTMS"
    contact_details = results[0]

    # 3. CTMS should show both formats (legacy `vpn_waitlist` field, and entry in `waitlists` list)
    assert contact_details["waitlists"] == [
        {
            "name": "vpn",
            "source": None,
            "fields": {
                "geo": "us",
                "platform": "ios,android",
            },
        }
    ]

    assert contact_details["vpn_waitlist"] == {
        "geo": "us",
        "platform": "ios,android",
    }

    # 4. Patch an attribute (eg. change country)
    print("Change country field", end="...")
    email_id = contact_details["email"]["email_id"]
    resp = requests.patch(
        f"{settings.ctms_server_url}/ctms/{email_id}",
        headers=ctms_headers,
        json={
            "vpn_waitlist": {"geo": "fr", "platform": "linux"},
        },
    )
    resp.raise_for_status()
    # Request the full contact details again.
    resp = requests.get(
        f"{settings.ctms_server_url}/ctms",
        params={"primary_email": email},
        headers=ctms_headers,
    )
    resp.raise_for_status()
    results = resp.json()
    assert len(results) == 1
    contact_details = results[0]
    assert contact_details["vpn_waitlist"] == {
        "geo": "fr",
        "platform": "linux",
    }
    print("OK")

    newsletters_by_name = {nl["name"]: nl for nl in contact_details["newsletters"]}
    assert newsletters_by_name[waitlist]["subscribed"]

    # 5. Unsubscribe from Basket
    print("Unsubscribe from Basket", end="...")
    basket_token = contact_details["email"]["basket_token"]
    unsubscribe_url = f"{settings.basket_server_url}/news/unsubscribe/{basket_token}/"
    resp = requests.post(unsubscribe_url, data={"newsletters": waitlist})
    resp.raise_for_status()

    # Request the full contact details again.
    # Wait for the worker to have processed the request.
    time.sleep(1)
    resp = requests.get(
        f"{settings.ctms_server_url}/ctms",
        params={"primary_email": email},
        headers=ctms_headers,
    )
    resp.raise_for_status()
    results = resp.json()
    assert len(results) == 1
    contact_details = results[0]

    newsletters_by_name = {nl["name"]: nl for nl in contact_details["newsletters"]}
    assert not newsletters_by_name[waitlist]["subscribed"]
    assert contact_details["vpn_waitlist"] == {
        "geo": None,
        "platform": None,
    }
    print("OK")


def test_relay_waitlists(ctms_headers):
    email = f"stage-test-{uuid4()}@restmail.net"
    waitlist = "relay-waitlist"

    print(f"Subscribe {email} to {waitlist}", end="...")
    subscribe_url = f"{settings.basket_server_url}/news/subscribe/"
    form_data = {
        "email": email,
        "newsletters": waitlist,
        "relay_country": "es",
        "format": "html",
        "country": "us",
        "lang": "en",
        "source_url": "https://relay.firefox.com/",
    }
    resp = requests.post(subscribe_url, data=form_data)
    resp.raise_for_status()
    assert resp.json()["status"] == "ok", resp.text
    print("OK")

    # 2. Basket should have set the `relay_waitlist` field/data.
    # Wait for the worker to have processed the request.
    time.sleep(1)
    resp = requests.get(
        f"{settings.ctms_server_url}/ctms",
        params={"primary_email": email},
        headers=ctms_headers,
    )
    resp.raise_for_status()
    results = resp.json()
    assert len(results) == 1, "Contact was saved in CTMS"
    contact_details = results[0]

    # 3. CTMS should show both formats (legacy `relay_waitlist` field, and entry in `waitlists` list)
    assert contact_details["waitlists"] == [
        {
            "name": "relay",
            "source": None,
            "fields": {
                "geo": "es",
            },
        }
    ]

    assert contact_details["relay_waitlist"] == {
        "geo": "es",
    }

    # 4. Subscribe to another relay waitlist, from another country.
    waitlist = "relay-vpn-bundle-waitlist"
    print(f"Subscribe {email} to {waitlist}", end="...")
    subscribe_url = f"{settings.basket_server_url}/news/subscribe/"
    form_data = {
        "email": email,
        "newsletters": waitlist,
        "relay_country": "fr",
        "format": "html",
        "country": "us",
        "lang": "en",
        "source_url": "https://relay.firefox.com/vpn-relay/waitlist/",
    }
    resp = requests.post(subscribe_url, data=form_data)
    resp.raise_for_status()
    assert resp.json()["status"] == "ok", resp.text
    print("OK")
    time.sleep(1)
    resp = requests.get(
        f"{settings.ctms_server_url}/ctms",
        params={"primary_email": email},
        headers=ctms_headers,
    )
    resp.raise_for_status()
    results = resp.json()
    contact_details = results[0]
    # CTMS has both waitlists.
    assert len(contact_details["waitlists"]) == 2
    # CTMS has both newsletters.
    newsletters_by_name = {nl["name"]: nl for nl in contact_details["newsletters"]}
    assert "relay-waitlist" in newsletters_by_name
    assert waitlist in newsletters_by_name
    # Country is taken from one of them.
    assert contact_details["relay_waitlist"] == {
        "geo": "fr",
    }

    # 6. Unsubscribe from one Relay waitlist.
    basket_token = contact_details["email"]["basket_token"]
    unsubscribe_url = f"{settings.basket_server_url}/news/unsubscribe/{basket_token}/"
    resp = requests.post(unsubscribe_url, data={"newsletters": waitlist})
    resp.raise_for_status()
    # Wait for the worker to have processed the request.
    time.sleep(1)
    resp = requests.get(
        f"{settings.ctms_server_url}/ctms",
        params={"primary_email": email},
        headers=ctms_headers,
    )
    resp.raise_for_status()
    results = resp.json()
    contact_details = results[0]
    # CTMS has now one waitlist.
    assert len(contact_details["waitlists"]) == 1
    newsletters_by_name = {nl["name"]: nl for nl in contact_details["newsletters"]}
    # And only one subscribed.
    assert not newsletters_by_name[waitlist]["subscribed"]
    assert newsletters_by_name["relay-waitlist"]["subscribed"]
    # Country is taken from the remaining one.
    assert contact_details["relay_waitlist"] == {
        "geo": "es",
    }

    # 6. Unsubscribe from the last Relay waitlist.
    basket_token = contact_details["email"]["basket_token"]
    unsubscribe_url = f"{settings.basket_server_url}/news/unsubscribe/{basket_token}/"
    resp = requests.post(unsubscribe_url, data={"newsletters": "relay-waitlist"})
    resp.raise_for_status()
    # Wait for the worker to have processed the request.
    time.sleep(1)
    resp = requests.get(
        f"{settings.ctms_server_url}/ctms",
        params={"primary_email": email},
        headers=ctms_headers,
    )
    resp.raise_for_status()
    results = resp.json()
    contact_details = results[0]
    # CTMS has no more waitlist or newsletter.
    assert len(contact_details["waitlists"]) == 0
    assert not any(nl["subscribed"] for nl in contact_details["newsletters"])
    # Relay attribute is now empty
    assert contact_details["relay_waitlist"] == {"geo": None}
