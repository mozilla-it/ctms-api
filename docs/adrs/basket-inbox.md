# Basket Inbox Endpoint

* Status: proposed
* Deciders: <CTMS stakeholders> + <Basket stakeholders>
* Date: March 28, 2022

## Context and Problem Statement

Onboarding new waiting lists requires changing, releasing, and redeploying Basket.

Basket uses some specific code to transform flat form data into CTMS nested objects, that has to be modified when a new field has to be sent to CTMS.
Our current approach to store customers waiting lists consists in adding a new field in the contact data. Therefore, onboarding a new waiting lists obliges us to modify Basket:

1. Open a pull-request to modify the CTMS mapping code in Basket
1. Request and wait for review
1. Request and wait for release
1. Request and wait for deployment

The amount of code to be modified is reasonably low, but the amount of coordination and efforts to enable a new waiting list is too high.

> Note: This document focuses on one part of the onboarding process only: Basket. There are other aeras within CTMS where the onboarding can be simplified too.

## Decision Drivers

In order to choose our solution we considered the following criteria:

- **Complexity**: Low → High: how complex is the solution
- **Onboarding Efforts**: Low → High: how much efforts are necessary
- **Separation of Concerns**: Fuzzy → Clear: whether each system has a clear role and scope

## Considered Options

1. [Option 0 - Do nothing](#option-0---do-nothing)
1. [Option 1 - Move mapping code from Basket to CTMS](#option-1---move-mapping-code-from-basket-to-ctms)

## Decision Outcome

Chosen option: Option 1 because

## Pros and Cons of the Options

### Option 0 - Do nothing

**Complexity**: N/A

**Onboarding Efforts**:

High: See problem statement.

**Separation of Concerns**:

Clear: Basket manages its schemas, and prepares data before posting it to CTMS.


### Option 1 - Move mapping code from Basket to CTMS

This option consists in moving the [Basket mapping transformation](https://github.com/mozmeao/basket/blob/341facbb2b199bfe2f26488942d0fa251010c1c8/basket/news/backends/ctms.py) into CTMS.

With this option, Basket will send its raw data to a new endpoint in CTMS (eg. `POST /inbox/basket`). CTMS will be in charge of transforming the incoming data into its internal format.

**Complexity**: Medium

The following has to be accomplished:

- duplicate the Basket trasformation code into a new CTMS endpoint
- change Basket to post the raw data on this new endpoint

**Onboarding Efforts**: Medium

When onboarding a new waiting list, Basket does not have to be changed anymore.

- A product team contacts the CTMS team to onboard a new use-case
- Captured fields are decided
- CTMS is modified to ingest new fields

**Separation of Concerns**: Fuzzy

CTMS currently has a clear contact management API, and consumers must comply.

By adding new specific endpoints dedicated to external systems in CTMS, we move the responsibility. CTMS is now in charge of transforming raw data from external systems in order to comply with its internal schema.

This is the tradeoff that we are willing to accept in this context, where the goal is to reduce the amount of efforts for onboarding. Plus, it could be limited to Basket data for now.
