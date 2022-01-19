"""Tests for PATCH /ctms/{email_id}"""
import json
from uuid import uuid4

import pytest
from structlog.testing import capture_logs

from ctms.crud import create_contact, get_email
from ctms.schemas import (
    AddOnsInSchema,
    AddOnsSchema,
    ContactInSchema,
    CTMSResponse,
    EmailSchema,
    FirefoxAccountsInSchema,
    FirefoxAccountsSchema,
    MozillaFoundationInSchema,
    MozillaFoundationSchema,
    RelayWaitlistSchema,
    VpnWaitlistSchema,
)


def swap_bool(existing):
    """Use the opposite of the existing value for this boolean."""
    return not existing


@pytest.mark.parametrize("contact_name", ("minimal", "maximal"))
@pytest.mark.parametrize(
    "group_name,key,value",
    (
        ("amo", "add_on_ids", "new-addon-id"),
        ("amo", "display_name", "New Display Name"),
        ("amo", "email_opt_in", swap_bool),
        ("amo", "language", "es"),
        ("amo", "last_login", "2020-04-07"),
        ("amo", "location", "New Location"),
        ("amo", "profile_url", "firefox/user/14612345"),
        ("amo", "user", swap_bool),
        ("amo", "user_id", "987"),
        ("amo", "username", "NewUsername"),
        ("email", "primary_email", "new-email@example.com"),
        ("email", "basket_token", "8b359504-d1b4-4691-9175-cfee3059b171"),
        ("email", "double_opt_in", swap_bool),
        ("email", "sfdc_id", "001A000001aNewUser"),
        ("email", "first_name", "New"),
        ("email", "last_name", "LastName"),
        ("email", "mailing_country", "uk"),
        ("email", "email_format", "T"),
        ("email", "email_lang", "eo"),
        ("email", "has_opted_out_of_email", swap_bool),
        ("email", "unsubscribe_reason", "new reason"),
        ("fxa", "fxa_id", "8b359504-d1b4-4691-9175-cfee3059b171"),
        ("fxa", "primary_email", "new-fxa-email@example.com"),
        ("fxa", "created_date", "2021-04-07T10:00:00+00:00"),
        ("fxa", "lang", "es"),
        ("fxa", "first_service", "vpn"),
        ("fxa", "account_deleted", swap_bool),
        ("mofo", "mofo_email_id", "8b359504-d1b4-4691-9175-cfee3059b171"),
        ("mofo", "mofo_contact_id", "8b359504-d1b4-4691-9175-cfee3059b171"),
        ("mofo", "mofo_relevant", swap_bool),
        ("vpn_waitlist", "geo", "uk"),
        ("vpn_waitlist", "platform", "linux"),
        ("relay_waitlist", "geo", "uk"),
    ),
)
def test_patch_one_new_value(
    client, sample_contacts, contact_name, group_name, key, value
):
    """PATCH can update a single value."""
    email_id, contact = sample_contacts[contact_name]
    # Add in defaults for unset groups, and convert Python values like
    # datetimes to JSON strings
    expected = json.loads(
        CTMSResponse(
            amo=contact.amo or AddOnsSchema(),
            email=contact.email,
            fxa=contact.fxa or FirefoxAccountsSchema(),
            mofo=contact.mofo or MozillaFoundationSchema(),
            newsletters=contact.newsletters or [],
            vpn_waitlist=contact.vpn_waitlist or VpnWaitlistSchema(),
            relay_waitlist=contact.relay_waitlist or RelayWaitlistSchema(),
        ).json()
    )
    existing_value = expected[group_name][key]

    # Set dynamic test values
    if callable(value):
        new_value = value(existing_value)
    else:
        new_value = value

    patch_data = {group_name: {key: new_value}}
    expected[group_name][key] = new_value
    assert existing_value != new_value

    resp = client.patch(f"/ctms/{email_id}", json=patch_data)
    assert resp.status_code == 200
    actual = resp.json()
    assert actual["status"] == "ok"
    del actual["status"]

    # Timestamps should be set for newly created amo group
    if group_name == "amo" and contact.amo is None:
        assert expected["amo"]["create_timestamp"] is None
        assert expected["amo"]["update_timestamp"] is None
        assert actual["amo"]["create_timestamp"] is not None
        assert actual["amo"]["update_timestamp"] is not None
        assert actual["amo"]["create_timestamp"] == actual["amo"]["update_timestamp"]
        expected["amo"]["create_timestamp"] = actual["amo"]["create_timestamp"]
    expected["amo"]["update_timestamp"] = actual["amo"]["update_timestamp"]
    expected["email"]["update_timestamp"] = actual["email"]["update_timestamp"]
    assert actual == expected


