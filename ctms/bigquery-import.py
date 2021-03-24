from google.cloud import bigquery
import os 

if "GOOGLE_APPLICATION_CREDENTIALS" not in os.environ:
    # TODO: put this in secrets somewhere
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "mozilla-cdp-prod-810d22419b61.json"

class BigQuerySFDCData():

    def __init__(self):
        self.bq_client = bigquery.Client()

    def get_table_rows(self, table_name=None, delta=True):

        if not table_name in ['email', 'fxa', 'newsletter', 'vpn_waitlist']:
            raise Exception(f"I don't understand table_name: {table_name}")

        if delta:
            full_table_name = f"CTMS_contact_updates_to_{table_name}"
        else:
            full_table_name = f"CTMS_contact_to_{table_name}"
    
        query = f"SELECT * FROM `mozilla-cdp-prod.sfdc_exports.{full_table_name}`"
    
        query_job_rows = self.bq_client.query(query)
    
        return query_job_rows

# usage:
# To get the last three hours of newsletter table updates:
# rows = BigQuerySFDCData().get_table_rows("newsletter", delta=True)
# for row in rows:
#     print(f"row['email_id']: {row['email_id']} row['newsletter_name']: {row['newsletter_name']}")
#
# To get _all_ the email table rows:
# rows = BigQuerySFDCData().get_table_rows("email", delta=False)
# for row in rows:
#     print(f"row['email_id']: {row['email_id']} row['primary_email']: {row['primary_email']}")
#
# Fields in tables:
#
# CTMS_contact_to_email
# ---------------------
# primary_email          STRING  NULLABLE 
# basket_token           STRING  NULLABLE 
# sfdc_id                STRING  NULLABLE 
# first_name             STRING  NULLABLE 
# last_name              STRING  NULLABLE 
# mailing_country        STRING  NULLABLE 
# email_format           STRING  NULLABLE 
# email_id               STRING  NULLABLE 
# email_lang             STRING  NULLABLE 
# double_opt_in          BOOLEAN NULLABLE 
# has_opted_out_of_email BOOLEAN NULLABLE 
# unsubscribe_reason     STRING  NULLABLE 
# create_timestamp       STRING  NULLABLE 
# update_timestamp       STRING  NULLABLE 
#
# CTMS_contact_to_amo
# -------------------
# email_id             STRING     NULLABLE     
# amo_add_on_ids       STRING     NULLABLE     
# amo_display_name     STRING     NULLABLE     
# amo_email_opt_in     BOOLEAN    NULLABLE     
# amo_language         STRING     NULLABLE     
# amo_last_login       STRING     NULLABLE     
# amo_location         STRING     NULLABLE     
# amo_profile_url      STRING     NULLABLE     
# amo_user             BOOLEAN    NULLABLE     
# amo_user_id          STRING     NULLABLE     
# amo_username         STRING     NULLABLE     
# create_timestamp     STRING     NULLABLE     
# update_timestamp     STRING     NULLABLE     
#
# CTMS_contact_to_fxa
# -------------------
# email_id             STRING     NULLABLE     
# fxa_id               STRING     NULLABLE     
# fxa_account_deleted  BOOLEAN    NULLABLE     
# fxa_lang             STRING     NULLABLE     
# fxa_first_service    STRING     NULLABLE     
# fxa_created_date     STRING     NULLABLE     
# fxa_primary_email    STRING     NULLABLE     
# create_timestamp     STRING     NULLABLE     
# update_timestamp     STRING     NULLABLE     
#
# CTMS_contact_to_newsletter
# --------------------------
# email_id                    STRING     NULLABLE     
# newsletter_name             STRING     NULLABLE     
# subscribed                  BOOLEAN    NULLABLE     
# newsletter_format           STRING     NULLABLE     
# newsletter_lang             STRING     NULLABLE     
# newsletter_source           STRING     NULLABLE     
# newsletter_unsub_reason     STRING     NULLABLE     
# create_timestamp            STRING     NULLABLE     
# update_timestamp            STRING     NULLABLE     
#
# CTMS_contact_to_vpn_waitlist
# ----------------------------
# email_id               STRING     NULLABLE     
# vpn_waitlist_geo       STRING     NULLABLE     
# vpn_waitlist_platform  STRING     NULLABLE     
# create_timestamp       STRING     NULLABLE     
# update_timestamp       STRING     NULLABLE     
