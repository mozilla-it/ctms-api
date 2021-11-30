# Stripe Subscription Event Data Empowering Email User Journeys

* Status: implemented
* Deciders: Bryan Sieber, John Whitlock, Ben Bangert, Jon Buckley, (Benson Wong, Stephen Hood)
* Date: September 30, 2021

Technical Story: [design and document approach for marketing | https://mozilla-hub.atlassian.net/jira/software/c/projects/CTMS/boards/364?modal=detail&selectedIssue=CTMS-73]

## Context and Problem Statement

Marketing wants to be able to differentiate customers based on their subscription information to empower marketing campaigns.

## Decision Drivers

* Design sustainable system for longterm data-health
* FxA source of Truth
* Stripe rate limits


## Considered Options

* Cloud Function triggered through Firestore
* Background process in CTMS
* New temporary service

## Decision Outcome

Chosen option: " Cloud Function triggered through Firestore", because the event snapshots can be captured and published to a Pub/Sub, upon which they can be pushed to CTMS with a JWT. We believe this is a more sustainable option.
