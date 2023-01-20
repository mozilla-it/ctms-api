from dataclasses import dataclass, fields
from time import monotonic
from typing import Any, Generator, List

from pydantic import BaseModel
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import Connection

from ctms.database import Base
from ctms.models import AmoAccount, Email, FirefoxAccount, Newsletter, Waitlist


@dataclass
class InputIOs:
    amo: Any = None
    emails: Any = None
    fxa: Any = None
    newsletters: Any = None
    waitlists: Any = None

    def finalize(self):
        missing = []
        for name in [f.name for f in fields(self)]:
            if getattr(self, name) is None:
                missing.append(name)

        if missing:
            raise BaseException(f"Must provide data for all tables. Missing {missing}")


class Ingester:
    def __init__(
        self,
        inputs: InputIOs,
        connection: Connection,
        batch_size: int = 10,
        total_inputs: int = 0,
    ):
        self.inputs = inputs
        self.db = connection
        self.batch_size = batch_size
        self.total_inputs = total_inputs

    def _insert_batch(self, batch: List[BaseModel], table: Base, stmt_args: dict):
        if len(batch) == 0:
            return

        # TODO: Handle things like `psycopg2.errors.DatatypeMismatch: column "email_id" is of type uuid but expression is of type integer`
        # smartly. This should mean something like recording which records
        # failed and why maybe if we're lucky? Also retries for disconnects
        # or other kinds of failures?
        stmt = insert(table).values(batch)
        stmt = stmt.on_conflict_do_update(**stmt_args, set_=dict(stmt.excluded))
        self.db.execute(stmt)

    def _table_loop(
        self,
        feed: Generator[BaseModel, None, None],
        table: Base,
        stmt_args: dict,
    ):
        batch = []
        prev = monotonic()
        for model in feed:
            batch.append(model)
            if len(batch) == self.batch_size:
                self._insert_batch(batch, table, stmt_args)
                batch = []
                now = monotonic()
                elapsed = now - prev
                per_second = int(self.batch_size / elapsed)
                print(f"Writing approx. {per_second} rows/second")
                prev = now
        # Finally write whatever is left over
        self._insert_batch(batch, table, stmt_args)

    def run(self):
        with self.db.begin():
            self._table_loop(
                self.inputs.emails, Email, {"index_elements": [Email.email_id]}
            )
            self._table_loop(
                self.inputs.amo, AmoAccount, {"index_elements": [AmoAccount.email_id]}
            )
            self._table_loop(
                self.inputs.fxa,
                FirefoxAccount,
                {"index_elements": [FirefoxAccount.email_id]},
            )
            self._table_loop(
                self.inputs.waitlists, Waitlist, {"constraint": "uix_wl_email_name"}
            )
            self._table_loop(
                self.inputs.newsletters, Newsletter, {"constraint": "uix_email_name"}
            )
