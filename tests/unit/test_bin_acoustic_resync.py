"""Tests for ctms/bin/acoustic.py resync"""

from ctms.bin.acoustic import do_resync
from ctms.models import PendingAcousticRecord


def test_main_force_resync_by_newsletter(dbsession, sample_contacts):
    _, some_contact = sample_contacts["minimal"]
    assert len(dbsession.query(PendingAcousticRecord).all()) == 0

    do_resync(dbsession, assume_yes=True, newsletter=some_contact.newsletters[0].name)

    assert len(dbsession.query(PendingAcousticRecord).all()) > 0


def test_main_force_resync_by_waitlist(dbsession, sample_contacts):
    _, some_contact = sample_contacts["maximal"]
    assert len(dbsession.query(PendingAcousticRecord).all()) == 0

    do_resync(dbsession, assume_yes=True, waitlist=some_contact.waitlists[0].name)

    assert len(dbsession.query(PendingAcousticRecord).all()) > 0


def test_main_force_resync_by_email_list(dbsession, sample_contacts, tmpdir):
    _, some_contact = sample_contacts["maximal"]

    assert len(dbsession.query(PendingAcousticRecord).all()) == 0

    f = tmpdir.join("temp.txt")
    f.write(some_contact.email.primary_email)
    do_resync(dbsession, assume_yes=True, emails_file=f)

    assert len(dbsession.query(PendingAcousticRecord).all()) > 0
