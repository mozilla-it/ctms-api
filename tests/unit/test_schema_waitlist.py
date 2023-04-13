import pytest

from ctms.schemas.waitlist import WaitlistInSchema


@pytest.mark.parametrize(
    "data",
    [
        {"name": "a"},
        {"name": "a", "source": None},
        {"name": "a", "source": "http://website.com"},
        {"name": "a", "source": "http://website.com", "fields": {}},
        {
            "name": "a",
            "source": "http://website.com",
            "fields": {"foo": "bar", "geo": "b"},
        },
    ],
)
def test_waitlist_with_valid_input_data(data):
    WaitlistInSchema(**data)


@pytest.mark.parametrize(
    "data",
    [
        {"name": ""},
        {"name": None},
        {"name": "a", "source": ""},
        {"name": "a", "source": "*&^"},
        {"name": "a", "fields": None},
        {"name": "a", "fields": "foo"},
        {"name": "a", "fields": [{}]},
    ],
)
def test_waitlist_with_invalid_input_data(data):
    with pytest.raises(ValueError):
        WaitlistInSchema(**data)


@pytest.mark.parametrize(
    "data",
    [
        # VPN
        {"name": "vpn", "fields": {"geo": "b", "platform": "win64", "extra": "boom"}},
        # Relay
        {"name": "relay"},
        {"name": "relay", "fields": {"geo": "fr", "extra": "boom"}},
        {"name": "relay", "fields": {"foo": "bar"}},
    ],
)
def test_relay_and_vpn_waitlist_invalid_data(data):
    with pytest.raises(ValueError):
        WaitlistInSchema(**data)


@pytest.mark.parametrize(
    "data",
    [
        # VPN
        {"name": "vpn", "fields": {"geo": "b"}},
        {"name": "vpn", "fields": {"geo": ""}},
        {"name": "vpn", "fields": {"geo": "b", "platform": ""}},
        {"name": "vpn", "fields": {"geo": "b", "platform": None}},
        {"name": "vpn", "fields": {"geo": "b", "platform": "win64"}},
        # Relay
        {"name": "relay", "fields": {"geo": "b"}},
        {"name": "relay", "fields": {"geo": ""}},
        {"name": "relay", "fields": {"geo": "b"}},
    ],
)
def test_relay_and_vpn_waitlist_valid_data(data):
    WaitlistInSchema(**data)
