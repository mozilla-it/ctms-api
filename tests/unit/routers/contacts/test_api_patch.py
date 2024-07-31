"""Tests for PATCH /ctms/{email_id}"""

import json
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi.encoders import jsonable_encoder

from ctms.schemas import (
    AddOnsInSchema,
    AddOnsSchema,
    ContactSchema,
    CTMSResponse,
    EmailSchema,
    FirefoxAccountsInSchema,
    FirefoxAccountsSchema,
    MozillaFoundationInSchema,
    MozillaFoundationSchema,
)
from ctms.schemas.waitlist import WaitlistInSchema
from tests.conftest import FuzzyAssert
from tests.unit.conftest import create_full_contact


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
    expected = json.loads(CTMSResponse(**contact.model_dump()).model_dump_json())
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
def test_patch_to_default(client, email_factory, group_name, key):
    """PATCH can set a field to the default value."""
    email = email_factory(
        sfdc_id="001A000001aMozFan",
        unsubscribe_reason="You know what you did.",
        double_opt_in=True,
        with_fxa=True,
        fxa__first_service="abc",
        with_mofo=True,
        with_amo=True,
    )

    expected = jsonable_encoder(
        CTMSResponse(**ContactSchema.from_email(email).model_dump())
    )
    existing_value = expected[group_name][key]

    # Load the default value from the schema
    field = {
        "amo": AddOnsSchema(),
        "email": EmailSchema(
            email_id=email.email_id,
            primary_email=email.primary_email,
        ),
        "fxa": FirefoxAccountsSchema(),
        "mofo": MozillaFoundationSchema(),
    }[group_name].model_fields[key]
    assert not field.is_required()
    default_value = field.get_default()
    patch_data = {group_name: {key: default_value}}
    expected[group_name][key] = default_value
    assert existing_value != default_value

    resp = client.patch(
        f"/ctms/{email.email_id}", json=patch_data, allow_redirects=True
    )
    assert resp.status_code == 200
    actual = resp.json()
    assert actual["status"] == "ok"
    del actual["status"]
    expected["amo"]["update_timestamp"] = actual["amo"]["update_timestamp"]
    expected["email"]["update_timestamp"] = actual["email"]["update_timestamp"]
    assert actual == expected


def test_patch_cannot_set_timestamps(client, email_factory):
    """PATCH can not set timestamps directly."""
    email = email_factory(with_amo=True)

    expected = jsonable_encoder(
        CTMSResponse(**ContactSchema.from_email(email).model_dump())
    )
    new_ts = datetime.now(tz=UTC).isoformat()
    assert expected["amo"]["create_timestamp"] == email.amo.create_timestamp.isoformat()
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
    resp = client.patch(
        f"/ctms/{email.email_id}", json=patch_data, allow_redirects=True
    )
    assert resp.status_code == 200
    actual = resp.json()
    assert actual["status"] == "ok"
    del actual["status"]

    assert actual["email"]["update_timestamp"] != new_ts
    assert actual["amo"]["update_timestamp"] != new_ts
    expected["amo"]["update_timestamp"] = actual["amo"]["update_timestamp"]
    expected["email"]["update_timestamp"] = actual["email"]["update_timestamp"]
    assert actual == expected


def test_patch_cannot_change_email_id(client, email_factory):
    """PATCH cannot change the email_id."""
    email = email_factory()

    patch_data = {"email": {"email_id": str(uuid4())}}
    resp = client.patch(f"/ctms/{email.email_id}", json=patch_data)
    assert resp.status_code == 422
    assert resp.json() == {"detail": "cannot change email_id"}


