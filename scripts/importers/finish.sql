-- We can set up these right out of the gate because
-- we know these are always defined and unique already
alter table emails add primary key (email_id);
alter table amo add primary key (id);
alter table fxa add primary key (id);
alter table newsletters add primary key (id);
alter table vpn_waitlist add primary key (id);
alter table amo add constraint amo_email_id_key unique (email_id);
alter table fxa add constraint fxa_email_id_key unique (email_id);
alter table newsletters add constraint uix_email_name unique (email_id, "name");
alter table vpn_waitlist add constraint vpn_waitlist_email_id_key unique (email_id);
alter table fxa add constraint fxa_fxa_id_key unique (fxa_id);

-- Easy enough to add this now too
create index bulk_read_index on emails (update_timestamp, email_id);

-- There's nothing we can do to save these (missing primary_email)
delete from emails where primary_email = ''; -- about 125447 records

-- But these we can save! (missing basket_token)
CREATE EXTENSION "uuid-ossp";
update emails set basket_token = uuid_generate_v4() where basket_token = '';
DROP EXTENSION "uuid-ossp";

-- Get rid of duplicate primary_emails
delete from emails where email_id in (select email_id from (select email_id, row_number() over w as rnum from emails window w as (partition by primary_email order by email_format, has_opted_out_of_email desc, update_timestamp desc)) t where t.rnum > 1);
-- And duplicate basket_tokens
delete from emails where email_id in (select email_id from (select email_id, row_number() over w as rnum from emails window w as (partition by basket_token order by email_format, has_opted_out_of_email desc, update_timestamp desc)) t where t.rnum > 1);

-- After which we can re-enable the unique constraints
alter table emails add constraint emails_primary_email_key unique (primary_email);
alter table emails add constraint emails_basket_token_key unique (basket_token);

-- Cascade those deletes we've just done to the other tables
delete from amo where not exists (select from emails where email_id = amo.email_id);
delete from fxa where not exists (select from emails where email_id = fxa.email_id);
delete from newsletters where not exists (select from emails where email_id = newsletters.email_id);
delete from vpn_waitlist where not exists (select from emails where email_id = vpn_waitlist.email_id);

-- Now add the foreign keys back!
alter table amo add constraint amo_email_id_fkey foreign key (email_id) references emails (email_id);
alter table fxa add constraint fxa_email_id_fkey foreign key (email_id) references emails (email_id);
alter table newsletters add constraint newsletters_email_id_fkey foreign key (email_id) references emails (email_id);
alter table vpn_waitlist add constraint vpn_waitlist_email_id_fkey foreign key (email_id) references emails (email_id);
alter table mofo add constraint mofo_email_id_fkey foreign key (email_id) references emails (email_id);

-- One more cleanup
update newsletters set "format" = 'T' where "format" = 'N';
alter table newsletters drop column source, add column source text;
