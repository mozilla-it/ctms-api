import csv
from datetime import datetime, timezone
import logging
from pathlib import Path
import sys

import click


logger = logging.getLogger(__name__)


SQL_COMMANDS_PRE = """
CREATE OR REPLACE PROCEDURE raise_notice (s TEXT) LANGUAGE plpgsql AS
$$
BEGIN
    RAISE NOTICE '%', s;
END;
$$;

CREATE TEMPORARY TABLE IF NOT EXISTS imported_{tmp_suffix} (
  email TEXT,
  unsubscribe_reason TEXT
);

CALL raise_notice('Start CSV import ({csv_rows_count} rows)...');

COPY imported_{tmp_suffix}(email, unsubscribe_reason)
  FROM '{csv_path}' -- fullpath
  DELIMITER '{delimiter}'
  {headers};

CALL raise_notice('CSV import done.');

CALL raise_notice('Join on existing contacts...');

CREATE TABLE IF NOT EXISTS optouts_{tmp_suffix} (
  idx SERIAL UNIQUE,
  email_id UUID,
  unsubscribe_reason TEXT
);

WITH all_primary_emails AS (
  SELECT email_id, primary_email FROM emails
   WHERE has_opted_out_of_email IS NOT true
  UNION
   SELECT email_id, primary_email FROM fxa
)
INSERT INTO optouts_{tmp_suffix}(email_id, unsubscribe_reason)
  SELECT email_id, unsubscribe_reason
  FROM imported_{tmp_suffix}
    JOIN all_primary_emails
      ON primary_email = email;

CALL raise_notice('Join on existing contacts done.');

SELECT COUNT(*) FROM optouts_{tmp_suffix};
"""

SQL_COMMANDS_POST = """
DROP PROCEDURE raise_notice;
DROP optouts_{tmp_suffix} CASCADE;
"""

SQL_BATCH = """
BEGIN;

CALL raise_notice('Batch {batch}/{batch_count}');

UPDATE emails
  SET update_timestamp = now(),
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
@click.argument('csv_path', type=click.Path(exists=True))
@click.option('--batch-size', default=10000, help='Number of updates per commit.')
@click.option('--files-count', default=5, help='Number of SQL files')
@click.option('--sleep-seconds', default=0.1, help='Wait between batches')
@click.option('--schedule-sync', default=False, help='Mark update emails as pending sync')
def main(csv_path, batch_size, files_count, sleep_seconds, schedule_sync) -> int:
    now = datetime.now(tz=timezone.utc)
    tmp_suffix = now.strftime("%Y%m%dT%H%M")
    with open(csv_path) as f:
        csv_rows_count = sum(1 for _ in f)
        f.seek(0)
        delimiter = csv.Sniffer().sniff(f.read(1024)).delimiter
        f.seek(0)
        has_headers = csv.Sniffer().has_header(f.read(1024))
        if has_headers:
            csv_rows_count -= 1

    batch_count = 1 + csv_rows_count // batch_size

    logger.info(f"{csv_rows_count} entries, {batch_count} batches of {batch_size} updates per commit.")

    batch_commands = []
    for i in range(batch_count):
        start_idx = i * batch_size
        end_idx = (i + 1) * batch_size
        batch_commands.append(
            SQL_BATCH.format(
                batch=i,
                batch_count=batch_count,
                start_idx=start_idx,
                end_idx=end_idx,
                tmp_suffix=tmp_suffix,
                sleep_seconds=sleep_seconds,
                schedule_sync=str(schedule_sync).lower(),
            )
        )

    csv_filename = Path(csv_path).name
    writefile(
        f"{csv_filename}.0.pre.sql",
        SQL_COMMANDS_PRE.format(
            headers="CSV HEADER" if has_headers else "",
            csv_rows_count=csv_rows_count,
            delimiter=delimiter,
            tmp_suffix=tmp_suffix,
            csv_path=csv_filename,
        ),
    )

    chunk_size = 1 + batch_count // files_count
    file_count = 0
    for batch in chunks(batch_commands, chunk_size):
        file_count += 1
        writefile(f"{csv_filename}.{file_count}.apply.sql", "".join(batch))

    logger.info(f"Produced {file_count} files, with {chunk_size} commits ({chunk_size * batch_size} updates).")

    writefile(
        f"{csv_filename}.{file_count + 1}.post.sql",
        SQL_COMMANDS_POST.format(
            tmp_suffix=tmp_suffix,
        ),
    )
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    sys.exit(main())
