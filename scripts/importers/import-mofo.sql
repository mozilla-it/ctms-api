BEGIN TRANSACTION;

--Turn this on if you want to restart
--TRUNCATE mofo RESTART IDENTITY;

CREATE TEMP TABLE mofo_temp (email_id uuid, primary_email text, mofo_email_id text, mofo_contact_id text);
\COPY mofo_temp(primary_email,mofo_email_id,mofo_contact_id) FROM 'mofo_ids.csv' WITH (FORMAT CSV, DELIMITER ',', HEADER);

UPDATE mofo_temp SET email_id = emails.email_id FROM emails WHERE emails.primary_email = mofo_temp.primary_email;

\COPY (SELECT primary_email,mofo_email_id,mofo_contact_id FROM mofo_temp WHERE email_id is null) TO 'invalid-emails.csv' WITH (FORMAT CSV, DELIMITER ',', HEADER);

INSERT INTO mofo (email_id, mofo_email_id, mofo_contact_id, mofo_relevant) SELECT email_id, mofo_email_id, mofo_contact_id, true FROM mofo_temp where email_id is not null on conflict do nothing;

END TRANSACTION;
