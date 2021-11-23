import logging
from datetime import datetime, timezone
from typing import Dict, List, Union

from ctms.acoustic_service import Acoustic, CTMSToAcousticService
from ctms.background_metrics import BackgroundMetricService
from ctms.crud import (
    delete_acoustic_record,
    get_acoustic_record_as_contact,
    get_all_acoustic_records_before,
    get_all_acoustic_records_count,
    get_all_acoustic_retries_count,
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
        acoustic_product_table_id,
        server_number,
        retry_limit=5,
        batch_limit=20,
        is_acoustic_enabled=True,
        metric_service: BackgroundMetricService = None,
    ):
        acoustic_client = Acoustic(
            client_id=client_id,
            client_secret=client_secret,
            refresh_token=refresh_token,
            server_number=server_number,
        )
        self.ctms_to_acoustic = CTMSToAcousticService(
            acoustic_client=acoustic_client,
            acoustic_main_table_id=acoustic_main_table_id,
            acoustic_newsletter_table_id=acoustic_newsletter_table_id,
            acoustic_product_table_id=acoustic_product_table_id,
            metric_service=metric_service,
        )
        self.logger = logging.getLogger(__name__)
        self.retry_limit = retry_limit
        self.batch_limit = batch_limit
        self.is_acoustic_enabled = is_acoustic_enabled
        self.metric_service = metric_service

    def sync_contact_with_acoustic(self, contact: ContactSchema):
        """

        :param contact:
        :return: Boolean value indicating success:True or failure:False
        """
        try:
            # Convert ContactSchema to Acoustic Readable, attempt API call
            return self.ctms_to_acoustic.attempt_to_upload_ctms_contact(contact)
        except Exception:  # pylint: disable=W0703
            self.logger.exception("Error executing sync.sync_contact_with_acoustic")
            return False

    def _sync_pending_record(self, db, pending_record: PendingAcousticRecord):
        state = "unknown"
        try:
            if self.is_acoustic_enabled:
                contact: ContactSchema = get_acoustic_record_as_contact(
                    db, pending_record
                )
                is_success = self.sync_contact_with_acoustic(contact)
            else:
                self.logger.debug(
                    "Acoustic is not currently enabled. Records will be classified as successful and "
                    "dropped from queue at this time."
                )
                is_success = True

            if is_success:
                # on success delete pending_record from table
                delete_acoustic_record(db, pending_record)
                if self.is_acoustic_enabled:
                    state = "synced"
                else:
                    state = "skipped"
                if self.metric_service:
                    self.metric_service.inc_acoustic_sync_total()
            else:
                # on failure increment retry of record in table
                retry_acoustic_record(db, pending_record)
                state = "retry"
        except Exception:  # pylint: disable=W0703
            self.logger.exception("Exception occurred when processing acoustic record.")
            state = "exception"
        return state

    def sync_records(self, db, end_time=None):
        context: Dict[str, Union[int, str]] = {
            "batch_limit": self.batch_limit,
            "retry_limit": self.retry_limit,
        }
        if end_time is None:
            context["end_time"] = "now"
            end_time = datetime.now(timezone.utc)
        else:
            context["end_time"] = end_time.isoformat()
        if self.metric_service:
            all_acoustic_records_count: int = get_all_acoustic_records_count(
                db=db, end_time=end_time, retry_limit=self.retry_limit
            )
            context["sync_backlog"] = all_acoustic_records_count
            self.metric_service.gauge_acoustic_sync_backlog(all_acoustic_records_count)
            all_retry_records_count: int = get_all_acoustic_retries_count(db=db)
            context["retry_backlog"] = all_acoustic_records_count
            self.metric_service.gauge_acoustic_retry_backlog(all_retry_records_count)
        # Get all Records before current time
        all_acoustic_records_before_now: List[
            PendingAcousticRecord
        ] = get_all_acoustic_records_before(
            db,
            end_time=end_time,
            retry_limit=self.retry_limit,
            batch_limit=self.batch_limit,
        )

        # For each record, attempt downstream sync
        context["count_total"] = 0
        for acoustic_record in all_acoustic_records_before_now:
            state = self._sync_pending_record(db, acoustic_record)
            context["count_total"] += 1
            context[f"count_{state}"] = context.get(f"count_{state}", 0) + 1
        # Commit changes to db after ALL records are batch-processed
        db.commit()
        return context
