import logging
import re

from django.utils.encoding import force_bytes
from lxml import etree
from silverpop.api import Silverpop, SilverpopResponseException

from ctms.schemas import ContactSchema

logger = logging.getLogger(__name__)


class AcousticResources:
    # TODO: externalize
    VALID_ACOUSTIC_MAIN_TABLE_FIELDS = {
        "sfdc_id": 1,
        "email": 1,
        "amo_add_on_ids": 1,
        "amo_display_name": 1,
        "amo_email_opt_in": 1,
        "amo_language": 1,
        "amo_last_login": 1,
        "amo_location": 1,
        "amo_profile_url": 1,
        "amo_user": 1,
        "amo_user_id": 1,
        "amo_username": 1,
        "create_timestamp": 1,
        "email_format": 1,
        "email_id": 1,
        "email_lang": 1,
        "vpn_waitlist_geo": 1,
        "vpn_waitlist_platform": 1,
        "fxa_id": 1,
        "fxa_account_deleted": 1,
        "fxa_lang": 1,
        "fxa_login_date": 1,
        "fxa_first_service": 1,
        "fxa_created_date": 1,
        "fxa_primary_email": 1,
        "double_opt_in": 1,
        "has_opted_out_of_email": 1,
        "mailing_country": 1,
        "first_name": 1,
        "last_name": 1,
        "sumo_contributor": 1,
        "sumo_user": 1,
        "sumo_username": 1,
        "basket_token": 1,
        "unsubscribe_reason": 1,
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
        logger.debug("Response: %s", resp.text)
        response = etree.fromstring(resp.text.encode("utf-8"))
        # success = response.find(".//SUCCESS")

        # how main table failures are reported:
        fault = response.find(".//Fault/FaultString")
        if fault is not None:
            print(fault.text)
            raise SilverpopResponseException(fault.text)

        # how RT failures are reported:    (hooray for consistency.)
        failures = response.findall(".//FAILURES/FAILURE")
        if failures is not None:
            for fail in failures:
                raise SilverpopResponseException(etree.tostring(fail))

        return response

    def _call(self, xml):
        logger.debug("Request: %s", xml)
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
        Constuct a CTMSToAcousticService object that can interface between contacts and acoustic forms of data
        """
        self.acoustic = Acoustic(
            client_id=client_id,
            client_secret=client_secret,
            refresh_token=refresh_token,
            server_number=server_number,
        )
        self.acoustic_main_table_id = acoustic_main_table_id
        self.acoustic_newsletter_table_id = acoustic_newsletter_table_id

    def _convert_ctms_to_acoustic(self, ctms_data: dict):
        # populate with all the sub_flags set to false
        # they'll get set to true below, as-needed
        acoustic_main_table = {
            v: "0" for v in AcousticResources.MAIN_TABLE_SUBSCR_FLAGS.values()
        }

        # flatten the "sub-dicts" into the main dict to match Acoustic's schema
        for subdict in ["amo", "fxa", "vpn_waitlist"]:
            for key, value in ctms_data[subdict].items():
                acoustic_field_name = subdict + "_" + key
                if key == "fxa_id":
                    acoustic_field_name = "fxa_id"
                if (
                    acoustic_field_name
                    in AcousticResources.VALID_ACOUSTIC_MAIN_TABLE_FIELDS
                ):
                    acoustic_main_table[
                        acoustic_field_name
                    ] = self._transform_field_for_acoustic(value)
                else:
                    print(
                        "Skipping CTMS field ctms_data[%s][%s] because no match in Acoustic"
                        % (subdict, key)
                    )

        for key, value in ctms_data["email"].items():
            acoustic_field_name = key
            if acoustic_field_name == "primary_email":
                acoustic_field_name = "email"
            if (
                acoustic_field_name
                in AcousticResources.VALID_ACOUSTIC_MAIN_TABLE_FIELDS
            ):
                acoustic_main_table[
                    acoustic_field_name
                ] = self._transform_field_for_acoustic(value)
            else:
                print(
                    "Skipping CTMS field ctms_data[email][%s] because no match in Acoustic"
                    % (key)
                )

        # create the RT rows for the newsletter table in acoustic
        newsletter_rows = []
        for newsletter in ctms_data["newsletters"]:
            newsletter_rows.append(
                {
                    "email_id": ctms_data["email"]["email_id"],
                    "newsletter_name": newsletter["name"],
                    "newsletter_format": newsletter["format"],
                    "newsletter_lang": newsletter["lang"],
                    "newsletter_source": newsletter["source"],
                    "newsletter_unsub_reason": newsletter["unsub_reason"],
                    "create_date": self._transform_field_for_acoustic(
                        newsletter["create_timestamp"]
                    ),
                    "update_date": self._transform_field_for_acoustic(
                        newsletter["update_timestamp"]
                    ),
                }
            )
            # and finally flip the main table's sub_<newsletter> flag to true for each subscription
            if newsletter["subscribed"]:
                acoustic_main_table[
                    AcousticResources.MAIN_TABLE_SUBSCR_FLAGS[newsletter["name"]]
                ] = "1"

        return acoustic_main_table, newsletter_rows

    @staticmethod
    def _transform_field_for_acoustic(data):
        if isinstance(data, bool):
            if data:
                return "1"
            return "0"
        # Acoustic doesn't have timestamps, so make timestamps into dates.
        # Is this appropriate for all TS fields?
        # Is the below RE appropriate for what we'll actually be getting from Postgres?
        try:
            matching = re.search(r"^(\d{4}-\d{2}-\d{2})T\d", data)
            if matching:
                return matching.groups()[0]
        except TypeError:
            pass
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

    def attempt_to_upload_ctms_contact(self, contact: ContactSchema):
        """

        :param contact: to be converted to acoustic table rows and uploaded
        :return: Boolean indicating True (success) or False (failure)
        """
        try:
            main_table_data, nl_data = self._convert_ctms_to_acoustic(contact.dict())

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
