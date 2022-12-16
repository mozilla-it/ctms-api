import pytest

from ctms.schemas.waitlist import WaitlistInSchema


@pytest.mark.parametrize(
    "data",
    [
        {"name": "a", "geo": "b"},
        {"name": "a", "geo": "b", "source": None},
        {"name": "a", "geo": "b", "source": "http://website.com"},
        {"name": "a", "geo": "b", "source": "http://website.com", "fields": {}},
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
        {"name": "vpn", "geo": "b", "fields": {"platform": ""}},
        {"name": "vpn", "geo": "b", "fields": {"platform": "win64", "extra": "boom"}},
    ],
)
def test_vpn_waitlist_invalid_data(data):
    with pytest.raises(ValueError):
        WaitlistInSchema(**data)


@pytest.mark.parametrize(
    "data",
    [
        {"name": "vpn", "geo": "b"},
        {"name": "vpn", "geo": "b", "fields": {}},
        {"name": "vpn", "geo": "b", "fields": {"platform": None}},
        {"name": "vpn", "geo": "b", "fields": {"platform": "win64"}},
    ],
)
def test_vpn_waitlist_valid_data(data):
    WaitlistInSchema(**data)
