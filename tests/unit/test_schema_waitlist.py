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
            "geo": "b",
            "source": "http://website.com",
            "fields": {"foo": "bar"},
        },
    ],
)
def test_waitlist_with_valid_input_data(data):
    WaitlistInSchema(**data)


@pytest.mark.parametrize(
    "data",
    [
        {"name": "a"},
        {"name": "a", "geo": None},
        {"name": "", "geo": "b"},
        {"name": None, "geo": "b"},
        {"name": "a", "geo": "b", "source": "*&^"},
        {"name": "a", "geo": "b", "fields": None},
        {"name": "a", "geo": "b", "fields": "foo"},
        {"name": "a", "geo": "b", "fields": [{}]},
    ],
)
def test_waitlist_with_invalid_input_data(data):
    with pytest.raises(ValueError):
        WaitlistInSchema(**data)


@pytest.mark.parametrize(
    "data",
    [
        {"name": "vpn", "fields": {"platform": "linux"}},
        {"name": "vpn", "fields": {"geo": "b", "platform": ""}},
        {"name": "vpn", "fields": {"geo": "b", "platform": "win64", "extra": "boom"}},
    ],
)
def test_vpn_waitlist_invalid_data(data):
    with pytest.raises(ValueError):
        WaitlistInSchema(**data)


@pytest.mark.parametrize(
    "data",
    [
        {"name": "vpn"},
        {"name": "vpn", "fields": {"geo": "b"}},
        {"name": "vpn", "fields": {"geo": "b", "platform": None}},
        {"name": "vpn", "fields": {"geo": "b", "platform": "win64"}},
    ],
)
def test_vpn_waitlist_valid_data(data):
    WaitlistInSchema(**data)
