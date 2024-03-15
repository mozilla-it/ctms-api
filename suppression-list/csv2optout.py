import csv
import logging
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import click

logger = logging.getLogger(__name__)


SQL_COMMANDS_PRE = """
CREATE OR REPLACE PROCEDURE raise_notice (s TEXT) LANGUAGE plpgsql AS
$$
BEGIN
    RAISE NOTICE '%', s;
END;
$$;

CREATE TEMPORARY TABLE IF NOT EXISTS csv_import (
  idx SERIAL UNIQUE,
  email TEXT,
  tstxt TEXT,
  unsubscribe_reason TEXT
);

CALL raise_notice('Start CSV import ({csv_rows_count} rows)...');

COPY csv_import(email, tstxt, unsubscribe_reason)
  FROM '{csv_path}' -- fullpath
  DELIMITER '{delimiter}'
  {headers}
  QUOTE AS '"';

CALL raise_notice('CSV import done.');

CREATE TABLE IF NOT EXISTS optouts_{tmp_suffix} (
  idx SERIAL UNIQUE,
  email_id UUID,
  unsubscribe_reason TEXT,
  ts TIMESTAMP
);

CALL raise_notice('Join on existing contacts...');
{join_batches}
CALL raise_notice('Join on existing contacts done.');

SELECT COUNT(*) FROM optouts_{tmp_suffix};
"""

SQL_JOIN_BATCH = """
BEGIN;

CALL raise_notice('Update batch {batch}/{batch_count}');

WITH all_primary_emails AS (
  SELECT email_id, primary_email FROM emails
   WHERE has_opted_out_of_email IS NOT true
  UNION
   SELECT email_id, primary_email FROM fxa
)
INSERT INTO optouts_{tmp_suffix}(idx, email_id, unsubscribe_reason, ts)
  SELECT
    idx,
    email_id,
    unsubscribe_reason,
    to_timestamp(tstxt,'YYYY-MM-DD HH12:MI AM')::timestamp AS ts
  FROM csv_import
    JOIN all_primary_emails
      ON primary_email = email
    WHERE idx > {start_idx} AND idx <= {end_idx};

COMMIT;
"""

SQL_COMMANDS_POST = """
DROP PROCEDURE raise_notice;
DROP optouts_{tmp_suffix} CASCADE;
"""

SQL_UPDATE_BATCH = """
BEGIN;

CALL raise_notice('Join batch {batch}/{batch_count}');

UPDATE emails
  SET update_timestamp = tmp.ts,
      has_opted_out_of_email = true,
      unsubscribe_reason = tmp.unsubscribe_reason
  FROM optouts_{tmp_suffix} tmp
  WHERE tmp.email_id = emails.email_id
    AND tmp.idx > {start_idx} AND tmp.idx <= {end_idx}
    -- Do not overwrite reason if user opted-out in the mean time
    AND has_opted_out_of_email IS NOT true;

INSERT INTO pending_acoustic(email_id, retry)
  SELECT email_id, 0 FROM optouts_{tmp_suffix}
    WHERE {schedule_sync} AND idx > {start_idx} AND idx <= {end_idx};

DELETE FROM optouts_{tmp_suffix}
  WHERE idx > {start_idx} AND idx <= {end_idx};

COMMIT;

SELECT pg_sleep({sleep_seconds});
"""


def chunks(l, n):
    for i in range(0, len(l), n):
        yield l[i : i + n]


def writefile(path, content):
    with open(path, "w") as f:
        f.write(content)
    logger.info(f"{path!r} written.")


@click.command()
@click.argument("csv_path", type=click.Path(exists=True))
@click.option(
    "--check-input-rows", default=1000, help="Number of rows to check from input CSV."
)
@click.option("--batch-size", default=10000, help="Number of updates per commit.")
@click.option("--files-count", default=5, help="Number of SQL files")
@click.option("--sleep-seconds", default=0.1, help="Wait between batches")
@click.option(
    "--schedule-sync", default=False, help="Mark update emails as pending sync"
)
@click.option(
    "--csv-path-server", default=".", help="Absolute path where to load the CSV from"
)
def main(
    csv_path,
    check_input_rows,
    batch_size,
    files_count,
    sleep_seconds,
    schedule_sync,
    csv_path_server,
) -> int:
    #
    # Inspect CSV input.
    #
    with open(csv_path) as f:
        csv_rows_count = sum(1 for _ in f)
        f.seek(0)
        delimiter = csv.Sniffer().sniff(f.read(1024)).delimiter
        f.seek(0)
        has_headers = csv.Sniffer().has_header(f.read(1024))
        f.seek(0)

        # Check format of X entries.
        reader = csv.reader(f)
        if has_headers:
            next(reader)
        for i, row in enumerate(reader):
            if i >= check_input_rows:
                break
            try:
                email, date, reason = row
                assert "@" in email
                assert re.match(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2} (AM|PM)", date)
            except (AssertionError, ValueError):
                raise ValueError(f"Line '{row}' does not look right")

    batch_count = 1 + csv_rows_count // batch_size
    chunk_size = 1 + batch_count // files_count
    logger.info(f"{csv_rows_count} entries")
    logger.info(f"{batch_size} updates per commit")
    logger.info(f"{batch_count} batches")
    logger.info(f"{files_count} files")
    logger.info(f"~{chunk_size} commits per file")
    #
    # Prepare SQL files
    #
    now = datetime.now(tz=timezone.utc)
    tmp_suffix = now.strftime("%Y%m%dT%H%M")
    join_batches = []
    update_batches = []
    for i in range(batch_count):
        start_idx = i * batch_size
        end_idx = (i + 1) * batch_size
        params = dict(
            batch=i + 1,
            batch_count=batch_count,
            start_idx=start_idx,
            end_idx=end_idx,
            tmp_suffix=tmp_suffix,
            sleep_seconds=sleep_seconds,
        )
        join_batches.append(SQL_JOIN_BATCH.format(**params))
        update_batches.append(
            SQL_UPDATE_BATCH.format(
                schedule_sync=str(schedule_sync).lower(),
                **params,
            )
        )

    csv_filename = Path(csv_path).name
    writefile(
        f"{csv_filename}.0.pre.sql",
        SQL_COMMANDS_PRE.format(
            headers="CSV HEADER" if has_headers else "",
            join_batches="".join(join_batches),
            csv_rows_count=csv_rows_count,
            delimiter=delimiter,
            tmp_suffix=tmp_suffix,
            csv_path=os.path.join(csv_path_server, csv_filename),
        ),
    )

    chunked = list(chunks(update_batches, chunk_size))
    file_count = len(chunked)
    for i, batch in enumerate(chunked):
        writefile(
            f"{csv_filename}.{i+1}.apply.sql",
            "".join(batch) + f"CALL raise_notice('File {i+1}/{file_count} done.');",
        )

    logger.info(
        f"Produced {file_count} files, with {chunk_size} commits ({chunk_size * batch_size} updates)."
    )

    writefile(
        f"{csv_filename}.{file_count+1}.post.sql",
        SQL_COMMANDS_POST.format(
            tmp_suffix=tmp_suffix,
        ),
    )
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    sys.exit(main())
