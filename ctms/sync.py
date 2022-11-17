import logging
from collections import defaultdict
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
from ctms.models import AcousticField, AcousticNewsletterMapping, PendingAcousticRecord
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
        acoustic_timeout=5.0,
    ):
        acoustic_client = Acoustic(
            client_id=client_id,
            client_secret=client_secret,
            refresh_token=refresh_token,
            server_number=server_number,
            timeout=acoustic_timeout,
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

    def sync_contact_with_acoustic(
        self,
        contact: ContactSchema,
        main_fields: set[str],
        newsletters_mapping: dict[str, str],
    ):
        """

        :param contact:
        :return: Boolean value indicating success:True or failure:False
        """
        try:
            # Convert ContactSchema to Acoustic Readable, attempt API call
            return self.ctms_to_acoustic.attempt_to_upload_ctms_contact(
                contact, main_fields, newsletters_mapping
            )
        except Exception:  # pylint: disable=W0703
            self.logger.exception("Error executing sync.sync_contact_with_acoustic")
            return False

    def _sync_pending_record(
        self,
        db,
        pending_record: PendingAcousticRecord,
        main_fields: set[str],
        newsletters_mapping: dict[str, str],
    ) -> str:
        state = "unknown"
        try:
            if self.is_acoustic_enabled:
                contact: ContactSchema = get_acoustic_record_as_contact(
                    db, pending_record
                )
                is_success = self.sync_contact_with_acoustic(
                    contact, main_fields, newsletters_mapping
                )
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

    def sync_records(self, db, end_time=None) -> Dict[str, Union[int, str]]:
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
            context["retry_backlog"] = all_retry_records_count
            self.metric_service.gauge_acoustic_retry_backlog(all_retry_records_count)

        # Obtain list of contact fields to sync from DB.
        main_acoustic_fields: List[AcousticField] = (
            db.query(AcousticField).filter(AcousticField.tablename == "main").all()
        )
        main_fields = {entry.field for entry in main_acoustic_fields}

        newsletters_mapping_entries: List[AcousticNewsletterMapping] = db.query(
            AcousticNewsletterMapping
        ).all()
        newsletters_mapping = {
            entry.source: entry.destination for entry in newsletters_mapping_entries
        }

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
        total = 0
        states: Dict[str, int] = defaultdict(int)
        record_created = None
        for acoustic_record in all_acoustic_records_before_now:
            state = self._sync_pending_record(
                db, acoustic_record, main_fields, newsletters_mapping
            )
            total += 1

            states[state] += 1
            if state == "synced" and acoustic_record.retry == 0:
                record_created = acoustic_record.create_timestamp
        # Commit changes to db after ALL records are batch-processed
        db.commit()

        context["count_total"] = total
        for state, count in states.items():
            context[f"count_{state}"] = count
        if self.metric_service and record_created:
            age_td = datetime.now(tz=timezone.utc) - record_created
            age_s = round(age_td.total_seconds(), 3)
            self.metric_service.gauge_acoustic_record_age(age_s)

        return context


def update_healthcheck(healthcheck_path):
    """Update the healthcheck file with the current time, if set."""
    if not healthcheck_path:
        return
    with open(healthcheck_path, "w", encoding="utf8") as health_file:
        health_file.write(datetime.now(tz=timezone.utc).isoformat())


def check_healthcheck(healthcheck_path, age_s):
    """
    Check that the healthcheck file is not too old.

    Raises exceptions for errors:
    * Environment variables unset
    * Healthcheck file doesn't exist
    * Contents are not in Python's ISO 8601 format
    * Age is too old

    Return the current age.
    """
    if not healthcheck_path:
        raise Exception("BACKGROUND_HEALTHCHECK_PATH not set")
    if age_s is None:
        raise Exception("BACKGROUND_HEALTHCHECK_AGE_S not set")
    with open(healthcheck_path, "r", encoding="utf8") as health_file:
        content = health_file.read().strip()
        written_at = datetime.fromisoformat(content)
        health_age_raw = (datetime.now(tz=timezone.utc) - written_at).total_seconds()
        health_age = round(health_age_raw, 3)
        if health_age > age_s:
            raise Exception(f"Age {health_age}s > {age_s}s, written at {content}")
    return health_age
