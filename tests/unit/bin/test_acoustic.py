from ctms.bin.acoustic import do_resync
from ctms.models import PendingAcousticRecord


def test_main_force_resync_by_newsletter(dbsession, minimal_contact):
    assert len(dbsession.query(PendingAcousticRecord).all()) == 0

    do_resync(
        dbsession, assume_yes=True, newsletter=minimal_contact.newsletters[0].name
    )

    assert len(dbsession.query(PendingAcousticRecord).all()) > 0


def test_main_force_resync_by_waitlist(dbsession, maximal_contact):
    assert len(dbsession.query(PendingAcousticRecord).all()) == 0

    do_resync(dbsession, assume_yes=True, waitlist=maximal_contact.waitlists[0].name)

    assert len(dbsession.query(PendingAcousticRecord).all()) > 0


def test_main_force_resync_by_email_list(dbsession, maximal_contact, tmpdir):
    assert len(dbsession.query(PendingAcousticRecord).all()) == 0

    f = tmpdir.join("temp.txt")
    f.write(maximal_contact.email.primary_email)
    do_resync(dbsession, assume_yes=True, emails_file=f)

    assert len(dbsession.query(PendingAcousticRecord).all()) > 0


def test_main_force_resync_by_reset_retry(dbsession, minimal_contact, maximal_contact):
    record = PendingAcousticRecord(email_id=minimal_contact.email.email_id, retry=99)
    dbsession.add(record)
    record = PendingAcousticRecord(email_id=maximal_contact.email.email_id, retry=99)
    dbsession.add(record)
    dbsession.flush()

    do_resync(dbsession, reset_retries=True)

    assert (
        len(
            dbsession.query(PendingAcousticRecord)
            .filter(PendingAcousticRecord.retry > 0)
            .all()
        )
        == 0
    )
