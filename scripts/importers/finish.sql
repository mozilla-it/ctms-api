BEGIN TRANSACTION;

alter table emails add primary key (email_id);
alter table emails add constraint emails_basket_token_key unique (basket_token);
alter table emails add constraint emails_primary_email_key unique (primary_email);


alter table amo add primary key (id);
alter table amo add constraint amo_email_id_key unique (email_id);
alter table amo add constraint amo_email_id_fkey foreign key (email_id) references emails (email_id);

alter table fxa add primary key (id);
alter table fxa add constraint fxa_email_id_key unique (email_id);
alter table fxa add constraint fxa_fxa_id_key unique (fxa_id);
alter table fxa add constraint fxa_email_id_fkey foreign key (email_id) references emails (email_id);

alter table newsletters add primary key (id);
alter table newsletters add constraint uix_email_name unique (email_id, "name");
alter table newsletters add constraint newsletters_email_id_fkey foreign key (email_id) references emails (email_id);

alter table vpn_waitlist add primary key (id);
alter table vpn_waitlist add constraint vpn_waistlist_email_id_key unique (email_id);
alter table vpn_waitlist add constraint vpn_waistlist_email_id_fkey foreign key (email_id) references emails (email_id);

END TRANSACTION;
