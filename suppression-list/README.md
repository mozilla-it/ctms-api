# CSV to Opt-Outs

## Prepare Input Files

Using a tool like [xsv](https://github.com/BurntSushi/xsv) to prepare the input CSV files and merge them into one that has the following columns:

```
"Email","Reason","Date"
"alice@corp.com","never subscribed","20200310"
"bob@fundation.org",,"20240501"
"postmaster@localhost","marked undeliverable","19700101"
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
    CASE WHEN random() < 0.5 THEN primary_email ELSE substr(md5(random()::text), 1, (random() * 15)::int) || '.fxa@' || substr(md5(random()::text), 1, (random() * 10)::int) || '.' || substr(md5(random()::text), 1, 3) END AS primary_email
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
    SELECT email, reason
    FROM (
        SELECT primary_email AS email, md5(random()::text) AS reason FROM emails TABLESAMPLE BERNOULLI(5)
        UNION
        SELECT primary_email AS email, md5(random()::text) AS reason FROM fxa TABLESAMPLE BERNOULLI(10)
    ) t
) TO '/tmp/optouts.csv';
```