@pytest.mark.parametrize(
    "group_name,key",
    (
        ("amo", "add_on_ids"),
        ("amo", "display_name"),
        ("amo", "email_opt_in"),
        ("amo", "language"),
        ("amo", "last_login"),
        ("amo", "location"),
        ("amo", "profile_url"),
        ("amo", "user"),
        ("amo", "user_id"),
        ("amo", "username"),
        ("email", "basket_token"),
        ("email", "double_opt_in"),
        ("email", "sfdc_id"),
        ("email", "first_name"),
        ("email", "last_name"),
        ("email", "mailing_country"),
        ("email", "email_lang"),
        ("email", "unsubscribe_reason"),
        ("fxa", "fxa_id"),
        ("fxa", "primary_email"),
        ("fxa", "created_date"),
        ("fxa", "lang"),
        ("fxa", "first_service"),
        ("mofo", "mofo_email_id"),
        ("mofo", "mofo_contact_id"),
        ("mofo", "mofo_relevant"),
        ("vpn_waitlist", "geo"),
        ("vpn_waitlist", "platform"),
        ("relay_waitlist", "geo"),
    ),
)
def test_patch_to_default(client, maximal_contact, group_name, key):
    """PATCH can set a field to the default value."""
    email_id = maximal_contact.email.email_id
    # Add in defaults for unset groups, and convert Python values like
    # datetimes to JSON strings
    expected = json.loads(
        CTMSResponse(
            amo=maximal_contact.amo or AddOnsSchema(),
            email=maximal_contact.email,
            fxa=maximal_contact.fxa or FirefoxAccountsSchema(),
            mofo=maximal_contact.mofo or MozillaFoundationSchema(),
            newsletters=maximal_contact.newsletters or [],
            vpn_waitlist=maximal_contact.vpn_waitlist or VpnWaitlistSchema(),
            relay_waitlist=maximal_contact.relay_waitlist or RelayWaitlistSchema(),
        ).json()
    )
    existing_value = expected[group_name][key]

    # Load the default value from the schema
    field = {
        "amo": AddOnsSchema(),
        "email": EmailSchema(
            email_id=email_id, primary_email=maximal_contact.email.primary_email
        ),
        "fxa": FirefoxAccountsSchema(),
        "mofo": MozillaFoundationSchema(),
        "vpn_waitlist": VpnWaitlistSchema(),
        "relay_waitlist": RelayWaitlistSchema(),
    }[group_name].__fields__[key]
    assert not field.required
    default_value = field.get_default()
    patch_data = {group_name: {key: default_value}}
    expected[group_name][key] = default_value
    assert existing_value != default_value

    resp = client.patch(f"/ctms/{email_id}", json=patch_data, allow_redirects=True)
    assert resp.status_code == 200
    actual = resp.json()
    assert actual["status"] == "ok"
    del actual["status"]
    expected["amo"]["update_timestamp"] = actual["amo"]["update_timestamp"]
    expected["email"]["update_timestamp"] = actual["email"]["update_timestamp"]
    assert actual == expected


