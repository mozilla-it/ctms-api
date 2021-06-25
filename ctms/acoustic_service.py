import datetime
import logging
import time
from decimal import Decimal
from typing import List
from uuid import UUID

import dateutil
from lxml import etree
from silverpop.api import Silverpop, SilverpopResponseException

from ctms.background_metrics import BackgroundMetricService
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


class AcousticResources:
    # TODO: externalize, maybe a DB table?
    VALID_ACOUSTIC_MAIN_TABLE_FIELDS = {
        "sfdc_id",
        "email",
        "amo_add_on_ids",
        "amo_display_name",
        "amo_email_opt_in",
        "amo_language",
        "amo_last_login",
        "amo_location",
        "amo_profile_url",
        "amo_user",
        "amo_user_id",
        "amo_username",
        "create_timestamp",
        "email_format",
        "email_id",
        "email_lang",
        "vpn_waitlist_geo",
        "vpn_waitlist_platform",
        "fxa_id",
        "fxa_account_deleted",
        "fxa_lang",
        "fxa_login_date",
        "fxa_first_service",
        "fxa_created_date",
        "fxa_primary_email",
        "double_opt_in",
        "has_opted_out_of_email",
        "mailing_country",
        "first_name",
        "last_name",
        "sumo_contributor",
        "sumo_user",
        "sumo_username",
        "basket_token",
        "unsubscribe_reason",
    }

    MAIN_TABLE_SUBSCR_FLAGS = {
        # maps the Basket/CTMS newsletter name to the Acoustic name
        "common-voice": "sub_common_voice",
        "mozilla-fellowship-awardee-alumni": "sub_mozilla_fellowship_awardee_alumni",
        "firefox-accounts-journey": "sub_firefox_accounts_journey",
        "firefox-news": "sub_firefox_news",
        "mozilla-and-you": "sub_firefox_news",
        "hubs": "sub_hubs",
        "internet-health-report": "sub_internet_health_report",
        "knowledge-is-power": "sub_knowledge_is_power",
        "miti": "sub_miti",
        "mixed-reality": "sub_mixed_reality",
        "mozilla-festival": "sub_mozilla_festival",
        "mozilla-foundation": "sub_mozilla_foundation",
        "mozilla-technology": "sub_mozilla_technology",
        "mozillians-nda": "sub_mozillians_nda",
        "take-action-for-the-internet": "sub_take_action_for_the_internet",
        "test-pilot": "sub_test_pilot",
        "about-mozilla": "sub_about_mozilla",
        "app-dev": "sub_apps_and_hacks",
    }


class Acoustic(Silverpop):
    """
    :param client_id
    :param client_secret
    :param refresh_token
    :param server_number
    """

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
        response = self.session.post(self.api_endpoint, data={"xml": force_bytes(xml)})
        return self._process_response(response)


