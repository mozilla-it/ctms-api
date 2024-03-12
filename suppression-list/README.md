# CSV to Opt-Outs

### Prepare Input Files

Using a tool like [xsv](https://github.com/BurntSushi/xsv) to prepare the input CSV files and merge them into one that has the following columns:

```
email,reason
alice@corp.com,never subscribed
bob@fundation.org,
...
```

### Turn Into SQL

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

### Execute

On the server, execute them in order. Note that the `*apply*` files are idempotent, and can be interrupted if necessary.

```
$ psql -U admin -d ctms

=# \i example.csv.0.pre.sql

=# \i example.csv.1.apply.sql
=# \i example.csv.2.apply.sql
=# \i example.csv.3.apply.sql

=# \i example.csv.4.post.sql
```