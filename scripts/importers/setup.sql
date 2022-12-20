BEGIN TRANSACTION;

TRUNCATE emails RESTART IDENTITY CASCADE;
TRUNCATE amo RESTART IDENTITY;
TRUNCATE fxa RESTART IDENTITY;
TRUNCATE newsletters RESTART IDENTITY;

ALTER TABLE amo DROP CONSTRAINT amo_pkey;
ALTER TABLE amo DROP CONSTRAINT amo_email_id_key;
ALTER TABLE amo DROP CONSTRAINT amo_email_id_fkey;

ALTER TABLE fxa DROP CONSTRAINT fxa_pkey;
ALTER TABLE fxa DROP CONSTRAINT fxa_email_id_key;
ALTER TABLE fxa DROP CONSTRAINT fxa_fxa_id_key;
ALTER TABLE fxa DROP CONSTRAINT fxa_email_id_fkey;

ALTER TABLE newsletters DROP CONSTRAINT newsletters_pkey;
ALTER TABLE newsletters DROP CONSTRAINT uix_email_name;
ALTER TABLE newsletters DROP CONSTRAINT newsletters_email_id_fkey;

ALTER TABLE mofo DROP CONSTRAINT mofo_email_id_fkey;

ALTER TABLE emails DROP CONSTRAINT emails_pkey;
ALTER TABLE emails DROP CONSTRAINT emails_basket_token_key;
ALTER TABLE emails DROP CONSTRAINT emails_primary_email_key;
DROP INDEX bulk_read_index;

END TRANSACTION;
