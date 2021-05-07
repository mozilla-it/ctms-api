import datetime
import logging
from decimal import Decimal
from typing import List

from lxml import etree
from silverpop.api import Silverpop, SilverpopResponseException

from ctms.schemas import ContactSchema, NewsletterSchema

logger = logging.getLogger(__name__)

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
        response = etree.fromstring(resp.text.encode("utf-8"))
        # success = response.find(".//SUCCESS")

        # how main table failures are reported:
        fault = response.find(".//Fault/FaultString")
        if fault is not None:
            # print(fault.text) # TODO: Convert to logging
            raise SilverpopResponseException(fault.text)

        # how RT failures are reported:    (hooray for consistency.)
        failures = response.findall(".//FAILURES/FAILURE")
        if failures is not None:
            raise SilverpopResponseException(
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
        client_id,
        client_secret,
        refresh_token,
        acoustic_main_table_id,
        acoustic_newsletter_table_id,
        server_number=6,
    ):
        """
        Construct a CTMSToAcousticService object that can interface between contacts and acoustic forms of data
        """
        self.acoustic = Acoustic(
            client_id=client_id,
            client_secret=client_secret,
            refresh_token=refresh_token,
            server_number=server_number,
        )
        self.acoustic_main_table_id = int(acoustic_main_table_id)
        self.acoustic_newsletter_table_id = int(acoustic_newsletter_table_id)

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
                        acoustic_main_table[
                            acoustic_field_name
                        ] = self.transform_field_for_acoustic(inner_value)
                    # else:
                    # print(f"Skipping CTMS field ({contact_attr}, {inner_attr}) because no match "
                    #       f"in Acoustic") # TODO: Convert to logging
        return acoustic_main_table

    def _newsletter_converter(self, acoustic_main_table, contact):
        # create the RT rows for the newsletter table in acoustic
        newsletter_rows = []
        contact_newsletters: List[NewsletterSchema] = contact.newsletters
        for newsletter in contact_newsletters:
            if newsletter.name in AcousticResources.MAIN_TABLE_SUBSCR_FLAGS.keys():
                newsletter_dict = newsletter.dict()
                create_timestamp = datetime.date.today().isoformat()
                if "create_timestamp" in newsletter_dict:
                    create_timestamp = newsletter_dict["create_timestamp"]
                update_timestamp = datetime.date.today().isoformat()
                if "update_timestamp" in newsletter_dict:
                    update_timestamp = newsletter_dict["update_timestamp"]
                newsletter_template = {
                    "email_id": contact.email.email_id,
                    "newsletter_name": newsletter.name,
                    "newsletter_format": newsletter.format,
                    "newsletter_lang": newsletter.lang,
                    "newsletter_source": newsletter.source,
                    "newsletter_unsub_reason": newsletter.unsub_reason,
                    "create_date": create_timestamp,
                    "update_date": update_timestamp,
                }
                newsletter_rows.append(newsletter_template)
                # and finally flip the main table's sub_<newsletter> flag to true for each subscription
                if newsletter.subscribed:
                    acoustic_main_table[
                        AcousticResources.MAIN_TABLE_SUBSCR_FLAGS[newsletter.name]
                    ] = "1"
            # else:
            # print(f"Skipping Newsletter {newsletter.name} because no match in Acoustic") # TODO: Convert to logging
        return newsletter_rows, acoustic_main_table

    @staticmethod
    def transform_field_for_acoustic(data):
        if isinstance(data, bool):
            if data:
                return "1"
            return "0"
        if isinstance(data, datetime.datetime):
            # Acoustic doesn't have timestamps, so make timestamps into dates.
            return data.date().isoformat()
        if isinstance(data, datetime.date):
            return data.isoformat()
        return data

    def _add_contact(self, list_id=None, sync_fields=None, columns=None):
        if columns is None:
            columns = {}
        if sync_fields is None:
            sync_fields = {}
        self.acoustic.add_recipient(
            list_id=list_id,
            created_from=3,
            update_if_found="TRUE",
            allow_html=False,
            sync_fields=sync_fields,
            columns=columns,
        )

    def _insert_update_newsletters(self, table_id=None, rows=None):
        if rows is None:
            rows = []
        self.acoustic.insert_update_relational_table(
            table_id=table_id,
            rows=rows,
        )

    def attempt_to_upload_ctms_contact(self, contact: ContactSchema) -> bool:
        """

        :param contact: to be converted to acoustic table rows and uploaded
        :return: Boolean indicating True (success) or False (failure)
        """
        try:
            main_table_data, nl_data = self.convert_ctms_to_acoustic(contact)

            main_table_id = self.acoustic_main_table_id
            self._add_contact(
                list_id=main_table_id,
                sync_fields={"email_id": main_table_data["email_id"]},
                columns=main_table_data,
            )

            newsletter_table_id = self.acoustic_newsletter_table_id
            self._insert_update_newsletters(table_id=newsletter_table_id, rows=nl_data)
            # success
            return True
        except SilverpopResponseException:
            # failure
            return False
