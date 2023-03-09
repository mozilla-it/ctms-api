"""Tests for ctms/bin/acoustic.py resync"""

import tempfile

from ctms.bin.acoustic import do_resync
from ctms.models import PendingAcousticRecord


def test_main_force_resync_by_newsletter(dbsession, sample_contacts):
    _, some_contact = sample_contacts["minimal"]
    assert len(dbsession.query(PendingAcousticRecord).all()) == 0

    do_resync(dbsession, newsletter=some_contact.newsletters[0].name)

    assert len(dbsession.query(PendingAcousticRecord).all()) > 0


def test_main_force_resync_by_waitlist(dbsession, sample_contacts):
    _, some_contact = sample_contacts["maximal"]
    assert len(dbsession.query(PendingAcousticRecord).all()) == 0

    do_resync(dbsession, waitlist=some_contact.waitlists[0].name)

    assert len(dbsession.query(PendingAcousticRecord).all()) > 0


def test_main_force_resync_by_email_list(dbsession, sample_contacts):
    _, some_contact = sample_contacts["maximal"]

    assert len(dbsession.query(PendingAcousticRecord).all()) == 0

    with tempfile.NamedTemporaryFile() as temp:
        temp.write(some_contact.email.primary_email.encode("utf-8"))
        temp.flush()
        temp.seek(0)

        do_resync(dbsession, email_list=temp)

    assert len(dbsession.query(PendingAcousticRecord).all()) > 0