def test_patch_to_group_default(client, dbsession, maximal_contact):
    """PATCH to default values deletes a group."""
    email_id = maximal_contact.email.email_id
    email = get_email(dbsession, email_id)
    assert email.vpn_waitlist
    assert email.relay_waitlist

    patch_data = {
        "vpn_waitlist": {"geo": None, "platform": None},
        "relay_waitlist": {"geo": None},
    }
    resp = client.patch(f"/ctms/{email_id}", json=patch_data, allow_redirects=True)
    assert resp.status_code == 200
    actual = resp.json()
    assert actual["vpn_waitlist"] == {"geo": None, "platform": None}
    assert actual["relay_waitlist"] == {"geo": None}

    email = get_email(dbsession, email_id)
    assert not email.vpn_waitlist
    assert not email.relay_waitlist


def test_patch_cannot_set_timestamps(client, maximal_contact):
    """PATCH can not set timestamps directly."""
    email_id = maximal_contact.email.email_id
    expected = json.loads(maximal_contact.json())
    new_ts = "2021-04-07T10:00:00+00:00"
    assert expected["amo"]["create_timestamp"] == "2017-05-12T15:16:00+00:00"
    assert expected["amo"]["create_timestamp"] != new_ts
    assert expected["amo"]["update_timestamp"] != new_ts
    assert expected["email"]["create_timestamp"] != new_ts
    assert expected["email"]["update_timestamp"] != new_ts
    patch_data = {
        "amo": {
            "create_timestamp": new_ts,
            "update_timestamp": new_ts,
        },
        "email": {
            "create_timestamp": new_ts,
            "update_timestamp": new_ts,
        },
    }
    resp = client.patch(f"/ctms/{email_id}", json=patch_data, allow_redirects=True)
    assert resp.status_code == 200
    actual = resp.json()
    assert actual["status"] == "ok"
    del actual["status"]

    assert actual["email"]["update_timestamp"] != new_ts
    assert actual["amo"]["update_timestamp"] != new_ts
    expected["amo"]["update_timestamp"] = actual["amo"]["update_timestamp"]
    expected["email"]["update_timestamp"] = actual["email"]["update_timestamp"]
    # products list is not (yet) in output schema
    assert expected["products"] == []
    assert "products" not in actual
    actual["products"] = []
    assert actual == expected


def test_patch_cannot_change_email_id(client, maximal_contact):
    """PATCH cannot change the email_id."""
    email_id = maximal_contact.email.email_id
    patch_data = {"email": {"email_id": str(uuid4())}}
    resp = client.patch(f"/ctms/{email_id}", json=patch_data)
    assert resp.status_code == 422
    assert resp.json() == {"detail": "cannot change email_id"}


def test_patch_cannot_set_email_to_null(client, maximal_contact):
    """PATCH cannot set the email address to null."""
    email_id = maximal_contact.email.email_id
    patch_data = {"email": {"primary_email": None}}
    resp = client.patch(f"/ctms/{email_id}", json=patch_data)
    assert resp.status_code == 422
    assert resp.json() == {
        "detail": [
            {
                "loc": ["body", "email", "primary_email"],
                "msg": "primary_email may not be None",
                "type": "assertion_error",
            }
        ]
    }


