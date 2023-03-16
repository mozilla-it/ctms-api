import os
import time
from uuid import uuid4

import pytest
import requests
from pydantic import BaseSettings


class Settings(BaseSettings):
    basket_url: str = "http://127.0.0.1:9000"
    ctms_url: str = "http://127.0.0.1:8000"
    # See `ctms-db-init.sql`
    ctms_client_id: str = "id_integration-test"
    ctms_secret: str = (
        "secret_xPS8MJSswx1IYOniwXZUV3vNQ5YnYJz5H1UkOSLKqrk"  # pragma: allowlist secret
    )


settings = Settings()


@pytest.fixture
def ctms_headers():
    """
    Trade the cliend id + secret for a bearer access token, and
    build the headers to be used on the server.

    TODO: use context manager with a requests session
    """
    resp = requests.post(
        f"{settings.ctms_url}/token",
        files={
            "grant_type": (None, "client_credentials"),
        },
        auth=(settings.ctms_client_id, settings.ctms_secret),
    )
    resp.raise_for_status()
    token = resp.json()
    return {
        "Authorization": f'{token["token_type"]} {token["access_token"]}',
    }


def test_integration(ctms_headers):
    # 1. Subscribe a certain email to a waitlist (eg. `vpn`)
    email = f"stage-test-{uuid4()}@restmail.net"
    waitlist = "guardian-vpn-waitlist"

    print(f"Subscribe {email} to {waitlist}", end="...")
    subscribe_url = f"{settings.basket_url}/news/subscribe/"
    form_data = {
        "email": email,
        "newsletters": waitlist,
        "fpn_country": "us",
        "fpn_platform": "ios,android",
        "format": "html",
        "country": "us",
        "lang": "en",
        "source_url": "https://relay.firefox.com/vpn-relay/waitlist/",
    }
    resp = requests.post(subscribe_url, data=form_data)
    resp.raise_for_status()
    assert resp.json()["status"] == "ok", resp.text
    print("OK")

    # 2. Basket should have set the `vpn_waitlist` field/data.
    # Wait for the worker to have processed the request.
    time.sleep(0.5)
    resp = requests.get(
        f"{settings.ctms_url}/ctms",
        params={"primary_email": email},
        headers=ctms_headers,
    )
    resp.raise_for_status()
    results = resp.json()
    assert len(results) == 1, "Contact was saved in CTMS"
    contact_details = results[0]
    email_id = contact_details["email"]["email_id"]

    # 3. CTMS should show both formats (legacy `vpn_waitlist` field, and entry in `waitlists` list)
    assert contact_details["waitlists"] == [
        {
            "name": "vpn",
            "source": None,  # not yet supported in basket
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
    resp = requests.patch(
        f"{settings.ctms_url}/ctms/{email_id}",
        headers=ctms_headers,
        json={
            "vpn_waitlist": {"geo": "fr", "platform": "linux"},
        },
    )
    resp.raise_for_status()
    # Request the full contact details again.
    resp = requests.get(
        f"{settings.ctms_url}/ctms",
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
    unsubscribe_url = f"{settings.basket_url}/news/unsubscribe/{basket_token}/"
    resp = requests.post(unsubscribe_url, data={"newsletters": waitlist})
    resp.raise_for_status()

    # Request the full contact details again.
    # Wait for the worker to have processed the request.
    time.sleep(0.5)
    resp = requests.get(
        f"{settings.ctms_url}/ctms",
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

    # TODO: check (or implement) these behaviours with legacy format:
    # - unsubscribe from "guardian-vpn-waitlist" newsletter also unenrolls from "vpn" waitlist
    # - unsubscribe from "relay*" newsletters un-enrolls if there is no other relay* subscribed
    #
    # The new format once https://github.com/mozmeao/basket/pull/962 is merged should :) manage
    # these as expected.
