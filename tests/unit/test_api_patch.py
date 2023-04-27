"""Tests for PATCH /ctms/{email_id}"""
import json
from uuid import uuid4

import pytest
from structlog.testing import capture_logs

from ctms.crud import create_contact
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
)


def swap_bool(existing):
    """Use the opposite of the existing value for this boolean."""
    return not existing


@pytest.mark.parametrize("contact_name", ("minimal_contact", "maximal_contact"))
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
    ),
)
def test_patch_one_new_value(client, contact_name, group_name, key, value, request):
    """PATCH can update a single value."""
    contact = request.getfixturevalue(contact_name)
    expected = json.loads(CTMSResponse(**contact.dict()).json())
    existing_value = expected[group_name][key]

    # Set dynamic test values
    if callable(value):
        new_value = value(existing_value)
    else:
        new_value = value

    patch_data = {group_name: {key: new_value}}
    expected[group_name][key] = new_value
    assert existing_value != new_value

    resp = client.patch(f"/ctms/{contact.email.email_id}", json=patch_data)
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
    ),
)
def test_patch_to_default(client, maximal_contact, group_name, key):
    """PATCH can set a field to the default value."""
    email_id = maximal_contact.email.email_id
    expected = json.loads(CTMSResponse(**maximal_contact.dict()).json())
    existing_value = expected[group_name][key]

    # Load the default value from the schema
    field = {
        "amo": AddOnsSchema(),
        "email": EmailSchema(
            email_id=email_id, primary_email=maximal_contact.email.primary_email
        ),
        "fxa": FirefoxAccountsSchema(),
        "mofo": MozillaFoundationSchema(),
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
    # The response shows computed fields for retro-compat. Contact schema
    # does not have them.
    # TODO waitlist: remove once Basket reads from `waitlists` list.
    del actual["vpn_waitlist"]
    del actual["relay_waitlist"]
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
    create_contact(dbsession, conflict_id, conflicting_data, metrics=None)

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


def test_patch_to_update_subscription(client, dbsession, newsletter_factory):
    """PATCH can update an existing newsletter subscription."""
    existing_newsletter = newsletter_factory()
    dbsession.commit()
    email_id = str(existing_newsletter.email.email_id)
    patch_data = {
        "newsletters": [{"name": existing_newsletter.name, "format": "H", "lang": "XX"}]
    }
    resp = client.patch(f"/ctms/{email_id}", json=patch_data, allow_redirects=True)
    assert resp.status_code == 200
    actual = resp.json()
    assert len(actual["newsletters"]) == 1
    assert actual["newsletters"][0] == {
        "format": "H",
        "lang": "XX",
        "name": existing_newsletter.name,
        "source": existing_newsletter.source,
        "subscribed": existing_newsletter.subscribed,
        "unsub_reason": existing_newsletter.unsub_reason,
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


@pytest.mark.parametrize("group_name", ("amo", "fxa", "mofo"))
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


def test_patch_will_validate_waitlist_fields(client, maximal_contact):
    """PATCH validates waitlist schema."""
    email_id = maximal_contact.email.email_id

    patch_data = {"waitlists": [{"name": "future-tech", "source": 42}]}
    resp = client.patch(f"/ctms/{email_id}", json=patch_data, allow_redirects=True)
    assert resp.status_code == 422
    details = resp.json()
    assert details["detail"][0]["loc"] == ["body", "waitlists", 0, "source"]


def test_patch_to_add_a_waitlist(client, maximal_contact):
    """PATCH can add a single waitlist."""
    email_id = maximal_contact.email.email_id
    patch_data = {"waitlists": [{"name": "future-tech", "fields": {"geo": "es"}}]}
    resp = client.patch(f"/ctms/{email_id}", json=patch_data, allow_redirects=True)
    assert resp.status_code == 200
    actual = resp.json()
    new_waitlists = actual["waitlists"]
    assert len(new_waitlists) == len(maximal_contact.waitlists) + 1
    new_waitlist = next((wl for wl in new_waitlists if wl["name"] == "future-tech"))
    assert new_waitlist == {
        "name": "future-tech",
        "source": None,
        "fields": {"geo": "es"},
    }


def test_patch_does_not_add_an_unsubscribed_waitlist(client, maximal_contact):
    email_id = maximal_contact.email.email_id
    patch_data = {"waitlists": [{"name": "future-tech", "subscribed": False}]}
    resp = client.patch(f"/ctms/{email_id}", json=patch_data, allow_redirects=True)
    assert resp.status_code == 200
    actual = resp.json()
    assert len(actual["waitlists"]) == len(maximal_contact.waitlists)


def test_patch_to_update_a_waitlist(client, maximal_contact):
    """PATCH can update a waitlist."""
    email_id = maximal_contact.email.email_id
    existing = [wl.dict() for wl in maximal_contact.waitlists]
    existing[0]["fields"]["geo"] = "ca"
    patch_data = {"waitlists": existing}
    resp = client.patch(f"/ctms/{email_id}", json=patch_data, allow_redirects=True)
    assert resp.status_code == 200
    actual = resp.json()
    assert (
        actual["waitlists"][0]["fields"]["geo"]
        != maximal_contact.waitlists[0].fields["geo"]
    )


def test_patch_to_remove_a_waitlist(client, maximal_contact):
    """PATCH can remove a single waitlist."""
    email_id = maximal_contact.email.email_id
    existing = [wl.dict() for wl in maximal_contact.waitlists]
    patch_data = {"waitlists": [{**existing[-1], "subscribed": False}]}
    resp = client.patch(f"/ctms/{email_id}", json=patch_data, allow_redirects=True)
    assert resp.status_code == 200
    actual = resp.json()
    assert len(actual["waitlists"]) == len(maximal_contact.waitlists) - 1


def test_patch_to_remove_all_waitlists(client, maximal_contact):
    """PATCH can remove all waitlists."""
    email_id = maximal_contact.email.email_id
    patch_data = {"waitlists": "UNSUBSCRIBE"}
    resp = client.patch(f"/ctms/{email_id}", json=patch_data, allow_redirects=True)
    assert resp.status_code == 200
    actual = resp.json()
    assert len(actual["waitlists"]) == 0


def test_patch_preserves_waitlists_if_omitted(client, maximal_contact):
    """PATCH won't update waitlists if omitted."""
    email_id = maximal_contact.email.email_id
    patch_data = {"email": {"first_name": "Jeff"}}
    resp = client.patch(f"/ctms/{email_id}", json=patch_data, allow_redirects=True)
    assert resp.status_code == 200
    actual = resp.json()
    assert len(actual["waitlists"]) == len(maximal_contact.waitlists)


def test_patch_vpn_waitlist_legacy_add(client, minimal_contact):
    email_id = minimal_contact.email.email_id
    patch_data = {"vpn_waitlist": {"geo": "fr", "platform": "win32"}}
    resp = client.patch(f"/ctms/{email_id}", json=patch_data, allow_redirects=True)
    assert resp.status_code == 200
    actual = resp.json()
    assert actual["waitlists"] == [
        {
            "name": "vpn",
            "source": None,
            "fields": {
                "geo": "fr",
                "platform": "win32",
            },
        }
    ]


def test_patch_vpn_waitlist_legacy_delete(client, maximal_contact):
    email_id = maximal_contact.email.email_id
    before = len(maximal_contact.waitlists)

    patch_data = {"vpn_waitlist": "DELETE"}
    resp = client.patch(f"/ctms/{email_id}", json=patch_data, allow_redirects=True)
    assert resp.status_code == 200
    actual = resp.json()
    assert len(actual["waitlists"]) == before - 1


def test_patch_vpn_waitlist_legacy_delete_default(client, maximal_contact):
    email_id = maximal_contact.email.email_id
    before = len(maximal_contact.waitlists)

    patch_data = {"vpn_waitlist": {"geo": None, "platform": None}}
    resp = client.patch(f"/ctms/{email_id}", json=patch_data, allow_redirects=True)
    assert resp.status_code == 200
    actual = resp.json()
    assert len(actual["waitlists"]) == before - 1


def test_patch_vpn_waitlist_legacy_update(client, dbsession, waitlist_factory):
    vpn_waitlist = waitlist_factory(
        name="vpn",
        source="https://www.example.com/vpn_signup",
        fields={"geo": "es", "platform": "ios"},
    )
    dbsession.commit()
    patch_data = {"vpn_waitlist": {"geo": "it"}}
    resp = client.patch(
        f"/ctms/{vpn_waitlist.email.email_id}", json=patch_data, allow_redirects=True
    )
    assert resp.status_code == 200
    actual = resp.json()
    assert actual["waitlists"] == [
        {
            "name": "vpn",
            "source": "https://www.example.com/vpn_signup",
            "fields": {"geo": "it", "platform": None},
        }
    ]


def test_patch_vpn_waitlist_legacy_update_full(client, dbsession, waitlist_factory):
    vpn_waitlist = waitlist_factory(
        name="vpn",
        source="https://www.example.com/vpn_signup",
        fields={"geo": "es", "platform": "ios"},
    )
    dbsession.commit()
    patch_data = {"vpn_waitlist": {"geo": "it", "platform": "linux"}}
    resp = client.patch(
        f"/ctms/{vpn_waitlist.email.email_id}", json=patch_data, allow_redirects=True
    )
    assert resp.status_code == 200
    actual = resp.json()
    assert actual["waitlists"] == [
        {
            "name": "vpn",
            "source": "https://www.example.com/vpn_signup",
            "fields": {"geo": "it", "platform": "linux"},
        }
    ]


def test_patch_relay_waitlist_legacy_add(client, minimal_contact):
    email_id = minimal_contact.email.email_id
    patch_data = {"relay_waitlist": {"geo": "fr"}}
    resp = client.patch(f"/ctms/{email_id}", json=patch_data, allow_redirects=True)
    assert resp.status_code == 200
    actual = resp.json()
    assert actual["waitlists"] == [
        {
            "name": "relay",
            "source": None,
            "fields": {"geo": "fr"},
        }
    ]


def test_patch_relay_waitlist_legacy_delete(client, maximal_contact):
    email_id = maximal_contact.email.email_id
    before = len(maximal_contact.waitlists)

    patch_data = {"relay_waitlist": "DELETE"}
    resp = client.patch(f"/ctms/{email_id}", json=patch_data, allow_redirects=True)
    assert resp.status_code == 200
    actual = resp.json()
    assert len(actual["waitlists"]) == before - 1


def test_patch_relay_waitlist_legacy_delete_default(client, maximal_contact):
    email_id = maximal_contact.email.email_id
    before = len(maximal_contact.waitlists)

    patch_data = {"relay_waitlist": {"geo": None}}
    resp = client.patch(f"/ctms/{email_id}", json=patch_data, allow_redirects=True)
    assert resp.status_code == 200
    actual = resp.json()
    assert len(actual["waitlists"]) == before - 1


def test_patch_relay_waitlist_legacy_update(client, dbsession, waitlist_factory):
    relay_waitlist = waitlist_factory(
        name="relay",
        source="https://www.example.com/relay_signup",
        fields={"geo": "es"},
    )
    dbsession.commit()
    patch_data = {"relay_waitlist": {"geo": "it"}}
    resp = client.patch(
        f"/ctms/{relay_waitlist.email.email_id}", json=patch_data, allow_redirects=True
    )
    assert resp.status_code == 200
    actual = resp.json()
    assert actual["waitlists"] == [
        {
            "name": "relay",
            "source": "https://www.example.com/relay_signup",
            "fields": {"geo": "it"},
        }
    ]


def test_patch_relay_waitlist_legacy_update_all(
    client, dbsession, email_factory, waitlist_factory
):
    # Test that all relay waitlists records are updated from the legacy way.
    email = email_factory()
    email.waitlists = [
        waitlist_factory.build(
            name="relay",
            source="https://www.example.com/relay_signup",
            fields={"geo": "es"},
            email=email,
        ),
        waitlist_factory.build(
            name="relay-vpn-bundle",
            source="https://www.example.com/relay_vpn_bundle_signup",
            fields={"geo": "es"},
            email=email,
        ),
    ]
    dbsession.commit()
    patch_data = {
        "waitlists": [
            {"name": "relay", "fields": {"geo": "fr"}},
            {"name": "relay-vpn-bundle", "fields": {"geo": "fr"}},
        ]
    }
    resp = client.patch(
        f"/ctms/{email.email_id}", json=patch_data, allow_redirects=True
    )
    assert resp.status_code == 200
    actual = resp.json()

    patch_data = {"relay_waitlist": {"geo": "it"}}
    resp = client.patch(
        f"/ctms/{email.email_id}", json=patch_data, allow_redirects=True
    )
    assert resp.status_code == 200
    actual = resp.json()
    assert actual["waitlists"] == [
        {
            "name": "relay",
            "source": "https://www.example.com/relay_signup",
            "fields": {"geo": "it"},
        },
        {
            "name": "relay-vpn-bundle",
            "source": "https://www.example.com/relay_vpn_bundle_signup",
            "fields": {"geo": "it"},
        },
    ]


def test_subscribe_to_relay_newsletter_turned_into_relay_waitlist(
    client, minimal_contact
):
    email_id = minimal_contact.email.email_id
    patch_data = {
        "relay_waitlist": {"geo": "ru"},
        "newsletters": [{"name": "relay-vpn-bundle-waitlist"}],
    }
    resp = client.patch(f"/ctms/{email_id}", json=patch_data, allow_redirects=True)
    assert resp.status_code == 200
    actual = resp.json()
    assert actual["waitlists"] == [
        {
            "name": "relay-vpn-bundle",
            "source": None,
            "fields": {"geo": "ru"},
        },
    ]


def test_unsubscribe_from_all_newsletters_removes_all_waitlists(
    client, maximal_contact
):
    email_id = maximal_contact.email.email_id
    assert len(maximal_contact.waitlists) > 0

    patch_data = {
        "newsletters": "UNSUBSCRIBE",
    }
    resp = client.patch(f"/ctms/{email_id}", json=patch_data, allow_redirects=True)
    current = resp.json()
    assert current["waitlists"] == []


def test_unsubscribe_from_guardian_vpn_newsletter_removes_vpn_waitlist(
    client, maximal_contact
):
    email_id = maximal_contact.email.email_id
    wl_names = {wl.name for wl in maximal_contact.waitlists}
    assert "vpn" in wl_names

    patch_data = {
        "newsletters": [
            {"name": "guardian-vpn-waitlist", "subscribed": False},
        ]
    }
    resp = client.patch(f"/ctms/{email_id}", json=patch_data, allow_redirects=True)
    current = resp.json()
    wl_names = {wl["name"] for wl in current["waitlists"]}
    assert "vpn" not in wl_names


def test_unsubscribe_from_relay_newsletter_removes_relay_waitlist(
    client, minimal_contact
):
    email_id = minimal_contact.email.email_id
    patch_data = {
        "relay_waitlist": {"geo": "ru"},
        "newsletters": [{"name": "relay-vpn-bundle-waitlist"}],
    }
    resp = client.patch(f"/ctms/{email_id}", json=patch_data, allow_redirects=True)
    current = resp.json()
    assert current["waitlists"] == [
        {"fields": {"geo": "ru"}, "name": "relay-vpn-bundle", "source": None}
    ]

    patch_data = {
        "newsletters": [{"name": "relay-vpn-bundle-waitlist", "subscribed": False}]
    }
    resp = client.patch(f"/ctms/{email_id}", json=patch_data, allow_redirects=True)
    assert resp.status_code == 200
    actual = resp.json()
    assert actual["waitlists"] == []


def test_cannot_subscribe_to_relay_newsletter_without_relay_country(
    client, minimal_contact
):
    email_id = minimal_contact.email.email_id
    patch_data = {"newsletters": [{"name": "relay-phone-waitlist"}]}
    resp = client.patch(f"/ctms/{email_id}", json=patch_data, allow_redirects=True)
    assert resp.status_code == 422
