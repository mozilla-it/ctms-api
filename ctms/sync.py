from datetime import datetime, timezone
from typing import List

from ctms.acoustic_service import CTMSToAcousticService
from ctms.crud import (
    delete_acoustic_record,
    get_acoustic_record_as_contact,
    get_all_acoustic_records_before,
    retry_acoustic_record,
)
from ctms.models import PendingAcousticRecord
from ctms.schemas import ContactSchema


class CTMSToAcousticSync:
    def __init__(
        self,
        client_id,
        client_secret,
        refresh_token,
        acoustic_main_table_id,
        acoustic_newsletter_table_id,
        server_number,
    ):
        self.ctms_to_acoustic = CTMSToAcousticService(
            client_id,
            client_secret,
            refresh_token,
            acoustic_main_table_id,
            acoustic_newsletter_table_id,
            server_number,
        )

    def sync_contact_with_acoustic(self, contact: ContactSchema):
        """

        :param contact:
        :return: Boolean value indicating success:True or failure:False
        """
        try:
            # Convert ContactSchema to Acoustic Readable, attempt API call
            return self.ctms_to_acoustic.attempt_to_upload_ctms_contact(contact)
        except Exception:  # pylint: disable=W0703
            return False

    def _sync_pending_record(self, db, pending_record: PendingAcousticRecord):
        contact: ContactSchema = get_acoustic_record_as_contact(db, pending_record)
        is_success = self.sync_contact_with_acoustic(contact)

        if is_success:
            # on success delete pending_record from table
            delete_acoustic_record(db, pending_record)
        else:
            # on failure increment retry of record in table
            retry_acoustic_record(db, pending_record)

    def sync_records(self, db, end_time=datetime.now(timezone.utc)):
        # Get all Records before current time
        all_acoustic_records_before_now: List[
            PendingAcousticRecord
        ] = get_all_acoustic_records_before(db, end_time=end_time)

        # For each record, attempt downstream sync; commit changes to db
        for acoustic_record in all_acoustic_records_before_now:
            self._sync_pending_record(db, acoustic_record)
            db.commit()