class CTMSToAcousticService:
    def __init__(
        self,
        acoustic_main_table_id,
        acoustic_newsletter_table_id,
        acoustic_client: Acoustic,
        metric_service: BackgroundMetricService = None,
    ):
        """
        Construct a CTMSToAcousticService object that can interface between contacts and acoustic forms of data
        """
        self.acoustic = acoustic_client
        self.acoustic_main_table_id = int(acoustic_main_table_id)
        self.acoustic_newsletter_table_id = int(acoustic_newsletter_table_id)
        self.logger = logging.getLogger(__name__)
        self.metric_service = metric_service

    def convert_ctms_to_acoustic(self, contact: ContactSchema):
        acoustic_main_table = self._main_table_converter(contact)
        newsletter_rows, acoustic_main_table = self._newsletter_converter(
            acoustic_main_table, contact
        )
        return acoustic_main_table, newsletter_rows

    def _main_table_converter(self, contact):
        acoustic_main_table = {
            # populate with all the sub_flags set to false
            # they'll get set to true below, as-needed
            v: "0"
            for v in AcousticResources.MAIN_TABLE_SUBSCR_FLAGS.values()
        }
        acceptable_subdicts = ["email", "amo", "fxa", "vpn_waitlist"]
        special_cases = {
            ("fxa", "fxa_id"): "fxa_id",
            ("email", "primary_email"): "email",
        }
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

                    if (
                        acoustic_field_name
                        in AcousticResources.VALID_ACOUSTIC_MAIN_TABLE_FIELDS
                    ):
                        if acoustic_field_name == "fxa_created_date":
                            inner_value = self.fxa_created_date_string_to_datetime(
                                inner_value
                            )

                        acoustic_main_table[
                            acoustic_field_name
                        ] = self.transform_field_for_acoustic(inner_value)
                    else:
                        self.logger.debug(
                            "Skipping CTMS field (%s, %s) because no match in Acoustic",
                            contact_attr,
                            inner_attr,
                        )
        return acoustic_main_table

    def fxa_created_date_string_to_datetime(self, inner_value):
        if isinstance(inner_value, str):
            self.logger.debug("created_date found; attempting conversion from string.")
            try:
                inner_value = dateutil.parser.parse(inner_value)
                self.logger.debug(
                    "Success, created_date converted to datetime in pre-processing."
                )
            except Exception:  # pylint: disable=broad-except
                self.logger.exception(
                    "Failure in attempt to convert created_date, using original value."
                )
        else:
            self.logger.debug(
                "No op. created_date found; but not as a string as a: %s.",
                type(inner_value),
            )
        return inner_value

    def _newsletter_converter(self, acoustic_main_table, contact):
        # create the RT rows for the newsletter table in acoustic
        newsletter_rows = []
        contact_newsletters: List[NewsletterSchema] = contact.newsletters
        contact_email_id = str(contact.email.email_id)
        contact_email_format = contact.email.email_format
        contact_email_lang = contact.email.email_lang
        for newsletter in contact_newsletters:
            newsletter_template = {
                "email_id": contact_email_id,
                "newsletter_format": contact_email_format,
                "newsletter_lang": contact_email_lang,
            }

            if newsletter.name in AcousticResources.MAIN_TABLE_SUBSCR_FLAGS.keys():
                newsletter_dict = newsletter.dict()
                _today = datetime.date.today().isoformat()
                newsletter_template["create_timestamp"] = newsletter_dict.get(
                    "create_timestamp", _today
                )
                newsletter_template["update_timestamp"] = newsletter_dict.get(
                    "update_timestamp", _today
                )
                newsletter_template["newsletter_name"] = newsletter.name
                newsletter_template["newsletter_unsub_reason"] = newsletter.unsub_reason
                _source = newsletter.source
                if _source is not None:
                    _source = str(_source)
                newsletter_template["newsletter_source"] = _source

                newsletter_rows.append(newsletter_template)
                # and finally flip the main table's sub_<newsletter> flag to true for each subscription
                if newsletter.subscribed:
                    acoustic_main_table[
                        AcousticResources.MAIN_TABLE_SUBSCR_FLAGS[newsletter.name]
                    ] = "1"
            else:
                self.logger.debug(
                    "Skipping Newsletter (%s) because no match in Acoustic",
                    newsletter.name,
                )
        return newsletter_rows, acoustic_main_table

    @staticmethod
    def transform_field_for_acoustic(data):
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
                metric_params = {"method": "add_recipient", "status": status}
                self.metric_service.inc_acoustic_request_total(**metric_params)
                metric_params.update({"duration_s": duration_s})
                self.metric_service.observe_acoustic_request_duration(**metric_params)

    def _insert_update_newsletters(self, table_id=None, rows=None):
        if rows is None:
            rows = []
        params = {"table_id": table_id, "rows": rows}
        if self.metric_service is None:
            self.acoustic.insert_update_relational_table(**params)
        else:  # Metrics are enabled
            start_time = time.monotonic()
            status = "success"
            try:
                self.acoustic.insert_update_relational_table(
                    **params
                )  # Call to Acoustic
            except Exception:  # pylint: disable=broad-except
                status = "failure"
                raise
            finally:
                duration = time.monotonic() - start_time
                duration_s = round(duration, 3)
                metric_params = {
                    "method": "insert_update_relational_table",
                    "status": status,
                }
                self.metric_service.inc_acoustic_request_total(**metric_params)
                metric_params.update({"duration_s": duration_s})
                self.metric_service.observe_acoustic_request_duration(**metric_params)

    def attempt_to_upload_ctms_contact(self, contact: ContactSchema) -> bool:
        """

        :param contact: to be converted to acoustic table rows and uploaded
        :return: Boolean indicating True (success) or False (failure)
        """
        self.logger.debug("Converting and uploading contact to acoustic...")
        try:
            main_table_data, nl_data = self.convert_ctms_to_acoustic(contact)
            main_table_id = str(self.acoustic_main_table_id)
            self._add_contact(
                list_id=main_table_id,
                sync_fields={"email_id": main_table_data["email_id"]},
                columns=main_table_data,
            )
            newsletter_table_id = str(self.acoustic_newsletter_table_id)
            self._insert_update_newsletters(table_id=newsletter_table_id, rows=nl_data)
            # success
            self.logger.debug("Successfully sync'd contact to acoustic...")
            return True
        except SilverpopResponseException:
            # failure
            self.logger.exception("Failure for contact in sync to acoustic...")
            return False
