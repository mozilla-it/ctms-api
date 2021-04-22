echo "EMAILS"
pv emails.csv | psql -h "$HOST" -p 5432 -U dataimport -d ctms -c "\COPY emails(primary_email,basket_token,sfdc_id,first_name,last_name,mailing_country,email_format,email_id,email_lang,double_opt_in,has_opted_out_of_email,unsubscribe_reason,create_timestamp,update_timestamp) FROM STDIN WITH (FORMAT CSV, DELIMITER ',', HEADER)";

echo "AMO"
pv amo.csv | psql -h "$HOST" -p 5432 -U dataimport -d ctms -c    "\COPY amo(email_id,add_on_ids,display_name,email_opt_in,language,last_login,location,profile_url,\"user\",user_id,username,create_timestamp,update_timestamp) FROM STDIN WITH (FORMAT CSV, DELIMITER ',', HEADER);"

echo "FXA"
pv fxa.csv | psql -h "$HOST" -p 5432 -U dataimport -d ctms -c    "\COPY fxa(email_id,fxa_id,account_deleted,lang,first_service,created_date,primary_email,create_timestamp,update_timestamp) FROM STDIN WITH (FORMAT CSV, DELIMITER ',', HEADER);"

echo "NEWSLETTERS"
pv newsletters.csv | psql -h "$HOST" -p 5432 -U dataimport -d ctms -c    "\COPY newsletters(email_id,name,subscribed,format,lang,source,unsub_reason,create_timestamp,update_timestamp) FROM STDIN WITH (FORMAT CSV, DELIMITER ',', HEADER);"

echo "VPN WAITLIST"
pv vpn_waitlist.csv | psql -h "$HOST" -p 5432 -U dataimport -d ctms -c   "\COPY vpn_waitlist(email_id,geo,platform,create_timestamp,update_timestamp) FROM STDIN WITH (FORMAT CSV, DELIMITER ',', HEADER);"
