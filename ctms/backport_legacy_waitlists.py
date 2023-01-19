from copy import deepcopy
from typing import Dict, Optional

from pydantic import UUID4
from sqlalchemy.orm import Session

from .models import Waitlist
from .schemas import RelayWaitlistInSchema, VpnWaitlistInSchema, WaitlistInSchema


def backport_newsletters_waitlists(
    db: Session, email_id: UUID4, input_data, schema_class
):
    """
    The role of this function is to turn the waitlists that were implemented using basic
    newsletters in CTMS-136 into real waitlists.
    """
    formatted = deepcopy(input_data) if schema_class == dict else input_data.dict()

    if formatted.get("waitlists") == "UNSUBSCRIBE":
        return input_data

    # This will be empty on contact creation.
    waitlists_in_db = {
        wl.name: {"name": wl.name, "source": wl.source, "fields": wl.fields}
        for wl in db.query(Waitlist).filter(Waitlist.email_id == email_id).all()
    }

    # This backport function is called after `format_legacy_vpn_relay_waitlist_input()`
    # hence we can lookup the `waitlists` field in the input data.
    input_waitlists_by_name = {wl["name"]: wl for wl in formatted.get("waitlists", [])}

    relay_newsletters_to_backport = []
    input_newsletters = formatted.get("newsletters", [])
    if input_newsletters == "UNSUBSCRIBE":
        for waitlist in waitlists_in_db.values():
            if waitlist["name"].startswith("relay-"):
                relay_newsletters_to_backport.append(
                    {"name": waitlist["name"] + "-waitlist", "subscribed": False}
                )
    else:
        for newsletter in input_newsletters:
            # We are looking of `relay-*-waitlist`, but not `relay` which is already processed
            # and turned into the `relay_waitlist` attribute by Basket already.
            if newsletter["name"].startswith("relay-"):
                if (
                    newsletter["name"].replace("-waitlist", "")
                    not in input_waitlists_by_name
                ):
                    relay_newsletters_to_backport.append(newsletter)

    if not relay_newsletters_to_backport:
        # Nothing to do.
        return input_data

    main_relay = input_waitlists_by_name.get("relay")
    if not main_relay:
        # We have no information about the main `relay` waitlist in payload.
        main_relay = waitlists_in_db.get("relay")

    if not main_relay:
        # This is problematic: a `relay-*-waitlist` newsletter was subscribed, without
        # the main `relay` waitlist information.
        names = ", ".join([nl["name"] for nl in relay_newsletters_to_backport])
        raise ValueError(f"Relay country cannot be found for {names}")

    # Now that all available information was gathered, backport.
    for newsletter in relay_newsletters_to_backport:
        waitlist_name = newsletter["name"].replace("-waitlist", "")
        if not newsletter.get("subscribed", True):
            input_waitlists_by_name[waitlist_name] = {
                "name": waitlist_name,
                "subscribed": False,
            }
        else:
            input_waitlists_by_name[waitlist_name] = {
                **main_relay,
                "name": waitlist_name,
            }

    formatted["waitlists"] = list(input_waitlists_by_name.values())
    return formatted if schema_class == dict else schema_class(**formatted)


def format_legacy_vpn_relay_waitlist_input(
    db: Session, email_id: UUID4, input_data, schema_class, metrics: Optional[Dict]
):
    """
    Mimic a recent payload format using the values in database.
    """
    # Use a dict to handle all the different schemas for create, create_or_update, or update
    formatted = deepcopy(input_data) if schema_class == dict else input_data.dict()

    if metrics and ("vpn_waitlist" in formatted or "relay_waitlist" in formatted):
        metrics["legacy_waitlists_requests"].inc()

    if len(formatted.get("waitlists", [])) > 0:
        # We are dealing with the current format. Nothing to do.
        return input_data

    existing_waitlists = {}
    if "vpn_waitlist" in formatted or "relay_waitlist" in formatted:
        rows = db.query(Waitlist).filter(Waitlist.email_id == email_id).all()
        existing_waitlists = {wl.name: wl for wl in rows}

    to_update = []
    if "vpn_waitlist" in formatted:
        has_vpn = "vpn" in existing_waitlists
        if formatted["vpn_waitlist"] == "DELETE" or formatted["vpn_waitlist"] is None:
            if has_vpn:
                to_update.append(WaitlistInSchema(name="vpn", subscribed=False))
        else:
            # Create, update, or remove the vpn waitlist record.
            parsed_vpn = VpnWaitlistInSchema(**formatted["vpn_waitlist"])
            if has_vpn and parsed_vpn.is_default():
                to_update.append(WaitlistInSchema(name="vpn", subscribed=False))
            else:
                # Create or update.
                to_update.append(
                    WaitlistInSchema(
                        name="vpn",
                        fields={"geo": parsed_vpn.geo, "platform": parsed_vpn.platform},
                    )
                )
                # Note: if `waitlists` was explicitly specified as an empty list and the `vpn_waitlist` fields too,
                # this would have precedence. Since our schemas have an empty list of waitlists by default, this
                # preserves simplicity and serves our retro compatibility needs.

    if "relay_waitlist" in formatted:
        relay_waitlists = [
            wl for wl in existing_waitlists.values() if wl.name.startswith("relay")
        ]
        if (
            formatted["relay_waitlist"] == "DELETE"
            or formatted["relay_waitlist"] is None
        ):
            # When deleting the Relay waitlist at the contact level, deletes all Relay waitlists.
            for waitlist in relay_waitlists:
                to_update.append(WaitlistInSchema(name=waitlist.name, subscribed=False))
        else:
            parsed_relay = RelayWaitlistInSchema(**formatted["relay_waitlist"])
            if parsed_relay.is_default():
                for waitlist in relay_waitlists:
                    to_update.append(
                        WaitlistInSchema(name=waitlist.name, subscribed=False)
                    )
            else:
                if len(relay_waitlists) == 0:  # Create with default name.
                    to_update.append(
                        WaitlistInSchema(name="relay", fields={"geo": parsed_relay.geo})
                    )
                else:  # Update all.
                    for waitlist in relay_waitlists:
                        to_update.append(
                            WaitlistInSchema(
                                name=waitlist.name, fields={"geo": parsed_relay.geo}
                            )
                        )

    if to_update:
        formatted["waitlists"] = [wl.dict() for wl in to_update]

    return formatted if schema_class == dict else schema_class(**formatted)
