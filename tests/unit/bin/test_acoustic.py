from uuid import UUID

from ctms.bin.acoustic import do_dump, do_resync
from ctms.crud import get_all_contacts_from_ids
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


def test_main_force_resync_will_reset_existing_retries(
    dbsession, maximal_contact, tmpdir
):
    record = PendingAcousticRecord(email_id=maximal_contact.email.email_id, retry=99)
    dbsession.add(record)
    dbsession.flush()

    f = tmpdir.join("temp.txt")
    f.write(maximal_contact.email.primary_email)
    do_resync(dbsession, assume_yes=True, emails_file=f)
    dbsession.flush()

    pending = dbsession.query(PendingAcousticRecord).all()
    assert len(pending) == 1
    assert pending[0].retry == 0


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


def test_csv_dump(dbsession, sample_contacts, tmpdir):
    uuids = [contact[0] for contact in sample_contacts.values()]
    contacts = get_all_contacts_from_ids(dbsession, email_ids=uuids)
    output_path = tmpdir.join("output.csv")

    with open(output_path, "w", encoding="utf-8") as output:
        do_dump(dbsession, contacts, output)

    with open(output_path, "r", encoding="utf-8") as produced:
        lines = produced.readlines()

    assert len(lines) == len(uuids) + 1  # with header line
    assert len(lines[0].split(",")) >= 52  # remains true if columns are added