def test_patch_cannot_set_email_to_null(client, email_factory):
    """PATCH cannot set the email address to null."""
    email = email_factory()

    patch_data = {"email": {"primary_email": None}}
    resp = client.patch(f"/ctms/{email.email_id}", json=patch_data)
    assert resp.status_code == 422
    assert resp.json() == {
        "detail": [
            {
                "ctx": {
                    "error": {},
                },
                "input": None,
                "loc": ["body", "email", "primary_email"],
                "msg": "Assertion failed, primary_email may not be None",
                "type": "assertion_error",
                "url": "https://errors.pydantic.dev/2.8/v/assertion_error",
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
def test_patch_error_on_id_conflict(client, dbsession, group_name, key, email_factory):
    """PATCH returns an error on ID conflicts, and makes none of the changes."""
    email = email_factory(with_mofo=True, with_fxa=True)

    existing_contact = ContactSchema.from_email(email)

    conflict_id = str(uuid4())
    conflicting_data = ContactSchema(
        amo=AddOnsInSchema(user_id="1337"),
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
            fxa_id="1337", primary_email="fxa-conflict@example.com"
        ),
    )
    create_full_contact(dbsession, conflicting_data)

    existing_value = getattr(getattr(existing_contact, group_name), key)
    conflicting_value = getattr(getattr(conflicting_data, group_name), key)
    assert existing_value
    assert conflicting_value
    assert existing_value != conflicting_value

    patch_data = {group_name: {key: str(conflicting_value)}}
    patch_data.setdefault("email", {})["first_name"] = "PATCHED"
    patch_data["vpn_waitlist"] = {"geo": "XX"}
    patch_data["relay_waitlist"] = {"geo": "XX"}

    email_id = existing_contact.email.email_id
    resp = client.patch(f"/ctms/{email_id}", json=patch_data, allow_redirects=True)
    assert resp.status_code == 409
    assert resp.json() == {
        "detail": (
            "Contact with primary_email, basket_token, mofo_email_id, or fxa_id"
            " already exists"
        )
    }


def test_patch_to_subscribe(client, email_factory):
    """PATCH can subscribe to a single newsletter."""
    email = email_factory(newsletters=1)

    patch_data = {"newsletters": [{"name": "zzz-newsletter"}]}
    resp = client.patch(
        f"/ctms/{email.email_id}", json=patch_data, allow_redirects=True
    )
    assert resp.status_code == 200
    actual = resp.json()
    assert len(actual["newsletters"]) == 2
    assert actual["newsletters"][1] == {
        "format": "H",
        "lang": "en",
        "name": "zzz-newsletter",
        "source": None,
        "subscribed": True,
        "unsub_reason": None,
        "create_timestamp": FuzzyAssert.iso8601(),
        "update_timestamp": FuzzyAssert.iso8601(),
    }


def test_patch_to_update_subscription(client, newsletter_factory):
    """PATCH can update an existing newsletter subscription."""
    existing_newsletter = newsletter_factory()

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
        "create_timestamp": existing_newsletter.create_timestamp.isoformat(),
        "update_timestamp": existing_newsletter.update_timestamp.isoformat(),
    }


def test_patch_to_unsubscribe(client, email_factory, newsletter_factory):
    """PATCH can unsubscribe by setting a newsletter field."""
    email = email_factory()
    existing_newsletter = newsletter_factory(name="common-voice", email=email)

    assert len(email.newsletters) == 1
    assert existing_newsletter.subscribed
    assert existing_newsletter.name == "common-voice"
    assert existing_newsletter.unsub_reason is None
    patch_data = {
        "newsletters": [
            {
                "name": "common-voice",
                "subscribed": False,
                "unsub_reason": "Too many emails.",
            }
        ]
    }
    resp = client.patch(
        f"/ctms/{email.email_id}", json=patch_data, allow_redirects=True
    )
    assert resp.status_code == 200
    actual = resp.json()
    assert len(actual["newsletters"]) == len(email.newsletters)
    assert actual["newsletters"][0] == {
        "format": existing_newsletter.format,
        "lang": existing_newsletter.lang,
        "name": "common-voice",
        "source": existing_newsletter.source,
        "subscribed": False,
        "unsub_reason": "Too many emails.",
        "create_timestamp": existing_newsletter.create_timestamp.isoformat(),
        "update_timestamp": FuzzyAssert.iso8601(),
    }


def test_patch_to_unsubscribe_but_not_subscribed(client, email_factory):
    """PATCH doesn't create a record when unsubscribing to a new newsletter."""
    email = email_factory(newsletters=1)

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
    resp = client.patch(
        f"/ctms/{email.email_id}", json=patch_data, allow_redirects=True
    )
    assert resp.status_code == 200
    actual = resp.json()
    assert len(actual["newsletters"]) == 1
    assert actual["newsletters"][0]["name"] != unknown_name


def test_patch_unsubscribe_all(client, email_factory):
    """PATCH with newsletters set to "UNSUBSCRIBE" unsubscribes all newsletters."""
    email = email_factory(newsletters=2)

    patch_data = {"newsletters": "UNSUBSCRIBE"}
    resp = client.patch(
        f"/ctms/{email.email_id}", json=patch_data, allow_redirects=True
    )
    assert resp.status_code == 200
    actual = resp.json()
    assert len(actual["newsletters"]) == 2
    assert all(not nl["subscribed"] for nl in actual["newsletters"])


@pytest.mark.parametrize("group_name", ("amo", "fxa", "mofo"))
def test_patch_to_delete_group(client, email_factory, group_name):
    """PATCH with a group set to "DELETE" resets the group to defaults."""
    email = email_factory(with_amo=True, with_fxa=True, with_mofo=True)

    patch_data = {group_name: "DELETE"}
    resp = client.patch(
        f"/ctms/{email.email_id}", json=patch_data, allow_redirects=True
    )
    assert resp.status_code == 200
    actual = resp.json()
    defaults = {
        "amo": AddOnsSchema(),
        "fxa": FirefoxAccountsSchema(),
        "mofo": MozillaFoundationSchema(),
    }[group_name].model_dump()
    assert actual[group_name] == defaults


def test_patch_to_delete_deleted_group(client, email_factory):
    """PATCH with a default group set to "DELETE" does nothing."""
    email = email_factory()

    assert email.amo is None

    patch_data = {"mofo": "DELETE"}
    resp = client.patch(
        f"/ctms/{email.email_id}", json=patch_data, allow_redirects=True
    )

    assert resp.status_code == 200
    actual = resp.json()
    default_mofo = MozillaFoundationSchema().model_dump()
    assert actual["mofo"] == default_mofo


def test_patch_will_validate_waitlist_fields(client, email_factory):
    """PATCH validates waitlist schema."""
    email = email_factory()

    patch_data = {"waitlists": [{"name": "future-tech", "source": 42}]}
    resp = client.patch(
        f"/ctms/{email.email_id}", json=patch_data, allow_redirects=True
    )
    assert resp.status_code == 422
    details = resp.json()
    assert details["detail"][0]["loc"] == [
        "body",
        "waitlists",
        "list[function-after[check_fields(), WaitlistBase]]",
        0,
        "source",
    ]


def test_patch_to_add_a_waitlist(client, email_factory):
    """PATCH can add a single waitlist."""
    email = email_factory()

    patch_data = {"waitlists": [{"name": "future-tech", "fields": {"geo": "es"}}]}
    resp = client.patch(
        f"/ctms/{email.email_id}", json=patch_data, allow_redirects=True
    )
    assert resp.status_code == 200
    actual = resp.json()
    [new_waitlist] = actual["waitlists"]
    assert new_waitlist == {
        "name": "future-tech",
        "source": None,
        "fields": {"geo": "es"},
        "subscribed": True,
        "unsub_reason": None,
        "create_timestamp": FuzzyAssert.iso8601(),
        "update_timestamp": FuzzyAssert.iso8601(),
    }


def test_patch_does_not_add_an_unsubscribed_waitlist(client, email_factory):
    email = email_factory()

    patch_data = {"waitlists": [{"name": "future-tech", "subscribed": False}]}
    resp = client.patch(
        f"/ctms/{email.email_id}", json=patch_data, allow_redirects=True
    )
    assert resp.status_code == 200
    actual = resp.json()
    assert len(actual["waitlists"]) == 0


def test_patch_to_update_a_waitlist(client, email_factory, waitlist_factory):
    """PATCH can update a waitlist."""
    email = email_factory()
    waitlist = waitlist_factory(fields={"geo": "fr"}, email=email)

    patched_waitlist = (
        WaitlistInSchema.from_orm(waitlist)
        .copy(update={"fields": {"geo": "ca"}})
        .model_dump()
    )
    patch_data = {"waitlists": [patched_waitlist]}
    resp = client.patch(
        f"/ctms/{email.email_id}", json=patch_data, allow_redirects=True
    )
    assert resp.status_code == 200
    actual = resp.json()
    assert actual["waitlists"][0]["fields"]["geo"] == "ca"


def test_patch_to_remove_a_waitlist(client, email_factory, waitlist_factory):
    """PATCH can remove a single waitlist."""
    email = email_factory()
    waitlist_factory(name="bye-bye", email=email)

    patch_data = {
        "waitlists": [
            WaitlistInSchema(
                name="bye-bye", subscribed=False, unsub_reason="Not interested"
            ).model_dump()
        ]
    }
    resp = client.patch(
        f"/ctms/{email.email_id}", json=patch_data, allow_redirects=True
    )
    assert resp.status_code == 200
    actual = resp.json()
    [unsubscribed] = actual["waitlists"]
    assert unsubscribed["subscribed"] is False
    assert unsubscribed["unsub_reason"] == "Not interested"


def test_patch_to_remove_all_waitlists(client, email_factory):
    """PATCH can remove all waitlists."""
    email = email_factory(waitlists=2)
    assert all(wl.subscribed for wl in email.waitlists)

    patch_data = {"waitlists": "UNSUBSCRIBE"}
    resp = client.patch(
        f"/ctms/{email.email_id}", json=patch_data, allow_redirects=True
    )

    assert resp.status_code == 200
    actual = resp.json()
    assert not any(wl["subscribed"] for wl in actual["waitlists"])


def test_patch_preserves_waitlists_if_omitted(client, email_factory):
    """PATCH won't update waitlists if omitted."""
    email = email_factory(waitlists=2)

    patch_data = {"email": {"first_name": "Jeff"}}
    resp = client.patch(
        f"/ctms/{email.email_id}", json=patch_data, allow_redirects=True
    )

    assert resp.status_code == 200
    actual = resp.json()
    assert len(actual["waitlists"]) == len(email.waitlists)


def test_patch_vpn_waitlist_legacy_add(client, email_factory):
    email = email_factory()

    patch_data = {"vpn_waitlist": {"geo": "fr", "platform": "win32"}}
    resp = client.patch(
        f"/ctms/{email.email_id}", json=patch_data, allow_redirects=True
    )
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
            "subscribed": True,
            "unsub_reason": None,
            "create_timestamp": FuzzyAssert.iso8601(),
            "update_timestamp": FuzzyAssert.iso8601(),
        }
    ]