@pytest.mark.parametrize(
    "group_name,key",
    (
        ("email", "primary_email"),
        ("email", "basket_token"),
        ("mofo", "mofo_email_id"),
        ("fxa", "fxa_id"),
    ),
)
def test_patch_error_on_id_conflict(
    client, dbsession, maximal_contact, group_name, key
):
    """PATCH returns an error on ID conflicts, and makes none of the changes."""
    conflict_id = str(uuid4())
    conflicting_data = ContactInSchema(
        amo=AddOnsInSchema(user_id=1337),
        email=EmailSchema(
            email_id=conflict_id,
            primary_email="conflict@example.com",
            basket_token=str(uuid4()),
            sfdc_id=str(uuid4()),
        ),
        mofo=MozillaFoundationInSchema(
            mofo_email_id=str(uuid4()),
            mofo_contact_id=str(uuid4()),
        ),
        fxa=FirefoxAccountsInSchema(
            fxa_id=1337, primary_email="fxa-conflict@example.com"
        ),
    )
    create_contact(dbsession, conflict_id, conflicting_data)

    existing_value = getattr(getattr(maximal_contact, group_name), key)
    conflicting_value = getattr(getattr(conflicting_data, group_name), key)
    assert existing_value
    assert conflicting_value
    assert existing_value != conflicting_value

    patch_data = {group_name: {key: str(conflicting_value)}}
    patch_data.setdefault("email", {})["first_name"] = "PATCHED"
    patch_data["vpn_waitlist"] = {"geo": "XX"}
    patch_data["relay_waitlist"] = {"geo": "XX"}

    email_id = maximal_contact.email.email_id
    resp = client.patch(f"/ctms/{email_id}", json=patch_data, allow_redirects=True)
    assert resp.status_code == 409
    assert resp.json() == {
        "detail": (
            "Contact with primary_email, basket_token, mofo_email_id, or fxa_id"
            " already exists"
        )
    }


def test_patch_to_subscribe(client, maximal_contact):
    """PATCH can subscribe to a single newsletter."""
    email_id = maximal_contact.email.email_id
    patch_data = {"newsletters": [{"name": "zzz-newsletter"}]}
    resp = client.patch(f"/ctms/{email_id}", json=patch_data, allow_redirects=True)
    assert resp.status_code == 200
    actual = resp.json()
    assert len(actual["newsletters"]) == len(maximal_contact.newsletters) + 1
    assert actual["newsletters"][-1] == {
        "format": "H",
        "lang": "en",
        "name": "zzz-newsletter",
        "source": None,
        "subscribed": True,
        "unsub_reason": None,
    }


def test_patch_to_update_subscription(client, maximal_contact):
    """PATCH can update an existing newsletter subscription."""
    email_id = maximal_contact.email.email_id
    existing_news_data = maximal_contact.newsletters[1].dict()
    assert existing_news_data == {
        "format": "T",
        "lang": "fr",
        "name": "common-voice",
        "source": "https://commonvoice.mozilla.org/fr",
        "subscribed": True,
        "unsub_reason": None,
    }
    patch_data = {
        "newsletters": [{"name": "common-voice", "format": "H", "lang": "en"}]
    }
    resp = client.patch(f"/ctms/{email_id}", json=patch_data, allow_redirects=True)
    assert resp.status_code == 200
    actual = resp.json()
    assert len(actual["newsletters"]) == len(maximal_contact.newsletters)
    assert actual["newsletters"][1] == {
        "format": "H",
        "lang": "en",
        "name": "common-voice",
        "source": "https://commonvoice.mozilla.org/fr",
        "subscribed": True,
        "unsub_reason": None,
    }


def test_patch_to_unsubscribe(client, maximal_contact):
    """PATCH can unsubscribe by setting a newsletter field."""
    email_id = maximal_contact.email.email_id
    existing_news_data = maximal_contact.newsletters[1].dict()
    assert existing_news_data == {
        "format": "T",
        "lang": "fr",
        "name": "common-voice",
        "source": "https://commonvoice.mozilla.org/fr",
        "subscribed": True,
        "unsub_reason": None,
    }
    patch_data = {
        "newsletters": [
            {
                "name": "common-voice",
                "subscribed": False,
                "unsub_reason": "Too many emails.",
            }
        ]
    }
    resp = client.patch(f"/ctms/{email_id}", json=patch_data, allow_redirects=True)
    assert resp.status_code == 200
    actual = resp.json()
    assert len(actual["newsletters"]) == len(maximal_contact.newsletters)
    assert actual["newsletters"][1] == {
        "format": "T",
        "lang": "fr",
        "name": "common-voice",
        "source": "https://commonvoice.mozilla.org/fr",
        "subscribed": False,
        "unsub_reason": "Too many emails.",
    }


