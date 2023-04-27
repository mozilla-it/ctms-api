from copy import deepcopy
from typing import Dict, Optional

from pydantic import UUID4
from sqlalchemy.orm import Session

from .models import Waitlist
from .schemas import RelayWaitlistInSchema, VpnWaitlistInSchema, WaitlistInSchema


def format_legacy_vpn_relay_waitlist_input(
    db: Session, email_id: UUID4, input_data, schema_class, metrics: Optional[Dict]
):
    """
    Mimic a recent payload format from the legacy `vpn_waitlist` and `relay_waitlist` fields.
    """
    # Use a dict to handle all the different schemas for create, create_or_update, or update
    formatted = deepcopy(input_data) if schema_class == dict else input_data.dict()

    if metrics and ("vpn_waitlist" in formatted or "relay_waitlist" in formatted):
        metrics["legacy_waitlists_requests"].inc()

    if len(formatted.get("waitlists", [])) > 0:
        # We are dealing with the current format. Nothing to do.
        return input_data

    rows = db.query(Waitlist).filter(Waitlist.email_id == email_id).all()
    existing_waitlists = {wl.name: wl for wl in rows}

    to_update = []

    # Waitlists are bound to newsletters.
    # Unsubscribing from the VPN newsletter or the Relay waitlists will un-enroll
    # from the related waitlists.
    input_newsletters = formatted.get("newsletters", [])
    input_relay_newsletters = []
    # If all newsletters are unsubscribed, then unsubscribe all waitlists in DB.
    if input_newsletters == "UNSUBSCRIBE":
        for waitlist in existing_waitlists.values():
            to_update.append(WaitlistInSchema(name=waitlist.name, subscribed=False))
    else:
        input_relay_newsletters = [
            nl for nl in input_newsletters if nl["name"].startswith("relay-")
        ]
        # Turn every waitlist newsletter unsubscription to an actual waitlist unsubscription.
        for newsletter in input_newsletters:
            if not newsletter["name"].endswith("-waitlist"):
                continue
            name = newsletter["name"].replace("-waitlist", "")
            # `guardian-vpn-waitlist` newsletter is the `vpn` waitlist.
            if name == "guardian-vpn":
                name = "vpn"
            if not newsletter.get("subscribed", True):
                to_update.append(WaitlistInSchema(name=name, subscribed=False))

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
                        source=existing_waitlists["vpn"].source if has_vpn else None,
                        fields={"geo": parsed_vpn.geo, "platform": parsed_vpn.platform},
                    )
                )
                # Note: if `waitlists` was explicitly specified as an empty list and the `vpn_waitlist` fields too,
                # this would have precedence. Since our schemas have an empty list of waitlists by default, this
                # preserves simplicity and serves our retro compatibility needs.

    relay_waitlists = [
        wl for wl in existing_waitlists.values() if wl.name.startswith("relay")
    ]

    # For Relay newsletters subscriptions, see below. For subscriptions, we can be sure that `relay_waitlist`
    # if provided since we enforce it in the `ContactInBase` and `ContactPatchSchema` schemas.

    if "relay_waitlist" in formatted:
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
                # `relay_waitlist` field was specified.
                if input_relay_newsletters:
                    # We are subscribing to a `relay-*-waitlist` newsletter.
                    # We don't care whether the contact had already subscribed
                    # to another Relay waitlist, we just subscribe.
                    for newsletter in input_relay_newsletters:
                        name = newsletter["name"].replace("-waitlist", "")
                        to_update.append(
                            WaitlistInSchema(
                                name=name, fields={"geo": parsed_relay.geo}
                            )
                        )
                elif len(relay_waitlists) == 0:
                    # We are subscribing to the `relay` waitlist for the first time.
                    to_update.append(
                        WaitlistInSchema(name="relay", fields={"geo": parsed_relay.geo})
                    )
                else:
                    # `relay_waitlist` was specified but without newsletter, hence update geo field
                    # of all subscribed Relay waitlists.
                    for waitlist in relay_waitlists:
                        to_update.append(
                            WaitlistInSchema(
                                name=waitlist.name,
                                source=waitlist.source,
                                fields={"geo": parsed_relay.geo},
                            )
                        )

    if to_update:
        formatted["waitlists"] = [wl.dict() for wl in to_update]

    return formatted if schema_class == dict else schema_class(**formatted)
