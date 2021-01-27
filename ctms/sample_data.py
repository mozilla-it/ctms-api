from uuid import UUID

from .models import ContactMainSchema, ContactSchema

SAMPLE_CONTACTS = {
    UUID("93db83d4-4119-4e0c-af87-a713786fa81d"): ContactSchema(
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
    ),
}