def test_patch_vpn_waitlist_legacy_delete(client, email_factory, waitlist_factory):
    email = email_factory()
    waitlist_factory(
        name="vpn", fields={"geo": "ca", "platform": "windows,android"}, email=email
    )

    assert len([wl for wl in email.waitlists if wl.subscribed]) == 1

    patch_data = {"vpn_waitlist": "DELETE"}
    resp = client.patch(
        f"/ctms/{email.email_id}", json=patch_data, allow_redirects=True
    )

    assert resp.status_code == 200
    actual = resp.json()
    assert len([wl for wl in actual["waitlists"] if wl["subscribed"]]) == 0


def test_patch_vpn_waitlist_legacy_delete_default(
    client, email_factory, waitlist_factory
):
    email = email_factory()
    waitlist_factory(
        name="vpn", fields={"geo": "ca", "platform": "windows,android"}, email=email
    )

    assert len([wl for wl in email.waitlists if wl.subscribed]) == 1

    patch_data = {"vpn_waitlist": {"geo": None, "platform": None}}
    resp = client.patch(
        f"/ctms/{email.email_id}", json=patch_data, allow_redirects=True
    )
    assert resp.status_code == 200
    actual = resp.json()
    assert len([wl for wl in actual["waitlists"] if wl["subscribed"]]) == 0


