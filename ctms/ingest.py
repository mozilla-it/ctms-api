from dataclasses import dataclass, fields
from typing import Generator, List, Optional

from pydantic import BaseModel
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import Connection

from ctms.database import Base
from ctms.models import AmoAccount, Email, FirefoxAccount, Newsletter, VpnWaitlist
from ctms.schemas import (
    AddOnsTableSchema,
    EmailTableSchema,
    FirefoxAccountsTableSchema,
    NewsletterTableSchema,
    VpnWaitlistTableSchema,
)


@dataclass
class InputIOs:
    amo: Optional[Generator[AddOnsTableSchema, None, None]] = None
    emails: Optional[Generator[EmailTableSchema, None, None]] = None
    fxa: Optional[Generator[FirefoxAccountsTableSchema, None, None]] = None
    vpn_waitlist: Optional[Generator[VpnWaitlistTableSchema, None, None]] = None
    newsletters: Optional[Generator[NewsletterTableSchema, None, None]] = None

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
    ):
        self.inputs = inputs
        self.db = connection
        self.batch_size = batch_size

    def _insert_batch(self, batch: List[BaseModel], table: Base, stmt_args: dict):
        if len(batch) == 0:
            return

        # TODO: Handle things like `psycopg2.errors.DatatypeMismatch: column "email_id" is of type uuid but expression is of type integer`
        # smartly. This should mean something like recording which records
        # failed and why maybe if we're lucky? Also retries for disconnects
        # or other kinds of failures?
        stmt = insert(table).values([r.dict() for r in batch])
        stmt = stmt.on_conflict_do_update(**stmt_args, set_=dict(stmt.excluded))
        self.db.execute(stmt)

    def _table_loop(
        self,
        feed: Generator[BaseModel, None, None],
        table: Base,
        stmt_args: dict,
    ):
        batch = []
        for model in feed:
            batch.append(model)
            if len(batch) == self.batch_size:
                self._insert_batch(batch, table, stmt_args)
                batch = []
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
                self.inputs.vpn_waitlist,
                VpnWaitlist,
                {"index_elements": [VpnWaitlist.email_id]},
            )
            self._table_loop(
                self.inputs.newsletters, Newsletter, {"constraint": "uix_email_name"}
            )
