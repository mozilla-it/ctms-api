import datetime
import time
from decimal import Decimal
from typing import Dict, List, Union
from uuid import UUID

import dateutil
import structlog
from lxml import etree
from requests.exceptions import Timeout
from silverpop.api import Silverpop, SilverpopResponseException

from ctms.background_metrics import BackgroundMetricService
from ctms.config import re_trace_email
from ctms.schemas import ContactSchema, NewsletterSchema

# Start cherry-picked from django.utils.encoding
_PROTECTED_TYPES = (
    type(None),
    int,
    float,
    Decimal,
    datetime.datetime,
    datetime.date,
    datetime.time,
)


def is_protected_type(obj):
    """Determine if the object instance is of a protected type.
    Objects of protected types are preserved as-is when passed to
    force_str(strings_only=True).
    """
    return isinstance(obj, _PROTECTED_TYPES)


def force_bytes(s, encoding="utf-8", strings_only=False, errors="strict"):
    # pylint: disable=C0103,R1705
    """
    Similar to smart_bytes, except that lazy instances are resolved to
    strings, rather than kept as lazy objects.
    If strings_only is True, don't convert (some) non-string-like objects.
    """
    # Handle the common case first for performance reasons.
    if isinstance(s, bytes):
        if encoding == "utf-8":
            return s
        else:
            return s.decode("utf-8", errors).encode(encoding, errors)
    if strings_only and is_protected_type(s):
        return s
    if isinstance(s, memoryview):
        return bytes(s)
    return str(s).encode(encoding, errors)


# End cherry-picked from django.utils.encoding


class AcousticUploadError(Exception):
    """Failure to upload a contact to Acoustic"""


class AcousticResources:
    SKIP_FIELDS = set(
        (
            # Known skipped fields from CTMS
            ("email", "update_timestamp"),
            ("amo", "update_timestamp"),
            ("amo", "create_timestamp"),
        )
    )


class Acoustic(Silverpop):
    """
    :param client_id
    :param client_secret
    :param refresh_token
    :param server_number
    """

    def __init__(self, timeout, *args, **kwargs):
        self.timeout = timeout
        super().__init__(*args, **kwargs)

    @staticmethod
    def _process_response(resp):
        # pylint: disable=c-extension-no-member
        response = etree.fromstring(resp.text.encode("utf-8"))
        # success = response.find(".//SUCCESS")
        # print("IS_SUCCESS: %s", success.text.upper())

        # how main table failures are reported:
        fault = response.find(".//Fault/FaultString")
        if fault is not None:
            # print(fault.text) # TODO: Convert to logging
            raise SilverpopResponseException(fault.text)

        # how RT failures are reported:
        failures = response.findall(".//FAILURES/FAILURE")
        if failures is not None and len(failures) > 0:
            raise SilverpopResponseException(
                # pylint: disable=c-extension-no-member
                [etree.tostring(fail) for fail in failures]
            )

        return response

    def _call(self, xml):
        # Following basket's suggested pattern,
        # adding force_bytes to deal with some Acoustic rejections
        response = self.session.post(
            self.api_endpoint, data={"xml": force_bytes(xml)}, timeout=self.timeout
        )
        return self._process_response(response)