def test_patch_vpn_waitlist_legacy_update(client, waitlist_factory):
    vpn_waitlist = waitlist_factory(
        name="vpn",
        source="https://www.example.com/vpn_signup",
        fields={"geo": "es", "platform": "ios"},
    )

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
            "subscribed": True,
            "unsub_reason": None,
            "create_timestamp": FuzzyAssert.iso8601(),
            "update_timestamp": FuzzyAssert.iso8601(),
        }
    ]


def test_patch_vpn_waitlist_legacy_update_full(client, waitlist_factory):
    vpn_waitlist = waitlist_factory(
        name="vpn",
        source="https://www.example.com/vpn_signup",
        fields={"geo": "es", "platform": "ios"},
    )

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
            "subscribed": True,
            "unsub_reason": None,
            "create_timestamp": FuzzyAssert.iso8601(),
            "update_timestamp": FuzzyAssert.iso8601(),
        }
    ]


def test_patch_relay_waitlist_legacy_add(client, email_factory):
    email = email_factory()

    patch_data = {"relay_waitlist": {"geo": "fr"}}
    resp = client.patch(
        f"/ctms/{email.email_id}", json=patch_data, allow_redirects=True
    )

    assert resp.status_code == 200
    actual = resp.json()
    assert actual["waitlists"] == [
        {
            "name": "relay",
            "source": None,
            "fields": {"geo": "fr"},
            "subscribed": True,
            "unsub_reason": None,
            "create_timestamp": FuzzyAssert.iso8601(),
            "update_timestamp": FuzzyAssert.iso8601(),
        }
    ]


def test_patch_relay_waitlist_legacy_delete(client, email_factory, waitlist_factory):
    email = email_factory()
    waitlist_factory(name="relay", fields={"geo": "cn"}, email=email)

    assert len([wl for wl in email.waitlists if wl.subscribed]) == 1

    patch_data = {"relay_waitlist": "DELETE"}
    resp = client.patch(
        f"/ctms/{email.email_id}", json=patch_data, allow_redirects=True
    )
    assert resp.status_code == 200
    actual = resp.json()
    assert len([wl for wl in actual["waitlists"] if wl["subscribed"]]) == 0


