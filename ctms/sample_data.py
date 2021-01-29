from uuid import UUID

from .models import (
    ContactAddonsSchema,
    ContactCommonVoiceSchema,
    ContactMainSchema,
    ContactSchema,
)

# A contact that has just some of the fields entered
SAMPLE_MINIMAL = ContactSchema(
    id=UUID("93db83d4-4119-4e0c-af87-a713786fa81d"),
    contact=ContactMainSchema(
        id="001A000001aABcDEFG",
        country="us",
        created_date="2014-01-22T15:24:00+00:00",
        email="ctms-user@example.com",
        lang="en",
        last_modified_date="2020-01-22T15:24:00.000+0000",
        optin=True,
        optout=False,
        postal_code="666",
        record_type="0124A0000001aABCDE",
        token="142e20b6-1ef5-43d8-b5f4-597430e956d7",
    ),
    newsletters=[
        "app-dev",
        "maker-party",
        "mozilla-foundation",
        "mozilla-learning-network",
    ],
)

# A contact that has all of the fields set
SAMPLE_MAXIMAL = ContactSchema(
    id=UUID("67e52c77-950f-4f28-accb-bb3ea1a2c51a"),
    amo=ContactAddonsSchema(
        display_name="#1 Mozilla Fan",
        homepage="https://www.mozilla.org/en-US/firefox/new/",
        id=123,
        last_login="2020-01-27T14:21:00.000+0000",
        location="The Internet",
        user=True,
    ),
    contact=ContactMainSchema(
        country="ca",
        created_date="2010-01-01T08:04:00+00:00",
        email="mozilla-fan@example.com",
        first_name="Fan of",
        format="H",
        id="001A000001aMozFan",
        lang="fr",
        last_modified_date="2020-01-28T14:50:00.000+0000",
        last_name="Mozilla",
        optin=True,
        optout=False,
        payee_id="cust_012345",
        postal_code="H2L",
        reason="done with this mailing list",
        record_type="0124A0000001aABCDE",
        source_url="https://developer.mozilla.org/fr/",
        token="d9ba6182-f5dd-4728-a477-2cc11bf62b69",
    ),
    cv=ContactCommonVoiceSchema(
        created_at="2020-10-14T16:05:21.423Z",
        days_interval=12,
        first_contribution_date="2020-10-15T10:07Z",
        goal_reached_at="2020-11-2T11:15:19.008Z",
        last_active_date="2021-1-10T11:15:19.008Z",
        two_day_streak=True,
    ),
    newsletters=[
        "about-addons",
        "about-mozilla",
        "ambassadors",
        "app-dev",
        "common-voice",
        "connected-devices",
        "developer-events",
        "firefox-accounts-journey",
        "firefox-desktop",
        "firefox-friends",
        "firefox-ios",
        "firefox-os",
        "firefox-welcome",
        "game-developer-conference",
        "get-involved",
        "guardian-vpn-waitlist",
        "hubs",
        "inhuman",
        "internet-health-report",
        "ios-beta-test-flight",
        "knowledge-is-power",
        "maker-party",
        "member-comm",
        "member-idealo",
        "member-tech",
        "member-tk",
        "miti",
        "mixed-reality",
        "mobile",
        "mozilla-and-you",
        "mozilla-fellowship-awardee-alumni",
        "mozilla-festival",
        "mozilla-foundation",
        "mozilla-general",
        "mozilla-leadership-network",
        "mozilla-learning-network",
        "mozilla-phone",
        "mozilla-technology",
        "mozilla-welcome",
        "mozillians-nda",
        "open-innovation-challenge",
        "open-leadership",
        "shape-web",
        "take-action-for-the-internet",
        "test-pilot",
        "view-source-conference-global",
        "view-source-conference-north-america",
        "webmaker",
    ],
)

# A sample user that has the OpenAPI schema examples
SAMPLE_EXAMPLE = ContactSchema(
    id=UUID("332de237-cab7-4461-bcc3-48e68f42bd5c"),
    amo=ContactAddonsSchema(**ContactAddonsSchema.Config.schema_extra["example"]),
    contact=ContactMainSchema(**ContactMainSchema.Config.schema_extra["example"]),
    cv=ContactCommonVoiceSchema(
        **ContactCommonVoiceSchema.Config.schema_extra["example"]
    ),
)


SAMPLE_CONTACTS = {
    SAMPLE_MINIMAL.id: SAMPLE_MINIMAL,
    SAMPLE_MAXIMAL.id: SAMPLE_MAXIMAL,
    SAMPLE_EXAMPLE.id: SAMPLE_EXAMPLE,
}