class CTMSToAcousticService:
    def __init__(
        self,
        acoustic_main_table_id,
        acoustic_newsletter_table_id,
        acoustic_product_table_id,
        acoustic_client: Acoustic,
        metric_service: BackgroundMetricService = None,
    ):
        """
        Construct a CTMSToAcousticService object that can interface between contacts and acoustic forms of data
        """
        self.acoustic = acoustic_client
        self.acoustic_main_table_id = int(acoustic_main_table_id)
        self.relational_tables = {
            "newsletter": str(int(acoustic_newsletter_table_id)),
            "product": str(int(acoustic_product_table_id)),
        }
        self.logger = structlog.get_logger(__name__)
        self.context: Dict[str, Union[str, int, List[str]]] = {}
        self.metric_service = metric_service

    def convert_ctms_to_acoustic(
        self,
        contact: ContactSchema,
        main_fields: set[str],
        newsletters_mapping: dict[str, str],
    ):
        acoustic_main_table = self._main_table_converter(contact, main_fields)
        newsletter_rows, acoustic_main_table = self._newsletter_converter(
            acoustic_main_table, contact, newsletters_mapping
        )
        acoustic_main_table = self._waitlist_converter(
            acoustic_main_table,
            contact,
            main_fields,
        )
        product_rows = self._product_converter(contact)
        return acoustic_main_table, newsletter_rows, product_rows

    def _main_table_converter(self, contact, main_fields):
        acoustic_main_table = {}
        acceptable_subdicts = ["email", "amo", "fxa"]
        special_cases = {
            ("fxa", "fxa_id"): "fxa_id",
            ("email", "primary_email"): "email",
        }
        skipped_fields = []
        for contact_attr in contact.dict():
            subdict_value = getattr(contact, contact_attr)
            contact_attr_name = str(contact_attr)
            if contact_attr_name in acceptable_subdicts and subdict_value is not None:
                for inner_attr in subdict_value.dict():
                    inner_value = getattr(subdict_value, inner_attr)
                    inner_attr_name = str(inner_attr)
                    if contact_attr_name != "email":
                        acoustic_field_name = contact_attr_name + "_" + inner_attr_name
                    else:
                        # Email table records should not be prefixed
                        acoustic_field_name = inner_attr_name

                    special_key = (contact_attr_name, inner_attr_name)
                    if special_key in special_cases:
                        acoustic_field_name = special_cases.get(special_key)
                    if acoustic_field_name == "email" and re_trace_email.match(
                        inner_value
                    ):
                        self.context["trace"] = inner_value

                    if acoustic_field_name in main_fields:
                        if acoustic_field_name == "fxa_created_date":
                            inner_value = self.fxa_created_date_string_to_datetime(
                                inner_value
                            )

                        acoustic_main_table[
                            acoustic_field_name
                        ] = self.transform_field_for_acoustic(inner_value)
                    elif (contact_attr, inner_attr) in AcousticResources.SKIP_FIELDS:
                        pass
                    else:
                        skipped_fields.append(f"{contact_attr}.{inner_attr}")
        if skipped_fields:
            self.context["skipped_fields"] = sorted(skipped_fields)
        return acoustic_main_table

    def fxa_created_date_string_to_datetime(self, inner_value):
        if isinstance(inner_value, str):
            try:
                inner_value = dateutil.parser.parse(inner_value)
                self.context["fxa_created_date_converted"] = "success"
            except Exception:  # pylint: disable=broad-except
                self.context["fxa_created_date_type"] = str(type(inner_value))
                self.context["fxa_created_date_converted"] = "failure"
                self.logger.exception(
                    "Failure in attempt to convert created_date, using original value."
                )
        else:
            self.context["fxa_created_date_type"] = str(type(inner_value))
            self.context["fxa_created_date_converted"] = "skipped"
        return inner_value

    def _newsletter_converter(self, acoustic_main_table, contact, newsletters_mapping):
        # create the RT rows for the newsletter table in acoustic
        newsletter_rows = []
        contact_newsletters: List[NewsletterSchema] = contact.newsletters
        contact_email_id = str(contact.email.email_id)
        skipped = []

        # populate with all the sub_flags set to false
        # they'll get set to true below, as-needed
        for sub_flag in newsletters_mapping.values():
            acoustic_main_table[sub_flag] = "0"

        for newsletter in contact_newsletters:
            newsletter_row = {
                "email_id": contact_email_id,
                "newsletter_name": newsletter.name,
                "newsletter_source": newsletter.source and str(newsletter.source),
                "create_timestamp": newsletter.create_timestamp.date().isoformat(),
                "update_timestamp": newsletter.update_timestamp.date().isoformat(),
                "newsletter_format": newsletter.format,
                "newsletter_lang": newsletter.lang,
                "subscribed": newsletter.subscribed,
                "newsletter_unsub_reason": newsletter.unsub_reason,
            }
            newsletter_rows.append(newsletter_row)

            if newsletter.name in newsletters_mapping:
                # and finally flip the main table's sub_<newsletter> flag to true for each subscription
                if newsletter.subscribed:
                    acoustic_main_table[newsletters_mapping[newsletter.name]] = "1"
            else:
                skipped.append(newsletter.name)
        if skipped:
            self.context["newsletters_skipped"] = sorted(skipped)
        return newsletter_rows, acoustic_main_table

    def _waitlist_converter(self, acoustic_main_table, contact, main_fields):
        """Turns waitlists into flat fields on the main table.

        If the field `{name}_waitlist_{field}` is not present in the `main_fields`
        list, then it is ignored.
        See `bin/acoustic_fields.py` to manage them (eg. add ``vpn_waitlist_source``).

        Note: In the future, a dedicated relation/table for waitlists can be considered.
        """
        waitlists_by_name = {wl.name: wl for wl in contact.waitlists}
        for acoustic_field_name in main_fields:
            if "_waitlist_" not in acoustic_field_name:
                continue
            name, _, field = acoustic_field_name.split("_")
            value = None
            if name in waitlists_by_name:
                waitlist = waitlists_by_name[name]
                value = getattr(waitlist, field, waitlist.fields.get(field, None))
            acoustic_main_table[
                acoustic_field_name
            ] = self.transform_field_for_acoustic(value)
        return acoustic_main_table

    @staticmethod
    def transform_field_for_acoustic(data):
        """Transform data for main contact table."""
        if isinstance(data, bool):
            if data:
                return "1"
            return "0"
        if isinstance(data, datetime.datetime):
            # Acoustic doesn't have timestamps, so make timestamps into dates.
            data = data.date()
        if isinstance(data, datetime.date):
            return data.strftime("%m/%d/%Y")
        if isinstance(data, UUID):
            return str(data)
        return data

    @staticmethod
    def to_acoustic_bool(bool_str):
        """Transform bool for products relational table."""
        if bool_str in (True, "true"):
            return "Yes"
        return "No"

    @staticmethod
    def to_acoustic_timestamp(dt_val):
        """Transform datetime for products relational table."""
        if dt_val:
            return dt_val.strftime("%m/%d/%Y %H:%M:%S")
        return ""

    def _product_converter(self, contact):
        """Create the rows for the product subscription table in Acoustic."""
        contact_email_id = str(contact.email.email_id)
        product_rows = []
        template: Dict[str, str] = {"email_id": contact_email_id}
        to_ts = CTMSToAcousticService.to_acoustic_timestamp
        for product in contact.products:
            row: Dict[str, str] = template.copy()
            row.update(
                {
                    "product_name": product.product_name or "",
                    "product_id": product.product_id,
                    "price_id": product.price_id,
                    "segment": product.segment.value,
                    "changed": to_ts(product.changed),
                    "sub_count": str(product.sub_count),
                    "payment_service": product.payment_service,
                    "payment_type": product.payment_type or "",
                    "card_brand": product.card_brand or "",
                    "card_last4": product.card_last4 or "",
                    "currency": product.currency or "",
                    "amount": "-1" if product.amount is None else str(product.amount),
                    "billing_country": product.billing_country or "",
                    "status": product.status.value if product.status else "",
                    "interval_count": (
                        "-1"
                        if product.interval_count is None
                        else str(product.interval_count)
                    ),
                    "interval": product.interval or "",
                    "created": to_ts(product.created),
                    "start": to_ts(product.start),
                    "current_period_start": to_ts(product.current_period_start),
                    "current_period_end": to_ts(product.current_period_end),
                    "canceled_at": to_ts(product.canceled_at),
                    "cancel_at_period_end": CTMSToAcousticService.to_acoustic_bool(
                        product.cancel_at_period_end
                    ),
                    "ended_at": to_ts(product.ended_at),
                }
            )
            product_rows.append(row)

        return product_rows

    def _add_contact(self, list_id=None, sync_fields=None, columns=None):
        if columns is None:
            columns = {}
        if sync_fields is None:
            sync_fields = {}
        params = {
            "list_id": list_id,
            "created_from": 3,
            "update_if_found": "TRUE",
            "allow_html": False,
            "sync_fields": sync_fields,
            "columns": columns,
        }
        if self.metric_service is None:
            self.acoustic.add_recipient(**params)
        else:  # Metrics are enabled
            start_time = time.monotonic()
            status = "success"
            try:
                self.acoustic.add_recipient(**params)  # Call to Acoustic
            except Exception:  # pylint: disable=broad-except
                status = "failure"
                raise
            finally:
                duration = time.monotonic() - start_time
                duration_s = round(duration, 3)
                metric_params = {
                    "method": "add_recipient",
                    "status": status,
                    "table": "main",
                }
                self.metric_service.inc_acoustic_request_total(**metric_params)
                metric_params.update({"duration_s": duration_s})
                self.metric_service.observe_acoustic_request_duration(**metric_params)
                self.context["main_status"] = status
                self.context["main_duration_s"] = duration_s

    def _insert_update_relational_table(self, table_name, rows):
        if not rows:
            return
        start_time = time.monotonic()
        status = "success"
        table_id = self.relational_tables[table_name]
        try:
            self.acoustic.insert_update_relational_table(
                table_id=table_id, rows=rows
            )  # Call to Acoustic
        except Exception:  # pylint: disable=broad-except
            status = "failure"
            raise
        finally:
            if self.metric_service:
                duration = time.monotonic() - start_time
                duration_s = round(duration, 3)
                metric_params = {
                    "method": "insert_update_relational_table",
                    "status": status,
                    "table": table_name,
                }
                self.metric_service.inc_acoustic_request_total(**metric_params)
                metric_params["duration_s"] = duration_s
                self.metric_service.observe_acoustic_request_duration(**metric_params)
                self.context[f"{table_name}_status"] = status
                self.context[f"{table_name}_duration_s"] = duration_s

    def attempt_to_upload_ctms_contact(
        self,
        contact: ContactSchema,
        main_fields: set[str],
        newsletters_mapping: dict[str, str],
    ):  # raises AcousticUploadError
        """

        :param contact: to be converted to acoustic table rows and uploaded
        :return: Boolean indicating True (success) or False (failure)
        """
        self.context = {}
        try:
            main_table_data, nl_data, prod_data = self.convert_ctms_to_acoustic(
                contact, main_fields, newsletters_mapping
            )
            main_table_id = str(self.acoustic_main_table_id)
            email_id = main_table_data["email_id"]
            self.context["email_id"] = email_id
            self.context["newsletter_count"] = len(nl_data)
            self.context["product_count"] = len(prod_data)
            self._add_contact(
                list_id=main_table_id,
                sync_fields={"email_id": email_id},
                columns=main_table_data,
            )
            self._insert_update_relational_table("newsletter", nl_data)
            self._insert_update_relational_table("product", prod_data)

            # success
            self.logger.debug(
                "Successfully sync'd contact to acoustic...",
                success=True,
                **self.context,
            )
        except (SilverpopResponseException, Timeout) as exc:
            # failure
            self.logger.exception(
                "Failure for contact in sync to acoustic...",
                success=False,
                **self.context,
            )
            # Silverpop is supposed to provide the fault string as message.
            # https://github.com/theatlantic/pysilverpop/blob/ee9d60a6e/silverpop/api.py#L520
            # Use `repr()` to obtain exception classname.
            raise AcousticUploadError(repr(exc)) from exc
