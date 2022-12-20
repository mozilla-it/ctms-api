import re
from datetime import datetime, timezone
from uuid import uuid4


class NonCanonicalError(BaseException):
    pass


def _ensure_timestamps(line: dict):
    create_ts = line.get("create_timestamp")
    update_ts = line.get("update_timestamp")
    if create_ts and update_ts:
        return

    if create_ts and not update_ts:
        line["update_timestamp"] = create_ts
    elif not create_ts and update_ts:
        line["create_timestamp"] = update_ts
    else:
        line["create_timestamp"] = datetime.now(timezone.utc)
        line["update_timestamp"] = datetime.now(timezone.utc)


def _fix_booleans(line: dict, fields: list):
    for bool_var in fields:
        if line.get(bool_var) in ["1", 1, "true"]:
            line[bool_var] = True
        elif line.get(bool_var) in ["0", 0, "false"]:
            line[bool_var] = False


def email_modifier(i: int, line: dict, isdev: bool, canonical_mapping, skip_writes):
    if canonical_mapping.get(line["email_id"]):
        raise NonCanonicalError  # We don't insert non-canonical email records
    _ensure_timestamps(line)
    if isdev:
        line["primary_email"] = f"{line['primary_email']}@example.com"

    if not line.get("primary_email"):
        skip_writes.add(line["email_id"])
        raise NonCanonicalError  # We don't insert non-canonical email records

    _fix_booleans(line, ["double_opt_in", "has_opted_out_of_email"])
    return line


def amo_modifier(i: int, line: dict, isdev: bool, canonical_mapping, skip_writes):
    email_id = line["email_id"]
    if canonical_mapping.get(line["email_id"]) or email_id in skip_writes:
        raise NonCanonicalError  # We don't insert non-canonical email records
    _ensure_timestamps(line)
    newline = {}
    for key, val in line.items():
        key = re.sub("^amo_", "", key)
        newline[key] = val
    _fix_booleans(newline, ["user", "email_opt_in"])
    return newline


def fxa_modifier(i: int, line: dict, isdev: bool, canonical_mapping, skip_writes):
    email_id = line["email_id"]
    if canonical_mapping.get(email_id) or email_id in skip_writes:
        raise NonCanonicalError  # We don't insert non-canonical email records
    _ensure_timestamps(line)
    if isdev:
        if line.get("fxa_primary_email"):
            line["fxa_primary_email"] = f"{line['fxa_primary_email']}@example.com"
        line.setdefault("fxa_id", str(uuid4()))
    newline = {}
    for key, val in line.items():
        if key != "fxa_id":
            key = re.sub("^fxa_", "", key)
        newline[key] = val
    _fix_booleans(newline, ["account_deleted"])
    return newline


def newsletter_modifier(
    i: int, line: dict, isdev: bool, canonical_mapping, skip_writes
):
    email_id = line["email_id"]
    if email_id in skip_writes:
        raise NonCanonicalError  # We don't insert non-canonical email records

    # For newsletters only, we actually replace the email_id
    # with the canonical id so that we don't lose subscriptions

    canonical_id = canonical_mapping.get(email_id)
    if canonical_id:
        line["email_id"] = canonical_id

    _ensure_timestamps(line)
    newline = {}
    for key, val in line.items():
        key = re.sub("^newsletter_", "", key)
        newline[key] = val
    _fix_booleans(newline, ["subscribed"])
    return newline


def waitlist_modifier(i: int, line: dict, isdev: bool, canonical_mapping, skip_writes):
    email_id = line["email_id"]
    if canonical_mapping.get(email_id) or email_id in skip_writes:
        raise NonCanonicalError  # We don't insert non-canonical email records
    _ensure_timestamps(line)
    newline = {}
    for key, val in line.items():
        key = re.sub("^waitlist_", "", key)
        newline[key] = val
    return newline