def test_patch_relay_waitlist_legacy_delete_default(
    client, email_factory, waitlist_factory
):
    email = email_factory()
    waitlist_factory(name="relay", fields={"geo": "cn"}, email=email)

    assert len([wl for wl in email.waitlists if wl.subscribed]) == 1

    patch_data = {"relay_waitlist": {"geo": None}}
    resp = client.patch(
        f"/ctms/{email.email_id}", json=patch_data, allow_redirects=True
    )
    assert resp.status_code == 200
    actual = resp.json()
    assert len([wl for wl in actual["waitlists"] if wl["subscribed"]]) == 0


def test_patch_relay_waitlist_legacy_update(client, waitlist_factory):
    relay_waitlist = waitlist_factory(
        name="relay",
        source="https://www.example.com/relay_signup",
        fields={"geo": "es"},
    )

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
            "subscribed": True,
            "unsub_reason": None,
            "create_timestamp": FuzzyAssert.iso8601(),
            "update_timestamp": FuzzyAssert.iso8601(),
        }
    ]


def test_patch_relay_waitlist_legacy_update_all(
    client, email_factory, waitlist_factory
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
            "subscribed": True,
            "unsub_reason": None,
            "create_timestamp": FuzzyAssert.iso8601(),
            "update_timestamp": FuzzyAssert.iso8601(),
        },
        {
            "name": "relay-vpn-bundle",
            "source": "https://www.example.com/relay_vpn_bundle_signup",
            "fields": {"geo": "it"},
            "subscribed": True,
            "unsub_reason": None,
            "create_timestamp": FuzzyAssert.iso8601(),
            "update_timestamp": FuzzyAssert.iso8601(),
        },
    ]


def test_subscribe_to_relay_newsletter_turned_into_relay_waitlist(
    client, email_factory
):
    email = email_factory()

    patch_data = {
        "relay_waitlist": {"geo": "ru"},
        "newsletters": [{"name": "relay-vpn-bundle-waitlist"}],
    }
    resp = client.patch(
        f"/ctms/{email.email_id}", json=patch_data, allow_redirects=True
    )
    assert resp.status_code == 200
    actual = resp.json()
    assert actual["waitlists"] == [
        {
            "name": "relay-vpn-bundle",
            "source": None,
            "fields": {"geo": "ru"},
            "subscribed": True,
            "unsub_reason": None,
            "create_timestamp": FuzzyAssert.iso8601(),
            "update_timestamp": FuzzyAssert.iso8601(),
        },
    ]


def test_unsubscribe_from_all_newsletters_removes_all_waitlists(client, email_factory):
    email = email_factory(newsletters=1, waitlists=1)

    assert len(email.waitlists) == 1

    patch_data = {
        "newsletters": "UNSUBSCRIBE",
    }
    resp = client.patch(
        f"/ctms/{email.email_id}", json=patch_data, allow_redirects=True
    )
    current = resp.json()
    assert not any(wl["subscribed"] for wl in current["waitlists"])


def test_unsubscribe_from_guardian_vpn_newsletter_removes_vpn_waitlist(
    client, email_factory, waitlist_factory
):
    email = email_factory()
    waitlist_factory(
        name="vpn",
        fields={"geo": "ca", "platform": "windows,android"},
        email=email,
    )

    patch_data = {
        "newsletters": [
            {"name": "guardian-vpn-waitlist", "subscribed": False},
        ]
    }
    resp = client.patch(
        f"/ctms/{email.email_id}", json=patch_data, allow_redirects=True
    )

    current = resp.json()
    [wl] = current["waitlists"]
    assert wl["subscribed"] is False


def test_unsubscribe_from_relay_newsletter_removes_relay_waitlist(
    client, email_factory, waitlist_factory
):
    email = email_factory()
    waitlist_factory(name="relay-vpn-bundle", fields={"geo": "ru"}, email=email)

    patch_data = {
        "newsletters": [{"name": "relay-vpn-bundle-waitlist", "subscribed": False}]
    }
    resp = client.patch(
        f"/ctms/{email.email_id}", json=patch_data, allow_redirects=True
    )
    assert resp.status_code == 200

    [patched_wl] = resp.json()["waitlists"]
    assert patched_wl["name"] == "relay-vpn-bundle"
    assert patched_wl["subscribed"] is False


def test_cannot_subscribe_to_relay_newsletter_without_relay_country(
    client, email_factory
):
    email = email_factory()

    patch_data = {"newsletters": [{"name": "relay-phone-waitlist"}]}
    resp = client.patch(
        f"/ctms/{email.email_id}", json=patch_data, allow_redirects=True
    )
    assert resp.status_code == 422