def test_patch_to_unsubscribe_but_not_subscribed(client, maximal_contact):
    """PATCH doesn't create a record when unsubscribing to a new newsletter."""
    email_id = maximal_contact.email.email_id
    unknown_name = "zzz-unknown-newsletter"
    patch_data = {
        "newsletters": [
            {
                "name": unknown_name,
                "subscribed": False,
                "unsub_reason": "bulk unsubscribe",
            }
        ]
    }
    resp = client.patch(f"/ctms/{email_id}", json=patch_data, allow_redirects=True)
    assert resp.status_code == 200
    actual = resp.json()
    assert len(actual["newsletters"]) == len(maximal_contact.newsletters)
    assert not any(nl["name"] == unknown_name for nl in actual["newsletters"])


def test_patch_unsubscribe_all(client, maximal_contact):
    """PATCH with newsletters set to "UNSUBSCRIBE" unsubscribes all newsletters."""
    email_id = maximal_contact.email.email_id
    patch_data = {"newsletters": "UNSUBSCRIBE"}
    resp = client.patch(f"/ctms/{email_id}", json=patch_data, allow_redirects=True)
    assert resp.status_code == 200
    actual = resp.json()
    assert len(actual["newsletters"]) == len(maximal_contact.newsletters)
    assert all(not nl["subscribed"] for nl in actual["newsletters"])


@pytest.mark.parametrize(
    "group_name", ("amo", "fxa", "mofo", "vpn_waitlist", "relay_waitlist")
)
def test_patch_to_delete_group(client, maximal_contact, group_name):
    """PATCH with a group set to "DELETE" resets the group to defaults."""
    email_id = maximal_contact.email.email_id
    patch_data = {group_name: "DELETE"}
    resp = client.patch(f"/ctms/{email_id}", json=patch_data, allow_redirects=True)
    assert resp.status_code == 200
    actual = resp.json()
    defaults = {
        "amo": AddOnsSchema(),
        "fxa": FirefoxAccountsSchema(),
        "mofo": MozillaFoundationSchema(),
        "vpn_waitlist": VpnWaitlistSchema(),
        "relay_waitlist": RelayWaitlistSchema(),
    }[group_name].dict()
    assert actual[group_name] == defaults


def test_patch_to_delete_deleted_group(client, minimal_contact):
    """PATCH with a default group set to "DELETE" does nothing."""
    email_id = minimal_contact.email.email_id
    assert minimal_contact.mofo is None
    patch_data = {"mofo": "DELETE"}
    resp = client.patch(f"/ctms/{email_id}", json=patch_data, allow_redirects=True)
    assert resp.status_code == 200
    actual = resp.json()
    default_mofo = MozillaFoundationSchema().dict()
    assert actual["mofo"] == default_mofo


def test_patch_no_trace(client, minimal_contact):
    """PATCH does not trace most contacts"""
    email_id = minimal_contact.email.email_id
    patch_data = {"email": {"first_name": "Jeff"}}
    with capture_logs() as caplogs:
        resp = client.patch(f"/ctms/{email_id}", json=patch_data)
    assert resp.status_code == 200
    assert len(caplogs) == 1
    assert "trace" not in caplogs[0]


def test_patch_with_trace(client, minimal_contact):
    """PATCH traces by email"""
    email_id = minimal_contact.email.email_id
    patch_data = {"email": {"primary_email": "jeff+trace-me-mozilla-1@example.com"}}
    with capture_logs() as caplogs:
        resp = client.patch(f"/ctms/{email_id}", json=patch_data)
    assert resp.status_code == 200
    assert len(caplogs) == 1
    assert caplogs[0]["trace"] == "jeff+trace-me-mozilla-1@example.com"
    assert caplogs[0]["trace_json"] == patch_data
