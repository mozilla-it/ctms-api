"""Test core ingestion logic"""

import pytest

from ctms.ingest import InputIOs


def test_input_io_can_finalize():
    ios = InputIOs()
    ios.amo = "something"
    ios.emails = "something"
    ios.fxa = "something"
    ios.vpn_waitlist = "something"
    ios.newsletters = "something"
    ios.finalize()


def test_input_io_rejects_if_emptyy():
    ios = InputIOs()
    with pytest.raises(BaseException) as e:
        ios.finalize()

        assert "fxa" in str(e)


def test_input_io_rejects_if_incomplete():
    ios = InputIOs()
    ios.fxa = "something"
    with pytest.raises(BaseException) as e:
        ios.finalize()

        assert "fxa" not in str(e)
