# CSV to Opt-Outs

## Prepare Input Files

Using a tool like [xsv](https://github.com/BurntSushi/xsv) to prepare the input CSV files and merge them into one that has the following columns:

```
"Email","Date","Reason"
"alice@corp.com","2024-03-12 05:17 PM","Opted out from list id 1364939"
"bob@fundation.org","2024-03-12 05:29 PM",
"postmaster@localhost","2024-03-12 10:11 AM","marked undeliverable"
...
```

## Turn Into SQL

A Python script with turn the specified CSV into SQL files to be executed on the server.

```
$ poetry shell
$ python suppression-list/csv2optout.py example.csv
INFO:__main__:2 entries, 1 batches.
INFO:__main__:'example.csv.0.pre.sql' written.
INFO:__main__:'example.csv.1.apply.sql' written.
INFO:__main__:'example.csv.2.post.sql' written.
```

Upload all the files to server, including the input CSV. Use `tar` and `scp` for example:

```
$ tar -zcvf "$(date '+%Y-%m-%d')-example.csv.tar.gz" example.csv*
$ scp 20240313-example.csv.tar.gz user@server:.
```

## Execute

On the server, execute them in order. Note that the `*apply*` files are idempotent, and can be interrupted if necessary.

First, alter the `*pre*` script to put the full path to the CSV. For example using `sed`:

```
$ sed s/"FROM 'example.csv'"/"FROM '\\/path\\/to\\/example.csv'"/ example.csv.0.pre.sql
```

And then execute them from `psql`:

```
$ psql -U admin -d ctms

=# \i example.csv.0.pre.sql

...
psql:example.csv.0.pre.sql:23: NOTICE:  Join on existing contacts...
CALL
INSERT 0 50430
...
psql:example.csv.0.pre.sql:43: NOTICE:  Join on existing contacts done.
CALL
 count
-------
 50430
(1 row)

```

Then execute each file with its thousands of batches of commits:

```
=# \i example.csv.1.apply.sql
=# \i example.csv.2.apply.sql
=# \i example.csv.3.apply.sql
```

And then cleanup:

```
=# \i example.csv.4.post.sql
```

## Development

Create a database locally with fake data.

```
$ pg_dump -d ctms -U postgres -t 'emails' -t 'fxa' -t 'pending_acoustic' --schema-only --no-acl --no-owner  > suppression-list/schema.sql
```

```
$ psql -U postgres -d postgres

postgres=# CREATE DATABASE optouts;
CREATE DATABASE
postgres=#
postgres=# \c optouts
You are now connected to database "optouts" as user "postgres".
optouts=#
optouts=# SET search_path TO public;
SET
optouts=#
optouts=# \i schema.sql
...
optouts=#
```

Generate ~1M fake emails.

```sql
INSERT INTO emails(email_id, primary_email)
  SELECT
    gen_random_uuid() AS email_id,
    substr(md5(random()::text), 1, (random() * 15)::int) || '@' || substr(md5(random()::text), 1, (random() * 10)::int) || '.' || substr(md5(random()::text), 1, 3) AS primary_email
  FROM generate_series(1, 1000000)
ON CONFLICT DO NOTHING;
```

Create an FxA account for 1% of them, with half of them using the same primary email.

```sql
INSERT INTO fxa(email_id, fxa_id, primary_email)
  SELECT
    email_id,
    substr(md5(random()::text), 1, 100) AS fxa_id,
    CASE WHEN random() < 0.5 THEN primary_email ELSE substr(md5(random()::text), 1, (random() * 15)::int + 1) || '.fxa@' || substr(md5(random()::text), 1, (random() * 10)::int) || '.' || substr(md5(random()::text), 1, 3) END AS primary_email
  FROM emails TABLESAMPLE BERNOULLI(1)
ON CONFLICT DO NOTHING;
```

Mark as opt-out 1% of them:

```sql
UPDATE emails SET has_opted_out_of_email = true
FROM (SELECT email_id FROM emails TABLESAMPLE BERNOULLI(1)) sub
WHERE sub.email_id = emails.email_id;
```

Product a CSV to opt-out some of them:

```
optouts=# COPY (
    SELECT email, to_char(date, 'YYYY-MM-DD HH12:MI AM') AS date, reason
    FROM (
        SELECT primary_email AS email, NOW() - (random() * (INTERVAL '1 year')) AS date, md5(random()::text) AS reason FROM emails TABLESAMPLE BERNOULLI(5)
        UNION
        SELECT primary_email AS email, NOW() - (random() * (INTERVAL '1 year')) AS date, md5(random()::text) AS reason FROM fxa TABLESAMPLE BERNOULLI(10)
    ) t
) TO '/tmp/optouts.csv' WITH CSV HEADER DELIMITER ',' FORCE QUOTE *;
```

## Full Cookbook on STAGE

## Preparation of SQL files

This section does not have to be done again for PROD.


Using these input files:

* `TAFTI_Unengaged.CSV`

```
$ head suppression-list/TAFTI_Unengaged.CSV
Email,Reason
xxxx@web.de,TAFTI Behaviorally Unengaged 2024
```

* `Acoustic_Main_Suppression_List_20240314.CSV`

```
$ head suppression-list/Acoustic_Main_Suppression_List_20240314.CSV
"Email","Opt In Date","Opt In Details"
"xxxxx@yahoo.com","2021-01-13 03:00 PM","User Name: sftpdrop_moco@mozilla.com. IP Address: 0.0.0.0"
```

I created a single CSV file `20240318-suppression-list.csv`:

```
$ head 20240318-suppression-list.csv
"Email","Date","Reason"
"xxxx@web.de","2024-03-18 05:32 PM","TAFTI Behaviorally Unengaged 2024"
```

Which I turned into SQL files to be executed using this command:

```
$ python csv2optout.py 20240318-suppression-list.csv --csv-path-server=`pwd`
```


## Import the CSV First

Since the `COPY` SQL command requires `superuser` privileges, we will do this first manually using `\copy`.

```
ERROR:  must be superuser or a member of the pg_read_server_files role to COPY from a file
HINT:  Anyone can COPY to stdout or from stdin. psql's \copy command also works for anyone.
```

Create the table manually:

```
CREATE TABLE csv_import (
  idx SERIAL UNIQUE,
  email TEXT,
  tstxt TEXT,
  unsubscribe_reason TEXT
);
```
And import the `20240318-suppression-list.csv` file:
```
ctms=> \copy csv_import(email, tstxt, unsubscribe_reason) FROM '20240318-suppression-list.csv' WITH DELIMITER ',' CSV HEADER QUOTE AS '"';
```


## Execute the SQL files

Enable logging of elapsed time and abort on error.

```
ctms=> \timing
ctms=> \set ON_ERROR_STOP on
```

The first SQL will join the imported CSV with the emails. This does not alter any existing table.

This took around 3H in STAGE.

```
ctms=> \i 20240318-suppression-list.csv.0.pre.sql
```

> Note: This script is idempotent, and be (re)executed several times if necessary.


The following SQL files will perform the updates on the `emails` table.

They should take around 2H each.

```
ctms=> \i 20240318-suppression-list.csv.1.apply.sql
```

```
ctms=> \i 20240318-suppression-list.csv.2.apply.sql
```

```
ctms=> \i 20240318-suppression-list.csv.3.apply.sql
```


## Cleanup

```
ctms=> \i 20240318-suppression-list.csv.4.post.sql
```
