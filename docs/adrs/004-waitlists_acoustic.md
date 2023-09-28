# Waitlists in Acoustic

* Status: proposed
* Deciders: <CTMS stakeholders> + <Basket stakeholders>
* Date: June 30, 2023

## Context and Problem Statement

Users join products waiting lists. Marketing wants to reach out when the product becomes available in a certain country or on a certain platform.

There needs to be a convenient way to target users waiting for a certain product from a certain country or platform (or other additional fields).

CTMS holds this waitlist data, but currently does not synchronize it to Acoustic.

## Decision Drivers

In order to choose our solution we considered the following criteria:

- **Complexity**: Low → High: how complex is the solution
- **Cost**: Low → High: how much engineering efforts is required
- **Level of self-service**: Low → High: how much efforts are necessary

## Considered Options

1. [Option 1 - Fields on the main table](#option-1---fields-on-the-main-table)
2. [Option 2 - One relational table]()
3. [Option 3 - Several relational tables]()
3. [Option 4 - Rely on contact lists]()

## Decision Outcome

Chosen option: Option 2 because it has the highest level of self-service and the lowest cost and complexity. Plus, it follows what we already have in place for newsletters.

## Pros and Cons of the Options

### Option 1 - Fields on the main table

With this solution, we add columns on the Acoustic main table, following the same approach as newsletters and VPN/Relay waitlists.

For example, currently we have the following columns:

* `vpn_waitlist_geo`
* `vpn_waitlist_platform`
* `relay_waitlist_geo`

For example, the marketing team uses the `*_geo` columns to target users waiting for the product from a specific country. Obviously, it will be empty for most contacts in the main table.

**Complexity**: Mid

This does not increase the complexity of the code base, since it follows an existing pattern.

However, technical debt increases over time. Because if we had to onboard many waitlists, with many additional fields, the number of columns on the main table could become very large and not very practicable.

**Cost**: Low

We already have the code in place for VPN and Relay where we sync columns with this pattern `{name}_waitlist_{field}`.

**Level of self-service**: Low

In order to synchronize a new waitlist on Acoustic, we would have to:

1. Create the column(s) in Acoustic
2. Declare the column(s) in CTMS using `acoustic.py fields add main:{name}_waitlist_{field}`


### Option 2 - One relational table

A new relational table, `waitlist`, almost equivalent to the PostgreSQL, but with fields being fattened as columns.

Since we have a single table for all waitlists, its columns will be the union of all waitlists different fields. If waitlists have all very different types of extra fields, these columns will mostly have empty cells.

**Complexity**: Low

This does not increase the complexity of the code base, since it follows an existing pattern.

**Cost**: Low

The code was trivial to implement since it follow exactly the same approach as for the newsletter relational table.

**Level of self-service**: Mid-High

In order to synchronize a new waitlist on Acoustic that has the same fields as others, no action would be required.

Otherwise, if the waitlist has a specific field that does not exist yet, then we would have to:

1. Create the column(s) in Acoustic
2. Declare the column(s) in CTMS using `acoustic.py fields add waitlist:{field}`

### Option 3 - Several relational tables

With this solution, we have a dedicated relational table for each waitlist. Each table contains the appropriate columns.

**Complexity**: Mid

The Acoustic service code currently relies on a finite list of tables. With this solution, it would become slightly more abstract and manage an arbitrary number of tables.

**Cost**: Mid

Some refactoring would be necessary, but globally this solution would follow what we currently do for newsletters.

**Level of self-service**: Low

In order to synchronize a new waitlist on Acoustic, we would have to:

1. Create the relational table in Acoustic
2. Declare the column(s) in CTMS using `acoustic.py fields add {name}:{field}`

### Option 4 - Rely on contact lists

With this solution, CTMS would process the wailists records and create contacts lists based on predefined segmentation.

For example, CTMS would create and maintain in sync contact lists per product and country and per platform.

**Complexity**: Mid

The concept is relatively simple. Since this is accomplished in background tasks, performance is not a major concern. And if implemented simply using queries, the complexity would be limited to the timestamp based synchronization.

**Cost**: Mid

The approach would be new in the Acoustic service code base, and we would have to leverage Acoustic APIs that we haven't used until now.

**Level of self-service**: Mid

We could imagine to have default segmentation criteria.

In order to synchronize a new waitlist on Acoustic that has the same predefined fields as others, no action would be required.

Otherwise, if the waitlist has a specific field to distinguish contacts:

1. Modify the code to add the distinction field or query
2. Redeploy
